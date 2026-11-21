# RCM v0.2.14 — Exact saved-state changes and live-client deployment guard

**Date:** Friday, November 20, 2026 (America/New_York)  
**Verified host:** AMD-DESKTOP  
**Repository:** `C:\work\RiftChatModern`  
**Addon source version:** `0.2.14`  
**RIFT Lua:** 5.1; addon `Environment = "4.3"`  
**Compatibility:** SavedVariables `schemaVersion = 2`, public `interfaceVersion = 2` (both unchanged)

## Why another correction was needed

The previous `pendingSessionChanges` feature counts actual saved-state mutations after a RIFT `Save.Begin` receipt. A review found that `Core.lua` advanced the revision even when `setFilter` selected the already-active, already-persisted filter; `setSearch` stored the identical query; or `clear` cleared already-empty history. In the actual UI, repeated tab clicks and RESET could cause false-positive pending changes, reducing the checkpoint indicator's reliability.

**Source correction:** `setFilter` and `setSearch` now compare both the live model field and the serialized SavedVariables field with the requested value before advancing the revision. This matters for a missing/invalid persisted default: the first material repair remains a genuine pending change. `clear` returns successfully without a revision change when history is already empty. Existing updates to nonempty history, new queries, changed filters, messages, and geometry still mark saved state dirty.

Two new Lua 5.1 regression tests cover the model and the real mocked UI tab/RESET callback sequence. The model test **failed against the old Core implementation** and passed once the code was corrected. UI clicks are tested after staging a RIFT Save.Begin receipt; a genuinely changed tab still marks pending changes.

## Deployment root cause

The guarded installer already checked host identity, manifest order, backups, rollback, and installed-file hashes, but a successful `--apply` was still permitted **while `rift_x64.exe` was running**. Prior notes instructed the operator to check the game process manually, which left an avoidable dependency on perfect operator sequencing.

**Code correction:** `tools/deploy_rcm.py` now uses Windows `tasklist.exe /fo csv /nh`, parsed by the shared `rcm_session_preflight.parse_tasklist`, immediately before any `--apply` file copy:

- Any actual `rift_x64.exe` PID refuses deployment with a clear error.
- An inaccessible, empty, failed, or unparseable process query refuses deployment rather than inferring the game is closed. A raw `rift_x64.exe` entry with malformed PID also fails closed.
- `rifterrorhandler_x64.exe` by itself does **not** count as a live game.
- Dry run remains read-only and explicitly reports `gameProcessCheck: not_checked`; a safe completed apply reports `gameProcessCheck: closed`.
- Existing exact-host, manifest, SHA-256, backup, rollback, and character SavedVariables isolation protections remain intact.

Three installer regression scenarios first failed against the prior version (running game, process query failure, absent check-result receipt), then passed. A fourth test exposed and corrected the malformed game-PID bypass. Positive tests use hermetic temporary addon folders only; they do not replace the physical RIFT installation.

## Verification on AMD-DESKTOP (earlier snapshot, 6:48 PM EST)

- Full Windows Python/Lua suite: **167 passed / 167 run**.
- Node observer and manual import suite: **27 passed / 27 run**.
- Combined: **194 passing automated tests**.
- Actual guarded process query (read only): **`RUNNING_RIFT_PIDS [23164]`** at the time of the check.
- Guarded installation dry run: source `0.2.14`; the three changing physical addon files would be `Core.lua`, `Main.lua`, and `RiftAddon.toc`; the other seven source files match. The **installed manifest is still `0.2.12`**.
- Exact-character, read-only disk audit: SavedVariables is still **schema 1**, with **33 retained rows, zero imported rows, no checkpoint**, modified at **2026-11-20 09:36:52 EST**. Eight other addon files share that timestamp within two seconds; none in the reported peer set were newer by 10+ seconds.
- No physical addon file was copied, no game input or reload issued, and no saved character file was modified during this cycle.

The unchanged disk snapshot does **not** prove the addon serializer is defective. RIFT manages save timing; the current game may not yet have completed a valid engine save. An in-memory Save.Begin or a simulated Lua callback is never treated as proof of bytes on disk.

## Deployment and physical acceptance checklist recorded before game exit

1. Preserve the active RIFT session. Only after the user closes the game intentionally, run `python -B tools/deploy_rcm.py` and then `python -B tools/deploy_rcm.py --apply --expect-host AMD-DESKTOP` from `C:\work\RiftChatModern`. The installer will refuse if the game is still running or process state cannot be established.
2. Verify the installed `RiftAddon.toc` version is `0.2.14` with all six ordered startup modules, the `Email` placeholder, and 10/10 matching source hashes. Do not copy code into an active game.
3. Start a fresh physical client, identify its new PID/HWND, and verify the RCM init message, draggable and readable window, tab/RESET behavior, imported-message formatting, and focused editor. Do not reuse old window IDs.
4. Check `/rcm checkpoint` before and after an actual engine save. After the normal save operation, run the independent `tools/rcm_disk_receipt.py` on the verified character's exact existing file with `--require-checkpoint`; report disk proof separately.
5. Ordinary native Say/Tell/Party/Guild/public-channel reception and automatic host-to-addon transport are still unverified. Do not market them as working.

No Ollama, OpenCode, or Codex CLI work was delegated in this cycle. No genuine internal ChatGPT worker-spawn action was available, so code changes and tests were performed directly rather than fabricating subagent execution.

## Physical deployment and first verified disk save — 7:49–7:51 PM EST

The user explicitly exited RIFT completely to permit a safe installation. Independent `rcm_session_preflight.py` and the installer process query found **no `rift_x64.exe` or RIFT Error Handler processes** on AMD-DESKTOP at approximately **7:49:39 PM EST**. The preflight returned exit code 2 solely because it also requires a running game and a log file for its separate live-chat investigation; **the absence of the game was the intended deployment precondition**. A fresh guarded dry run selected the established OneDrive RIFT AddOns location and showed exactly three changed files.

The new guarded `--apply --expect-host AMD-DESKTOP` ran with exit code **0** at approximately **7:49:48 PM EST**. It replaced only **`Core.lua`, `Main.lua`, and `RiftAddon.toc`** and preserved verified prior copies under the ignored local backup directory `artifacts/deploy-backups/20261121T004948Z-0xjvzrxg/`. The report explicitly stated `gameProcessCheck: closed`, `hashVerified: true`, `gameInputSent: false`, and `savedVariablesTouched: false`. A **separate subsequent dry run** found **0 changed files and 10/10 SHA-256 matches**; direct reading of the installed `RiftAddon.toc` confirmed version **0.2.14**, Environment **4.3**, the required Email placeholder, all **six ordered startup modules**, and the character SavedVariables declaration.

### Independent saved-data result, newly available after clean exit

The character-scoped read-only `rcm_disk_receipt.py` inspection, including a separate passing run with `--require-checkpoint`, found the existing saved file had changed **before the new source was deployed**: last modified **2026-11-20 7:49:09.042611 PM EST**, SHA-256 **`87c4ad76cbc5cf7e2cb82b7b5cb8fd54c780fb1aa3f6880f7625cfad5ebb617a`**, size **9,974 bytes**. It contained:

- **Saved schema v2**, **50 history rows**, last history ID 50, next ID 51.
- A genuine **serialized** checkpoint in the file: format 1, schema 2, event sequence 1, timestamp 1795222148, history count 50, last history ID 50, last imported ID 0; all metadata checks consistent.
- **Zero retained `kind=import` rows.** Thus the earlier manual live import is **not present in this observed disk snapshot**. This does not establish why it disappeared or whether it remained in memory until any specific exit/restart. A future fresh import must be saved and independently audited to prove retained-import persistence.
- Eight peer-addon save files with timestamps within two seconds of RCM, independently supporting a game-wide save operation. The audit did not modify or execute Lua contents.

**Interpretation:** this is the *first independently verified RCM disk-save receipt* after earlier negative snapshots. The save occurred while the prior addon version **0.2.12** was installed, approximately 39 seconds before deploying **0.2.14**. It therefore verifies the older release's serialized save-checkpoint mechanism, **not** a physical load or save of 0.2.14. Neither the actual `Save.End` callback nor an in-game 0.2.14 UI test was observed. Do not confuse stored metadata with evidence of successful native Say/Tell/Guild/Party chat capture.

### What remains after successful installation

1. Start RIFT normally and obtain a new PID/HWND; inspect the actual in-game init message and full chat window, version, drag/resize, focus, tabs, search/reset, and details. Installed bytes alone do not prove successful runtime initialization.
2. Use the original native chat input for `/rcm checkpoint` and `/rcm show` as needed. Verify the RCM status in-game and keep the editor's local `:commands` distinct from native slash commands.
3. For retained-import proof, create a deliberately identified new manual candidate import, verify its `HOST/...` classification, save via an ordinary RIFT logout or intentional `/reloadui`, then rerun the **exact-character** disk checker with `--require-checkpoint` and validate `importRowsOnDisk>0`, `lastImportedIdOnDisk`, `checkpoint.lastImportId`, and whether the test message's ID is retained.
4. Native social chat reception and automatic host delivery remain separate unproven capabilities. Do not claim these simply because the historical system messages and checkpoint are now persisted.
