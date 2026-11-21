# RCM host observer — RCM-owned editor import output mode

**Development date:** Friday, November 20, 2026 (America/New_York)  
**Verified host:** AMD-DESKTOP  
**Canonical repo:** C:\work\RiftChatModern  
**Installed game addon:** v0.2.17; unchanged by this host-only extension

## Purpose

The physical addon now has a bounded :import transfer command in its **own focused editor**, reusing precisely the same RCM1-B64URL HostIngress decoder and persisted token identity as the old native /rcm import input. However, the separate Windows Log.txt observer's opt-in --prepare-import feature still emitted native /rcm commands only. A real host observation would therefore force manual conversion or re-entering text in the original RIFT chat, despite RCM having its own route.

This change wires the host-side producer to the new editor-side consumer. It does **not** pretend the transport is automatic or that the ordinary native player-chat stream has been proven in the current client.

## Implemented in existing host tools, no new decoder

- tools/rcm-chat-observer.cjs now recognizes **--input-mode editor** or **--input-mode native** when and only when **--prepare-import** is explicitly present. Its default, with no mode override, remains native for backward compatibility. Invalid, duplicate or unpaired options are rejected.
- The observer passes the mode to the **existing** tools/rcm-chat-import.cjs encoder, already used by the v0.2.17 installer and verified to yield equivalent message bytes and transfer IDs. In editor mode candidate records produce manually pasteable **:import TOKEN INDEX/TOTAL BASE64URL** commands. Native mode still emits **/rcm import TOKEN INDEX/TOTAL BASE64URL**.
- The JSONL started receipt now identifies the opt-in inputMode; without prepareImport it is null. Event rcm_manual_import retains automaticGameInput=false, requiresManualEntry=true and liveGameDeliveryVerified=false.
- The same conservative message-quality boundary still applies: a truncated original chat body causes import_skipped: truncated_chat_body instead of silently saving a prefix. Historical bracket parser matches remain unverified until actual RIFT client bytes are observed.
- tools/rcm-log-probe.ps1 now exposes **-PrepareImport -InputMode editor** as an explicit choice. Without -PrepareImport, specifying -InputMode is rejected. Preview reports prepareImport/inputMode and warns that generated commands carry **encoded chat text**. It never sends input, edits the configuration, or enables game logging.
- The observer continues to reuse LuaPadModern's established read-only noncombat log decoder; the LuaPadModern repo and currently installed RIFT addon were not modified.

## Red/green test evidence

A new real Node child-process fixture first failed on the old observer because --input-mode was not understood. The new validation test also failed because a mode override could not be parsed. After wiring the mode to the existing encoder, both passed. The child-process test confirms the command prefix is exactly :import, the decoded wire payload remains identical to the candidate's complete message and sender/channel, and no game input or claimed delivery is reported.

A new Windows PowerShell 5.1 preview test first failed because -PrepareImport was unsupported. The updated launcher passed both its preview and a separate actual Windows PowerShell → Node timeout test against an isolated temporary Rift.cfg with -PrepareImport -InputMode editor. The emitted started event carried prepareImport=true and inputMode=editor, proving the option traversed the real wrapper, not only a mocked argument object. The test used no physical RIFT session.

**Full checks: 196/196 Python/Lua tests plus 44/44 Node.js tests = 240 passing.** git diff whitespace validation exited 0. A separate deploy_rcm.py dry run found changedFiles=[] and hashVerified=true for all **10 installed v0.2.17 files** on AMD-DESKTOP; there was no reason to reinstall or bump the game addon.

## Operator commands

Start with a no-input preview from **Windows PowerShell** in C:\work\RiftChatModern:

    .\tools\rcm-log-probe.ps1 -Preview -Nonce RCM_SOURCE_20261120 -PrepareImport -InputMode editor

When RIFT is physically running and its noncombat logging state is independently established, use a bounded observer (examples show behavior; **not yet live accepted**):

    .\tools\rcm-log-probe.ps1 -Nonce RCM_SOURCE_20261120 -TimeoutSeconds 120 -PrepareImport -InputMode editor

The observer will print **rcm_manual_import** records with commands beginning :import if the historical candidate parser recognizes a **complete** newly appended line. Copy each command to **RCM's own focused editor** and press Enter. Neither the observer nor the wrapper types into RIFT, activates focus, uses the clipboard or captures native social-chat messages by itself.

For a controlled first proof of a **specific** game-produced Say line, prefer the prior two-stage and exact-text observer in metadata-only mode:

    .\tools\rcm-log-probe.ps1 -Nonce RCM_MARK_20261120 -TimeoutSeconds 120 -RequireChatAfterMarker -RequireChatText RCM_CHAT_EXACT_20261120

Wait for started → matched → chat_phase_armed before sending the exact test text in the **original RIFT chat box**. Only after independently confirming the actual RIFT log format and path should opt-in chat-body import preparation be considered useful for normal operation.

The persisted RIFT config currently records LogConsole=False, the configured noncombat Log.txt does not exist, and RIFT was closed during this work. These observations do not prove runtime logging state or social-chat capture. **Do not toggle /log blindly**: the actual November 17 executable implements an on/off routine, with potentially private noncombat log output on disk.

## Remaining product acceptance

Physical GUI focus/keyboard acceptance of v0.2.17's :import field, an actual game-created chat Log.txt record, exact sender/channel mapping, and automatic Windows-to-Lua delivery are all separate unresolved steps. Host-side generation of copyable commands is **not automatic delivery**. RCM must retain its native chat fallback until real native receiving and sending are proven independently.

No Ollama, OpenCode, Codex CLI, or fabricated internal subagent was used.
