"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const os=require("node:os");
const path=require("node:path");
const {spawn,spawnSync}=require("node:child_process");

const observer=path.resolve(__dirname,"..","tools","rcm-chat-observer.cjs");

function launchFixture(lines,includeText,prepareImport=false,rawSampleLines=0,inputMode="native"){
  return new Promise((resolve,reject)=>{
    const dir=fs.mkdtempSync(path.join(os.tmpdir(),"rcm-observer-cli-"));
    const file=path.join(dir,"Log.txt");
    // An existing stale chat line must not replay after the observer starts.
    fs.writeFileSync(file,"[Guild][OldPlayer]: stale should be ignored\n");
    const args=[observer,"--path",file,"--nonce","RCM_CLI_20261120",
      "--timeout-ms","2500","--poll-ms","25","--max-candidates","10"];
    if(includeText)args.push("--include-text");
    if(prepareImport)args.push("--prepare-import");
    if(inputMode!=="native")args.push("--input-mode",inputMode);
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
  assert.equal(r.records[0].includeText,false);
  const observed=r.records.filter(x=>x.event==="candidate_chat");
  assert.equal(observed.length,1);
  assert.equal("text" in observed[0],false);
  assert.equal(JSON.stringify(observed).includes("Hello from fixture"),false);
  assert.ok(r.records.some(x=>x.event==="matched"));
});
test("observer opt-in preparation can target RCM editor without sending input",async()=>{
  const result=await launchFixture(
    "[Guild][RCMProbe]: original fixture chat\n"+
    "LPB_PROBE|RCM_CLI_20261120|unknown\n",false,true,0,"editor"
  );
  assert.equal(result.code,0);
  assert.equal(result.records[0].prepareImport,true);
  assert.equal(result.records[0].inputMode,"editor");
  const imports=result.records.filter(e=>e.event==="rcm_manual_import");
  assert.equal(imports.length,1);
  assert.equal(imports[0].inputMode,"editor");
  assert.match(imports[0].commands[0],/^:import [A-F0-9]{12} 1\/1 /);
  assert.equal(Buffer.from(imports[0].commands[0].split(" ").at(-1),"base64url")
    .toString("utf8"),"G\0RCMProbe\0Guild\0original fixture chat");
  assert.equal(imports[0].automaticGameInput,false);
  assert.equal(imports[0].liveGameDeliveryVerified,false);
  const observed=result.records.filter(e=>e.event==="candidate_chat");
  assert.equal(observed.length,1);
  assert.equal("text" in observed[0],false);
  assert.equal(JSON.stringify(observed).includes("original fixture chat"),false);
});

test("prepared slash imports refuse truncated chat but keep complete next record",async()=>{
  const tooLong="🍀".repeat(130);
  const result=await launchFixture(
    "[Guild][LongPlayer]: "+tooLong+"\n"+
    "[Party][Ready]: complete line\n"+
    "LPB_PROBE|RCM_CLI_20261120|unknown\n",
    false,true
  );
  assert.equal(result.code,0);
  const candidates=result.records.filter(e=>e.event==="candidate_chat");
  assert.equal(candidates.length,2);
  assert.equal(candidates[0].truncated,true);
  assert.equal(candidates[0].textBytes,520);
  assert.ok(candidates.every(e=>!("text" in e)));
  const prepared=result.records.filter(e=>e.event==="rcm_manual_import");
  assert.equal(prepared.length,1);
  const payload=Buffer.from(prepared[0].commands[0].split(" ").at(-1),"base64url")
    .toString("utf8");
  assert.equal(payload,"P\0Ready\0Party\0complete line");
  const skipped=result.records.filter(e=>e.event==="import_skipped");
  assert.equal(skipped.length,1);
  assert.equal(skipped[0].reason,"truncated_chat_body");
  assert.equal(result.records.some(e=>e.event==="rcm_manual_import"&&e.kind==="guild"),false);
});

test("explicit include-text remains independent of command preparation",async()=>{
  const r=await launchFixture("[Guild][Atank]: clearly visible text\n"+
    "LPB_PROBE|RCM_CLI_20261120|unknown\n",true,true);
  assert.equal(r.code,0);
  const events=r.records.filter(e=>e.event==="candidate_chat");
  assert.equal(events.length,1);
  assert.equal(events[0].text,"clearly visible text");
  assert.equal(r.records.filter(e=>e.event==="rcm_manual_import").length,1);
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

test("CLI follows RIFT configured path when the log file is created after startup",async()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),"rcm-cfg-cli-"));
  const configuredRoot=path.join(dir,"RIFT configured data");
  const file=path.join(configuredRoot,"Log.txt");
  const roaming=path.join(dir,"home","AppData","Roaming");
  const conf=path.join(roaming,"RIFT","Rift.cfg");
  fs.mkdirSync(configuredRoot,{recursive:true});
  fs.mkdirSync(path.dirname(conf),{recursive:true});
  fs.writeFileSync(conf,["[Client]","DocumentsDirectory = "+configuredRoot,
    "LogConsole = False",""].join("\n"));
  const legacy=path.join(dir,"home","OneDrive","Documents","RIFT");
  fs.mkdirSync(legacy,{recursive:true});
  fs.writeFileSync(path.join(legacy,"Log.txt"),"old fallback content\n");
  const env={...process.env,APPDATA:roaming,USERPROFILE:path.join(dir,"home"),
    LUAPAD_LOG_CANDIDATES:""};
  const args=[observer,"--nonce","RCM_CLI_20261120","--timeout-ms","2500",
    "--poll-ms","25","--sample-raw-lines","1"];
  try{
    const run=await new Promise((resolve,reject)=>{
      const proc=spawn(process.execPath,args,{
        windowsHide:true,env,stdio:["ignore","pipe","pipe"]
      });
      let buffer="",stderr="",events=[],started=false,closed=false;
      const abort=setTimeout(()=>{if(!closed)proc.kill();},4500);
      proc.stdout.on("data",chunk=>{
        buffer+=chunk.toString();
        let index;
        while((index=buffer.indexOf("\n"))>=0){
          const raw=buffer.slice(0,index);buffer=buffer.slice(index+1);
          if(!raw)continue;
          let event;
          try{event=JSON.parse(raw)}catch(err){reject(err);return}
          events.push(event);
          if(event.event==="started" && !started){
            started=true;
            assert.equal(event.pathSelection,"rift_cfg_documents_directory");
            assert.equal(event.path,file);
            assert.equal(event.persistedLogConsole,false);
            assert.equal(event.runtimeLoggingEnabledVerified,false);
            assert.match(event.loggingReadinessHint,/LogConsole=False/);
            assert.equal(fs.existsSync(file),false);
            fs.appendFileSync(file,"unrecognized RIFT log format example\n");
          }
        }
      });
      proc.stderr.on("data",chunk=>{stderr+=chunk.toString()});
      proc.on("error",err=>{clearTimeout(abort);reject(err)});
      proc.on("close",code=>{
        closed=true;clearTimeout(abort);
        if(stderr)reject(new Error(stderr));
        else resolve({code,events,started});
      });
    });
    assert.equal(run.code,0);
    assert.equal(run.started,true);
    const lines=run.events.filter(e=>e.event==="raw_log_sample");
    assert.equal(lines.length,1);
    assert.equal(lines[0].decodedLine,"unrecognized RIFT log format example");
    assert.ok(run.events.some(e=>e.event==="finished" && e.reason==="raw_sample_limit"));
    assert.equal(JSON.stringify(run.events).includes("old fallback content"),false);
  }finally{fs.rmSync(dir,{recursive:true,force:true})}
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


function twoPhaseFixture({beforeMarker="",afterArmed="",rawSampleLines=0,
  truncateAfterArmed=false,replaceWithChatAfterArmed=false,replayMarker=false,
  expectedChatText=null,maxCandidates=200,prepareImport=false,
  inputMode="native"}={}){
  return new Promise((resolve,reject)=>{
    const dir=fs.mkdtempSync(path.join(os.tmpdir(),"rcm-observer-two-phase-"));
    const file=path.join(dir,"Log.txt");
    fs.writeFileSync(file,"[Guild][OldPlayer]: stale content\n");
    const args=[observer,"--path",file,"--nonce","RCM_PHASE_20261120",
      "--require-chat-after-marker","--timeout-ms","1600","--poll-ms","25"];
    if(rawSampleLines)args.push("--sample-raw-lines",String(rawSampleLines));
    if(expectedChatText)args.push("--require-chat-text",expectedChatText);
    if(maxCandidates!==200)args.push("--max-candidates",String(maxCandidates));
    if(prepareImport)args.push("--prepare-import","--input-mode",inputMode);
    const proc=spawn(process.execPath,args,{windowsHide:true,
      stdio:["ignore","pipe","pipe"]});
    let buffer="",stderr="",events=[],closed=false,armed=false,started=false;
    const abort=setTimeout(()=>{if(!closed)proc.kill()},3500);
    const cleanup=()=>fs.rmSync(dir,{recursive:true,force:true});
    proc.stdout.on("data",data=>{
      buffer+=data.toString();
      let index;
      while((index=buffer.indexOf("\n"))>=0){
        const line=buffer.slice(0,index);buffer=buffer.slice(index+1);
        if(!line)continue;
        let event;try{event=JSON.parse(line)}catch(err){reject(err);return}
        events.push(event);
        if(event.event==="started"&&!started){
          started=true;
          fs.appendFileSync(file,beforeMarker+
            "LPB_PROBE|RCM_PHASE_20261120|unknown\n");
        }
        if(event.event==="chat_phase_armed"&&!armed){
          armed=true;
          if(truncateAfterArmed)fs.truncateSync(file,0);
          else if(replaceWithChatAfterArmed)
            fs.writeFileSync(file,"[Guild][Injected]: must not count\n");
          else if(replayMarker)
            fs.appendFileSync(file,"LPB_PROBE|RCM_PHASE_20261120|unknown\n");
          else if(afterArmed)fs.appendFileSync(file,afterArmed);
        }
        if(event.event==="chat_phase_rearmed"&&afterArmed)
          fs.appendFileSync(file,afterArmed);
      }
    });
    proc.stderr.on("data",data=>{stderr+=data.toString()});
    proc.on("error",error=>{clearTimeout(abort);cleanup();reject(error)});
    proc.on("close",code=>{
      closed=true;clearTimeout(abort);cleanup();
      if(stderr)reject(new Error(stderr));
      else resolve({code,events,armed,started});
    });
  });
}

test("two-phase editor preparation preserves full candidate internally and rejects pre-marker text",async()=>{
  const token="RCM_AFTER_MARKER_20261120";
  const result=await twoPhaseFixture({
    beforeMarker:"[Guild][BeforeProbe]: pre-marker data must be ignored\n",
    afterArmed:"[Party][AfterProbe]: "+token+"\n",
    prepareImport:true,inputMode:"editor",expectedChatText:token
  });
  assert.equal(result.code,0);
  assert.equal(result.events[0].includeText,false);
  assert.equal(result.events[0].inputMode,"editor");
  const candidates=result.events.filter(e=>e.event==="candidate_chat");
  assert.equal(candidates.length,1);
  assert.equal(candidates[0].sender,"AfterProbe");
  assert.equal(candidates[0].chatTextMatched,true);
  assert.equal("text" in candidates[0],false);
  const imported=result.events.filter(e=>e.event==="rcm_manual_import");
  assert.equal(imported.length,1);
  assert.equal(imported[0].inputMode,"editor");
  assert.match(imported[0].commands[0],/^:import [A-F0-9]{12} 1\/1 /);
  assert.equal(Buffer.from(imported[0].commands[0].split(" ").at(-1),"base64url")
    .toString("utf8"),"P\0AfterProbe\0Party\0"+token);
  assert.equal(imported[0].automaticGameInput,false);
  assert.equal(imported[0].liveGameDeliveryVerified,false);
});

test("two-phase file replacement cannot emit an editor-import command",async()=>{
  const result=await twoPhaseFixture({
    replaceWithChatAfterArmed:true,
    prepareImport:true,inputMode:"editor"
  });
  assert.equal(result.code,2);
  assert.equal(result.events.filter(e=>e.event==="rcm_manual_import").length,0);
  assert.equal(result.events.find(e=>e.event==="finished").reason,
    "chat_source_changed_after_marker");
});

test("exact chat proof waits for intended text, not unrelated chat",async()=>{
  const proof="RCM_CHAT_EXACT_20261120";
  const result=await twoPhaseFixture({
    expectedChatText:proof,
    afterArmed:"[Guild][OtherPlayer]: unrelated chat\n"+
      "[Say][Atank]: "+proof+"\n"
  });
  assert.equal(result.code,0);
  assert.equal(result.events[0].requireChatAfterMarker,true);
  assert.equal(result.events[0].expectedChatTextRequired,true);
  const candidates=result.events.filter(e=>e.event==="candidate_chat");
  assert.equal(candidates.length,2);
  assert.equal(candidates[0].chatTextMatched,false);
  assert.equal(candidates[1].chatTextMatched,true);
  assert.equal(candidates[1].afterMarker,true);
  assert.equal("text" in candidates[1],false);
  assert.equal(JSON.stringify(result.events).includes("unrelated chat"),false);
  const done=result.events.find(e=>e.event==="finished");
  assert.equal(done.reason,"exact_chat_candidate_after_marker");
  assert.equal(done.chatTextMatched,true);
  assert.equal(done.chatCandidatesAfterMarker,2);
  assert.equal(done.transportVerified,false);
});

test("exact chat proof refuses only unrelated chat and times out",async()=>{
  const result=await twoPhaseFixture({
    expectedChatText:"RCM_CHAT_EXACT_20261120",
    afterArmed:"[Guild][OtherPlayer]: not the test message\n"
  });
  assert.equal(result.code,2);
  assert.equal(result.events.filter(e=>e.event==="candidate_chat").length,1);
  const done=result.events.find(e=>e.event==="finished");
  assert.equal(done.reason,"timeout_waiting_exact_chat_after_marker");
  assert.equal(done.chatTextMatched,false);
  assert.equal(done.chatCandidatesAfterMarker,1);
});

test("exact chat proof fails rather than falsely succeeding at unrelated candidate limit",async()=>{
  const result=await twoPhaseFixture({
    expectedChatText:"RCM_CHAT_EXACT_20261120",
    maxCandidates:1,
    afterArmed:"[Guild][OtherPlayer]: unrelated message one\n"+
      "[Guild][OtherPlayer]: unrelated message two\n"
  });
  assert.equal(result.code,2);
  const finished=result.events.find(e=>e.event==="finished");
  assert.equal(finished.reason,"candidate_limit_without_exact_chat");
  assert.equal(finished.chatTextMatched,false);
  assert.equal(finished.chatCandidatesAfterMarker,1);
});

test("two-phase mode confirms log marker THEN a freshly submitted chat candidate",async()=>{
  const result=await twoPhaseFixture({
    beforeMarker:"[Guild][BeforeProbe]: must not satisfy after-marker gate\n",
    afterArmed:"[Guild][AfterProbe]: bounded secret should stay redacted\n"
  });
  assert.equal(result.code,0);
  assert.equal(result.armed,true);
  const events=result.events;
  const marker=events.findIndex(e=>e.event==="matched");
  const armed=events.findIndex(e=>e.event==="chat_phase_armed");
  const candidate=events.findIndex(e=>e.event==="candidate_chat");
  assert.ok(marker>=0 && armed>marker && candidate>armed);
  assert.equal(events[candidate].sender,"AfterProbe");
  assert.equal(events[candidate].afterMarker,true);
  assert.equal("text" in events[candidate],false);
  assert.equal(JSON.stringify(events).includes("bounded secret"),false);
  assert.equal(JSON.stringify(events).includes("BeforeProbe"),false);
  const finished=events.find(e=>e.event==="finished");
  assert.equal(finished.reason,"chat_candidate_after_marker");
  assert.equal(finished.probeMatched,true);
  assert.equal(finished.chatCandidatesAfterMarker,1);
  assert.equal(finished.transportVerified,false);
});

test("two-phase mode cannot count old or pre-marker chat as proof",async()=>{
  const result=await twoPhaseFixture({
    beforeMarker:"[Guild][BeforeProbe]: not after the confirmed marker\n"
  });
  assert.equal(result.code,2);
  assert.equal(result.armed,true);
  assert.equal(result.events.filter(e=>e.event==="candidate_chat").length,0);
  const finished=result.events.find(e=>e.event==="finished");
  assert.equal(finished.reason,"timeout_waiting_chat_after_marker");
  assert.equal(finished.probeMatched,true);
  assert.equal(finished.chatCandidatesAfterMarker,0);
});

test("two-phase opt-in raw discovery never confuses unrecognized format with verified chat",async()=>{
  const result=await twoPhaseFixture({
    afterArmed:"Some unknown client format 🌋\n",rawSampleLines:1
  });
  assert.equal(result.code,2);
  const raw=result.events.find(e=>e.event==="raw_log_sample");
  assert.ok(raw);
  assert.equal(raw.decodedLine,"Some unknown client format 🌋");
  assert.equal(raw.physicalRiftOriginVerified,false);
  const finished=result.events.find(e=>e.event==="finished");
  assert.equal(finished.reason,"raw_sample_limit_without_chat_candidate");
  assert.equal(finished.chatCandidatesAfterMarker,0);
});

test("two-phase mode fails closed when Log.txt is truncated after the marker",async()=>{
  const result=await twoPhaseFixture({truncateAfterArmed:true});
  assert.equal(result.armed,true);
  assert.equal(result.code,2);
  assert.ok(result.events.some(e=>e.event==="file_reset"));
  const finished=result.events.find(e=>e.event==="finished");
  assert.equal(finished.reason,"chat_source_changed_after_marker");
  assert.equal(finished.probeMatched,true);
  assert.equal(finished.chatCandidatesAfterMarker,0);
});

test("file replacement and a fresh-looking chat line cannot forge second-stage proof",async()=>{
  const result=await twoPhaseFixture({replaceWithChatAfterArmed:true});
  assert.equal(result.code,2);
  assert.equal(result.armed,true);
  assert.ok(result.events.some(e=>e.event==="file_reset"));
  assert.equal(result.events.filter(e=>e.event==="candidate_chat").length,0);
  assert.equal(result.events.find(e=>e.event==="finished").reason,
    "chat_source_changed_after_marker");
});

test("a repeated marker rearms the second phase rather than freezing its tailer",async()=>{
  const result=await twoPhaseFixture({replayMarker:true,
    afterArmed:"[Guild][AfterRearm]: fresh after second marker\n"});
  assert.equal(result.code,0);
  assert.ok(result.events.some(e=>e.event==="chat_phase_rearmed"));
  assert.equal(result.events.filter(e=>e.event==="candidate_chat").length,1);
  assert.equal(result.events.find(e=>e.event==="finished").reason,
    "chat_candidate_after_marker");
});

test("startup receipt precedes candidates arriving in the initial poll",()=>{
  // Inject one first-poll record in a separate Node process; no RIFT or log file.
  const script=`
    const {LogTailProbe}=require(${JSON.stringify(path.resolve(__dirname,"..","..","LuaPadModern","tools","rift-log-probe.cjs"))});
    const original=LogTailProbe.prototype.poll;
    let first=true;
    LogTailProbe.prototype.poll=function(...args){
      if(first){
        first=false;
        const when=Date.now();
        this.readLine("[Guild][EarlyPlayer]: first poll fixture",when);
        this.readLine("LPB_PROBE|RCM_ORDER_20261120|unknown",when);
        return this.match ? [{event:"file_opened",offset:0},this.match] : [];
      }
      return original.apply(this,args);
    };
    require(${JSON.stringify(observer)}).start([
      "--nonce","RCM_ORDER_20261120","--timeout-ms","1000","--poll-ms","25"]);
  `;
  const run=spawnSync(process.execPath,["-e",script],{
    cwd:path.resolve(__dirname,".."),windowsHide:true,encoding:"utf8",timeout:4000
  });
  assert.equal(run.status,0,run.stderr);
  const events=run.stdout.trim().split(/\r?\n/).map(JSON.parse);
  assert.equal(events[0].event,"started");
  assert.equal(events[1].event,"file_opened");
  assert.equal(events[2].event,"candidate_chat");
  assert.equal(events[2].sender,"EarlyPlayer");
  assert.ok(events.some(x=>x.event==="matched"));
  assert.ok(events.some(x=>x.event==="finished"&&x.reason==="marker_matched"));
});
