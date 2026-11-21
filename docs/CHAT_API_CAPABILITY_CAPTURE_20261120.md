# RCM chat capability audit — persisted October 2026 RIFT client API documentation

**Report date:** Friday, November 20, 2026 (America/New_York)
**Verified machine:** AMD-DESKTOP
**Repository:** C:\work\RiftChatModern
**Impact:** Host-side reference research and reusable offline verifier; no RIFT Lua or installed addon changes.

## Objective

Find independent evidence for the exact RIFT MMORPG client addon APIs that might provide ordinary player **Say / Guild / Party / Tell / public-channel** text, rather than assuming the existence of a generic chat event from unrelated games or addon messages.

The already installed local **API Atlas** companion has a persisted, normalized JSON snapshot from a prior live RIFT client. The snapshot is never re-collected or overwritten by this investigation.

## Independent current-era client source

A read-only inspection on AMD-DESKTOP found an existing local normalized API Atlas snapshot with:

- **Capture status:** complete
- **Source kind:** rift-client
- **Captured at:** **2026-10-28T15:15:25Z** (October 28, 2026)
- **Recorded client build:** **Oct 23 2026 11:32:27, RIFT-BUILD-12; internal STABLE-1-1178-A-1256632**
- **Catalog size:** **1,940** uniquely named API entries
- **Source status:** persisted historical client documentation, **not a live November 20 API query**.

This snapshot predates subsequent November game activity and cannot, by itself, prove the precise APIs available in a later client build. The snapshot capture remains private to the user's local API Atlas installation; no full snapshot or unrelated documentation was copied into RCM or published.

## Exact documented functions and events

| Namespace | Names actually present in the captured client |
| --- | --- |
| Event.Chat.* | Event.Chat.Notify; Event.Chat.Npc |
| Inspect.Console.* | Inspect.Console.Detail; Inspect.Console.List |
| Command.Console.* | Command.Console.Display |
| Event.Message.* | Event.Message.Receive |
| Command.Message.* | Command.Message.Accept; Broadcast; Reject; Send |
| UI.Native.Console* | Console1 through Console7; ConsoleSetting |

Neither an Event.Chat.PlayerMessage nor a generic Event.Chat.Guild, .Say, .Tell, .Party, or similar social transcript event was listed among the 1,940 entries. No Inspect.Console.History or Inspect.Console.ReadText method was listed.

**Important distinction:** The recorded Event.Message.Receive documentation explicitly calls it **receipt of an addon message**, even though the transport scope may use terms such as guild, party, say and tell. Its existence does not demonstrate capture of normal player chat. Likewise, Inspect.Console.Detail describes console settings/category flags; it does not document an API to retrieve the console's message history. Command.Console.Display writes an addon line to a console; it is not a transcript reader.

This is **evidence that no general player-chat receiver was documented in that complete captured API catalog**, not a claim that undocumented game-client facilities cannot exist or that the current client has no different APIs. Direct runtime evidence would be necessary to establish those stronger claims.

## Reusable RCM checker

A new stand-alone, read-only host tool **tools/rcm_api_chat_capabilities.py** projects *only API names and capture provenance* from an existing API Atlas JSON snapshot. It does not duplicate Atlas's collection, browsing, importing or exporting services.

Features:

- Uses the current user's existing API Atlas normalized snapshot by default; --snapshot supplies a different persisted JSON capture.
- Requires the source to identify itself as a RIFT-client capture; checks bounded file size, stable metadata during read, catalog structure and duplicate API names.
- Exposes capture status, source build/time, documented chat events, possible future chat-event candidates, console inspection/output methods, addon message APIs, and native console objects.
- **Never prints full source documentation, user chat, unrelated snapshot entries or confidential data.**
- Always labels the result **snapshotOnlyNotLive=true** and **nativePlayerChatReceptionVerified=false**, including if a future candidate Event.Chat.* name appears.
- Optional **--require-complete** exits 2 for an incomplete source capture instead of silently treating it as exhaustive; malformed input is exit 1.

From **Windows PowerShell** in C:\work\RiftChatModern:

    & "C:\work\riftreader2\.venv\Scripts\python.exe" -B tools\rcm_api_chat_capabilities.py --require-complete

The optional --snapshot parameter can point to another existing persisted API Atlas JSON file after a later RIFT update. Re-running with a fresh complete client capture can reveal changes in the documented surface without guessing.

## Verification

- **5/5** Python fixture tests passed, including future candidate-event reporting without claiming live reception, incomplete capture rejection, duplicate API-name rejection, non-RIFT source rejection, read-only exact file verification, and non-disclosure of documentation bodies.
- The tool ran against the actual persisted **1,940-entry** local snapshot with **exit code 0** and found exactly the API names listed above.
- No local RIFT process was running during this check, no game input was issued, no SavedVariables or addon file was modified, and no source snapshot was rewritten.
- Installed RCM **v0.2.16** remains a separate, already SHA-256-verified physical release; this research requires no additional .toc revision or deployment.

## Next source-of-truth decision

**P0 remains proving a real noncombat RIFT Log.txt player-chat record** with the corrected tools/rcm-log-probe.ps1 launcher. Use started.pathSelection from the RCM observer, a deliberately produced live chat sample, and bounded raw-line inspection if needed. Until those bytes exist, keep the host parser's historical formats unverified.

If current RIFT logging cannot provide the required channels, a separate **read-only external client chat source** investigation may be warranted. Reuse existing local RIFT reader and desktop inspection components instead of assuming the addon-only API has capabilities the captured client documentation does not show.

This report deliberately excludes similarly named Minecraft proxy, Discord or unrelated "Rift" APIs; they are **not** RIFT MMORPG addon interfaces.

## External historical cross-checks

- https://www.seebs.net/rift/pts/ — historical RIFT MMORPG addon API index, listing Event.Chat.Npc and Event.Chat.Notify.
- https://support.gamigo.com/en/support/solutions/articles/201000105472-rift-using-chat — official RIFT MMORPG native player-chat guide.
- https://github.com/Bamux/RiftEventTracker — historical RIFT MMORPG noncombat Log.txt reader precedent; this does not prove current live functionality.

No Ollama, OpenCode or Codex CLI was used, and no independent OpenAI subagents were claimed.
