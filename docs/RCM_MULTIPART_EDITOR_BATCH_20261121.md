# RCM multipart editor batch — Windows host companion milestone

**Date:** November 21, 2026 · 1:38 AM EST  
**Host:** AMD-DESKTOP · `C:\work\RiftChatModern`  
**Addon:** v0.2.19 (no Lua or .toc update)  
**Companion:** `tools/RcmEditorSender` (.NET 10, Windows)

## Root problem

The existing Windows sender validates and optionally types **one** `:import`
fragment per invocation. RCM's host observer and Node encoder can prepare up
to 12 fragments. Invoking the sender separately for every fragment leaves
ordering, token continuity and transfers that expire during long manual
entry to an external coordinator.

The v0.2.19 Lua receiver already counts the 45-second idle limit from the last
new fragment, rather than the first fragment. This release adds a matching
**bounded complete-transfer contract** on the Windows companion side so all
fragments are validated as one unit *before* typing is considered.

## Implementation

- New `RcmImportBatchContract` accepts exactly one encoded
  `rcm_manual_import` object from the existing Node encoder, piped via
  `--stdin-batch`. The default remains **NO INPUT**.
- Requires `protocol=RCM1-B64URL`, `inputMode=editor`, the correct sender
  metadata, and 1–12 ordered commands sharing an identical uppercase token
  and part count. Missing, duplicate, reversed or mixed chunks are rejected.
- Reassembles base64url and verifies canonical encoding, maximum 780 raw
  bytes, exact four wire fields, supported channel kind, strict UTF-8, and
  sender/channel/text byte limits. No malformed record can start an input
  sequence.
- Refuses unknown or duplicate JSON keys, trailing second objects,
  noncanonical payloads, malformed UTF-8 and JSON larger than 8192 bytes.
- Emits only digest, token, kind, counts and explicit evidence-status fields.
  The encoded message body is not included in sender receipts.
- Existing `--command` and `--stdin-command` single-part workflows remain
  available and unchanged in meaning.

### Input activation remains explicitly separate

Only a deliberate combination of `--send --ack-editor-focused --submit
--ack-submit --ack-batch` **plus six exact RIFT process/window/executable
pins** can select batch typing. Before entering a character, it verifies the
running game, foreground/root HWND, PID/process epoch, class/title, session and
executable hash; per-key identity and held-modifier checks are repeated.

Each fragment uses the sender's existing Unicode key pairs followed by one
Enter pair, with a 100-ms inter-fragment pause. If Windows reports partial
input or the game identity changes, the sender stops and **never silently
retries**. Its receipts report the number of parts attempted and explicitly
distinguish inserted Windows events from confirmed RCM history.

**Important limitation:** The host cannot independently verify that the
actual RCM RiftTextfield remains focused after Enter. The operator focus
acknowledgment and `--ack-batch` are not substitutes for observed in-game
receipts. Batch send is a prototype awaiting supervised physical acceptance,
not a verified autonomous chat bridge or native social-chat source.

## Safe PowerShell preflight (does not type into RIFT)

From the repository root:

```powershell
dotnet build .\tools\RcmEditorSender\RcmEditorSender.csproj -c Release

node .\tools\rcm-chat-import.cjs --kind guild --sender BatchProbe --channel Guild --text "RCM batch dry run" --input-mode editor |
    dotnet .\tools\RcmEditorSender\bin\Release\net10.0-windows\RcmEditorSender.dll --stdin-batch
```

Expected status: `batch_validated_no_input`. It returns the transfer token,
part count, total character count and a SHA-256; `gameInputSent=false`.
The pipeline does not open RIFT, change focus or touch its installed files.

## Validation

The exact Node encoder and Windows .NET executable were integrated using
fresh synthetic Guild/Party records. Initial regression coverage:

- Nine batch contract tests pass: one-part, multipart Unicode, incomplete,
  mixed-token, reordered, invalid metadata/JSON/wire bytes, missing required
  acknowledgment, fake process/window and sender-input separation.
- A tenth end-to-end regression passes: a real Node JSON batch is validated
  by .NET, then its fragments are submitted **only in a Lua 5.1 mocked
  RiftTextfield**, producing one imported history row with matching text and
  token, no command recall leak and no fictitious disk receipt.
- .NET 10 Release build: 0 warnings, 0 errors.
- RIFT remained running but not foreground; tests sent **zero** Windows keys.

The preflight is not live acceptance of RIFT text entry, not proof of
noncombat Log.txt social chat capture, and not proof of native social-chat
transmission. Those require separate physical receipts.

**No Ollama, OpenCode, Codex CLI or simulated OpenAI subagent was used.**
