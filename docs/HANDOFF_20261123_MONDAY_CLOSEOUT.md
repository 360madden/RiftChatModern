# RCM — Monday development handoff and publication checkpoint

**Checkpoint:** Monday, November 23, 2026, approximately 11:39 PM EST (America/New_York)  
**Development host:** LEGION · Workbridge 0.16.4-dev · `C:\work\RiftChatModern`  
**Physical game workstation:** AMD-DESKTOP — connection unavailable during the Monday development cycles; no current game/session qualification.  
**Repository:** [360madden/RiftChatModern](https://github.com/360madden/RiftChatModern), branch `main`.  
**Last development commit before handoff:** `ec800f3675df2eb058e64da801b856570bf8841b`.  
**Remote before publication:** `b4b8b77bf911117cc42370239ef7ffd3edf919ef` (Sunday closeout; confirmed with git ls-remote). Local tree was clean, five commits ahead.  
**Source addon:** v0.2.26 · **Last physically accepted addon:** v0.2.23 (November 21 on AMD-DESKTOP).  
**Public API and character history:** interfaceVersion 2, schemaVersion 2, host import wire protocol unchanged.

> Start with [ROADMAP.md](../ROADMAP.md), the authoritative living plan. This handoff is a historical checkpoint, not a competing roadmap. Monday's software verification is offline; do not claim a live v0.2.26 deployment, public-channel import, or native social-chat replacement.

## 1. Monday work completed

| Commit | Scope | Evidence |
|---|---|---|
| 11405ef | RCM-002: isolated Python environment, pinned dependencies, portable .NET discovery, explicit test prerequisites | [M0 LEGION qualification](M0_LEGION_TOOLCHAIN_20261123.md); 321 Python/Lua + 129 Node passed |
| 2187359 | v0.2.24: persistent validated palette, 15 fixed presentation keys, command/API editing, sparse overrides | [Palette foundation](V0_2_24_CHANNEL_PALETTE_20261123.md); 330 Python/Lua passed |
| da7c77d | v0.2.25: graphical COLORS editor, swatches, RGB preview, category visibility, reset controls, focus and draft preservation | [Graphical palette](V0_2_25_PALETTE_PANEL_20261123.md); 341 Python/Lua + 129 Node passed |
| d08289d | v0.2.26 / RCM-060: mutation-safe subscriber delivery, session diagnostics, strict query arguments, pre-ready capability reporting, complete API reference and optional standalone consumer | [API verification](V0_2_26_API_INTEGRATION_20261123.md); 353 Python/Lua + 129 Node passed |
| ec800f3 | RCM-062: redacted aggregate health CLI, shared bounded journal reader, cross-profile conflict and lock diagnostics | [Companion health contract](COMPANION_HEALTH_20261123.md); 353 Python/Lua + 144 Node passed |

The latest host-only change does not bump the Lua addon version. The optional [RCMIntegrationDemo](../examples/RCMIntegrationDemo/README.md) is independently installable and not included in the normal RCM package. No other repository was modified.

### Implementation details important to the next developer

- **Palette:** fixed 15-category model; `channelColors` holds nondefault uppercase RGB hex overrides; `hiddenChannels` contains only explicit hidden keys. Both are optional character-local fields; history schema stays at 2. Unknown/malformed preference values are repaired independently of good history. Visibility affects displayed history, paging, search and Copy History; API history, IDs, import-token lookup, retained history and save checkpoint remain independent.
- **UI:** COLORS is a third exclusive history-card view alongside ordinary history and the native subscription inspector; closes the message detail reader, keeps unsent editor text, validates input focus, and falls back to commands on insufficient viewport size. A real Lua 5.1 compile test caught the 60-upvalue ceiling; extracting the detail-reader builder fixed the root cause. No new game API or startup module.
- **API:** `GetChannelColors()`, `SetChannelColor()`, `ResetChannelColor()`, `GetChannelVisibility()`, `SetChannelVisible()`, `ResetChannelVisibility()` are additive API v2 methods. See [current API v2 reference](ADDON_API_V2.md). Subscriptions snapshot registration identities, sort by name, skip deleted/replaced registrations, and isolate callback errors. Nested publications retain their rows but do not recursively fan out. Only nil requests history-query defaults; invalid false/control-character inputs fail closed.
- **Health:** `tools/rcm-companion-health.cjs` produces one redacted JSON object, schema RCM_COMPANION_HEALTH_V1, exit codes 0 offline pass, 1 attention, 2 blocked, 64 malformed arguments. It checks seven dependencies, both journals, their locks, shared claim lock, capacity, unfinished capture, and cross-profile conflicts. It does not create files, run subprocesses, launch or focus RIFT, change logging, dispatch input, or authorize recovery. Its observation is not atomic. `tools/rcm-readonly-file.cjs` bounds reads and validates descriptor identity; missing journals are distinguished from malformed/unsafe files.

## 2. Actual evidence and environment

**Final completed development regression, LEGION, November 23:**

| Check | Result |
|---|---|
| Python / Lua 5.1 | 353 passed, zero failures/skips; 41.280 s |
| Node.js | 144 passed, zero failures/skips; 7.722 s |
| Combined | **497 passed, zero failures or skips** |
| .NET editor sender | Last Release build passed with zero warnings/errors during M0; no later sender-source changes |
| Git diff check | Passed; ordinary CRLF warning only |
| Read-only health CLI | offline_checks_passed, expected host matched, seven dependency items found, no local journal/lock files |
| Physical RIFT / addon deployment / exact public disk receipt | **NOT RUN** |

The prior Sunday LEGION failures were superseded by the isolated environment qualification. No Windows Application Control policy was changed. Monday's final regression is a completed source/mock/host-fixture test run, not live-game proof; it was performed at the development checkpoint before this docs-only handoff.

**Toolchain:** Python 3.14.10 with Lupa 2.8 (Lua 5.1) and Pillow 13.0.0 in RCM's ignored `.venv`; Node 24.20.0; .NET SDK 10.0.403. The sibling LuaPadModern decoder was clean at 559a721ba95f23b419af2ca02597f7d2079c8e18, SHA-256 1ed80e2b43073a4d4d70a670a6fafa603616bbb68be842102fdf4ee5d1d7d399. The sibling checkout was ahead of its own remote by 16 commits when checked. Do not assume another machine or a fresh public clone provides that exact dependency. The health command identifies a changed hash; qualify compatibility before relying on a new decoder.

Both default private journals and their queue directory are **absent on LEGION**. This is not proof that AMD-DESKTOP has empty journals or that previously accepted Say data has disappeared. The private AMD queue and RIFT character data were not accessed or changed during Monday's development.

## 3. Resume in the correct order

**Highest overall priority (P0): M1 / RCM-010 through RCM-015 — real public-channel acceptance.** AMD-DESKTOP's connection must first be available. Do not confuse the LEGION code/test environment with a verified live-game workstation.

1. Verify hostname, Git status/remote SHA, active game process/window/executable identity, current RIFT config DocumentsDirectory, active AddOns directory, installed RCM version, actual log path and character SavedVariables. Re-run read-only health locally on the correct host. Never reuse old PID/HWND/start ticks or assume the currently installed source version.
2. Verify existing Say and public journals and shared lock; preserve any unresolved claim. Do not automatically clear, retry, or recreate a journal.
3. If deploying current source, perform the guarded installer dry-run, back up and hash-verify the actual addon directory, and use native `/reloadui`. No full game restart required for a normal addon update. Test startup, version and existing Say history before further live operations.
4. Re-establish actual noncombat logging state; `/log` is a toggle, not an idempotent enable command. Confirm the game is foregroundable. Saturday's public attempt refused before input and sent zero keys.
5. Follow the existing [Saturday public-channel handoff](HANDOFF_20261121_EVENING_PUBLIC.md) and [public coordinator contract](PUBLIC_CHANNEL_DELIVERY_20261121.md) for one bounded capture from EOF of a new, naturally occurring Level 1–29 message. No synthetic public traffic or old-byte replay.
6. Preflight and perform exactly one freshly pinned, explicitly acknowledged dispatch; no prior manual claim, no retry of ambiguous input. Verify a single actual HOST/PUBLIC row. After the normal game save via reloadui, independently match the exact token in current-character SavedVariables; confirm the coordinator's disk_saved state and restore original logging. If proof is missing, record the specific failure rather than declaring success.

**Single next success condition:** one new genuine public source line → one correctly labeled RCM row → one independently verified game-save receipt. The historical Say coordinator pass is preserved; public import remains unverified.

### Independent offline continuation while AMD is blocked

**RCM-063 — backward compatibility and migration testing** is the next practical source task. Use existing fixtures and actual prior release contracts (schema 1 migration, schema 2, v0.2.23 baseline, v0.2.24 colors, v0.2.25 visibility, v0.2.26 API). Test old history/import tokens and checkpoint metadata, absent optional fields, corrupted preferences, no-op revisions, existing local commands, API v2 consumers and host wire compatibility. Assert migration never destroys valid history or manufactures game receipts. Keep any source version changes consistent with manifest and public documentation.

**RCM-064 — operator workflow:** add concise repeatable installation/setup, dependency health, safe deployment and troubleshooting recipes; prioritize reproducibility and remove machine-specific assumptions only with evidence.

**RCM-053/055 — physical UX acceptance:** once current source is installed on the verified game machine, capture real screenshots of COLORS at min/default/large sizes, change/reset a color, hide/show a retained row, verify draft/focus behavior and actual saved settings after reload/relogin. This is still open despite all offline tests passing.

**RCM-061 — physical addon integration:** install the optional demo alongside RCM only if intentionally selected, confirm exactly one startup diagnostic, run a local status/ping and verify the actual row/source. Do not describe mock execution as a game roundtrip.

## 4. Reproducible commands

Run from the verified RCM repo root. Replace the host label with the actual target. No commands below trigger live game input.

~~~powershell
cd C:\work\RiftChatModern
git status -sb
git log -6 --oneline
git ls-remote origin refs/heads/main
node tools/rcm-companion-health.cjs --expect-host LEGION
& .\.venv\Scripts\python.exe -m unittest discover -s tests
node --test tests/test_chat_import.cjs tests/test_chat_observer.cjs tests/test_chat_observer_cli.cjs tests/test_chat_batch_gate.cjs tests/test_live_say_batch.cjs tests/test_live_say_follow.cjs tests/test_live_public_follow.cjs tests/test_say_delivery.cjs tests/test_public_delivery.cjs tests/test_test_python.cjs tests/test_dotnet_host.cjs tests/test_companion_health.cjs
dotnet build tools/RcmEditorSender/RcmEditorSender.csproj -c Release --nologo
~~~

If the virtual environment is absent, follow the documented installation in [CONTRIBUTING.md](../CONTRIBUTING.md) using `requirements-dev.txt`. Do not publish virtual environments, compiled outputs, raw log data, private queue bodies, saved variables or unredacted screenshots. Do not modify sibling reference repos as a side effect.

## 5. Durable project state

The roadmap now marks RCM-002, RCM-060 and RCM-062 as qualified offline; RCM-053 implementation is offline-tested, not physically accepted. Use the [Sunday closeout](HANDOFF_20261122_SUNDAY_CLOSEOUT.md) for historical context, and the latest Monday reports above for current source evidence.

The author of this handoff checked the five outgoing development commits against the actual remote: only scoped source, tests, requirements, example and documentation were present. This handoff and its navigation/contract changes will be committed next and pushed by explicit user request. The final remote SHA will be verified separately and recorded in the conversation. Do not invent that SHA in a pre-commit document.

Retain existing project rules: meaningful commented code, evidence-first root-cause fixes, bounded and repeatable tests, actual machine qualification, no automatic retries of uncertain deliveries, no fabricated game evidence, no unrelated repository edits, and no external/local-model delegation. Workbridge command slots are not ChatGPT subagents.

