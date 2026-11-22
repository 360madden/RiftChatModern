# RCM — Saturday Evening Handoff: Public-Channel Pipeline

**Checkpoint:** November 21, 2026, 8:55 PM EST
**Project:** RiftChatModern (RCM), RIFT Live Lua addon plus optional Windows host tools
**Verified machine:** AMD-DESKTOP, Workbridge 0.16.5-dev
**Canonical repository:** `C:\work\RiftChatModern`
**Branch/remote:** `main` → `https://github.com/360madden/RiftChatModern.git`
**Baseline at handoff creation:** `dcb379c6c28a66585b0cd233649ddf44397c0776`
**In-game Lua addon:** **v0.2.23**, installed package unchanged (23 source files hash-verified)

> **Start here:** The new **public Level 1–29 / slot 4** host capture and delivery pipeline has passed offline testing, including cross-profile locking against the already physically proven Say pipeline. **Actual public-chat → RCM editor → saved token acceptance is still pending.** Do not label the public path physically accepted or claim continuous unattended/native Lua social chat reception.

## 1. Project purpose and UI requirements

RiftChatModern is a modern compact dark-mode chat-style UI and developer hub for RIFT Live. Requirements: legible local timestamps to seconds, separate source/channel/sender/body columns, readable fonts, draggable and resizable window with bottom-right grip and offscreen clamping, reliable focus indicator and text input, message search/details/copy, customizable filter/channel colors, persistence via character SavedVariables, local colon commands and a CLI/API usable by other addons. Always show the addon version in the window and colored initialization message. Current in-game build is v0.2.23.

Current history tabs are **ALL / IMPORTS / NOTICES / NPC SAY / ADDONS / DEV / CONSOLE**. Removed redundant CHAT tab because it falsely suggested native player-chat interception; `:filter chat` remains an Imports alias. The CONSOLE view reads actual RIFT subscription settings. It **does not** expose raw social-chat message bodies. Maintain strict HOST provenance on imported chat. Direct social sending, Guild, Party and Tell remain unverified.

## 2. Most recent verified milestones

| Commit | Meaning | Verification |
|---|---|---|
| `5a95d0e` | v0.2.23 real Say → file → manual editor → saved import | Physical RIFT and exact disk-token proof |
| `f899a73` | Bounded new-only Say follower | Unit tests and physical log smoke; later end-to-end qualified |
| `eee37e0` | Serialized Say coordinator | Offline integration, explicit pinned input and disk auditor |
| `407bcbe` | Previous Saturday handoff | Pushed |
| `5061db9` | One **real Say** through coordinator accepted; 20 real numbered public-channel log lines; strict new parser | RIFT physical screenshot and exact disk proof for Say; real log evidence for public format |
| `dcb379c` | Separate public follower, separate private coordinator and journal, shared source-integrity core, shared editor claim lock | **Offline tests only** for public; Say regressions still green |

**Critical proven Say facts:** On AMD-DESKTOP the running RIFT client generated an exact new Say line in its `Log.txt`. Bounded capture, one serialized queued transfer, .NET 10 no-input preflight, single pinned Windows dispatch, separate screenshot confirming exactly one new `[HOST/SAY]` RCM Imports row, and `/reloadui` followed by independent on-disk token receipt all passed. The coordinator journal ended with **disk_saved=1, queued=0, claimed=0**. Logging was restored to **disabled**, with an actual native-chat screenshot confirming that message.

The same real log contained **20** numbered public-channel lines, all from slot 4 / Level 1–29, with the redacted format:

    HH:MM:SS: [4. Level 1-29][Speaker@Shard]: message

This establishes *that observed public syntax*, not Guild/Tell/Party syntax, not other public slots, and not independent game provenance for arbitrary synthetic lines.

## 3. Current architecture and ownership

### Lua addon — v0.2.23 unchanged

`addon/RiftChatModern/` contains `RiftAddon.toc`, `Core.lua`, `Main.lua`, `HostIngress.lua`, `ConsoleCategories.lua`, `NativeChatProbe.lua`, `AddonMessages.lua`, `ConsoleMirror.lua`, fonts and textures. The `.toc` requires correct **Email**, Version, identifier, dependency/run order and character SavedVariables. Use `/reloadui` for addon updates after deployment to the **verified active** OneDrive Documents/RIFT AddOns path; no full game restart needed.

### Windows host source

- `tools/rcm-chat-observer.cjs`: recognizes real current-client Say format and real timestamped numbered public-channel syntax; historical guesses for other social types remain unverified.
- `tools/rcm-live-social-follow-core.cjs`: shared bounded `LogTailProbe` processing; new-only EOF, rolling source integrity checks, no replay, no truncated-content import, redacted output by default. Depends on `C:\work\LuaPadModern\tools\rift-log-probe.cjs`.
- `tools/rcm-live-say-follow.cjs`: explicit **Say** profile only.
- `tools/rcm-live-public-follow.cjs`: explicit **public Level 1–29 / slot 4** profile only; other slots and Say messages ignored.
- `tools/rcm-delivery-coordinator-core.cjs`: shared CLI implementation for capture/status/preflight/claim/dispatch/verify-disk/cancel/recover. Does not send game keys during capture.
- `tools/rcm-say-delivery-state.cjs`: profile-specific private state journal and wire validation. Default export preserves Say behavior and schema; public profile is independent.
- `tools/rcm-say-delivery.cjs`: stable original Say-only CLI.
- `tools/rcm-public-delivery.cjs`: separate public-channel CLI. Uses distinct private schema/file.
- `tools/rcm-chat-import.cjs`: canonical bounded `RCM1-B64URL` editor encoder. Say wire prefix `S`, public `C`.
- `tools/RcmEditorSender`: .NET 10 pinned-window editor command sender, no input in preflight. Actual dispatch requires exact live host/PID/HWND/process start ticks/EXE path/SHA and four explicit acknowledgments; a Win32 receipt is not an addon receipt.
- `tools/rcm_disk_receipt.py`: independent read-only exact-token and game-save-checkpoint audit.

### Two separate journals; one global editor

The ignored private state directory is `artifacts/rcm-private-queue/`. The Say journal is `rcm-say-delivery.json`, schema `RCM_SAY_DELIVERY_V1`; public is `rcm-public-delivery.json`, schema `RCM_PUBLIC_DELIVERY_V1`.

These files contain **Base64URL-encoded, NOT encrypted**, messages. Do not publish their bytes, names, original screenshots, original game log or character SavedVariables. Status only prints aggregate redacted metadata.

The global import editor is shared across profiles, so `claim` and `dispatch` take `rcm-global-editor-claim.lock` in their common state directory. They check the *other* journal for a claimed transfer and reject cross-profile duplicate tokens. This prevents Say/public interleaved command batches. A held lock or unresolved claimed transfer blocks closed. Never remove a lock while a process might own it.

Transitions: queued → claimed → independently verified disk_saved, or explicit cancelled. There is **no** claimed → queued auto-retry. A failed/ambiguous capture quarantines queued records. A sender reported keyboard insertion does not establish RCM acceptance or persistence.

## 4. Testing completed

The latest verified **full regression suite** at commit `dcb379c`:

| Suite | Outcome |
|---|---|
| Node.js | **119 / 119 passed** |
| Python/Lua | **315 / 315 passed** |
| Total | **434 passed, 0 failed** |
| .NET 10 RcmEditorSender Release build | **0 warnings, 0 errors** |
| Installed addon deploy dry-run | **23 source files match, no copied files, no SavedVariables changes, no game input** |
| Read-only public follower against real old log | EOF 5246, 9 polls, 0 new messages, no historical replay |
| Existing real Say journal read | revision 6, `disk_saved=1`, nothing pending |
| New public journal read at this handoff | revision 0, empty queue and sessions |

PowerShell testing commands on AMD-DESKTOP:

    cd C:\work\RiftChatModern
    node --test tests/test_chat_import.cjs tests/test_chat_observer.cjs tests/test_chat_observer_cli.cjs tests/test_chat_batch_gate.cjs tests/test_live_say_batch.cjs tests/test_live_say_follow.cjs tests/test_live_public_follow.cjs tests/test_say_delivery.cjs tests/test_public_delivery.cjs
    & "C:\work\riftreader2\.venv\Scripts\python.exe" -m unittest discover -s tests
    dotnet build .\tools\RcmEditorSender\RcmEditorSender.csproj -c Release --nologo
    & "C:\work\riftreader2\.venv\Scripts\python.exe" tools/deploy_rcm.py
    node tools/rcm-say-delivery.cjs status
    node tools/rcm-public-delivery.cjs status

## 5. Current live-game blocker

During the most recent attempt to start supervised passive Level 1–29 capture, the RIFT process was observed as PID 32504, HWND 0x60590 (historical **only**, do not reuse these target pins). Logging was at the prior **disabled** state and the RIFT `Log.txt` still measured **5246 bytes**. The pinned `/log` action returned `refused_before_input` with **zero key events** and `gameInputSent=false` because Windows could not obtain the exact game foreground. A subsequent window inspection showed RIFT **minimized**. No retry was performed; file metadata remained unchanged. This does **not** qualify the public pipeline as live accepted.

Only physical game/window evidence can clear that blocker. No control of the user's current foreground should be inferred from historical results.

## 6. Next optimal actions

**P0 — First physical public-channel import acceptance**

1. Inspect **current** host, Git status, branch, both queue statuses and live RIFT PID/HWND/exe SHA/process start. Read actual `Rift.cfg` DocumentsDirectory and current `Log.txt` state. Never reuse historic PID/HWND/ticks.
2. Confirm the game is in-world, foregroundable, and the RCM v0.2.23 window is available. Do not blindly toggle `/log` (it is a toggle). If needed, enable for the finite experiment and later restore its original state.
3. Run a short explicit public capture only after the log is confirmed active:

       node tools/rcm-public-delivery.cjs capture --path "C:\path\to\RIFT\Log.txt" --timeout-ms 60000 --poll-ms 100 --max-messages 1

   Allow a **naturally occurring** public Level 1–29 message; do not post a synthetic public test message. Capture must occur after EOF baseline, not from history.
4. Verify one queued public transfer, complete public **preflight** with the .NET sender (zero game input), then physically confirm RCM editor **INPUT • FOCUSED** using a live screenshot.
5. Use a **single** pinned `dispatch` with fully fresh target identity and explicit acknowledgments. Do **not** run `claim` immediately before `dispatch`: that would intentionally reserve/block the transfer. Keep Say and public state files in the same private directory for cross-profile lock enforcement.
6. Independently view one new `[HOST/PUBLIC]` / public-channel-host row in the actual RCM Imports view. If key insertion was ambiguous, **do not retry**.
7. Defocus RCM editor, issue native `/reloadui`, and verify the **exact** matching claimed token with `node tools/rcm-public-delivery.cjs verify-disk --file <current character RiftChatModern.lua> --python <absolute python.exe>`. Require consistent checkpoint. Then read queue state for `disk_saved=1`.
8. Independently verify persisted row in RCM after reload; restore original noncombat logging state and return previous foreground. Write a dated acceptance/failure report with source-file hash and redacted screenshot metadata.

**P1 — Broader public chat:** extend beyond slot 4 only after obtaining actual client-created lines for additional channel indices/names; no guess-based mapping.

**P2 — Other player social channels:** Guild/Party/Tell require independent actual game bytes. Native Lua social interception/sending remains unsupported by verified evidence.

**P3 — Unattended delivery:** only after repeated supervised proofs, add explicit opt-in, per-message receipts, backpressure and recovery without duplicates or silent replay. This is a larger milestone, not implied by the current tools.

## 7. Workflow and restrictions

- Prioritize root causes; avoid bandaids and unsupported claims. Use real screenshot evidence and exact saved-token proof for live acceptance.
- No Ollama, OpenCode or Codex CLI delegation. Internal ChatGPT subagents are the user's preference, but **this chat's exposed tools did not include actual ChatGPT reasoning-subagent spawning**. Workbridge's job assignments and parallel independent test jobs are **not AI subagents**; do not misrepresent them.
- The repo is on AMD-DESKTOP; verify machine before touching RIFT. Local folder aliases for LEGION are not interchangeable.
- Any actual Lua changes require correctly ordered `.toc`, including **Email**, Version, deployment to the active AddOns directory, and `/reloadui`. Host-only modifications do not require addon deployment or version bump.
- No edits to actual character SavedVariables to fake disk receipts. No full game restart when `/reloadui` suffices.
- Never publish private log lines, encoded journal data, unredacted screenshots or player-identifying file paths.
- Earlier technical records remain important: [Say coordinator physical proof](COORDINATOR_PHYSICAL_ACCEPTANCE_20261121.md), [public log syntax](LIVE_PUBLIC_CHANNEL_LOG_FORMAT_20261121.md), [public delivery design](PUBLIC_CHANNEL_DELIVERY_20261121.md), [prior Saturday handoff](HANDOFF_20261121_SATURDAY.md), and the [engineering archive](ENGINEERING_ARCHIVE_README_THROUGH_20261121.md).

## 8. Git and publication

At authoring time the worktree was clean and synchronized to `dcb379c`. This new handoff will be committed on top of it and pushed to `origin/main`. Treat only **post-push** local HEAD vs `git ls-remote origin refs/heads/main` as proof of successful publication.

**Resume command (PowerShell):**

    cd C:\work\RiftChatModern
    git status -sb
    git log -5 --oneline
    node tools/rcm-public-delivery.cjs status
    node tools/rcm-say-delivery.cjs status

**Immediate next success criterion:** one NEW game-generated Level 1–29 message → public-only follower → public journal → exactly one import into the real RCM editor → normal RIFT save → independent exact-token disk verification, without disturbing the settled Say history or leaving logging enabled.
