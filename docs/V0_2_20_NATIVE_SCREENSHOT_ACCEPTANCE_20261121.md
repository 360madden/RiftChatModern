# RCM v0.2.20 — Physical screenshot and managed-focus acceptance

**Observation date:** November 21, 2026 · America/New_York

**Verified host:** AMD-DESKTOP · **RIFT process:** `rift_x64` PID 37676 at time of test

**RIFT main window:** HWND `0x360BC4`, class `TWNClientFramework`, title `RIFT`

## Result

**RCM v0.2.20 is visibly running inside the physical RIFT client.**

The native RIFT screenshot shows the RCM version label `v0.2.20`,
turquoise/teal outlined glass panels, active-tab styling, colored message
markers, a local input box, and the focus label `INPUT • NOT FOCUSED`.
The screenshot is **not** a rendered illustration or an offline mock.

RIFT's actual game screenshot key is **Numpad Multiply (`*`)**. It saves
JPEGs under the `Screenshots` directory configured by `Rift.cfg`.

## Two physical screenshot receipts

| Receipt | 7:07 AM EST | 7:13 AM EST |
|---|---|---|
| Screenshot filename | `2026-11-21_070741.jpg` | `2026-11-21_071335.jpg` |
| Dimensions | 2560 × 1369 | 2560 × 1369 |
| Size | 2,027,487 bytes | 2,044,137 bytes |
| SHA-256 | `816d37555cf6b0631e2434187a1f15399c6daa0a88d2b2d55612709db20c6784` | `081f906c62530ac70db18482dee0cfc33e7a314c0382fb91c0d48f06446fd262` |
| Foreground acquired | Yes | Yes |
| One game screenshot keypair inserted | Yes | Yes |
| Prior foreground restored | Yes | Yes |
| Screenshot file independently validated | Yes, after the initial helper had returned an error | Yes, within the helper |
| Incomplete-file validation retries | Initial helper failed immediately | 1 retry; successful |

**Evidence boundary:** insertion of Windows keyboard events alone is not
proof of game consumption. In these runs, new time-correlated complete JPEGs
were found in the actual configured RIFT screenshots directory and the image
content visibly matches RIFT with the v0.2.20 RCM window. Neither the
screenshot nor the process/window checks prove that ordinary native social
chat has been captured or transmitted. The screenshots do not prove that
every button and resize path has passed live interactive acceptance.

The user-visible native game image still includes character-identifying
text, so **no unblurred screenshot was committed or uploaded to GitHub**.
The existing privacy-redacted historical v0.2.2 README image is separate.

## Root-cause fix: screenshot file writing race

The original `tools/rcm_screenshot_once.py` called
`rcm_game_screenshot_receipt.inspect_folder` immediately after sending
the screenshot key. A new JPEG filename may become visible before RIFT
finishes writing a complete image. The strict complete-file validator then
raises `ScreenshotReceiptError`.

The orchestrator formerly reported `new_image_verification_failed`
**immediately**, even though the JPEG would become readable moments later.
The fix retries **read-only file validation** within its existing finite
`--wait-ms` window. It **never retries the keyboard keypress** and
retains `gameInputSent=true` for any uncertainty after insertion. A
persistently corrupted or invalid image still fails closed.

Two added tests verified the prior failure and the corrected behavior:
transient incomplete JPEG becomes valid with exactly one game input, and
persistent invalid JPEG never receives a successful receipt.

## Managed temporary focus

`tools/rcm_focused_screenshot_once.py` is a new workstation-only
convenience wrapper. It reuses:

1. RCM's existing `RcmScreenshotKey` read-only process/epoch/executable
   inspection.
2. The **proven attach-first focus method** in the sibling
   `C:\work\Rift-Personal-Teleporter\src\python_win32_input.py`
   (`Win32Input._focus`). No replacement Win32 input engine.
3. The existing RCM `rcm_screenshot_once.execute` exactly-once key
   insertion and independent image receipt.
4. Restoring the previous HWND after completion or failure. If another
   application independently takes foreground mid-capture, the wrapper
   does **not** override that newer choice.

From PowerShell on AMD-DESKTOP, in `C:\work\RiftChatModern`:

```powershell
# Inspect the game without changing focus or sending input
& "C:\work\riftreader2\.venv\Scripts\python.exe" -B tools\rcm_focused_screenshot_once.py --expect-host AMD-DESKTOP --dry-run

# Explicitly authorized one-shot foreground -> screenshot -> restore
& "C:\work\riftreader2\.venv\Scripts\python.exe" -B tools\rcm_focused_screenshot_once.py --expect-host AMD-DESKTOP --capture --ack-temporary-focus --ack-single-screenshot --wait-ms 8500
```

If multiple RIFT clients exist, add `--pid` with a **fresh verified**
client PID; never guess which one owns the desired character.

## Automated regressions

- `tests/test_screenshot_once.py`: transient-then-complete and persistent
  incomplete-file behavior, no key retries, existing screenshot guards.
- `tests/test_focused_screenshot_once.py`: exact client selection,
  intentional focus and restore, dry-run no-focus, error paths, preserved
  external focus, and no false-positive screenshot success.
- **278 Python/Lua and 58 Node tests passed** on November 21, 2026,
  including the new managed-focus and incomplete-JPEG cases.

## Remaining physical acceptance

The game image proves the new skin is in use. Direct physical clicking,
hovering, resizing, and editor typing still deserve a separate in-game
interaction trial; **no successful ordinary player Say/Guild/Party/Tell
send/receive pathway is claimed**.

This run did not restart RIFT, change client configuration, modify
SavedVariables, or rewrite the screenshot image.
