"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const os=require("node:os");
const crypto=require("node:crypto");
const {spawnSync}=require("node:child_process");
const {chooseFromBytes,parseArgs}=require("../tools/rcm-live-say-batch.cjs");
const SOURCE=path.resolve(__dirname,"..","tools","rcm-live-say-batch.cjs");
const CANARY="RCM_CHAT_TEST_20261121";
function sha(buffer){return crypto.createHash("sha256").update(buffer).digest("hex");}
function fixture(verb="says"){
  return Buffer.from("Noncombat logging enabled\n"+
     "17:17:23: [ExampleCharacter] "+verb+": "+CANARY+"\n","utf8");
}
test("one exact captured Say becomes one correctly bounded editor import",()=>{
  const bytes=fixture();
  const encoded=chooseFromBytes(bytes,CANARY,sha(bytes));
  assert.equal(encoded.inputMode,"editor");
  assert.equal(encoded.kind,"general");
  assert.equal(encoded.parts,1);
  assert.equal(encoded.automaticGameInput,false);
  assert.equal(encoded.liveGameDeliveryVerified,false);
  assert.equal(encoded.requiresManualEntry,true);
  const command=encoded.commands[0];
  assert.match(command,/^:import [A-F0-9]{12} 1\/1 [A-Za-z0-9_-]+$/);
  const wire=Buffer.from(command.split(" ").at(-1),"base64url").toString("utf8");
  assert.equal(wire,"S\0ExampleCharacter\0Say\0"+CANARY);
});
test("exact canary, format and file hash must all match",()=>{
  const bytes=fixture();
  assert.throws(()=>chooseFromBytes(bytes,CANARY,"0".repeat(64)),/hash changed/);
  assert.throws(()=>chooseFromBytes(bytes,"RCM_OTHER_TEST","0".repeat(64)),/hash changed/);
  assert.throws(()=>chooseFromBytes(bytes,"plain message",sha(bytes)),/controlled/);
  assert.throws(()=>chooseFromBytes(fixture("shouts"),CANARY,sha(fixture("shouts"))),
    /outside verified live Say/);
  assert.throws(()=>chooseFromBytes(Buffer.alloc(0),CANARY,sha(Buffer.alloc(0))),/Invalid/);
});
test("refuses duplicate canary or partial replay without silent truncation",()=>{
  const one=fixture(), dup=Buffer.concat([one,one]);
  assert.throws(()=>chooseFromBytes(dup,CANARY,sha(dup)),/exactly one/);
  const missing=Buffer.from("Noncombat logging enabled\n");
  assert.throws(()=>chooseFromBytes(missing,CANARY,sha(missing)),/exactly one/);
  const embedded=Buffer.from("17:17:23: [ExampleCharacter] says: hi "+CANARY+"\n");
  assert.throws(()=>chooseFromBytes(embedded,CANARY,sha(embedded)),/outside verified/);
});
test("CLI accepts only absolute canonical Log.txt and exact arguments",()=>{
  assert.throws(()=>parseArgs([]),/Usage/);
  assert.throws(()=>parseArgs(["--path","relative/Log.txt","--canary",CANARY,"--expect-sha256","a".repeat(64)]),/absolute/);
  assert.throws(()=>parseArgs(["--path","C:\\private\\Chat.txt","--canary",CANARY,"--expect-sha256","a".repeat(64)]),/Log.txt/);
});
test("subprocess never starts game input; output is one batch, no other log bodies",()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),"rcm-physical-say-preflight-"));
  const file=path.join(dir,"Log.txt");
  try{
    const data=Buffer.concat([fixture(),Buffer.from(
      "17:18:15: [AnotherCharacter] says: unrelated private chat content\n")]);
    fs.writeFileSync(file,data);
    const result=spawnSync(process.execPath,[SOURCE,"--path",file,
      "--canary",CANARY,"--expect-sha256",sha(data)],
      {encoding:"utf8",timeout:15000,windowsHide:true});
    assert.equal(result.status,0,result.stderr);
    const decoded=JSON.parse(result.stdout.trim());
    assert.equal(decoded.event,"rcm_manual_import");
    assert.equal(decoded.inputMode,"editor");
    assert.equal(decoded.parts,1);
    assert.equal(decoded.automaticGameInput,false);
    assert.ok(!result.stdout.includes("unrelated private"));
    assert.ok(!result.stderr.includes("unrelated private"));
    assert.ok(!decoded.commands.join(" ").includes("AnotherCharacter"));
  }finally{fs.rmSync(dir,{recursive:true,force:true})}
});
