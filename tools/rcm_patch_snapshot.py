"""Private, machine-bound RCM patch snapshot; never changes the game.

Copies only the installed RCM package and existing RCM character save files.
The shared Update Helper owns game-install manifests; this tool supplements
them with addon-specific rollback evidence. Never execute serialized Lua.
A successful snapshot is a non-atomic disk observation, not a game-save or
runtime receipt. Raw saves and path identities must stay under ignored artifacts.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import stat
import sys
import tempfile

from deploy_rcm import ADDON, manifest
from rcm_session_preflight import read_rift_config

MAX_FILE = 16 * 1024 * 1024
MAX_TOTAL = 64 * 1024 * 1024
MAX_FILES = 128
MAX_ENTRIES = 20000
SAVE_NAME = "RiftChatModern.lua"


def plain(path: Path, directory: bool) -> os.stat_result:
    """Reject symlinks/junctions and non-regular objects before traversing."""
    info = path.lstat()
    if path.is_symlink() or path.is_junction():
        raise ValueError("linked_path")
    if not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)):
        raise ValueError("unexpected_path_type")
    return info


def check_ancestry(path: Path) -> None:
    # Do not follow a redirected junction silently. The real OneDrive path
    # obtained from the client config is acceptable if its ancestors are plain.
    for parent in reversed((path, *path.parents)):
        plain(parent, True)


def discover(root: Path) -> list[Path]:
    """Bounded walk; copy only RCM files, never unrelated addon/character data."""
    addon = root / "Interface" / "AddOns" / ADDON
    saved = root / "Interface" / "Saved"
    check_ancestry(addon)
    if not (addon / "RiftAddon.toc").is_file():
        raise ValueError("missing_installed_manifest")
    files = []
    scanned = 0
    def failed(error: OSError) -> None:
        raise error
    for base, package in ((addon, True), (saved, False)):
        if not package and not base.exists() and not base.is_symlink() and not base.is_junction():
            continue
        check_ancestry(base)
        for folder, directories, names in base.walk(on_error=failed, follow_symlinks=False):
            scanned += len(directories) + len(names)
            if scanned > MAX_ENTRIES:
                raise ValueError("inventory_limit")
            for directory in directories:
                plain(folder / directory, True)
            for name in names:
                path = folder / name
                if package or (name.casefold() == SAVE_NAME.casefold()
                               and folder.name.casefold() == "savedvariables"):
                    plain(path, False)
                    files.append(path.relative_to(root))
                    if len(files) > MAX_FILES:
                        raise ValueError("file_count_limit")
    if len({str(p).casefold() for p in files}) != len(files):
        raise ValueError("case_collision")
    return sorted(files, key=lambda p: p.as_posix().casefold())


def stable_bytes(path: Path) -> bytes:
    """Read with size and identity guards; never deserialize executable Lua."""
    check_ancestry(path.parent)
    before = plain(path, False)
    if before.st_size > MAX_FILE:
        raise ValueError("file_size_limit")
    def identity(s):
        return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
    with path.open("rb") as reader:
        if identity(os.fstat(reader.fileno())) != identity(before):
            raise ValueError("file_changed")
        data = reader.read(MAX_FILE + 1)
        after = os.fstat(reader.fileno())
    if len(data) != before.st_size or identity(after) != identity(before):
        raise ValueError("file_changed")
    if identity(plain(path, False)) != identity(before):
        raise ValueError("file_changed")
    return data


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def snapshot(root: Path, output: Path, phase: str, host: str, source_version: str) -> dict:
    """Write a new private backup and publish a manifest only on success."""
    if phase not in ("before", "after"):
        raise ValueError("invalid_phase")
    check_ancestry(root)
    if output.exists() and (output.is_symlink() or output.is_junction()):
        raise ValueError("linked_output")
    if output.resolve().is_relative_to(root.resolve()):
        raise ValueError("output_overlaps_game_documents")
    inventory = discover(root)
    manifest_path = Path("Interface") / "AddOns" / ADDON / "RiftAddon.toc"
    original_manifest = stable_bytes(root / manifest_path)
    toc = original_manifest.decode("utf-8-sig")
    if not re.search(r'(?m)^\s*Identifier\s*=\s*"RiftChatModern"', toc):
        raise ValueError("unexpected_installed_identifier")
    version = re.search(r'(?m)^\s*Version\s*=\s*"(\d+\.\d+\.\d+)"', toc)
    if not version:
        raise ValueError("invalid_installed_version")
    # Validate the existing parent before creating any output directory.
    check_ancestry(output.parent)
    output.mkdir(exist_ok=True)
    check_ancestry(output)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    directory = Path(tempfile.mkdtemp(prefix=f"{stamp}-{host}-{phase}-", dir=output))
    rows = []
    total = 0
    for relative in inventory:
        data = stable_bytes(root / relative)
        total += len(data)
        if total > MAX_TOTAL:
            raise ValueError("total_size_limit")
        target = directory / "files" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as writer:
            writer.write(data)
        sha = digest(data)
        if digest(stable_bytes(target)) != sha:
            raise ValueError("backup_verification_failed")
        rows.append({"relative": relative.as_posix(), "bytes": len(data), "sha256": sha})
    # Re-inventory and re-hash original bytes to catch observable changes while
    # copying. This still cannot prove an atomic snapshot of a running client.
    if inventory != discover(root):
        raise ValueError("inventory_changed")
    for relative, row in zip(inventory, rows):
        if digest(stable_bytes(root / relative)) != row["sha256"]:
            raise ValueError("file_changed_during_snapshot")
    if stable_bytes(root / manifest_path) != original_manifest:
        raise ValueError("manifest_changed")
    report = {
        "schema": "RCM_PATCH_SNAPSHOT_V1", "phase": phase, "host": host,
        "capturedUtc": datetime.now(timezone.utc).isoformat(),
        "installedVersion": version.group(1), "sourceVersion": source_version,
        "addonFiles": sum(p.parts[1] == "AddOns" for p in inventory),
        "savedVariableFiles": sum(p.parts[1] == "Saved" for p in inventory),
        "bytes": total, "files": rows, "consistency": "non_atomic_rechecked",
        "gameSaveTriggered": False, "runtimeVerified": False,
    }
    with (directory / "manifest.json").open("x", encoding="utf-8") as writer:
        json.dump(report, writer, indent=2)
        writer.write("\n")
    # Never print private character names, save contents, or account paths.
    return {key: val for key, val in report.items() if key != "files"} | {
        "artifactDirectory": directory.name, "manifestSha256": digest(stable_bytes(directory / "manifest.json"))
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expect-host", required=True)
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    args = parser.parse_args(argv)
    host = socket.gethostname()
    if host.casefold() != args.expect_host.casefold() or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", host):
        print(json.dumps({"status": "blocked", "reason": "host_mismatch"}))
        return 2
    try:
        project = Path(__file__).resolve().parents[1]
        cfg = read_rift_config(Path.home(), os.environ)
        configured = cfg["settings"].get("DocumentsDirectory")
        if not configured or cfg.get("readError"):
            raise ValueError("unverified_documents_directory")
        source_version = manifest(project / "addon" / ADDON)["version"]
        report = snapshot(Path(configured), project / "artifacts" / "patch-snapshots",
                          args.phase, host, source_version)
        print(json.dumps({"status": "captured", **report}, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        # OS errors may contain private paths. Never echo arbitrary error text.
        print(json.dumps({"status": "blocked", "errorType": type(exc).__name__,
                          "reason": str(exc) if isinstance(exc, ValueError) and
                          re.fullmatch(r"[a-z_]+", str(exc)) else "snapshot_failed",
                          "gameInputSent": False}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
