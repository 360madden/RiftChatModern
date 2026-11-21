# RiftChatModern — Saturday Engineering Handoff

**Date:** Saturday, November 21, 2026 (America/New_York, EST)  
**Project:** RCM — Rift Chat Modern, RIFT Live Lua 5.1 addon with optional Windows host companions  
**Canonical repo:** C:\work\RiftChatModern  
**Verified machine:** AMD-DESKTOP, Workbridge 0.16.5-dev  
**Branch / remote:** main → origin, https://github.com/360madden/RiftChatModern  
**Current installed in-game addon:** v0.2.23, unchanged by later Windows-only helper work.

> **POST-HANDOFF UPDATE (later November 21):** This document is the historical 16:20 EST handoff. The previously pending coordinator P0 was subsequently **physically accepted** with a real Say import and exact disk token. See [the coordinator acceptance](COORDINATOR_PHYSICAL_ACCEPTANCE_20261121.md) and [new verified public-channel log format](LIVE_PUBLIC_CHANNEL_LOG_FORMAT_20261121.md) before following the older P0 steps below. Unattended continuous social interception and native social sending remain unverified.

## 1. Goals and current boundaries

RCM is intended to provide a modern compact dark chat-style UI with legible fonts, mouse drag, bottom-right resize, focus indicator, local-second timestamps, separate colored message columns, history, search, detail, copy, filters, native console inspection, saved geometry, character SavedVariables, and an addon-to-addon diagnostics/command API. Visual preference: lean modern webpage styling, not ornate RPG chrome. Preserve clear initialization message and displayed version.

History tabs: ALL / IMPORTS / NOTICES / NPC SAY / ADDONS / DEV / CONSOLE. Removed the deceptive CHAT tab because it only duplicated host imports. Historical :filter chat alias means Imports. The CONSOLE tab shows actual read-only subscription settings, not native player-chat message text.

The RIFT addon API review established: Inspect.Console.List/Detail retrieves IDs and settings, NOT transcripts; Event.Chat.Npc and Event.Chat.Notify concern NPC speech and notifications; Event.Message.Receive and Command.Message.Send are addon-data transport, NOT ordinary social-message interception or sending. Guild/Party/Tell/public-channel current-client log formats remain unverified. Keep host-imported rows visibly labeled HOST and retain native RIFT chat as fallback. See V0_2_22_NATIVE_RIFT_CONSOLE_CATEGORIES_20261121.md.

## 2. Verified state and evidence

| Area | Evidence / limitation |
|---|---|
| In-game addon | v0.2.23 installed and physically observed; shows HOST/SAY for imported real Say |
| Modern UI | Drag, resize, editor focus, responsive columns, navigation and persistence physically tested in v0.2.20–0.2.21 |
| Native CONSOLE | v0.2.22 game/loot/player/channel/combat settings physically checked against RIFT console, read-only |
| Real player chat | ONE real Say line from a game-created noncombat Log.txt physically verified |
| Previous end-to-end import | Real Say -> parser -> .NET editor submission -> RCM IMPORTS row -> /reloadui -> exact matching SavedVariables import token physically verified |
| New bounded follower | Host-only, newly appended newline-complete Say log lines, rolling integrity checks; synthetic tests pass; physical read-only log smoke found zero new Say |
| New serialized delivery | Queued batch, one claimed transfer, .NET sender preflight, explicitly pinned dispatch, exact-token disk auditor; synthetic integration and fake-target refusal pass |
| New coordinator live acceptance | **PENDING**: no new supervised successful game delivery or disk verification via coordinator |
| Full unattended social chat | **NOT IMPLEMENTED**, and no verified native Lua social sending/interception |

The physically observed RIFT Say log line has the redacted structure:

    HH:MM:SS: [Speaker] says: message

The parser tags the narrow format as rift-live-2026-say, channel Say, family general. The bracket contains the speaker, not a channel name. Log timestamps in the one physical test were five hours different from the displayed native chat time; preserve raw log timestamps rather than invent timezone conversion.

**Do not misstate:** historical two-/three-bracket Guild/Tell/Party fixtures are not confirmed 2026 native RIFT output. An observer's syntactic match alone is not proof of process origin. .NET SendInput results alone are not proof that the addon accepted an import. The game Save.Begin callback alone is not proof SavedVariables were written.

## 3. Recent Saturday commits

| Commit | Result |
|---|---|
| 5a95d0e | RCM v0.2.23: one physically proven live Say log-to-editor-to-disk import and corrected HOST/SAY subtype |
| f899a73 | Bounded read-only Say log follower with new-only EOF behavior, rolling integrity checkpoint and offline tests |
| eee37e0 | Serialized private host delivery journal, one claimed transfer, pinned .NET dispatch, exact-token disk receipts and integration tests |

**Last verified full suite at eee37e0:** 315 Python/Lua and 94 Node.js = **409 passing tests, zero failures**. .NET 10 Release sender build: zero warnings/errors. Deploy dry-run: 23 installed source files hash-match v0.2.23, zero changes, zero SavedVariables edits, zero game input. Windows helper work does not change the in-game addon version or require /reloadui.

### Commands (PowerShell, on AMD-DESKTOP)

    cd C:\work\RiftChatModern
    & "C:\work\riftreader2\.venv\Scripts\python.exe" -m unittest discover -s tests
    node --test tests/test_chat_import.cjs tests/test_chat_observer.cjs tests/test_chat_observer_cli.cjs tests/test_chat_batch_gate.cjs tests/test_live_say_batch.cjs tests/test_live_say_follow.cjs tests/test_say_delivery.cjs
    dotnet build tools/RcmEditorSender/RcmEditorSender.csproj -c Release --nologo
    & "C:\work\riftreader2\.venv\Scripts\python.exe" tools/deploy_rcm.py
    node tools/rcm-say-delivery.cjs status

The last read-only private coordinator status returned revision 0 and empty session/queue counts. **Reread current state**; never assume it remains unchanged in a subsequent conversation.

## 4. Source ownership / architecture

### RIFT Lua addon

- addon/RiftChatModern/RiftAddon.toc: manifest including mandatory Identifier, Email, Version, Environment, ordered RunOnStartup, character SavedVariables.
- Core.lua / Main.lua: model, UI, history, local commands, provenance, timestamp and subtype display, save state.
- HostIngress.lua: RCM1-B64URL import receiver, strict multipart validation, importToken retention and duplicate protection.
- ConsoleCategories.lua / NativeChatProbe.lua: read-only game settings, not native social transcripts.
- AddonMessages.lua / ConsoleMirror.lua: diagnostics, local addon transport.

### Windows side

- tools/rcm-chat-observer.cjs: parse one real 2026 Say syntax; other social syntaxes remain historical candidates.
- tools/rcm-live-say-batch.cjs: exact source-hash-pinned one-message test converter.
- tools/rcm-live-say-follow.cjs: bounded new-only Say follower. Uses existing sibling C:\work\LuaPadModern\tools\rift-log-probe.cjs decoder.
- tools/rcm-chat-import.cjs: canonical multipart RCM1-B64URL encoder, no input by default.
- tools/rcm-say-delivery.cjs: coordinator entry point (capture/status/preflight/claim/dispatch/verify-disk/cancel/recover).
- tools/rcm-say-delivery-state.cjs: private journal with single-in-flight claim, lock, atomic writes, encoded batch validation, SHA-256 integrity checks.
- tools/RcmEditorSender: .NET 10 Win32 sender, dry-run by default; game input only with explicit acknowledgments and exact freshly verified window/process/executable pins.
- tools/rcm_disk_receipt.py: read-only exact character SavedVariables token and checkpoint proof.
- tools/deploy_rcm.py: guarded install to actual verified AddOns folder, dry-run default, hash checks.

Flow:

    RIFT Log.txt, newly appended game Say
         -> bounded host follower
         -> redacted observation + validated RCM1 editor batch
         -> private journal, queued
         -> .NET preflight, zero input
         -> one explicit claimed/dispatch transfer with pinned RIFT window
         -> independently observe one RCM IMPORTS HOST/SAY row
         -> normal in-game /reloadui
         -> independent exact-token SavedVariables disk audit
         -> disk_saved status

The new journal defaults to artifacts/rcm-private-queue/rcm-say-delivery.json (excluded by .gitignore). The contents are **encoded, NOT encrypted**, and can reveal message bodies and character names. Never publish or attach it. Queued -> claimed -> disk_saved (or cancelled). Failed/ambiguous capture -> quarantined. **There is no claimed -> queued retry.** In uncertain input cases, the transfer remains claimed until independently resolved. The exclusive .lock must not be forcibly removed without confirming the owning process is gone.

Detailed contract: [Serialized delivery coordinator](SAY_DELIVERY_COORDINATOR_20261121.md). Follower: [Bounded Say follow](BOUNDED_SAY_FOLLOW_20261121.md).

## 5. Highest-priority next steps

**P0 — Physically accept one new Say transfer using the new coordinator.**

1. Confirm AMD-DESKTOP, current Git branch and queue status, exact live RIFT PID/HWND/process epoch/executable path/SHA-256 and installed RCM v0.2.23. Never reuse a prior PID, HWND or process-start timestamp.
2. Verify the real RIFT Log.txt path (DocumentsDirectory may be OneDrive redirected), whether noncombat logging is currently active, and the real game's current state. The native /log command is a **toggle**; do not blindly enable/disable it. If a controlled trial changes it, restore prior state.
3. Start a short explicitly bounded coordinator capture (see commands in coordinator doc) only after the source is qualified. Send one new unique benign Say canary through the ORIGINAL native RIFT chat *after* follower readiness, not before. Verify the game actually emitted a fresh Say line.
4. Inspect queue status and confirm one new queued batch. Run preflight for a read-only .NET validation.
5. **Important:** Do NOT first run claim and then dispatch; claim marks the token in flight and dispatch intentionally refuses another claimed transfer. Use either a fully supervised manual claim path OR one explicit dispatch of an unclaimed eligible entry.
6. Independently verify that the RCM editor is focused. For dispatch, provide full fresh host/PID/HWND/process-start ticks/exe path/exe SHA and required acknowledgments. The sender refuses to activate the game itself, verifies identity before typing, and does not automatically retry partial insertion.
7. Check actual in-game RCM IMPORTS tab for **one** unique HOST/SAY row. Capture authentic screenshot evidence. Numpad * may be consumed by a focused RCM RiftTextfield; use the already proven bounded foreground capture helper if necessary.
8. After game acceptance, defocus RCM, submit /reloadui from the original native chat, locate the correct **current character** RiftChatModern.lua SavedVariables and run verify-disk with the exact active token.
9. Record full evidence and any failures in a new milestone doc, preserving privacy. If uncertain, leave the batch claimed and investigate before any manual resolution.

**P1 — Additional real social format:** obtain game-created *different* social type (Guild, Party, Tell, named public channel) bytes and qualify its actual exact structure before changing parsers.

**P2 — Reliability/UI:** improve bounded session observability and receipt reconciliation after P0; then work from real in-game screenshots for UX issues, maintain drag/resize/focus/persistence and clear provenance. Never market unverified seamless or lossless continuous import.

## 6. Development policy and pitfalls

- Fix root causes, not bandaids; run existing regression suites and the actual game when physically verifying UI/input.
- No Ollama or OpenCode. Internal ChatGPT subagents may be used only when actually available. Workbridge's 36 jobs/assignment slots are **not** internal ChatGPT model subagents.
- Verify machine binding: this project was developed on AMD-DESKTOP; do not assume a LEGION installation or alternate AddOns directory.
- After actual addon Lua changes, update ordered .toc metadata including Version and Email, deploy into the **verified active** RIFT AddOns directory, and use /reloadui (not an unnecessary full game restart).
- Do not write or fabricate SavedVariables receipt data. Do not commit private RIFT logs, private screenshots, player names, full saves or encoded private queue.
- Use authentic in-game RIFT screenshots. Foreground capture can be done temporarily with existing guarded tooling and must restore focus; the editor can consume the Numpad screenshot key.
- UI requirements include dark compact glass appearance, legible columns, local-second timestamps, drag+resize+clamping, correct tabs, exact version in init and window, focus feedback and persisted settings.
- Preserve the evidence boundary between unit tests, Windows keyboard receipts, actual game visuals, and game-created disk receipts.

## 7. Publication and restart

At handoff creation, origin was confirmed as https://github.com/360madden/RiftChatModern.git, and the working tree was clean with two local commits ahead of origin/main. This handoff should be its own additional commit. **Post-push verification, not this document, establishes whether publication succeeded.**

Resuming in PowerShell:

    cd C:\work\RiftChatModern
    git status -sb
    git log -5 --oneline
    node tools/rcm-say-delivery.cjs status

**Success criterion for the next iteration:** a *new real game-generated* Say log line is captured by the coordinator, the exact serialized import reaches the actual RCM editor once, one retained HOST/SAY row is physically observed, and the same transfer token is verified in the game's actual saved file after the normal save lifecycle. Until all evidence is present, report **partial**.
