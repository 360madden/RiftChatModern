-- RiftChatModern / Main.lua -- compact, standalone RIFT addon chat/diagnostic console.
-- Native player say/tell/guild transmit and full native chat interception are NOT
-- exposed by the verified addon APIs. This UI never pretends to send those.
local info = ...
local ADDON, VERSION = "RiftChatModern", (type(info)=="table" and info.version) or "0.2.1"
local Core = _G.RiftChatModernCore
local MessageBridge = _G.RiftChatModernAddonMessages
local NativeProbe = _G.RiftChatModernNativeProbe
local ConsoleMirror = _G.RiftChatModernConsoleMirror
local W,H,LINES=760,618,13
local C = {
    bg={0.065,0.080,0.11,0.98}, header={0.090,0.111,0.15,1},
    card={0.092,0.117,0.15,1}, alt={0.081,0.102,0.13,1},
    border={0.16,0.21,0.27,1}, control={0.14,0.19,0.25,1},
    hover={0.19,0.27,0.34,1}, accent={0.12,0.67,0.75,1},
    text={0.90,0.94,0.97,1}, muted={0.61,0.72,0.79,1},
    warning={1.0,0.73,0.43,1}, good={0.40,0.91,0.70,1}
}
local model,panel,editor,searchField,statusField,focusIndicator,rows,tabLabels,drag
local selectedId,detailOverlay,detailTitle,detailBody
local mirror,mirrorButtonLabel
local transport
local context,visibleOffset,lastFocusState= nil,0,nil
local lastViewportW,lastViewportH
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
    if not drag then return end
    if mouse() then dragMove(true)
    elseif panel then shift(panel:GetLeft(),panel:GetTop(),true) end
    drag=nil
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
    f:SetFontSize(size or 16)
    -- Bundled Lato follows the RPT Lab typography, with native-font fallback.
    pcall(function() f:SetFont(ADDON,bold and "fonts/Lato-Bold.ttf"
        or "fonts/Lato-Regular.ttf") end)
    f:SetWordwrap(false)
    f:SetMouseMasking("limited") -- text labels cannot block parent buttons/drag handles
    f:SetText(value or "")
    ink(f,color or C.text)
    return f
end
local function button(name,value,parent,x,y,w,h,fn,strong)
    local control=frame(name,parent,x,y,w,h,strong and C.accent or C.control)
    control:SetMouseMasking("full")
    local caption=text(name.."Label",control,value,8,math.max(1,(h-21)/2),w-16,22,15,
        strong and C.bg or C.text,true)
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
local function focusState()
    if not panel or not panel:GetVisible() then return "hidden" end
    if not editor or type(editor.GetKeyFocus)~="function" then return "unavailable" end
    local ok,focused=pcall(editor.GetKeyFocus,editor)
    if not ok or type(focused)~="boolean" then return "unavailable" end
    if focused then return "focused" end
    if searchField and type(searchField.GetKeyFocus)=="function" then
        local found,value=pcall(searchField.GetKeyFocus,searchField)
        if found and value==true then return "search" end
    end
    return "unfocused"
end
local function updateFocusIndicator(force)
    local state=focusState()
    if focusIndicator and (force or lastFocusState~=state) then
        local label=state=="focused" and "INPUT  ●  FOCUSED"
            or state=="search" and "SEARCH  ●  FOCUSED"
            or state=="hidden" and "INPUT  •  HIDDEN"
            or state=="unfocused" and "INPUT  •  NOT FOCUSED"
            or "INPUT  ?  UNAVAILABLE"
        focusIndicator:SetText(label)
        ink(focusIndicator,state=="focused" and C.good
            or state=="search" and C.accent
            or state=="unavailable" and C.warning or C.muted)
    end
    lastFocusState=state
    return state
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
    updateFocusIndicator(true)
    if good and value==true then
        notifyUi("Editor focused • local commands start with :")
        return true
    end
    return nil,"focus_not_acquired"
end
local function focusSearch()
    if not searchField or not panel or not panel:GetVisible() then return nil,"search_hidden" end
    if type(searchField.SetKeyFocus)~="function" then return nil,"focus_api_unavailable" end
    local ok=pcall(searchField.SetKeyFocus,searchField,true)
    if not ok then return nil,"focus_request_failed" end
    local state=updateFocusIndicator(true)
    return state=="search" and true or nil,state~="search" and "focus_not_acquired" or nil
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
local function selectedMessage()
    if not model or not selectedId then return nil,"no_selection" end
    return model:getMessage(selectedId)
end
local function closeDetails()
    selectedId=nil
    if detailOverlay then detailOverlay:SetVisible(false) end
    return true
end
local function copyMessage()
    local row,err=selectedMessage()
    if not row then return nil,err end
    if not Command or type(Command.CopyToClipboard)~="function" then
        notifyUi("Clipboard unavailable.");return nil,"clipboard_unavailable"
    end
    local text=row.source..": "..row.text
    local ok,result=pcall(Command.CopyToClipboard,text)
    if not ok or result==false then
        notifyUi("Copy message failed.");return nil,"clipboard_failed"
    end
    notifyUi("Copied complete message #"..tostring(row.id).." ("..#text.." bytes).")
    return true
end
local function openMessage(id)
    if not model then return nil,"not_ready" end
    local row,err=model:getMessage(id)
    if not row then return nil,err end
    selectedId=id
    if detailOverlay and detailBody and detailTitle then
        detailTitle:SetText(string.format("%s  •  %s  •  #%d",
            row.kind:upper(),row.source,row.id))
        detailBody:SetText(row.text)
        detailOverlay:SetVisible(true)
    end
    return true
end
local function render()
    if not model or not panel then return end
    local selection,total=model:getHistory(model.filter,model.search,LINES,visibleOffset)
    for i=1,LINES do
        local r=selection[i]
        rows[i].messageId=r and r.id or nil
        if r then
            local ts="--:--"
            if os and os.date then
                local ok,value=pcall(os.date,"%H:%M",math.floor(r.at))
                if ok and type(value)=="string" then ts=value end
            end
            local msg=string.format("%s  %-7s  %-14s %s",ts,r.kind:upper(),
                cutUtf8(r.source,14),r.text)
            rows[i].entry:SetText(cutUtf8(msg,79))
            ink(rows[i].entry,r.kind=="dev" and C.accent or
                r.kind=="system" and C.warning or C.text)
        else rows[i].entry:SetText("") end
    end
    local count=math.min(total,visibleOffset+LINES)
    local first=math.max(0,count-math.min(LINES,total-visibleOffset)+1)
    if selectedId then
        local current=model:getMessage(selectedId)
        if not current then closeDetails() end
    end
    notifyUi(string.format("%d messages  •  showing %d–%d  •  %s  •  native chat separate",
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
local function executeLocal(value)
    if not model then return nil,"not_ready" end
    -- Clipboard is an actual in-game feature, not a placeholder console line.
    if type(value)=="string" and value:match("^%s*:copy%s*$") then
        return copyHistory()
    end
    return model:execute(value,clock())
end
local function mirrorStatus()
    return mirror and mirror:status()
        or {enabled=false,ownsHook=false,captured=0,rejected=0,
            type="addon_console_output_only",nativePlayerChatCaptured=false}
end
local function setMirror(enabled)
    if not mirror then return nil,"console_mirror_unavailable" end
    if type(enabled)~="boolean" then return nil,"invalid_state" end
    local ok,err
    if enabled then ok,err=mirror:enable() else ok,err=mirror:disable() end
    local state=mirror:status()
    if mirrorButtonLabel then
        mirrorButtonLabel:SetText(state.enabled and "MIRROR ON" or "MIRROR OFF")
    end
    if ok then
        notifyUi(state.enabled and "Mirroring addon console output, not player chat."
            or "Addon console mirroring disabled.")
        return true
    end
    notifyUi("Addon console mirror unavailable: "..tostring(err))
    return nil,err
end
local function mirrorCommand(args)
    args=(args or ""):lower()
    if args=="on" then
        local ok,err=setMirror(true)
        return ok and "Mirroring addon console output, not player chat."
            or "Mirror unavailable: "..tostring(err)
    elseif args=="off" then
        local ok,err=setMirror(false)
        return ok and "Addon console mirror disabled."
            or "Mirror disabled; another wrapper may remain: "..tostring(err)
    elseif args=="" or args=="status" then
        local state=mirrorStatus()
        return string.format("Console mirror %s | captured=%d | hook-owned=%s | not player chat",
            state.enabled and "ON" or "OFF",state.captured,tostring(state.ownsHook))
    end
    return "Usage: :mirror on | off | status"
end
local function submit()
    if not model or not editor then return nil,"not_ready" end
    local value=editor:GetText() or ""
    if #value==0 then return nil,"empty" end
    local ok,err=executeLocal(value)
    if not ok then
        if err=="native_send_unavailable" then
            notifyUi("Normal chat/send and native slash commands are not yet routed. Use :commands.")
        else notifyUi("Command rejected: "..tostring(err)) end
        return nil,err -- Keep unsent draft visible.
    end
    editor:SetText("")
    visibleOffset=0
    -- Copy writes a useful receipt into the footer; preserve it until changed.
    if not value:match("^%s*:copy%s*$") then render() end
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
    local header=frame("Header",panel,0,0,W,58,C.header)
    -- The drag surface is only over the title. The close button remains clickable.
    local handle=frame("DragHandle",header,0,0,370,58)
    handle:SetMouseMasking("full")
    handle:EventAttach(Event.UI.Input.Mouse.Left.Down,startDrag,ADDON.." drag start")
    handle:EventAttach(Event.UI.Input.Mouse.Left.Up,stopDrag,ADDON.." drag stop")
    handle:EventAttach(Event.UI.Input.Mouse.Left.Upoutside,stopDrag,ADDON.." drag outside")
    text("Title",handle,"RIFT CHAT  /  MODERN",18,15,320,28,21,C.text,true)
    focusIndicator=text("FocusIndicator",header,"INPUT  •  HIDDEN",
        383,20,188,24,14,C.muted,true)
    text("Version",header,"v"..VERSION,579,19,118,22,16,C.accent,true)
    button("Close","×",header,715,11,34,34,function()
        drag=nil
        if editor and type(editor.SetKeyFocus)=="function" then
            pcall(editor.SetKeyFocus,editor,false)
        end
        if searchField and type(searchField.SetKeyFocus)=="function" then
            pcall(searchField.SetKeyFocus,searchField,false)
        end
        panel:SetVisible(false)
        updateFocusIndicator(true)
    end)
    frame("Divider",panel,0,58,W,1,C.border)
    tabLabels={}
    local tabs={{"all","ALL"},{"chat","CHAT"},{"system","SYSTEM"},{"npc","NPC"},
        {"addons","ADDONS"},{"dev","DEV"}}
    for i,tab in ipairs(tabs) do
        local name,display=tab[1],tab[2]
        local b,label=button("Tab"..name,display,panel,16+(i-1)*122,69,110,34,
            function() model:setFilter(name);visibleOffset=0;render() end)
        tabLabels[name]=label
    end
    text("FindLabel",panel,"SEARCH",17,118,60,25,15,C.muted,true)
    searchField=UI.CreateFrame("RiftTextfield","RCMSearchField",panel)
    searchField:SetPoint("TOPLEFT",panel,"TOPLEFT",84,111)
    searchField:SetWidth(506);searchField:SetHeight(33)
    pcall(function() searchField:SetFontSize(16) end)
    rgba(searchField,C.control)
    searchField:SetText(model.search)
    if Event.UI.Textfield and Event.UI.Textfield.Change then
        searchField:EventAttach(Event.UI.Textfield.Change,function()
            local val=searchField:GetText() or ""
            if #val<=60 then model:setSearch(val);visibleOffset=0;render() end
        end,ADDON.." search updated")
    end
    button("FindReset","RESET",panel,605,111,75,33,function()
        searchField:SetText(""); model:setSearch("");visibleOffset=0;render()
    end)
    button("PageUp","▲",panel,694,160,50,34,function()
        visibleOffset=math.min(240,visibleOffset+LINES);render()
    end)
    button("PageDown","▼",panel,694,205,50,34,function()
        visibleOffset=math.max(0,visibleOffset-LINES);render()
    end)
    rows={}
    local list=frame("MessageCard",panel,14,154,666,326,C.card)
    for i=1,LINES do
        local row=frame("Line"..i,list,5,6+(i-1)*24,656,24,
            i%2==0 and C.card or C.alt)
        row:SetMouseMasking("full")
        rows[i]={entry=text("LineText"..i,row,"",9,2,634,22,16,C.text),
            frame=row,messageId=nil}
        row:EventAttach(Event.UI.Input.Mouse.Left.Click,function()
            local id=rows[i].messageId
            if id then openMessage(id) end
        end,ADDON.." open message "..i)
    end
    -- Complete-message reader overlays only the message list, not the controls.
    -- The regular rows remain available immediately after CLOSE.
    detailOverlay=frame("DetailOverlay",list,4,4,658,318,C.header)
    detailOverlay:SetMouseMasking("full")
    detailTitle=text("DetailTitle",detailOverlay,"MESSAGE DETAILS",
        14,13,520,25,18,C.accent,true)
    detailBody=text("DetailBody",detailOverlay,"",
        14,51,630,194,16,C.text)
    detailBody:SetWordwrap(true)
    button("DetailCopy","COPY MESSAGE",detailOverlay,14,267,162,36,
        copyMessage,true)
    button("DetailClose","CLOSE",detailOverlay,551,267,94,36,closeDetails)
    detailOverlay:SetVisible(false)
    button("Copy","COPY HISTORY",panel,14,490,170,35,copyHistory,true)
    button("Clear","CLEAR",panel,195,490,98,35,function()
        closeDetails();model:clear();visibleOffset=0;render()
    end)
    button("Focus","FOCUS INPUT",panel,304,490,145,35,focusEditor)
    local _,caption=button("Mirror","MIRROR OFF",panel,465,490,174,35,
        function() setMirror(not mirrorStatus().enabled) end)
    mirrorButtonLabel=caption
    mirrorButtonLabel:SetText(mirrorStatus().enabled and "MIRROR ON" or "MIRROR OFF")
    editor=UI.CreateFrame("RiftTextfield","RCMInput",panel)
    editor:SetPoint("TOPLEFT",panel,"TOPLEFT",14,535)
    editor:SetWidth(632);editor:SetHeight(40)
    pcall(function() editor:SetFontSize(18) end)
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
    button("Send","RUN",panel,655,535,90,40,submit,true)
    statusField=text("Status",panel,"",16,587,726,24,14,C.muted)
    -- All controls remain inside the 760×618 panel, even at reduced UI scale.
    -- Explicit input focus indication; opening the window never steals focus.
    if Event.UI.Input.Mouse.Left.Click then
        searchField:EventAttach(Event.UI.Input.Mouse.Left.Click,function()
            focusSearch()
        end,ADDON.." search click focus")
    end
    local focusEvents=Event.UI.Input.Key and Event.UI.Input.Key.Focus
    if focusEvents then
        for _,field in ipairs({editor,searchField}) do
            if focusEvents.Gain then
                pcall(field.EventAttach,field,focusEvents.Gain,
                    function() updateFocusIndicator(true) end,ADDON.." focus gain")
            end
            if focusEvents.Loss then
                pcall(field.EventAttach,field,focusEvents.Loss,
                    function() updateFocusIndicator(true) end,ADDON.." focus loss")
            end
        end
    end
    model.onChange=render
    panel:SetVisible(false)
    updateFocusIndicator(true)
    render()
end
local function show(yes)
    if not model then return nil,"not_ready" end
    makeUi()
    if not yes then
        closeDetails()
        if drag then
            shift(panel:GetLeft(),panel:GetTop(),true)
            drag=nil
        end
        if editor and type(editor.SetKeyFocus)=="function" then
            pcall(editor.SetKeyFocus,editor,false)
        end
        if searchField and type(searchField.SetKeyFocus)=="function" then
            pcall(searchField.SetKeyFocus,searchField,false)
        end
    end
    panel:SetVisible(yes)
    updateFocusIndicator(true)
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
        notice("Input: :help :status :mirror on/off :native :rpt ... :addon CHARACTER MESSAGE.")
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

local function getNativeConsoles()
    if NativeProbe and type(NativeProbe.capture)=="function" then
        return NativeProbe.capture(UI,Inspect)
    end
    return {scope="unavailable",windowCount=0,visibleCount=0,
        focusCount=0,windows={},nativeTranscriptReadable=false,
        nativeSocialSendAvailable=false}
end
local nativeChannelNames={"say","tell","guild","party","officer","raid",
    "system","npc","channel","combatGood","combatBad"}
local function nativeProbeCommand(args)
    local data=getNativeConsoles()
    args=(args or ""):lower()
    if args=="channels" or args=="copy" then
        if not data.consoleListReady then return "Console list API unavailable." end
        local lines={"RIFT native console subscriptions (metadata, not chat text):"}
        for _,entry in ipairs(data.consoles or {}) do
            local enabled={}
            for _,key in ipairs(nativeChannelNames) do
                if entry.channels and entry.channels[key]==true then
                    enabled[#enabled+1]=key
                end
            end
            lines[#lines+1]=(entry.name or entry.id)..": "
                ..(#enabled>0 and table.concat(enabled,", ") or "(none/unknown)")
        end
        if args=="copy" then
            if not Command or type(Command.CopyToClipboard)~="function" then
                return "Clipboard API unavailable."
            end
            local output=table.concat(lines,"\n")
            local ok,result=pcall(Command.CopyToClipboard,output)
            return ok and result~=false and
                ("Copied "..tostring(#lines-1).." console descriptions (metadata only).")
                or "Console metadata copy failed."
        end
        local description=table.concat(lines," | ")
        return description:sub(1,512)
    end
    return string.format("Native windows: %d (%d visible), configured consoles: %d%s. "
        .."Console subscriptions are metadata, not readable chat messages.",
        data.windowCount,data.visibleCount,data.consoleCount or 0,
        data.consoleListReady and "" or " (list unavailable)")
end

local function sendAddonCommand(args)
    if not transport or not transport.ready then
        return "Addon-data transport unavailable (normal chat unchanged)."
    end
    local target,message=args:match("^(%S+)%s+(.+)$")
    if not target or not message then
        return "Usage: :addon CHARACTER MESSAGE (addon data, not player chat)"
    end
    local outcome,err=transport:sendTo(target,message)
    if not outcome then return "Addon message refused: "..tostring(err) end
    return "Addon-data send submitted to RIFT API for "..target
        .." (#"..outcome.id.."); server acknowledgment/delivery pending."
end

local function onAddonReceived(from,kind,channel,identifier,data)
    -- Unlike most addon lifecycle callbacks, Event.Message.Receive provides
    -- from/type/channel/identifier/data directly, without event handle.
    if transport then transport:receive(from,kind,channel,identifier,data) end
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
    model:registerCommand("addon",sendAddonCommand)
    model:registerCommand("native",nativeProbeCommand)
    model:registerCommand("mirror",mirrorCommand)
    if ConsoleMirror and type(ConsoleMirror.new)=="function"
        and Command and Command.Console
        and type(Command.Console.Display)=="function" then
        mirror=ConsoleMirror.new(Command.Console,function(line,channel)
            if model then
                return model:publish("addons",line,
                    ("Console:"..channel):sub(1,40),clock())
            end
        end)
    end
    if MessageBridge and type(MessageBridge.new)=="function"
        and Command and Command.Message
        and type(Command.Message.Send)=="function"
        and type(Command.Message.Accept)=="function" then
        local bridge=MessageBridge.new(
            function(...) return Command.Message.Send(...) end,
            function(...) return Command.Message.Accept(...) end,
            function(from,data)
                if model then
                    local line= #from>40 and (from..": "..data) or data
                    model:publish("addons",line,from:sub(1,40),clock())
                end
            end,
            function(note,to)
                if model then
                    model:publish("dev",note,("RCM to "..to):sub(1,40),clock())
                end
            end,
            function()
                local ok,now=pcall(Inspect.Time.Real)
                if ok and finite(now) then return now end
                return nil
            end)
        if bridge then
            local ok=bridge:enable()
            if ok then transport=bridge end
        end
    end
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
local function eventInfo(first,second)
    if type(second)=="table" then return second end
    if type(first)=="table" then return first end
    return nil
end
local function nativeNpc(first,second)
    local info=eventInfo(first,second)
    if not model or not info or type(info.message)~="string" then return end
    local source=type(info.fromName)=="string" and info.fromName:sub(1,40) or "NPC"
    model:publish("npc",info.message:sub(1,512),source,clock())
end
local function nativeNotify(first,second)
    local info=eventInfo(first,second)
    if not model or not info then return end
    if type(info.message)=="string" then
        model:publish("system",info.message:sub(1,512),"Game alert",clock())
        return
    end
    -- Some existing RIFT addons receive a keyed unit->notification table.
    -- Only record explicit strings/text; never stringify arbitrary units.
    local count=0
    for unit,value in pairs(info) do
        count=count+1
        if count>16 then break end
        local message=type(value)=="string" and value
            or type(value)=="table" and type(value.message)=="string"
                and value.message or nil
        if message and #message>0 then
            local from=type(unit)=="string" and unit:sub(1,40) or "Game alert"
            model:publish("system",message:sub(1,512),from,clock())
        end
    end
end
local function dragTick()
    if drag then
        local m=mouse()
        if not m or m.Left==false then stopDrag()
        else dragMove(false) end
    end
    if panel and panel:GetVisible() then
        local w,h=UIParent:GetWidth(),UIParent:GetHeight()
        if finite(w) and finite(h)
            and (lastViewportW~=w or lastViewportH~=h) then
            lastViewportW,lastViewportH=w,h
            if not drag then shift(panel:GetLeft(),panel:GetTop(),true) end
        end
        updateFocusIndicator(false)
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
        local state=focusState()
        data.editorFocusState=state
        data.editorFocused=state=="focused"
        data.searchFocused=state=="search"
        data.addonTransportReady=transport~=nil and transport.ready or false
        data.consoleMirrorEnabled=mirrorStatus().enabled
        return data
    end,
    GetHistory=function(kind,search,limit,offset)
        if not model then return nil,"not_ready" end
        return model:getHistory(kind,search,limit or 50,offset or 0)
    end,
    GetMessage=function(id)
        if not model then return nil,"not_ready" end
        return model:getMessage(id)
    end,
    OpenMessage=openMessage,
    GetSelectedMessage=selectedMessage,
    CopySelectedMessage=copyMessage,
    CloseMessage=closeDetails,
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
    Submit=executeLocal,
    Copy=function()
        if not model then return nil,"not_ready" end
        return copyHistory()
    end,
    Show=function() return show(true) end,
    Hide=function() return show(false) end,
    FocusEditor=focusEditor,
    FocusSearch=focusSearch,
    GetFocusState=focusState,
    GetNativeConsoles=getNativeConsoles,
    GetConsoleMirrorStatus=mirrorStatus,
    SetConsoleMirror=setMirror,
    GetAddonTransportStatus=function()
        return transport and transport:status()
            or {ready=false,identifier="RCMDevV1",pending=false}
    end,
    SendAddon=function(target,message)
        if not transport then return nil,"transport_unavailable" end
        return transport:sendTo(target,message)
    end,
}
Command.Event.Attach(Event.Addon.SavedVariables.Load.End,onSaveLoad,"RCM history load")
Command.Event.Attach(Event.Addon.Load.End,onLoaded,"RCM initialized")
if Event.Chat and Event.Chat.Npc then
    Command.Event.Attach(Event.Chat.Npc,nativeNpc,"RCM NPC messages")
end
if Event.Chat and Event.Chat.Notify then
    Command.Event.Attach(Event.Chat.Notify,nativeNotify,"RCM game alerts")
end
if Event.Message and Event.Message.Receive then
    Command.Event.Attach(Event.Message.Receive,onAddonReceived,"RCM addon data")
end
Command.Event.Attach(Event.System.Update.Begin,dragTick,"RCM drag tracking")
local slash=Command.Slash.Register("rcm")
if slash then Command.Event.Attach(slash,parseSlash,"RCM commands") end
