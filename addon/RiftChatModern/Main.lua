-- RiftChatModern / Main.lua -- compact, standalone RIFT addon chat/diagnostic console.
-- Native player say/tell/guild transmit and full native chat interception are NOT
-- exposed by the verified addon APIs. This UI never pretends to send those.
local info = ...
local ADDON, VERSION = "RiftChatModern", (type(info)=="table" and info.version) or "0.2.23"
local Core = _G.RiftChatModernCore
local MessageBridge = _G.RiftChatModernAddonMessages
local NativeProbe = _G.RiftChatModernNativeProbe
local ConsoleMirror = _G.RiftChatModernConsoleMirror
local HostIngress = _G.RiftChatModernHostIngress
local DEFAULT_W, DEFAULT_H, MIN_W, MIN_H=760,618,680,480
local W,H,LINES=DEFAULT_W,DEFAULT_H,13
local ROW_H,MAX_ROWS=24,80
local TAB_ORDER={"all","imports","system","npc","addons","dev","native"}
local ACTION_ORDER={"Copy","Clear","Focus","Mirror"}
local ACTION_WEIGHTS={170/587,98/587,145/587,174/587}
-- Version 0.2.20: image-backed glass chrome. Colors below remain the safe
-- fallback when the RIFT client cannot load packaged texture resources.
local C = {
    bg={0.025,0.075,0.10,0.94}, header={0.036,0.106,0.14,0.93},
    card={0.030,0.080,0.11,0.49}, alt={0.022,0.061,0.087,0.48},
    border={0.16,0.37,0.43,0.82}, control={0.07,0.16,0.20,0.86},
    hover={0.10,0.24,0.29,0.91}, accent={0.12,0.82,0.83,1},
    text={0.94,0.98,0.99,1}, muted={0.66,0.78,0.82,1},
    warning={1.0,0.75,0.46,1}, good={0.40,0.94,0.72,1},
    clear={0,0,0,0}, input={0.035,0.105,0.13,0.38},
    info={0.60,0.78,1,1}
}
local model,panel,editor,searchField,statusField,focusIndicator,rows,tabLabels,drag
local resize, resizeGrip, header, handle, titleFrame, versionFrame, divider
local list, findLabel, controls, layoutWindow, render
local selectedId,detailOverlay,detailTitle,detailBody,detailPageStatus
local detailPageIndex,refreshDetail=1,nil
local mirror,mirrorButtonLabel
local transport,hostIngress,lastEditorImportReceipt
local context,visibleOffset,lastFocusState= nil,0,nil
local lastViewportW,lastViewportH
local initialized=false
-- These event counts are in-memory diagnostics only. A RIFT Save.End event
-- is NOT independent proof that any new SavedVariables bytes reached disk.
local saveBeginEvents,saveEndEvents=0,0
local function saveStatus()
    local result=model and model:checkpointStatus() or
        {saveEventReceiptAvailable=false,eventSequence=0,
         pendingSessionChanges=false,onDiskVerified=false,
         requiredDiskVerification=true,nativeSaveEventsAreNotDiskProof=true}
    result.saveBeginEventsThisSession=saveBeginEvents
    result.saveEndEventsThisSession=saveEndEvents
    result.saveEndObservedThisSession=saveEndEvents>0
    result.diskPersistedVerified=false
    return result
end
-- Editor commands are recalled in memory only; never written to SavedVariables.
local HISTORY_CAP=32
local commandHistory,recallIndex,recallDraft,recallWritten={},nil,nil,nil
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
local function rememberExecuted(value)
    if type(value)~="string" or value:sub(1,1)~=":" then return end
    -- Transfer chunks may contain private chat. Never put the encoded input
    -- into the editor command recall, even if accepted successfully.
    local verb=value:match("^%s*:([a-zA-Z][a-zA-Z0-9_]*)")
    if verb and verb:lower()=="import" then
        recallIndex,recallDraft,recallWritten=nil,nil,nil
        return
    end
    if commandHistory[#commandHistory]~=value then
        commandHistory[#commandHistory+1]=value
        if #commandHistory>HISTORY_CAP then table.remove(commandHistory,1) end
    end
    recallIndex,recallDraft,recallWritten=nil,nil,nil
end
local function recallCommand(direction)
    if not editor or #commandHistory==0 then return false end
    local value
    if direction=="older" then
        if not recallIndex then
            recallDraft=editor:GetText() or ""
            recallIndex=#commandHistory
        else
            recallIndex=math.max(1,recallIndex-1)
        end
        value=commandHistory[recallIndex]
    elseif direction=="newer" then
        if not recallIndex then return false end
        if recallIndex<#commandHistory then
            recallIndex=recallIndex+1
            value=commandHistory[recallIndex]
        else
            value=recallDraft or ""
            recallIndex,recallDraft=nil,nil
        end
    else return false end
    recallWritten=value
    editor:SetText(value)
    if type(editor.SetCursor)=="function" then
        pcall(editor.SetCursor,editor,#value)
    end
    notifyUi(recallIndex and ("Local command "..recallIndex.."/"..#commandHistory..
        " • session-only history") or "Restored unsent draft")
    return true
end
-- Reuse the existing controls upvalue in makeUi: Lua 5.1 limits a function
-- to 60 distinct upvalues. Extra direct state captures break addon loading.
controls=controls or {}
controls._skin={}
controls._categories=_G.RiftChatModernConsoleCategories
controls._native={active=false,group="game",sourceIndex=nil,page=0,snapshot=nil,lines={}}
controls._commandActions={
    recall=recallCommand,
    changed=function(current)
        if recallWritten~=nil and current==recallWritten then
            recallWritten=nil
            return
        end
        recallIndex,recallDraft,recallWritten=nil,nil,nil
    end,
}
local function mouse()
    if not Inspect or type(Inspect.Mouse)~="function" then return nil end
    local ok,value=pcall(Inspect.Mouse)
    if ok and type(value)=="table" and finite(value.x) and finite(value.y) then
        return value
    end
end
local function saveGeometry()
    if not model or not panel then return end
    local ui=type(model.saved.ui)=="table" and model.saved.ui or {}
    local left,top=panel:GetLeft(),panel:GetTop()
    local changed=ui.x~=left or ui.y~=top or ui.w~=W or ui.h~=H
    ui.x=left;ui.y=top
    ui.w=W;ui.h=H
    model.saved.ui=ui -- preserve other SavedVariables fields and history
    if changed then model:markSavedStateChanged() end
end
local function shift(x,y,save)
    if not panel or not finite(x) or not finite(y) then return end
    local vw,vh=UIParent:GetWidth(),UIParent:GetHeight()
    if not finite(vw) or not finite(vh) then return end
    x=math.max(0,math.min(math.max(0,vw-W),math.floor(x+0.5)))
    y=math.max(0,math.min(math.max(0,vh-H),math.floor(y+0.5)))
    -- Frame:SetPoint creates permanent anchors; replace instead of stacking.
    panel:ClearAll()
    panel:SetPoint("TOPLEFT",UIParent,"TOPLEFT",x,y)
    panel:SetWidth(W);panel:SetHeight(H)
    if save then saveGeometry() end
end
local function startDrag()
    if resize then return end
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
-- RIFT's Texture:SetTexture(addon, filename) supports local PNG resources.
-- A missing/unsupported texture leaves a readable solid-color fallback.
local function skinTexture(name,parent,asset,layer)
    local t=UI.CreateFrame("Texture","RCM"..name,parent)
    t:SetPoint("TOPLEFT",parent,"TOPLEFT",0,0)
    t:SetWidth(parent:GetWidth());t:SetHeight(parent:GetHeight())
    if type(t.SetLayer)=="function" then t:SetLayer(layer or -8) end
    if type(t.SetMouseMasking)=="function" then t:SetMouseMasking("limited") end
    if type(t.SetTexture)~="function"
        or not pcall(t.SetTexture,t,ADDON,"textures/"..asset..".png") then
        t:SetVisible(false)
        return nil
    end
    return t
end
controls._skinTexture=skinTexture
local function repaintControl(name,hovered)
    local item=controls and controls[name]
    if not item then return end
    if type(hovered)=="boolean" then item.hovered=hovered end
    local asset
    if item.tab then
        asset=item.active and "glass_tab_active"
            or item.hovered and "glass_tab_hover" or "glass_tab_idle"
    elseif item.strong then
        asset=item.hovered and "glass_primary_hover" or "glass_primary"
    else
        asset=item.hovered and "glass_button_hover" or "glass_button"
    end
    if item.skin and item.asset~=asset then
        if pcall(item.skin.SetTexture,item.skin,ADDON,"textures/"..asset..".png") then
            item.asset=asset
        else
            item.skin:SetVisible(false)
            item.skin=nil
        end
    end
    rgba(item.frame,item.skin and C.clear
        or item.strong and C.accent
        or item.hovered and C.hover or C.control)
end
local function button(name,value,parent,x,y,w,h,fn,strong)
    local control=frame(name,parent,x,y,w,h,strong and C.accent or C.control)
    control:SetMouseMasking("full")
    local tab=name:sub(1,3)=="Tab"
    local initial=tab and "glass_tab_idle"
        or strong and "glass_primary" or "glass_button"
    local plate=skinTexture(name.."Plate",control,initial)
    local caption=text(name.."Label",control,value,8,math.max(1,(h-21)/2),w-16,22,15,
        strong and C.bg or C.text,true)
    controls=controls or {}
    controls[name]={frame=control,label=caption,skin=plate,asset=plate and initial,
        tab=tab,strong=strong,active=false,hovered=false}
    repaintControl(name)
    control:EventAttach(Event.UI.Input.Mouse.Left.Click,function()
        if type(fn)=="function" then fn() end
    end,ADDON.." "..name.." clicked")
    if Event.UI.Input.Mouse.Cursor and Event.UI.Input.Mouse.Cursor.In then
        control:EventAttach(Event.UI.Input.Mouse.Cursor.In,function()
            repaintControl(name,true)
        end,ADDON.." "..name.." hover")
    end
    if Event.UI.Input.Mouse.Cursor and Event.UI.Input.Mouse.Cursor.Out then
        control:EventAttach(Event.UI.Input.Mouse.Cursor.Out,function()
            repaintControl(name,false)
        end,ADDON.." "..name.." leave")
    end
    return control,caption
end
local function place(obj,parent,x,y,w,h)
    if not obj then return end
    obj:ClearAll()
    obj:SetPoint("TOPLEFT",parent,"TOPLEFT",math.floor(x),math.floor(y))
    obj:SetWidth(math.max(1,math.floor(w)))
    obj:SetHeight(math.max(1,math.floor(h)))
end
local function placeButton(name,parent,x,y,w,h)
    local b=controls and controls[name]
    if not b then return end
    place(b.frame,parent,x,y,w,h)
    if b.skin then place(b.skin,b.frame,0,0,w,h) end
    place(b.label,b.frame,8,math.max(1,(h-21)/2),w-16,22)
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
    local previous=lastFocusState
    if focusIndicator and (force or previous~=state) then
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
    -- The footer is shared by import receipts, command results and focus
    -- instructions. Only refresh a *focus-specific* footer on a state change;
    -- never overwrite unrelated status or leave stale success visible.
    if previous~=state and statusField
        and type(statusField.GetText)=="function" then
        local ok,message=pcall(statusField.GetText,statusField)
        if ok and type(message)=="string"
            and message:sub(1,7)=="FOCUS: " then
            local current=state=="focused" and "FOCUS: Editor focused • local commands start with :"
                or state=="search" and "FOCUS: SEARCH FOCUSED"
                or state=="hidden" and "FOCUS: WINDOW HIDDEN"
                or state=="unfocused" and "FOCUS: INPUT NOT FOCUSED • click FOCUS INPUT"
                or "FOCUS: Input focus unavailable"
            statusField:SetText(current)
        end
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
        notifyUi("FOCUS: Editor focused • local commands start with :")
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
local function boundedUtf8(str,maximum)
    if Core and type(Core.utf8Prefix)=="function" then
        return Core.utf8Prefix(str,maximum)
    end
    return str:sub(1,maximum)
end
local function cutUtf8(str,maximum)
    if #str<=maximum then return str end
    return boundedUtf8(str,maximum).."..."
end
local function selectedMessage()
    if not model or not selectedId then return nil,"no_selection" end
    return model:getMessage(selectedId)
end
-- A detail reader is a true modal, not a transparent overlay of active
-- history rows. Same-layer sibling ordering is undefined in RIFT, so hiding
-- the backing rows is required to prevent overlapping glyphs and hitboxes.
local function showHistoryRows(visible)
    for i,item in ipairs(rows or {}) do
        item.frame:SetVisible(visible and i<=LINES)
    end
end
local function closeDetails()
    selectedId=nil
    detailPageIndex=1
    if detailOverlay then detailOverlay:SetVisible(false) end
    showHistoryRows(true)
    return true
end
local function copyMessage()
    local row,err=selectedMessage()
    if not row then return nil,err end
    if not Command or type(Command.CopyToClipboard)~="function" then
        notifyUi("Clipboard unavailable.");return nil,"clipboard_unavailable"
    end
    local text=row.kind=="import" and (Core.rowLabel(row).." "..row.source..": "..row.text)
        or (row.source..": "..row.text)
    local ok,result=pcall(Command.CopyToClipboard,text)
    if not ok or result==false then
        notifyUi("Copy message failed.");return nil,"clipboard_failed"
    end
    notifyUi("Copied complete message #"..tostring(row.id).." ("..#text.." bytes).")
    return true
end
refreshDetail=function()
    if not selectedId or not detailBody then return end
    local record=selectedMessage()
    if not record then return end
    local body=record.text
    local columns=math.max(18,math.floor((detailBody:GetWidth()-20)/11))
    local lines=math.max(1,math.floor(detailBody:GetHeight()/23))
    local capacity=math.max(28,math.floor(columns*lines*0.72))
    local pages,first={},1
    while first<=#body do
        local last=math.min(#body,first+capacity-1)
        -- Split UTF-8 at a lead-byte boundary; never start on a continuation.
        while last<#body and last>=first do
            local nextByte=body:byte(last+1)
            if not nextByte or nextByte<128 or nextByte>=192 then break end
            last=last-1
        end
        if last<first then last=first end
        pages[#pages+1]=body:sub(first,last)
        first=last+1
    end
    if #pages==0 then pages={""} end
    detailPageIndex=math.max(1,math.min(detailPageIndex,#pages))
    detailBody:SetText(pages[detailPageIndex])
    if detailPageStatus then
        detailPageStatus:SetText("PAGE "..detailPageIndex.."/"..#pages)
    end
end
local function detailPageStep(amount)
    if not selectedId then return end
    detailPageIndex=math.max(1,detailPageIndex+amount)
    refreshDetail()
end
local function openMessage(id)
    if not model then return nil,"not_ready" end
    local row,err=model:getMessage(id)
    if not row then return nil,err end
    selectedId=id
    detailPageIndex=1
    if detailOverlay and detailBody and detailTitle then
        detailTitle:SetText(string.format("%s  •  %s  •  #%d",
            Core.rowLabel(row),row.source,row.id))
        showHistoryRows(false)
        detailOverlay:SetVisible(true)
        refreshDetail()
    end
    return true
end
render=function()
    if not model or not panel or not rows then return end
    -- :find and /rcm find can update the model independently of the textfield.
    -- Keep the displayed query synchronized without resetting matching input.
    if searchField and searchField:GetText()~=model.search then
        searchField:SetText(model.search)
    end
    local selection,total=model:getHistory(model.filter,model.search,LINES,visibleOffset)
    local oldestOffset=total>0 and math.floor((total-1)/LINES)*LINES or 0
    if visibleOffset>oldestOffset then
        visibleOffset=oldestOffset
        selection,total=model:getHistory(model.filter,model.search,LINES,visibleOffset)
    end
    -- Each row owns four independent text frames rather than one padded
    -- monolithic string. This keeps channel/source provenance visible while
    -- allowing the message to claim every remaining pixel on resize.
    for i=1,LINES do
        local item=rows[i]
        local r=selection[i]
        item.messageId=r and r.id or nil
        if r then
            local ts="--:--:--"
            if os and os.date then
                -- Local Windows time, with seconds. The stored epoch is never
                -- rewritten and time formatting never affects message data.
                local ok,value=pcall(os.date,"%H:%M:%S",math.floor(r.at))
                if ok and type(value)=="string" then ts=value end
            end
            local color=r.kind=="import" and C.accent
                or r.kind=="npc" and C.good
                or r.kind=="system" and C.warning
                or r.kind=="dev" and C.info or C.accent
            item.time:SetText(ts)
            item.channel:SetText("["..cutUtf8(Core.rowShortLabel(r),12).."]")
            item.sender:SetText(cutUtf8(r.source,
                math.max(6,math.floor(item.sender:GetWidth()/7.5)-2)))
            item.entry:SetText(cutUtf8(r.text,
                math.max(12,math.floor(item.entry:GetWidth()/8.2)-2)))
            ink(item.time,C.muted)
            ink(item.channel,color)
            ink(item.sender,r.kind=="npc" and C.good or C.text)
            ink(item.entry,C.text)
            rgba(item.marker,color)
            item.marker:SetVisible(true)
        else
            item.time:SetText("")
            item.channel:SetText("")
            item.sender:SetText("")
            item.entry:SetText("")
            item.marker:SetVisible(false)
        end
    end
    local nativeActive=controls._native.active==true
    if controls._native.panel then
        controls._native.panel:SetVisible(nativeActive)
    end
    if nativeActive then
        showHistoryRows(false)
        if controls._native.paint then controls._native.paint() end
    elseif not selectedId then
        showHistoryRows(true)
    end
    local count=math.max(0,total-visibleOffset)
    local first=#selection>0 and (count-#selection+1) or 0
    if selectedId then
        local current=model:getMessage(selectedId)
        if not current then closeDetails() end
    end
    if nativeActive then
        notifyUi("Read-only RIFT console subscriptions; no native player-chat transcript")
    else
        notifyUi(string.format("%d messages  •  showing %d–%d  •  %s  •  native chat separate",
            total,first,count,model.filter))
    end
    if controls.PageUp and controls.PageDown then
        controls.PageUp.label:SetText(nativeActive and "PREV" or "OLDER")
        controls.PageDown.label:SetText(nativeActive and "NEXT" or "NEWER")
    end
    for key,label in pairs(tabLabels or {}) do
        local selected=nativeActive and key=="native"
            or (not nativeActive and (key==model.filter
                or key=="imports" and model.filter=="chat"))
        ink(label,selected and C.accent or C.muted)
        local item=controls and controls["Tab"..key]
        if item and item.active~=selected then
            item.active=selected
            repaintControl("Tab"..key)
        end
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
    lastEditorImportReceipt=nil
    -- RCM editor has its own import route. Reuse the SAME bounded receiver
    -- as native /rcm import; no second decoder, persistent queue or file IO.
    local verb=type(value)=="string" and
        value:match("^%s*:([a-zA-Z][a-zA-Z0-9_]*)")
    if verb and verb:lower()=="import" then
        if #value>160 then return nil,"import_command_too_long" end
        local rest=value:match("^%s*:[a-zA-Z][a-zA-Z0-9_]*%s+(.-)%s*$")
        if not rest or rest=="" then return nil,"import_usage" end
        if not hostIngress then return nil,"host_import_unavailable" end
        if rest=="help" then
            lastEditorImportReceipt=":import ID INDEX/TOTAL BASE64URL | status | cancel"
        elseif rest=="status" then
            local state=hostIngress:status(clock())
            lastEditorImportReceipt=state.pending and
                ("HOST import "..state.pendingParts.."/"..state.pendingTotal
                 .." parts pending; native chat/disk unverified.") or
                ("HOST imports="..state.imported.." duplicates="..state.duplicates
                 .."; native chat/disk unverified.")
        elseif rest=="cancel" then
            local ok,why=hostIngress:cancelPending()
            if not ok then return nil,why end
            lastEditorImportReceipt="Pending HOST import cancelled; saved chat unchanged."
        else
            local ok,why=hostIngress:receiveLine(rest,clock())
            if not ok then return nil,why end
            local state=hostIngress:status(clock())
            if why=="imported_unverified" then
                lastEditorImportReceipt="HOST import saved in RCM history #"
                    ..tostring(state.lastImportedMessageId or "unknown")
                    .."; native player chat and disk persistence NOT verified."
            elseif why=="already_imported" or why=="already_received" then
                lastEditorImportReceipt="HOST import duplicate ignored ("..why..")."
            else
                lastEditorImportReceipt="HOST import "..state.pendingParts
                    .."/"..state.pendingTotal.." parts (unverified)."
            end
        end
        notifyUi(lastEditorImportReceipt)
        return true
    end
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
    rememberExecuted(value)
    editor:SetText("")
    visibleOffset=0
    -- Copy writes a useful receipt into the footer; preserve it until changed.
    if not value:match("^%s*:copy%s*$") then render() end
    -- render updates the standard footer; restore the precise import receipt.
    if lastEditorImportReceipt then notifyUi(lastEditorImportReceipt) end
    lastEditorImportReceipt=nil
    return true
end
-- Central layout pass; parent-relative anchors are recalculated only on size change.
local function makeRow(i)
    local row=frame("Line"..i,list,5,6+(i-1)*ROW_H,656,ROW_H,
        i%2==0 and C.card or C.alt)
    row:SetMouseMasking("full")
    local marker=frame("LineMarker"..i,row,2,3,3,ROW_H-6,C.accent)
    rows[i]={
        time=text("LineTime"..i,row,"",12,2,72,22,14,C.muted,true),
        channel=text("LineChannel"..i,row,"",90,2,124,22,14,C.accent,true),
        sender=text("LineSender"..i,row,"",222,2,115,22,15,C.text,true),
        entry=text("LineText"..i,row,"",345,2,301,22,16,C.text),
        frame=row,marker=marker,messageId=nil}
    row:EventAttach(Event.UI.Input.Mouse.Left.Click,function()
        local id=rows[i].messageId
        if id then openMessage(id) end
    end,ADDON.." open message "..i)
end
layoutWindow=function()
    if not panel or not list or not rows or not controls then return end
    local w,h=W,H
    if controls._skin.panel then place(controls._skin.panel,panel,0,0,w,h) end
    place(header,panel,0,0,w,58)
    if controls._skin.header then place(controls._skin.header,header,0,0,w,58) end
    place(handle,header,0,0,w-380,58)
    place(titleFrame,handle,18,15,math.min(320,w-407),28)
    place(focusIndicator,header,w-377,20,188,24)
    place(versionFrame,header,w-181,19,118,22)
    placeButton("Close",header,w-45,11,34,34)
    place(divider,panel,0,58,w,1)
    local tabWidth=(w-32-(#TAB_ORDER-1)*8)/#TAB_ORDER
    for i,name in ipairs(TAB_ORDER) do
        placeButton("Tab"..name,panel,16+(i-1)*(tabWidth+8),69,tabWidth,34)
    end
    place(findLabel,panel,17,118,60,25)
    if controls._skin.search then place(controls._skin.search,panel,84,111,w-254,33) end
    place(searchField,panel,84,111,w-254,33)
    placeButton("FindReset",panel,w-155,111,75,33)
    placeButton("PageUp",panel,w-74,160,64,34)
    placeButton("PageDown",panel,w-74,205,64,34)
    local cardW,cardH=w-94,h-292
    place(list,panel,14,154,cardW,cardH)
    if controls._skin.history then place(controls._skin.history,list,0,0,cardW,cardH) end
    local count=math.min(MAX_ROWS,math.max(1,math.floor((cardH-10)/ROW_H)))
    for i=#rows+1,count do makeRow(i) end
    LINES=count
    for i,row in ipairs(rows) do
        if i<=count then
            local rowW=cardW-10
            local senderW=rowW<=620 and 92 or 115
            local bodyX=222+senderW+8
            place(row.frame,list,5,6+(i-1)*ROW_H,rowW,ROW_H)
            place(row.marker,row.frame,2,3,3,ROW_H-6)
            place(row.time,row.frame,12,2,72,22)
            place(row.channel,row.frame,90,2,124,22)
            place(row.sender,row.frame,222,2,senderW,22)
            place(row.entry,row.frame,bodyX,2,rowW-bodyX-8,22)
            row.frame:SetVisible(not selectedId)
        else
            row.messageId=nil
            row.frame:SetVisible(false)
            -- Park hidden rows inside the card for reliable viewport tests.
            place(row.frame,list,5,6,cardW-10,ROW_H)
        end
    end
    local overlayW,overlayH=cardW-8,cardH-8
    place(detailOverlay,list,4,4,overlayW,overlayH)
    local native=controls._native
    if native.panel then
        place(native.panel,list,4,4,overlayW,overlayH)
        place(native.title,native.panel,14,10,math.max(100,overlayW-278),24)
        placeButton("NativeSource",native.panel,overlayW-250,9,132,27)
        placeButton("NativeRefresh",native.panel,overlayW-110,9,98,27)
        local groupWidth=(overlayW-20-4*6)/5
        for i,entry in ipairs(native.groupButtons or {}) do
            placeButton("NativeGroup"..entry[1],native.panel,
                10+(i-1)*(groupWidth+6),42,groupWidth,30)
        end
        native.pageSize=math.max(2,math.min(16,math.floor((overlayH-128)/23)))
        for i,line in ipairs(native.line) do
            place(line.label,native.panel,18,82+(i-1)*23,overlayW-122,23)
            place(line.state,native.panel,overlayW-85,82+(i-1)*23,65,23)
        end
        place(native.note,native.panel,14,overlayH-29,overlayW-28,22)
    end
    if controls._skin.detail then place(controls._skin.detail,detailOverlay,0,0,overlayW,overlayH) end
    place(detailTitle,detailOverlay,14,13,overlayW-138,25)
    place(detailBody,detailOverlay,14,51,overlayW-28,math.max(24,overlayH-124))
    placeButton("DetailCopy",detailOverlay,14,overlayH-51,162,36)
    placeButton("DetailPrev",detailOverlay,185,overlayH-51,74,36)
    placeButton("DetailNext",detailOverlay,269,overlayH-51,74,36)
    place(detailPageStatus,detailOverlay,352,overlayH-43,100,22)
    placeButton("DetailClose",detailOverlay,overlayW-107,overlayH-51,94,36)
    if selectedId then refreshDetail() end
    -- Distribute action buttons proportionally across the available width.
    local available=w-28-3*10
    local x=14
    for i,name in ipairs(ACTION_ORDER) do
        local width=i==4 and (w-14-x) or math.floor(available*ACTION_WEIGHTS[i])
        placeButton(name,panel,x,h-128,width,35)
        x=x+width+10
    end
    if controls._skin.input then place(controls._skin.input,panel,14,h-83,w-128,40) end
    place(editor,panel,14,h-83,w-128,40)
    placeButton("Send",panel,w-105,h-83,90,40)
    place(statusField,panel,16,h-31,w-65,24)
    place(resizeGrip,panel,w-30,h-30,26,26)
end
local function resizeTo(width,height,save)
    if not panel or not finite(width) or not finite(height) then
        return nil,"invalid_window_size"
    end
    local vw,vh=UIParent:GetWidth(),UIParent:GetHeight()
    if not finite(vw) or not finite(vh) or vw<=0 or vh<=0 then
        return nil,"invalid_viewport"
    end
    -- A dragged corner cannot push the opposite edges offscreen.
    local maxW=math.max(1,math.floor(vw-panel:GetLeft()))
    local maxH=math.max(1,math.floor(vh-panel:GetTop()))
    local nextW=math.max(math.min(MIN_W,maxW),math.min(maxW,math.floor(width+0.5)))
    local nextH=math.max(math.min(MIN_H,maxH),math.min(maxH,math.floor(height+0.5)))
    if nextW~=W or nextH~=H then
        W,H=nextW,nextH
        panel:SetWidth(W);panel:SetHeight(H)
        layoutWindow()
        render()
    end
    if save then saveGeometry() end
    return true
end
local function startResize()
    if drag or resize or not panel then return end
    local m=mouse()
    if not m then return end
    resize={mx=m.x,my=m.y,w=W,h=H}
    rgba(resizeGrip,C.accent)
end
local function resizeMove(save)
    if not resize then return end
    local m=mouse()
    if m then
        resizeTo(resize.w+m.x-resize.mx,resize.h+m.y-resize.my,save)
    elseif save then
        saveGeometry()
    end
end
local function stopResize()
    if not resize then return end
    resizeMove(true)
    resize=nil
    if resizeGrip then rgba(resizeGrip,C.control) end
end
local function makeUi()
    if panel then return end
    context=UI.CreateContext("RiftChatModernContext")
    local ui=model and type(model.saved.ui)=="table" and model.saved.ui or nil
    local vw,vh=UIParent:GetWidth(),UIParent:GetHeight()
    -- Sanitize old/malformed sizes without altering character history.
    local maxW,maxH=math.max(1,math.floor(vw)),math.max(1,math.floor(vh))
    local savedW=ui and finite(ui.w) and ui.w or DEFAULT_W
    local savedH=ui and finite(ui.h) and ui.h or DEFAULT_H
    W=math.min(maxW,math.max(math.min(MIN_W,maxW),math.floor(savedW+0.5)))
    H=math.min(maxH,math.max(math.min(MIN_H,maxH),math.floor(savedH+0.5)))
    panel=UI.CreateFrame("Frame","RiftChatModernWindow",context)
    panel:SetWidth(W);panel:SetHeight(H)
    rgba(panel,C.bg)
    shift(ui and finite(ui.x) and ui.x or math.max(0,math.floor((vw-W)/2)),
        ui and finite(ui.y) and ui.y or math.max(0,math.floor((vh-H)/3)),false)
    lastViewportW,lastViewportH=vw,vh
    controls._skin.panel=controls._skinTexture("PanelPlate",panel,"glass_panel",-100)
    if controls._skin.panel then rgba(panel,C.clear) end
    header=frame("Header",panel,0,0,W,58,C.header)
    controls._skin.header=controls._skinTexture("HeaderPlate",header,"glass_header")
    if controls._skin.header then rgba(header,C.clear) end
    -- The drag surface is only over the title. The close button remains clickable.
    handle=frame("DragHandle",header,0,0,370,58)
    handle:SetMouseMasking("full")
    handle:EventAttach(Event.UI.Input.Mouse.Left.Down,startDrag,ADDON.." drag start")
    handle:EventAttach(Event.UI.Input.Mouse.Left.Up,stopDrag,ADDON.." drag stop")
    handle:EventAttach(Event.UI.Input.Mouse.Left.Upoutside,stopDrag,ADDON.." drag outside")
    titleFrame=text("Title",handle,"RIFT CHAT  /  MODERN",18,15,320,28,21,C.text,true)
    focusIndicator=text("FocusIndicator",header,"INPUT  •  HIDDEN",
        383,20,188,24,14,C.muted,true)
    versionFrame=text("Version",header,"v"..VERSION,579,19,118,22,16,C.accent,true)
    button("Close","×",header,715,11,34,34,function()
        if resize then stopResize() end
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
    divider=frame("Divider",panel,0,58,W,1,C.accent)
    tabLabels={}
    local tabs={{"all","ALL"},{"imports","IMPORTS"},
        {"system","NOTICES"},{"npc","NPC SAY"},{"addons","ADDONS"},{"dev","DEV"},
        {"native","CONSOLE"}}
    for i,tab in ipairs(tabs) do
        local name,display=tab[1],tab[2]
        local b,label=button("Tab"..name,display,panel,16+(i-1)*122,69,110,34,
            function()
                if name=="native" then
                    closeDetails()
                    controls._native.active=true
                    controls._native.snapshot=nil
                    controls._native.page=0
                else
                    controls._native.active=false
                    model:setFilter(name);visibleOffset=0
                end
                render()
            end)
        label:SetFontSize(13)
        tabLabels[name]=label
    end
    findLabel=text("FindLabel",panel,"SEARCH",17,118,60,25,15,C.muted,true)
    controls._skin.search=controls._skinTexture("SearchPlate",panel,"glass_input",-20)
    searchField=UI.CreateFrame("RiftTextfield","RCMSearchField",panel)
    searchField:SetPoint("TOPLEFT",panel,"TOPLEFT",84,111)
    searchField:SetWidth(506);searchField:SetHeight(33)
    pcall(function() searchField:SetFontSize(16) end)
    rgba(searchField,controls._skin.search and C.input or C.control)
    searchField:SetText(model.search)
    if Event.UI.Textfield and Event.UI.Textfield.Change then
        searchField:EventAttach(Event.UI.Textfield.Change,function()
            local val=searchField:GetText() or ""
            if #val<=60 and val~=model.search then model:setSearch(val);visibleOffset=0;render() end
        end,ADDON.." search updated")
    end
    button("FindReset","RESET",panel,605,111,75,33,function()
        searchField:SetText(""); model:setSearch("");visibleOffset=0;render()
    end)
    button("PageUp","OLDER",panel,686,160,64,34,function()
        if controls._native.active then
            controls._native.page=math.max(0,controls._native.page-1)
            render();return
        end
        local _,total=model:getHistory(model.filter,model.search,1,0)
        local oldestOffset=total>0 and math.floor((total-1)/LINES)*LINES or 0
        visibleOffset=math.min(oldestOffset,visibleOffset+LINES)
        render()
    end)
    button("PageDown","NEWER",panel,686,205,64,34,function()
        if controls._native.active then
            controls._native.page=controls._native.page+1
            render();return
        end
        visibleOffset=math.max(0,visibleOffset-LINES);render()
    end)
    rows={}
    list=frame("MessageCard",panel,14,154,666,326,C.card)
    controls._skin.history=controls._skinTexture("HistoryPlate",list,"glass_history")
    if controls._skin.history then rgba(list,C.clear) end
    -- Actual message rows are created lazily by layoutWindow().
    -- Complete-message reader overlays only the message list, not the controls.
    -- The regular rows remain available immediately after CLOSE.
    detailOverlay=frame("DetailOverlay",list,4,4,658,318,C.header)
    -- The detail reader is a modal: backing history siblings are hidden
    -- while open. Preserve the RIFT-tested child/texture layer relationship
    -- (negative-layer background, default-layer text/buttons) rather than
    -- moving the parent above its own children.
    controls._skin.detail=controls._skinTexture("DetailPlate",detailOverlay,"glass_detail")
    rgba(detailOverlay,C.header)
    detailOverlay:SetMouseMasking("full")
    detailTitle=text("DetailTitle",detailOverlay,"MESSAGE DETAILS",
        14,13,520,25,18,C.accent,true)
    detailBody=text("DetailBody",detailOverlay,"",
        14,51,630,194,16,C.text)
    detailBody:SetWordwrap(true)
    button("DetailCopy","COPY MESSAGE",detailOverlay,14,267,162,36,
        copyMessage,true)
    button("DetailPrev","PREV",detailOverlay,185,267,74,36,
        function() detailPageStep(-1) end)
    button("DetailNext","NEXT",detailOverlay,269,267,74,36,
        function() detailPageStep(1) end)
    detailPageStatus=text("DetailPageStatus",detailOverlay,"PAGE 1/1",
        352,275,100,22,14,C.muted,true)
    button("DetailClose","CLOSE",detailOverlay,551,267,94,36,closeDetails)
    detailOverlay:SetVisible(false)
    -- Read-only native RIFT console inspector. These are configured
    -- subscriptions from Inspect.Console.Detail, not received social text.
    local native=controls._native
    native.panel=frame("NativeCatalog",list,4,4,658,318,C.header)
    native.panel:SetMouseMasking("full")
    native.title=text("NativeCatalogTitle",native.panel,"RIFT CONSOLE SETTINGS",
        14,12,300,24,17,C.accent,true)
    native.note=text("NativeCatalogNote",native.panel,
        "Subscription metadata only; NOT a chat transcript",
        14,289,600,22,13,C.muted)
    native.line={}
    for i=1,16 do
        native.line[i]={
            label=text("NativeCategoryLabel"..i,native.panel,"",
                18,82+(i-1)*23,380,23,16,C.text),
            state=text("NativeCategoryState"..i,native.panel,"",
                520,82+(i-1)*23,90,23,15,C.muted,true)}
    end
    native.groupButtons={{"game","GAME"},{"loot","LOOT"},{"player","PLAYER"},
        {"public","CHANNELS"},{"combat","COMBAT"}}
    for _,entry in ipairs(native.groupButtons) do
        local key,title=entry[1],entry[2]
        button("NativeGroup"..key,title,native.panel,10,42,95,30,function()
            native.group=key;native.page=0;render()
        end)
    end
    button("NativeSource","NEXT CONSOLE",native.panel,395,9,127,27,function()
        local snapshot=native.snapshot
        local count=snapshot and snapshot.consoleCount or 0
        if count>0 then
            local _,index=controls._categories.choose(snapshot,native.sourceIndex)
            native.sourceIndex=index%count+1
            native.page=0
        end
        render()
    end)
    button("NativeRefresh","REFRESH",native.panel,532,9,101,27,function()
        native.snapshot=nil
        native.page=0
        render()
    end)
    native.panel:SetVisible(false)
    button("Copy","COPY HISTORY",panel,14,490,170,35,copyHistory,true)
    button("Clear","CLEAR",panel,195,490,98,35,function()
        if controls._native.active then
            if statusField then
                statusField:SetText("History CLEAR is disabled in read-only CONSOLE view")
            end
            return
        end
        closeDetails();model:clear();visibleOffset=0;render()
    end)
    button("Focus","FOCUS INPUT",panel,304,490,145,35,focusEditor)
    local _,caption=button("Mirror","MIRROR OFF",panel,465,490,174,35,
        function() setMirror(not mirrorStatus().enabled) end)
    mirrorButtonLabel=caption
    mirrorButtonLabel:SetText(mirrorStatus().enabled and "MIRROR ON" or "MIRROR OFF")
    controls._skin.input=controls._skinTexture("InputPlate",panel,"glass_input",-20)
    editor=UI.CreateFrame("RiftTextfield","RCMInput",panel)
    editor:SetPoint("TOPLEFT",panel,"TOPLEFT",14,535)
    editor:SetWidth(632);editor:SetHeight(40)
    pcall(function() editor:SetFontSize(18) end)
    editor:SetText("")
    rgba(editor,controls._skin.input and C.input or C.control)
    if editor.Event then
        -- RIFT Textfield's native KeyDown is the proven input path (LuaPadModern).
        function editor.Event:KeyDown(key)
            if not panel or not panel:GetVisible() or type(key)~="string" then return end
            local normalized=key:lower()
            if key:byte(1)==13 or key:byte(1)==10
                or normalized=="enter" or normalized=="return" then
                submit()
            elseif normalized=="up" or normalized=="arrowup" then
                controls._commandActions.recall("older")
            elseif normalized=="down" or normalized=="arrowdown" then
                controls._commandActions.recall("newer")
            end
        end
    end
    if Event.UI.Textfield and Event.UI.Textfield.Change then
        editor:EventAttach(Event.UI.Textfield.Change,function()
            -- Typing or pasting into recalled text exits history navigation.
            controls._commandActions.changed(editor:GetText() or "")
        end,ADDON.." input changed")
    end
    if Event.UI.Input.Mouse.Left.Click then
        editor:EventAttach(Event.UI.Input.Mouse.Left.Click,function()
            focusEditor()
        end,ADDON.." editor click focus")
    end
    button("Send","RUN",panel,655,535,90,40,submit,true)
    statusField=text("Status",panel,"",16,587,726,24,14,C.muted)
    resizeGrip=frame("ResizeGrip",panel,W-30,H-30,26,26,C.control)
    resizeGrip:SetMouseMasking("full")
    text("ResizeGlyph",resizeGrip,"//",4,2,18,21,17,C.text,true)
    resizeGrip:EventAttach(Event.UI.Input.Mouse.Left.Down,startResize,
        ADDON.." resize start")
    resizeGrip:EventAttach(Event.UI.Input.Mouse.Left.Up,stopResize,
        ADDON.." resize stop")
    resizeGrip:EventAttach(Event.UI.Input.Mouse.Left.Upoutside,stopResize,
        ADDON.." resize outside")
    if Event.UI.Input.Mouse.Cursor and Event.UI.Input.Mouse.Cursor.In then
        resizeGrip:EventAttach(Event.UI.Input.Mouse.Cursor.In,function()
            if not resize then rgba(resizeGrip,C.hover) end
        end,ADDON.." resize grip hover")
    end
    if Event.UI.Input.Mouse.Cursor and Event.UI.Input.Mouse.Cursor.Out then
        resizeGrip:EventAttach(Event.UI.Input.Mouse.Cursor.Out,function()
            if not resize then rgba(resizeGrip,C.control) end
        end,ADDON.." resize grip leave")
    end
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
    layoutWindow()
    panel:SetVisible(false)
    updateFocusIndicator(true)
    render()
end
local function show(yes)
    if not model then return nil,"not_ready" end
    makeUi()
    if not yes then
        closeDetails()
        if resize then stopResize() end
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
-- The importer tracks only this session's transfer tokens, while real
-- history rows can survive reloads. Query the retained model separately so
-- the ID remains discoverable without fabricating a disk-save receipt.
local function hostIngressStatus()
    local state=hostIngress and hostIngress:status(clock()) or
        {ready=false,mode="unavailable",liveChatVerified=false,
         autoInputAvailable=false}
    if model then
        local rows,total=model:getHistory("imports","",1,0)
        state.retainedImportCount=total or 0
        state.lastRetainedImportMessageId=rows and rows[1] and rows[1].id or nil
    else
        state.retainedImportCount=0
    end
    return state
end
local function hostStatusSummary()
    if not hostIngress then return "Host manual import unavailable." end
    local state=hostIngressStatus()
    local summary=string.format("host candidate imports=%d | rejects=%d | duplicates=%d | cancelled=%d | expired=%d",
        state.imported,state.rejected,state.duplicates,state.cancelled,state.expired)
    if state.lastImportedMessageId then
        summary=summary.." | last imported history #"..state.lastImportedMessageId
            .." (NOT verified on disk)"
    end
    if state.lastRetainedImportMessageId then
        summary=summary.." | latest retained import history #"
            ..state.lastRetainedImportMessageId.." (NOT verified on disk)"
    end
    if state.pending then
        return string.format("Host import %s: %d/%d chunks | %s",
            state.pendingId,state.pendingParts,state.pendingTotal,summary)
    end
    return "Host import idle | "..summary
end
local function hostCommand(args)
    args=(args or ""):lower()
    if args=="" or args=="status" then return hostStatusSummary() end
    if args=="cancel" then
        if not hostIngress then return "Host manual import unavailable." end
        local ok,reason=hostIngress:cancelPending()
        return ok and "Pending host import cancelled; saved chat unchanged."
            or "No pending host import to cancel ("..tostring(reason)..")."
    end
    return "Usage: :host status | cancel (manual import only)"
end
local function checkpointSummary()
    local state=saveStatus()
    local phase=state.saveEventReceiptAvailable
        and ("RIFT Save.Begin receipt #"..state.eventSequence
             .." (history "..state.historyCountAtEvent..")")
        or "No RIFT Save.Begin receipt stored"
    return phase.." | session changes: "..
        (state.pendingSessionChanges and "yes" or "no")
        .." | on-disk save NOT independently verified."
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
    elseif verb=="size" then
        local requestedW,requestedH=rest:match("^(%d+)%s+(%d+)$")
        if rest=="reset" then requestedW,requestedH=DEFAULT_W,DEFAULT_H end
        if not requestedW then
            notice("Usage: /rcm size WIDTH HEIGHT | reset")
        else
            makeUi()
            local ok,err=resizeTo(tonumber(requestedW),tonumber(requestedH),true)
            notice(ok and ("Window size "..W.."x"..H) or ("Size failed: "..tostring(err)))
        end
    elseif verb=="checkpoint" then notice(checkpointSummary())
    elseif verb=="import" then
        -- Every intermediate receipt must be visible in native chat even if
        -- the RCM addon window is hidden during the manual transfer.
        if rest=="status" then notice(hostStatusSummary())
        elseif rest=="cancel" then notice(hostCommand("cancel"))
        elseif rest=="help" then
            notice("/rcm import ID INDEX/TOTAL BASE64URL | status | cancel")
        elseif not hostIngress then notice("Host import unavailable.")
        else
            local ok,result=hostIngress:receiveLine(rest,clock())
            if not ok then
                notice("Host import rejected: "..tostring(result))
            elseif result=="imported_unverified" then
                local receipt=hostIngress:status(clock())
                if receipt.lastImportedMessageId then
                    notice("Host candidate imported as RCM history #"
                        ..receipt.lastImportedMessageId
                        .."; NOT verified native chat; NOT verified on disk.")
                else
                    notice("Host candidate imported; history ID unavailable; NOT verified native chat; NOT verified on disk.")
                end
            elseif result=="already_imported" or result=="already_received" then
                notice("Host import duplicate chunk ignored ("..result..").")
            else
                local progress=hostIngress:status(clock())
                notice(string.format("Host import %s: %d/%d chunks received (NOT verified native chat)",
                    tostring(progress.pendingId or "unknown"),
                    progress.pendingParts,progress.pendingTotal))
            end
        end
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
        notice("/rcm [show|hide|focus|status|copy|clear|import ID PART/TOTAL B64|import status|import cancel|size W H|size reset]")
        notice("Input: :import ID INDEX/TOTAL BASE64URL | :host status | :mirror | :native | :logprobe | :addon ...")
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
-- A read-only view of RIFT's *configured* console subscriptions. This
-- cannot read the message transcript or change the game's console options.
controls._native.paint=function()
    local view=controls._native
    if not view.panel or not view.active then return end
    if not view.snapshot then view.snapshot=getNativeConsoles() end
    local catalog=controls._categories
    if not catalog then
        view.title:SetText("RIFT CONSOLE SETTINGS • categories unavailable")
        view.note:SetText("No native category registry loaded.")
        for _,line in ipairs(view.line) do
            line.label:SetVisible(false);line.state:SetVisible(false)
        end
        return
    end
    local group=catalog.group(view.snapshot,view.group,view.sourceIndex)
    if not group then return end
    local pagesize=view.pageSize or 8
    local total=#group.entries
    local pages=math.max(1,math.ceil(total/pagesize))
    view.page=math.min(math.max(0,view.page),pages-1)
    view.title:SetText(group.consoleName.." • "..group.title)
    for i,line in ipairs(view.line) do
        local index=view.page*pagesize+i
        local entry=i<=pagesize and group.entries[index] or nil
        line.label:SetVisible(entry~=nil)
        line.state:SetVisible(entry~=nil)
        if entry then
            line.label:SetText(entry.label)
            line.state:SetText(entry.state)
            local color=entry.state=="ON" and C.good
                or entry.state=="OFF" and C.muted
                or entry.state=="N/A" and C.warning or C.info
            ink(line.state,color)
            ink(line.label,C.text)
        end
    end
    if group.id=="public" and total==0 then
        view.note:SetText("No enabled public names reported; disabled names unknown")
    else
        view.note:SetText(string.format("%d ON / %d OFF / %d ? / %d N/A  •  page %d/%d  •  no chat text",
            group.enabled,group.disabled,group.unknown,group.notExposed,
            view.page+1,pages))
    end
    for _,item in ipairs(view.groupButtons or {}) do
        local ref=controls["NativeGroup"..item[1]]
        if ref then ink(ref.label,item[1]==view.group and C.good or C.text) end
    end
end
local nativeChannelNames={"say","yell","tell","party","raid","raidWarning",
    "guild","officer","system","npc","emote","combatGood","combatBad",
    "combatOther","combatNeutral","combatSpecial","craftingSelf",
    "craftingOther","lootMoney","lootGroup","lootItem","experience",
    "achievement","notoriety","skill","purchase","accolade"}
local function nativeProbeCommand(args)
    local data=getNativeConsoles()
    args=(args or ""):lower()
    local catalog=controls._categories
    if args=="help" then
        return ":native view | groups | game | loot | player | public | combat | channels | copy (subscriptions, NOT messages)"
    elseif args=="view" then
        closeDetails()
        controls._native.active=true
        controls._native.group="game"
        controls._native.page=0
        controls._native.snapshot=data
        if panel then render() end
        return "Read-only RIFT console subscriptions view; NOT a chat transcript."
    elseif catalog and (args=="groups" or args=="map") then
        return boundedUtf8(catalog.overview(data),512)
    elseif catalog and (args=="game" or args=="loot" or args=="player"
        or args=="public" or args=="combat") then
        local summary=catalog.summary(data,args)
        return summary or "Console subscription categories unavailable."
    end
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
            local public=entry.publicChannels or {}
            local summary=#enabled>0 and table.concat(enabled,", ") or "(none/unknown)"
            if #public>0 then
                summary=summary.." | public: "..table.concat(public,", ")
                if entry.publicChannelsTruncated then summary=summary..", ..." end
            elseif entry.publicChannelsTruncated then
                summary=summary.." | public: (truncated)"
            end
            lines[#lines+1]=(entry.name or entry.id)..": "..summary
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
        return boundedUtf8(description,512)
    end
    return string.format("Native windows: %d (%d visible), configured consoles: %d%s. "
        .."Console subscriptions are metadata, not readable chat messages.",
        data.windowCount,data.visibleCount,data.consoleCount or 0,
        data.consoleListReady and "" or " (list unavailable)")
end

-- Opt-in RIFT-to-host log feasibility marker. Compatible with the existing
-- LuaPadModern read-only LogTailProbe. Emission is NOT proof of disk delivery.
local function logProbeCommand(args)
    if type(args)~="string" or #args<8 or #args>80
        or not args:match("^[A-Za-z0-9_-]+$") then
        return "Usage: :logprobe TOKEN (8-80 ASCII letters, numbers, _ or -)."
    end
    if not Command or not Command.Console
        or type(Command.Console.Display)~="function" then
        return "Log probe unavailable: native console API missing."
    end
    local epoch="unknown"
    if Inspect and Inspect.Time and type(Inspect.Time.Server)=="function" then
        local ok,seconds=pcall(Inspect.Time.Server)
        if ok and finite(seconds) and seconds>=1500000000
            and seconds<4200000000 then
            epoch=string.format("%.3f",seconds)
        end
    end
    local marker="LPB_PROBE|"..args.."|"..epoch
    local ok,result=pcall(Command.Console.Display,"general",false,marker,false)
    if not ok or result==false then
        return "Log probe emission failed; no RIFT-to-host transport evidence."
    end
    return "Probe "..args.." submitted to native console; Log.txt receipt unverified."
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
        RiftChatModernSaved={schemaVersion=2,history={}}
    end
    if not Core or type(Core.new)~="function" then
        notice("Core module missing. Recording disabled.");return
    end
    local m,err=Core.new(RiftChatModernSaved)
    if not m then notice("Saved data rejected: "..tostring(err));return end
    model=m
    if HostIngress and type(HostIngress.new)=="function" then
        hostIngress=HostIngress.new(function(row,at)
            return model:publish(row.kind,row.text,row.source,at,{
                origin=row.origin,channelKind=row.channelKind,
                channelName=row.channelName,importToken=row.importToken})
        end,function(token)
            -- Durable replay check against actual bounded saved history.
            return model:findImportToken(token)~=nil
        end)
    end
    -- Optional cross-repository adapter; no hard dependency or input injection.
    model:registerCommand("rpt",optionalRPT)
    model:registerCommand("addon",sendAddonCommand)
    model:registerCommand("native",nativeProbeCommand)
    model:registerCommand("logprobe",logProbeCommand)
    model:registerCommand("host",hostCommand)
    model:registerCommand("checkpoint",checkpointSummary)
    model:registerCommand("mirror",mirrorCommand)
    if ConsoleMirror and type(ConsoleMirror.new)=="function"
        and Command and Command.Console
        and type(Command.Console.Display)=="function" then
        mirror=ConsoleMirror.new(Command.Console,function(line,channel)
            if model then
                return model:publish("addons",line,
                    ("Console:"..channel):sub(1,40),clock(),{origin="addon_data"})
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
                if not model then return false end
                local line= #from>40 and (from..": "..data) or data
                local row=model:publish("addons",line,from:sub(1,40),clock(),{origin="addon_data"})
                return row~=nil
            end,
            function(note,to)
                if model then
                    model:publish("dev",note,("RCM to "..to):sub(1,40),clock(),{origin="local_addon"})
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
-- RIFT's own save lifecycle is the only supported Lua SavedVariables flush
-- path; never pretend that an addon command can force a disk commit.
local function onSaveBegin(_,name)
    if name~=ADDON or not model then return end
    local state,why=model:recordSaveBegin(clock())
    if not state then
        notice("Save.Begin receipt unavailable: "..tostring(why))
        return
    end
    saveBeginEvents=saveBeginEvents+1
end
local function onSaveEnd(_,name)
    if name~=ADDON or not model then return end
    saveEndEvents=saveEndEvents+1
    -- Do NOT mutate SavedVariables here: serialization may have completed.
end
local function onLoaded(_,name)
    if name~=ADDON or initialized then return end
    initialized=true
    if model then
        makeUi()
        model:publish("system","Modern chat window ready. :help lists local commands.",
            "RiftChatModern",clock(),{origin="local_addon"})
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
    local source=type(info.fromName)=="string" and boundedUtf8(info.fromName,40) or "NPC"
    if #source==0 then source="NPC" end
    model:publish("npc",boundedUtf8(info.message,512),source,clock(),{origin="game_event"})
end
local function nativeNotify(first,second)
    local info=eventInfo(first,second)
    if not model or not info then return end
    if type(info.message)=="string" then
        model:publish("system",boundedUtf8(info.message,512),"Game alert",clock(),{origin="game_event"})
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
            local from=type(unit)=="string" and boundedUtf8(unit,40) or "Game alert"
            if #from==0 then from="Game alert" end
            model:publish("system",boundedUtf8(message,512),from,clock(),{origin="game_event"})
        end
    end
end
local function dragTick()
    if resize then
        local m=mouse()
        if not m or m.Left==false then stopResize()
        else resizeMove(false) end
    elseif drag then
        local m=mouse()
        if not m or m.Left==false then stopDrag()
        else dragMove(false) end
    end
    if panel and panel:GetVisible() then
        local w,h=UIParent:GetWidth(),UIParent:GetHeight()
        if finite(w) and finite(h) and w>0 and h>0
            and (lastViewportW~=w or lastViewportH~=h) then
            lastViewportW,lastViewportH=w,h
            if resize then stopResize() end
            if drag then stopDrag() end
            -- Shrink window before clamping position on resolution/UI-scale changes.
            W,H=math.min(W,math.floor(w)),math.min(H,math.floor(h))
            panel:SetWidth(W);panel:SetHeight(H)
            shift(panel:GetLeft(),panel:GetTop(),false)
            layoutWindow()
            saveGeometry()
            render()
        end
        updateFocusIndicator(false)
    end
end
_G.RiftChatModernAPI={
    interfaceVersion=2,version=VERSION,
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
        data.hostManualImportReady=hostIngress~=nil
        data.hostEditorImportReady=hostIngress~=nil
        data.hostAutoImportAvailable=false
        data.hostImportNativeChatVerified=false
        data.logProbeAvailable=Command and Command.Console
            and type(Command.Console.Display)=="function" or false
        data.logProbeTransportVerified=false -- needs independent Log.txt receipt
        data.windowWidth=W;data.windowHeight=H
        data.minimumWindowWidth=MIN_W;data.minimumWindowHeight=MIN_H
        data.visibleRows=LINES
        data.displayMode=controls._native.active and "native_subscriptions" or "history"
        data.nativeSubscriptionsReadOnly=true
        data.nativeTranscriptReadable=false
        data.nativeSourceGroup=controls._native.active and controls._native.group or nil
        data.commandHistoryCount=#commandHistory
        data.commandHistoryPersisted=false
        data.saveCheckpoint=saveStatus()
        data.resizable=panel~=nil
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
    SetWindowSize=function(width,height)
        if not model then return nil,"not_ready" end
        makeUi()
        return resizeTo(width,height,true)
    end,
    GetSaveCheckpointStatus=saveStatus,
    GetHostIngressStatus=hostIngressStatus,
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
if Event.Addon.SavedVariables.Save then
    if Event.Addon.SavedVariables.Save.Begin then
        Command.Event.Attach(Event.Addon.SavedVariables.Save.Begin,
            onSaveBegin,"RCM Save.Begin receipt")
    end
    if Event.Addon.SavedVariables.Save.End then
        Command.Event.Attach(Event.Addon.SavedVariables.Save.End,
            onSaveEnd,"RCM Save.End observation")
    end
end
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
