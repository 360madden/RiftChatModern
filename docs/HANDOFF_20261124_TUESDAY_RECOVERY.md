# RCM — Tuesday recovery handoff

**Date:** November 24, 2026 (America/New_York / EST). **Work:** recovery branch `recovery/20261124-target-guard`, [PR #1](https://github.com/360madden/RiftChatModern/pull/1), based on main `d2e280a3e30217516337b4f378aac821508049e0`. Source addon **v0.2.26**; last verified installed addon **v0.2.23**. This report supersedes current-status links; [Monday's closeout](HANDOFF_20261123_MONDAY_CLOSEOUT.md) and all earlier dated evidence remain unchanged.

**Verified Windows result:** **387 Python/Lua + 144 Node = 531 passed**, zero failures/skips/todo, and all three Release builds completed with zero warnings/errors at code commit **[`bd8d40a1ee4ed71b4b676b01e085e1db77ccc8cd`](https://github.com/360madden/RiftChatModern/commit/bd8d40a1ee4ed71b4b676b01e085e1db77ccc8cd)**. Both [PR run 45496085182](https://github.com/360madden/RiftChatModern/actions/runs/45496085182) and [push run 45496076722](https://github.com/360madden/RiftChatModern/actions/runs/45496076722) completed **SUCCESS**. Physical patch recovery remains **blocked**; no deployment or game acceptance occurred.

The Windows Server 2025 runner used **CPython 3.14.10, Node 24.22.3 and .NET SDK 10.0.404**. The inspected [job log](https://github.com/360madden/RiftChatModern/actions/runs/45496085182/job/138806834438) records 387 Python/Lua tests in 38.561 seconds and the complete 144-pass Node summary. These results bind to the code commit above; later changes require their own successful gate.

## Current evidence and blockers

| Boundary | Observation | Meaning |
|---|---|---|
| Current complete Windows gate | **531 passed** at `bd8d40a`; both PR and push runs succeeded; three builds clean | Current offline qualification, including rollback and native-slash regressions |
| Historical main baseline | LEGION: **367 Python/Lua + 144 Node = 511 passed**, no failures/skips; see [pre-patch bug hunt](PATCH_RECOVERY_BUGHUNT_20261124.md) | Recorded result for earlier source, not a rerun of this branch |
| Current recovery review | Actual Git checkout available in Linux; Python 3.12, Node 24 | Suitable for scoped portable regressions; Windows integration still requires Windows |
| Scoped guard tests | Initially **25 deployment + 22 session preflight = 47 passed**; after five new rollback regressions, **30 deployment + 22 session preflight = 52 passed** on Linux Python 3.12 | Actual repository tests; these counts do not include CI-summary tests or claim Windows qualification |
| Native-slash correction | **16/16 tests passed** on Linux Python 3.12, including three new regressions; 12 separate pure event-construction comparisons matched original types and bytes | With the 52 guard tests, **68 focused repository tests passed** before the complete successful Windows rerun |
| First Actions attempt | [Run 45493512689](https://github.com/360madden/RiftChatModern/actions/runs/45493512689), at `03c3bfa`, failed YAML validation at line 41 with no jobs | No test execution occurred in that attempt |
| First repaired Windows attempt | [Run 45494659151](https://github.com/360madden/RiftChatModern/actions/runs/45494659151), at `523e1b3`: all three Release builds passed; **379 Python/Lua methods, six failures, zero errors/skips**; **144/144 Node passed** | Historical failed gate; the hidden backend dependency was corrected and the complete rerun passed at `bd8d40a` |
| AMD-DESKTOP | Unavailable | Historical Say/UI/disk receipts do not establish current access or runtime state |
| LEGION | Current recovery candidate; `workspace_info` returned **`Session terminated`** during this session | No current game process, patch state, active addon path or runtime behavior was verified here |
| Physical patch / addon acceptance | **NOT RUN** | No game input, deployment, `/reloadui`, logging toggle or SavedVariables restore performed by this recovery work |

The earlier broad Linux run was not qualifying: 379 Python methods produced 28 failures, two errors and 39 skips, with the failures/errors involving the unbuilt Windows screenshot helper. Node reported 135 passes, five failures and four skips, involving Windows path expectations and missing sender output. These results are retained as environment evidence; they were not promoted to a pass. The later complete Windows run supplies the qualification result.

## Changes and root causes

- **Deployment target selection:** an explicit `--target` previously bypassed the client's configured DocumentsDirectory. The shared selector now rejects mismatches and unreadable configuration, and rechecks selection after the process probe before copying. See the [original target-guard report](PATCH_RECOVERY_TARGET_GUARD_20261124.md).
- **Configuration and log selection:** malformed, duplicate, relative or unresolved DocumentsDirectory values must fail closed. Strict bounded config reads now report failures, and a stale fallback log cannot qualify a different configured root. See the [original config-guard report](PATCH_RECOVERY_CONFIG_GUARD_20261124.md).
- **Complete Windows qualification:** the runner builds `RcmEditorInput`, `RcmEditorSender` and `RcmScreenshotKey`, then runs the actual Python/Lua and Node suites with no skipped/todo acceptance. It supplies the interpreter and .NET host explicitly. The minimum gate is now **387 Python/Lua and 144 Node tests**, matching the completed passing run. See [offline CI](OFFLINE_CI.md).
- **First workflow correction:** `--only-binary=:all: -r` required a YAML block scalar. Fresh-clone tests also need the sibling LuaPadModern decoder; the workflow now checks out the two repositories side by side and uses Node 24, matching the documented Windows toolchain family.

No addon Lua, version, SavedVariables schema or production decoder health baseline was changed by these guards and CI setup.

### Deployment rollback correction

Five regressions failed against the old deployment rollback and passed after the fix. The old error path could overwrite a newer edit, delete a newly deployed file after someone changed it, restore corrupted backup bytes, stop before recovering independent files, or truncate an installed file during an interrupted direct restore.

The corrected path verifies that the current destination still matches the bytes this deployment wrote and checks retained backup hashes. It stages and verifies each restoration before an atomic replacement. Changed destinations are preserved, corrupt backups are refused, and a per-file failure does not prevent independent recoveries. If rollback remains incomplete, the error retains the original deployment failure, each recovery error and the retained-backup directory for inspection. A fully successful rollback preserves the original exception.

**Verification:** all **30 deployment tests passed**, including the five fail-before/pass-after cases; all **22 session-preflight tests passed**. These are bounded checks around individual file operations, not filesystem locking or a transaction across the whole addon package. They do not authorize automatic restoration of character SavedVariables.

### Windows native-slash fixture failure

The six Python failures in the first repaired Windows run exposed event construction that imported a private RPT module even when the caller supplied an injected backend. The same six failures were reproduced without that private module. The implemented correction constructs each inert event through the supplied backend's `_key` factory, preserving the backend's Windows input ABI. It prepares the bounded event pairs before acquiring focus, so a construction failure refuses before focus or input.

All **16 native-slash tests passed locally**, including three new regressions, and then passed in the complete Windows gate. Separately, **12 pure construction checks** against the existing private backend matched the original event types and raw bytes; no private source was copied into this repository. Public CI is self-contained apart from the explicit public pinned LuaPadModern decoder. Tests use inert construction and fixture backends; no real game input occurred.

## Companion dependency provenance

The GitHub runner uses public LuaPadModern commit **`9c65386489f8d1e4c8d81b9ed01c6c22b98e4ecc`**, restricted to `tools/rift-log-probe.cjs`. That file's Git blob is `f2b1f6c5565e52c429b23a73d6ae97681e3e2fa2`; the SHA-256 of the **Git blob/source bytes** is `b039109e209b739ec586f725c20b09d381782eb8da1eff49c43ec0a6be916c2e`. This is not a measured Windows working-tree hash; checkout line endings can differ.

The historical LEGION dependency was commit `559a721ba95f23b419af2ca02597f7d2079c8e18`, 16 commits ahead of its remote, with decoder SHA-256 `1ed80e2b43073a4d4d70a670a6fafa603616bbb68be842102fdf4ee5d1d7d399`. GitHub could not resolve that commit. The public pinned decoder is different and is now **offline-qualified against the complete current Windows suites**. It is not newly live-qualified, and the production companion-health baseline remains unchanged.

## Resume order

1. **RCM-085: establish the physical patch-only baseline.** Once LEGION access returns, verify hostname/repo status and the actual updater/build state, validate retained backups, capture fresh game/window identity, and follow the [patch recovery playbook](PATCH_RECOVERY_20261124.md). Test the existing installed v0.2.23 before a separate v0.2.26 upgrade. Actual patch installation has not been independently established by this session.
2. **RCM-010 → RCM-015: complete M1 after patch qualification.** Confirm native chat fallback, current log/runtime logging state, clean or independently reconciled queues, and focused editor. Observe one newly generated Level 1–29 / slot 4 line from EOF, perform one guarded dispatch, then prove the visible `HOST/PUBLIC` row and exact saved transfer token after a normal save. Preserve ambiguous claims and never blindly resend.
3. **Independent offline work:** RCM-063 compatibility/migration tests and RCM-064 operator instructions remain useful while physical access is blocked. They cannot substitute for RCM-085 or M1 acceptance. Future code changes must pass the complete current Windows gate before promotion.

**Single next success condition:** obtain a fresh, dated **physical patch-only baseline** on the verified game host with installed v0.2.23. The recovery code's complete Windows gate has passed. The physical baseline must establish the current game build, addon startup/UI, actual log path/source and save behavior. M1's first genuine public import is the following distinct success condition.

No historical PID/HWND, executable hash, logging flag or saved receipt authorizes new input. Current priorities remain in [ROADMAP.md](../ROADMAP.md).
