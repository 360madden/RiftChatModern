"""RIFT MMO native-console category contract, verified Lua 5.1 fixtures.

The categories are read-only Inspect.Console.Detail subscription metadata,
not an ordinary Say/Guild/Tell/Party transcript. Includes the exact labels
from physical native Console Settings screenshots.
"""
from pathlib import Path
import unittest

try:
    from lupa.lua51 import LuaRuntime
except ImportError:
    LuaRuntime = None

ADDON=Path(__file__).resolve().parents[1]/"addon"/"RiftChatModern"

@unittest.skipUnless(LuaRuntime is not None,"Requires actual Lua 5.1")
class ConsoleCategoriesTests(unittest.TestCase):
    def run_lua(self,body):
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute((ADDON/"NativeChatProbe.lua").read_text(encoding="utf-8"))
        lua.execute((ADDON/"ConsoleCategories.lua").read_text(encoding="utf-8"))
        lua.execute(body)

    def test_group_names_and_exact_rift_native_settings(self):
        self.run_lua(r'''
local api=RiftChatModernConsoleCategories
local sections=api.sections()
assert(#sections==5)
assert(sections[1].id=="game" and sections[1].title=="GAME MESSAGES")
assert(sections[2].id=="loot" and sections[3].id=="player")
assert(sections[4].id=="public" and sections[5].id=="combat")
local snap=RiftChatModernNativeProbe.capture(nil,{Console={
 List=function() return {v002=true,v001=true} end,
 Detail=function(id)
  if id=="v001" then return {name="General",id=id,
      system=true,skill=true,npc=true,
      achievement=true,accolade=true,
      say=true,tell=true,emote=true,yell=false,guild=true,
      officer=false,party=true,raidWarning=true,raid=true,
      lootItem=true,lootMoney=true,lootGroup=true,
      purchase=true,craftingSelf=true,
      channel={["Silverwood"]=true,["Level 1-29"]=true,
        ["Events"]=true,["Level 30-49"]=true,["Trade"]=false}}
  end
  return {name="Combat",id=id,combatGood=true,combatBad=true}
 end,
}})
local game=assert(api.group(snap,"game"))
assert(game.consoleName=="General" and game.consoleIndex==1)
assert(#game.entries==7)
assert(game.entries[1].label=="System" and game.entries[1].state=="ON")
assert(game.entries[3].label=="Notoriety" and game.entries[3].state=="OFF")
assert(game.entries[7].label=="Experience" and game.entries[7].state=="OFF")
assert(game.entries[4].label=="NPC Say" and game.entries[4].state=="ON")
assert(game.enabled==5 and game.disabled==2 and game.unknown==0)
local loot=assert(api.group(snap,"loot"))
assert(#loot.entries==6 and loot.entries[6].state=="OFF")
local player=assert(api.group(snap,"player"))
assert(#player.entries==10)
assert(player.entries[1].label=="Say" and player.entries[1].state=="ON")
assert(player.entries[10].label=="Warfront")
assert(player.entries[10].state=="N/A")
assert(player.entries[10].source=="native_ui_only_no_documented_api_flag")
assert(player.notExposed==1)
local public=assert(api.group(snap,"public"))
assert(#public.entries==4)
assert(public.entries[1].label=="Events")
assert(public.entries[1].state=="ON")
assert(public.entries[2].label=="Level 1-29")
assert(public.entries[3].label=="Level 30-49")
assert(public.entries[4].label=="Silverwood")
local summary=assert(api.summary(snap,"player"))
assert(summary:find("Warfront=N/A",1,true))
assert(summary:find("native settings only",1,true))
assert(not summary:find("Trade",1,true))
assert(player.nativeSocialSendAvailable==false)
assert(player.nativeTranscriptReadable==false)
''')

    def test_no_console_data_never_defaults_to_off(self):
        self.run_lua(r'''
local api=RiftChatModernConsoleCategories
local game=api.group(nil,"game")
assert(game.consoleCount==0 and game.consoleDetailAvailable==false)
assert(game.entries[1].state=="?" and game.enabled==0)
assert(game.unknown==7)
local player=api.group({consoles={{name="No Detail"}}},"player")
assert(player.entries[1].state=="?" and player.entries[10].state=="N/A")
local pub=api.group(nil,"public")
assert(#pub.entries==0 and pub.enabled==0)
assert(api.summary(nil,"public"):find("none reported",1,true))
local result,reason=api.group(nil,"invented")
assert(result==nil and reason=="unknown_console_category")
''')

    def test_console_selection_cycling_and_bounds(self):
        self.run_lua(r'''
local api=RiftChatModernConsoleCategories
local snap={consoles={
 {id="a",name="Party",detailAvailable=true,channels={party=true}},
 {id="b",name="General",detailAvailable=true,channels={party=false}},
 {id="c",name="Combat",detailAvailable=true,channels={combatGood=true}}
 }}
local row,i,n=api.choose(snap)
assert(row.name=="General" and i==2 and n==3)
assert(api.group(snap,"player").entries[7].state=="OFF")
assert(api.group(snap,"player",1).entries[7].state=="ON")
assert(api.group(snap,"combat",3).entries[1].state=="ON")
assert(api.group(snap,"player",99).consoleName=="General")
assert(api.group(snap,"player",0).consoleIndex==2)
assert(api.overview(snap):find("General",1,true))
''')

    def test_public_channels_are_read_only_and_do_not_forge_disabled(self):
        self.run_lua(r'''
local api=RiftChatModernConsoleCategories
local one={name="General",detailAvailable=true,
 publicChannels={"Silverwood","Events"},publicChannelsTruncated=true,
 channels={guild=false,system=true}}
local snap={consoles={one}}
local p=api.group(snap,"public")
assert(p.enabled==2 and p.disabled==0 and p.unknown==1)
assert(p.entries[1].source=="native_public_channel_subscription")
assert(p.entries[2].state=="ON")
assert(not p.entries[3])
assert(#api.summary(snap,"public")<=470)
local game=api.group(snap,"game")
assert(game.entries[1].state=="ON" and game.entries[2].state=="OFF")
assert(not game.nativeTranscriptReadable and not game.nativeSocialSendAvailable)
''')

if __name__=="__main__":
    unittest.main()
