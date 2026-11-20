# Rift Chat Modern v0.2.4 — Resizable Window Development and Acceptance

**Date:** 2026-11-20 (America/New_York)
**Host:** AMD-DESKTOP, Workbridge 0.16.5-dev
**Repo:** C:\work\RiftChatModern
**Target:** RIFT Live, Lua 5.1, Environment 4.3
**Source:** addon/RiftChatModern, deployed separately to verified OneDrive AddOns location.

## Implemented

- Bottom-right 26×26 resize grip with mouse-down, mouse-up and mouse-up-outside, pointer-left recovery via Inspect.Mouse(), and hover/active feedback. Drag and resize cannot run together.
- Centralized layoutWindow() updates positions/dimensions of header, tabs, search, message card, rows, overlay, copy/clear/focus/mirror actions, editor, RUN button, status footer and resize grip.
- Default window is 760×618; nominal minimum 680×480. Maximum bounds are determined by the current UIParent viewport and the window's fixed top/left position.
- Number of visible rows follows the message card height, lazily creates only required row frames (up to 80), and keeps paging bounded by retained messages (240).
- Message previews use the current history-card width instead of a fixed 79-character cutoff.
- Full message details support PREV/NEXT paging with UTF-8 safe page breaks, and COPY MESSAGE still copies the complete original message.
- Position and size are stored as RiftChatModernSaved.ui = {x, y, w, h}. Existing history remains untouched. Malformed values are sanitized; display viewport changes clamp bounds.
- CLI /rcm size W H and /rcm size reset plus additive Lua API RiftChatModernAPI.SetWindowSize(w,h); status includes dimensions, minimums and visible row count.
- Existing startup ordering, zero-return chunk contract, Lato fonts, opt-in console mirror, RCMDevV1 addon transport, and native chat fallback are unchanged.

## API reference

Use /rcm to open the panel, drag the // grip, or enter /rcm size 1000 750 into native RIFT chat.

    local rcm = _G.RiftChatModernAPI
    if rcm and rcm.interfaceVersion == 1 then
        local ok, err = rcm.SetWindowSize(1000, 750)
        local status = rcm.GetStatus()
        -- status.windowWidth, status.windowHeight, status.visibleRows
    end

## Validation evidence and limitations

- **MOCK:** 63/63 tests under real Lua 5.1 via RR2 Python Lupa. Nine resize-specific tests cover default size, diagonal and single-axis gestures, release recovery, parent-relative containment at 680×480 / 760×618 / 1100×800, viewport transitions, invalid/restored SavedVariables, paging, focus, drag/resize independence and idle frame allocation.
- **MOCK:** tests/test_rift_startup_contract.py verifies that RunOnStartup files return no values; RiftAddon.toc retains Author 360madden and Email placeholder.
- **LIVE:** This document does not claim an in-game pass for v0.2.4 until screenshot/input-confirmed physical RIFT testing is separately recorded.
- **NOT CLAIMED:** Native social player say/tell/guild reception or sending; cross-client data receipt; actual clipboard integration testing.

## Physical acceptance checklist

1. Confirm process identity and current game window; do not reuse historical PID/HWND without fresh verification.
2. Load v0.2.4 via /reloadui or client restart, verify colored startup message and title version 0.2.4, and inspect any addon-error dialog.
3. Open with /rcm; drag the bottom-right grip horizontally, vertically and diagonally; verify it does not move the title-bar anchor.
4. Verify tabs, search, history, buttons and editor remain readable after resizing. Compare message density at 680×480 and approximately 1000×750.
5. Open a long message, use PREV/NEXT and COPY MESSAGE only when clipboard replacement is permitted.
6. After release, reload and verify SavedVariables size and position restored and message history survived.
7. Record exact observed pass/fail evidence. Distinguish source/installed checks from live game memory.

## Deployment policy

Copy only nine canonical addon files from addon/RiftChatModern to verified existing OneDrive RIFT AddOns directory, then compare SHA-256. Do not touch user SavedVariables or publish private in-game screenshots. Commit and push only reviewed source, README, tests and this document.
