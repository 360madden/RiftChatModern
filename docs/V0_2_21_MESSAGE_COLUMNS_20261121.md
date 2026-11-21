# RCM v0.2.21 — Message presentation refactor

**Date:** November 21, 2026

**Machine:** AMD-DESKTOP · **Repository:** `C:\work\RiftChatModern`

**Game target:** RIFT Live, Lua 5.1, manifest Environment 4.3

## Problem

In the verified v0.2.20 native screenshot, all rows were a single
space-padded `Text` element:

```text
21:54  SYSTEM        Game alert    Rifts from the Planes...
```

That prevented independently styling the timestamp, category, sender, and
message. It also dropped seconds from locally formatted timestamps and
reserved fixed-width text padding rather than using the remaining space
adaptively.

## Root-cause correction

Each message now uses **four separate, read-only text frames** plus the
existing clickable row surface and slim channel-color marker.

| Column | RIFT text frame per row | Format |
|---|---|---|
| Time | `RCMLineTimeN` | Local `HH:MM:SS`, read from the retained epoch |
| Kind/channel | `RCMLineChannelN` | Bracketed kind, e.g. `[SYSTEM]`, `[ADDONS]` |
| Sender/source | `RCMLineSenderN` | Independently truncated source |
| Message preview | `RCMLineTextN` | UTF-8 bounded, expands with window width |
| Color marker | `RCMLineMarkerN` | Channel-specific accent |

This is a rendering-only schema-preserving change. The history model,
`GetHistory`, `Copy`, `CopySelectedMessage`, search, pagination, import
deduplication, editor commands, and saved window placement retain their
existing semantics.

**Provenance is never omitted:** a manually imported Guild candidate is
rendered `[HOST/GUILD]`, not `[GUILD]`. Ordinary native social-chat
reception or sending remains independently unverified.

The frame model also preserves the ability to click an entire row to open
the full message, even if its single-line preview is truncated.

## Responsive layout

The message row remains 24 pixels high, retaining existing viewport row
counts and scroll behavior. The local time and channel columns keep their
positions; sender width compresses at the minimum supported window width
so the message body still receives the remaining horizontal space.

Each frame has its own color and size while staying inside the actual row
parent. Content is never modified in SavedVariables to accommodate layout.

## Verification

- Dedicated Lua 5.1 tests: complete timestamp format, four independent
  fields, explicit host-import provenance, 680×480/760×618/1100×800
  containment without overlapping columns, long-message detail/copy,
  empty-row cleanup after filter changes, and time formatting fallback.
- Existing integration tests updated only where their expected UI field
  semantics changed.
- **Physical v0.2.21 screenshot accepted:** native RIFT initialization and
  real 2560×1369 JPEG display of local seconds, channel/sender/body fields,
  active tab styling and readable message density.
- A real in-game message click exposed sibling-history/reader overlap.
  This was fixed by hiding history row surfaces while details are open and
  preserving the prior working texture/child layer order. The first layer
  override also failed physically and its failure is preserved in the
  [full physical acceptance report](V0_2_21_PHYSICAL_ACCEPTANCE_20261121.md).
- The corrected reader and Close restored content were independently
  accepted via additional native screenshots. The success of these
  interactions does not establish native social-chat reception.

## Physical acceptance status

1. **Passed:** v0.2.21 is installed and was loaded with `/reloadui`; no game restart.
2. **Passed:** four distinct message fields and timestamp seconds visible.
3. **Passed:** DEV and ALL tab click/selection in the physical RIFT UI.
4. **Passed after root-cause repair:** modal details show complete content
   with no overlapping history; Close restores rows. Both states captured
   using RIFT's own Numpad Multiply screenshot key.
5. **Still pending:** physical input focus, editor text entry, drag and resize,
   saved-geometry reload, clipboard effects and social chat send/receive.

See [physical receipts and root-cause history](V0_2_21_PHYSICAL_ACCEPTANCE_20261121.md).

No unblurred screenshot containing character names should be published to
GitHub. The historical README screenshot remains explicitly labeled v0.2.2.
