"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const cp=require("node:child_process");
const path=require("node:path");
const {
  encodeRecord,parseOptions
}=require("../tools/rcm-chat-import.cjs");

const cli=path.resolve(__dirname,"..","tools","rcm-chat-import.cjs");
function call(args,input) {
  return cp.spawnSync(process.execPath,[cli,...args],{
    input,encoding:"utf8",timeout:8000,windowsHide:true
  });
}
function decoded(commands) {
  return Buffer.from(commands.map(x=>x.split(" ").at(-1)).join(""),"base64url")
    .toString("utf8");
}
test("RCM editor mode emits the same bytes with :import, not native /rcm commands",()=>{
  const record={kind:"guild",sender:"Atank",channel:"Guild",text:"Go to RCM"};
  const direct=encodeRecord(record,"ABCDEF123456","editor");
  const native=encodeRecord(record,"ABCDEF123456");
  assert.equal(direct.inputMode,"editor");
  assert.equal(direct.automaticGameInput,false);
  assert.equal(direct.liveGameDeliveryVerified,false);
  assert.equal(direct.requiresManualEntry,true);
  assert.ok(direct.commands.every(cmd=>cmd.startsWith(":import ")));
  assert.ok(native.commands.every(cmd=>cmd.startsWith("/rcm import ")));
  assert.equal(decoded(direct.commands),decoded(native.commands));
  assert.equal(direct.parts,native.parts);
  const run=call(["--kind","guild","--sender","Atank","--channel","Guild",
                  "--text","Go to RCM","--id","ABCDEF123456",
                  "--input-mode","editor"]);
  assert.equal(run.status,0,run.stderr);
  const output=JSON.parse(run.stdout.trim());
  assert.equal(output.commands.length,1);
  assert.equal(output.commands[0],direct.commands[0]);
  assert.throws(()=>encodeRecord(record,"ABCDEF123456","unknown"));
  assert.throws(()=>parseOptions(["--input-mode","unknown"]));
});

test("stdin-json editor mode keeps typed commands and refuses incomplete chat",()=>{
  const rows=[
    {event:"candidate_chat",kind:"party",sender:"Sam",
      channel:"Party",text:"Hello editor",truncated:false},
    {event:"candidate_chat",kind:"guild",sender:"Sam",
      channel:"Guild",text:"shortened",truncated:true}
  ];
  const run=call(["--stdin-json","--input-mode","editor"],
    rows.map(JSON.stringify).join("\n")+"\n");
  assert.equal(run.status,2);
  const output=run.stdout.trim().split("\n").map(JSON.parse);
  assert.equal(output[0].inputMode,"editor");
  assert.ok(output[0].commands[0].startsWith(":import "));
  assert.equal(decoded(output[0].commands),"P\0Sam\0Party\0Hello editor");
  assert.equal(output[1].reason,"truncated_chat_body");
  assert.equal(output[2].generated,1);
  assert.equal(output[2].skipped,1);
});

test("short manual import has bounded slash command and strict metadata",()=>{
  const out=encodeRecord({kind:"guild",sender:"Atank",
    channel:"Guild",text:"Hi from host"},"ABCDEF123456");
  assert.equal(out.parts,1);
  assert.equal(out.protocol,"RCM1-B64URL");
  assert.equal(out.automaticGameInput,false);
  assert.equal(out.liveGameDeliveryVerified,false);
  assert.equal(out.requiresManualEntry,true);
  assert.match(out.commands[0],/^\/rcm import ABCDEF123456 1\/1 [A-Za-z0-9_-]+$/);
  assert.equal(decoded(out.commands),"G\0Atank\0Guild\0Hi from host");
});
test("full UTF-8 size generates 12 or fewer short slash chunks",()=>{
  const text="🌋".repeat(128);
  const out=encodeRecord({kind:"public",sender:"Iño",
    channel:"World@Deepwood",text},"ABCDEF123456");
  assert.ok(out.parts>1);
  assert.ok(out.parts<=12);
  assert.ok(out.commands.every(x=>x.length<=160));
  assert.equal(decoded(out.commands),"C\0Iño\0World@Deepwood\0"+text);
});
test("valid kind codes remain stable for all supported chat categories",()=>{
  for(const [kind,code] of Object.entries({
    general:"S",party:"P",guild:"G",tell:"T",public:"C"
  })){
    const p=encodeRecord({kind,sender:"Player",channel:kind,text:"text"},"ABCDEF123456");
    assert.ok(decoded(p.commands).startsWith(code+"\0"));
  }
});
test("oversize, control chars, invalid tokens and unknown category rejected",()=>{
  const base={kind:"guild",sender:"Player",channel:"Guild",text:"ok"};
  for(const bad of [
    {...base,text:"x".repeat(513)},{...base,sender:"X\nY"},
    {...base,channel:"Guild\r"},{...base,kind:"admin"},
    {...base,text:""},{...base,sender:"Bad\uD800Name"}
  ]) assert.throws(()=>encodeRecord(bad,"ABCDEF123456"));
  assert.throws(()=>encodeRecord(base,"abc"));
  assert.throws(()=>encodeRecord(base,"XYZXYZXYZXYZ"));
  assert.throws(()=>parseOptions(["--stdin-json","--kind","guild"]));
  assert.throws(()=>parseOptions(["--max-records","0"]));
  assert.throws(()=>parseOptions(["--unknown"]));
});
test("never encode a shortened source chat record as a full message",()=>{
  const full="🍀".repeat(130);
  const candidate=require("../tools/rcm-chat-observer.cjs")
    .parseCandidateLine("[Guild][Atank]: "+full);
  assert.equal(candidate.truncated,true);
  assert.equal(candidate.textBytes,520);
  assert.equal(Buffer.byteLength(candidate.text,"utf8"),512);
  assert.throws(
    ()=>encodeRecord(candidate,"ABCDEF123456"),
    /truncated/,
  );
  const complete={...candidate,text:full,truncated:false};
  assert.throws(()=>encodeRecord(complete,"ABCDEF123456"));
  // Source byte count can expose truncation even when the flag is wrong.
  assert.throws(()=>encodeRecord({kind:"guild",sender:"Atank",channel:"Guild",
    text:"short",textBytes:520,truncated:false},"ABCDEF123456"),/truncated/);
});

test("stdin-json refuses truncated observer records and exposes the reason",()=>{
  const truncated={event:"candidate_chat",source:"RIFT_Log.txt",kind:"guild",
    channel:"Guild",sender:"Atank",text:"🍀".repeat(128),
    truncated:true,textBytes:520};
  const ok={event:"candidate_chat",source:"RIFT_Log.txt",kind:"guild",
    channel:"Guild",sender:"Atank",text:"short complete",truncated:false};
  const run=call(["--stdin-json"],[truncated,ok]
    .map(JSON.stringify).join("\n")+"\n");
  assert.equal(run.status,2,run.stderr);
  const result=run.stdout.trim().split("\n").map(JSON.parse);
  assert.equal(result[0].event,"import_skipped");
  assert.equal(result[0].reason,"truncated_chat_body");
  assert.equal(result[1].parts,1);
  assert.equal(decoded(result[1].commands),"G\0Atank\0Guild\0short complete");
  assert.equal(result[2].generated,1);
  assert.equal(result[2].skipped,1);
});

test("manual CLI prints exactly one user-pasteable command, not game input",()=>{
  const r=call(["--kind","tell","--sender","Sam","--channel",
    "Tell","--text","Hello","--id","ABCDEF123456"]);
  assert.equal(r.status,0,r.stderr);
  const row=JSON.parse(r.stdout.trim());
  assert.equal(row.commands.length,1);
  assert.equal(row.liveGameDeliveryVerified,false);
  assert.equal(row.automaticGameInput,false);
  assert.equal(decoded(row.commands),"T\0Sam\0Tell\0Hello");
});
test("stdin-json accepts candidate_chat lines with explicit text",()=>{
  const lines=[
    {event:"started",source:"RIFT_Log.txt",transportVerified:false},
    {event:"candidate_chat",source:"RIFT_Log.txt",kind:"party",
      sender:"Sam",channel:"Party",text:"Hello from real text fixture",
      verifiedLiveFormat:false},
    {event:"candidate_chat",source:"RIFT_Log.txt",kind:"guild",
      sender:"Mia",channel:"Guild",text:"Second line",verifiedLiveFormat:false}
  ];
  const r=call(["--stdin-json","--max-records","2"],
    lines.map(x=>JSON.stringify(x)).join("\n")+"\n");
  assert.equal(r.status,0,r.stderr);
  const parsed=r.stdout.trim().split("\n").map(x=>JSON.parse(x));
  assert.equal(parsed.length,3);
  assert.equal(parsed[0].kind,"party");
  assert.equal(parsed[1].kind,"guild");
  assert.equal(parsed[2].generated,2);
  assert.equal(parsed[2].skipped,0);
  assert.equal(parsed[2].automaticGameInput,false);
});
test("stdin-json does not invent absent chat bodies",()=>{
  const row={event:"candidate_chat",kind:"guild",sender:"Sam",
    channel:"Guild",verifiedLiveFormat:false};
  const r=call(["--stdin-json"],JSON.stringify(row)+"\n");
  assert.equal(r.status,2);
  const parsed=r.stdout.trim().split("\n").map(x=>JSON.parse(x));
  assert.equal(parsed[0].event,"import_skipped");
  assert.equal(parsed[0].reason,"message_text_not_requested");
  assert.equal(parsed[1].generated,0);
});
test("CLI help is bounded and does not start a game interaction",()=>{
  const r=call(["--help"]);
  assert.equal(r.status,0);
  assert.match(r.stdout,/Never sends input to RIFT/);
  assert.equal(r.stderr,"");
});
