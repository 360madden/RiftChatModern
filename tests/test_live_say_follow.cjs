"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const os=require("node:os");
const path=require("node:path");
const {spawn}=require("node:child_process");
const follow=require("../tools/rcm-live-say-follow.cjs");
const SCRIPT=path.resolve(__dirname,"../tools/rcm-live-say-follow.cjs");
const SAY="17:17:23: [ExampleCharacter] says: RCM_FOLLOW_SAMPLE_20261121\n";
function fixture() {
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),"rcm-follow-"));
  const file=path.join(dir,"Log.txt");
  fs.writeFileSync(file,"Noncombat logging enabled\n"+SAY); // stale baseline
  return {dir,file};
}
async function session({changes,onStarted,onRecord,maxMessages=1,pollMs=25,extraArgs=[]}={}) {
  const {dir,file}=fixture();
  const args=[SCRIPT,"--path",file,"--poll-ms",String(pollMs),"--timeout-ms","1800",
    "--max-messages",String(maxMessages),...extraArgs];
  const child=spawn(process.execPath,args,{windowsHide:true,stdio:["ignore","pipe","pipe"]});
  let buf="",stderr="",records=[],started=false,done=false;
  let timeout;
  const result=new Promise((resolve,reject)=>{
    timeout=setTimeout(()=>child.kill(),3500);
    child.stdout.on("data",chunk=>{
      buf+=chunk.toString("utf8");
      let end;
      while((end=buf.indexOf("\n"))!==-1){
        const line=buf.slice(0,end);buf=buf.slice(end+1);
        if(!line)continue;
        let r;
        try{r=JSON.parse(line);}catch(e){reject(e);child.kill();return;}
        records.push(r);
        if(onRecord)onRecord(r,file);
        if(r.event==="started" && !started){
          started=true;
          if(onStarted)onStarted(file);
          else if(changes)changes(file);
        }
      }
    });
    child.stderr.on("data",x=>{stderr+=x.toString("utf8");});
    child.once("error",reject);
    child.once("close",code=>{
      done=true;
      resolve({code,records,started,stderr,stdoutRemainder:buf});
    });
  });
  try{return await result;}finally{
    clearTimeout(timeout);
    if(!done)child.kill();
    fs.rmSync(dir,{recursive:true,force:true});
  }
}
test("strict bounded flags, path and privacy opt-in",()=>{
  assert.throws(()=>follow.parseArgs([]),/Supply --path/);
  assert.throws(()=>follow.parseArgs(["--path","relative/Log.txt"]),/absolute/);
  assert.throws(()=>follow.parseArgs(["--path","C:\\x\\Chat.txt"]),/Log.txt/);
  assert.throws(()=>follow.parseArgs(["--path","C:\\x\\Log.txt",
    "--poll-ms","0"]),/range/);
  assert.throws(()=>follow.parseArgs(["--path","C:\\x\\Log.txt",
    "--max-messages","101"]),/range/);
  assert.throws(()=>follow.parseArgs(["--path","C:\\x\\Log.txt",
    "--prepare-import","--prepare-import"]),/Duplicate/);
  assert.equal(follow.parseArgs(["--help"]).help,true);
  assert.equal(follow.isObservedSay({event:"candidate_chat",
    format:"historical-bracket",verifiedLiveFormat:false,kind:"guild",
    channel:"Guild",source:"RIFT_Log.txt"}),false);
});
test("real numbered public format never enters the verified Say-only follower",()=>{
  const {parseCandidateLine}=require("../tools/rcm-chat-observer.cjs");
  const event=parseCandidateLine(
    "23:37:21: [4. Level 1-29][Example@Greybriar]: harmless fixture");
  assert.equal(event.verifiedLiveFormat,true);
  assert.equal(event.kind,"public");
  assert.equal(follow.isObservedSay(event),false);
});
test("new complete Say is emitted, stale baseline ignored and body redacted",async()=>{
  const r=await session({changes:file=>fs.appendFileSync(file,SAY)});
  assert.equal(r.code,0,r.stderr);
  assert.ok(r.started);
  assert.equal(r.records[0].oldHistoryReplayed,false);
  assert.equal(r.records.filter(x=>x.event==="say_observed").length,1);
  assert.equal(r.records.filter(x=>x.event==="rcm_manual_import").length,0);
  assert.equal(r.records.at(-1).reason,"message_limit_reached");
  assert.equal(r.records[1].textBytes,26);
  assert.equal(r.records[1].physicalRiftOriginVerified,false);
  assert.ok(!JSON.stringify(r.records).includes("ExampleCharacter"));
  assert.ok(!JSON.stringify(r.records).includes("RCM_FOLLOW_SAMPLE_20261121"));
});
test("explicit preparation returns a single editor-only batch with exact source",async()=>{
  const r=await session({changes:file=>fs.appendFileSync(file,SAY),
    extraArgs:["--prepare-import"]});
  assert.equal(r.code,0,r.stderr);
  const prepared=r.records.filter(x=>x.event==="rcm_manual_import");
  assert.equal(prepared.length,1);
  assert.equal(prepared[0].inputMode,"editor");
  assert.equal(prepared[0].automaticGameInput,false);
  assert.equal(prepared[0].liveGameDeliveryVerified,false);
  const wire=Buffer.from(prepared[0].commands[0].split(" ").at(-1),"base64url").toString("utf8");
  assert.equal(wire,"S\0ExampleCharacter\0Say\0RCM_FOLLOW_SAMPLE_20261121");
  assert.equal(r.records.at(-1).diskSavedVerified,false);
});
test("unverified historical Guild is never promoted into live Say",async()=>{
  const r=await session({
    changes:file=>fs.appendFileSync(file,"[Guild][ExampleCharacter]: imagined\n")
  });
  assert.equal(r.code,0,r.stderr);
  assert.equal(r.records.filter(x=>x.event==="say_observed").length,0);
  assert.equal(r.records.at(-1).reason,"timeout");
});
test("does not silently persist truncated Say; later complete Say passes",async()=>{
  const r=await session({changes:file=>{
    fs.appendFileSync(file,"17:17:23: [ExampleCharacter] says: "+"🚀".repeat(140)+"\n");
    fs.appendFileSync(file,SAY);
  },extraArgs:["--prepare-import"]});
  assert.equal(r.code,0,r.stderr);
  assert.equal(r.records.filter(x=>x.event==="say_skipped").length,1);
  assert.equal(r.records.filter(x=>x.event==="rcm_manual_import").length,1);
  assert.equal(r.records.at(-1).skipped,1);
});
test("truncated/overwritten original log aborts without publishing pending import",async()=>{
  const r=await session({changes:file=>{
    fs.writeFileSync(file,"17:17:23: [Bad] says: bogus\n");
  },extraArgs:["--prepare-import"]});
  assert.equal(r.code,2,r.stderr);
  assert.ok(["log_identity_changed","log_reset_or_corrupt_line"].includes(r.records.at(-1).reason));
  assert.equal(r.records.filter(x=>x.event==="rcm_manual_import").length,0);
});
test("same-size in-place rewrite of baseline fails anchor check",async()=>{
  const r=await session({changes:file=>{
    const old=fs.readFileSync(file,"utf8");
    const edited=old.replace("Noncombat logging enabled","Noncombat logging stopped");
    assert.equal(edited.length,old.length);
    fs.writeFileSync(file,edited+SAY);
  },extraArgs:["--prepare-import"]});
  assert.equal(r.code,2,r.stderr);
  assert.equal(r.records.at(-1).reason,"log_identity_changed");
  assert.equal(r.records.filter(x=>x.event==="rcm_manual_import").length,0);
});
test("rolling checkpoint detects in-place rewrite after first new Say",async()=>{
  let scheduled=false;
  const r=await session({maxMessages:2,pollMs:100,
    extraArgs:["--prepare-import"],
    changes:file=>fs.appendFileSync(file,SAY),
    onRecord:(event,file)=>{
      if(event.event!=="say_observed"||scheduled)return;
      scheduled=true;
      setTimeout(()=>{
        const old=fs.readFileSync(file,"utf8");
        const at=old.lastIndexOf(SAY);
        assert.ok(at>=0);
        const rewritten=SAY.replace("SAMPLE","SAMPLF");
        assert.equal(rewritten.length,SAY.length);
        fs.writeFileSync(file,old.slice(0,at)+rewritten+old.slice(at+SAY.length)+SAY);
      },10);
    }});
  assert.equal(r.code,2,r.stderr);
  assert.equal(r.records.at(-1).reason,"log_identity_changed");
  assert.equal(r.records.filter(x=>x.event==="say_observed").length,1);
  assert.equal(r.records.filter(x=>x.event==="rcm_manual_import").length,1);
});
