"use strict";

// RCM companion health V1: a deliberately read-only, redacted inspection.
// No coordinator capture/claim/dispatch, no shell or subprocess, no lock
// acquisition, no creation/repair of a journal, no RIFT/Windows input.
// File availability is NOT executable qualification or game acceptance.
const fs=require("node:fs");
const path=require("node:path");
const os=require("node:os");
const crypto=require("node:crypto");
const state=require("./rcm-say-delivery-state.cjs");
const {resolveDotnet}=require("./rcm-dotnet-host.cjs");
const {inspectPath,comparable,readBounded}=require("./rcm-readonly-file.cjs");

const ROOT=path.resolve(__dirname,"..");
const SCHEMA="RCM_COMPANION_HEALTH_V1";
const BASELINE_DECODER="1ed80e2b43073a4d4d70a670a6fafa603616bbb68be842102fdf4ee5d1d7d399";
const MAX_DEPENDENCY=2*1024*1024;
const PROFILES=["say","public"];
const COUNTS=["queued","claimed","disk_saved","cancelled","quarantined"];

function parseArgs(argv) {
    const options={stateDir:path.join(ROOT,"artifacts","rcm-private-queue")};
    const seen=new Set();
    for(let i=0;i<argv.length;i++) {
        const name=argv[i];
        if(seen.has(name))throw Error("duplicate_option");
        seen.add(name);
        if(name==="--help") { options.help=true; continue; }
        if(!["--state-dir","--python","--expect-host"].includes(name))
            throw Error("unknown_option");
        const value=argv[++i];
        if(typeof value!=="string"||!value||value.startsWith("--")||
            value.length>4096||/[\x00-\x1f\x7f]/.test(value))
            throw Error("invalid_option_value");
        if(name==="--expect-host") {
            if(value.length>255)throw Error("invalid_expected_host");
            options.expectHost=value;
        } else {
            if(!path.isAbsolute(value))throw Error("absolute_path_required");
            options[name==="--state-dir"?"stateDir":"python"]=path.resolve(value);
        }
    }
    if(options.help&&seen.size!==1)throw Error("help_must_be_alone");
    return options;
}

function dependencyFile(file,hash=false) {
    const seen=inspectPath(file);
    if(seen.state!=="present")return {state:seen.state};
    if(!hash)return {state:"present"};
    if(seen.stat.size>BigInt(MAX_DEPENDENCY))return {state:"oversized"};
    try {
        const data=readBounded(file,MAX_DEPENDENCY,seen);
        return {state:"present",sha256:crypto.createHash("sha256").update(data).digest("hex")};
    } catch(e) { return {state:e.message==="file_changed_during_read"?"changed_during_read":"unreadable"}; }
}
function checkDependencies(root,python,env,platform) {
    const decoder=dependencyFile(path.resolve(root,"..","LuaPadModern","tools","rift-log-probe.cjs"),true);
    if(decoder.state==="present")decoder.matchesKnownBaseline=decoder.sha256===BASELINE_DECODER;
    let dotnet;
    try {
        dotnet={state:resolveDotnet({env,platform})?"present":"absent"};
    } catch(_) { dotnet={state:"invalid_override"}; }
    // Explicit interpreter is authoritative. Default is RCM's own .venv;
    // report availability only, not a guarantee that it can execute.
    const localPython=path.join(root,".venv",platform==="win32"?"Scripts":"bin",
        platform==="win32"?"python.exe":"python");
    const pythonFile=python||localPython;
    let pythonState;
    try {
        // venv/bin/python may legitimately be a symlink on POSIX.
        pythonState={state:fs.statSync(pythonFile).isFile()?"present":"unsafe"};
    } catch(e) { pythonState={state:e.code==="ENOENT"?"absent":"unreadable"}; }
    pythonState.source=python?"explicit":"project_venv";
    const sender=dependencyFile(path.join(root,"tools","RcmEditorSender","bin","Release",
        "net10.0-windows","RcmEditorSender.dll"));
    const auditor=dependencyFile(path.join(root,"tools","rcm_disk_receipt.py"));
    const manifest=dependencyFile(path.join(root,"addon","RiftChatModern","RiftAddon.toc"));
    const preflight=dependencyFile(path.join(root,"tools","rcm_session_preflight.py"));
    return {decoder,dotnet,python:pythonState,sender,auditor,manifest,preflight};
}

// Check file and lock metadata around bounded journal validation. No lock is
// taken: even a stable observation is NOT atomic and authorizes no input.
function inspectQueues(dir) {
    const beforeDir=inspectPath(dir,"directory");
    const result={directory:beforeDir.state,consistency:"not_atomic",
        globalLock:"not_inspected",profiles:{},crossProfileTokenCollision:null,
        simultaneousClaims:null,changedDuringInspection:false};
    if(!["present","absent"].includes(beforeDir.state)) {
        for(const name of PROFILES)result.profiles[name]={state:"not_inspected"};
        return result;
    }
    const global=path.join(dir,state.GLOBAL_EDITOR_LOCK);
    const beforeGlobal=inspectPath(global);
    result.globalLock=beforeGlobal.state;
    const journals={},observations=[];
    for(const name of PROFILES) {
        const store=state.createStore(name);
        const file=path.join(dir,store.profile.filename);
        const lock=file+".lock";
        const beforeFile=inspectPath(file),beforeLock=inspectPath(lock);
        observations.push({name,file,lock,beforeFile,beforeLock});
        const report={state:beforeFile.state,lock:beforeLock.state};
        result.profiles[name]=report;
        if(beforeFile.state==="present"&&beforeFile.stat.size>BigInt(store.MAX_FILE)) {
            report.state="oversized";
        } else if(["present","absent"].includes(beforeFile.state)) {
            try {
                const journal=beforeFile.state==="absent"?store.fresh():store.readState(file);
                const counts=Object.fromEntries(COUNTS.map(key=>[key,0]));
                const sessions={capturing:0,completed:0,failed:0};
                for(const entry of journal.entries)counts[entry.status]++;
                for(const session of journal.sessions)sessions[session.state]++;
                report.state=beforeFile.state==="present"?"valid":"absent";
                report.counts=counts;
                report.sessions=sessions;
                report.capacity={entriesUsed:journal.entries.length,entryLimit:store.MAX_ENTRIES,
                    sessionsUsed:journal.sessions.length,sessionLimit:store.MAX_SESSIONS};
                journals[name]=journal;
            } catch(_) {
                // Never propagate arbitrary parser/OS messages, session
                // reasons, tokens, wire bytes or user paths into health output.
                report.state="invalid_or_unreadable";
            }
        }
    }
    // Recheck BOTH profiles after all journal reads, not just immediately
    // after each one. This catches many intervening changes to the first
    // journal while the second is being inspected. It is still best effort.
    for(const {name,file,lock,beforeFile,beforeLock} of observations) {
        if(!comparable(beforeFile,inspectPath(file))||
           !comparable(beforeLock,inspectPath(lock))) {
            const report=result.profiles[name];
            report.state="changed_during_inspection";
            delete report.counts;delete report.sessions;delete report.capacity;
            delete journals[name];
            result.changedDuringInspection=true;
        }
    }
    if(!comparable(beforeGlobal,inspectPath(global))||
       !comparable(beforeDir,inspectPath(dir,"directory"))) {
        result.changedDuringInspection=true;
    }
    if(!result.changedDuringInspection&&journals.say&&journals.public) {
        const sayTokens=new Set(journals.say.entries.map(e=>e.token));
        result.crossProfileTokenCollision=journals.public.entries.some(e=>sayTokens.has(e.token));
        result.simultaneousClaims=PROFILES.every(name=>
            journals[name].entries.some(e=>e.status==="claimed"));
    }
    return result;
}

function collectHealth(options={}, {root=ROOT,env=process.env,platform=process.platform,
    hostname=os.hostname()}={}) {
    const issues=[];
    const issue=(severity,code,component)=>issues.push({severity,code,component});
    const hostMatch=options.expectHost==null?null:
        options.expectHost.toLowerCase()===hostname.toLowerCase();
    if(hostMatch===false)issue("blocked","expected_host_mismatch","host");
    const dependencies=checkDependencies(root,options.python,env,platform);
    for(const [key,value] of Object.entries(dependencies)) {
        if(value.state!=="present")issue("blocked","dependency_"+value.state,key);
    }
    if(dependencies.decoder.state==="present"&&!dependencies.decoder.matchesKnownBaseline)
        issue("attention","decoder_differs_from_qualified_baseline","decoder");
    if(platform!=="win32")issue("blocked","windows_sender_requires_windows","host");

    const queues=inspectQueues(options.stateDir||path.join(root,"artifacts","rcm-private-queue"));
    if(!["present","absent"].includes(queues.directory))
        issue("blocked","unsafe_or_unreadable_queue_directory","queues");
    if(queues.changedDuringInspection)
        issue("attention","queue_changed_during_inspection","queues");
    if(queues.globalLock==="present")issue("attention","global_editor_lock_present","queues");
    else if(!["absent","not_inspected"].includes(queues.globalLock))
        issue("blocked","unsafe_or_unreadable_global_lock","queues");
    for(const name of PROFILES) {
        const p=queues.profiles[name];
        if(!["valid","absent","not_inspected","changed_during_inspection"].includes(p.state))
            issue("blocked","journal_"+p.state,name);
        if(p.lock==="present")issue("attention","profile_lock_present",name);
        else if(p.lock&&!["absent"].includes(p.lock))
            issue("blocked","unsafe_or_unreadable_profile_lock",name);
        if(p.counts) {
            if(p.counts.claimed)issue("attention","unresolved_claim_do_not_retry",name);
            if(p.counts.queued)issue("attention","queued_transfers_present",name);
            if(p.counts.quarantined)issue("attention","quarantined_transfers_present",name);
        }
        if(p.sessions&&p.sessions.capturing)
            issue("attention","capture_session_unfinished_or_active",name);
        if(p.capacity&&(p.capacity.entriesUsed>=p.capacity.entryLimit||
            p.capacity.sessionsUsed>=p.capacity.sessionLimit))
            issue("attention","journal_capacity_reached",name);
    }
    if(queues.crossProfileTokenCollision===true)
        issue("blocked","cross_profile_token_collision","queues");
    if(queues.simultaneousClaims===true)
        issue("blocked","simultaneous_claims_across_profiles","queues");
    const outcome=issues.some(i=>i.severity==="blocked")?"blocked":
        issues.length?"attention":"offline_checks_passed";
    return {schema:SCHEMA,status:outcome,expectedHostMatched:hostMatch,
        dependencies,queues,issues,readOnly:true,pathsEmitted:false,messageTextEmitted:false,
        transferTokensEmitted:false,subprocessesStarted:false,gameInputSent:false,
        gameSessionVerified:false,installedAddonVerified:false,dispatchAuthorized:false,
        diskPersistenceVerifiedByThisCheck:false};
}
function run(argv=process.argv.slice(2),emit=value=>process.stdout.write(JSON.stringify(value)+"\n")) {
    let options;
    try { options=parseArgs(argv); }
    catch(e) {
        emit({schema:SCHEMA,status:"invalid_arguments",code:e.message,
            messageTextEmitted:false,gameInputSent:false,dispatchAuthorized:false});
        return 64;
    }
    if(options.help) {
        emit({schema:SCHEMA,status:"usage",
            usage:"node tools/rcm-companion-health.cjs [--state-dir ABSOLUTE_DIRECTORY] [--python ABSOLUTE_EXECUTABLE] [--expect-host HOST]",
            exitCodes:{"0":"offline_checks_passed","1":"attention","2":"blocked","64":"invalid_arguments"},
            dispatchAuthorized:false});
        return 0;
    }
    let report;
    try { report=collectHealth(options); }
    catch(_) {
        emit({schema:SCHEMA,status:"blocked",issues:[{severity:"blocked",
            code:"inspection_failed",component:"health"}],readOnly:true,
            messageTextEmitted:false,gameInputSent:false,dispatchAuthorized:false});
        return 2;
    }
    emit(report);
    return report.status==="blocked"?2:report.status==="attention"?1:0;
}
if(require.main===module)process.exitCode=run();
module.exports={SCHEMA,parseArgs,inspectQueues,checkDependencies,collectHealth,run};
