"use strict";

// Host-side encoder for manually pastable /rcm import commands.
// It does NOT send keys, modify the game, or claim verified social chat.
const crypto=require("node:crypto");
const readline=require("node:readline");

const KINDS={general:"S",party:"P",guild:"G",tell:"T",public:"C"};
const MAX_CHUNK=88;
const MAX_PARTS=12;
const MAX_INPUT_BYTES=780;

function validField(v,min,max) {
  if(typeof v!=="string" || Buffer.byteLength(v,"utf8")<min ||
      Buffer.byteLength(v,"utf8")>max || /[\x00-\x1F\x7F]/.test(v))return false;
  return Buffer.from(v,"utf8").toString("utf8")===v;
}
function encodeRecord(record, id=crypto.randomBytes(6).toString("hex").toUpperCase()) {
  if(!record || !Object.hasOwn(KINDS,record.kind) ||
    !validField(record.sender,1,40) ||
    !validField(record.channel,1,72) ||
    !validField(record.text,1,512)) {
    throw Error("Invalid source, channel, kind or message field");
  }
  if(!/^[A-F0-9]{12}$/.test(id))throw Error("ID must be 12 uppercase hex characters");
  const raw=Buffer.from([KINDS[record.kind],record.sender,record.channel,
    record.text].join("\0"),"utf8");
  if(raw.length>MAX_INPUT_BYTES)throw Error("Record exceeds import byte bound");
  const b64=raw.toString("base64url");
  const chunks=b64.match(/.{1,88}/g)||[];
  if(chunks.length<1||chunks.length>MAX_PARTS)throw Error("Too many import chunks");
  const commands=chunks.map((segment,index)=>"/rcm import "+id+" "+
    (index+1)+"/"+chunks.length+" "+segment);
  if(commands.some(cmd=>cmd.length>160))throw Error("RIFT slash argument limit exceeded");
  return {event:"rcm_manual_import",protocol:"RCM1-B64URL",id,kind:record.kind,
    parts:chunks.length,source:"Windows_candidate_parser",
    automaticGameInput:false,liveGameDeliveryVerified:false,
    requiresManualEntry:true,commands};
}
function parseOptions(argv){
  const v={stdinJson:false,maxRecords:30};
  for(let i=0;i<argv.length;i++){
    const flag=argv[i];
    if(flag==="--stdin-json"||flag==="--help"){
      if(v[flag.slice(2).replace("-","")]===true)throw Error("Duplicate option");
      if(flag==="--stdin-json")v.stdinJson=true;else v.help=true;
      continue;
    }
    if(!["--kind","--sender","--channel","--text","--id","--max-records"].includes(flag) ||
      argv[i+1]===undefined)throw Error("Unknown/incomplete option: "+flag);
    const key=flag.slice(2);
    if(Object.hasOwn(v,key))throw Error("Duplicate option: "+flag);
    v[key]=argv[++i];
  }
  if(v["max-records"]!==undefined){
    const n=Number(v["max-records"]);
    if(!Number.isSafeInteger(n)||n<1||n>100)throw Error("Invalid max-records");
    v.maxRecords=n;
  }
  if(v.stdinJson){
    if(["kind","sender","channel","text","id"].some(key=>v[key]!==undefined))
      throw Error("stdin-json cannot be mixed with a manual record");
  }else if(!v.help && ["kind","sender","channel","text"].some(key=>v[key]===undefined)){
    throw Error("Supply kind/sender/channel/text or --stdin-json");
  }
  return v;
}
function start(argv=process.argv.slice(2)) {
  let v;
  try{v=parseOptions(argv)}
  catch(e){process.stderr.write(e.message+"\n");process.exitCode=1;return}
  if(v.help) {
    process.stdout.write(
      "node tools/rcm-chat-import.cjs --kind guild --sender Sam --channel Guild --text TEXT\n"+
      "node tools/rcm-chat-import.cjs --stdin-json < observer-jsonl\n"+
      "Outputs manual /rcm import commands only. Never sends input to RIFT.\n");
    return;
  }
  const write=(out)=>process.stdout.write(JSON.stringify(out)+"\n");
  if(!v.stdinJson){
    try{write(encodeRecord(v,v.id))}
    catch(e){process.stderr.write(e.message+"\n");process.exitCode=1}
    return;
  }
  let count=0,errors=0;
  const rl=readline.createInterface({input:process.stdin,crlfDelay:Infinity});
  rl.on("line",line=>{
    if(count>=v.maxRecords)return;
    if(line.length>16384){errors++;return}
    try{
      const event=JSON.parse(line);
      if(event.event!=="candidate_chat")return;
      if(event.text===undefined){
        errors++;write({event:"import_skipped",reason:"message_text_not_requested"});
        return;
      }
      write(encodeRecord(event));count++;
    }catch(e){errors++;write({event:"import_skipped",reason:"malformed_or_unencodable_record"})}
  });
  rl.on("close",()=>{
    write({event:"import_summary",generated:count,skipped:errors,
      automaticGameInput:false,liveGameDeliveryVerified:false});
    if(errors>0)process.exitCode=2;
  });
}
if(require.main===module)start();
module.exports={encodeRecord,parseOptions,start};
