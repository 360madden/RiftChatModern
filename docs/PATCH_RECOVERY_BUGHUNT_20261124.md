# RCM — Pre-patch recovery bug hunt

**Session:** November 23–24, 2026 EST · **Machine:** LEGION · **Base:** `38f76911e80d019972250184804d78461d52d0b5`. Scope: recovery-critical host tools, with existing full Lua/Python and Node regression suites. Source addon v0.2.26 and installed v0.2.23 intentionally unchanged. See [patch playbook](PATCH_RECOVERY_20261124.md).

## Reproduced defects and root causes

| Defect | Before (isolated regression) | Correction |
|---|---|---|
| Fresh clone backup fails | Missing ignored artifacts parent caused FileNotFoundError | Create absent output components one by one; reject unsafe existing path components |
| Interrupted manifest publication | Injected write failure left a partial manifest.json | Write pending JSON, flush/fsync, validate readback, atomically publish completion manifest |
| Wrong-machine dry-run | Explicitly mismatched hostname returned success | Enforce supplied host for both dry-run and apply; apply still requires an explicit hostname |
| Stale deployment root | Client-configured override ignored and obsolete conventional Documents addon selected | Use actual Rift.cfg DocumentsDirectory first; do not fall back to stale copy when configured addon is absent; refuse unreadable config |
| Stale deployment preflight | Newer installed bytes overwritten after plan capture | Pin source and destination SHA-256 for all planned files, revalidate plan before mutation, recheck backup/target and staged source before replace, and validate final hashes against plan |

All five new defect-reproduction tests failed before fixes and passed after fixes. All 21 deployment tests passed. These checks are bounded observations, not filesystem locking or atomic multi-file deployment. No external edits should be made during apply.

## Backup integrity requalification

Added read-only `--verify <directory-name> --manifest-sha256 <independently-recorded-hash> --expect-host LEGION` to the existing snapshot tool. It checks the original manifest hash, expected machine, supported schema and phase, counts/byte totals, installed version, and exact inventory of RCM package/save files. It enumerates actual backup paths rather than opening arbitrary paths named in JSON. Tampered bytes, missing files and wrong manifest/host are refused. No restores, no game writes, no disclosure of character paths.

Real verification of the already retained pre-patch artifact succeeded (exit 0): `20261124T044936Z-LEGION-before-ohkcq6qm`, manifest SHA-256 `288f91bdbf47ce966c0e5372adf9a209faa6d18b59aa31d72993c82e6b7770ab`, v0.2.23, 23 addon files, one existing character save, 1,517,017 bytes. The existing artifact was not replaced or edited. The real deployment dry-run also passed, finding the same configured target and nine differences from source; it made no writes.

## Validation boundary

The Node suite passed 144/144 (zero failures/skips), including parser/follower, queue, exact-token disk audit, dependency and sender fixture tests. The complete Python/Lua suite passed 367/367 (59.615 seconds, no skips/failures), for 511 total tests. This includes all 11 snapshot tests and 21 deployment tests; the 7 new tests cover five reproduced defects and two independent verification contracts. Git diff --check passed (line-ending warnings only). Fresh companion health on LEGION passed with all seven dependencies present and no private journals or locks. No real game input, addon deployment, SavedVariables restore, patch installation, or physical post-patch acceptance was performed. Keep the pre-patch installed version unchanged until the new game build is tested, then qualify any addon upgrade separately.

