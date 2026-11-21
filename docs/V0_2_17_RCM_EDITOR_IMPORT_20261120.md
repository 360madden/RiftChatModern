# RCM v0.2.17 — Manual host import through the RCM editor

**Development date:** Friday, November 20, 2026 (America/New_York)  
**Verified workstation:** AMD-DESKTOP  
**Canonical repo:** C:\work\RiftChatModern  
**Game addon package:** v0.2.17 (Lua 5.1; RIFT Environment 4.3)  
**Compatibility:** SavedVariables schema 2 and public interfaceVersion 2 unchanged.

## Objective: stop making native RIFT chat the only inbound host command field

RCM's long-term purpose is an independently useful modern chat replacement, with discovery commands and interoperable messages for the user's other RIFT addon projects. The prior host-side encoder and Lua receiver handled bounded /rcm import messages **only when the player typed them into RIFT's original native chat input**.

That was an avoidable dependency on precisely the window RCM eventually aims to replace. It also made future Windows companion automation more complicated than necessary. A successful normal chat import from the external host did *not* establish that the RCM-owned focused text editor could accept the same data.

## Root-level implementation

This release adds an opt-in, user-entered editor command **:import** which reaches **the very same HostIngress receiver and model publisher** as the existing native /rcm import command. No second decoder, alternate persistent store, client memory writer, game filesystem ingestion, network listener or automatic input loop was added.

- Main.lua intercepts local :import ID INDEX/TOTAL BASE64URL at the existing executeLocal boundary, before generic model command dispatch. Input is bounded at 160 characters; host receiver still independently validates transfer token, fragment bounds, sequencing, UTF-8 payload and matching retained-token identities. Rejected input returns an explicit reason and **keeps the unsent editor draft**.
- :import status and :import cancel use the same transient import state; cancellation only discards pending fragments and never touches saved chat rows. :import help supplies syntax.
- Accepted fragments show a UI receipt (chunk progress, duplicate refusal or assigned imported history ID) in the actual RCM status/footer field. The editor's render pass preserves the final receipt. Receipts explicitly say **native player chat and disk persistence are not verified**.
- Successfully entered :import transfer commands **never enter RCM's 32-item session command recall**. This avoids storing Base64-encoded chat text in a secondary command-history surface. No transfer history or unvalidated metadata is written to SavedVariables.
- The generic model RegisterCommand API rejects the reserved name import. Another addon cannot quietly override the native-equivalent editor path. The public GetStatus() adds **hostEditorImportReady**; GetHostIngressStatus().mode now says **manual_slash_or_editor**, not the obsolete manual_slash_only.
- All existing native /rcm import behavior remains for compatibility, and retained-token replay prevention from v0.2.16 still works identically across either field.

## Windows encoder support

tools/rcm-chat-import.cjs adds **--input-mode editor**, producing human-pasteable **:import** commands with exactly the same RCM1-B64URL payload and 12-character transfer identity as the default **/rcm import** commands. It works with both manual --kind / --sender / --channel / --text input and --stdin-json candidate records, and still refuses truncated or invalid messages.

Example, from Windows PowerShell in C:\work\RiftChatModern:

    node .\tools\rcm-chat-import.cjs --kind guild --sender RCMProbe --channel Guild --text "RCM v0.2.17 editor acceptance" --input-mode editor

The resulting JSON contains one or more commands. Paste **each value from commands**, in order, into RCM's own editor and press Enter. The encoder does **not** focus RIFT, send key presses, paste text automatically, or establish a working incoming player-chat feed. The test sender is a **synthetic host candidate**; the imported message is identified as HOST IMPORT, not actual native Guild chat.

The exact transfer ID should be taken from the generated result rather than guessed. The new CLI defaults to the existing native input mode unless editor is explicitly chosen, so prior workflows remain compatible.

## Test-first evidence, including failures

First, two new Lua 5.1 integration tests failed before the new input was implemented:
1. RCM's own textfield rejected one valid transfer while the same exact fragment worked in native /rcm chat; no imported history row appeared.
2. A multi-fragment import could not be started/cancelled in RCM's editor, because command dispatch routed it to the generic model rather than HostIngress.

Two new Node tests also failed before implementation: the encoder had no output inputMode=editor or :import command rendering, and the CLI rejected the --input-mode editor flag.

After the implementation, tests pass for:
- Actual mocked RCM editor SetText + Enter, assigned imported ID, saved history classification and correct transfer token.
- Direct same-client RiftChatModernAPI.Submit of a duplicate transfer, with no second history row.
- Invalid editor import preserves the draft; no fake imported message.
- Multi-part import, progress, explicit cancellation and fresh completion using the same receiver.
- No editor-command recall pollution and no additional SavedVariables transfer ledger.
- RegisterCommand cannot override the reserved import command.
- Existing native /rcm import, Unicode multi-part payloads, existing disk-auditor identities, and all other addon mock cases.
- Default native CLI mode vs requested editor mode and equivalent decoded payloads, including --stdin-json with incomplete-record refusal.

**Source validation: 195/195 Python/Lua 5.1 tests and 43/43 Node tests = 238 total passing**, with all source/manifest/test version literals updated to **0.2.17**. Before the physical install, the guarded installer dry run identified exactly **Core.lua, HostIngress.lua, Main.lua, and RiftAddon.toc** as changed.

## Physical acceptance remains separate

The physical client was closed during implementation. Passing Lua mocks does **not** prove RIFT's actual textfield focus, paste/Enter submission, or Windows companion delivery in a live game.

When RIFT is deliberately launched on AMD-DESKTOP:
1. Capture new process PID and HWND, verify addon startup notice and in-game panel version **v0.2.17**, and check drag/focus/legibility visually.
2. Open RCM with /rcm show. Focus **RCM's editor**, not native chat; paste the encoder's **:import** command and press Enter.
3. Confirm a progress or imported history #ID receipt and a single HOST/GUILD row in the IMPORTS tab. Repeat the same token and confirm no second row is inserted.
4. Use :import status and a deliberate multi-part :import cancel test; retain existing saved history.
5. Let RIFT complete its normal save lifecycle. Independently check the actual character SavedVariables file with rcm_disk_receipt.py and **both** --require-import-id and --require-import-token. Do not infer disk persistence from an in-memory row or Save.Begin callback.

Native player Say/Guild/Tell/Party/public chat capture remains unverified in the current client. The host's Log.txt observer remains blocked by the real persisted RIFT setting LogConsole=False, with no live log file; any enabling of noncombat logging must be deliberate. Automatic Windows-to-RCM input and native social-chat sending are *not* implemented by this release.

No Ollama, OpenCode or Codex CLI was used, and no independent ChatGPT subagent was claimed without an actual worker-spawn tool.

## Guarded physical installation receipt — 9:10 PM EST

After local commit f0bf4f923686284ac8dfa25c2a7eea2e51c2e20c, AMD-DESKTOP was reverified and RIFT_PIDS was []. The standard guarded deploy command ran:

    C:\work\riftreader2\.venv\Scripts\python.exe -B tools\deploy_rcm.py --apply --expect-host AMD-DESKTOP

It completed with exit 0, gameProcessCheck=closed and hashVerified=true. Exactly **Core.lua, HostIngress.lua, Main.lua and RiftAddon.toc** changed in the physical OneDrive RIFT AddOns/RiftChatModern installation. Old files were backed up at:

    C:\work\RiftChatModern\artifacts\deploy-backups\20261121T021022Z-hwku21bt\

A second, separate dry run after deployment found **changedFiles: [] and hashVerified: true for all 10 installed/source files**. Direct reading of the installed RiftAddon.toc verified version **0.2.17**, Environment **4.3**, mandatory Email placeholder, six ordered startup modules and character-scoped RiftChatModernSaved. No other installed addon was changed.

The independent disk auditor was rerun against the exact existing Deepwood/Atank character file. The SHA-256 remains **87c4ad76cbc5cf7e2cb82b7b5cb8fd54c780fb1aa3f6880f7625cfad5ebb617a**, modified **November 20 at 7:49:09 PM EST**. It still contains 50 system rows, zero imported rows, schema v2 and internally consistent checkpoint #1. This **confirms no SavedVariables modification by installation**. It does not prove editor input or imports have been executed in RIFT.

The updated Node encoder was run with --input-mode editor and produced a unique one-part, not-yet-sent acceptance command, transfer token **C0A4F8141CFA**:

    :import C0A4F8141CFA 1/1 RwBSQ01Qcm9iZQBHdWlsZABSQ00gdjAuMi4xNyBlZGl0b3IgaW1wb3J0IGFjY2VwdGFuY2U

This is encoded host candidate text, not an ordinary Guild message received from the game. The next game run must use RCM's own focused text field (not the original native chat input) and separately verify the actual message ID, IMPORTS tab and saved on-disk receipt. RIFT remained closed during the deployment.
