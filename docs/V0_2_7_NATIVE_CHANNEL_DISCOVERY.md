# RCM v0.2.7 — Native channel discovery and player-chat research

**Date:** Friday, November 20, 2026, America/New_York  
**Verified machine:** AMD-DESKTOP  
**Source:** `C:\work\RiftChatModern`  
**Verified physical addon directory:** `C:\Users\mrkoo\OneDrive\Documents\RIFT\Interface\AddOns\RiftChatModern`

## Product objective

RCM's long-range target is a modern, independently useful chat window for the RIFT MMO with native-chat behavior and a richer discovery/command surface shared by RR2, RRE and other C:\work projects. The original RIFT chat remains intact until message reception and social send work in a physical session. Native-console **subscription metadata is not a conversation transcript**.

## What we discovered

1. The installed **Gadgets** addon, `wtLibCore/wtLog.lua`, reads `Inspect.Console.List()` then calls `Inspect.Console.Detail(list)`; another Gadgets file, `wtDataTextBar.lua`, calls `Detail(cid)` for individual IDs. Existing `nkTextureViewer` sources also iterate `Detail(list)` and use `consoleData.channel` as a map of public-channel names. These are independent, existing shipped examples; none read ordinary player-chat text from the RIFT Lua API.
2. Historical RIFT addon documentation describes `Inspect.Console.Detail` with a `channel` member containing a **table of public channels** and many other boolean subscription fields. RCM previously treated `channel` as if it were a boolean and only recognized 12 flags, missing `raidWarning`, `combatNeutral`, `lootMoney`, `craftingSelf`, `achievement` and others.
3. Historical `Bamux/RiftEventTracker` describes manually enabling `/log` to create a noncombat `Log.txt` under Documents/RIFT. RCM and LuaPadModern have **not** proven this on the current RIFT Live client. Read-only checks of the OneDrive and normal Documents `RIFT/Log.txt` and `CombatLog.txt` candidates on AMD-DESKTOP found all four files absent on November 20. This does not establish whether logging is enabled or whether a custom path is used.
4. LuaPadModern already has a bounded, source-tested read-only `Log.txt` watcher in `tools/rift-log-probe.cjs` and a .NET 10 `HostCore/NoncombatLogTailer.cs`. RCM should reuse those instead of duplicating the file-tail mechanism. Their exact nonce-matching tests prove synthetic file behavior, **not** genuine in-game message arrival.

Sources: historical RIFT API:  
https://github-wiki-see.page/m/chrisbecke/Igor/wiki/RIFT-API-Documents  
Installed original Gadgets addon: `Gadgets/wtLibCore/wtLog.lua`, `Gadgets/wtDataTextBar.lua` and `nkTextureViewer/Libs/EnKai/map/zone.lua`  
Historical RIFT chat logger: https://github.com/Bamux/RiftEventTracker

## Code changes in v0.2.7

- `NativeChatProbe.lua`: recognizes 27 documented boolean console-subscription fields, avoiding interpretation of `info.channel` as a boolean. Added a bounded, sorted `publicChannels` list, `publicChannelCount`, and `publicChannelsTruncated` for each console with accessible details.
- Public channel maps accept common `name=true` entries and list-style string entries; reject missing, disabled, control-character and oversized names. Scan at most 32 entries and retain at most 16 names per console. Results are **config only** and cannot claim messages were captured.
- `Main.lua`: `:native channels` and `:native copy` show the updated category list and public-channel names, with a clear metadata-only explanation. This can help choose which native subscriptions to investigate without opening or altering the native console.
- RIFT loader contract and standalone addon structure preserved. Manifest, model and startup fallback version synchronized to v0.2.7, public API interfaceVersion remains 1, `RCMDevV1` transport and character SavedVariables schema remain unchanged.

## Validation and limits

- Lua 5.1 regression suite: **83/83 passed** in the pre-version-bump test run; includes two new tests covering console-ID maps, named public channels, all previously omitted categories, invalid names, sorted output, bounds and truncation.
- `tests/test_addon.py` also checks the actual `:native channels` and `:native copy` output with public-channel names, and ensures no social-chat transcript claim.
- This is **offline, mocked API evidence**. No live `/rcm` acceptance, native keyboard acceptance, receipt of normal player say/tell/party/guild chat, or live social send may be inferred from passing tests. No game input was sent during this research.

## Current blockers and next milestones

**P0 — Prove input and output in physical RIFT.** Check the installed .toc and version after client-controlled `/reloadui`, ensure no error window, run `/rcm`, then `:native channels`. Verify whether configured public channels appear as expected. Do not use `:native copy` if clipboard content must be preserved.

**P1 — Demonstrate player-chat reception outside RIFT Lua.** First establish whether `/log` is on and whether `Log.txt` actually appears. If enabled, use LuaPadModern's existing read-only watcher with a correlated test marker and a real player-chat line; verify path, freshness, line format and channel mapping without assuming that `Command.Console.Display` output equals player chat.

**P2 — Build a separately reviewed host-to-addon ingress.** A host reading Log.txt does not by itself make the text available to the Lua addon. No verified automatic file/HTTP socket ingress to Lua exists in the documented RIFT addon API. Before enabling one, prove a real, bounded, reversible mechanism with explicit availability and delivery receipts. A clipboard/manual import could be a low-throughput interim tool but must not be mislabeled live mirroring.

**P3 — Native social send.** Do not confuse `Command.Message.Send` with ordinary player say/guild/tell transmission. Research and validate the input route separately, preserving the native chat fallback until end-to-end proof.

## Deployment and acceptance record

**Actual deployment receipt (November 20, approximately 10:45 AM ET):** Workbridge verified host `AMD-DESKTOP`, canonical source, established physical OneDrive RIFT addon path, manifest Identifier, v0.2.7 Version, Email, SavedVariables and five RunOnStartup modules. It replaced only `Core.lua`, `Main.lua`, `NativeChatProbe.lua`, `RiftAddon.toc`, then SHA-256 checked all **9/9** installed payload files against source, with **zero mismatches**. No character SavedVariables or unrelated addons were touched. The client was not reloaded or physically tested as part of deployment.

Build and deployment verification are separate from live client acceptance. Source files must match the installed addon directory by SHA-256. Preserve existing `SavedVariables` and the user's clipboard. Log path checks and native console metadata probes are read-only; live `/log` and `/reloadui` require deliberate action and should not be silently toggled.

## Useful commands

```powershell
Set-Location C:\work\RiftChatModern
& "C:\work\riftreader2\.venv\Scripts\python.exe" -B -m unittest discover -s tests -v
```

In RIFT native chat, `/rcm` opens the panel. In RCM's own editor, `:native` summarizes console handles; `:native channels` reports subscription metadata; `:native copy` copies the detailed report to the Windows clipboard.
