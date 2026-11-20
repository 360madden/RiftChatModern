# RCM v0.2.6 — Editor history, search synchronization, and regression report

Date: November 20, 2026 (America/New_York)
Verified host: AMD-DESKTOP
Canonical repo: `C:\work\RiftChatModern`
Physical addon directory verified by Workbridge:
`C:\Users\mrkoo\OneDrive\Documents\RIFT\Interface\AddOns\RiftChatModern`

## Product scope

RCM is a standalone RIFT MMO Lua chat-style console intended to provide a readable modern alternative and reusable interface for other addons (RRE, RR2, RPT and others). The existing RIFT social-chat box is kept intact. Confirmed Lua addon APIs expose NPC speech, notifications, configured native console metadata, addon-specific peer messages and local addon diagnostics. They do not yet provide a validated way to fully read or send ordinary say/guild/tell/party player chat.

## Changes

- Added a 32-entry bounded editor command-recall list. Only successful, manually entered local colon commands are included. Adjacent duplicates are ignored, and entries are kept in memory only, not in SavedVariables.
- In the focused RCM editor, native `RiftTextfield.Event:KeyDown` can recall older/newer commands for `up`/`down` or `arrowup`/`arrowdown`. Actual physical key labels and routing require live proof.
- Forward past newest restores the exact draft that was in the editor before recall; edits and paste stop recall navigation.
- Normal player-chat text and unknown commands remain in the draft when rejected, without false send success or recall-history entry.
- Fixed visible search-text desynchronization when local `:find` or native `/rcm find` updates the model; synchronized query changes avoid unnecessary redraw recursion.
- Added `GetStatus().commandHistoryCount` and `GetStatus().commandHistoryPersisted=false`. Public interfaceVersion remains 1 and the persisted schema remains version 1.
- Manifest, model status and startup version synchronized at 0.2.6. No new RIFT loader files.

## Failures and lessons retained

The first new implementation increased the `makeUi` closure's captured locals over the Lua 5.1 60-upvalue limit. A full 81-test run failed with `function ... has more than 60 upvalues`. **No v0.2.6 deployment occurred at that stage.** The design was changed to share the existing `controls` table as the callback holder, avoiding extra upvalues in `makeUi`. The corrected full regression run passed: 81/81 in 0.433 seconds (Lua 5.1 via Lupa and RIFT API mocks).

The physical RIFT read-only screenshot attempt was refused with `UI_TURN_BUSY`; no UI state was changed or live acceptance claimed on that basis. The RIFT process was observed as `rift_x64` PID 22532, but a running process is not evidence that v0.2.6 has been loaded.

## Verification

Command from the Windows PowerShell 7 shell, at the project root:

```powershell
& "C:\work\riftreader2\.venv\Scripts\python.exe" -B -m unittest discover -s tests -v
```

The 81 cases include the previous 76 plus five editor-specific tests: cursor cycling, unsent-draft restoration, edit interruption, rejected native-chat safety, capacity/deduplication, and visible search synchronization.

## Outstanding physical acceptance

1. Verify installed manifest Email, Version, and RunOnStartup files. Confirm all deployed file hashes match canonical source.
2. In the actual RIFT client, reload its UI (operator-controlled), check addon errors and versioned startup announcement, then open `/rcm`.
3. Focus the RCM editor and enter `:echo one`, `:echo two`; test Up twice and Down through the newest command. Confirm unsent text recovery and that editing breaks recall navigation.
4. Enter `:find example` and `/rcm find example`; compare visible search query, filtered results and Reset.
5. Validate draggable/resizable window, partial-page history, detailed message copy and physical clipboard behavior separately. Clipboard-copy tests may overwrite current Windows clipboard content: protect it first.
6. A separate client is still required to prove receipt of `RCMDevV1` addon data. RIFT `Log.txt` external reader cannot be asserted to work until a live `/log` pilot confirms path and freshness.

## Handoff

Next product milestone should prioritize actual player-chat ingestion and, separately, a proven input route. Reuse mature LuaPadModern read-only `Log.txt` watchers rather than writing a duplicate. Historical RIFT log-monitoring tools demonstrate a candidate path, but RCM has no verified live host-to-Lua feed. Do not conflate addon data, console metadata, or local `Publish` events with true player social chat.

## Confirmed deployment receipt (09:55 ET, November 20)

Read-only host inventory and exact path verified `AMD-DESKTOP`, `C:\work` repository, and the established OneDrive RIFT addon installation. A bounded local Python command checked manifest Identifier, Email, Version 0.2.6, five startup Lua files and character-scoped SavedVariables, then atomically replaced only changed files: `Core.lua`, `Main.lua`, `RiftAddon.toc`. All 9/9 source/deployed files matched by SHA-256 afterward, with zero mismatches. No SavedVariables were read or modified; unrelated addons were untouched. Deployment is **not** proof of a successful /reloadui or physical keyboard behavior.
