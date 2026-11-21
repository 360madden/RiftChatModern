# RCM P0 host observer — deterministic startup event ordering

**Date:** Friday, November 20, 2026 (America/New_York)  
**Verified machine:** AMD-DESKTOP  
**Repository:** `C:\work\RiftChatModern`  
**Scope:** Windows-side `tools/rcm-chat-observer.cjs`, Node regression; **no installed Lua addon change**. Installed in-game release remains `0.2.16`.

## Root-cause defect and red/green proof

The observer's first `LogTailProbe.poll()` intentionally runs before the public `started` receipt to establish a safe log baseline. That poll can synchronously invoke the observer's `readLine` hook if a missing/rotated log has just appeared. The hook emitted `candidate_chat` (or a bounded `raw_log_sample`) immediately, before the caller learned the selected path and readiness state. This violated a useful JSONL lifecycle contract even though the candidate record itself might be valid.

A deterministic child-process regression intercepts only the first **mock** `LogTailProbe.poll()`, feeds one historical Guild candidate and an exact test nonce, and returns a fake `file_opened` plus `matched` receipt. No RIFT client, game log, game input, configuration, or SavedVariables are involved.

**Before fix (RED):** first event was `candidate_chat`, but the test required `started`.  
**After fix (GREEN):** the emitted sequence is:

1. `started` with selected log path and `pathSelection`
2. `file_opened` / other first-poll transport events
3. first-poll `candidate_chat` and optional raw samples, in callback order
4. `matched` if the marker was found in that poll
5. `finished` with `marker_matched`

The observer now buffers bounded initial callbacks only until `started` is emitted. It preserves the initial EOF/missing-file baseline and the existing underlying LuaPadModern decoder. Subsequent polling streams directly without a new queue.

## Verification and boundaries

- **28/28 Node.js tests passed**, including the new child-process startup ordering regression.
- **193/193 Python/Lua tests passed**, including the real Windows PowerShell 5.1 launcher tests.
- `git diff --check` completed successfully (only Git LF→CRLF conversion notices).
- Guarded deployment dry run independently found **10/10 installed RCM v0.2.16 files identical** to source, `changedFiles: []`.
- Read-only physical process/log preflight found `rift_x64.exe` absent and no `Log.txt` in configured and conventional candidate paths. `Rift.cfg` still exposed `LogConsole=False`; its exact live-toggle semantics were **not** established.

This is a **host-event ordering fix**, not evidence that November 2026 RIFT Live writes ordinary Say/Guild/Tell chat to disk or that the current historical parser recognizes its real records. Native RIFT player-chat reception/sending and automatic Windows-to-addon transfer remain unverified. RCM v0.2.16 has not yet received a physical live-load acceptance after its latest deployment.

## Next physical acceptance

When RIFT is running again, capture a fresh PID/HWND, run the read-only preflight, verify existing logging state, then run `tools/rcm-log-probe.ps1` with a unique nonce. The exact `started.path` and `started.pathSelection` must be recorded before intentionally creating a matching game log marker and short social-chat example. Do **not** blindly toggle `/log`: historical RIFT used it as a logging toggle. Use actual current RIFT-produced bytes to adjust any parser formats.

**Development path:** internal ChatGPT coding with the verified AMD-DESKTOP connection; no Codex CLI, Ollama, OpenCode, or claimed independent internal subagents.
