"use strict";

// RCM private host delivery journal; strictly bound to an explicit profile.
// Never writes RIFT SavedVariables or retries ambiguous keyboard insertion.
const fs=require("node:fs");
const path=require("node:path");
const crypto=require("node:crypto");
const {TextDecoder}=require("node:util");

const PROFILES=Object.freeze({
  say:Object.freeze({schema:"RCM_SAY_DELIVERY_V1",filename:"rcm-say-delivery.json",
    name:"say",kind:"general",wire:"S",channel:"Say",slot:null,
    event:"say_observed",format:"rift-live-2026-say"}),
  public:Object.freeze({schema:"RCM_PUBLIC_DELIVERY_V1",filename:"rcm-public-delivery.json",
    name:"public",kind:"public",wire:"C",channel:"Level 1-29",slot:4,
    event:"public_observed",format:"rift-live-2026-numbered-public"})
});
function createStore(profileName="say"){
const profile=PROFILES[profileName];
if(!profile)throw Error("unknown_delivery_profile");
const SCHEMA=profile.schema;
const MAX_ENTRIES=200,MAX_SESSIONS=50,MAX_FILE=2*1024*1024;
const ENTRY_STATES=new Set(["queued","claimed","disk_saved","cancelled","quarantined"]);
const SESSION_STATES=new Set(["capturing","completed","failed"]);
const TOKEN=/^[A-F0-9]{12}$/;
const textDecoder=new TextDecoder("utf-8",{fatal:true});

function fail(code){throw Error(code);}
function properString(v,min,max){
  return typeof v==="string" && Buffer.byteLength(v,"utf8")>=min &&
    Buffer.byteLength(v,"utf8")<=max && !/[\x00-\x1f\x7f]/.test(v) &&
    Buffer.from(v,"utf8").toString("utf8")===v;
}
function validateBatch(b, observed){
  if(!b||typeof b!=="object"||Array.isArray(b)||
      b.event!=="rcm_manual_import"||b.protocol!=="RCM1-B64URL"||
      !TOKEN.test(b.id||"")||b.kind!==profile.kind||b.inputMode!=="editor"||
      b.source!=="Windows_candidate_parser"||
      b.automaticGameInput!==false||b.liveGameDeliveryVerified!==false||
      b.requiresManualEntry!==true ||
      !Array.isArray(b.commands)||b.commands.length<1||
      b.commands.length>12||b.parts!==b.commands.length)
    fail("invalid_editor_batch");
  const segments=b.commands.map((command,index)=>{
    if(typeof command!=="string"||command.length>160)
      fail("invalid_editor_command");
    const matched=/^:import ([A-F0-9]{12}) ([1-9]\d*)\/([1-9]\d*) ([A-Za-z0-9_-]{1,88})$/.exec(command);
    if(!matched||matched[1]!==b.id||Number(matched[2])!==index+1||
        Number(matched[3])!==b.parts)fail("multipart_order_or_id_mismatch");
    return matched[4];
  });
  if(segments.some((x,i)=>i<segments.length-1 && x.length!==88))
    fail("noncanonical_chunk_size");
  const b64=segments.join("");
  const raw=Buffer.from(b64,"base64url");
  if(raw.length>780 || raw.toString("base64url")!==b64)
    fail("noncanonical_or_oversized_wire");
  let decoded;
  try{decoded=textDecoder.decode(raw);}
  catch(_){fail("invalid_utf8_wire");}
  if(Buffer.byteLength(decoded,"utf8")!==raw.length)fail("invalid_utf8_wire");
  const fields=decoded.split("\0");
  if(fields.length!==4||fields[0]!==profile.wire||fields[2]!==profile.channel||
     !properString(fields[1],1,40)||!properString(fields[3],1,512))
    fail("not_verified_"+profile.name+"_wire");
  if(observed){
    if(!isObservedReceipt(observed)||observed.textBytes!==
       Buffer.byteLength(fields[3],"utf8"))
      fail("observed_message_mismatch");
  }
  return {token:b.id,byteLength:raw.length,textBytes:Buffer.byteLength(fields[3],"utf8"),
    wireSha256:crypto.createHash("sha256").update(raw).digest("hex")};
}
function isObservedReceipt(e){
  return !!e && e.event===profile.event && e.format===profile.format &&
    e.channel===profile.channel && e.kind===profile.kind &&
    e.source==="RIFT_Log.txt" &&
    (profile.slot===null || e.channelSlot===profile.slot) &&
    e.verifiedLiveFormat===true && e.physicalRiftOriginVerified===false &&
    e.senderRedacted===true && e.textRedacted===true &&
    Number.isSafeInteger(e.sequence) && e.sequence>=1 && e.sequence<=100 &&
    Number.isSafeInteger(e.textBytes) && e.textBytes>=1 && e.textBytes<=512 &&
    typeof e.gameTimestamp==="string";
}
function fresh(){
  return {schema:SCHEMA,revision:0,sessions:[],entries:[]};
}
function assertJournal(data){
  if(!data||typeof data!=="object"||Array.isArray(data)||
     data.schema!==SCHEMA||!Number.isSafeInteger(data.revision)||
     data.revision<0||!Array.isArray(data.sessions)||!Array.isArray(data.entries)||
     data.sessions.length>MAX_SESSIONS||data.entries.length>MAX_ENTRIES)
    fail("invalid_delivery_journal");
  const ids=new Set(),tokens=new Set();
  for(const s of data.sessions){
    if(!s||typeof s!=="object"||!TOKEN.test(s.id||"")||
       !SESSION_STATES.has(s.state)||ids.has(s.id)||
       typeof s.startedAt!=="string")
      fail("invalid_delivery_session");
    ids.add(s.id);
  }
  let claimed=0;
  for(const e of data.entries){
    if(!e||typeof e!=="object"||!ENTRY_STATES.has(e.status)||
       !ids.has(e.sessionId)||tokens.has(e.token)||
       !TOKEN.test(e.token||"")||!Number.isSafeInteger(e.sequence)||
       !Number.isSafeInteger(e.textBytes)||e.textBytes<1||
       e.textBytes>512)
      fail("invalid_delivery_entry");
    if(e.status==="claimed")claimed++;
    tokens.add(e.token);
    const validated=validateBatch(e.batch);
    if(validated.token!==e.token || validated.wireSha256!==e.wireSha256 ||
       validated.textBytes!==e.textBytes)fail("stored_batch_drift");
    const owner=data.sessions.find(s=>s.id===e.sessionId);
    if((e.status==="quarantined"&&owner.state!=="failed") ||
       (e.status!=="quarantined"&&owner.state==="failed") ||
       (["claimed","disk_saved","cancelled"].includes(e.status)&&owner.state!=="completed"))
      fail("delivery_state_session_mismatch");
    if(e.status==="disk_saved"&&
       (!e.diskProof||e.diskProof.diskReceiptVerified!==true||
        !/^[0-9a-f]{64}$/.test(e.diskProof.sha256||"")))
      fail("invalid_saved_receipt");
  }
  if(claimed>1)fail("multiple_in_flight_transfers");
  return data;
}
function validStatePath(p){
  if(typeof p!=="string"||!path.isAbsolute(p)||
     path.basename(p).toLowerCase()!==profile.filename)
    fail("state_must_be_absolute_private_journal");
  return path.resolve(p);
}
function readState(file){
  validStatePath(file);
  if(!fs.existsSync(file))return fresh();
  const st=fs.lstatSync(file);
  if(!st.isFile()||st.isSymbolicLink()||st.size>MAX_FILE)
    fail("unsafe_or_oversized_delivery_journal");
  const bytes=fs.readFileSync(file);
  if(bytes.length>MAX_FILE)fail("oversized_delivery_journal");
  let value;
  try{value=JSON.parse(textDecoder.decode(bytes));}
  catch(_){fail("corrupt_delivery_journal");}
  return assertJournal(value);
}
function writeState(file,state){
  validStatePath(file);assertJournal(state);
  const dir=path.dirname(file);
  const stat=fs.lstatSync(dir);
  if(!stat.isDirectory()||stat.isSymbolicLink())fail("unsafe_state_directory");
  if(fs.existsSync(file)){
    const fstat=fs.lstatSync(file);
    if(!fstat.isFile()||fstat.isSymbolicLink())fail("unsafe_existing_state_file");
  }
  const payload=JSON.stringify(state)+"\n";
  if(Buffer.byteLength(payload,"utf8")>MAX_FILE)fail("delivery_journal_full");
  const temp=path.join(dir,".rcm-"+profile.name+"-"+crypto.randomBytes(12).toString("hex")+".tmp");
  let fd;
  try {
    fd=fs.openSync(temp,"wx",0o600);
    fs.writeFileSync(fd,payload,"utf8");
    fs.fsyncSync(fd);
    fs.closeSync(fd);fd=null;
    fs.renameSync(temp,file);
  }finally{
    if(fd!==null&&fd!==undefined)fs.closeSync(fd);
    if(fs.existsSync(temp))fs.unlinkSync(temp);
  }
}
function ensureStateFolder(file){
  validStatePath(file);
  const dir=path.dirname(file);
  fs.mkdirSync(dir,{recursive:true});
  const st=fs.lstatSync(dir);
  if(!st.isDirectory()||st.isSymbolicLink())fail("unsafe_state_directory");
}
function withLock(file,fn){
  ensureStateFolder(file);
  const lock=file+".lock";
  let fd;
  try{fd=fs.openSync(lock,"wx",0o600);}
  catch(_){fail("delivery_lock_held_inspect_before_recovery");}
  let released=false;
  function release(){
    if(released)return;
    released=true;
    if(fd!==null&&fd!==undefined)fs.closeSync(fd);
    fs.unlinkSync(lock);
  }
  try{
    fs.writeFileSync(fd,JSON.stringify({pid:process.pid,when:new Date().toISOString()})+"\n");
    fs.fsyncSync(fd);fs.closeSync(fd);fd=null;
    const result=fn();
    if(result && typeof result.then==="function")return result.finally(release);
    release();return result;
  }catch(e){release();throw e;}
}
function save(file,state){
  state.revision++;
  writeState(file,state);
  return state;
}
function beginSession(state){
  if(state.sessions.some(s=>s.state==="capturing"))
    fail("unfinished_capture_requires_operator_recovery");
  if(state.sessions.length>=MAX_SESSIONS||state.entries.length>=MAX_ENTRIES)
    fail("delivery_journal_capacity_reached");
  const id=crypto.randomBytes(6).toString("hex").toUpperCase();
  state.sessions.push({id,state:"capturing",startedAt:new Date().toISOString(),
    received:0,reason:null});
  return id;
}
function acceptPair(state,sessionId,observed,batch){
  const session=state.sessions.find(s=>s.id===sessionId);
  if(!session||session.state!=="capturing")fail("capture_session_not_active");
  const parsed=validateBatch(batch,observed);
  if(observed.sequence!==session.received+1)fail("capture_sequence_mismatch");
  if(state.entries.length>=MAX_ENTRIES)fail("delivery_journal_capacity_reached");
  if(state.entries.some(x=>x.token===parsed.token))fail("repeated_transfer_token");
  state.entries.push({token:parsed.token,sessionId,
    status:"queued",sequence:observed.sequence,textBytes:parsed.textBytes,
    wireSha256:parsed.wireSha256,batch,createdAt:new Date().toISOString(),
    claimedAt:null,diskProof:null});
  session.received++;
  return {token:parsed.token,sequence:observed.sequence};
}
function completeSession(state,sessionId,success,reason){
  const s=state.sessions.find(x=>x.id===sessionId);
  if(!s||s.state!=="capturing")fail("capture_session_not_active");
  s.state=success?"completed":"failed";
  s.reason=reason;
  s.endedAt=new Date().toISOString();
  if(!success)for(const e of state.entries)
    if(e.sessionId===sessionId&&e.status==="queued")e.status="quarantined";
}
function claimNext(state){
  if(state.sessions.some(s=>s.state==="capturing"))fail("capture_in_progress");
  if(state.entries.some(e=>e.status==="claimed"))
    fail("previous_delivery_unresolved");
  const item=state.entries.find(e=>e.status==="queued"&&
    state.sessions.some(s=>s.id===e.sessionId&&s.state==="completed"));
  if(!item)fail("no_eligible_queued_transfer");
  item.status="claimed";
  item.claimedAt=new Date().toISOString();
  return item;
}
function cancelClaim(state,token){
  const e=state.entries.find(x=>x.token===token);
  if(!e||e.status!=="claimed")fail("no_matching_claimed_transfer");
  e.status="cancelled";e.cancelledAt=new Date().toISOString();
  return e;
}
function applyDiskProof(state,token,receipt){
  const e=state.entries.find(x=>x.token===token);
  if(!e||e.status!=="claimed")fail("no_matching_claimed_transfer");
  if(!receipt||receipt.schema!=="RCM_DISK_RECEIPT_V1"||
     receipt.diskReceiptVerified!==true||
     receipt.requiredImportIdentityMatched!==true||
     receipt.requiredImportTokenPresent!==true||
     receipt.requiredImportToken!==token||
     receipt.checkpointMetadataConsistent!==true||
     receipt.savedVariablesModified!==false||
     !/^[a-f0-9]{64}$/.test(receipt.sha256||""))
    fail("disk_receipt_unverified_or_wrong_token");
  e.diskProof={sha256:receipt.sha256,diskReceiptVerified:true,
    inspectedAt:new Date().toISOString()};
  e.status="disk_saved";
  return e;
}
function summary(state){
  assertJournal(state);
  const counts={queued:0,claimed:0,disk_saved:0,cancelled:0,quarantined:0};
  for(const x of state.entries)counts[x.status]++;
  return {schema:state.schema,revision:state.revision,
    sessions:state.sessions.map(s=>({id:s.id,state:s.state,received:s.received,
      reason:s.reason})),counts,activeToken:state.entries.find(x=>x.status==="claimed")?.token||null,
    messageTextEmitted:false};
}
return {SCHEMA,MAX_ENTRIES,profile,parseBatch:validateBatch,assertJournal,
  fresh,validStatePath,readState,writeState,ensureStateFolder,withLock,save,
  beginSession,acceptPair,completeSession,claimNext,cancelClaim,applyDiskProof,summary,
  isObservedReceipt};
}
module.exports={...createStore("say"),createStore,PROFILES};
