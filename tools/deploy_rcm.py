"""Rift Chat Modern guarded deployment and SHA-256 verification.

Examples from a PowerShell terminal:
  python tools/deploy_rcm.py
  python tools/deploy_rcm.py --apply --expect-host AMD-DESKTOP

Dry-run by default. The install must already exist with the expected toc.
Replacing an existing RIFT addon while the game runs is supported: after a
verified copy, run /reloadui inside RIFT to load the new Lua and manifest.
Never touches SavedVariables or unrelated addon folders.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

from rcm_session_preflight import GAME, parse_tasklist, read_rift_config

ADDON = "RiftChatModern"
MODULES = ("Core.lua", "AddonMessages.lua", "NativeChatProbe.lua",
           "ConsoleCategories.lua", "ConsoleMirror.lua", "HostIngress.lua", "Main.lua")
MAX_FILE = 16 * 1024 * 1024


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as reader:
        for chunk in iter(lambda: reader.read(131072), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest(source: Path) -> dict:
    toc = source / "RiftAddon.toc"
    if toc.is_symlink() or not toc.is_file():
        raise ValueError("Missing plain RCM RiftAddon.toc")
    data = toc.read_text(encoding="utf-8-sig")
    def named(key: str) -> str:
        match = re.search(rf'(?m)^\s*{re.escape(key)}\s*=\s*"([^"\r\n]+)"', data)
        if not match:
            raise ValueError(f"Manifest missing {key}")
        return match.group(1)
    if named("Identifier") != ADDON:
        raise ValueError("Incorrect manifest Identifier")
    version = named("Version")
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Invalid version format")
    if named("Environment") != "4.3":
        raise ValueError("Unexpected RIFT addon Environment")
    if not named("Email"):
        raise ValueError("Manifest missing Email")
    block = re.search(r'RunOnStartup\s*=\s*\{([^}]*)\}', data)
    if not block:
        raise ValueError("Manifest missing RunOnStartup")
    modules = tuple(re.findall(r'"([^"]+)"', block.group(1)))
    if modules != MODULES:
        raise ValueError("RunOnStartup list/order mismatch")
    if not re.search(
        r'SavedVariables\s*=\s*\{\s*RiftChatModernSaved\s*=\s*"character"\s*\}', data
    ):
        raise ValueError("Character SavedVariables manifest contract broken")
    for name in MODULES:
        if not (source / name).is_file():
            raise ValueError(f"Missing startup file {name}")
    if (source / "Core.lua").is_symlink() or (source / "Main.lua").is_symlink():
        raise ValueError("Symlinked startup file")
    if f'version="{version}"' not in (source / "Core.lua").read_text(encoding="utf-8"):
        raise ValueError("Core version differs from manifest")
    if f'or "{version}"' not in (source / "Main.lua").read_text(encoding="utf-8"):
        raise ValueError("Main fallback version differs from manifest")
    return {"identifier": ADDON, "version": version, "modules": modules}


def discover_targets(home: Path, environ: dict) -> list[Path]:
    # An explicit client override is authoritative, even when the addon is
    # absent there. Never select a stale installation as a fallback.
    config = read_rift_config(home, environ)
    if config.get("readError"):
        raise ValueError("RIFT DocumentsDirectory configuration unreadable")
    configured = config["settings"].get("DocumentsDirectory")
    if configured:
        folder = Path(configured) / "Interface" / "AddOns" / ADDON
        return [folder] if folder.is_dir() and (folder / "RiftAddon.toc").is_file() else []
    roots = []
    for name in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        value = environ.get(name)
        if value and Path(value).is_absolute():
            roots.append(Path(value) / "Documents")
    roots.extend([home / "OneDrive" / "Documents", home / "Documents"])
    seen = set()
    found = []
    for root in roots:
        folder = root / "RIFT" / "Interface" / "AddOns" / ADDON
        key = os.path.normcase(os.path.normpath(str(folder))).casefold()
        if key in seen:
            continue
        seen.add(key)
        if folder.is_dir() and (folder / "RiftAddon.toc").is_file():
            found.append(folder)
    return found


def select_target(explicit: Path | None, home: Path, environ: dict) -> Path:
    """An explicit path may disambiguate discovery, not override RIFT config."""
    if explicit is None:
        choices = discover_targets(home, environ)
        if len(choices) != 1:
            raise ValueError(f"Expected exactly one verified installation, found {len(choices)}")
        return choices[0]
    if not explicit.is_absolute():
        raise ValueError("Target must be an absolute path")
    config = read_rift_config(home, environ)
    if config.get("readError"):
        raise ValueError("RIFT DocumentsDirectory configuration unreadable")
    configured = config["settings"].get("DocumentsDirectory")
    if configured:
        expected = Path(configured) / "Interface" / "AddOns" / ADDON
        if explicit != expected:
            raise ValueError("Explicit target does not match configured RIFT DocumentsDirectory")
    return explicit


def payload(source: Path) -> list[Path]:
    result = []
    for file in source.rglob("*"):
        if file.is_symlink():
            raise ValueError(f"Refusing source symlink {file}")
        if not file.is_file():
            continue
        if file.stat().st_size > MAX_FILE:
            raise ValueError(f"Source file too large: {file}")
        result.append(file.relative_to(source))
    if len(result) < len(MODULES) + 1:
        raise ValueError("Incomplete source payload")
    if sorted(p.name for p in result if p.suffix.lower() == ".lua") != sorted(MODULES):
        raise ValueError("Unexpected Lua file not declared in RunOnStartup")
    return sorted(result)


def preflight(source: Path, target: Path) -> dict:
    expected = manifest(source)
    if not target.is_absolute():
        raise ValueError("Target must be an absolute path")
    if target.is_symlink() or not target.is_dir() or target.name != ADDON:
        raise ValueError("Target must be an existing non-symlinked RiftChatModern folder")
    existing = target / "RiftAddon.toc"
    if existing.is_symlink() or not existing.is_file():
        raise ValueError("Target has no established RCM manifest")
    if not re.search(
        r'(?m)^\s*Identifier\s*=\s*"RiftChatModern"', existing.read_text(encoding="utf-8-sig")
    ):
        raise ValueError("Target is not an established RCM installation")
    all_files = payload(source)
    changes = []
    source_hashes, target_hashes = {}, {}
    for rel in all_files:
        installed = target / rel
        if installed.is_symlink():
            raise ValueError("Refusing installed path link")
        # New releases may introduce texture subdirectories. Missing parent
        # directories are allowed, but existing links/files in their place
        # must fail closed before any asset is copied.
        parent = installed.parent
        while parent != target:
            if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
                raise ValueError(f"Unsafe installed parent: {parent}")
            parent = parent.parent
        if installed.exists() and not installed.is_file():
            raise ValueError(f"Installed item is not a file: {rel}")
        source_hashes[rel] = sha256(source / rel)
        target_hashes[rel] = sha256(installed) if installed.is_file() else None
        if target_hashes[rel] != source_hashes[rel]:
            changes.append(rel)
    return {"version": expected["version"], "files": all_files, "changed": changes,
            "sourceHashes": source_hashes, "targetHashes": target_hashes}


def _rollback_file_hash(path: Path) -> str | None:
    """Inspect recovery paths without following a replaced file or parent link."""
    for parent in path.parents:
        if parent.is_symlink() or parent.is_junction() or not parent.is_dir():
            raise RuntimeError(f"Unsafe rollback parent: {parent}")
    if path.is_symlink() or path.is_junction():
        raise RuntimeError(f"Unsafe rollback link: {path}")
    if not path.exists():
        return None
    if not path.is_file():
        raise RuntimeError(f"Rollback item is not a file: {path}")
    return sha256(path)


def _rollback_file(destination: Path, original: Path | None,
                   deployed_hash: str, original_hash: str | None) -> None:
    """Restore only our written bytes, using a verified, staged backup."""
    current_hash = _rollback_file_hash(destination)
    if current_hash == original_hash:
        return  # Already restored (or a newly added file already removed).
    if current_hash != deployed_hash:
        raise RuntimeError("Destination changed after deployment; preserved current state")
    if original is None:
        destination.unlink()
        if _rollback_file_hash(destination) is not None:
            raise RuntimeError("Destination reappeared after removal; preserved current state")
        return
    if _rollback_file_hash(original) != original_hash:
        raise RuntimeError("Retained backup checksum mismatch")
    fd, staging = tempfile.mkstemp(prefix=".rcm-rollback-", suffix=".tmp", dir=destination.parent)
    try:
        with os.fdopen(fd, "wb") as out, original.open("rb") as inp:
            shutil.copyfileobj(inp, out)
        if sha256(Path(staging)) != original_hash:
            raise RuntimeError("Staged backup checksum mismatch")
        # A backup read can fail or take time. Never truncate the installed
        # file, and check it again before the final atomic replacement.
        if _rollback_file_hash(destination) != deployed_hash:
            raise RuntimeError("Destination changed during rollback; preserved current state")
        os.replace(staging, destination)
        if _rollback_file_hash(destination) != original_hash:
            raise RuntimeError("Restored file checksum mismatch")
    finally:
        Path(staging).unlink(missing_ok=True)


def apply_copy(source: Path, target: Path, plan: dict, project: Path) -> dict:
    """Copy after full preflight, preserve originals, roll back on failure."""
    if not target.is_absolute():
        raise ValueError("Target must be an absolute path")
    # Guard the entire plan, including initially unchanged files. An old
    # dry-run must not overwrite a newer edit or deploy a different source.
    current = preflight(source, target)
    if current != plan:
        raise RuntimeError("Deployment source or target changed since preflight")
    pending = plan["changed"]
    if not pending:
        return {"changed": [], "backups": None, "rollback": False}
    backup_root = project / "artifacts" / "deploy-backups"
    backup_root.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = Path(tempfile.mkdtemp(prefix=f"{now}-", dir=backup_root))
    originals = {}
    written = []
    created_dirs = []
    try:
        for rel in pending:
            destination = target / rel
            expected_hash = plan["targetHashes"][rel]
            if destination.is_symlink() or destination.is_junction():
                raise RuntimeError("Deployment target changed to a link")
            actual_hash = sha256(destination) if destination.is_file() else None
            if actual_hash != expected_hash:
                raise RuntimeError("Deployment target changed before backup")
            if destination.exists():
                backup = backup_dir / rel
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(destination, backup)
                if sha256(backup) != expected_hash or sha256(destination) != expected_hash:
                    raise RuntimeError(f"Backup verification failed: {rel}")
                originals[rel] = backup
            else:
                originals[rel] = None
        for rel in pending:
            destination = target / rel
            # Preflight allows absent asset folders. Create only directories
            # directly under the verified addon folder, after backups exist.
            missing = []
            parent = destination.parent
            while parent != target:
                if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
                    raise RuntimeError(f"Unsafe destination parent: {parent}")
                if not parent.exists():
                    missing.append(parent)
                parent = parent.parent
            for folder in reversed(missing):
                folder.mkdir()
                created_dirs.append(folder)
            fd, staging = tempfile.mkstemp(prefix=".rcm-deploy-", suffix=".tmp", dir=destination.parent)
            try:
                with os.fdopen(fd, "wb") as out, (source / rel).open("rb") as inp:
                    shutil.copyfileobj(inp, out)
                if sha256(Path(staging)) != plan["sourceHashes"][rel]:
                    raise RuntimeError(f"Staged source changed: {rel}")
                if destination.is_symlink() or destination.is_junction():
                    raise RuntimeError("Deployment target changed to a link")
                current_hash = sha256(destination) if destination.is_file() else None
                if current_hash != plan["targetHashes"][rel]:
                    raise RuntimeError(f"Deployment target changed before copy: {rel}")
                os.replace(staging, destination)
                written.append(rel)
            finally:
                if os.path.exists(staging):
                    os.unlink(staging)
        bad = [str(rel) for rel in plan["files"]
               if not (target / rel).is_file()
               or sha256(target / rel) != plan["sourceHashes"][rel]
               or sha256(source / rel) != plan["sourceHashes"][rel]]
        if bad:
            raise RuntimeError("Deployment hash mismatch: " + ", ".join(bad))
    except Exception as error:
        rollback_errors = []
        for rel in reversed(written):
            try:
                _rollback_file(target / rel, originals[rel],
                               plan["sourceHashes"][rel], plan["targetHashes"][rel])
            except Exception as rollback_error:
                # Continue recovering independent files; retain every failure
                # and the original deployment error for manual recovery.
                rollback_errors.append(f"{rel}: {rollback_error}")
        # Remove only directories created by this specific deployment, and
        # only if empty after file rollback. Never remove pre-existing data.
        for folder in reversed(created_dirs):
            try:
                if not folder.is_symlink() and not folder.is_junction():
                    folder.rmdir()
            except OSError:
                pass
        if rollback_errors:
            raise RuntimeError(
                f"Deployment failed: {error}; rollback incomplete: "
                + "; ".join(rollback_errors)
                + f"; retained backups: {backup_dir}"
            ) from error
        raise
    return {"changed": [str(rel) for rel in pending],
            "backups": str(backup_dir), "rollback": False}


def running_game_pids() -> list[int]:
    """Independently query Windows processes; unknown state refuses apply."""
    if os.name != "nt":
        raise RuntimeError("game_process_query_unavailable_non_windows")
    try:
        completed = subprocess.run(["tasklist.exe", "/fo", "csv", "/nh"],
                                   capture_output=True, text=True, timeout=12,
                                   encoding="utf-8", errors="replace")
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError("game_process_query_failed") from error
    if completed.returncode != 0 or not completed.stdout.strip():
        raise RuntimeError("game_process_query_failed")
    # Reuse the exact-process parser from RCM's read-only session preflight.
    # An Error Handler companion is not evidence that the game is running.
    rows = parse_tasklist(completed.stdout)
    pids = [row["pid"] for row in rows if row["name"] == GAME]
    if GAME in completed.stdout.casefold() and not pids:
        # Never treat a malformed PID for a listed game as proof it is closed.
        raise RuntimeError("game_process_query_unparseable")
    return pids


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Copy after explicit host verification")
    parser.add_argument("--expect-host", default=None, help="Expected exact Windows hostname")
    parser.add_argument("--target", type=Path, default=None, help="Existing installed RCM addon folder")
    args = parser.parse_args(argv)

    host = socket.gethostname()
    project = Path(__file__).resolve().parents[1]
    source = project / "addon" / ADDON
    try:
        if args.expect_host and host.casefold() != args.expect_host.casefold():
            raise ValueError("Expected host does not match the verified machine")
        if args.apply and not args.expect_host:
            raise ValueError("Apply requires --expect-host matching the verified machine")
        target = select_target(args.target, Path.home(), os.environ)
        plan = preflight(source, target)
        changes = [str(x) for x in plan["changed"]]
        result = {
            "machine": host, "source": str(source), "installed": str(target),
            "version": plan["version"], "mode": "apply" if args.apply else "dry_run",
            "sourceFiles": len(plan["files"]), "changedFiles": changes,
            "savedVariablesTouched": False, "gameInputSent": False,
            "physicalGameLoaded": False,
            "gameProcessCheck": "not_checked"
        }
        if args.apply:
            # Existing RIFT addons may be updated on disk while rift_x64 runs.
            # Actual Lua/toc changes become active after /reloadui, not merely
            # after a successful filesystem copy. Avoid a needless game exit.
            live_pids = running_game_pids()
            result["gameProcessCheck"] = "running" if live_pids else "closed"
            result["runningGamePids"] = live_pids
            result["reloadUiRequired"] = bool(live_pids and changes)
            result["reloadUiCommand"] = "/reloadui" if live_pids and changes else None
            result["runtimeReloadVerified"] = False
            # The process query may take several seconds. Re-read the client
            # configuration before touching the target; a changed selection
            # invalidates the plan even if the old package hashes still match.
            if select_target(args.target, Path.home(), os.environ) != target:
                raise RuntimeError("Deployment target selection changed since preflight")
            result.update(apply_copy(source, target, plan, project))
            result["hashVerified"] = all(
                sha256(source / rel) == sha256(target / rel) for rel in plan["files"]
            )
            if not result["hashVerified"]:
                raise RuntimeError("Post-deployment checksum mismatch")
        else:
            result["hashVerified"] = len(changes) == 0
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        print(json.dumps({"machine": host, "mode": "apply" if args.apply else "dry_run",
                          "success": False, "error": str(error), "gameInputSent": False}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
