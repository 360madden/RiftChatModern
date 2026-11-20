# RCM v0.2.11 — Physical RIFT restart and provenance acceptance

**Date:** Friday, November 20, 2026, approximately 3:38–3:50 PM EST
**Verified machine:** AMD-DESKTOP
**Canonical repository:** `C:\work\RiftChatModern`
**In-game addon:** `RiftChatModern` v0.2.11
**Git baseline before this report:** `66cccd45d72cbd6c2acdb0386faebbc412709ac6`

## Why this test mattered

The v0.2.10 live import placed a Windows-generated test message into RCM history with `kind="guild"`, even though no native Guild chat was captured. The v0.2.11 correction separates canonical message kind (`import`) from origin (`host_manual`) and claimed channel (`guild`), with a validated SavedVariables schema migration.

The previous live attempt was inconclusive because `/reloadui` entered the wrong text field, and an earlier test command was concatenated in native chat. The user exited and restarted RIFT and explicitly asked for a fresh connection and retry.

## Fresh session identity and local-file proof

- Workbridge independently verified **AMD-DESKTOP** and current RIFT process **PID 31820**, window **HWND 3805750**, executable `rift_x64`, title `RIFT`, class `TWNClientFramework`.
- **The previous PID/HWND (42992/24252650) were not reused.**
- Guarded deployment dry-run found installed version **0.2.11**, **10 source/installed SHA-256 matches**, and **zero changed files**. No addon copy or UI reload was necessary after the user's restart.
- The RIFT diagnostic log had progressed through addon loading and world entry; the log's addon-load marker alone is not sufficient for acceptance.
- The current character SavedVariables file on disk was still **schemaVersion 1**, 33 saved system messages, and last modified at 09:36:52 EST. Independent Lua 5.1 testing of that exact saved file (in a separate, sandboxed environment without game input) successfully migrated 33 rows to schema 2 in memory.
- The previously reported v0.2.10 `RCMTest` record was **not present in that old on-disk saved file**, so the live test cannot claim it was migrated from disk. Absence from the old snapshot is not proof that v0.2.11 deleted it.

## Actual RIFT in-game acceptance

1. Inspected the new game window and verified that native RIFT chat was visible.
2. Opened the **original RIFT chat entry**, visually verified a blank line, typed `/rcm show` without submitting, and confirmed the exact command was in the native chat input.
3. Submitted it with Enter, then physically captured the **RCM v0.2.11** window with an **IMPORTS** tab. At that point the panel contained **34 messages**, matching the 33 prior on-disk messages plus the current startup record.
4. Generated a **one-part Windows host import** using the checked-in `tools/rcm-chat-import.cjs` with ID `2A7B39E4C1F0`, kind `guild`, sender `RCMTest`, channel `Guild`, and body `v0.2.11 provenance classification check`.
5. Opened the native RIFT chat field, typed the generated `/rcm import ...` command, inspected the draft in the actual native input, and submitted it.
6. Direct visual inspection of **RCM v0.2.11 ALL history** showed a new bottom record: **15:46 · HOST/GUILD · RCMTest · v0.2.11 provenance classification che...**. The stored row is not presented as normal `GUILD` chat.
7. Clicked the **IMPORTS** tab in the physical client; the tab showed exactly **one record** with the same **HOST/GUILD** label. The footer reported **`1 messages ... imports ... native chat separate`**. The ALL history count had increased to **35**.

These are observed in-game UI receipts after actual Windows input, **not** just unit tests or keyboard-event acknowledgements.

## Evidence and restrictions

A cropped visual acceptance screenshot was saved **locally only** to:

`C:\work\RiftChatModern\artifacts\live-acceptance\rcm-v0211-imports-tab-20261120.png`

SHA-256: `6ac5584679c745731b897fd3b64e4f29f265bf25fc0a6d8ca8d86937485698c3`

Dimensions: 840×655 pixels. It remains in the repo's **gitignored `artifacts/` directory** and was **not** committed or uploaded. A separate in-session screenshot also displayed the ALL tab with 35 messages and the HOST/GUILD test row.

An additional **user-provided full-game screenshot** independently confirms the live RCM v0.2.11 IMPORTS panel with a single `15:46 HOST/GUILD RCMTest` record. The original RIFT chat remains visible in the same image, with the RCM acknowledgment indicating that a host candidate was imported. That screenshot is part of the conversation, **not copied into this public GitHub repository**. The underlying Guild channel remains a *claimed channel* of external data; this evidence does not establish native Guild-message reception.

The local file's **schemaVersion remains 1 on disk** as of this report; the in-game code has loaded its v1 history and displayed the v0.2.11 UI. SavedVariables flush/persistence on a subsequent clean logout is not yet independently demonstrated. **Do not edit or replace the live saved file to manufacture a migration receipt.** A pre-change on-disk backup exists under ignored `artifacts/savedvariables-backups/`.

The message detail overlay was clicked in one attempt, but no overlay appeared in the subsequent screenshot. That action is **not a verified live detail-view pass** and needs a separately targeted test; UI mock tests still pass.

## Conclusions

**Passed physically:**
- Fresh RIFT PID/HWND binding on AMD-DESKTOP
- RCM v0.2.11 actual loading and `/rcm show` slash command
- Preserved prior 33 saved messages and current startup message in the visible runtime history
- Actual one-part Windows-generated host record delivered into RCM
- Correct `HOST/GUILD` visual classification, never native `GUILD`
- IMPORTS tab filtering to exactly one imported record

**Still unverified:**
- A real ordinary RIFT Guild/Say/Tell chat transcript source
- Automatic Windows-to-addon import
- Long/multi-part manual import in this restarted session
- Live external API/subscriber metadata or clipboard export inspection
- On-disk persistence of schema 2 after a clean RIFT save point
- Live detail overlay opening from a row click

**Safety and reversibility:** no process injection, game memory patch, network interception, `/log` toggle, clipboard overwrite, or manual SavedVariables edit was performed in this acceptance. Original RIFT chat remained usable.

## Regression status and next priority

Before installation, **138/138 Python/Lua 5.1 tests and 27/27 Node tests (165 total)** passed, including six origin/migration cases and the 35-record synthetic migration fixture. All ten deployed addon files were hash-verified.

The best next development step is to establish a **real RIFT `Log.txt` chat record** and separately verify schema persistence after a normal user-initiated exit/restart. Do not mistake host-import channel metadata for server-delivered native Guild chat.
