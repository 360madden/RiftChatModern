-- RiftChatModern / Main.lua -- compact, standalone RIFT addon chat/diagnostic console.
-- Native player say/tell/guild transmit and full native chat interception are NOT
-- exposed by the verified addon APIs. This UI never pretends to send those.
local info = ...
local ADDON, VERSION = "RiftChatModern", (type(info)=="table" and info.version) or "0.1.0"
local Core = _G.RiftChatModernCore
local W,H,LINES=750,558,13
local C = {
    bg={0.065,0.080,0.11,0.98}, header={0.090,0.111,0.15,1},
    card={0.092,0.117,0.15,1}, alt={0.081,0.102,0.13,1},
    border={0.16,0.21,0.27,1}, control={0.14,0.19,0.25,1},
    hover={0.19,0.27,0.34,1}, accent={0.12,0.67,0.75,1},
    text={0.90,0.94,0.97,1}, muted={0.61,0.72,0.79,1},
    warning={1.0,0.73,0.43,1}
}
local model,panel,editor,searchField,statusField,rows,tabLabels,drag
local context,searchHint,visibleOffset= nil,nil,0
local initialized=false
local function finite(v)
    return type(v)=="number" and v==v and v>-math.huge and v<math.huge
end
local function rgba(frame,color)
    frame:SetBackgroundColor(color[1],color[2],color[3],color[4] or 1)
end
local function ink(frame,color)
    frame:SetFontColor(color[1],color[2],color[3],color[4] or 1)
end
local function clock()
    local ok,n=pcall(Inspect.Time.Server)
    if ok and finite(n) and n>=0 then return n end
    return 0
end
local function notice(msg)
    local line="RiftChatModern v"..VERSION.." | "..msg
    if Command and Command.Console and type(Command.Console.Display)=="function" then
        local html='<font color="#3BC4D0">'..line:gsub("&","&amp;"):gsub("<","&lt;"):gsub(">","&gt;")..'</font>'
        local ok=pcall(Command.Console.Display,"general",true,html,true)
        if ok then return end
    end
    if print then print(line) end
end
local function notifyUi(text)
    if statusField then statusField:SetText(text) end
end
local function mouse()
    if not Inspect or type(Inspect.Mouse)~="function" then return nil end
    local ok,value=pcall(Inspect.Mouse)
    if ok and type(value)=="table" and finite(value.x) and finite(value.y) then
        return value
    end
end
local function shift(x,y,save)
    if not panel or not finite(x) or not finite(y) then return end
    local vw,vh=UIParent:GetWidth(),UIParent:GetHeight()
    if not finite(vw) or not finite(vh) then return end
    x=math.max(0,math.min(vw-W,math.floor(x+0.5)))
    y=math.max(0,math.min(vh-H,math.floor(y+0.5)))
    panel:SetPoint("TOPLEFT",UIParent,"TOPLEFT",x,y)
    if save and model then
        model.saved.ui={x=x,y=y}
    end
end
local function startDrag()
    local m=mouse()
    if m and panel then drag={dx=m.x-panel:GetLeft(),dy=m.y-panel:GetTop()} end
end
local function dragMove(save)
    if not drag then return end
    local m=mouse()
    if m then shift(m.x-drag.dx,m.y-drag.dy,save) end
end
local function stopDrag()
    if drag then dragMove(true);drag=nil end
end
local function frame(name,parent,x,y,w,h,color)
    local f=UI.CreateFrame("Frame","RCM"..name,parent)
    f:SetPoint("TOPLEFT",parent,"TOPLEFT",x,y)
    f:SetWidth(w);f:SetHeight(h)
    if color then rgba(f,color) end
    return f
end
local function text(name,parent,value,x,y,w,h,size,color,bold)
    local f=UI.CreateFrame("Text","RCM"..name,parent)
    f:SetPoint("TOPLEFT",parent,"TOPLEFT",x,y)
    f:SetWidth(w);f:SetHeight(h)
    f:SetFontSize(size or 14)
    f:SetWordwrap(false)
    f:SetText(value or "")
    ink(f,color or C.text)
    return f
end
local function button(name,value,parent,x,y,w,h,fn,strong)
    local control=frame(name,parent,x,y,w,h,strong and C.accent or C.control)
    control:SetMouseMasking("full")
    local caption=text(name.."Label",control,value,8,math.max(1,(h-19)/2),w-16,20,14,
        strong and C.bg or C.text)
    control:EventAttach(Event.UI.Input.Mouse.Left.Click,function()
        if type(fn)=="function" then fn() end
    end,ADDON.." "..name.." clicked")
    if Event.UI.Input.Mouse.Cursor and Event.UI.Input.Mouse.Cursor.In then
        control:EventAttach(Event.UI.Input.Mouse.Cursor.In,function()
            rgba(control,strong and C.accent or C.hover)
        end,ADDON.." "..name.." hover")
    end
    if Event.UI.Input.Mouse.Cursor and Event.UI.Input.Mouse.Cursor.Out then
        control:EventAttach(Event.UI.Input.Mouse.Cursor.Out,function()
            rgba(control,strong and C.accent or C.control)
        end,ADDON.." "..name.." leave")
    end
    return control,caption
end
local function focusEditor()
    if not editor or not panel or not panel:GetVisible() then
        return nil,"editor_hidden"
    end
    if type(editor.SetKeyFocus)~="function" or type(editor.GetKeyFocus)~="function" then
        return nil,"focus_api_unavailable"
    end
    local ok=pcall(editor.SetKeyFocus,editor,true)
    if not ok then return nil,"focus_request_failed" end
    local good,value=pcall(editor.GetKeyFocus,editor)
    if good and value==true then
        notifyUi("Editor focused • local commands start with :")
        return true
    end
    return nil,"focus_not_acquired"
end
local function cutUtf8(str,maximum)
    if #str<=maximum then return str end
    local i=maximum
    while i>1 do
        local byte=str:byte(i+1)
        if not byte or byte<128 or byte>=192 then break end
        i=i-1
    end
    return str:sub(1,i).."..."
end
local function render()
    if not model or not panel then return end
    local selection,total=model:getHistory(model.filter,model.search,LINES,visibleOffset)
    for i=1,LINES do
        local r=selection[i]
        if r then
            local ts="--:--"
            if os and os.date then
                local ok,value=pcall(os.date,"%H:%M",math.floor(r.at))
                if ok and type(value)=="string" then ts=value end
            end
            local msg=string.format("%s  %-7s  %-14s %s",ts,r.kind:upper(),
                cutUtf8(r.source,14),r.text)
            rows[i].entry:SetText(cutUtf8(msg,118))
            ink(rows[i].entry,r.kind=="dev" and C.accent or
                r.kind=="system" and C.warning or C.text)
        else rows[i].entry:SetText("") end
    end
    local count=math.min(total,visibleOffset+LINES)
    local first=math.max(0,count-math.min(LINES,total-visibleOffset)+1)
    notifyUi(string.format("%d messages  •  showing %d–%d  •  %s  •  native social chat remains separate",
        total,first,count,model.filter))
    for key,label in pairs(tabLabels or {}) do
        ink(label,key==model.filter and C.accent or C.muted)
    end
end
local function copyHistory()
    if not model then return nil,"not_ready" end
    if not Command or type(Command.CopyToClipboard)~="function" then
        notifyUi("Clipboard unavailable in this client");return nil,"clipboard_unavailable"
    end
    local out,err=model:exportText(nil,nil,48000)
    if not out then return nil,err end
    local ok,answer=pcall(Command.CopyToClipboard,out)
    if not ok or answer==false then
        notifyUi("Clipboard copy failed");return nil,"clipboard_failed"
    end
    notifyUi("Copied filtered history to clipboard ("..#out.." bytes)")
    return true
end
local function submit()
    if not model or not editor then return nil,"not_ready" end
    local value=editor:GetText() or ""
    if #value==0 then return nil,"empty" end
    local ok,err=model:execute(value,clock())
    if not ok then
        if err=="native_send_unavailable" then
            notifyUi("Normal chat/send and native slash commands are not yet routed. Use :commands.")
        else notifyUi("Command rejected: "..tostring(err)) end
        return nil,err -- Keep unsent draft visible.
    end
    editor:SetText("")
    visibleOffset=0
    render()
    return true
end
local function makeUi()
    if panel then return end
    context=UI.CreateContext("RiftChatModernContext")
    panel=UI.CreateFrame("Frame","RiftChatModernWindow",context)
    panel:SetWidth(W);panel:SetHeight(H)
    rgba(panel,C.bg)
    local ui=model and model.saved.ui
    local vw,vh=UIParent:GetWidth(),UIParent:GetHeight()
    shift(ui and ui.x or math.max(0,math.floor((vw-W)/2)),
        ui and ui.y or math.max(0,math.floor((vh-H)/3)),false)
    local header=frame("Header",panel,0,0,W,52,C.header)
    text("Title",header,"RIFT CHAT  /  MODERN",18,13,440,25,19,C.text)
    text("Version",header,"v"..VERSION,560,14,90,20,14,C.accent)
    button("Close","×",header,708,9,32,32,function()
        if editor and type(editor.SetKeyFocus)=="function" then
            pcall(editor.SetKeyFocus,editor,false)
        end
        panel:SetVisible(false)
    end)
    local handle=frame("DragHandle",header,0,0,548,52)
    handle:SetMouseMasking("full")
    handle:EventAttach(Event.UI.Input.Mouse.Left.Down,startDrag,ADDON.." drag start")
    handle:EventAttach(Event.UI.Input.Mouse.Left.Up,stopDrag,ADDON.." drag stop")
    handle:EventAttach(Event.UI.Input.Mouse.Left.Upoutside,stopDrag,ADDON.." drag outside")
    frame("Divider",panel,0,52,W,1,C.border)
    tabLabels={}
    local tabs={{"all","ALL"},{"chat","CHAT"},{"system","SYSTEM"},{"npc","NPC"},
        {"addons","ADDONS"},{"dev","DEV"}}
    for i,tab in ipairs(tabs) do
        local name,display=tab[1],tab[2]
        local b,label=button("Tab"..name,display,panel,14+(i-1)*119,61,109,29,
            function() model:setFilter(name);visibleOffset=0;render() end)
        tabLabels[name]=label
    end
    text("FindLabel",panel,"FIND",17,104,54,24,14,C.muted)
    searchField=UI.CreateFrame("RiftTextfield","RCMSearchField",panel)
    searchField:SetPoint("TOPLEFT",panel,"TOPLEFT",68,99)
    searchField:SetWidth(521);searchField:SetHeight(29)
    rgba(searchField,C.control)
    searchField:SetText(model.search)
    if Event.UI.Textfield and Event.UI.Textfield.Change then
        searchField:EventAttach(Event.UI.Textfield.Change,function()
            local val=searchField:GetText() or ""
            if #val<=60 then model:setSearch(val);visibleOffset=0;render() end
        end,ADDON.." search updated")
    end
    button("FindReset","RESET",panel,602,99,73,29,function()
        searchField:SetText(""); model:setSearch("");visibleOffset=0;render()
    end)
    button("PageUp","▲",panel,685,143,50,32,function()
        visibleOffset=math.min(240,visibleOffset+LINES);render()
    end)
    button("PageDown","▼",panel,685,185,50,32,function()
        visibleOffset=math.max(0,visibleOffset-LINES);render()
    end)
    rows={}
    local list=frame("MessageCard",panel,14,138,658,300,C.card)
    for i=1,LINES do
        local row=frame("Line"..i,list,5,5+(i-1)*22,648,22,
            i%2==0 and C.card or C.alt)
        rows[i]={entry=text("LineText"..i,row,"",9,1,630,20,14,C.text)}
    end
    button("Copy","COPY HISTORY",panel,14,449,155,30,copyHistory,true)
    button("Clear","CLEAR",panel,178,449,104,30,function()
        model:clear();visibleOffset=0;render()
    end)
    button("Focus","FOCUS INPUT",panel,292,449,139,30,focusEditor)
    text("Meta",panel,"Addon diagnostics + NPC + alerts • :help",448,456,285,20,13,C.muted)
    editor=UI.CreateFrame("RiftTextfield","RCMInput",panel)
    editor:SetPoint("TOPLEFT",panel,"TOPLEFT",14,491)
    editor:SetWidth(622);editor:SetHeight(35)
    editor:SetText("")
    rgba(editor,C.control)
    if editor.Event then
        function editor.Event:KeyDown(key)
            if type(key)=="string" and (key:byte(1)==13 or key:byte(1)==10
                or key:lower()=="enter" or key:lower()=="return") then
                submit()
            end
        end
    end
    if Event.UI.Input.Mouse.Left.Click then
        editor:EventAttach(Event.UI.Input.Mouse.Left.Click,function()
            focusEditor()
        end,ADDON.." editor click focus")
    end
    button("Send","RUN",panel,643,491,92,35,submit,true)
    statusField=text("Status",panel,"",16,530,700,20,12,C.muted)
    -- Keep the status text inside the window; no automatic native chat interception.
    statusField:SetPoint("TOPLEFT",panel,"TOPLEFT",16,529)
    model.onChange=render
    panel:SetVisible(false)
    render()
end
local function show(yes)
    if not model then return nil,"not_ready" end
    makeUi()
    if not yes and drag then stopDrag() end
    panel:SetVisible(yes)
    if yes then render() end
    return true
end
local function parseSlash(_,args)
    args=type(args)=="string" and args or ""
    if #args>160 then notice("Command too long");return end
    local verb,rest=args:match("^%s*(%S*)%s*(.-)%s*$")
    verb=(verb or ""):lower()
    if verb=="" then show(not (panel and panel:GetVisible()));return end
    if verb=="show" then show(true)
    elseif verb=="hide" then show(false)
    elseif verb=="focus" then show(true);focusEditor()
    elseif verb=="copy" then copyHistory()
    elseif verb=="clear" then if model then model:clear() end
    elseif verb=="status" then
        if model then
            local stat=model:status()
            notice(string.format("%d stored / filter %s / editor owned; native social send unavailable",
                stat.historyCount,stat.filter))
        end
    elseif verb=="tab" and model then
        local ok=model:setFilter(rest)
        if not ok then notice("Unknown tab: "..rest) else visibleOffset=0;render() end
    elseif verb=="find" and model then
        local ok,err=model:setSearch(rest)
        if not ok then notice("Search rejected: "..tostring(err))
        else visibleOffset=0;render() end
    elseif verb=="help" then
        notice("/rcm [show|hide|focus|status|copy|clear|tab KIND|find TEXT]")
        notice("Input owns :help :status :filter :find :echo plus addon extension commands.")
    else notice("Unknown command. Use /rcm help") end
end

local function optionalRPT(args)
    local api=_G.RPTTravelLabAPI
    if type(api)~="table" then return "RPT Travel Lab is not loaded." end
    local verb,rest=args:match("^%s*(%S*)%s*(.-)%s*$")
    verb=(verb or "status"):lower()
    if verb=="" then verb="status" end
    local operation
    if verb=="status" and type(api.GetStatus)=="function" then
        local ok,data=pcall(api.GetStatus)
        if not ok or type(data)~="table" then return "RPT status unavailable." end
        return string.format("RPT %s | ready=%s | recording=%s | trials=%s | samples=%s",
            tostring(data.version),tostring(data.ready),tostring(data.recording),
            tostring(data.trialCount),tostring(data.sampleCount))
    elseif verb=="arm" then operation=api.Arm
    elseif verb=="stop" then operation=api.Stop
    elseif verb=="mark" and rest~="" then operation=api.Mark
    elseif verb=="last" and type(api.GetLastTrial)=="function" then
        local ok,data=pcall(api.GetLastTrial)
        if not ok or type(data)~="table" then return "RPT last trial unavailable." end
        return string.format("RPT %s | %s | %d samples / %d events",
            tostring(data.id),tostring(data.result and data.result.status or "active"),
            #(data.samples or {}),#(data.events or {}))
    else
        return "RPT commands: :rpt status | arm | stop | mark NOTE | last"
    end
    if type(operation)~="function" then return "RPT action unavailable." end
    local ran,result,err=pcall(operation,verb=="mark" and rest or nil)
    if not ran or result~=true then
        return "RPT "..verb.." refused: "..tostring(err or result)
    end
    return "RPT "..verb.." accepted by addon API; in-game outcome unverified."
end

local function onSaveLoad(_,name)
    if name~=ADDON then return end
    if RiftChatModernSaved==nil then
        RiftChatModernSaved={schemaVersion=1,history={}}
    end
    if not Core or type(Core.new)~="function" then
        notice("Core module missing. Recording disabled.");return
    end
    local m,err=Core.new(RiftChatModernSaved)
    if not m then notice("Saved data rejected: "..tostring(err));return end
    model=m
    -- Optional cross-repository adapter; no hard dependency or input injection.
    model:registerCommand("rpt",optionalRPT)
end
local function onLoaded(_,name)
    if name~=ADDON or initialized then return end
    initialized=true
    if model then
        makeUi()
        model:publish("system","Modern chat window ready. :help lists local commands.",
            "RiftChatModern",clock())
    end
    notice("Loaded. /rcm opens the console. Version "..VERSION)
end
local function nativeNpc(_,info)
    if model and type(info)=="table" and type(info.message)=="string" then
        model:publish("npc",info.message:sub(1,512),
            type(info.fromName)=="string" and info.fromName:sub(1,40) or "NPC",clock())
    end
end
local function nativeNotify(_,info)
    if model and type(info)=="table" and type(info.message)=="string" then
        model:publish("system",info.message:sub(1,512),"Game alert",clock())
    end
end
local function dragTick()
    if drag then
        local m=mouse()
        if not m or m.Left==false then stopDrag()
        else dragMove(false) end
    end
end
_G.RiftChatModernAPI={
    interfaceVersion=1,version=VERSION,
    Publish=function(kind,msg,source)
        if not model then return nil,"not_ready" end
        return model:publish(kind,msg,source,clock())
    end,
    GetStatus=function()
        local data=model and model:status() or {version=VERSION,ready=false}
        data.ready=model~=nil
        data.windowVisible=panel and panel:GetVisible() or false
        data.editorFocused=(editor and panel and panel:GetVisible()
            and type(editor.GetKeyFocus)=="function"
            and (function()
                local ok,focused=pcall(editor.GetKeyFocus,editor)
                return ok and focused==true
            end)()) or false
        return data
    end,
    GetHistory=function(kind,search,limit,offset)
        if not model then return nil,"not_ready" end
        return model:getHistory(kind,search,limit or 50,offset or 0)
    end,
    RegisterCommand=function(name,fn)
        if not model then return nil,"not_ready" end
        return model:registerCommand(name,fn)
    end,
    Subscribe=function(name,fn)
        if not model then return nil,"not_ready" end
        return model:subscribe(name,fn)
    end,
    Unsubscribe=function(name)
        if not model then return nil,"not_ready" end
        return model:unsubscribe(name)
    end,
    Submit=function(command)
        if not model then return nil,"not_ready" end
        return model:execute(command,clock())
    end,
    Copy=function()
        if not model then return nil,"not_ready" end
        return copyHistory()
    end,
    Show=function() return show(true) end,
    Hide=function() return show(false) end,
    FocusEditor=focusEditor,
}
Command.Event.Attach(Event.Addon.SavedVariables.Load.End,onSaveLoad,"RCM history load")
Command.Event.Attach(Event.Addon.Load.End,onLoaded,"RCM initialized")
if Event.Chat and Event.Chat.Npc then
    Command.Event.Attach(Event.Chat.Npc,nativeNpc,"RCM NPC messages")
end
if Event.Chat and Event.Chat.Notify then
    Command.Event.Attach(Event.Chat.Notify,nativeNotify,"RCM game alerts")
end
Command.Event.Attach(Event.System.Update.Begin,dragTick,"RCM drag tracking")
local slash=Command.Slash.Register("rcm")
if slash then Command.Event.Attach(slash,parseSlash,"RCM commands") end
