# Rift Chat Modern v0.2.12 — Native save-lifecycle receipts and disk audit

**Date:** Friday, November 20, 2026 (America/New_York)
**Verified host:** AMD-DESKTOP
**Canonical repository:** `C:\work\RiftChatModern`
**Release:** v0.2.12, RIFT Lua 5.1, Environment 4.3
**SavedVariables schema:** **2**, unchanged from v0.2.11
**Public API:** `RiftChatModernAPI.interfaceVersion = 2`, unchanged

## Why this cycle was necessary

The previous physical RCM v0.2.11 acceptance proved a manually generated message reached the live RIFT addon and displayed with the correct **HOST/GUILD** classification. It did **not** prove that schema v2 or that newly imported record had reached disk.

At approximately 4:50 PM EST November 20, independent process queries found **no active `rift_x64.exe`** but did find the RIFT Error Handler. The character-scoped RCM SavedVariables file remained schema v1, contained 33 older messages, and had a last modified time of **9:36:52 AM EST**. Eight other recently active RIFT addons' save files also had last-write times within two seconds of this same time. No later files were found among these peer saves, and the RIFT diagnostic log and recent Windows Application events checked did not establish the reason the game process exited.

This is consistent with no successful game-wide SavedVariables save checkpoint since 9:36 AM. **It is not proof that RCM crashed the client, nor evidence that its schema migration failed in memory.** The engine controls its save schedule.

### What RIFT actually guarantees

Historical RIFT addon documentation lists `Event.Addon.SavedVariables.Save.Begin` and `Save.End`. Original RIFT addon developer discussion explains that normal addon SavedVariables are saved on **logout or `/reloadui`**, not continuously. The actual RIFT client still needs to complete that lifecycle. A Lua callback or Win32 keystroke acknowledgement is not proof of a flushed file.

References:
- https://github-wiki-see.page/m/chrisbecke/Igor/wiki/RIFT-API-Documents
- https://www.riftui.com/downloads/fileinfo.php?id=203&page=1&so=newest

## Changes: true save event observability, no artificial disk-write claim

**`Core.lua`** now has:

- `Model:recordSaveBegin(at)`: generates a small bounded scalar record inside the existing **character-scoped** `RiftChatModernSaved.saveCheckpoint` table only after RIFT raises the matching `Save.Begin` event. The record contains `formatVersion`, `schemaVersion`, `sequence`, `at`, `historyCount`, `nextId`, `lastHistoryId`, and `lastImportId`.
- `Model:checkpointStatus()`: returns a read-only summary of any stored receipt and current unsaved-state tracking, always with `onDiskVerified=false`. Malformed older checkpoint data is ignored without dropping valid messages or modifying schema.
- `Model:markSavedStateChanged()`: tracks saved geometry updates even though a window drag or resize does not need a history redraw.

**`Main.lua`** now subscribes to the documented RIFT `Save.Begin` and `Save.End` addon events. On Begin it stages the scalar checkpoint for the game's regular serializer; on End it increments an **in-memory-only** observation counter and deliberately avoids mutating SavedVariables after serialization may have completed. The same event filters used for addon loading ensure an unrelated addon's save does not create a false RCM receipt.

Two read-only interfaces are added:

- `RiftChatModernAPI.GetSaveCheckpointStatus()` and `GetStatus().saveCheckpoint`
- `/rcm checkpoint` (original RIFT chat) and `:checkpoint status` (RCM editor), both explicitly stating that **on-disk save is not independently verified**.

No command in this release forces `/reloadui`, triggers a logout, launches another process, writes disk files directly from Lua, or rewrites RIFT memory. The native-player chat reception limitation is unchanged.

## Windows independent disk checker

**New:** `tools/rcm_disk_receipt.py`. It reads a selected existing `RiftChatModern.lua` SavedVariables file and reports only:

- File hash, byte count, last-modified time, schema version
- Number of stored rows and imported rows, last message ID
- Whether the save checkpoint was actually serialized into the file and whether its message counts and import ID match the stored history
- Count of other addon save files near the same write time (metadata only)

It **does not execute saved Lua**, disclose chat bodies, modify the file, or assume that a Save.End event means the disk contains current data. The parser rejects oversized, invalid UTF-8 or malformed table structure and ignores fake checkpoint strings embedded inside a chat message.

In **Windows PowerShell**, from `C:\work\RiftChatModern`:

```powershell
& "C:\work\riftreader2\.venv\Scripts\python.exe" -B tools\rcm_disk_receipt.py --expect-host AMD-DESKTOP --file "C:\exact\RIFT\Interface\Saved\ACCOUNT\SHARD\CHARACTER\SavedVariables\RiftChatModern.lua" --require-checkpoint
```

Replace `ACCOUNT`, `SHARD`, and `CHARACTER` with the existing character save path. This explicit path avoids ambiguously choosing another character's save. Exit code 0 means a consistent receipt exists when `--require-checkpoint` is used, 2 means no consistent receipt yet, and 1 means the audit could not reliably inspect the requested file.

### Actual AMD-DESKTOP diagnostic finding

The first real-file audit found schema v1, **33 stored rows**, zero imported rows, **no save checkpoint**, **8 other addon files with writes within two seconds**, and **0 addon files newer by ten seconds or more**. It did not alter the character file. RIFT was not running at that time, so no live Save.Begin event could be observed.

This is a **negative persistence result** for the previous live import and migration, not a claim that the v0.2.12 feature itself failed. It has not yet been physically loaded.

## Regression and dependencies

- **159/159 Lua/Python tests passed after the separate disk-auditor hardening**, including seven save-lifecycle tests for Save.Begin, Save.End, wrong-addon filtering, no-save exit simulation, receipt generation and rollover, reloading a staged receipt, invalid metadata, native slash/editor status, and **geometry changes updating the pending-state indicator**.
- **14/14 Windows disk-audit fixture tests passed after hardening**, covering structural parsing of real-style and forged Lua table contents, strict UTF-8, duplicate fields, inconsistent receipt counts, wrong machine, exact filename, and peer-file write timestamps. **27/27 Node.js observer/import tests** also passed, for **186 automated tests total**.
- Existing model, schema-v1 migration, host import, API, chat UI and native message tests remain in the complete suite.
- The existing `RiftAddon.toc` module order, six RunOnStartup modules, character SavedVariables declaration, and required Email metadata are preserved.
- `interfaceVersion=2` and `schemaVersion=2` remain compatible with v0.2.11. Only `saveCheckpoint` is an additive, bounded persisted subtable.

## Guarded deployment receipt — approximately 5:04 PM EST

Before any file replacement, an independent exact-host Windows process check found **zero running `rift_x64.exe` processes** on AMD-DESKTOP. The verified installer then updated only **`Core.lua`, `Main.lua`, and `RiftAddon.toc`** in the previously established physical OneDrive RIFT addon directory. Existing copies were backed up locally to ignored `artifacts/deploy-backups/20261120T220407Z-f9ycjfe_`.

The installer validated the addon identifier, v0.2.12 manifest, Email field, Environment 4.3, six ordered startup files and character SavedVariables declaration, and compared **10/10 source and installed files by SHA-256 with zero mismatches**. It did not change character SavedVariables, send game input, restart or reload RIFT, or publish the private backup. The disk checker still reports the old schema-v1 saved data because the client has **not yet loaded v0.2.12** and reached a new engine save checkpoint.

## Outstanding physical acceptance

1. **Fresh RIFT process:** Verify the exact new PID/HWND and whether the error-handler is a companion or an error-only state. Do not reuse a previous game window identity.
2. **Save lifecycle:** In the live v0.2.12 addon, check `/rcm checkpoint`, generate an imported test message, then use RIFT's **original** native chat input for an intentional `/reloadui` or normal logout. Make sure RCM's editor does not capture the command.
3. **Independent disk proof:** Run `rcm_disk_receipt.py --require-checkpoint` against the exact character's file **after the save operation** and confirm schema 2, the checkpoint record, and that the imported ID appears among retained records. Never manually edit SavedVariables to fabricate a pass.
4. **UI detail and regular native chat:** Verify the message detail reader and RCM/native chat remain functional. Neither native social chat reception nor automatic host-to-addon delivery is claimed.
5. **Reliability root cause:** If another session exits without any addon save timestamps moving, preserve any actual error/crash report and investigate the game-wide save/exit issue separately from RCM data model correctness.

## Record of failures and corrections

The first Windows disk-audit run had **six errors among nine tests** because `re.finditer` was invoked with unsupported start/end positional arguments; after that repair, masked quoted values allowed a regex to consume too much whitespace. Both problems were fixed by using a compiled regex's bounded `finditer` and replacing quoted contents with a non-whitespace masking sentinel. Strict UTF-8 rejection was added afterward. In a separate post-release audit, Lua's **multiline bracketed strings and comments** were found to be another potential false-positive path: arbitrary `saveCheckpoint` text in `[[...]]` or `--[=[...]=]` could otherwise be parsed as real metadata. The disk checker now masks these constructs, rejects unterminated long literals, and includes four dedicated tests. These failures and corrections are retained in the engineering record, not hidden.

**Follow-up classification:** The multiline-literal protection changes only `tools/rcm_disk_receipt.py` and its tests; the physically installed v0.2.12 addon is unchanged. The repeat real-file audit again reported schema v1, 33 stored rows, no import rows, and no disk checkpoint. **Never equate a simulated save receipt, successful input submission, or on-screen RCM message with proven disk persistence.**
