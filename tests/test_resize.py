"""RCM v0.2.21 resize/viewport and persistence contracts using Lua 5.1 mocks.

These tests verify code geometry and event handling, not physical RIFT mouse behavior.
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
class ResizeTests(unittest.TestCase):
    def run_lua(self, script):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(RIFT_MOCK)
        for name in ("Core.lua", "AddonMessages.lua", "NativeChatProbe.lua",
                     "ConsoleMirror.lua", "HostIngress.lua", "Main.lua"):
            source = (ADDON / name).read_text(encoding="utf-8")
            lua.execute("assert(loadstring(" + _lua_quote(source) +
                        "))({identifier='RiftChatModern',version='0.2.21'}, {})")
        lua.execute(script)

    def test_every_active_child_fits_parent_across_window_sizes(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
local function actual(frame)
    if not frame.anchorParent then return frame.x or 0,frame.y or 0 end
    local x,y=actual(frame.anchorParent)
    return x+frame.anchorX,y+frame.anchorY
end
local function trulyVisible(frame)
    if frame.visible==false then return false end
    return not frame.anchorParent or trulyVisible(frame.anchorParent)
end
local p=frames.RiftChatModernWindow
for _,dims in ipairs({{680,480},{760,618},{1100,800}}) do
    assert(api.SetWindowSize(dims[1],dims[2]))
    for name,f in pairs(frames) do
        if name:sub(1,3)=="RCM" and f.anchorParent and f.width and f.height
            and trulyVisible(f) and f.anchorParent.width then
            local x,y=actual(f)
            local px,py=actual(f.anchorParent)
            assert(x>=px and y>=py and x+f.width<=px+f.anchorParent.width+1
                and y+f.height<=py+f.anchorParent.height+1,
                "Child outside parent: "..name.." at "..dims[1].."x"..dims[2])
        end
    end
end
''')

    def test_default_layout_and_resize_grip(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
local p=frames.RiftChatModernWindow
assert(p.width==760 and p.height==618)
assert(api.GetStatus().resizable and api.GetStatus().visibleRows==13)
assert(frames.RCMResizeGrip.mouseMask=="full")
assert(frames.RCMResizeGlyph.text=="//")
assert(frames.RCMMessageCard.width==666 and frames.RCMMessageCard.height==326)
assert(frames.RCMLine1.visible and frames.RCMLine13.visible)
assert(frames.RCMStatus.y>=p.y and frames.RCMStatus.y+frames.RCMStatus.height<=p.y+p.height)
''')

    def test_diagonal_drag_grip_persists_mouse_up_outside(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
local p=frames.RiftChatModernWindow
local x,y=p:GetLeft(),p:GetTop()
mx,my=x+p.width-12,y+p.height-12
held=true
triggerFrame(frames.RCMResizeGrip,Event.UI.Input.Mouse.Left.Down)
-- Resizing owns the pointer: title-bar drag cannot be started.
triggerFrame(frames.RCMDragHandle,Event.UI.Input.Mouse.Left.Down)
mx,my=mx+210,my+192
fire(Event.System.Update.Begin)
assert(p.width==970 and p.height==810)
assert(p:GetLeft()==x and p:GetTop()==y)
local needed=math.floor((p.height-292-10)/24)
assert(api.GetStatus().visibleRows==needed)
assert(frames.RCMLine19.visible)
assert(frames.RCMLineText1.width==frames.RCMLine1.width-
    frames.RCMLineText1.anchorX-8)
held=false
triggerFrame(frames.RCMResizeGrip,Event.UI.Input.Mouse.Left.Upoutside)
assert(RiftChatModernSaved.ui.w==970 and RiftChatModernSaved.ui.h==810)
assert(RiftChatModernSaved.ui.x==x and RiftChatModernSaved.ui.y==y)
assert(api.GetStatus().editorFocusState=="unavailable")
local priorW,priorH=p.width,p.height
fire(Event.System.Update.Begin)
assert(p.width==priorW and p.height==priorH)
''')

    def test_horizontal_vertical_and_lost_mouse_release(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
assert(RiftChatModernAPI.Show())
local p=frames.RiftChatModernWindow
mx,my=p.x+p.width-8,p.y+p.height-8
held=true
triggerFrame(frames.RCMResizeGrip,Event.UI.Input.Mouse.Left.Down)
mx=mx+140
fire(Event.System.Update.Begin)
assert(p.width==900 and p.height==618)
held=false
fire(Event.System.Update.Begin)
assert(RiftChatModernSaved.ui.w==900)
assert(RiftChatModernSaved.ui.h==618)
mx,my=p.x+p.width-8,p.y+p.height-8
held=true
triggerFrame(frames.RCMResizeGrip,Event.UI.Input.Mouse.Left.Down)
my=my+112
fire(Event.System.Update.Begin)
assert(p.width==900 and p.height==730)
held=false
triggerFrame(frames.RCMResizeGrip,Event.UI.Input.Mouse.Left.Up)
assert(RiftChatModernSaved.ui.w==900)
assert(RiftChatModernSaved.ui.h==730)
''')

    def test_minimum_maximum_and_dynamic_rows_paging(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
local p=frames.RiftChatModernWindow
for i=1,120 do assert(api.Publish("dev","event-"..i,"RR2")) end
assert(api.SetWindowSize(50,50))
assert(p.width==680 and p.height==480)
assert(api.GetStatus().visibleRows==7)
assert(frames.RCMLine8==nil or not frames.RCMLine8.visible)
assert(frames.RCMMessageCard.height==188)
assert(frames.RCMInput.y==p.y+397)
assert(frames.RCMResizeGrip.x==p.x+650)
triggerFrame(frames.RCMPageUp,Event.UI.Input.Mouse.Left.Click)
assert(frames.RCMStatus.text:find("showing",1,true))
assert(api.SetWindowSize(10000,10000))
assert(p:GetLeft()+p.width==UIParent:GetWidth())
assert(p:GetTop()+p.height==UIParent:GetHeight())
assert(api.GetStatus().visibleRows>13)
assert(frames.RCMLine8.visible)
assert(frames.RCMLineText1.width==frames.RCMLine1.width-
    frames.RCMLineText1.anchorX-8)
assert(not api.SetWindowSize(0/0,700))
assert(not api.SetWindowSize("oops",700))
assert(api.GetStatus().windowWidth==p.width)
''')

    def test_saved_dimensions_restore_and_preserve_history(self):
        self.run_lua(r'''
RiftChatModernSaved={schemaVersion=1,nextId=9,
    history={{id=8,kind="dev",at=1700,source="RR2",text="keep me"}},
    ui={x=123,y=140,w=1010,h=792,customTag="retained"}}
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
local p=frames.RiftChatModernWindow
assert(p.width==1010 and p.height==792)
assert(p.x==123 and p.y==140)
assert(api.GetStatus().historyCount==2)
assert(RiftChatModernSaved.history[1].text=="keep me")
assert(api.SetWindowSize(990,740))
assert(RiftChatModernSaved.ui.w==990 and RiftChatModernSaved.ui.h==740)
assert(RiftChatModernSaved.ui.customTag=="retained")
assert(RiftChatModernSaved.history[1].text=="keep me")
''')

    def test_bad_saved_geometry_and_viewport_changes_fail_safe(self):
        self.run_lua(r'''
RiftChatModernSaved={schemaVersion=1,history={},
    ui={x="bad",y=0/0,w=math.huge,h=-100}}
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
local p=frames.RiftChatModernWindow
assert(p.width==760 and p.height==480)
assert(p.x>=0 and p.y>=0)
UIParent:SetWidth(850);UIParent:SetHeight(600)
fire(Event.System.Update.Begin)
assert(p.width<=850 and p.height<=600)
assert(p.x>=0 and p.y>=0)
assert(p.x+p.width<=850 and p.y+p.height<=600)
assert(RiftChatModernSaved.ui.w==p.width and RiftChatModernSaved.ui.h==p.height)
assert(RiftChatModernSaved.schemaVersion==2)
''')

    def test_focus_drag_detail_and_resizing_independent(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
assert(api.FocusEditor())
local p=frames.RiftChatModernWindow
assert(api.Publish("dev",string.rep("Hello ",70),"RR2"))
triggerFrame(frames.RCMLine2,Event.UI.Input.Mouse.Left.Click)
assert(frames.RCMDetailOverlay.visible)
assert(api.SetWindowSize(1100,850))
assert(frames.RCMDetailOverlay.width==frames.RCMMessageCard.width-8)
assert(frames.RCMDetailBody.width==frames.RCMDetailOverlay.width-28)
assert(api.GetFocusState()=="focused")
assert(api.CloseMessage())
local sx,sy=p:GetLeft(),p:GetTop()
mx,my=sx+32,sy+18
held=true
triggerFrame(frames.RCMDragHandle,Event.UI.Input.Mouse.Left.Down)
triggerFrame(frames.RCMResizeGrip,Event.UI.Input.Mouse.Left.Down)
mx,my=mx+20,my+24
fire(Event.System.Update.Begin)
assert(p.width==1100 and p.height==850)
assert(p.x==sx+20 and p.y==sy+24)
held=false
triggerFrame(frames.RCMDragHandle,Event.UI.Input.Mouse.Left.Upoutside)
assert(RiftChatModernSaved.ui.w==1100 and RiftChatModernSaved.ui.h==850)
assert(api.Hide() and api.Show())
assert(api.GetStatus().windowWidth==1100)
''')

    def test_slash_size_reset_and_idle_does_not_rebuild_frames(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
fire(slash.rcm,"size 1000 800")
assert(api.GetStatus().windowWidth==1000 and api.GetStatus().windowHeight==800)
local count=0
for _ in pairs(frames) do count=count+1 end
for i=1,100 do fire(Event.System.Update.Begin) end
local after=0
for _ in pairs(frames) do after=after+1 end
assert(after==count)
fire(slash.rcm,"size reset")
assert(api.GetStatus().windowWidth==760 and api.GetStatus().windowHeight==618)
assert(RiftChatModernSaved.ui.w==760 and RiftChatModernSaved.ui.h==618)
''')


if __name__ == "__main__":
    unittest.main()
