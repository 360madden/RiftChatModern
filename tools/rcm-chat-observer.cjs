"use strict";

// RCM Windows-side chat reader. A narrow Say format was physically verified
// against RIFT Live on 2026-11-21. Other chat formats remain historical candidates.
// Reuses LuaPadModern's bounded LogTailProbe file decoder.
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
  // Exact physical RIFT Live evidence, Nov 21 2026. In the game-created
  // Log.txt, the bracket is the speaker, *not* the channel, and "says"
  // supplies the Say channel. One deliberately sent unique Say token
  // matched this format at source-file level. Do not infer Guild/Tell/Party.
  // A synthetic match to this shape alone does NOT prove RIFT origin.
  const live=/^((?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d): \[([^\]\r\n]{1,40})\] says: (.+)$/u.exec(trimmed);
  if(live) {
    const [,time,sender,body]=live;
    if(!cleanField(sender,40)||!cleanField(body,MAX_LINE))return null;
    const bounded=safePrefix(body,MAX_TEXT_BYTES);
    return {event:"candidate_chat",format:"rift-live-2026-say",
      source:"RIFT_Log.txt",verifiedLiveFormat:true,
      kind:"general",channel:"Say",sender,
      gameTimestamp:time,text:bounded.text,
      textBytes:Buffer.byteLength(body,"utf8"),truncated:bounded.truncated};
  }
  // Confirmed in 20 game-created Log.txt records on 2026-11-21:
  // HH:MM:SS: [4. Level 1-29][Speaker@Shard]: message
  // Only this numbered PUBLIC-CHANNEL structure is established. The index is
  // a live client channel slot, not part of the retained readable channel name.
  // It does NOT establish native Guild/Party/Tell interception or provenance
  // from matching text in an arbitrary synthetic log.
  const livePublic=/^((?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d): \[([1-9]\d{0,2})\. ([^\]\r\n]{1,66})\]\[([^\]\r\n]{1,40})\]: (.+)$/u.exec(trimmed);
  if(livePublic){
    const [,time,slot,name,sender,body]=livePublic;
    const c=classifyChannel(slot+". "+name);
    if(!c || c.kind!=="public" || !cleanField(sender,40) ||
       !cleanField(body,MAX_LINE))return null;
    const bounded=safePrefix(body,MAX_TEXT_BYTES);
    return {event:"candidate_chat",format:"rift-live-2026-numbered-public",
      source:"RIFT_Log.txt",verifiedLiveFormat:true,
      kind:"public",channel:c.channel,channelSlot:Number(slot),sender,
      gameTimestamp:time,text:bounded.text,
      textBytes:Buffer.byteLength(body,"utf8"),truncated:bounded.truncated};
  }
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
function attachChatObserver(tailer, onCandidate, includeText=false, onRawLine=null,
                            requiredChatText=null) {
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
        // Compare the *complete* source message before removing the text.
        // Do not emit a private chat body just to establish exact-match proof.
        if(requiredChatText!==null)
          event.chatTextMatched=!parsed.truncated && parsed.text===requiredChatText;
        if(!includeText)delete event.text;
        // The second argument carries the validated original candidate only
        // to the internal encoder; normal JSONL output can remain redacted.
        onCandidate(event,parsed);
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
// RIFT's [Client] DocumentsDirectory overrides conventional Documents.
// Read the same bounded config once for both the exact log path and its saved
// LogConsole flag. A disk setting is NOT proof of current in-game toggle state.
function readRiftClientConfig(env=process.env) {
  const result={filePath:null,logConsoleConfigured:null,
    configReadable:false,runtimeLoggingEnabledVerified:false};
  const roaming=env.APPDATA ||
    (env.USERPROFILE ? path.join(env.USERPROFILE,"AppData","Roaming") : null);
  if(typeof roaming!=="string" || !path.isAbsolute(roaming))return result;
  const config=path.join(roaming,"RIFT","Rift.cfg");
  let value;
  try {
    const info=fs.statSync(config);
    if(!info.isFile() || info.size>512*1024)return result;
    value=fs.readFileSync(config,"utf8").replace(/^\uFEFF/,"");
  }catch(_){return result}
  result.configReadable=true;
  let section="",root=null;
  for(const line of value.split(/\r?\n/)) {
    const hdr=/^\s*\[([A-Za-z_0-9]+)\]\s*$/.exec(line);
    if(hdr){section=hdr[1].toLowerCase();continue}
    if(section!=="client")continue;
    const item=/^\s*DocumentsDirectory\s*=\s*(.*?)\s*$/.exec(line);
    if(item)root=item[1].trim().replace(/^"(.*)"$/,"$1");
    const flag=/^\s*LogConsole\s*=\s*(.*?)\s*$/i.exec(line);
    if(flag) {
      const raw=flag[1].trim();
      result.logConsoleConfigured=/^true$/i.test(raw) ? true
        : /^false$/i.test(raw) ? false : null;
    }
  }
  if(typeof root!=="string" || root.length===0 || root.length>2048 ||
    /[\x00-\x1F\x7F]/.test(root))return result;
  root=root.replace(/%([A-Za-z_0-9]+)%/g,(_,key)=>{
    const match=Object.keys(env).find(name=>name.toLowerCase()===key.toLowerCase());
    return match ? env[match] : "%"+key+"%";
  });
  if(!path.isAbsolute(root) || root.includes("%"))return result;
  result.filePath=path.join(root,"Log.txt");
  return result;
}
function readConfiguredLogPath(env=process.env) {
  return readRiftClientConfig(env).filePath;
}
function resolveLogSelection(cfg,env=process.env,clientConfig=null) {
  if(cfg.filePath){
    return {filePath:cfg.filePath,candidates:[cfg.filePath],source:"explicit_path"};
  }
  // Keep LuaPadModern's explicit test/user override semantics intact.
  if(env.LUAPAD_LOG_CANDIDATES){
    const candidates=defaultLogPaths(env);
    return {filePath:candidates.find(f=>fs.existsSync(f))||
      candidates.find(f=>fs.existsSync(path.dirname(f)))||candidates[0],
      candidates,source:"luapad_override"};
  }
  const configured=(clientConfig||readRiftClientConfig(env)).filePath;
  if(configured){
    // An absent configured file is more useful than silently tailing an
    // unrelated stale log under some other historical Documents folder.
    return {filePath:configured,candidates:[configured],
      source:"rift_cfg_documents_directory"};
  }
  const candidates=defaultLogPaths(env);
  return {filePath:candidates.find(f=>fs.existsSync(f))||
    candidates.find(f=>fs.existsSync(path.dirname(f)))||candidates[0],
    candidates,source:"generic_documents_fallback"};
}
function options(argv) {
  const out={timeoutMs:120000,pollMs:100,maxCandidates:200,includeText:false,
    prepareImport:false,rawSampleLines:0,requireChatAfterMarker:false,
    requireChatText:null,inputMode:"native",inputModeExplicit:false,
    nonce:"RCM_CHAT_"+crypto.randomBytes(8).toString("hex")};
  for(let i=0;i<argv.length;i++) {
    const flag=argv[i];
    if(flag==="--include-text"){out.includeText=true;continue}
    if(flag==="--prepare-import"){out.prepareImport=true;continue}
    if(flag==="--require-chat-after-marker"){
      if(out.requireChatAfterMarker)throw Error("Duplicate two-phase option");
      out.requireChatAfterMarker=true;continue;
    }
    if(flag==="--help"){out.help=true;continue}
    if(!["--path","--nonce","--timeout-ms","--poll-ms","--max-candidates","--sample-raw-lines","--require-chat-text","--input-mode"].includes(flag) ||
      !argv[i+1])throw Error("Unsupported or incomplete option: "+flag);
    const val=argv[++i];
    if(flag==="--path")out.filePath=validLogPath(val);
    else if(flag==="--nonce")out.nonce=validateNonce(val);
    else if(flag==="--input-mode"){
      if(out.inputModeExplicit || !["native","editor"].includes(val))
        throw Error("Input mode must be native or editor, specified once");
      out.inputMode=val;out.inputModeExplicit=true;
    }
    else if(flag==="--require-chat-text"){
      if(out.requireChatText!==null || !/^[A-Za-z0-9_-]{8,80}$/.test(val))
        throw Error("Exact chat text must be a unique 8-80 character ASCII test token");
      out.requireChatText=val;
    }
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
  if(out.requireChatText!==null && !out.requireChatAfterMarker)
    throw Error("Exact chat text requires --require-chat-after-marker");
  if(out.inputModeExplicit && !out.prepareImport)
    throw Error("--input-mode requires explicit --prepare-import");
  return out;
}
function start(argv=process.argv.slice(2)) {
  let cfg;
  try{cfg=options(argv)}catch(e){process.stderr.write(e.message+"\n");process.exitCode=1;return}
  if(cfg.help){
    process.stdout.write("node tools/rcm-chat-observer.cjs [--path ABSOLUTE_Log.txt] "+
      "[--timeout-ms 120000] [--poll-ms 100] [--max-candidates 200] "+
      "[--nonce TOKEN] [--include-text] [--prepare-import] [--input-mode editor] [--sample-raw-lines 5] "+
      "[--require-chat-after-marker] [--require-chat-text TEST_TOKEN]\n"+
      "Read-only candidate RIFT chat observer. Defaults to metadata-only. "+
      "Two-phase mode arms a new file tail after the marker before counting social candidates. "+
      "Physical RIFT Live Say format verified on 2026-11-21; other social formats remain historical candidates. --sample-raw-lines emits bounded decoded log text (explicit opt-in).\n"+
      "--prepare-import outputs manual native /rcm or RCM editor :import commands. Never sends game input.\n");
    return;
  }
  // An initial poll can observe a newly created log and call readLine before
  // the readiness receipt is printed. Buffer only those bounded early callbacks
  // so downstream consumers can always treat `started` as the first event.
  const early=[];
  let startedEmitted=false;
  const emit=(item)=>{
    if(!startedEmitted && item.event!=="started"){
      early.push(item);return;
    }
    if(item.event==="started")startedEmitted=true;
    process.stdout.write(JSON.stringify(item)+"\n");
  };
  const clientConfig=readRiftClientConfig();
  const selection=resolveLogSelection(cfg,process.env,clientConfig);
  const candidates=selection.candidates;
  let filePath=selection.filePath;
  let remainingCandidates=candidates.length>0&&!fs.existsSync(filePath);
  const startAt=Date.now();
  let count=0,ignoredCount=0,rawSamples=0,completed=false,timer=null;
  let markerMatched=false,chatPhaseArmed=false,chatCandidatesAfterMarker=0;
  let exactChatTextMatched=false;
  let pendingCandidates=[];
  let tailer,stats;
  function publishCandidate(event,fullRecord){
    if(count>=cfg.maxCandidates){ignoredCount++;return}
    count++;
    if(cfg.requireChatAfterMarker && chatPhaseArmed){
      chatCandidatesAfterMarker++;
      event.afterMarker=true;
      if(cfg.requireChatText!==null && event.chatTextMatched===true)
        exactChatTextMatched=true;
    }
    emit(event);
    if(cfg.prepareImport){
      // Opt-in manual preview, NOT automatic injection into RIFT.
      // Never represent a shortened candidate as an original chat body.
      if(event.truncated){
        emit({event:"import_skipped",reason:"truncated_chat_body"});
      }else{
        try{emit(encodeRecord(fullRecord,undefined,cfg.inputMode))}
        catch(e){emit({event:"import_skipped",reason:"unencodable_candidate"})}
      }
    }
  }
  function createTailer(file,fromStart=false){
    const t=new LogTailProbe({filePath:file,nonce:cfg.nonce,fromStart});
    const s=attachChatObserver(t,(event,fullRecord)=>{
      // A chat line observed BEFORE the marker cannot satisfy the second
      // stage, even if it arrived in the same filesystem read as the marker.
      if(cfg.requireChatAfterMarker && !chatPhaseArmed)return;
      if(cfg.requireChatAfterMarker){
        // File reset/error events are reported AFTER readLine callbacks.
        // Defer publication until the poll's source-identity evidence arrives.
        if(pendingCandidates.length>=cfg.maxCandidates){ignoredCount++;return}
        pendingCandidates.push({event,fullRecord});return;
      }
      publishCandidate(event,fullRecord);
    },cfg.includeText,(line,observedAt)=>{
      if(cfg.requireChatAfterMarker && !chatPhaseArmed)return;
      if(rawSamples>=cfg.rawSampleLines)return;
      rawSamples++;
      const preview=safePrefix(line,1024);
      emit({event:"raw_log_sample",source:"RIFT_Log.txt",
        observedAt:new Date(observedAt).toISOString(),encoding:t.encoding||"unknown",
        decodedLine:preview.text,decodedUtf8Bytes:Buffer.byteLength(line,"utf8"),
        lineTruncated:preview.truncated,physicalRiftOriginVerified:false,
        note:"Decoded text, not byte-for-byte disk evidence when source is UTF-16"});
    },cfg.requireChatText);
    return {t,s};
  }
  let current=createTailer(filePath);
  tailer=current.t;stats=current.s;
  // Establish baseline before declaring readiness, so new messages can't be
  // missed because of a race between "started" and the initial EOF probe.
  let initial=tailer.poll();
  emit({event:"started",source:"RIFT_Log.txt",path:filePath,
    pathSelection:selection.source,nonce:cfg.nonce,
    persistedLogConsole:clientConfig.logConsoleConfigured,
    configReadable:clientConfig.configReadable,
    runtimeLoggingEnabledVerified:false,
    loggingReadinessHint:clientConfig.logConsoleConfigured===false
      ? "Rift.cfg LogConsole=False; saved setting suggests noncombat logging off, runtime state unverified; /log is a toggle"
      : clientConfig.logConsoleConfigured===true
        ? "Rift.cfg LogConsole=True; runtime logging still requires a live log receipt"
        : "Rift.cfg LogConsole not verified; runtime logging state unknown",
    gameInputSent:false,gameLoggingChanged:false,transportVerified:false,
    candidateFormatVerified:false,includeText:cfg.includeText,
    prepareImport:cfg.prepareImport,
    inputMode:cfg.prepareImport ? cfg.inputMode : null,
    rawSampleLines:cfg.rawSampleLines,
    requireChatAfterMarker:cfg.requireChatAfterMarker,
    expectedChatTextRequired:cfg.requireChatText!==null,
    automaticGameInput:false,
    mode:cfg.requireChatAfterMarker ? "marker_then_candidate_chat"
      : "bounded_live_say_and_historical_candidates",timeoutMs:cfg.timeoutMs});
  function finish(reason,code=0){
    if(completed)return;
    completed=true;if(timer)clearInterval(timer);
    tailer.close();
    emit({event:"finished",reason,candidates:count,ignored:ignoredCount,
      rawSamples,chatCandidatesAfterMarker,chatPhaseArmed,
      expectedChatTextRequired:cfg.requireChatText!==null,
      chatTextMatched:exactChatTextMatched,
      probeMatched:markerMatched||Boolean(tailer.match),transportVerified:false,
      candidateFormatVerified:false,physicalRiftOriginVerified:false,
      elapsedMs:Date.now()-startAt});
    process.exitCode=code;
  }
  // The shared LuaPad tailer stops reading permanently once its nonce is
  // matched. For a real chat-source trial we must OPEN A NEW tailer at the
  // current end of file, then explicitly tell the operator when to send chat.
  // This prevents pre-marker text (including text in the matching file read)
  // from being misclassified as a post-marker social-chat sample.
  function armChatPhase(rearm=false){
    pendingCandidates=[];
    tailer.close();
    current=createTailer(filePath);
    tailer=current.t;stats=current.s;
    const baseline=tailer.poll();
    for(const event of baseline)emit(event);
    if(!tailer.opened||tailer.match){
      finish("chat_phase_setup_failed",2);return;
    }
    chatPhaseArmed=true;
    emit({event:rearm?"chat_phase_rearmed":"chat_phase_armed",
      source:"RIFT_Log.txt",path:filePath,nonce:cfg.nonce,
      mode:"fresh_tail_after_marker",startingOffset:tailer.offset,
      transportVerified:false,candidateFormatVerified:false,
      gameInputSent:false,
      instruction:"Now send one NEW chat message in RIFT; earlier messages do not count."});
  }
  function markerDetected(){
    markerMatched=true;
    if(cfg.requireChatAfterMarker)armChatPhase(chatPhaseArmed);
    else finish("marker_matched",0);
  }
  // File-open/reset evidence must precede initial candidate callbacks, and
  // marker receipts follow them. A marker found in the first poll is not lost.
  for(const x of initial){if(x.event!=="matched")emit(x)}
  for(const x of early)emit(x);
  for(const x of initial){
    if(x.event==="matched"){emit(x);markerDetected();break}
  }
  if(completed)return;
  timer=setInterval(()=>{
    if(Date.now()-startAt>=cfg.timeoutMs){
      finish(cfg.requireChatAfterMarker&&markerMatched
        ?(cfg.requireChatText!==null
          ?"timeout_waiting_exact_chat_after_marker"
          :"timeout_waiting_chat_after_marker"):"timeout",2);return;
    }
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
    for(const event of events)emit(event);
    if(cfg.requireChatAfterMarker && chatPhaseArmed && events.some(event=>
      event.event==="file_reset" || event.event==="file_disappeared" ||
      event.event==="read_error")){
      // A reset/replacement can replay earlier file bytes. Do not treat
      // candidates in that same poll as fresh post-marker evidence.
      pendingCandidates=[];
      finish("chat_source_changed_after_marker",2);return;
    }
    if(pendingCandidates.length){
      const ready=pendingCandidates;pendingCandidates=[];
      for(const candidate of ready)publishCandidate(candidate.event,candidate.fullRecord);
    }
    if(cfg.requireChatAfterMarker && chatCandidatesAfterMarker>0 &&
       (cfg.requireChatText===null || exactChatTextMatched)){
      finish(cfg.requireChatText!==null
        ?"exact_chat_candidate_after_marker":"chat_candidate_after_marker",0);
      return;
    }
    if(tailer.match){
      markerDetected();return;
    }
    if(cfg.rawSampleLines>0 && rawSamples>=cfg.rawSampleLines){
      finish(cfg.requireChatAfterMarker
        ?"raw_sample_limit_without_chat_candidate":"raw_sample_limit",
        cfg.requireChatAfterMarker?2:0);
    }else if(count>=cfg.maxCandidates){
      finish(cfg.requireChatText!==null && !exactChatTextMatched
        ?"candidate_limit_without_exact_chat"
        :(cfg.requireChatAfterMarker
          ?"chat_candidate_after_marker":"candidate_limit"),
        cfg.requireChatText!==null && !exactChatTextMatched?2:0);
    }
  },cfg.pollMs);
  process.once("SIGINT",()=>finish("interrupted",130));
}
if(require.main===module)start();
module.exports={parseCandidateLine,attachChatObserver,safePrefix,validLogPath,
  readConfiguredLogPath,readRiftClientConfig,resolveLogSelection,options,start};
