# RiftChatModern (RCM) — Development Roadmap

> **Living plan · Established Sunday, 2026-11-22 (America/New_York) · Maintained in Git**
>
> **Canonical source:** `ROADMAP.md` at repository root. **Repository:** [360madden/RiftChatModern](https://github.com/360madden/RiftChatModern) · **Development folder:** `C:\work\RiftChatModern` · **Physical RIFT qualification:** AMD-DESKTOP (historical acceptance); LEGION (current patch recovery candidate, fresh physical qualification required). See [November 24 recovery playbook](docs/PATCH_RECOVERY_20261124.md).
>
> **Baseline when this roadmap was written:** Git `main` at `29941242778de4026dc32b9a806e88538c6a6ebe`, in-game addon **v0.2.23**. LEGION has a freshly cloned development copy, **not** a verified RIFT client/deployment. The last *recorded* complete suite (November 21 on AMD-DESKTOP) passed **315 Python/Lua + 119 Node = 434 tests** and a .NET 10 Release build. These results have **not been rerun merely by creating this roadmap**.

> **Current checkpoint — Tuesday, 2026-11-24 (America/New_York):** **387 Python/Lua + 144 Node = 531 Windows tests passed**, zero failures/skips and three clean Release builds at code commit `bd8d40a`; both PR and push CI succeeded. See [PR #1](https://github.com/360madden/RiftChatModern/pull/1) and the [Tuesday handoff](docs/HANDOFF_20261124_TUESDAY_RECOVERY.md). Source **v0.2.26**, last verified installed version **v0.2.23**. **Physical recovery remains blocked:** AMD-DESKTOP is unavailable, and LEGION bridge access returned `Session terminated`. Fresh game patch acceptance is pending.

## 1. Mission, success, and the central feasibility constraint

Build **the most useful modern, legible and reliable RIFT Live chat experience that the actual client permits**, without confusing a diagnostic console, external log companion, and a true replacement for the original social-chat window.

**Deliver two explicit product levels, not one exaggerated claim:**

1. **RCM Core (addon-only):** a polished, responsive, draggable dark-mode console for verified RIFT NPC/notification events, addon messages, native console *settings inspection*, searchable history, local commands and saved layout. Must work without a Windows helper or any player-chat interception.
2. **RCM Companion (optional Windows host):** a bounded, opt-in pipeline for *physically qualified* player-chat lines from the actual RIFT noncombat log, visibly marked as `HOST/...`. Add channels only after game-generated source-format evidence and complete delivery/persistence receipts.
3. **Full social-chat replacement (conditional stretch goal):** requires **repeatable inbound coverage and a proven outbound mechanism** for the required player channels, acceptable latency/reliability, and a way to preserve native chat fallback. **Not promised or scheduled until the feasibility gate passes.**

**Core product success:** a player can install RCM, use and customize the window, persist settings, find/copy history, and receive supported messages without addon errors. **Companion success:** each imported message has source/channel provenance, a stable transfer identity, and a confirmed saved receipt, with no known duplicates or historical replay. **Replacement success:** only after receive *and* send behaviors are physically verified across the agreed social-channel matrix.

### Evidence vocabulary — use these terms consistently

| Status | Meaning | What it does *not* mean |
|---|---|---|
| `VERIFIED-LIVE` | Observed on the physical RIFT client with dated evidence | Other versions, channels or machines also work |
| `VERIFIED-DISK` | Independent exact matching token/metadata in real game SavedVariables after a normal save | Keyboard input alone succeeded |
| `TESTED-OFFLINE` | Deterministic Lua 5.1/Node/Python/.NET test or fixture passed | Real game accepted the feature |
| `RESEARCH` | API documentation, archive, static inspection or candidate finding | Executable capability has been established |
| `BLOCKED` | Specific unmet dependency, reproducible failure or inaccessible game | Work is complete |
| `PLANNED` | Not yet implemented/tested | It is already available |
| `DONE` | Meets that milestone's **explicit** acceptance criteria and linked evidence | All downstream milestones are complete |

A Git commit, a passing unit test, a successful Win32 SendInput call, a visible RCM row, and a saved-game disk receipt are **different evidence layers**. Never promote one to another.

## 2. Reality check: as-of baseline

| Area | Established evidence | Gap / next proof |
|---|---|---|
| In-game Lua addon | v0.2.23; ordered `RiftAddon.toc` with `Email`, character-scoped SavedVariables | Test on future game builds and at more viewport sizes |
| UI | Actual client drag, resize, focus, command Enter, message columns, layout saved through `/reloadui` | Physical min/max, logout/relogin, clipboard and color-editor acceptance |
| RIFT Console | v0.2.22 physical Game/Loot/Player/public-channel subscription settings, read-only | The settings API is **not** a player-chat transcript API |
| Native API | Captured 2026-10-28 API catalog: `Event.Chat.Npc` and `Event.Chat.Notify`, but no documented ordinary player-chat feed | Recheck on new client builds; do not manufacture a Lua event |
| Say | **Two supervised real Say imports**, including follower → serialized coordinator → RCM → exact disk receipt | No unattended, continuous or no-loss guarantee |
| Public chat | 20 real lines of `[4. Level 1-29][Speaker@Shard]: message`; strict public-only parser and companion tests | **First new real public import → RCM → disk** is NOT YET accepted |
| Guild/Party/Tell | Some historical guesses/fixtures | Exact current-client bytes and send/receive evidence still missing |
| Windows companion | Separate Say/public journals; shared exclusive editor claim lock; .NET 10 pinned-window sender; read-only disk audit | Cross-session reliability/automatic operation, latencies, fault recovery |
| Quality | Code commit `bd8d40a`: **531 Windows tests passed**, no failures/skips; three Release builds with zero warnings/errors | Keep future code commits green; offline acceptance does not qualify the physical game |
| Current host / patch | AMD-DESKTOP unavailable; LEGION bridge returned `Session terminated` on November 24 | Fresh host identity, actual patch/build, installed addon, log and save qualification required |

**Do not rewrite history:** Earlier per-version reports may record older intermediate failures or then-pending tasks. Prefer the latest dated acceptance or handoff that supersedes them.

## 3. Critical path and work allocation

~~~text
M0 establish machine + clean Git + test toolchain
  |
  v
RCM-085 qualify actual post-patch client with installed v0.2.23
  |
  v
M1 qualify NEW live Level 1-29 -> public import -> saved receipt
  |
  v
M2 capture/qualify other real chat formats; identify what RIFT emits
  |
  +--> GATE A: choose supported incoming channel set
  |       |
  |       v
  +--> M3 bounded multi-channel delivery and recovery
  |       |
  |       v
  +--> M4 opt-in reliable companion + measured soak testing
  |
  +--> GATE B: evidence for social outgoing channel operations
          |                     |
     PROVEN + tested      NOT PROVEN / unreliable
          |                     |
          v                     v
     RCM replacement      RCM Core + Companion
     prototype             product release

Parallel, independent of player-chat intercept feasibility:
UX1 UI polish & configuration -> API1 addon integration -> REL1 release quality
~~~

**Execution order:** Finish a tiny vertical slice against the real game before generalizing to more chat types or adding autonomous input. Keep at most **one live-game experiment and one independent offline/UX workstream** active at a time. Stop after an ambiguous input/receipt and investigate rather than repeating the send. Document failures, not just successes.

**Priority definitions:** `P0` next correctness/feasibility blocker; `P1` required for a reliable bounded companion or a high-value core feature; `P2` release polish/integration; `P3` conditional exploration. Priorities are *relative*, not fabricated delivery dates.

## 4. Milestones and executable backlog

### M0 — Reproducible development baseline (P0, prerequisite to all implementation)

**Objective:** prove which machine, repo state, tools, and game build are actually in use.

- [ ] **RCM-001 · Host and repo qualification:** Record hostname, verified `C:\work\RiftChatModern` root, remote URL, branch, local HEAD, `origin/main` SHA, untracked/modified files and whether AMD-DESKTOP is reachable. Never conflate LEGION with AMD-DESKTOP. Preserve any pre-existing local changes.
- [x] **RCM-002 · Toolchain (LEGION 2026-11-23; Windows CI 2026-11-24):** Complete current gate passed at `bd8d40a`: Python 3.14.10 with Lua 5.1, Node 24.22.3, .NET SDK 10.0.404, **387 Python/Lua + 144 Node**, all three Release builds clean. See [Tuesday verification](docs/HANDOFF_20261124_TUESDAY_RECOVERY.md). Runner results do not establish current LEGION access or game acceptance.
- [ ] **RCM-003 · Evidence index:** Keep one latest-session evidence matrix (source format → test → real-game screenshot → save token → commit) with links to dated `docs/` reports. Preserve original reports as immutable historical records.
- [ ] **RCM-004 · Client preflight, machine-bound:** Verify exact game PID/HWND/start ticks/EXE SHA and current `Rift.cfg` DocumentsDirectory, active addon location, `Log.txt` path and actual noncombat logging state. Never reuse the historical pins in documents.

**Exit gate:** current machine and Git state are known, full available regression results are recorded without exaggeration, and a reproducible live-game preflight is possible on the freshly verified host. LEGION is the current recovery candidate; inaccessible physical milestones remain `BLOCKED`. After a game update, RCM-085 patch-only qualification precedes M1. **No Lua version bump** is needed for a documentation-only change.

### M1 — First complete public-channel acceptance (P0; most valuable next proof)

**Objective:** one **new, naturally game-generated** Level 1–29 / slot 4 message reaches RCM and its real persisted history, without interfering with previously settled Say transfers.

- [ ] **RCM-010 · Verify physical prerequisites:** On the freshly qualified game host after RCM-085, verify RIFT is running in world, its window can be foregrounded, the accepted installed RCM editor is usable, native chat fallback works, the Say claim is settled and the public journal has no unresolved transfer. LEGION is the recovery candidate; AMD-DESKTOP's historical receipts do not qualify it. Read current status rather than reusing old process pins or journal values.
- [ ] **RCM-011 · Log activation, finite session:** Determine current noncombat logging state from actual client evidence. `/log` is a **toggle**, never a blind enable action. If changed for this test, record and restore original state. Start capture from EOF, not from historic bytes.
- [ ] **RCM-012 · Genuine input source:** Observe one complete, newly appended `[4. Level 1-29]` line while the bounded public follower is active. Do not synthesize public messages or mislabel an old line as new.
- [ ] **RCM-013 · Preflight and single dispatch:** Verify one public queued token, shared lock, exact format/slot, .NET no-input preflight; obtain fresh process/window/executable pins and physically confirm `INPUT • FOCUSED`. Use **one** guarded `dispatch`; **do not `claim` first**, because it reserves the transfer. No retry of partial/ambiguous keyboard input.
- [ ] **RCM-014 · Triple acceptance receipt:** (a) game-created log line, (b) one visible `HOST/PUBLIC` RCM Imports row, (c) after native `/reloadui`, independent exact-token `verify-disk` on the **current character's** SavedVariables and `disk_saved` journal state. Reopen RCM and confirm row remains. Restore foreground and logging.
- [ ] **RCM-015 · Failure reporting:** If the window is minimized/unforegroundable, log startup or capture fails, tokens mismatch, sender refuses, or disk verification fails, retain truthful failure state plus redacted diagnostics. Do **not** force a success marker.

**Acceptance target:** at least **one** unique real public line with full three-layer provenance, zero observed duplicates, one saved receipt, Say history unchanged. Publish a dated sanitized acceptance report. **Until then M1 is BLOCKED/PENDING, even though its offline unit tests pass.**

**Reproduction guidance:** [Saturday evening public handoff](docs/HANDOFF_20261121_EVENING_PUBLIC.md) · [Public coordinator](docs/PUBLIC_CHANNEL_DELIVERY_20261121.md) · [Say physical proof](docs/COORDINATOR_PHYSICAL_ACCEPTANCE_20261121.md).

### M2 — Real source coverage and channel classification (P1; depends on M1)

**Objective:** stop guessing what counts as Say, public, Guild, Party, Tell, Emote, Yell, Officer, Raid, Raid Warning or system/loot.

- [ ] **RCM-020 · Source matrix:** Inventory *native console setting labels* separately from *log message syntaxes* and *RCM history kinds*. Track per channel: game API vs log source, exact bracket grammar, sender, shard, timestamp, encoding, observed client build, verified sample count, and privacy-redacted fixture.
- [ ] **RCM-021 · Other numbered channels:** Gather a genuine, newline-complete record for at least one other currently subscribed numbered public channel. Do not assume the `4` slot, locale or shard mapping stays constant. Extend strict parsing only with evidence and negative/cross-channel tests.
- [ ] **RCM-022 · Private/social types:** Independently qualify game-created Party/Guild/Tell (and Officer/Raid where practical). **Do not** infer these from historical two-/three-bracket guesses, native console checkboxes, addon data or third-party UI claims.
- [ ] **RCM-023 · Timestamp/provenance semantics:** Preserve original game `HH:MM:SS` text as a source field; display RCM's local seconds distinctly. The observed native-chat/log clock discrepancy cannot be “corrected” by assuming UTC offset. Decide how date rollover, shard suffix and missing dates are represented without fabricating time.
- [ ] **RCM-024 · Parser contract:** Fuzz malformed/truncated/multibyte/oversize lines, unsupported channel numbers, rotation, replacements, partial EOF and forged source strings. Strict, bounded parser must quarantine unknowns; output can contain channel + source provenance without leaking full private text in normal status.

**Exit gate (GATE A):** publish an observed vs unsupported **channel coverage matrix**. Each activated category has (i) authentic current-client source evidence, (ii) offline positive/negative tests, and (iii) at least one physically accepted full transfer before it is marketed as supported. Unknowns stay unsupported. If the source omits required types, research a distinct external read-only source; do not claim one exists.

### M3 — Reliable import pipeline, recovery, and auditability (P1; depends on M1 and GATE A)

**Objective:** turn a one-off controlled path into an understandable, bounded, crash-resistant multi-profile companion **without silently re-sending**.

- [ ] **RCM-030 · Canonical message envelope:** Define versioned fields `sourceKind`, `sourceFormat`, `observedChannel`, `channelSlot` (optional), `speaker`, `rawTimestamp`, `content`, `origin=host`, `transferToken`, capture epoch and byte-range/hash evidence; keep Lua history `kind`, origin and claimed channel separate. Migrate with schema tests, not ad hoc renames.
- [ ] **RCM-031 · Queue correctness:** Retain distinct private profile journals and single global editor claim lock. Verify crash-after-lock, parallel Say/public capture, idempotent token matching, stale-lock fail-closed, source rotation/truncation, queue bounds and atomic journal writes.
- [ ] **RCM-032 · Explicit reconciliation:** Add **read-only** command to summarize `queued` / `claimed` / `disk_saved` / `quarantined` / `cancelled` with last known evidence. Ambiguous claimed imports remain claimed pending *independent* disk/in-game inspection; **never blindly replay**.
- [ ] **RCM-033 · Batch discipline and backpressure:** Safe size/part limits for `RCM1-B64URL`, per-message acknowledgments, explicit high-water behavior, full-message-only filtering, dedupe across restarts and source epochs. Measure actual transfer time, not just CLI “sent” duration.
- [ ] **RCM-034 · Version compatibility:** Preserve existing v0.2.23 history/provenance, transfer tokens, SavedVariables and host protocol where possible. Add migration fixtures and rollback guidance before changing schema, token format or editor commands.
- [ ] **RCM-035 · Private data boundaries:** Keep actual `Log.txt`, RIFT character saves, Base64URL journal (not encryption), unredacted screenshots, player/character IDs, private messages and raw capture outside public Git. Redacted reports should still permit reproducible verification.

**Exit gate:** all existing Say/public regressions remain green; tests cover interruption at every transition; no duplicate accepted transfer tokens in deterministic replay/stress trials; a second controlled live acceptance verifies re-entry after restart or `/reloadui`. Publish actual counters, not just “reliable”.

### M4 — Opt-in continuous companion (P1/P2; depends on M3)

**Objective:** a usable, observable Windows companion **if** the log pathway can provide acceptable current messages.

- [ ] **RCM-040 · Run modes:** Explicit start/stop/pause/status, configured finite session initially, exact source path, currently supported channels, capture health and log-file epoch. Never enable `/log` invisibly.
- [ ] **RCM-041 · Controlled delivery:** Gate in-game input behind visibly focused editor, a verified current process/window, a user-enabled session and a global claim. No sending when game is minimized, disconnected, in a modal state, or recipient status is ambiguous.
- [ ] **RCM-042 · Receipt loop:** Distinguish captured, queued, Win32-dispatched, RCM-observed and disk-saved states. SavedVariables may persist only on game saves, so show **awaiting game save** instead of claiming an immediate disk receipt. Safe pause on uncertainty.
- [ ] **RCM-043 · Long-run tests:** Synthetic **≥1,000** mixed messages with forced partial lines, rotation, restarts, malformed payloads and two competing workers; target **0 duplicated accepted tokens**, **0 pre-start replay**, **0 unacknowledged successful-delivery claims**. Report drops/rejections honestly.
- [ ] **RCM-044 · Physical soak:** After two individually proved channel types, supervise ≥30 authentic new messages and ≥3 normal `/reloadui` checkpoints. Record median/P95 capture-to-visible latency, rows captured/accepted/persisted, errors, focus interruptions and unsupported types. A *target* is not a result.
- [ ] **RCM-045 · Companion usability:** One clear operator-facing status/health command; user-visible degraded/offline indication and log-off instruction. Provide a stop path that does not lose already settled import receipts.

**Exit gate:** the companion can be deliberately started, observed, safely stopped and recovered; measurable provenance and honest failure reporting survive restarts. Not necessarily “unattended no-loss chat” if source logging is incomplete.

### UX1 — Modern in-game window and controls (parallel P1/P2; independent of M1)

**Objective:** win on usability **now**, even if the client does not permit full social replacement.

- [ ] **RCM-050 · Visual language:** Preserve compact neutral charcoal/glass theme, readable Lato font, clear hover/active/focus states, restrained accent colors, version in title and colored init message. Review **actual RIFT screenshots**, not just generated mockups.
- [ ] **RCM-051 · Responsive sizes:** Validate 680×480 minimum, default, large, viewport edge clamping, scrollbar/long-message behavior, bottom-right resize grip, title drag/release, off-screen recovery and UI scaling. Physical tests at multiple resolutions; avoid fixed screen-coordinate assumptions.
- [ ] **RCM-052 · Filters vs console inspector:** Separate **message-history filters** (All, Imports, Notices, NPC Say, Addons, Dev) from **read-only RIFT Console settings** (Game, Loot, Player, Channels, Combat). Ensure controls never falsely represent console flags as live messages; unsupported flags display `N/A` or `?` correctly.
- [ ] **RCM-053 · Channel palette and visibility:** Design per-supported-source color swatches/filter toggles, readable defaults, reset control, live preview, SaveVariables schema migration and positive/negative focus tests. Color names must match **observed** channel identities; unknown channels fall back safely. **TESTED-OFFLINE (v0.2.25):** graphical 15-category palette, live draft preview, persisted view-only visibility, reset controls, and focus/geometry regressions implemented. Physical RIFT and character-save acceptance remain open. See [panel contract](docs/V0_2_25_PALETTE_PANEL_20261123.md) and [palette foundation](docs/V0_2_24_CHANNEL_PALETTE_20261123.md).
- [ ] **RCM-054 · Text usability:** Verify local-second timestamps, source/channel/speaker/body column truncation and detail expansion, copy single/filtered message, search pagination, Unicode and long text, editor history, Enter/Tab handling and focus loss. Never turn a local `:` command into social sending.
- [ ] **RCM-055 · Persistence:** Verify configuration/history across `/reloadui` **and** full logout/login, independent read-only disk audit, corrupt SavedVariables recovery and defaults without deleting good user data.
- [ ] **RCM-056 · High-density readability:** Validate at 100%/125% Windows scale where meaningful, contrast on dark game backgrounds, low visual noise and keyboard-only navigation where the RIFT UI API allows it.

**Exit gate:** testable UX checklist with image receipts and no major regression in drag/resize/focus/geometry. Visual work must not be used to claim native chat transport capability.

### API1 — Addon ecosystem and tooling (parallel P2)

**Objective:** RCM remains a reusable local diagnostics hub regardless of social-chat feasibility.

- [x] **RCM-060 · Versioned API:** Inventory `RiftChatModernAPI` `interfaceVersion = 2`, `Publish`, `RegisterCommand`, subscribe/history/UI/copy behavior, argument validation and failure modes. **TESTED-OFFLINE (v0.2.26):** [complete API reference](docs/ADDON_API_V2.md), [optional demo addon](examples/RCMIntegrationDemo/README.md), mutation-safe subscriber dispatch, strict queries and readiness diagnostics. Physical integration remains RCM-061.
- [ ] **RCM-061 · Cross-addon smoke:** Confirm dependency order and a nontrivial live integration from an existing sibling addon (RPT/RR2/Telemetry as available). Verify one published event and one command result physically; keep project repositories isolated.
- [x] **RCM-062 · CLI contracts:** **TESTED-OFFLINE:** [companion health V1](docs/COMPANION_HEALTH_20261123.md) emits redacted JSON, fixed exit codes, dependency availability, bounded journal validation, lock and cross-profile diagnostics. No game input or automatic recovery.
- [ ] **RCM-063 · Backwards compatibility:** Compatibility test for existing published commands/filters, importer framing, history schema and saved UI; changes to wire/API must be versioned and migration-tested.
- [ ] **RCM-064 · Operator documentation:** Practical PowerShell recipes for initial install, verified deployment, `/reloadui`, read-only log inspection, opt-in capture, full stop and troubleshooting.

**Exit gate:** documented contract, automated consumers/tests, and at least one real addon-to-addon roundtrip accepted in-game.

### GATE B — Social sending and replacement feasibility (P3; research, not a promise)

**Question:** Can normal player **Say, public, Guild, Party and Tell** be transmitted by an RCM-owned input workflow reliably and appropriately without a nonexistent Lua API?

- [ ] **RCM-070 · Capability audit:** Recheck the client's current captured `Inspect.Documentation`/API surface after game updates. Keep `Command.Message.Send` / `Event.Message.Receive` *addon-data* separate from native player social messages.
- [ ] **RCM-071 · Candidate design:** Evaluate externally mediated *native chat entry* only in a supervised session after read-only format evidence and safe focus preflight. Distinguish sending a user command to original native chat from an addon-only send API. Test each exact supported channel separately.
- [ ] **RCM-072 · End-to-end outgoing proof:** Each claimed channel requires an actual game-visible outgoing message/recipient observation, explicit input provenance and an independent game receipt. A key-insertion receipt alone is insufficient; do not claim delivery to other players without receiver proof.
- [ ] **RCM-073 · GO/NO-GO review:** Record coverage, latency, user control, UI handoff, focus failures and maintenance cost. If receiving/sending is not credible, **release RCM Core + bounded Companion** with native RIFT social chat retained; do not keep rewriting the product description to imply replacement.

**Decision:** only call something “full chat replacement” if agreed incoming/outgoing channel matrix is physically validated in repeated sessions, with fallback and acceptable user-visible behavior. This gate may correctly end in **NO-GO**, without failing the useful Core product.

### REL1 — Release, regression, deployment and maintenance (P2; after required gates)

- [ ] **RCM-080 · Quality bar:** Clean known test failures and lint/build errors; run Lua 5.1/Python, all Node host tests, .NET 10 Release, README/roadmap links, manifest checks and deployment dry-run. Report actual counts and exact tool versions.
- [ ] **RCM-081 · Verified install:** Confirm correct machine, current active RIFT Documents/OneDrive AddOns directory, `RiftAddon.toc` identity + **Email** + Version + startup order + SavedVariables. Back up existing installed package, hash-verify copy, and use `/reloadui` (no unnecessary game restart). Never overwrite user saves.
- [ ] **RCM-082 · Compatibility matrix:** Test clean install, upgrade from v0.2.23, addon absent/disabled, unexpected SavedVariables data, host disconnected, RIFT minimized, console settings unavailable, and client updates.
- [ ] **RCM-083 · Observability & support:** Redacted bug-report template, failure signatures, supported channel/version matrix, complete known limitations and recovery steps; publish authentic privacy-cropped screenshots.
- [ ] **RCM-084 · Shipping:** Prepare an honest release tier (`Core` or `Core + Companion`), changelog, versioned source tag and distributable addon package. Do not mix host helper binaries into the Lua addon without a documented opt-in path. CurseForge publication and licensing decisions are separate owner approvals.
- [ ] **RCM-085 · Post-update recovery:** On each RIFT patch, reverify API presence, source line grammars, native window/process identity policy, log path and deployment; compare source evidence before changing adapters. Maintain known-good rollback. **BLOCKED 2026-11-24:** [recovery playbook](docs/PATCH_RECOVERY_20261124.md) and historical LEGION before-snapshot exist; current host access and actual patch-only runtime qualification are pending. Preserve installed v0.2.23 until that gate passes. The [Tuesday recovery branch](docs/HANDOFF_20261124_TUESDAY_RECOVERY.md) adds deployment/config guards and Windows CI; offline fixes do not complete physical recovery.

**Exit gate:** a new installation and upgrade pass actual game smoke tests; artifacts match committed code; no unresolved P0 defects; release notes state exactly which social channels are supported and how.

## 5. Evidence-driven release scorecard

These are **goals and pass/fail gates**, not claimed current results.

| Indicator | Definition / target | Proof |
|---|---|---|
| Native-addon startup | No RCM addon error; `/rcm` opens; displayed version matches `.toc` | Real game + screenshot + source hash |
| Editor/geometry | Drag, grip resize, focus, local `:echo` and saved placement all pass | Physical input + `/reloadui` + disk geometry |
| Native console taxonomy | Grouped flags reflect current `Inspect.Console.Detail` settings, including `?` / `N/A` | Native screenshot comparisons |
| Say host import | 1 current-client record + exactly one visible row + exact disk token | Already VERIFIED-LIVE+DISK **once through coordinator** |
| Public host import | ≥1 **new** slot 4 Level 1–29 record + exact row/token | M1 gate **NOT YET PASSED** |
| Additional channels | ≥1 genuine source sample, positive/negative tests and accepted import *per claimed type* | M2 coverage matrix and game receipts |
| Parser/queue | 0 duplicated accepted tokens, 0 pre-start replay in ≥1,000 synthetic events | M3/M4 automated stress run |
| Physical companion soak | ≥30 authentic new events, ≥3 reload checkpoints, measured P50/P95; publish misses/errors | M4 time-series report, not simulated evidence |
| Persistence | UI settings/history survive reload **and** relog; corrupt save handled non-destructively | Actual game save and replay |
| Build quality | 0 known regression failures, full Node/Python-Lua/.NET build reported | Dated command logs and exit codes |
| Replacement label | Inbound+outbound across agreed supported channel matrix with fallback | GATE B decision memo |

## 6. Architecture and decision records

**Prefer the existing implemented parts rather than another parallel framework.**

| Boundary | Source / owning module | Guardrail |
|---|---|---|
| RIFT addon state | `addon/RiftChatModern/Core.lua`, `Main.lua` | Lua 5.1 only; preserve history/schema |
| Addon manifest | `addon/RiftChatModern/RiftAddon.toc` | Required Email/version/dependency order and character SavedVariables |
| Read-only console inspection | `NativeChatProbe.lua`, `ConsoleCategories.lua` | Subscription metadata != social transcript |
| Addon-data transport | `AddonMessages.lua`, `ConsoleMirror.lua` | Addon traffic != ordinary social chat |
| Host ingress | `HostIngress.lua`, `tools/rcm-chat-import.cjs` | Versioned `RCM1-B64URL`; token, strict validation and provenance |
| Source parsing | `tools/rcm-chat-observer.cjs`, `rcm-live-social-follow-core.cjs` | No support without authentic source shape |
| Per-channel host follow | `rcm-live-say-follow.cjs`, `rcm-live-public-follow.cjs` | Bounded new-only, no historical replay |
| Queue / lock | `rcm-delivery-coordinator-core.cjs`, `rcm-say-delivery-state.cjs` | Different profile journals, one editor lock, no blind retry |
| Explicit host dispatch | `tools/RcmEditorSender` (.NET 10) | Pinned live process/window, real focus, no auto retry |
| Saved receipt | `tools/rcm_disk_receipt.py` | Independent read-only exact on-disk proof |
| Deployment | `tools/deploy_rcm.py` | Verified host/path, dry-run, backup, hash check, `/reloadui` |

**Decision record format:** `docs/DECISION_YYYYMMDD_<topic>.md` includes problem, options considered, source evidence, decision, rejected alternatives, rollback implications, tests and owner/date. First decision required at GATE A; second at GATE B. Do not retroactively alter old acceptance reports.

**Anti-bandaid rule:** Diagnose source/format/API/focus/persistence failure first; fix at the owning boundary; add a regression that fails before the fix and passes afterward; resist duplicate parsing paths and unverified channel aliases.

## 7. Risks and triggers

| Risk | Likelihood / impact | Early signal | Response |
|---|---|---|---|
| No native Lua player-chat event | Evidence already limits available catalog; **high product impact** | Only console settings/NPC/notify events available | Gate full-replacement claims; maximize Core + Companion |
| RIFT `/log` off or toggled incorrectly | Operational dependency / medium-high | Log unchanged despite new native text | Inspect client state; finite capture; restore original value |
| Minimized/unfocusable game | Observed blocker / high for host dispatch | `refused_before_input`, zero input | Keep failed receipt, inspect window, retry only after fresh preflight |
| Wrong profile/classification | High trust impact | Mislabelled channel/slot or false transcript | Strict source evidence, isolate unknowns, test negative cases |
| Duplicate import after ambiguous sender | High data integrity impact | Claimed token but no independent saved receipt | Fail closed, inspect game/save; never auto-resend |
| Private messages in host files | High exposure if published | Encoded journal or raw logs in changed files | Ignore private paths, review diff before commit/push |
| Game patch breaks parser/window | Medium-high | Build/API/log grammar changes | Requalify source and client identity on patch; retain prior version |
| LEGION vs AMD confusion | High deployment risk | Historical AMD acceptance mistaken for current LEGION qualification | Verify hostname, active game and installed version per session; never cross-deploy by assumption |
| Overexpansion before vertical proof | High schedule risk | Many unverified adapters/UI panels at once | WIP limit, M1 acceptance first, evidence-driven promotion |
| Locked-to-foreground import UX | High usability risk | Game cannot receive input in normal play | Treat host helper as opt-in companion, investigate alternatives before always-on claim |

## 8. Repeatable workflow for every development session

1. **Establish identity:** date/time zone, machine hostname, exact repo root, `git status -sb`, local HEAD, remote HEAD, existing changes, last dated handoff and latest outstanding claimed host tokens. Stop if uncertain about the target machine.
2. **Choose next unblocked item:** select one P0 and at most one independent offline/UX item; record item IDs, current evidence and acceptance test **before** coding.
3. **Research at source:** first the genuine current client/API/screenshot/log; distinguish real data from synthetic fixtures. Use existing local reference tools as **read-only evidence** when useful.
4. **Implement small reversible change:** choose actual owner module, guard all inputs, preserve schema and source provenance. Do not modify installed client, game saves or unrelated repos merely to improve tests.
5. **Test in layers:** static/fixture tests → full existing suites → .NET build if relevant → deploy dry-run → physical RIFT test only when on the verified machine → exact saved-state audit. Record skipped levels honestly.
6. **Check output and privacy:** review diff, verify README/roadmap links and test logs, redact screenshots/reports and ensure no live logs/saves/private journals were staged.
7. **Promote status only with proof:** update this file's status matrix and dated `docs/` record with SHA/build/host and pass/fail counts. A source change alone never sets `VERIFIED-LIVE`.
8. **Commit and publish:** commit scoped files, push approved branch, verify remote SHA and clean worktree. A local commit alone is not a GitHub backup. If remote fails, report local-only status.
9. **Handoff:** write a short dated `docs/HANDOFF_YYYYMMDD_*.md` with what changed, files/hashes, tests, current blocker and the **single next P0**. Keep historical reports.

**Example local test commands (PowerShell in verified repo root; use the machine's actually installed tools):**

~~~powershell
cd C:\work\RiftChatModern
git status -sb
git log -3 --oneline
& .\.venv\Scripts\python.exe -B tools/rcm_offline_ci.py
& .\.venv\Scripts\python.exe -B tools/deploy_rcm.py --expect-host LEGION
~~~

Use the [Windows qualification setup](docs/OFFLINE_CI.md), including the sibling decoder and actual tool versions. `LEGION` above is the current recovery candidate; substitute only the freshly verified host. The `deploy_rcm.py` invocation is **dry-run by default** and refuses a hostname mismatch. Do not `--apply` until exact host, installed folder and backup are checked and the patch-only baseline has passed.

## 9. Current project board and next move

| Work item / milestone | Status on 2026-11-24 | Owner environment | Next action |
|---|---|---|---|
| Core v0.2.23 UI and Say coordinator | `VERIFIED-LIVE` / `VERIFIED-DISK` (as recorded Nov 21) | AMD-DESKTOP | Preserve working baseline |
| M0 Git checkout and toolchain | `TESTED-OFFLINE`: **531 Windows tests passed**, all three builds clean at `bd8d40a` | GitHub Windows Server 2025 runner | Preserve passing gate for subsequent code changes; verify actual game host separately |
| RCM-085 patch recovery | `BLOCKED` for physical acceptance; deployment/config/rollback fixes and Windows CI qualified offline | LEGION candidate; bridge returned `Session terminated` | Restore access, verify actual updater/build state and qualify installed v0.2.23 before deployment |
| M1 Level 1–29 import | `TESTED-OFFLINE` only; live pending after RCM-085 | Freshly verified game host | After patch-only baseline, complete exact new source → RCM → disk proof |
| M2 additional social formats | `RESEARCH` | Qualified live host | Obtain current real log examples after M1 |
| M3 queue/recovery extension | `PLANNED` (foundations implemented) | Any dev host with tests | Start after M1 |
| M4 continuous companion | `PLANNED` | Qualified live host | Start after M3 |
| UX1 improvements | `TESTED-OFFLINE` v0.2.25 graphical palette and visibility implemented; physical acceptance pending | Development host; freshly qualified game host for acceptance | After staged addon upgrade, verify color/visibility and reload/relogin persistence |
| API1 integration | `TESTED-OFFLINE` RCM-060 API/consumer + RCM-062 redacted companion health | Development host; freshly qualified game host for acceptance | RCM-061 physical roundtrip; independent RCM-063 compatibility and RCM-064 operator workflow |
| GATE B full replacement | `RESEARCH`, no GO decision | Physical current client required | After incoming coverage/source feasibility |
| REL1 release | `PLANNED` | Verified game host | After required gates |

**Immediate P0:** **RCM-085 → RCM-010 → RCM-015** on the freshly verified game host. Establish the actual patch/build and existing installed-v0.2.23 baseline first. Only then capture one *new authentic* Level 1–29 message, prove one RCM-host row and one saved transfer token, and restore the original logging state. The Windows offline gate has passed. AMD-DESKTOP is unavailable and current LEGION access failed; continue evidence-backed offline work without marking the physical gate complete.

**Tuesday recovery checkpoint:** [PR #1](https://github.com/360madden/RiftChatModern/pull/1) contains explicit deployment-target, malformed-config/stale-log and rollback guards plus the native-slash backend correction and Windows qualification runner. At **`bd8d40a1ee4ed71b4b676b01e085e1db77ccc8cd`**, [PR CI](https://github.com/360madden/RiftChatModern/actions/runs/45496085182) and [push CI](https://github.com/360madden/RiftChatModern/actions/runs/45496076722) both completed successfully: **387 Python/Lua + 144 Node = 531 passed**, no failures/skips/todo, and three Release builds with zero warnings/errors. Five rollback regressions and the six original native-slash failures were reproduced before their fixes. The [Tuesday handoff](docs/HANDOFF_20261124_TUESDAY_RECOVERY.md) preserves the initial YAML failure, first Windows failures, corrective work and exact toolchain. No live deployment or patch acceptance occurred.

**Sunday LEGION-only validation checkpoint:** The new roadmap contract passed 5/5; Node host tests returned 117 passed / 2 skipped; the .NET 10 sender Release build passed. The broader Python suite did **not** pass on LEGION (missing Pillow and Lua 5.1 prerequisites plus a Windows application-control-blocked screenshot helper). Details: [Sunday roadmap bootstrap handoff](docs/HANDOFF_20261122_ROADMAP.md). Do not replace the historical AMD 434-pass result with a false current all-green claim.

**Monday LEGION-only checkpoint:** RCM's isolated Python environment and .NET host discovery now work. 321 Python/Lua and 129 Node tests passed with zero skips/failures; .NET Release build clean. See [M0 toolchain qualification](docs/M0_LEGION_TOOLCHAIN_20261123.md). Physical M1 acceptance remains blocked.

**Historical Monday closeout:** source v0.2.26, graphical palette/visibility and API improvements implemented, aggregate companion health added. That checkpoint's full LEGION regression was 353 Python/Lua + 144 Node = **497 passed**, zero failures/skips. See the [Monday development handoff](docs/HANDOFF_20261123_MONDAY_CLOSEOUT.md). The later [pre-patch bug hunt](docs/PATCH_RECOVERY_BUGHUNT_20261124.md) established the historical main baseline of **367 Python/Lua + 144 Node = 511 passed**. RCM-063 compatibility and migration testing remains independent offline work; physical recovery takes priority before M1.

## 10. Roadmap maintenance policy (durability contract)

- **This root file is authoritative for forward priorities and current milestone state.** `README.md` links here; `docs/` contains the detailed historical evidence and acceptance records. Do not make a second conflicting “current roadmap”.
- **Update on every meaningful milestone, blocker, dependency change or product capability claim**, not only when a feature is visually impressive. Adjust the `Current project board` and checklist; append a dated decision or acceptance report when proof changes.
- **Never erase negative or superseded evidence.** Link to newer proof; do not silently rewrite old documents or claim old tests were rerun.
- **Status is timestamped and machine-specific.** List test counts, client/build, repo SHA and actual physical host. “Offline passed” is never “live passed”.
- **Durability = local Git commit + verified remote push.** The GitHub copy is the recovery source for future ChatGPT sessions/machines. A new machine must clone/pull before editing; never assume AMD/LEGION are automatically synchronized.
- **Protect user data and working repos:** preserve unrelated changes, maintain original RIFT native chat fallback, require active-folder verification before deployment, and never edit saved character state to manufacture receipts.
- **Review cadence:** after each completed P0 gate, after any RIFT client update, and at the start of each substantial development session. Reprioritize if source evidence disproves a dependency; reject features that do not help the Core or companion success criteria.

### Reference index

- [Latest development handoff](docs/HANDOFF_20261124_TUESDAY_RECOVERY.md)
- [Windows offline qualification](docs/OFFLINE_CI.md)
- [Patch recovery playbook](docs/PATCH_RECOVERY_20261124.md)
- [Historical Monday closeout](docs/HANDOFF_20261123_MONDAY_CLOSEOUT.md)
- [Monday LEGION toolchain qualification](docs/M0_LEGION_TOOLCHAIN_20261123.md)
- [Latest Sunday development handoff](docs/HANDOFF_20261122_SUNDAY_CLOSEOUT.md)
- [Sunday roadmap bootstrap and LEGION validation](docs/HANDOFF_20261122_ROADMAP.md)
- [Latest Saturday evening handoff](docs/HANDOFF_20261121_EVENING_PUBLIC.md)
- [Real Say coordinator proof](docs/COORDINATOR_PHYSICAL_ACCEPTANCE_20261121.md)
- [Public-channel pipeline](docs/PUBLIC_CHANNEL_DELIVERY_20261121.md)
- [Observed Level 1–29 log syntax](docs/LIVE_PUBLIC_CHANNEL_LOG_FORMAT_20261121.md)
- [Current native console taxonomy](docs/V0_2_22_NATIVE_RIFT_CONSOLE_CATEGORIES_20261121.md)
- [Persisted current-era API audit](docs/CHAT_API_CAPABILITY_CAPTURE_20261120.md)
- [Verified UI drag/resize/focus/persistence](docs/V0_2_21_UI_INTERACTION_ACCEPTANCE_20261121.md)
- [Release homepage and capability limits](README.md)
