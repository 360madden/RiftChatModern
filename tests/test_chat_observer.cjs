"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const os=require("node:os");
const path=require("node:path");
const {
  parseCandidateLine,attachChatObserver,safePrefix,validLogPath,
  readConfiguredLogPath,readRiftClientConfig,resolveLogSelection,options
}=require("../tools/rcm-chat-observer.cjs");
const {LogTailProbe}=require("../../LuaPadModern/tools/rift-log-probe.cjs");

test("historical 3-field bracket chat, preserving sender, channel, time and text",()=>{
  const result=parseCandidateLine("[10:04:05][Guild][Atank]: hello from guild");
  assert.equal(result.event,"candidate_chat");
  assert.equal(result.kind,"guild");
  assert.equal(result.channel,"Guild");
  assert.equal(result.sender,"Atank");
  assert.equal(result.gameTimestamp,"10:04:05");
  assert.equal(result.text,"hello from guild");
  assert.equal(result.verifiedLiveFormat,false);
});
test("historical 2-field public channel from third-party RIFT logger",()=>{
  const result=parseCandidateLine("[3. World@Deepwood][AnotherPlayer]: world hello");
  assert.equal(result.kind,"public");
  assert.equal(result.channel,"World@Deepwood");
  assert.equal(result.sender,"AnotherPlayer");
  assert.equal(result.gameTimestamp,null);
});
test("common RIFT social categories mapped to internal RCM history kinds",()=>{
  for(const [label,kind] of Object.entries({
    "Say":"general","Local":"general","Yell":"general",
    "Raid":"party","Party":"party","Guild":"guild",
    "Officer":"guild","Tell":"tell","Whisper":"tell"
  })){
    assert.equal(parseCandidateLine("["+label+"][Sam]: "+label+" text").kind,kind);
  }
});
test("rejects combat/event/plain lines and malformed bracket structure",()=>{
  for(const line of [
    "20:23:13: ( 23, T=P, etc ) Damage 12",
    "RiftChatModern v0.2.8 | Loaded",
    "[NPC] someone is nearby","[Guild][Sam]:",
    "[Guild][Sam]: \r\n command", "[Guild][Sam]: hi\nadmin",
    "[Guild][Sa\nm]: text", "[Guild][]: text",
    "[Guild][Sam]: \x00bad",
    "[Something#Weird][Sam]: text"
  ]) assert.equal(parseCandidateLine(line),null,line);
});
test("avoids classifying system and combat notices as player chat",()=>{
  for(const name of ["System","NPC","Combat","CombatSpecial","LootMoney",
    "Quest","Achievement","Experience","Notification","Debug","Addons"]){
    assert.equal(parseCandidateLine("["+name+"][Server]: World event"),null,name);
  }
  assert.equal(parseCandidateLine("[Emote][Sam]: waves hello").kind,"general");
});
test("handles UTF-8 without splitting multibyte code points",()=>{
  const data="🍀".repeat(130);
  const msg=parseCandidateLine("[Tell][Iño]: "+data);
  assert.equal(msg.kind,"tell");
  assert.equal(msg.text,"🍀".repeat(128));
  assert.equal(msg.truncated,true);
  assert.equal(Buffer.byteLength(msg.text,"utf8"),512);
  const p=safePrefix("hello💚世界",10);
  assert.equal(p.text,"hello💚");
  assert.equal(p.truncated,true);
});
test("metadata-only observer redacts chat text while retaining original marker matching",()=>{
  const location=path.join(fs.mkdtempSync(path.join(os.tmpdir(),"rcm-chat-")),"Log.txt");
  try{
    fs.writeFileSync(location,"old stale log line\n");
    const t=new LogTailProbe({filePath:location,nonce:"RCM_TEST_123456"});
    const received=[];
    attachChatObserver(t,event=>received.push(event),false);
    let events=t.poll();
    assert.ok(events.some(x=>x.event==="file_opened"));
    fs.appendFileSync(location,"[Guild][Sam]: secret not shared\n");
    events=t.poll();
    assert.equal(received.length,1);
    assert.equal(received[0].sender,"Sam");
    assert.equal(Object.hasOwn(received[0],"text"),false);
    assert.equal(received[0].textBytes,17);
    assert.equal(t.match,null);
    fs.appendFileSync(location,"[15:14:13][Say][Atank]: hello\n"+
      "[System][Server]: LPB_PROBE|RCM_TEST_123456|1795180000.000\n");
    events=t.poll();
    assert.equal(received.length,2);
    assert.equal(received[1].textBytes,5);
    assert.ok(events.some(x=>x.event==="matched"));
    assert.equal(t.match.nonce,"RCM_TEST_123456");
    t.close();
  }finally{fs.rmSync(path.dirname(location),{recursive:true,force:true})}
});
test("includes message text only when caller explicitly requests it",()=>{
  const fake={readLine(){return null},poll(){return []}};
  const messages=[];
  attachChatObserver(fake,x=>messages.push(x),true);
  fake.readLine("[Party][Sam]: have a good day",Date.UTC(2026,10,20,15,0,0));
  assert.equal(messages.length,1);
  assert.equal(messages[0].text,"have a good day");
  assert.equal(messages[0].verifiedLiveFormat,false);
});
test("handles split file writes and UTF-16LE using LuaPadModern decoder",()=>{
  const location=path.join(fs.mkdtempSync(path.join(os.tmpdir(),"rcm-chat-")),"Log.txt");
  try{
    fs.writeFileSync(location,Buffer.from([0xFF,0xFE]));
    const tail=new LogTailProbe({filePath:location,nonce:"RCM_TEST_123456",fromStart:true});
    const messages=[];
    attachChatObserver(tail,x=>messages.push(x),true);
    tail.poll();
    const line=Buffer.from("[Guild][Iño]: 東京へようこそ\n","utf16le");
    fs.appendFileSync(location,line.subarray(0,17));
    tail.poll();
    assert.equal(messages.length,0);
    fs.appendFileSync(location,line.subarray(17));
    tail.poll();
    assert.equal(messages.length,1);
    assert.equal(messages[0].text,"東京へようこそ");
    tail.close();
  }finally{fs.rmSync(path.dirname(location),{recursive:true,force:true})}
});
test("reads a new chat record after the log has been truncated or replaced",()=>{
  const location=path.join(fs.mkdtempSync(path.join(os.tmpdir(),"rcm-chat-")),"Log.txt");
  try{
    fs.writeFileSync(location,"old first observation\n");
    const tail=new LogTailProbe({filePath:location,nonce:"RCM_TEST_123456"});
    const messages=[];
    attachChatObserver(tail,x=>messages.push(x),true);
    tail.poll();
    fs.appendFileSync(location,"[Say][Atank]: first post-baseline\n");
    tail.poll();
    assert.equal(messages.length,1);
    fs.truncateSync(location,0);
    tail.poll();
    fs.appendFileSync(location,"[Guild][Friend]: after rotation\n");
    tail.poll();
    assert.equal(messages.length,2);
    assert.equal(messages[1].text,"after rotation");
    tail.close();
  }finally{fs.rmSync(path.dirname(location),{recursive:true,force:true})}
});
test("Rift.cfg DocumentsDirectory overrides stale fallback logs and reports source",()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),"rcm-config-"));
  try{
    const user=path.join(dir,"home"), roaming=path.join(user,"AppData","Roaming");
    const root=path.join(dir,"RIFT Custom Data");
    fs.mkdirSync(path.join(roaming,"RIFT"),{recursive:true});
    fs.mkdirSync(root,{recursive:true});
    const legacy=path.join(user,"OneDrive","Documents","RIFT");
    fs.mkdirSync(legacy,{recursive:true});
    fs.writeFileSync(path.join(legacy,"Log.txt"),"old unrelated log\n");
    const cfg=path.join(roaming,"RIFT","Rift.cfg");
    fs.writeFileSync(cfg,["[Client]",'DocumentsDirectory = "'+root+'"',
      "LogConsole = False",""].join("\n"));
    const env={APPDATA:roaming,USERPROFILE:user};
    const chosen=readConfiguredLogPath(env);
    assert.equal(chosen,path.join(root,"Log.txt"));
    const selection=resolveLogSelection({},env);
    assert.equal(selection.source,"rift_cfg_documents_directory");
    assert.deepEqual(selection.candidates,[chosen]);
    assert.equal(selection.filePath,chosen);
    assert.equal(fs.existsSync(chosen),false);
    // An explicit command-line override always takes precedence.
    const explicit=resolveLogSelection({filePath:path.join(legacy,"Log.txt")},env);
    assert.equal(explicit.source,"explicit_path");
    assert.equal(explicit.filePath,path.join(legacy,"Log.txt"));
    const override=resolveLogSelection({}, {...env,LUAPAD_LOG_CANDIDATES:path.join(legacy,"Log.txt")});
    assert.equal(override.source,"luapad_override");
    assert.equal(override.filePath,path.join(legacy,"Log.txt"));
  }finally{fs.rmSync(dir,{recursive:true,force:true})}
});
test("Rift.cfg LogConsole is reported as persisted configuration, never a live state",()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),"rcm-logging-readiness-"));
  try{
    const roaming=path.join(dir,"Roaming");
    const cfg=path.join(roaming,"RIFT","Rift.cfg");
    fs.mkdirSync(path.dirname(cfg),{recursive:true});
    const env={APPDATA:roaming,USERPROFILE:dir};
    const docs=path.join(dir,"Redirected Documents");
    fs.writeFileSync(cfg,[
      "[Other]","LogConsole = True","[Client]",
      "DocumentsDirectory = "+docs,"LogConsole = False",""
    ].join("\n"));
    const off=readRiftClientConfig(env);
    assert.equal(off.filePath,path.join(docs,"Log.txt"));
    assert.equal(off.logConsoleConfigured,false);
    assert.equal(off.configReadable,true);
    assert.equal(off.runtimeLoggingEnabledVerified,false);
    assert.equal(Object.hasOwn(off,"chatHistory"),false);
    fs.writeFileSync(cfg,"[Client]\nLogConsole = True\n");
    const on=readRiftClientConfig(env);
    assert.equal(on.logConsoleConfigured,true);
    assert.equal(on.filePath,null);
    assert.equal(on.runtimeLoggingEnabledVerified,false);
    fs.writeFileSync(cfg,"[Client]\nLogConsole = suspicious\n");
    assert.equal(readRiftClientConfig(env).logConsoleConfigured,null);
    fs.rmSync(cfg);
    const missing=readRiftClientConfig(env);
    assert.equal(missing.logConsoleConfigured,null);
    assert.equal(missing.configReadable,false);
  }finally{fs.rmSync(dir,{recursive:true,force:true})}
});

test("invalid or oversized RIFT config fails safely to bounded default candidates",()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),"rcm-config-"));
  try{
    const roaming=path.join(dir,"AppData","Roaming"),user=path.join(dir,"home");
    const cfg=path.join(roaming,"RIFT","Rift.cfg");
    fs.mkdirSync(path.dirname(cfg),{recursive:true});
    const env={APPDATA:roaming,USERPROFILE:user};
    for(const bad of [
      ["[Client]","DocumentsDirectory = ..\\relative",""].join("\n"),
      ["[Other]","DocumentsDirectory = "+dir,""].join("\n"),
      ["[Client]","DocumentsDirectory = %NOT_DEFINED%\\RIFT",""].join("\n"),
      ["[Client]","DocumentsDirectory = "+("x".repeat(2400)),""].join("\n")
    ]){
      fs.writeFileSync(cfg,bad);
      assert.equal(readConfiguredLogPath(env),null);
      assert.equal(resolveLogSelection({},env).source,"generic_documents_fallback");
    }
    fs.writeFileSync(cfg,"x".repeat(512*1024+1));
    assert.equal(readConfiguredLogPath(env),null);
    assert.equal(resolveLogSelection({},env).source,"generic_documents_fallback");
    // Literal environment expansion is supported when it resolves absolutely.
    fs.writeFileSync(cfg,["[Client]","DocumentsDirectory = %USERPROFILE%\\RIFT",""].join("\n"));
    assert.equal(readConfiguredLogPath(env),path.join(user,"RIFT","Log.txt"));
  }finally{fs.rmSync(dir,{recursive:true,force:true})}
});
test("rejects unsafe/relative output paths and unbounded CLI options",()=>{
  assert.throws(()=>validLogPath("relative/Log.txt"));
  assert.throws(()=>validLogPath("C:\\Users\\test\\CombatLog.txt"));
  assert.throws(()=>options(["--poll-ms","1"]));
  assert.throws(()=>options(["--timeout-ms","9999999"]));
  assert.throws(()=>options(["--max-candidates","900000"]));
  assert.throws(()=>options(["--bad-option"]));
  assert.throws(()=>options(["--require-chat-text","RCM_CHAT_EXACT_20261120"]));
  assert.throws(()=>options(["--require-chat-after-marker","--require-chat-text","space invalid"]));
  assert.throws(()=>options(["--require-chat-after-marker","--require-chat-text","lowercase"] .concat(["--require-chat-text","SECOND_TOKEN_20261120"])));
  const exact=options(["--require-chat-after-marker","--require-chat-text","RCM_CHAT_EXACT_20261120"]);
  assert.equal(exact.requireChatAfterMarker,true);
  assert.equal(exact.requireChatText,"RCM_CHAT_EXACT_20261120");
  const opts=options(["--nonce","RCM_TEST_123456","--include-text"]);
  assert.equal(opts.nonce,"RCM_TEST_123456");
  assert.equal(opts.includeText,true);
});
