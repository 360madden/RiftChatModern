"""One-command, exactly pinned RIFT native screenshot trial.

Default --dry-run is read-only. --capture needs --ack-single-screenshot and
can issue exactly ONE VK_MULTIPLY down/up through the separate .NET helper.
No focus changes, clipboard operations, game memory access, or file writes
are performed by this Python program. RIFT itself may write a JPEG.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time

from rcm_game_screenshot_receipt import (
    ScreenshotReceiptError,
    _inside_windows_config,
    inspect_folder,
)

ROOT = Path(__file__).resolve().parents[1]
TRIGGER_DLL = ROOT / "tools" / "RcmScreenshotKey" / "bin" / "Release" / "net10.0-windows" / "RcmScreenshotKey.dll"
SHA256_RE = re.compile(r"\A[0-9A-F]{64}\Z")


class SessionError(ValueError):
    pass


class SessionParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise SessionError(message)


def _invoke(args: list[str], runner) -> tuple[int, dict]:
    try:
        result = runner(args, capture_output=True, text=True,
                        encoding="utf-8", errors="replace", timeout=30,
                        check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SessionError("dotnet_helper_unavailable_or_timed_out") from exc
    try:
        response = json.loads(result.stdout.strip())
    except (ValueError, AttributeError) as exc:
        raise SessionError("invalid_dotnet_helper_receipt") from exc
    if not isinstance(response, dict) or response.get("schema") != "RCM_GAME_SCREENSHOT_TRIGGER_V1":
        raise SessionError("unexpected_dotnet_helper_schema")
    return result.returncode, response


def _pin_from_inspection(report: dict, host: str) -> list[str]:
    if report.get("status") != "read_only_target_candidate" or (
        report.get("machine", "").lower() != host.lower()
    ):
        raise SessionError("no_verified_exact_rift_window")
    pid, hwnd, ticks = report.get("pid"), report.get("hwnd"), report.get("startUtcTicks")
    sha, exe = report.get("exeSha256"), report.get("exePath")
    if (not isinstance(pid, int) or pid < 1 or not isinstance(ticks, int)
        or ticks < 621355968000000000 or not isinstance(hwnd, str)
        or not re.fullmatch(r"0x[0-9A-Fa-f]{1,12}", hwnd)
        or not isinstance(sha, str) or not SHA256_RE.fullmatch(sha)
        or not isinstance(exe, str) or not Path(exe).is_absolute()):
        raise SessionError("malformed_rift_process_identity")
    return ["--expect-host", host, "--pid", str(pid),
            "--hwnd", hwnd, "--start-ticks", str(ticks),
            "--exe-path", exe, "--exe-sha256", sha]


def execute(argv: list[str] | None = None, *,
            command_runner=None, file_checker=None, config_resolver=None,
            clock_ns=None, sleep=None) -> tuple[int, dict]:
    parser = SessionParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--capture", action="store_true")
    parser.add_argument("--ack-single-screenshot", action="store_true")
    parser.add_argument("--expect-host", required=True)
    parser.add_argument("--pid", type=int, default=None,
                        help="Required to choose one client if multiboxing")
    parser.add_argument("--arm-seconds", type=int, default=0)
    parser.add_argument("--wait-ms", type=int, default=5000)
    opt = parser.parse_args(argv)
    if opt.expect_host.lower() != socket.gethostname().lower():
        raise SessionError("wrong_host")
    if opt.capture != opt.ack_single_screenshot:
        raise SessionError("capture_requires_explicit_ack")
    if opt.arm_seconds < 0 or opt.arm_seconds > 15:
        raise SessionError("arm_seconds_out_of_bounds")
    if opt.arm_seconds and not opt.capture:
        raise SessionError("arm_seconds_requires_capture")
    if not 0 <= opt.wait_ms <= 12000:
        raise SessionError("wait_ms_out_of_bounds")
    if opt.pid is not None and opt.pid < 1:
        raise SessionError("invalid_target_pid")

    dotnet = shutil.which("dotnet")
    if not dotnet or not TRIGGER_DLL.is_file():
        raise SessionError("dotnet10_trigger_not_built")
    runner = command_runner or subprocess.run
    checker = file_checker or inspect_folder
    resolver = config_resolver or _inside_windows_config
    now = clock_ns or time.time_ns
    snooze = sleep or time.sleep

    args = [dotnet, str(TRIGGER_DLL), "--inspect"]
    if opt.pid is not None:
        args.extend(("--pid", str(opt.pid)))
    read_rc, identity = _invoke(args, runner)
    if read_rc != 0:
        return 2, {"schema": "RCM_SCREENSHOT_SESSION_V1",
                   "status": "rift_inspection_not_ready",
                   "reason": identity.get("status"), "gameInputSent": False,
                   "screenshotFileVerified": False, "gameFocusChanged": False}
    pins = _pin_from_inspection(identity, opt.expect_host)
    action = "--capture" if opt.capture else "--dry-run"
    command = [dotnet, str(TRIGGER_DLL), action]
    if opt.capture:
        command.append("--ack-single-screenshot")
        if opt.arm_seconds:
            command.extend(("--arm-seconds", str(opt.arm_seconds)))
    command.extend(pins)
    action_rc, action_report = _invoke(command, runner)
    entered = action_report.get("gameInputSent")
    if opt.capture and action_rc == 0 and entered is True:
        baseline = action_report.get("baselineEpochNs")
        if not isinstance(baseline, int) or baseline < 1 or abs(now() - baseline) > 60_000_000_000:
            return 2, {"schema": "RCM_SCREENSHOT_SESSION_V1",
                "status": "invalid_capture_baseline_after_key",
                "reason": "invalid_capture_baseline_epoch",
                "gameInputSent": True, "screenshotFileVerified": False,
                "physicalRiftOriginVerified": False,
                "gameFocusChanged": False}
        config = Path(os.environ.get("APPDATA", "")) / "RIFT" / "Rift.cfg"
        try:
            folder = resolver(config)
        except (OSError, ScreenshotReceiptError):
            return 2, {"schema": "RCM_SCREENSHOT_SESSION_V1",
                "status": "image_source_unavailable_after_key",
                "reason": "screenshot_folder_unavailable",
                "gameInputSent": True, "screenshotFileVerified": False,
                "physicalRiftOriginVerified": False,
                "gameFocusChanged": False}
        deadline = time.monotonic() + opt.wait_ms / 1000
        while True:
            try:
                receipt = checker(folder, baseline)
            except (OSError, ScreenshotReceiptError):
                return 2, {"schema": "RCM_SCREENSHOT_SESSION_V1",
                "status": "new_image_verification_failed",
                "reason": "screenshot_file_unverifiable",
                "gameInputSent": True, "screenshotFileVerified": False,
                "physicalRiftOriginVerified": False,
                "gameFocusChanged": False}
            if receipt.get("status") == "new_screenshot_file":
                return 0, {
                    "schema": "RCM_SCREENSHOT_SESSION_V1",
                    "status": "new_post_key_image_verified",
                    "machine": opt.expect_host,
                    "pid": identity["pid"],
                    "hwnd": identity["hwnd"],
                    "baselineEpochNs": baseline,
                    "keyEventsInserted": action_report.get("keyEventsInserted"),
                    "screenshot": receipt["screenshot"],
                    "gameInputSent": True,
                    "screenshotFileVerified": True,
                    "gameWindowCorrelated": False,  # time/path coincidence is not origin proof
                    "physicalRiftOriginVerified": False,
                    "gameFocusChanged": False,
                }
            if time.monotonic() >= deadline:
                break
            snooze(0.1)
        return 2, {
            "schema": "RCM_SCREENSHOT_SESSION_V1",
            "status": "key_events_inserted_but_no_new_image",
            "pid": identity["pid"],
            "hwnd": identity["hwnd"],
            "baselineEpochNs": baseline,
            "gameInputSent": True,
            "screenshotFileVerified": False,
            "physicalRiftOriginVerified": False,
            "gameFocusChanged": False,
        }
    return (0 if action_rc == 0 and (not opt.capture or entered is True) else 2), {
        "schema": "RCM_SCREENSHOT_SESSION_V1",
        "status": ("inconsistent_capture_receipt" if opt.capture and action_rc == 0
                   and entered is not True else action_report.get("status", "action_inconclusive")),
        "pid": identity["pid"], "hwnd": identity["hwnd"],
        "gameInputSent": entered,
        "screenshotFileVerified": False,
        "gameFocusChanged": False,
        "physicalRiftOriginVerified": False,
    }


def main(argv: list[str] | None = None, **kwargs) -> int:
    try:
        code, record = execute(argv, **kwargs)
        print(json.dumps(record, indent=2))
        return code
    except (SessionError, OSError) as exc:
        print(json.dumps({
            "schema": "RCM_SCREENSHOT_SESSION_V1",
            "status": "refused",
            "reason": str(exc),
            "gameInputSent": None,
            "screenshotFileVerified": False,
        }, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
