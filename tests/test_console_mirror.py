"""Opt-in console mirroring preserves Command.Console.Display behavior."""
from pathlib import Path
import unittest
try:
    from lupa.lua51 import LuaRuntime
except ImportError:
    LuaRuntime=None

SRC=Path(__file__).resolve().parents[1]/"addon"/"RiftChatModern"/"ConsoleMirror.lua"


@unittest.skipUnless(LuaRuntime is not None,"Lua 5.1 unavailable")
class ConsoleMirrorTests(unittest.TestCase):
    def run_lua(self,body):
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute(SRC.read_text(encoding="utf-8"))
        lua.execute(body)

    def test_explicit_opt_in_passthrough_and_restore(self):
        self.run_lua(r'''
local calls,lines={},{}
local original=function(...)
    calls[#calls+1]={...}
    return true,nil,32
end
local api={Display=original}
local mirror=assert(RiftChatModernConsoleMirror.new(api,
    function(line,channel) lines[#lines+1]=channel..":"..line return true end))
assert(not mirror:status().enabled)
assert(api.Display("general",true,"before",false)==true)
assert(#lines==0)
assert(mirror:enable())
assert(mirror:status().ownsHook==true)
local first,second,third=api.Display("general",false,"RR2 ready",false)
assert(first==true and second==nil and third==32)
assert(#calls==2 and calls[2][1]=="general")
assert(#lines==1 and lines[1]=="general:RR2 ready")
assert(mirror:status().captured==1)
assert(mirror:disable())
assert(mirror:status().enabled==false)
assert(api.Display==original)
assert(api.Display("general",false,"after",false)==true)
assert(#lines==1)
''')

    def test_html_normalization_and_self_notices_filtered(self):
        self.run_lua(r'''
local captured={}
local api={Display=function() return true end}
local mirror=assert(RiftChatModernConsoleMirror.new(api,
    function(line,channel) captured[#captured+1]=line return true end))
assert(mirror:enable())
api.Display("general",true,
    '<font color="#00ff00">RRE &lt;ready&gt; &amp; loaded</font>',true)
api.Display("general",true,
    '<font color="#ffffff">RiftChatModern v0.2.2 | Loaded</font>',true)
assert(#captured==1)
assert(captured[1]=="RRE <ready> & loaded")
assert(mirror:status().captured==1)
''')

    def test_recursion_guard_captures_first_only(self):
        self.run_lua(r'''
local events,native=0,0
local api={Display=function() native=native+1;return true end}
local mirror=assert(RiftChatModernConsoleMirror.new(api,
    function(line)
        events=events+1
        api.Display("general",true,"callback diagnostic",false)
        return true
    end))
assert(mirror:enable())
api.Display("general",true,"outer",false)
assert(events==1 and native==2)
assert(mirror:status().captured==1)
''')

    def test_hook_replaced_by_other_addon_is_not_overwritten(self):
        self.run_lua(r'''
local orig=function() return true end
local api={Display=orig}
local mirror=assert(RiftChatModernConsoleMirror.new(api,function() end))
assert(mirror:enable())
local wrapper=api.Display
local foreign=function(...) return wrapper(...) end
api.Display=foreign
local ok,why=mirror:disable()
assert(ok==nil and why=="hook_chained")
assert(mirror:status().enabled==false)
assert(api.Display==foreign)
assert(not mirror:enable())
assert(api.Display("general",true,"no capture",false)==true)
assert(mirror:status().captured==0)
''')

    def test_capture_failure_not_misreported_as_stored_message(self):
        self.run_lua(r'''
local api={Display=function() return true end}
local mirror=assert(RiftChatModernConsoleMirror.new(api,function()
    return nil,"no storage"
end))
assert(mirror:enable())
assert(api.Display("general",true,"not stored",false)==true)
assert(mirror:status().captured==0)
assert(mirror:status().rejected==1)
''')

    def test_original_explicit_false_does_not_get_mirrored(self):
        self.run_lua(r'''
local calls=0
local api={Display=function() return false end}
local mirror=assert(RiftChatModernConsoleMirror.new(api,function()
    calls=calls+1
    return true
end))
assert(mirror:enable())
assert(api.Display("general",true,"native refused",false)==false)
assert(calls==0 and mirror:status().captured==0)
''')

    def test_original_errors_not_suppressed(self):
        self.run_lua(r'''
local captured=0
local api={Display=function() error("native rejected") end}
local mirror=assert(RiftChatModernConsoleMirror.new(api,function()
    captured=captured+1
end))
assert(mirror:enable())
local ok,err=pcall(api.Display,"general",true,"data",false)
assert(not ok and err:find("native rejected",1,true))
assert(captured==0)
''')

    def test_disabled_mirror_cannot_claim_player_chat(self):
        self.run_lua(r'''
local api={Display=function() return true end}
local mirror=assert(RiftChatModernConsoleMirror.new(api,function() end))
local status=mirror:status()
assert(status.type=="addon_console_output_only")
assert(status.nativePlayerChatCaptured==false)
assert(status.enabled==false)
''')

if __name__=="__main__":
    unittest.main()
