# RIFT Chat Modern

**Standalone chat-style console and addon diagnostics hub for RIFT Live**

![RIFT Live](https://img.shields.io/badge/RIFT-Live-3bc4d0?style=flat-square) ![Lua](https://img.shields.io/badge/Lua-5.1-536dfe?style=flat-square) ![Version](https://img.shields.io/badge/Version-0.2.10-16a34a?style=flat-square) ![Status](https://img.shields.io/badge/Native_social_bridge-not_verified-c67b28?style=flat-square)

A compact, dark-mode chat window that can receive addon diagnostics, record event history, filter/search, copy to clipboard, and expose a command API to **all our RIFT repositories**. LuaPadModern inspired the editor focus design; this is **original code** with no LuaPadModern dependency or source modifications.

**Development record:** [concept through v0.2.2, including failures and live proof](docs/DEVELOPMENT_HISTORY_CONCEPT_TO_V0_2_2.md), [v0.2.3 navigation](docs/V0_2_3_NAVIGATION_AND_RELEASE.md), [v0.2.4 resizing](docs/V0_2_4_RESIZE.md), [v0.2.5 codebase bug hunt](docs/V0_2_5_CODEBASE_BUGHUNT.md), [v0.2.6 editor improvements / deployment receipt](docs/V0_2_6_EDITOR_HISTORY_AND_SEARCH.md), [v0.2.7 console subscription discovery](docs/V0_2_7_NATIVE_CHANNEL_DISCOVERY.md), [v0.2.8 Log.txt probe pilot](docs/V0_2_8_LOG_PROBE_HANDOFF.md), [host chat observer research / tests](docs/HOST_CHAT_OBSERVER_20261120.md), [v0.2.9 manual host ingress](docs/V0_2_9_MANUAL_HOST_INGRESS.md), and [v0.2.10 transfer recovery / guarded deployment](docs/V0_2_10_IMPORT_RECOVERY_AND_DEPLOYMENT.md).

## Implemented

| Feature | Current state |
| --- | --- |
| Modern dark UI, default 760×618, **21pt title / 16pt message font** | ✅ v0.2.2 basic UI live-verified; later revisions offline-verified, live acceptance pending |
| Dedicated **18pt editor**, getter-verified input/search focus badge, Enter dispatch | ✅ Lua 5.1 mock; physical acceptance pending |
| **Session-only Up/Down command recall**, 32 entries, restores unsent draft | ✅ v0.2.6 Lua 5.1 tests; live key acceptance pending |
| Search field stays synchronized with `:find` and `/rcm find` | ✅ v0.2.6 regression tests |
| Drag release outside, viewport clamping and saved placement | ✅ Tests |
| **Resizable window**, responsive message-history rows and saved width/height | ✅ v0.2.4 Lua 5.1 geometry tests; physical acceptance pending |
| **Paged detail reading** for long messages at compact window sizes | ✅ v0.2.4 Lua 5.1 tests |
| Bundled Lato Regular/Bold fonts and original OFL license | ✅ SHA-256 verified |
| All / Chat / System / NPC / Addons / Dev tabs | ✅ |
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
| Windows-side **candidate social-chat observer**, using existing LuaPadModern log decoder | ✅ 14 Node observer tests; historical format only, physical Log.txt receipt pending |
| **Manual host-to-RCM chat import**, UTF-8/base64url chunks and `HOST?` provenance | ✅ v0.2.10 adds visible chunk receipts, transfer status/cancel; physical acceptance pending |
| **Guarded installation**, hostname check, backups, manifest contract and SHA-256 | ✅ v0.2.10 fixture tests and actual AMD-DESKTOP deployment |
| **Opt-in log feasibility probe** compatible with LuaPadModern `LogTailProbe` | ✅ v0.2.8 tests and cross-repo parser smoke; real RIFT disk transport unverified |
| **Native console read-only capability probe** | ✅ Lua 5.1 getter/mock tests |
| Saves up to 240 messages, character scoped | ✅ |
| Capture ordinary native player chat (say/party/guild/tell) | ⏳ Not verified |
| Transmit ordinary native player chat / arbitrary native slash | ⏳ Not available through the verified addon APIs |

**Important:** RiftChatModern is a chat-style window and developer console, **not yet a full social-chat replacement**. Native RIFT chat remains untouched as fallback. A Windows/Python host input/output adapter is a follow-up, not something simulated as success.

## Install / start

The source addon is **C:\work\RiftChatModern\addon\RiftChatModern**:

- **RiftAddon.toc:** identity, version, placeholder contact, startup and SavedVariables.
- **Core.lua:** bounded model, search, filters, history, subscriptions and local commands.
- **AddonMessages.lua:** dedicated `RCMDevV1` addon-data channel, send/receive validation, queue acknowledgment and timeout handling.
- **NativeChatProbe.lua:** read-only native-frame and actual console subscription inventory; does not modify consoles or read native player-chat text.
- **ConsoleMirror.lua:** disabled-by-default pass-through of RIFT `Command.Console.Display` calls into searchable addon-output history. It restores the original function when safely possible and does not intercept player chat.
- **HostIngress.lua:** validated, bounded, transient manual host-to-addon chat import; imported text is visibly tagged as unverified.
- **Main.lua:** draggable dark frame, getter-backed focus indicator, editor, event adapters and RPT Lab integration.
- **fonts/**: bundled Lato Regular/Bold and original SIL Open Font License. The app uses native font fallback if custom fonts aren't available.

Use `tools/deploy_rcm.py` for a dry-run before updating the verified physical RIFT Interface\AddOns folder. An `--apply` requires the exact expected hostname, backs up replaced files under the local ignored `artifacts/` folder and verifies all installed file hashes. The running game still needs an intentional UI reload and separate physical acceptance.

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
if chat and chat.interfaceVersion == 1 then
    chat.Publish("addons", "Position sampler ready", "RR2")
    chat.RegisterCommand("rr2", function(args)
        if args == "status" then return "RR2: running" end
        return "Usage: :rr2 status"
    end)
end
~~~

| API | Description |
| --- | --- |
| Publish(kind, message, source) | Add a timestamped message and notify subscribers |
| GetHistory(kind, search, limit, offset) | Return copies, never mutable history references |
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
| GetHostIngressStatus() | Manual import mode, accepted chunks, pending fragment counts, completed imports, duplicates, cancellations, errors and expiry; **not native-chat delivery proof** |
| GetNativeConsoles() | Read-only native-frame and console-channel metadata, including `publicChannels`, `publicChannelCount`, `publicChannelsTruncated` per console; **never** claims ordinary chat-message access |
| SetConsoleMirror(boolean) / GetConsoleMirrorStatus() | Explicit optional pass-through interception of addon console output, preserving native behavior |
| GetFocusState() | Read the addon-owned input/search focus state; does not infer native RIFT chat focus |
| SetWindowSize(width, height) | Resize and persist a window's dimensions; requires initialized addon |

Channel labels include **general, party, guild, tell, system, npc, combat, addons, dev**. They are *categories* for records, not assertions that the game server transmitted them.

Limits: 240 saved rows, 512-byte messages, 40-byte sources, 60-byte search, 48 KB clipboard export. Stored data is character-scoped. Corrupted saved histories cause a refusal rather than a silent reset.

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

[Version 0.2.1 developer notes](docs/V0_2_1.md) explain message details, mirror behavior and native subscription metadata.

See [addon messaging and native-console probe](docs/ADDON_TRANSPORT.md) for the exact APIs, reliable-send restrictions and evidence limits.

**v0.2.2 startup hotfix (November 20):** RIFT reported four real addon-load errors in v0.2.1 (Core, AddonMessages, NativeChatProbe and ConsoleMirror). Their top-level module return values were removed from RunOnStartup execution, and a dedicated loader-contract regression test was added. The fix was subsequently **observed working in the physical RIFT client**: v0.2.2 loaded, /rcm opened, the editor-focus indicator responded, and the window dragged. No new four-module assertions were observed in the captured startup portion; this is not an exhaustive absence-of-errors guarantee. See [live startup fix](docs/V0_2_2_LIVE_STARTUP_FIX.md) and [live acceptance report](docs/LIVE_ACCEPTANCE_V0_2_2_20261120.md).

Built on AMD-DESKTOP for reusable RIFT development tooling.

## v0.2.3 navigation polish (2026-11-20)

The message-history pagination buttons now read **OLDER** and **NEWER** instead of tiny arrow glyphs. The manifest, startup window and status API all report v0.2.3. All 54 Lua 5.1 mock tests passed, including the RIFT startup-loader contract and paging-control regression. Physical RIFT acceptance of v0.2.3 remains pending; the physical v0.2.2 acceptance is preserved in the historical report.

The addon is also available publicly at https://github.com/360madden/RiftChatModern.

## v0.2.4 — resizable responsive window

Drag the **// grip** at the bottom-right corner of the RCM window to resize horizontally, vertically, or diagonally. The title bar still moves the window independently. The history region consumes most added height, dynamically expanding the number of rows shown; wider windows reveal longer message previews. At the compact minimum (680 × 480), message details have **PREV/NEXT** pages with a page indicator so long text remains accessible.

Window position and dimensions persist under the existing character-scoped RiftChatModernSaved.ui (x, y, w, h) with validation and viewport clamping. Existing messages and custom UI state are preserved. The new API SetWindowSize(w, h) is additive; interfaceVersion remains 1. The native chat command /rcm size 1000 750 provides a direct test and /rcm size reset restores the default size.

**Verification:** 63/63 Lua 5.1 mock tests, including resize gestures, independent axes, mouse release outside, full control containment, persistence and restore, viewport clamping, detailed messages, RIFT startup loader contract and old API regression. **Physical v0.2.4 acceptance remains separate**; inspect the in-game version, resizing, saved dimensions after /reloadui and errors before claiming a live pass. See [v0.2.4 engineering notes](docs/V0_2_4_RESIZE.md).

## v0.2.5 — Codebase bug hunt and reliability fixes

This release audits all five Lua runtime modules, the RIFT manifest, local tests, and API compatibility against the installed RIFT API reference.

**Resolved:** RIFT frame-anchor accumulation on reflow (clear anchors and restore sizes); oldest-page overlap and incorrect history counters; malformed clipboard export bounds; duplicate saved message IDs; persisted search controls; UTF-8 safe command responses, NPC/alert text, message previews, console metadata and mirrored diagnostics; blank NPC names; addon-data storage failures counted as received; and uncertain send submissions misclassified as server rejections.

**Testing:** 76/76 Lua 5.1 regression tests passed, including new bug-hunt and messaging checks. Existing SavedVariables schema, addon transport identifier, CLI commands and public API interfaceVersion = 1 remain compatible. Full audit details and evidence limitations are in [v0.2.5 bug hunt](docs/V0_2_5_CODEBASE_BUGHUNT.md).

**Physical in-game acceptance:** separate from mock verification. Loading the installed files in RIFT, error checks, drag/resize, paging, and clipboard behavior must be verified in the actual client before being labeled LIVE PASS. Normal native social chat still requires a distinct bridge.

## v0.2.6 — Console input history and search synchronization

**New:** The local editor now remembers the latest 32 successfully submitted `:` commands for in-session Up/Down recall, avoids consecutive duplicates, and restores unsent text when navigating forward past the newest command. An edit or paste exits navigation. The history is deliberately **not persisted** to SavedVariables; unsent native/social drafts are never counted as successful commands. API calls to `Submit` are separate from manual editor recall.

**Fixed:** `:find` and `/rcm find` previously changed the active model search without updating the visible search textbox. The renderer now synchronizes the query without redundant change events.

**Compatibility regression caught before deployment:** Adding keyboard handlers initially pushed the UI constructor beyond the Lua 5.1 **60-upvalue** compilation limit, failing many tests and preventing addon startup. Input callbacks were consolidated through the existing controls upvalue; the revised loader and runtime suites pass **81/81 tests**. These are offline tests, not physical keyboard acceptance.

See [v0.2.6 engineering and acceptance notes](docs/V0_2_6_EDITOR_HISTORY_AND_SEARCH.md). Native social-chat send/receive remains unimplemented through the verified Lua addon API. No character SavedVariables migration or destructive install procedure is required.

## v0.2.7 — Native console subscription discovery

The read-only native inspector now recognizes **all 27 documented boolean subscription flags** from `Inspect.Console.Detail` (including raid warnings, loot and other combat/crafting categories). It also handles `Detail.channel` as a **public-channel name table**, displaying named channels such as `LookingForGroup` and `World@Deepwood` in `:native channels` and `:native copy`. The earlier inspector only checked 12 boolean fields and silently discarded public-channel names. Results are bounded, sorted, sanitized and reported separately from any actual chat text.

The API handles console ID maps returned by `Inspect.Console.List()`, preserves the public `interfaceVersion=1`, and continues to mark native transcript capture/social chat send as unverified. Mocked Lua 5.1 test coverage grew from 81 to **83**. The revised code was validated against the shipped Gadgets addon examples and historical RIFT API documentation, not yet independently accepted in the physical client.

See [v0.2.7 implementation, source findings, risks and live checklist](docs/V0_2_7_NATIVE_CHANNEL_DISCOVERY.md).

## v0.2.8 — RIFT-to-host Log.txt feasibility probe

From RCM's focused editor, type `:logprobe RCM_TEST_20261120` to print a bounded nonce marker to the game's **native console**. This is a manually initiated diagnostics action; it does not toggle RIFT logging and cannot claim that a line reached disk. The matching Windows-side launcher at `tools/rcm-log-probe.ps1` reuses **LuaPadModern's existing read-only Node log watcher** instead of implementing a second tailer.

**Preparation preview in Windows PowerShell 5.1 or 7 (run from the RCM repo):**

```powershell
.\tools\rcm-log-probe.ps1 -Preview -Nonce RCM_TEST_20261120
```

When RIFT is intentionally configured to write a verified `Log.txt`, remove `-Preview` to start one bounded watcher; then enter the matching `:logprobe` command in the already-loaded RCM editor. The watcher reports receipts but never sends game input. **Do not blindly type `/log`**: it toggles logging state.

**Tests:** 87/87 Lua 5.1 cases; 4 new cases test valid/invalid marker emission, unavailable APIs and missing server clock. The Windows PowerShell 5.1 preview and rejection paths were tested, and the exact marker was recognized by LuaPadModern's `LogTailProbe.readLine` against a synthetic string. No RIFT Live `Log.txt` receipt or player-chat ingestion has been demonstrated. See [v0.2.8 notes](docs/V0_2_8_LOG_PROBE_HANDOFF.md).

## Windows host candidate-chat observer (source-only; in-game version remains v0.2.8)

The independent `tools/rcm-chat-observer.cjs` listens for new records in a RIFT `Log.txt` using LuaPadModern's existing bounded file decoder; it does **not** copy or replace that decoder. It parses historical bracketed sender/channel formats and emits structured *candidate* events to the Windows terminal. `--include-text` is required to output message bodies; by default the tool emits metadata only. It handles UTF-8/UTF-16, partial appends, log truncation and newly created files. A matched `LPB_PROBE` nonce ends the bounded run.

From a **Windows PowerShell** terminal in `C:\work\RiftChatModern`:

```powershell
node .\tools\rcm-chat-observer.cjs --help
node .\tools\rcm-chat-observer.cjs --nonce RCM_CHAT_20261120 --timeout-ms 120000
node --test .\tests\test_chat_observer.cjs .\tests\test_chat_observer_cli.cjs
```

**Verification:** 13/13 separate Node tests using synthetic files and child processes; original 87/87 Lua addon tests unchanged. RIFT's current `Log.txt` is not yet verified, so the parser's records explicitly mark `verifiedLiveFormat=false`. The observer does not ingest messages back into the in-game addon and does not send native social chat. **No new .toc version or addon deployment was required at the host-observer checkpoint.**

See [host observer implementation, historical sources, known failures and live protocol checklist](docs/HOST_CHAT_OBSERVER_20261120.md).

## v0.2.9 — Bounded manual host-to-addon import

This release introduces the missing inbound half of the Windows-host research path. The Node helper `tools/rcm-chat-import.cjs` converts a candidate-chat JSON record into one or more compact `/rcm import ...` native slash commands. A new Lua 5.1 `HostIngress.lua` module (registered **before Main.lua in the six-file manifest**) validates and reassembles the chunks, then publishes a clearly marked `[HOST? Channel]` message into RCM history.

**Synthetic demonstration** (Windows PowerShell in `C:\work\RiftChatModern`):

```powershell
node .\tools\rcm-chat-import.cjs --kind guild --sender Atank --channel Guild --text "Hello from host"
```

Copy the `commands` field's complete `/rcm import ...` line and paste it into **RIFT's original native chat input** after v0.2.9 is loaded. RCM's **CHAT** or **ALL** tab will contain the imported candidate, visibly labeled as external. Long messages yield several commands; copy every part. No command is sent automatically.

For the existing Windows log observer, `--prepare-import` explicitly enables body-text output and prints these manual commands alongside each candidate record. Without a verified RIFT `Log.txt`, that observer still cannot acquire actual player messages.

**Validation:** 95/95 Lua 5.1 tests and 22/22 Node.js tests (117 total). Includes cross-language round trips, duplicate suppression, out-of-order chunks, malformed UTF-8, bounded payloads, missing callbacks and native slash dispatch under mocked RIFT APIs. **Physical import acceptance, real Log.txt reception, and automatic host input remain pending.** See [v0.2.9 engineering and live acceptance checklist](docs/V0_2_9_MANUAL_HOST_INGRESS.md).

## v0.2.10 — Native import feedback, recovery and repeatable deployment

After manually pasting a long `/rcm import` transfer in original RIFT chat, the addon now **prints a colored receipt for each accepted chunk** even when its custom window is hidden. `/rcm import status` reports the active message ID and chunk progress; `/rcm import cancel` abandons a stuck transfer without deleting saved messages. The in-window commands `:host status` and `:host cancel` provide the same operations. A pending transfer also expires when its status is queried after the existing 45-second limit.

**New guarded installer:** `tools/deploy_rcm.py` selects an existing RCM installation, verifies .toc identity and startup metadata, requires an exact hostname for applying changes, preserves backups and compares source/installed file hashes. From Windows PowerShell at `C:\work\RiftChatModern`:

```powershell
& "C:\work\riftreader2\.venv\Scripts\python.exe" -B tools\deploy_rcm.py
& "C:\work\riftreader2\.venv\Scripts\python.exe" -B tools\deploy_rcm.py --apply --expect-host AMD-DESKTOP
```

**Verification:** 107/107 Python/Lua tests plus 22/22 Node.js tests. The actual AMD-DESKTOP deployment replaced only four changed files, backed up the prior installed copies and verified **10/10 source/deployed SHA-256 matches**. No SavedVariables or unrelated addons were touched. **The running physical RIFT client has not yet been independently accepted for v0.2.10.**

See [v0.2.10 release notes, tests, deployment proof and live checklist](docs/V0_2_10_IMPORT_RECOVERY_AND_DEPLOYMENT.md).
