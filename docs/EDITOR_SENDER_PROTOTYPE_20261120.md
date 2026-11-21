# RCM editor sender prototype — Windows-to-addon boundary

**Engineering date:** Friday, November 20, 2026 (America/New_York)  
**Machine:** AMD-DESKTOP  
**Project:** `C:\work\RiftChatModern`  
**Addon package:** v0.2.19 (unchanged by this companion)  
**Runtime:** .NET 10, Windows only

## Why this exists

The RCM-owned RiftTextfield supports the `:import TOKEN PART/TOTAL BASE64URL`
local command and the HostIngress receiver has a shared, bounded transport.
Previously, the Windows host could only **prepare** a candidate command for a
human to type or paste. This helper is an opt-in prototype for the *final input
boundary*; it is not a native player-chat source and cannot establish game
delivery without an independent in-game receipt.

The sender and the existing **read-only** preflight use the exact same
`RcmImportContract` parser, moved without altering its strict protocol bounds
into `tools/RcmEditorInput/ImportContract.cs`. The read-only preflight remains
free of Windows keyboard APIs. The sender is built as its own .NET 10 executable.

## Operation and guardrails

- **Default is validation only.** Supply one bounded `--command` or
  `--stdin-command`; output contains a SHA-256 and chunk metadata, never a
  full chat payload. No keyboard or clipboard access.
- **Explicit send requires `--send --ack-editor-focused`** plus six exact game
  identity pins: host, PID, root HWND, process start UTC ticks, executable path
  and executable SHA-256. This is an operator acknowledgment, **not** machine
  verification of RiftTextfield focus.
- Before inserting, the helper requires the pinned RIFT foreground window,
  class/title, owning process, session, epoch and executable. These checks
  repeat per character; Ctrl/Alt/Shift/Win held down causes refusal.
- It uses one Unicode key down/up pair for each ASCII `:import` character.
  It neither activates windows nor changes the clipboard. A separate
  `--submit --ack-submit` pair is necessary to attempt Enter.
- On partial input or a changed game identity, it refuses automatic retries,
  reports the input as **partial or unknown**, and asks for manual inspection.
  This avoids doubling or completing an uncertain import.
- Insertion, in-game reception, a saved history row and disk persistence are
  separate evidence levels. The sender never claims the latter three.

## No-input verification

From **PowerShell**, with the repository as the working directory:

```powershell
dotnet build .\tools\RcmEditorSender\RcmEditorSender.csproj -c Release
dotnet run --project .\tools\RcmEditorSender\RcmEditorSender.csproj -- --self-test
dotnet run --project .\tools\RcmEditorInput\RcmEditorInput.csproj -- --inspect
dotnet run --project .\tools\RcmEditorSender\RcmEditorSender.csproj -- --command ":import ABCDEF123456 1/1 QUJDRA"
```

The last command only validates a synthetic test transfer. Real message input
should use `--stdin-command` so that encoded text does not enter command-line
arguments. The send path additionally requires the six exact pins returned
by inspection, deliberate focus of **RCM's own editor** inside RIFT, and an
explicit send/submit authorization. Never infer focus from a foreground title.

## Verification receipts (November 20)

- .NET 10 `RcmEditorInput` and `RcmEditorSender` builds: **0 errors/warnings**.
- Sender input-free self-test: **12 passed**.
- New `tests/test_editor_sender.py`: **7 passed**, including no-input
  validation, single-line stdin, missing acknowledgment, wrong host and
  stale fake HWND. Tests deliberately do **not** execute a valid send.
- Full existing plus new suite: **240/240 Python/Lua tests passed**.
- Host encoder/observer suite: **47/47 Node.js tests passed**.
- Total: **287 passing**, no skipped tests under the Lua-enabled
  `C:\work\riftreader2\.venv\Scripts\python.exe`.

**Physical game acceptance:** pending. No keyboard events were sent to RIFT by
this prototype during the verification described here. Even a successful
Windows SendInput count would not prove that RCM accepted a fragment.

**Separate addon release:** v0.2.19 fixes an import idle-deadline defect and
can be installed while RIFT is running; `/reloadui` activates installed addon
changes. This companion does not alter `RiftAddon.toc`, any SavedVariables,
or RIFT game files.

No Ollama, OpenCode or Codex CLI used.

## Later cross-component proof — 11:50 PM EST

Added `tests/test_editor_sender_roundtrip.py` to connect all three actual
implementations end-to-end **without Windows input**: the Node `--input-mode
editor` encoder, the .NET 10 sender in validation-only mode, and the Lua 5.1
mock RiftTextfield calling the real `:import` receiver.

The single-fragment Guild test verifies SHA-256, zero game input, exact text,
provenance, preserved import token, one assigned history ID, no command-recall
pollution and no fabricated disk-save proof. A multiple-fragment UTF-8 Party
test verifies each ordered encoded part against the sender and the actual Lua
importer, including exact reconstructed text and replay idempotence.

**Failure preserved:** The first generated Party fixture exceeded the real
encoder's **512-byte text ceiling** and was correctly rejected as invalid
source. The fixture was corrected to fit the documented transport bound,
without weakening the encoder. Both cross-component tests then passed.

These two tests raise the full Python/Lua suite from 240 to **242** and combined
Python/Lua + Node coverage from 287 to **289**, subject to full-suite rerun.
No test sent any key into physical RIFT. Successful host-to-client delivery
remains a separate live acceptance criterion.
