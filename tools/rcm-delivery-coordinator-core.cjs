"use strict";

// RCM host-only delivery coordinator; explicitly pinned to one real-game
// social profile and its private state file. No automatic Windows input.
// Source integrity and game/disk receipts must be verified independently.
// Claim != game receipt; only the existing disk auditor can verify a save.
const fs=require("node:fs");
const path=require("node:path");
const os=require("node:os");
const {spawn,spawnSync}=require("node:child_process");
const {resolveDotnet}=require("./rcm-dotnet-host.cjs");
const {validLogPath}=require("./rcm-chat-observer.cjs");
const stateModule=require("./rcm-say-delivery-state.cjs");
const followerProfiles=require("./rcm-live-social-follow-core.cjs").PROFILES;
function createCoordinator(profileName="say"){
  const store=stateModule.createStore(profileName);
  const profile=store.profile;
  const follower=followerProfiles[profileName];
  if(!follower || follower.format!==profile.format ||
     follower.kind!==profile.kind || follower.channel!==profile.channel ||
     follower.slot!==profile.slot)throw Error("coordinator_profile_mismatch");

const FOLLOW=path.resolve(__dirname,profileName==="say"?
  "rcm-live-say-follow.cjs":"rcm-live-public-follow.cjs");
const AUDITOR=path.resolve(__dirname,"rcm_disk_receipt.py");
const SENDER=path.resolve(__dirname,"RcmEditorSender","bin","Release",
  "net10.0-windows","RcmEditorSender.dll");
const DEFAULT_STATE=path.resolve(__dirname,"..","artifacts",
  "rcm-private-queue",profile.filename);
const TOKEN=/^[A-F0-9]{12}$/;
function fail(why){throw Error(why);}
function parseOptions(argv){
  const command=argv[0];
  if(!["capture","status","claim","preflight","dispatch","verify-disk","cancel","recover","help"].includes(command))
    fail("Use capture, status, claim, preflight, dispatch, verify-disk, cancel, recover, or help");
  const o={command,state:DEFAULT_STATE,timeoutMs:30000,pollMs:100,maxMessages:20};
  const seen=new Set();
  for(let i=1;i<argv.length;i++){
    const name=argv[i];
    if(!/^--[a-z0-9-]+$/.test(name)||seen.has(name))fail("unknown_or_duplicate_option");
    seen.add(name);
    if(name==="--ack-discard"){o.ackDiscard=true;continue;}
    if(name==="--ack-abandoned-capture"){o.ackAbandonedCapture=true;continue;}
    if(name==="--ack-send-in-game"){o.ackSendInGame=true;continue;}
    if(name==="--ack-editor-focused"){o.ackEditorFocused=true;continue;}
    if(name==="--ack-submit"){o.ackSubmit=true;continue;}
    if(name==="--ack-batch"){o.ackBatch=true;continue;}
    const val=argv[++i];
    if(typeof val!=="string"||!val)fail("missing_option_value");
    if(name==="--state")o.state=store.validStatePath(val);
    else if(name==="--path")o.filePath=validLogPath(val);
    else if(name==="--file")o.savedFile=path.resolve(val);
    else if(name==="--python"){
      if(!path.isAbsolute(val))fail("python_path_must_be_absolute");
      o.python=path.resolve(val);
    }else if(name==="--token"){
      if(!TOKEN.test(val))fail("invalid_transfer_token");
      o.token=val;
    }else if(name==="--expect-host")o.expectHost=val;
    else if(name==="--exe-path")o.exePath=val;
    else if(name==="--exe-sha256")o.exeSha256=val;
    else if(name==="--hwnd")o.hwnd=val;
    else if(name==="--pid")o.pid=val;
    else if(name==="--start-ticks")o.startTicks=val;
    else if(["--timeout-ms","--poll-ms","--max-messages"].includes(name)){
      if(!/^\d+$/.test(val))fail("invalid_numeric_option");
      const n=Number(val);
      const bounds={"--timeout-ms":[1000,300000],
        "--poll-ms":[25,1000],"--max-messages":[1,100]}[name];
      if(!Number.isSafeInteger(n)||n<bounds[0]||n>bounds[1])
        fail("option_out_of_bounds");
      o[{"--timeout-ms":"timeoutMs","--poll-ms":"pollMs",
        "--max-messages":"maxMessages"}[name]]=n;
    }else fail("unknown_option");
  }
  const allowed={
    capture:["--state","--path","--timeout-ms","--poll-ms","--max-messages"],
    status:["--state"],claim:["--state"],preflight:["--state"],
    dispatch:["--state","--expect-host","--pid","--hwnd","--start-ticks",
      "--exe-path","--exe-sha256","--ack-send-in-game","--ack-editor-focused",
      "--ack-submit","--ack-batch"],
    "verify-disk":["--state","--token","--file","--python"],
    cancel:["--state","--token","--ack-discard"],
    recover:["--state","--ack-abandoned-capture"],help:[]
  }[command];
  if([...seen].some(x=>!allowed.includes(x)))fail("invalid_option_for_action");
  if(command==="capture"&&!o.filePath)fail("capture_requires_log_path");
  if(command==="dispatch"){
    if(!o.ackSendInGame||!o.ackEditorFocused||!o.ackSubmit||!o.ackBatch)
      fail("dispatch_requires_four_explicit_acknowledgments");
    if(o.expectHost!==os.hostname()||!/^[1-9][0-9]{0,9}$/.test(o.pid||"")||
       !/^0x[0-9a-fA-F]{1,12}$/.test(o.hwnd||"")||
       !/^[0-9]{18,19}$/.test(o.startTicks||"")||
       !path.isAbsolute(o.exePath||"")||
       !/^[a-fA-F0-9]{64}$/.test(o.exeSha256||""))
      fail("dispatch_target_pins_missing_or_invalid");
  }
  if(command==="verify-disk"&&(!o.savedFile||!o.python))fail("verify_requires_saved_file_and_python");
  if(command==="cancel"&&(!o.token||!o.ackDiscard))fail("cancel_requires_token_and_ack_discard");
  if(command==="recover"&&!o.ackAbandonedCapture)
    fail("recover_requires_explicit_abandoned_capture_acknowledgment");
  return o;
}
function emit(o){process.stdout.write(JSON.stringify(o)+"\n");}
function safeError(err){return String(err&&err.message||err).slice(0,180);}
async function capture(o,output=emit){
  return store.withLock(o.state,async()=>{
    // A crash during capture leaves a 'capturing' session and a lock.
    // Never silently resume/read old log bytes after an uncertain boundary.
    const journal=store.readState(o.state);
    const sessionId=store.beginSession(journal);
    store.save(o.state,journal); // durable BEFORE starting the tailer
    let initialized=false,observed=null,finished=null;
    let failure=null,lineBuffer="",totalBytes=0,stderrBytes=0;
    const argv=[FOLLOW,"--path",o.filePath,"--timeout-ms",String(o.timeoutMs),
      "--poll-ms",String(o.pollMs),"--max-messages",String(o.maxMessages),
      "--prepare-import"];
    const child=spawn(process.execPath,argv,{shell:false,windowsHide:true,
      stdio:["ignore","pipe","pipe"]});
    function consumeLine(line){
      if(line.length>16384)fail("follower_record_oversized");
      let e;
      try{e=JSON.parse(line);}catch(_){fail("invalid_follower_json");}
      if(!e||typeof e!=="object"||Array.isArray(e)||typeof e.event!=="string")
        fail("invalid_follower_event");
      if(finished)fail("follower_records_after_finished");
      if(e.event==="started"){
        if(initialized||e.mode!==follower.mode||
           e.source!=="RIFT_Log.txt"||e.format!==profile.format||
           e.channel!==profile.channel || e.channelSlot!==profile.slot ||
           e.kind!==profile.kind ||
           e.prepareImport!==true||e.oldHistoryReplayed!==false||
           e.gameInputSent!==false||e.editorDeliveryVerified!==false)
          fail("follower_did_not_establish_verified_eof");
        initialized=true;
        output({event:"capture_started",sessionId,oldHistoryReplayed:false,
          gameInputSent:false});
      }else{
        if(!initialized)fail("follower_event_before_started");
        if(e.event===follower.event){
          if(observed||!store.isObservedReceipt(e))
            fail("unpaired_or_invalid_say_receipt");
          observed=e;
        }else if(e.event==="rcm_manual_import"){
          if(!observed)fail("batch_without_observed_say");
          const accepted=store.acceptPair(journal,sessionId,observed,e);
          store.save(o.state,journal); // one atomic journal entry per batch
          output({event:"capture_queued",sessionId,token:accepted.token,
            sequence:accepted.sequence,gameInputSent:false,
            editorDeliveryVerified:false});
          observed=null;
        }else if(e.event===follower.skipped){
          if(observed||!["truncated_chat_body","unencodable_chat_body"].includes(e.reason))
            fail("invalid_skipped_message");
        }else if(e.event==="finished"){
          if(observed)fail("incomplete_observed_say_pair");
          if(!Number.isSafeInteger(e.delivered)||
             e.delivered!==journal.sessions.find(s=>s.id===sessionId).received||
             e.gameInputSent!==false||e.editorDeliveryVerified!==false||
             e.diskSavedVerified!==false)
            fail("follower_finished_receipt_mismatch");
          finished=e;
        }else fail("unexpected_follower_event");
      }
    }
    const exitCode=await new Promise(resolve=>{
      child.stdout.on("data",chunk=>{
        if(failure)return;
        totalBytes+=chunk.length;
        if(totalBytes>256*1024){failure="follower_output_budget_exceeded";child.kill();return;}
        lineBuffer+=chunk.toString("utf8");
        if(lineBuffer.length>32768){failure="follower_line_buffer_exceeded";child.kill();return;}
        let end;
        while((end=lineBuffer.indexOf("\n"))!==-1&&!failure){
          const line=lineBuffer.slice(0,end).replace(/\r$/,"");
          lineBuffer=lineBuffer.slice(end+1);
          try{consumeLine(line);}catch(err){failure=safeError(err);child.kill();}
        }
      });
      child.stderr.on("data",chunk=>{
        stderrBytes+=chunk.length;
        if(stderrBytes>16384){failure="follower_stderr_budget_exceeded";child.kill();}
      });
      child.once("error",()=>{failure="follower_process_failed";});
      child.once("close",code=>resolve(code));
    });
    if(lineBuffer.trim())failure=failure||"incomplete_follower_stream";
    const okay=!failure&&exitCode===0&&finished&&initialized&&
      ["timeout","message_limit_reached"].includes(finished.reason);
    store.completeSession(journal,sessionId,!!okay,
      okay?finished.reason:(failure||"follower_failed_or_interrupted"));
    store.save(o.state,journal);
    output({event:"capture_finished",sessionId,
      state:okay?"completed":"failed",
      queued:journal.entries.filter(e=>e.sessionId===sessionId&&e.status==="queued").length,
      quarantined:journal.entries.filter(e=>e.sessionId===sessionId&&e.status==="quarantined").length,
      reason:okay?finished.reason:(failure||"follower_failed_or_interrupted"),
      gameInputSent:false});
    return okay?0:2;
  });
}
function withGlobalEditorClaimLock(statePath,fn){
  // The Lua import receiver serializes batches globally, not by channel.
  // Separate private journals therefore share ONE exclusive claim/input lock.
  store.ensureStateFolder(statePath);
  const dir=path.dirname(statePath);
  const lock=path.join(dir,stateModule.GLOBAL_EDITOR_LOCK);
  let fd;
  try{fd=fs.openSync(lock,"wx",0o600);}
  catch(_){fail("global_editor_claim_lock_held_inspect_before_recovery");}
  try{
    fs.writeFileSync(fd,JSON.stringify({pid:process.pid,profile:profileName,
      when:new Date().toISOString()})+"\n");
    fs.fsyncSync(fd);fs.closeSync(fd);fd=null;
    const otherName=profileName==="say"?"public":"say";
    const otherStore=stateModule.createStore(otherName);
    const otherPath=path.join(dir,otherStore.profile.filename);
    const other=otherStore.readState(otherPath);
    if(other.entries.some(e=>e.status==="claimed"))
      fail("other_profile_delivery_unresolved");
    return fn(other);
  }finally{
    if(fd!==undefined && fd!==null)fs.closeSync(fd);
    fs.unlinkSync(lock);
  }
}
function rejectCrossProfileToken(other,token){
  if(other.entries.some(e=>e.token===token))
    fail("cross_profile_transfer_token_collision");
}
function claim(o,output=emit){
  return withGlobalEditorClaimLock(o.state,other=>store.withLock(o.state,()=>{
    const journal=store.readState(o.state);
    const e=store.claimNext(journal);
    rejectCrossProfileToken(other,e.token);
    store.save(o.state,journal); // durable before showing private batch
    output(e.batch); // no game input
    return 0;
  }));
}
function senderCall(item,pins=null){
  if(!fs.existsSync(SENDER))fail("release_editor_sender_not_built");
  const dotnet=resolveDotnet();
  if(!dotnet)fail("dotnet_host_not_found");
  const batch=JSON.stringify(item.batch);
  if(Buffer.byteLength(batch,"utf8")>8192)fail("sender_batch_over_budget");
  const argv=[SENDER,"--stdin-batch"];
  if(pins){
    argv.push("--send","--ack-editor-focused","--submit","--ack-submit",
      "--ack-batch","--expect-host",pins.expectHost,"--pid",pins.pid,
      "--hwnd",pins.hwnd,"--start-ticks",pins.startTicks,
      "--exe-path",pins.exePath,"--exe-sha256",pins.exeSha256);
  }
  const result=spawnSync(dotnet,argv,{input:batch+"\n",encoding:"utf8",
    timeout:30000,maxBuffer:64*1024,windowsHide:true});
  if(result.error || typeof result.stdout!=="string" ||
     result.stdout.length>16384)
    return {ok:false,status:"sender_failed_without_reliable_receipt",
      inputUnknown:!!pins};
  let receipt;
  try{receipt=JSON.parse(result.stdout);}
  catch(_){return {ok:false,status:"sender_unparseable_receipt",inputUnknown:!!pins};}
  if(receipt.schema!=="RCM_EDITOR_SEND_V1"||
     (receipt.token!==undefined&&receipt.token!==item.token))
    return {ok:false,status:"sender_token_or_schema_mismatch",inputUnknown:!!pins};
  if(!pins){
    if(result.status!==0||receipt.status!=="batch_validated_no_input"||
       receipt.gameInputSent!==false||receipt.token!==item.token||
       receipt.parts!==item.batch.parts)
      return {ok:false,status:"sender_validation_not_proven",inputUnknown:false};
    return {ok:true,status:receipt.status,token:item.token,
      sha256:receipt.sha256,gameInputSent:false};
  }
  // Even successful Win32 SendInput does not prove RCM consumed the transfer.
  const reported=receipt.gameInputSent;
  const ok=result.status===0 &&
    receipt.status==="windows_batch_and_enter_inserted_game_receipts_unverified" &&
    receipt.token===item.token && reported===true;
  return {ok,status:typeof receipt.status==="string"?receipt.status:"unknown",
    inputUnknown:reported!==false,gameInputSent:reported===true?true:
      reported===false?false:null,token:item.token,
    charsInserted:Number.isSafeInteger(receipt.charsInserted)?receipt.charsInserted:null,
    completedParts:Number.isSafeInteger(receipt.completedParts)?receipt.completedParts:null};
}
function previewSender(o,output=emit){
  const state=store.readState(o.state);
  const item=state.entries.find(e=>e.status==="claimed")||
    state.entries.find(e=>e.status==="queued"&&
      state.sessions.some(s=>s.id===e.sessionId&&s.state==="completed"));
  if(!item)fail("no_eligible_transfer_for_sender_preview");
  const outcome=senderCall(item);
  if(!outcome.ok)fail(outcome.status);
  output({event:"editor_sender_preflight",token:item.token,
    status:outcome.status,sha256:outcome.sha256,
    gameInputSent:false,diskSavedVerified:false,messageTextEmitted:false});
  return 0;
}
function dispatch(o,output=emit){
  return withGlobalEditorClaimLock(o.state,other=>store.withLock(o.state,()=>{
    const state=store.readState(o.state);
    if(state.entries.some(e=>e.status==="claimed"))
      fail("previous_delivery_unresolved");
    const next=state.entries.find(e=>e.status==="queued"&&
      state.sessions.some(s=>s.id===e.sessionId&&s.state==="completed"));
    if(!next)fail("no_eligible_queued_transfer");
    rejectCrossProfileToken(other,next.token);
    const prepared=senderCall(next);
    if(!prepared.ok)fail("sender_preflight_failed_before_claim");
    const item=store.claimNext(state);
    store.save(o.state,state); // durable BEFORE any Windows key invocation
    const result=senderCall(item,o);
    item.senderReceipt={status:result.status,gameInputSent:result.gameInputSent??null,
      inputUnknown:result.inputUnknown,recordedAt:new Date().toISOString()};
    store.save(o.state,state); // failed/partial receipts NEVER requeue automatically
    output({event:"editor_sender_attempted",token:item.token,
      senderStatus:result.status,windowsInputReported:result.gameInputSent??null,
      addonAcceptedVerified:false,diskSavedVerified:false,
      retryAllowed:false,stillClaimed:true,messageTextEmitted:false});
    return result.ok?0:2;
  }));
}
function verifyDisk(o,output=emit){
  return store.withLock(o.state,()=>{
    const journal=store.readState(o.state);
    const item=journal.entries.find(e=>e.status==="claimed");
    if(!item)fail("no_claimed_transfer_to_verify");
    if(o.token&&o.token!==item.token)fail("active_transfer_token_mismatch");
    if(path.basename(o.savedFile).toLowerCase()!=="riftchatmodern.lua")
      fail("invalid_saved_file_path");
    if(!fs.existsSync(o.python)||!fs.existsSync(AUDITOR))
      fail("disk_verifier_not_installed");
    const params=[AUDITOR,"--file",o.savedFile,"--require-checkpoint",
      "--require-import-token",item.token,"--expect-host",os.hostname()];
    const result=spawnSync(o.python,params,{encoding:"utf8",timeout:15000,
      maxBuffer:256*1024,windowsHide:true,stdio:["ignore","pipe","pipe"]});
    if(result.error||result.status!==0){
      output({event:"disk_not_verified",token:item.token,
        remains:"claimed",gameInputSentUnknown:true,
        retryAllowed:false,messageTextEmitted:false});
      return 2;
    }
    let receipt;
    try{receipt=JSON.parse(result.stdout);}
    catch(_){fail("invalid_disk_auditor_receipt");}
    store.applyDiskProof(journal,item.token,receipt);
    store.save(o.state,journal);
    output({event:"disk_saved_verified",token:item.token,
      saveSha256:receipt.sha256,diskReceiptVerified:true,
      messageTextEmitted:false});
    return 0;
  });
}
function cancel(o,output=emit){
  return store.withLock(o.state,()=>{
    const journal=store.readState(o.state);
    const item=store.cancelClaim(journal,o.token);
    store.save(o.state,journal);
    output({event:"delivery_cancelled",token:item.token,reason:"operator_discarded",
      willNotRetry:true,messageTextEmitted:false});
    return 0;
  });
}
function recover(o,output=emit){
  return store.withLock(o.state,()=>{
    const journal=store.readState(o.state);
    const sessions=journal.sessions.filter(s=>s.state==="capturing");
    if(!sessions.length)fail("no_abandoned_capture");
    for(const s of sessions)
      store.completeSession(journal,s.id,false,"operator_confirmed_interrupted");
    store.save(o.state,journal);
    output({event:"abandoned_capture_quarantined",sessions:sessions.length,
      messageTextEmitted:false});
    return 0;
  });
}
function run(argv=process.argv.slice(2),output=emit){
  const o=parseOptions(argv);
  if(o.command==="help"){
    output({event:"usage",text:[
      "capture --path ABSOLUTE_Log.txt [--timeout-ms 30000] [--max-messages 20] [--poll-ms 100]",
      "status",
      "claim  (one batch; marks in-flight BEFORE printing; no game input)",
      "preflight  (read-only .NET 10 validation of one batch; no game input)",
      "dispatch --expect-host HOST --pid PID --hwnd 0xHEX --start-ticks TICKS --exe-path PATH --exe-sha256 SHA256 --ack-send-in-game --ack-editor-focused --ack-submit --ack-batch",
      "verify-disk --file ABSOLUTE_RiftChatModern.lua --python ABSOLUTE_python.exe [--token TOKEN]",
      "cancel --token TOKEN --ack-discard  (never requeue uncertain input)",
      "recover --ack-abandoned-capture (only after checking no follower/owner active)",
      "All actions optionally take --state ABSOLUTE_"+profile.filename+"."
    ]});
    return 0;
  }
  if(o.command==="capture")return capture(o,output);
  if(o.command==="status"){
    output({event:"delivery_status",...store.summary(store.readState(o.state))});
    return 0;
  }
  if(o.command==="claim")return claim(o,output);
  if(o.command==="preflight")return previewSender(o,output);
  if(o.command==="dispatch")return dispatch(o,output);
  if(o.command==="verify-disk")return verifyDisk(o,output);
  if(o.command==="cancel")return cancel(o,output);
  return recover(o,output);
}
function main(argv){
  Promise.resolve().then(()=>run(argv)).then(code=>{process.exitCode=code||0;})
    .catch(e=>{
      // Never print private batch content on errors.
      process.stderr.write("RCM "+profileName+" delivery refused: "+safeError(e)+"\n");
      process.exitCode=2;
    });
}
return {DEFAULT_STATE,profile,parseOptions,capture,claim,previewSender,dispatch,
  verifyDisk,cancel,recover,run,main};
}
module.exports={createCoordinator};
