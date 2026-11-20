"""Read-only RIFT native-console capability discovery, without transcript claims."""
from pathlib import Path
import unittest

try:
    from lupa.lua51 import LuaRuntime
except ImportError:
    LuaRuntime = None

SCRIPT = Path(__file__).resolve().parents[1] / "addon" / "RiftChatModern" / "NativeChatProbe.lua"


@unittest.skipUnless(LuaRuntime is not None, "Lua 5.1 unavailable")
class NativeConsoleProbeTests(unittest.TestCase):
    def run_lua(self, script):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(SCRIPT.read_text(encoding="utf-8"))
        lua.execute(script)

    def test_missing_native_handles_never_claim_chat_stream(self):
        self.run_lua(r'''
local none=RiftChatModernNativeProbe.capture(nil)
assert(none.windowCount==0 and none.nativeTranscriptReadable==false)
local empty=RiftChatModernNativeProbe.capture({Native={}})
assert(empty.windowCount==0 and empty.focusCount==0)
assert(empty.nativeSocialSendAvailable==false)
''')

    def test_supported_frame_getters_read_no_chat_content(self):
        self.run_lua(r'''
local calls=0
local frame={
    GetVisible=function() return true end,
    GetLoaded=function() return true end,
    GetKeyFocus=function() return false end,
    GetText=function() calls=calls+1; error("never read native chat transcript") end
}
local other={
    GetVisible=function() return false end,
    GetKeyFocus=function() return true end
}
local result=RiftChatModernNativeProbe.capture({
    Native={Console1=frame,Console3=other}
})
assert(result.windowCount==2 and result.visibleCount==1 and result.focusCount==1)
assert(result.windows[1].index==1 and result.windows[1].visible==true)
assert(result.windows[2].index==3 and result.windows[2].elementKeyFocus==true)
assert(calls==0)
assert(result.nativeTranscriptReadable==false)
assert(result.nativeSocialSendAvailable==false)
''')

    def test_broken_getters_and_bad_values_remain_unavailable(self):
        self.run_lua(r'''
local frame={
    GetVisible=function() error("blocked") end,
    GetLoaded=function() return 1 end,
    GetKeyFocus=function() return "yes" end,
}
local result=RiftChatModernNativeProbe.capture({Native={Console1=frame}})
assert(result.windowCount==1 and result.visibleCount==0 and result.focusCount==0)
assert(result.windows[1].visible==nil)
assert(result.windows[1].loaded==nil)
assert(result.windows[1].elementKeyFocus==nil)
''')

    def test_console_list_and_chat_channel_configuration(self):
        self.run_lua(r'''
local listCalls,detailCalls=0,0
local observed=RiftChatModernNativeProbe.capture({Native={}},
  {Console={
    List=function()
        listCalls=listCalls+1
        return {"v001","v005","v002"}
    end,
    Detail=function(id)
        detailCalls=detailCalls+1
        if id=="v001" then return {
            id=id,name="General",guild=true,tell=true,party=false,
            system=true,say=true,chatHistory="do not inspect",channel={"World"}
        } elseif id=="v005" then return {
            id=id,name="Combat",combatGood=true,combatBad=true
        } end
        return {id=id,name="Guild",guild=true,officer=false}
    end
  }})
assert(listCalls==1 and detailCalls==3)
assert(observed.consoleListReady==true)
assert(observed.consoleCount==3)
assert(observed.consoles[1].id=="v001")
assert(observed.consoles[1].name=="General")
assert(observed.consoles[1].channels.guild==true)
assert(observed.consoles[1].channels.tell==true)
assert(observed.consoles[1].channels.party==false)
assert(observed.consoles[2].id=="v002")
assert(observed.consoles[3].channels.combatGood==true)
assert(observed.nativeTranscriptReadable==false)
''')

    def test_real_console_map_and_named_public_channels(self):
        # RIFT Inspect.Console.List is commonly {id=true}, and Detail.channel
        # is a mapping of public channel names, not a boolean subscription.
        self.run_lua(r'''
local got=RiftChatModernNativeProbe.capture(nil,{Console={
    List=function() return {v005=true,v001=true} end,
    Detail=function(id)
        if id=="v001" then return {name="General",id=id,say=true,
            guild=false,raidWarning=true,lootMoney=true,combatSpecial=true,
            channel={["World@Deepwood"]=true,["LookingForGroup"]=true,
                ["Trade"]=false}}
        end
        return {name="Combat",id=id,combatNeutral=true,
            channel={"Zone@Deepwood","World@Deepwood"}}
    end
}})
assert(got.consoleCount==2 and got.consoleListReady)
assert(got.consoles[1].id=="v001")
assert(got.consoles[1].channels.raidWarning==true)
assert(got.consoles[1].channels.lootMoney==true)
assert(got.consoles[1].channels.combatSpecial==true)
assert(got.consoles[1].channels.channel==nil)
assert(got.consoles[1].publicChannelCount==2)
assert(got.consoles[1].publicChannels[1]=="LookingForGroup")
assert(got.consoles[1].publicChannels[2]=="World@Deepwood")
assert(got.consoles[1].publicChannelsTruncated==false)
assert(got.consoles[2].publicChannelCount==2)
assert(got.consoles[2].publicChannels[1]=="World@Deepwood")
assert(got.consoles[2].publicChannels[2]=="Zone@Deepwood")
assert(got.nativeTranscriptReadable==false)
assert(got.nativeSocialSendAvailable==false)
''')

    def test_public_channels_reject_malformed_and_bound_untrusted_tables(self):
        self.run_lua(r'''
local channels={[""]=true,["bad"..string.char(10).."name"]=true,["disabled"]=false,
    [1]="Local",[2]="Local"}
for i=1,200 do channels["zone_"..string.format("%03d",i)]=true end
local captured=RiftChatModernNativeProbe.capture(nil,{Console={
    List=function() return {"v001"} end,
    Detail=function() return {id="v001",name="General",channel=channels} end
}})
local one=captured.consoles[1]
assert(one.detailAvailable and #one.publicChannels<=16)
assert(one.publicChannelsTruncated==true)
for _,name in ipairs(one.publicChannels) do
    assert(name~="" and not name:find(string.char(10),1,true) and name~="disabled")
end
assert(captured.nativeTranscriptReadable==false)
''')

    def test_console_detail_errors_and_large_list_are_bounded(self):
        self.run_lua(r'''
local count=0
local source={}
for i=1,99 do source[i]=string.format("v%03d",i) end
local observed=RiftChatModernNativeProbe.capture(nil,
    {Console={
        List=function() return source end,
        Detail=function(id) count=count+1;error("inaccessible") end
    }})
assert(observed.consoleListReady==true)
assert(observed.consoleListTruncated==true)
assert(observed.consoleCount<=32 and count<=32)
for _,row in ipairs(observed.consoles) do
    assert(row.detailAvailable==false)
end
assert(observed.nativeSocialSendAvailable==false)
''')

    def test_console_api_missing_never_promotes_unavailable(self):
        self.run_lua(r'''
local observed=RiftChatModernNativeProbe.capture(nil,{Console={}})
assert(observed.consoleListReady==false)
assert(observed.consoleCount==0)
assert(observed.nativeTranscriptReadable==false)
''')

if __name__=="__main__":
    unittest.main()
