r"""RCM read-only physical game + chat-log preflight (Windows, no dependencies).

Verify the RIFT process independently of cached desktop-window inventory.
Does not launch, inject, focus, capture, click, or alter RIFT or its log state.

Run in Windows PowerShell in C:\work\RiftChatModern:
  & "C:\work\riftreader2\.venv\Scripts\python.exe" -B tools\rcm_session_preflight.py --expect-host AMD-DESKTOP
"""
from __future__ import annotations
import argparse
import csv
import ctypes
from ctypes import wintypes
from datetime import datetime
import io
import json
import os
import re
from pathlib import Path
import socket
import subprocess
import sys

GAME="rift_x64.exe"
ERROR_HANDLER="rifterrorhandler_x64.exe"
MAX_FILES=16

def parse_tasklist(output: str) -> list[dict]:
    """Parse quoted tasklist CSV, not locale-dependent table columns."""
    if not isinstance(output,str) or len(output)>2_000_000:
        raise ValueError("invalid_tasklist_output")
    result=[]
    for row in csv.reader(io.StringIO(output)):
        if len(row)<2:continue
        name,pid=row[0].strip(),row[1].strip()
        if name.casefold() not in (GAME,ERROR_HANDLER):continue
        if not pid.isdigit():continue
        number=int(pid)
        if 0<number<2**32:
            result.append({"name":name.casefold(),"pid":number})
        if len(result)>32:raise ValueError("unexpected_process_count")
    return sorted(result,key=lambda row:(row["name"],row["pid"]))

def classify_processes(rows: list[dict]) -> str:
    names=[row["name"].casefold() for row in rows]
    games=names.count(GAME)
    error=ERROR_HANDLER in names
    if games>1 and error:return "multiple_games_plus_error_handler"
    if games>1:return "multiple_game_processes"
    if games and error:return "game_plus_error_handler"
    if games:return "game_process_present"
    if error:return "error_handler_only"
    return "game_process_absent"

def discover_shell_documents() -> tuple[Path|None,str]:
    if os.name!="nt":return None,"non_windows"
    try:
        import winreg
        key=r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,key) as handle:
            raw=winreg.QueryValueEx(handle,"Personal")[0]
        if isinstance(raw,str) and raw:
            return Path(os.path.expandvars(raw)),"registry_user_shell_folders"
    except (OSError,ValueError,TypeError):
        pass
    return None,"unavailable"

def parse_rift_client_settings(contents: str) -> dict:
    """Read only whitelisted [Client] values; never expose other config fields."""
    if not isinstance(contents,str) or len(contents)>512*1024:
        raise ValueError("invalid_config_source")
    section=""
    settings={}
    allowed={"DocumentsDirectory","LogConsole","LogCombatConsole",
             "LogCombatConsoleExpanded","CombatLogFileFlushInterval"}
    for line in contents.splitlines():
        header=re.match(r"^\s*\[([A-Za-z_0-9]+)\]\s*$",line)
        if header:
            section=header.group(1).casefold()
            continue
        item=re.match(r"^\s*([A-Za-z_][A-Za-z_0-9]*)\s*=\s*(.*?)\s*$",line)
        if section!="client" or not item or item.group(1) not in allowed:
            continue
        key,value=item.groups()
        if key=="DocumentsDirectory":
            parsed=os.path.expandvars(value.strip().strip('"'))
            if len(parsed)<=260 and Path(parsed).is_absolute():
                settings[key]=parsed
        elif key in ("LogConsole","LogCombatConsole","LogCombatConsoleExpanded"):
            if value.casefold() in ("true","false"):
                settings[key]=value.casefold()=="true"
        elif key=="CombatLogFileFlushInterval":
            if re.fullmatch(r"\d+(?:\.\d+)?",value):
                settings[key]=float(value)
    return settings

def read_rift_config(home:Path,env:dict) -> dict:
    """Read only recognized config keys; no edits or arbitrary-file searching."""
    roaming=env.get("APPDATA")
    path=(Path(roaming) if roaming else home/"AppData"/"Roaming")/"RIFT"/"Rift.cfg"
    state={"path":str(path),"exists":False,"settings":{},
           "logFlagSemanticsConfirmed":False}
    try:
        if not path.is_file():return state
        if path.stat().st_size>512*1024:
            state["readError"]="oversize"
            return state
        contents=path.read_text(encoding="utf-8-sig",errors="replace")
        state["exists"]=True
        state["settings"]=parse_rift_client_settings(contents)
    except (OSError,ValueError):
        state["readError"]="unavailable"
    return state

def candidate_log_paths(home:Path, documents:Path|None, env:dict, game_exes:list[str]|None=None,
                        configured_root:Path|None=None) -> list[Path]:
    """Bounded documented candidates. No recursive scanning or file reads."""
    doc_roots=[]
    if documents: doc_roots.append(documents)
    doc_roots.extend([home/"Documents",home/"OneDrive"/"Documents"])
    for key in ("OneDrive","OneDriveConsumer","OneDriveCommercial"):
        value=env.get(key)
        if value and Path(value).is_absolute():
            doc_roots.append(Path(value)/"Documents")
    roots=[]
    if configured_root and configured_root.is_absolute():
        roots.append(configured_root)
    roots.extend(d/"RIFT" for d in doc_roots)
    for exe in game_exes or []:
        if not exe:continue
        p=Path(exe)
        if p.is_absolute() and p.name.casefold() in (GAME,ERROR_HANDLER):
            roots.append(p.parent)
    files,seen=[],set()
    for root in roots:
        for name in ("Log.txt","CombatLog.txt"):
            file=root/name
            key=os.path.normcase(str(file)).casefold()
            if key not in seen:
                seen.add(key);files.append(file)
            if len(files)>=MAX_FILES:return files
    return files

def process_image(pid: int) -> tuple[str|None,str|None]:
    if os.name!="nt":return None,"non_windows"
    try:
        kernel=ctypes.WinDLL("kernel32",use_last_error=True)
        kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
        kernel.OpenProcess.restype=wintypes.HANDLE
        kernel.QueryFullProcessImageNameW.argtypes=[
            wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
        kernel.QueryFullProcessImageNameW.restype=wintypes.BOOL
        kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        kernel.CloseHandle.restype=wintypes.BOOL
        handle=kernel.OpenProcess(0x1000,False,pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:return None,"open_process_denied_or_missing"
        try:
            buf=ctypes.create_unicode_buffer(32768)
            n=wintypes.DWORD(len(buf))
            if kernel.QueryFullProcessImageNameW(handle,0,buf,ctypes.byref(n)):
                return buf.value,None
            return None,"image_query_failed"
        finally:
            kernel.CloseHandle(handle)
    except (OSError,AttributeError,TypeError,ValueError):
        return None,"image_query_unavailable"

def window_identity(hwnd:int|None) -> dict|None:
    if hwnd is None:return None
    if os.name!="nt":return {"hwnd":hwnd,"present":False,"pid":None,"reason":"non_windows"}
    try:
        user=ctypes.WinDLL("user32",use_last_error=True)
        user.IsWindow.argtypes=[wintypes.HWND];user.IsWindow.restype=wintypes.BOOL
        user.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
        user.GetWindowThreadProcessId.restype=wintypes.DWORD
        alive=bool(user.IsWindow(hwnd))
        pid=wintypes.DWORD(0)
        if alive:user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
        return {"hwnd":hwnd,"present":alive,"pid":pid.value if alive else None}
    except (OSError,AttributeError,ValueError):
        return {"hwnd":hwnd,"present":False,"pid":None,"reason":"win32_query_failed"}

def inspect_log_candidates(paths:list[Path]) -> list[dict]:
    rows=[]
    for path in paths[:MAX_FILES]:
        record={"path":str(path),"exists":False}
        try:
            if path.is_file():
                meta=path.stat()
                record.update({"exists":True,"bytes":meta.st_size,
                               "modifiedLocal":datetime.fromtimestamp(meta.st_mtime)
                                   .astimezone().isoformat()})
        except OSError as error:
            record["metadataError"]=type(error).__name__
        rows.append(record)
    return rows

def make_report(processes:list[dict],host:str,docs:Path|None,
                doc_source:str,candidates:list[Path],window:dict|None,
                expected_pid:int|None,expected_host:str|None,
                game_config:dict|None=None) -> dict:
    state=classify_processes(processes)
    active=[row["pid"] for row in processes if row["name"]==GAME]
    error=[row["pid"] for row in processes if row["name"]==ERROR_HANDLER]
    reasons=[]
    if expected_host and expected_host.casefold()!=host.casefold():
        reasons.append("unexpected_host")
    if expected_pid and expected_pid not in active:
        reasons.append("expected_game_pid_not_running")
    if window is not None and (not window["present"] or
            window["pid"] not in active or
            (expected_pid and window["pid"]!=expected_pid)):
        reasons.append("window_identity_mismatch")
    selected=bool(expected_pid and window and window.get("present")
                  and window.get("pid")==expected_pid and expected_pid in active)
    if state=="multiple_game_processes" and not selected:
        reasons.append("multiple_game_processes_require_exact_target")
    elif state not in ("game_process_present","multiple_game_processes"):
        reasons.append("no_unambiguous_active_game_process")
    files=inspect_log_candidates(candidates)
    settings=(game_config or {}).get("settings") or {}
    hints=[]
    if settings.get("LogConsole") is False:
        hints.append("rift_cfg_logconsole_false_observed_runtime_semantics_unverified")
    if not any(x["exists"] and Path(x["path"]).name.casefold()=="log.txt" for x in files):
        reasons.append("no_log_file_found_in_known_paths")
    return {
        "schema":"RCM_SESSION_PREFLIGHT_V1",
        "observedLocal":datetime.now().astimezone().isoformat(),
        "machine":host,"processState":state,
        "gamePids":active,"errorHandlerPids":error,
        "documentsFolder":str(docs) if docs else None,
        "documentsResolution":doc_source,
        "gameConfig":game_config or {"exists":False,"settings":{}},
        "hints":hints,
        "expectedWindow":window,
        "logCandidates":files,
        "canClaimLiveChatReception":False,
        "canClaimGameLoaded":False,
        "gameInputSent":False,"gameLoggingChanged":False,
        "readyForLiveChatAcceptance":False,
        "canAttemptSupervisedLogTest":not bool(reasons),
        "blockers":reasons,
    }

def run(argv:list[str]|None=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expect-host",default=None)
    parser.add_argument("--expected-pid",type=int,default=None)
    parser.add_argument("--expected-hwnd",type=int,default=None)
    args=parser.parse_args(argv)
    host=socket.gethostname()
    try:
        completed=subprocess.run(["tasklist.exe","/fo","csv","/nh"],
                                 capture_output=True,text=True,timeout=12,
                                 encoding="utf-8",errors="replace")
        if completed.returncode!=0:raise RuntimeError("tasklist_failed")
        processes=parse_tasklist(completed.stdout)
        docs,doc_source=discover_shell_documents()
        config=read_rift_config(Path.home(),os.environ)
        for row in processes:
            row["imagePath"],row["imageError"]=process_image(row["pid"])
        configured=config["settings"].get("DocumentsDirectory")
        paths=candidate_log_paths(
            Path.home(),docs,os.environ,
            [row["imagePath"] for row in processes if row["imagePath"]],
            Path(configured) if configured else None)
        window=window_identity(args.expected_hwnd)
        report=make_report(processes,host,docs,doc_source,paths,window,
                           args.expected_pid,args.expect_host,config)
        # Non-zero means unverified/preflight blocked; not a diagnosis.
        blocked=bool(report["blockers"])
        print(json.dumps(report,indent=2,ensure_ascii=False))
        return 2 if blocked else 0
    except (OSError,RuntimeError,ValueError) as error:
        print(json.dumps({"schema":"RCM_SESSION_PREFLIGHT_V1","machine":host,
            "status":"unavailable","reason":type(error).__name__,
            "gameInputSent":False,"canClaimLiveChatReception":False}))
        return 1

if __name__=="__main__":
    sys.exit(run())
