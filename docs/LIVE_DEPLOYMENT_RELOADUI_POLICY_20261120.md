# RCM — Live addon deployment using /reloadui

**Date:** Friday, November 20, 2026, 11:24 PM EST (America/New_York)
**Machine:** AMD-DESKTOP
**Repository:** C:\work\RiftChatModern
**Source and installed:** v0.2.18

## Root cause

The original RCM deployment script categorically rejected any running rift_x64.exe process, incorrectly insisting that RIFT close before addon files could be updated. For an existing RIFT addon, this is unnecessary: update the installed Lua and RiftAddon.toc files, then issue /reloadui in the running game's native chat to load the new UI and addon code.

This unnecessary script restriction repeatedly deferred tested development. The user explicitly corrected the assumption, so this is the new standard RCM iteration policy.

## Corrected workflow

1. Verify the actual AMD-DESKTOP host and the exact physical RIFT addon directory.
2. Run tests and tools/deploy_rcm.py dry-run, checking the toc identifier, Email field, Environment 4.3, module startup order and character SavedVariables contract.
3. Use tools/deploy_rcm.py --apply --expect-host AMD-DESKTOP while RIFT is open or closed. It queries live process IDs to report state, but DOES NOT block simply because RIFT is running.
4. Back up changed originals under the ignored artifacts/deploy-backups directory. The installer verifies backups, stages and atomically replaces files, then checks SHA-256 source-to-install equality. Rollback remains available for copy failures.
5. When files changed and RIFT was running, the installer reports reloadUiRequired=true, reloadUiCommand=/reloadui, runtimeReloadVerified=false. If no file changed, no UI reload is required. Unknown process-query failure still blocks apply.
6. Issue exactly one /reloadui in the ORIGINAL RIFT native chat input to activate the updated addon. This is a UI reload, not a full game restart or Windows reboot.
7. Verify the RCM startup/version 0.2.18 and addon-error state through an independently captured in-game screenshot or other live evidence. Do not confuse installed files with a loaded runtime.
8. Inspect character SavedVariables read-only after the game saves. Never write into the live SavedVariables file from the installer.

## Red and green evidence

Two existing installer test expectations were updated from a false running-game refusal to the correct hot-deployment behavior. The old installer failed the first test as expected. After the root correction, the installer fixtures passed for running-game apply, a running-game no-op requiring no reload, closed-game apply, unknown/unparseable process query refusal, rollback and idempotent SHA-256 verification. The source full suite also passed 230 Python/Lua and 47 Node.js tests before deployment, with a clean git diff whitespace check.

## Actual physical installation

The following was executed with physical RIFT still running:

    python -B tools/deploy_rcm.py --apply --expect-host AMD-DESKTOP

The installer returned exit 0:
- runningGamePids=[34596], gameProcessCheck=running;
- exactly Core.lua, Main.lua and RiftAddon.toc replaced with source v0.2.18;
- backup folder C:\work\RiftChatModern\artifacts\deploy-backups\20261121T042347Z-lv1xr7f1;
- hashVerified=true, reloadUiRequired=true, reloadUiCommand=/reloadui;
- savedVariablesTouched=false, gameInputSent=false, runtimeReloadVerified=false.

A completely separate post-deployment dry run confirmed 10/10 source-to-installed SHA-256 matches with zero changed files. Direct reading of installed RiftAddon.toc confirmed Version 0.2.18 and the required loader metadata. The game process stayed alive after the copy; no game exit/restart was requested.

A separate read-only actual Deepwood/Atank saved-file audit showed schema 2, 65 system rows, 0 imported rows and a consistent checkpoint sequence 2. SHA256 9a11a2c413b5317fb7dfc63ad189df4022514fc0e661fd98305082756511a616, last modified at 11:20:42 PM EST. This older saved state was not written by the installer.

## Honest remaining validation

The updated addon files are VERIFIED ON DISK. Their runtime load and the /reloadui effect have not yet been independently proven in this session. RIFT is running and the next step is an intentional in-game /reloadui followed by an actual displayed version screenshot.

An earlier Workbridge project successfully performed a one-shot /reloadui in November, but its original singleton receipt must not be blindly replayed. No keyboard, mouse or clipboard input was sent in this deployment, and no game process or SavedVariables file was modified.

No Ollama, OpenCode, or Codex CLI was used.
