-- Standalone, explicitly installed RIFT addon example.
-- It neither reads external files nor sends native chat. RCM retains the
-- sample's diagnostics as external_api/addons records, not player speech.
local info = ...
local ADDON = type(info)=="table" and info.identifier or "RCMIntegrationDemo"
local SOURCE = "RCMIntegrationDemo"
local COMMAND_NAME = "rcmdemo"
local LISTENER_NAME = "RCMIntegrationDemo"
local registered,observing,announced=false,false,false
local observed,lastId=0,nil

-- The dependency controls load order, but readiness is a separate condition.
-- Do not assume that a global table means SavedVariables initialization passed.
local function readyApi()
    local api=_G.RiftChatModernAPI
    if type(api)~="table" or api.interfaceVersion~=2 then return nil end
    for _,name in ipairs({"GetStatus","Publish","RegisterCommand","Subscribe","Unsubscribe"}) do
        if type(api[name])~="function" then return nil end
    end
    local ok,status=pcall(api.GetStatus)
    if not ok or type(status)~="table" or status.ready~=true then return nil end
    return api
end

-- Every delivered row is a copy. The demo only tracks its own diagnostic
-- counts/IDs, never collects other addons' or players' message text.
local function observe(row)
    if type(row)=="table" and row.kind=="addons"
        and row.origin=="external_api" and row.source==SOURCE then
        observed=observed+1
        lastId=row.id
    end
end

local function startObserving(api)
    if observing then return true end
    local ok,why=api.Subscribe(LISTENER_NAME,observe)
    if not ok then return nil,why end
    observing=true
    return true
end

local function localCommand(args)
    local api=readyApi()
    if not api then return "RCM demo: API unavailable." end
    if args=="" or args=="status" then
        return string.format("RCM demo: observing=%s, own diagnostics=%d, last ID=%s",
            tostring(observing),observed,tostring(lastId or "none"))
    elseif args=="ping" then
        local row,why=api.Publish("addons","RCM demo diagnostic ping",SOURCE)
        return row and ("RCM demo retained diagnostic #"..tostring(row.id))
            or ("RCM demo publish refused: "..tostring(why))
    elseif args=="stop" then
        if not observing then return "RCM demo observation already stopped." end
        local ok,why=api.Unsubscribe(LISTENER_NAME)
        if not ok then return "RCM demo unsubscribe refused: "..tostring(why) end
        observing=false
        return "RCM demo observation stopped; history retained."
    elseif args=="start" then
        local ok,why=startObserving(api)
        return ok and "RCM demo observation enabled."
            or ("RCM demo subscribe refused: "..tostring(why))
    end
    return "Usage: :rcmdemo status | ping | start | stop"
end

-- Bounded lifecycle retries: only our own or RCM's Load.End events. No
-- per-frame polling, no repeated startup messages, no overwrite of an
-- existing consumer's registration when a name collision occurs.
local function connect(_,name)
    if name~=ADDON and name~="RiftChatModern" then return end
    local api=readyApi()
    if not api then return end
    if not registered then
        local ok=api.RegisterCommand(COMMAND_NAME,localCommand)
        if not ok then return end
        registered=true
    end
    if not announced then
        if not startObserving(api) then return end
        local row=api.Publish("addons","RCM integration demo ready",SOURCE)
        if row then announced=true end
    end
end

Command.Event.Attach(Event.Addon.Load.End,connect,ADDON.." connect to RCM")
-- RIFT RunOnStartup modules return no values.
