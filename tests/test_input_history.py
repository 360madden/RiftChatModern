"""RiftChatModern v0.2.17 editor recall, draft and search-sync regressions.

These are offline Lua 5.1 mock tests, not physical RIFT keyboard acceptance.
"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_addon import RIFT_MOCK, _lua_quote

try:
    from lupa.lua51 import LuaRuntime
except ImportError:
    LuaRuntime = None

ADDON = Path(__file__).resolve().parents[1] / "addon" / "RiftChatModern"
MODULES = ("Core.lua", "AddonMessages.lua", "NativeChatProbe.lua",
           "ConsoleMirror.lua", "HostIngress.lua", "Main.lua")


@unittest.skipUnless(LuaRuntime is not None, "Requires Lua 5.1 via Lupa")
class InputHistoryTests(unittest.TestCase):
    def run_lua(self, scenario):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(RIFT_MOCK)
        for filename in MODULES:
            source = (ADDON / filename).read_text(encoding="utf-8")
            lua.execute("assert(loadstring(" + _lua_quote(source) +
                        "))({identifier='RiftChatModern',version='0.2.17'}, {})")
        lua.execute(scenario)

    def test_up_down_cycles_and_restores_unsent_draft(self):
        self.run_lua(r"""
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
assert(api.FocusEditor())
local input=frames.RCMInput
input:SetText(":echo first")
input.Event:KeyDown("enter")
input:SetText(":echo second")
input.Event:KeyDown("\r")
assert(api.GetStatus().commandHistoryCount==2)
assert(api.GetStatus().commandHistoryPersisted==false)
input:SetText("unsent social draft")
input.Event:KeyDown("up")
assert(input:GetText()==":echo second")
input.Event:KeyDown("UP")
assert(input:GetText()==":echo first")
input.Event:KeyDown("arrowup")
assert(input:GetText()==":echo first")
input.Event:KeyDown("Down")
assert(input:GetText()==":echo second")
input.Event:KeyDown("arrowdown")
assert(input:GetText()=="unsent social draft")
input.Event:KeyDown("down")
assert(input:GetText()=="unsent social draft")
assert(RiftChatModernSaved.commandHistory==nil)
""")

    def test_user_edit_interrupts_recall_and_preserves_new_draft(self):
        self.run_lua(r"""
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
assert(RiftChatModernAPI.Show())
local input=frames.RCMInput
input:SetText(":echo saved")
input.Event:KeyDown("return")
input:SetText("working draft")
input.Event:KeyDown("up")
assert(input:GetText()==":echo saved")
-- Simulate the native textfield Change event after a manual edit or paste.
input:SetText(":echo modified")
triggerFrame(input,Event.UI.Textfield.Change)
input.Event:KeyDown("up")
assert(input:GetText()==":echo saved")
input.Event:KeyDown("down")
assert(input:GetText()==":echo modified")
input.Event:KeyDown(33) -- malformed key payload cannot run a command
assert(input:GetText()==":echo modified")
""")

    def test_failed_normal_chat_draft_not_recorded_or_discarded(self):
        self.run_lua(r"""
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
assert(RiftChatModernAPI.Show())
local input=frames.RCMInput
input:SetText("hello guild")
input.Event:KeyDown("enter")
assert(input:GetText()=="hello guild")
assert(RiftChatModernAPI.GetStatus().commandHistoryCount==0)
input:SetText(":unknown command")
input.Event:KeyDown("return")
assert(input:GetText()==":unknown command")
assert(RiftChatModernAPI.GetStatus().commandHistoryCount==0)
input.Event:KeyDown("up")
assert(input:GetText()==":unknown command")
""")

    def test_bounded_deduplicated_transient_history(self):
        self.run_lua(r"""
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
assert(RiftChatModernAPI.Show())
local input=frames.RCMInput
for i=1,40 do
    input:SetText(":echo command_"..i)
    input.Event:KeyDown("enter")
end
assert(RiftChatModernAPI.GetStatus().commandHistoryCount==32)
for i=1,40 do input.Event:KeyDown("up") end
assert(input:GetText()==":echo command_9")
input.Event:KeyDown("enter")
input:SetText(":echo command_9")
input.Event:KeyDown("enter")
assert(RiftChatModernAPI.GetStatus().commandHistoryCount==32)
assert(RiftChatModernSaved.commandHistory==nil)
""")

    def test_local_and_native_find_sync_visible_search_field(self):
        self.run_lua(r"""
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
assert(api.Submit(":find Atank"))
assert(api.GetStatus().search=="Atank")
assert(frames.RCMSearchField:GetText()=="Atank")
fire(slash.rcm,"find RRE")
assert(api.GetStatus().search=="RRE")
assert(frames.RCMSearchField:GetText()=="RRE")
local input=frames.RCMSearchField
input:SetText("RR2")
triggerFrame(input,Event.UI.Textfield.Change)
assert(api.GetStatus().search=="RR2")
assert(api.Submit(":find"))
assert(api.GetStatus().search=="")
assert(input:GetText()=="")
""")


if __name__ == "__main__":
    unittest.main()
