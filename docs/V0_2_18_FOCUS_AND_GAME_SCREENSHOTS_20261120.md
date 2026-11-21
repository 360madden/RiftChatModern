# RCM v0.2.18 — Focus consistency and native game screenshots

**Date:** Friday, November 20, 2026 (America/New_York)
**Verified machine:** AMD-DESKTOP
**Canonical repository:** C:\work\RiftChatModern
**Source version:** v0.2.18
**Installed version:** v0.2.17 — deployment deferred while RIFT is running
**Compatibility:** RIFT Environment 4.3, SavedVariables schema 2, API interface 2 unchanged

## Root cause from the actual screenshot

A native RIFT screenshot made at 9:39:25 PM EST showed the RCM v0.2.17 header reading INPUT • NOT FOCUSED while the footer simultaneously claimed Editor focused • local commands start with : . This was an actual contradiction visible to the user.

The editor's GetKeyFocus-derived state and header were correct. The footer was holding an earlier success message from focusEditor(), which did not update when the game or another text field took keyboard focus.

In addon/RiftChatModern/Main.lua, a focus-specific footer now carries an explicit FOCUS: prefix and is refreshed ONLY on a real GetKeyFocus-derived state transition: focused, search, unfocused, hidden or unavailable. Ordinary command responses, imported history-ID receipts and other status messages are preserved and not overwritten during focus polling.

A new real Lua 5.1 mock test first FAILED when the editor lost focus after a successful FocusEditor() call: the footer still claimed focus. After the change, the same test passed, including search focus, preserving nonfocus command receipts and hiding the window. This changes RCM's actual Lua and therefore increments the source, .toc and all version-specific tests to v0.2.18.

This is source verification, NOT a claim that v0.2.18 has loaded in physical RIFT. The client is still open; do not hot-deploy.

## Actual native screenshot evidence

Previously generated, read-only file:

    C:\Users\mrkoo\OneDrive\Documents\RIFT\Screenshots\2026-11-20_213925.jpg

- Format: JPEG, dimensions: 2560 x 1369; bytes: 1,874,791.
- SHA256: 8f56980b976657ddf43028056b71798b7919628d5b023adb94492b3e220f1ffe.
- Visible: RCM v0.2.17, dark compact panel with tabs, history, search, text editor and contradictory focus statuses.
- This is real game-rendered image evidence, NOT proof which key triggered it.
- WinApp desktop capture still encountered UI_TURN_BUSY; RIFT's own screenshot file is usable.

The source image was NOT modified, uploaded to Git or used as a fake live-v0.2.18 acceptance screenshot.

## Read-only screenshot receipt tool

The new Python tool tools/rcm_game_screenshot_receipt.py reads the existing %APPDATA%\RIFT\Rift.cfg [Client] DocumentsDirectory and selects its Screenshots subfolder. No guessed fixed OneDrive path is used.

It has strict host identity, RIFT screenshot filename pattern checks, bounded directory and image limits, real JPEG/PNG decode and full load, SHA-256 plus before/after stable-file metadata. Invalid image, extension mismatch, symlink, wrong/missing game config or changing bytes fail instead of being accepted as evidence.

The default mode reports the newest EXISTING screenshot with freshnessVerified=false. --baseline returns a new nanosecond boundary without touching game input. --after-ns with --require-new must find an image strictly newer than that baseline or exits nonzero. A bounded optional --wait-ms can wait for a user-generated file without creating a background service.

The output is explicitly labelled: gameInputSent=false, keyPressVerified=false, gameWindowCorrelated=false, physicalRiftOriginVerified=false, filesChanged=false. Matching a screenshot path does not independently establish that a specific RIFT keyboard input occurred.

Eight fixture tests passed: existing SHA and dimensions, fresh vs stale, latest eligible image, unrelated files, corrupted or format-mismatched images, bounded new-image polling, invalid options/machine, invalid configuration. Real AMD-DESKTOP audit reported 45 candidate screenshot names and correctly verified the exact 9:39 PM file.

A read-only baseline was recorded during development:

    baselineEpochNs = 1795233249143726500

That number applies only to images created later, not to the existing JPEG.

## Manual use from Windows PowerShell

Run in C:\work\RiftChatModern, while RIFT is active:

    & "C:\work\riftreader2\.venv\Scripts\python.exe" -B tools\rcm_game_screenshot_receipt.py --expect-host AMD-DESKTOP --baseline

With the actual RIFT window in foreground and RCM visible, manually press Numpad * in the game. Then check using the NEW baseline printed above:

    & "C:\work\riftreader2\.venv\Scripts\python.exe" -B tools\rcm_game_screenshot_receipt.py --expect-host AMD-DESKTOP --after-ns BASELINE_NUMBER --require-new

This tool does NOT synthesize a key, change the clipboard, change focus, write images, change config or modify character SavedVariables.

## Full validation and deployment boundary

- 212/212 Python/Lua 5.1 tests passed.
- 47/47 Node.js tests passed.
- 259 total automated tests passed.
- Git diff whitespace check passed (only standard Windows line-ending warnings).
- Version literals synchronized to source v0.2.18 across Lua/toc/tests, preserving SavedVariables schema 2.
- Guarded installer dry run identified exactly Core.lua, Main.lua and RiftAddon.toc as changed files.
- The live RIFT process remained open. NO deployment was attempted and the physical installation remains v0.2.17. The source must be deployed only after verifying the game has closed, followed by an independent 10/10 hash check and a fresh physical screenshot.

The core product blockers remain real social-chat reception, a confirmed editor import accepted by the running game, automatic verified host-to-addon delivery, and separately checked social sending. No Ollama, OpenCode or Codex CLI was used and no imaginary internal AI subagents were claimed.
