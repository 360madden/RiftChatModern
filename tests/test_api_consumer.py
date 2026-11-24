"""RCM API v2 contract and standalone consumer integration.

Real Lua 5.1 + RIFT mocks only. No physical client interaction.
"""
from pathlib import Path
import re
import unittest

from test_addon import RIFT_MOCK, _lua_quote

try:
    from lupa.lua51 import LuaRuntime
except ImportError:
    LuaRuntime = None

ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / "addon" / "RiftChatModern"
DEMO = ROOT / "examples" / "RCMIntegrationDemo"
FILES = ("Core.lua", "AddonMessages.lua", "NativeChatProbe.lua", "ConsoleCategories.lua",
         "ConsoleMirror.lua", "HostIngress.lua", "Main.lua")


@unittest.skipUnless(LuaRuntime is not None, "Lua 5.1 unavailable")
class ApiConsumerTests(unittest.TestCase):
    def run_lua(self, scenario, ui=False, demo=False):
        lua = LuaRuntime(unpack_returned_tuples=True)
        if ui:
            lua.execute(RIFT_MOCK)
        for name in FILES if ui else ("Core.lua",):
            src = (ADDON / name).read_text(encoding="utf-8")
            lua.execute("assert(loadstring(" + _lua_quote(src) +
                        "))({identifier='RiftChatModern',version='0.2.26'}, {})")
        if demo:
            src = (DEMO / "Main.lua").read_text(encoding="utf-8")
            lua.execute("assert(loadstring(" + _lua_quote(src) +
                        "))({identifier='RCMIntegrationDemo',version='1.0.0'}, {})")
        lua.execute(scenario)

    def test_subscription_changes_are_not_delivered_during_current_event(self):
        self.run_lua(r'''
local m=assert(RiftChatModernCore.new({schemaVersion=2,nextId=1,history={}}))
local seen={}
local second=function(r) seen[#seen+1]="second:"..r.text end
assert(m:subscribe("b",second))
assert(m:subscribe("a",function(r)
    seen[#seen+1]="first:"..r.text
    if r.text=="one" then
        assert(m:unsubscribe("b"))
        assert(m:subscribe("b",second))
        assert(m:subscribe("c",function(x) seen[#seen+1]="new:"..x.text end))
    end
end))
assert(m:publish("addons","one","Demo",1))
assert(table.concat(seen,",")=="first:one",table.concat(seen,","))
assert(m:publish("addons","two","Demo",2))
assert(table.concat(seen,",")=="first:one,first:two,second:two,new:two")
''')

    def test_callback_errors_and_self_unsubscribe_do_not_interrupt_peers(self):
        self.run_lua(r'''
local m=assert(RiftChatModernCore.new({schemaVersion=2,nextId=1,history={}}))
local seen=0
assert(m:subscribe("a",function()
    assert(m:unsubscribe("a"))
    error("deliberate consumer failure")
end))
assert(m:subscribe("b",function(r)
    assert(r.text=="original")
    seen=seen+1
    r.text="changed only in copy"
end))
assert(m:publish("addons","original","Demo",1).text=="original")
assert(m:publish("addons","original","Demo",2))
assert(seen==2)
assert(m:status().listenerCount==1)
assert(m:status().listenerErrors==1)
assert(m:getHistory("all","",10,0)[1].text=="original")
''')

    def test_listener_diagnostics_do_not_modify_saved_preferences(self):
        self.run_lua(r'''
local s={schemaVersion=2,nextId=1,history={}}
local m=assert(RiftChatModernCore.new(s))
assert(m:subscribe("one",function() end))
assert(m:status().listenerCount==1 and m:status().listenerErrors==0)
assert(m:status().revision==0)
assert(m:unsubscribe("one"))
assert(m:status().listenerCount==0)
assert(m:status().revision==0 and s.listeners==nil and s.listenerErrors==nil)
''')

    def test_history_rejects_false_instead_of_silently_defaulting(self):
        self.run_lua(r'''
local api=RiftChatModernAPI
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
assert(api.GetHistory())
for _,args in ipairs({
 {false,"",10,0}, {"all",false,10,0}, {"all","",false,0},
 {"all","",10,false}, {"all","bad\0query",10,0},
}) do
    local result,err=api.GetHistory(unpack(args))
    assert(result==nil and err=="invalid_query",tostring(err))
end
assert(api.GetStatus().nativePlayerChatCaptureAvailable==false)
''', ui=True)

    def test_pre_ready_status_is_truthful_and_operations_fail_closed(self):
        self.run_lua(r'''
local api=RiftChatModernAPI
local s=api.GetStatus()
assert(s.ready==false)
assert(s.nativePlayerChatCaptureAvailable==false)
assert(s.nativeSocialSendAvailable==false)
for _,name in ipairs({"Publish","GetHistory","RegisterCommand","Subscribe",
                      "Unsubscribe","SetChannelVisible","SetChannelColor"}) do
    local ok,err=api[name]()
    assert(ok==nil and err=="not_ready",name..":"..tostring(err))
end
''', ui=True)

    def test_demo_manifest_declares_dependency_and_startup(self):
        toc = (DEMO / "RiftAddon.toc").read_text(encoding="utf-8")
        self.assertRegex(toc, r'Identifier\s*=\s*"RCMIntegrationDemo"')
        self.assertRegex(toc, r'Dependencies\s*=\s*\{\s*RiftChatModern\s*=\s*\{\s*"required"\s*,\s*"before"\s*\}\s*\}')
        self.assertRegex(toc, r'RunOnStartup\s*=\s*\{\s*"Main.lua"\s*\}')
        self.assertRegex(toc, r'Email\s*=\s*"[^"]+"')
        self.assertTrue((DEMO / "Main.lua").is_file())

    def test_demo_connects_once_when_ready_and_publishes_own_diagnostics(self):
        self.run_lua(r'''
local api=RiftChatModernAPI
fire(Event.Addon.Load.End,"RCMIntegrationDemo")
assert(api.GetStatus().ready==false)
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"UnrelatedAddon")
assert(api.GetStatus().listenerCount==0)
fire(Event.Addon.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RCMIntegrationDemo")
fire(Event.Addon.Load.End,"RCMIntegrationDemo")
local rows,total=api.GetHistory("addons","RCM integration demo ready",20,0)
assert(total==1 and #rows==1)
assert(rows[1].source=="RCMIntegrationDemo" and rows[1].origin=="external_api")
assert(rows[1].nativePlayerChatVerified==false)
assert(api.GetStatus().listenerCount==1)
assert(api.Submit(":rcmdemo status"))
local status=api.GetHistory("dev","own diagnostics=1",10,0)
assert(#status==1)
assert(api.Submit(":rcmdemo ping"))
local p,n=api.GetHistory("addons","RCM demo diagnostic ping",10,0)
assert(n==1 and p[1].origin=="external_api")
assert(api.Submit(":rcmdemo status"))
assert(#api.GetHistory("dev","own diagnostics=2",10,0)==1)
assert(#sends==0)
''', ui=True, demo=True)

    def test_demo_stop_start_and_collision_are_isolated(self):
        self.run_lua(r'''
local api=RiftChatModernAPI
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
assert(api.GetStatus().listenerCount==1)
assert(api.Submit(":rcmdemo stop"))
assert(api.GetStatus().listenerCount==0)
fire(Event.Addon.Load.End,"RCMIntegrationDemo")
assert(api.GetStatus().listenerCount==0)
assert(api.Submit(":rcmdemo ping"))
assert(api.Submit(":rcmdemo start"))
assert(api.Submit(":rcmdemo start"))
assert(api.GetStatus().listenerCount==1)
assert(api.Submit(":rcmdemo ping"))
assert(api.Submit(":rcmdemo status"))
assert(#api.GetHistory("dev","own diagnostics=2",10,0)==1)
assert(#api.GetHistory("addons","RCM demo diagnostic ping",10,0)==2)
''', ui=True, demo=True)

    def test_demo_never_replaces_an_existing_command(self):
        self.run_lua(r'''
local api=RiftChatModernAPI
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
assert(api.RegisterCommand("rcmdemo",function() return "existing owner" end))
fire(Event.Addon.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RCMIntegrationDemo")
assert(api.GetStatus().listenerCount==0)
assert(api.Submit(":rcmdemo status"))
assert(#api.GetHistory("dev","existing owner",10,0)==1)
assert(#api.GetHistory("addons","RCM integration demo ready",10,0)==0)
''', ui=True, demo=True)

    def test_demo_waits_for_compatible_interface(self):
        self.run_lua(r'''
local api=RiftChatModernAPI
api.interfaceVersion=1
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RCMIntegrationDemo")
assert(api.GetStatus().listenerCount==0)
assert(#api.GetHistory("addons","RCM integration demo ready",10,0)==0)
api.interfaceVersion=2
fire(Event.Addon.Load.End,"RCMIntegrationDemo")
assert(api.GetStatus().listenerCount==1)
assert(#api.GetHistory("addons","RCM integration demo ready",10,0)==1)
''', ui=True, demo=True)

    def test_registry_limit_and_nested_publish_contract(self):
        self.run_lua(r'''
local m=assert(RiftChatModernCore.new({schemaVersion=2,nextId=1,history={}}))
local seen=0
for i=1,48 do
    assert(m:subscribe("listener"..i,function(row)
        seen=seen+1
        if i==1 then assert(m:publish("dev","nested","Demo",2)) end
    end))
end
local ok,err=m:subscribe("overflow",function() end)
assert(ok==nil and err=="listener_limit")
assert(m:publish("addons","outer","Demo",1))
assert(seen==48 and m:status().historyCount==2 and m:status().listenerErrors==0)
assert(m:unsubscribe("listener1"))
assert(m:subscribe("replacement",function() end))
assert(m:status().listenerCount==48)
''')

    def test_every_exported_api_function_is_documented(self):
        source = (ADDON / "Main.lua").read_text(encoding="utf-8")
        block = source.split("_G.RiftChatModernAPI={", 1)[1].split("\n}", 1)[0]
        methods = re.findall(r"(?m)^    ([A-Z][A-Za-z0-9]+)=", block)
        self.assertGreaterEqual(len(methods), 30)
        doc = (ROOT / "docs" / "ADDON_API_V2.md").read_text(encoding="utf-8")
        for name in methods:
            with self.subTest(method=name):
                self.assertIn(name + "(", doc)


if __name__ == "__main__":
    unittest.main()
