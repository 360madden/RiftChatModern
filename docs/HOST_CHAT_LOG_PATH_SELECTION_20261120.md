# RCM — Authoritative RIFT chat-log path selection

**Date:** Friday, November 20, 2026 (America/New_York)

**Machine verified:** AMD-DESKTOP

**Repository:** `C:\work\RiftChatModern`

**In-game addon release:** v0.2.10 (unchanged)

## Purpose

The Windows chat observer previously chose from generic OneDrive/Documents `Log.txt` locations. That could select an old log file from the wrong folder while RIFT's own `[Client] DocumentsDirectory` pointed somewhere else. This made a live chat-reception test unreliable, even if RIFT began logging.

The installed client's actual configuration was read-only verified at `%APPDATA%\RIFT\Rift.cfg`:

```ini
[Client]
DocumentsDirectory = C:/Users/mrkoo/OneDrive/Documents/RIFT
LogConsole = False
LogCombatConsole = False
LogCombatConsoleExpanded = False
CombatLogFileFlushInterval = 0.500000
```

**These are observed file values, not runtime proof of whether console logging is on.** The game remains stopped at its RIFT Error Handler, and no `Log.txt` has been observed at the configured path.

## Source changes

`tools/rcm-chat-observer.cjs` now reads only the bounded `Rift.cfg` file in the Windows user's roaming RIFT configuration directory, extracts the `DocumentsDirectory` value from its `[Client]` section, and uses `DocumentsDirectory\Log.txt` for the observer. It never modifies the configuration or enables `/log`.

Selection order:

1. Explicit CLI `--path C:\verified\RIFT\Log.txt` if supplied
2. `LUAPAD_LOG_CANDIDATES` override, if deliberately set
3. The game's own `[Client] DocumentsDirectory`
4. Bounded, previously supported Documents/OneDrive fallbacks if the game configuration is missing or invalid

When a valid game-configured path exists, the observer **does not silently replace it with a potentially stale fallback** simply because `Log.txt` has not been created yet. The existing LuaPadModern tailer waits for the configured file to appear. It starts from the beginning for a newly created file and skips pre-existing history in an already opened file.

The observer's `started` event now includes `pathSelection` with one of `explicit_path`, `luapad_override`, `rift_cfg_documents_directory`, or `generic_documents_fallback`, and the selected filename. These are selection facts, not claims of physical player-chat capture.

## Verified evidence

- **Live AMD-DESKTOP path selection:** a read-only local Node invocation returned `rift_cfg_documents_directory`, `C:\Users\mrkoo\OneDrive\Documents\RIFT\Log.txt`, and `exists=false`. No RIFT process or logfile was modified.
- **Full Windows observer smoke:** a one-second, bounded run emitted `started` with the same configured path and `pathSelection="rift_cfg_documents_directory"`. It ended with `finished: timeout`, zero candidate records and no marker match (exit code 2). This is the expected behavior while `Log.txt` is absent, not proof of a working physical game log.
- **Node.js test suite:** 27/27 tests passed. Three added tests validate configured-path priority over a stale fallback, malformed/missing/oversized configuration fallback, and a real child process recognizing a newly created synthetic file under the configured path *after* the observer has started.
- **Lua/Python test suite:** 129/129 passed; addon behavior, loader and deployment contracts unchanged.
- `git diff --check` passed with only normal Windows line-ending warnings.

The tests are synthetic and cannot establish a live game-produced chat record. The RIFT Error Handler is still open; the game is not active in the most recent independent session preflight.

## Physical test procedure once RIFT is running

From **Windows PowerShell**, in `C:\work\RiftChatModern`:

```powershell
node .\tools\rcm-chat-observer.cjs --sample-raw-lines 5 --timeout-ms 60000
```

The `started` event should identify `pathSelection: "rift_cfg_documents_directory"` and the actual configured file. With logging intentionally active and verified, create one known RIFT chat line **after** the watcher starts and compare the resulting `raw_log_sample` entry with the game. The command prints up to five raw decoded lines on explicit request; it does not save a transcript.

For a user-verified alternate path, specify `--path` instead. Do not blindly run `/log` because it is a toggle. Do not assume that a `LPB_PROBE` diagnostic marker equals ordinary player say/guild/tell capture.

**Next acceptance gates:** a restarted RIFT client, direct log creation and raw-line correlation, then physically tested `/rcm import` delivery. Automatic native social-chat mirroring remains unproven. No new `.toc` deployment is required for this Windows-only enhancement.
