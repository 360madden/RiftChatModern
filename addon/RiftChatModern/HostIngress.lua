-- RiftChatModern / HostIngress.lua
-- Manual host-to-addon import of candidate chat text. Lua 5.1, inert data only.
-- NO direct Log.txt access, network connection, native chat interception, or
-- claim of verified player-chat reception. RIFT RunOnStartup returns no value.
local Ingress={}
local Receiver={}
Receiver.__index=Receiver

local ALPHABET="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
local KINDS={S="general",P="party",G="guild",T="tell",C="general"}
local MAX_PARTS,MAX_PART_LEN,MAX_DECODED,MAX_SECONDS=12,88,780,45
local MAX_RECENT=32

local function finite(n)
    return type(n)=="number" and n==n and n>=0 and n<math.huge
end
local function validText(value,minLen,maxLen)
    if type(value)~="string" or #value<minLen or #value>maxLen then return false end
    local i,n=1,#value
    while i<=n do
        local b=value:byte(i)
        if b<32 or b==127 then return false end
        if b<128 then i=i+1
        else
            local len,lo,hi
            if b>=194 and b<=223 then len,lo,hi=2,128,191
            elseif b==224 then len,lo,hi=3,160,191
            elseif b>=225 and b<=236 then len,lo,hi=3,128,191
            elseif b==237 then len,lo,hi=3,128,159
            elseif b>=238 and b<=239 then len,lo,hi=3,128,191
            elseif b==240 then len,lo,hi=4,144,191
            elseif b>=241 and b<=243 then len,lo,hi=4,128,191
            elseif b==244 then len,lo,hi=4,128,143
            else return false end
            if i+len-1>n then return false end
            local b2=value:byte(i+1)
            if b2<lo or b2>hi then return false end
            for j=i+2,i+len-1 do
                local continuation=value:byte(j)
                if continuation<128 or continuation>191 then return false end
            end
            i=i+len
        end
    end
    return true
end
local function decode(base64)
    if type(base64)~="string" or #base64<4 or #base64>MAX_PARTS*MAX_PART_LEN
        or #base64%4==1 then return nil,"invalid_base64" end
    local bits,carry,out=0,0,{}
    for i=1,#base64 do
        local char=base64:sub(i,i)
        local position=ALPHABET:find(char,1,true)
        if not position then return nil,"invalid_base64" end
        carry=carry*64+(position-1)
        bits=bits+6
        if bits>=8 then
            bits=bits-8
            local octet=math.floor(carry/2^bits)
            out[#out+1]=string.char(octet)
            carry=carry%(2^bits)
            if #out>MAX_DECODED then return nil,"too_many_bytes" end
        end
    end
    if carry~=0 then return nil,"invalid_base64_padding" end
    return table.concat(out)
end
local function parsePayload(data)
    if type(data)~="string" or #data>MAX_DECODED then
        return nil,"invalid_payload_size"
    end
    local a=data:find("\0",1,true)
    local b=a and data:find("\0",a+1,true)
    local c=b and data:find("\0",b+1,true)
    if not a or not b or not c then return nil,"invalid_payload" end
    local code=data:sub(1,a-1)
    local sender=data:sub(a+1,b-1)
    local channel=data:sub(b+1,c-1)
    local body=data:sub(c+1)
    if #code~=1 or not KINDS[code] or
        not validText(sender,1,40) or not validText(channel,1,72)
        or not validText(body,1,512) then return nil,"invalid_fields" end
    -- Always mark the unverified outside origin in the displayed text.
    local header="[HOST? "..channel.."] "
    local full=header..body
    local Core=_G.RiftChatModernCore
    if #full>512 and Core and type(Core.utf8Prefix)=="function" then
        full=Core.utf8Prefix(full,512)
    end
    if #full>512 or #full==0 then return nil,"invalid_render" end
    return {kind=KINDS[code],source=sender,text=full,
        originalBytes=#body,unverified=true,channel=channel}
end

function Ingress.new(publish)
    if type(publish)~="function" then return nil,"invalid_publisher" end
    return setmetatable({publish=publish,pending=nil,recent={},seen={},
        acceptedChunks=0,imported=0,rejected=0,duplicates=0,
        expired=0,publishFailed=0},Receiver)
end
function Receiver:_remember(id)
    self.recent[#self.recent+1]=id
    self.seen[id]=true
    if #self.recent>MAX_RECENT then
        local oldest=table.remove(self.recent,1)
        self.seen[oldest]=nil
    end
end
function Receiver:receiveLine(line,at)
    if type(line)~="string" or #line>145 then
        self.rejected=self.rejected+1;return nil,"invalid_line" end
    if not finite(at) then
        self.rejected=self.rejected+1;return nil,"invalid_time" end
    local id,index,total,piece=line:match("^([A-F0-9]+) (%d+)/(%d+) ([A-Za-z0-9_-]+)$")
    if not id or #id~=12 or not index or not total
        or #piece<1 or #piece>MAX_PART_LEN then
        self.rejected=self.rejected+1;return nil,"invalid_chunk" end
    index,total=tonumber(index),tonumber(total)
    if not index or not total or index<1 or total<1 or total>MAX_PARTS
        or index>total then
        self.rejected=self.rejected+1;return nil,"invalid_index" end
    if self.seen[id] then
        self.duplicates=self.duplicates+1;return true,"already_imported" end
    local pending=self.pending
    if pending and at>=pending.at and at-pending.at>MAX_SECONDS then
        self.pending=nil;self.expired=self.expired+1;pending=nil
    end
    if pending and (pending.id~=id or pending.total~=total) then
        self.rejected=self.rejected+1;return nil,"import_busy" end
    if not pending then
        pending={id=id,total=total,parts={},count=0,at=at}
        self.pending=pending
    end
    if pending.parts[index] then
        if pending.parts[index]==piece then
            self.duplicates=self.duplicates+1
            return true,"already_received"
        end
        self.rejected=self.rejected+1;return nil,"conflicting_chunk"
    end
    pending.parts[index]=piece;pending.count=pending.count+1
    self.acceptedChunks=self.acceptedChunks+1
    if pending.count<total then
        return true,"part "..pending.count.."/"..total
    end
    self.pending=nil
    local payload,err=decode(table.concat(pending.parts))
    if not payload then
        self.rejected=self.rejected+1;return nil,err end
    local row,parseErr=parsePayload(payload)
    if not row then
        self.rejected=self.rejected+1;return nil,parseErr end
    local ok,result=pcall(self.publish,row.kind,row.source,row.text,at)
    if not ok or not result then
        self.publishFailed=self.publishFailed+1
        return nil,"publisher_refused"
    end
    self:_remember(id)
    self.imported=self.imported+1
    return true,"imported_unverified"
end
function Receiver:status()
    local p=self.pending
    return {ready=true,mode="manual_slash_only",liveChatVerified=false,
        autoInputAvailable=false,imported=self.imported,
        acceptedChunks=self.acceptedChunks,rejected=self.rejected,
        duplicates=self.duplicates,expired=self.expired,
        publishFailed=self.publishFailed,
        pending=p~=nil,pendingId=p and p.id or nil,
        pendingParts=p and p.count or 0,
        pendingTotal=p and p.total or 0}
end
Ingress.decode=decode
Ingress.parsePayload=parsePayload
_G.RiftChatModernHostIngress=Ingress
-- RIFT RunOnStartup chunks must return no module value.
