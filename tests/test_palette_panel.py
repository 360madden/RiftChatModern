"""RCM v0.2.25 graphical palette and view-only visibility.

Actual Lua 5.1 with mocked RIFT UI/events. No game input or physical save proof.
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
class PalettePanelTests(unittest.TestCase):
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
            code = (ADDON / name).read_text(encoding="utf-8")
            lua.execute("assert(loadstring(" + _lua_quote(code) +
                        "))({identifier='RiftChatModern',version='0.2.25'}, {})")
        lua.execute(scenario)

    def test_visibility_defaults_noops_and_persistence(self):
        self.run_lua(r'''
local saved={schemaVersion=2,nextId=1,history={}}
local m=assert(RiftChatModernCore.new(saved))
assert(m:getChannelVisibility().host_public==true)
assert(saved.hiddenChannels==nil and m:status().revision==0)
assert(m:setChannelVisible("host_public",true))
assert(m:status().revision==0)
assert(m:setChannelVisible("host_public",false))
assert(saved.hiddenChannels.host_public==true and m:status().revision==1)
assert(m:setChannelVisible("host_public",false))
assert(m:status().revision==1)
local v=m:getChannelVisibility();v.host_public=true
assert(m:getChannelVisibility().host_public==false)
local reload=assert(RiftChatModernCore.new(saved))
assert(reload:getChannelVisibility().host_public==false)
assert(reload:resetChannelVisibility())
assert(saved.hiddenChannels==nil and reload:status().revision==1)
assert(reload:resetChannelVisibility())
assert(reload:status().revision==1)
''')

    def test_visibility_repair_and_invalid_input(self):
        self.run_lua(r'''
local saved={schemaVersion=2,nextId=2,history={{id=1,at=1,kind="import",
 origin="host_manual",channelKind="public",channelName="Level 1-29",
 source="Test",text="fixture",importToken="AABBCCDDEEFF"}},
 hiddenChannels={host_public=true,host_say=false,extra=true,dev=1}}
local m=assert(RiftChatModernCore.new(saved))
assert(saved.hiddenChannels.host_public==true)
assert(saved.hiddenChannels.host_say==nil and saved.hiddenChannels.extra==nil)
assert(saved.hiddenChannels.dev==nil and m:status().revision==1)
assert(m:findImportToken("AABBCCDDEEFF")==1)
assert(not m:setChannelVisible("host_public","false"))
assert(not m:setChannelVisible("unknown",false))
assert(m:status().revision==1)
''')

    def test_hidden_rows_are_view_only_and_search_and_export_agree(self):
        self.run_lua(r'''
local m=assert(RiftChatModernCore.new({schemaVersion=2,nextId=1,history={}}))
assert(m:publish("import","fixture public","Test",1,
 {origin="host_manual",channelKind="public",channelName="Level 1-29",
  importToken="AABBCCDDEEFF"}))
assert(m:publish("dev","fixture diagnostic","Test",2,{origin="local_addon"}))
assert(m:setChannelVisible("host_public",false))
local a,n=m:getHistory("all","fixture",240,0)
assert(n==2 and #a==2)
local b,n=m:getHistory("all","fixture",240,0,true)
assert(n==1 and b[1].kind=="dev")
local c,n=m:getHistory("imports","",240,0,true)
assert(n==0 and #c==0)
assert(m:getMessage(1).text=="fixture public")
assert(m:findImportToken("AABBCCDDEEFF")==1)
assert(m:exportText("all","",48000,true):find("fixture public",1,true)==nil)
assert(m:exportText("all","",48000):find("fixture public",1,true))
assert(m:execute(":color visible host_public on",3))
assert(m:getChannelVisibility().host_public)
assert(m:execute(":color showall",3))
assert(m:status().historyCount==2)
''')

    def test_preview_is_nonmutating_and_same_validation_as_apply(self):
        self.run_lua(r'''
local m=assert(RiftChatModernCore.new({schemaVersion=2,nextId=1,history={}}))
local rgb,hex=m:previewChannelColor("#f0e080")
assert(hex=="F0E080" and math.abs(rgb[1]-240/255)<0.00001)
assert(not m:previewChannelColor("000000"))
assert(m.saved.channelColors==nil and m:status().revision==0)
local keys=m:getChannelKeys();keys[1]="tamper"
assert(m:getChannelKeys()[1]=="system")
''')

    def test_open_close_and_focus_preserve_chat_draft(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show() and api.FocusEditor())
frames.RCMInput:SetText(":echo unsent")
triggerFrame(frames.RCMPaletteOpen,Event.UI.Input.Mouse.Left.Click)
assert(frames.RCMPalettePanel.visible and not frames.RCMLine1.visible)
assert(api.GetStatus().displayMode=="palette")
assert(not api.GetStatus().editorFocused and api.GetFocusState()=="palette_open")
assert(frames.RCMInput.text==":echo unsent")
triggerFrame(frames.RCMPaletteHex,Event.UI.Input.Mouse.Left.Click)
assert(api.GetFocusState()=="palette" and api.GetStatus().paletteInputFocused)
assert(not api.GetStatus().editorFocused)
frames.RCMInput.Event:KeyDown("Enter")
assert(frames.RCMInput.text==":echo unsent")
triggerFrame(frames.RCMPaletteClose,Event.UI.Input.Mouse.Left.Click)
assert(not frames.RCMPalettePanel.visible and frames.RCMLine1.visible)
assert(frames.RCMPaletteHex.focus==false and frames.RCMInput.text==":echo unsent")
assert(api.FocusEditor() and api.GetFocusState()=="focused")
''', ui=True)

    def test_click_apply_reset_and_invalid_preview(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
assert(api.Submit(":color panel"))
local click=Event.UI.Input.Mouse.Left.Click
local change=Event.UI.Textfield.Change
triggerFrame(frames.RCMPageDown,click)
assert(frames.RCMPaletteTitle.text:find("2/3",1,true))
triggerFrame(frames.RCMPaletteCategory6,click)
assert(frames.RCMPaletteSelection.text=="HOST PUBLIC")
local previous=api.GetChannelColors().host_public
local revision=api.GetStatus().revision
frames.RCMPaletteHex:SetText("#FFFFFF")
triggerFrame(frames.RCMPaletteHex,change)
assert(frames.RCMPalettePreviewSwatch.bg[1]==1)
assert(api.GetStatus().revision==revision and api.GetChannelColors().host_public==previous)
triggerFrame(frames.RCMPaletteApply,click)
assert(api.GetChannelColors().host_public=="FFFFFF")
assert(api.GetStatus().revision==revision+1)
frames.RCMPaletteHex:SetText("#000000")
triggerFrame(frames.RCMPaletteHex,change)
assert(frames.RCMPalettePreviewNote.text:find("Too dark",1,true))
triggerFrame(frames.RCMPaletteApply,click)
assert(api.GetChannelColors().host_public=="FFFFFF")
assert(api.GetStatus().revision==revision+1)
triggerFrame(frames.RCMPaletteReset,click)
assert(api.GetChannelColors().host_public==previous)
triggerFrame(frames.RCMPageDown,click)
assert(frames.RCMPaletteTitle.text:find("3/3",1,true))
assert(not frames.RCMPaletteCategory4.visible)
''', ui=True)

    def test_visibility_toggle_keeps_history_and_copy_matches_view(self):
        self.run_lua(r'''
RiftChatModernSaved={schemaVersion=2,nextId=2,history={{id=1,at=1700,
 kind="import",origin="host_manual",channelKind="public",
 channelName="Level 1-29",source="Test",text="fixture public",importToken="AABBCCDDEEFF"}}}
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
local click=Event.UI.Input.Mouse.Left.Click
assert(frames.RCMLineChannel1.text=="[HOST/PUBLIC]")
triggerFrame(frames.RCMPaletteOpen,click)
triggerFrame(frames.RCMPageDown,click)
triggerFrame(frames.RCMPaletteCategory6,click)
triggerFrame(frames.RCMPaletteVisibility,click)
assert(not api.GetChannelVisibility().host_public)
assert(frames.RCMPaletteVisibilityLabel.text=="SHOW ROWS")
assert(RiftChatModernSaved.hiddenChannels.host_public==true)
triggerFrame(frames.RCMClear,click)
assert(api.GetMessage(1).text=="fixture public")
triggerFrame(frames.RCMPaletteClose,click)
assert(frames.RCMLineChannel1.text~="[HOST/PUBLIC]")
assert(api.GetHistory("imports","",1,0)[1].importToken=="AABBCCDDEEFF")
assert(api.Copy() and not copied:find("fixture public",1,true))
triggerFrame(frames.RCMPaletteOpen,click)
triggerFrame(frames.RCMPaletteShowAll,click)
triggerFrame(frames.RCMPaletteClose,click)
assert(frames.RCMLineChannel1.text=="[HOST/PUBLIC]")
assert(api.Copy() and copied:find("fixture public",1,true))
''', ui=True)

    def test_modal_exclusivity_resize_and_hide(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
local click=Event.UI.Input.Mouse.Left.Click
triggerFrame(frames.RCMLine1,click)
assert(frames.RCMDetailOverlay.visible)
triggerFrame(frames.RCMPaletteOpen,click)
assert(not frames.RCMDetailOverlay.visible and frames.RCMPalettePanel.visible)
triggerFrame(frames.RCMPaletteHex,click)
assert(api.GetFocusState()=="palette")
triggerFrame(frames.RCMTabnative,click)
assert(not frames.RCMPalettePanel.visible and not frames.RCMPaletteHex.focus)
assert(frames.RCMNativeCatalog.visible and not frames.RCMLine1.visible)
triggerFrame(frames.RCMPaletteOpen,click)
assert(not frames.RCMNativeCatalog.visible)
for _,dims in ipairs({{680,480},{760,618},{1100,800}}) do
    assert(api.SetWindowSize(dims[1],dims[2]))
    local parent=frames.RCMPalettePanel
    assert(parent.visible)
    for name,f in pairs(frames) do
        if name:find("^RCMPalette") and f.anchorParent==parent then
            assert(f.anchorX>=0 and f.anchorY>=0)
            assert(f.anchorX+f.width<=parent.width+1,name)
            assert(f.anchorY+f.height<=parent.height+1,name)
        end
    end
end
assert(api.Hide())
assert(not frames.RCMPalettePanel.visible and not frames.RCMPaletteHex.focus)
assert(api.Show())
assert(frames.RCMLine1.visible)
''', ui=True)

    def test_draft_survives_history_updates_and_rejected_apply(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show() and api.Submit(":color panel"))
frames.RCMPaletteHex:SetText("#F0E080")
triggerFrame(frames.RCMPaletteHex,Event.UI.Textfield.Change)
assert(api.Publish("dev","Incoming diagnostic","Test"))
assert(frames.RCMPaletteHex.text=="#F0E080")
assert(api.SetWindowSize(680,480))
assert(frames.RCMPaletteHex.text=="#F0E080")
assert(api.FocusSearch())
assert(not frames.RCMPalettePanel.visible)
''', ui=True)

    def test_hex_enter_requires_verified_color_focus(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show() and api.Submit(":color panel"))
local original=api.GetChannelColors().system
frames.RCMPaletteHex:SetText("#FFFFFF")
frames.RCMPaletteHex.Event:KeyDown("Enter")
assert(api.GetChannelColors().system==original)
triggerFrame(frames.RCMPaletteHex,Event.UI.Input.Mouse.Left.Click)
frames.RCMPaletteHex.Event:KeyDown("Enter")
assert(api.GetChannelColors().system=="FFFFFF")
''', ui=True)

    def test_small_viewport_closes_palette_and_preserves_command_fallback(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show() and api.Submit(":color panel"))
triggerFrame(frames.RCMPaletteHex,Event.UI.Input.Mouse.Left.Click)
UIParent:SetWidth(620);UIParent:SetHeight(440)
fire(Event.System.Update.Begin)
assert(not frames.RCMPalettePanel.visible and not frames.RCMPaletteHex.focus)
assert(not frames.RCMPaletteOpen.visible)
assert(not api.Submit(":color panel"))
assert(api.Submit(":color set system FFFFFF"))
assert(api.GetChannelColors().system=="FFFFFF")
''', ui=True)


if __name__ == "__main__":
    unittest.main()
