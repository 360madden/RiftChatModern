"""Cross-client RIFT addon-data channel tests, using actual Lua 5.1.

Command.Message.Send is addon DATA, never normal say/guild/party/tell chat.
"""
from pathlib import Path
import unittest

try:
    from lupa.lua51 import LuaRuntime
except ImportError:
    LuaRuntime = None

MODULE = Path(__file__).resolve().parents[1] / "addon" / "RiftChatModern" / "AddonMessages.lua"


@unittest.skipUnless(LuaRuntime is not None, "Lua 5.1 unavailable")
class AddonMessagingTests(unittest.TestCase):
    def run_lua(self, script):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(MODULE.read_text(encoding="utf-8"))
        lua.execute(script)

    def test_accept_exact_namespace_and_receive_text_data(self):
        self.run_lua(r'''
local accepted, incoming, notifications={},{},{}
local clock=10
local bridge=assert(RiftChatModernAddonMessages.new(
    function() error("unexpected send") end,
    function(kind,id) accepted[#accepted+1]={kind,id} end,
    function(from,data) incoming[#incoming+1]={from,data} end,
    function(note,to) notifications[#notifications+1]={note,to} end,
    function() return clock end
))
assert(bridge:enable())
assert(bridge:enable()) -- idempotent; one accept registration only
assert(#accepted==1 and accepted[1][1]=="send"
    and accepted[1][2]=="RCMDevV1")
assert(not bridge:receive("Atank","say",nil,"RCMDevV1","hi"))
assert(not bridge:receive("Atank","send",nil,"OTHER","hi"))
assert(not bridge:receive("Atank","send","channel","RCMDevV1","hi"))
assert(bridge:receive("Atank","send",nil,"RCMDevV1","RR2 online"))
assert(incoming[1][1]=="Atank" and incoming[1][2]=="RR2 online")
assert(bridge:status().received==1)
assert(not bridge:receive("Atank","send",nil,"RCMDevV1",string.rep("x",241)))
assert(bridge:status().invalid==1)
assert(#notifications==0)
''')

    def test_send_is_rate_limited_and_ack_not_delivery(self):
        self.run_lua(r'''
local clock=10
local queued,notes={},{}
local bridge=assert(RiftChatModernAddonMessages.new(
    function(target,id,data,callback)
        queued[#queued+1]={target,id,data,callback}
        return true
    end,
    function(kind,id) return true end,
    function(from,data) end,
    function(note,to) notes[#notes+1]={note,to} end,
    function() return clock end))
assert(bridge:enable())
local result=assert(bridge:sendTo("Atank","probe"))
assert(result.status=="api_submitted" and result.delivery_verified==false)
assert(bridge:status().pending==true)
assert(not bridge:sendTo("Atank","second"))
assert(queued[1][2]=="RCMDevV1" and queued[1][3]=="probe")
queued[1][4](false,"")
assert(bridge:status().pending==false)
assert(bridge:status().accepted==1 and bridge:status().submitted==1)
assert(notes[1][1]:find("delivery unverified",1,true))
-- A duplicate callback does not record a second acknowledgment.
queued[1][4](false,"")
assert(bridge:status().accepted==1)
clock=11
local row,reason=bridge:sendTo("Atank","too soon")
assert(row==nil and reason=="rate_limited")
clock=12.2
local accepted=assert(bridge:sendTo("Atank","again"))
assert(accepted.id==2)
queued[2][4](true,"no queue space")
assert(bridge:status().rejected==1)
assert(bridge:status().pending==false)
''')

    def test_invalid_input_not_sent_and_uncertain_submission_not_retried(self):
        self.run_lua(r'''
local clock=5
local calls=0
local bridge=assert(RiftChatModernAddonMessages.new(
    function(target,id,data,callback)
        calls=calls+1
        error("transport went away after possible insertion")
    end,
    function() return true end,
    function() end,
    function() end,
    function() return clock end))
assert(bridge:enable())
assert(not bridge:sendTo("bad target","test"))
assert(not bridge:sendTo("Atank",""))
assert(not bridge:sendTo("Atank","multi\nline"))
assert(not bridge:sendTo("Atank",string.rep("x",241)))
assert(calls==0)
local sent,reason=bridge:sendTo("Atank","once")
assert(sent==nil and reason=="submission_uncertain")
assert(calls==1)
assert(bridge:status().pending==false and bridge:status().unknown==1
    and bridge:status().rejected==0)
local later,why=bridge:sendTo("Atank","blind retry")
assert(later==nil and why=="rate_limited")
assert(calls==1)
''')

    def test_missing_ack_expires_as_unknown_without_automatic_retry(self):
        self.run_lua(r'''
local now=1
local submissions,notes={},{}
local bridge=assert(RiftChatModernAddonMessages.new(
    function(target,id,data,cb)
        submissions[#submissions+1]={target,id,data,cb}
        return true
    end,
    function() return true end,
    function() end,
    function(note) notes[#notes+1]=note end,
    function() return now end))
assert(bridge:enable())
local sent=assert(bridge:sendTo("Atank","request"))
assert(sent.id==1)
now=15.9
assert(bridge:status().pending==true)
now=16
local status=bridge:status()
assert(status.pending==false and status.unknown==1 and status.accepted==0)
assert(#submissions==1 and #notes==1)
-- The late callback is intentionally ignored after a lost receipt.
submissions[1][4](false,"too late")
assert(bridge:status().accepted==0 and bridge:status().unknown==1)
local later=assert(bridge:sendTo("Atank","new deliberate request"))
assert(later.id==2 and #submissions==2)
submissions[2][4](false,"queued")
assert(bridge:status().accepted==1)
''')

    def test_cross_shard_target_and_synchronous_callback_ack(self):
        self.run_lua(r'''
local now=10
local calls=0
local bridge=assert(RiftChatModernAddonMessages.new(
    function(target,id,data,cb)
        assert(target=="Atank@Deepwood" and id=="RCMDevV1")
        calls=calls+1
        cb(false,"queued during invocation")
        return true
    end,
    function() return true end,
    function() end,
    function() end,
    function() return now end))
assert(bridge:enable())
local result=assert(bridge:sendTo("Atank@Deepwood","ping"))
assert(result.status=="server_queue_accepted")
assert(result.delivery_verified==false)
assert(bridge:status().accepted==1 and bridge:status().pending==false)
assert(calls==1)
''')

    def test_synchronous_callback_failure_does_not_report_send_success(self):
        self.run_lua(r'''
local bridge=assert(RiftChatModernAddonMessages.new(
    function(target,id,data,cb)
        cb(true,"bad destination")
        return true
    end,
    function() return true end,
    function() end,
    function() end,
    function() return 5 end))
assert(bridge:enable())
local ok,reason=bridge:sendTo("Atank","x")
assert(ok==nil and reason=="server_rejected")
assert(bridge:status().rejected==1 and bridge:status().accepted==0)
''')

    def test_immediate_rejection_plus_false_return_not_double_counted(self):
        self.run_lua(r'''
local bridge=assert(RiftChatModernAddonMessages.new(
    function(target,id,data,cb)
        cb(true,"rejected")
        return false
    end,
    function() return true end,
    function() end,
    function() end,
    function() return 10 end))
assert(bridge:enable())
local ok,reason=bridge:sendTo("Atank","once")
assert(ok==nil and reason=="server_rejected")
assert(bridge:status().rejected==1)
assert(bridge:status().submitted==1)
assert(bridge:status().unknown==0)
''')

    def test_missing_dependencies_or_clock_rejected(self):
        self.run_lua(r'''
assert(not RiftChatModernAddonMessages.new(nil,nil,nil,nil,nil))
local bridge=assert(RiftChatModernAddonMessages.new(
    function() end,function() return false end,
    function() end,function() end,function() return 2 end))
local ok,why=bridge:enable()
assert(ok==nil and why=="accept_unavailable")
assert(bridge:status().ready==false)
''')

    def test_valid_receive_failure_is_not_wire_format_failure(self):
        self.run_lua(r"""
local b=assert(RiftChatModernAddonMessages.new(
    function() end,function() return true end,
    function() return false end,function() end,function() return 1 end))
assert(b:enable())
assert(not b:receive("Atank","send",nil,"RCMDevV1","x"))
local status=b:status()
assert(status.received==0 and status.invalid==0 and status.receiveFailed==1)
""")

    def test_no_remote_command_execution_in_received_payload(self):
        self.run_lua(r'''
local received={}
local bridge=assert(RiftChatModernAddonMessages.new(
    function() end,function() return true end,
    function(from,data) received[#received+1]=data end,
    function() end,function() return 10 end))
assert(bridge:enable())
assert(bridge:receive("Atank","send",nil,"RCMDevV1",":rpt arm"))
assert(received[1]==":rpt arm")
-- Received data is only passed to a data callback; no dispatcher exists.
assert(bridge:status().received==1 and bridge:status().submitted==0)
''')

if __name__ == "__main__":
    unittest.main()
