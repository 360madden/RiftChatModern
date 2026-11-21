"use strict";

// Opt-in, bounded live RIFT Log.txt follower for the ONE physically observed
// player-social syntax (2026 Say). No input, clipboard, game focus, file writes,
// or persistence. Only newly appended, newline-complete records are eligible.
const fs=require("node:fs");
const path=require("node:path");
const crypto=require("node:crypto");
const {LogTailProbe}=require(path.resolve(__dirname,"..","..","LuaPadModern","tools","rift-log-probe.cjs"));
const {attachChatObserver,validLogPath}=require("./rcm-chat-observer.cjs");
const {encodeRecord}=require("./rcm-chat-import.cjs");

const MAX_PENDING=200;
function parseArgs(argv) {
  const out={timeoutMs:30000,pollMs:100,maxMessages:20,prepareImport:false};
  const seen=new Set();
  for(let i=0;i<argv.length;i++) {
    const flag=argv[i];
    if(seen.has(flag))throw Error("Duplicate option: "+flag);
    seen.add(flag);
    if(flag==="--help"){out.help=true;continue;}
    if(flag==="--prepare-import"){out.prepareImport=true;continue;}
    if(!["--path","--timeout-ms","--poll-ms","--max-messages"].includes(flag) ||
       typeof argv[i+1]!=="string")throw Error("Unsupported or incomplete option: "+flag);
    const val=argv[++i];
    if(flag==="--path"){out.filePath=validLogPath(val);continue;}
    if(!/^\d+$/.test(val))throw Error("Option must be an integer: "+flag);
    const n=Number(val);
    const limits={
      "--timeout-ms":[1000,300000],"--poll-ms":[25,1000],"--max-messages":[1,100]
    }[flag];
    if(!Number.isSafeInteger(n)||n<limits[0]||n>limits[1])
      throw Error("Option out of range: "+flag);
    out[{"--timeout-ms":"timeoutMs","--poll-ms":"pollMs",
         "--max-messages":"maxMessages"}[flag]]=n;
  }
  if(!out.help&&!out.filePath)throw Error("Supply --path ABSOLUTE_Log.txt");
  return out;
}
function sourceInfo(file) {
  const st=fs.lstatSync(file);
  if(!st.isFile()||st.isSymbolicLink())throw Error("Expected an existing regular Log.txt");
  return st;
}
function anchorFor(file, offset) {
  const size=Math.min(128,offset);
  const start=offset-size;
  const fd=fs.openSync(file,"r");
  try {
    const b=Buffer.alloc(size);
    if(fs.readSync(fd,b,0,size,start)!==size)
      throw Error("Source changed while checking its baseline");
    return crypto.createHash("sha256").update(b).digest("hex");
  }finally{fs.closeSync(fd);}
}
function isObservedSay(e) {
  return e.event==="candidate_chat" &&
    e.format==="rift-live-2026-say" &&
    e.verifiedLiveFormat===true && e.kind==="general" &&
    e.channel==="Say" && e.source==="RIFT_Log.txt";
}
function follow(cfg, emit=(x)=>process.stdout.write(JSON.stringify(x)+"\n")) {
  sourceInfo(cfg.filePath); // Deliberately reject absent/ambiguous log sources.
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
     pending.length!==0 || overloaded) {
    tailer.close();throw Error("Could not establish a clean log EOF baseline");
  }
  const baselineOffset=tailer.offset;
  const fileKey=tailer.fileKey;
  const baselineAnchor=anchorFor(cfg.filePath,baselineOffset);
  let checkpointOffset=baselineOffset;
  let checkpointAnchor=baselineAnchor;
  const baselineOversized=tailer.oversizedLineCount;
  const start=Date.now();
  function finish(reason,code=0){
    if(finished)return;
    finished=true;
    if(timer!==null)clearInterval(timer);
    tailer.close();
    emit({event:"finished",reason,delivered,skipped,polls,
      gameInputSent:false,editorDeliveryVerified:false,diskSavedVerified:false});
    process.exitCode=code;
  }
  emit({event:"started",mode:"bounded_verified_say_follow",
    source:"RIFT_Log.txt",format:"rift-live-2026-say",
    baselineOffset,timeoutMs:cfg.timeoutMs,maxMessages:cfg.maxMessages,
    prepareImport:cfg.prepareImport,oldHistoryReplayed:false,
    senderAndTextRedacted:!cfg.prepareImport,
    gameInputSent:false,editorDeliveryVerified:false});
  function pollOnce(){
    if(finished)return;
    if(Date.now()-start>=cfg.timeoutMs){finish("timeout");return;}
    let events;
    try {
      const info=sourceInfo(cfg.filePath);
      if(info.size<checkpointOffset || tailer.fileKey!==fileKey ||
         anchorFor(cfg.filePath,checkpointOffset)!==checkpointAnchor) {
        finish("log_identity_changed",2);return;
      }
      pending=[];overloaded=false;
      events=tailer.poll();
      // Validate again AFTER polling: a source reset during the read must
      // never publish candidates collected from the wrong file generation.
      const after=sourceInfo(cfg.filePath);
      if(after.size<tailer.offset ||
         String(after.dev)+":"+String(after.ino)!==fileKey ||
         anchorFor(cfg.filePath,checkpointOffset)!==checkpointAnchor){
        pending=[];finish("log_identity_changed",2);return;
      }
      // Pin the most recently consumed bytes, not just the original startup
      // prefix. This detects in-place rewriting of later log records before
      // the next batch can be emitted.
      checkpointOffset=tailer.offset;
      checkpointAnchor=anchorFor(cfg.filePath,checkpointOffset);
    }catch(_) {finish("log_read_error_or_source_changed",2);return;}
    polls++;
    // Read-line callbacks run before poll returns file reset/error evidence.
    // Discard ALL pending lines from an ambiguous poll.
    if(overloaded || tailer.oversizedLineCount!==baselineOversized ||
       tailer.fileKey!==fileKey ||
       events.some(e=>["file_reset","file_disappeared","read_error"].includes(e.event))) {
      pending=[];finish(overloaded?"candidate_backpressure":
        "log_reset_or_corrupt_line",2);return;
    }
    for(const {event,record} of pending) {
      if(!isObservedSay(event))continue; // Never promote historical guesses.
      if(event.truncated || !record || record.truncated ||
         record.textBytes!==Buffer.byteLength(record.text,"utf8")) {
        skipped++;emit({event:"say_skipped",reason:"truncated_chat_body"});
        continue;
      }
      let batch=null;
      if(cfg.prepareImport){
        try{batch=encodeRecord(record,undefined,"editor");}
        catch(_){
          skipped++;emit({event:"say_skipped",reason:"unencodable_chat_body"});
          continue;
        }
      }
      delivered++;
      emit({event:"say_observed",sequence:delivered,format:event.format,
        channel:"Say",kind:"general",textBytes:event.textBytes,
        source:"RIFT_Log.txt",gameTimestamp:event.gameTimestamp,
        senderRedacted:true,textRedacted:true,verifiedLiveFormat:true,
        physicalRiftOriginVerified:false});
      if(batch)emit(batch);
      if(delivered>=cfg.maxMessages){finish("message_limit_reached");return;}
    }
    pending=[];
  }
  timer=setInterval(pollOnce,cfg.pollMs);
  process.once("SIGINT",()=>finish("interrupted",130));
  return {stop:()=>finish("stopped"),pollOnce};
}
function run(argv=process.argv.slice(2)){
  let cfg;
  try {
    cfg=parseArgs(argv);
    if(cfg.help) {
      process.stdout.write("Usage: node tools/rcm-live-say-follow.cjs --path ABSOLUTE_Log.txt "+
        "[--timeout-ms 30000] [--poll-ms 100] [--max-messages 20] [--prepare-import]\n"+
        "Read-only, session-bounded follower. Only post-start, physically observed Say syntax. "+
        "Without --prepare-import sender/text stay redacted; with it encoded :import batches "+
        "are printed for separate manual delivery. No RIFT keyboard, clipboard or file writes.\n");
      return;
    }
    follow(cfg);
  }catch(e){
    process.stderr.write("RCM Say follow refused: "+e.message+"\n");
    process.exitCode=2;
  }
}
if(require.main===module)run();
module.exports={parseArgs,sourceInfo,anchorFor,isObservedSay,follow,run};
