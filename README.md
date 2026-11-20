# RIFT Chat Modern

**Standalone chat-style console and addon diagnostics hub for RIFT Live**

![RIFT Live](https://img.shields.io/badge/RIFT-Live-3bc4d0?style=flat-square) ![Lua](https://img.shields.io/badge/Lua-5.1-536dfe?style=flat-square) ![Version](https://img.shields.io/badge/Version-0.2.5-16a34a?style=flat-square) ![Status](https://img.shields.io/badge/Native_social_bridge-not_verified-c67b28?style=flat-square)

A compact, dark-mode chat window that can receive addon diagnostics, record event history, filter/search, copy to clipboard, and expose a command API to **all our RIFT repositories**. LuaPadModern inspired the editor focus design; this is **original code** with no LuaPadModern dependency or source modifications.

**Development record:** [Complete project history — concept, version timeline, failures, fixes, live proof, and outstanding work](docs/DEVELOPMENT_HISTORY_CONCEPT_TO_V0_2_2.md).

## Implemented

| Feature | Current state |
| --- | --- |
| Modern dark UI, default 760×618, **21pt title / 16pt message font** | ✅ Live v0.2.3; v0.2.4 resize mock-tested |
| Dedicated **18pt editor**, getter-verified input/search focus badge, Enter dispatch | ✅ Lua 5.1 mock; physical acceptance pending |
| Drag release outside, viewport clamping and saved placement | ✅ Tests |
| **Resizable window**, responsive message-history rows and saved width/height | ✅ v0.2.4 Lua 5.1 geometry tests; physical acceptance pending |
| **Paged detail reading** for long messages at compact window sizes | ✅ v0.2.4 Lua 5.1 tests |
| Bundled Lato Regular/Bold fonts and original OFL license | ✅ SHA-256 verified |
| All / Chat / System / NPC / Addons / Dev tabs | ✅ |
| Timestamped history, paging, search | ✅ |
| Copy filtered chat history to clipboard, including `:copy` | ✅ Via Command.CopyToClipboard |
| **Click-to-expand full messages** and copy one message | ✅ Lua 5.1 UI tests |
| Opt-in capture of other addons' `Command.Console.Display` output | ✅ Mocked runtime; live acceptance pending |
| Inspect real native console channel subscriptions | ✅ `Inspect.Console.List/Detail` read-only tests |
| RIFT NPC lines and screen notifications | ✅ Via documented Event.Chat APIs |
| Addon diagnostic publication and subscriptions | ✅ |
| Register local commands from sibling addons | ✅ |
| Built-in optional RPT Lab status/arm/mark/stop/last | ✅ |
| **Reliable RIFT addon-data messaging to another client** | ✅ Lua 5.1 API mock; physical acceptance pending |
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
- **Main.lua:** draggable dark frame, getter-backed focus indicator, editor, event adapters and RPT Lab integration.
- **fonts/**: bundled Lato Regular/Bold and original SIL Open Font License. The app uses native font fallback if custom fonts aren't available.

Copy the whole folder to the physical RIFT Interface\AddOns folder. Restart RIFT if it has not discovered the new addon, or enable it in the AddOns manager.

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
| :native channels | Show names and configured chat subscriptions (metadata, not transcript) |
| :native copy | Copy the native console configuration report to clipboard |
| :mirror on / off / status | Opt-in mirroring of other addons' console output; never player chat |
| :copy | Copy all currently filtered history via the game clipboard API |

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
| GetStatus() | Version, ready/visible state, **editorFocusState** (`focused`, `search`, `unfocused`, `hidden`, `unavailable`), focus flags, filter, count and capabilities |
| RegisterCommand(name, callback) | Register local colon-command |
| Subscribe(name, callback) / Unsubscribe(name) | Receive copied event data |
| Submit(":command args") | Execute a local command |
| Copy() | Copy filtered history to Windows clipboard |
| Show() / Hide() / FocusEditor() / FocusSearch() | Explicit own-window GUI focus operations |
| SendAddon(target, message) | Request reliable addon-data send with server queue acknowledgment (not peer delivery) |
| GetAddonTransportStatus() | Read queue-ready, pending, accepted/rejected/unknown, received and invalid counters |
| GetNativeConsoles() | Read-only native-frame and console-channel metadata; **never** claims ordinary chat-message access |
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
