-- RiftChatModern optional console-output mirror.
-- Captures calls by other addons to Command.Console.Display after explicit opt-in.
-- This does NOT intercept player say/tell/guild/party chat and never invokes input.
local Mirror={}
Mirror.__index=Mirror

local function pack(...) return {n=select("#",...), ...} end
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
local function plain(value,html)
    if type(value)~="string" or #value==0 then return nil end
    local line=value
    if html==true then
        line=line:gsub("<[^>]*>","")
        line=line:gsub("&lt;","<"):gsub("&gt;",">")
            :gsub("&quot;",'"'):gsub("&#39;","'")
            :gsub("&amp;","&")
    end
    line=line:gsub("[%z\1-\8\11\12\14-\31]"," ")
    line=line:gsub("[\r\n]"," ")
    if #line>512 then line=utf8Prefix(line,509).."..." end
    if #line==0 then return nil end
    -- Our own startup/errors are already in native RIFT chat; avoid loops.
    if line:sub(1,16)=="RiftChatModern v" then return nil end
    return line
end

function Mirror.new(console,callback)
    if (type(console)~="table" and type(console)~="userdata")
        or type(callback)~="function" then return nil,"invalid_dependencies" end
    return setmetatable({console=console,callback=callback,
        original=nil,wrapper=nil,enabled=false,captured=0,
        rejected=0,inside=false},Mirror)
end

function Mirror:enable()
    if self.enabled then return true end
    if self.wrapper then
        local ok,current=pcall(function() return self.console.Display end)
        if not ok or current~=self.wrapper then
            return nil,"console_hook_replaced"
        end
        self.enabled=true
        return true
    end
    local original
    local ok=pcall(function() original=self.console.Display end)
    if not ok or type(original)~="function" then
        return nil,"console_unavailable"
    end
    local selfRef=self
    local wrapper=function(...)
        -- Pass through the complete original call and return values unchanged.
        local call=pack(pcall(original,...))
        if call[1]~=true then error(call[2],0) end
        if selfRef.enabled and not selfRef.inside and call[2]~=false then
            local console,suppress,body,html=...
            local line=plain(body,html)
            if line then
                selfRef.inside=true
                local delivered,record=pcall(selfRef.callback,line,
                    type(console)=="string" and console:sub(1,32) or "console")
                selfRef.inside=false
                if delivered and record~=nil and record~=false then
                    selfRef.captured=selfRef.captured+1
                else selfRef.rejected=selfRef.rejected+1 end
            end
        end
        return unpack(call,2,call.n)
    end
    local set=pcall(function() self.console.Display=wrapper end)
    if not set or self.console.Display~=wrapper then
        return nil,"console_hook_unavailable"
    end
    self.original,self.wrapper,self.enabled=original,wrapper,true
    return true
end

function Mirror:disable()
    if not self.wrapper then self.enabled=false;return true end
    self.enabled=false
    local ok,current=pcall(function() return self.console.Display end)
    if not ok then return nil,"console_unavailable" end
    if current~=self.wrapper then
        -- A later addon may have wrapped ours. Stop recording, never
        -- overwrite its newer hook or claim complete uninstallation.
        return nil,"hook_chained"
    end
    local restored=pcall(function() self.console.Display=self.original end)
    if not restored or self.console.Display~=self.original then
        return nil,"restore_failed"
    end
    self.original,self.wrapper=nil,nil
    return true
end

function Mirror:status()
    local ok,current=pcall(function() return self.console.Display end)
    return {enabled=self.enabled,
        ownsHook=ok and self.wrapper~=nil and current==self.wrapper,
        captured=self.captured,rejected=self.rejected,
        type="addon_console_output_only",
        nativePlayerChatCaptured=false}
end

_G.RiftChatModernConsoleMirror=Mirror
-- RIFT RunOnStartup scripts must not return module values.
