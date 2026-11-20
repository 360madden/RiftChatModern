# RCM v0.2.13 — Track schema migration as unsaved state

**Date:** Friday, November 20, 2026 (America/New_York)
**Repository:** `C:\work\RiftChatModern`
**Verified Windows machine:** AMD-DESKTOP
**Runtime:** RIFT Lua 5.1, addon Environment 4.3
**Compatibility:** SavedVariables schemaVersion **2** and public API interfaceVersion **2** remain unchanged

## The root problem

v0.2.11 introduced a validated one-way migration from schema v1 to v2. The code updates `saved.history` and `saved.schemaVersion` in memory. v0.2.12 then added a read-only `pendingSessionChanges` indicator to show changes since RIFT's most recent Save.Begin receipt.

Those two features had an integration defect: `Core.new(saved)` initialized `revision=0` even when it **changed saved data** to migrate schema v1 to v2, or repaired a missing `nextId`. As a result, an unsaved migration could report `pendingSessionChanges=false` before RIFT had staged the next engine save. This is a state-tracking issue, not proof that the RIFT game save serializer malfunctioned.

The corrected `Core.new` initializes `revision=1` whenever it actually migrates a valid v1 history or generates a missing next ID. It otherwise keeps the existing revision-zero behavior. On a valid RIFT Save.Begin, `recordSaveBegin` stages the compact receipt and updates `_lastCheckpointRevision`, so the pending indicator becomes false until another saved-state change occurs.

**The change is deliberately narrow.** It does not rewrite a character's saved history on disk, force a flush, alter the v2 schema format, change the message origin model, or claim a completed disk save.

## Red-to-green regression evidence

A new dedicated test `test_migration_and_repaired_next_id_are_unsaved_until_engine_checkpoint` was run against the old implementation. It **failed** at the assertion that a successful v1→v2 migration must leave `pendingSessionChanges=true`. The model was then corrected, and the test passed.

The second, higher-level regression `test_full_rift_startup_marks_schema1_migration_unsaved_until_save_begin` drives the mocked RIFT startup events with a legacy host-imported Guild record. It checks that:

- The existing `[HOST? Guild]` record migrates to `kind="import"`, `origin="host_manual"`, and `channelKind="guild"` without losing its body.
- The public v2 checkpoint status reports **pending changes** after addon loading.
- Another addon's Save.Begin event does **not** clear the pending flag.
- RCM's own Save.Begin stages a checkpoint containing the imported message ID and clears the pending state.
- `onDiskVerified` remains **false** until an independent filesystem audit establishes that bytes actually persisted.

These tests exercise the production model and Main.lua through Lua 5.1 mocks, including the real manifest startup order. They are *not* a physical game save receipt.

## No alternative local AI agents

At the user's explicit direction, this workflow **does not use** Codex CLI, OpenCode, or Ollama. Two previously untracked local-model reviewer scripts were moved to `artifacts/retired-local-model-review/`, which is already excluded by `.gitignore`. They were preserved for reversibility but are not part of this release and are not launched.

Native ChatGPT subagent creation was checked again. The tool environment did not expose a genuine internal spawn/delegate action, so no workers or thinking-effort settings were fabricated. Source modifications and test verification were performed directly.

## Release and dependencies

Version references are synchronized to **0.2.13** in `Core.lua`, `Main.lua`, `RiftAddon.toc`, and the matching RIFT/Lua Python tests. The six `RunOnStartup` files, required `Email` field, character SavedVariables declaration, and addon-data channel remain unchanged.

The current installed addon and source may differ while RIFT is running. **Do not hot-copy these changes into an active RIFT session**: the release should be installed using `tools/deploy_rcm.py` after independently verifying that the game is closed, followed by a deliberate game launch and a physical UI acceptance test.

To validate locally from Windows PowerShell, with `C:\work\RiftChatModern` selected:

```powershell
& "C:\work\riftreader2\.venv\Scripts\python.exe" -B -m unittest discover -s tests -q
node --test tests/test_chat_observer.cjs tests/test_chat_observer_cli.cjs tests/test_chat_import.cjs
& "C:\work\riftreader2\.venv\Scripts\python.exe" -B tools/deploy_rcm.py
```

## Remaining checkpoints

1. **Physical deployment:** Only after RIFT is closed; run a guarded dry run and then `--apply --expect-host AMD-DESKTOP`. Verify every installed file's SHA-256 and exact `.toc` version.
2. **Save lifecycle:** In the freshly loaded v0.2.13 client, inspect `/rcm checkpoint` before and after the RIFT Save.Begin event. Distinguish event receipt from disk persistence.
3. **Disk persistence:** After a normal game save, use `tools/rcm_disk_receipt.py` against the exact character's `RiftChatModern.lua` and verify its checkpoint and imported-row metadata. Never fabricate a receipt by writing the file manually.
4. **Native social chat:** Ordinary Say, Tell, Guild, Party, and public-channel reception remains unproven; `kind="import"` is still correctly distinguished from real native chat.
5. **Debugging:** Any failure from a future live run must be recorded separately with the current PID/HWND, error text and save-file timestamps. Do not infer crashes from an error-handler companion process alone.

This document records the state-tracking fix and the evidence requirements. It is not a claim that the live RIFT client has loaded v0.2.13 or completed an on-disk save.
