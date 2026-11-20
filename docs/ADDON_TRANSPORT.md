# RiftChatModern v0.2.0 — addon messaging and native-console probe

**Scope:** RIFT MMO client-side addons. Tested under Lua 5.1 mocks on AMD-DESKTOP on November 20, 2026. Live RIFT acceptance is pending.

## Sources and semantics

The installed RIFT API documentation and the existing MessageViewer addon (read-only source references) confirm:

- Command.Message.Accept("send", "RCMDevV1") registers only this addon-data identifier.
- Command.Message.Send(target, identifier, data, callback) sends reliable **addon data** to a game player. The callback confirms/refuses server queuing, **not peer delivery**. Nearby/guild/party/raid/previous-contact restrictions apply.
- Event.Message.Receive(from, type, channel, identifier, data) reports addon data from a peer. This callback does **not** include an initial lifecycle-event handle.
- UI.Native.Console1 through Console7 are documented native frames. Their existence, visibility and GetKeyFocus result are **not** evidence of a readable social-chat transcript.
- Event.Chat.Npc and Event.Chat.Notify expose NPC speech and screen notifications, not general player say/tell/guild/party messages.

References: installed RIFT_API_Docs/LLM_RIFT_API/Message, installed MessageViewer/Main.lua (not modified), https://www.seebs.net/rift/pts/command_message_send.html and https://www.seebs.net/rift/pts/

## New calls and commands

| API or command | What it does |
| --- | --- |
| RiftChatModernAPI.SendAddon(target, message) | Sends up to 240 bytes with identifier RCMDevV1. Returns API-submitted status, never peer-delivery proof |
| RiftChatModernAPI.GetAddonTransportStatus() | Copy of ready/pending/submitted/accepted/rejected/unknown/received/invalid counters |
| RiftChatModernAPI.GetNativeConsoles() | Read-only inventory of up to seven native console handles and boolean getter results |
| RiftChatModernAPI.Publish("addons", text, source) | Publishes a **local** same-client entry, without remote sending |
| :addon TARGET MESSAGE | Requests RIFT addon-data transmission, not ordinary player chat |
| :native | Reports native-console handle presence and visibility/focus getter observations |

The sender allows one outstanding request, a two-second interval, a 15-second callback deadline, and **no automatic retries**. Missing receipts or uncertain API calls are recorded as unknown. Incoming messages are **inert data** displayed in the Addons tab; received text like ":rpt arm" never executes a local command.

The version remains a compact, draggable dark UI with Lato, explicit editor/search focus detection, filters, timestamps, search, 240-entry saved history and clipboard export.

## Offline validation

From PowerShell in C:\work\RiftChatModern:

~~~powershell
& "C:\work\riftreader2\.venv\Scripts\python.exe" -B -m unittest discover -s tests -v
~~~

The 32-test v0.2.0 suite covers Send callback success/refusal/timeout, cross-shard-style target strings, receipt counters, queue guards, source validation, read-only native probing, UI/focus, SavedVariables, history, clipboard and RPT integration.

**Physical acceptance is separate:** load v0.2.0 into RIFT, verify /rcm, focus, drag and clipboard, then perform one bounded addon-data send to a known second client whose addon accepts RCMDevV1. A callback from Send does not establish that the other client received anything.

## Player chat remains a separate milestone

The verified addon API does not currently expose a general say/party/guild/tell transcript reader or ordinary player-chat send function. Command.Message.Send is **addon messaging**, even though its allowed transport types have chat-like names.

For actual player-chat reception **outside** the addon, a read-only RIFT Log.txt watcher is a candidate when the user has enabled /log. The existing LuaPadModern repository already has tested log watcher implementations, so avoid building an unnecessary duplicate. The physical file path, flushing, and external-to-addon ingestion still require verification. No game encrypted datastream inspection or modification is necessary for this research.

Reference addon MessageViewer and LuaPadModern were not modified or linked.
