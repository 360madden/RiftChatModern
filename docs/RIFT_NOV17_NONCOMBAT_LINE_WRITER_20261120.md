# RIFT Live November 17 client — narrow noncombat logging write-path evidence

**Research date:** Friday, November 20, 2026 (America/New_York)
**Machine:** AMD-DESKTOP
**Target:** read-only analysis of `C:\Program Files (x86)\Glyph\Games\RIFT\Live\rift_x64.exe`
**Exact executable SHA-256:** `df954b798331e18359be62a31cc74b49fc3f50b87385ebb080a5448256322c01`
**Tools:** existing local RRE Python virtual environment, pefile and Capstone

## Goal

Determine whether the installed RIFT build contains a real noncombat `Log.txt` writer, beyond the historical documentation and embedded string names, without pretending that ordinary Say/Guild/Party/Tell chat has already been captured.

The earlier investigation in `RIFT_NOV17_LOGGING_IMPLEMENTATION_20261120.md` identified the actual `LogConsole` config flag, `Log.txt` file name, `_wfopen` mode `a`, `fclose`, and runtime on/off logic. This follow-up traces actual narrow-output CRT calls and identifies one candidate write path.

## Observed machine-code facts (RVA relative to image base 0x140000000)

- The build imports `fputs` at IAT RVA **0x25FE4E8**, `fflush` at IAT RVA **0x25FE4D8**, `fwrite` at **0x25FE630**, and Win32 `WriteFile` at **0x25FD638**. These were independently enumerated from this executable's import table.
- A writer region in a recorded `.pdata` function/funclet interval **0x70E10C–0x70E333** accesses a file pointer at **[rsi + 0xF8]**, matching the field used in the observed noncombat open/close implementation.
- At **0x70E2B0**, the code calls imported `fputs` with a dynamically prepared narrow string and that file pointer.
- At **0x70E2BD**, the code loads a constant from RVA **0x26C6A04**. Its file bytes begin **0A 00**, a single newline byte followed by NUL.
- At **0x70E2C4**, it calls `fputs` again with this newline constant and the same file pointer. At **0x70E2D1**, it calls imported `fflush` with the file pointer.

This is meaningful **static evidence of a line-oriented, narrow-byte output and flush path** associated with the noncombat logger. Because `fputs` writes a narrow byte string, the exact character encoding still depends on the source text conversion; it is **not proven** to be UTF-8 just because the file can be read with a UTF-8/UTF-16 capable tailer.

## Important call-graph caution

The `.pdata` record begins at **0x70E10C**, which itself does not have a conventional prologue and has **no direct `CALL rel32` references** in the scanned `.text` segment. Nor was a direct absolute code pointer found for this address in scanned `.rdata` and `.data` sections. It may be a compiler-generated funclet, an indirect-call target, or part of a more complex exception/control-flow scheme. **Do not claim that 0x70E10C is the top-level chat handler.**

Another imported `fputs` site at **0x705338** reads a file pointer from a different register and has not been tied to noncombat chat; it should not be conflated with the confirmed same-object +0xF8 writer.

These static references show the client can write lines to a file. They do **not** show whether ordinary player say/guild/tell messages pass through that writer, which channels are logged, the actual current text layout, or whether the runtime logging toggle is currently active.

## Physical evidence needed next

Current persisted `Rift.cfg [Client] LogConsole=False` and absent configured noncombat `Log.txt` explain why the host observer has no verified current-game chat bytes. The physical RIFT process is running but the game was not foreground during host checks.

After deliberate activation of noncombat logging, the existing two-stage exact-text observer can correlate (1) its own RCM console marker and (2) one new user-entered Say message using a fresh `Log.txt` read boundary. If the actual line differs from the historical bracket parser, a short explicitly opted-in raw-line sample should be used to revise the parser from **real bytes**, not guesses.

No game input, client memory access, executable write, RIFT config edit, or SavedVariables modification occurred during this investigation. The addon is installed as **v0.2.19** and separately awaits actual `/reloadui` runtime activation; this report is read-only research, not a new addon version.
