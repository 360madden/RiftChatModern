# RiftChatModern v0.2.5 — Full Codebase Bug Hunt

Date: Friday, November 20, 2026 (America/New_York)
Host: AMD-DESKTOP | Repository: C:\work\RiftChatModern
Language: Lua 5.1 | RIFT addon Environment 4.3 | Public GitHub: 360madden/RiftChatModern

## Scope

Reviewed all project Lua runtime modules (Core.lua, AddonMessages.lua, NativeChatProbe.lua, ConsoleMirror.lua, Main.lua), the RIFT addon manifest, README, existing regression tests, and installed RIFT API references for Frame:SetPoint/Frame:ClearAll and Command.Message.Send.

The v0.2.4 worktree started clean and baseline passed 63/63 Lua 5.1 tests. New tests reproduced defects first, then source fixes were implemented. No user SavedVariables were rewritten or deleted. The RIFT live loader and UI must be evaluated separately.

## Confirmed bugs resolved

| Area | Defect | Change |
|---|---|---|
| Main.lua UI | Repeated SetPoint without clearing persistent anchors | ClearAll before re-anchoring, then restore width/height; stricter fake RIFT API catches conflicts |
| Main.lua pagination | OLDER skipped the last partial page and overlapping ranges were reported | Limit offset to whole pages, preserve final partial page, calculate first/last from actual selection |
| Core.lua persistence | Duplicate saved row IDs accepted, making GetMessage ambiguous | Reject duplicate IDs without deleting saved data |
| Core.lua export | NaN, infinity and fractional clipboard byte limits bypassed validation | Require finite integer |
| Core.lua persisted search | Control characters could be restored into search state | Ignore malformed persisted search; retained messages unchanged |
| Core.lua extensions | 512-byte response slicing could cut a multibyte character | UTF-8-boundary-preserving prefix |
| Main.lua game events | NPC name and game notification clipping could split UTF-8 | Boundary-safe prefix for NPC sender, NPC text, alerts, native channel report |
| Main.lua NPC source | Empty NPC fromName dropped otherwise valid event | Fall back to NPC |
| ConsoleMirror.lua | Long multibyte console output could truncate mid-character | UTF-8-safe bounded mirror output |
| AddonMessages.lua receive | Peer receipt counted even if local callback failed | Count received only after store; add receiveFailed counter |
| Main.lua peer adapter | Incoming-data handler discarded actual storage result | Return true/false storage outcome |
| AddonMessages.lua send | Submission error incremented rejected, implying server refusal | Count as unknown, no automatic retries |
| Lua mock harness | SetPoint mock never detected stale anchors or Frame:ClearAll | Include ClearAll behavior and strict anchor regression |
| Tests | Missing malformed IDs, limits, Unicode, partial paging and receipts | Added test_bug_hunt.py and expanded messaging tests |

## Verification

- 76/76 Lua 5.1 tests with Lupa and RIFT mock APIs.
- RunOnStartup zero-return contract preserved for all startup files; version and Email metadata remain present.
- Existing resize, drag, focus, clipboard, native console and transport suites retained.
- Tests do not prove physical RIFT runtime accepted v0.2.5 or actual clipboard worked.

## Deployment and live acceptance

Canonical source: C:\work\RiftChatModern\addon\RiftChatModern
Installed folder to verify: C:\Users\mrkoo\OneDrive\Documents\RIFT\Interface\AddOns\RiftChatModern

PowerShell 7:
    cd C:\work\RiftChatModern
    & "C:\work\riftreader2\.venv\Scripts\python.exe" -B -m unittest discover -s tests -v

In physical RIFT: load new addon with /reloadui, use /rcm; inspect version, addon error dialogs, paging, drag, resize, detail reader, and versioned startup. No blind input when native/editor focus uncertain. Do not modify SavedVariables or publish private screenshots.

## Open verification / limitations

- Physical v0.2.5 loader, paging, resize, drag acceptance requires independent live proof.
- Clipboard copying is mocked but not independently verified live; could replace current clipboard content.
- Peer RCMDevV1 receipt needs a second real RIFT client.
- Native player say/tell/guild social-chat send/receive remains a future product milestone.
