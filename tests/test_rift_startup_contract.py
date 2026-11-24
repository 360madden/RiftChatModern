"""RIFT RunOnStartup module execution regression (live-client error Nov 20).

A pure helper loaded with RunOnStartup is an addon script, not a require() module.
Do not return a module table from a startup file. Known-working RiftReader2
uses the supplied private addon table; RiftChatModern exports named tables.
"""
from pathlib import Path
import re
import unittest

try:
    from lupa.lua51 import LuaRuntime
except ImportError:
    LuaRuntime = None

HERE = Path(__file__).resolve().parents[1] / "addon" / "RiftChatModern"
NAMES = ("Core.lua", "AddonMessages.lua", "NativeChatProbe.lua", "ConsoleCategories.lua", "ConsoleMirror.lua", "HostIngress.lua", "Main.lua")


@unittest.skipUnless(LuaRuntime is not None, "Lua 5.1 unavailable")
class RiftStartupContractTests(unittest.TestCase):
    def test_all_manifest_startup_files_return_no_values(self):
        from test_addon import RIFT_MOCK, _lua_quote
        toc = (HERE / "RiftAddon.toc").read_text(encoding="utf-8")
        manifest_files = re.search(r"RunOnStartup\s*=\s*\{([^}]*)\}", toc)
        self.assertIsNotNone(manifest_files)
        self.assertEqual(tuple(re.findall(r'"([^"]+)"', manifest_files.group(1))), NAMES)
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(RIFT_MOCK)
        for name in NAMES:
            with self.subTest(startup=name):
                source = (HERE / name).read_text(encoding="utf-8")
                # Execute with RIFT's two addon arguments and verify the chunk
                # returned NO exported module value to its host.
                value = lua.execute(
                    "local chunk=assert(loadstring(" + _lua_quote(source)
                    + "));return chunk({identifier='RiftChatModern',"
                      "version='0.2.25'}, {})")
                self.assertIsNone(value, f"{name} must not return from RIFT RunOnStartup")
        lua.execute('''
assert(type(RiftChatModernCore)=="table")
assert(type(RiftChatModernAddonMessages)=="table")
assert(type(RiftChatModernNativeProbe)=="table")
assert(type(RiftChatModernConsoleCategories)=="table")
assert(type(RiftChatModernConsoleMirror)=="table")
assert(type(RiftChatModernHostIngress)=="table")
assert(type(RiftChatModernAPI)=="table")
assert(RiftChatModernAPI.GetHostIngressStatus().ready==false)
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
assert(RiftChatModernAPI.GetStatus().version=="0.2.25")
assert(RiftChatModernAPI.GetStatus().ready)
''')

    def test_four_helper_files_end_in_assignment_not_return(self):
        for name in NAMES[:5]:
            with self.subTest(startup=name):
                source = (HERE / name).read_text(encoding="utf-8")
                self.assertNotRegex(source, r"(?m)^\s*return\s+(Core|Bridge|Probe|Registry|Mirror)\s*$")
                self.assertRegex(source, r"_G\.RiftChatModern[A-Za-z]+\s*=\s*(Core|Bridge|Probe|Registry|Mirror)")

if __name__ == "__main__":
    unittest.main()
