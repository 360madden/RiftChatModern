# RCM chat-source P0 — Correct the log probe's path-selection chain

**Date:** Friday, November 20, 2026 (America/New_York)  
**Verified machine:** AMD-DESKTOP  
**Repository:** C:\work\RiftChatModern  
**Type of change:** Windows host helper only; installed RIFT Lua addon remains v0.2.16

## Goal

Prove whether the current RIFT MMORPG client writes real Say, Guild, Party, Tell and public-channel chat to a local, noncombat **Log.txt**, with a physically correlated sample. A historical third-party RIFT log reader is a useful precedent, but the actual 2026 RIFT Live format is still unverified.

A log watcher that silently tails the wrong Documents folder is not credible physical evidence, even when its parser and tests work correctly.

## Root cause found

The earlier PowerShell entrypoint tools/rcm-log-probe.ps1 was still launching **LuaPadModern/tools/rift-log-probe.cjs directly**, using that generic reader's path selection and printing instructions about a LuaPad sample. However, RCM had since added its own tools/rcm-chat-observer.cjs, which already correctly prioritizes **RIFT's actual %APPDATA%\RIFT\Rift.cfg [Client] DocumentsDirectory** before any generic fallback. On AMD-DESKTOP, that game config points to the user's actual redirected OneDrive Documents/RIFT tree.

The old entrypoint could therefore run the wrong watcher/path logic, while the operator was expecting RCM's configured-path observer. This was a *tool wiring defect*, not evidence that RIFT's logging was broken.

## Root-level fix

The launcher now starts **RCM's own Node observer**. That observer internally **reuses LuaPadModern's established read-only LogTailProbe decoder**; no duplicate file-tailing engine was created, and the LuaPadModern repository was not modified.

- Dependencies are validated by exact local file existence: RCM observer, LuaPad decoder and node.exe.
- The observer reports its actual source path and selection evidence via JSON **started.path** and **started.pathSelection**. An explicit -LogPath still has priority.
- A new optional **-SampleRawLines N** (N=1..30; default 0) forwards to the observer's bounded raw-line discovery. It can reveal real chat text; this mode is never enabled by default.
- -Preview emits a structured RCM receipt only. It does not tail the file, launch RIFT, enter native chat, toggle /log, or change config.
- The existing strict nonce, absolute Log.txt filename, timeout and poll interval checks remain.
- Neither a successful call to Command.Console.Display nor a synthetic fixture establishes verified live social-chat reception.

## Red/green regression evidence

A new real-Windows-PowerShell fixture test initially failed because:
1. -SampleRawLines was unrecognized and the preview lacked the RCM observer path.
2. The old generic LuaPad watcher did not emit the required RCM-specific **started.pathSelection** during a bounded test.

The fixture itself initially wrote literal escaped newline characters to the synthetic Rift.cfg and was corrected to write an actual [Client] section. The final test runs against **Windows PowerShell 5.1** and launches the real Node observer with a **temporary, isolated Rift.cfg DocumentsDirectory**. It proved that the observer selected the fixture's configured Log.txt rather than a fallback and timed out correctly without creating a log file.

All **3/3** focused tests passed after the correction. They cover preview, explicit raw sampling, invalid nonce / relative path refusal, exact Rift.cfg priority, no game input, no log writes and bounded timeout.

## Operating procedure for the next supervised live test

Open **Windows PowerShell** on AMD-DESKTOP, change to C:\work\RiftChatModern, and first inspect the selected helper:

    .\tools\rcm-log-probe.ps1 -Preview -Nonce RCM_LOG_20261120

Once the user has intentionally started RIFT, confirmed that v0.2.16 loaded, and established the current logging state, run the normal bounded observer:

    .\tools\rcm-log-probe.ps1 -Nonce RCM_LOG_20261120 -TimeoutSeconds 120

Read the emitted **started.path**, **started.pathSelection**, and nonce before entering the matching **:logprobe RCM_LOG_20261120** in RCM's own in-game editor. The observer may time out if the file has not been created; this is an inconclusive transport test until the actual game logging state is established.

To investigate an *unknown* game-produced text format, request at most three newly appended decoded log lines deliberately:

    .\tools\rcm-log-probe.ps1 -Nonce RCM_RAW_20261120 -TimeoutSeconds 90 -SampleRawLines 3

**Raw line discovery can expose real/private chat messages.** Use it only intentionally, and do not include those lines in a public Git repository or status report. The default observer and launcher remain metadata-only.

**Do not blindly type /log.** In RIFT this is historically a toggle; first confirm whether logging is currently enabled. The last observed Rift.cfg contained LogConsole=False, but the precise relationship of that setting to live /log state is unproven.

## Evidence classification and next decision

- **Verified now:** RCM's Windows launcher uses the correctly configured observer, which reuses LuaPadModern's tested decoder; its source-selection and bounded timeout behavior passed an isolated real-process fixture on AMD-DESKTOP.
- **Not verified:** RIFT's current runtime /log state; existence of live Log.txt; physical player-chat lines, category labels and timing; automatic host-to-addon import; normal social-chat sending.
- **P0:** Start RIFT, establish one real game log record and compare it against the game window with a unique test line. Preserve timestamps and the selected path, and adjust the parser only from actual observed RIFT bytes. If no current social-log source is viable, investigate the already inventoried read-only external client inspection track rather than assuming the native RIFT addon API exposes general social transcript events.

References for historical provenance (not live 2026 proof):
- RIFT API listing: https://www.seebs.net/rift/pts/ (Event.Chat.Npc and Event.Chat.Notify are documented, not a generic player chat event).
- RIFT support chat guide: https://support.gamigo.com/en/support/solutions/articles/201000105472-rift-using-chat
- Historical log reader: https://github.com/Bamux/RiftEventTracker (documented /log → Log.txt workflow).

**Restrictions followed:** No Ollama or OpenCode, no direct game input, no RIFT configuration change, no character SavedVariables write and no unverified claim of native social-chat reception.
