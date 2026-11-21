"""Physical-scope RIFT Console tab contracts via Lua 5.1 UI mocks.

Read-only console configuration must not be confused with history content.
The RIFT screenshots supply display labels; Inspect.Console provides booleans.
"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_addon import RIFT_MOCK,_lua_quote

try:
    from lupa.lua51 import LuaRuntime
except ImportError:
    LuaRuntime=None

ADDON=Path(__file__).resolve().parents[1]/"addon"/"RiftChatModern"
FILES=("Core.lua","AddonMessages.lua","NativeChatProbe.lua",
       "ConsoleCategories.lua","ConsoleMirror.lua","HostIngress.lua","Main.lua")

@unittest.skipUnless(LuaRuntime is not None,"Lua 5.1 unavailable")
class NativeConsoleViewTests(unittest.TestCase):
    def run_lua(self,script):
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute(RIFT_MOCK)
        lua.execute(r'''
Inspect.Console={
 List=function() return {v001=true,v002=true} end,
 Detail=function(id)
  if id=="v001" then return {id=id,name="General",
    say=true,guild=true,party=false,system=true,skill=true,
    npc=true,achievement=true,accolade=true,
    lootItem=true,lootMoney=true,lootGroup=true,purchase=true,
    craftingSelf=true,
    tell=true,emote=true,yell=false,officer=false,raid=true,raidWarning=true,
    channel={Silverwood=true,Events=true,["Level 1-29"]=true,
             ["Level 30-49"]=true,Trade=false}} end
  return {id=id,name="Combat",combatGood=true,combatBad=true}
 end
}
''')
        for name in FILES:
            src=(ADDON/name).read_text(encoding="utf-8")
            lua.execute("assert(loadstring("+_lua_quote(src)
                        +"))({identifier='RiftChatModern',version='0.2.22'}, {})")
        lua.execute(script)

    def test_ui_matches_native_game_loot_player_channel_groups(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
assert(frames.RCMTabnative and frames.RCMNativeCatalog)
assert(frames.RCMTabchat==nil) -- was a duplicate of Imports, mislabeled as native chat
assert(frames.RCMTabsystemLabel.text=="NOTICES")
assert(frames.RCMTabnpcLabel.text=="NPC SAY")
assert(frames.RCMNativeCatalog.visible==false)
local initialCount=api.GetStatus().historyCount
triggerFrame(frames.RCMTabnative,Event.UI.Input.Mouse.Left.Click)
assert(frames.RCMNativeCatalog.visible)
assert(api.GetStatus().displayMode=="native_subscriptions")
assert(api.GetStatus().nativeSocialSendAvailable==false)
assert(api.GetStatus().nativeTranscriptReadable==false)
assert(not frames.RCMLine1.visible)
assert(frames.RCMNativeCatalogTitle.text:find("General",1,true))
assert(frames.RCMNativeCategoryLabel1.text=="System")
assert(frames.RCMNativeCategoryState1.text=="ON")
assert(frames.RCMNativeCategoryLabel3.text=="Notoriety")
assert(frames.RCMNativeCategoryState3.text=="OFF")
assert(frames.RCMNativeCategoryState7.text=="OFF")
assert(frames.RCMTabnativePlate.texturePath=="textures/glass_tab_active.png")
triggerFrame(frames.RCMNativeGrouploot,Event.UI.Input.Mouse.Left.Click)
assert(frames.RCMNativeCategoryLabel1.text=="Item Loot")
assert(frames.RCMNativeCategoryLabel6.text=="Crafting Others")
assert(frames.RCMNativeCategoryState6.text=="OFF")
triggerFrame(frames.RCMNativeGroupplayer,Event.UI.Input.Mouse.Left.Click)
assert(frames.RCMNativeCategoryLabel1.text=="Say")
assert(frames.RCMNativeCategoryState1.text=="ON")
-- Page 2 contains Warfront; explicitly NOT accessible in documented API.
triggerFrame(frames.RCMPageDown,Event.UI.Input.Mouse.Left.Click)
assert(frames.RCMNativeCategoryLabel2.text=="Warfront")
assert(frames.RCMNativeCategoryState2.text=="N/A")
triggerFrame(frames.RCMNativeGrouppublic,Event.UI.Input.Mouse.Left.Click)
assert(frames.RCMNativeCategoryLabel1.text=="Events")
assert(frames.RCMNativeCategoryLabel2.text=="Level 1-29")
assert(frames.RCMNativeCategoryLabel3.text=="Level 30-49")
assert(frames.RCMNativeCategoryLabel4.text=="Silverwood")
assert(frames.RCMNativeCategoryState4.text=="ON")
assert(api.GetStatus().historyCount==initialCount)
triggerFrame(frames.RCMClear,Event.UI.Input.Mouse.Left.Click)
assert(api.GetStatus().historyCount==initialCount)
assert(frames.RCMStatus.text:find("disabled in read-only CONSOLE",1,true))
triggerFrame(frames.RCMTaball,Event.UI.Input.Mouse.Left.Click)
assert(frames.RCMNativeCatalog.visible==false)
assert(frames.RCMLine1.visible==true)
assert(api.GetStatus().displayMode=="history")
assert(api.GetStatus().filter=="all")
''')

    def test_native_panel_small_window_paging_and_source_switch(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
assert(api.SetWindowSize(680,480))
triggerFrame(frames.RCMTabnative,Event.UI.Input.Mouse.Left.Click)
assert(frames.RCMNativeCatalog.width==frames.RCMMessageCard.width-8)
assert(frames.RCMNativeCatalog.visible)
local n=api.GetStatus()
assert(n.nativeSourceGroup=="game" and n.displayMode=="native_subscriptions")
local shown=0
for i=1,16 do
 if frames["RCMNativeCategoryLabel"..i].visible then
  shown=shown+1
  local f=frames["RCMNativeCategoryLabel"..i]
  assert(f.anchorX+f.width<=frames.RCMNativeCatalog.width)
  assert(f.anchorY+f.height<frames.RCMNativeCatalog.height)
 end
end
assert(shown>=2 and shown<=5)
assert(frames.RCMPageUpLabel.text=="PREV")
assert(frames.RCMPageDownLabel.text=="NEXT")
triggerFrame(frames.RCMPageDown,Event.UI.Input.Mouse.Left.Click)
assert(frames.RCMNativeCatalogNote.text:find("page 2/",1,true))
triggerFrame(frames.RCMNativeSource,Event.UI.Input.Mouse.Left.Click)
assert(frames.RCMNativeCatalogTitle.text:find("Combat",1,true))
assert(frames.RCMNativeCategoryState1.text=="OFF")
triggerFrame(frames.RCMNativeGroupcombat,Event.UI.Input.Mouse.Left.Click)
assert(frames.RCMNativeCategoryLabel1.text=="Combat Good")
assert(frames.RCMNativeCategoryState1.text=="ON")
triggerFrame(frames.RCMNativeRefresh,Event.UI.Input.Mouse.Left.Click)
assert(frames.RCMNativeCatalog.visible)
triggerFrame(frames.RCMTaball,Event.UI.Input.Mouse.Left.Click)
assert(frames.RCMPageUpLabel.text=="OLDER")
assert(frames.RCMPageDownLabel.text=="NEWER")
''')

    def test_legacy_chat_filter_still_shows_imports_as_selected_tab(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
assert(api.Submit(":filter chat"))
assert(api.GetStatus().filter=="chat")
assert(frames.RCMTabimportsPlate.texturePath=="textures/glass_tab_active.png")
assert(frames.RCMTabchat==nil)
triggerFrame(frames.RCMTabimports,Event.UI.Input.Mouse.Left.Click)
assert(api.GetStatus().filter=="imports")
''')

    def test_event_notifications_and_npc_say_are_not_mislabeled_system_transcript(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
fire(Event.Chat.Notify,{message="Boss alert"})
fire(Event.Chat.Npc,{fromName="Guardian",message="You shall not pass"})
local system=api.GetHistory("system","",10,0)
local npc=api.GetHistory("npc","",10,0)
assert(RiftChatModernCore.rowLabel(system[#system])=="SCREEN NOTIFY")
assert(RiftChatModernCore.rowShortLabel(system[#system])=="NOTIFY")
assert(RiftChatModernCore.rowLabel(npc[1])=="NPC SAY")
assert(RiftChatModernCore.rowShortLabel(npc[1])=="NPC SAY")
assert(frames.RCMLineChannel2.text=="[NOTIFY]")
assert(frames.RCMLineChannel3.text=="[NPC SAY]")
assert(system[#system].nativePlayerChatVerified==false)
assert(npc[1].nativePlayerChatVerified==false)
''')

    def test_native_groups_command_is_settings_only_not_social_history(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
assert(api.Submit(":native player"))
local row=api.GetHistory("dev","",10,0)[1]
assert(row.text:find("Warfront=N/A",1,true))
assert(row.text:find("native settings only",1,true))
assert(not row.nativePlayerChatVerified)
assert(api.Submit(":native groups"))
assert(api.GetHistory("dev","",10,0)[2].kind=="dev")
assert(api.Submit(":native view"))
assert(api.GetStatus().displayMode=="native_subscriptions")
assert(frames.RCMNativeCatalog.visible)
''')

if __name__=="__main__":
    unittest.main()
