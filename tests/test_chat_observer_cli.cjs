"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const os=require("node:os");
const path=require("node:path");
const {spawn}=require("node:child_process");

const observer=path.resolve(__dirname,"..","tools","rcm-chat-observer.cjs");

function launchFixture(lines,includeText){
  return new Promise((resolve,reject)=>{
    const dir=fs.mkdtempSync(path.join(os.tmpdir(),"rcm-observer-cli-"));
    const file=path.join(dir,"Log.txt");
    // An existing stale chat line must not replay after the observer starts.
    fs.writeFileSync(file,"[Guild][OldPlayer]: stale should be ignored\n");
    const args=[observer,"--path",file,"--nonce","RCM_CLI_20261120",
      "--timeout-ms","2500","--poll-ms","25","--max-candidates","10"];
    if(includeText)args.push("--include-text");
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
  assert.equal(chat.some(x=>x.sender==="OldPlayer"),false);
  assert.ok(r.records.some(x=>x.event==="matched"));
  assert.ok(r.records.some(x=>x.event==="finished"&&x.reason==="marker_matched"));
  assert.ok(r.records.every(x=>x.transportVerified===undefined||x.transportVerified===false));
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
