# RCM v0.2.22 — RIFT native console taxonomy and read-only inspector

**Date:** November 21, 2026 · **Host:** AMD-DESKTOP

**Repository:** `C:\work\RiftChatModern` · **Target:** RIFT Live addon Lua 5.1

## Evidence and correction

The user supplied six actual game screenshots, including five panels from
**RIFT's native CONSOLE SETTINGS**. Those panels show an entirely different
classification model than RCM's previous All/Chat/Imports/System/NPC/Addons/Dev
history tabs.

Crucially, RIFT **console categories** and **RCM history source kinds**
are different concepts:

- `Inspect.Console.List()` enumerates game console IDs.
- `Inspect.Console.Detail(id)` returns the configured subscription flags and
  `channel` public-channel table for an individual console.
- These functions **do not return the existing chat history** or prove
  receipt of Say/Guild/Party/Tell text.
- `Event.Chat.Npc` provides NPC speech, and `Event.Chat.Notify` provides
  screen notifications; neither is the ordinary player-chat feed.
- `Event.Message.Receive` and `Command.Message.Send` are
  **addon-data transport**, even if their delivery scope contains
  `say`, `guild`, `party`, `tell` or `channel`.

Sources for the actual RIFT MMO addon API:

- https://www.seebs.net/rift/pts/inspect_console_detail.html
- https://www.seebs.net/rift/pts/inspect_console_list.html
- https://www.seebs.net/rift/pts/event_chat_npc.html
- https://www.seebs.net/rift/pts/event_chat_notify.html
- https://www.seebs.net/rift/pts/command_console_display.html
- https://www.seebs.net/rift/pts/command_message_broadcast.html

These are **RIFT MMO addon documents**, not a similarly named Minecraft
proxy or independent messaging client.

## RIFT console taxonomy

The following groups mirror the user-supplied CONSOLE SETTINGS screens:

| View | Native labels | Inspector keys |
|---|---|---|
| Game Messages | System, Skill, Notoriety, NPC Say, Achievements, Accolades, Experience | `system`, `skill`, `notoriety`, `npc`, `achievement`, `accolade`, `experience` |
| Loot Messages | Item Loot, Money Loot, Group Loot, Purchases, Crafting Self, Crafting Others | `lootItem`, `lootMoney`, `lootGroup`, `purchase`, `craftingSelf`, `craftingOther` |
| Player Messages | Say, Tell, Emote, Yell, Guild, Guild Officer, Party, Raid Warning, Raid, Warfront | `say`, `tell`, `emote`, `yell`, `guild`, `officer`, `party`, `raidWarning`, `raid`; Warfront currently **N/A** |
| Channel Messages | Dynamic public-channel names such as Silverwood, Level 1–29, Events, Level 30–49 | `detail.channel`, names read from the **current game**, never hardcoded as live subscriptions |
| Combat (additional documented flags) | Combat Good, Bad, Neutral, Other, Special | `combatGood`, `combatBad`, `combatNeutral`, `combatOther`, `combatSpecial` |

**Warfront:** The screenshot shows this native checkbox, but the reviewed
`Inspect.Console.Detail` contract has **no documented Warfront boolean**.
RCM renders it `N/A`, never a guessed `OFF`. If later direct
`Inspect.Documentation` evidence supplies a new flag, it can be added.

The native **General** page separately exposes Font Size, Background Color,
Background Opacity, and Show Timestamps. Those screenshots do **not**
establish readable/writable addon API fields for those preferences. RCM
does not claim to retrieve or change them.

## New in RCM v0.2.22

- A new `ConsoleCategories.lua` registry, loaded from `RiftAddon.toc`
  before `Main.lua`.
- A `CONSOLE` tab, **read-only**, that shows Game/Loot/Player/Channels/Combat
  grouped settings from live `Inspect.Console.List/Detail` data.
- `NEXT CONSOLE` cycles actual game console IDs; `REFRESH` explicitly
  resamples the native API. PREV/NEXT pages over longer subscription lists,
  including at RCM's minimum 680×480 size.
- States: `ON`/green = documented flag true; `OFF`/muted = documented flag false **or absent from a successful Detail response**, cross-checked against three unchecked settings in the physical client; `?`/blue = detail unavailable; `N/A`/amber = no documented flag. Disabled **public channel names** are not enumerated
  by RCM because `detail.channel` only supplied confirmed enabled names
  in the supported shape.
- New local commands `:native game`, `:native loot`,
  `:native player`, `:native public`, `:native combat`,
  `:native groups`, `:native view`. The previous `:native channels`
  inventory and `:native copy` remain available.
- The global **CLEAR** button is guarded while viewing read-only native console settings. It cannot erase RCM message history from CONSOLE mode. Lua 5.1 fixture tests validate this without clicking a destructive action against the user's live history.
- The redundant `CHAT` tab was removed: it had displayed the same
  host-imported records as `IMPORTS`, **not** a native social chat feed.
  Legacy `:filter chat` remains a supported Imports alias.
- Existing history tabs now show
  **ALL / IMPORTS / NOTICES / NPC SAY / ADDONS / DEV / CONSOLE**.
- The local history renderer labels RIFT `Event.Chat.Notify` records
  `[NOTIFY]` (instead of implying native console System chat) and
  `Event.Chat.Npc` records `[NPC SAY]`. Local RCM startup notices are
  labeled `[RCM]`. Persisted kinds, the history schema, filtering, and
  source/provenance are unchanged; this is a display-only correction.

**Not changed:** ordinary Say/Tell/Guild/Party reception or transmission
remains **unverified**. The new console inspector does not turn settings
metadata into message content, send player chat, or mutate the native RIFT
checkboxes, colors or window configuration.

## Third-party reference review

- [RiftUI Chat category](https://www.riftui.com/downloads/cat55-Chat.html)
  lists **Backchat, Black Chat, Loggin', Socialize, Stampy, Headlines**.
  Their presence under Chat does not by itself establish a Lua intercept
  for native social transcript text; their historical releases predate the
  current client.
- [CurseForge nkUI](https://www.curseforge.com/rift/addons/nkui), updated
  March 2026, acknowledges limited RIFT addon API control over the native UI.
- [CurseForge API Browser](https://www.curseforge.com/rift/addons/apibrowser)
  supplies a way to read `Inspect.Documentation` in the actual game, which
  is the next authoritative check for undocumented categories.
- [Historical RIFT remote chat library](https://github.com/kevinbrill/rift.net)
  documented guild/officer/whisper chat through an **external service**,
  but there is no current 2026 authentication or endpoint proof for that
  older path. It does not establish a native Lua receiver.

These are useful reference sources but do not justify representing RCM as
a complete replacement for the native social chat stream.

## Testing and physical acceptance

The new Lua 5.1 fixtures confirm:

- Exact native groups and label names;
- `ON`, `OFF`, `?` and `N/A` semantics, including Warfront;
- Dynamic public-channel names, disabled channel omission and bounded text;
- Missing/broken console data fails closed, never treated as `OFF`;
- General console selection, other consoles and refresh;
- The CONSOLE tab's 680×480 paging and layout;
- Returning to history restores the previous rows and saved filter;
- Legacy `:filter chat` continues to select Imports;
- Display-only notification/NPC label corrections preserve existing data.

**Physical acceptance:** v0.2.22 was deployed, `/reloadui` and `/rcm` worked, and native RIFT screenshots confirmed the new history labels and live General console category inspection. The first captured General page showed System/Skill/NPC Say/Achievements/Accolades enabled, with Notoriety and Experience omitted by the API. A second real RIFT screenshot of Loot showed the same pattern for Crafting Others. All three missing values were unchecked in the user-supplied native settings shots. The registry now reports these as OFF only when `Inspect.Console.Detail` successfully returns a console detail; unavailable or failed detail remains unknown. Warfront remains N/A. **Post-fix screenshot confirmation also passed.** Native RIFT images were read and reviewed at 2560×1369:

| Source JPEG | Captured category | Verified current-game state |
|---|---|---|
| `2026-11-21_112950.jpg` | General / Game | 5 ON, 2 OFF: Notoriety and Experience now OFF |
| `2026-11-21_113117.jpg` | General / Loot | 5 ON, 1 OFF: Crafting Others now OFF |
| `2026-11-21_113211.jpg` | General / public channels | 4 ON: `Events@Greybriar`, `Level 1-29@Greybriar`, `Level 30-49@Greybriar`, `Silverwood` |
| `2026-11-21_113451.jpg` | General / Player | 9 ON, Warfront N/A because there is no documented flag |

These physical results agree with the user-supplied native settings screenshots for comparable controls. The original RIFT JPEGs remain local and private. The public README image is a verified **975×810 crop** from the 11:32:11 JPEG showing the actual v0.2.22 inspector, not a mocked rendering. The checked public channels were sampled dynamically from the live game and not hardcoded.

**Final automation:** 312 Python/Lua tests and 58 Node tests passed (370 total). Source deployment was verified against the installed 23-file RCM v0.2.22 package; existing character SavedVariables were untouched by deployment. The physical evidence does **not** establish native player chat text capture or sending.
