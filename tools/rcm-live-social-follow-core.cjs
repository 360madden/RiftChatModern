"use strict";

// Shared bounded, read-only current-client RIFT Log.txt stream follower.
// Profile selection is explicit; each profile admits only a physically
// observed syntax. Log continuity is enforced before any batch is emitted.
// Never sends game input, edits RIFT files, or resumes old EOF on restart.
const fs=require("node:fs");
const path=require("node:path");
const crypto=require("node:crypto");
const {LogTailProbe}=require(path.resolve(__dirname,"..","..","LuaPadModern","tools","rift-log-probe.cjs"));
const {attachChatObserver,validLogPath}=require("./rcm-chat-observer.cjs");
const {encodeRecord}=require("./rcm-chat-import.cjs");

const MAX_PENDING=200;
const PROFILES=Object.freeze({
  say:Object.freeze({
    mode:"bounded_verified_say_follow",
    format:"rift-live-2026-say",
    kind:"general",channel:"Say",slot:null,
    event:"say_observed",skipped:"say_skipped"
  }),
  public:Object.freeze({
    mode:"bounded_verified_public_follow",
    format:"rift-live-2026-numbered-public",
    kind:"public",channel:"Level 1-29",slot:4,
    event:"public_observed",skipped:"public_skipped"
  })
});
function profileFor(name){
  if(!Object.hasOwn(PROFILES,name))throw Error("unknown_capture_profile");
  return PROFILES[name];
}
function parseArgs(argv){
  const out={timeoutMs:30000,pollMs:100,maxMessages:20,prepareImport:false};
  const seen=new Set();
  for(let i=0;i<argv.length;i++){
    const flag=argv[i];
    if(seen.has(flag))throw Error("Duplicate option: "+flag);
    seen.add(flag);
    if(flag==="--help"){out.help=true;continue;}
    if(flag==="--prepare-import"){out.prepareImport=true;continue;}
    if(!["--path","--timeout-ms","--poll-ms","--max-messages"].includes(flag)||
       typeof argv[i+1]!=="string")throw Error("Unsupported or incomplete option: "+flag);
    const val=argv[++i];
    if(flag==="--path"){out.filePath=validLogPath(val);continue;}
    if(!/^\d+$/.test(val))throw Error("Option must be an integer: "+flag);
    const n=Number(val);
    const bounds={"--timeout-ms":[1000,300000],
      "--poll-ms":[25,1000],"--max-messages":[1,100]}[flag];
    if(!Number.isSafeInteger(n)||n<bounds[0]||n>bounds[1])
      throw Error("Option out of range: "+flag);
    out[{"--timeout-ms":"timeoutMs","--poll-ms":"pollMs",
      "--max-messages":"maxMessages"}[flag]]=n;
  }
  if(!out.help&&!out.filePath)throw Error("Supply --path ABSOLUTE_Log.txt");
  return out;
}
function sourceInfo(file){
  const st=fs.lstatSync(file);
  if(!st.isFile()||st.isSymbolicLink())throw Error("Expected an existing regular Log.txt");
  return st;
}
function anchorFor(file,offset){
  const size=Math.min(128,offset);
  const fd=fs.openSync(file,"r");
  try{
    const b=Buffer.alloc(size);
    if(fs.readSync(fd,b,0,size,offset-size)!==size)
      throw Error("Source changed while checking its baseline");
    return crypto.createHash("sha256").update(b).digest("hex");
  }finally{fs.closeSync(fd);}
}
function isObserved(profileName,e){
  const p=profileFor(profileName);
  return !!e && e.event==="candidate_chat" &&
    e.format===p.format && e.verifiedLiveFormat===true &&
    e.kind===p.kind && e.channel===p.channel && e.source==="RIFT_Log.txt" &&
    (p.slot===null || e.channelSlot===p.slot);
}
function follow(cfg, emit=(x)=>process.stdout.write(JSON.stringify(x)+"\n"),
                profileName="say"){
  const p=profileFor(profileName);
  sourceInfo(cfg.filePath);
  const tailer=new LogTailProbe({filePath:cfg.filePath,
    nonce:"RCM_FOLLOW_"+crypto.randomBytes(8).toString("hex")});
  let pending=[],overloaded=false,finished=false,timer=null;
  let delivered=0,skipped=0,polls=0;
  attachChatObserver(tailer,(event,record)=>{
    if(pending.length>=MAX_PENDING){overloaded=true;return;}
    pending.push({event,record});
  },false);
  const baselineEvents=tailer.poll();
  if(!tailer.opened || baselineEvents.some(x=>x.event!=="file_opened") ||
     pending.length!==0||overloaded){
    tailer.close();throw Error("Could not establish a clean log EOF baseline");
  }
  const baselineOffset=tailer.offset;
  const fileKey=tailer.fileKey;
  let checkpointOffset=baselineOffset;
  let checkpointAnchor=anchorFor(cfg.filePath,checkpointOffset);
  const baselineOversized=tailer.oversizedLineCount;
  const startedAt=Date.now();
  function finish(reason,code=0){
    if(finished)return;
    finished=true;
    if(timer!==null)clearInterval(timer);
    tailer.close();
    emit({event:"finished",reason,delivered,skipped,polls,
      gameInputSent:false,editorDeliveryVerified:false,diskSavedVerified:false});
    process.exitCode=code;
  }
  emit({event:"started",mode:p.mode,source:"RIFT_Log.txt",format:p.format,
    channel:p.channel,channelSlot:p.slot,kind:p.kind,
    baselineOffset,timeoutMs:cfg.timeoutMs,maxMessages:cfg.maxMessages,
    prepareImport:cfg.prepareImport,oldHistoryReplayed:false,
    senderAndTextRedacted:!cfg.prepareImport,
    gameInputSent:false,editorDeliveryVerified:false});
  function pollOnce(){
    if(finished)return;
    if(Date.now()-startedAt>=cfg.timeoutMs){finish("timeout");return;}
    let events;
    try{
      const info=sourceInfo(cfg.filePath);
      if(info.size<checkpointOffset || tailer.fileKey!==fileKey ||
         anchorFor(cfg.filePath,checkpointOffset)!==checkpointAnchor){
        finish("log_identity_changed",2);return;
      }
      pending=[];overloaded=false;
      events=tailer.poll();
      const after=sourceInfo(cfg.filePath);
      if(after.size<tailer.offset ||
         String(after.dev)+":"+String(after.ino)!==fileKey ||
         anchorFor(cfg.filePath,checkpointOffset)!==checkpointAnchor){
        pending=[];finish("log_identity_changed",2);return;
      }
      checkpointOffset=tailer.offset;
      checkpointAnchor=anchorFor(cfg.filePath,checkpointOffset);
    }catch(_){finish("log_read_error_or_source_changed",2);return;}
    polls++;
    // Callback order precedes source-state evidence. Never publish a
    // candidate from a poll that reset/replaced its source or overflowed.
    if(overloaded || tailer.oversizedLineCount!==baselineOversized ||
       tailer.fileKey!==fileKey ||
       events.some(e=>["file_reset","file_disappeared","read_error"].includes(e.event))){
      pending=[];finish(overloaded?"candidate_backpressure":
        "log_reset_or_corrupt_line",2);return;
    }
    for(const {event,record} of pending){
      if(!isObserved(profileName,event))continue;
      if(event.truncated || !record || record.truncated ||
         record.textBytes!==Buffer.byteLength(record.text,"utf8")){
        skipped++;emit({event:p.skipped,reason:"truncated_chat_body"});continue;
      }
      let batch=null;
      if(cfg.prepareImport){
        try{batch=encodeRecord(record,undefined,"editor");}
        catch(_){skipped++;emit({event:p.skipped,reason:"unencodable_chat_body"});continue;}
      }
      delivered++;
      emit({event:p.event,sequence:delivered,format:p.format,
        kind:p.kind,channel:p.channel,channelSlot:p.slot,
        textBytes:event.textBytes,source:"RIFT_Log.txt",
        gameTimestamp:event.gameTimestamp,senderRedacted:true,textRedacted:true,
        verifiedLiveFormat:true,physicalRiftOriginVerified:false});
      if(batch)emit(batch);
      if(delivered>=cfg.maxMessages){finish("message_limit_reached");return;}
    }
    pending=[];
  }
  timer=setInterval(pollOnce,cfg.pollMs);
  process.once("SIGINT",()=>finish("interrupted",130));
  return {stop:()=>finish("stopped"),pollOnce};
}
function start(argv=process.argv.slice(2),profileName="say"){
  let cfg,p;
  try{p=profileFor(profileName);cfg=parseArgs(argv);}
  catch(e){process.stderr.write(e.message+"\n");process.exitCode=1;return;}
  if(cfg.help){
    const file=profileName==="say"?"rcm-live-say-follow.cjs":"rcm-live-public-follow.cjs";
    process.stdout.write("node tools/"+file+" --path ABSOLUTE_Log.txt "+
      "[--timeout-ms 30000] [--poll-ms 100] [--max-messages 20] [--prepare-import]\n"+
      "Read-only new-only "+p.channel+" follower for only "+p.format+". "+
      (p.slot===null?"":"Requires physically observed channel slot "+p.slot+". ")+
      "Default output redacts sender/text; --prepare-import emits private encoded editor batches. "+
      "Never sends RIFT input or writes game files.\n");
    return;
  }
  try{follow(cfg,undefined,profileName);}
  catch(e){process.stderr.write("RCM "+profileName+" follow refused: "+e.message+"\n");process.exitCode=2;}
}
module.exports={PROFILES,parseArgs,sourceInfo,anchorFor,isObserved,follow,start};
