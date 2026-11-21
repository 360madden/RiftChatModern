# RCM P0 — Two-phase social chat observation

**Date:** Friday, November 20, 2026 (America/New_York)
**Verified workstation:** AMD-DESKTOP
**Repository:** C:\work\RiftChatModern
**Scope:** Host observer and PowerShell launcher only. Installed RIFT Lua addon remains v0.2.16.

## Root cause and correction

RCM previously stopped its noncombat Log.txt observer as soon as the LPB_PROBE nonce was found. This was insufficient for a real chat-source experiment: the shared LuaPadModern LogTailProbe permanently stops consuming additional lines after a match. Simply leaving that reader running would never capture a later player-chat line.

The host observer now accepts the optional **--require-chat-after-marker** flag. Its two-stage operation is:

1. Emit a started receipt containing the exact log path and path-selection provenance; ignore historical content and pre-marker chat for the second-stage result.
2. Find the exact matching LPB_PROBE marker, emit matched, close the now-consumed tailer, reopen a **fresh** tailer at that file's current end and then emit **chat_phase_armed**.
3. Accept only a newly appended recognized candidate_chat line after chat_phase_armed. That line is flagged afterMarker=true; actual chat text is omitted unless explicitly requested.
4. Complete with finished.reason=chat_candidate_after_marker and chatCandidatesAfterMarker>=1, but **never claim verified live social-chat transport solely from this result**. The historical log format and physical RIFT origin still require an actual game session and independent correlation.

A repeated marker during the second stage causes another explicit chat_phase_rearmed state, rather than freezing the tailer. If the source is replaced, truncated, disappears or produces a read error after the marker, the process now exits **2** with reason chat_source_changed_after_marker. Candidate callbacks are held until each poll has reported its source-identity events, so text from a rotated file cannot produce a false second-stage pass.

Timeout while awaiting a post-marker candidate also exits **2**. If raw-line discovery (opt-in only) sees unrecognized text, it exits **2** with raw_sample_limit_without_chat_candidate; this is *not* proof of live player-chat reception.

The PowerShell wrapper now forwards **-RequireChatAfterMarker** and displays the required chat_phase_armed instruction in its preview. It still uses RCM's configured-path observer, which itself reuses LuaPadModern's mature read-only decoder. No new tailer was duplicated.

## Validation with failures preserved

Three new child-process two-phase tests initially failed because the original observer rejected the new argument. After implementation, tests passed for fresh after-marker chat, ignoring pre-marker candidates, and refusing to classify unknown raw text as verified social chat.

A fourth test reproduced a real flaw: truncating the temporary Log.txt after the marker previously led to a timeout, not an explicit source invalidation. The corrected reader now refuses the changed source with exit 2. A fifth test verifies that a replaced file containing a fresh-looking Guild line **in the same poll as the reset** cannot forge a chat result. A sixth test passes for repeated-marker rearming and subsequent successful chat.

PowerShell 5.1 launcher tests were extended for the new flag, including an actual PowerShell-to-Node run with an isolated temporary RIFT.cfg. The existing observer startup-order regression (developed separately in the same working tree) also passes.

**Full automated verification:** 193/193 Python/Lua tests and 34/34 Node.js tests, **227 passing**. Git diff check passed without whitespace errors. The installer dry run reports **10/10 installed v0.2.16 files matching source, zero changed files**. No actual game input, restart, logging toggle, character SavedVariables edit or addon redeployment occurred.

## Supervised physical acceptance

A future in-game trial should use **Windows PowerShell** with C:\work\RiftChatModern as the current directory:

    .\tools\rcm-log-probe.ps1 -Preview -Nonce RCM_P0_20261120 -RequireChatAfterMarker
    .\tools\rcm-log-probe.ps1 -Nonce RCM_P0_20261120 -TimeoutSeconds 120 -RequireChatAfterMarker

After started identifies the intended file, enter **:logprobe RCM_P0_20261120** in RCM's own in-game editor. Wait until matched **and chat_phase_armed** appear in the Windows terminal. Only then type a new short test line, e.g. **/say RCM_P0_TEST_20261120**, in the original RIFT chat field. Correlate the actual game window, file path and candidate record; do not infer verified native social-chat reception from the marker alone.

If current RIFT uses an unknown log format, a deliberately authorized run can add **-SampleRawLines 3** to capture at most three newly appended decoded lines after the marker. These samples can contain private chat and must not be committed into a public repository.

RIFT's **/log** is historically a toggle; do not use it without establishing the current game logging state. The last observed RIFT.cfg contained LogConsole=False, but its exact live semantics remain unverified.

## Remaining blockers

The actual physical RIFT client has not yet produced a confirmed player Say, Guild, Party, Tell or public-chat record in a noncombat Log.txt in this development cycle. Host readback, even if subsequently proven, still needs an automatic host-to-RCM Lua input path and a separately validated native social send route. The installed v0.2.16 addon also awaits its new physical visual acceptance.

No Ollama, OpenCode or Codex CLI was used. No independent OpenAI worker was claimed without a genuine worker-spawn capability.
