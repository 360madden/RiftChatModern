# RiftChatModern v0.2.3 — navigation readability and release

**Date:** 2026-11-20; **host:** AMD-DESKTOP; **repository:** C:\work\RiftChatModern.

## Changes

- Replace hard-to-read history arrow buttons with the words **OLDER** and **NEWER**, using wider 64-pixel controls.
- Keep the 760x618 panel and the existing draggable title-bar and input-focus behaviors.
- Synchronize version 0.2.3 across the RiftAddon.toc manifest, Main.lua fallback, core status API, documentation and tests.
- Add paging-label and minimum-width assertions to the Lua 5.1 geometry regression suite.

## Verification

54/54 Lua 5.1 mock regression tests passed after the changes, including the RunOnStartup zero-return contract. The previously documented v0.2.2 physical startup/drag/focus acceptance is **historical**; it does not prove physical acceptance of this new revision.

## Remaining work

- Reload/restart the physical RIFT client and confirm v0.2.3 startup, no new addon errors, paging labels and click behavior.
- Verify live clipboard copy without inadvertently replacing the user's existing clipboard content.
- Verify peer addon-data delivery with a second real RIFT client.
- Investigate a genuine social-chat receive/send bridge; addon data alone does not meet the product goal.
