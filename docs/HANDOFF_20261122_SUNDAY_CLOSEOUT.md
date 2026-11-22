# RCM — Sunday Development Handoff (Roadmap Closeout / Next Session)

**Checkpoint:** Sunday, November 22, 2026, approximately 08:08 EST (America/New_York)  
**Project:** RiftChatModern (RCM), RIFT Live Lua 5.1 addon and optional Windows host companion  
**Machine actually accessed this session:** **LEGION**, with working `C:\work\RiftChatModern` checkout  
**Physical RIFT test/deployment machine:** **AMD-DESKTOP** — *not reached or requalified in this Sunday session*  
**Git repository:** [360madden/RiftChatModern](https://github.com/360madden/RiftChatModern), branch `main`  
**Checked starting HEAD and `origin/main`:** `8e171ee74d3402e0124b02cf249ed53f6df7576b` (matched remotely, clean worktree before this handoff)  
**Last physically verified in-game addon:** **v0.2.23**, per November 21 AMD-DESKTOP records; unchanged by Sunday's documentation development.

> **Next-session directive:** Start with [`ROADMAP.md`](../ROADMAP.md) — it is the **only authoritative living plan**. This file is a dated execution handoff, **not another competing roadmap**. Do not claim the public-channel import, continuous live social capture, Guild/Party/Tell support or outbound player chat are complete.

## 1. What changed on Sunday

The user asked for a new detailed roadmap that maximizes engineering success and is durable. That task was completed and **pushed to GitHub** in commit `8e171ee`:

| File | Outcome |
|---|---|
| [`ROADMAP.md`](../ROADMAP.md) | Authoritative 10-section development roadmap, distinct Core / Companion / conditional full-chat replacement scopes |
| [`README.md`](../README.md) | Roadmap link added to landing-page navigation and documentation |
| [`docs/README.md`](README.md) | Roadmap indexed for engineering readers |
| [`tests/test_roadmap_contract.py`](../tests/test_roadmap_contract.py) | Five basic checks of roadmap presence, references, unique milestone/task IDs and evidence boundaries |
| [`HANDOFF_20261122_ROADMAP.md`](HANDOFF_20261122_ROADMAP.md) | Original Sunday bootstrap report, including actual LEGION test limitations |

The roadmap covers M0 environment, M1 real public chat import, M2 evidence-first multi-channel taxonomy, M3 durable import/recovery, M4 opt-in continuous companion, UX1 visual usability, API1 addon ecosystem, conditional social-send GO/NO-GO gate and release quality. It has explicit task IDs (`RCM-001` onward), prerequisites, exit criteria, test standards, data boundaries and a current project board.

**This follow-up change:** add this succinct next-session handoff and point the roadmap/docs indexes to it. No functional addon code, manifest, host transport or RIFT game files are intentionally changed.

## 2. Current proven functionality versus pending work

| Capability | Evidence/status | Correct next action |
|---|---|---|
| UI: dark glass style, drag, resize, focus, local editor and saved layout | **VERIFIED-LIVE** in November 21 AMD session (v0.2.21+), current addon v0.2.23 | Preserve; test additional sizes and logout/login later |
| Read-only native CONSOLE taxonomy (Game, Loot, Player, named public channels, Combat) | **VERIFIED-LIVE** in v0.2.22 screenshots | Keep distinct from actual chat transcripts |
| Say import from genuine RIFT `Log.txt` through serialized coordinator and exact game save receipt | **VERIFIED-LIVE + VERIFIED-DISK**, one supervised coordinator run (plus earlier manual proof) | Preserve the settled Say journal, no blind replay |
| Level 1–29 public-channel source grammar, slot 4 | 20 real game-created lines, strict host parser and queues **TESTED-OFFLINE** | **P0:** first *new* public capture → RCM → SavedVariables receipt |
| Guild / Party / Tell and other public slots | **RESEARCH / unsupported as live imports** | Gather exact new game-created source examples; no guessing |
| Unattended continuous chat import and ordinary native social sending | **UNVERIFIED / not established** | Only consider after repeated vertical-slice proof; maintain original chat fallback |

The October 2026 API Atlas capture documents `Event.Chat.Npc` / `Event.Chat.Notify` and read-only `Inspect.Console.Detail`, but **does not document a general Lua ordinary-player-chat transcript API**. RIFT addon-data `Event.Message.Receive` is **not** ordinary social chat. Full replacement is an *evidence-gated stretch goal*, not an existing feature.

## 3. Actual Sunday validation results on LEGION (historical test checkpoint)

Results were recorded during the roadmap authoring run; **not rerun merely for this handoff**.

| Check | Result | Interpretation |
|---|---|---|
| Roadmap contract | **5/5 PASS** | Document links, IDs, scope and maintenance checks passed |
| Node host test group | **117 pass / 2 skip / 0 fail** (119 tests) | Two Python-dependent disk-auditor cases skipped on LEGION |
| `tools/RcmEditorSender` .NET 10 Release | **PASS — 0 warnings, 0 errors** | Build works on LEGION with local .NET 10 SDK |
| Entire Python unittest discover | **NOT GREEN**: 255 discovered; 16 failures, 5 errors, 136 skipped | Incomplete LEGION toolchain; not evidence of new roadmap regression |
| Physical RIFT game, addon installation, `/reloadui` and public import | **NOT RUN** this Sunday | AMD-DESKTOP connection/game not available |

**Identified LEGION blockers:** AMD-only Python venv path is absent; Python 3.14 has no Pillow (`PIL`); Lua 5.1 validation setup is incomplete; `RcmScreenshotKey.dll` execution was blocked by Windows Application Control (`0x800711C7`). Do not silently bypass Windows policy, disable security, fabricate test passes or copy AMD's working runtime destructively. Establish a reproducible LEGION environment first if further testing there is needed.

Last recorded **AMD-DESKTOP** full suite prior to Sunday: **315 Python/Lua and 119 Node passed** (434 total) on November 21, plus clean .NET 10 Release build. That is historical machine-specific proof, **not a current LEGION result**.

## 4. Highest priority: M1 public chat physical acceptance (RCM-010 through RCM-015)

**Exit criterion:** one *fresh real* `[4. Level 1-29][Speaker@Shard]: message` line is captured only after follower readiness, queued once in the public journal, imported once as a correctly labeled `HOST/PUBLIC` RCM Imports row, persisted after a normal `/reloadui` and independently matched to the exact claimed transfer token in actual current-character SavedVariables. Do not disturb historical Say journal state.

**Execution order on the verified AMD-DESKTOP game machine:**

1. Reconnect and inspect the **current** hostname, clean/dirty Git status and origin SHA, RIFT build, process start/PID/HWND/executable SHA, active addon directory, installed RCM version, character save, `Rift.cfg` DocumentsDirectory, `Log.txt` path, and both coordinator queue statuses. **Never reuse old process pins.**
2. Confirm character is in world, RIFT can become exact foreground, native chat works, and RCM editor is visible and focusable. The latest Saturday failure was `refused_before_input` with **zero keystrokes** because RIFT was minimized. That did **not** prove a public import.
3. Determine actual noncombat logging state from the running client. `/log` **toggles**, so never issue it blindly. For a bounded trial, record original state and restore it afterward. Enable only if required.
4. Use the existing public coordinator capture from **EOF** with finite timeout and maximum message count, then observe a **naturally occurring** new Level 1–29 message. Do not synthesize public traffic or import old log bytes.
5. Inspect exactly one eligible queued transfer and perform **read-only .NET preflight**. Confirm in-game RCM editor `INPUT • FOCUSED` using actual game evidence. Use freshly pinned **single dispatch** with the specified acknowledgments. **Do not use `claim` first**, because it reserves the message and blocks dispatch. Never auto-retry ambiguous input.
6. Independently verify one new RCM Imports row with host/public provenance. Return focus to native chat and use `/reloadui` to prompt the normal game's character state save, *not* a full game restart.
7. Use `rcm-public-delivery.cjs verify-disk` against the verified **current character** `RiftChatModern.lua` with an absolute Python interpreter. Match exact transfer token and consistent save checkpoint; then confirm public journal `disk_saved` and persisted RCM row after reload.
8. Restore original logging state and previous desktop foreground. Save a **redacted** dated acceptance or failure document. If any proof is missing, report partial rather than “passed”.

**If AMD remains inaccessible:** no claim that M1 moved forward. Execute **M0/RCM-002** toolchain checks on LEGION or isolated UX1/API1 offline work. Any subsequent real-client test needs a fresh AMD machine/session qualification first.

## 5. Next work after M1

- **M2 / RCM-020–024:** observed-vs-unsupported channel matrix; test another genuine numbered public slot and then exact Guild/Party/Tell source shapes when available. Reject unsupported formats.
- **M3 / RCM-030–035:** canonical versioned provenance envelope; cross-profile global editor lock; queue crash recovery, journal integrity, explicit reconciliation; **no automatic retry** of an in-flight token.
- **M4 / RCM-040–045:** opt-in bounded-to-continuous companion only after channel acceptance; measurable latency, ≥1,000 synthetic stress messages and ≥30 real-message controlled soak, with honest skipped/missed counters.
- **UX1 / RCM-050–056:** dark compact UI, channel color editor, readability, source/history filters vs native console inspector, geometry and actual reload/relogin persistence.
- **API1 / RCM-060–064:** stable `RiftChatModernAPI` integration and example addon; avoid confusing Lua addon data with player chat.
- **GATE B / RCM-070–073:** establish outbound social send/receiver proofs, or explicitly **NO-GO** for “full social replacement” while releasing a useful Core + Companion.
- **REL1:** complete tests, verified deployment and `.toc`, recoverable install, release documentation and truthful feature matrix.

**Project policy:** root-cause fixes and regression tests, source provenance, no fabricated live acceptance, actual RIFT screenshots, local-second timestamps, preserved character data, and verified addon deployment. Existing addon installations can normally take updated Lua with **`/reloadui`**; full client restart is not routine. Never change `C:\work\telarafly` as a side effect of this repository. Do not delegate to Ollama, OpenCode or Codex CLI. Workbridge job slots are not ChatGPT reasoning subagents; only describe real delegation when the capability actually exists.

## 6. Precise resume checklist (PowerShell on the **correct host**)

~~~powershell
cd C:\work\RiftChatModern
git status -sb
git remote -v
git log -5 --oneline
git ls-remote origin refs/heads/main
node tools/rcm-say-delivery.cjs status
node tools/rcm-public-delivery.cjs status
~~~

**Environment-only checks** (run when Python/Lua/Node/.NET are actually configured on this machine; do not assume an AMD venv path exists on LEGION):

~~~powershell
py -3.14 -m unittest discover -s tests -p test_roadmap_contract.py
node --test tests/test_chat_import.cjs tests/test_chat_observer.cjs tests/test_chat_observer_cli.cjs tests/test_chat_batch_gate.cjs tests/test_live_say_batch.cjs tests/test_live_say_follow.cjs tests/test_live_public_follow.cjs tests/test_say_delivery.cjs tests/test_public_delivery.cjs
dotnet build tools/RcmEditorSender/RcmEditorSender.csproj -c Release --nologo
~~~

For **AMD only**, after confirming the known-good Python venv is present, run the entire Python/Lua suite and dry-run `tools/deploy_rcm.py` before a physical test. Compare current game build and `RiftAddon.toc` (including **Email**, Version, startup order, SavedVariables) before any Lua deploy. Guarded deployment must use the **verified** AddOns tree; never assume both machines point to the same OneDrive Documents folder.

## 7. Git publication and handoff provenance

At this document's initial authoring, `main` on LEGION was **clean** and matched remote `8e171ee74d3402e0124b02cf249ed53f6df7576b`. This new handoff and its navigation links are to be committed as the next docs-only change, pushed to `origin/main`, and **separately verified** by comparing local HEAD with `git ls-remote origin refs/heads/main`. The final pushed SHA must be recorded in the assistant's handoff response, not guessed in advance.

**Privacy:** do not put real RIFT `Log.txt`, original chat text/speaker names, Base64URL private journal, character SavedVariables, private screenshots or personally identifying install paths into public commits. Historical redacted artifacts and source-code tests are sufficient.

### Source-of-truth links

- [Canonical development roadmap](../ROADMAP.md)
- [Sunday roadmap authoring and toolchain handoff](HANDOFF_20261122_ROADMAP.md)
- [Saturday evening public-channel evidence and precise acceptance script](HANDOFF_20261121_EVENING_PUBLIC.md)
- [Actual Say-coordinator end-to-end physical proof](COORDINATOR_PHYSICAL_ACCEPTANCE_20261121.md)
- [Strict public-channel pipeline contract](PUBLIC_CHANNEL_DELIVERY_20261121.md)
- [RIFT documented API capability boundary](CHAT_API_CAPABILITY_CAPTURE_20261120.md)

**Single next success condition:** a *real newly generated* Level 1–29 message visible as one authenticated host-public row in RCM **and** independently verified under its exact token after the real game save — with no duplicate import and original logging state restored.
