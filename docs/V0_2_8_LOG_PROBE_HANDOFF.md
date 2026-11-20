# RCM v0.2.8 — Controlled Log.txt feasibility probe and host watcher reuse

**Date:** Friday, November 20, 2026 (America/New_York)  
**Machine verified:** AMD-DESKTOP  
**Repository:** `C:\work\RiftChatModern`  
**Physical addon:** `C:\Users\mrkoo\OneDrive\Documents\RIFT\Interface\AddOns\RiftChatModern`  
**Dependency used, not modified:** `C:\work\LuaPadModern\tools\rift-log-probe.cjs`

## Why this exists

The core RCM objective remains genuine player social-chat capture and eventual send behavior, while providing reusable diagnostics for other repositories. The documented RIFT Lua addon API does not offer a proven general player-chat transcript reader or unrestricted social-chat sender. RIFT's historical noncombat `/log` facility provides a candidate game-to-Windows output path. It is not yet verified in today's physical RIFT client; the current candidate paths were absent when checked.

v0.2.8 adds **the missing RCM-owned sender half of a bounded experiment**, without duplicating the existing LuaPadModern read-only Windows watcher.

## In-game addon change

RCM's local editor accepts:

```text
:logprobe RCM_TEST_20261120
```

The command validates 8–80 ASCII nonce characters (`A-Z a-z 0-9 _ -`) and calls the documented RIFT API `Command.Console.Display("general", false, marker, false)` with this text:

```text
LPB_PROBE|RCM_TEST_20261120|<server Unix seconds or unknown>
```

This marker format is exactly what `LuaPadModern/tools/rift-log-probe.cjs` already recognizes. RCM does **not** turn on `/log`, start processes, write external files, or transmit ordinary social chat. A no-exception console call is **not** evidence that `Log.txt` received it. The user-facing command response states that clearly. `GetStatus()` now exposes `logProbeAvailable` and always reports `logProbeTransportVerified=false` until an independently verified live delivery is designed and proven.

The addon manifest remains five startup scripts with Email metadata, Lua 5.1, `Environment = "4.3"`, and the existing character SavedVariables schema. The public interface version remains 1.

## Windows helper: reuse rather than reimplementation

`tools/rcm-log-probe.ps1` supports Windows PowerShell 5.1 and PowerShell 7. It calls the already-tested LuaPadModern Node watcher with the matching nonce and bounded timeouts. It does not implement its own polling, parsing, file reading, game UI interaction, logging toggle, or background service.

In **Windows PowerShell** opened at `C:\work\RiftChatModern`, run a non-invasive preview:

```powershell
.\tools\rcm-log-probe.ps1 -Preview -Nonce RCM_TEST_20261120
```

When ready for a deliberately coordinated live test:

1. Check whether RIFT `/log` is already enabled before using it. **Typing `/log` toggles its state**; do not toggle blindly. If the file path is custom, find the verified `Log.txt`.
2. Ensure the latest RCM build is loaded in-game with an intentional `/reloadui`, and open `/rcm`.
3. In Windows PowerShell, run `.\tools\rcm-log-probe.ps1 -Nonce RCM_TEST_20261120 -TimeoutSeconds 120`. Optionally specify `-LogPath "C:\exact\path\Log.txt"`.
4. **After the watcher is running**, focus RCM's own editor and enter `:logprobe RCM_TEST_20261120`. Ignore the LuaPad sample snippet printed by the reused watcher; this is the RCM-specific pilot.
5. Look for an independently emitted exact `matched` receipt from the Windows watcher. Record path, observed time and appended bytes. The included server-clock delta is **not true flush latency**, since clocks may not agree. A timeout without confirmed log state is inconclusive.
6. Repeat with different nonces and a real, known player-chat line before claiming ordinary social-chat reception. The nonce probe proves only **console output** reaches the file, not that say/guild/tell/party messages do.

Do not replace Windows clipboard data, mutate SavedVariables, or read private chat logs during previews.

## Tested evidence and failures

- **87/87 Lua 5.1 tests passed** after adding four log-probe specific tests. These verify successful marker formatting, invalid token refusals, missing/throwing RIFT console API behavior and a missing server clock fallback.
- A separate direct Node smoke used the **real** `LuaPadModern LogTailProbe.readLine` implementation against a *synthetic string*. It returned the expected matched nonce. No game logfile was read, and the test did not prove real RIFT logging.
- The first launcher preview tried `pwsh.exe` and could not find an executable in Workbridge's direct execution environment. Live inspection found Windows PowerShell at `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe`. The helper was changed for compatibility; its PowerShell 5.1 preview subsequently **passed** with a structured receipt.
- Two negative PowerShell 5.1 preview tests rejected an invalid nonce and a relative log path with exit code 1, as designed. No watcher started in these tests.
- `Log.txt` and `CombatLog.txt` were absent from the common OneDrive and local Documents RIFT folders on AMD-DESKTOP during the November 20 preflight. The live game client's `/log` state is unknown. No in-game acceptance, live disk receipt, or actual player-chat acquisition has yet occurred.
- **Physical addon file deployment, 10:56 AM ET:** The host-verified copy changed only `Core.lua`, `Main.lua` and `RiftAddon.toc`, preserving the other six existing files. All **9/9 source-to-install SHA-256 checks matched** with no errors. The manifest's Email, version 0.2.8, SavedVariables and five RunOnStartup scripts were confirmed. No SavedVariables, unrelated addons or native game settings were altered. Deployment does not imply that the running client loaded v0.2.8.

## Next engineering steps

1. Independently verify a physical `Log.txt` receipt using matching RCM/Windows nonces with RIFT logging deliberately enabled.
2. Determine which actual player-chat categories the RIFT log stores and whether existing LogTailProbe-based parsing can extract them without losing sender, channel, timestamp or UTF-8 fidelity.
3. Design a separately proven Windows-host-to-RCM ingestion route. A working Windows watcher alone cannot deliver new lines to Lua code in-game.
4. Prove native send separately. `Command.Message.Send` carries **addon-specific data**, not ordinary player social chat.
5. Keep the native chat fallback until both reception and sending are independently verified in the physical game.

## Source references

- RIFT historical documented console command API: https://github-wiki-see.page/m/chrisbecke/Igor/wiki/Commands
- RIFT log tool precedent: https://github.com/Bamux/RiftEventTracker
- Reused watcher source: `C:\work\LuaPadModern\tools\rift-log-probe.cjs`
- Previous checkpoint: [v0.2.7 native-console discovery](V0_2_7_NATIVE_CHANNEL_DISCOVERY.md)
