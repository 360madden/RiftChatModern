# RCM post-deployment disk audit hardening — November 20, 2026

**Date:** Friday, November 20, 2026 (America/New_York)  
**Verified computer:** AMD-DESKTOP  
**Repository:** `C:\work\RiftChatModern`  
**Installed addon:** v0.2.14, unchanged by this host-only tooling update  
**Files changed:** `tools/rcm_disk_receipt.py`, `tests/test_disk_receipt.py`

## Primary findings

The physically installed v0.2.14 has **not yet been loaded in a fresh game session**. At 7:52 PM ET the independent Windows process and window checks showed no active `rift_x64.exe`. The OneDrive character saved file still has the independently verified 7:49:09 PM checkpoint with 50 rows, schema 2, sequence 1, and `nextId=51`.

A read-only category inspection of this exact file returned **50 `system` rows and 0 `import` rows**, with IDs 1–50. It did not emit message text. This makes the absence of the previous manual import a concrete on-disk fact, not a diagnosis of why it did not persist. Earlier live v0.2.11 testing proved a host-imported row appeared in the UI, but not that it survived a successful save before a subsequent restart.

## Discovered false-positive risks in the independent checker

The original `rcm_disk_receipt.py` could report a consistent checkpoint for malformed fixture data where:

1. Two history rows had the same message ID, which `Core.new` would reject on a future game load.
2. History IDs were out of order yet the checkpoint had been fabricated to match the last listed row, making `lastHistoryId` an unreliable high-water mark.
3. The checkpoint's recorded `nextId` disagreed with the actual serialized root `RiftChatModernSaved.nextId`.
4. The tool provided no small category breakdown, requiring separate private-file inspection to know what kinds of messages survived.
5. If RIFT rewrote the file between the auditor's initial metadata check and its final timestamp read, the auditor could combine one version's bytes/hash with a different version's timestamp and claim an apparently verified snapshot.

Regression fixtures reproduced these failure modes against the previous checker. The corrected parser refuses duplicate and nonmonotonic row IDs, checks root `nextId` against the checkpoint before claiming consistency, and reports `historyKindsOnDisk` as a bounded category-to-count mapping. It does not execute any saved Lua or include chat bodies in output. A new stable-read guard compares file identity, size, nanosecond modification/creation timestamps, and actual byte count before and after reading. If the file changed during the audit, exit **1** reports `saved_file_changed_during_audit` rather than claiming a consistent receipt.

## Exact imported-message retention proof

A new opt-in `--require-import-id ID` argument checks that the selected on-disk character file contains a retained `kind=import` row with **that exact numeric ID**, and that its serialized save checkpoint is internally consistent. This avoids accepting a mere count of unrelated imports as proof of the test message.

In **Windows PowerShell**, with `C:\work\RiftChatModern` as the current directory, use after a legitimate RIFT save:

```powershell
& "C:\work\riftreader2\.venv\Scripts\python.exe" -B tools\rcm_disk_receipt.py --expect-host AMD-DESKTOP --file "C:\Users\mrkoo\OneDrive\Documents\RIFT\Interface\Saved\<ACCOUNT>\<SHARD>\<CHARACTER>\SavedVariables\RiftChatModern.lua" --require-import-id <ACTUAL_IMPORT_MESSAGE_ID>
```

Replace the placeholders with an already verified exact character save location and **actual imported row ID** from the game/API; do not guess the ID or write directly to the file. This flag implies the same checkpoint requirement as `--require-checkpoint`.

- Exit **0**: exact import ID exists in the serialized file **and** the checkpoint metadata is consistent.
- Exit **2**: the selected file was readable, but the requested import is absent or the checkpoint is inconsistent.
- Exit **1**: invalid request or an audit error; no success claim.

The output includes `requiredImportId`, `requiredImportIdPresent`, `historyKindsOnDisk`, and the original receipt metadata. It never prints imported message bodies, changes the game, or edits character SavedVariables.

## Red/green and physical evidence

- **Red phase:** Four identifier/count regression cases failed against the original parser; the exact-import CLI tests also initially failed before implementation. The later concurrent-write fixture failed against the old read path, then passed after a stable-read guard was added.
- **Green phase:** **21/21** focused disk-checker fixture tests passed after fixing the defects; **174/174** full Python/Lua tests and **27/27** Node observer/import tests passed (201 total). A separate red-phase test reproduced an accepted mixed-version snapshot before the stability guard, then passed with the guard.
- **Real file, strict checkpoint:** Exit **0** on AMD-DESKTOP. Schema 2, history 50, kinds `{"system":50}`, no imports, checkpoint #1, root/checkpoint `nextId=51`, hash `87c4ad76cbc5cf7e2cb82b7b5cb8fd54c780fb1aa3f6880f7625cfad5ebb617a`.
- **Real file, requested historical candidate import ID 35:** Expected exit **2**, `requiredImportIdPresent=false` while `diskReceiptVerified=true`. This is negative *import-specific* proof, not a failed disk checkpoint.

## Release boundary

This is a **Windows/Python host-auditor-only improvement**. It does **not** modify any of the six RIFT Lua startup modules, `RiftAddon.toc`, addon API, or saved schema. Therefore the installed game addon remains **v0.2.14**, verified 10/10 source/installed hashes at the prior deployment, and no additional deployment or reload is required.

**Remaining live acceptance:** Start a new physical RIFT process, verify actual v0.2.14 UI and slash handling, submit a deliberate manual host import using native chat, verify its assigned saved-history ID, then use a normal engine save and the new `--require-import-id` checker against the exact character file. Native Say/Tell/Guild/Party receipt and automatic host-to-addon delivery remain unproven. No Ollama, OpenCode, or Codex CLI was used for this work.
