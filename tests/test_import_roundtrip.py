"""End-to-end manual import → Lua Save.Begin → disk audit → fresh Lua client.

Fixtures deliberately serialize a minimal, known subset of RIFT character
SavedVariables. This is NOT a physical RIFT serializer or live-game proof.
The real Node encoder and Lua 5.1 runtime are exercised without game input.
"""
from __future__ import annotations

import contextlib
import io
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from test_addon import RIFT_MOCK, _lua_quote
from rcm_disk_receipt import inspect_saved_data, run as audit_disk

try:
    from lupa.lua51 import LuaRuntime
except ImportError:
    LuaRuntime = None

ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / "addon" / "RiftChatModern"
NODE = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
ENCODER = ROOT / "tools" / "rcm-chat-import.cjs"
MODULES = ("Core.lua", "AddonMessages.lua", "NativeChatProbe.lua", "ConsoleCategories.lua",
           "ConsoleMirror.lua", "HostIngress.lua", "Main.lua")


def encode_scalar(value):
    if isinstance(value, str):
        return _lua_quote(value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(value):
            raise ValueError("nonfinite_fixture_number")
        return repr(value)
    raise ValueError("unexpected_fixture_value")


def table_fields(source, keys):
    entries = []
    for name in keys:
        value = source[name]
        if value is not None:
            entries.append(f"{name} = {encode_scalar(value)}")
    return "{" + ", ".join(entries) + "}"


def serialize_fixture(saved):
    """Serialize only recognized RCM scalar structures; never run saved input."""
    history = saved["history"]
    row_keys = ("id", "at", "kind", "origin", "source", "text",
                "channelKind", "channelName", "importToken")
    row_text = [table_fields(history[i], row_keys)
                for i in range(1, len(history) + 1)]
    root = [f"schemaVersion = {encode_scalar(saved['schemaVersion'])}",
            f"nextId = {encode_scalar(saved['nextId'])}",
            "history = {" + ", ".join(row_text) + "}"]
    receipt = saved["saveCheckpoint"]
    if receipt is not None:
        checkpoint_keys = ("formatVersion", "schemaVersion", "sequence",
                           "at", "historyCount", "nextId", "lastHistoryId",
                           "lastImportId")
        root.append("saveCheckpoint = " + table_fields(receipt, checkpoint_keys))
    return "RiftChatModernSaved = {" + ", ".join(root) + "}\n"


@unittest.skipUnless(LuaRuntime is not None and NODE, "Lua 5.1 and Node.js needed")
class ImportRoundTripTests(unittest.TestCase):
    def client(self, saved_source=None):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(RIFT_MOCK)
        if saved_source is not None:
            lua.execute(saved_source)
        for module in MODULES:
            text = (ADDON / module).read_text(encoding="utf-8")
            lua.execute("assert(loadstring(" + _lua_quote(text) +
                        "))({identifier='RiftChatModern',version='0.2.23'}, {})")
        lua.execute('fire(Event.Addon.SavedVariables.Load.End, "RiftChatModern")')
        lua.execute('fire(Event.Addon.Load.End, "RiftChatModern")')
        return lua

    def manual_commands(self):
        result = subprocess.run(
            [NODE, str(ENCODER), "--kind", "guild", "--sender", "RCMProbe",
             "--channel", "Guild", "--text", "persistence fixture 🌋",
             "--id", "B3A0705FD6AA"],
            capture_output=True, text=True, encoding="utf-8",
            timeout=10, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertFalse(data["automaticGameInput"])
        self.assertEqual(data["kind"], "guild")
        return data["commands"]

    def import_to_client(self, lua, commands):
        for command in commands:
            self.assertTrue(command.startswith("/rcm import "))
            lua.execute("fire(slash.rcm, " + _lua_quote(command[5:]) + ")")
        imports, total = lua.globals().RiftChatModernAPI.GetHistory(
            "imports", "", 10, 0)
        self.assertEqual(total, 1)
        self.assertEqual(imports[1]["kind"], "import")
        self.assertEqual(imports[1]["origin"], "host_manual")
        self.assertEqual(imports[1]["channelKind"], "guild")
        return int(imports[1]["id"])

    def test_manual_import_checkpoint_disk_audit_and_fresh_reload(self):
        lua = self.client()
        commands = self.manual_commands()
        history_id = self.import_to_client(lua, commands)
        state = lua.globals().RiftChatModernAPI.GetHostIngressStatus()
        self.assertEqual(state["lastImportedMessageId"], history_id)
        self.assertEqual(state["lastRetainedImportMessageId"], history_id)
        self.assertEqual(state["lastImportToken"], "B3A0705FD6AA")
        before = serialize_fixture(lua.globals().RiftChatModernSaved)
        before_report = inspect_saved_data(before, required_import_id=history_id,
                                           required_import_token="B3A0705FD6AA")
        self.assertTrue(before_report["requiredImportIdentityMatched"])
        self.assertFalse(before_report["checkpointOnDisk"])

        # Stage the RIFT Save.Begin callback but never claim real disk delivery.
        lua.execute('fire(Event.Addon.SavedVariables.Save.Begin, "RiftChatModern")')
        checkpoint = lua.globals().RiftChatModernSaved["saveCheckpoint"]
        self.assertEqual(int(checkpoint["lastImportId"]), history_id)
        self.assertEqual(int(checkpoint["nextId"]), history_id + 1)
        fixture = serialize_fixture(lua.globals().RiftChatModernSaved)
        report = inspect_saved_data(fixture, required_import_id=history_id,
                                    required_import_token="B3A0705FD6AA")
        self.assertTrue(report["requiredImportIdentityMatched"])
        self.assertTrue(report["checkpointMetadataConsistent"])
        self.assertEqual(report["historyKindsOnDisk"]["import"], 1)

        # Exercise the actual disk checker against temporary bytes.
        with tempfile.TemporaryDirectory(prefix="rcm-import-roundtrip-") as folder:
            path = Path(folder) / "RiftChatModern.lua"
            path.write_text(fixture, encoding="utf-8")
            digest_before = path.read_bytes()
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = audit_disk(["--file", str(path), "--require-import-id",
                                   str(history_id), "--require-import-token",
                                   "B3A0705FD6AA"])
            self.assertEqual(code, 0)
            self.assertTrue(json.loads(out.getvalue())["requiredImportIdPresent"])
            self.assertEqual(path.read_bytes(), digest_before)

        # A new Lua VM must recover imported history, not the session counter.
        fresh = self.client(fixture)
        fresh_status = fresh.globals().RiftChatModernAPI.GetHostIngressStatus()
        self.assertEqual(fresh_status["imported"], 0)
        self.assertIsNone(fresh_status["lastImportedMessageId"])
        self.assertEqual(fresh_status["lastRetainedImportMessageId"], history_id)
        self.assertEqual(fresh_status["retainedImportCount"], 1)
        rows, total = fresh.globals().RiftChatModernAPI.GetHistory("imports", "", 10, 0)
        self.assertEqual(rows[1]["importToken"], "B3A0705FD6AA")
        self.assertFalse(fresh.globals().RiftChatModernAPI.GetSaveCheckpointStatus()
                         ["onDiskVerified"])

    def test_import_without_engine_save_does_not_fake_checkpoint_proof(self):
        lua = self.client()
        history_id = self.import_to_client(lua, self.manual_commands())
        fixture = serialize_fixture(lua.globals().RiftChatModernSaved)
        with tempfile.TemporaryDirectory(prefix="rcm-unsaved-import-") as folder:
            path = Path(folder) / "RiftChatModern.lua"
            path.write_text(fixture, encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = audit_disk(["--file", str(path), "--require-import-id",
                                 str(history_id)])
            self.assertEqual(rc, 2)
            proof = json.loads(out.getvalue())
            self.assertTrue(proof["requiredImportIdPresent"])
            self.assertFalse(proof["diskReceiptVerified"])

    def test_replayed_import_token_after_relaunch_is_idempotent(self):
        # A user may paste the same host-generated /rcm import after a restart.
        # The persistent history must not silently duplicate that record.
        lua = self.client()
        commands = self.manual_commands()
        old_id = self.import_to_client(lua, commands)
        lua.execute('fire(Event.Addon.SavedVariables.Save.Begin, "RiftChatModern")')
        fixture = serialize_fixture(lua.globals().RiftChatModernSaved)
        fresh = self.client(fixture)
        for command in commands:
            fresh.execute("fire(slash.rcm, " + _lua_quote(command[5:]) + ")")
        imports, count = fresh.globals().RiftChatModernAPI.GetHistory(
            "imports", "", 10, 0)
        self.assertEqual(count, 1, "replaying an existing token created a second saved import")
        self.assertEqual(int(imports[1]["id"]), old_id)
        self.assertEqual(imports[1]["importToken"], "B3A0705FD6AA")
        stat = fresh.globals().RiftChatModernAPI.GetHostIngressStatus()
        self.assertGreaterEqual(stat["duplicates"], 1)
        self.assertEqual(stat["lastRetainedImportMessageId"], old_id)


if __name__ == "__main__":
    unittest.main()
