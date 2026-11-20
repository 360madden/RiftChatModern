"use strict";

// RCM Windows-side candidate chat reader. RIFT Live chat format is not yet
// physically verified. Reuses LuaPadModern's bounded LogTailProbe file decoder.
// No game injection, no saved-variable edits, no live socket, no background service.
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const {encodeRecord}=require("./rcm-chat-import.cjs");
const {
  LogTailProbe, defaultLogPaths, validateNonce
} = require(path.resolve(__dirname, "..", "..", "LuaPadModern", "tools", "rift-log-probe.cjs"));

const MAX_TEXT_BYTES = 512;
const MAX_LINE = 8192;
const CHANNELS = new Map([
  ["say","general"], ["local","general"], ["yell","general"], ["emote","general"],
  ["party","party"], ["raid","party"], ["raid warning","party"],
  ["guild","guild"], ["officer","guild"], ["guild officer","guild"],
  ["tell","tell"], ["whisper","tell"], ["private","tell"], ["pm","tell"]
]);
const NON_SOCIAL = new Set([
  "system","npc","combat","combatgood","combatbad","combatspecial",
  "combatother","combatneutral","notification","alert","error","warning",
  "crafting","experience","achievement","loot","lootmoney","lootitem",
  "lootgroup","accolade","notoriety","purchase","skill","quest",
  "addons","dev","debug"
]);

function cleanField(value, max) {
  return typeof value === "string" && value.length>0 &&
    Buffer.byteLength(value,"utf8") <= max &&
    !/[\x00-\x1F\x7F]/.test(value);
}

function safePrefix(value, maxBytes) {
  const bytes=Buffer.from(value,"utf8");
  if(bytes.length<=maxBytes)return {text:value,truncated:false};
  let length=maxBytes;
  // Truncate only at a UTF-8 character boundary, not midway in a code point.
  while(length>0 && (bytes[length]&0xC0)===0x80) length--;
  return {text:bytes.subarray(0,length).toString("utf8"),truncated:true};
}
function classifyChannel(raw) {
  if(!cleanField(raw,72))return null;
  const value=raw.trim();
  const stripped=value.replace(/^\d{1,3}[.:\s-]+\s*/,"");
  const key=stripped.toLowerCase().replace(/\s+/g," ");
  if(CHANNELS.has(key))return {kind:CHANNELS.get(key), channel:stripped};
  if(NON_SOCIAL.has(key.replace(/[^a-z]/g,"")))return null;
  // Named public chat channels are not a fixed list in RIFT. Accept concise
  // labels only if the sender/message structure is itself a bracketed record.
  if(!/^[\p{L}\p{N}_@. -]{1,72}$/u.test(stripped))return null;
  return {kind:"public",channel:stripped};
}
function isTimestamp(token) {
  return /^\d{1,2}:\d\d(?::\d\d)?(?: [AP]M)?$/i.test(token) ||
    /^\d{4}-\d\d-\d\d(?:[ T]\d\d:\d\d(?::\d\d)?)?$/.test(token);
}
// Historical Bamux/RiftEventTracker splits at "][" and "]:", then reads the
// second bracket field as sender. This strictly parses that candidate shape.
// Format is NOT confirmed for the currently installed RIFT Live client.
function parseCandidateLine(line) {
  if(typeof line!=="string" || Buffer.byteLength(line,"utf8")>MAX_LINE ||
     line.includes("\0"))return null;
  const trimmed=line.replace(/\r$/,"").replace(/^\uFEFF/,"");
  let match=/^\[([^\]\r\n]{1,36})\]\[([^\]\r\n]{1,72})\]\[([^\]\r\n]{1,40})\]: +(.+)$/u.exec(trimmed);
  let time=null,rawChannel,sender,body;
  if(match && isTimestamp(match[1])) {
    [,time,rawChannel,sender,body]=match;
  } else {
    match=/^\[([^\]\r\n]{1,72})\]\[([^\]\r\n]{1,40})\]: +(.+)$/u.exec(trimmed);
    if(!match)return null;
    [,rawChannel,sender,body]=match;
  }
  const channel=classifyChannel(rawChannel);
  if(!channel||!cleanField(sender,40)||!cleanField(body,MAX_LINE))return null;
  const bounded=safePrefix(body,MAX_TEXT_BYTES);
  return {
    event:"candidate_chat",format:"historical-bracket",
    source:"RIFT_Log.txt",verifiedLiveFormat:false,
    kind:channel.kind,channel:channel.channel,sender,
    gameTimestamp:time,text:bounded.text,
    textBytes:Buffer.byteLength(body,"utf8"),truncated:bounded.truncated
  };
}
function attachChatObserver(tailer, onCandidate, includeText=false, onRawLine=null) {
  if(!tailer || typeof tailer.readLine!=="function" ||
     typeof tailer.poll!=="function" || typeof onCandidate!=="function" ||
     (onRawLine!==null && typeof onRawLine!=="function")) {
    throw Error("Unsupported LuaPadModern LogTailProbe interface");
  }
  const original=tailer.readLine;
  let candidateCount=0;
  tailer.readLine=function(line,when) {
    // Raw decoded lines require an explicitly enabled, bounded callback.
    if(onRawLine)onRawLine(line,when);
    // Do not copy marker probes into the social-chat feed.
    if(!line.includes("LPB_PROBE|")){
      const parsed=parseCandidateLine(line);
      if(parsed) {
        candidateCount++;
        const event={...parsed,observedAt:new Date(when).toISOString()};
        if(!includeText)delete event.text;
        onCandidate(event);
      }
    }
    return original.call(tailer,line,when);
  };
  return {getCandidateCount:()=>candidateCount};
}
function validLogPath(value) {
  if(typeof value!=="string" || !path.isAbsolute(value) ||
    path.basename(value).toLowerCase()!=="log.txt") {
    throw Error("Expected an absolute Log.txt path");
  }
  return path.resolve(value);
}
function options(argv) {
  const out={timeoutMs:120000,pollMs:100,maxCandidates:200,includeText:false,
    prepareImport:false,rawSampleLines:0,
    nonce:"RCM_CHAT_"+crypto.randomBytes(8).toString("hex")};
  for(let i=0;i<argv.length;i++) {
    const flag=argv[i];
    if(flag==="--include-text"){out.includeText=true;continue}
    if(flag==="--prepare-import"){out.prepareImport=true;out.includeText=true;continue}
    if(flag==="--help"){out.help=true;continue}
    if(!["--path","--nonce","--timeout-ms","--poll-ms","--max-candidates","--sample-raw-lines"].includes(flag) ||
      !argv[i+1])throw Error("Unsupported or incomplete option: "+flag);
    const val=argv[++i];
    if(flag==="--path")out.filePath=validLogPath(val);
    else if(flag==="--nonce")out.nonce=validateNonce(val);
    else{
      const n=Number(val);
      if(!Number.isSafeInteger(n))throw Error("Option must be an integer: "+flag);
      const range={
        "--timeout-ms":[1000,300000],
        "--poll-ms":[25,1000],
        "--max-candidates":[1,2000],
        "--sample-raw-lines":[1,30]
      }[flag];
      if(n<range[0] || n>range[1])throw Error("Option out of range: "+flag);
      out[{"--timeout-ms":"timeoutMs","--poll-ms":"pollMs",
        "--max-candidates":"maxCandidates","--sample-raw-lines":"rawSampleLines"}[flag]]=n;
    }
  }
  return out;
}
function start(argv=process.argv.slice(2)) {
  let cfg;
  try{cfg=options(argv)}catch(e){process.stderr.write(e.message+"\n");process.exitCode=1;return}
  if(cfg.help){
    process.stdout.write("node tools/rcm-chat-observer.cjs [--path ABSOLUTE_Log.txt] "+
      "[--timeout-ms 120000] [--poll-ms 100] [--max-candidates 200] "+
      "[--nonce TOKEN] [--include-text] [--prepare-import] [--sample-raw-lines 5]\n"+
      "Read-only candidate RIFT chat observer. Defaults to metadata-only. "+
      "Output format historical/unverified. --sample-raw-lines emits bounded decoded log text (explicit opt-in).\n"+
      "--prepare-import prints manual /rcm commands. Never sends game input.\n");
    return;
  }
  const emit=(item)=>process.stdout.write(JSON.stringify(item)+"\n");
  const candidates=cfg.filePath?[]:defaultLogPaths();
  let filePath=cfg.filePath||candidates.find(x=>fs.existsSync(x))||
    candidates.find(x=>fs.existsSync(path.dirname(x)))||candidates[0];
  let remainingCandidates=candidates.length>0&&!fs.existsSync(filePath);
  const startAt=Date.now();
  let count=0,ignoredCount=0,rawSamples=0,completed=false,timer=null;
  let tailer,stats;
  function createTailer(file,fromStart=false){
    const t=new LogTailProbe({filePath:file,nonce:cfg.nonce,fromStart});
    const s=attachChatObserver(t,event=>{
      if(count>=cfg.maxCandidates){ignoredCount++;return}
      count++;
      emit(event);
      if(cfg.prepareImport) {
        // Opt-in manual preview, NOT automatic injection into RIFT.
        // Note: emitted text and slash commands contain the message body.
        try{emit(encodeRecord(event))}
        catch(e){emit({event:"import_skipped",reason:"unencodable_candidate"})}
      }
    },cfg.includeText,(line,observedAt)=>{
      if(rawSamples>=cfg.rawSampleLines)return;
      rawSamples++;
      const preview=safePrefix(line,1024);
      emit({event:"raw_log_sample",source:"RIFT_Log.txt",
        observedAt:new Date(observedAt).toISOString(),encoding:t.encoding||"unknown",
        decodedLine:preview.text,decodedUtf8Bytes:Buffer.byteLength(line,"utf8"),
        lineTruncated:preview.truncated,physicalRiftOriginVerified:false,
        note:"Decoded text, not byte-for-byte disk evidence when source is UTF-16"});
    });
    return {t,s};
  }
  let current=createTailer(filePath);
  tailer=current.t;stats=current.s;
  // Establish baseline before declaring readiness, so new messages can't be
  // missed because of a race between "started" and the initial EOF probe.
  let initial=tailer.poll();
  emit({event:"started",source:"RIFT_Log.txt",path:filePath,nonce:cfg.nonce,
    gameInputSent:false,gameLoggingChanged:false,transportVerified:false,
    candidateFormatVerified:false,includeText:cfg.includeText,
    prepareImport:cfg.prepareImport,rawSampleLines:cfg.rawSampleLines,
    automaticGameInput:false,
    mode:"historical-bracket-candidate",timeoutMs:cfg.timeoutMs});
  function finish(reason,code=0){
    if(completed)return;
    completed=true;if(timer)clearInterval(timer);
    tailer.close();
    emit({event:"finished",reason,candidates:count,ignored:ignoredCount,
      rawSamples,
      probeMatched:Boolean(tailer.match),transportVerified:false,
      elapsedMs:Date.now()-startAt});
    process.exitCode=code;
  }
  for(const x of initial) {
    if(x.event!=="matched")emit(x);
    else {emit(x);finish("marker_matched",0)}
  }
  if(completed)return;
  timer=setInterval(()=>{
    if(Date.now()-startAt>=cfg.timeoutMs){finish("timeout",2);return}
    if(remainingCandidates&&!fs.existsSync(filePath)){
      const discovered=candidates.find(x=>fs.existsSync(x));
      if(discovered){
        tailer.close();filePath=discovered;
        current=createTailer(filePath,true);tailer=current.t;stats=current.s;
        remainingCandidates=false;
        emit({event:"log_path_selected",path:filePath});
      }
    }
    const events=tailer.poll();
    for(const x of events){
      if(x.event!=="matched")emit(x);
      else emit(x);
    }
    if(tailer.match)finish("marker_matched");
    else if(cfg.rawSampleLines>0 && rawSamples>=cfg.rawSampleLines)finish("raw_sample_limit");
    else if(count>=cfg.maxCandidates)finish("candidate_limit");
  },cfg.pollMs);
  process.once("SIGINT",()=>finish("interrupted",130));
}
if(require.main===module)start();
module.exports={parseCandidateLine,attachChatObserver,safePrefix,validLogPath,options,start};
