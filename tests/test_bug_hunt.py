"""RCM codebase bug-hunt regression tests: real Lua 5.1 + bounded fake RIFT UI.

These are offline contracts, not claims of physical-game acceptance.
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
class BugHuntTests(unittest.TestCase):
    def run_lua(self, source, script):
        lua = LuaRuntime(unpack_returned_tuples=True)
        if source == "main":
            lua.execute(RIFT_MOCK)
            for name in ("Core.lua", "AddonMessages.lua", "NativeChatProbe.lua",
                         "ConsoleMirror.lua", "HostIngress.lua", "Main.lua"):
                module = (ADDON / name).read_text(encoding="utf-8")
                lua.execute("assert(loadstring("+_lua_quote(module)+
                            "))({identifier='RiftChatModern',version='0.2.20'}, {})")
        else:
            lua.execute((ADDON / source).read_text(encoding="utf-8"))
        lua.execute(script)

    def test_older_page_shows_only_remaining_messages_without_overlap(self):
        self.run_lua("main", r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
assert(RiftChatModernAPI.Show())
for i=1,16 do assert(RiftChatModernAPI.Publish("dev","line-"..i,"RR2")) end
assert(RiftChatModernAPI.GetStatus().historyCount==17)
triggerFrame(frames.RCMPageUp,Event.UI.Input.Mouse.Left.Click)
-- Seventeen records with a thirteen-row page -> exactly four older rows.
assert(frames.RCMStatus.text:find("showing 1–4",1,true))
assert(frames.RCMLine1.messageId==nil or frames.RCMLine1.visible)
assert(frames.RCMLineText5.text=="")
triggerFrame(frames.RCMPageDown,Event.UI.Input.Mouse.Left.Click)
assert(frames.RCMStatus.text:find("showing 5–17",1,true))
''')

    def test_relayout_replaces_anchor_instead_of_adding_conflicts(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(RIFT_MOCK)
        # RIFT SetPoint creates persistent anchors; emulate a stricter frame API.
        lua.execute(r'''
local proto=getmetatable(UIParent).__index
local original=proto.SetPoint
function proto:ClearAll()
    self.pointAnchors=0
    self.width=nil
    self.height=nil
end
function proto:SetPoint(...)
    assert((self.pointAnchors or 0)==0,"anchor conflict")
    self.pointAnchors=1
    original(self,...)
end
''')
        for name in ("Core.lua", "AddonMessages.lua", "NativeChatProbe.lua",
                     "ConsoleMirror.lua", "HostIngress.lua", "Main.lua"):
            src = (ADDON / name).read_text(encoding="utf-8")
            lua.execute("assert(loadstring("+_lua_quote(src)+
                        "))({identifier='RiftChatModern',version='0.2.20'}, {})")
        lua.execute(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
assert(api.SetWindowSize(1080,820))
assert(api.SetWindowSize(720,525))
assert(api.SetWindowSize(930,690))
local p=frames.RiftChatModernWindow
assert(p.width==930 and p.height==690)
assert(frames.RCMLine1.pointAnchors==1)
assert(frames.RCMInput.pointAnchors==1)
''')

    def test_export_rejects_nan_inf_and_fractional_limits(self):
        self.run_lua("Core.lua", r'''
local c=assert(RiftChatModernCore.new({schemaVersion=1,history={}}))
assert(c:publish("dev","message","RR2",1))
for _,value in ipairs({0/0,math.huge,-math.huge,512.5}) do
    local output,reason=c:exportText(nil,nil,value)
    assert(output==nil and reason=="invalid_limit")
end
assert(c:exportText(nil,nil,512))
''')

    def test_duplicate_saved_message_ids_are_rejected(self):
        self.run_lua("Core.lua", r'''
local row={id=5,kind="dev",source="RR2",text="entry",at=5}
local other={id=5,kind="dev",source="RR2",text="duplicate",at=6}
local model,why=RiftChatModernCore.new({schemaVersion=1,history={row,other},nextId=6})
assert(model==nil and why=="invalid_saved_history")
''')

    def test_extension_response_truncation_preserves_utf8(self):
        self.run_lua("Core.lua", r'''
local c=assert(RiftChatModernCore.new({schemaVersion=1,history={}}))
local euro=string.char(226,130,172)
assert(c:registerCommand("unicode",function() return string.rep(euro,171) end))
assert(c:execute(":unicode",5))
local value=c:getHistory("dev","",1,0)[1].text
assert(#value<=512)
assert(#value%3==0)
for i=1,#value,3 do assert(value:sub(i,i+2)==euro) end
''')

    def test_channel_receiver_callback_error_not_falsely_counted_as_received(self):
        self.run_lua("AddonMessages.lua", r'''
local b=assert(RiftChatModernAddonMessages.new(
    function() return true end, function() return true end,
    function() error("storage failed") end, function() end, function() return 1 end))
assert(b:enable())
local yes,why=b:receive("Atank","send",nil,"RCMDevV1","event")
assert(yes==nil and why=="receive_storage_failed")
assert(b:status().received==0)
assert(b:status().invalid==0 and b:status().receiveFailed==1)
''')

    def test_mirror_failed_callback_preserves_original_returns(self):
        self.run_lua("ConsoleMirror.lua", r'''
local native=0
local api={Display=function(...)
    native=native+1
    return true,nil,77
end}
local mirror=assert(RiftChatModernConsoleMirror.new(api,function()
    error("receiver unavailable")
end))
assert(mirror:enable())
local a,b,c=api.Display("general",true,"some output",false)
assert(a==true and b==nil and c==77)
assert(native==1 and mirror:status().captured==0 and mirror:status().rejected==1)
''')

    def test_unicode_game_events_do_not_split_codepoints(self):
        self.run_lua("main", r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
local euro=string.char(226,130,172)
fireMessage(Event.Chat.Npc,{fromName=string.rep(euro,14),
    message=string.rep(euro,171)})
local npc=api.GetHistory("npc","",1,0)[1]
assert(#npc.source==39 and #npc.source%3==0)
assert(#npc.text==510 and #npc.text%3==0)
fireMessage(Event.Chat.Notify,{message=string.rep(euro,171)})
local msg=api.GetHistory("system","",1,0)[1]
assert(#msg.text==510 and #msg.text%3==0)
''')

    def test_empty_npc_sender_does_not_drop_event(self):
        self.run_lua("main", r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
fireMessage(Event.Chat.Npc,{fromName="",message="Important NPC event"})
local rows,total=RiftChatModernAPI.GetHistory("npc","",10,0)
assert(total==1 and rows[1].source=="NPC" and rows[1].text=="Important NPC event")
''')

    def test_html_mirror_truncates_without_corrupting_utf8(self):
        self.run_lua("ConsoleMirror.lua", r'''
local api={Display=function() return true end}
local content
local mirror=assert(RiftChatModernConsoleMirror.new(api,
    function(line) content=line;return true end))
assert(mirror:enable())
local euro=string.char(226,130,172)
api.Display("general",true,string.rep(euro,171),false)
assert(type(content)=="string" and #content<=512)
local body=content:gsub("%.%.%.$","")
assert(#body%3==0)
for i=1,#body,3 do assert(body:sub(i,i+2)==euro) end
''')

    def test_invalid_saved_search_is_ignored_without_history_reset(self):
        self.run_lua("Core.lua", r'''
local saved={schemaVersion=1,history={},search="evil"..string.char(1)}
local c=assert(RiftChatModernCore.new(saved))
assert(c.search=="")
assert(c:publish("dev","okay","RR2",2))
assert(c:status().historyCount==1)
''')

    def test_resize_does_not_reset_history_and_restores_small_viewport(self):
        self.run_lua("main", r'''
RiftChatModernSaved={schemaVersion=1,history={},
    ui={x=1000,y=700,w=1200,h=900}}
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
local p=frames.RiftChatModernWindow
assert(p.x+p.width<=UIParent:GetWidth())
assert(p.y+p.height<=UIParent:GetHeight())
UIParent:SetWidth(600)
UIParent:SetHeight(400)
fire(Event.System.Update.Begin)
assert(p.x+p.width<=600)
assert(p.y+p.height<=400)
assert(api.GetStatus().windowWidth<=600)
assert(RiftChatModernSaved.schemaVersion==2)
assert(api.GetStatus().historyCount>=1)
''')

if __name__ == "__main__":
    unittest.main()
