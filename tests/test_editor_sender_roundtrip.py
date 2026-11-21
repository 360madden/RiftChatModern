"""Cross-component RCM editor bridge contract, without Windows input.

Uses the actual Node encoder, the separately permissioned .NET sender in its
NO-INPUT validation mode, and a Lua 5.1 RIFT mock editor. This is not a
physical acceptance test or proof of native player-chat capture.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_addon import RIFT_MOCK, _lua_quote

try:
    from lupa.lua51 import LuaRuntime
except ImportError:
    LuaRuntime = None


ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / "addon" / "RiftChatModern"
ENCODER = ROOT / "tools" / "rcm-chat-import.cjs"
SENDER_PROJECT = ROOT / "tools" / "RcmEditorSender" / "RcmEditorSender.csproj"
SENDER_DLL = ROOT / "tools" / "RcmEditorSender" / "bin" / "Release" / "net10.0-windows" / "RcmEditorSender.dll"
NODE = shutil.which("node")
DOTNET = shutil.which("dotnet")
MODULES = ("Core.lua", "AddonMessages.lua", "NativeChatProbe.lua", "ConsoleCategories.lua",
           "ConsoleMirror.lua", "HostIngress.lua", "Main.lua")


@unittest.skipUnless(os.name == "nt" and NODE and DOTNET and LuaRuntime is not None,
                     "Requires Windows, Node, .NET 10 and Lua 5.1 via Lupa")
class EditorSenderRoundtripTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (os.name == "nt" and NODE and DOTNET and LuaRuntime is not None):
            return
        result = subprocess.run(
            [DOTNET, "build", str(SENDER_PROJECT), "--configuration", "Release", "--nologo"],
            cwd=ROOT, capture_output=True, text=True, timeout=60, check=False)
        if result.returncode:
            raise AssertionError(f"Editor sender build failed: {result.stdout}\n{result.stderr}")

    def encode(self, text: str, token: str, kind: str = "guild"):
        proc = subprocess.run(
            [NODE, str(ENCODER), "--kind", kind, "--sender", "BridgeProbe",
             "--channel", "Guild" if kind == "guild" else "Party",
             "--text", text, "--id", token, "--input-mode", "editor"],
            capture_output=True, text=True, encoding="utf-8",
            timeout=20, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        record = json.loads(proc.stdout)
        self.assertEqual(record["inputMode"], "editor")
        self.assertEqual(record["parts"], len(record["commands"]))
        self.assertFalse(record["automaticGameInput"])
        for line in record["commands"]:
            self.assertTrue(line.startswith(":import "))
            self.assertLessEqual(len(line), 160)
        return record

    def validate_in_sender(self, command: str, index: int, total: int):
        proc = subprocess.run(
            [DOTNET, str(SENDER_DLL), "--command", command],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
            timeout=20, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        reply = json.loads(proc.stdout)
        self.assertEqual(reply["status"], "validated_no_input")
        self.assertEqual(reply["sha256"],
                         hashlib.sha256(command.encode("utf-8")).hexdigest().upper())
        self.assertEqual((reply["part"], reply["total"]), (index, total))
        self.assertIs(reply["gameInputSent"], False)
        self.assertIs(reply["addonAcceptedVerified"], False)
        self.assertNotIn(command, proc.stdout)
        return reply

    def mock_game(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(RIFT_MOCK)
        for name in MODULES:
            source = (ADDON / name).read_text(encoding="utf-8")
            lua.execute("local f=assert(loadstring(" + _lua_quote(source) +
                        "));assert(f({identifier='RiftChatModern',version='0.2.23'}, {})==nil)")
        lua.execute('fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")')
        lua.execute('fire(Event.Addon.Load.End,"RiftChatModern")')
        lua.execute("assert(RiftChatModernAPI.Show())")
        lua.execute("assert(RiftChatModernAPI.FocusEditor())")
        return lua

    def submit_to_mock_editor(self, lua, command):
        lua.execute("local field=frames.RCMInput;field:SetText(" +
                    _lua_quote(command) + ");field.Event:KeyDown('enter')")

    def test_single_part_node_dotnet_lua_editor_no_input(self):
        message = "RCM E2E single part END_SIGNAL"
        record = self.encode(message, token="AAAABBBBCCCC")
        self.assertEqual(record["parts"], 1)
        self.validate_in_sender(record["commands"][0], 1, 1)
        lua = self.mock_game()
        self.submit_to_mock_editor(lua, record["commands"][0])
        lua.execute("""
local rows,n=RiftChatModernAPI.GetHistory("imports","END_SIGNAL",10,0)
assert(n==1 and rows[1].text=="RCM E2E single part END_SIGNAL")
assert(rows[1].kind=="import" and rows[1].origin=="host_manual")
assert(rows[1].source=="BridgeProbe" and rows[1].importToken=="AAAABBBBCCCC")
assert(RiftChatModernAPI.GetHostIngressStatus().lastImportedMessageId==rows[1].id)
assert(RiftChatModernAPI.GetStatus().commandHistoryCount==0)
assert(RiftChatModernAPI.GetSaveCheckpointStatus().onDiskVerified==false)
""")

    def test_multipart_utf8_node_dotnet_lua_editor_exactly_once(self):
        message = ("Unicode café✓ fragment boundary " * 11) + " FINAL_MARKER"
        record = self.encode(message, token="DDDDEEEEFFFF", kind="party")
        self.assertGreaterEqual(record["parts"], 3)
        lua = self.mock_game()
        for i, command in enumerate(record["commands"], 1):
            self.validate_in_sender(command, i, record["parts"])
            self.submit_to_mock_editor(lua, command)
        lua.execute("""
local rows,n=RiftChatModernAPI.GetHistory("imports","FINAL_MARKER",10,0)
assert(n==1 and rows[1].text==""" + _lua_quote(message) + """)
assert(rows[1].channelKind=="party" and rows[1].channelName=="Party")
assert(rows[1].importToken=="DDDDEEEEFFFF")
assert(RiftChatModernAPI.GetHostIngressStatus().imported==1)
assert(RiftChatModernAPI.GetStatus().commandHistoryCount==0)
assert(RiftChatModernAPI.GetSaveCheckpointStatus().onDiskVerified==false)
""")
        # Replaying all validated chunks is safe and must not publish twice.
        for command in record["commands"]:
            self.submit_to_mock_editor(lua, command)
        lua.execute("""
local rows,n=RiftChatModernAPI.GetHistory("imports","FINAL_MARKER",10,0)
assert(n==1 and RiftChatModernAPI.GetHostIngressStatus().imported==1)
""")

    def test_complete_node_json_batch_preflight_then_lua_editor(self):
        # A single bounded batch preflight is the missing link between the
        # existing Node encoder and RCM's real Lua editor importer. Only the
        # *mock* receives editor commands; no Windows input is requested.
        message = ("Batch preflight UTF8 café✓ " * 11) + " COMPLETE_20261121"
        record = self.encode(message, token="0A0B0C0D0E0F", kind="guild")
        self.assertGreaterEqual(record["parts"], 3)
        batch_json = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        proc = subprocess.run(
            [DOTNET, str(SENDER_DLL), "--stdin-batch"],
            input=batch_json, cwd=ROOT, capture_output=True,
            text=True, encoding="utf-8", timeout=20, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        reply = json.loads(proc.stdout)
        self.assertEqual(reply["status"], "batch_validated_no_input")
        self.assertEqual(reply["sha256"],
                         hashlib.sha256(batch_json.encode("utf-8")).hexdigest().upper())
        self.assertEqual((reply["parts"], reply["token"]),
                         (record["parts"], "0A0B0C0D0E0F"))
        self.assertIs(reply["gameInputSent"], False)
        self.assertIs(reply["addonAcceptedVerified"], False)
        self.assertNotIn(message, proc.stdout)
        lua = self.mock_game()
        for command in record["commands"]:
            self.submit_to_mock_editor(lua, command)
        lua.execute("""
local rows,n=RiftChatModernAPI.GetHistory("imports","COMPLETE_20261121",10,0)
assert(n==1 and rows[1].text==""" + _lua_quote(message) + """)
assert(rows[1].importToken=="0A0B0C0D0E0F")
assert(rows[1].kind=="import" and rows[1].origin=="host_manual")
assert(RiftChatModernAPI.GetStatus().commandHistoryCount==0)
assert(RiftChatModernAPI.GetSaveCheckpointStatus().onDiskVerified==false)
""")


    def test_synthetic_observer_gate_dotnet_batch_then_lua_editor(self):
        # Complete offline source-to-sink: simulated two-phase observer receipts
        # -> Node's exact-candidate gate -> .NET batch validator -> Lua mock.
        # No physical Log.txt, RIFT UI action, or game input is claimed.
        message = ("GATED_UTF8_é✓ " * 19) + " GATE_COMPLETE"
        selected = self.encode(message, token="1234ABCD5678", kind="guild")
        unrelated = self.encode("UNRELATED_CANDIDATE", token="AAAA0000BBBB",
                                kind="guild")
        events = [
            {"event": "started", "requireChatAfterMarker": True,
             "expectedChatTextRequired": True, "prepareImport": True,
             "inputMode": "editor", "transportVerified": False,
             "automaticGameInput": False},
            {"event": "matched", "nonce": "RCM_GATE_20261121"},
            {"event": "chat_phase_armed", "mode": "fresh_tail_after_marker"},
            {"event": "candidate_chat", "source": "RIFT_Log.txt",
             "chatTextMatched": False, "afterMarker": True, "truncated": False},
            unrelated,
            {"event": "candidate_chat", "source": "RIFT_Log.txt",
             "chatTextMatched": True, "afterMarker": True,
             "truncated": False, "verifiedLiveFormat": False},
            selected,
            {"event": "finished", "reason": "exact_chat_candidate_after_marker",
             "expectedChatTextRequired": True, "chatTextMatched": True,
             "probeMatched": True, "chatCandidatesAfterMarker": 2,
             "transportVerified": False, "physicalRiftOriginVerified": False}
        ]
        gate = ROOT / "tools" / "rcm-chat-batch-gate.cjs"
        payload = "\n".join(json.dumps(event) for event in events) + "\n"
        picked = subprocess.run(
            [NODE, str(gate)], input=payload, cwd=ROOT,
            capture_output=True, text=True, encoding="utf-8",
            timeout=20, check=False)
        self.assertEqual(picked.returncode, 0, picked.stderr)
        prepared = json.loads(picked.stdout)
        self.assertEqual(prepared["id"], "1234ABCD5678")
        self.assertEqual(prepared["commands"], selected["commands"])
        self.assertNotIn("UNRELATED_CANDIDATE", picked.stdout)
        plan = subprocess.run(
            [DOTNET, str(SENDER_DLL), "--stdin-batch"], input=picked.stdout,
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
            timeout=20, check=False)
        self.assertEqual(plan.returncode, 0, plan.stderr)
        receipt = json.loads(plan.stdout)
        self.assertEqual(receipt["status"], "batch_validated_no_input")
        self.assertEqual(receipt["token"], "1234ABCD5678")
        self.assertIs(receipt["gameInputSent"], False)
        self.assertIs(receipt["addonAcceptedVerified"], False)
        lua = self.mock_game()
        for command in prepared["commands"]:
            self.submit_to_mock_editor(lua, command)
        lua.execute("""
local rows,n=RiftChatModernAPI.GetHistory("imports","GATE_COMPLETE",10,0)
assert(n==1 and rows[1].text==""" + _lua_quote(message) + """)
assert(rows[1].importToken=="1234ABCD5678" and rows[1].origin=="host_manual")
assert(RiftChatModernAPI.GetHostIngressStatus().imported==1)
assert(RiftChatModernAPI.GetSaveCheckpointStatus().onDiskVerified==false)
""")

if __name__ == "__main__":
    unittest.main()
