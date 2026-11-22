"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const os=require("node:os");
const path=require("node:path");
const {spawn,spawnSync}=require("node:child_process");
const {encodeRecord}=require("../tools/rcm-chat-import.cjs");
const say=require("../tools/rcm-say-delivery-state.cjs");
const pub=say.createStore("public");
const cli=require("../tools/rcm-public-delivery.cjs");
const CLI=path.resolve(__dirname,"../tools/rcm-public-delivery.cjs");
const SENDER=path.resolve(__dirname,"../tools/RcmEditorSender/bin/Release/net10.0-windows/RcmEditorSender.dll");
const PYTHON="C:\\work\\riftreader2\\.venv\\Scripts\\python.exe";
const BODY="RCM_PUBLIC_CHANNEL_FIXTURE_20261121";
const LINE="23:37:21: [4. Level 1-29][Example@Greybriar]: "+BODY+"\n";
const SAY="23:37:22: [Example] says: unrelated say\n";
const OTHER="23:37:23: [5. Events][Example@Greybriar]: unrelated channel\n";
const TOKEN="C0FFEE123456";
function f(){
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),"rcm-public-delivery-"));
  return {dir,state:path.join(dir,"rcm-public-delivery.json"),
    sayState:path.join(dir,"rcm-say-delivery.json"),
    log:path.join(dir,"Log.txt"),saved:path.join(dir,"RiftChatModern.lua")};
}
function record(body=BODY){
  return {kind:"public",sender:"Example@Greybriar",channel:"Level 1-29",text:body};
}
function batch(body=BODY,id=TOKEN){return encodeRecord(record(body),id,"editor");}
function observation(body=BODY,sequence=1,slot=4){
  return {event:"public_observed",format:"rift-live-2026-numbered-public",
    source:"RIFT_Log.txt",kind:"public",channel:"Level 1-29",channelSlot:slot,
    textBytes:Buffer.byteLength(body,"utf8"),gameTimestamp:"23:37:21",
    senderRedacted:true,textRedacted:true,verifiedLiveFormat:true,
    physicalRiftOriginVerified:false,sequence};
}
function run(args,options={}){
  return spawnSync(process.execPath,[CLI,...args],{encoding:"utf8",timeout:11000,
    windowsHide:true,maxBuffer:256*1024,...options});
}
function seed(fx,count=1){
  const state=pub.fresh();
  const id=pub.beginSession(state);
  for(let n=0;n<count;n++){
    const b=BODY+"_"+n,token=n===0?TOKEN:"A1B2C3D4E5F6";
    pub.acceptPair(state,id,observation(b,n+1),batch(b,token));
  }
  pub.completeSession(state,id,true,"message_limit_reached");
  pub.writeState(fx.state,state);
  return state;
}
function savedFixture(token){
  return "RiftChatModernSaved = {\n"+
    " history = {\n"+
    '  { at = 1701, id = 1, kind = "import", origin = "host_manual",'+
    ' channelKind = "public", channelName = "Level 1-29",\n'+
    '    source = "Example", text = "fixture", importToken = "'+token+'" },\n'+
    " }, nextId = 2, schemaVersion = 2,\n"+
    " saveCheckpoint = { at = 1701.25, formatVersion = 1,\n"+
    "  historyCount = 1, nextId = 2, lastHistoryId = 1, lastImportId = 1,\n"+
    "  schemaVersion = 2, sequence = 1 }\n}\n";
}
async function capture({lines=LINE,timeoutMs=1400,maxMessages=1}={}){
  const fx=f();
  fs.writeFileSync(fx.log,"Noncombat logging enabled\n"+LINE);
  const child=spawn(process.execPath,[CLI,"capture","--path",fx.log,
    "--state",fx.state,"--timeout-ms",String(timeoutMs),
    "--poll-ms","25","--max-messages",String(maxMessages)],{
      stdio:["ignore","pipe","pipe"],windowsHide:true});
  let pending="",stderr="",out="",events=[],timer;
  const result=new Promise((resolve,reject)=>{
    timer=setTimeout(()=>child.kill(),5000);
    child.stdout.on("data",chunk=>{
      out+=chunk.toString("utf8");pending+=chunk.toString("utf8");
      let index;
      while((index=pending.indexOf("\n"))!==-1){
        const line=pending.slice(0,index);pending=pending.slice(index+1);
        if(!line)continue;
        let e;try{e=JSON.parse(line)}catch(x){reject(x);child.kill();return}
        events.push(e);
        if(e.event==="capture_started")fs.appendFileSync(fx.log,lines);
      }
    });
    child.stderr.on("data",chunk=>{stderr+=chunk.toString("utf8")});
    child.once("error",reject);
    child.once("close",code=>resolve({code,events,stderr,out}));
  });
  try{
    const resultValue=await result;
    return {...resultValue,state:pub.readState(fx.state)};
  }finally{
    clearTimeout(timer);child.kill();
    fs.rmSync(fx.dir,{recursive:true,force:true});
  }
}
test("strict distinct public profile, defaults, and cross-journal paths",()=>{
  assert.equal(pub.SCHEMA,"RCM_PUBLIC_DELIVERY_V1");
  assert.equal(say.SCHEMA,"RCM_SAY_DELIVERY_V1");
  assert.equal(pub.profile.slot,4);
  assert.notEqual(cli.DEFAULT_STATE,
    require("../tools/rcm-say-delivery.cjs").DEFAULT_STATE);
  assert.match(cli.DEFAULT_STATE,/rcm-public-delivery\.json$/i);
  assert.throws(()=>pub.validStatePath(path.resolve("rcm-say-delivery.json")),/private_journal/);
  assert.throws(()=>say.validStatePath(path.resolve("rcm-public-delivery.json")),/private_journal/);
  assert.throws(()=>cli.parseOptions(["capture"]),/requires_log/);
  assert.throws(()=>cli.parseOptions(["dispatch"]),/four_explicit/);
});
test("public wire/receipt is validated, Say and wrong public channel never promoted",()=>{
  const result=pub.parseBatch(batch(),observation());
  assert.equal(result.token,TOKEN);
  assert.equal(result.textBytes,Buffer.byteLength(BODY));
  assert.match(result.wireSha256,/^[0-9a-f]{64}$/);
  assert.throws(()=>pub.parseBatch(batch(),observation(BODY,1,5)),/observed_message_mismatch/);
  assert.throws(()=>pub.parseBatch(batch(),observation(BODY+"extra")),/observed_message_mismatch/);
  assert.throws(()=>pub.parseBatch(encodeRecord({kind:"general",sender:"Example",
    channel:"Say",text:BODY},TOKEN,"editor")),/invalid_editor_batch/);
  assert.throws(()=>pub.parseBatch(encodeRecord({...record(),
    channel:"Events"},TOKEN,"editor")),/not_verified_public_wire/);
  assert.equal(pub.isObservedReceipt({...observation(),verifiedLiveFormat:"true"}),false);
});
test("public-state schema rejects Say journal and modified wire digests",()=>{
  const fx=f();
  try{
    seed(fx);
    const state=pub.readState(fx.state);
    state.entries[0].wireSha256="0".repeat(64);
    fs.writeFileSync(fx.state,JSON.stringify(state));
    assert.throws(()=>pub.readState(fx.state),/stored_batch_drift/);
    fs.writeFileSync(fx.state,JSON.stringify(say.fresh()));
    assert.throws(()=>pub.readState(fx.state),/invalid_delivery_journal/);
  }finally{fs.rmSync(fx.dir,{recursive:true,force:true})}
});
test("public follower to coordinator queues ONLY fresh numbered slot 4",async()=>{
  const r=await capture({lines:SAY+OTHER+LINE});
  assert.equal(r.code,0,r.stderr);
  assert.equal(r.events[0].event,"capture_started");
  assert.equal(r.events.filter(e=>e.event==="capture_queued").length,1);
  assert.equal(r.state.entries.length,1);
  assert.equal(r.state.entries[0].batch.kind,"public");
  assert.equal(r.state.entries[0].status,"queued");
  assert.equal(r.state.sessions[0].received,1);
  assert.equal(r.state.sessions[0].state,"completed");
  assert.equal(r.events.at(-1).queued,1);
  assert.ok(!r.out.includes("Example@Greybriar"));
  assert.ok(!r.out.includes(BODY));
});
test("public coordinator ignores other slots and Say and does not fabricate queue entries",async()=>{
  const r=await capture({lines:SAY+OTHER});
  assert.equal(r.code,0,r.stderr);
  assert.equal(r.state.sessions[0].state,"completed");
  assert.equal(r.state.entries.length,0);
  assert.equal(r.events.at(-1).reason,"timeout");
});
test("public queue claim is single-inflight, durable, private in status",()=>{
  const fx=f();
  try{
    seed(fx,2);
    const status=run(["status","--state",fx.state]);
    assert.equal(status.status,0,status.stderr);
    assert.equal(JSON.parse(status.stdout).counts.queued,2);
    assert.ok(!status.stdout.includes("Example@Greybriar"));
    assert.ok(!status.stdout.includes(BODY));
    const first=run(["claim","--state",fx.state]);
    assert.equal(first.status,0,first.stderr);
    assert.equal(JSON.parse(first.stdout).id,TOKEN);
    assert.equal(pub.readState(fx.state).entries[0].status,"claimed");
    const second=run(["claim","--state",fx.state]);
    assert.equal(second.status,2);
    assert.equal(second.stdout,"");
    assert.match(second.stderr,/unresolved/);
    const canceled=run(["cancel","--state",fx.state,"--token",TOKEN,"--ack-discard"]);
    assert.equal(canceled.status,0,canceled.stderr);
    assert.equal(JSON.parse(run(["claim","--state",fx.state]).stdout).id,
      "A1B2C3D4E5F6");
  }finally{fs.rmSync(fx.dir,{recursive:true,force:true})}
});
test("public .NET sender preflight is no-input and cannot claim the batch",()=>{
  if(!fs.existsSync(SENDER))return;
  const fx=f();
  try{
    seed(fx);
    const old=fs.readFileSync(fx.state);
    const r=run(["preflight","--state",fx.state]);
    assert.equal(r.status,0,r.stderr);
    const e=JSON.parse(r.stdout);
    assert.equal(e.event,"editor_sender_preflight");
    assert.equal(e.status,"batch_validated_no_input");
    assert.equal(e.token,TOKEN);
    assert.equal(e.gameInputSent,false);
    assert.deepEqual(fs.readFileSync(fx.state),old);
  }finally{fs.rmSync(fx.dir,{recursive:true,force:true})}
});
test("fake window PID refuses public dispatch and never automatically retries",()=>{
  if(!fs.existsSync(SENDER))return;
  const fx=f();
  try{
    seed(fx);
    const args=["dispatch","--state",fx.state,
      "--expect-host",os.hostname(),"--pid","999999999","--hwnd","0x1",
      "--start-ticks","638000000000000000",
      "--exe-path","C:\\nonexistent\\rift_x64.exe","--exe-sha256","0".repeat(64),
      "--ack-send-in-game","--ack-editor-focused","--ack-submit","--ack-batch"];
    const r=run(args);
    assert.equal(r.status,2,r.stderr);
    const e=JSON.parse(r.stdout);
    assert.equal(e.windowsInputReported,false);
    assert.equal(e.retryAllowed,false);
    assert.equal(pub.readState(fx.state).entries[0].status,"claimed");
    const refused=run(args);
    assert.equal(refused.status,2);
    assert.equal(refused.stdout,"");
  }finally{fs.rmSync(fx.dir,{recursive:true,force:true})}
});
test("public disk verifier requires exact token and independently saved checkpoint",
  {skip:!fs.existsSync(PYTHON)},()=>{
  const fx=f();
  try{
    seed(fx);
    assert.equal(run(["claim","--state",fx.state]).status,0);
    fs.writeFileSync(fx.saved,savedFixture("000000000000"));
    const miss=run(["verify-disk","--state",fx.state,"--file",fx.saved,
      "--python",PYTHON]);
    assert.equal(miss.status,2,miss.stderr);
    assert.equal(pub.readState(fx.state).entries[0].status,"claimed");
    fs.writeFileSync(fx.saved,savedFixture(TOKEN));
    const yes=run(["verify-disk","--state",fx.state,"--file",fx.saved,
      "--python",PYTHON,"--token",TOKEN]);
    assert.equal(yes.status,0,yes.stderr);
    assert.equal(JSON.parse(yes.stdout).diskReceiptVerified,true);
    assert.equal(pub.readState(fx.state).entries[0].status,"disk_saved");
  }finally{fs.rmSync(fx.dir,{recursive:true,force:true})}
});
test("abandoned public capture never auto resumes stale history",()=>{
  const fx=f();
  try{
    const s=pub.fresh();pub.beginSession(s);pub.writeState(fx.state,s);
    assert.equal(run(["claim","--state",fx.state]).status,2);
    assert.equal(run(["recover","--state",fx.state,
      "--ack-abandoned-capture"]).status,0);
    assert.equal(pub.readState(fx.state).sessions[0].state,"failed");
    assert.equal(pub.summary(pub.readState(fx.state)).counts.queued,0);
  }finally{fs.rmSync(fx.dir,{recursive:true,force:true})}
});
test("shared editor lock blocks public claim and dispatch while Say is in flight",()=>{
  const fx=f();
  try{
    seed(fx);
    const state=say.fresh(),id=say.beginSession(state);
    const sayBody="RCM_SAY_PENDING_OTHER_PROFILE";
    say.acceptPair(state,id,{
      event:"say_observed",format:"rift-live-2026-say",source:"RIFT_Log.txt",
      kind:"general",channel:"Say",textBytes:Buffer.byteLength(sayBody),
      gameTimestamp:"23:37:24",senderRedacted:true,textRedacted:true,
      verifiedLiveFormat:true,physicalRiftOriginVerified:false,sequence:1
    },encodeRecord({kind:"general",sender:"Example",channel:"Say",
      text:sayBody},"123456ABCDEF","editor"));
    say.completeSession(state,id,true,"message_limit_reached");
    say.claimNext(state);
    say.writeState(fx.sayState,state);
    const blocked=run(["claim","--state",fx.state]);
    assert.equal(blocked.status,2,blocked.stderr);
    assert.equal(blocked.stdout,"");
    assert.match(blocked.stderr,/other_profile_delivery_unresolved/);
    const fake=run(["dispatch","--state",fx.state,
      "--expect-host",os.hostname(),"--pid","999999999","--hwnd","0x1",
      "--start-ticks","638000000000000000",
      "--exe-path","C:\\nonexistent\\rift_x64.exe","--exe-sha256","0".repeat(64),
      "--ack-send-in-game","--ack-editor-focused","--ack-submit","--ack-batch"]);
    assert.equal(fake.status,2);
    assert.equal(fake.stdout,"");
    assert.match(fake.stderr,/other_profile_delivery_unresolved/);
    assert.equal(pub.readState(fx.state).entries[0].status,"queued");
    assert.equal(fs.existsSync(path.join(fx.dir,"rcm-global-editor-claim.lock")),false);
    say.cancelClaim(state,"123456ABCDEF");
    say.writeState(fx.sayState,state);
    assert.equal(run(["claim","--state",fx.state]).status,0);
  }finally{fs.rmSync(fx.dir,{recursive:true,force:true})}
});
test("claimed public delivery blocks Say claim until resolved",()=>{
  const fx=f();
  try{
    const state=seed(fx);
    pub.claimNext(state);pub.writeState(fx.state,state);
    const other=say.fresh(),id=say.beginSession(other);
    const body="OTHER_SAY_QUEUE";
    say.acceptPair(other,id,{
      event:"say_observed",format:"rift-live-2026-say",source:"RIFT_Log.txt",
      kind:"general",channel:"Say",textBytes:Buffer.byteLength(body),
      gameTimestamp:"23:37:24",senderRedacted:true,textRedacted:true,
      verifiedLiveFormat:true,physicalRiftOriginVerified:false,sequence:1
    },encodeRecord({kind:"general",sender:"Example",channel:"Say",
      text:body},"123456ABCDEF","editor"));
    say.completeSession(other,id,true,"message_limit_reached");
    say.writeState(fx.sayState,other);
    const blocked=spawnSync(process.execPath,[path.resolve(__dirname,
      "../tools/rcm-say-delivery.cjs"),"claim","--state",fx.sayState],
      {encoding:"utf8",timeout:8000});
    assert.equal(blocked.status,2);
    assert.match(blocked.stderr,/other_profile_delivery_unresolved/);
    assert.equal(say.readState(fx.sayState).entries[0].status,"queued");
  }finally{fs.rmSync(fx.dir,{recursive:true,force:true})}
});
test("global editor lock held by another process refuses without changing queued state",()=>{
  const fx=f();
  try{
    seed(fx);
    const lock=path.join(fx.dir,"rcm-global-editor-claim.lock");
    fs.writeFileSync(lock,"existing owner");
    const before=fs.readFileSync(fx.state);
    const blocked=run(["claim","--state",fx.state]);
    assert.equal(blocked.status,2);
    assert.match(blocked.stderr,/global_editor_claim_lock_held/);
    assert.equal(blocked.stdout,"");
    assert.deepEqual(fs.readFileSync(fx.state),before);
    assert.equal(fs.readFileSync(lock,"utf8"),"existing owner");
  }finally{fs.rmSync(fx.dir,{recursive:true,force:true})}
});
test("cross-profile transfer-token collision is blocked even after other queue settled",()=>{
  const fx=f();
  try{
    seed(fx);
    const other=say.fresh(),id=say.beginSession(other);
    const body="ANOTHER_SOURCE";
    say.acceptPair(other,id,{
      event:"say_observed",format:"rift-live-2026-say",source:"RIFT_Log.txt",
      kind:"general",channel:"Say",textBytes:Buffer.byteLength(body),
      gameTimestamp:"23:37:24",senderRedacted:true,textRedacted:true,
      verifiedLiveFormat:true,physicalRiftOriginVerified:false,sequence:1
    },encodeRecord({kind:"general",sender:"Example",channel:"Say",
      text:body},TOKEN,"editor"));
    say.completeSession(other,id,true,"message_limit_reached");
    say.writeState(fx.sayState,other);
    const blocked=run(["claim","--state",fx.state]);
    assert.equal(blocked.status,2);
    assert.match(blocked.stderr,/cross_profile_transfer_token_collision/);
    assert.equal(pub.readState(fx.state).entries[0].status,"queued");
  }finally{fs.rmSync(fx.dir,{recursive:true,force:true})}
});
