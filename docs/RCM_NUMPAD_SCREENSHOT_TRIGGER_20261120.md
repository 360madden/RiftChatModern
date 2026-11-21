# RCM — One-shot Numpad * screenshot key for the physical RIFT client

**Engineering date:** Friday, November 20, 2026 (America/New_York)
**Verified machine:** AMD-DESKTOP
**Canonical repo:** C:\work\RiftChatModern
**Current installed addon:** v0.2.17; v0.2.18 source remains pending while RIFT runs

## Why this helper exists

Windows WinApp desktop capture repeatedly returned UI_TURN_BUSY on the physical RIFT client. The user identified a simpler built-in RIFT action: pressing **Numpad *** in the actual game writes a JPEG into RIFT's configured Screenshots directory.

A prior real file was independently inspected at:

    C:\Users\mrkoo\OneDrive\Documents\RIFT\Screenshots\2026-11-20_213925.jpg

It was JPEG, 2560x1369, 1,874,791 bytes, SHA256 8f56980b976657ddf43028056b71798b7919628d5b023adb94492b3e220f1ffe. It visibly included the RCM v0.2.17 window. **It was captured earlier by the user, not by this helper**.

RCM already has an independent **read-only screenshot verifier** in tools/rcm_game_screenshot_receipt.py, which reads Rift.cfg to locate Screenshots, validates complete file bytes/dimensions and can require a file newer than an exact nanosecond baseline. The missing half was a narrowly scoped, controlled Numpad Multiply key trigger.

## Implementation: .NET 10 Windows, only VK_MULTIPLY

New standalone host project:

    tools/RcmScreenshotKey/RcmScreenshotKey.csproj
    tools/RcmScreenshotKey/Program.cs

The helper is **deliberately separate** from tools/RcmEditorInput, which remains read-only and is protected by a no-input source regression.

Supported actions:

- **--inspect [--pid PID]**: read-only current RIFT process identity (machine, PID, main HWND, process start UTC ticks, exact executable path and SHA-256, Win32 class/title and foreground state). If multiple RIFT processes exist, refuse automatic selection until an exact PID is supplied.
- **--dry-run**: requires six exact identity fields; reads and confirms the process, window and foreground conditions without sending keyboard input.
- **--capture --ack-single-screenshot**: additionally requires six exact identity fields, then checks the same Windows session, exact rift_x64 process/start, exe path and SHA-256, exact root HWND ownership, visible/non-minimized window, title RIFT/class TWNClientFramework, foreground identity and absence of held modifier keys. Only after those checks can it issue a **single atomic Windows SendInput batch of exactly two events**: VK_MULTIPLY down and VK_MULTIPLY up. It **never activates the game, changes focus, types chat text, uses the clipboard, touches client memory, retries ambiguous key presses or changes RIFT settings**.
- On a successful Windows key-insertion receipt, the helper records baselineEpochNs just before SendInput and explicitly says screenshotFileVerified=false. It must be paired with the independent Python screenshot verifier to establish whether a new actual JPEG appeared.

No arbitrary keycode is configurable. The helper sends neither Enter nor editor text. A Windows SendInput return of 2 proves only two OS input events were inserted, **not that RIFT handled the hotkey or wrote a screenshot**. A partial result is marked ambiguous, never retried automatically. If an exception occurs after an input call has started, the receipt marks gameInputSent unknown instead of incorrectly asserting false.

## Test-first evidence and root fixes

- .NET 10 Release build: **zero errors, zero warnings**.
- Internal .NET self-tests: **13 assertions passed**, including Win32 INPUT struct size, exact VK_MULTIPLY key-down/key-up flags, strict CLI parsing, and no arbitrary keys.
- **7 actual Windows/Python subprocess integration tests passed**. They cover explicit capture acknowledgment, rejecting invalid/duplicate arguments, wrong machine/PID/HWND and unknown keys without input, read-only process inspection, and a real pinned dry run against the physical RIFT process (without generating an image).
- A separate pinned dry run initially FAILED because the code counted only six arguments, omitting the --dry-run mode flag. It was corrected to require seven distinct options in dry-run and eight in capture mode. This failure was observed before the fix and the case is included in the regression suite.
- One manually requested, exactly pinned live trial used process PID 34596, HWND 0xA0C2C, start ticks 639308249563595623 and executable SHA256 DF954B798331E18359BE62A31CC74B49FC3F50B87385EBB080A5448256322C01. **RIFT was not the Windows foreground window**, so the helper returned **exit code 2, status game_not_foreground_no_input and gameInputSent=false**. It did NOT press the key.
- The independent screenshot verifier, using baselineEpochNs **1795233789937468100** recorded just before the trial, returned **exit code 2, status no_new_screenshot, 45 filename-matching candidate images**. This is the correct no-input/no-new-file result, not a failed screenshot by the game.
- The helper has never been shown to insert VK_MULTIPLY into a foreground RIFT game. Actual key handling and screenshot creation still require a separate accepted physical trial.

## Exact supervised workflow

Run from **Windows PowerShell** in C:\work\RiftChatModern:

    dotnet build .\tools\RcmScreenshotKey\RcmScreenshotKey.csproj -c Release
    dotnet .\tools\RcmScreenshotKey\bin\Release\net10.0-windows\RcmScreenshotKey.dll --inspect

Use the **FRESH** PID, HWND, process start ticks, full exe path and SHA shown in this inspection, not the historical values above.

With RIFT deliberately brought to the foreground, the following form performs a read-only guard check:

    dotnet .\tools\RcmScreenshotKey\bin\Release\net10.0-windows\RcmScreenshotKey.dll --dry-run --expect-host AMD-DESKTOP --pid PID --hwnd 0xHANDLE --start-ticks TICKS --exe-path "RIFT_EXE_PATH" --exe-sha256 SHA256

Only when this returns ready_no_input and the user intends one screenshot, add **--capture --ack-single-screenshot instead of --dry-run**. This is the one action that may write a new RIFT JPEG via the game's built-in hotkey. The helper will not steal focus if ChatGPT/PowerShell is currently foreground.

If a single capture reports windows_key_events_inserted and baselineEpochNs B, independently check the file using:

    & "C:\work\riftreader2\.venv\Scripts\python.exe" -B tools\rcm_game_screenshot_receipt.py --expect-host AMD-DESKTOP --after-ns B --require-new --wait-ms 5000

Only a successful new-file receipt and visual inspection prove the game created a useful screenshot. Do not treat an existing JPEG, an arbitrary newer file, or the Win32 input receipt alone as proof of RCM UI behavior.

## Physical RCM addon deployment is separately pending

The game was still running when this code was built. The installed addon remains **v0.2.17**, and tested **v0.2.18 source** requires replacement of Core.lua, Main.lua and RiftAddon.toc only after a clean RIFT shutdown; never hot-deploy merely to test screenshot capture.

## Bounded foreground arming — no focus changes

A follow-up regression reproduced the remaining usability gap: a screenshot attempt from ChatGPT naturally finds the RIFT game in the background. Without an explicit arming mode, the otherwise valid request immediately returns game_not_foreground_no_input.

The optional **--arm-seconds N** flag (integer **1–15** only) is now available **exclusively with --capture --ack-single-screenshot**. It waits at most N seconds for the already-pinned RIFT HWND to become foreground, without using SetForegroundWindow or any window activation. Once it becomes foreground, the entire process path, start epoch, executable SHA, HWND and window title/class are independently rechecked, and key-down/key-up may be sent once. If it never becomes foreground, it returns **foreground_timeout_no_input**, no key events are sent, and the process exits nonzero. An invalid wait, missing capture opt-in or changed target is refused. It never loops indefinitely or retries an uncertain keypress.

A newly added red-phase Windows integration test initially failed because --arm-seconds was unrecognized. The green phase passed for an accepted bounded request, out-of-range/negative/noninteger waits, and refusal to arm a dry run. A live **two-second** exactly pinned arm was attempted after new screenshot baselineEpochNs **1795234079754584700**; RIFT remained in the background, so the helper correctly returned exit 2 **foreground_timeout_no_input**, gameInputSent=false. Independent verification reported **no_new_screenshot** and 45 existing candidate screenshot names. **No input event was sent in this trial**.

The follow-up self-test count is **19 internal .NET assertions**, and the integration suite has **8 Windows subprocess cases**. A further input-integrity review fixed the partial-batch edge case: when SendInput reports that only the first keyboard event was inserted, the helper may send **one keyup-only recovery event** if the SAME RIFT HWND remains foreground and has the SAME PID owner. It never retries VK_MULTIPLY key-down, does not send a release into a different foreground application, and reports whether the release was attempted and inserted. If the release cannot be confirmed, `partialKeyReleaseUnverified` remains true rather than falsely claiming a clean key state. Five pure .NET self-test assertions cover the release decision. The full RCM regression suites pass **220/220 Python/Lua and 47/47 Node.js tests, 267 total**. The .NET Release build previously passed with zero warnings/errors; the updated project is also built by the passing integration suite.

The one-shot PowerShell command form with arm support is the same as above, adding **--arm-seconds 10** after --capture --ack-single-screenshot. The user can initiate it, then voluntarily switch to RIFT during that bounded window. RCM does not automatically steal desktop focus. A screenshot is established only after a separately verified fresh JPEG receipt.

No Ollama, OpenCode or Codex CLI was used. No fictitious ChatGPT subagents were claimed.
