# RCM host chat observer — source-only milestone (November 20, 2026)

**Project:** Rift Chat Modern  
**Verified host:** AMD-DESKTOP  
**Canonical project:** `C:\work\RiftChatModern`  
**In-game release unchanged:** v0.2.8 (the new work is Windows-side only)

## Purpose and boundaries

Rift Chat Modern aims to replicate and improve RIFT MMO native player chat while serving as a discovery console for other RIFT addons. The Windows-side proof-of-concept implemented here is *not* a replacement for the game's native chat yet. It provides a structured **candidate social chat stream** from a RIFT `Log.txt` when that file exists and uses a recognized layout. The running RIFT Live client has not yet produced a confirmed `Log.txt` receipt in this development cycle. No claim of live chat integration, chat sending, or automatic Windows-to-addon import is made.

No new RIFT Lua files were changed, so the in-game .toc, current version v0.2.8, and physical addon deployment remain unchanged. The native RIFT chat is preserved.

## Sources and format confidence

- Official RIFT support documents player conversation via native say/channel commands and numbered public channels: https://support.gamigo.com/en/support/solutions/articles/201000105472-rift-using-chat
- Bamux's open-source RiftEventTracker describes `/log` creating `Documents\RIFT\Log.txt`: https://github.com/Bamux/RiftEventTracker
- The **actual** historical RiftEventTracker.py source extracts a sender using `line.split("][")[1].split("]:")[0]`. This provides evidence for bracketed sender fields, but it is not a complete specification of 2026 RIFT Live output: https://github.com/Bamux/RiftEventTracker/blob/master/RiftEventTracker.py
- RCM's earlier v0.2.8 proof sender and `LuaPadModern/tools/rift-log-probe.cjs` identify a matching tagged diagnostic line. Tests demonstrate the existing watcher can decode split UTF-8/UTF-16 and detect markers, not that RIFT Live generated them.

**Unknown:** Whether the modern game produces this file, its exact line format, how long flushing takes, and which channels appear. All parser events explicitly carry `verifiedLiveFormat:false` until independently proven.

## Implemented

`tools/rcm-chat-observer.cjs`:
- Uses the existing **LuaPadModern LogTailProbe** (no copied or independently rewritten file-tail engine). It hooks only the per-instance `readLine` callback, preserving the existing exact marker matcher, read bounds, file creation/truncation handling, partial-line and UTF-16 behavior.
- Recognizes two *historical candidate* shapes: `[Channel][Player]: message`, and `[HH:MM:SS][Channel][Player]: message`. These are test inputs; no live schema assertion.
- Maps recognizable Say/Yell/Emote, Party/Raid, Guild/Officer, Tell/Whisper, and named public channels into RCM-style categories. Ignores system/NPC/combat/loot/crafting categories rather than falsely labeling them player chat.
- Emits newline-delimited JSON to stdout with `source:RIFT_Log.txt`, `event:candidate_chat`, game timestamp when recognizable, channel, sender, message bytes and a `verifiedLiveFormat:false` flag.
- **Default omits message bodies** from stdout. Explicit `--include-text` permits bounded (512 UTF-8 bytes) message text. Never writes or archives log content itself.
- Bounded run: 1–300 seconds, poll 25–1000 ms, at most 200 candidates by default (1–2000 configurable), optional absolute filename `Log.txt` path. Does not send keys, focus RIFT, toggle `/log`, change settings, touch SavedVariables, or install a service.
- Existing logs are opened at EOF to avoid replay; a newly created/truncated/rotated file is followed using the existing watcher. A matching `LPB_PROBE|NONCE|...` diagnostic ends the run with a receipt.

## Operator commands

Open **Windows PowerShell** on AMD-DESKTOP:

```powershell
Set-Location C:\work\RiftChatModern
node .\tools\rcm-chat-observer.cjs --help
node .\tools\rcm-chat-observer.cjs --nonce RCM_CHAT_20261120 --timeout-ms 120000
```

This defaults to metadata-only and exits if its bounded window expires. To see candidate message bodies locally, add `--include-text` intentionally. If RIFT uses a verified nonstandard location, add `--path "C:\exact\RIFT\Log.txt"`. The path must be absolute and must end in `Log.txt`.

**Important:** RIFT `/log` is a toggle. Do not enter it blindly when its state is unknown. First confirm that it is off/on through a reliable in-game indication and verify the resulting file. The external observer *does not enable logging*.

### Coordinating with the v0.2.8 in-game probe

After the watcher prints `started`, in an **already-loaded** RCM v0.2.8 editor enter the *matching* local command:

```text
:logprobe RCM_CHAT_20261120
```

If the watcher later prints `matched` for that exact nonce, it establishes a game-to-file candidate receipt **only with corroborating RIFT origin, path and timing evidence**. The watcher then exits. A diagnostic marker is not a player chat message. To observe ordinary player chat longer, start another bounded observer with a new nonce without submitting a marker, and independently compare actual game messages with the resulting file records.

## Tests run on AMD-DESKTOP

- **13/13 Node.js tests PASS** after fixes, in `tests/test_chat_observer.cjs` and `tests/test_chat_observer_cli.cjs`. Includes pure parsing, categories, Unicode and UTF-8 truncation, UTF-16LE split writes/BOM, file rotation, stale-history avoidance, read-only default redaction, explicit text inclusion, synthetic child-process end-to-end marker matching, and invalid options.
- Existing **87/87 Lua 5.1 addon tests PASS**, proving the new host-only files did not modify RCM runtime.
- The first new Node suite had two failures: a newline after a bracket header was treated as whitespace, and UTF-16LE BOM could hide the first candidate record. Both were fixed and regression-tested before release.
- A bounded read-only check against the current common OneDrive `Documents\RIFT\Log.txt` path returned **timeout, zero candidates, no probe match**, exit code 2 (expected when the file is absent). This does not prove failure of RIFT logging, as `/log` state is unverified. The RIFT process remains running; the separate desktop screenshot operation was blocked by `UI_TURN_BUSY`. It was not bypassed.

Run tests from PowerShell in the RCM repo:

```powershell
node --test .\tests\test_chat_observer.cjs .\tests\test_chat_observer_cli.cjs
& "C:\work\riftreader2\.venv\Scripts\python.exe" -B -m unittest discover -s tests -q
```

## What remains

1. Obtain a **real** RIFT `Log.txt` path and correlate the game's visible chat lines and `:logprobe` with file receipts. If the format differs, amend the parser from exact observed examples, not guesses.
2. Verify actual player-chat channel mapping, sender identity, fidelity and flushing, including party/guild/tells where available. Do not treat a metadata subscription as captured text.
3. Establish a real Windows-to-addon inbound mechanism with end-to-end receipts. This Windows observer currently prints to the host terminal only and does not display its records inside the RCM UI.
4. Independently prove sending normal RIFT chat. `Command.Message.Send` remains addon-data-only.
5. Keep native chat intact until actual reception and send are proven, then build a full compact UX atop those capabilities.

**Deployment note:** There is **no new addon version to hot-copy** for this host milestone. Existing v0.2.8 remains installed with its proper .toc and its previous 9/9 SHA-256 deployment verification.
