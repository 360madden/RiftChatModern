"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const os=require("node:os");
const path=require("node:path");
const crypto=require("node:crypto");
const {spawn,spawnSync}=require("node:child_process");
const queue=require("../tools/rcm-say-delivery-state.cjs");
const cli=require("../tools/rcm-say-delivery.cjs");
const {encodeRecord}=require("../tools/rcm-chat-import.cjs");
const CLI=path.resolve(__dirname,"../tools/rcm-say-delivery.cjs");
const TEST_BODY="RCM_SERIALIZED_20261121";
const PYTHON="C:\\work\\riftreader2\\.venv\\Scripts\\python.exe";
function fixtures(){
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),"rcm-delivery-"));
  return {dir,state:path.join(dir,"rcm-say-delivery.json"),
    log:path.join(dir,"Log.txt"),saved:path.join(dir,"RiftChatModern.lua")};
}
function transfer(text=TEST_BODY,id="A1B2C3D4E5F6"){
  return encodeRecord({kind:"general",sender:"ExampleCharacter",
    channel:"Say",text},id,"editor");
}
function observed(text=TEST_BODY,sequence=1){
  return {event:"say_observed",format:"rift-live-2026-say",
    sequence,kind:"general",channel:"Say",source:"RIFT_Log.txt",
    textBytes:Buffer.byteLength(text,"utf8"),gameTimestamp:"17:17:23",
    senderRedacted:true,textRedacted:true,verifiedLiveFormat:true,
    physicalRiftOriginVerified:false};
}
function result(argv){
  return spawnSync(process.execPath,[CLI,...argv],{
    encoding:"utf8",timeout:10000,maxBuffer:256*1024,windowsHide:true});
}
function savedFixture(token){
  return "RiftChatModernSaved = {\n"+
    "  history = {\n"+
    "    { at = 1701, id = 1, kind = \"import\", source = \"ExampleCharacter\",\n"+
    "      text = \"fixture only\", origin = \"host_manual\",\n"+
    "      channelKind = \"general\", channelName = \"Say\", importToken = \""+token+"\" }\n"+
    "  },\n"+
    "  nextId = 2, schemaVersion = 2,\n"+
    "  saveCheckpoint = {\n"+
    "    at = 1701.125, formatVersion = 1, historyCount = 1,\n"+
    "    lastHistoryId = 1, lastImportId = 1, nextId = 2,\n"+
    "    schemaVersion = 2, sequence = 1\n"+
    "  }\n"+
    "}\n";
}
function seeded(f,entries=1){
  let j=queue.fresh(),id=queue.beginSession(j);
  for(let i=0;i<entries;i++) {
    const body=TEST_BODY+"_"+i;
    queue.acceptPair(j,id,observed(body,i+1),
      transfer(body,i===0?"A1B2C3D4E5F6":"B2C3D4E5F607"));
  }
  queue.completeSession(j,id,true,"message_limit_reached");
  queue.writeState(f.state,j);
  return j;
}
async function captureFixture({changes,maxMessages=2,timeoutMs=1700}={}){
  const f=fixtures();
  fs.writeFileSync(f.log,"17:17:23: [ExampleCharacter] says: STALE_MESSAGE\n");
  const args=[CLI,"capture","--path",f.log,"--state",f.state,
    "--poll-ms","25","--timeout-ms",String(timeoutMs),
    "--max-messages",String(maxMessages)];
  const child=spawn(process.execPath,args,{
    windowsHide:true,stdio:["ignore","pipe","pipe"]});
  let buffer="",stdout="",stderr="",events=[],closed=false,timer;
  const outcome=new Promise((resolve,reject)=>{
    timer=setTimeout(()=>child.kill(),5000);
    child.stdout.on("data",bytes=>{
      stdout+=bytes.toString("utf8");
      buffer+=bytes.toString("utf8");
      let ix;
      while((ix=buffer.indexOf("\n"))!==-1){
        const line=buffer.slice(0,ix);buffer=buffer.slice(ix+1);
        if(!line)continue;
        let item;
        try{item=JSON.parse(line);}catch(err){reject(err);child.kill();return;}
        events.push(item);
        if(item.event==="capture_started"&&changes)changes(f.log);
      }
    });
    child.stderr.on("data",bytes=>{stderr+=bytes.toString("utf8");});
    child.once("error",reject);
    child.once("close",code=>{closed=true;resolve({code,events,stderr,stdout});});
  });
  try{
    const result=await outcome;
    return {...result,journal:queue.readState(f.state),f};
  }finally{
    clearTimeout(timer);
    if(!closed)child.kill();
    // The journal is copied into the returned object before removal.
    fs.rmSync(f.dir,{recursive:true,force:true});
  }
}
test("CLI accepts bounded action-specific options, refuses ambiguous calls",()=>{
  assert.throws(()=>cli.parseOptions(["capture"]),/requires_log/);
  assert.throws(()=>cli.parseOptions(["claim","--path","C:\\x\\Log.txt"]),/invalid_option_for_action/);
  assert.throws(()=>cli.parseOptions(["status","--state","relative.json"]),/absolute/);
  assert.throws(()=>cli.parseOptions(["cancel","--token","A1B2C3D4E5F6"]),/ack_discard/);
  assert.throws(()=>cli.parseOptions(["recover"]),/explicit/);
  assert.throws(()=>cli.parseOptions(["capture","--path","C:\\x\\Log.txt",
    "--timeout-ms","300001"]),/bounds/);
  assert.equal(cli.parseOptions(["help"]).command,"help");
});
test("Say batch validator checks canonical Base64URL, all chunks, provenance and original text size",()=>{
  const b=transfer();
  const verified=queue.parseBatch(b,observed());
  assert.equal(verified.token,"A1B2C3D4E5F6");
  assert.equal(verified.textBytes,Buffer.byteLength(TEST_BODY));
  assert.match(verified.wireSha256,/^[0-9a-f]{64}$/);
  assert.throws(()=>queue.parseBatch(b,{...observed(),textBytes:1}),/mismatch/);
  assert.throws(()=>queue.parseBatch({...b,kind:"guild"}),/invalid_editor_batch/);
  assert.throws(()=>queue.parseBatch({...b,liveGameDeliveryVerified:true}),/invalid_editor_batch/);
  assert.throws(()=>queue.parseBatch({...b,commands:[b.commands[0]+"X"]}),/noncanonical|not_verified/);
  assert.throws(()=>queue.parseBatch({...b,commands:[b.commands[0].replace("1/1","2/1")]}),/order/);
  const nonSay=encodeRecord({kind:"guild",sender:"Example",
    channel:"Guild",text:"fixture"},"A1B2C3D4E5F6","editor");
  assert.throws(()=>queue.parseBatch({...nonSay,kind:"general"}),/not_verified_say_wire/);
});
test("journal atomic round-trip stores one private batch but status never contains chat",()=>{
  const f=fixtures();
  try{
    const j=seeded(f);
    const stored=queue.readState(f.state);
    assert.equal(stored.entries.length,1);
    assert.equal(stored.entries[0].batch.id,"A1B2C3D4E5F6");
    assert.equal(stored.sessions[0].state,"completed");
    assert.equal(queue.summary(stored).counts.queued,1);
    assert.ok(fs.readFileSync(f.state,"utf8").includes("A1B2C3D4E5F6"));
    assert.ok(!JSON.stringify(queue.summary(stored)).includes("ExampleCharacter"));
    assert.ok(!JSON.stringify(queue.summary(stored)).includes(TEST_BODY));
    assert.equal(j.revision,0);
    assert.equal(queue.readState(f.state).revision,0);
  }finally{fs.rmSync(f.dir,{recursive:true,force:true});}
});
test("in-flight claim is durable, serial and no implicit retry after a crash",()=>{
  const f=fixtures();
  try{
    seeded(f,2);
    const first=queue.readState(f.state);
    assert.equal(queue.claimNext(first).token,"A1B2C3D4E5F6");
    queue.save(f.state,first);
    const reopened=queue.readState(f.state);
    assert.equal(reopened.entries[0].status,"claimed");
    assert.throws(()=>queue.claimNext(reopened),/unresolved/);
    assert.equal(queue.cancelClaim(reopened,"A1B2C3D4E5F6").status,"cancelled");
    assert.equal(queue.claimNext(reopened).token,"B2C3D4E5F607");
    assert.throws(()=>queue.cancelClaim(reopened,"A1B2C3D4E5F6"),/no_matching/);
  }finally{fs.rmSync(f.dir,{recursive:true,force:true});}
});
test("failed capture quarantines all queued records and cannot be claimed",()=>{
  const f=fixtures();
  try{
    const j=queue.fresh(),id=queue.beginSession(j);
    queue.acceptPair(j,id,observed(),transfer());
    queue.completeSession(j,id,false,"source_changed");
    assert.equal(j.entries[0].status,"quarantined");
    assert.throws(()=>queue.claimNext(j),/no_eligible/);
    assert.throws(()=>queue.acceptPair(j,id,observed(TEST_BODY,2),transfer()),/not_active/);
  }finally{fs.rmSync(f.dir,{recursive:true,force:true});}
});
test("disk proof requires exact same claimed token, independent checkpoint and SHA",()=>{
  const f=fixtures();
  try{
    const j=seeded(f);
    queue.claimNext(j);
    const proof={schema:"RCM_DISK_RECEIPT_V1",diskReceiptVerified:true,
      requiredImportIdentityMatched:true,requiredImportTokenPresent:true,
      requiredImportToken:"A1B2C3D4E5F6",checkpointMetadataConsistent:true,
      savedVariablesModified:false,sha256:"a".repeat(64)};
    assert.throws(()=>queue.applyDiskProof(j,"A1B2C3D4E5F6",
      {...proof,requiredImportToken:"000000000000"}),/wrong_token/);
    assert.throws(()=>queue.applyDiskProof(j,"A1B2C3D4E5F6",
      {...proof,checkpointMetadataConsistent:false}),/unverified/);
    assert.equal(j.entries[0].status,"claimed");
    queue.applyDiskProof(j,"A1B2C3D4E5F6",proof);
    assert.equal(j.entries[0].status,"disk_saved");
    assert.throws(()=>queue.claimNext(j),/no_eligible/);
  }finally{fs.rmSync(f.dir,{recursive:true,force:true});}
});
test("refuses corrupt journal and concurrent lock; no destructive repair",()=>{
  const f=fixtures();
  try{
    fs.writeFileSync(f.state,"{invalid JSON");
    assert.throws(()=>queue.readState(f.state),/corrupt/);
    fs.unlinkSync(f.state);
    const lock=f.state+".lock";
    fs.writeFileSync(lock,"someone may still own this");
    assert.throws(()=>queue.withLock(f.state,()=>{}),/lock_held/);
    assert.equal(fs.readFileSync(lock,"utf8"),"someone may still own this");
  }finally{fs.rmSync(f.dir,{recursive:true,force:true});}
});
test("two fresh synthetic Say lines flow through real follower to serialized journal",async()=>{
  const r=await captureFixture({changes:file=>{
    fs.appendFileSync(file,"17:17:23: [Alpha] says: CAPTURE_ALPHA\n"+
      "17:17:24: [Beta] says: CAPTURE_BETA\n");
  }});
  assert.equal(r.code,0,r.stderr);
  assert.equal(r.events.filter(x=>x.event==="capture_queued").length,2);
  assert.equal(r.journal.sessions[0].state,"completed");
  assert.equal(r.journal.entries.length,2);
  assert.deepEqual(r.journal.entries.map(x=>x.status),["queued","queued"]);
  assert.ok(!r.stdout.includes("Alpha"));
  assert.ok(!r.stdout.includes("CAPTURE_ALPHA"));
  assert.equal(r.events.at(-1).state,"completed");
});
test("unknown historical Guild lines are never enqueued",async()=>{
  const r=await captureFixture({changes:file=>
    fs.appendFileSync(file,"[Guild][ExampleCharacter]: imagined\n"),
    maxMessages:1,timeoutMs:1300});
  assert.equal(r.code,0,r.stderr);
  assert.equal(r.journal.entries.length,0);
  assert.equal(r.events.at(-1).state,"completed");
});
test("claim CLI emits exactly one batch, subsequent claims refuse, cancel unblocks",()=>{
  const f=fixtures();
  try{
    seeded(f,2);
    const first=result(["claim","--state",f.state]);
    assert.equal(first.status,0,first.stderr);
    assert.equal(JSON.parse(first.stdout).id,"A1B2C3D4E5F6");
    assert.equal(queue.readState(f.state).entries[0].status,"claimed");
    const second=result(["claim","--state",f.state]);
    assert.equal(second.status,2);
    assert.equal(second.stdout,"");
    assert.match(second.stderr,/unresolved/);
    const canceled=result(["cancel","--state",f.state,
      "--token","A1B2C3D4E5F6","--ack-discard"]);
    assert.equal(canceled.status,0,canceled.stderr);
    assert.equal(JSON.parse(canceled.stdout).willNotRetry,true);
    const next=result(["claim","--state",f.state]);
    assert.equal(next.status,0,next.stderr);
    assert.equal(JSON.parse(next.stdout).id,"B2C3D4E5F607");
  }finally{fs.rmSync(f.dir,{recursive:true,force:true});}
});
test("status command hides encoded text, claim command reveals opt-in transfer",()=>{
  const f=fixtures();
  try{
    seeded(f);
    const s=result(["status","--state",f.state]);
    assert.equal(s.status,0,s.stderr);
    assert.equal(JSON.parse(s.stdout).counts.queued,1);
    assert.ok(!s.stdout.includes("ExampleCharacter"));
    assert.ok(!s.stdout.includes("RCM_SERIALIZED"));
    assert.equal(JSON.parse(result(["claim","--state",f.state]).stdout).inputMode,"editor");
  }finally{fs.rmSync(f.dir,{recursive:true,force:true});}
});
test("real Python disk auditor verifies a synthetic exact-token save; failed receipt cannot clear claim",
  {skip:!fs.existsSync(PYTHON)},()=>{
  const f=fixtures();
  try{
    seeded(f);queue.ensureStateFolder(f.state);
    assert.equal(result(["claim","--state",f.state]).status,0);
    fs.writeFileSync(f.saved,savedFixture("000000000000"));
    const fail=result(["verify-disk","--state",f.state,"--file",f.saved,
      "--python",PYTHON]);
    assert.equal(fail.status,2,fail.stderr);
    assert.equal(JSON.parse(fail.stdout).event,"disk_not_verified");
    assert.equal(queue.readState(f.state).entries[0].status,"claimed");
    fs.writeFileSync(f.saved,savedFixture("A1B2C3D4E5F6"));
    const good=result(["verify-disk","--state",f.state,"--file",f.saved,
      "--python",PYTHON,"--token","A1B2C3D4E5F6"]);
    assert.equal(good.status,0,good.stderr);
    assert.equal(JSON.parse(good.stdout).diskReceiptVerified,true);
    assert.equal(queue.readState(f.state).entries[0].status,"disk_saved");
  }finally{fs.rmSync(f.dir,{recursive:true,force:true});}
});
test("unresolved crashed capture is not silently resumed, explicit recovery quarantines it",()=>{
  const f=fixtures();
  try{
    const j=queue.fresh();queue.beginSession(j);queue.writeState(f.state,j);
    const bad=result(["claim","--state",f.state]);
    assert.equal(bad.status,2);
    const recovered=result(["recover","--state",f.state,
      "--ack-abandoned-capture"]);
    assert.equal(recovered.status,0,recovered.stderr);
    assert.equal(queue.readState(f.state).sessions[0].state,"failed");
    assert.equal(result(["claim","--state",f.state]).status,2);
  }finally{fs.rmSync(f.dir,{recursive:true,force:true});}
});
test("sender preflight uses real .NET 10 validator without changing durable queue",()=>{
  const sender=path.resolve(__dirname,"../tools/RcmEditorSender/bin/Release/net10.0-windows/RcmEditorSender.dll");
  if(!fs.existsSync(sender))return;
  const f=fixtures();
  try{
    seeded(f);
    const before=fs.readFileSync(f.state,"utf8");
    const p=result(["preflight","--state",f.state]);
    assert.equal(p.status,0,p.stderr);
    const receipt=JSON.parse(p.stdout);
    assert.equal(receipt.event,"editor_sender_preflight");
    assert.equal(receipt.status,"batch_validated_no_input");
    assert.equal(receipt.gameInputSent,false);
    assert.equal(receipt.token,"A1B2C3D4E5F6");
    assert.equal(fs.readFileSync(f.state,"utf8"),before);
  }finally{fs.rmSync(f.dir,{recursive:true,force:true});}
});
test("dispatch syntax requires exact pins and four explicit acknowledgments",()=>{
  const host=require("node:os").hostname();
  const pins=["--expect-host",host,"--pid","999999999","--hwnd","0x1",
    "--start-ticks","638000000000000000",
    "--exe-path","C:\\nonexistent\\rift_x64.exe",
    "--exe-sha256","0".repeat(64)];
  assert.throws(()=>cli.parseOptions(["dispatch",...pins]),/four_explicit/);
  assert.throws(()=>cli.parseOptions(["dispatch",...pins,"--ack-send-in-game",
    "--ack-editor-focused","--ack-submit","--ack-batch",
    "--exe-sha256","1".repeat(64)]),/duplicate/);
  assert.equal(cli.parseOptions(["dispatch",...pins,"--ack-send-in-game",
    "--ack-editor-focused","--ack-submit","--ack-batch"]).pid,"999999999");
});
test("impossible target pins refuse before input but still leave a no-retry claim",()=>{
  const sender=path.resolve(__dirname,"../tools/RcmEditorSender/bin/Release/net10.0-windows/RcmEditorSender.dll");
  if(!fs.existsSync(sender))return;
  const f=fixtures();
  try{
    seeded(f);
    const args=["dispatch","--state",f.state,
      "--expect-host",require("node:os").hostname(),
      "--pid","999999999","--hwnd","0x1",
      "--start-ticks","638000000000000000",
      "--exe-path","C:\\nonexistent\\rift_x64.exe",
      "--exe-sha256","0".repeat(64),
      "--ack-send-in-game","--ack-editor-focused","--ack-submit","--ack-batch"];
    const res=result(args);
    assert.equal(res.status,2,res.stderr);
    const event=JSON.parse(res.stdout);
    assert.equal(event.event,"editor_sender_attempted");
    assert.equal(event.windowsInputReported,false);
    assert.equal(event.addonAcceptedVerified,false);
    assert.equal(event.retryAllowed,false);
    const state=queue.readState(f.state);
    assert.equal(state.entries[0].status,"claimed");
    assert.equal(state.entries[0].senderReceipt.gameInputSent,false);
    assert.equal(result(args).status,2); // no automatic second attempt
    assert.equal(queue.readState(f.state).entries[0].status,"claimed");
  }finally{fs.rmSync(f.dir,{recursive:true,force:true});}
});
test("journal catches stored wire-digest drift before any claim or dispatch",()=>{
  const f=fixtures();
  try{
    seeded(f);
    const state=queue.readState(f.state);
    state.entries[0].wireSha256="0".repeat(64);
    fs.writeFileSync(f.state,JSON.stringify(state)+"\n");
    assert.throws(()=>queue.readState(f.state),/stored_batch_drift/);
    const attempted=result(["claim","--state",f.state]);
    assert.equal(attempted.status,2);
    assert.equal(attempted.stdout,"");
  }finally{fs.rmSync(f.dir,{recursive:true,force:true});}
});
test("exclusive journal lock remains held throughout an asynchronous capture",async()=>{
  const f=fixtures();
  let release;
  try{
    const running=queue.withLock(f.state,()=>new Promise(resolve=>{release=resolve;}));
    assert.throws(()=>queue.withLock(f.state,()=>{}),/lock_held/);
    release();
    await running;
    assert.equal(fs.existsSync(f.state+".lock"),false);
  }finally{
    if(release)release();
    fs.rmSync(f.dir,{recursive:true,force:true});
  }
});
