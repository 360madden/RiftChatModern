"""Cross-release compatibility with a synthetic save produced by actual v0.2.23.

CI requires no Git history. Regenerate explicitly with --generate-fixture
from a full checkout. Never loads real character data or sends game input.
"""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path
import subprocess
import sys
import unittest

from test_addon import RIFT_MOCK, _lua_quote
from test_import_roundtrip import serialize_fixture
from rcm_disk_receipt import inspect_saved_data

try:
    from lupa.lua51 import LuaRuntime, lua_type
except ImportError:
    LuaRuntime = None
    lua_type = None

ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / "addon" / "RiftChatModern"
FIXTURE = Path(__file__).with_name("rcm-v023-compat.json")
LEGACY = "5a95d0e56e7652dca7ef2e2dc7a481dea5a7673b"
MODULES = ("Core.lua", "AddonMessages.lua", "NativeChatProbe.lua",
           "ConsoleCategories.lua", "ConsoleMirror.lua", "HostIngress.lua", "Main.lua")
TOKENS = ("AABBCCDDEEFF", "112233445566")
RECORDS = (("S", "FixtureSpeaker", "Say", "fixture Say message"),
           ("C", "FixtureSpeaker", "Level 1-29", "fixture public message"))


def as_data(value):
    """Convert bounded synthetic save tables to JSON-compatible data."""
    if lua_type(value) != "table":
        return value
    items = list(value.items())
    if items and all(type(key) is int for key, _ in items):
        if sorted(key for key, _ in items) != list(range(1, len(items) + 1)):
            raise ValueError("non_contiguous_fixture_array")
        return [as_data(value[i]) for i in range(1, len(items) + 1)]
    if any(type(key) is not str for key, _ in items):
        raise ValueError("non_string_fixture_key")
    return {key: as_data(item) for key, item in items}


def wire_command(token, fields):
    wire = base64.urlsafe_b64encode("\0".join(fields).encode("utf-8")).decode("ascii")
    return f"import {token} 1/1 {wire.rstrip('=')}"


def client(sources, version, saved=None):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(RIFT_MOCK)
    if saved is not None:
        lua.globals().RiftChatModernSaved = lua.table_from(saved, recursive=True)
    for name in MODULES:
        lua.execute("assert(loadstring(" + _lua_quote(sources[name]) +
                    "))({identifier='RiftChatModern',version=" +
                    _lua_quote(version) + "}, {})")
    lua.execute('fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")')
    lua.execute('fire(Event.Addon.Load.End,"RiftChatModern")')
    return lua


def generate_fixture():
    """Run exact historical sources, never installed addon files."""
    sources = {name: subprocess.check_output(
        ["git", "show", f"{LEGACY}:addon/RiftChatModern/{name}"],
        cwd=ROOT, timeout=15).decode("utf-8") for name in MODULES}
    lua = client(sources, "0.2.23")
    lua.execute(r'''
assert(RiftChatModernAPI.Publish("addons","compatibility fixture message","FixtureAddon"))
assert(RiftChatModernAPI.Show())
assert(RiftChatModernAPI.SetWindowSize(940,680))
fire(slash.rcm,"tab chat")
fire(slash.rcm,"find fixture")
''')
    for token, fields in zip(TOKENS, RECORDS):
        lua.execute("fire(slash.rcm," + _lua_quote(wire_command(token, fields)) + ")")
    lua.execute(r'''
now=1701
fire(Event.Addon.SavedVariables.Save.Begin,"RiftChatModern")
fire(Event.Addon.SavedVariables.Save.End,"RiftChatModern")
''')
    api = lua.globals().RiftChatModernAPI
    saved = as_data(lua.globals().RiftChatModernSaved)
    assert len(saved["history"]) == 4 and saved["saveCheckpoint"]["lastImportId"] == 4
    query_rows, query_count = api.GetHistory("chat", "fixture", 20, 0)
    assert query_count == 2
    return {"fixtureVersion": 1, "syntheticOnly": True, "release": "0.2.23",
            "sourceCommit": LEGACY,
            "apiFunctions": sorted(k for k, v in api.items() if lua_type(v) == "function"),
            "interfaceVersion": api.interfaceVersion, "saved": saved,
            "legacyChatQuery": as_data(query_rows)}


@unittest.skipUnless(LuaRuntime is not None, "Lua 5.1 via Lupa required")
class ReleaseCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(self.fixture["sourceCommit"], LEGACY)
        self.assertEqual(self.fixture["release"], "0.2.23")
        self.assertIs(self.fixture["syntheticOnly"], True)
        self.assertEqual(self.fixture["fixtureVersion"], 1)
        self.sources = {name: (ADDON / name).read_text(encoding="utf-8")
                        for name in MODULES}

    def upgraded(self, data=None):
        # Derive the candidate release from the source manifest rather than
        # silently testing an old version label after future version bumps.
        toc = (ADDON / "RiftAddon.toc").read_text(encoding="utf-8")
        versions = re.findall(r'^Version\s*=\s*"([^"]+)"\s*$', toc, re.M)
        self.assertEqual(len(versions), 1)
        return client(self.sources, versions[0], self.fixture["saved"] if data is None else data)

    def test_historical_save_upgrade_preserves_rows_tokens_and_layout(self):
        lua = self.upgraded()
        api = lua.globals().RiftChatModernAPI
        saved = as_data(lua.globals().RiftChatModernSaved)
        original = self.fixture["saved"]
        self.assertTrue(api.GetStatus()["ready"])
        self.assertEqual(saved["schemaVersion"], 2)
        self.assertEqual(saved["history"][:len(original["history"])], original["history"])
        self.assertEqual(len(saved["history"]), len(original["history"]) + 1)
        self.assertEqual(saved["nextId"], original["nextId"] + 1)
        for key in ("ui", "filter", "search", "saveCheckpoint"):
            self.assertEqual(saved[key], original[key], key)
        self.assertIsNone(lua.globals().RiftChatModernSaved["channelColors"])
        self.assertIsNone(lua.globals().RiftChatModernSaved["hiddenChannels"])
        self.assertFalse(api.GetSaveCheckpointStatus()["onDiskVerified"])
        self.assertTrue(api.Show())
        self.assertEqual(api.GetStatus()["windowWidth"], 940)
        self.assertEqual(api.GetStatus()["windowHeight"], 680)
        rows, count = api.GetHistory("chat", "fixture", 20, 0)
        self.assertEqual(count, 2)
        self.assertEqual(as_data(rows), self.fixture["legacyChatQuery"])

    def test_existing_api_v2_surface_and_valid_calls_remain_compatible(self):
        lua = self.upgraded()
        api = lua.globals().RiftChatModernAPI
        self.assertEqual(api.interfaceVersion, self.fixture["interfaceVersion"])
        for name in self.fixture["apiFunctions"]:
            with self.subTest(endpoint=name):
                self.assertEqual(lua_type(api[name]), "function")
        lua.execute(r'''
local api=RiftChatModernAPI
assert(api.Show())
assert(api.GetMessage(3).importToken=="AABBCCDDEEFF")
assert(api.OpenMessage(3))
assert(api.GetSelectedMessage().id==3)
assert(api.CopySelectedMessage())
assert(copied:find("fixture Say message",1,true))
api.CloseMessage()
-- The RIFT mock does not implement exclusive key focus; mirror the
-- documented getter-verified transition used by test_ui_geometry.
assert(api.FocusEditor())
frames.RCMInput:SetKeyFocus(false)
assert(api.FocusSearch())
assert(api.GetFocusState()=="search")
frames.RCMSearchField:SetKeyFocus(false)
assert(api.FocusEditor())
assert(api.GetFocusState()=="focused")
assert(api.RegisterCommand("legacyfixture",function(args) return "legacy "..args end))
local seen=0
assert(api.Subscribe("legacyfixture",function(row)
    seen=seen+1
    row.text="do not mutate retained history"
end))
assert(api.Submit(":legacyfixture ok"))
assert(seen==1)
assert(api.Unsubscribe("legacyfixture"))
assert(api.GetHistory("dev","legacy ok",10,0)[1].text=="legacy ok")
assert(api.Submit(":filter chat"))
assert(api.Submit(":find fixture"))
assert(api.GetStatus().filter=="chat" and api.GetStatus().search=="fixture")
assert(api.Copy())
assert(copied:find("fixture Say message",1,true))
assert(copied:find("fixture public message",1,true))
assert(api.Hide())
assert(not api.GetStatus().windowVisible)
''')

    def test_historical_import_commands_cannot_replay_after_upgrade(self):
        lua = self.upgraded()
        api = lua.globals().RiftChatModernAPI
        for token, fields in zip(TOKENS, RECORDS):
            command = wire_command(token, fields)
            lua.execute("fire(slash.rcm," + _lua_quote(command) + ")")
            api.Submit(":" + command)
        state = api.GetHostIngressStatus()
        self.assertEqual(state["imported"], 0)
        self.assertGreaterEqual(state["duplicates"], 4)
        rows, count = api.GetHistory("imports", "", 20, 0)
        self.assertEqual(count, 2)
        self.assertEqual(as_data(rows), self.fixture["legacyChatQuery"])

    def test_new_palette_and_save_reload_preserve_legacy_import_identity(self):
        lua = self.upgraded()
        api = lua.globals().RiftChatModernAPI
        self.assertTrue(api.SetChannelColor("host_say", "FFFFFF"))
        self.assertTrue(api.SetChannelVisible("host_public", False))
        lua.execute('now=1702; fire(Event.Addon.SavedVariables.Save.Begin,"RiftChatModern")')
        saved = lua.globals().RiftChatModernSaved
        snapshot = as_data(saved)
        self.assertEqual(snapshot["saveCheckpoint"]["sequence"], 2)
        # Reuse the existing synthetic serializer and independent verifier.
        report = inspect_saved_data(serialize_fixture(saved),
                                    required_import_id=4, required_import_token=TOKENS[1])
        self.assertTrue(report["requiredImportIdentityMatched"])
        self.assertTrue(report["checkpointMetadataConsistent"])
        self.assertFalse(api.GetSaveCheckpointStatus()["onDiskVerified"])
        fresh = self.upgraded(snapshot)
        api2 = fresh.globals().RiftChatModernAPI
        self.assertEqual(api2.GetChannelColors()["host_say"], "FFFFFF")
        self.assertFalse(api2.GetChannelVisibility()["host_public"])
        self.assertEqual(api2.GetMessage(3)["importToken"], TOKENS[0])
        self.assertEqual(api2.GetMessage(4)["importToken"], TOKENS[1])
        self.assertEqual(as_data(fresh.globals().RiftChatModernSaved)["history"][:4],
                         self.fixture["saved"]["history"])


if __name__ == "__main__":
    if sys.argv[1:] == ["--generate-fixture"]:
        print(json.dumps(generate_fixture(), ensure_ascii=True, sort_keys=True, indent=2))
    else:
        unittest.main()
