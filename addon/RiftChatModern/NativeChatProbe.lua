-- Read-only facts about RIFT's native Console1..Console7 UI handles.
-- A Native console object does NOT imply access to its message transcript.
-- This code never opens/closes the console, invokes commands or reads chat text.
local Probe={}
local function read(obj,name)
    if not obj then return nil end
    local ok,fn=pcall(function() return obj[name] end)
    if not ok or type(fn)~="function" then return nil end
    local good,value=pcall(fn,obj)
    if good and type(value)=="boolean" then return value end
    return nil
end
local channelFlags={"say","yell","tell","party","raid","guild","officer",
    "system","npc","channel","emote","combatGood","combatBad"}
local function readable(value,maximum)
    return type(value)=="string" and #value>0 and #value<=maximum
        and not value:find("[%z\1-\31\127]")
end
local function channels(info)
    local out={}
    if type(info)~="table" then return out end
    for _,name in ipairs(channelFlags) do
        local value=info[name]
        if type(value)=="boolean" then out[name]=value end
    end
    return out
end
local function readConsoles(out,inspect)
    if type(inspect)~="table" or type(inspect.Console)~="table"
        or type(inspect.Console.List)~="function"
        or type(inspect.Console.Detail)~="function" then return end
    local ok,listing=pcall(inspect.Console.List)
    if not ok or type(listing)~="table" then return end
    out.consoleListReady=true
    local ids,seen={},{}
    local scanned=0
    for key,value in pairs(listing) do
        scanned=scanned+1
        if scanned>32 then out.consoleListTruncated=true; break end
        local id=type(value)=="string" and value
            or type(key)=="string" and key or nil
        if readable(id,80) and not seen[id] then
            seen[id]=true
            ids[#ids+1]=id
        end
    end
    table.sort(ids)
    for _,id in ipairs(ids) do
        local good,info=pcall(inspect.Console.Detail,id)
        local row={id=id,detailAvailable=good and type(info)=="table"}
        if row.detailAvailable then
            if readable(info.name,60) then row.name=info.name end
            row.channels=channels(info)
        end
        out.consoles[#out.consoles+1]=row
    end
    out.consoleCount=#out.consoles
end
function Probe.capture(ui,inspect)
    local out={windowCount=0,visibleCount=0,focusCount=0,
        windows={},consoles={},consoleCount=0,consoleListReady=false,
        nativeTranscriptReadable=false,nativeSocialSendAvailable=false,
        scope="native_frame_and_channel_metadata_only"}
    readConsoles(out,inspect)
    if type(ui)~="table" and type(ui)~="userdata" then return out end
    local ok,native=pcall(function() return ui.Native end)
    if not ok or (type(native)~="table" and type(native)~="userdata") then
        return out
    end
    for i=1,7 do
        local available,handle=pcall(function() return native["Console"..i] end)
        if available and handle~=nil then
            local row={index=i,available=true,
                visible=read(handle,"GetVisible"),
                loaded=read(handle,"GetLoaded"),
                elementKeyFocus=read(handle,"GetKeyFocus")}
            out.windows[#out.windows+1]=row
            out.windowCount=out.windowCount+1
            if row.visible==true then out.visibleCount=out.visibleCount+1 end
            if row.elementKeyFocus==true then out.focusCount=out.focusCount+1 end
        end
    end
    return out
end
_G.RiftChatModernNativeProbe=Probe
-- RIFT RunOnStartup scripts must not return module values.
