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

if __name__=="__main__":
    unittest.main()
