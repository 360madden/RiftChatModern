"""RCM v0.2.23 — independent timestamp, channel, sender and body columns.

Executed with actual Lua 5.1 and the RIFT API mock. These checks validate
layout and interaction contracts, not physical RIFT screenshot acceptance.
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
class MessageColumnsTests(unittest.TestCase):
    def run_lua(self, script):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(RIFT_MOCK)
        for filename in ("Core.lua", "AddonMessages.lua", "NativeChatProbe.lua", "ConsoleCategories.lua",
                         "ConsoleMirror.lua", "HostIngress.lua", "Main.lua"):
            code = (ADDON / filename).read_text(encoding="utf-8")
            lua.execute("assert(loadstring(" + _lua_quote(code) +
                        "))({identifier='RiftChatModern',version='0.2.23'}, {})")
        lua.execute(script)

    def test_time_channel_sender_body_are_independent_and_second_accurate(self):
        self.run_lua(r'''
local called=0
local saved=os.date
os.date=function(format,epoch)
    assert(format=="%H:%M:%S")
    assert(type(epoch)=="number" and epoch>=0)
    called=called+1
    return "07:50:21"
end
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
local message=assert(api.Publish("addons","Position sampler ready","RR2"))
assert(message.id>=1)
assert(frames.RCMLineTime2.text=="07:50:21")
assert(frames.RCMLineChannel2.text=="[ADDONS]")
assert(frames.RCMLineSender2.text=="RR2")
assert(frames.RCMLineText2.text=="Position sampler ready")
assert(frames.RCMLineTime2.fontSize>=14)
assert(frames.RCMLineText2.fontSize>=16)
assert(frames.RCMLineChannel2.fg[2]>0.6)
assert(called>=2)
os.date=saved
''')

    def test_host_import_retains_explicit_provenance_not_native_guild(self):
        self.run_lua(r'''
RiftChatModernSaved={
  schemaVersion=2,nextId=12,
  history={{id=11,at=1700,kind="import",origin="host_manual",
            source="HostSource",text="verified bytes, origin unknown",
            channelKind="guild",channelName="Guild"}}
}
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
assert(frames.RCMLineChannel1.text=="[HOST/GUILD]")
assert(frames.RCMLineSender1.text=="HostSource")
assert(frames.RCMLineText1.text=="verified bytes, origin unknown")
assert(not frames.RCMLineChannel1.text:find("[GUILD]",1,true))
local row=api.GetHistory("imports","",1,0)[1]
assert(row.origin=="host_manual" and row.kind=="import")
assert(row.nativePlayerChatVerified==false)
''')

    def test_columns_fit_and_reflow_without_overlaps_at_three_sizes(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
for _,dims in ipairs({{680,480},{760,618},{1100,800}}) do
    assert(api.SetWindowSize(dims[1],dims[2]))
    local row=frames.RCMLine1
    local fields={
        frames.RCMLineTime1,frames.RCMLineChannel1,
        frames.RCMLineSender1,frames.RCMLineText1
    }
    for i=1,#fields do
        local f=fields[i]
        assert(f.width>0 and f.height>=20)
        assert(f.anchorX>=0 and f.anchorX+f.width<=row.width,
            "field escapes row at "..dims[1]..": "..i)
        if i>1 then
            local prev=fields[i-1]
            assert(prev.anchorX+prev.width<=f.anchorX,
                "columns overlap at "..dims[1]..": "..i)
        end
    end
    assert(frames.RCMLineText1.width==row.width-
        frames.RCMLineText1.anchorX-8)
end
''')

    def test_long_message_only_truncates_visual_body_detail_remains_complete(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
local text=string.rep("E",392).."✓"
local row=assert(api.Publish("dev",text,"RRE"))
assert(frames.RCMLineText2.text:sub(-3)=="...")
assert(frames.RCMLineChannel2.text=="[DEV]")
assert(frames.RCMLineSender2.text=="RRE")
triggerFrame(frames.RCMLine2,Event.UI.Input.Mouse.Left.Click)
assert(api.GetSelectedMessage().text==text)
assert(api.CopySelectedMessage())
assert(copied=="RRE: "..text)
''')

    def test_empty_rows_do_not_leave_stale_columns_after_filtering(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
assert(api.Publish("addons","hello","RR2"))
assert(frames.RCMLineChannel2.text=="[ADDONS]")
triggerFrame(frames.RCMTabnpc,Event.UI.Input.Mouse.Left.Click)
for i=1,api.GetStatus().visibleRows do
    assert(frames["RCMLineTime"..i].text=="")
    assert(frames["RCMLineChannel"..i].text=="")
    assert(frames["RCMLineSender"..i].text=="")
    assert(frames["RCMLineText"..i].text=="")
    assert(frames["RCMLineMarker"..i].visible==false)
end
''')

    def test_failing_clock_formatter_keeps_data_and_draws_placeholder(self):
        self.run_lua(r'''
local old=os.date
os.date=function() error("date service unavailable") end
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
assert(api.Publish("dev","not lost","RRE"))
assert(frames.RCMLineTime2.text=="--:--:--")
assert(frames.RCMLineText2.text=="not lost")
os.date=old
''')


if __name__ == "__main__":
    unittest.main()
