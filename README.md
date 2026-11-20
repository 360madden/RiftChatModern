# RIFT Chat Modern

**Standalone chat-style console and addon diagnostics hub for RIFT Live**

![RIFT Live](https://img.shields.io/badge/RIFT-Live-3bc4d0?style=flat-square) ![Lua](https://img.shields.io/badge/Lua-5.1-536dfe?style=flat-square) ![Version](https://img.shields.io/badge/Version-0.2.1-16a34a?style=flat-square) ![Status](https://img.shields.io/badge/Native_social_bridge-not_verified-c67b28?style=flat-square)

A compact, dark-mode chat window that can receive addon diagnostics, record event history, filter/search, copy to clipboard, and expose a command API to **all our RIFT repositories**. LuaPadModern inspired the editor focus design; this is **original code** with no LuaPadModern dependency or source modifications.

## Implemented

| Feature | Current state |
| --- | --- |
| Modern dark UI, 760×618, **21pt title / 16pt message font** | ✅ Lua 5.1 geometry tests |
| Dedicated **18pt editor**, getter-verified input/search focus badge, Enter dispatch | ✅ Lua 5.1 mock; physical acceptance pending |
| Drag release outside, viewport clamping and saved placement | ✅ Tests |
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

**Important:** The first build is a useful chat-style window and developer console, **not yet a full social-chat replacement**. Native RIFT chat remains untouched as fallback. A Windows/Python host input/output adapter is a follow-up, not something simulated as success.

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

Built on AMD-DESKTOP for reusable RIFT development tooling.
