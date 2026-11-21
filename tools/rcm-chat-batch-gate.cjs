"use strict";
const {StringDecoder}=require("node:string_decoder");

// Select exactly one proven *candidate* batch from the RCM two-phase observer.
// Input: bounded RCM observer JSONL on stdin.
// Output: one complete RCM1 editor import JSON object, or no stdout on failure.
// Does NOT claim physical RIFT origin, send input, or change logging settings.
const MAX_LINES=150;
const MAX_LINE_BYTES=16384;
const MAX_TOTAL_BYTES=512*1024;

function extract(lines) {
  if (!Array.isArray(lines) || lines.length>MAX_LINES)
    throw Error("Invalid or unbounded observer stream");
  let started=false,matched=false,armed=false,finished=false;
  let exactSeen=0,awaitImport=false,selected=null;
  let count=0;
  for (const item of lines) {
    count++;
    if (!item || typeof item!=="object" || Array.isArray(item) ||
        typeof item.event!=="string")
      throw Error("Malformed observer event");
    if (finished)throw Error("Observer emitted records after finished");
    if (item.event==="started"){
      if (started || count!==1 ||
          item.requireChatAfterMarker!==true ||
          item.expectedChatTextRequired!==true ||
          item.prepareImport!==true || item.inputMode!=="editor" ||
          item.transportVerified!==false ||
          item.automaticGameInput!==false)
        throw Error("Observer is not in exact-match editor preparation mode");
      started=true;
      continue;
    }
    if (!started)throw Error("No initial observer started record");
    if (item.event==="matched") {
      if (armed || matched)throw Error("Repeated or ambiguous log marker");
      matched=true;continue;
    }
    if (item.event==="chat_phase_armed"){
      if (!matched || armed || item.mode!=="fresh_tail_after_marker")
        throw Error("Unverified chat phase arming");
      armed=true;continue;
    }
    if (item.event==="log_path_selected"){
      // An absent configured file may be created when logging starts.
      // Reselecting a path is acceptable only before the marker.
      if(matched || armed || typeof item.path!=="string" || !item.path)
        throw Error("Chat source changed after marker");
      continue;
    }
    if (item.event==="chat_phase_rearmed" ||
        item.event==="file_reset" || item.event==="file_disappeared" ||
        item.event==="read_error")
      throw Error("Chat source identity or arm state changed");
    if (item.event==="candidate_chat"){
      if (!armed || item.afterMarker!==true)
        throw Error("Candidate arrived before the proven marker boundary");
      if (awaitImport)throw Error("Missing import record after exact candidate");
      if (item.chatTextMatched===true) {
        // Historically this gate refused *all* verifiedLiveFormat=true
        // because no physical format had been proven. RIFT Live Say was
        // independently established on Nov 21 2026, and can now pass with
        // its exact narrow shape. This still does not prove that the event
        // was emitted by the physical process; the separate receipt does.
        const observedSay=item.verifiedLiveFormat===true &&
          item.format==="rift-live-2026-say" &&
          item.kind==="general" && item.channel==="Say";
        const legacyCandidate=item.verifiedLiveFormat===false ||
          item.verifiedLiveFormat===undefined;
        if (item.truncated===true || item.source!=="RIFT_Log.txt" ||
            (!observedSay && !legacyCandidate))
          throw Error("Invalid or falsely verified exact candidate");
        exactSeen++;
        if (exactSeen>1)throw Error("Multiple matching chat candidates");
        awaitImport=true;
      }
      continue;
    }
    if (item.event==="rcm_manual_import"){
      if (!awaitImport || selected!==null)
        continue; // Non-matching candidate's preview is not a selected batch.
      if (item.protocol!=="RCM1-B64URL" || item.inputMode!=="editor" ||
          item.automaticGameInput!==false ||
          item.liveGameDeliveryVerified!==false ||
          item.requiresManualEntry!==true ||
          !Array.isArray(item.commands))
        throw Error("Invalid prepared editor batch");
      selected=item;
      awaitImport=false;
      continue;
    }
    if (item.event==="import_skipped"){
      if (awaitImport)throw Error("Exact matching chat was not encodable");
      continue;
    }
    if (item.event==="finished"){
      if (!matched || !armed || awaitImport || exactSeen!==1 ||
          selected===null || item.reason!=="exact_chat_candidate_after_marker" ||
          item.expectedChatTextRequired!==true || item.chatTextMatched!==true ||
          item.probeMatched!==true ||
          item.transportVerified!==false ||
          item.physicalRiftOriginVerified!==false ||
          !Number.isSafeInteger(item.chatCandidatesAfterMarker) ||
          item.chatCandidatesAfterMarker<1)
        throw Error("No complete exact-chat-after-marker candidate receipt");
      finished=true;
      continue;
    }
    // Other metadata diagnostics are intentionally ignored; never include
    // raw_log_sample decoded text in stdout.
  }
  if (!finished || selected===null)
    throw Error("Observer stream finished without one exact prepared batch");
  return selected;
}

async function main(argv=process.argv.slice(2)){
  if (argv.length>1 || (argv.length===1 && argv[0]!=="--status"))
    throw Error("Only optional --status is supported");
  const showStatus=argv[0]==="--status";
  const lines=[];
  let total=0,partial="";
  const decoder=new StringDecoder("utf8");
  function takeLine(line){
    if (!line || Buffer.byteLength(line,"utf8")>MAX_LINE_BYTES ||
        lines.length>=MAX_LINES)
      throw Error("Observer record count or line size exceeded");
    let event;
    try{event=JSON.parse(line);}
    catch(_){throw Error("Malformed observer JSON line");}
    lines.push(event);
    if(!showStatus || !event || typeof event!=="object")return;
    if(event.event==="started"){
      const nonce=typeof event.nonce==="string" &&
        /^[A-Za-z0-9_-]{8,80}$/.test(event.nonce)
          ? event.nonce : "(see observer configuration)";
      process.stderr.write(
        "RCM watcher started. Enter :logprobe "+nonce+
        " in RCM's focused editor once logging is enabled.\n");
      if(event.persistedLogConsole===false)
        process.stderr.write(
          "RIFT.cfg has LogConsole=False; live logging remains unverified.\n");
    }else if(event.event==="chat_phase_armed"){
      process.stderr.write(
        "RCM chat phase armed. Send the exact chosen test text in native RIFT chat now.\n");
    }else if(event.event==="candidate_chat" && event.chatTextMatched===true){
      process.stderr.write(
        "RCM exact candidate observed; waiting for final observer receipt.\n");
    }else if(event.event==="finished"){
      process.stderr.write(
        "RCM observer finished; validating the one candidate batch.\n");
    }
  }
  function drain(){
    let index;
    while((index=partial.indexOf("\n"))!==-1){
      const line=partial.slice(0,index).replace(/\r$/,"");
      partial=partial.slice(index+1);
      takeLine(line);
    }
    if(Buffer.byteLength(partial,"utf8")>MAX_LINE_BYTES)
      throw Error("Observer line exceeds byte limit");
  }
  for await (const chunk of process.stdin){
    const bytes=Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    total+=bytes.length;
    if(total>MAX_TOTAL_BYTES)
      throw Error("Observer stream exceeds byte budget");
    partial+=decoder.write(bytes);
    drain();
  }
  partial+=decoder.end();
  drain();
  if(partial)takeLine(partial.replace(/\r$/,""));
  const selected=extract(lines);
  process.stdout.write(JSON.stringify(selected)+"\n");
}

if(require.main===module)main().catch(()=>{
  process.stderr.write("RCM batch gate could not read observer stream\n");
  process.exitCode=2;
});
module.exports={extract,main};
