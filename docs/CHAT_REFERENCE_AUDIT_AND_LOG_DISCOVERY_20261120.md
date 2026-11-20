# RCM — Legacy Chat Addon Audit and Raw Log-Format Discovery

**Date:** Friday, November 20, 2026 (America/New_York)
**Verified machine:** AMD-DESKTOP
**Repository:** `C:\work\RiftChatModern`
**Installed in-game version:** v0.2.10 (unchanged; this milestone is host-side only)
**Main objective:** Obtain independently verifiable real player-chat reception and eventually a reliable native-chat replacement

## Findings from actual archived source

An original 2013 `NubzRiftInstantMessenger.zip` was downloaded from the CurseForge **Rift Instant Messenger** project (file ID 703668) into a local ignored research folder; no files were copied into RIFT's addon directory or executed.

- Source page: https://www.curseforge.com/rift/addons/rift-instant-messenger/files/703668
- Original ZIP: `artifacts/external-references/NubzRiftInstantMessenger-2013.zip` (ignored, **not committed**)
- SHA-256: `d5493edbcab0b933bd10f986c553b5efcda3cea3d133349dda3b1ab8fe298708`
- Manifest: `Identifier = "Nrim"`, `Environment = "2.2"`, `RunOnStartup = {"Main.lua"}`. The archived startup file is spelled `main.lua`; this case difference is usually resolved on Windows and alone is not a loader failure.
- Lua 5.1 static parsing of that startup file succeeds. Syntax alone **does not** establish that its APIs exist at runtime.
- The archive inspector found **41 first-party Lua source files, 0 RIFT-specific API markers, 61 WoW-style API/XML indicators**, including `DEFAULT_CHAT_FRAME`, `CHAT_MSG_WHISPER`, `ChatFrame1EditBox`, `CreateFrame` and Blizzard `http://www.blizzard.com/wow/ui/` XML namespaces.
- **Decision:** this archive does not provide a proven native RIFT social chat reception mechanism, despite its RIFT manifest and marketing description. Its code is predominantly a World of Warcraft instant-messenger adaptation. Do not import its event/send code into RCM.

The separate RIFT API reference by seebs enumerates `Event.Chat.Npc` and `Event.Chat.Notify`, but not a documented general say/guild/tell receiver. This narrows what can be claimed from the conventional addon API; it does not rule out a separately proven Windows-side game-log or external reader.

- https://www.seebs.net/rift/pts/
- https://www.riftui.com/downloads/cat55-Chat.html lists other historical chat addon references, including Backchat and Loggin'. Their existence is **not** live 2026 API proof.

## New audit utility

`tools/audit_rift_addon_archive.py` is a **read-only static ZIP inspector** to screen future legacy addon references before investing time in them.

It checks one `RiftAddon.toc`, identity/version/environment and ordered `RunOnStartup` names; case-insensitive Windows loader name matching; Lua 5.1 **syntax compilation only** (never execution); suspicious WoW-specific symbols; known RIFT API symbols; and unsafe/oversized ZIP entries. It returns an explicit verdict that is **never** a claim of verified live game behavior.

From a **Windows PowerShell** terminal at `C:\work\RiftChatModern`:

```powershell
& "C:\work\riftreader2\.venv\Scripts\python.exe" -B tools\audit_rift_addon_archive.py artifacts\external-references\NubzRiftInstantMessenger-2013.zip
```

Use the same command with any other already-downloaded RIFT addon ZIP reference, keeping third-party archives out of the installed addon directory until code and manifest have been reviewed.

## New raw-log format discovery (opt-in)

The existing `tools/rcm-chat-observer.cjs` has a new `--sample-raw-lines N` mode for **1 to 30 newly appended decoded lines**, independent of whether the current historical parser recognizes the line shape. Each sample emits JSON with:

- `event="raw_log_sample"`, `observedAt`, and the underlying decoder's `encoding`
- `decodedLine` capped at **1024 UTF-8 bytes**, `decodedUtf8Bytes` for the whole decoded line and `lineTruncated`
- `physicalRiftOriginVerified=false` (the source file and event still require physical correlation)

The decoded byte count is **not a physical on-disk byte count for UTF-16 logs**. Actual raw bytes need separate evidence, if necessary. The mode never modifies the file, sends game input, triggers `/log`, or saves captured lines to disk.

**Default operation remains metadata-only; raw text is emitted only when `--sample-raw-lines` is explicitly provided.** A sample run stops at the line limit or the configured timeout. Old pre-existing history is ignored by starting the shared LuaPadModern tailer from EOF.

### Supervised physical test procedure

1. Verify that **RIFT Live is loaded** with the expected RCM version. Confirm that the game's `/log` setting and actual noncombat `Log.txt` location are known. `/log` is a **toggle**; do not type it blindly when its state is unknown.
2. In Windows PowerShell at `C:\work\RiftChatModern`, run:

```powershell
node .\tools\rcm-chat-observer.cjs --sample-raw-lines 5 --timeout-ms 60000
```

3. If the game writes elsewhere, specify `--path "C:\the\verified\RIFT\Log.txt"`. Once the watcher reports `started`, use the **original RIFT native chat box** to send a known, short test line or run a known `:logprobe TOKEN` from the RCM editor.
4. Compare the line on screen to the output's `decodedLine` and note the exact event shape, source path, observed time, encoding and truncation. A synthetic text file is not sufficient proof.
5. If the watcher times out without a file or lines, record the failure as **inconclusive** until the game's logging state and path are established. Do not silently infer that the Lua API, server or watcher is broken.

The sample may include ordinary guild/private chat text if such messages happen during the observation. Run this mode deliberately and avoid saving or publishing private conversations.

## Validation and failures preserved

- The standalone archive audit has **9/9 fixture tests PASS**, including the actual RCM addon as a positive RIFT API control, WoW-styled code as a negative control, unsafe filenames, duplicate case-insensitive member names, invalid syntax, missing startup file and no-TOC errors.
- `audit_rift_addon_archive.py` was then run against the actual downloaded RIM archive: the verdict was `wow_api_dominant_no_rift_runtime_evidence`; all reported features remain **static**, not runtime.
- The raw-line observer's new child-process cases verify unfamiliar decoded line layouts, suppression of stale history, a bounded two-line stop, 1024-byte Unicode-safe truncation, explicit opt-in and default message redaction.
- **116/116 Python/Lua tests and 24/24 Node tests passed** in the development environment. The in-game RCM v0.2.10 has not been modified in this source-only milestone.
- The first candidate ZIP was misleading as a source of RIFT events; a RIFT `.toc` by itself is not a compatibility proof. The initial Lua syntax probe was rechecked for the correct `loadstring` return handling and confirmed that `main.lua` compiles, while its functions still use WoW APIs.
- The common OneDrive and normal Documents `RIFT\Log.txt` locations remain absent in the latest read-only AMD-DESKTOP checks. No physical game-produced social chat record has been independently captured yet.
- The desktop screenshot facility previously returned `UI_TURN_BUSY`; this milestone does not bypass that lock or claim visual acceptance.

## Next priority and acceptance gates

**P0: real chat log evidence.** Use the new opt-in raw-line mode only after confirming the file path and deliberately creating a test message in the physical client. Amend the parser from actual observed RIFT lines rather than guesses.

**P1: in-game v0.2.10 manual import.** Verify the loaded addon and its `/rcm import status`, partial-chunk receipt and cancel behavior. Installed-file hashes already match; that is a disk proof, not a live UI pass.

**P2: automatic host-to-addon transport.** Design and test only after P0/P1 give reliable input/output receipts. Keep original RIFT chat intact until true player-chat reception and sending are proven.

This document and new tools do not change RCM's `RiftAddon.toc`, version or current deployed files.
