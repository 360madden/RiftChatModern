r"""Temporarily focus an exactly identified RIFT client, take ONE native screenshot,
then restore the previous foreground window.

Development workstation helper. It reuses the proven attach-before-
SetForegroundWindow focus backend in C:\work\Rift-Personal-Teleporter and the
existing RCM screenshot key/receipt orchestrator. No duplicated SendInput code.

Explicit --capture --ack-temporary-focus --ack-single-screenshot is required
for actual focus change and input. Default --dry-run never changes focus.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys

import rcm_screenshot_once as screenshot

ROOT = Path(__file__).resolve().parents[1]
FOCUS_BACKEND = ROOT.parent / "Rift-Personal-Teleporter" / "src" / "python_win32_input.py"
SCHEMA = "RCM_FOCUSED_NATIVE_SCREENSHOT_V1"


def _focus_backend():
    if not FOCUS_BACKEND.is_file():
        raise RuntimeError("proven_focus_backend_not_installed")
    # Import from the sibling repository without copying/reimplementing
    # the native focus and scan-code methods into RCM.
    sys.path.insert(0, str(FOCUS_BACKEND.parent))
    from python_win32_input import Win32Input
    return Win32Input()


def _inspect(pid: int | None):
    dotnet = shutil.which("dotnet")
    if not dotnet or not screenshot.TRIGGER_DLL.is_file():
        raise RuntimeError("native_screenshot_trigger_not_available")
    cmd = [dotnet, str(screenshot.TRIGGER_DLL), "--inspect"]
    if pid is not None:
        cmd.extend(("--pid", str(pid)))
    rc, identity = screenshot._invoke(cmd, subprocess.run)
    if rc != 0:
        raise RuntimeError("rift_inspection_failed_" + str(identity.get("status")))
    screenshot._pin_from_inspection(identity, socket.gethostname())
    return identity


def execute(argv: list[str] | None = None, *,
            inspector=None, backend=None, shot=None,
            hostname=None) -> tuple[int, dict]:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--capture", action="store_true")
    parser.add_argument("--expect-host", required=True)
    parser.add_argument("--pid", type=int)
    parser.add_argument("--ack-temporary-focus", action="store_true")
    parser.add_argument("--ack-single-screenshot", action="store_true")
    parser.add_argument("--wait-ms", type=int, default=8500)
    args = parser.parse_args(argv)

    host = hostname or socket.gethostname()
    if args.expect_host.casefold() != host.casefold():
        return 1, {"schema": SCHEMA, "status": "refused",
                   "reason": "wrong_host", "gameInputSent": False,
                   "focusChanged": False}
    if (args.capture != args.ack_single_screenshot or
        args.capture != args.ack_temporary_focus):
        return 1, {"schema": SCHEMA, "status": "refused",
                   "reason": "capture_requires_both_acks",
                   "gameInputSent": False, "focusChanged": False}
    if args.pid is not None and args.pid < 1:
        return 1, {"schema": SCHEMA, "status": "refused",
                   "reason": "invalid_pid", "gameInputSent": False,
                   "focusChanged": False}
    if not 0 <= args.wait_ms <= 12000:
        return 1, {"schema": SCHEMA, "status": "refused",
                   "reason": "invalid_wait_ms", "gameInputSent": False,
                   "focusChanged": False}

    inspect = inspector or _inspect
    session = shot or screenshot.execute
    try:
        identity = inspect(args.pid)
        if (not isinstance(identity, dict) or
            identity.get("status") != "read_only_target_candidate" or
            identity.get("machine", "").casefold() != host.casefold()):
            raise RuntimeError("exact_rift_identity_unverified")
        if args.pid is not None and identity.get("pid") != args.pid:
            raise RuntimeError("rift_pid_mismatch")
        screenshot._pin_from_inspection(identity, host)
    except Exception as exc:
        return 2, {"schema": SCHEMA, "status": "refused_before_focus",
                   "reason": str(exc), "gameInputSent": False,
                   "focusChanged": False}

    session_args = ["--expect-host", host, "--pid", str(identity["pid"])]
    if args.dry_run:
        # The underlying screenshot key guard requires foreground, but the
        # whole purpose of THIS helper is to acquire that foreground on apply.
        # An exact identity is sufficient for a useful read-only preview.
        return 0, {"schema": SCHEMA, "status": "ready_to_focus_no_input",
                   "inspection": {"pid": identity["pid"],
                                  "hwnd": identity["hwnd"],
                                  "foreground": identity.get("foreground")},
                   "gameInputSent": False, "focusChanged": False}

    try:
        focus = backend or _focus_backend()
    except Exception as exc:
        return 2, {"schema": SCHEMA, "status": "focus_backend_unavailable_no_input",
                   "reason": str(exc), "gameInputSent": False, "focusChanged": False}
    previous: int | None = None
    target_hwnd: int | None = None
    changed = False
    was_iconic = False
    result: dict = {"schema": SCHEMA, "status": "capture_not_attempted",
                    "inspection": {"pid": identity["pid"],
                                   "hwnd": identity["hwnd"]},
                    "gameInputSent": False, "focusChanged": False,
                    "restoredPreviousForeground": False}
    code = 2
    try:
        target = {"pid": identity["pid"], "hwnd": identity["hwnd"],
                  "title": "RIFT"}
        target_hwnd, target_pid = focus._validate_target(target)
        previous = int(focus.get_foreground() or 0)
        was_iconic = bool(focus.is_iconic(target_hwnd))
        changed = previous != target_hwnd
        # A minimized DirectX client needs more than the usual quarter-second
        # to restore its renderer before RIFT will handle Numpad Multiply.
        focus_receipt = focus._focus(target_hwnd, target_pid,
                                    1250 if was_iconic else 250)
        result["focusReceipt"] = focus_receipt
        result["focusChanged"] = changed
        code, screenshot_receipt = session([
            *session_args, "--capture", "--ack-single-screenshot",
            "--wait-ms", str(args.wait_ms),
        ])
        result["screenshot"] = screenshot_receipt
        result["gameInputSent"] = screenshot_receipt.get("gameInputSent")
        verified = code == 0 and screenshot_receipt.get("screenshotFileVerified") is True
        result["status"] = "capture_verified" if verified else "capture_inconclusive"
        if not verified and code == 0:
            code = 2  # no verified image means no successful capture receipt
    except Exception as exc:
        result["status"] = "capture_or_focus_exception"
        result["reason"] = str(exc)
        # Do not claim no game input if the screenshot session could have
        # started before an exception.
        if changed:
            result["gameInputSent"] = None
        code = 2
    finally:
        # The operator explicitly asked to return to their prior foreground.
        # Never overwrite a NEW foreground that appeared while RIFT was active.
        try:
            current = int(focus.get_foreground() or 0)
            result["foregroundAtRestoreCheck"] = f"0x{current:X}"
            if previous is None:
                result["restoreStatus"] = "no_prior_foreground_recorded"
            elif previous == target_hwnd:
                result["restoredPreviousForeground"] = current == previous
                result["restoreStatus"] = "rift_was_already_foreground"
            elif current != target_hwnd:
                result["restoreStatus"] = "external_focus_change_preserved"
                result["restoredPreviousForeground"] = current == previous
            elif focus.is_window(previous):
                focus._restore(previous, target_hwnd)
                after_restore = int(focus.get_foreground() or 0)
                if after_restore == target_hwnd:
                    # Retry the proven attached-thread focus only if RIFT
                    # still owns foreground. Never steal a third application's
                    # newly acquired focus.
                    previous_thread, previous_pid = focus._owner(previous)
                    if previous_thread and previous_pid:
                        focus._focus(previous, previous_pid, 250)
                result["restoredPreviousForeground"] = (
                    int(focus.get_foreground() or 0) == previous
                )
                result["restoreStatus"] = ("restored" if result["restoredPreviousForeground"]
                                           else "restore_unverified")
            else:
                result["restoreStatus"] = "previous_window_no_longer_exists"
            # Restore an originally minimized RIFT window only after leaving
            # its foreground. A new user-selected foreground is never stolen.
            if (was_iconic and previous != target_hwnd and
                int(focus.get_foreground() or 0) != target_hwnd and
                focus.is_window(target_hwnd)):
                focus.show_window(target_hwnd, 6)  # SW_MINIMIZE
                result["minimizedStateRestored"] = bool(focus.is_iconic(target_hwnd))
        except Exception as exc:
            result["restoreStatus"] = "restore_exception"
            result["restoreReason"] = str(exc)
        result["originalForegroundHwnd"] = f"0x{previous:X}" if previous else None
        result["foregroundAfter"] = f"0x{int(focus.get_foreground() or 0):X}"
    return code, result


def main(argv=None):
    try:
        code, receipt = execute(argv)
    except Exception as exc:
        code, receipt = 2, {"schema": SCHEMA, "status": "unhandled_before_receipt",
                            "reason": str(exc), "gameInputSent": None}
    print(json.dumps(receipt, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
