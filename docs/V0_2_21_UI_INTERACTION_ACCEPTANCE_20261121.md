# RCM v0.2.21 — Physical drag, resize, editor and persistence acceptance

**Date:** November 21, 2026 · **Host:** AMD-DESKTOP

**Code baseline:** RCM v0.2.21 · **Game:** physical RIFT Live client

**Canonical repo:** `C:\work\RiftChatModern`

## Why this run

The prior [v0.2.21 physical acceptance](V0_2_21_PHYSICAL_ACCEPTANCE_20261121.md)
qualified four-column rendering, tab changes, and message-details
open/close. The next unqualified high-impact behaviors were direct window
drag/resize, editor focus and keyboard submission, and state persistence
after `/reloadui`.

This report uses real RIFT game screenshots and an independent read-only
SavedVariables disk inspection. No RIFT client restart was performed.
Native social Say/Guild/Party/Tell delivery remains a separate unproven
capability.

## Real client input and observations

| Operation | Direct evidence | Result |
|---|---|---|
| Title drag | Physical focused mouse-down, six short move steps, key-up; native screenshot `2026-11-21_100306.jpg` | **Passed**: window moved left and up by the requested approximate 105×62 pixels |
| First grip trial | Native `2026-11-21_100415.jpg` | **No resize**: press was slightly above the actual grip |
| Second grip trial | Native `2026-11-21_100534.jpg` | **No resize**: a further erroneous Windows-title-bar correction placed the press too high |
| Correct grip center | Native `2026-11-21_100718.jpg` | **Passed**: exact client grip center (2409,1060), approximately 70×62 increase; wider responsive layout and more visible rows |
| Editor focus | Physical **FOCUS INPUT** click and contemporaneous read-only desktop image | **Passed**: green `INPUT • FOCUSED` and focus-specific footer |
| Editor typing/submit | 24 Unicode characters plus virtual-key Enter, single controlled focus session | **Passed**: local `:echo RCM_FOCUS_20261121` created a `[DEV]` / `Console` history row and cleared the editor |
| RIFT UI reload | Native `/reloadui` and `/rcm`; RIFT-created `2026-11-21_101443.jpg` | **Passed**: same relocated/resized UI, ALL filter and DEV canary history row returned |
| Independent on-disk SavedVariables | Read-only inspection of the character-scoped `RiftChatModern.lua` | **Passed**: on-disk `ui={x=1547,y=364,w=952,h=775}` and exact DEV canary text present |

### Screenshot file checksums

These files are private native RIFT JPEGs stored in the game's configured
Screenshots directory, not GitHub assets:

| Filename | SHA-256 |
|---|---|
| `2026-11-21_100306.jpg` | `afdc06195016d41c57372f02954922346556699a55854ef1257e8e1c8a58a538` |
| `2026-11-21_100415.jpg` | `dd6dd4d0ccf1e1c3aea2cd63edc3c3a3ed5d2fda7e35facd5805757ec8bdad70` |
| `2026-11-21_100534.jpg` | `02407b5b769c0ca83a8484272b7baaa5bddedd5a4a67830e5f01e9455cde9d1d` |
| `2026-11-21_100718.jpg` | `4a7c751e64179b8907ce56278dda772c8ec9bb0c81c7df5a934128f50258cab5` |
| `2026-11-21_101443.jpg` | `607acec1d8e64449e4c321540781caa009f63514987ca313a4dd388b4ca227da` |

The independent SavedVariables file was 21,474 bytes at observation,
SHA-256 `5e51a9f3bf7dee0013a45824fa48fe2a324b1e76034a89fcc13abc96d41c9fd4`.
The file content was not copied into the repo or published.

### Reproducible on-disk geometry audit

Extended the existing privacy-conscious `tools/rcm_disk_receipt.py` with
`--require-ui-geometry X,Y,W,H`. It uses the project's established masked
Lua string/comment scanner and top-level table-depth validation; it never
executes SavedVariables Lua and does not print message bodies.

PowerShell invocation from the repository, replacing the placeholder with
the actual character-scoped `RiftChatModern.lua` file:

```powershell
& "C:\work\riftreader2\.venv\Scripts\python.exe" -B tools\rcm_disk_receipt.py --expect-host AMD-DESKTOP --file "PATH_TO_RIFT_SAVEDVARIABLES\RiftChatModern.lua" --require-ui-geometry 1547,364,952,775
```

The live CLI audit returned `requiredUiGeometryMatched=true`,
`uiGeometryComplete=true`, `diskReceiptVerified=true`,
`checkpointMetadataConsistent=true`, `historyRowsOnDisk=110` and
`savedVariablesModified=false`. A wrong requested geometry fails with a
nonzero exit code rather than silently accepting it. Fixture regression
tests cover absent/partial fields, forged text, duplicate tables and
invalid numeric arguments.

## Correct diagnosis of the apparent resize failure

The earlier failed grips were **test-coordinate errors**, not demonstrated
RCM addon bugs. A close-up of the genuine RIFT JPEG put the visual grip
center at *client-local* (2409,1060). RIFT's own screenshots are already
client-local; the Windows title bar offset must **not** be subtracted when
reusing those screenshot pixel coordinates as `send_left_click` client
coordinates.

With that correction, the exact same Lua resize path worked immediately.
The addon was **not modified** to compensate for the erroneous inputs.

## Focus restoration — verified root-cause improvement

RCM's host screenshot and native-slash helpers had sometimes recorded
`restoredPreviousForeground=false` with HWND `0x0` immediately after
`SetForegroundWindow(previous)`. A following tool call observed that the
original window had already returned to foreground. This is the normal
short transient where Windows reports no active foreground while the
handoff settles; an immediate single read falsely reports failure.

The two host helpers now use one bounded read-only
`_observe_foreground_restore` function. It polls for at most 500 ms:

- **Previous HWND observed:** report success.
- **Different third-party foreground:** preserve that selection; no
  forced reactivation.
- **Still game/NULL after deadline:** report unresolved, not success.
- Only if the original game is still foreground after the wait may
  the established attach-first recovery be attempted.

Two additional tests reproduced the old false negative before the fix,
then passed. A real no-game-input Windows focus session returned the
exact original foreground HWND with `settled_to_previous`; later
`/reloadui` and native screenshot sessions returned
`restoredPreviousForeground=true` and the same observation.

No arbitrary keyboard input, mouse events or game actions are required
to test this foreground-only restoration.

## Updated public GitHub screenshot — privacy

The homepage is refreshed with a real **v0.2.21** image, not the prior
v0.2.2 historical photo. The public file is:

`assets/screenshots/rcm-v0.2.21-live-ui-cropped.jpg`

It is a 992×820 JPEG cropped at `(1523,342,2515,1162)` from the verified
native `2026-11-21_101443.jpg` image (2560×1369). Public crop SHA-256:
`a0baff2c0bb776d0913a09aa259ad141ee51c98cb9b484aecbdd0eabe3585124`.

The crop contains the actual v0.2.21 RCM window and nearby game backdrop.
The character-name HUD, portrait, telemetry and original native chat are
outside the crop. The historical v0.2.2 redacted screenshot is retained
for reference.

## Remaining acceptance work

- Real clipboard copy, including safe preservation of the operator's
  existing clipboard content: **not tested**.
- A full save/logout/relogin cycle: **not tested**; `/reloadui` persistence
  **and the independent on-disk geometry/history record were verified**.
- Dragging/resizing repeated at minimum/maximum window sizes: mocked
  tests passed, full physical boundary suite still pending.
- Native player Say/Guild/Party/Tell capture and transmission:
  **not established**.

**Final regression result:** 303 Python/Lua tests and 58 Node tests passed; the installed 22-file RCM v0.2.21 package hash-matched its source with zero pending copies.

This cycle changed **host tools, tests, docs and the public screenshot**.
The tested and installed RCM Lua addon remains v0.2.21; no version bump
was needed solely for host workflow or README work.
