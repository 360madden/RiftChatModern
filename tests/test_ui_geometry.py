"""RiftChatModern v0.2.13 visual geometry, drag and key-focus contracts.

Actual Lua 5.1 with mocked game UI. Does not inject keyboard/mouse into RIFT.
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


@unittest.skipUnless(LuaRuntime is not None, "Lua 5.1 unavailable")
class UiGeometryTests(unittest.TestCase):
    def run_lua(self, script):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(RIFT_MOCK)
        lua.execute((ADDON / "Core.lua").read_text(encoding="utf-8"))
        lua.execute((ADDON / "AddonMessages.lua").read_text(encoding="utf-8"))
        lua.execute((ADDON / "NativeChatProbe.lua").read_text(encoding="utf-8"))
        lua.execute((ADDON / "ConsoleMirror.lua").read_text(encoding="utf-8"))
        lua.execute((ADDON / "HostIngress.lua").read_text(encoding="utf-8"))
        source = (ADDON / "Main.lua").read_text(encoding="utf-8")
        lua.execute("assert(loadstring(" + _lua_quote(source) +
                    "))({identifier='RiftChatModern',version='0.2.13'})")
        lua.execute(script)

    def test_every_control_fits_and_fonts_are_legible(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
assert(RiftChatModernAPI.Show())
local p=frames.RiftChatModernWindow
assert(p.width==760 and p.height==618)
assert(frames.RCMTitle.fontSize>=20)
assert(frames.RCMInput.fontSize>=18)
assert(frames.RCMLineText1.fontSize>=16)
assert(frames.RCMFocusIndicator.fontSize>=14)
assert(frames.RCMDragHandle.mouseMask=="full")
assert(frames.RCMTitle.mouseMask=="limited")
assert(frames.RCMPageUpLabel.text=="OLDER")
assert(frames.RCMPageDownLabel.text=="NEWER")
assert(frames.RCMPageUp.width>=60 and frames.RCMPageDown.width>=60)
for name,control in pairs(frames) do
    if name:sub(1,3)=="RCM" and control~=p
        and control.width and control.height then
        assert(control.x>=p.x and control.y>=p.y
            and control.x+control.width<=p.x+p.width+1
            and control.y+control.height<=p.y+p.height+1,
            "Control escapes window: "..name)
    end
end
''')

    def test_getter_verified_focus_search_hidden_unknown(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
-- The mock initially returns nil; never equate missing focus data to "closed".
assert(api.GetFocusState()=="unavailable")
assert(api.GetStatus().editorFocusState=="unavailable")
assert(api.FocusEditor())
assert(api.GetFocusState()=="focused")
assert(api.GetStatus().editorFocused==true)
assert(frames.RCMFocusIndicator.text:find("FOCUSED",1,true))
frames.RCMInput:SetKeyFocus(false)
assert(api.FocusSearch())
assert(api.GetFocusState()=="search")
assert(api.GetStatus().searchFocused==true)
assert(api.Hide())
assert(api.GetFocusState()=="hidden")
assert(api.GetStatus().editorFocused==false)
assert(api.GetStatus().searchFocused==false)
''')

    def test_drag_persists_on_mouse_release_outside_and_clamps(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
assert(RiftChatModernAPI.Show())
local p=frames.RiftChatModernWindow
local startX,startY=p:GetLeft(),p:GetTop()
mx,my=startX+40,startY+20
held=true
triggerFrame(frames.RCMDragHandle,Event.UI.Input.Mouse.Left.Down)
mx,my=mx+110,my+70
fire(Event.System.Update.Begin)
assert(p:GetLeft()==startX+110 and p:GetTop()==startY+70)
held=false
triggerFrame(frames.RCMDragHandle,Event.UI.Input.Mouse.Left.Upoutside)
assert(RiftChatModernSaved.ui.x==startX+110)
assert(RiftChatModernSaved.ui.y==startY+70)
-- Deliberately move beyond the game bounds; drag code clamps position.
mx,my=p:GetLeft()+20,p:GetTop()+20
held=true
triggerFrame(frames.RCMDragHandle,Event.UI.Input.Mouse.Left.Down)
mx,my=9000,9000
fire(Event.System.Update.Begin)
held=false
fire(Event.System.Update.Begin)
assert(p:GetLeft()==UIParent:GetWidth()-p.width)
assert(p:GetTop()==UIParent:GetHeight()-p.height)
assert(RiftChatModernSaved.ui.x==p:GetLeft())
assert(RiftChatModernSaved.ui.y==p:GetTop())
''')

    def test_fonts_and_license_are_in_the_addon(self):
        fonts = ADDON / "fonts"
        for name in ("Lato-Regular.ttf", "Lato-Bold.ttf", "Lato-OFL.txt"):
            with self.subTest(file=name):
                self.assertTrue((fonts / name).is_file())


if __name__ == "__main__":
    unittest.main()
