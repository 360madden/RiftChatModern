# RIFT Chat Modern

**Standalone chat-style console and addon diagnostics hub for RIFT Live**

![RIFT Live](https://img.shields.io/badge/RIFT-Live-3bc4d0?style=flat-square) ![Lua](https://img.shields.io/badge/Lua-5.1-536dfe?style=flat-square) ![Installed](https://img.shields.io/badge/Installed-0.2.19-16a34a?style=flat-square) ![Status](https://img.shields.io/badge/Native_social_bridge-not_verified-c67b28?style=flat-square)

A compact, dark-mode chat window that can receive addon diagnostics, record event history, filter/search, copy to clipboard, and expose a command API to **all our RIFT repositories**. LuaPadModern inspired the editor focus design; this is **original code** with no LuaPadModern dependency or source modifications.

**Development record:** [concept through v0.2.2, including failures and live proof](DEVELOPMENT_HISTORY_CONCEPT_TO_V0_2_2.md), [v0.2.3 navigation](V0_2_3_NAVIGATION_AND_RELEASE.md), [v0.2.4 resizing](V0_2_4_RESIZE.md), [v0.2.5 codebase bug hunt](V0_2_5_CODEBASE_BUGHUNT.md), [v0.2.6 editor improvements / deployment receipt](V0_2_6_EDITOR_HISTORY_AND_SEARCH.md), [v0.2.7 console subscription discovery](V0_2_7_NATIVE_CHANNEL_DISCOVERY.md), [v0.2.8 Log.txt probe pilot](V0_2_8_LOG_PROBE_HANDOFF.md), [host chat observer research / tests](HOST_CHAT_OBSERVER_20261120.md), [v0.2.9 manual host ingress](V0_2_9_MANUAL_HOST_INGRESS.md), [v0.2.10 transfer recovery / guarded deployment](V0_2_10_IMPORT_RECOVERY_AND_DEPLOYMENT.md), [player-chat transport alternatives (historical REST, logging, native API)](CHAT_TRANSPORT_ALTERNATIVES_20261120.md), [legacy addon audit / raw log-format discovery](CHAT_REFERENCE_AUDIT_AND_LOG_DISCOVERY_20261120.md), [v0.2.11 structured provenance and schema migration](V0_2_11_STRUCTURED_PROVENANCE.md), [v0.2.11 physical RIFT acceptance](V0_2_11_PHYSICAL_ACCEPTANCE_20261120.md), [v0.2.12 save-lifecycle receipts and independent disk audit](V0_2_12_SAVE_CHECKPOINT_AND_DISK_AUDIT.md), [v0.2.13 migration dirty-state fix](V0_2_13_MIGRATION_DIRTY_STATE.md), [v0.2.14 accurate pending changes / deployment guard](V0_2_14_NOOP_DIRTY_AND_DEPLOY_GUARD.md), [v0.2.15 imported-message ID receipts across reloads](V0_2_15_IMPORT_RECEIPT_AND_RELOAD.md), [v0.2.16 persistent import tokens across saves and restarts](V0_2_16_PERSISTENT_IMPORT_TOKENS_20261120.md), [P0 configured-path log-probe launcher correction](CHAT_SOURCE_LOG_LAUNCHER_FIX_20261120.md), [persisted RIFT client chat API capability audit](CHAT_API_CAPABILITY_CAPTURE_20261120.md), [host-observer startup ordering regression](CHAT_OBSERVER_STARTUP_ORDER_20261120.md), [two-stage marker-then-chat observation](CHAT_OBSERVER_TWO_PHASE_20261120.md), [complete-message-only host import regression](HOST_IMPORT_TRUNCATED_MESSAGE_FIX_20261120.md), [v0.2.17 RCM-owned editor import](V0_2_17_RCM_EDITOR_IMPORT_20261120.md), and [host observer editor-mode output](HOST_OBSERVER_EDITOR_MODE_20261120.md).

## Implemented

| Feature | Current state |
| --- | --- |
| Modern dark UI, default 760×618, **21pt title / 16pt message font** | ✅ v0.2.11 window and version physically verified on AMD-DESKTOP (other UI features remain separately tested) |
| Dedicated **18pt editor**, getter-verified input/search focus badge, Enter dispatch | ✅ Lua 5.1 mock; physical acceptance pending |
| **Session-only Up/Down command recall**, 32 entries, restores unsent draft | ✅ v0.2.6 Lua 5.1 tests; live key acceptance pending |
| Search field stays synchronized with `:find` and `/rcm find` | ✅ v0.2.6 regression tests |
| Drag release outside, viewport clamping and saved placement | ✅ Tests |
| **Resizable window**, responsive message-history rows and saved width/height | ✅ v0.2.4 Lua 5.1 geometry tests; physical acceptance pending |
| **Paged detail reading** for long messages at compact window sizes | ✅ v0.2.4 Lua 5.1 tests |
| Bundled Lato Regular/Bold fonts and original OFL license | ✅ SHA-256 verified |
| All / Chat / **Imports** / System / NPC / Addons / Dev tabs | ✅ IMPORTS tab physically verified with one host-imported message in v0.2.11 |
| Timestamped history, paging, search | ✅ |
| Copy filtered chat history to clipboard, including `:copy` | ✅ Via Command.CopyToClipboard |
| **Click-to-expand full messages** and copy one message | ✅ Lua 5.1 UI tests |
| Opt-in capture of other addons' `Command.Console.Display` output | ✅ Mocked runtime; live acceptance pending |
| Inspect real native console channel subscriptions, **including named public channels** | ✅ v0.2.7 `Inspect.Console.List/Detail` Lua 5.1 read-only tests; live acceptance pending |
| RIFT NPC lines and screen notifications | ✅ Via documented Event.Chat APIs |
| Addon diagnostic publication and subscriptions | ✅ |
| Register local commands from sibling addons | ✅ |
| Built-in optional RPT Lab status/arm/mark/stop/last | ✅ |
| **Reliable RIFT addon-data messaging to another client** | ✅ Lua 5.1 API mock; physical acceptance pending |
| Windows-side **candidate social-chat observer**, using existing LuaPadModern log decoder | ✅ Node observer tests; historical format only, physical Log.txt receipt pending |
| **Physical RIFT session and log-path preflight** | ✅ read-only Windows process, HWND/PID, Documents and log checks; reports a crashed/exited client explicitly |
| **Manual host-to-RCM import** with separate kind, origin, and claimed channel | ✅ **v0.2.11 physically accepted**: original native RIFT chat input → imported row displayed as HOST/GUILD, not GUILD |
| **Guarded installation**, hostname check, backups, manifest contract and SHA-256 | ✅ v0.2.10 fixture tests and actual AMD-DESKTOP deployment |
| **Opt-in log feasibility probe** compatible with LuaPadModern `LogTailProbe` | ✅ v0.2.8 tests and cross-repo parser smoke; real RIFT disk transport unverified |
| **Native console read-only capability probe** | ✅ Lua 5.1 getter/mock tests |
| Saves up to 240 messages, character scoped; validated **schema v1 → v2 migration** | ✅ Six dedicated provenance/migration tests |
| **RIFT save-lifecycle checkpoints and independent disk verification** | ✅ v0.2.12 Lua/mock and Windows audit tests; physical save acceptance pending |
| Capture ordinary native player chat (say/party/guild/tell) | ⏳ Not verified |
| Transmit ordinary native player chat / arbitrary native slash | ⏳ Not available through the verified addon APIs |

**Important:** RiftChatModern is a chat-style window and developer console, **not yet a full social-chat replacement**. Native RIFT chat remains untouched as fallback. A Windows/Python host input/output adapter is a follow-up, not something simulated as success.

## Install / start

The source addon is **C:\work\RiftChatModern\addon\RiftChatModern**:

- **RiftAddon.toc:** identity, version, placeholder contact, startup and SavedVariables.
- **Core.lua:** bounded **schema-v2 provenance-aware** model, versioned migration, search, filters, history, subscriptions and local commands.
- **AddonMessages.lua:** dedicated `RCMDevV1` addon-data channel, send/receive validation, queue acknowledgment and timeout handling.
- **NativeChatProbe.lua:** read-only native-frame and actual console subscription inventory; does not modify consoles or read native player-chat text.
- **ConsoleMirror.lua:** disabled-by-default pass-through of RIFT `Command.Console.Display` calls into searchable addon-output history. It restores the original function when safely possible and does not intercept player chat.
- **HostIngress.lua:** bounded manual host-to-addon import; writes `kind=import`, `origin=host_manual`, plus separate unverified `channelKind` and `channelName` metadata.
- **Main.lua:** draggable dark frame, getter-backed focus indicator, editor, event adapters and RPT Lab integration.
- **fonts/**: bundled Lato Regular/Bold and original SIL Open Font License. The app uses native font fallback if custom fonts aren't available.

Use `tools/deploy_rcm.py` to preview the verified RIFT Interface\AddOns package, then `--apply --expect-host AMD-DESKTOP` to install. **Do not close RIFT just to deploy an existing addon:** replacement files are backed up and hash-verified even while RIFT runs. Use **`/reloadui` in RIFT's original native chat** to activate changed Lua/toc content; the installer reports whether it is required. See the [live deploy + /reloadui policy](LIVE_DEPLOYMENT_RELOADUI_POLICY_20261120.md).

Open the window **once from native RIFT chat**:

~~~text
/rcm
~~~

After that, the new editor handles its **own local commands**.

## Native launcher commands

| Native RIFT command | Function |
| --- | --- |
| /rcm | Toggle window |
| /rcm show / hide / focus | Visibility and editor focus |
| /rcm tab addons | Filter channel |
| /rcm find Atank | Search messages |
| /rcm copy | Copy filtered history |
| /rcm clear | Clear saved local history |
| /rcm size WIDTH HEIGHT | Resize the addon window within supported viewport limits |
| /rcm size reset | Restore the default 760 × 618 size |
| /rcm import ID INDEX/TOTAL BASE64URL | Manually import a host candidate record from Windows; **requires operator entry, not automatic chat capture** |
| /rcm import status | Display pending transfer ID, received chunk count, rejection and expiry counters in original native chat |
| /rcm import cancel | Cancel only the incomplete in-memory import, without clearing saved chat history |
| /rcm import help | Show import command syntax |
| /rcm checkpoint | Report the last RIFT Save.Begin receipt and tracked unsaved changes; never claims disk save proof |
| /rcm status / help | Diagnostics |

## Local editor commands

| Enter into the new editor | Function |
| --- | --- |
| :help | Local command list |
| :status | History, active filter, extension count |
| :filter addons | Change local filter |
| :find Atank | Search |
| :echo Hello | Record local Dev message |
| :rpt status | Query RPT Travel Lab API |
| :rpt arm | Arm 30-second RPT observation |
| :rpt mark clicked | Timestamp an operator event |
| :rpt last | Summarize last completed RPT trial |
| :rpt stop | Stop active RPT observation |
| :addon Atank@Deepwood TEST MESSAGE | Request reliable addon-data send to that character; **not ordinary player chat** |
| :native | Summarize native console handles and subscription availability |
| :native channels | Show per-console subscriptions and named public channels (configuration metadata, **not** chat transcript) |
| :native copy | Copy named console/public-channel configuration report to clipboard (replaces existing clipboard) |
| :host status / :host cancel | View or cancel the manual host-import transfer from RCM's own editor |
| :checkpoint status | Read RIFT save-lifecycle event status; disk save still requires independent verification |
| :logprobe TOKEN | Emit an explicitly requested `LPB_PROBE\|TOKEN\|epoch` marker to native RIFT console for a matching read-only Windows log watcher; not proof of disk delivery |
| :mirror on / off / status | Opt-in mirroring of other addons' console output; never player chat |
| :copy | Copy all currently filtered history via the game clipboard API |
| Up / Down (editor focused) | Browse up to 32 previously successful local editor commands; Down past newest restores unsent draft (live acceptance pending) |

A plain social-chat draft or native slash command entered into the new editor **is not silently sent**. It remains in the editor with a clear status explaining the missing native send route.

## Universal addon API

Consumer addons should declare a dependency in their own manifest:

~~~lua
Dependencies = { RiftChatModern = {"required", "before"} }
~~~

Then use direct dot calls:

~~~lua
local chat = _G.RiftChatModernAPI
if chat and chat.interfaceVersion == 2 then
    chat.Publish("addons", "Position sampler ready", "RR2")
    chat.RegisterCommand("rr2", function(args)
        if args == "status" then return "RR2: running" end
        return "Usage: :rr2 status"
    end)
end
~~~

| API | Description |
| --- | --- |
| Publish(kind, message, source) | Add a timestamped **non-social** message; unverified native Guild/Party/Tell/Say kinds are rejected |
| GetHistory(filter, search, limit, offset) | Return isolated rows with `kind`, `origin`, `channelKind`, and `channelName`. Use `imports` to filter imports |
| GetMessage(id) / OpenMessage(id) | Look up a retained message by stable ID and open its full-text reader |
| GetSelectedMessage() / CopySelectedMessage() / CloseMessage() | Inspect/copy the full selected message without losing history context |
| GetStatus() | Version, UI/focus, search, counts, transport flags, **hostManualImportReady**, **hostAutoImportAvailable=false**, **hostImportNativeChatVerified=false**, and capabilities |
| RegisterCommand(name, callback) | Register local colon-command |
| Subscribe(name, callback) / Unsubscribe(name) | Receive copied event data |
| Submit(":command args") | Execute a local command |
| Copy() | Copy filtered history to Windows clipboard |
| Show() / Hide() / FocusEditor() / FocusSearch() | Explicit own-window GUI focus operations |
| SendAddon(target, message) | Request reliable addon-data send with server queue acknowledgment (not peer delivery) |
| GetAddonTransportStatus() | Read queue-ready, pending, accepted/rejected/unknown, received and invalid counters |
| GetSaveCheckpointStatus() | Read-only RIFT save event receipt, event counters, last imported ID and tracked pending changes; disk persistence **unverified** until host inspection |
| GetHostIngressStatus() | Manual import mode, accepted chunks, pending fragment counts, completed imports, duplicates, cancellations, errors and expiry; **not native-chat delivery proof** |
| GetNativeConsoles() | Read-only native-frame and console-channel metadata, including `publicChannels`, `publicChannelCount`, `publicChannelsTruncated` per console; **never** claims ordinary chat-message access |
| SetConsoleMirror(boolean) / GetConsoleMirrorStatus() | Explicit optional pass-through interception of addon console output, preserving native behavior |
| GetFocusState() | Read the addon-owned input/search focus state; does not infer native RIFT chat focus |
| SetWindowSize(width, height) | Resize and persist a window's dimensions; requires initialized addon |

**v0.2.11 contract:** `kind=import` denotes external candidate messages; `origin=host_manual` and `channelKind=guild|party|tell|general|public` record separate provenance and claimed channel. The **HOST/GUILD** row is never stored or exported as native Guild chat. Other kinds include system, npc, addons, dev, and combat. Ordinary native social reception and sending remain unverified. `interfaceVersion=2` is a breaking change; [migration and dependent-consumer instructions](V0_2_11_STRUCTURED_PROVENANCE.md).

Limits: 240 saved rows, 512-byte messages, 40-byte sources, 60-byte search, 48 KB clipboard export. Character-scoped SavedVariables now use **schemaVersion=2**; valid schema-v1 data migrates atomically on load. Invalid histories fail closed without resetting data. A pre-migration disk backup is retained locally (not committed).

## Validation

Run in **PowerShell 7** in this repository:

~~~powershell
& "C:\work\riftreader2\.venv\Scripts\python.exe" -B -m unittest discover -s tests -v
~~~

The tests exercise actual Lua 5.1 with game API mocks, **control bounds, 21/18/16pt text, input/search focus getters, drag outside release, complete-message reading, copy-selected/filtered history, 1,200-message stress**, NPC/alerts (both callback forms), addon commands and RPT integration, reliable addon-data messaging, bounded native console configuration discovery and optional console-output mirroring. These remain **offline** tests, not physical UI acceptance. They do **not** substitute for actual physical RIFT UI acceptance.

## RIFT API findings

The historical documented RIFT addon API provides Event.Chat.Npc, Event.Chat.Notify, Command.Console.Display, Command.CopyToClipboard and addon-specific message transport through Command.Message.Send. Addon messages are not normal player say/guild/tell messages. UI.Native.Console1 is an exposed native console frame, but the verified APIs do not provide its complete social-chat transcript or arbitrary text-send capability.

Reference: https://github-wiki-see.page/m/chrisbecke/Igor/wiki/RIFT-API-Documents

**Next priority:** verify the physical window/editor/copy and optional console mirror; prove end-to-end `RCMDevV1` delivery between two real clients; reuse the mature LuaPadModern read-only Log.txt watcher when investigating actual social-chat reception. Keep native chat intact until a full replacement is independently demonstrated.

[Version 0.2.1 developer notes](V0_2_1.md) explain message details, mirror behavior and native subscription metadata.

See [addon messaging and native-console probe](ADDON_TRANSPORT.md) for the exact APIs, reliable-send restrictions and evidence limits.

**v0.2.2 startup hotfix (November 20):** RIFT reported four real addon-load errors in v0.2.1 (Core, AddonMessages, NativeChatProbe and ConsoleMirror). Their top-level module return values were removed from RunOnStartup execution, and a dedicated loader-contract regression test was added. The fix was subsequently **observed working in the physical RIFT client**: v0.2.2 loaded, /rcm opened, the editor-focus indicator responded, and the window dragged. No new four-module assertions were observed in the captured startup portion; this is not an exhaustive absence-of-errors guarantee. See [live startup fix](V0_2_2_LIVE_STARTUP_FIX.md) and [live acceptance report](LIVE_ACCEPTANCE_V0_2_2_20261120.md).

Built on AMD-DESKTOP for reusable RIFT development tooling.

## v0.2.3 navigation polish (2026-11-20)

The message-history pagination buttons now read **OLDER** and **NEWER** instead of tiny arrow glyphs. The manifest, startup window and status API all report v0.2.3. All 54 Lua 5.1 mock tests passed, including the RIFT startup-loader contract and paging-control regression. Physical RIFT acceptance of v0.2.3 remains pending; the physical v0.2.2 acceptance is preserved in the historical report.

The addon is also available publicly at https://github.com/360madden/RiftChatModern.

## v0.2.4 — resizable responsive window

Drag the **// grip** at the bottom-right corner of the RCM window to resize horizontally, vertically, or diagonally. The title bar still moves the window independently. The history region consumes most added height, dynamically expanding the number of rows shown; wider windows reveal longer message previews. At the compact minimum (680 × 480), message details have **PREV/NEXT** pages with a page indicator so long text remains accessible.

Window position and dimensions persist under the existing character-scoped RiftChatModernSaved.ui (x, y, w, h) with validation and viewport clamping. Existing messages and custom UI state are preserved. The new API SetWindowSize(w, h) is additive; interfaceVersion remains 1. The native chat command /rcm size 1000 750 provides a direct test and /rcm size reset restores the default size.

**Verification:** 63/63 Lua 5.1 mock tests, including resize gestures, independent axes, mouse release outside, full control containment, persistence and restore, viewport clamping, detailed messages, RIFT startup loader contract and old API regression. **Physical v0.2.4 acceptance remains separate**; inspect the in-game version, resizing, saved dimensions after /reloadui and errors before claiming a live pass. See [v0.2.4 engineering notes](V0_2_4_RESIZE.md).

## v0.2.5 — Codebase bug hunt and reliability fixes

This release audits all five Lua runtime modules, the RIFT manifest, local tests, and API compatibility against the installed RIFT API reference.

**Resolved:** RIFT frame-anchor accumulation on reflow (clear anchors and restore sizes); oldest-page overlap and incorrect history counters; malformed clipboard export bounds; duplicate saved message IDs; persisted search controls; UTF-8 safe command responses, NPC/alert text, message previews, console metadata and mirrored diagnostics; blank NPC names; addon-data storage failures counted as received; and uncertain send submissions misclassified as server rejections.

**Testing:** 76/76 Lua 5.1 regression tests passed, including new bug-hunt and messaging checks. Existing SavedVariables schema, addon transport identifier, CLI commands and public API interfaceVersion = 1 remain compatible. Full audit details and evidence limitations are in [v0.2.5 bug hunt](V0_2_5_CODEBASE_BUGHUNT.md).

**Physical in-game acceptance:** separate from mock verification. Loading the installed files in RIFT, error checks, drag/resize, paging, and clipboard behavior must be verified in the actual client before being labeled LIVE PASS. Normal native social chat still requires a distinct bridge.

## v0.2.6 — Console input history and search synchronization

**New:** The local editor now remembers the latest 32 successfully submitted `:` commands for in-session Up/Down recall, avoids consecutive duplicates, and restores unsent text when navigating forward past the newest command. An edit or paste exits navigation. The history is deliberately **not persisted** to SavedVariables; unsent native/social drafts are never counted as successful commands. API calls to `Submit` are separate from manual editor recall.

**Fixed:** `:find` and `/rcm find` previously changed the active model search without updating the visible search textbox. The renderer now synchronizes the query without redundant change events.

**Compatibility regression caught before deployment:** Adding keyboard handlers initially pushed the UI constructor beyond the Lua 5.1 **60-upvalue** compilation limit, failing many tests and preventing addon startup. Input callbacks were consolidated through the existing controls upvalue; the revised loader and runtime suites pass **81/81 tests**. These are offline tests, not physical keyboard acceptance.

See [v0.2.6 engineering and acceptance notes](V0_2_6_EDITOR_HISTORY_AND_SEARCH.md). Native social-chat send/receive remains unimplemented through the verified Lua addon API. No character SavedVariables migration or destructive install procedure is required.

## v0.2.7 — Native console subscription discovery

The read-only native inspector now recognizes **all 27 documented boolean subscription flags** from `Inspect.Console.Detail` (including raid warnings, loot and other combat/crafting categories). It also handles `Detail.channel` as a **public-channel name table**, displaying named channels such as `LookingForGroup` and `World@Deepwood` in `:native channels` and `:native copy`. The earlier inspector only checked 12 boolean fields and silently discarded public-channel names. Results are bounded, sorted, sanitized and reported separately from any actual chat text.

The API handles console ID maps returned by `Inspect.Console.List()`, preserves the public `interfaceVersion=1`, and continues to mark native transcript capture/social chat send as unverified. Mocked Lua 5.1 test coverage grew from 81 to **83**. The revised code was validated against the shipped Gadgets addon examples and historical RIFT API documentation, not yet independently accepted in the physical client.

See [v0.2.7 implementation, source findings, risks and live checklist](V0_2_7_NATIVE_CHANNEL_DISCOVERY.md).

## v0.2.8 — RIFT-to-host Log.txt feasibility probe

From RCM's focused editor, type `:logprobe RCM_TEST_20261120` to print a bounded nonce marker to the game's **native console**. This is a manually initiated diagnostics action; it does not toggle RIFT logging and cannot claim that a line reached disk. The matching Windows-side launcher at `tools/rcm-log-probe.ps1` now starts **RCM's configured-path observer**, which in turn reuses **LuaPadModern's read-only Node log decoder**. This retains a single tailing engine while respecting RIFT's own configured DocumentsDirectory. See the later [P0 launcher correction](CHAT_SOURCE_LOG_LAUNCHER_FIX_20261120.md).

**Preparation preview in Windows PowerShell 5.1 or 7 (run from the RCM repo):**

```powershell
.\tools\rcm-log-probe.ps1 -Preview -Nonce RCM_TEST_20261120
```

When RIFT is intentionally configured to write a verified `Log.txt`, remove `-Preview` to start one bounded watcher; then enter the matching `:logprobe` command in the already-loaded RCM editor. The watcher reports receipts but never sends game input. **Do not blindly type `/log`**: it toggles logging state.

**Tests:** 87/87 Lua 5.1 cases; 4 new cases test valid/invalid marker emission, unavailable APIs and missing server clock. The Windows PowerShell 5.1 preview and rejection paths were tested, and the exact marker was recognized by LuaPadModern's `LogTailProbe.readLine` against a synthetic string. No RIFT Live `Log.txt` receipt or player-chat ingestion has been demonstrated. See [v0.2.8 notes](V0_2_8_LOG_PROBE_HANDOFF.md).

## Windows host candidate-chat observer (source-only; in-game version remains v0.2.8)

The independent `tools/rcm-chat-observer.cjs` listens for new records in a RIFT `Log.txt` using LuaPadModern's existing bounded file decoder; it does **not** copy or replace that decoder. It parses historical bracketed sender/channel formats and emits structured *candidate* events to the Windows terminal. `--include-text` is required to output message bodies; by default the tool emits metadata only. It handles UTF-8/UTF-16, partial appends, log truncation and newly created files. A matched `LPB_PROBE` nonce ends the bounded run.

From a **Windows PowerShell** terminal in `C:\work\RiftChatModern`:

```powershell
node .\tools\rcm-chat-observer.cjs --help
node .\tools\rcm-chat-observer.cjs --nonce RCM_CHAT_20261120 --timeout-ms 120000
node --test .\tests\test_chat_observer.cjs .\tests\test_chat_observer_cli.cjs
```

**Verification:** 13/13 separate Node tests using synthetic files and child processes; original 87/87 Lua addon tests unchanged. RIFT's current `Log.txt` is not yet verified, so the parser's records explicitly mark `verifiedLiveFormat=false`. The observer does not ingest messages back into the in-game addon and does not send native social chat. **No new .toc version or addon deployment was required at the host-observer checkpoint.**

See [host observer implementation, historical sources, known failures and live protocol checklist](HOST_CHAT_OBSERVER_20261120.md).

## v0.2.9 — Bounded manual host-to-addon import

This release introduces the missing inbound half of the Windows-host research path. The Node helper `tools/rcm-chat-import.cjs` converts a candidate-chat JSON record into one or more compact `/rcm import ...` native slash commands. A new Lua 5.1 `HostIngress.lua` module (registered **before Main.lua in the six-file manifest**) validates and reassembles the chunks, then publishes a clearly marked `[HOST? Channel]` message into RCM history.

**Synthetic demonstration** (Windows PowerShell in `C:\work\RiftChatModern`):

```powershell
node .\tools\rcm-chat-import.cjs --kind guild --sender Atank --channel Guild --text "Hello from host"
```

Copy the `commands` field's complete `/rcm import ...` line and paste it into **RIFT's original native chat input** after v0.2.9 is loaded. RCM's **CHAT** or **ALL** tab will contain the imported candidate, visibly labeled as external. Long messages yield several commands; copy every part. No command is sent automatically.

For the existing Windows log observer, `--prepare-import` explicitly enables body-text output and prints these manual commands alongside each candidate record. Without a verified RIFT `Log.txt`, that observer still cannot acquire actual player messages.

**Validation:** 95/95 Lua 5.1 tests and 22/22 Node.js tests (117 total). Includes cross-language round trips, duplicate suppression, out-of-order chunks, malformed UTF-8, bounded payloads, missing callbacks and native slash dispatch under mocked RIFT APIs. **Physical import acceptance, real Log.txt reception, and automatic host input remain pending.** See [v0.2.9 engineering and live acceptance checklist](V0_2_9_MANUAL_HOST_INGRESS.md).

## v0.2.10 — Native import feedback, recovery and repeatable deployment

After manually pasting a long `/rcm import` transfer in original RIFT chat, the addon now **prints a colored receipt for each accepted chunk** even when its custom window is hidden. `/rcm import status` reports the active message ID and chunk progress; `/rcm import cancel` abandons a stuck transfer without deleting saved messages. The in-window commands `:host status` and `:host cancel` provide the same operations. A pending transfer also expires when its status is queried after the existing 45-second limit.

**New guarded installer:** `tools/deploy_rcm.py` selects an existing RCM installation, verifies .toc identity and startup metadata, requires an exact hostname for applying changes, preserves backups and compares source/installed file hashes. From Windows PowerShell at `C:\work\RiftChatModern`:

```powershell
& "C:\work\riftreader2\.venv\Scripts\python.exe" -B tools\deploy_rcm.py
& "C:\work\riftreader2\.venv\Scripts\python.exe" -B tools\deploy_rcm.py --apply --expect-host AMD-DESKTOP
```

**Verification:** 107/107 Python/Lua tests plus 22/22 Node.js tests. The actual AMD-DESKTOP deployment replaced only four changed files, backed up the prior installed copies and verified **10/10 source/deployed SHA-256 matches**. No SavedVariables or unrelated addons were touched. **The running physical RIFT client has not yet been independently accepted for v0.2.10.**

See [v0.2.10 release notes, tests, deployment proof and live checklist](V0_2_10_IMPORT_RECOVERY_AND_DEPLOYMENT.md).

## Native player-chat reception research

The [November 20 transport alternatives report](CHAT_TRANSPORT_ALTERNATIVES_20261120.md) compares historical RIFT mobile REST chat, actual addon chat APIs, the local `Log.txt` watcher, and a bounded external client-inspection fallback. An older `rift.net` C# client did implement remote RIFT guild chat in 2015, but the RIFT Mobile app was retired and only certain event-tracker API functions were reportedly retained. **No old remote chat endpoint has been verified working in 2026.** The highest-value acceptance work remains obtaining a *real* RIFT player-chat log sample and independently proving one manual RCM import inside the game, not adding another unverified proxy layer.

## Host-side reference audit and raw-log discovery (no in-game version change)

**Archive audit:** `tools/audit_rift_addon_archive.py` inspects RIFT addon ZIPs without extracting or running archived addon code. It checks `RiftAddon.toc` startup files, Lua 5.1 syntax only, recognizable RIFT API calls and WoW-specific API patterns. The 2013 *Nubz Rift Instant Messenger* archive contains a RIFT manifest but showed **61 WoW-style API/XML indicators and no recognized RIFT API calls**. It is not reliable evidence of RIFT player-chat reception.

**Raw log sampling:** `tools/rcm-chat-observer.cjs --sample-raw-lines 5 --timeout-ms 60000` can now print up to five **fresh decoded lines**, including unknown formats that the historical candidate parser ignores. Each sample is UTF-8-byte bounded and identified as **unverified physical RIFT origin**. Unlike the default observer, this explicit option may reveal real chat text in the Windows console, so use it only for deliberately supervised tests.

From Windows PowerShell in `C:\work\RiftChatModern`:

```powershell
& "C:\work\riftreader2\.venv\Scripts\python.exe" -B tools\audit_rift_addon_archive.py artifacts\external-references\NubzRiftInstantMessenger-2013.zip
node .\tools\rcm-chat-observer.cjs --sample-raw-lines 5 --timeout-ms 60000
```

These host-only changes passed **116/116 Python/Lua and 24/24 Node tests** at that checkpoint. The in-game release remains **v0.2.10**; no new addon files or `.toc` deployment are required. **No physical game-produced `Log.txt` has yet been proven.** See the [source audit, limitations, tests and live checklist](CHAT_REFERENCE_AUDIT_AND_LOG_DISCOVERY_20261120.md).

## Read-only physical session / game-crash preflight

The helper `tools/rcm_session_preflight.py` independently checks the **actual running RIFT process**, error-handler processes, the game's own `%APPDATA%\RIFT\Rift.cfg` `[Client] DocumentsDirectory` setting, fallback Documents paths, known `Log.txt` locations, and optional exact window PID/HWND. It distinguishes stale targets and multibox ambiguity instead of relying on previous desktop window listings. No input, network action, logging toggle, UI reload or game restart is performed.

From **Windows PowerShell** at `C:\work\RiftChatModern`:

```powershell
& "C:\work\riftreader2\.venv\Scripts\python.exe" -B tools\rcm_session_preflight.py --expect-host AMD-DESKTOP
```

On November 20, the preflight first found an **exited game with its Error Handler open**. After a user restart at **12:49 PM EST**, it independently confirmed a live game and exact window binding (PID `42992`/HWND `24252650`). RIFT and its error-handler companion began **at the same timestamp**, so the helper's presence alone is **not a crash indication**; the preflight now handles this correctly. The only remaining live log-test blocker was an absent `Log.txt`. The real `Rift.cfg` contained `LogConsole=False` and `LogCombatConsole=False`, which are observed configuration values, **not confirmed runtime log state**. Exit code `2` denotes a blocked **log reception** preflight, not a diagnosis. Fresh process identity is required after every subsequent restart. See [physical-session evidence, correction, and acceptance checklist](SESSION_PREFLIGHT_AND_RIFT_ERROR_20261120.md).

## Authoritative chat-log directory (Windows tooling only)

The host observer now selects `Log.txt` from **RIFT's own `%APPDATA%\RIFT\Rift.cfg` `[Client] DocumentsDirectory`** when available, instead of silently following an unrelated Documents fallback. Explicit `--path` and deliberate `LUAPAD_LOG_CANDIDATES` overrides take priority. The `started` JSON event reports `pathSelection` and the selected path.

When the configured file does not exist yet, the observer waits for it to appear and reads newly created content without treating synthetic or stale data as live evidence. This behavior is backed by **27/27 Node.js tests**, including an actual child-process test; **129/129 Lua/Python tests** were green at that checkpoint. At that earlier Windows-only checkpoint the installed addon remained v0.2.10; the later v0.2.11 release was physically accepted, and v0.2.12 adds separately tested save observability.

See [host observer configured-path implementation, verification and supervised live-test procedure](HOST_CHAT_LOG_PATH_SELECTION_20261120.md).

## v0.2.11 physical acceptance — November 20

Following a user-initiated RIFT restart, the fresh AMD-DESKTOP game instance was identified independently (PID `31820`, HWND `3805750`). The **v0.2.11 UI**, full history, and **IMPORTS** tab were visually confirmed in the physical client. A new message was generated through `tools/rcm-chat-import.cjs`, entered and submitted in RIFT's **original native chat**, and appeared as **HOST/GUILD · RCMTest** with the body `v0.2.11 provenance classification check`. ALL history increased from 34 to 35 messages, and the IMPORTS tab showed exactly **one** record.

This establishes end-to-end **manual host import and correct provenance display**. It does **not** establish normal server-delivered Guild chat reception, automatic chat mirroring, or yet prove schema-v2 bytes were persisted to the saved file after a clean game exit. The previous v0.2.10 test record was absent from the old on-disk v1 save and could not itself be physically migrated. Detailed evidence, local ignored screenshot hash, successful checks, and remaining limitations: [v0.2.11 physical acceptance report](V0_2_11_PHYSICAL_ACCEPTANCE_20261120.md).

## v0.2.12 — Engine save-lifecycle receipts and disk verification

RIFT controls when addon SavedVariables reach disk: the documented lifecycle offers `Event.Addon.SavedVariables.Save.Begin/End`, and saved data normally flushes on a successful logout or `/reloadui`. **A live imported message is not evidence that the save file was updated.** After the previous RIFT session ended, RCM and eight other active addons still had their last saved writes at about 9:36 AM, consistent with a missed game-wide flush.

RCM now records a **small structured save checkpoint** on the engine's Save.Begin event, retaining history count and latest imported-message ID without duplicating message bodies. `/rcm checkpoint`, `:checkpoint status`, `GetSaveCheckpointStatus()`, and `GetStatus().saveCheckpoint` expose the observed lifecycle and tracked unsaved changes. Save.End is counted in memory, but neither callback claims an actual disk write. Saved window geometry changes also update the pending-state indicator.

The independent read-only `tools/rcm_disk_receipt.py` audits the **actual character-specific** `RiftChatModern.lua` file after an engine save. It reports file timestamp/hash, schema and imported-row counts, consistent checkpoint metadata, and peer-addon save timestamps without executing stored Lua or exposing chat bodies. Use `--file` for an exact path, `--expect-host` to verify the machine, and `--require-checkpoint` when a missing receipt should return a nonzero result.

The v0.2.12 source retains **SavedVariables schemaVersion 2 and API interfaceVersion 2**. The new `saveCheckpoint` subtable is additive; ordinary native chat reception remains unverified. All validation is offline so far; the RIFT process was absent during this development cycle. Read the [full save-lifecycle investigation, independent audit, test evidence and acceptance checklist](V0_2_12_SAVE_CHECKPOINT_AND_DISK_AUDIT.md).

## v0.2.13 — Fix missed unsaved-state tracking after migration

The save-lifecycle audit exposed a correctness issue: v0.2.12's `pendingSessionChanges` status could be **false immediately after migrating schema v1 to v2**, even though RCM had modified its in-memory SavedVariables. The same issue affected a missing `nextId` repair.

RCM now marks these initialization changes as pending until the game's own Save.Begin event. It preserves the **schemaVersion 2 / interfaceVersion 2** contracts and does **not** force a save or treat Save.Begin as proof that bytes reached disk. A regression first reproduced the defect against the previous code, and an additional full RIFT Lua 5.1 startup test verifies the migration, imported Guild provenance, and subsequent Save.Begin receipt.

This is a source-only development release until RIFT is closed and the guarded installer can safely apply it. External local-model worker tooling was retired to the ignored `artifacts/` area at the user's request; no alternative AI model was run as part of this release. For source changes, tests, migration data protection, and live acceptance requirements, see [v0.2.13 migration dirty-state investigation](V0_2_13_MIGRATION_DIRTY_STATE.md).

## v0.2.14 — Accurate save status and enforced game-closed deployment

Repeat clicks on the already-active tab, resetting an already-empty search, and clearing already-empty history no longer mark SavedVariables as modified. A newly initialized persisted default **does** still count as an actual change. Separate Lua 5.1 model and mocked-UI callback regressions cover these behaviors, including the RIFT Save.Begin tracking boundary.

The guarded installer now checks the real Windows `rift_x64.exe` process list before applying an update and **refuses to copy any addon files while the game is active or the process query is untrustworthy**. It reuses the session-preflight parser, distinguishes an error-handler companion from a running game, and retains exact-host, backup/rollback, manifest, and checksum verification.

**Earlier verification (6:48 PM EST):** 167/167 Python/Lua tests and 27/27 Node tests passed. The game was still running (PID `23164`), so v0.2.14 was not hot-deployed and the only saved-data snapshot available then was the older schema-v1 file. See the [v0.2.14 engineering report](V0_2_14_NOOP_DIRTY_AND_DEPLOY_GUARD.md).

**Physical deployment (7:49 PM EST):** After the user exited RIFT, two process checks confirmed no game or error-handler process. The guarded installer backed up and installed exactly `Core.lua`, `Main.lua`, and `RiftAddon.toc`; a second hash-verified dry run reported **10/10 files identical** to v0.2.14 source and zero pending changes. The installed manifest now shows **0.2.14**. No RIFT input, restart, UI reload, or character SavedVariables modification was performed by the installer.

**First independently verified on-disk save (7:49:09 PM EST):** A fresh game exit saved schema **v2**, **50 retained messages**, and a consistent **sequence-1 serialized Save.Begin checkpoint** for the exact character. The `rcm_disk_receipt.py --require-checkpoint` audit returned exit code **0**, with zero retained imports. That save occurred **before** the v0.2.14 installation, so it confirms v0.2.12's real serialized checkpoint and not v0.2.14 runtime acceptance. The next live run still needs UI verification and a new manual import followed by an engine save to prove imported-message persistence. Detailed timestamps and evidence are in the [v0.2.14 physical deployment and disk receipt update](V0_2_14_NOOP_DIRTY_AND_DEPLOY_GUARD.md).

### Post-deployment disk-auditor hardening (host-only; installed addon unchanged)

A strict audit of the first saved v2 file established that all **50** retained messages are classified **system**, with **no** imported row. The standalone read-only disk checker now rejects duplicate and out-of-order message IDs and refuses to accept a save checkpoint whose `nextId` disagrees with the serialized character root. Its `historyKindsOnDisk` breakdown reports types and counts without printing chat text. The checker also refuses an apparent receipt if the saved file changes while being read, preventing mixed-version hash/timestamp evidence.

The new `--require-import-id ID` flag requires a **specific** retained imported-message ID **and** a valid serialized checkpoint (exit 0). Missing imports or inconsistent checkpoints return exit 2. This will be used for the next physical RIFT session's import-and-save acceptance; it does not fake native Guild/Say/Tell chat delivery. The real file still passes checkpoint verification, while a check for candidate historical import ID 35 correctly reports it absent. After these host-only changes **174/174 Python/Lua** and **27/27 Node.js** tests passed (**201 total**). RIFT Lua files, installed v0.2.14, and character SavedVariables were not altered **during that host-audit milestone**. See [post-deployment disk audit investigation and exact-import proof procedure](POST_DEPLOY_DISK_AUDIT_HARDENING_20261120.md).

## v0.2.15 — Link manual import receipts to the exact retained history row

RCM now includes the actual **history #ID** in its native chat acknowledgment after a successful manual host import; `/rcm import status`, `:host status`, and `GetHostIngressStatus()` expose the session's latest accepted transfer token and assigned message ID without pretending the record has already reached disk. The status API and native command also obtain the **latest retained imported history #ID** from actual model rows, so that ID remains discoverable after a game restart even though session-only transfer counters reset.

These changes provide the missing link to the independent `rcm_disk_receipt.py --require-import-id ID` auditor for a controlled import → RIFT save → exact-row persistence proof. No ordinary native player-chat receiver or automatic host-to-addon delivery is claimed. Lua 5.1 red/green tests reproduced both the missing acknowledgment and the missing restart lookup before correcting them. **177/177 Python/Lua tests and 27/27 Node tests passed (204 total)** in source validation. **Physical deployment completed at 8:03 PM EST:** the guarded installer copied exactly four files after confirming RIFT was closed, backed them up, and independently verified **10/10 installed files match v0.2.15 source** on AMD-DESKTOP. A separate exact-character SavedVariables audit found the previous 50-row disk checkpoint unchanged. **At this historical v0.2.15 milestone, a physical game load and manual import/save acceptance were still outstanding**; see the [v0.2.15 engineering report and deployment receipt](V0_2_15_IMPORT_RECEIPT_AND_RELOAD.md).

## v0.2.16 — Persistent import identity across saves and restarts

The first Node → Lua 5.1 → mocked RIFT Save.Begin → fixture disk audit → fresh Lua session integration test exposed a real replay defect: repasting the same previously imported transfer after a restart produced **two** saved import rows. The old import receiver only remembered transfer IDs for the current session. The regression failed against v0.2.15, then passed after the v0.2.16 correction.

Manual imported messages now optionally retain their strictly validated 12-character **importToken** within the existing schema-v2 history. The Core model and HostIngress receiver reject duplicate tokens already retained in saved history, including across fresh addon sessions. Invalid and duplicate saved tokens are rejected; older schema-v2 imports without tokens remain compatible. This identity cache is bounded by the same 240-row history; if a row is evicted or deliberately cleared, its token is no longer remembered.

The independent read-only disk checker adds **--require-import-token TOKEN** and can combine it with **--require-import-id ID**, requiring both to identify the *same* retained row and a consistent RIFT save checkpoint. **185/185 Python/Lua tests and 27/27 Node tests passed (212 total)** in source verification. No ordinary native RIFT player-chat capture or automatic host import is claimed. Detailed failures, corrected implementation and physical acceptance procedure: [v0.2.16 engineering report](V0_2_16_PERSISTENT_IMPORT_TOKENS_20261120.md).

**Physical installation, 8:13 PM EST November 20:** RIFT was confirmed closed on AMD-DESKTOP. The guarded installer backed up and replaced exactly four addon files, and an independent second pass verified **all 10 installed files match v0.2.16 source by SHA-256**. The installed manifest has the correct Email field, six ordered startup scripts, Environment 4.3 and character SavedVariables. The previous 50-row on-disk saved checkpoint remained byte-for-byte unchanged. A new one-part manual import command has been generated and documented for the next in-game acceptance; **v0.2.16 has not yet been physically loaded or tested in RIFT**.

## P0 chat-source probe — correct the actual Windows launcher

The older `tools/rcm-log-probe.ps1` still started LuaPadModern's generic watcher directly, which could choose a fallback Documents directory instead of the one RIFT actually configured. RCM now launches its own `rcm-chat-observer.cjs` from PowerShell, while that observer continues to reuse LuaPadModern's proven decoder. The resulting `started.pathSelection` identifies the source, prioritizing `%APPDATA%\RIFT\Rift.cfg` `[Client] DocumentsDirectory` when there is no explicit `-LogPath` override.

A new optional `-SampleRawLines 1..30` forwards deliberately requested bounded raw-format discovery; the default remains metadata-only and does not emit general chat bodies. **Three real Windows PowerShell 5.1 regression tests pass**, including an isolated fake Rift.cfg, the actual Node process, path priority and timeout, plus negative input validation. The launcher never toggles `/log`, starts RIFT, sends input or edits SavedVariables. **No live RIFT Log.txt or normal player-chat reception has been demonstrated yet.** See [chat-source P0 engineering evidence and supervised live procedure](CHAT_SOURCE_LOG_LAUNCHER_FIX_20261120.md).

## Captured RIFT client API evidence — 1,940 documented entries

A previously collected, **complete API Atlas snapshot captured October 28, 2026** from the RIFT MMORPG client was independently audited on AMD-DESKTOP. It contains **1,940 named APIs**, including exactly **Event.Chat.Notify** and **Event.Chat.Npc** under `Event.Chat.*`, only `Inspect.Console.Detail` and `Inspect.Console.List` for console inspection, and `Event.Message.Receive` for **addon data**, not general social chat. No generic player-chat transcript event or console history readback is documented in that captured catalog. This does **not** prove undocumented runtime facilities are impossible or that a later game update exposes the exact same surface.

The new read-only host helper `tools/rcm_api_chat_capabilities.py --require-complete` projects capture time, client version and chat/console API names from an existing normalized API Atlas snapshot. It never executes documentation or copies chat bodies; it explicitly refuses to equate API documentation with verified live player-chat reception. **Five fixture tests passed**, and the real 1,940-entry local capture was accepted with a complete provenance report. The installed RCM v0.2.16 addon was not changed. See [API capture evidence, source limitations and rerun procedure](CHAT_API_CAPABILITY_CAPTURE_20261120.md).

## Host observer P0 — deterministic first-event readiness

A new child-process regression reproduced an actual observer JSONL ordering defect: a chat candidate arriving in the initial log poll was emitted before the `started` path/nonce receipt. The host reader now buffers only first-poll callbacks until it advertises readiness, then emits first-poll file events, candidates and matching marker receipts in deterministic order. The red test failed before correction and passed afterward. **193/193 Python/Lua and 28/28 Node.js tests passed (221 total)**. A separate dry run again verified all 10 installed v0.2.16 addon files with zero pending deployment changes. This is a **Windows-only source fix**; neither native social-chat capture nor physical v0.2.16 acceptance is yet established. See [root-cause analysis, red/green test and acceptance handoff](CHAT_OBSERVER_STARTUP_ORDER_20261120.md).

## Host observer P0 — marker first, player-chat candidate second

The previous Windows observer stopped once its LPB_PROBE marker was matched. This was appropriate for proving one console marker reached a file, but the shared LuaPadModern tailer then ceased all further reading, so no later player-chat line could be tested in the same run. The optional **--require-chat-after-marker** flag now makes RCM close that matched tailer, open a fresh read boundary on the same file, and emit **chat_phase_armed**. Only newly appended candidate chat after this readiness event can complete the second stage. Pre-marker lines, including lines arriving in the marker's read, cannot satisfy the test.

The guarded second stage handles repeated markers by rearming; it rejects a log file truncated, replaced or lost after the marker and fails if the only subsequent text is an unrecognized format. Even a successful candidate is explicitly labelled historical/unverified until independently correlated with the actual RIFT game window. The PowerShell entrypoint supports **-RequireChatAfterMarker** and continues to keep raw text off by default. The full suites passed **193/193 Python/Lua** and **34/34 Node** cases (**227 total**). Installed RCM v0.2.16 remains unchanged with 10/10 matching SHA-256 hashes. See the [two-phase chat-source evidence and supervised trial procedure](CHAT_OBSERVER_TWO_PHASE_20261120.md).

## Host import correctness — prevent incomplete chat from appearing complete

A new regression uncovered **silent content loss**: when the read-only observer bounded a long player-chat body to a 512-byte UTF-8 prefix, its `--prepare-import` option and the separate `--stdin-json` importer still produced valid `/rcm import` commands for the shortened message. A synthetic 520-byte Guild line reproduced this. Both ingestion paths now refuse shortened records with `import_skipped: truncated_chat_body`, while still preparing complete subsequent messages. The encoder independently checks the original byte count even when the truncation flag is inconsistent. This keeps saved RCM history truthful instead of silently dropping the remainder of a chat message.

**193/193 Python/Lua and 37/37 Node tests passed (230 total)** after the fix. The installed RIFT Lua addon and SavedVariables schema are unchanged; this is a Windows host-only pipeline correction. Complete long-message support would require a coordinated model/protocol change beyond the current 512-byte body limit. See the [root-cause analysis and red/green receipt](HOST_IMPORT_TRUNCATED_MESSAGE_FIX_20261120.md).

## P0 exact player-chat test text — reject unrelated messages

The two-stage noncombat log probe previously returned success for **any** recognized candidate after the console marker. That could be somebody else's Guild/Say message, not the specific test line entered by the user. The optional **--require-chat-text TEST_TOKEN** flag, paired with **--require-chat-after-marker**, now requires an exact, case-sensitive 8–80-character ASCII test line. The observer performs the comparison before redacting candidate text; the normal terminal output provides only the matching boolean and metadata. Unrelated chat no longer ends the test, and noisy candidate limits fail rather than returning false success.

The PowerShell launcher supports **-RequireChatText TEST_TOKEN** and prevents using it without **-RequireChatAfterMarker**. Red/green tests reproduced two previously unimplemented behaviors (unrelated-then-exact and unrelated-only), plus the candidate-limit refusal and malformed argument checks. **193/193 Python/Lua and 40/40 Node tests passed (233 total)**, and a verified launcher preview did not disclose the test token. Installed RCM **v0.2.16** remains byte-for-byte unchanged with 10/10 hashes matching source. This is a test-integrity improvement, *not* proof that real RIFT Live writes player chat into Log.txt. See the [exact-text proof procedure and evidence](EXACT_CHAT_TEXT_PROOF_20261120.md).

## Current RIFT client logging implementation — verified static code path

The actual AMD-DESKTOP **November 17, 2026** RIFT client (`rift_x64.exe`, SHA-256 `df954b798331e18359be62a31cc74b49fc3f50b87385ebb080a5448256322c01`) was inspected **read-only** using the existing RRE pefile/Capstone toolchain. Its original instructions reference **LogConsole**, read the saved flag with a false default, and contain an on/off function that opens `{0}\\Log.txt` with CRT `_wfopen` mode `a` and closes it with `fclose`. A separate runtime toggle caller leads to literal **Noncombat logging enabled / disabled** messages. These are exact-build code observations, *not a claim that ordinary live player chat is already captured*.

The real `Rift.cfg` currently has **LogConsole=False** and sets **DocumentsDirectory** to the OneDrive RIFT folder. There is no current `Log.txt` at that configured path; RIFT is still closed. To avoid confusing a persisted flag with an active in-game state, the Windows observer now reports **persistedLogConsole** (true/false/unknown), **configReadable**, **runtimeLoggingEnabledVerified=false** and a clear readiness hint in the `started` receipt. Path and flag derive from a **single bounded read** of the existing config; no game setting is changed. This narrows the next P0 live test to enabling and confirming noncombat logging deliberately rather than guessing its existence. See the [exact November 17 client logging-disassembly evidence](RIFT_NOV17_LOGGING_IMPLEMENTATION_20261120.md).

## v0.2.17 — Import directly into RCM's own editor

The manual Windows host-ingress path no longer depends exclusively on RIFT's original native chat input. RCM's own editor now accepts **`:import ID INDEX/TOTAL BASE64URL`** (plus `:import status`, `:import cancel`, and `:import help`) through the **same** previously tested Lua receiver, saved-history publisher, and cross-restart token deduplication as `/rcm import`. No alternate decoder or persistent transfer ledger was created. Successful import chunks are **excluded from command-history recall**, so encoded chat does not linger in a second UI surface. Receipts indicate real assigned RCM history IDs without claiming native social-chat capture or disk persistence. A new GetStatus().hostEditorImportReady flag distinguishes editor availability from still-unavailable automatic host input.

The Windows encoder supports **`--input-mode editor`** to generate copyable `:import` commands instead of default native `/rcm import` commands, including for explicitly supplied JSON candidate chat. Both modes use exactly the same validated RCM1-B64URL bytes and transfer token. **195/195 Python/Lua and 43/43 Node tests passed (238 total)** after red/green reproduction of the missing editor routing. A proper physical RIFT startup, editor focus/Enter acceptance, and on-disk imported-row proof remain outstanding. **Physical deployment at 9:10 PM EST:** the guarded installer confirmed RIFT closed, backed up the prior four changed files, and independently verified all **10 source/install hashes** for v0.2.17. A separate read-only audit found character SavedVariables unchanged. The real game still needs a fresh v0.2.17 startup and own-editor import acceptance. See [v0.2.17 engineering history and installation evidence](V0_2_17_RCM_EDITOR_IMPORT_20261120.md).

## Windows host observer — prepare editor imports without native chat

The Windows noncombat observer now supports **`--prepare-import --input-mode editor`**, generating bounded **`:import`** commands directly from candidate chat records through the existing RCM1-B64URL encoder. Its default **native** mode still emits `/rcm import` commands. The PowerShell wrapper exposes the same explicit choice as **`-PrepareImport -InputMode editor`**, and rejects editor mode without the opt-in preparation switch. Prepared commands contain encoded chat text and **require manual entry**; neither tool sends keys, enables RIFT logging or claims verified native player-chat reception.

Red/green Node process tests proved the new option, validated the decoded payload and unchanged source classification, and confirmed default native behavior remains intact. An actual Windows PowerShell 5.1 → Node fixture verified the editor mode reaches the observer. **196/196 Python/Lua and 44/44 Node tests pass (240 total)**, with the installed v0.2.17 package unchanged and all 10 file hashes matching source. The current game LogConsole=False setting still blocks direct real-log verification until deliberately enabled and tested. See [host observer editor-target release notes](HOST_OBSERVER_EDITOR_MODE_20261120.md).

## Host import command preparation — redacted observation, complete internal payload

The observer's **--prepare-import** option previously also forced **--include-text**, duplicating each recognized chat message in clear candidate JSON and reversible encoded import commands. That was unnecessary for manual host delivery and interfered with the advertised metadata-only observation mode. The implementation now passes a **separate internal full candidate** to the original encoder while keeping normal candidate event output redacted unless **--include-text** is independently requested. The same separation survives the marker-then-chat boundary and rejects candidate records when the underlying log is replaced or truncated. No input is sent and no normal player-chat capture is claimed.

Real Node child-process red/green tests reproduced the previous duplication; cross-component tests also prove exact post-marker **:import** generation, refusal after source resets, and explicit include-text behavior. **196/196 Python/Lua plus 47/47 Node.js tests passed (243 total)**. Installed RCM v0.2.17 and the character SavedVariables file were not changed; the 10-file deployment integrity check passes. Details: [prepared import redaction root-cause and regression evidence](HOST_PREPARED_IMPORT_REDACTION_20261120.md).

## .NET 10 editor-command preflight — no keyboard or game actions

A new .NET 10 Windows helper in tools/RcmEditorInput validates RCM-owned **:import TOKEN INDEX/TOTAL BASE64URL** commands and returns only a SHA-256 fingerprint and bounded part/count metadata, not the reversible encoded chat body. It also supports **--stdin-command** to keep encoded chat out of Windows process arguments, plus read-only inspection of a running RIFT process PID/start epoch/window/path/build SHA and exact pin matching. It **does not type, paste, submit, focus RIFT, or verify actual RCM editor input**; successful process identity alone is not evidence that the game accepted any command.

The tool's original tests found an incorrect fixture length and a real .NET regex trailing-newline acceptance defect; both were corrected. Windows subprocess integration also verified stdin handling and refusal of multiple, incomplete or malformed commands. **21/21 built-in .NET assertions and 7/7 new Python integration tests passed.** The full repository suites at that milestone passed **203/203 Python/Lua plus 47/47 Node.js tests (250 total)**. See the [read-only .NET 10 preflight contract, failures and next physical acceptance](RCM_EDITOR_PREFLIGHT_DOTNET10_20261120.md).

## v0.2.18 source — focus-state consistency and native RIFT screenshots

An actual RIFT game screenshot made at 9:39:25 PM EST, November 20 revealed an RCM focus discrepancy: the header correctly indicated **INPUT • NOT FOCUSED**, but the footer still said **Editor focused** from an earlier focus action. The v0.2.18 Lua source fixes the cause: only a focus-specific footer is synchronized with live RiftTextfield:GetKeyFocus-derived state changes. Import receipts and other command results are never overwritten by focus polling. The regression reproduced the contradictory state before the fix and passed after it, including editor/search focus and other status-message preservation.

The new **read-only** `tools/rcm_game_screenshot_receipt.py` resolves RIFT's configured screenshot directory, checks complete JPEG/PNG bytes, SHA-256 and dimensions, and can mark a precise timestamp baseline to reject stale captures. The native game screenshot dated November 20 at 9:39 PM was verified as JPEG **2560×1369**, SHA-256 `8f56980b976657ddf43028056b71798b7919628d5b023adb94492b3e220f1ffe`. **Eight** screenshot fixture tests passed, including fresh vs stale, malformed, renamed and concurrently created file handling. The helper never presses a key or writes a game file.

**259/259 tests passed at the initial v0.2.18 source milestone (212 Python/Lua, 47 Node.js).** The three changed addon files were subsequently installed **while RIFT was running**, and their hashes verified; the game requires `/reloadui` to load those bytes. See [v0.2.18 focus root-cause and native screenshot verification report](V0_2_18_FOCUS_AND_GAME_SCREENSHOTS_20261120.md).

## One-shot RIFT Numpad * screenshot trigger — .NET 10

A separate, tightly scoped **RcmScreenshotKey** Windows helper can inspect the actual RIFT PID, startup epoch, HWND, executable path/hash and foreground state before considering an in-game screenshot hotkey. Unlike the read-only RcmEditorInput helper, **only** its explicit `--capture --ack-single-screenshot` mode is capable of sending input: one `VK_MULTIPLY` key-down/key-up pair through Windows SendInput. It does **not** steal foreground focus, type commands or change client/clipboard/SavedVariables data. A separate `--dry-run` checks all conditions without sending anything. The existing independent `rcm_game_screenshot_receipt.py` verifies whether a new real JPEG appeared after the trigger's baseline timestamp; OS input insertion alone is not counted as a game screenshot.

The optional **`--arm-seconds 1..15`** mode now waits briefly for RIFT to become the foreground window, without ever activating it. It still requires the explicit one-shot capture acknowledgment and all six exact process/window pins; timeout means **no input**. A failing test first exposed that this option did not exist, and the completed implementation passed its bounded validation and error-case tests. A controlled two-second arm expired as `foreground_timeout_no_input`, and the independent screenshot checker still found no new image.

**Eight Windows subprocess integration tests and 19 internal .NET assertions pass**. If Windows accepts only a key-down during a partial SendInput call, RCM now attempts one **keyup-only recovery**, and only while the same RIFT HWND remains foreground and owned by the same PID; it never repeats the screenshot key-down. The latest full repository suites pass **267/267 tests (220 Python/Lua and 47 Node.js)**. This screenshot-helper milestone itself did not change the RIFT Lua package. The later **v0.2.18 live deployment succeeded without stopping RIFT**. See [one-shot screenshot key helper, arm mode, evidence and controlled acceptance procedure](RCM_NUMPAD_SCREENSHOT_TRIGGER_20261120.md).

## Native screenshot capture from a single command

The new `tools/rcm_screenshot_once.py` removes the manual six-field PID/HWND/process-hash handoff. It checks the actual RIFT process through the existing .NET helper, pins the matching identity, optionally arms a single Numpad `*` screenshot for at most 15 seconds, and independently verifies whether RIFT's configured screenshot folder received a **new complete JPEG** after the trigger timestamp. A read-only **--dry-run** is available by default; actual key input requires both **--capture** and **--ack-single-screenshot**. The tool never steals foreground focus or retries an uncertain keypress.

Ten deterministic cross-component tests passed after red/green corrections for corrupt new images, unavailable screenshot folders and invalid post-key baselines. All these failures retain the known key-insertion result instead of converting it into a false claim that no input occurred. The live one-command trial returned **foreground_timeout_no_input** while RIFT was in the background, with zero key events and no new screenshot. **277 total repository tests pass (230 Python/Lua and 47 Node.js)**. Details and the compact Windows PowerShell command are in the [one-command screenshot engineering report](RCM_ONE_COMMAND_SCREENSHOT_20261120.md).

## Current live deployment policy — update while RIFT runs, then /reloadui

A previous RCM installer check incorrectly treated any running `rift_x64.exe` as a reason to refuse addon deployment. **That assumption has been corrected.** A fresh live deployment on AMD-DESKTOP replaced the three pending v0.2.18 files (`Core.lua`, `Main.lua`, `RiftAddon.toc`) while PID 34596 remained running. The installer created verified backups, and an independent second pass confirmed **10/10 source/installed hashes match**, with character SavedVariables untouched. The installer now returns `reloadUiRequired=true` for a changed live addon, false for an unchanged no-op, and keeps `runtimeReloadVerified=false` until game-side evidence exists.

The first verified live hot-deployment installed **v0.2.18**; source development has subsequently advanced to **v0.2.19**. **Actual UI activation still requires `/reloadui` and an in-game version check; no game restart is necessary.** This is now the standard RCM development iteration policy, enforced by new running-game/no-op regression tests. See the [root cause, corrected deploy procedure, red/green tests, and exact physical deployment receipt](LIVE_DEPLOYMENT_RELOADUI_POLICY_20261120.md).

## v0.2.19 — Preserve actively progressing multipart imports

The existing 45-second host transfer deadline was incorrectly measured from the **first** chunk, so a multi-part message could expire even while new fragments arrived regularly. The receiver now measures inactivity since the **last newly accepted fragment**, allowing a complete transfer that lasts longer than 45 seconds as long as each new part arrives promptly. Duplicate/rejected chunks do **not** reset the clock. This fixes a concrete root cause rather than adding another retry layer or protocol.

The failure was reproduced first using the real Node encoder and Lua 5.1 receiver: chunks 30 seconds apart exceeded the original 45-second absolute deadline and never completed. The corrected receiver produced exactly one imported row, preserved its transfer token and message-ID receipt, and still expired an idle import despite duplicate replays. **233/233 Python/Lua tests and 47/47 Node tests passed (280 total)**. The startup manifest and version-pinned tests are synchronized to **v0.2.19**, with SavedVariables schema 2 unchanged. **The release was deployed while RIFT was running**, with source/installed SHA-256 matching for **all 10 files**, backups of the four changed files, and no SavedVariables writes. **/reloadui** is required to activate the installed code; a live runtime reload has not yet been verified. See the [v0.2.19 root cause, red/green tests, and physical installation receipt](V0_2_19_MULTIPART_IDLE_TIMEOUT_20261120.md).

## Exact-build RIFT noncombat log writer — static evidence only

Read-only analysis of the November 17 RIFT Live executable traced the active noncombat logging file pointer to a line-writing region that calls **`fputs` for a prepared message, `fputs` again for a newline, then `fflush`**. It supports the existence of an actual line-writing mechanism, but **does not prove that the current client delivers ordinary Guild/Say/Tell/Party messages into the log**, nor does it establish the text encoding. RCM's historical log parser remains tentative until a real game-produced sample can be compared. See the [exact-client log writer source investigation and limits](RIFT_NOV17_NONCOMBAT_LINE_WRITER_20261120.md).

## Host companion — complete multipart editor batch (November 21)

The Windows .NET 10 `RcmEditorSender` now accepts **one complete 1–12-fragment Node import record** via `--stdin-batch`. Before any input is attempted, it verifies every fragment's token/order/size, canonical base64url, exact wire fields, Unicode validity and source metadata. **The default is validation-only**; a full batch send requires explicit focus/submission/batch acknowledgments and exact RIFT process pins, and cannot claim in-game receipt without physical evidence. This removes the need to coordinate separate helper launches for every encoded fragment. See [the batch bridge implementation, fail-closed tests and precise limits](RCM_MULTIPART_EDITOR_BATCH_20261121.md). No addon Lua or `.toc` was modified for this host-only milestone.

### Exact-source selection from the live observer JSONL

The host observer's JSONL output can now pass through **`tools/rcm-chat-batch-gate.cjs`**, which selects only the complete editor import following an exact, fresh, after-marker chat candidate and a matching final receipt. Unrelated messages, source resets, missing chunks, and dubious status claims are rejected instead of silently imported. `--status` streams sanitized marker/phase instructions to stderr while the observer runs; stdout contains only the selected batch for the .NET validator. This is **not** proof of physical native RIFT chat reception, which remains blocked pending a deliberate Log.txt experiment. See [observer-to-batch-gate workflow and tests](RCM_LOG_OBSERVER_BATCH_GATE_20261121.md).