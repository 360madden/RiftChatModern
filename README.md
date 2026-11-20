# RIFT Chat Modern

**Standalone chat-style console and addon diagnostics hub for RIFT Live**

![RIFT Live](https://img.shields.io/badge/RIFT-Live-3bc4d0?style=flat-square) ![Lua](https://img.shields.io/badge/Lua-5.1-536dfe?style=flat-square) ![Version](https://img.shields.io/badge/Version-0.1.0-16a34a?style=flat-square) ![Status](https://img.shields.io/badge/Native_social_bridge-not_verified-c67b28?style=flat-square)

A compact, dark-mode chat window that can receive addon diagnostics, record event history, filter/search, copy to clipboard, and expose a command API to **all our RIFT repositories**. LuaPadModern inspired the editor focus design; this is **original code** with no LuaPadModern dependency or source modifications.

## Implemented

| Feature | Current state |
| --- | --- |
| Modern, legible dark UI and draggable header | ✅ Lua 5.1 mocked runtime |
| Dedicated editor with explicit focus and Enter dispatch | ✅ Mocked runtime |
| All / Chat / System / NPC / Addons / Dev tabs | ✅ |
| Timestamped history, paging, search | ✅ |
| Copy all filtered chat history to clipboard | ✅ Via Command.CopyToClipboard |
| RIFT NPC lines and screen notifications | ✅ Via documented Event.Chat APIs |
| Addon diagnostic publication and subscriptions | ✅ |
| Register local commands from sibling addons | ✅ |
| Built-in optional RPT Lab status/arm/mark/stop/last | ✅ |
| Saves up to 240 messages, character scoped | ✅ |
| Capture ordinary native player chat (say/party/guild/tell) | ⏳ Not verified |
| Transmit ordinary native player chat / arbitrary native slash | ⏳ Not available through the verified addon APIs |

**Important:** The first build is a useful chat-style window and developer console, **not yet a full social-chat replacement**. Native RIFT chat remains untouched as fallback. A Windows/Python host input/output adapter is a follow-up, not something simulated as success.

## Install / start

The source addon is **C:\work\RiftChatModern\addon\RiftChatModern**:

- **RiftAddon.toc:** identity, version, placeholder contact, startup and SavedVariables.
- **Core.lua:** bounded model, search, filters, history, subscriptions and local commands.
- **Main.lua:** in-game frame, editor, chat event adapters and RPT Lab integration.

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
| GetStatus() | Version, ready state, editor focus, filter, count and capabilities |
| RegisterCommand(name, callback) | Register local colon-command |
| Subscribe(name, callback) / Unsubscribe(name) | Receive copied event data |
| Submit(":command args") | Execute a local command |
| Copy() | Copy filtered history to Windows clipboard |
| Show() / Hide() / FocusEditor() | Own-window UI functions |

Channel labels include **general, party, guild, tell, system, npc, combat, addons, dev**. They are *categories* for records, not assertions that the game server transmitted them.

Limits: 240 saved rows, 512-byte messages, 40-byte sources, 60-byte search, 48 KB clipboard export. Stored data is character-scoped. Corrupted saved histories cause a refusal rather than a silent reset.

## Validation

Run in **PowerShell 7** in this repository:

~~~powershell
& "C:\work\riftreader2\.venv\Scripts\python.exe" -B -m unittest discover -s tests -v
~~~

The tests exercise real Lua 5.1, fake RIFT UI events, focus requests, dragging, Enter input, history, search, copy, NPC/alerts, extension calls, and RPT integration. They do **not** substitute for actual physical RIFT UI acceptance.

## RIFT API findings

The historical documented RIFT addon API provides Event.Chat.Npc, Event.Chat.Notify, Command.Console.Display, Command.CopyToClipboard and addon-specific message transport through Command.Message.Send. Addon messages are not normal player say/guild/tell messages. UI.Native.Console1 is an exposed native console frame, but the verified APIs do not provide its complete social-chat transcript or arbitrary text-send capability.

Reference: https://github-wiki-see.page/m/chrisbecke/Igor/wiki/RIFT-API-Documents

**Next priority:** verify physical window/editor and clipboard, then investigate a separately qualified host adapter for native social-chat input/output. Keep existing native chat intact until the replacement is independently demonstrated.

Built on AMD-DESKTOP for reusable RIFT development tooling.
