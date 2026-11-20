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

## Verification on AMD-DESKTOP

- Full Windows Python/Lua suite: **167 passed / 167 run**.
- Node observer and manual import suite: **27 passed / 27 run**.
- Combined: **194 passing automated tests**.
- Actual guarded process query (read only): **`RUNNING_RIFT_PIDS [23164]`** at the time of the check.
- Guarded installation dry run: source `0.2.14`; the three changing physical addon files would be `Core.lua`, `Main.lua`, and `RiftAddon.toc`; the other seven source files match. The **installed manifest is still `0.2.12`**.
- Exact-character, read-only disk audit: SavedVariables is still **schema 1**, with **33 retained rows, zero imported rows, no checkpoint**, modified at **2026-11-20 09:36:52 EST**. Eight other addon files share that timestamp within two seconds; none in the reported peer set were newer by 10+ seconds.
- No physical addon file was copied, no game input or reload issued, and no saved character file was modified during this cycle.

The unchanged disk snapshot does **not** prove the addon serializer is defective. RIFT manages save timing; the current game may not yet have completed a valid engine save. An in-memory Save.Begin or a simulated Lua callback is never treated as proof of bytes on disk.

## Deployment and physical acceptance still required

1. Preserve the active RIFT session. Only after the user closes the game intentionally, run `python -B tools/deploy_rcm.py` and then `python -B tools/deploy_rcm.py --apply --expect-host AMD-DESKTOP` from `C:\work\RiftChatModern`. The installer will refuse if the game is still running or process state cannot be established.
2. Verify the installed `RiftAddon.toc` version is `0.2.14` with all six ordered startup modules, the `Email` placeholder, and 10/10 matching source hashes. Do not copy code into an active game.
3. Start a fresh physical client, identify its new PID/HWND, and verify the RCM init message, draggable and readable window, tab/RESET behavior, imported-message formatting, and focused editor. Do not reuse old window IDs.
4. Check `/rcm checkpoint` before and after an actual engine save. After the normal save operation, run the independent `tools/rcm_disk_receipt.py` on the verified character's exact existing file with `--require-checkpoint`; report disk proof separately.
5. Ordinary native Say/Tell/Party/Guild/public-channel reception and automatic host-to-addon transport are still unverified. Do not market them as working.

No Ollama, OpenCode, or Codex CLI work was delegated in this cycle. No genuine internal ChatGPT worker-spawn action was available, so code changes and tests were performed directly rather than fabricating subagent execution.
