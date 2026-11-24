# RCM — Tuesday afternoon deployment guard (2026-11-24)

Base: `d2e280a3e30217516337b4f378aac821508049e0`. Recovery candidate: LEGION. Live access unavailable during this work. No game patch, runtime acceptance, deployment or physical save is claimed.

## Root cause and correction

The automatic deployment path honored an explicit configured DocumentsDirectory, but the CLI's `--target` branch bypassed config discovery entirely. A valid stale addon package could therefore be selected even while the client specified a different directory. The new shared target selector refuses mismatching explicit paths and unreadable configuration, retains manual selection when no override is known, and rechecks target selection after the game-process probe but before any copy. It does not resolve alternative links as equivalent paths. Existing configured-path discovery, version, hash and backup guards remain in force.

## Qualification

Seven isolated Python 3.13 fixture tests of the exact new selector body passed (matching/mismatching configured target, unavailable config, absent override, relative target, unique and ambiguous automatic discovery). These used mocked configuration/discovery, not a full clone. Four integrated regression methods were added to the deployment suite, including dry-run/apply refusal and a simulated config change during the process probe. Existing CLI fixture tests now isolate APPDATA from the actual user's configuration. Full suite, Windows path behavior and live acceptance remain unverified. No CI workflow was present at the base tree; direct network cloning was unavailable in the offline environment.

## Next gate

Run the deployment unit suite and all existing offline tests on LEGION before merging this branch. Follow PATCH_RECOVERY_20261124.md to validate the installed v0.2.23 against the actual game build before upgrading. This is a host-tool change only; the addon version and SavedVariables schema remain unchanged. The selector does not guarantee configuration cannot change after the last check and cannot validate overrides that the existing config parser silently ignores; investigate those separately rather than claiming atomicity.
