"""RCM opt-in log feasibility marker, compatible with LuaPadModern watcher.

No live game input, actual log files, clipboard, or real RIFT transport used.
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
FILES = ("Core.lua", "AddonMessages.lua", "NativeChatProbe.lua",
         "ConsoleMirror.lua", "HostIngress.lua", "Main.lua")


@unittest.skipUnless(LuaRuntime is not None, "Lua 5.1 via Lupa required")
class LogProbeTests(unittest.TestCase):
    def run_lua(self, script):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(RIFT_MOCK)
        for filename in FILES:
            source = (ADDON / filename).read_text(encoding="utf-8")
            lua.execute("assert(loadstring(" + _lua_quote(source) +
                        "))({identifier='RiftChatModern',version='0.2.17'}, {})")
        lua.execute(script)

    def test_explicit_logprobe_emits_luapad_compatible_marker(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.GetStatus().logProbeAvailable==true)
assert(api.GetStatus().logProbeTransportVerified==false)
now=1795180000
local before=#displays
assert(api.Submit(":logprobe RCM_PROBE_20261120"))
assert(#displays==before+1)
assert(displays[#displays]=="LPB_PROBE|RCM_PROBE_20261120|1795180000.000")
local rows,total=api.GetHistory("dev","",10,0)
assert(total>=1)
assert(rows[#rows].text:find("Log.txt receipt unverified",1,true))
local markerRows,found=api.GetHistory("all","LPB_PROBE|",10,0)
assert(found==0) -- probe emitted to console; history is not player-chat ingestion
assert(api.GetStatus().nativePlayerChatCaptureAvailable==false)
assert(RiftChatModernSaved.logProbeHistory==nil)
''')

    def test_invalid_nonce_does_not_emit_marker(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
local count=#displays
for _,input in ipairs({":logprobe",
    ":logprobe short",
    ":logprobe ABC+1234",
    ":logprobe "..string.rep("A",81)}) do
    assert(api.Submit(input))
    assert(#displays==count)
end
local rows=api.GetHistory("dev","",10,0)
assert(rows[#rows].text:find("Usage",1,true))
''')

    def test_missing_console_api_and_failures_never_claim_delivery(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
Command.Console.Display=nil
assert(api.GetStatus().logProbeAvailable==false)
assert(api.Submit(":logprobe RCM_TEST_123456"))
local rows=api.GetHistory("dev","",10,0)
assert(rows[#rows].text:find("unavailable",1,true))
Command.Console.Display=function() error("blocked") end
assert(api.Submit(":logprobe RCM_TEST_123456"))
rows=api.GetHistory("dev","",10,0)
assert(rows[#rows].text:find("emission failed",1,true))
Command.Console.Display=function() return false end
assert(api.Submit(":logprobe RCM_TEST_123456"))
rows=api.GetHistory("dev","",10,0)
assert(rows[#rows].text:find("emission failed",1,true))
''')

    def test_missing_server_clock_uses_unknown_epoch(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
Inspect.Time.Server=function() error("clock unavailable") end
local api=RiftChatModernAPI
assert(api.Submit(":logprobe RCM_TEST_123456"))
assert(displays[#displays]=="LPB_PROBE|RCM_TEST_123456|unknown")
local rows=api.GetHistory("dev","",10,0)
assert(rows[#rows].text:find("receipt unverified",1,true))
''')

if __name__ == "__main__":
    unittest.main()
