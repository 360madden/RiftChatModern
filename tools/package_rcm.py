"""Build a reproducible RCM addon-only ZIP; never install or access game data.

The exact runtime allowlist excludes development files, private journals and
SavedVariables. Packaging uses the existing deployment manifest validator and
Lua 5.1 syntax compiler. Same source bytes yield the same ZIP bytes, regardless
of source file timestamps. The optional --check reconstructs and verifies it.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import zipfile

from audit_rift_addon_archive import MAX_ARCHIVE, MAX_MEMBER, compile_lua
from deploy_rcm import ADDON, MODULES, manifest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "addon" / ADDON
OUTPUT = ROOT / "dist"
FONTS = ("Lato-Bold.ttf", "Lato-Regular.ttf", "Lato-OFL.txt")
TEXTURES = tuple("glass_" + item + ".png" for item in (
    "button", "button_hover", "detail", "header", "history", "input",
    "panel", "primary", "primary_hover", "tab_active", "tab_hover", "tab_idle"))
LAYOUT = {"": (*MODULES, "RiftAddon.toc"), "fonts": FONTS, "textures": TEXTURES}
ZIP_TIME = (1980, 1, 1, 0, 0, 0)
# Windows cloud placeholders, junctions and ordinary symlinks are not
# reproducible release inputs. Read only real, local source files.
REPARSE_POINT = 0x400


def plain_info(path: Path, *, directory: bool = False):
    info = path.lstat()
    expected = stat.S_ISDIR if directory else stat.S_ISREG
    if (not expected(info.st_mode)
            or getattr(info, "st_file_attributes", 0) & REPARSE_POINT):
        raise ValueError("non_plain_package_path")
    return info


def identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def read_regular(path: Path, maximum: int) -> bytes:
    """Bound reads and reject observable edits/replacements during a read."""
    before = plain_info(path)
    if before.st_size > maximum:
        raise ValueError("package_file_too_large")
    with path.open("rb") as reader:
        opened = os.fstat(reader.fileno())
        if not stat.S_ISREG(opened.st_mode) or identity(opened) != identity(before):
            raise ValueError("package_file_changed")
        data = reader.read(maximum + 1)
        after = os.fstat(reader.fileno())
    if (len(data) > maximum or len(data) != before.st_size
            or identity(before) != identity(after)
            or identity(before) != identity(plain_info(path))):
        raise ValueError("package_file_changed")
    return data


def collect(source: Path) -> dict[str, bytes]:
    """Reject unexpected files/directories instead of silently bundling them."""
    plain_info(source, directory=True)
    records = {}
    for folder, filenames in LAYOUT.items():
        parent = source / folder
        plain_info(parent, directory=True)
        allowed = set(filenames)
        if not folder:
            allowed.update(("fonts", "textures"))
        if {child.name for child in parent.iterdir()} != allowed:
            raise ValueError("package_layout_mismatch")
        for name in filenames:
            relative = f"{folder}/{name}" if folder else name
            records[relative] = read_regular(parent / name, MAX_MEMBER)
            if not records[relative]:
                raise ValueError("empty_package_file")
    return records


@dataclass(frozen=True)
class Package:
    version: str
    data: bytes
    files: int

    @property
    def filename(self):
        return f"{ADDON}-{self.version}.zip"

    @property
    def sha256(self):
        return hashlib.sha256(self.data).hexdigest()

    @property
    def checksum(self):
        return f"{self.sha256}  {self.filename}\n".encode("ascii")


def build_package(source: Path = SOURCE) -> Package:
    records = collect(source)
    # Validate the exact captured bytes, not a second potentially changed
    # working-tree read. The existing manifest validator owns the startup
    # order, schema scope, version synchronization and addon identity checks.
    with tempfile.TemporaryDirectory(prefix="rcm-package-") as folder:
        staged = Path(folder) / ADDON
        for name, data in records.items():
            path = staged / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        version = manifest(staged)["version"]
    for name in MODULES:
        valid, _ = compile_lua(records[name].decode("utf-8-sig"))
        if valid is not True:
            raise ValueError("lua51_compile_unavailable_or_invalid:" + name)

    # Stored ZIP entries avoid zlib-version drift. Fixed metadata and sorted
    # POSIX names make identical source bytes reproduce the same package.
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, data in sorted(records.items()):
            info = zipfile.ZipInfo(f"{ADDON}/{name}", ZIP_TIME)
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, data)
    packed = output.getvalue()
    if len(packed) > MAX_ARCHIVE:
        raise ValueError("package_archive_too_large")
    # Independently reopen the ZIP and verify every entry, including assets.
    with zipfile.ZipFile(io.BytesIO(packed)) as archive:
        expected = [f"{ADDON}/{name}" for name in sorted(records)]
        if archive.namelist() != expected:
            raise ValueError("package_archive_inventory_mismatch")
        for name, data in records.items():
            if archive.read(f"{ADDON}/{name}") != data:
                raise ValueError("package_archive_content_mismatch")
    return Package(version, packed, len(records))


def existing_matches(path: Path, expected: bytes) -> bool:
    """Missing is distinct from corrupt, different, or unsafe output."""
    try:
        path.lstat()
    except FileNotFoundError:
        return False
    if read_regular(path, len(expected)) != expected:
        raise ValueError("existing_package_output_conflicts")
    return True


def publish_one(path: Path, data: bytes):
    if existing_matches(path, data):
        return
    # Publish a fully written file without ever replacing existing output.
    # NTFS and common local filesystems support hard-link creation. If the
    # filesystem does not, fail rather than fall back to a partial overwrite.
    fd, temporary = tempfile.mkstemp(prefix=".rcm-package-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as writer:
            writer.write(data)
            writer.flush()
            os.fsync(writer.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if not existing_matches(path, data):
                raise ValueError("package_output_changed")
    finally:
        Path(temporary).unlink()
    if not existing_matches(path, data):
        raise ValueError("package_publication_unverified")


def publish_package(package: Package, folder: Path = OUTPUT, *, check=False):
    if not check:
        folder.mkdir(exist_ok=True)
    plain_info(folder, directory=True)
    outputs = ((folder / package.filename, package.data),
               (folder / (package.filename + ".sha256"), package.checksum))
    # Validate BOTH existing destinations before publishing either. A missing
    # checksum after interruption can be repaired by repeating the build.
    matches = [existing_matches(path, data) for path, data in outputs]
    if check and not all(matches):
        raise ValueError("package_output_missing")
    if not check:
        for (path, data), present in zip(outputs, matches):
            if not present:
                publish_one(path, data)
    if not all(existing_matches(path, data) for path, data in outputs):
        raise ValueError("package_publication_unverified")
    return {"schema": "RCM_ADDON_PACKAGE_V1", "version": package.version,
            "archive": package.filename, "sha256": package.sha256,
            "bytes": len(package.data), "runtimeFiles": package.files,
            "lua51SyntaxVerified": True, "archiveBytesVerified": True,
            "physicalRiftAcceptanceVerified": False, "gameFilesTouched": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="Verify existing dist outputs against current source; no writes")
    args = parser.parse_args(argv)
    try:
        report = publish_package(build_package(), check=args.check)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(json.dumps({"success": False, "reason": str(error)[:200],
                          "gameFilesTouched": False}), file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
