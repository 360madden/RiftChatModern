-- RiftChatModern / ConsoleCategories.lua
-- Native RIFT console subscription taxonomy, read-only. Lua 5.1.
-- Subscriptions indicate configuration, NOT transcript access or delivery.
local Registry={}
local definitions={
    game={title="GAME MESSAGES",items={
        {"System","system"},{"Skill","skill"},{"Notoriety","notoriety"},
        {"NPC Say","npc"},{"Achievements","achievement"},
        {"Accolades","accolade"},{"Experience","experience"}}},
    loot={title="LOOT MESSAGES",items={
        {"Item Loot","lootItem"},{"Money Loot","lootMoney"},
        {"Group Loot","lootGroup"},{"Purchases","purchase"},
        {"Crafting Self","craftingSelf"},{"Crafting Others","craftingOther"}}},
    player={title="PLAYER MESSAGES",items={
        {"Say","say"},{"Tell","tell"},{"Emote","emote"},{"Yell","yell"},
        {"Guild","guild"},{"Guild Officer","officer"},{"Party","party"},
        {"Raid Warning","raidWarning"},{"Raid","raid"},
        -- Warfront exists in the native settings screenshot, but the
        -- verified Inspect.Console.Detail contract exposes no flag for it.
        {"Warfront",false}}},
    public={title="CHANNEL MESSAGES"},
    combat={title="COMBAT MESSAGES",items={
        {"Combat Good","combatGood"},{"Combat Bad","combatBad"},
        {"Combat Neutral","combatNeutral"},{"Combat Other","combatOther"},
        {"Combat Special","combatSpecial"}}}
}
local order={"game","loot","player","public","combat"}
local function bounded(v,max)
    return type(v)=="string" and #v>0 and #v<=max
        and not v:find("[%z\1-\31\127]")
end
function Registry.sections()
    local out={}
    for i,name in ipairs(order) do
        out[i]={id=name,title=definitions[name].title}
    end
    return out
end
function Registry.choose(snapshot,index)
    if type(snapshot)~="table" or type(snapshot.consoles)~="table"
        or #snapshot.consoles==0 then return nil,0,0 end
    local source=snapshot.consoles
    local preferred=1
    for i,console in ipairs(source) do
        if type(console)=="table" and type(console.name)=="string"
            and console.name:lower()=="general" then preferred=i;break end
    end
    if type(index)=="number" and index%1==0
        and index>=1 and index<=#source then preferred=index end
    return source[preferred],preferred,#source
end
function Registry.group(snapshot,category,index)
    local def=definitions[category]
    if not def then return nil,"unknown_console_category" end
    local console,chosen,total=Registry.choose(snapshot,index)
    local out={id=category,title=def.title,
        consoleName=console and bounded(console.name,60) and console.name or
            console and bounded(console.id,60) and console.id or "Unknown",
        consoleIndex=chosen,consoleCount=total,
        consoleDetailAvailable=console and console.detailAvailable==true or false,
        entries={},enabled=0,disabled=0,unknown=0,notExposed=0,
        nativeTranscriptReadable=false,nativeSocialSendAvailable=false,
        isReadOnlySubscriptionMetadata=true}
    if category=="public" then
        local names=console and type(console.publicChannels)=="table"
            and console.publicChannels or {}
        for i,name in ipairs(names) do
            if i>16 then break end
            if bounded(name,72) then
                out.entries[#out.entries+1]={label=name,state="ON",
                    apiKey="channel",source="native_public_channel_subscription"}
                out.enabled=out.enabled+1
            end
        end
        out.unknown=console and console.publicChannelsTruncated and 1 or 0
    else
        local flags=console and type(console.channels)=="table"
            and console.channels or {}
        for _,pair in ipairs(def.items) do
            local label,key=pair[1],pair[2]
            -- Physical RIFT console proof: unchecked Notoriety,
            -- Experience and Crafting Others were absent (nil) in a
            -- *successful* Inspect.Console.Detail snapshot, not false.
            -- In this documented boolean subscription map, absence after
            -- successful detail retrieval means unchecked. If Detail
            -- itself is unavailable, never invent an OFF value.
            local state
            if key==false then state="N/A"
            elseif flags[key]==true then state="ON"
            elseif flags[key]==false or out.consoleDetailAvailable then
                state="OFF"
            else state="?" end
            out.entries[#out.entries+1]={label=label,
                apiKey=key or false,state=state,
                source=key==false and "native_ui_only_no_documented_api_flag"
                    or "inspect_console_detail"}
            if state=="ON" then out.enabled=out.enabled+1
            elseif state=="OFF" then out.disabled=out.disabled+1
            elseif state=="N/A" then out.notExposed=out.notExposed+1
            else out.unknown=out.unknown+1 end
        end
    end
    return out
end
local function cut(s,max)
    if #s<=max then return s end
    return s:sub(1,max-3).."..."
end
function Registry.summary(snapshot,category,index)
    local name=category or "game"
    if name=="channels" then name="public" end
    local group,err=Registry.group(snapshot,name,index)
    if not group then return nil,err end
    local pieces={}
    for _,entry in ipairs(group.entries) do
        pieces[#pieces+1]=entry.label.."="..entry.state
    end
    if #pieces==0 then pieces[1]="none reported (unknown other subscriptions)" end
    local heading=group.consoleName.." / "..group.title..": "
    local footer=" | native settings only; NOT chat history"
    return cut(heading..table.concat(pieces,"; ")..footer,470)
end
function Registry.overview(snapshot,index)
    local picked=Registry.choose(snapshot,index)
    local bits={}
    for _,name in ipairs(order) do
        local group=Registry.group(snapshot,name,index)
        bits[#bits+1]=name..":"..group.enabled.." ON/"
            ..group.disabled.." OFF/"..group.unknown.." ?"
    end
    return (picked and picked.name or "Unknown").." | "
        ..table.concat(bits,"; ").." | subscriptions only, no player-chat text"
end
_G.RiftChatModernConsoleCategories=Registry
-- No values returned from a RIFT RunOnStartup source file.
