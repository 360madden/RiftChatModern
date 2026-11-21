"use strict";
const assert=require("node:assert/strict");
const {test}=require("node:test");
const {spawn,spawnSync}=require("node:child_process");
const path=require("node:path");
const gate=require("../tools/rcm-chat-batch-gate.cjs");
const {encodeRecord}=require("../tools/rcm-chat-import.cjs");

const SCRIPT=path.resolve(__dirname,"../tools/rcm-chat-batch-gate.cjs");
function fixture(text="EXACT_TEST_MARK_20261121"){
  const payload=encodeRecord({
    kind:"guild",sender:"HostProbe",channel:"Guild",text
  },"CAFEBABE1234","editor");
  return [
    {event:"started",requireChatAfterMarker:true,
      expectedChatTextRequired:true,prepareImport:true,inputMode:"editor",
      transportVerified:false,automaticGameInput:false},
    {event:"matched",nonce:"GATE_NONCE_20261121"},
    {event:"chat_phase_armed",mode:"fresh_tail_after_marker"},
    {event:"candidate_chat",source:"RIFT_Log.txt",
      chatTextMatched:true,afterMarker:true,truncated:false,
      verifiedLiveFormat:false},
    payload,
    {event:"finished",reason:"exact_chat_candidate_after_marker",
      expectedChatTextRequired:true,chatTextMatched:true,
      probeMatched:true,chatCandidatesAfterMarker:1,
      transportVerified:false,physicalRiftOriginVerified:false}
  ];
}
function run(items,options={}){
  const input=options.text??items.map(x=>JSON.stringify(x)).join("\n")+"\n";
  return spawnSync(process.execPath,[SCRIPT,...(options.args||[])],{
    encoding:"utf8",input,timeout:3000,maxBuffer:1024*1024
  });
}
function refused(items){
  const r=run(items);
  assert.equal(r.status,2,r.stderr);
  assert.equal(r.stdout,"");
  return r;
}

test("exact after-marker candidate selects only the actual Node editor batch",()=>{
  const items=fixture();
  const expected=items[4];
  assert.deepEqual(gate.extract(items),expected);
  const r=run(items);
  assert.equal(r.status,0,r.stderr);
  assert.deepEqual(JSON.parse(r.stdout),expected);
  assert.equal(JSON.parse(r.stdout).automaticGameInput,false);
});
test("physically observed Say shape is eligible but never claims whole-game proof",()=>{
  const items=fixture("RCM_CHAT_TEST_20261121");
  items[3]={event:"candidate_chat",source:"RIFT_Log.txt",
    format:"rift-live-2026-say",kind:"general",channel:"Say",
    verifiedLiveFormat:true,chatTextMatched:true,afterMarker:true,truncated:false};
  items[4]=encodeRecord({kind:"general",sender:"ExampleCharacter",
    channel:"Say",text:"RCM_CHAT_TEST_20261121"},"A1B2C3D4E5F6","editor");
  const result=run(items);
  assert.equal(result.status,0,result.stderr);
  const payload=JSON.parse(result.stdout);
  assert.equal(payload.kind,"general");
  assert.equal(payload.liveGameDeliveryVerified,false);
  assert.equal(payload.automaticGameInput,false);
  for(const wrong of [
    {format:"invented-format"},
    {kind:"guild"},
    {channel:"Guild"},
    {verifiedLiveFormat:true,format:"historical-bracket"},
    {verifiedLiveFormat:"true"}
  ]){
    const invalid=fixture("RCM_CHAT_TEST_20261121");
    invalid[3]={...items[3],...wrong};
    invalid[4]=items[4];
    refused(invalid);
  }
});
test("valid source may appear only after configured log is created",()=>{
  const items=fixture();
  items.splice(1,0,{event:"log_path_selected",path:"C:\\RIFT\\Log.txt"});
  assert.equal(run(items).status,0);
  items.splice(5,0,{event:"log_path_selected",path:"C:\\RIFT\\Log.txt"});
  refused(items);
});
test("unrelated candidate and raw sample never substitute for exact text",()=>{
  const items=fixture();
  const extra=encodeRecord({
    kind:"guild",sender:"Someone",channel:"Guild",text:"unrelated"
  },"101010101010","editor");
  items.splice(3,0,
    {event:"raw_log_sample",decodedLine:"private raw diagnostic"},
    {event:"candidate_chat",source:"RIFT_Log.txt",
      chatTextMatched:false,afterMarker:true,truncated:false},
    extra);
  const r=run(items);
  assert.equal(r.status,0,r.stderr);
  assert.deepEqual(JSON.parse(r.stdout),items[7]);
  assert.ok(!r.stdout.includes("private raw diagnostic"));
  assert.ok(!r.stdout.includes("unrelated"));
});
test("missing marker, missing arming or wrong observer mode cannot pass",()=>{
  const wrongStart=fixture();wrongStart[0].requireChatAfterMarker=false;
  refused(wrongStart);
  const wrongMode=fixture();wrongMode[0].inputMode="native";
  refused(wrongMode);
  const noMarker=fixture();noMarker.splice(1,1);
  refused(noMarker);
  const noArm=fixture();noArm.splice(2,1);
  refused(noArm);
});
test("no exact candidate, missing batch or a skipped match is refused",()=>{
  const noExact=fixture();noExact[3].chatTextMatched=false;
  refused(noExact);
  const noBatch=fixture();noBatch.splice(4,1);
  refused(noBatch);
  const skipped=fixture();skipped.splice(4,1,
    {event:"import_skipped",reason:"truncated_chat_body"});
  refused(skipped);
});
test("duplicate exact candidate and source reset are refused",()=>{
  const double=fixture();
  double.splice(5,0,{event:"candidate_chat",source:"RIFT_Log.txt",
    chatTextMatched:true,afterMarker:true,truncated:false});
  refused(double);
  for(const event of ["file_reset","file_disappeared","read_error",
                       "chat_phase_rearmed"]){
    const values=fixture();
    values.splice(3,0,{event});
    refused(values);
  }
});
test("unsupported batch metadata and failed final receipt are refused",()=>{
  for (const key of ["protocol","inputMode","liveGameDeliveryVerified"]){
    const values=fixture();
    values[4][key]=key==="liveGameDeliveryVerified"?true:"unexpected";
    refused(values);
  }
  for(const key of ["chatTextMatched","probeMatched","physicalRiftOriginVerified"]){
    const values=fixture();
    values[5][key]=key==="physicalRiftOriginVerified"?true:false;
    refused(values);
  }
  const timeout=fixture();timeout[5].reason="timeout_waiting_exact_chat_after_marker";
  refused(timeout);
});
test("malformed JSON, extraneous records and excessive data fail closed",()=>{
  const good=fixture();
  refused([...good,{event:"finished"}]);
  const duplicateStarted=fixture();duplicateStarted.splice(1,0,good[0]);
  refused(duplicateStarted);
  for (const text of ["bad json\n",JSON.stringify(good[0])+"\n\n",
                      "z".repeat(600000),JSON.stringify(good[0])+"\n"+("x".repeat(20000))]){
    const r=run(good,{text});
    assert.equal(r.status,2,r.stderr);
    assert.equal(r.stdout,"");
  }
});
test("--status streams readiness BEFORE the observer finishes, without chat contents",async()=>{
  const events=fixture("EXACT_PRIVATE_TEST_TEXT_20261121");
  events[0].nonce="GATE_NONCE_20261121";
  events[0].persistedLogConsole=false;
  const child=spawn(process.execPath,[SCRIPT,"--status"],{stdio:["pipe","pipe","pipe"]});
  let stderr="",stdout="";
  child.stderr.on("data",part=>{stderr+=part.toString("utf8")});
  child.stdout.on("data",part=>{stdout+=part.toString("utf8")});
  const liveStarted=new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>reject(Error("Status not streamed during active watcher")),1800);
    const check=()=>{
      if(stderr.includes("RCM watcher started")){
        clearTimeout(timer);child.stderr.off("data",check);resolve();
      }
    };
    child.stderr.on("data",check);
    check();
  });
  child.stdin.write(JSON.stringify(events[0])+"\n");
  await liveStarted.catch(e=>{child.kill();throw e;});
  assert.equal(stdout,"");
  assert.ok(stderr.includes("GATE_NONCE_20261121"));
  child.stdin.end(events.slice(1).map(x=>JSON.stringify(x)).join("\n")+"\n");
  const code=await new Promise(resolve=>child.once("close",resolve));
  assert.equal(code,0,stderr);
  assert.equal(JSON.parse(stdout).id,events[4].id);
  assert.ok(stderr.includes("chat phase armed"));
  assert.ok(stderr.includes("LogConsole=False"));
  assert.ok(!stderr.includes("EXACT_PRIVATE_TEST_TEXT_20261121"));
});
test("unexpected CLI flags cannot bypass a gated batch",()=>{
  const result=run(fixture(),{args:["--send"]});
  assert.equal(result.status,2);
  assert.equal(result.stdout,"");
});
test("candidate source proof does not become claimed physical RIFT verification",()=>{
  const values=fixture();
  assert.equal(values[4].liveGameDeliveryVerified,false);
  assert.equal(values[5].physicalRiftOriginVerified,false);
  const output=gate.extract(values);
  assert.equal(output.requiresManualEntry,true);
  assert.equal(output.inputMode,"editor");
  assert.equal(output.automaticGameInput,false);
});
