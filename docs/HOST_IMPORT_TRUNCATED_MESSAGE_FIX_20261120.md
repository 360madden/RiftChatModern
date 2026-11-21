# Rift Chat Modern — Complete-message-only host import

**Development date:** Friday, November 20, 2026, approximately 8:39 PM EST  
**Verified host:** AMD-DESKTOP  
**Repository:** `C:\work\RiftChatModern`  
**Installed addon:** v0.2.16 (unchanged by this host-only correction)

## Root cause

RCM's Windows candidate observer limits its displayed chat body to **512 UTF-8 bytes** while preserving a `textBytes` count for the original decoded line and `truncated=true` when the original body was longer. This is an intentional bound for read-only observation and output.

However, two other paths treated that shortened preview as though it were the original full player-chat message:

- `tools/rcm-chat-observer.cjs --prepare-import` passed the truncated candidate into `encodeRecord`, producing manually pasteable `/rcm import` commands.
- `tools/rcm-chat-import.cjs --stdin-json` similarly accepted candidate JSON records with `truncated=true` and a shortened `text`.

The RCM core and manual host-ingress decoder already cap a single message body at 512 bytes; the issue was *silent loss of source text*, not an inability to encode the preview. This matters for a chat replacement because history would inaccurately represent an incomplete message as complete.

## Test-first evidence

Regression fixtures reproduced the failure **before the fix**:

1. A synthetic Guild log line containing 130 green-clover emojis (520 UTF-8 bytes) was reduced to the correct Unicode-safe 512-byte prefix, but the encoder unexpectedly accepted it.
2. The CLI imported a `truncated=true` JSON candidate rather than returning a nonzero result.
3. A real child-process observer with `--prepare-import` produced two imported-command records—one for that incomplete message and one for an unrelated complete Party message—rather than skipping the incomplete one.

Those failures proved actual data loss within our synthetic host pipeline. No live RIFT message was used or claimed.

## Corrected behavior

- The shared `encodeRecord` boundary now rejects an input if `truncated===true`, or if a valid original `textBytes` count exceeds the bytes present in `text`, even when the flag says `truncated=false`.
- `--stdin-json` gives a typed `{"event":"import_skipped","reason":"truncated_chat_body"}` response for such records, increments its skip count, and returns exit code **2** when any record is skipped.
- The observer's opt-in `--prepare-import` branch now emits the same clear skip reason for incomplete records instead of outputting a misleading manual import command.
- Complete later records remain importable. The ordinary metadata-only observer continues to report candidate count, `textBytes` and `truncated` without exposing private message bodies.

The fix **does not fabricate missing text**, make a network request, change RIFT's native chat, enable logging, modify SavedVariables or automatically send input to RIFT.

## Current limits and next technical step

The current manual-ingress protocol supports up to 12 command chunks, an overall 780-byte decoded record, and a **512-byte chat body**. This correction intentionally refuses a longer source message rather than silently storing a prefix. Supporting complete longer messages later will require a coordinated, separately tested revision of the model, wire format and UI, not a change to the observer's preview limit alone.

Also, the actual physical RIFT client has not yet produced a verified normal Say/Guild/Party/Tell line in the observed noncombat Log.txt. The next P0 test remains the two-stage `-RequireChatAfterMarker` live procedure documented in `CHAT_OBSERVER_TWO_PHASE_20261120.md`. A host parser match or successful import of synthetic text does not establish native chat reception.

## Verification and artifact boundary

- **RED:** Three regression tests failed against the old importer/observer.
- **GREEN:** The same tests pass after the fix, including Unicode-safe length detection, typed skip reporting, and continued acceptance of complete subsequent records.
- **193/193 Python/Lua** and **37/37 Node** tests passed (**230 total**).
- `git diff --check` passed with only standard Windows line-ending notices.
- A separate guarded deploy dry run confirmed source/installed RCM **v0.2.16, all 10/10 files matching**, with no pending addon changes.
- No addon metadata, RIFT Lua code, character data or LuaPadModern source was changed in this milestone.

No Ollama, OpenCode or Codex CLI was used; no synthetic chat record was represented as a real game capture.
