# RiftChatModern v0.2.2 — physical RIFT acceptance report

**2026-11-20 · AMD-DESKTOP · RIFT PID 22532 / HWND 0x980F44**

## Outcome

| Check | Evidence | Outcome |
| --- | --- | --- |
| Game startup | After deploying v0.2.2, a read-only RIFT client capture included the colored native chat line "RiftChatModern v0.2.2 \| Loaded. /rcm opens the console." | **LIVE PASS** |
| Four v0.2.1 startup exceptions | User supplied addon-error screenshots for Core.lua, AddonMessages.lua, NativeChatProbe.lua and ConsoleMirror.lua ("Unknown: assertion failed", [C]: assert). The subsequent v0.2.2 startup portion of the native chat display lacked these errors. | **LIVE IMPROVEMENT OBSERVED**, not exhaustive log proof |
| Dismiss stale error modal | One exact-window guarded mouse click on IGNORE at client (932,1090), 3/3 SendInput events. Subsequent independent screenshot showed the modal absent. | **LIVE PASS** |
| Native chat entry | One exact-window scan-code Enter pulse, 2/2 events. A read-only crop showed the input field open. | **LIVE PASS** |
| Native /rcm slash launcher | Sent '/' and verified the visible draft, then 'r', 'c', 'm', Enter as individual exact-HWND 2/2-event pulses. New screenshot showed the RCM v0.2.2 panel open. | **LIVE PASS** |
| Compact dark UI | The exact-HWND screenshot showed title, channel tabs, search, messages, copy/clear/focus/mirror/run buttons, and version header. | **LIVE PASS** |
| Custom editor focus | One reviewed FOCUS INPUT click at client (1280,758), 3/3 events. Screenshot independently showed a green "INPUT • FOCUSED" label and "Editor focused" footer. | **LIVE PASS** |
| Title-bar drag | One pinned mouse down / 8 incremental moves / release, 11 Win32 SendInput events total. Start (1198,269), end (1318,329), requested delta (+120,+60). The next screenshot showed approximately that panel displacement. | **LIVE PASS** |
| History clipboard | Clipboard preflight listed seven formats, including image-related formats 2, 8, 17. The copy test was deliberately **NOT executed** to avoid replacing an existing image/other clipboard data. | **PENDING**, offline mocked test passed |
| Native social chat | No actual say/guild/tell capture or native social-message sending verified. | **NOT IMPLEMENTED/VERIFIED** |
| Addon-data channel and optional console mirror | Lua 5.1 mocked tests passed; no second physical client delivery tested. Mirror remained OFF. | **OFFLINE PASS ONLY** |

## Root cause and fix

v0.2.1 displayed four separate startup assertions in modules that each ended with a top-level returned module table. The corresponding known-working RiftReader2 and RRECollector startup scripts do not return module values. The v0.2.2 patch removed the four top-level module return statements while preserving named global exports, with a new test verifying all five RunOnStartup chunks execute without returning a value.

**Exact internal RIFT loader code is not available.** The physical observation supports the fix, but does not establish the loader's private assertion implementation.

## Screenshot proof retained locally (not published)

- Path: C:\work\RiftChatModern\artifacts\RiftChatModern-v0.2.2-after-drag-20261120.png
- Capture UTC: 2026-11-20T12:13:41.045976+00:00
- Dimensions: 2560 x 1369
- SHA-256: 6d74fc8df2061280dc4dd982f13a2d308b9b1296e59ca38a82707bcd98485b41
- Size: 4,845,459 bytes
- Capture: exact-HWND read-only ImageGrab using existing RPT helper; verified PID/HWND before capture
- Private: under gitignored artifacts/; contains in-game player chat and must **not** be pushed.

Earlier read-only screenshots used the same pinned RIFT window and confirmed the old error modal, modal dismissal, native chat draft, launch, input-focus indicator, and drag movement. Input-receipt IDs are recoverable from Workbridge command history under the rcm-v022 names.

## Important boundaries

- The assistant did **not** issue /reloadui; a new v0.2.2 game load occurred between read-only observations. Do not claim the assistant caused the reload.
- The test did not move Atank, cast spells, invoke travel, or modify the encrypted game stream.
- Exact command-insertion receipts alone are not game action proof; they were paired with independent game-window screenshots.
- The saved character-history data was preserved; the chat panel showed startup messages from more than one reload.
- Repeated startup announcements and the small paging-arrow glyphs are UX refinements for later revisions.
- Source/manifest v0.2.2 hotfix commit: 1bb63bd190ff705cb7a7c1f4b621490eeb7d3d83. Tests: **54/54 Lua 5.1 passes** before live acceptance.

## Next high-impact work

1. Test live Copy History **only after preserving or intentionally replacing** the user's current clipboard data.
2. Replace difficult-to-read paging-arrow glyphs with legible controls; consider compact per-channel options.
3. Prove peer receipt of the dedicated addon-data channel on a second physical RIFT client.
4. Research actual native player-chat reception separately from addon data. Reuse the existing LuaPadModern read-only Log.txt watcher if RIFT /log is confirmed; do not silently misrepresent addon messages as player chat.
