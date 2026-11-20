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
accepts, sends = {}, {}
Event = {
    Addon={SavedVariables={Load={End={}}},Load={End={}}},
    System={Update={Begin={}}},
    Chat={Notify={},Npc={}},
    Message={Receive={}},
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
function fireMessage(event,...)
    for _,fn in ipairs(handlers[event] or {}) do fn(...) end
end
local f={}; f.__index=f
function f:ClearAll()
    self.x=0;self.y=0
    self.width=nil;self.height=nil
    self.anchorParent=nil
end
function f:SetPoint(where,parent,point,x,y)
    -- Keep parent-relative anchors for layout tests after moving/resizing parents.
    self.anchorParent=parent
    self.anchorX=x or 0
    self.anchorY=y or 0
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
    Time={Server=function() return now end,Real=function() return now end},
    Mouse=function() return {x=mx,y=my,Left=held} end
}
Command={
    Event={Attach=function(event,fn) attach(handlers,event,fn) end},
    Slash={Register=function(name) slash[name]={};return slash[name] end},
    Console={Display=function(channel,flag,msg,html) displays[#displays+1]=msg end},
    CopyToClipboard=function(value) copied=value return true end,
    Message={
        Accept=function(kind,id) accepts[#accepts+1]={kind=kind,id=id}; return true end,
        Send=function(target,id,data,callback)
            sends[#sends+1]={target=target,id=id,data=data,callback=callback}
            return true
        end
    }
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
        lua.execute((ADDON / "AddonMessages.lua").read_text(encoding="utf-8"))
        lua.execute((ADDON / "NativeChatProbe.lua").read_text(encoding="utf-8"))
        lua.execute((ADDON / "ConsoleMirror.lua").read_text(encoding="utf-8"))
        lua.execute((ADDON / "HostIngress.lua").read_text(encoding="utf-8"))
        lua.execute('assert(loadstring('+_lua_quote(self.main)+'))({identifier="RiftChatModern",version="0.2.9"})')
        lua.execute(scenario)

    def test_startup_ui_theme_drag_focus_and_version(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
assert(#displays==1 and displays[1]:find("v0.2.9",1,true))
local api=RiftChatModernAPI
assert(api.interfaceVersion==1 and api.GetStatus().ready)
assert(api.GetStatus().historyCount==1)
local active=assert(api.Show())
assert(frames.RiftChatModernWindow.visible)
assert(frames.RiftChatModernWindow.width==760)
assert(frames.RiftChatModernWindow.height==618)
assert(frames.RCMVersion.text=="v0.2.9")
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


    def test_addon_data_send_receive_with_receipts(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.GetStatus().addonTransportReady==true)
assert(#accepts==1 and accepts[1].kind=="send" and accepts[1].id=="RCMDevV1")
local first=assert(api.SendAddon("Atank","RR2 is active"))
assert(first.status=="api_submitted" and first.delivery_verified==false)
assert(#sends==1 and sends[1].id=="RCMDevV1")
assert(api.GetAddonTransportStatus().pending==true)
local refused,reason=api.SendAddon("Atank","cannot overlap")
assert(refused==nil and reason=="send_pending")
fireMessage(Event.Message.Receive,"Atank","send",nil,"OTHER","unrelated")
assert(api.GetAddonTransportStatus().received==0)
fireMessage(Event.Message.Receive,"Atank","send",nil,"RCMDevV1","RPT observation ready")
assert(api.GetAddonTransportStatus().received==1)
local incoming=api.GetHistory("addons","",5,0)
assert(#incoming==1 and incoming[1].text=="RPT observation ready")
-- Identifier does not become an executable command, even for colon-prefixed text.
fireMessage(Event.Message.Receive,"Atank","send",nil,"RCMDevV1",":rpt arm")
assert(api.GetHistory("addons","",1,0)[1].text==":rpt arm")
sends[1].callback(false,"accepted for queue")
assert(api.GetAddonTransportStatus().accepted==1)
assert(api.GetAddonTransportStatus().pending==false)
now=now+2.2
assert(api.Submit(":addon Atank probe reply"))
assert(#sends==2 and sends[2].data=="probe reply")
sends[2].callback(true,"rejected")
assert(api.GetAddonTransportStatus().rejected==1)
assert(api.GetStatus().nativeSocialSendAvailable==false)
''')

    def test_long_peer_name_is_not_lost_in_message_history(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local from=string.rep("A",55)
fireMessage(Event.Message.Receive,from,"send",nil,"RCMDevV1","hello")
local row=RiftChatModernAPI.GetHistory("addons","",1,0)[1]
assert(row.source==from:sub(1,40))
assert(row.text==from..": hello")
assert(RiftChatModernAPI.GetAddonTransportStatus().received==1)
''')

    def test_transport_unavailable_keeps_local_console_working(self):
        self.run_lua(r'''
Command.Message=nil
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.GetStatus().ready)
assert(api.GetStatus().addonTransportReady==false)
local result,why=api.SendAddon("Atank","test")
assert(result==nil and why=="transport_unavailable")
assert(api.Submit(":addon Atank message"))
assert(api.GetHistory("dev","",1,0)[1].text:find("unavailable",1,true))
assert(api.Submit(":rpt status"))
''')

    def test_native_console_probe_is_readonly_not_social_capture(self):
        self.run_lua(r'''
UI.Native={Console1={
    GetVisible=function() return true end,
    GetLoaded=function() return true end,
    GetKeyFocus=function() return true end,
    GetText=function() error("Native transcript must not be accessed") end
}}
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
local probe=api.GetNativeConsoles()
assert(probe.windowCount==1 and probe.visibleCount==1)
assert(probe.focusCount==1)
assert(probe.nativeTranscriptReadable==false)
assert(api.Submit(":native"))
local response=api.GetHistory("dev","",1,0)[1]
assert(response.text:find("Console subscriptions are metadata",1,true))
assert(api.GetStatus().nativePlayerChatCaptureAvailable==false)
''')

    def test_both_chat_event_callback_shapes_and_grouped_notifications(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
-- RIFT API docs document one event-info argument; some addons use event+info.
fireMessage(Event.Chat.Npc,{message="Direct NPC",fromName="Merchant"})
fire(Event.Chat.Npc,{message="Attached NPC",fromName="Keeper"})
fireMessage(Event.Chat.Notify,{message="Direct warning"})
fire(Event.Chat.Notify,{
    ["unit-A"]={message="A warning"},
    ["unit-B"]="B warning",
    ["unit-C"]=true
})
local npc,count=api.GetHistory("npc","",10,0)
assert(count==2 and npc[1].source=="Merchant" and npc[2].source=="Keeper")
local sys,total=api.GetHistory("system","",10,0)
assert(total==4) -- startup + direct notification + 2 grouped notifications
local byText={}
for _,row in ipairs(sys) do byText[row.text]=row.source end
assert(byText["Direct warning"]=="Game alert")
assert(byText["A warning"]=="unit-A")
assert(byText["B warning"]=="unit-B")
assert(not byText["true"])
''')

    def test_optional_addon_console_mirror_captures_other_repo_output(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
assert(api.GetConsoleMirrorStatus().enabled==false)
assert(frames.RCMMirrorLabel.text=="MIRROR OFF")
assert(api.Submit(":mirror on"))
assert(api.GetConsoleMirrorStatus().enabled==true)
assert(frames.RCMMirrorLabel.text=="MIRROR ON")
Command.Console.Display("general",true,"RRECollector snapshot ready",false)
local lines,count=api.GetHistory("addons","",12,0)
assert(count==1 and lines[1].text=="RRECollector snapshot ready")
assert(lines[1].source=="Console:general")
assert(api.GetConsoleMirrorStatus().captured==1)
-- Own notices are still sent to the native game console, never recursively mirrored.
fire(slash.rcm,"status")
assert(api.GetConsoleMirrorStatus().captured==1)
-- The mirror is disabled through the visible button as well as through :mirror.
triggerFrame(frames.RCMMirror,Event.UI.Input.Mouse.Left.Click)
assert(api.GetConsoleMirrorStatus().enabled==false)
assert(frames.RCMMirrorLabel.text=="MIRROR OFF")
Command.Console.Display("general",true,"after mirror stopped",false)
local records,total=api.GetHistory("addons","",10,0)
assert(total==1)
assert(api.GetStatus().nativePlayerChatCaptureAvailable==false)
''')

    def test_native_console_channel_summary_and_copy(self):
        self.run_lua(r'''
Inspect.Console={
    List=function() return {"v001","v002"} end,
    Detail=function(id)
        if id=="v001" then return {id=id,name="General",
            say=true,tell=true,party=false,system=true,npc=true,
            raidWarning=true,lootMoney=true,
            channel={["World@Deepwood"]=true,["LookingForGroup"]=true,
                ["Trade"]=false}} end
        return {id=id,name="Guild",guild=true,officer=false}
    end
}
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
local state=api.GetNativeConsoles()
assert(state.consoleListReady and state.consoleCount==2)
assert(state.consoles[1].channels.say==true)
assert(state.nativeTranscriptReadable==false)
assert(api.Submit(":native channels"))
local line=api.GetHistory("dev","",1,0)[1].text
assert(line:find("General: say, tell",1,true))
assert(line:find("raidWarning",1,true))
assert(line:find("public: LookingForGroup, World@Deepwood",1,true))
assert(line:find("Guild: guild",1,true))
assert(api.Submit(":native copy"))
assert(copied:find("RIFT native console subscriptions",1,true))
assert(copied:find("Guild: guild",1,true))
assert(copied:find("public: LookingForGroup, World@Deepwood",1,true))
assert(not copied:find("player chat transcript",1,true))
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
        for key,value in {"Identifier":"RiftChatModern","Version":"0.2.9","Environment":"4.3"}.items():
            self.assertRegex(text,rf'(?m)^{key} = "{re.escape(value)}"$')
        self.assertRegex(text,r'(?m)^Email = "placeholder@example.com"')
        self.assertIn('"Core.lua", "AddonMessages.lua", "NativeChatProbe.lua", "ConsoleMirror.lua", "HostIngress.lua", "Main.lua"',text)
        self.assertIn('RiftChatModernSaved = "character"',text)

if __name__=="__main__":
    unittest.main()
