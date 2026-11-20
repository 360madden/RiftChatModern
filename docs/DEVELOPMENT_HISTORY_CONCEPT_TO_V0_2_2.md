# RiftChatModern — Complete Development History and Engineering Handoff

**Project:** RiftChatModern (RIFT Live addon)  
**Report date:** November 20, 2026 (America/New_York)  
**Coverage:** initial concept through v0.2.2 and the November 20 physical-client acceptance cycle  
**Primary host:** AMD-DESKTOP; Workbridge 0.16.5-dev during the documented work  
**Canonical local repository:** C:\work\RiftChatModern  
**Source addon:** C:\work\RiftChatModern\addon\RiftChatModern  
**Installed addon:** C:\Users\mrkoo\OneDrive\Documents\RIFT\Interface\AddOns\RiftChatModern  
**Branch / last verified HEAD before this report:** main / 08b5ef4bdc0ece53a73a2762b13ea00514a39bc1  
**Current product version:** 0.2.2; interfaceVersion = 1; Lua 5.1; RIFT manifest Environment = 4.3  
**Status summary:** actual RIFT loader, /rcm launcher, own-editor focus indicator, legible dark window, and title dragging are physically verified. Full native social-chat reception/send, cross-client addon-data receipt, and actual clipboard copying remain unverified or unavailable.  
**Evidence grading:** LIVE = observed in the physical game with independent readback; INSTALLED = source and physical AddOns files match by hash; MOCK = tested with actual Lua 5.1 under simulated RIFT APIs; RESEARCH = documentation/source analysis; PLANNED = not implemented; UNKNOWN = not established.

> This is a **historical record, not a claim of full completion**. Past failures, tests that gave misleading confidence, and unresolved functionality are kept deliberately. Historical source files in Git and other documents below remain the authoritative proof for a given revision. A test with mocked APIs is not an in-game pass, and the presence of a UI category called “guild” is not proof that native guild messages can be received.

---

## 1. Why this project exists

The original problem arose during work on the Rift Personal Teleporter (RPT) and other RIFT tooling. RPT Travel Lab was able to expose Lua commands, collect SavedVariables and record travel observations, but repeatedly asking the operator to enter native chat slash commands was too slow and fragile for the development schedule before December 2026. We already had Windows input helpers, Workbridge and LuaPadModern.

The first proposal was to determine whether the **native RIFT chat input had keyboard focus** from Python/Win32 or through the addon API. Windows GetGUIThreadInfo, UI Automation and image comparison were investigated in the **Rift-Personal-Teleporter** repository. Those methods did not establish a reliable native-chat-open detector, because RIFT can draw the editor within its primary game HWND and expose little of it to Windows accessibility. A screenshot alone could not tell whether an invisible/internal textfield owned input.

The project then took two inadequate shapes before the user clarified the actual product:

1. A narrow RPT command/data bridge was proposed: accept restricted commands and return results without using native chat. This would have helped one project but missed the larger requirement.
2. The correct mandate became a **standalone, reusable, modern RIFT chat-replacement addon**, useful to all local RIFT repositories, with ordinary chat-like history, tabs, search, legible text, draggable GUI, own textfield with observable focus, clipboard copying and interfaces for other addons.

The user explicitly noted that existing RIFT chat replacements could show chat and copy content, and recommended **LuaPadModern as scaffolding** because its own textfields, key-focus handling, execution UI and clipboard routines were already demonstrated. The implementation used LuaPadModern and installed third-party addons as **references**, not as source-code modifications or runtime dependencies.

The desired final product is broader than the currently implemented console: it should ultimately handle most routine native RIFT chat behavior while making diagnostics and automation across RPT, RR2, RRE and similar repos easier. The distinction between this goal and the v0.2.2 implementation is critical.

### Core product requirements established

- Independent addon and Git repository under C:\work; do not alter RPT or LuaPadModern to own it.
- Compact webpage-like **dark mode**, not RPG-themed; readable fonts, strong contrast, legible icons, version visible in title.
- **Actually draggable** and position persists; usable at different window sizes, mouse-up outside supported.
- Own text input with **real getter-backed editor/search focus status**, not a guessed native chat-focus flag.
- Timestamped history, channel tabs, search, paging, full-message viewing and **copy one message / copy filtered history**.
- Colored versioned initialization message printed to the game console.
- CLI-first local command registry, public Lua API, and character-scoped SavedVariables for other addons.
- Preserve native chat as a fallback until ordinary social chat receives/transmits are independently proven.
- Strong test coverage, physical addon deployment to canonical OneDrive AddOns, source-hash checks, durable commits and explicit separation of mocked versus live evidence.

---

## 2. Repository, installation and architecture

### Current tree (v0.2.2)

    C:\work\RiftChatModern\
      .gitignore
      README.md
      addon\RiftChatModern\
        RiftAddon.toc
        Core.lua
        AddonMessages.lua
        NativeChatProbe.lua
        ConsoleMirror.lua
        Main.lua
        fonts\
          Lato-Regular.ttf
          Lato-Bold.ttf
          Lato-OFL.txt
      docs\
        ADDON_TRANSPORT.md
        V0_2_1.md
        V0_2_2_LIVE_STARTUP_FIX.md
        LIVE_ACCEPTANCE_V0_2_2_20261120.md
        DEVELOPMENT_HISTORY_CONCEPT_TO_V0_2_2.md  (this report)
      tests\
        test_addon.py
        test_addon_messages.py
        test_console_mirror.py
        test_core_stress.py
        test_message_detail.py
        test_native_probe.py
        test_rift_startup_contract.py
        test_ui_geometry.py
      artifacts\                 (Git-ignored; contains private in-game screenshot)

**RiftAddon.toc:** Identifier "RiftChatModern", Name "Rift Chat Modern", short name RCM, Author 360madden, Email placeholder@example.com, Version 0.2.2, Environment 4.3, character SavedVariables named RiftChatModernSaved. Startup order is Core.lua -> AddonMessages.lua -> NativeChatProbe.lua -> ConsoleMirror.lua -> Main.lua. **The Email field is present intentionally**, because past RIFT addon packaging showed that missing/incorrect manifest fields can prevent the addon appearing at all.

**Core.lua:** bounded message model and local command registry; timestamps, categories, defensive message copies, per-character history, filter/search, 240-entry limit and stable message IDs. It exposes the global RiftChatModernCore.

**AddonMessages.lua:** the separate RIFT **addon-data** messaging transport with identifier RCMDevV1, exact acceptance, bounded payload, rate limit and callbacks. It exposes RiftChatModernAddonMessages.

**NativeChatProbe.lua:** read-only native console frames (Console1–Console7) and configuration from Inspect.Console.List and Inspect.Console.Detail. The result explicitly says nativeTranscriptReadable=false. It exposes RiftChatModernNativeProbe.

**ConsoleMirror.lua:** optional, initially OFF, pass-through wrapper for addon calls to Command.Console.Display; stores a searchable copy, handles HTML normalization, avoids recursion, and does not overwrite a later third-party hook. It exposes RiftChatModernConsoleMirror.

**Main.lua:** UI, colored/versioned startup, /rcm native launcher, local colon-commands, optional RPT integration, event adapters and global RiftChatModernAPI.

The **physical AddOns copy** is deployed into the user's OneDrive Documents RIFT Interface\AddOns, not into RPT's addon folder. v0.2.2 installed-file hash checks passed. The SavedVariables history is stored under the game account/shard/character tree for Atank on Deepwood. No history deletion or migration was needed for the v0.2.2 loader fix.

**RIFT addon source, installed addon, Git repository, running game and SavedVariables are five distinct things.** A correct source file and manifest on disk do not by themselves prove that the currently running game has reloaded those bytes.

---

## 3. Verified chronological Git history

All six project commits in the inspected repository had November 20, 2026 local timestamps. The list below is chronological.

| Time (ET) | Commit | Milestone | Evidence |
| --- | --- | --- | --- |
| 05:23:35 | 74f2c2a | Initial standalone chat-style console, model, editable input, history, clipboard and tests | Source, offline Lua 5.1 mocks; first installation |
| 05:43:18 | d8e3790 | v0.1.1 modern UI polish: Lato fonts, clickable/drag header, focus indication, larger text, layout regression tests | Offline mock and installed hash verification |
| 06:09:15 | bb4c039 | v0.2.0 reliable addon-data transport, recipient/ack rules and native-console frame probe | Offline mocked tests, code, source-hash deployment |
| 06:39:45 | 42bfdad | v0.2.1 full message details/copy, console subscription metadata, opt-in addon console mirror | 52 offline Lua 5.1 tests and installed hashes |
| 06:58:15 | 1bb63bd | v0.2.2 startup-loader hotfix: four helper modules stop returning module tables; add loader-contract test | 54 offline tests; subsequently live evidence |
| 07:15:47 | 08b5ef4 | Persist physical v0.2.2 startup, /rcm, focus and drag acceptance evidence | Real RIFT screenshots plus guarded input receipts |

**At the time of the handoff, main was clean at 08b5ef4 and no GitHub push had been made.** Any new documentation commit will advance HEAD but must not be represented as a published GitHub update.

---

## 4. Version-by-version work: successes, setbacks and corrections

### 4.1 Initial design and v0.1.0 (05:23)

Created the new directory and Git repo at C:\work\RiftChatModern. Established Core.lua, Main.lua, a complete RiftAddon.toc and the first test harness. The first build included a compact dark 750×558 chat-like window, own RiftTextfield editor, startup message, /rcm command, All/Chat/System/NPC/Addons/Dev tabs, search, 13-row paging, SavedVariables, local commands, optional RPT Lab adapter, clipboard button and global API.

**Technical wins:** a working model independent of UI; character-scoped bounded history; copy-on-read semantics so other addons cannot modify saved records by editing returned tables; no misleading success for plain say/guild/tell strings entered into the custom editor; independent original addon not tied to LuaPadModern.

**Actual early failures:** first offline Lua 5.1 test runs exposed errors in the **test harness itself** (Lua mock table syntax and test-script scope), requiring corrections before tests became meaningful. The first complete test cycle reached **12/12** passes. Tests initially verified simulated RIFT APIs, not physical load. The brand-new Git repository also lacked local author configuration; author/name were taken from an existing RIFT repository rather than invented, and the initial commit then succeeded.

**Key mismatch with original goal:** most features were a useful developer console, not true social-chat ingress or send. This was documented rather than hidden. Normal native chat still had to remain available.

### 4.2 v0.1.1 UI-quality pass (05:43)

The user emphasized **dragging, legible fonts, clean styling and reliable focus detection**. Increased window to 760×618, title font to 21, message rows to 16 and editor to 18; bundled Lato Regular/Bold with original SIL OFL. Fixed text-label mouse masking so it would not steal click/drag events. Restricted drag to title region, handled release outside window, persisted window position, clamped to screen bounds and added focus indication to the header.

**Focus semantics:** the addon can report its **own** editor and search focus via GetKeyFocus: focused, search, unfocused, hidden or unavailable. It cannot infer focus of RIFT's native chat input from this.

**Failures/corrections:** the first independent geometry probe had expected "unfocused" while the mock's unspecified GetKeyFocus returned nil, properly classified as "unavailable." A model stress probe expected the wrong sequence number after status/filter/find commands had generated additional records. These were **test assumptions**, not proof of an addon defect, and the checks were corrected. All expanded 18 regression tests passed.

**Workbridge delegation:** five separate real developer jobs executed regression, layout/focus, bounded-history stress, font license/integrity and manifest checks; all finished and were verified. These were Workbridge worker jobs, **not GPT-6.2 Astra subagents**. Do not claim AI-agent swarms without an actual AI delegation capability.

### 4.3 v0.2.0 addon-to-addon messaging and native probe (06:09)

Research inspected the installed Imhothar MessageViewer addon and RIFT API docs. The API supports reliable **addon messages** using Command.Message.Send, Command.Message.Accept and Event.Message.Receive. The send callback proves only **server queueing**, not receipt by a specific player. RIFT type labels ("tell", "guild", etc.) in Command.Message do NOT mean ordinary player say/tell/guild transport.

Built **RCMDevV1** exact-identifier transport with maximum 240-byte message, validated target, one pending send, minimum two seconds between sends, 15-second missing-ack timeout and no automatic retry. Logged accepted, rejected, unknown, received and invalid counters. Incoming addon messages stay **inert text**: remote ':rpt arm' payloads do not execute commands. Optional local ':addon CHARACTER MESSAGE' and SendAddon API were added.

Added read-only inventory for UI.Native.Console1–Console7. Initial observation could report visibility, loaded and focus-getter metadata, but **not native chat transcript**.

**Notable bug fixes:** tests exposed ambiguous callback/return combinations, synchronous success/refusal handling, timeout deadlock risk, cross-shard-style target strings and long sender-name source limits. These were hardened and regression-tested. The completed v0.2.0 suite passed **34/34** tests; the installed source/manifest also passed a mocked game-load smoke test.

**Still unknown:** no real second RIFT client independently received a RCMDevV1 packet. Receiver delivery is not live-verified.

### 4.4 v0.2.1 usability, console configuration and diagnostic mirroring (06:39)

**Full-message reader:** clicking a stored message opens an overlay with the full saved text, source and message ID; COPY MESSAGE exports the complete selected line. Selected IDs survive filter changes and paging and fail safely when history is cleared/evicted. The prior single-line display used a short preview, so longer messages were not comfortably readable before this change.

**Clipboard command correction:** the first ':copy' merely printed a placeholder. It was replaced with a call to the real Command.CopyToClipboard API (still only mocked until live test).

**Native console configuration:** added Inspect.Console.List/Detail read-only integration, exposing names and enabled channel categories (say/guild/party/tell/NPC/system/combat). This is **channel subscription metadata**, not recovered chat messages. Added ':native', ':native channels' and ':native copy'.

**Console mirroring:** added opt-in (OFF by default) wrapper around Command.Console.Display. It forwards original arguments/results/errors, normalizes bounded HTML/plain text into stored addon diagnostics, avoids recursive capture and refuses to overwrite a newer third-party wrapper on disable. This can collect console output emitted by RR2/RRE/RPT **after being enabled**, without editing those repositories. It is not a tap into native client-generated player chat.

**Event compatibility:** handled both (info) and (event, info) NPC/notification callback forms plus bounded keyed notification collections, based on RIFT API docs and other installed addons. Nontext values remain ignored.

**Failures/corrections:** early geometry and core stress assumptions were corrected; later a newly added ':native copy' path introduced a Lua 5.1 number-concatenation syntax error, exposed by the full suite and fixed. The console mirror initially risked counting rejected/unstored output as captured; tests drove a correction. The full v0.2.1 suite finished **52/52**.

**Important limitation:** these were **mock results**. v0.2.1 was installed by exact file hashes but had not been successfully accepted inside RIFT when the next problem appeared.

### 4.5 The major LIVE failure: four "ADDON ERROR" dialogs (v0.2.1)

The user supplied native RIFT screenshots showing:

    ADDON ERROR
    Rift Chat Modern 0.2.1
    Error: Unknown: assertion failed!
    In RiftChatModern / Core.lua
    stack traceback: [C]: in function 'assert'

The game chat additionally showed the same assertion failure for **AddonMessages.lua, NativeChatProbe.lua and ConsoleMirror.lua**. This was not an offline report or imagined defect; it was a real game-client error.

**Why previous tests missed it:** our Lupa harness loaded each helper file as a valid Lua script and did not require a zero-value return from each RIFT RunOnStartup module. Four helpers assigned their module to a global but also ended with a top-level 'return Core', 'return Bridge', 'return Probe' or 'return Mirror'. RIFT's addon loader apparently disapproved of this pattern. A direct comparison found that working installed RiftReader2 and RRECollector startup modules did not return helper module values.

**Caveat on root cause:** exact RIFT loader internals were not available. The shared return pattern was a strong, concrete hypothesis and later the disappearance of all four errors after changing it strongly supports the diagnosis. It is **not** source-level proof of the private game's assert implementation.

**Communication/reasoning failures retained:** earlier responses spent too long trying to solve native chat-input focus even after the user specified a replica addon, then narrowed the concept to a teleporter-only command bridge. The first interpretation of one user screenshot was also wrong and needed correction: the screenshot was plainly showing Rift Chat Modern's own ADDON ERROR. These mistakes cost time and are lessons in respecting the actual product goal and giving live player evidence priority over offline test counts.

### 4.6 v0.2.2 loader compatibility hotfix (06:58)

Removed only the **top-level module returns** from all four helpers. Preserved global exported APIs and startup order. Added test_rift_startup_contract.py to load **all five** RunOnStartup files using Lua 5.1 and two addon arguments, assert they return no module values, and verify the exported objects and model initialization.

The new full test suite passed **54/54**, and all nine installed files (manifest, five Lua modules, Lato fonts and license) matched source hashes. The fix was locally committed as **1bb63bd**.

At that stage **real game acceptance was still missing**, so the correct status was offline-verified/installed, not solved.

---

## 5. Actual RIFT v0.2.2 acceptance: how it was proved

This is the strongest evidence in the project as of this document. The inspected target was physical RIFT x64 on AMD-DESKTOP, PID **22532**, HWND **0x980F44** during this session. These are **historical handles** and must never be reused without fresh identity verification.

The standard Workbridge screenshot adapter returned UI_TURN_BUSY. Instead of inventing an active screenshot, we reused the existing read-only exact-HWND **Python ImageGrab/window capture** from the RPT helpers. This recovered a useful visual channel. Each game input was sent only to the current identity using the existing hash-pinned RiftReader SendInput method or an explicit, short bounded Python mouse-drag probe, with independent screenshots after actions.

### 5.1 Stale error dialog dismissed

The earlier modal still displayed **Rift Chat Modern 0.2.1** after files had been updated. One reviewed IGNORE-button click at client coordinates (932,1090) inserted 3/3 Windows mouse events. A fresh capture showed the dialog gone. This was **modal dismissal**, not a v0.2.2 reload and not proof of a fixed startup.

### 5.2 Actual new version appeared

Later read-only game captures showed a colored line in native RIFT chat similar to:

    RiftChatModern v0.2.2 | Loaded. /rcm opens the console. Version 0.2.2

The old four v0.2.1 startup assertions were not observed in the new startup portion. This is **live positive evidence**; however, no exhaustive game log was collected to prove that every event in the session lacked warnings.

**Important provenance:** the assistant did not send /reloadui for this transition. Do not claim its own reload command caused the new version to load.

### 5.3 Native launcher and window

A single scan-code **Enter** pulse opened the native RIFT chat input (verified visually); a '/' was entered and separately verified in the visible draft. Then 'r', 'c', 'm' and Enter were sent as individual two-event, exact-HWND pulses. The next read-only screenshot independently showed **RIFT CHAT / MODERN v0.2.2** open with tabs, search, history, clipboard, clear, focus, mirror, input and run controls.

This is a **LIVE PASS** for startup + /rcm launcher + basic visual rendering, not merely a Win32 input receipt.

### 5.4 Focus detection

One reviewed click on the addon-owned FOCUS INPUT button at game-client (1280,758) had 3/3 inserted mouse events. The next screenshot showed the header change from **INPUT • NOT FOCUSED** to green **INPUT • FOCUSED**, and the footer said the editor was focused.

This is **LIVE PASS** for the addon textfield's own focus detector. It does **not** solve native chat-input focus detection.

### 5.5 Dragging

A bounded mouse drag started at (1198,269) and ended at (1318,329): requested displacement **+120 px horizontal, +60 px vertical**. One mouse-down, eight incremental moves and a mouse-up produced **11 inserted events**. A fresh client screenshot showed the RiftChatModern panel had moved by approximately those amounts.

This is **LIVE PASS** for the draggable title bar and successful release. The exact position-persistence behavior across a later reload has not been independently measured live.

### 5.6 Clipboard: explicitly NOT live tested

A read-only Win32 clipboard preflight returned seven active formats, including image-related formats 2, 8 and 17. Clicking COPY HISTORY would replace Windows clipboard contents; the operator could have an image or other rich data there. The test was intentionally stopped **without changing the clipboard**. Offline API simulations passed, but **actual clipboard copying remains unverified**.

### 5.7 Private proof and data

The final exact-HWND read-only screenshot after dragging was saved under the Git-ignored repository artifacts folder:

    C:\work\RiftChatModern\artifacts\RiftChatModern-v0.2.2-after-drag-20261120.png

SHA-256: **6d74fc8df2061280dc4dd982f13a2d308b9b1296e59ca38a82707bcd98485b41**  
Capture UTC: **2026-11-20T12:13:41.045976+00:00**  
Dimensions: **2560 × 1369**. Contains player/chat information: **do not publish this image**.

RIFT's SavedVariables file contained multiple older startup records and retained its schemaVersion = 1. This shows persistence, but not the complete native social-chat history. No user data was deleted.

The live-acceptance report and proof were committed in **08b5ef4**. Neither the historical screenshot nor other private artifacts were included in Git.

---

## 6. Current features and their real verification level

| Capability | Implemented? | Best supporting evidence | Caveat |
| --- | --- | --- | --- |
| v0.2.2 RunOnStartup and colored init | Yes | **LIVE** visual startup/version | No exhaustive error-log audit |
| /rcm launcher | Yes | **LIVE** command + separate screenshot | In native chat once to open |
| Compact dark-mode panel + Lato | Yes | **LIVE** rendered screenshot | Minor paging icons still hard to read |
| Drag via title bar | Yes | **LIVE** 120×60 drag and after image | Persistence after new reload not live checked |
| Own-editor focus indication | Yes | **LIVE** green focus indicator | Not native chat focus |
| Search field focus detection | Yes | MOCK | Live search-focus not measured |
| Tabs, filtering, timestamps, paging | Yes | MOCK + visible UI | Actual channel history is limited to captured records |
| Full-message overlay and copy-selected | Yes | MOCK | Not separately live clicked |
| Copy filtered history / :copy | Yes | MOCK only | Real clipboard test deliberately deferred |
| Character SavedVariables | Yes | Real character-scoped file and visible repeated history | At least startup entries, not entire social chat |
| NPC and game notifications | Yes, adapter exists | API docs + MOCK | Actual event stream not independently exercised live |
| Publish + subscribe + local command registry | Yes | MOCK | Third-party addon live integration not independently measured |
| RPT status/arm/mark/last/stop adapter | Yes | MOCK | No live RPT action performed by this chat panel |
| Reliable addon data RCMDevV1 | Yes, implementation | API docs + MOCK | No second client's real receive proof |
| Native consoles / subscriptions | Yes, read-only probe | API docs + MOCK | Never a native transcript |
| Optional Command.Console.Display mirror | Yes, OFF by default | MOCK | Not yet toggled live; only addon console output |
| Native player say, tell, guild, party read | **No** | Research | Requires separate proven route |
| Native player say, tell, guild, party send | **No** | Research | :addon is not the same as player chat |
| Fully replace original RIFT chat | **No** | Product milestone | Native chat remains a necessary fallback |
| GitHub remote publication | **No** | Git history / local repository state | Local commits only |

---

## 7. Design contracts developers must preserve

### 7.1 Public API and local commands

The addon exports **RiftChatModernAPI**, interfaceVersion 1, plus named helper globals. Other RIFT addons can publish events, subscribe, register a local colon-command and query history and state.

Main APIs:

- Publish(kind, text, source), GetHistory(filter, search, limit, offset), GetMessage(id).
- RegisterCommand(name, callback), Subscribe(name, callback), Unsubscribe(name), Submit(":command args").
- Show, Hide, FocusEditor, FocusSearch, GetFocusState, GetStatus.
- OpenMessage, GetSelectedMessage, CopySelectedMessage, CloseMessage, Copy.
- SendAddon(target, message), GetAddonTransportStatus.
- GetNativeConsoles, SetConsoleMirror(boolean), GetConsoleMirrorStatus.

Native launcher: /rcm (plus show/hide/focus/tab/find/copy/clear/status/help).

Own editor examples: :help, :status, :filter addons, :find Atank, :echo test, :rpt status, :rpt arm, :rpt mark NOTE, :rpt last, :rpt stop, :native, :native channels, :native copy, :mirror on/off/status, :addon CHARACTER MESSAGE, :copy.

Unknown or unsupported plain player-social commands should **not** be reported as sent. The draft remains visible instead of being silently discarded.

### 7.2 Bounds and persistence

- History: max 240 rows, oldest dropped when full.
- Message text: max 512 bytes; source name: max 40 bytes.
- Search: max 60 bytes; clipboard filtered history: default 48 KB.
- Addon remote data: max 240 bytes, unique RCMDevV1 identifier.
- Addon send: one pending, two-second minimum interval, 15-second callback timeout, no blind resend.
- Extensions/subscriptions: bounded at 48 each; copies returned to callers, not direct references to saved data.
- Character-specific SavedVariables schemaVersion 1. Corrupted schemas fail closed; preserve existing history.
- No game encrypted datastream interception or client native-chat mutation was undertaken by this addon project.

### 7.3 Startup and UI-specific requirements

1. Keep the exact, correctly formed RiftAddon.toc with identifier, version, Email placeholder, RunOnStartup order and SavedVariables.
2. The **four helper startup chunks must not return module tables**. They must export their named globals and return zero values in RIFT.
3. The addon-owned dark panel must be draggable and remain legible, with copy buttons that do what their labels promise.
4. Version must match in both TOC and startup/window; colored startup notification must remain.
5. The focus badge reports **only known addon editor/search state** and must not silently claim RIFT-native focus.
6. The console mirror must start **OFF**, preserve the original console call, and avoid overwriting another addon's later wrapper.
7. Installed files must match the tested sources; game reload, in-game execution, Win32 input receipt and screenshot observation must be tracked separately.

---

## 8. Testing history and why each kind matters

| Build/checkpoint | Reported result | Coverage | Meaning |
| --- | --- | --- | --- |
| Initial model/runtime | 7/7, later 12/12 | Lua 5.1 + fake game events | First project and manifest behavior |
| v0.1.1 | 18/18 | UI geometry, focus, dragging, font license, history stress | Mock quality gate |
| v0.2.0 | 34/34 | Addon messaging, callbacks, native frame probe | Still offline |
| v0.2.1 | 52/52 | Full-message reader, console subscriptions and optional mirror | Missed RIFT startup-loader return contract |
| v0.2.2 hotfix | 54/54 | Added no-top-level-return test for all manifest startup chunks | Offline loader compatibility |
| v0.2.2 physical | Actual game observations | Versioned load, /rcm, own focus and drag | **Independent live acceptance**, first meaningful UI proof |

**Crucial process lesson:** 52 passing Lua runtime tests did not prevent four real startup exceptions. The suite tested valid Lua and mocked functions; it had failed to model a real RIFT loader rule. Following v0.2.2, the loader-contract test and physical UI inspection are both required. Never report mock-only results as if the actual RIFT client consumed them.

Workbridge provided parallel developer commands and durable assignment/verify metadata (five lanes for v0.1.1 and later cycles). That **does not** establish that GPT-6.2 Astra subagents were running. Model delegation requires an actual AI agent mechanism not verified in this development record.

External/sibling addon inspection stayed read-only. RRE, RR2, RPT, LuaPadModern and MessageViewer were not altered by this chat-replacement project.

---

## 9. Failed experiments, unresolved blockers and lessons

| Problem / failure | What actually happened | Correction or next action |
| --- | --- | --- |
| Solved wrong problem initially | Focus investigation and teleporter-only bridge were pursued despite user's broader replica goal | Treat full shared chat replacement as primary requirement; RPT is one integration |
| Mistook API transport for chat | RIFT Command.Message.Send supports addon data, not ordinary player chat | Separate addon telemetry from user-facing say/tell/guild/party |
| UI copied native chat insufficiently | First build previewed one line and placeholder-copy command | Full-message details plus actual clipboard call in v0.2.1; live clipboard still pending |
| Simulated UI passed while live loader failed | RIFT v0.2.1 raised four module assertions | Removed four top-level module returns and added loader-specific tests; v0.2.2 live opened |
| Initial Lua test harness failed | Mock event tables and Lua variable scope errors caused early red runs | Fix test harness and rerun complete suites |
| Test assertions incorrectly expected state | Unknown focus incorrectly expected unfocused, sequence count ignored command responses | Align assertions with actual API semantics |
| v0.2.1 added another Lua syntax failure during development | Native console copy concatenated a number unsafely | Full Lua test caught it and source was corrected before release |
| Console mirror accounting ambiguity | A failed storage callback could appear captured | Distinguish captured versus rejected; preserve original console behavior |
| Console wrapper lifecycle conflict | Another addon may wrap Command.Console.Display later | Disable capture without overwriting newer wrapper; report hook_chained |
| Screenshot adapter blocked | Workbridge desktop_capture_window returned UI_TURN_BUSY | Reused exact-HWND read-only Python ImageGrab; obtained valid screenshots |
| Older error dialog persisted | v0.2.1 modal still on screen after v0.2.2 file deployment | Dismissed with one exact-button click; separately observed v0.2.2 startup |
| No reliable native chat-focus detection | Windows GUI thread + accessibility did not expose internal game editor state | Use own textfield focus; retain native chat automation gating |
| Clipboard has nontext formats | Windows clipboard preflight exposed rich/image data | Deferred destructive clipboard overwrite; live test remains pending |
| Full social-chat reception absent | No documented addon API returns native player transcript | Evaluate the already existing LuaPadModern Log.txt read-only watcher after physical /log path check |
| Full social-chat send absent | No proven addon API for arbitrary normal player chat send | Research host-side verified input bridge; do not claim the local editor sends social text |
| Game-control success can be overstated | SendInput receipt only proves Windows inserted input events | Pair with independent game screenshots, as done for /rcm and drag |
| Small paging glyphs | Live v0.2.2 screenshots show tiny controls | Improve legibility in next UI revision |
| Repeated initialization messages | Saved history contains startup rows from multiple UI loads | Keep history but consider bounded, unobtrusive startup notices; not a functional failure |

---

## 10. Current next-action priority, in working order

**P0 — preserve the known-good live build.** Treat v0.2.2 + commit 1bb63bd and screenshot-backed acceptance at 08b5ef4 as the recovery baseline. Verify exact current host/PID/HWND and clean Git status before any new input or code deployment. Do not remove saved history or overwrite unrelated changes.

**P1 — finish live UI acceptance.** Choose a time when the operator explicitly permits overwriting the Windows clipboard or implement an equally reliable format-preserving backup/restore; then test Copy History and Copy Selected Message with actual clipboard readback. Test search focus, message detail row and close behavior live. A live error-dialog-free test remains mandatory after any new RunOnStartup changes.

**P2 — polish weak UI controls.** Replace tiny up/down paging glyphs, verify in-game layout at current resolution, and keep header drag and editor focus regression tests. Favor high-value fixes over cosmetic process work.

**P3 — prove a real peer addon-data round trip.** On two known active RIFT clients with matching RCMDevV1 receiver registration, send a one-shot bounded payload and independently read the receiving client's addon history or equivalent proof. A sender callback is insufficient.

**P4 — research native player-chat reception using existing assets.** LuaPadModern already contains a read-only RIFT Log.txt tailer (managed and Node implementations with synthetic tests). Determine the correct physical file path and whether /log records normal social messages, then establish freshness, scope and bridge direction. Avoid duplicating those tools or presenting Log.txt as automatically readable by addon Lua.

**P5 — evaluate native social send route separately.** The guarded RiftReader/RPT Win32 input helpers can enter slash commands into the native client; their success does not automatically give RiftChatModern's local textfield a native-chat send API. Build an explicit, verified and bounded host adapter only when its input/focus and result detection are proven.

**P6 — keep documentation and commits durable.** Versioned notes, real test counts, hashes and live screenshots must remain distinguishable. A GitHub push requires a separate, explicit publishing action and a final README review.

---

## 11. Reproduction, validation and handoff commands

From **PowerShell 7 on AMD-DESKTOP**:

    cd C:\work\RiftChatModern
    git status --short --branch
    git log --oneline -8
    & "C:\work\riftreader2\.venv\Scripts\python.exe" -B -m unittest discover -s tests -v

The Lua runtime comes from the existing RR2 Python venv with a real Lua 5.1 binding (Lupa). The tests simulate RIFT lifecycle/UI, so passing them alone is a **source/mock gate**.

Game-side after loading an updated addon, use **native** RIFT chat to open it with:

    /rcm

Inside the **addon-owned editor** use:

    :help
    :status
    :native
    :native channels
    :mirror status
    :rpt status

Do not use :mirror on unless its shared global console hook is deliberately desired. Do not use :addon to send personal social-chat text and mistake it for a native tell.

### Sources for verification and future updates

- Git history: 74f2c2a, d8e3790, bb4c039, 42bfdad, 1bb63bd, 08b5ef4.
- README.md — current usage, limitations and public API.
- docs/ADDON_TRANSPORT.md — v0.2.0 addon-message semantics and references.
- docs/V0_2_1.md — full-message reader, console mirror and channel metadata design.
- docs/V0_2_2_LIVE_STARTUP_FIX.md — original live assertion failure and loader hotfix.
- docs/LIVE_ACCEPTANCE_V0_2_2_20261120.md — separately evidenced physical startup, launcher, focus, dragging and clipboard deferral.
- tests/test_rift_startup_contract.py — regression that specifically addresses the missing loader contract.
- All eight tests/test_*.py files — current bounded Lua simulation regression.
- Installed local API docs in OneDrive RIFT Interface\AddOns\RIFT_API_Docs\LLM_RIFT_API: Console, Chat and Message API descriptions.
- Installed MessageViewer/Main.lua — prior addon-data message inspection example, examined read-only.
- LuaPadModern/docs/AUTOMATION-ARCHITECTURE.md and its log-probe tools — existing host-side evidence/transport research.
- Git-ignored local screenshot in artifacts/ named above — physical UI proof, **not for remote publication**.

## Final project state as of this history

**Confirmed accomplishments:** separate reusable repository and addon, complete startup manifest, color/version messages, modern readable dark UI, real draggable title bar, real custom editor focus feedback, functioning /rcm launcher, bounded saved data and local command APIs, mocked peer-data and console-mirror implementations, 54/54 Lua tests, and physical v0.2.2 screenshot-backed acceptance for startup/launcher/focus/drag.

**Confirmed failure recovered:** four v0.2.1 RIFT startup assertion errors associated with helper-module returns; hotfix removed returns, and v0.2.2 subsequently loaded without those observed assertions.

**What remains:** a trustworthy ordinary native social-chat transcript and send path; real cross-client receipt; live clipboard/read-full-message tests; visual refinement of paging buttons; full release/publication workflow.

**Operating principle:** *Do the work, preserve the failures, distinguish evidence levels, and validate in the real game before claiming the game-specific feature works.*
