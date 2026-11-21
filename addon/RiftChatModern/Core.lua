-- RiftChatModern / Core.lua
-- Standalone bounded message model and command registry. Lua 5.1, no RIFT UI.
local Core = {}
local Model = {}
Model.__index = Model
local MAX_HISTORY, MAX_TEXT, MAX_SOURCE = 240, 512, 40
-- Version 2 separates message family from the *claimed* social channel.
-- No verified ordinary native player-chat receiver is implemented.
local kinds = {system=true, npc=true, addons=true, dev=true,
    combat=true, import=true}
local oldSocialKinds = {general=true, party=true, guild=true, tell=true}
local channelKinds = {general=true, party=true, guild=true, tell=true, public=true}
local origins = {local_addon=true, game_event=true, addon_data=true,
    external_api=true, host_manual=true, legacy_unknown=true}
local filters = {all=true, chat=true, imports=true, system=true,
    npc=true, addons=true, dev=true, combat=true}
local originLabels = {host_manual="HOST IMPORT",legacy_unknown="UNVERIFIED",
    external_api="EXTERNAL",local_addon="LOCAL",game_event="GAME EVENT",
    addon_data="ADDON DATA"}
local function channelTitle(kind)
    return ({general="General",party="Party",guild="Guild",
        tell="Tell",public="Public"})[kind]
end
local function isImport(row)
    return row.kind=="import"
end
local function rowLabel(row)
    if isImport(row) then
        local title=row.channelName or channelTitle(row.channelKind) or "Unknown"
        return (originLabels[row.origin] or "UNVERIFIED").." / "..title
    end
    return row.kind:upper()
end
local function rowShortLabel(row)
    if row.kind=="import" then
        local origin=row.origin=="host_manual" and "HOST"
            or row.origin=="legacy_unknown" and "LEGACY" or "EXTERNAL"
        return origin.."/"..(row.channelKind or "UNKNOWN"):upper()
    end
    return row.kind:upper()
end
local function importFromLegacy(row)
    local kind=row.kind
    local name,body
    if type(row.text)=="string" then
        -- v1 host imports embedded the only provenance in this marker.
        name,body=row.text:match("^%[HOST%? ([^%]]+)%] (.+)$")
    end
    local channelKind=kind
    if name and #name<=72 and not name:find("[%z\1-\31\127]") then
        if kind=="general" and name~="General" and name~="Say"
            and name~="Yell" and name~="Local" then
            channelKind="public"
        end
        return {kind="import",origin="host_manual",
            channelKind=channelKind,channelName=name,
            source=row.source,text=body,id=row.id,at=row.at}
    end
    return {kind="import",origin="legacy_unknown",
        channelKind=kind,channelName=channelTitle(kind),
        source=row.source,text=row.text,id=row.id,at=row.at}
end
local function oldRow(row)
    if oldSocialKinds[row.kind] then return importFromLegacy(row) end
    return {kind=row.kind,origin="legacy_unknown",source=row.source,
        text=row.text,id=row.id,at=row.at}
end
-- Preserve whole UTF-8 code points when bounding external strings by bytes.
-- RIFT text normally arrives as valid UTF-8; this never guesses missing bytes.
local function utf8Prefix(value,limit)
    if #value<=limit then return value end
    local last=limit
    while last>0 do
        local nextByte=value:byte(last+1)
        if not nextByte or nextByte<128 or nextByte>=192 then break end
        last=last-1
    end
    return value:sub(1,last)
end
local function validString(v, min, max)
    return type(v)=="string" and #v>=min and #v<=max
        and not v:find("[%z\1-\8\11\12\14-\31]")
end
local function singleLine(v)
    return (v:gsub("\r", " "):gsub("\n", " "))
end
-- A transport token is an idempotency identity, not a native chat claim.
-- v2 imports from older releases are valid without this optional field.
local function validImportToken(value)
    return type(value)=="string" and #value==12
        and value:match("^[A-F0-9]+$")~=nil
end
local function validRow(row)
    if type(row)~="table" or not kinds[row.kind]
        or not origins[row.origin] or not validString(row.source,1,MAX_SOURCE)
        or not validString(row.text,1,MAX_TEXT)
        or type(row.id)~="number" or row.id<1 or row.id%1~=0
        or type(row.at)~="number" or row.at~=row.at
        or row.at<0 or row.at==math.huge then return false end
    if isImport(row) then
        return (row.origin=="host_manual" or row.origin=="legacy_unknown"
                or row.origin=="external_api")
            and channelKinds[row.channelKind]
            and validString(row.channelName,1,72)
            and (row.importToken==nil or (row.origin=="host_manual"
                and validImportToken(row.importToken)))
    end
    return row.channelKind==nil and row.channelName==nil
        and row.importToken==nil
end
local function copyRow(row)
    return {id=row.id,at=row.at,kind=row.kind,source=row.source,
        text=row.text,origin=row.origin,channelKind=row.channelKind,
        channelName=row.channelName,importToken=row.importToken,
        nativePlayerChatVerified=false}
end
local function match(row, filter, search)
    if filter~="all" and not (filter=="chat" and isImport(row))
        and not (filter=="imports" and isImport(row))
        and row.kind~=filter then return false end
    if search~="" then
        local target=(row.source.." "..row.text.." "..rowLabel(row)):lower()
        if not target:find(search:lower(), 1, true) then return false end
    end
    return true
end

function Core.new(saved)
    if type(saved)~="table" or (saved.schemaVersion~=1
        and saved.schemaVersion~=2) or type(saved.history)~="table" then
        return nil,"invalid_saved_schema"
    end
    local migrating=saved.schemaVersion==1
    local size,maximum,maxId=0,0,0
    local seenIds,seenTokens,converted={},{},{}
    for k,row in pairs(saved.history) do
        if type(k)~="number" or k<1 or k%1~=0
            or type(row)~="table" or seenIds[row.id] then
            return nil,"invalid_saved_history"
        end
        if migrating and not (kinds[row.kind] or oldSocialKinds[row.kind]) then
            return nil,"invalid_saved_history"
        end
        local candidate=migrating and oldRow(row) or row
        if not validRow(candidate) then return nil,"invalid_saved_history" end
        if candidate.importToken and seenTokens[candidate.importToken] then
            return nil,"invalid_saved_history"
        end
        seenIds[row.id]=true
        if candidate.importToken then seenTokens[candidate.importToken]=true end
        converted[k]=candidate
        size=size+1
        maximum=math.max(maximum,k)
        maxId=math.max(maxId,row.id)
    end
    if size~=maximum or size>MAX_HISTORY then return nil,"invalid_history_bounds" end
    if saved.nextId~=nil and (type(saved.nextId)~="number"
        or saved.nextId<=maxId or saved.nextId%1~=0) then return nil,"invalid_sequence" end
    -- Commit the complete v1->v2 migration only after ALL rows validate.
    -- Never mutate/destroy a partially invalid SavedVariables history.
    if migrating then
        saved.history=converted
        saved.schemaVersion=2
    end
    -- Migration and missing nextId repair mutate character SavedVariables.
    -- They must remain marked as unsaved until an actual RIFT Save.Begin.
    local initializedSavedState=migrating or saved.nextId==nil
    local self=setmetatable({saved=saved, handlers={}, listeners={},
        filter="all", search="", onChange=nil, onCommand=nil,
        revision=initializedSavedState and 1 or 0}, Model)
    saved.nextId=saved.nextId or (maxId+1)
    if saved.filter~=nil and filters[saved.filter] then self.filter=saved.filter end
    if type(saved.search)=="string" and #saved.search<=60
        and not saved.search:find("[%z\1-\8\11\12\14-\31]") then
        self.search=saved.search
    end
    return self
end
function Model:_changed()
    self.revision=self.revision+1
    if type(self.onChange)=="function" then pcall(self.onChange) end
end
-- Bounded scan of retained rows: survives logout and a new addon session.
-- It does not claim that a current in-memory row is already saved on disk.
function Model:findImportToken(token)
    if not validImportToken(token) then return nil end
    for _,row in ipairs(self.saved.history) do
        if row.kind=="import" and row.importToken==token then return row.id end
    end
    return nil
end
function Model:publish(kind, text, source, at, metadata)
    -- Native social delivery is not proven, so no caller can mint a normal
    -- "guild", "tell", "party" or "general" record from an external string.
    if oldSocialKinds[kind] then return nil,"native_chat_not_available" end
    if not kinds[kind] then return nil,"invalid_kind" end
    if not validString(text,1,MAX_TEXT) then return nil,"invalid_text" end
    if not validString(source,1,MAX_SOURCE) then return nil,"invalid_source" end
    if type(at)~="number" or at~=at or at<0 or at==math.huge then
        return nil,"invalid_time"
    end
    metadata=metadata or {}
    if type(metadata)~="table" then return nil,"invalid_metadata" end
    local row={id=self.saved.nextId,at=at,kind=kind,source=source,
        text=singleLine(text),origin=metadata.origin or "external_api",
        channelKind=metadata.channelKind,channelName=metadata.channelName,
        importToken=metadata.importToken}
    if not validRow(row) then return nil,"invalid_metadata" end
    if row.importToken and self:findImportToken(row.importToken) then
        return nil,"duplicate_import_token"
    end
    local history=self.saved.history
    if #history>=MAX_HISTORY then table.remove(history,1) end
    history[#history+1]=row
    self.saved.nextId=self.saved.nextId+1
    self:_changed()
    if not self._notifying then
        self._notifying=true
        for _,cb in pairs(self.listeners) do pcall(cb,copyRow(row)) end
        self._notifying=false
    end
    return copyRow(row)
end
function Model:getHistory(filter, search, limit, offset)
    filter=filter or self.filter
    search=search or self.search
    if not filters[filter] or type(search)~="string" or #search>60
        or type(limit)~="number" or limit<1 or limit>MAX_HISTORY
        or limit%1~=0 or type(offset)~="number" or offset<0
        or offset%1~=0 then return nil,"invalid_query" end
    local all={}
    for _,row in ipairs(self.saved.history) do
        if match(row,filter,search) then all[#all+1]=row end
    end
    local total=#all
    local result={}
    local last=math.max(0,total-offset)
    for i=math.max(1,last-limit+1),last do
        if all[i] then result[#result+1]=copyRow(all[i]) end
    end
    return result,total
end
-- Stable-ID lookup survives paging and filtering; returns an isolated row copy.
function Model:getMessage(id)
    if type(id)~="number" or id~=id or id%1~=0 or id<1 then
        return nil,"invalid_message_id"
    end
    for _,row in ipairs(self.saved.history) do
        if row.id==id then return copyRow(row) end
    end
    return nil,"message_not_retained"
end

function Model:setFilter(filter)
    if not filters[filter] then return nil,"invalid_filter" end
    -- A repeated tab selection must not falsely report pending disk changes.
    -- An absent/invalid persisted default DOES count when first repaired.
    local changed=self.filter~=filter or self.saved.filter~=filter
    self.filter=filter
    self.saved.filter=filter
    if changed then self:_changed() end
    return true
end
function Model:setSearch(value)
    if type(value)~="string" or #value>60
        or value:find("[%z\1-\8\11\12\14-\31]") then
        return nil,"invalid_search"
    end
    local changed=self.search~=value or self.saved.search~=value
    self.search=value
    self.saved.search=value
    if changed then self:_changed() end
    return true
end
function Model:clear()
    -- Empty history is already serialized as empty: do not manufacture a save.
    if #self.saved.history==0 then return true end
    self.saved.history={}
    self:_changed()
    return true
end
function Model:exportText(filter, search, maximum)
    maximum=maximum or 48000
    if type(maximum)~="number" or maximum~=maximum
        or maximum<=-math.huge or maximum>=math.huge
        or maximum%1~=0 or maximum<512 or maximum>120000 then
        return nil,"invalid_limit"
    end
    local rows,total=self:getHistory(filter,search,MAX_HISTORY,0)
    if not rows then return nil,total end
    local result={"RiftChatModern export v2 | filtered messages: "..total}
    local size=#result[1]
    for _,row in ipairs(rows) do
        local time
        if os and type(os.date)=="function" then
            local ok,value=pcall(os.date,"%H:%M:%S",math.floor(row.at))
            time=ok and value or "??:??:??"
        else time="??:??:??" end
        local line=string.format("[%s] [%s] %s: %s",time,rowLabel(row),
            row.source,row.text)
        if size+#line+1>maximum-90 then
            result[#result+1]="[Truncated: clipboard export byte limit reached]"
            break
        end
        result[#result+1]=line
        size=size+#line+1
    end
    return table.concat(result,"\n")
end
function Model:subscribe(name,callback)
    if not validString(name,1,40) or type(callback)~="function"
        or self.listeners[name] then return nil,"invalid_listener" end
    local count=0
    for _ in pairs(self.listeners) do count=count+1 end
    if count>=48 then return nil,"listener_limit" end
    self.listeners[name]=callback
    return true
end
function Model:unsubscribe(name)
    if not self.listeners[name] then return nil,"not_found" end
    self.listeners[name]=nil
    return true
end
function Model:registerCommand(name,callback)
    if type(name)~="string" or not name:match("^[a-z][a-z0-9_]*$")
        or #name>24 or type(callback)~="function" or self.handlers[name]
        or name=="help" or name=="clear" or name=="filter" or name=="find"
        or name=="status" or name=="echo" or name=="copy"
        or name=="import" then
        return nil,"invalid_command"
    end
    if self:commandCount()>=48 then return nil,"command_limit" end
    self.handlers[name]=callback
    return true
end
function Model:execute(text, clock)
    if not validString(text,1,512) then return nil,"invalid_text" end
    if text:sub(1,1)~=":" then return nil,"native_send_unavailable" end
    local name,args=text:sub(2):match("^%s*([a-zA-Z][a-zA-Z0-9_]*)%s*(.-)%s*$")
    if not name then return nil,"invalid_command" end
    name=name:lower()
    local handled=true
    local response
    if name=="help" then
        response="Local commands: :help :clear :status :filter TAB :find TEXT :copy :echo TEXT | extension commands: "..tostring(self:commandCount())
    elseif name=="clear" then self:clear();response=nil
    elseif name=="filter" then
        local ok,err=self:setFilter(args)
        if not ok then return nil,err end
        response="Filter: "..args
    elseif name=="find" then
        local ok,err=self:setSearch(args)
        if not ok then return nil,err end
        response="Search: "..(args~="" and args or "(cleared)")
    elseif name=="echo" then
        if not validString(args,1,MAX_TEXT-5) then return nil,"invalid_text" end
        response=args
    elseif name=="status" then
        response=string.format("%d stored | %d extensions | filter=%s",
            #self.saved.history,self:commandCount(),self.filter)
    elseif name=="copy" then response="[Copy from the button or API; clipboard requires a RIFT runtime]"
    else
        local fn=self.handlers[name]
        if not fn then return nil,"unknown_local_command" end
        local ok, result=pcall(fn,args)
        if not ok then return nil,"extension_error" end
        if result==false then return nil,"extension_refused" end
        response=type(result)=="string" and utf8Prefix(result,MAX_TEXT) or
            "Extension command accepted (actual effect unverified)."
    end
    if response and response~="" then
        local row,err=self:publish("dev",response,"Console",clock,{origin="local_addon"})
        if not row then return nil,err end
    end
    return handled
end
function Model:commandCount()
    local count=0
    for _ in pairs(self.handlers) do count=count+1 end
    return count
end
function Model:status()
    return {version="0.2.19",schemaVersion=2,
        provenanceRequired=true,historyCount=#self.saved.history,
        filter=self.filter,search=self.search,revision=self.revision,
        commandCount=self:commandCount(),nativeSocialSendAvailable=false,
        nativePlayerChatCaptureAvailable=false}
end
-- UI geometry is persisted outside the usual history/filter callbacks.
-- Mark it dirty without forcing a render during drag or resize.
function Model:markSavedStateChanged()
    self.revision=self.revision+1
    return true
end
-- RIFT controls when character SavedVariables are serialized. This tiny
-- checkpoint receipt is written only during SavedVariables.Save.Begin.
-- It never claims that bytes reached disk; host inspection must verify that.
local function safeCheckpoint(record)
    if type(record)~="table" or record.formatVersion~=1
        or record.schemaVersion~=2 then return nil end
    local function integer(value,min,max)
        return type(value)=="number" and value==value
            and value%1==0 and value>=min and value<=max
    end
    if not integer(record.sequence,1,1000000000)
        or not integer(record.historyCount,0,MAX_HISTORY)
        or not integer(record.nextId,1,1000000000000)
        or not integer(record.lastHistoryId,0,1000000000000)
        or not integer(record.lastImportId,0,1000000000000)
        or record.lastHistoryId>=record.nextId
        or record.lastImportId>record.lastHistoryId
        or type(record.at)~="number" or record.at~=record.at
        or record.at<0 or record.at==math.huge then return nil end
    return record
end
function Model:recordSaveBegin(at)
    if type(at)~="number" or at~=at or at<0 or at==math.huge then
        return nil,"invalid_time"
    end
    local previous=safeCheckpoint(self.saved.saveCheckpoint)
    local sequence=previous and previous.sequence or 0
    if sequence>=1000000000 then sequence=0 end
    local history=self.saved.history
    local count=#history
    local last=count>0 and history[count].id or 0
    local lastImport=0
    for i=count,1,-1 do
        if history[i].kind=="import" then
            lastImport=history[i].id
            break
        end
    end
    local record={formatVersion=1,schemaVersion=2,sequence=sequence+1,
        at=at,historyCount=count,nextId=self.saved.nextId,
        lastHistoryId=last,lastImportId=lastImport}
    -- Save.Begin is the last addon-controlled opportunity to stage metadata.
    self.saved.saveCheckpoint=record
    self._lastCheckpointRevision=self.revision
    return self:checkpointStatus()
end
function Model:checkpointStatus()
    local checkpoint=safeCheckpoint(self.saved.saveCheckpoint)
    local dirty=self.revision>(self._lastCheckpointRevision or 0)
    return {saveEventReceiptAvailable=checkpoint~=nil,
        eventSequence=checkpoint and checkpoint.sequence or 0,
        eventAt=checkpoint and checkpoint.at or nil,
        historyCountAtEvent=checkpoint and checkpoint.historyCount or nil,
        nextIdAtEvent=checkpoint and checkpoint.nextId or nil,
        lastHistoryIdAtEvent=checkpoint and checkpoint.lastHistoryId or nil,
        lastImportIdAtEvent=checkpoint and checkpoint.lastImportId or nil,
        pendingSessionChanges=dirty,
        onDiskVerified=false,requiredDiskVerification=true,
        nativeSaveEventsAreNotDiskProof=true}
end
Core.filters=filters
Core.rowLabel=rowLabel
Core.rowShortLabel=rowShortLabel
Core.utf8Prefix=utf8Prefix
Core.maxHistory=MAX_HISTORY
Core.kinds=kinds
_G.RiftChatModernCore = Core
-- RIFT RunOnStartup scripts must not return module values.
