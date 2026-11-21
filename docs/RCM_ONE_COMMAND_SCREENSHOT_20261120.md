# RCM — One-command native RIFT screenshot session

**Engineering date:** Friday, November 20, 2026 (America/New_York)
**Verified machine:** AMD-DESKTOP
**Repository:** C:\work\RiftChatModern
**Installed addon:** v0.2.17; tested v0.2.18 source is not deployed while RIFT runs

## Purpose

RIFT itself can save an in-game JPEG with Numpad *. The prior real 9:39 PM screenshot showed the modern RCM window even though Windows capture repeatedly returned UI_TURN_BUSY. The one-shot .NET 10 screenshot-key helper and the independent Python screenshot receipt checker were already implemented, but they required copying six volatile RIFT identity fields between two separate commands.

The new tools/rcm_screenshot_once.py is a **single explicit command** that composes those two established components. It does not create another keyboard sender, image parser or persistent background agent.

## Exact workflow

1. Validate the explicitly named AMD-DESKTOP hostname.
2. Start the existing .NET RcmScreenshotKey.dll --inspect in read-only mode and require a uniquely identified RIFT process/window. For multibox sessions, require --pid instead of randomly selecting an account.
3. Read and preserve the fresh RIFT PID, HWND, process-start UTC ticks, executable absolute path and SHA256, passing those exact values to the .NET helper.
4. Default --dry-run performs the target checks without any game input.
5. --capture must be accompanied by --ack-single-screenshot. Optional --arm-seconds (1–15) waits briefly for RIFT to be foreground **without activating or focusing it**. Only the .NET helper can send the single VK_MULTIPLY down/up pair.
6. After a reported successful Windows key insertion, use the pre-existing read-only rcm_game_screenshot_receipt.py functions to select a complete JPEG/PNG created after the trigger's baseline nanosecond timestamp in the Screenshots directory selected by RIFT's actual Rift.cfg.
7. Return one combined JSON receipt. The screenshot image remains only in the game folder. No clipboard operations, game config changes, SavedVariables modifications, game relaunch or image copies are performed.

The wait after the key (default 5000ms, maximum 12000ms) is bounded inside this same tool call and does not create a scheduled task or future background work.

## Status distinctions

- foreground_timeout_no_input / game_not_foreground_no_input: RIFT was not active; **no key sent**.
- new_post_key_image_verified: Windows reported the key and the checker found a stable, complete new screenshot after the trigger baseline; the image cannot be cryptographically linked to the HWND from time alone, so physicalRiftOriginVerified remains false.
- key_events_inserted_but_no_new_image: Windows input was reported, but there was no matching new JPEG during the configured window.
- new_image_verification_failed: a candidate file was corrupt or could not be independently read. This is not screenshot proof.
- image_source_unavailable_after_key / invalid_capture_baseline_after_key: evidence is missing after input, so gameInputSent remains **true**, not erased by a later exception.
- rift_inspection_not_ready: no unique RIFT process or an ambiguous multibox selection.
- refused: wrong machine, missing explicit capture acknowledgment, missing helper build, malformed flags or invalid subprocess protocol.

## Real AMD-DESKTOP evidence

The live read-only dry run inspected RIFT PID 34596, HWND 0xA0C2C and the exact November 17 Glyph client build. It returned game_not_foreground_no_input and never called SendInput.

A complete one-command trial was also invoked with --capture --ack-single-screenshot --arm-seconds 2. It returned exit **2**, foreground_timeout_no_input, gameInputSent=false, screenshotFileVerified=false and gameFocusChanged=false. RIFT remained in the background throughout. No game input or new screenshot is claimed.

## Test-first regression evidence

The initial eight deterministic fixture tests verified one inspect → pinned action → independent screenshot receipt, dry-run no-input, explicit acknowledgment, wrong hostname, ambiguous multiple RIFT clients, no image after input and invalid child protocol.

A subsequent red/green review found three problems: a corrupt screenshot caused an uncaught exception, a missing screenshot directory concealed that the OS key had already been inserted, and invalid post-key timestamp handling also lost the known input receipt. These tests first failed. After repair, post-key failures return exit 2 with gameInputSent=true and screenshotFileVerified=false.

**Ten deterministic Python orchestration tests pass.** All use mocked child subprocesses and temporary data, and NEVER call Windows input. The separately compiled .NET helper has 19 internal assertions and eight Windows subprocess tests, with release build warnings treated as errors.

## One practical Windows PowerShell command

From C:\work\RiftChatModern, inspect and validate without any game input:

    & "C:\work\riftreader2\.venv\Scripts\python.exe" -B tools\rcm_screenshot_once.py --expect-host AMD-DESKTOP --dry-run

Explicitly request one screenshot with a short foreground arm window:

    & "C:\work\riftreader2\.venv\Scripts\python.exe" -B tools\rcm_screenshot_once.py --expect-host AMD-DESKTOP --capture --ack-single-screenshot --arm-seconds 10

The RIFT game must be brought to the foreground by the operator during the arm period; the helper NEVER activates it itself. If more than one RIFT client is running, add --pid and the exact desired client PID. The .NET Release DLL must already have been built by dotnet build on this machine.

The previous v0.2.18 focus-footer source fix is committed but **not yet installed** while RIFT remains open. Only a fresh game-created image after the actual key will complete the new screenshot workflow's physical acceptance.

No Ollama, OpenCode or Codex CLI was used. No fictitious internal ChatGPT reasoning agents were claimed.
