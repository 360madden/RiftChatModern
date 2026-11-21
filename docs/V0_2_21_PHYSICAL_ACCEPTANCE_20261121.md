# RCM v0.2.21 — Physical in-game UI acceptance

**Date:** November 21, 2026 · **Host:** AMD-DESKTOP

**Repository:** `C:\work\RiftChatModern` · **RIFT:** `rift_x64` PID 37676 (session-specific)

## Scope and evidence

This cycle is a **real physical RIFT acceptance**, not simulated GUI output.
Source and installed-addon checksums were verified by the guarded deployer.
RIFT restarted **zero** times: the native `/reloadui` command reloaded Lua
and `/rcm` opened the window.

The original native RIFT chat explicitly displayed:
`RiftChatModern v0.2.21 | Loaded. /rcm opens the console. Version 0.2.21`.

### Real image receipts

| RIFT-created screenshot | Observed result | SHA-256 |
|---|---|---|
| `2026-11-21_084621.jpg` | v0.2.21, four message columns, local timestamps to seconds, readable teal glass UI | `b710bc6a5d3bd2941e9504774a9658e999b2d107f26a1930f1d3de6617acc2bb` |
| `2026-11-21_084818.jpg` | Click on **DEV** successfully selects tab, zero Dev messages | `cd70a0480d7cf159d19a17bb91f87247e046e15fe68b2e29358f46ad8c8ce71b` |
| `2026-11-21_085003.jpg` | Click on **ALL** restores full history list | `fe6a1ada9715c173d29730b9418b6176e1e7d9adc4578b3377dadf02cac120ba` |
| `2026-11-21_085056.jpg` | **Failed:** details title/body/buttons visually overlap active history rows | `2da1bffcd13e4bc6655d8456d2b0e32966c06d8d92715489a7f18faa2506a082` |
| `2026-11-21_085617.jpg` | **Failed:** hiding rows plus setting modal layer 40 hid details text and buttons behind backdrop | `0903c3fc3403c49db938ee1b80d27503fee6f0aa75d9c66680f07a9dc3771ebc` |
| `2026-11-21_085851.jpg` | **Passed:** modal shows detail title, full body, Copy/Prev/Next/Page/Close controls, no history glyph bleed | `678e07f5f42f9cfa5ba7edce8e6a4618d7a651e87e8e2fee67ad5017bba44a42` |
| `2026-11-21_085942.jpg` | **Passed:** clicking CLOSE restores populated ALL-tab history rows, footer and normal layout | `0090f3d99a045efdb5ea239c3cf3b33e7d24ff816cc8cd670627274978387a3c` |

All images were written by RIFT itself under its configured OneDrive
`Documents\RIFT\Screenshots` directory as complete **2560 × 1369 JPEGs**.
The hashes above are independently inspected file receipts.

**Privacy:** Raw images contain real character-identifying labels and chat
content. Do not publish them to GitHub as-is. The public historical README
screenshot remains the separately redacted v0.2.2 image.

## Main work: chat-like message columns

The previous single padded text string is replaced with four independently
styled fields per row:

- local `HH:MM:SS`, preserving the stored timestamp;
- provenance-aware channel label (`[SYSTEM]`, `[ADDONS]`, `[HOST/GUILD]`),
  separately colored;
- sender/source, separately truncated;
- full-width message preview, with the existing open/copy full-body reader.

The screenshot independently demonstrates the four-column layout and
preserved message history. Ordinary native Say/Guild/Party/Tell
sending/reception is **still not verified**.

## Root-cause bug hunt: message reader overlay

The first physical click into a message on v0.2.21 exposed a defect missed
by the old mock tests. RIFT permitted history row siblings and the
detail overlay to render in an undefined same-layer order, leading to
overlapping text and competing click hitboxes.

A first proposed fix hid background rows, moved the modal parent to layer
40, and retained a dark background. That removed history bleed but pushed
the detail children below the parent's new layer, rendering a blank modal
surface. This exact failed physical result was captured.

The corrected design:

1. **Treat details as a modal state.** Hide history row surfaces while
   a selected message is open, including after resize or live history
   updates. Restoring/closing re-shows only currently valid rows.
2. **Preserve working child layers.** The detail texture remains at
   its original negative layer (`-8`) below title, body, and buttons.
   Do **not** raise the parent above its children.
3. **Keep a dark fallback background** independent of texture loading.
4. Add tests that first failed against the prior implementation, then
   passed: modal row isolation, no hitbox overlap while resizing, full
   detail body/copy access, and clean restoration on Close.

This is the root-cause fix, **not a cover-up by trimming message text**.

RIFT generated native image receipts for opening the corrected modal
and closing it with the content restored.

## Native chat interaction and screenshot automation

An initial scan-code command helper silently failed to submit `/reloadui`;
later Numpad screenshot presses entered `**` into the native chat textbox.
Read-only screen inspection exposed the issue.

`tools/rcm_native_slash_once.py` was corrected to send **virtual-key Enter**
and **Unicode keyboard text**, using the same event formats already
validated by the RCM editor sender. The narrow repair flow cleared the
two `**` characters, submitted `/reloadui`, and real native chat
provided the version receipt.

All later commands used exact RIFT process identity, the verified
attach-before-foreground backend from the existing local helper, and
short, bounded input. A successful SendInput call alone was never counted
as game acceptance. Fresh native screenshots were required to qualify
the UI state.

## Validation and release boundary

- **297 Python/Lua tests passed** and **58 Node tests passed** after
  the modal root fix.
- Verified source and installed addon: 22 file package, new v0.2.21 code;
  `Main.lua` re-deployed after fixes with a recoverable backup.
- Existing character SavedVariables were not deleted or modified by
  deployment, and no RIFT game restart occurred.
- Tab switching, four-column visual structure, modal opening and closing
  were physically observed inside RIFT.

**Still pending:** real-world drag/resize interaction proof,
editor focus/typing/clipboard receipts, channel color editing, and
native social-chat transport discovery. Native screen images do not
establish those unrelated features.

**Foreground caveat:** The screenshot helper sometimes reports
`restoredPreviousForeground=false` when Windows declines focus restoration.
This is a real unresolved Windows focus receipt, not evidence that RIFT
failed to save the screenshot. Do not report restoration success for
those individual trials.
