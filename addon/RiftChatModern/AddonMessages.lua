-- RIFT Chat Modern: reliable addon-data messaging (NOT player/social chat).
-- A narrow, namespace-owned channel for developer tools across clients.
-- RIFT Command.Message.Send callback acknowledges server queueing, never delivery.
local Bridge = {}
Bridge.__index = Bridge
Bridge.identifier = "RCMDevV1"

local function printable(value,max)
    return type(value)=="string" and #value>0 and #value<=max
        and not value:find("[%z\1-\31\127]")
end
local function validTarget(name)
    return printable(name,60) and name:match("^[%a][%w._@%-]*$")~=nil
end
local function validTime(now)
    return type(now)=="number" and now==now and now>=0 and now<math.huge
end
local function copyStatus(self)
    return {ready=self.ready,identifier=Bridge.identifier,
        pending=self.pending~=nil,submitted=self.submitted,
        accepted=self.accepted,rejected=self.rejected,unknown=self.unknown,
        received=self.received,invalid=self.invalid}
end

-- All dependencies injected, so this module can be exercised under Lua 5.1
-- without a game process. Never patches Command.Message methods.
function Bridge.new(send,accept,onReceive,onNotice,clock)
    if type(send)~="function" or type(accept)~="function"
        or type(onReceive)~="function" or type(onNotice)~="function"
        or type(clock)~="function" then return nil,"invalid_dependencies" end
    local self=setmetatable({
        send=send,accept=accept,onReceive=onReceive,onNotice=onNotice,
        clock=clock,ready=false,pending=nil,lastSent=nil,sequence=0,
        submitted=0,accepted=0,rejected=0,unknown=0,received=0,invalid=0,
    },Bridge)
    return self
end

function Bridge:enable()
    if self.ready then return true end
    -- Accept only our own identifier, and only the reliable "send" class.
    local ok,result=pcall(self.accept,"send",Bridge.identifier)
    if not ok or result==false then return nil,"accept_unavailable" end
    self.ready=true
    return true
end

function Bridge:receive(from,kind,channel,identifier,data)
    if not self.ready or kind~="send" or channel~=nil
        or identifier~=Bridge.identifier then return nil,"not_our_message" end
    if not validTarget(from) or not printable(data,240) then
        self.invalid=self.invalid+1
        return nil,"invalid_addon_message"
    end
    self.received=self.received+1
    pcall(self.onReceive,from,data)
    return true
end

-- An absent callback cannot permanently lock the channel. A timed-out
-- submission is explicitly UNKNOWN and never retried automatically.
function Bridge:_expirePending()
    if not self.pending then return end
    local ok,now=pcall(self.clock)
    if not ok or not validTime(now) then return end
    if now-self.pending.at>=15 then
        local target=self.pending.target
        self.pending=nil
        self.unknown=self.unknown+1
        pcall(self.onNotice,"Addon message acknowledgment timed out; delivery unknown. Do not blindly retry.",target)
    end
end

function Bridge:sendTo(target,data)
    if not self.ready then return nil,"not_ready" end
    self:_expirePending()
    if not validTarget(target) then return nil,"invalid_target" end
    if not printable(data,240) then return nil,"invalid_text" end
    if self.pending then return nil,"send_pending" end
    local ok,now=pcall(self.clock)
    if not ok or not validTime(now) then return nil,"clock_unavailable" end
    if self.lastSent and now-self.lastSent<2 then return nil,"rate_limited" end
    self.sequence=self.sequence+1
    local seq=self.sequence
    self.pending={id=seq,target=target,at=now}
    self.lastSent=now
    local callbackFired=false
    local callbackState=nil
    local function completed(failure,message)
        if callbackFired or not self.pending or self.pending.id~=seq then return end
        callbackFired=true
        self.pending=nil
        if failure==false then
            callbackState="server_queue_accepted"
            self.accepted=self.accepted+1
            pcall(self.onNotice,"Addon message accepted for RIFT server queue; delivery unverified.",target)
        elseif failure==true then
            callbackState="server_rejected"
            self.rejected=self.rejected+1
            pcall(self.onNotice,"RIFT rejected addon message (no automatic retry).",target)
        else
            callbackState="callback_unknown"
            self.unknown=self.unknown+1
            pcall(self.onNotice,"Addon send callback state unknown; no automatic retry.",target)
        end
    end
    local ran,result=pcall(self.send,target,Bridge.identifier,data,completed)
    if not ran or result==false then
        if callbackFired then
            -- Callback already settled this request; avoid double-counting a
            -- contradictory return value from the API wrapper.
            self.submitted=self.submitted+1
            if callbackState=="server_queue_accepted" then
                return {id=seq,status=callbackState,delivery_verified=false}
            end
            return nil,callbackState or "callback_unknown"
        end
        -- May already have been queued. Never silently retry.
        if self.pending and self.pending.id==seq then self.pending=nil end
        self.rejected=self.rejected+1
        pcall(self.onNotice,"Addon message submission uncertain; no automatic retry.",target)
        return nil,"submission_uncertain"
    end
    self.submitted=self.submitted+1
    if callbackFired then
        if callbackState=="server_queue_accepted" then
            return {id=seq,status="server_queue_accepted",delivery_verified=false}
        end
        return nil,callbackState or "callback_unknown"
    end
    return {id=seq,status="api_submitted",delivery_verified=false}
end

function Bridge:status()
    self:_expirePending()
    return copyStatus(self)
end

_G.RiftChatModernAddonMessages = Bridge
-- RIFT RunOnStartup scripts must not return module values.
