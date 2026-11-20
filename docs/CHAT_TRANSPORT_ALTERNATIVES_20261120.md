# RCM Chat Transport Alternatives — Evidence Review (2026-11-20)

**Project:** Rift Chat Modern
**Canonical workspace:** `C:\work\RiftChatModern`
**Verified local game host:** AMD-DESKTOP
**Research date:** Friday, November 20, 2026
**Status:** Reference research only — no change to v0.2.10 addon, credentials, game files or remote chat services

## Objective

Find a genuinely capable source for ordinary RIFT MMO player chat (say, guild, party, tells and public channels), rather than continuing to treat addon diagnostic messages and native console subscription metadata as if they were the same thing.

RCM's v0.2.10 manual Windows-to-addon import now has robust progress/recovery and passes its test suites, but is not automated native player-chat reception. This document ranks plausible intake strategies based on *evidence*, not guessed API capabilities.

## Findings and confidence

### 1. Live RIFT Log.txt → Windows observer — highest practical near-term candidate

- Historical RIFT community tooling such as `Bamux/RiftEventTracker` reads noncombat `Log.txt`, with bracketed chat-like records that could contain sender information.
- Our `tools/rcm-chat-observer.cjs` reuses LuaPadModern's tested bounded UTF-8/UTF-16 file tailer, with a parser for *candidate historical formats*.
- The exact game-produced `Log.txt` filename/path, enabling `/log`, current channel format, buffering and fidelity are still **unverified in the physical client**. Several common paths on AMD-DESKTOP were missing at the last read-only check.
- Even if the Windows observer works, an *automatic* host-to-Lua ingestion path must be established separately. v0.2.10 has only manual RIFT native `/rcm import` commands, not an automatic input route.

**Next proof:** correlate one real, intentionally observed RIFT player chat line and `:logprobe TOKEN` marker with exact file bytes and an independently observed watcher receipt. Do not equate the console emission with game-to-disk delivery.

References:
- https://github.com/Bamux/RiftEventTracker
- https://github.com/Bamux/RiftEventTracker/blob/master/RiftEventTracker.py
- https://support.gamigo.com/en/support/solutions/articles/201000105472-rift-using-chat

### 2. Native RIFT Lua / Inspect.Console — metadata usable; full player transcript not proven

- The historical RIFT addon API documents `Event.Chat.Npc`, `Event.Chat.Notify`, `Event.Message.Receive` (addon-data messages), `Command.Console.Display`, `Inspect.Console.List` / `Detail` and `UI.Native.Console1` through Console7.
- `Inspect.Console.Detail` can describe which native social and public chat channels are configured; these are **settings/metadata**, not a general player-chat-message event.
- `Command.Message.Send` / `Broadcast` use addon identifiers and accept filters: their type values (say/guild/tell etc.) describe *transport scopes*, not arbitrary ordinary chat transcripts.
- RCM's v0.2.7 native inspector and v0.2.8 log probe already cover these verified capabilities. No conclusive ordinary player say/guild/tell read or send route has been found in the inspected Lua API or installed addons.

**Recommendation:** preserve the existing native chat fallback and keep investigating *actual* surviving RIFT addon sources. A custom RIFT UI that looks like chat does not by itself prove it receives general native chat messages.

Reference:
- https://github-wiki-see.page/m/chrisbecke/Igor/wiki/RIFT-API-Documents

### 3. Historical RIFT Mobile / RIFT REST Chat API — real precedent, not verified for 2026

A legitimate older client existed:
- `kevinbrill/rift.net` is a C# wrapper around Trion Worlds' **RIFT MMO** remote REST/chat API, not a similarly named Minecraft or Discord product. Its source and README document connecting to guild/officer chat and handling whisper events.
- The `rift.net.chat` NuGet release 1.4.0 was last updated on **October 20, 2015**; the parent `rift.net` package 1.9.1 was last updated on **October 21, 2015**. These packages target older .NET Framework technology, not a proven modern RIFT Live server interface.
- Trion's original RIFT Mobile app supported real-time guild/friend chat. It was reportedly removed around the RIFT 3.4 update in **October 2015**. Crucially, subsequent contemporaneous coverage reported that an **API subset was saved for RIFT event trackers**, so it would be incorrect to conclude that every related endpoint immediately stopped operating.
- We have **no 2026 login, chat-listening, endpoint-health or live-service proof** for the old library. Do not ask for account credentials or attempt login based only on archived code. Do not mark it as a functioning solution.

**Decision:** catalog for possible read-only follow-up, but deprioritize versus the already-built local `Log.txt` and native-console experiments.

References:
- https://github.com/kevinbrill/rift.net
- https://www.nuget.org/packages/rift.net.chat
- https://www.nuget.org/packages/rift.net
- https://www.trionworlds.com/en/news/press-releases/2012/01/rift-app-android/
- https://riftgrate.wordpress.com/2015/10/02/livestream-summary-3-4-overview/
- https://riftgrate.wordpress.com/2015/09/25/livestream-summary-3-4-crafting-and-ui/

### 4. Existing modern RIFT addon UIs — valuable visual/reference patterns, not proven chat ingress

`nkUI`, a modern-style suite updated on **March 8, 2026** on CurseForge, explicitly describes RIFT's addon API limitations and the need to configure or hide parts of the original UI. That supports studying its UI structure, but does not by itself establish a general player-message interception API.

Reference:
- https://www.curseforge.com/rift/addons/nkui

### 5. Read-only external client inspection — fallback research track

If `Log.txt` is unavailable or materially incomplete, a host-side read-only look at the client's rendered chat history and/or process memory may reveal a robust candidate source. This is **not implemented in RCM** and would need a separate independent proof, exact-window/process binding, bounded samples, encoding analysis, and full input/output tests. Existing RR2/RRE research utilities can inform a review, but their successes in other areas do not prove chat-reader correctness.

A previous read-only desktop capture attempt against the actual RIFT window returned `UI_TURN_BUSY`. No physical chat capture should be claimed based on that failed tool request.

## Prioritized next actions

1. **P0 — Prove the live output path.** Check RIFT's current logging state and actual `Log.txt` location. Correlate one self-created short chat sample and `:logprobe` with a Windows watcher receipt; preserve the exact record shape, not a guessed regex.
2. **P1 — Prove the v0.2.10 manual inbound path.** Confirm `/rcm import`, chunk progress and cancel in a physically loaded client before any automatic dispatch.
3. **P2 — Adapter architecture.** Only after P0 and P1, create a bounded, typed, explicit import queue with clear delivery/failure receipts. It should never claim native social-chat sending merely because a Windows key injection returns success.
4. **P3 — Inspect modern RIFT addon UI examples.** Borrow durable UI/focus/layout techniques that are permitted by the actual game addon API; retain original standalone architecture.
5. **Fallback — Host-side read-only chat buffer research.** Trigger only if the game log experiment is not viable.

## Evidence labels to retain

- **Mocked or synthetic:** Lua 5.1 and Windows fixture tests; proves code contracts, *not* live game reception.
- **Installed:** SHA-256 matching files in the verified physical RIFT addon directory; proves disk deployment, *not* addon execution.
- **Physical pass:** only an independently observed actual RIFT game event and correlated output/receipt.
- **Historical alternative:** archived RIFT Mobile API and third-party source, not a current operational claim.

This document is a decision aid. It does **not** add a new RCM addon version or change v0.2.10 installed files.
