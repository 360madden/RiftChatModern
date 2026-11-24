"""RCM 0.2.24 channel palette: model and in-game API mock regression tests.

No game input or deployment is performed. SavedVariables are simulated.
"""
from pathlib import Path
import unittest

from test_addon import RIFT_MOCK, _lua_quote

try:
    from lupa.lua51 import LuaRuntime
except ImportError:
    LuaRuntime = None

ADDON = Path(__file__).resolve().parents[1] / "addon" / "RiftChatModern"


@unittest.skipUnless(LuaRuntime is not None, "Lua 5.1 unavailable")
class ChannelPaletteTests(unittest.TestCase):
    def run_lua(self, scenario, ui=False):
        lua = LuaRuntime(unpack_returned_tuples=True)
        if ui:
            lua.execute(RIFT_MOCK)
            names = ("Core.lua", "AddonMessages.lua", "NativeChatProbe.lua",
                     "ConsoleCategories.lua", "ConsoleMirror.lua",
                     "HostIngress.lua", "Main.lua")
        else:
            names = ("Core.lua",)
        for name in names:
            source = (ADDON / name).read_text(encoding="utf-8")
            lua.execute("assert(loadstring(" + _lua_quote(source) +
                        "))({identifier='RiftChatModern',version='0.2.24'}, {})")
        lua.execute(scenario)

    def test_old_save_has_defaults_without_dirtying_or_mutating(self):
        self.run_lua(r'''
local saved={schemaVersion=2,nextId=1,history={}}
local m=assert(RiftChatModernCore.new(saved))
assert(saved.channelColors==nil and m:status().revision==0)
local p=m:getChannelColors()
assert(p.host_say=="1FD1D4" and p.host_public=="99C7FF")
p.host_say="000000"
assert(m:getChannelColor("host_say")=="1FD1D4")
assert(m:resetChannelColor("all"))
assert(m:status().revision==0)
''')

    def test_sparse_persistence_normalization_and_reset(self):
        self.run_lua(r'''
local saved={schemaVersion=2,nextId=1,history={}}
local m=assert(RiftChatModernCore.new(saved))
assert(m:setChannelColor("host_public","#f0e080"))
assert(saved.channelColors.host_public=="F0E080")
assert(m:status().revision==1)
assert(m:setChannelColor("host_public","F0E080"))
assert(m:status().revision==1)
local reload=assert(RiftChatModernCore.new(saved))
assert(reload:getChannelColor("host_public")=="F0E080")
assert(reload:status().revision==0)
assert(reload:resetChannelColor("host_public"))
assert(saved.channelColors==nil and reload:status().revision==1)
assert(reload:resetChannelColor("host_public"))
assert(reload:status().revision==1)
''')

    def test_invalid_and_dark_colors_do_not_modify_state(self):
        self.run_lua(r'''
local s={schemaVersion=2,nextId=1,history={}}
local m=assert(RiftChatModernCore.new(s))
for _,value in ipairs({"000000","121212","GGGGGG","#FFF","AABBCCDD"," FFFFFF",5,{}}) do
    assert(not m:setChannelColor("npc",value))
end
assert(not m:setChannelColor("unknown","FFFFFF"))
assert(not m:setChannelColor(nil,"FFFFFF"))
assert(not m:setChannelColor("npc",nil))
assert(not m:resetChannelColor("unknown"))
assert(s.channelColors==nil and m:status().revision==0)
''')

    def test_corrupt_palette_repairs_only_presentation(self):
        self.run_lua(r'''
local row={id=7,at=1,kind="import",origin="host_manual",channelKind="public",
 channelName="Level 1-29",source="Test",text="hello",importToken="AABBCCDDEEFF"}
local s={schemaVersion=2,nextId=8,history={row},
 channelColors={npc="ffffff",dev="000000",extra="FFFFFF",host_say="1FD1D4"}}
local m=assert(RiftChatModernCore.new(s))
assert(s.channelColors.npc=="FFFFFF" and s.channelColors.dev==nil)
assert(s.channelColors.extra==nil and s.channelColors.host_say==nil)
assert(s.history[1]==row and m:findImportToken("AABBCCDDEEFF")==7)
assert(m:status().revision==1)
assert(m:checkpointStatus().pendingSessionChanges)
''')

    def test_all_defaults_are_valid_and_independent(self):
        self.run_lua(r'''
local m=assert(RiftChatModernCore.new({schemaVersion=2,nextId=1,history={}}))
local n=0
for key,value in pairs(m:getChannelColors()) do
    assert(m:setChannelColor(key,value),key)
    n=n+1
end
assert(n==15 and m:status().revision==0)
''')

    def test_provenance_controls_palette_family(self):
        self.run_lua(r'''
local m=assert(RiftChatModernCore.new({schemaVersion=2,nextId=1,history={}}))
local _,k=m:getRowColor({kind="import",origin="host_manual",channelKind="general",channelName="Say"})
assert(k=="host_say")
_,k=m:getRowColor({kind="import",origin="host_manual",channelKind="public",channelName="Level 1-29"})
assert(k=="host_public")
_,k=m:getRowColor({kind="import",origin="external_api",channelKind="public"})
assert(k=="import")
_,k=m:getRowColor({kind="import",origin="legacy_unknown",channelKind="guild"})
assert(k=="import")
_,k=m:getRowColor({kind="import",origin="host_manual",channelKind="general",channelName="Unrecognized"})
assert(k=="host_general")
''')

    def test_commands_do_not_consume_history_or_mark_noops_dirty(self):
        self.run_lua(r'''
local m=assert(RiftChatModernCore.new({schemaVersion=2,nextId=1,history={}}))
local ok,out=m:execute(":color list",1700)
assert(ok and out:find("host_public=",1,true))
assert(m:execute(":color show host_say",1700))
assert(m:execute(":color set host_say #FFFFFF",1700))
assert(m:status().revision==1 and m:status().historyCount==0)
assert(m:execute(":color set host_say FFFFFF",1700))
assert(m:status().revision==1)
assert(not m:execute(":color set host_say 000000",1700))
assert(not m:registerCommand("color",function() end))
assert(m:execute(":color reset all",1700))
assert(m:status().revision==2 and m:status().historyCount==0)
''')

    def test_ui_updates_existing_label_marker_and_keeps_host_identity(self):
        self.run_lua(r'''
RiftChatModernSaved={schemaVersion=2,nextId=2,history={{
 id=1,at=1700,kind="import",origin="host_manual",channelKind="public",
 channelName="Level 1-29",source="Test",text="fixture"}}}
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
assert(frames.RCMLineChannel1.text=="[HOST/PUBLIC]")
local before=api.GetStatus().historyCount
assert(api.SetChannelColor("host_public","#FFFFFF"))
assert(frames.RCMLineChannel1.fg[1]==1 and frames.RCMLineChannel1.fg[2]==1)
assert(frames.RCMLineMarker1.bg[1]==1)
assert(frames.RCMLineChannel1.text=="[HOST/PUBLIC]")
assert(api.GetHistory("imports","",1,0)[1].nativePlayerChatVerified==false)
assert(api.Submit(":color reset host_public"))
assert(frames.RCMLineChannel1.fg[1]<1)
assert(api.GetStatus().historyCount==before)
assert(api.GetStatus().version=="0.2.24")
''', ui=True)

    def test_not_ready_and_saved_palette_ui_render(self):
        self.run_lua(r'''
local api=RiftChatModernAPI
assert(not api.GetChannelColors())
assert(not api.SetChannelColor("npc","FFFFFF"))
assert(not api.ResetChannelColor("all"))
RiftChatModernSaved={schemaVersion=2,nextId=2,channelColors={npc="FFFFFF"},
 history={{id=1,at=1700,kind="npc",origin="game_event",source="NPC",text="test"}}}
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
assert(api.Show())
assert(frames.RCMLineChannel1.fg[1]==1 and frames.RCMLineChannel1.fg[2]==1)
assert(api.GetChannelColors().npc=="FFFFFF")
''', ui=True)


if __name__ == "__main__":
    unittest.main()
