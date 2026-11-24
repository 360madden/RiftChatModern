# RCM — November 24, 2026 RIFT patch recovery playbook

**Prepared:** November 23, 2026, 11:49 PM EST · **Target:** anticipated November 24 patch (schedule not independently confirmed). **Host:** LEGION. **Owner:** RCM-085 in [ROADMAP.md](../ROADMAP.md). Keep the [Monday closeout](HANDOFF_20261123_MONDAY_CLOSEOUT.md) as historical development evidence.

## 1. Pre-patch evidence

| Boundary | Observed result |
|---|---|
| Git before this recovery work | Clean main, local and remote both `86fd85b637d5bd90ad237aad3aabde4ab4cc8a0a` |
| Game install | Shared Update Helper `before-20261124-legion.json` verified, 266 files, 26,754,214,661 bytes; verification checks the stored manifest, not a new live file scan |
| Game executable baseline | SHA-256 `df954b798331e18359be62a31cc74b49fc3f50b87385ebb080a5448256322c01` |
| Shared manifest SHA-256 | `6612cab5ad31162cc0eab21266ed3839c4a2ef1e12e3a2aa82536d5b195c983e` |
| LEGION session | Exact game process present, companion error handler present, preflight exit 0; configured DocumentsDirectory and existing noncombat Log.txt detected. No window pin or current logging-state proof |
| Installed addon | v0.2.23 on disk; 23 files, existing target discovered and checked against configured DocumentsDirectory; 9 files differ from v0.2.26 source |
| RCM private backup | 23 addon files + 1 RCM character SavedVariables file, 1,517,017 bytes, all copied and re-hashed; non-atomic snapshot |
| RCM backup directory | `artifacts/patch-snapshots/20261124T044936Z-LEGION-before-ohkcq6qm` (ignored and local only) |
| RCM backup manifest SHA-256 | `288f91bdbf47ce966c0e5372adf9a209faa6d18b59aa31d72993c82e6b7770ab` |
| Offline tests | 353 existing Python/Lua + 144 Node passed; 7 new backup-specific tests passed independently; .NET 10 Release build 0 warnings/errors |
| Companion health | Host match, all 7 dependencies available, sibling decoder hash matches, both local journals absent |
| Physical acceptance | Last live+disk v0.2.23 remains historical AMD-DESKTOP evidence. LEGION process/install existence does not prove current RCM startup, chat delivery or game-save acceptance |

No game input, reload, deployment, log toggle or changes to original SavedVariables were performed. Preserve the existing installed version until patch-only testing is complete. The backup represents the current disk save, not unsaved in-memory game state. Do not copy it back automatically.

## 2. P0: after Glyph completes the update

Run in PowerShell on the actual LEGION machine. First verify that the updater is complete, the correct RIFT Live installation is selected, and files have settled. Do not run any dispatch or deployment yet.

~~~powershell
Set-Location -LiteralPath 'C:\work\Update Helper'
python -B update_helper.py verify before-20261124-legion.json
python -B update_helper.py capture --phase after --expected-host LEGION --out after-20261124-legion-a.json
python -B update_helper.py capture --phase after --expected-host LEGION --out after-20261124-legion-b.json
python -B update_helper.py compare --consistency --before after-20261124-legion-a.json --after after-20261124-legion-b.json --out consistency-20261124-legion.json
python -B update_helper.py compare --before before-20261124-legion.json --after after-20261124-legion-b.json --out changes-20261124-legion.json
~~~

Stop on nonzero exit, changed/inconsistent post-update captures, or mismatched root/host; investigate and use fresh output filenames. A successful compare may legitimately report changes. No changes means no *observed file changes* in that capture, not proof of live behavior. RCM consumes this shared evidence and does not maintain a second game file scanner.

~~~powershell
Set-Location -LiteralPath 'C:\work\RiftChatModern'
git status -sb
git rev-parse HEAD
git ls-remote origin refs/heads/main
& .\.venv\Scripts\python.exe -B tools/rcm_patch_snapshot.py --phase after --expect-host LEGION
& .\.venv\Scripts\python.exe -B tools/rcm_session_preflight.py --expect-host LEGION
& .\.venv\Scripts\python.exe -B tools/deploy_rcm.py --expect-host LEGION
node tools/rcm-companion-health.cjs --expect-host LEGION
~~~

The backup helper uses actual Rift.cfg DocumentsDirectory; it copies only the installed RCM folder and exact RCM character save files beneath Interface/Saved, to a fresh ignored artifact directory. Python 3.12+ required (qualified 3.14). It refuses wrong host, links/junctions, excessive inventory, overlapping output, and observable changing files. A partial directory without a successful manifest is not rollback evidence. Keep raw saved data and private paths local; do not commit or publish artifacts. Health exit 1 is attention, 2 blocked; session exit 2 may simply indicate a missing process/log. A deploy dry-run does not establish runtime compatibility; use the actual configured path, not a guessed fallback. If private snapshots differ, compare their relative file identities and hashes locally without publishing account/character names; a save change is not automatically a regression.

## 3. P0: qualify current client before upgrading

The previous AMD machine restriction is replaced by machine-bound qualification: LEGION is the current recovery candidate, AMD remains a historical acceptance host. Freshly enumerate exact PID/HWND, start time and executable identity; do not reuse pre-patch identities. When the game is ready, qualify the *existing v0.2.23* independently:
 
1. Native chat must remain functional. Check addon list, startup, absence of ADDON ERROR, `/rcm show`, version, `:status`, `:echo` with a local marker, drag/resize/editor focus; capture actual screenshots as appropriate.
2. Inspect native Console categories and read-only state. Confirm the expected API availability, including Event.Chat.Npc/Notify, Inspect.Console.List/Detail and addon-message APIs. If a fresh complete API Atlas client snapshot exists, run `tools/rcm_api_chat_capabilities.py --snapshot <actual path> --require-complete` and compare documented names/build to the [historical audit](CHAT_API_CAPABILITY_CAPTURE_20261120.md). Old snapshots are not current-client proof. Do not add guessed chat APIs.
3. Verify current Log.txt path, actual runtime logging state, and a new game-generated source line. The config flag is a hint only; /log is a toggle. Start new bounded capture at EOF and compare raw format privately to existing Say and public slot-4 grammars; do not replay previous log bytes or dispatch on an unverified source. Preserve unresolved claims and locks; use [companion health](COMPANION_HEALTH_20261123.md).
4. Verify prior history and layout, then normal game save via /reloadui and independent disk receipt with the existing auditor where applicable. Never clear saves to fix a regression. Restore original logging state after controlled testing.
5. Requalify one genuine Say import only after correct session pins, source bytes, queue and sender preflight, supervised dispatch and independently matching saved token. Keep public import (M1) as a separate open acceptance gate. Never retry ambiguous input.

## 4. Offline regression and optional v0.2.26 upgrade

Run from RCM root after collecting evidence. Build sender before running test suites to avoid sharing partially built outputs.

~~~powershell
dotnet build tools/RcmEditorSender/RcmEditorSender.csproj -c Release --nologo
& .\.venv\Scripts\python.exe -B -m unittest discover -s tests
node --test tests/test_chat_import.cjs tests/test_chat_observer.cjs tests/test_chat_observer_cli.cjs tests/test_chat_batch_gate.cjs tests/test_live_say_batch.cjs tests/test_live_say_follow.cjs tests/test_live_public_follow.cjs tests/test_say_delivery.cjs tests/test_public_delivery.cjs tests/test_test_python.cjs tests/test_dotnet_host.cjs tests/test_companion_health.cjs
git diff --check
~~~

If installed v0.2.23 is compatible and current source is tested, optionally upgrade v0.2.26 as a *separate* stage: verify target under the configured RIFT root, ensure another verified backup exists, run guarded deployment with explicit host/target, and use native /reloadui. Test palette visibility/color/draft, API v2 demo and schema-2 settings/history. Do not claim physical acceptance without screenshots and independent save evidence. If v0.2.23 fails, isolate the failing API/manifest/parser on that version before upgrading. Avoid speculative version bumps, unrelated refactors or cross-repo modifications.

## 5. Failure routing and exit gates

| Symptom | First investigation |
|---|---|
| Game does not start | Updater/install/host preflight; do not change addon code based solely on error-handler process |
| Addon startup error | Actual installed .toc, Environment, startup order, Lua error and version; preserve the failing package and exact error |
| Window or local commands fail | Core.lua/Main.lua, actual error and fresh screenshot; add minimal reproducer |
| Console categories change | NativeChatProbe.lua / ConsoleCategories.lua; compare actual API results, not assumed labels |
| Chat absent or parser rejects | Confirm actual Log.txt, logging state and new authentic source format; fix targeted parser with positive/negative regression fixtures |
| Sender/queue blocked | Health report, exact window identity, SDK and dependencies, unresolved claim; no automatic replay |
| Saved settings/history missing | Preserve before/after files, inspect schema and save checkpoints using read-only auditor; never overwrite newer user data blindly |

**Rollback:** if a verified upgrade introduces a failure, stop new captures and dispatches, preserve both current and backup artifacts, verify backup manifest/hash and destination host/root, compare package files and restore only intended RCM addon files through a reviewed, explicit operation. Do not automatically restore SavedVariables (would discard newer history/settings), do not roll back the game executable or unrelated addons. Re-test via /reloadui. Keep all before/after receipts in ignored artifacts.

**Exit:** stable shared game comparison, valid RCM after snapshot, all offline suites green, no startup error, current-session native UI/API/log/persistence evidence, and separately labeled tested channel receipts. Mark the recovery as BLOCKED or PARTIAL when any required observation is unavailable. Report timestamp, host, game SHA, source/installed version, exact test counts and evidence links. Resume M1 only once patch-only baseline is qualified. Repeat this process for future patches with fresh date-bound names and verified machine identity.
