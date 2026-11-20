# RCM session preflight and physical RIFT error-handler observation

**Date:** Friday, November 20, 2026 (America/New_York)
**Verified Windows machine:** AMD-DESKTOP
**Repository:** `C:\work\RiftChatModern`
**Installed game addon:** RCM v0.2.10 (on-disk SHA-256 verified in preceding checkpoint)
**Live-client acceptance:** blocked while the game process is absent

## Why this was needed

Previous RCM cycles used Windows desktop-window inventory results to infer that the physical `rift_x64` client was running. During this cycle an earlier inventory reported `rift_x64` PID `22532` and HWND `9965380`, but a separate local Windows `tasklist` query could not find that process, and Win32 `IsWindow` reported that the HWND was no longer valid.

A fresh desktop inventory subsequently showed the foreground **RIFT - Error Handler**, PID `21120` (class `#32770`), rather than the game. Independent Win32 process enumeration confirmed `rifterrorhandler_x64.exe` was present and `rift_x64.exe` was not. This explains the stale target identity and invalidates any prior assumption that the game remained running.

Read-only Win32 enumeration of the error dialog showed buttons labeled **Send report and restart the game**, **Send report and close**, and **Cancel**. No button was pressed, and no user input or game restart was issued.

Windows Application events 1000 and 1001 from the preceding three hours contained **no matching RIFT or Glyph crash entry under the applied filter**. This does not prove there was no crash report elsewhere or establish any crash cause. Nothing observed attributes the crash to RCM; the last RCM work involved host-only research tools.

## Real Documents and installation paths

Windows' User Shell Folders registry verified that Documents points to the user's **OneDrive\Documents** folder. The running error handler's actual executable path independently established the installed RIFT Live game directory under the Glyph Games RIFT Live tree.

**New primary evidence (12:31 PM ET):** The actual `%APPDATA%\RIFT\Rift.cfg` contains `[Client] DocumentsDirectory = C:/Users/mrkoo/OneDrive/Documents/RIFT`. RIFT 1.10 hotfix notes expressly identify this configuration key as the override for user-generated files, including screenshots, addons and combat logs: https://www.magelo.com/tw/forum/messages.jspa?topic=11024

The config also contains `LogConsole=False`, `LogCombatConsole=False`, `LogCombatConsoleExpanded=False`, and `CombatLogFileFlushInterval=0.500000`. These are **actual observed config values**. While the names are consistent with disabled logging, their precise runtime semantics and the current `/log` toggle state remain unverified. The file was read selectively and **not edited**. The preflight now reads only these whitelisted keys and checks the configured directory **before** fallback paths.

Read-only checks found **no existing `Log.txt` or `CombatLog.txt`** in the redirected Documents\RIFT location, the conventional local Documents\RIFT fallback, or the game executable directory. These findings establish missing files at those locations at the observed time; they do **not** prove RIFT's `/log` feature is broken or disabled.

The historical game patch note states that `/log` writes noncombat text to `Log.txt` alongside `CombatLog.txt`: https://arstechnica.com/civis/threads/rift-official-release-thread-ars-guild-info.1137621/page-4

## New read-only, repeatable diagnostic

`tools/rcm_session_preflight.py` is a standalone Windows Python utility that:
- Reads the RIFT client's own `[Client] DocumentsDirectory` setting from `%APPDATA%\RIFT\Rift.cfg` and uses it as the **primary** log directory before trying Windows Documents and bounded OneDrive fallbacks; outputs only whitelisted config values
- Enumerates exact `rift_x64.exe` and `rifterrorhandler_x64.exe` processes from local Windows `tasklist` CSV, not cached GUI metadata
- Uses limited-access Win32 process image queries to discover additional log-file candidate directories
- Optionally cross-checks an expected game PID and window HWND against the same live process list
- Checks **only file existence, size and modification time**, never chat-log contents
- Reports `game_process_present`, `game_process_absent`, `error_handler_only`, `game_plus_error_handler`, and multi-client states. Multiple concurrently running game processes require explicit matching PID/HWND before a target is considered selected
- Blocks unverified or mismatched targets and never asserts physical RCM startup, live player-chat reception, or automatic sending

From **Windows PowerShell**, in `C:\work\RiftChatModern`:

```powershell
& "C:\work\riftreader2\.venv\Scripts\python.exe" -B tools\rcm_session_preflight.py --expect-host AMD-DESKTOP
```

For a specific previously observed RIFT window and PID, append `--expected-pid 22532 --expected-hwnd 9965380`. When that window is stale, the tool rejects it and explains why. After a user-initiated game restart, use **fresh** identity values rather than reusing the example.

Exit codes: **0** means basic process/log prerequisites for a supervised investigation were detected; **2** means one or more blockers; **1** means the preflight could not run reliably. The `LogConsole=False` config value is reported as a **hint**, not a verified claim that current logging is off. Even exit code 0 is **not** evidence that the current addon is loaded, that the chat parser recognizes messages, or that the server delivered them. The output deliberately preserves these separate evidence levels.

## Acceptance criteria and further work

1. The user chooses whether to restart the game using the existing error dialog; RCM development tooling does not press the buttons or send native input.
2. Re-run `rcm_session_preflight.py` after the restart. Record a **fresh** exact game PID and HWND from independent sources. Verify the expected RCM startup line and `/rcm` UI in the physical client.
3. Establish the `/log` setting with direct game evidence before toggling it; entering `/log` is a toggle. Discover the exact `Log.txt` path.
4. Start the existing `rcm-chat-observer.cjs --sample-raw-lines 5` only after it has a plausible source; correlate a deliberately created RIFT chat line and/or exact `:logprobe TOKEN` with file receipts. A historical regex test is not a live observation.
5. After native player-chat reception is independently demonstrated, use the proven RCM manual host import and then plan automatic message delivery. Keep native chat intact until there is equivalent functionality.

**Validation:** 13/13 focused preflight fixture tests passed, including exact target identity, multibox ambiguity, configured document-path priority, whitelisted `Rift.cfg` keys, and `LogConsole=False` remaining a hint rather than native-log proof. The actual AMD-DESKTOP preflight returned exit code 2, correctly identifying the error handler and missing noncombat log file. This is an expected blocked result, not a test failure.

This is a **host tooling and research checkpoint**. The v0.2.10 Lua addon, `.toc`, SavedVariables, and installed game files have not been modified as part of this diagnostic. No new in-game release is required.

## Restart observation and preflight correction — 12:56 PM EST

A subsequent user-initiated restart produced a **new** physical RIFT process, PID `42992`, and game HWND `24252650`. Win32 `IsWindow` and `GetWindowThreadProcessId` independently matched the window to the running game. Windows process start times show both `rift_x64.exe` (42992) and the new `rifterrorhandler_x64.exe` (31856) started at **12:49:20 PM**, consistent with the error-handler process being launched as a companion. Its presence alone is **not proof of a new crash**. The previous error-handler-only observation remains a historical fact about the earlier, exited game session.

The current RIFT diagnostic log lists `Rift Chat Modern` in the addon-loading sequence and finishes with `Entering world (100% complete)` at about **12:50 PM EST**. No fatal/exception message appeared in that diagnostic log. This supports startup progression, not confirmation of RCM window rendering or all addon operations.

A bug was found in the **host-only** `rcm_session_preflight.py`: it incorrectly treated `game_plus_error_handler` as a missing active game. The corrected preflight regards one verified game plus its error-handler companion as a valid live process state, while still rejecting `error_handler_only` and requiring exact PID/HWND binding for multiple simultaneously running game clients. A specific `error_handler_companion_present_not_crash_evidence` hint was added. The fix does not start or focus RIFT.

The corrected preflight was run with `--expect-host AMD-DESKTOP --expected-pid 42992 --expected-hwnd 24252650`. It verified the new live game and window, and **only** reported `no_log_file_found_in_known_paths` as a blocker. The configured `LogConsole=False` remains a hint, not confirmed runtime logging state. **Do not confuse a blocked log test with a crashed game.**

The in-game addon remains v0.2.10; 10/10 installed files matched source by SHA-256 after the restart. The on-disk check alone does not prove `/rcm import` works in the physical game.

The remaining live acceptance steps are to inspect the RCM window and send a one-part `/rcm import` manually in RIFT's original chat input. Screenshot capture via WinApp remained blocked by `UI_TURN_BUSY`, so no visual UI acceptance was claimed.
