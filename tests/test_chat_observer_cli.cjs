"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const os=require("node:os");
const path=require("node:path");
const {spawn}=require("node:child_process");

const observer=path.resolve(__dirname,"..","tools","rcm-chat-observer.cjs");

function launchFixture(lines,includeText,prepareImport=false,rawSampleLines=0){
  return new Promise((resolve,reject)=>{
    const dir=fs.mkdtempSync(path.join(os.tmpdir(),"rcm-observer-cli-"));
    const file=path.join(dir,"Log.txt");
    // An existing stale chat line must not replay after the observer starts.
    fs.writeFileSync(file,"[Guild][OldPlayer]: stale should be ignored\n");
    const args=[observer,"--path",file,"--nonce","RCM_CLI_20261120",
      "--timeout-ms","2500","--poll-ms","25","--max-candidates","10"];
    if(includeText)args.push("--include-text");
    if(prepareImport)args.push("--prepare-import");
    if(rawSampleLines)args.push("--sample-raw-lines",String(rawSampleLines));
    const proc=spawn(process.execPath,args,{windowsHide:true,stdio:["ignore","pipe","pipe"]});
    let stdout="",stderr="",records=[],started=false,closed=false;
    const cleanup=()=>fs.rmSync(dir,{recursive:true,force:true});
    const abort=setTimeout(()=>{if(!closed)proc.kill();},4500);
    proc.stdout.on("data",data=>{
      stdout+=data.toString();
      let index;
      while((index=stdout.indexOf("\n"))>=0){
        const json=stdout.slice(0,index);
        stdout=stdout.slice(index+1);
        if(!json)continue;
        let item;
        try{item=JSON.parse(json)}catch(e){reject(e);return}
        records.push(item);
        if(item.event==="started"&&!started){
          started=true;
          fs.appendFileSync(file,lines);
        }
      }
    });
    proc.stderr.on("data",data=>{stderr+=data.toString()});
    proc.on("error",error=>{clearTimeout(abort);cleanup();reject(error)});
    proc.on("close",code=>{
      closed=true;clearTimeout(abort);cleanup();
      if(stderr)reject(new Error(stderr));
      else resolve({code,records,started});
    });
  });
}

test("CLI tails only new candidate chat and returns a marker receipt",async()=>{
  const r=await launchFixture(
    "[Guild][NewPlayer]: secret sample\n"+
    "RIFT damage event 134\n"+
    "LPB_PROBE|RCM_CLI_20261120|1795180000.000\n",false);
  assert.equal(r.code,0);
  assert.equal(r.started,true);
  assert.equal(r.records[0].event,"started");
  const chat=r.records.filter(x=>x.event==="candidate_chat");
  assert.equal(chat.length,1);
  assert.equal(chat[0].sender,"NewPlayer");
  assert.equal(chat[0].kind,"guild");
  assert.equal("text" in chat[0],false);
  assert.equal(r.records.filter(x=>x.event==="raw_log_sample").length,0);
  assert.equal(chat.some(x=>x.sender==="OldPlayer"),false);
  assert.ok(r.records.some(x=>x.event==="matched"));
  assert.ok(r.records.some(x=>x.event==="finished"&&x.reason==="marker_matched"));
  assert.ok(r.records.every(x=>x.transportVerified===undefined||x.transportVerified===false));
});

test("CLI emits human-pasteable /rcm import commands only when explicitly enabled",async()=>{
  const r=await launchFixture(
    "[Guild][Atank]: Hello from fixture\n"+
    "LPB_PROBE|RCM_CLI_20261120|unknown\n",false,true);
  assert.equal(r.code,0);
  const ingestions=r.records.filter(x=>x.event==="rcm_manual_import");
  assert.equal(ingestions.length,1);
  assert.equal(ingestions[0].parts,1);
  assert.equal(ingestions[0].automaticGameInput,false);
  assert.equal(ingestions[0].liveGameDeliveryVerified,false);
  assert.match(ingestions[0].commands[0],/^\/rcm import [A-F0-9]{12} 1\/1 /);
  const payload=Buffer.from(ingestions[0].commands[0].split(" ").at(-1),"base64url")
    .toString("utf8");
  assert.equal(payload,"G\0Atank\0Guild\0Hello from fixture");
  assert.equal(r.records[0].prepareImport,true);
  assert.ok(r.records.some(x=>x.event==="matched"));
});
test("opt-in raw-line discovery sees previously unknown formats but never stale lines",async()=>{
  const r=await launchFixture(
    "unknown line format from 2026\n" +
    "a second log line 🌋\n",
    false,false,2);
  assert.equal(r.code,0);
  assert.equal(r.started,true);
  const samples=r.records.filter(x=>x.event==="raw_log_sample");
  assert.equal(samples.length,2);
  assert.equal(samples[0].decodedLine,"unknown line format from 2026");
  assert.equal(samples[1].decodedLine,"a second log line 🌋");
  assert.equal(samples[0].physicalRiftOriginVerified,false);
  assert.equal(samples[0].encoding,"utf8");
  assert.equal(r.records[0].rawSampleLines,2);
  assert.equal(r.records.filter(x=>x.event==="candidate_chat").length,0);
  assert.ok(r.records.some(x=>x.event==="finished" && x.reason==="raw_sample_limit"));
  assert.equal(r.records.some(x=>JSON.stringify(x).includes("OldPlayer")),false);
});
test("raw sample truncates long decoded text at UTF-8 boundaries",async()=>{
  const r=await launchFixture("🌋".repeat(350)+"\n",false,false,1);
  assert.equal(r.code,0);
  const sample=r.records.find(x=>x.event==="raw_log_sample");
  assert.ok(sample);
  assert.equal(sample.decodedUtf8Bytes,1400);
  assert.equal(Buffer.byteLength(sample.decodedLine,"utf8"),1024);
  assert.equal(sample.lineTruncated,true);
});
test("CLI includes bounded message body only after explicit --include-text",async()=>{
  const r=await launchFixture(
    "[Tell][NewPlayer]: こんにちは from chat\n"+
    "LPB_PROBE|RCM_CLI_20261120|unknown\n",true);
  assert.equal(r.code,0);
  const chat=r.records.filter(x=>x.event==="candidate_chat");
  assert.equal(chat.length,1);
  assert.equal(chat[0].text,"こんにちは from chat");
  assert.equal(chat[0].verifiedLiveFormat,false);
});
