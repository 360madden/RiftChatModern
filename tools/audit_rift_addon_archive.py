"""Static, read-only audit of RIFT MMO addon ZIPs; no extraction/execution."""
from __future__ import annotations
import argparse, hashlib, json, re, stat, sys, zipfile
from pathlib import Path, PurePosixPath

MAX_ARCHIVE, MAX_MEMBERS, MAX_INFLATED, MAX_MEMBER = 8*1024*1024, 500, 24*1024*1024, 4*1024*1024
RIFT = {
    "UI.CreateFrame": r"\bUI\.CreateFrame\s*\(",
    "Command.Event.Attach": r"\bCommand\.Event\.Attach\s*\(",
    "Command.Slash.Register": r"\bCommand\.Slash\.Register\s*\(",
    "Event.Chat": r"\bEvent\.Chat\.",
    "Inspect.Console": r"\bInspect\.Console\.",
    "Command.Console": r"\bCommand\.Console\.",
}
WOW = {
    "DEFAULT_CHAT_FRAME": r"\bDEFAULT_CHAT_FRAME\b",
    "CHAT_MSG": r"\bCHAT_MSG_[A-Z_]+\b",
    "ChatEdit": r"\b(?:ChatFrame1EditBox|ChatEdit_SendText)\b",
    "RegisterEvent": r"\bRegisterEvent\s*\(\s*[\"'](?:CHAT_MSG_|GUILD_ROSTER_UPDATE|ADDON_LOADED)",
    "CreateFrame": r"(?<![.\w])CreateFrame\s*\(",
    "StaticPopup": r"\b(?:StaticPopup_Show|StaticPopupDialogs)\b",
}

class AuditError(ValueError): pass

def members(z):
    infos = z.infolist()
    if len(infos) > MAX_MEMBERS: raise AuditError("too_many_entries")
    seen, total = {}, 0
    for f in infos:
        name = f.filename.replace("\\", "/")
        if (not name or name.startswith("/") or re.match(r"^[A-Za-z]:",name)
                or ".." in PurePosixPath(name).parts or "\0" in name):
            raise AuditError("unsafe_path")
        if stat.S_IFMT(f.external_attr >> 16) == stat.S_IFLNK:
            raise AuditError("symlink")
        total += f.file_size
        if f.file_size > MAX_MEMBER or total > MAX_INFLATED:
            raise AuditError("oversized_zip_contents")
        if name.casefold() in seen:
            raise AuditError("ambiguous_case_insensitive_names")
        if not f.is_dir(): seen[name.casefold()] = f
    return seen

def field(text, key):
    match = re.search(rf'(?m)^\s*{re.escape(key)}\s*=\s*"([^"\r\n]+)"',text)
    return match.group(1) if match else None

def compile_lua(source):
    try: from lupa.lua51 import LuaRuntime
    except ImportError: return None, "Lua51 parser unavailable"
    try: outcome = LuaRuntime(unpack_returned_tuples=True).eval("loadstring")(source)
    except Exception as err: return False, str(err)[:180]
    if callable(outcome): return True, None
    return False, str(outcome[1] if isinstance(outcome, tuple) and len(outcome)>1 else outcome)[:180]

def inspect_archive(path: Path):
    if not path.is_file() or path.stat().st_size > MAX_ARCHIVE:
        raise AuditError("missing_or_oversize_archive")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    try: z = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as err: raise AuditError("invalid_zip") from err
    with z:
        entries = members(z)
        tocs = [m for name,m in entries.items() if name == "riftaddon.toc" or name.endswith("/riftaddon.toc")]
        if len(tocs) != 1: raise AuditError("expected_one_riftaddon_toc")
        toc = tocs[0]
        toc_name = toc.filename.replace("\\", "/")
        base = toc_name[:-len("RiftAddon.toc")]
        manifest = z.read(toc).decode("utf-8-sig","replace")
        start = re.search(r"RunOnStartup\s*=\s*\{([^}]*)\}",manifest,re.S)
        declared = re.findall(r'"([^"]+)"',start.group(1)) if start else []
        missing, actual, case_diffs, syntax = [],[],[],[]
        for item in declared:
            expected = base + item.replace("\\", "/")
            member = entries.get(expected.casefold())
            if not member:
                missing.append(item); continue
            name = member.filename.replace("\\", "/")
            actual.append(name)
            if expected != name: case_diffs.append(item)
            ok, error = compile_lua(z.read(member).decode("utf-8-sig","replace"))
            syntax.append({"file":item,"lua51SyntaxOnly":ok,"error":error})
        authored = [m for name,m in entries.items() if
            name.startswith(base.casefold()) and name.endswith(".lua") and not
            any("/"+p+"/" in name for p in ("libs","skins","locale","localization"))]
        counts = {}
        examples = {}
        for label, pattern in {**RIFT, **WOW}.items():
            compiled = re.compile(pattern)
            hits = [m.filename for m in authored
                    if compiled.search(z.read(m).decode("utf-8-sig","replace"))]
            counts[label] = len(hits)
            if hits: examples[label]=hits[0]
        wow_xml = sum(1 for name,m in entries.items()
            if name.startswith(base.casefold()) and name.endswith(".xml")
            and b"blizzard.com/wow/ui" in z.read(m).lower())
        rift_hits=sum(counts[x] for x in RIFT)
        wow_hits=sum(counts[x] for x in WOW)+wow_xml
        if not declared or missing or any(x["lua51SyntaxOnly"] is False for x in syntax):
            verdict="manifest_or_compile_blocker"
        elif wow_hits>=2 and rift_hits==0: verdict="wow_api_dominant_no_rift_runtime_evidence"
        elif rift_hits>0 and wow_hits==0: verdict="rift_api_candidate_needs_live_test"
        else: verdict="indeterminate_needs_manual_review"
        return {"schema":"RCM_REFERENCE_AUDIT_V1","source":str(path),"sha256":digest,
            "identifier":field(manifest,"Identifier"),"name":field(manifest,"Name"),
            "version":field(manifest,"Version"),"environment":field(manifest,"Environment"),
            "toc":toc_name,"runOnStartup":declared,"startupFilesFound":actual,
            "missingStartupFiles":missing,"caseMismatchWindowsMayResolve":case_diffs,
            "lua51SyntaxOnly":syntax,"firstPartyLuaFiles":len(authored),
            "riftApiFileHits":rift_hits,"wowApiFileAndXmlHits":wow_hits,
            "markerCounts":counts,"markerExampleFiles":examples,"wowUiXmlFiles":wow_xml,
            "verdict":verdict,"physicalRiftCompatibilityVerified":False,
            "nativePlayerChatReceptionVerified":False,"addonCodeExecuted":False,
            "gameFilesTouched":False}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive",type=Path)
    args=parser.parse_args(argv)
    try: result=inspect_archive(args.archive)
    except AuditError as e:
        print(json.dumps({"success":False,"reason":str(e),"gameFilesTouched":False}))
        return 1
    print(json.dumps(result,indent=2,ensure_ascii=False))
    return 0

if __name__=="__main__":
    sys.exit(main())
