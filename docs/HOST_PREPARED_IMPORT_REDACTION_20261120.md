# RCM — Prepared host-import output no longer duplicates chat bodies

**Engineering date:** Friday, November 20, 2026, approximately 9:25 PM EST (America/New_York)
**Verified machine:** AMD-DESKTOP
**Repository:** C:\work\RiftChatModern
**Installed addon:** v0.2.17, unchanged (host-only correction)

## Root cause

RCM has one bounded manual host-ingress protocol (RCM1-B64URL), with native /rcm import and RCM-owned :import editor forms. The Windows observer can prepare either form from complete candidate social-chat records found in noncombat Log.txt.

Before this correction, opting into --prepare-import implicitly forced --include-text=true. Each candidate therefore appeared twice in the observable JSONL stream: as the full candidate_chat.text and as the reversible encoded bytes inside rcm_manual_import.commands. This duplicated bodies unnecessarily and violated the expected metadata-only default for candidate observation.

## Corrected design

The existing LuaPadModern file reader and the RCM historical-bracket parser are unchanged. The existing encoder remains the single producer for both import command forms.

1. The --prepare-import flag and --include-text flag are now **independent**. The former prepares manual command(s), while only the latter exposes candidate_chat.text.
2. The attachChatObserver callback passes a second **internal, complete candidate record** alongside the ordinary redacted observation event. The internal candidate feeds encodeRecord; the public event can remain metadata-only.
3. The two-phase marker/readiness gate retains each pending redacted event together with the internal candidate. It refuses to emit/import pre-marker candidates or candidates from a replaced/truncated log, preserving exact source identity tests.
4. No truncated chat line is silently encoded as a complete message. UTF-8, record limits, token identity, source labels, and default native versus requested editor output remain intact.
5. The output still explicitly reports automaticGameInput=false and liveGameDeliveryVerified=false. This does not implement a Windows controller or automatic delivery into RIFT.

**Boundary:** Prepared rcm_manual_import.commands intentionally contain reversible Base64URL message text. This fix removes duplicate *plain-text* events, not the content necessary to paste an encoded command. --include-text remains available as a separate explicit opt-in.

## Red/green evidence

- Red: Node child-process fixtures showed started.includeText=true even though the caller only requested --prepare-import. The full original candidate_chat.text was printed in both native and editor input modes.
- Red: A truncated candidate's shortened 512-byte preview appeared in the event stream without explicit include-text, although no import command was generated for that incomplete source.
- Green: After separating the private encoder payload from the public observation event, the same tests passed. An explicit --include-text + --prepare-import fixture also passed to prove independent behavior.
- Two additional real child-process fixtures passed for editor-target command preparation only *after* the marker and chat_phase_armed receipt, and refusal to produce commands after a file reset, even when it contained a plausible newly appended Guild line.
- All existing JavaScript/PowerShell and Python/Lua tests remained green. Full suite: **196/196 Python/Lua tests and 47/47 Node.js tests, 243 total**.
- git diff whitespace validation returned exit code 0 with ordinary Windows LF-to-CRLF conversion notices.
- The guarded deploy dry-run found **all 10 installed v0.2.17 files match source**, with changedFiles=[]; no addon redeployment is required.

## Live acceptance boundaries

The current RIFT client remains closed. Its persisted configuration records LogConsole=False; the exact configured Log.txt has not produced a verified current-game social-chat sample. An on-disk game log source, actual RCM-editor focus/Enter, and an automatic host-to-Lua delivery path remain unverified.

Manual host observer invocation, after deliberate noncombat logging setup and game launch, from Windows PowerShell in C:\work\RiftChatModern:

    .\tools\rcm-log-probe.ps1 -Nonce RCM_SOURCE_20261120 -TimeoutSeconds 120 -PrepareImport -InputMode editor

That command *prepares* manually pasteable :import lines from candidate chat, and does **not** inject keys, focus RIFT, toggle /log, or claim native social chat reception. Do not confuse synthetic historical bracket fixtures with actual physical RIFT chat.

No Ollama, OpenCode, or Codex CLI was used. No internal ChatGPT subagent was claimed without a real spawn capability.
