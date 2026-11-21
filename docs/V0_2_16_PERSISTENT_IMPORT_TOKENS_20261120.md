# RCM v0.2.16 — Persistent manual-import identity and verified save checks

**Date:** Friday, November 20, 2026, America/New_York
**Development host:** AMD-DESKTOP
**Repository:** C:\work\RiftChatModern
**Runtime:** Lua 5.1 / RIFT Addon Environment 4.3
**Compatibility:** character SavedVariables schema **2**; public API interface **2**, unchanged.

## Root cause reproduced

The v0.2.15 host ingress receiver remembered only the latest 32 transfer tokens **in process memory**. Even after a valid RIFT save, re-pasting the same /rcm import command following a new RIFT session would create a second history row, because the in-memory recent-token cache was reset.

A new integration test exercised the actual Node encoder, RIFT Lua 5.1 mocks, Save.Begin, fixture serialization, the independent disk verifier, fresh Lua startup and replay of exactly the same token. Before the fix the replay regression FAILED, showing **2 imported messages instead of 1**. That was a concrete persistence/identity defect rather than a UI issue.

This test is a synthetic full-stack fixture, **not evidence of physical RIFT execution**.

## Root-level code correction

- **Core.lua** adds an optional saved history field named importToken, restricted to imported, host_manual records and strictly validated as **12 uppercase ASCII hexadecimal characters**.
- Model:publish stores the validated token. Model:findImportToken searches retained history (at most 240 rows). A duplicated retained token is refused before another row can be appended, without advancing the history revision.
- Core.new rejects duplicate persisted token IDs and invalid token data without mutating the saved history. Existing schema-v2 imports with no token and older schema-v1 migrations remain compatible.
- **HostIngress.lua** attaches the transfer ID to successfully decoded candidate imports. Its optional stored-token lookup runs before fragment assembly; a broken lookup fails closed instead of guessing a new import is safe.
- **Main.lua** connects HostIngress to Core's persistent lookup, forwards the token in publish metadata and continues showing the actual assigned history ID and an explicit NOT verified on disk notice.
- The token is included as an optional field in read-only GetHistory/GetMessage row copies. No public API interface or SavedVariables schema version bump was needed.

## Independent disk proof upgraded

The read-only Python checker tools/rcm_disk_receipt.py now recognizes optional importToken fields in actual Lua history tables, while ignoring quoted chat bodies, comments and unrelated table scopes. It refuses malformed/duplicate tokens and tokens outside a host_manual import.

The new **--require-import-token TOKEN** option requires a retained imported row with the exact token and a consistent serialized Save.Begin checkpoint. Combining **--require-import-id ID** and **--require-import-token TOKEN** requires the **same saved row** to satisfy both identifiers. Two different matching rows cannot cause a false success.

- Exit **0** means the requested imported identity and checkpoint match on disk.
- Exit **2** means the file was readable but the identity/checkpoint requirement failed.
- Exit **1** means an invalid request, inconsistent structure or unstable file read prevented a reliable audit.

The checker does not execute saved Lua, edit the character file or disclose chat bodies. It reports the count of tokenized imported rows without printing tokens by default.

## Tests, including failures

- Red: replaying a saved import token after a fresh Lua session yielded **two imports**, violating exactly-once behavior for retained records.
- Green: that same test now retains only the original imported row and history ID.
- Added provenance-model tests: valid token, wrong-case/invalid token rejection, non-import misuse refusal, duplicate saved-token rejection, backward-compatible old v2 row acceptance.
- Added receiver test: an exception in saved-token lookup cannot publish or acknowledge success.
- Added auditor tests: require token + history ID on the same row; detect cross-row false matches and duplicate saved tokens.
- **Full source test pass:** 185/185 Python/Lua and 27/27 Node.js tests, **212 total**.
- Git diff whitespace check passed. Reported Git LF/CRLF notices were conversion warnings rather than patch errors.
- The predeployment dry run selected the real AMD-DESKTOP installation and identified four changed files: Core.lua, HostIngress.lua, Main.lua and RiftAddon.toc.

## Boundaries

The source preserves a bounded 240-message history. Duplicate suppression lasts while the message carrying the matching import token remains retained. If an imported record is evicted or deliberately cleared, RCM may accept that token again. There is no separate unbounded token ledger.

This release does **not** establish normal server-delivered Say, Tell, Guild, Party or public-channel reception. Manual host records remain explicitly classified as IMPORT and host_manual.

## Real game acceptance still required

1. Load the correctly installed v0.2.16 with a fresh game PID/HWND; physically verify the actual window, text readability, focus, drag/resize and tab behavior.
2. Generate a unique manual test import from the existing Node encoder. In the **original RIFT native chat entry**, paste the generated /rcm import command(s). Record both the **12-character transfer token** and RCM's returned **history #ID**. Verify the HOST/GUILD row in the IMPORTS tab.
3. Repeat the same command in-session; verify a duplicate acknowledgment rather than a second row.
4. Complete a legitimate RIFT save. Use tools/rcm_disk_receipt.py against the **exact existing character file**, with --expect-host AMD-DESKTOP and both --require-import-id ID and --require-import-token TOKEN. Only a zero exit code is disk proof for that exact row.
5. Restart RIFT; use /rcm import status to verify the previously retained history ID, then repeat the same token and ensure it cannot create a second row. Neither mocked Save.Begin nor an installed-file hash is a physical acceptance substitute.

**Development restrictions honored:** No Ollama, OpenCode or Codex CLI; no fabricated internal ChatGPT workers. Source changes and verification used the live, verified AMD-DESKTOP development connection.
