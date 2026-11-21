# RCM editor-input preflight — .NET 10, read-only

**Development date:** Friday, November 20, 2026 (America/New_York)
**Verified workstation:** AMD-DESKTOP
**Repository:** C:\work\RiftChatModern
**Component:** tools/RcmEditorInput (C#/.NET 10 Windows)

## Product purpose

RCM v0.2.17 supports the **:import TOKEN I/N BASE64URL** command in its own focused editor, using the same tested Lua RCM1-B64URL decoder and saved-history duplicate checks as /rcm import.

The next milestone is Windows-to-RCM editor delivery with independently observed game acceptance. Existing RR2 movement SendInput evidence does NOT prove text entry into RCM's own editor. This new helper is deliberately **preflight only**, not a speculative automatic keyboard sender.

## Implemented

The standalone project is under:

    C:\work\RiftChatModern\tools\RcmEditorInput\RcmEditorInput.csproj
    C:\work\RiftChatModern\tools\RcmEditorInput\Program.cs

It performs these bounded, read-only operations:

- Validates one :import command with a 12-uppercase-hex transfer token, INDEX/TOTAL both 1–12, INDEX <= TOTAL, a base64url chunk of 1–88 characters, and at most 160 UTF-8 bytes. It refuses normal player-chat text, native /rcm commands, multiple commands, trailing newlines and unknown flags.
- Generates a JSON receipt with command character count, part/total, SHA-256 command fingerprint and machine. It does NOT print the reversible Base64URL chat payload.
- Supports --stdin-command for exactly one bounded piped command, avoiding encoded chat in Windows process arguments. --command remains available for a disposable synthetic test.
- Supports --inspect to read the currently running RIFT process PID, process-start UTC ticks, main HWND/title, executable path and SHA-256. Zero RIFT processes are unavailable, and multiple same-name processes are ambiguous rather than randomly bound.
- Supports --verify-target to compare an explicitly pinned PID, start ticks, HWND, executable path and SHA-256. That check is process identity inspection, NOT actual game/editor keyboard-focus verification.
- Produces gameInputSent=false, editorFocusVerified=false, addonImportAcceptedVerified=false and diskSaveVerified=false. No keyboard, clipboard, focus, remote connection, game launch or game file write is implemented.

## Red/green evidence

Local installed SDK: **.NET 10.0.302**. Release build passed with zero warnings and zero errors and no additional NuGet dependencies.

- The initial self-test fixture mistakenly expected a 30-character import command when the correct count was 31; this was corrected.
- The real validator initially accepted an import with a trailing newline because .NET's dollar-sign regex end anchor can match just before the final newline. It was fixed using absolute start-of-input and absolute end-of-input anchors. The negative test passes.
- A Python test fixture first supplied CRLF to a Windows text-mode subprocess, yielding a doubled carriage return. The fixture now supplies one LF and relies on Windows text-mode translation; the pure self-test separately covers single CRLF.
- **21/21 .NET internal assertions passed** and **7/7 Python Windows subprocess tests passed**. The integration tests check real dotnet child-process invocation, valid/invalid commands, fingerprints, stdin, oversized/multiple lines and option rejection. One additional source-level regression refuses to accept Windows input, foreground, clipboard or direct file-writing API dependencies in this inspection-only component.

The read-only helper's --inspect operation previously located the currently running physical RIFT process on AMD-DESKTOP with PID 34596, HWND 0xA0C2C, process start ticks 639308249563595623 and the November 17 client executable SHA256 DF954B798331E18359BE62A31CC74B49FC3F50B87385EBB080A5448256322C01. These values are session-specific and MUST NOT be reused without fresh process checks. A separate Windows window inventory confirmed window title RIFT, process rift_x64, class TWNClientFramework, 2576x1408 geometry. A screenshot attempt returned UI_TURN_BUSY and no in-game addon/editor screenshot was obtained.

No input, focus action, clipboard or RIFT settings change occurred. The last observed persisted RIFT LogConsole flag was False, with no noncombat Log.txt file. Normal Say/Guild/Party/Tell reception is still unverified.

## Windows PowerShell examples

Run these from C:\work\RiftChatModern:

    dotnet build .\tools\RcmEditorInput\RcmEditorInput.csproj --configuration Release
    dotnet run --project .\tools\RcmEditorInput\RcmEditorInput.csproj --configuration Release --no-build -- --self-test
    dotnet run --project .\tools\RcmEditorInput\RcmEditorInput.csproj --configuration Release --no-build -- --inspect

Validate the synthetic v0.2.17 editor acceptance candidate WITHOUT sending it:

    dotnet run --project .\tools\RcmEditorInput\RcmEditorInput.csproj --configuration Release --no-build -- --command ":import C0A4F8141CFA 1/1 RwBSQ01Qcm9iZQBHdWlsZABSQ00gdjAuMi4xNyBlZGl0b3IgaW1wb3J0IGFjY2VwdGFuY2U"

A connected companion can instead pipe one complete command into --stdin-command so the reversible encoded text does not appear in Windows command-line arguments. The result remains validation only.

## Next acceptance gates

- Physically load RCM v0.2.17; verify the real editor has focus and accepts one manually entered :import.
- Record the actual assigned imported history ID, IMPORTS tab row and duplicate replay behavior.
- Confirm the legitimate RIFT Save.Begin/normal save sequence and independently verify the exact ID plus transfer token in the real character SavedVariables file.
- Independently prove the current RIFT client produces real noncombat social-chat Log.txt records before treating any historical bracket parser candidate as ordinary player chat.
- Only after those live facts are established can a sender be designed and validated. OS-level input insertion alone cannot prove that the game accepted the message.

This project adds no game addon changes, no new .toc version, no client memory writes, no console logging toggles and no automatic desktop actions. Git ignores generated bin and obj directories, keeping only the source/project, tests and documentation.

No Ollama, OpenCode or Codex CLI was used, and no unspawned ChatGPT subagents were claimed.
