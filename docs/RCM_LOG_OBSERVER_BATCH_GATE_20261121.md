# RCM P0 — Exact-chat observer → editor batch gate

**Date:** Saturday, November 21, 2026 · 1:43 AM EST  
**Machine:** AMD-DESKTOP · `C:\work\RiftChatModern`  
**Scope:** Windows/Node host workflow; installed RCM addon remains v0.2.19

## The integration gap

The existing RCM host observer emits **JSON lines**: a start receipt,
marker receipt, chat-phase arming, candidate chat metadata, optionally a
prepared `rcm_manual_import` batch, then a final receipt. The .NET 10
editor batch validator correctly accepts **one complete JSON batch**, not
a stream of unrelated events. Piping the complete observer stream into it
was therefore not a working input contract.

`tools/rcm-chat-batch-gate.cjs` now selects the **one** complete prepared
editor batch associated with an exact matched test candidate. It is a
bounded, input-free bridge between the existing observer and the existing
.NET batch preflight. It does not replace the LuaPadModern log decoder,
the RCM observer, the Node encoder, or the .NET sender validator.

## State machine and boundaries

It requires, in order:

1. A `started` record declaring two-phase observation, an exact text
   requirement, prepared imports, and `inputMode=editor`; its native
   input and transport proof fields must remain false.
2. A log `matched` nonce and one `chat_phase_armed` receipt. An
   intentionally selected log file may appear before this marker.
3. Exactly one post-marker, **nontruncated** `candidate_chat` with
   `chatTextMatched=true`. Unrelated candidates and their prepared
   payloads are ignored, rather than accidentally forwarded.
4. The immediately following `rcm_manual_import` editor-mode batch.
   Its encoded bytes are validated independently by the .NET receiver.
5. A final successful `exact_chat_candidate_after_marker` receipt,
   confirming the marker, chat phase and exact match while still
   reporting `transportVerified=false` and
   `physicalRiftOriginVerified=false`.

No output is produced for incomplete, ambiguous, duplicated, late,
truncated, reset, malformed or excessive observer data. Input is limited
to 512 KiB overall, 16 KiB per line and 150 parsed records, checked
**while streaming**. No chat line is echoed in diagnostics.

The optional `--status` prints **sanitized live readiness instructions
to stderr** (never the actual message body) as the observer runs, so a
PowerShell pipeline does not hide the marker and chat-phase prompts.
The sole stdout payload, if successful, is the matching Node encoder JSON
record. Other events never reach the .NET import input.

## Offline testable pipeline

With actual logging independently enabled and the intended physical
RIFT client verified, the supervised test can be run from **PowerShell**
in `C:\work\RiftChatModern`:

```powershell
node .\tools\rcm-chat-observer.cjs --nonce RCM_GATE_20261121 --require-chat-after-marker --require-chat-text RCM_CHAT_TEST_20261121 --prepare-import --input-mode editor --timeout-ms 120000 |
  node .\tools\rcm-chat-batch-gate.cjs --status |
  dotnet .\tools\RcmEditorSender\bin\Release\net10.0-windows\RcmEditorSender.dll --stdin-batch
```

This is **validation-only** and sends **no input to the game**. The gate
prints when the observer starts; enter the instructed `:logprobe` nonce
into RCM's focused editor. Only after `chat_phase_armed`, enter the
**exact** chosen test string into RIFT's original native chat field.
A successful source-to-gate pass yields `batch_validated_no_input`.

A deliberate, separately authorized typing action would require the
.NET sender's `--send` plus all original pins and the explicit
focus/submit/batch acknowledgments; it is intentionally **not** part of
this command. Even if Windows input is inserted, the in-game history
receipt and on-disk SavedVariables checkpoint remain separate proofs.

## Findings and test evidence

- Nine initial selector regressions passed for source ordering, exact
  candidate selection, unrelated chat, missing/repeated events, source
  resets, status claims and malformed/bounded input.
- A streaming-status regression first exposed an accidental double-escaped
  newline delimiter introduced in the new CLI. The root cause was fixed
  in the parser (and the test fixture), rather than hiding the failure.
- **11 selector tests pass**, including a test that receives a status
  indication **before the observer stream ends**.
- A complete synthetic path is tested from observer-style JSONL, through
  the selector and .NET batch validator, then into RCM's Lua 5.1 mock
  editor. The result is the one selected imported message with exact text
  and transfer token, no unrelated import, and no fabricated disk receipt.

**Physical status:** RIFT was running on AMD-DESKTOP but not foreground
during development, and the last preflight found `LogConsole=False` and
no configured `Log.txt`. No native player-chat logging or automatic
RIFT import has been physically demonstrated. No game input, log toggles,
SavedVariables writes, addon deployment or game-memory edits were made
by this host-only work.

No Ollama, OpenCode, Codex CLI or simulated ChatGPT subagents used.
