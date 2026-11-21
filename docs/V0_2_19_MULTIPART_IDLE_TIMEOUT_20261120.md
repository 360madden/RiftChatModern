# RCM v0.2.19 — Multipart import idle-timeout correction

**Date:** Friday, November 20, 2026 (America/New_York)
**Verified machine:** AMD-DESKTOP
**Repo:** C:\work\RiftChatModern
**Addon package:** v0.2.19; Lua 5.1, RIFT Environment 4.3
**Compatibility:** SavedVariables schema 2 and public API interface 2 unchanged.

## Product defect and root cause

RCM's manually entered host-to-addon transfer uses the existing RCM1-B64URL protocol with at most 12 fragments and a 45-second timeout for an incomplete transfer. The receiver previously set `pending.at` from the **first fragment only** and checked `at - pending.at > 45` on each subsequent fragment or status request.

That caused a real reliability defect: an 8-part transfer entered every 30 seconds could expire after the second fragment despite continuing to make progress. The remaining pieces might be accepted into a new incomplete buffer, with no final imported message.

The user's preferred workflow is now deploy-to-installed-addon while physical RIFT remains open, then **/reloadui** rather than exiting/restarting the game. This milestone follows that corrected policy.

## Precise implementation

`addon/RiftChatModern/HostIngress.lua` now maintains a dedicated **lastProgressAt** timestamp for the last *newly accepted* fragment. The expiry check measures 45 seconds of inactivity from that timestamp instead of the first fragment's arrival. A newly received unique part advances the progress clock. **Duplicate, conflicting, rejected, or merely status-query input does not extend it**, preventing a stalled transfer from being kept indefinitely alive by replaying one fragment. A backwards-running timestamp never rewinds the idle deadline.

The receiver's original protocol fields, saved-history publisher, transfer-token deduplication, UTF-8 validation, and caller-facing response receipts remain unchanged. No new persistent state or SavedVariables migration is required. Existing completed imports remain retained and idempotent across /reloadui.

## Test-first evidence

Two new Lua 5.1 integration tests in `tests/test_host_ingress.py` use **actual Node.js encoder output**:

1. A multipart Guild message with 30-second gaps between *new* fragments, and total transfer time exceeding 45 seconds. This test **failed before the change** because the original receiver expired active work. It now passes with exactly one accepted import and the correct token/history-ID receipt.
2. A Party message whose first fragment is repeated 39 seconds later. Even though the duplicate is acknowledged, querying at 46 seconds from the original unique fragment must expire it. A later fragment starts a fresh incomplete transfer rather than silently reviving the old one. This test also passes.

The test run after the fix passed all **19 targeted HostIngress integration tests**. The full suite passed **233/233 Python/Lua 5.1 tests** plus **47/47 Node.js tests**, **280 total**. `git diff --check` returned exit 0 with only Windows CRLF conversion warnings. Version literals were synchronized in Core.lua, Main.lua, RiftAddon.toc and all version-pinned Python tests, with no remaining v0.2.18 literals in current Lua, toc, or Python files.

The guarded installer dry-run identified exactly **four** changed installed files: Core.lua, HostIngress.lua, Main.lua, RiftAddon.toc.

## Physical deployment and acceptance

This is an ordinary addon hot update: from PowerShell at the verified repo root:

    & "C:\work\riftreader2\.venv\Scripts\python.exe" -B tools\deploy_rcm.py --apply --expect-host AMD-DESKTOP

The verified deployment script creates source-hash-checked backups, writes atomically, and checks 10/10 installed source-file hashes. It **does not require RIFT to close**, and reports reloadUiRequired when changed files are installed into an already-running RIFT client.

Then issue **/reloadui** in the game's original native chat field, and verify RCM's title/init message shows **v0.2.19**. Actual physical text-field acceptance of a slowly transferred multipart message still requires a deliberate live test, and an on-disk saved row still requires normal RIFT save plus independent inspection of its retained transfer token.

**Scope boundaries:** This fix improves an existing import receiver. It does NOT prove that RIFT's ordinary Guild/Say/Tell/Party text is captured into the noncombat Log.txt file, does not send native chat, and does not implement automatic Windows-to-addon delivery. The separate Windows editor-sender prototype remains outside this release and is not a verified live transport.

## Actual installed v0.2.19 receipt

The v0.2.19 source changes were committed locally at **c0fb762922b73465f10292ac73eba62c63c94923**, deliberately excluding the separate unfinished Windows editor-sender prototype.

The verified AMD-DESKTOP installer was run with **RIFT still open**:

    python -B tools/deploy_rcm.py --apply --expect-host AMD-DESKTOP

It completed successfully (exit 0) with gameProcessCheck=running, runningGamePids=[34596], hashVerified=true and reloadUiRequired=true. Exactly **Core.lua, HostIngress.lua, Main.lua, RiftAddon.toc** were replaced, with backups preserved at:

    C:\work\RiftChatModern\artifacts\deploy-backups\20261121T044657Z-5xkotld8

A completely independent second dry run found changedFiles=[] and hashVerified=true for **all 10** installed/source files. Direct reading of the installed RiftAddon.toc confirms Version **0.2.19**, Email placeholder, Environment **4.3**, six startup files in correct order and character-scoped RiftChatModernSaved.

The actual Deepwood/Atank SavedVariables file was separately inspected read-only; it still has SHA-256 **9a11a2c413b5317fb7dfc63ad189df4022514fc0e661fd98305082756511a616**, schema 2, 65 system rows, 0 imported rows and a valid checkpoint sequence 2. The installer did not modify that file.

**Runtime activation is still pending:** the user or a separately verified RIFT input action must issue **/reloadui** in the *native RIFT chat field*. No client restart is needed. The installed package verification is not proof that v0.2.19 has been loaded into the already-running Lua runtime; a fresh in-game title/init message or screenshot must confirm that.

No Ollama, OpenCode, or Codex CLI was used.
