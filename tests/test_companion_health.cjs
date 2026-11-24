"use strict";

// All queue files and dependency stubs below are temporary synthetic fixtures.
// No real RIFT log, game save, player chat, or live input is accessed.
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const os=require("node:os");
const path=require("node:path");
const {spawnSync}=require("node:child_process");
const {encodeRecord}=require("../tools/rcm-chat-import.cjs");
const state=require("../tools/rcm-say-delivery-state.cjs");
const health=require("../tools/rcm-companion-health.cjs");
const {inspectPath,readBounded}=require("../tools/rcm-readonly-file.cjs");

function fixture(t) {
    const base=fs.mkdtempSync(path.join(os.tmpdir(),"rcm-health-"));
    t.after(()=>fs.rmSync(base,{recursive:true,force:true}));
    const root=path.join(base,"RiftChatModern");
    const dir=path.join(root,"artifacts","rcm-private-queue");
    const python=path.join(root,".venv","Scripts","python.exe");
    const dotnet=path.join(base,"sdk","dotnet.exe");
    const decoder=path.join(base,"LuaPadModern","tools","rift-log-probe.cjs");
    function put(file,text="fixture") {
        fs.mkdirSync(path.dirname(file),{recursive:true});
        fs.writeFileSync(file,text);
    }
    for(const file of [python,dotnet,decoder,
        path.join(root,"tools","RcmEditorSender","bin","Release","net10.0-windows","RcmEditorSender.dll"),
        path.join(root,"tools","rcm_disk_receipt.py"),
        path.join(root,"tools","rcm_session_preflight.py"),
        path.join(root,"addon","RiftChatModern","RiftAddon.toc")])put(file);
    const context={root,hostname:"FIXTURE",platform:"win32",env:{RCM_DOTNET:dotnet}};
    const file=name=>path.join(dir,state.createStore(name).profile.filename);
    function report(extra={}) {
        return health.collectHealth({stateDir:dir,python,expectHost:"FIXTURE",...extra},context);
    }
    function seed(name,token="AABBCCDDEEFF",claim=false) {
        fs.mkdirSync(dir,{recursive:true});
        const store=state.createStore(name),p=store.profile;
        const s=store.fresh(),sid=store.beginSession(s);
        const text="PRIVATE_FIXTURE_CHAT_BODY";
        const batch=encodeRecord({kind:p.kind,channel:p.channel,sender:"PRIVATE_FIXTURE_SPEAKER",text},token,"editor");
        store.acceptPair(s,sid,{
            event:p.event,format:p.format,channel:p.channel,kind:p.kind,
            channelSlot:p.slot,source:"RIFT_Log.txt",verifiedLiveFormat:true,
            physicalRiftOriginVerified:false,senderRedacted:true,textRedacted:true,
            sequence:1,textBytes:Buffer.byteLength(text),gameTimestamp:"12:00:00"
        },batch);
        store.completeSession(s,sid,true,"PRIVATE_SESSION_REASON");
        if(claim)store.claimNext(s);
        store.writeState(file(name),s);
        return s;
    }
    return {base,root,dir,python,dotnet,decoder,context,put,file,report,seed};
}
function codes(report) {return report.issues.map(x=>x.code);}
function cli(args) {
    return spawnSync(process.execPath,[path.resolve(__dirname,"../tools/rcm-companion-health.cjs"),...args],
        {encoding:"utf8",timeout:15000,windowsHide:true});
}

test("fresh missing directory and journals are not created or represented as existing",t=>{
    const f=fixture(t),r=f.report();
    assert.equal(r.queues.directory,"absent");
    for(const name of ["say","public"]) {
        assert.equal(r.queues.profiles[name].state,"absent");
        assert.equal(r.queues.profiles[name].counts.claimed,0);
    }
    assert.equal(r.status,"attention"); // synthetic decoder differs from known baseline
    assert.equal(r.dispatchAuthorized,false);
    assert.equal(r.gameSessionVerified,false);
    assert.equal(fs.existsSync(f.dir),false);
});

test("dependency checks identify missing decoder without importing its code",t=>{
    const f=fixture(t);
    fs.unlinkSync(f.decoder);
    const r=f.report();
    assert.equal(r.status,"blocked");
    assert.equal(r.dependencies.decoder.state,"absent");
    assert.ok(codes(r).includes("dependency_absent"));
    assert.equal(r.subprocessesStarted,false);
});

test("explicit missing Python and wrong host block without disclosing values",t=>{
    const f=fixture(t);
    const r=f.report({python:path.join(f.base,"PRIVATE_MISSING_EXECUTABLE.exe"),expectHost:"WRONG_PRIVATE_HOST"});
    assert.equal(r.status,"blocked");
    assert.equal(r.expectedHostMatched,false);
    assert.equal(r.dependencies.python.state,"absent");
    assert.ok(codes(r).includes("expected_host_mismatch"));
    assert.doesNotMatch(JSON.stringify(r),/WRONG_PRIVATE_HOST|PRIVATE_MISSING_EXECUTABLE/);
});

test("valid queues retain counts but never emit identity, message, or session fields",t=>{
    const f=fixture(t);
    f.seed("say","AABBCCDDEEFF",true);
    f.seed("public","112233445566");
    const original=fs.readFileSync(f.file("say"));
    const r=f.report();
    assert.equal(r.status,"attention");
    assert.equal(r.queues.profiles.say.state,"valid");
    assert.equal(r.queues.profiles.say.counts.claimed,1);
    assert.equal(r.queues.profiles.public.counts.queued,1);
    assert.equal(r.queues.crossProfileTokenCollision,false);
    assert.ok(codes(r).includes("unresolved_claim_do_not_retry"));
    assert.ok(codes(r).includes("queued_transfers_present"));
    assert.doesNotMatch(JSON.stringify(r),/AABBCCDDEEFF|112233445566|PRIVATE_FIXTURE|PRIVATE_SESSION_REASON/);
    assert.ok(!JSON.stringify(r).includes(f.base));
    assert.deepEqual(fs.readFileSync(f.file("say")),original);
    assert.equal(fs.existsSync(path.join(f.dir,state.GLOBAL_EDITOR_LOCK)),false);
});

test("existing profile and global locks are observed, never removed or read",t=>{
    const f=fixture(t);
    f.seed("say");
    const lock=path.join(f.dir,state.GLOBAL_EDITOR_LOCK);
    const profileLock=f.file("say")+".lock";
    f.put(lock,"PRIVATE_LOCK_CONTENT");
    f.put(profileLock,"PRIVATE_PROFILE_LOCK");
    const r=f.report();
    assert.equal(r.queues.globalLock,"present");
    assert.equal(r.queues.profiles.say.lock,"present");
    assert.ok(codes(r).includes("global_editor_lock_present"));
    assert.ok(codes(r).includes("profile_lock_present"));
    assert.equal(fs.readFileSync(lock,"utf8"),"PRIVATE_LOCK_CONTENT");
    assert.equal(fs.readFileSync(profileLock,"utf8"),"PRIVATE_PROFILE_LOCK");
    assert.doesNotMatch(JSON.stringify(r),/PRIVATE_LOCK_CONTENT|PRIVATE_PROFILE_LOCK/);
});

test("cross-profile token collision and simultaneous claims block the aggregate",t=>{
    const f=fixture(t);
    f.seed("say","AABBCCDDEEFF",true);
    f.seed("public","AABBCCDDEEFF",true);
    const r=f.report();
    assert.equal(r.status,"blocked");
    assert.equal(r.queues.crossProfileTokenCollision,true);
    assert.equal(r.queues.simultaneousClaims,true);
    assert.ok(codes(r).includes("cross_profile_token_collision"));
    assert.ok(codes(r).includes("simultaneous_claims_across_profiles"));
});

test("malformed journal is not an empty journal and is left untouched",t=>{
    const f=fixture(t);
    f.put(f.file("say"),'{"PRIVATE_CORRUPT_PAYLOAD":');
    const r=f.report();
    assert.equal(r.status,"blocked");
    assert.equal(r.queues.profiles.say.state,"invalid_or_unreadable");
    assert.equal(r.queues.profiles.say.counts,undefined);
    assert.equal(r.queues.crossProfileTokenCollision,null);
    assert.equal(fs.readFileSync(f.file("say"),"utf8"),'{"PRIVATE_CORRUPT_PAYLOAD":');
    assert.doesNotMatch(JSON.stringify(r),/PRIVATE_CORRUPT_PAYLOAD/);
});

test("oversized journal is refused before parsing",t=>{
    const f=fixture(t);
    f.put(f.file("say"),Buffer.alloc(state.MAX_FILE+1,0x20));
    const r=f.report();
    assert.equal(r.status,"blocked");
    assert.equal(r.queues.profiles.say.state,"oversized");
    assert.throws(()=>state.readState(f.file("say")),/unsafe_or_oversized_delivery_journal/);
});

test("unfinished session and capacity pressure are actionable attention",t=>{
    const f=fixture(t);
    fs.mkdirSync(f.dir,{recursive:true});
    const store=state.createStore("say"),s=store.fresh();
    for(let i=0;i<store.MAX_SESSIONS-1;i++){
        const id=store.beginSession(s);store.completeSession(s,id,true,"fixture");
    }
    store.beginSession(s);
    store.writeState(f.file("say"),s);
    const r=f.report();
    assert.equal(r.status,"attention");
    assert.ok(codes(r).includes("capture_session_unfinished_or_active"));
    assert.ok(codes(r).includes("journal_capacity_reached"));
    assert.equal(r.queues.profiles.say.capacity.sessionsUsed,store.MAX_SESSIONS);
});

test("unsafe directory and journal path are blocked, not repaired",t=>{
    const f=fixture(t);
    f.put(f.dir,"PRIVATE_NOT_A_DIRECTORY");
    const r=f.report();
    assert.equal(r.status,"blocked");
    assert.equal(r.queues.directory,"unsafe");
    assert.equal(r.queues.profiles.say.state,"not_inspected");
    assert.throws(()=>state.readState(f.file("say")),/unsafe_state_directory/);
    fs.unlinkSync(f.dir);
    fs.mkdirSync(f.file("say"),{recursive:true});
    assert.equal(f.report().queues.profiles.say.state,"unsafe");
    assert.throws(()=>state.readState(f.file("say")),/unsafe_or_oversized_delivery_journal/);
});

test("bounded reader validates exact descriptor and rejects changed size",t=>{
    const f=fixture(t),file=path.join(f.base,"reader.txt");
    f.put(file,"abc");
    const seen=inspectPath(file);
    assert.equal(readBounded(file,3,seen).toString(),"abc");
    assert.throws(()=>readBounded(file,2),/file_over_budget/);
    f.put(file,"abcd");
    assert.throws(()=>readBounded(file,8,seen),/file_changed_during_read/);
});

test("aggregate suppresses cross-profile conclusions if the first journal changes during the second read",t=>{
    const f=fixture(t);
    f.seed("say","AABBCCDDEEFF");
    f.seed("public","112233445566");
    // Inject a controlled concurrent modification during the second profile's
    // read. A whitespace append preserves valid JSON but changes the first
    // file's metadata without changing its parent directory.
    const original=state.createStore;
    try {
        state.createStore=function(name) {
            const store=original(name);
            if(name==="public") {
                const read=store.readState;
                store.readState=file=>{
                    fs.appendFileSync(f.file("say")," ");
                    return read(file);
                };
            }
            return store;
        };
        const r=f.report();
        assert.equal(r.queues.changedDuringInspection,true);
        assert.equal(r.queues.profiles.say.state,"changed_during_inspection");
        assert.equal(r.queues.profiles.say.counts,undefined);
        assert.equal(r.queues.crossProfileTokenCollision,null);
        assert.equal(r.queues.simultaneousClaims,null);
        assert.ok(codes(r).includes("queue_changed_during_inspection"));
    } finally {
        state.createStore=original;
    }
});

test("dangling directory links cannot masquerade as absent journals",t=>{
    const f=fixture(t);
    const target=path.join(f.base,"link-target");
    fs.mkdirSync(target);
    fs.mkdirSync(f.dir,{recursive:true});
    fs.symlinkSync(target,f.file("say"),process.platform==="win32"?"junction":"dir");
    fs.rmdirSync(target);
    assert.equal(inspectPath(f.file("say")).state,"unsafe");
    assert.throws(()=>state.readState(f.file("say")),/unsafe_or_oversized_delivery_journal/);
    assert.throws(()=>state.writeState(f.file("say"),state.fresh()),/unsafe_existing_state_file/);
    const r=f.report();
    assert.equal(r.status,"blocked");
    assert.equal(r.queues.profiles.say.state,"unsafe");
});

test("CLI rejects unknown, duplicate, incomplete and relative arguments with redacted JSON",()=>{
    for(const args of [["--unknown","PRIVATE_ARGUMENT"],["--python","relative.exe"],
        ["--expect-host"],["--help","--help"],["--help","--expect-host","PRIVATE_HOST"]]) {
        const result=cli(args);
        assert.equal(result.status,64,result.stderr);
        const r=JSON.parse(result.stdout);
        assert.equal(r.schema,health.SCHEMA);
        assert.equal(r.status,"invalid_arguments");
        assert.equal(r.dispatchAuthorized,false);
        assert.doesNotMatch(result.stdout,/PRIVATE_ARGUMENT|PRIVATE_HOST/);
        assert.equal(result.stderr,"");
    }
});

test("CLI usage and blocked host are machine-readable without launching anything",()=>{
    const help=cli(["--help"]);
    assert.equal(help.status,0);
    assert.equal(JSON.parse(help.stdout).status,"usage");
    const wrong=cli(["--expect-host","NOT_THE_EXPECTED_HOST_PRIVATE"]);
    assert.equal(wrong.status,2,wrong.stderr);
    const report=JSON.parse(wrong.stdout);
    assert.equal(report.expectedHostMatched,false);
    assert.equal(report.readOnly,true);
    assert.equal(report.gameInputSent,false);
    assert.equal(report.dispatchAuthorized,false);
    assert.doesNotMatch(wrong.stdout,/NOT_THE_EXPECTED_HOST_PRIVATE/);
});
