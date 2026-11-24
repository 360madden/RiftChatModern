# RCM companion health — read-only CLI contract V1

**Development checkpoint:** November 23, 2026 (EST) · LEGION · base commit `d08289ddb4b970a5d25e55a520e3695ade8e79bc` · addon source v0.2.26 unchanged.

## Usage

From the repository root in PowerShell:

~~~powershell
node tools/rcm-companion-health.cjs --expect-host LEGION
node tools/rcm-companion-health.cjs --help
~~~

Use the actual expected machine name for a different workstation. An optional absolute `--state-dir` selects the directory containing both named private journals and their locks. An optional absolute `--python` selects the disk-auditor interpreter for the availability check; otherwise the project-local virtual environment is checked.

The command emits one JSON object on stdout, using schema `RCM_COMPANION_HEALTH_V1`. It never starts a subprocess, captures chat, sends input, acquires or removes a lock, creates a journal, edits a save, deploys an addon, or changes game logging. It does not print source paths, player names, message text, encoded batches, tokens, session IDs, session reasons, or lock contents.

| Exit code | Status | Meaning |
|---|---|---|
| 0 | offline_checks_passed | Required files/tools were found and no inspected queue condition requires attention; no live acceptance implied |
| 0 | usage | Help only |
| 1 | attention | Inspect queued/claimed/quarantined transfers, active or unfinished captures, locks, capacity, changed snapshots or a different decoder hash |
| 2 | blocked | Dependency/host mismatch, unsafe or invalid journals/locks, cross-profile token collision or simultaneous claims |
| 64 | invalid_arguments | Unknown, duplicate, incomplete or malformed arguments |

## Report fields

- `expectedHostMatched`: true/false when a host is explicitly supplied; null otherwise. The supplied and actual names are not emitted.
- `dependencies`: static availability of seven items (sibling LuaPadModern decoder, .NET host, Python, editor sender DLL, disk auditor, addon manifest, session preflight). A decoder SHA-256 is compared against the qualified November 23 LEGION baseline. A different hash is an attention condition, not an assertion that the decoder is incompatible.
- `queues`: directory and lock states, independent Say/public journal validation, redacted entry/session counts, capacity, cross-profile collision and simultaneous-claim observations.
- `issues`: fixed severity/code/component values, never arbitrary OS/parser messages.
- Explicit negative flags: `gameSessionVerified`, `installedAddonVerified`, `dispatchAuthorized`, `diskPersistenceVerifiedByThisCheck` are false. This health check is not a sender preflight or physical game test.

An absent journal is distinguished from a valid empty journal. Invalid journals do not receive invented zero counts. The aggregate compares metadata before and after both bounded reads and suppresses cross-profile conclusions when changes are detected. This is a **non-atomic read-only observation**, not a transaction or a substitute for existing claim locks and fresh preflight. The shared bounded file reader verifies file identity/metadata before and after descriptor reads and refuses unsafe leaf paths, changed files and oversized inputs. The journal reader and writer distinguish dangling links from absence.

## Operator response

- Unresolved claim: preserve it. Inspect independent exact-token game-save evidence and reconcile explicitly; never automatically retry.
- Lock present: inspect the actual owner/session before any recovery. Presence alone does not distinguish a valid active lock from a stale lock.
- Capture unfinished: do not resume old bytes; use the established explicit recovery procedure after verifying the capture owner is inactive.
- Invalid/oversized/unsafe journal: stop and preserve the original file for inspection; never auto-reset.
- Decoder changed: review source provenance and run the full regression suite before relying on it.
- Missing runtime: provision the documented environment or specify the correct absolute interpreter. The health command does not install or launch it.

See [toolchain qualification](M0_LEGION_TOOLCHAIN_20261123.md), [public delivery design](PUBLIC_CHANNEL_DELIVERY_20261121.md), [physical preflight](SESSION_PREFLIGHT_AND_RIFT_ERROR_20261120.md), and the [roadmap](../ROADMAP.md).

## Evidence

The real LEGION health check initially returned offline_checks_passed, host match true, all seven dependencies present, matching decoder hash, and both default journals absent. This is a new-machine baseline and **not** evidence about AMD-DESKTOP's queue or game. Fifteen focused Node tests passed, including redaction, cross-profile conflicts, concurrent changes, capacity, dangling links, bounded reads and invalid CLI arguments. The final LEGION health check after all edits reproduced the same clean offline baseline. Full regressions: **353 Python/Lua + 144 Node = 497 passed, zero failures or skips** (41.280s and 7.722s respectively). Git diff check passed. No physical game acceptance or deployment was performed.
