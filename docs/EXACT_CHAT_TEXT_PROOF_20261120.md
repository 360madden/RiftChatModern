# RCM P0 — Exact player-chat text verification after a log marker

**Development date:** Friday, November 20, 2026 (America/New_York)
**Verified workstation:** AMD-DESKTOP
**Repository:** C:\work\RiftChatModern
**Change scope:** Windows host observer and PowerShell wrapper only; installed RIFT addon v0.2.16 is unchanged.

## Problem reproduced

The previously corrected two-phase log observer could verify that a console marker reached the chosen Log.txt and that a *recognized* chat-format line appeared after the chat-stage readiness receipt. However, the first recognized line could have come from any other player or channel. The process could exit with a successful chat candidate even though the user had not yet sent the deliberate test message.

This created a false-positive risk for the central RCM question: does the **physical RIFT MMORPG client** write the specific player-chat line seen in its native window to the monitored noncombat Log.txt?

The original observer also redacts chat bodies by default, so requiring an exact comparison must not force private messages to be printed in the Windows terminal.

## Root-level correction

The Node observer now accepts an optional strict --require-chat-text TEST_TOKEN option. It requires the existing --require-chat-after-marker mode; the token is **8–80 ASCII letters, digits, underscore or hyphen**, and case-sensitive. Invalid, duplicate, incomplete or incorrectly scoped options are rejected.

The existing shared LuaPadModern decoder and the RCM historical-bracket parser are unchanged. The observer compares the complete internally parsed message text to the expected token **before redacting the body**, provided the candidate is not truncated. When a token is required:

- A candidate_chat record includes chatTextMatched=true/false, afterMarker=true and its normal source/channel/sender metadata, but does not output the message body unless the user independently opted into body display.
- Unrelated chat, partial matches, pre-marker content, stale history, or truncated text cannot satisfy the exact proof.
- The observer continues through unrelated candidates instead of returning success on the first one.
- A verified sequence of matching marker → chat_phase_armed → **the exact recognized test line** ends with reason exact_chat_candidate_after_marker and chatTextMatched=true.
- Unmatched candidates before the configured maximum, or a timeout, exit **2** with an explicit reason such as timeout_waiting_exact_chat_after_marker or candidate_limit_without_exact_chat. No false success is claimed at a noisy-chat limit.
- The result always reports transportVerified=false, candidateFormatVerified=false and physicalRiftOriginVerified=false until an independently observed **real running RIFT window and actual game-produced file bytes** corroborate the candidate. Exact matching of a synthetic file does not prove the game's origin.

The PowerShell helper has a matching -RequireChatText TEST_TOKEN argument, and still uses RCM's configured-path observer plus LuaPadModern's read-only decoder. It refuses -RequireChatText unless -RequireChatAfterMarker was specified. Its preview reports expectedChatTextRequired=true but **does not echo the expected text**. No game settings, input, clipboard, SavedVariables or RIFT process were touched.

## Test-first evidence and failures

The new Node child-process regressions initially **failed** because the original observer did not recognize --require-chat-text:

1. A fixture appended unrelated Guild chatter and then the exact intended Say line after chat_phase_armed. The required behavior is two candidate records but success only after the exact one, without revealing the bodies.
2. A fixture appended only unrelated Guild chatter. The required result is a nonzero timeout, not a candidate success.

After implementing the option and pre-redaction comparison, both passed. A third fixture established that reaching the maximum candidate count with **only unrelated messages** returns exit 2 and a distinct candidate_limit_without_exact_chat receipt. Direct option-validation tests cover wrong scope, invalid tokens and duplicate flags.

The PowerShell preview test first **failed** because the launcher did not recognize -RequireChatText. After the change, an actual Windows PowerShell 5.1 invocation passed and reported its expected boolean, tested the correct path/decoder, and did not emit the test token. Invalid-option and isolated fake Rift.cfg tests remain green.

**Full regression results on AMD-DESKTOP: 193/193 Python/Lua, 40/40 Node tests, 233 total.** Git whitespace verification passed (Windows LF-to-CRLF conversion notices only). A separate guarded installer dry run found **zero installed addon changes and SHA-256 matches for all 10 v0.2.16 files**. This is host-side source only; no Lua module or .toc version change was required.

## Two-stage live acceptance command

After RIFT is **actually running** and its logging state is understood, in **Windows PowerShell**, from C:\work\RiftChatModern:

    .\tools\rcm-log-probe.ps1 -Preview -Nonce RCM_MARK_20261120 -RequireChatAfterMarker -RequireChatText RCM_CHAT_EXACT_20261120

Then run the bounded real observer:

    .\tools\rcm-log-probe.ps1 -Nonce RCM_MARK_20261120 -TimeoutSeconds 120 -RequireChatAfterMarker -RequireChatText RCM_CHAT_EXACT_20261120

Use the actual nonce shown in the observer's started receipt. In RCM's own **in-game editor**, manually enter:

    :logprobe RCM_MARK_20261120

Wait for the external observer to show both matched **and chat_phase_armed**. Only then, in the game's **original native chat input** field, send:

    /say RCM_CHAT_EXACT_20261120

Compare the native chat line as seen in the running game with the observer's source/path/channel/sender and chatTextMatched=true record. This should be recorded with a fresh RIFT PID/window identity. If the game's actual Log.txt format differs from the historical bracket parser, the result remains inconclusive; deliberately enabling limited -SampleRawLines can reveal current record structure, but can expose private chat, so raw samples should not be committed to a public repo.

**Never blindly type /log**: historical RIFT uses it as an enable/disable toggle. The earlier observed Rift.cfg contained LogConsole=False but its runtime meaning has not been demonstrated. The current physical game has not yet emitted a confirmed chat Log.txt record in this development cycle.

## Remaining actual product gaps

1. Independently prove *physical* Say/Guild/Party/Tell/public chat is observable from the current RIFT client, including the actual file encoding and record shape.
2. Establish a reliable host-to-addon transport for automatic inbound chat. The installed addon can accept **manual** host imports but no automatic verified Windows-to-Lua channel currently exists.
3. Implement separately verified ordinary social-chat sending and finish visual focus/drag/resize testing before the original RIFT chat can safely be replaced.

The helper only improves the integrity of the physical experiment. No Ollama, OpenCode, Codex CLI or invented internal ChatGPT subagents were used.
