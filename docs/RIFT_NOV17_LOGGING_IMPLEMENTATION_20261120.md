# RCM P0 — November 17 RIFT Live noncombat logging implementation

**Research date:** Friday, November 20, 2026 (America/New_York)  
**Verified host:** AMD-DESKTOP  
**Project:** C:\work\RiftChatModern  
**Scope:** read-only investigation of the locally installed RIFT MMORPG client, not a game session or a chat capture.

## Current exact client identity

The actual installed game was found using the Windows uninstall registry entry for RIFT and an independently verified pathname under Glyph.

- Executable: C:\Program Files (x86)\Glyph\Games\RIFT\Live\rift_x64.exe
- Size: **60,574,536 bytes**
- SHA-256: **df954b798331e18359be62a31cc74b49fc3f50b87385ebb080a5448256322c01**
- Last modified, local: **November 17, 2026, 9:10:53 AM EST**
- PE architecture: 64-bit AMD64, image base **0x140000000**
- Toolchain: the **existing RRE virtual environment** with pefile 2024.8.26 and Capstone 5.0.7, not a new package installation. .pdata, .rdata and .text were read from the original executable; no process memory, client state, game code or PE bytes were modified.

The previous October/early-November research often used a **different executable** (60,493,640 bytes and SHA beginning 1935A05C). Its offsets and function claims must **not** be used as this November 17 build's evidence.

## Original client settings and local status

The current file at %APPDATA%\RIFT\Rift.cfg contains the actual [Client] settings:

    DocumentsDirectory = C:/Users/mrkoo/OneDrive/Documents/RIFT
    LogConsole = False

The configured noncombat log destination is consequently:

    C:\Users\mrkoo\OneDrive\Documents\RIFT\Log.txt

That file did **not exist** in the read-only AMD-DESKTOP check, and no rift_x64.exe process was running. A persisted config value is not an independent measurement of RIFT's current in-memory toggle state when the game is running.

## Static evidence: logging is implemented in this exact build

The evidence goes beyond merely finding strings:

| Source RVA | Verified observation |
| --- | --- |
| 0x26C9378 | UTF-16 literal **LogConsole** (direct RIP-relative LEA references at 0x707A11 and 0x707A2C) |
| 0x707600–0x707A8A | Configuration/constructor function. At 0x707A0E it passes false as default; 0x707A1D calls the bool-read helper; 0x707A26 stores its result to object +0x101; a later conditional invokes logging initialization |
| 0x706540 | The bool-read helper; the caller passes the LogConsole key and r8d=0 |
| 0x706820 | Companion config helper invoked with the parsed bool; its exact persistence semantics are not fully established |
| 0x711E80–0x711F9E | Noncombat log open/close implementation. Tracks the file pointer at object +0xF8 and an enable flag at +0x100. The path construction uses a wide literal **{0}\Log.txt** at RVA 0x26CA200 |
| 0x711F15 / 0x711F1F | Loads mode **a** at RVA 0x26C9104 and calls imported CRT **api-ms-win-crt-stdio-l1-1-0.dll!_wfopen** to open the file for appending |
| 0x711ED0 | Calls imported CRT **fclose** when disabling the active file stream |
| 0x7138C0–0x71390D | A separate toggle routine: if logging is active, closes the file and clears +0xF8; otherwise invokes 0x711E80 with true. Called from RVA **0x6C3213** |
| 0x6C31D0–0x6C34AB | Caller of the toggle routine. Its conditional output branches reference literal text **Noncombat logging enabled** and **Noncombat logging disabled** at RVAs 0x26C4300 / 0x26C4320 |

This exact current-build control flow establishes a real, toggleable client file-logging implementation, not just a leftover string or old manual. The historical **/log** command is a strong candidate for the runtime entrypoint, but the present source-only trace does not independently prove the current slash-command dispatch registration, the present UI behavior, or whether chat channels make it into the file. Those questions still require physical RIFT acceptance.

The code also has an independent LogCombatConsole path; that setting and CombatLog.txt are **not** substitutes for the noncombat Log.txt target.

## Resulting host-observer code correction

Previously the observer selected a sensible Log.txt path but **did not surface the persisted LogConsole flag**, making a stalled test ambiguous.

RCM now uses one bounded, read-only **readRiftClientConfig()** function in tools/rcm-chat-observer.cjs to inspect only the [Client] DocumentsDirectory and LogConsole values. The original configured-path selection behavior remains unchanged. At startup the observer's JSONL **started** receipt adds:

- persistedLogConsole: true, false or null (unknown)
- configReadable: whether a bounded Rift.cfg was read
- runtimeLoggingEnabledVerified: **always false**
- loggingReadinessHint: a careful warning when persisted LogConsole=False; no automatic toggle or configuration edit

The unchanged readConfiguredLogPath() and resolveLogSelection() consumer interfaces still work, and a provided explicit log path or LuaPad test override retains its prior priority. The only direct effect is a more informative observer receipt; the original RIFT client and character files remain untouched.

The actual read-only host check with this new parser yielded:

    machine = AMD-DESKTOP
    configReadable = true
    persistedLogConsole = false
    runtimeLoggingEnabledVerified = false
    source = rift_cfg_documents_directory
    noncombatFileExists = false
    configChanges = false
    gameInputSent = false

## Red/green evidence

Two new/extended regression fixtures initially failed:
1. The Node config consumer lacked readRiftClientConfig and could not distinguish a persisted false flag from live game state.
2. The child-process observer's started record lacked the persistedLogConsole=false and runtimeLoggingEnabledVerified=false fields, even with a real temporary Rift.cfg.

After the correction, both suites passed. Cases include true, false, invalid and missing LogConsole values, [Other] section isolation, reading the redirected DocumentsDirectory, and a real Node file watcher observing a test Log.txt that is created later. No unrelated content in Rift.cfg is emitted. The persisted false flag does **not** block the observer if real new bytes still arrive, since the runtime state may differ from the saved configuration.

**Verification complete:** The full tests passed **193/193 Python/Lua** and **41/41 Node.js** cases (**234 total**). `git diff --check` exited **0**, with only normal Windows LF-to-CRLF notices. A guarded dry run independently confirmed that **10/10 installed v0.2.16 addon files match source** and there are **zero pending deployment changes**. No Lua addon redeployment was needed.

A separate **real read-only observer invocation** on AMD-DESKTOP, with a one-second bound, emitted `started.persistedLogConsole=false`, `configReadable=true`, `runtimeLoggingEnabledVerified=false`, and `pathSelection=rift_cfg_documents_directory` for the exact OneDrive Log.txt path. It then correctly exited **2** with `finished.reason=timeout`, `probeMatched=false` and zero chat candidates, because RIFT was closed and no log file was present. This is a correct *unavailable* result, not a failed player-chat source verification.

## Physical acceptance and configuration-change boundary

When the game is launched intentionally, verify the current process/window and actual logging state. The current code strongly suggests that a persisted LogConsole=False normally disables logging on startup, but the exact live condition must be checked. **Do not blindly type /log**, because the toggle can also disable an already-running log.

Enabling noncombat logging would **change a game setting and write in-game console/chat history to disk**, possibly including private messages. This investigation intentionally made **no config edit, /log invocation, game launch, clipboard change or game input**. Once the user deliberately enables logging, run the supervised marker + exact-chat test already provided in docs/EXACT_CHAT_TEXT_PROOF_20261120.md, then use its fresh real output as the basis for any parser adjustments or automatic host-to-addon bridge.

No Ollama, OpenCode, Codex CLI, full Ghidra PE import, or claimed internal subagent was used. The static findings are pinned to the above exact executable SHA and must be requalified after the next patch.
