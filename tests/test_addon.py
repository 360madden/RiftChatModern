"""RiftChatModern addon contracts, including Lua 5.1 runtime and fake RIFT UI."""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]
ADDON=ROOT/"addon"/"RiftChatModern"
MANIFEST=ADDON/"RiftAddon.toc"

try:
    from lupa.lua51 import LuaRuntime
except ImportError:
    LuaRuntime=None

RIFT_MOCK = r'''
frames, handlers, slash, displays = {}, {}, {}, {}
copied, now, mx, my, held = nil, 1700, 100, 100, false
Event = {
    Addon={SavedVariables={Load={End={}}},Load={End={}}},
    System={Update={Begin={}}},
    Chat={Notify={},Npc={}},
    UI={Input={Mouse={Left={Click={},Down={},Up={},Upoutside={}},
            Cursor={In={},Out={}}}},Textfield={Change={}}},
}
local function attach(store,event,fn)
    store[event]=store[event] or {}
    table.insert(store[event],fn)
end
function fire(event,...)
    for _,fn in ipairs(handlers[event] or {}) do fn(event,...) end
end
local f={}; f.__index=f
function f:SetPoint(where,parent,point,x,y)
    self.x=(parent.x or 0)+(x or 0)
    self.y=(parent.y or 0)+(y or 0)
end
function f:GetLeft() return self.x end
function f:GetTop() return self.y end
function f:SetWidth(v) self.width=v end
function f:SetHeight(v) self.height=v end
function f:GetWidth() return self.width end
function f:GetHeight() return self.height end
function f:SetBackgroundColor(...) self.bg={...} end
function f:SetFontColor(...) self.fg={...} end
function f:SetFontSize(v) self.fontSize=v end
function f:SetWordwrap(v) self.wrap=v end
function f:SetMouseMasking(v) self.mouseMask=v end
function f:SetVisible(v) self.visible=v end
function f:GetVisible() return self.visible end
function f:SetText(v) self.text=v end
function f:GetText() return self.text end
function f:SetKeyFocus(v) self.focus=v end
function f:GetKeyFocus() return self.focus end
function f:EventAttach(e,fn)
    self.localEvents[e]=self.localEvents[e] or {}
    table.insert(self.localEvents[e],fn)
end
local function newFrame(name)
    assert(not frames[name],"duplicate frame: "..name)
    local z=setmetatable({x=0,y=0,visible=true,localEvents={},Event={}},f)
    frames[name]=z
    return z
end
UIParent=newFrame("UIParent")
UIParent:SetWidth(1920);UIParent:SetHeight(1080)
UI={
    CreateContext=function(name) return newFrame(name) end,
    CreateFrame=function(kind,name,parent)
        assert(parent~=nil)
        local obj=newFrame(name)
        obj.kind=kind
        return obj
    end
}
Inspect={
    Time={Server=function() return now end},
    Mouse=function() return {x=mx,y=my,Left=held} end
}
Command={
    Event={Attach=function(event,fn) attach(handlers,event,fn) end},
    Slash={Register=function(name) slash[name]={};return slash[name] end},
    Console={Display=function(channel,flag,msg,html) displays[#displays+1]=msg end},
    CopyToClipboard=function(value) copied=value return true end
}
function triggerFrame(frame,event)
    for _,fn in ipairs(frame.localEvents[event] or {}) do fn(event) end
end
'''

class CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if LuaRuntime is None: raise unittest.SkipTest("Requires Lua 5.1 via Lupa")
        cls.core=(ADDON/"Core.lua").read_text(encoding="utf-8")

    def run_lua(self,body):
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute(self.core)
        lua.execute(body)

    def test_bounded_history_filter_search_and_copy_isolation(self):
        self.run_lua(r'''
local c=assert(RiftChatModernCore.new({schemaVersion=1,history={}}))
for i=1,250 do assert(c:publish("addons","entry-"..i,"RR2",1700+i)) end
assert(c:status().historyCount==240)
local first=assert(c:getHistory("all","",240,0))
assert(first[1].id==11 and first[#first].id==250)
first[1].text="tamper"
assert(c:getHistory("all","",240,0)[1].text~="tamper")
local ok=assert(c:setFilter("addons"))
assert(c:setSearch("entry-249"))
local rows,count=c:getHistory(nil,nil,10,0)
assert(count==1 and rows[1].text=="entry-249")
local export=assert(c:exportText(nil,nil,1200))
assert(export:find("entry-249",1,true))
assert(not export:find("entry-248",1,true))
assert(c:setSearch(""))
assert(c:setFilter("all"))
assert(c:clear())
assert(c:status().historyCount==0)
''')

    def test_command_registry_and_social_send_does_not_fake_success(self):
        self.run_lua(r'''
local c=assert(RiftChatModernCore.new({schemaVersion=1,history={}}))
assert(c:registerCommand("rr2",function(arg) return "status "..arg end))
assert(not c:registerCommand("rr2",function() end))
assert(c:execute(":rr2 health",1700))
assert(c:getHistory("dev","",10,0)[1].text=="status health")
local ok,err=c:execute("/rptlab status",1700)
assert(not ok and err=="native_send_unavailable")
assert(c:status().nativeSocialSendAvailable==false)
assert(c:status().nativePlayerChatCaptureAvailable==false)
assert(c:execute(":help",1701))
local count=0
assert(c:subscribe("probe",function(r) count=count+1;r.text="changed" end))
local row=c:publish("npc","hello","Narrator",1702)
assert(row.text=="hello" and count==1)
assert(c:getHistory("npc","",10,0)[1].text=="hello")
''')

    def test_history_storage_round_trip_and_paging(self):
        self.run_lua(r'''
local saved={schemaVersion=1,history={}}
local a=assert(RiftChatModernCore.new(saved))
for i=1,31 do assert(a:publish("system","notice"..i,"Game",2000+i)) end
local first,total=a:getHistory("all","",10,0)
assert(total==31 and first[#first].text=="notice31")
local previous=a:getHistory("all","",10,10)
assert(previous[#previous].text=="notice21")
local b=assert(RiftChatModernCore.new(saved))
assert(b:getHistory("all","",1,0)[1].text=="notice31")
assert(b:publish("npc","after reload","Keeper",2040).id==32)
assert(#saved.history==32)
''')

    def test_text_limits_draft_and_export_bound(self):
        self.run_lua(r'''
local a=assert(RiftChatModernCore.new({schemaVersion=1,history={}}))
local ok,err=a:execute("hi",2000)
assert(not ok and err=="native_send_unavailable")
assert(a:status().historyCount==0)
assert(not a:publish("dev",string.rep("X",513),"Test",2000))
assert(a:publish("dev",string.rep("X",500),"Test",2000))
local output=assert(a:exportText("all","",1024))
assert(#output<=1024)
assert(output:find("Truncated",1,true) or #output<1024)
assert(not a:exportText("all","",200))
''')

    def test_sequence_guard_clear_and_reentrant_listener(self):
        self.run_lua(r'''
local saved={schemaVersion=1,history={{id=12,at=1700,
    kind="dev",source="RR2",text="old"}}}
assert(not RiftChatModernCore.new({schemaVersion=1,
    history=saved.history,nextId=12}))
local c=assert(RiftChatModernCore.new(saved))
assert(c:publish("dev","next","RR2",1701).id==13)
local calls=0
assert(c:subscribe("reentrant",function(row)
    calls=calls+1
    c:publish("dev","nested","RRE",1702)
end))
assert(c:publish("dev","outer","RR2",1702))
assert(calls==1)
assert(c:status().historyCount==4)
assert(c:execute(":clear",1703))
assert(c:status().historyCount==0)
''')

    def test_invalid_saved_data_and_bad_commands_rejected(self):
        self.run_lua(r'''
assert(not RiftChatModernCore.new({schemaVersion=2,history={}}))
assert(not RiftChatModernCore.new({schemaVersion=1,history={[2]={
    id=2,at=1700,kind="dev",source="a",text="b"}}}))
local c=assert(RiftChatModernCore.new({schemaVersion=1,history={}}))
assert(not c:publish("unknown","data","RR2",1700))
assert(not c:publish("addons","","RR2",1700))
assert(not c:publish("addons","data","RR2",0/0))
assert(not c:setFilter("nonexistent"))
assert(not c:setSearch(string.rep("A",61)))
assert(not c:registerCommand("clear",function() end))
local ok,err=c:execute(":rr2 status",1700)
assert(not ok and err=="unknown_local_command")
''')

class AddonRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if LuaRuntime is None: raise unittest.SkipTest("Requires Lua 5.1 via Lupa")
        cls.core=(ADDON/"Core.lua").read_text(encoding="utf-8")
        cls.main=(ADDON/"Main.lua").read_text(encoding="utf-8")

    def run_lua(self,scenario):
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute(RIFT_MOCK)
        lua.execute(self.core)
        lua.execute('assert(loadstring('+_lua_quote(self.main)+'))({identifier="RiftChatModern",version="0.1.1"})')
        lua.execute(scenario)

    def test_startup_ui_theme_drag_focus_and_version(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
assert(#displays==1 and displays[1]:find("v0.1.1",1,true))
local api=RiftChatModernAPI
assert(api.interfaceVersion==1 and api.GetStatus().ready)
assert(api.GetStatus().historyCount==1)
local active=assert(api.Show())
assert(frames.RiftChatModernWindow.visible)
assert(frames.RiftChatModernWindow.width==760)
assert(frames.RiftChatModernWindow.height==618)
assert(frames.RCMVersion.text=="v0.1.1")
assert(frames.RCMInput.kind=="RiftTextfield")
assert(api.FocusEditor())
assert(api.GetStatus().editorFocused==true)
assert(api.Hide())
assert(api.GetStatus().editorFocused==false or not api.GetStatus().windowVisible)
''')

    def test_npc_notification_publish_filter_copy_and_external_commands(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
fire(Event.Chat.Npc,{message="Beware of the storm!",fromName="Guardian"})
fire(Event.Chat.Notify,{message="Event in progress"})
assert(api.Publish("addons","Atank position 123","RR2"))
assert(api.GetStatus().historyCount==4)
assert(api.RegisterCommand("rr2",function(args) return "RR2 says "..args end))
assert(api.Submit(":rr2 status"))
assert(api.GetStatus().historyCount==5)
assert(not api.Submit("/say hello"))
local all,count=api.GetHistory("all","",20,0)
assert(count==5)
all[1].text="tampered"
assert(api.GetHistory("all","",20,0)[1].text~="tampered")
assert(api.Show())
local out=assert(api.Copy())
assert(copied:find("Beware of the storm",1,true))
assert(copied:find("Atank position",1,true))
assert(copied:find("RR2 says status",1,true))
fire(slash.rcm,"tab addons")
assert(api.GetStatus().filter=="addons")
fire(slash.rcm,"find Atank")
assert(api.GetStatus().search=="Atank")
assert(api.Copy())
assert(copied:find("Atank position",1,true))
assert(not copied:find("Beware of the storm",1,true))
''')

    def test_drag_and_composer_enter_uses_local_dispatch(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
assert(RiftChatModernAPI.Show())
local window=frames.RiftChatModernWindow
local originalX,originalY=window:GetLeft(),window:GetTop()
mx,my=originalX+40,originalY+20
held=true
triggerFrame(frames.RCMDragHandle,Event.UI.Input.Mouse.Left.Down)
mx,my=mx+75,my+41
fire(Event.System.Update.Begin)
assert(window:GetLeft()==originalX+75)
held=false
fire(Event.System.Update.Begin)
assert(RiftChatModernSaved.ui.x==originalX+75)
assert(RiftChatModernSaved.ui.y==originalY+41)
frames.RCMInput:SetText(":echo working")
frames.RCMInput.Event:KeyDown("enter")
assert(frames.RCMInput:GetText()=="")
assert(RiftChatModernAPI.GetHistory("dev","",10,0)[1].text=="working")
frames.RCMInput:SetText("/say this must stay a draft")
frames.RCMInput.Event:KeyDown("enter")
assert(frames.RCMInput:GetText()=="/say this must stay a draft")
''')

    def test_rpt_cross_addon_adapter_uses_api_not_native_chat(self):
        self.run_lua(r'''
local armed, stopped, marked=0,0,nil
RPTTravelLabAPI={
    GetStatus=function() return {version="0.3.2",ready=true,recording=false,
        trialCount=5,sampleCount=0} end,
    Arm=function() armed=armed+1 return true end,
    Stop=function() stopped=stopped+1 return true end,
    Mark=function(note) marked=note return true end,
    GetLastTrial=function() return {id="sample",result={status="settled"},
        samples={{}},events={{},{}}} end
}
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Submit(":rpt status"))
assert(api.Submit(":rpt arm"))
assert(api.Submit(":rpt mark clicked Porticulum"))
assert(api.Submit(":rpt last"))
assert(api.Submit(":rpt stop"))
assert(armed==1 and stopped==1 and marked=="clicked Porticulum")
local records=api.GetHistory("dev","",20,0)
assert(#records==5)
assert(records[2].text:find("accepted by addon API",1,true))
assert(records[1].text:find("0.3.2",1,true))
assert(api.GetStatus().commandCount>=1)
RPTTravelLabAPI=nil
assert(api.Submit(":rpt status"))
assert(api.GetHistory("dev","",1,0)[1].text=="RPT Travel Lab is not loaded.")
''')

    def test_saved_records_are_preserved_and_wrong_addon_event_ignored(self):
        self.run_lua(r'''
RiftChatModernSaved={schemaVersion=1,history={{id=3,kind="dev",
    at=1700,source="Older",text="retained"}},nextId=4}
fire(Event.Addon.SavedVariables.Load.End,"Other")
assert(RiftChatModernAPI.GetStatus().ready==false)
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
assert(RiftChatModernSaved.history[1].text=="retained")
assert(RiftChatModernAPI.GetStatus().historyCount==2)
assert(RiftChatModernSaved.history[2].id==4)
''')

def _lua_quote(text):
    # Literal quoted Lua string, escape newlines and non-ASCII for tests.
    result='"'
    for b in text.encode("utf-8"):
        if b in (34,92): result+="\\"+chr(b)
        elif b in (10,13): result+="\\n" if b==10 else "\\r"
        elif b<32 or b>=127: result+=f"\\{b:03d}"
        else: result+=chr(b)
    return result+'"'

class ManifestTests(unittest.TestCase):
    def test_loader_contract(self):
        text=MANIFEST.read_text(encoding="utf-8")
        for key,value in {"Identifier":"RiftChatModern","Version":"0.1.1","Environment":"4.3"}.items():
            self.assertRegex(text,rf'(?m)^{key} = "{re.escape(value)}"$')
        self.assertRegex(text,r'(?m)^Email = "placeholder@example.com"')
        self.assertIn('"Core.lua", "Main.lua"',text)
        self.assertIn('RiftChatModernSaved = "character"',text)

if __name__=="__main__":
    unittest.main()
