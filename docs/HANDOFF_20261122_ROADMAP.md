# RCM — Sunday Roadmap Bootstrap and Validation Handoff

**Date:** Sunday, November 22, 2026 · America/New_York  
**Host actually accessed:** LEGION (Workbridge 0.16.4-dev)  
**Canonical physical game workstation:** AMD-DESKTOP (connection unavailable for this session)  
**Repository:** `C:\work\RiftChatModern` · `main` · `origin=https://github.com/360madden/RiftChatModern.git`  
**Starting SHA:** `29941242778de4026dc32b9a806e88538c6a6ebe`  
**Installed addon version:** v0.2.23 is historical AMD evidence; **no game/deployment verified on LEGION**.

## Purpose

Create an actionable, durable, living product roadmap grounded in the latest *physically verified* RIFT evidence and explicit unsupported capability boundaries. The root [ROADMAP.md](../ROADMAP.md) is now the canonical priorities/acceptance contract; the home README and docs index link to it. Existing Saturday handoffs remain historical proof and were not overwritten.

## Authored changes

- `ROADMAP.md`: new 10-section plan with current baseline, verified-vs-unverified status vocabulary, critical path, per-task IDs, M0–M4 / UX1 / API1 / GATE B / REL1 milestones, measurable gates, source ownership, risk matrix, daily operating loop and roadmap update policy.
- `README.md`: direct roadmap navigation and documentation-index link.
- `docs/README.md`: canonical roadmap link at the top of engineering navigation.
- `tests/test_roadmap_contract.py`: five pure-Python tests for discoverability, internal links, milestone/task IDs, capability boundaries and roadmap maintenance invariants.

All edits above are docs and tests only. No addon Lua, `RiftAddon.toc`, RIFT client installation, game saves or private host journals were modified.

## Actual LEGION checks (2026-11-22)

| Check | Result | Meaning |
|---|---|---|
| Roadmap contract | **5 / 5 PASS** (`py -3.14 -m unittest discover -s tests -p test_roadmap_contract.py`) | Canonical roadmap and source links valid |
| Node host regression | **117 PASS, 2 SKIP, 0 FAIL** / 119 discovered | Two Python-dependent disk-auditor integration tests did not run on LEGION |
| .NET 10 sender Release | **PASS, 0 warnings, 0 errors** | Sender builds with local `dotnet 10.0.403` SDK |
| Python full suite | **FAILED: 255 discovered; 16 failures, 5 errors, 136 skipped** | LEGION is not the fully provisioned AMD workstation; do not interpret as green baseline |
| Physical RIFT import/deploy | **NOT RUN** | AMD connection unavailable; RIFT instance/version/foreground not verified |

### Root cause of LEGION's Python-test limitations (not fixed in this docs-only cycle)

1. The historical AMD virtual-env path `C:\work\riftreader2\.venv\Scripts\python.exe` was not present on LEGION. Tests were run using the installed `py -3.14` launcher.
2. Several Python tests could not import `PIL` (Pillow), making screenshot and public README presentation tests unavailable.
3. Lua 5.1 archive/compiler validation tests returned indeterminate instead of positive/negative qualification; the required Lua syntax validation toolchain is not available in the tested LEGION configuration.
4. `RcmScreenshotKey.dll` was rejected by Windows Application Control (0x800711C7), causing screenshot-trigger test failures. Do **not** disable security settings, bypass policy or reclassify these results as passed. Diagnose the environment and use an authorized supported binary/build route separately if needed.
5. The two skipped Node disk-auditor integration tests require a suitable Python configured for the host tests.

**Do not transfer or delete AMD-DESKTOP's known-good environment in an attempt to match LEGION.** First compare dependency manifests, local SDKs and tool invocation paths. This is a useful M0 bootstrap task, not a blocker to publishing docs.

## Immediate engineering continuation

**P0 (when AMD-DESKTOP is available):** RCM-010 through RCM-015 — first *new* real public Level 1–29/slot 4 source → bounded follower → public journal → one verified HOST/PUBLIC RCM row → `/reloadui` → exact SavedVariables disk token. The prior refused foreground input attempt did not send any keys; never recycle that historical PID/HWND. Preserve Say journal settlement and restore original noncombat logging state.

**Parallel M0 (LEGION):** Choose reproducible project-local Python environment; install only justified dependencies through a documented setup, validate Lua 5.1, inspect .NET application-control issue without changing host policies, rerun the complete test suite, and update a dated verification record.

**Parallel UX1 (optional):** Develop source/channel color-editor design and responsiveness regression checks without implying native social chat reception.

## Durability rule

The **root roadmap is the living source of priorities**. This handoff is an immutable historical snapshot. After every subsequent significant milestone, update the root board/status and add a dated evidence report. Commit scoped changes, push to `origin/main` and confirm the exact remote SHA; a local commit alone is not a remote backup.
