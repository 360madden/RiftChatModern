"""Read-only receipts for RIFT's own screenshots (not Windows desktop capture).

Default source: [Client] DocumentsDirectory in the existing Rift.cfg, then
Screenshots. Never presses a key, changes focus, writes an image, or opens RIFT.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import socket
import sys
import time

from PIL import Image, UnidentifiedImageError

MAX_CONFIG_BYTES = 512 * 1024
MAX_IMAGE_BYTES = 32 * 1024 * 1024
MAX_FOLDER_ENTRIES = 5000
IMAGE_NAME = re.compile(
    r"(?:\d{4}-\d\d-\d\d_\d{6}|rift_auto_\d{4}-\d\d-\d\d_\d{6}_\d{3}_[0-9a-f]{6})"
    r"\.(?:jpg|jpeg|png)\Z", re.I,
)


class ScreenshotReceiptError(ValueError):
    pass


def _inside_windows_config(config: Path) -> Path:
    if not config.is_file() or config.stat().st_size > MAX_CONFIG_BYTES:
        raise ScreenshotReceiptError("missing_or_oversized_rift_config")
    try:
        data = config.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as e:
        raise ScreenshotReceiptError("unreadable_rift_config") from e
    section = ""
    value = None
    for line in data.splitlines():
        header = re.fullmatch(r"\s*\[([A-Za-z_0-9]+)\]\s*", line)
        if header:
            section = header.group(1).lower()
            continue
        if section != "client":
            continue
        item = re.fullmatch(r"\s*DocumentsDirectory\s*=\s*(.*?)\s*", line, re.I)
        if item:
            value = item.group(1).strip().strip('"')
    if not value or len(value) > 2048 or any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ScreenshotReceiptError("missing_or_invalid_documents_directory")
    root = Path(os.path.expandvars(value))
    if not root.is_absolute() or "%" in str(root):
        raise ScreenshotReceiptError("documents_directory_not_absolute")
    folder = root / "Screenshots"
    if folder.is_symlink() or not folder.is_dir():
        raise ScreenshotReceiptError("screenshots_folder_not_available")
    return folder


def _candidates(folder: Path) -> list[Path]:
    items: list[Path] = []
    count = 0
    try:
        for p in folder.iterdir():
            count += 1
            if count > MAX_FOLDER_ENTRIES:
                raise ScreenshotReceiptError("screenshots_directory_entry_limit")
            if IMAGE_NAME.fullmatch(p.name) and p.is_file() and not p.is_symlink():
                items.append(p)
    except OSError as exc:
        raise ScreenshotReceiptError("screenshots_directory_unreadable") from exc
    items.sort(key=lambda p: (p.stat().st_mtime_ns, p.name), reverse=True)
    return items


def _image_receipt(file: Path) -> dict:
    if file.is_symlink() or not file.is_file():
        raise ScreenshotReceiptError("screenshot_missing_or_symlink")
    before = file.stat()
    if not 64 <= before.st_size <= MAX_IMAGE_BYTES:
        raise ScreenshotReceiptError("invalid_screenshot_size")
    blob = file.read_bytes()
    if len(blob) != before.st_size:
        raise ScreenshotReceiptError("screenshot_changed_during_read")
    try:
        with Image.open(io.BytesIO(blob)) as im:
            fmt = im.format
            width, height = im.size
            if fmt not in ("JPEG", "PNG") or not (200 <= width <= 16384 and 200 <= height <= 16384):
                raise ScreenshotReceiptError("unsupported_image_format_or_dimensions")
            if (fmt == "JPEG" and file.suffix.lower() not in (".jpg", ".jpeg")) or (
                fmt == "PNG" and file.suffix.lower() != ".png"
            ):
                raise ScreenshotReceiptError("screenshot_extension_format_mismatch")
            im.load()  # reject truncated data, not just a valid leading image header
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise ScreenshotReceiptError("corrupted_or_unreadable_screenshot") from exc
    after = file.stat()
    attributes = lambda s: (s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    if attributes(before) != attributes(after):
        raise ScreenshotReceiptError("screenshot_changed_during_read")
    return {
        "file": str(file),
        "filename": file.name,
        "bytes": before.st_size,
        "modifiedEpochNs": before.st_mtime_ns,
        "format": fmt,
        "width": width,
        "height": height,
        "sha256": hashlib.sha256(blob).hexdigest(),
    }


def inspect_folder(folder: Path, after_ns: int | None = None) -> dict:
    if folder.is_symlink() or not folder.is_dir():
        raise ScreenshotReceiptError("screenshots_folder_not_available")
    matches = _candidates(folder)
    eligible = [p for p in matches if after_ns is None or p.stat().st_mtime_ns > after_ns]
    if not eligible:
        return {
            "status": "no_new_screenshot" if after_ns is not None else "no_screenshots",
            "folder": str(folder),
            "candidates": len(matches),
            "afterEpochNs": after_ns,
            "freshnessVerified": False,
        }
    selection = _image_receipt(eligible[0])
    return {
        "status": "new_screenshot_file" if after_ns is not None else "existing_screenshot_file",
        "folder": str(folder),
        "candidates": len(matches),
        "afterEpochNs": after_ns,
        "freshnessVerified": after_ns is not None,
        "screenshot": selection,
    }


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expect-host", required=True)
    parser.add_argument("--config", type=Path, default=Path(os.environ.get("APPDATA", "")) / "RIFT" / "Rift.cfg")
    parser.add_argument("--baseline", action="store_true", help="Report a fresh before-key timestamp; no screenshot requested")
    parser.add_argument("--after-ns", type=int, default=None)
    parser.add_argument("--require-new", action="store_true")
    parser.add_argument("--wait-ms", type=int, default=0)
    options = parser.parse_args(argv)
    try:
        if options.expect_host.lower() != socket.gethostname().lower():
            raise ScreenshotReceiptError("unexpected_machine_identity")
        if options.wait_ms < 0 or options.wait_ms > 15000:
            raise ScreenshotReceiptError("wait_ms_out_of_bounds")
        if options.after_ns is not None and (options.after_ns < 0 or options.after_ns > time.time_ns() + 60_000_000_000):
            raise ScreenshotReceiptError("invalid_after_epoch_ns")
        if options.baseline and (options.require_new or options.after_ns is not None or options.wait_ms):
            raise ScreenshotReceiptError("baseline_must_be_a_separate_read_only_operation")
        if options.require_new and options.after_ns is None:
            raise ScreenshotReceiptError("require_new_requires_after_ns")
        if options.wait_ms and (not options.require_new or options.after_ns is None):
            raise ScreenshotReceiptError("wait_requires_new_screenshot_boundary")
        folder = _inside_windows_config(options.config)
        before_time = time.time_ns()
        if options.baseline:
            result = {
                "status": "baseline_recorded",
                "folder": str(folder),
                "baselineEpochNs": before_time,
                "candidates": len(_candidates(folder)),
                "freshnessVerified": False,
            }
        else:
            deadline = time.monotonic() + options.wait_ms / 1000
            while True:
                result = inspect_folder(folder, options.after_ns)
                if result["status"] not in ("no_new_screenshot", "no_screenshots") or time.monotonic() >= deadline:
                    break
                time.sleep(0.1)
        result.update({
            "schema": "RCM_GAME_SCREENSHOT_RECEIPT_V1",
            "machine": socket.gethostname(),
            "source": "rift_cfg_documents_screenshots",
            "gameInputSent": False,
            "keyPressVerified": False,
            "gameWindowCorrelated": False,
            "physicalRiftOriginVerified": False,
            "filesChanged": False,
        })
        print(json.dumps(result, indent=2))
        return 2 if options.require_new and not result["freshnessVerified"] else 0
    except (OSError, ScreenshotReceiptError) as exc:
        print(json.dumps({
            "schema": "RCM_GAME_SCREENSHOT_RECEIPT_V1",
            "status": "refused",
            "reason": str(exc),
            "gameInputSent": False,
            "filesChanged": False,
            "physicalRiftOriginVerified": False,
        }))
        return 1


if __name__ == "__main__":
    sys.exit(run())
