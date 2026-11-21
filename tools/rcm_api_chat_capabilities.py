"""Read-only chat/console capability projection from a persisted API Atlas capture.

This is NOT a live RIFT query or a claim that undocumented runtime APIs are
impossible. It does not copy, rewrite, or execute snapshot documentation.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sys

MAX_BYTES = 12 * 1024 * 1024
MAX_ENTRIES = 50000
CHAT_EVENTS_ALREADY_KNOWN_NON_SOCIAL = frozenset({
    "Event.Chat.Notify", "Event.Chat.Npc"
})


class CapabilityAuditError(ValueError):
    pass


def inspect_snapshot(data: object) -> dict:
    if not isinstance(data, dict):
        raise CapabilityAuditError("invalid_snapshot_root")
    capture = data.get("capture")
    source = data.get("source")
    entries = data.get("entries")
    if not isinstance(capture, dict) or not isinstance(source, dict):
        raise CapabilityAuditError("missing_capture_provenance")
    if source.get("kind") != "rift-client":
        raise CapabilityAuditError("not_rift_client")
    if not isinstance(entries, list) or not (1 <= len(entries) <= MAX_ENTRIES):
        raise CapabilityAuditError("invalid_catalog_entries")
    status = capture.get("status")
    if not isinstance(status, str) or len(status) > 40:
        raise CapabilityAuditError("invalid_capture_status")
    captured_at = source.get("captured_at")
    if captured_at is not None:
        if not isinstance(captured_at, str) or len(captured_at) > 60:
            raise CapabilityAuditError("invalid_capture_timestamp")
        try:
            datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise CapabilityAuditError("invalid_capture_timestamp") from exc
    client_version = source.get("client_version")
    if client_version is not None and (
        not isinstance(client_version, str)
        or len(client_version) > 300
        or any(ord(char) < 32 for char in client_version)
    ):
        raise CapabilityAuditError("invalid_client_version")

    names: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise CapabilityAuditError("invalid_api_entry")
        name = entry.get("name")
        if not isinstance(name, str) or not (1 <= len(name) <= 256):
            raise CapabilityAuditError("invalid_api_name")
        if any(ord(char) < 32 or ord(char) == 127 for char in name):
            raise CapabilityAuditError("invalid_api_name")
        if name in names:
            raise CapabilityAuditError("duplicate_api_name")
        names.add(name)

    def listing(prefix: str) -> list[str]:
        return sorted(name for name in names if name.startswith(prefix))

    chat = listing("Event.Chat.")
    candidates = sorted(set(chat) - CHAT_EVENTS_ALREADY_KNOWN_NON_SOCIAL)
    return {
        "schema": "RCM_CHAT_API_CAPABILITIES_V1",
        "sourceType": "persisted_rift_client_documentation",
        "sourceCaptureAt": captured_at,
        "sourceClientVersion": client_version,
        "captureStatus": status,
        "captureComplete": status == "complete",
        "entriesScanned": len(names),
        "documentedChatEvents": chat,
        "possiblePlayerChatEventCandidates": candidates,
        "documentedConsoleInspection": listing("Inspect.Console."),
        "documentedConsoleOutput": listing("Command.Console."),
        "documentedNativeConsoleObjects": listing("UI.Native.Console"),
        "addonMessageReceive": (
            "Event.Message.Receive" if "Event.Message.Receive" in names else None
        ),
        "documentedAddonMessageCommands": listing("Command.Message."),
        "snapshotOnlyNotLive": True,
        "nativePlayerChatReceptionVerified": False,
        "generalPlayerChatCaptureEstablished": False,
        "nextEvidenceGate": (
            "inspect_new_chat_event_in_live_client" if candidates
            else "prove_game_noncombat_log_or_read_only_client_chat_source"
        ),
        "snapshotChanged": False,
    }


def inspect_file(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise CapabilityAuditError("snapshot_file_missing_or_link")
    before = path.stat()
    if not (0 < before.st_size <= MAX_BYTES):
        raise CapabilityAuditError("snapshot_size_out_of_bounds")
    contents = path.read_bytes()
    after = path.stat()
    identity = lambda item: (
        item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_ctime_ns
    )
    if identity(before) != identity(after) or len(contents) != after.st_size:
        raise CapabilityAuditError("snapshot_changed_during_read")
    try:
        parsed = json.loads(contents.decode("utf-8-sig", errors="strict"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CapabilityAuditError("invalid_snapshot_json") from exc
    return inspect_snapshot(parsed)


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path,
                        default=Path.home() / ".api-atlas" / "snapshot.json",
                        help="Existing persisted API Atlas JSON snapshot")
    parser.add_argument("--require-complete", action="store_true",
                        help="Exit 2 if source capture did not finish completely")
    options = parser.parse_args(argv)
    try:
        result = inspect_file(options.snapshot)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if options.require_complete and not result["captureComplete"]:
            return 2
        return 0
    except (OSError, CapabilityAuditError) as error:
        print(json.dumps({
            "schema": "RCM_CHAT_API_CAPABILITIES_V1",
            "snapshotOnlyNotLive": True,
            "nativePlayerChatReceptionVerified": False,
            "snapshotChanged": False,
            "error": str(error),
        }, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(run())
