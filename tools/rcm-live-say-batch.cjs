"use strict";

// One exact, already-observed RIFT /say canary -> bounded RCM editor batch.
// Offline, local, READ-ONLY log inspection. Default emits only an encoded
// one-part import recipe; NEVER focuses game or sends keys.
// Requires exact SHA of the source file so another session/rotation cannot
// silently change the chosen source. Keep actual game Log.txt out of Git.
const fs=require("node:fs");
const path=require("node:path");
const crypto=require("node:crypto");
const {parseCandidateLine}=require("./rcm-chat-observer.cjs");
const {encodeRecord}=require("./rcm-chat-import.cjs");

function chooseFromBytes(bytes,expected,expectedSha) {
  if(!Buffer.isBuffer(bytes)||bytes.length===0||bytes.length>1048576)
    throw Error("Invalid or overlarge game log");
  if(!/^RCM_[A-Z0-9_]{8,64}$/.test(expected))
    throw Error("Expected one controlled RCM test token");
  if(!/^[a-f0-9]{64}$/i.test(expectedSha))
    throw Error("Expected SHA256");
  const sha=crypto.createHash("sha256").update(bytes).digest("hex");
  if(sha.toLowerCase()!==expectedSha.toLowerCase())
    throw Error("Log hash changed; refuse ambiguous source");
  const matches=[];
  const lines=bytes.toString("utf8").replace(/^\uFEFF/,"").split(/\r?\n/);
  if(lines.length>10000)throw Error("Too many log lines");
  for(const line of lines) {
    if(!line.includes(expected))continue;
    const parsed=parseCandidateLine(line);
    if(!parsed || parsed.format!=="rift-live-2026-say" ||
        parsed.verifiedLiveFormat!==true || parsed.kind!=="general" ||
        parsed.channel!=="Say" || parsed.text!==expected ||
        parsed.truncated || parsed.textBytes!==Buffer.byteLength(expected,"utf8"))
      throw Error("Exact test token appears outside verified live Say shape");
    matches.push(parsed);
  }
  if(matches.length!==1)throw Error("Expected exactly one complete Say canary");
  return encodeRecord(matches[0],undefined,"editor");
}
function parseArgs(argv) {
  if(argv.length!==6 || argv[0]!=="--path" || argv[2]!=="--canary" ||
      argv[4]!=="--expect-sha256")
    throw Error("Usage: --path ABSOLUTE_Log.txt --canary RCM_TOKEN --expect-sha256 SHA256");
  const file=argv[1];
  if(typeof file!=="string" || !path.isAbsolute(file) ||
      path.basename(file).toLowerCase()!=="log.txt")
    throw Error("Must use absolute RIFT Log.txt");
  return {file,canary:argv[3],sha:argv[5]};
}
function run(argv=process.argv.slice(2)) {
  const opts=parseArgs(argv);
  const st=fs.lstatSync(opts.file);
  if(!st.isFile()||st.isSymbolicLink()||st.size>1048576)
    throw Error("Not a bounded regular Log.txt file");
  const result=chooseFromBytes(fs.readFileSync(opts.file),opts.canary,opts.sha);
  process.stdout.write(JSON.stringify(result)+"\n");
  return result;
}
if(require.main===module) {
  try{run();}
  catch(err){
    // Never print file content, private sender or encoded text on failure.
    process.stderr.write("RCM exact Say import preparation refused: "+err.message+"\n");
    process.exitCode=2;
  }
}
module.exports={chooseFromBytes,parseArgs,run};
