# Rift Chat Modern v0.2.15 — Verifiable manual import IDs across reloads

**Date:** Friday, November 20, 2026 (America/New_York)  
**Verified development machine:** AMD-DESKTOP  
**Repository:** `C:\work\RiftChatModern`  
**Lua/runtime:** RIFT Lua 5.1, Environment 4.3  
**SavedVariables / public API:** schema 2 / interface 2 (both unchanged)

## Root cause and purpose

RCM can already accept a candidate host record through a manually entered `/rcm import` command, and the independent Windows disk checker can require a specific imported history ID after a genuine RIFT save. However, the Lua import handler previously returned only `imported_unverified`, and the native chat acknowledgment omitted the ID assigned by `Model:publish`. After a restart the transient transfer status was reset, leaving an avoidable gap between successful import, the serialized record, and its independent disk audit.

This release closes that identity/receipt gap **without inventing native social-chat reception or forcing a game save**.

## Implementation

- `HostIngress.lua` captures the publisher's actual returned `row.id` after a successful import, validating that it is a finite positive integer. It exposes `lastImportedMessageId` and the 12-character `lastImportToken` in **session-only** `GetHostIngressStatus()` metadata. A generic publisher that merely returns `true` remains accepted, but RCM reports no invented history ID.
- The real RCM import completion notice in native RIFT chat now includes **`history #ID`**, and explicitly says **`NOT verified native chat; NOT verified on disk`**.
- `/rcm import status` and `:host status` report the last imported history ID for the current session.
- `Main.lua` also derives `retainedImportCount` and `lastRetainedImportMessageId` from the current model's actual retained `kind=import` rows. Unlike transient transfer metadata, this lookup still works when saved history is loaded after a fresh game session. Both status surfaces expose the **latest retained import history #ID** with the same disk-verification disclaimer.
- The existing `RiftChatModernAPI.GetHistory("imports","",LIMIT,0)` and `GetMessage(ID)` continue to return isolated read-only row copies. No persisted schema fields or other addon API versions change.

## Red/green test evidence

The new tests first **failed against v0.2.14**:
1. A completed single-part import did not expose the assigned history ID or its transfer token, nor include the ID in the actual mocked native RIFT chat acknowledgment.
2. A Boolean-only external publisher had no appropriately characterized transfer token/ID status.
3. A new mock RIFT session loading a previously serialized imported row did not expose its retained ID in the status API or native `/rcm import status` command.

The code was updated and the Lua 5.1 tests passed. Duplicate replay is also checked not to create a second retained row or alter the latest assigned ID. The new saved-history lookup does not claim that file bytes were independently inspected: `GetSaveCheckpointStatus().onDiskVerified` remains `false` even when the mocked saved table contains a checkpoint.

The full suite passed at the source verification checkpoint: **177/177 Python/Lua tests and 27/27 Node tests (204 total)**. All six manifest startup modules and the required Email metadata remain in order, and source versions are synchronized to **0.2.15**.

## Physical acceptance plan

The following requires a fresh RIFT startup after a guarded deployment. **No in-game v0.2.15 acceptance is claimed by passing the automated tests.**

1. Verify the active host is AMD-DESKTOP, all 10 installed addon-file hashes match, the loaded manifest shows version 0.2.15, and the addon initialization notice is visible. Use the *original* RIFT chat field for `/rcm show` and `/rcm import status`.
2. Open Windows PowerShell in `C:\work\RiftChatModern` and generate a unique **manual** test import command:

   ```powershell
   node .\tools\rcm-chat-import.cjs --kind guild --sender RCMProbe --channel Guild --text "v0.2.15 persistence acceptance"
   ```

   This prints one or more commands. It **does not send input** to the game. Enter the displayed `/rcm import ...` command(s) in RIFT's original chat entry, not the RCM editor.
3. Observe RCM's native acknowledgment containing `history #ID`; independently confirm the corresponding `HOST/GUILD` entry in RCM's IMPORTS tab. Use `/rcm import status` to record `last imported history #ID` and `latest retained import history #ID`. Do not assume the number in advance.
4. Use the game's native `/rcm checkpoint`, then a **normal** RIFT logout or intentional game save lifecycle. Do not manually edit the character SavedVariables file.
5. On AMD-DESKTOP, check the **exact existing character file** with `tools/rcm_disk_receipt.py --expect-host AMD-DESKTOP --file "C:\<verified character save path>\RiftChatModern.lua" --require-import-id ID`, substituting the observed ID. Exit 0 requires both the exact import row and a structurally consistent checkpoint on disk; exit 2 is a failure of those proof requirements. The checker never prints message bodies.
6. After a subsequent game start, `/rcm import status` should still show the last **retained** imported ID even though the current session's transfer counter has reset. Verify actual UI content and classification separately.

## Remaining boundaries

- RIFT's ordinary native Say/Tell/Guild/Party/public-channel stream remains **unverified** through the addon APIs, and there is no proven automatic Windows-to-RCM inbound chat path.
- The RCM game window's physical drag, focus, tab and detail acceptance must be observed in the newly launched client, not inferred from test mocks.
- A Save.Begin event receipt or retained in-memory row does not prove disk persistence until the independent host audit passes.

This release used direct ChatGPT reasoning with Workbridge's verified project access and local test executables. **No Ollama, OpenCode, or Codex CLI was used.** Workbridge task assignments are not independent AI workers and none are claimed.

## Physical deployment receipt — 8:03 PM EST, November 20

After a separate exact-process check returned **`RUNNING_RIFT_PIDS []`** on **AMD-DESKTOP**, the guarded `tools/deploy_rcm.py --apply --expect-host AMD-DESKTOP` completed successfully at approximately **8:03:20 PM EST**. It replaced exactly four physical addon files: `Core.lua` (synchronized version), `HostIngress.lua` (new ID receipts), `Main.lua` (restart-aware status / completion notice), and `RiftAddon.toc` (version 0.2.15).

The installer independently verified that the game was closed before copying (`gameProcessCheck: closed`), backed up the old files to the ignored local `artifacts/deploy-backups/20261121T010320Z-cpzjx9he/` folder, and reported `hashVerified: true`, `savedVariablesTouched: false`, `gameInputSent: false`, and `physicalGameLoaded: false`.

A **second, independent post-install dry run** found **zero pending changed files among all 10 source/installed files**, and `hashVerified: true`. Direct reading of the installed `RiftAddon.toc` confirmed version **0.2.15**, Environment 4.3, Email placeholder, all six startup modules in exact order, and character-scoped SavedVariables.

The real character file was then independently inspected read-only with `rcm_disk_receipt.py --require-checkpoint`. Its SHA-256 remained **`87c4ad76cbc5cf7e2cb82b7b5cb8fd54c780fb1aa3f6880f7625cfad5ebb617a`**, last modification **7:49:09 PM EST**, 50 retained `system` rows, zero imports and checkpoint sequence 1. This shows **the v0.2.15 installation did not modify character history**; it does not demonstrate that the new addon has loaded or processed its first import.

**Next physical proof remains outstanding:** user starts RIFT, verifies new game PID and actual v0.2.15 window, generates one unique manual test import, records the actual reported history ID, completes a normal engine save, and confirms that ID with `--require-import-id` against the exact saved file. Native social-chat reception still requires an independent transport experiment.
