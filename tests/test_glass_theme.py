"""RiftChatModern v0.2.23 glass theme and RIFT texture API contracts.

Real Lua 5.1 with a modeled RIFT UI, never a physical in-game claim.
"""
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_addon import RIFT_MOCK, _lua_quote

try:
    from lupa.lua51 import LuaRuntime
except ImportError:
    LuaRuntime = None

ADDON = Path(__file__).resolve().parents[1] / "addon" / "RiftChatModern"
TEXTURES = ADDON / "textures"
REQUIRED = (
    "glass_panel", "glass_header", "glass_history", "glass_detail",
    "glass_tab_idle", "glass_tab_active", "glass_tab_hover",
    "glass_button", "glass_button_hover", "glass_primary",
    "glass_primary_hover", "glass_input",
)


@unittest.skipUnless(LuaRuntime is not None, "Lua 5.1 unavailable")
class GlassThemeTests(unittest.TestCase):
    def run_lua(self, script):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(RIFT_MOCK)
        for name in ("Core.lua", "AddonMessages.lua", "NativeChatProbe.lua", "ConsoleCategories.lua",
                     "ConsoleMirror.lua", "HostIngress.lua", "Main.lua"):
            source = (ADDON / name).read_text(encoding="utf-8")
            lua.execute("assert(loadstring(" + _lua_quote(source)
                        + "))({identifier='RiftChatModern',version='0.2.23'}, {})")
        lua.execute(script)

    def test_all_theme_assets_are_real_rgba_pngs(self):
        self.assertEqual(len(list(TEXTURES.glob("glass_*.png"))), len(REQUIRED))
        for name in REQUIRED:
            path = TEXTURES / (name + ".png")
            with self.subTest(asset=name):
                data = path.read_bytes()
                self.assertLess(len(data), 100 * 1024)
                self.assertEqual(data[:8], bytes([137,80,78,71,13,10,26,10]))
                self.assertEqual(data[12:16], b"IHDR")
                w, h = struct.unpack(">II", data[16:24])
                self.assertGreater(w, 100)
                self.assertGreater(h, 50)
                self.assertEqual(data[25], 6, "Expected RGBA PNG for transparency")

    def test_game_texture_paths_tab_selection_and_hover(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
assert(RiftChatModernAPI.Show())
assert(frames.RCMPanelPlate.textureSource=="RiftChatModern")
assert(frames.RCMPanelPlate.texturePath=="textures/glass_panel.png")
assert(frames.RCMHeaderPlate.texturePath=="textures/glass_header.png")
assert(frames.RCMHistoryPlate.texturePath=="textures/glass_history.png")
assert(frames.RCMInputPlate.texturePath=="textures/glass_input.png")
assert(frames.RCMSearchPlate.texturePath=="textures/glass_input.png")
assert(frames.RCMTaballPlate.texturePath=="textures/glass_tab_active.png")
assert(frames.RCMTabaddonsPlate.texturePath=="textures/glass_tab_idle.png")
triggerFrame(frames.RCMTabaddons,Event.UI.Input.Mouse.Left.Click)
assert(RiftChatModernAPI.GetStatus().filter=="addons")
assert(frames.RCMTaballPlate.texturePath=="textures/glass_tab_idle.png")
assert(frames.RCMTabaddonsPlate.texturePath=="textures/glass_tab_active.png")
triggerFrame(frames.RCMTabdev,Event.UI.Input.Mouse.Cursor.In)
assert(frames.RCMTabdevPlate.texturePath=="textures/glass_tab_hover.png")
triggerFrame(frames.RCMTabdev,Event.UI.Input.Mouse.Cursor.Out)
assert(frames.RCMTabdevPlate.texturePath=="textures/glass_tab_idle.png")
assert(frames.RCMSendPlate.texturePath=="textures/glass_primary.png")
triggerFrame(frames.RCMSend,Event.UI.Input.Mouse.Cursor.In)
assert(frames.RCMSendPlate.texturePath=="textures/glass_primary_hover.png")
triggerFrame(frames.RCMSend,Event.UI.Input.Mouse.Cursor.Out)
assert(frames.RCMSendPlate.texturePath=="textures/glass_primary.png")
''')

    def test_skin_responds_to_resizing_and_color_marker(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
assert(api.Publish("npc","Hello from the game","NPC"))
for _,size in ipairs({{680,480},{760,618},{1040,780}}) do
    assert(api.SetWindowSize(size[1],size[2]))
    assert(frames.RCMPanelPlate.width==size[1])
    assert(frames.RCMPanelPlate.height==size[2])
    assert(frames.RCMHeaderPlate.width==size[1])
    assert(frames.RCMHistoryPlate.width==size[1]-94)
    assert(frames.RCMInputPlate.width==size[1]-128)
    assert(frames.RCMInputPlate.height==40)
end
assert(frames.RCMLineMarker1.visible==true)
assert(frames.RCMLineMarker1.width==3)
local npcColorVerified=false
for i=1,api.GetStatus().visibleRows do
    local label=frames["RCMLineText"..i]
    if label and label.text:find("Hello from the game",1,true) then
        assert(frames["RCMLineMarker"..i].bg[2]>0.8)
        npcColorVerified=true
    end
end
assert(npcColorVerified,"NPC message not found among rendered rows")
assert(frames.RCMLineMarker8.visible==false,
    "Marker8 visible="..tostring(frames.RCMLineMarker8.visible)
    .." history="..tostring(api.GetStatus().historyCount)
    .." marker1color="..tostring(frames.RCMLineMarker1.bg[2]))
''')

    def test_missing_texture_api_keeps_safe_color_fallback(self):
        self.run_lua(r'''
-- Override a future UI.CreateFrame call to emulate texture load rejection.
local original = UI.CreateFrame
UI.CreateFrame = function(kind,name,parent)
    local f=original(kind,name,parent)
    if kind=="Texture" then
        function f:SetTexture(source,path) error("texture unavailable") end
    end
    return f
end
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
assert(RiftChatModernAPI.Show())
assert(frames.RCMPanelPlate.visible==false)
assert(frames.RiftChatModernWindow.bg[4]>0.9)
assert(frames.RCMTaball.bg[4]>0.8)
assert(frames.RCMTitle.text=="RIFT CHAT  /  MODERN")
assert(RiftChatModernAPI.GetStatus().nativeSocialSendAvailable==false)
''')
