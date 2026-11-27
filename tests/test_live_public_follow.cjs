"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const os=require("node:os");
const path=require("node:path");
const {spawn,spawnSync}=require("node:child_process");
const publicFollow=require("../tools/rcm-live-public-follow.cjs");
const sayFollow=require("../tools/rcm-live-say-follow.cjs");
const SCRIPT=path.resolve(__dirname,"../tools/rcm-live-public-follow.cjs");
const PUBLIC="23:37:21: [4. Level 1-29][Example@Greybriar]: PUBLIC_RCM_FIXTURE_20261121\n";
const OTHER="23:37:22: [5. Events][Example@Greybriar]: should be excluded\n";
const SAY="23:37:23: [Example@Greybriar] says: should be excluded\n";
function fixture(){
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),"rcm-public-follow-"));
  const file=path.join(dir,"Log.txt");
  fs.writeFileSync(file,"Noncombat logging enabled\n"+PUBLIC);
  return {dir,file};
}
async function session({changes,onRecord,maxMessages=1,pollMs=25,timeoutMs=1400,prepare=false}={}){
  const {dir,file}=fixture();
  const args=[SCRIPT,"--path",file,"--poll-ms",String(pollMs),
    "--timeout-ms",String(timeoutMs),"--max-messages",String(maxMessages)];
  if(prepare)args.push("--prepare-import");
  const child=spawn(process.execPath,args,{stdio:["ignore","pipe","pipe"],windowsHide:true});
  const events=[];let stderr="",pending="",timeout;
  const result=new Promise((resolve,reject)=>{
    timeout=setTimeout(()=>child.kill(),4000);
    child.stdout.on("data",chunk=>{
      pending+=chunk.toString("utf8");
      let end;
      while((end=pending.indexOf("\n"))!==-1){
        const line=pending.slice(0,end);pending=pending.slice(end+1);
        if(!line)continue;
        let event;
        try{event=JSON.parse(line);}catch(e){reject(e);child.kill();return;}
        events.push(event);
        if(event.event==="started"&&changes)changes(file);
        if(onRecord)onRecord(event,file);
      }
    });
    child.stderr.on("data",chunk=>{stderr+=chunk.toString("utf8");});
    child.once("error",reject);
    child.once("close",code=>resolve({code,events,stderr}));
  });
  try{return await result;}finally{
    clearTimeout(timeout);child.kill();
    fs.rmSync(dir,{recursive:true,force:true});
  }
}
test("public follower requires explicit profile; Say remains isolated",()=>{
  const {parseCandidateLine}=require("../tools/rcm-chat-observer.cjs");
  const publicEvent=parseCandidateLine(PUBLIC.trim());
  const sayEvent=parseCandidateLine(SAY.trim());
  const otherEvent=parseCandidateLine(OTHER.trim());
  assert.equal(publicFollow.isObservedPublic(publicEvent),true);
  assert.equal(publicFollow.isObservedPublic(sayEvent),false);
  assert.equal(publicFollow.isObservedPublic(otherEvent),false);
  assert.equal(sayFollow.isObservedSay(publicEvent),false);
  assert.equal(publicFollow.parseArgs(["--help"]).help,true);
  assert.throws(()=>publicFollow.parseArgs(["--path","relative/Log.txt"]),/absolute/);
});
test("observes ONLY fresh slot 4 public; old log, Say, other slots ignored",async()=>{
  const r=await session({changes:f=>fs.appendFileSync(f,SAY+OTHER+PUBLIC)});
  assert.equal(r.code,0,r.stderr);
  assert.equal(r.events[0].event,"started");
  assert.equal(r.events[0].channelSlot,4);
  assert.equal(r.events[0].channel,"Level 1-29");
  assert.equal(r.events[0].oldHistoryReplayed,false);
  const messages=r.events.filter(e=>e.event==="public_observed");
  assert.equal(messages.length,1);
  assert.equal(messages[0].kind,"public");
  assert.equal(messages[0].format,"rift-live-2026-numbered-public");
  assert.equal(messages[0].physicalRiftOriginVerified,false);
  assert.equal(messages[0].textBytes,27);
  assert.equal(r.events.at(-1).reason,"message_limit_reached");
  assert.ok(!JSON.stringify(r.events).includes("Example@Greybriar"));
  assert.ok(!JSON.stringify(r.events).includes("PUBLIC_RCM_FIXTURE_20261121"));
});
test("explicit preparation produces canonical public editor command, no game input",async()=>{
  const r=await session({changes:f=>fs.appendFileSync(f,PUBLIC),prepare:true});
  assert.equal(r.code,0,r.stderr);
  const b=r.events.filter(e=>e.event==="rcm_manual_import");
  assert.equal(b.length,1);
  assert.equal(b[0].kind,"public");
  assert.equal(b[0].inputMode,"editor");
  assert.equal(b[0].automaticGameInput,false);
  const wire=Buffer.from(b[0].commands[0].split(" ").at(-1),"base64url").toString("utf8");
  assert.equal(wire,"C\0Example@Greybriar\0Level 1-29\0PUBLIC_RCM_FIXTURE_20261121");
});
test("long public records never persist silent truncation",async()=>{
  const r=await session({prepare:true,changes:f=>{
    fs.appendFileSync(f,
      "23:37:21: [4. Level 1-29][Example@Greybriar]: "+("🍀".repeat(140))+"\n"+PUBLIC);
  }});
  assert.equal(r.code,0,r.stderr);
  assert.equal(r.events.filter(e=>e.event==="public_skipped").length,1);
  assert.equal(r.events.filter(e=>e.event==="rcm_manual_import").length,1);
  assert.equal(r.events.at(-1).skipped,1);
});
test("source rewrite aborts before emitting a public import",async()=>{
  const r=await session({prepare:true,changes:f=>{
    fs.writeFileSync(f,"23:37:22: [4. Level 1-29][Example]: fake\n");
  }});
  assert.equal(r.code,2,r.stderr);
  assert.equal(r.events.filter(e=>e.event==="rcm_manual_import").length,0);
});
test("other live public slot alone is not admitted to current profile",async()=>{
  const r=await session({changes:f=>fs.appendFileSync(f,OTHER)});
  assert.equal(r.code,0,r.stderr);
  assert.equal(r.events.filter(e=>e.event==="public_observed").length,0);
  assert.equal(r.events.at(-1).reason,"timeout");
});

test("startup read failures preserve bounded codes without private error text",()=>{
  const {dir,file}=fixture();
  const preload=path.join(dir,"read-failure.cjs");
  const secret="PRIVATE_ACCOUNT_AND_CHAT_FIXTURE";
  try{
    for(const profile of ["public","say"]){
      for(const code of ["UNKNOWN","EACCES",secret]){
        fs.writeFileSync(preload,
          'const fs=require("node:fs");const original=fs.openSync;'+
          'fs.openSync=function(file,...args){if(file==='+JSON.stringify(file)+')'+
          '{const error=Error('+JSON.stringify(secret+" "+dir)+');'+
          'error.code='+JSON.stringify(code)+';throw error;}'+
          'return original.call(this,file,...args);};');
        const script=path.resolve(__dirname,"../tools/rcm-live-"+profile+"-follow.cjs");
        const result=spawnSync(process.execPath,["--require",preload,script,"--path",file],
          {encoding:"utf8",timeout:5000,windowsHide:true,maxBuffer:16384});
        assert.equal(result.status,2,result.stderr);
        const events=result.stdout.trim().split("\n").filter(Boolean).map(JSON.parse);
        assert.equal(events.length,1);
        assert.equal(events[0].event,"refused");
        assert.equal(events[0].reason,"log_baseline_read_error");
        assert.equal(events[0].readErrorCode,code===secret?"UNAVAILABLE":code);
        assert.equal(events[0].mode,profile==="public"?
          "bounded_verified_public_follow":"bounded_verified_say_follow");
        assert.equal(events[0].gameInputSent,false);
        assert.equal(events[0].editorDeliveryVerified,false);
        assert.equal(events[0].diskSavedVerified,false);
        assert.ok(!(result.stdout+result.stderr).includes(secret));
        assert.ok(!(result.stdout+result.stderr).includes(dir));
      }
    }
  }finally{fs.rmSync(dir,{recursive:true,force:true});}
});

test("missing log refuses startup without exposing the absolute path",()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),"rcm-missing-private-path-"));
  try{
    const result=spawnSync(process.execPath,[SCRIPT,"--path",path.join(dir,"Log.txt")],
      {encoding:"utf8",timeout:5000,windowsHide:true,maxBuffer:16384});
    assert.equal(result.status,2);
    const receipt=JSON.parse(result.stdout);
    assert.equal(receipt.event,"refused");
    assert.equal(receipt.reason,"log_source_unavailable");
    assert.equal(receipt.readErrorCode,"ENOENT");
    assert.ok(!(result.stdout+result.stderr).includes(dir));
  }finally{fs.rmSync(dir,{recursive:true,force:true});}
});

test("baseline anchor failure closes the already opened tailer",()=>{
  const {dir,file}=fixture();
  const originalOpen=fs.openSync,originalClose=fs.closeSync;
  const live=new Set();let opens=0;
  try{
    fs.openSync=function(name,...args){
      if(name===file && ++opens===2){
        const error=Error("private anchor failure");error.code="EIO";throw error;
      }
      const fd=originalOpen.call(this,name,...args);
      if(name===file)live.add(fd);
      return fd;
    };
    fs.closeSync=function(fd){live.delete(fd);return originalClose.call(this,fd);};
    assert.throws(()=>publicFollow.follow({filePath:file,timeoutMs:1000,pollMs:25,
      maxMessages:1},()=>{}),error=>
        error.message==="log_baseline_read_error" && error.readErrorCode==="EIO");
    assert.equal(live.size,0);
  }finally{
    fs.openSync=originalOpen;fs.closeSync=originalClose;
    for(const fd of live)originalClose(fd);
    fs.rmSync(dir,{recursive:true,force:true});
  }
});
