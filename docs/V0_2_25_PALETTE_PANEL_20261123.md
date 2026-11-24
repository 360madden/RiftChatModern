# RCM v0.2.25 — Graphical channel palette and visibility

**Date:** November 23, 2026 (EST) · **Host:** LEGION · **Base commit:** `21873594bd18d2349151b1f9a6bd69b4b99fe6ee`

**Evidence:** Lua 5.1/RIFT API mock acceptance only. The v0.2.25 source build has not been deployed to a physical RIFT client. AMD-DESKTOP remains unreachable; v0.2.23 remains the last physically verified baseline. No native social-chat capability is implied by a presentation category.

## Operator workflow

1. Open RCM and click **COLORS** in the right-side navigation rail (or enter `:color panel` in RCM / `/rcm color panel` in original chat).
2. The history card becomes an exclusive settings view. **PREV / NEXT** pages through all 15 fixed categories, six per page. Click a category's colored swatch/card to select it.
3. Edit its six-digit RGB hex value. The preview immediately uses the same color validation as the model. Nothing is saved while typing.
4. Click **APPLY** (or Enter in the focused hex field) to update the selected color. **DEFAULT** restores just that color; **RESET COLORS** restores all color defaults.
5. **HIDE ROWS / SHOW ROWS** toggles the selected category in RCM's history view. **SHOW ALL** restores visibility for all categories. Neither action deletes or changes a message, token, sender, or provenance.
6. Close the panel to return to history. The native subscription inspector and message detail reader never display simultaneously with the palette. The chat draft survives opening, closing, resizing, and selecting another view. Opening settings does not acquire chat input focus.

If the window is too small for the panel, it is closed and the command path remains available:
- `:color set host_public #F0E080`
- `:color visible host_public off` / `:color visible host_public on`
- `:color showall` restores visibility without changing colors.

## Model, API and save contract

`channelColors` remains a sparse map of nondefault uppercase hex strings. The optional `hiddenChannels` table stores only known keys whose visibility is explicitly false (stored as true in the hidden map). Both are character-local presentation preferences. Malformed optional fields are repaired independently of valid history and transfer tokens; history schema stays at 2.

The additive API v2 methods are:
- `GetChannelVisibility()`: fresh map of visible booleans, not the saved hidden table.
- `SetChannelVisible(key, visible)`: true or nil/error, with strict boolean validation.
- `ResetChannelVisibility()`: restores all categories.
- Existing palette methods remain compatible.

The **on-screen history, paging, search results and Copy History** respect visibility. Existing API `GetHistory`, retained-ID lookup, subscriptions, import token reconciliation, and save checkpoints still include retained messages. Explicit history clear retains its existing destructive semantics; the CLEAR button is blocked while the settings panel is open. Host/native provenance labels do not change.

The graphical view uses existing RIFT frame, text, textfield and button primitives. Color previews and actual message rendering share the same validated RGB conversion. No additional game API or new startup module is required. The existing detail-reader builder was extracted from the oversized UI initializer after the first Lua 5.1 compile test exposed its 60-upvalue ceiling. This preserves its behavior while reducing the initializer's captured-local count.

## Verification

Eleven focused tests passed: visibility persistence and no-ops, malformed settings repair, hidden history/token retention, view/export agreement, validated nonmutating previews, draft/focus preservation, swatch selection, apply/reset/invalid values, exclusive view switching, geometry at three normal sizes, and small-viewport fallback. Keyboard Enter requires confirmed palette input focus.

Final full regression: **341 Python/Lua + 129 Node = 470 passed, zero failures or skips**. Python/Lua completed in 39.797s; Node completed in 6.840s. Git diff check passed. All startup scripts compiled and executed in Lua 5.1. No physical game/deployment acceptance is implied.

## Physical acceptance still required

On the verified AMD-DESKTOP workstation: confirm the active addon directory and source hashes, deploy v0.2.25 with the guarded installer, use native `/reloadui`, and verify startup/version in RIFT. Capture genuine screenshots of COLORS at minimum/default/large sizes. Change and reset a category, hide and restore a retained host row, verify no duplicate or deleted history, and independently audit the real character save after reload. Recheck logout/login persistence and keyboard focus. Do not mark RCM-053 physically complete until this evidence is recorded.

The critical-path M1 public-channel import is still pending live game evidence.
