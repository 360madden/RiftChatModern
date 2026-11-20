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
function Probe.capture(ui)
    local out={windowCount=0,visibleCount=0,focusCount=0,
        windows={},nativeTranscriptReadable=false,nativeSocialSendAvailable=false,
        scope="native_frame_metadata_only"}
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
return Probe
