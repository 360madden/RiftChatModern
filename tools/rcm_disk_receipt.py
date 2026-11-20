"""Read-only RCM SavedVariables disk receipt verifier.

The game's Save.Begin event can stage a receipt, but only a fresh serialized
SavedVariables file is on-disk evidence. This tool reads ONLY scalar schema,
checkpoint, message-kind and ID fields; it never prints message bodies or
executes the serialized Lua.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import socket
import sys

MAX_SIZE = 8 * 1024 * 1024
REQUIRED = ("formatVersion", "schemaVersion", "sequence", "historyCount",
            "nextId", "lastHistoryId", "lastImportId", "at")


class DiskAuditError(ValueError):
    pass


def mask_strings_comments(source: str) -> str:
    """Keep offsets; mask strings with a non-whitespace sentinel and comments with blanks."""
    result = list(source)
    index = 0
    size = len(source)
    while index < size:
        c = source[index]
        if c == "-" and index + 1 < size and source[index + 1] == "-":
            while index < size and source[index] not in "\r\n":
                result[index] = " "
                index += 1
            continue
        if c in ('"', "'"):
            quote = c
            result[index] = "~"
            index += 1
            closed = False
            while index < size:
                if source[index] == "\\":
                    result[index] = "~"
                    index += 1
                    if index < size:
                        result[index] = "~"
                        index += 1
                    continue
                if source[index] == quote:
                    result[index] = "~"
                    index += 1
                    closed = True
                    break
                result[index] = "~"
                index += 1
            if not closed:
                raise DiskAuditError("unterminated_lua_string")
            continue
        index += 1
    return "".join(result)


def depths_for(masked: str) -> list[int]:
    depth = 0
    out = []
    for ch in masked:
        out.append(depth)
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                raise DiskAuditError("unbalanced_saved_table")
    if depth != 0:
        raise DiskAuditError("unbalanced_saved_table")
    return out


def table_end(masked: str, start: int) -> int:
    if masked[start] != "{":
        raise DiskAuditError("not_a_lua_table")
    nest = 1
    for i in range(start + 1, len(masked)):
        if masked[i] == "{":
            nest += 1
        elif masked[i] == "}":
            nest -= 1
            if nest == 0:
                return i
    raise DiskAuditError("unclosed_lua_table")


def find_child_table(masked: str, depths: list[int], scope: tuple[int, int],
                     name: str, depth: int) -> tuple[int, int] | None:
    pattern = re.compile(r"\b" + re.escape(name) + r"\s*=\s*(\{)")
    found = []
    for m in pattern.finditer(masked, scope[0] + 1, scope[1]):
        if depths[m.start()] == depth:
            brace = m.start(1)
            found.append((brace, table_end(masked, brace)))
    if len(found) > 1:
        raise DiskAuditError("ambiguous_" + name + "_tables")
    return found[0] if found else None


def scalar(masked: str, depths: list[int], scope: tuple[int, int],
           name: str, depth: int, allow_float: bool = False) -> int | float | None:
    pattern = re.compile(r"\b" + re.escape(name) +
                         r"\s*=\s*(-?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)")
    matches = [m.group(1) for m in pattern.finditer(masked, scope[0]+1, scope[1])
               if depths[m.start()] == depth]
    if len(matches) > 1:
        raise DiskAuditError("duplicate_" + name)
    if not matches:
        return None
    try:
        number = float(matches[0])
    except ValueError as exc:
        raise DiskAuditError("invalid_" + name) from exc
    if not math.isfinite(number) or number < 0:
        raise DiskAuditError("invalid_" + name)
    if allow_float:
        return number
    if number % 1 != 0 or number > 10**13:
        raise DiskAuditError("invalid_" + name)
    return int(number)


def saved_history_rows(source: str, masked: str, depths: list[int],
                       history: tuple[int, int] | None) -> list[dict]:
    if history is None:
        return []
    opening, closing = history
    rows = []
    for i in range(opening + 1, closing):
        if masked[i] != "{" or depths[i] != depths[opening] + 1:
            continue
        scope = (i, table_end(masked, i))
        ident = scalar(masked, depths, scope, "id", depths[i] + 1)
        m = [x for x in re.compile(r"\bkind\s*=\s*").finditer(masked, scope[0]+1, scope[1])
             if depths[x.start()] == depths[i]+1]
        if len(m) != 1:
            raise DiskAuditError("invalid_history_kind")
        kind = re.match(r"""(["'])([a-z_]+)\1""", source[m[0].end():])
        if ident is None or kind is None:
            raise DiskAuditError("invalid_history_row")
        rows.append({"id": ident, "kind": kind.group(2)})
    if len(rows) > 240:
        raise DiskAuditError("unexpected_history_size")
    return rows


def inspect_saved_data(source: str) -> dict:
    if len(source.encode("utf-8")) > MAX_SIZE:
        raise DiskAuditError("saved_file_too_large")
    masked = mask_strings_comments(source)
    depths = depths_for(masked)
    roots = list(re.finditer(r"(?m)^\s*RiftChatModernSaved\s*=\s*(\{)", masked))
    if len(roots) != 1:
        raise DiskAuditError("missing_or_multiple_rcm_root")
    start = roots[0].start(1)
    root = (start, table_end(masked, start))
    if depths[start] != 0:
        raise DiskAuditError("invalid_root_depth")
    schema = scalar(masked, depths, root, "schemaVersion", 1)
    hist = find_child_table(masked, depths, root, "history", 1)
    checkpoint = find_child_table(masked, depths, root, "saveCheckpoint", 1)
    rows = saved_history_rows(source, masked, depths, hist)
    last_import = max((x["id"] for x in rows if x["kind"] == "import"), default=0)
    last_id = rows[-1]["id"] if rows else 0
    record = {}
    if checkpoint:
        for name in REQUIRED:
            value = scalar(masked, depths, checkpoint, name, 2,
                           allow_float=name == "at")
            if value is None:
                raise DiskAuditError("incomplete_checkpoint_" + name)
            record[name] = value
    consistent = bool(record) and schema == 2 and (
        record["formatVersion"] == 1 and record["schemaVersion"] == 2 and
        1 <= record["sequence"] <= 1000000000 and
        record["historyCount"] == len(rows) and
        record["lastHistoryId"] == last_id and
        record["lastImportId"] == last_import and
        record["nextId"] > last_id)
    return {"schemaVersionOnDisk": schema,
            "historyRowsOnDisk": len(rows),
            "importRowsOnDisk": sum(x["kind"] == "import" for x in rows),
            "lastHistoryIdOnDisk": last_id,
            "lastImportedIdOnDisk": last_import,
            "checkpointOnDisk": bool(record),
            "checkpointMetadataConsistent": consistent,
            "checkpoint": record if record else None,
            "messageBodiesEmitted": False,
            "engineSaveEndProven": False}


def peer_file_metadata(file: Path) -> dict:
    try:
        base = file.stat().st_mtime
        files = [p for p in file.parent.iterdir()
                 if p.is_file() and not p.is_symlink()
                 and p.suffix.casefold() == ".lua" and p != file]
        times = [x.stat().st_mtime for x in files]
        return {"otherAddonSaveFiles": len(times),
                "othersWrittenWithinTwoSecondsOfRcm": sum(abs(x-base)<=2 for x in times),
                "othersWrittenLaterByTenSecondsOrMore": sum(x>=base+10 for x in times)}
    except OSError:
        return {"peerMetadataAvailable": False}


def run(args: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, required=True,
                        help="Exact character-scoped RiftChatModern.lua SavedVariables file")
    parser.add_argument("--expect-host", default=None)
    parser.add_argument("--require-checkpoint", action="store_true")
    options = parser.parse_args(args)
    host = socket.gethostname()
    try:
        if options.expect_host and host.casefold() != options.expect_host.casefold():
            raise DiskAuditError("wrong_machine")
        path = options.file
        if path.name.casefold() != "riftchatmodern.lua" or path.is_symlink():
            raise DiskAuditError("incorrect_saved_filename")
        if not path.is_file() or path.stat().st_size > MAX_SIZE:
            raise DiskAuditError("missing_or_oversize_saved_file")
        data = path.read_bytes()
        parsed = inspect_saved_data(data.decode("utf-8-sig", "strict"))
        result = {"schema": "RCM_DISK_RECEIPT_V1", "machine": host,
                  "savedFile": str(path), "bytes": len(data),
                  "sha256": hashlib.sha256(data).hexdigest(),
                  "modifiedLocal": datetime.fromtimestamp(path.stat().st_mtime)
                  .astimezone().isoformat(),
                  "diskReceiptVerified": parsed["checkpointOnDisk"] and
                  parsed["checkpointMetadataConsistent"],
                  "savedVariablesModified": False}
        result.update(parsed)
        result["peerSaveMetadata"] = peer_file_metadata(path)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 2 if options.require_checkpoint and not result["diskReceiptVerified"] else 0
    except (DiskAuditError, OSError, UnicodeError) as exc:
        print(json.dumps({"schema": "RCM_DISK_RECEIPT_V1",
                          "machine": host, "error": str(exc),
                          "savedVariablesModified": False,
                          "diskReceiptVerified": False}))
        return 1


if __name__ == "__main__":
    sys.exit(run())
