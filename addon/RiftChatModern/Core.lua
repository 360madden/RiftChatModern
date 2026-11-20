-- RiftChatModern / Core.lua
-- Standalone bounded message model and command registry. Lua 5.1, no RIFT UI.
local Core = {}
local Model = {}
Model.__index = Model
local MAX_HISTORY, MAX_TEXT, MAX_SOURCE = 240, 512, 40
local kinds = {system=true, npc=true, addons=true, dev=true,
    general=true, party=true, guild=true, tell=true, combat=true}
local filters = {all=true, chat=true, system=true, npc=true, addons=true,
    dev=true, combat=true}
local chatKinds = {general=true, party=true, guild=true, tell=true}
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
local function copyRow(row)
    return {id=row.id, at=row.at, kind=row.kind, source=row.source, text=row.text}
end
local function match(row, filter, search)
    if filter~="all" and not (filter=="chat" and chatKinds[row.kind])
        and row.kind~=filter then return false end
    if search~="" then
        local target=(row.source.." "..row.text):lower()
        if not target:find(search:lower(), 1, true) then return false end
    end
    return true
end

function Core.new(saved)
    if type(saved)~="table" or saved.schemaVersion~=1
        or type(saved.history)~="table" then return nil,"invalid_saved_schema" end
    local size, maximum, maxId=0,0,0
    local seenIds={}
    for k,row in pairs(saved.history) do
        if type(k)~="number" or k<1 or k%1~=0
            or type(row)~="table" or not kinds[row.kind]
            or not validString(row.source,1,MAX_SOURCE)
            or not validString(row.text,1,MAX_TEXT)
            or type(row.id)~="number" or row.id<1 or row.id%1~=0
            or type(row.at)~="number" or row.at~=row.at
            or row.at<0 or row.at==math.huge
            or seenIds[row.id] then
            return nil,"invalid_saved_history"
        end
        seenIds[row.id]=true
        size=size+1
        maximum=math.max(maximum,k)
        maxId=math.max(maxId,row.id)
    end
    if size~=maximum or size>MAX_HISTORY then return nil,"invalid_history_bounds" end
    if saved.nextId~=nil and (type(saved.nextId)~="number"
        or saved.nextId<=maxId or saved.nextId%1~=0) then return nil,"invalid_sequence" end
    local self=setmetatable({saved=saved, handlers={}, listeners={},
        filter="all", search="", onChange=nil, onCommand=nil, revision=0}, Model)
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
function Model:publish(kind, text, source, at)
    if not kinds[kind] then return nil,"invalid_kind" end
    if not validString(text,1,MAX_TEXT) then return nil,"invalid_text" end
    if not validString(source,1,MAX_SOURCE) then return nil,"invalid_source" end
    if type(at)~="number" or at~=at or at<0 or at==math.huge then
        return nil,"invalid_time"
    end
    local row={id=self.saved.nextId,at=at,kind=kind,source=source,
        text=singleLine(text)}
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
    self.filter=filter
    self.saved.filter=filter
    self:_changed()
    return true
end
function Model:setSearch(value)
    if type(value)~="string" or #value>60
        or value:find("[%z\1-\8\11\12\14-\31]") then
        return nil,"invalid_search"
    end
    self.search=value
    self.saved.search=value
    self:_changed()
    return true
end
function Model:clear()
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
    local result={"RiftChatModern v1 | filtered messages: "..total}
    local size=#result[1]
    for _,row in ipairs(rows) do
        local time
        if os and type(os.date)=="function" then
            local ok,value=pcall(os.date,"%H:%M:%S",math.floor(row.at))
            time=ok and value or "??:??:??"
        else time="??:??:??" end
        local line=string.format("[%s] [%s] %s: %s",time,row.kind,
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
        or name=="status" or name=="echo" or name=="copy" then
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
        local row,err=self:publish("dev",response,"Console",clock)
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
    return {version="0.2.6",historyCount=#self.saved.history,
        filter=self.filter,search=self.search,revision=self.revision,
        commandCount=self:commandCount(),nativeSocialSendAvailable=false,
        nativePlayerChatCaptureAvailable=false}
end
Core.filters=filters
Core.utf8Prefix=utf8Prefix
Core.maxHistory=MAX_HISTORY
Core.kinds=kinds
_G.RiftChatModernCore = Core
-- RIFT RunOnStartup scripts must not return module values.
