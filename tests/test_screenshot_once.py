"""The RCM screenshot session coordinates one .NET key request and an independent
new-JPEG check without silently choosing a character or sending repeated input.

All tests use mocked child-process receipts. No physical game key is sent.
"""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import rcm_screenshot_once as session

HOST = socket.gethostname()
PIN = {
    "schema": "RCM_GAME_SCREENSHOT_TRIGGER_V1",
    "status": "read_only_target_candidate",
    "machine": HOST,
    "pid": 34596,
    "hwnd": "0xA0C2C",
    "startUtcTicks": 639308249563595623,
    "exePath": r"C:\Program Files (x86)\Glyph\Games\RIFT\Live\rift_x64.exe",
    "exeSha256": "A" * 64,
    "foreground": False,
    "gameInputSent": False,
}


class FakeProcess:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.calls.append(list(argv))
        if not self.responses:
            raise AssertionError("Orchestrator invoked an unexpected extra child process.")
        code, obj = self.responses.pop(0)
        return subprocess.CompletedProcess(argv, code, json.dumps(obj), "")


class ScreenshotOnceTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix="rcm-one-shot-test-")
        self.addCleanup(self.folder.cleanup)
        self.fake_dll = Path(self.folder.name) / "RcmScreenshotKey.dll"
        self.fake_dll.write_bytes(b"test fixture only")
        self.patch = mock.patch.object(session, "TRIGGER_DLL", self.fake_dll)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.now = time.time_ns()

    def call(self, flags, responses, *, checker=None, resolver=None):
        runner = FakeProcess(responses)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = session.main(
                flags, command_runner=runner,
                config_resolver=resolver or (lambda config: Path(self.folder.name)),
                file_checker=checker or (lambda folder, after: {"status": "no_new_screenshot"}),
                clock_ns=lambda: self.now,
                sleep=lambda delay: None,
            )
        return code, json.loads(buffer.getvalue()), runner

    def test_dry_run_pins_exact_process_without_any_input(self):
        code, record, runner = self.call(
            ["--expect-host", HOST, "--dry-run"],
            [(0, PIN), (0, {
                "schema": PIN["schema"], "status": "ready_no_input",
                "gameInputSent": False, "screenshotFileVerified": False,
            })],
        )
        self.assertEqual(code, 0)
        self.assertEqual(record["status"], "ready_no_input")
        self.assertFalse(record["gameInputSent"])
        self.assertEqual(len(runner.calls), 2)
        self.assertIn("--inspect", runner.calls[0])
        action = runner.calls[1]
        self.assertIn("--dry-run", action)
        self.assertNotIn("--capture", action)
        for key in ("--expect-host", "--pid", "--hwnd", "--start-ticks",
                    "--exe-path", "--exe-sha256"):
            self.assertIn(key, action)
        self.assertEqual(action[action.index("--pid") + 1], str(PIN["pid"]))

    def test_capture_arm_uses_exact_pin_and_one_action_only(self):
        fired = {
            "schema": PIN["schema"], "status": "windows_key_events_inserted",
            "baselineEpochNs": self.now, "gameInputSent": True,
            "keyEventsInserted": 2, "screenshotFileVerified": False,
        }
        saved = {
            "status": "new_screenshot_file",
            "freshnessVerified": True,
            "screenshot": {
                "filename": "2026-11-20_231500.jpg",
                "file": str(Path(self.folder.name) / "2026-11-20_231500.jpg"),
                "sha256": "b" * 64,
                "format": "JPEG", "width": 2560, "height": 1369,
            },
        }
        checked = []
        def checker(folder, after):
            checked.append((str(folder), after))
            return saved
        code, record, runner = self.call(
            ["--expect-host", HOST, "--capture", "--ack-single-screenshot",
             "--arm-seconds", "10", "--wait-ms", "0"],
            [(0, PIN), (0, fired)], checker=checker,
        )
        self.assertEqual(code, 0)
        self.assertEqual(record["status"], "new_post_key_image_verified")
        self.assertTrue(record["gameInputSent"])
        self.assertTrue(record["screenshotFileVerified"])
        self.assertFalse(record["physicalRiftOriginVerified"])
        self.assertFalse(record["gameWindowCorrelated"])
        self.assertEqual(record["screenshot"]["format"], "JPEG")
        self.assertEqual(checked[0][1], self.now)
        self.assertEqual(len(runner.calls), 2)
        command = runner.calls[1]
        self.assertEqual(command.count("--capture"), 1)
        self.assertIn("--ack-single-screenshot", command)
        self.assertEqual(command[command.index("--arm-seconds") + 1], "10")

    def test_background_refusal_never_queries_image_or_retries(self):
        invoked = []
        def reject_image(folder, after):
            invoked.append("checker-called")
            return {"status": "new_screenshot_file"}
        code, record, runner = self.call(
            ["--expect-host", HOST, "--capture", "--ack-single-screenshot",
             "--arm-seconds", "2"],
            [(0, PIN), (2, {
                "schema": PIN["schema"], "status": "foreground_timeout_no_input",
                "gameInputSent": False, "screenshotFileVerified": False,
            })], checker=reject_image,
        )
        self.assertEqual(code, 2)
        self.assertEqual(record["status"], "foreground_timeout_no_input")
        self.assertFalse(record["gameInputSent"])
        self.assertEqual(len(runner.calls), 2)
        self.assertEqual(invoked, [])

    def test_key_inserted_but_no_new_jpeg_is_not_declared_success(self):
        code, record, runner = self.call(
            ["--expect-host", HOST, "--capture", "--ack-single-screenshot",
             "--wait-ms", "0"],
            [(0, PIN), (0, {
                "schema": PIN["schema"], "status": "windows_key_events_inserted",
                "gameInputSent": True, "baselineEpochNs": self.now,
                "keyEventsInserted": 2,
            })],
        )
        self.assertEqual(code, 2)
        self.assertEqual(record["status"], "key_events_inserted_but_no_new_image")
        self.assertTrue(record["gameInputSent"])
        self.assertFalse(record["screenshotFileVerified"])
        self.assertEqual(len(runner.calls), 2)

    def test_corrupt_post_key_image_does_not_hide_inserted_key_events(self):
        def broken_image(folder, after):
            raise session.ScreenshotReceiptError("invalid JPEG payload")
        code, report, runner = self.call(
            ["--expect-host", HOST, "--capture", "--ack-single-screenshot",
             "--wait-ms", "0"],
            [(0, PIN), (0, {
                "schema": PIN["schema"], "status": "windows_key_events_inserted",
                "gameInputSent": True, "baselineEpochNs": self.now,
                "keyEventsInserted": 2,
            })], checker=broken_image,
        )
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "new_image_verification_failed")
        self.assertTrue(report["gameInputSent"])
        self.assertFalse(report["screenshotFileVerified"])
        self.assertEqual(len(runner.calls), 2)

    def test_unavailable_post_key_directory_preserves_true_input_receipt(self):
        def absent_config(file):
            raise session.ScreenshotReceiptError("missing screenshots folder")
        code, report, runner = self.call(
            ["--expect-host", HOST, "--capture", "--ack-single-screenshot"],
            [(0, PIN), (0, {
                "schema": PIN["schema"], "status": "windows_key_events_inserted",
                "gameInputSent": True, "baselineEpochNs": self.now,
                "keyEventsInserted": 2,
            })], resolver=absent_config,
        )
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "image_source_unavailable_after_key")
        self.assertTrue(report["gameInputSent"])
        self.assertFalse(report["screenshotFileVerified"])
        self.assertEqual(len(runner.calls), 2)

    def test_ambiguous_clients_fail_before_capture(self):
        code, record, runner = self.call(
            ["--expect-host", HOST, "--capture", "--ack-single-screenshot"],
            [(2, {
                "schema": PIN["schema"],
                "status": "multiple_rift_processes_require_pid",
                "gameInputSent": False,
            })],
        )
        self.assertEqual(code, 2)
        self.assertEqual(record["status"], "rift_inspection_not_ready")
        self.assertEqual(record["reason"], "multiple_rift_processes_require_pid")
        self.assertEqual(len(runner.calls), 1)

    def test_capture_without_ack_or_wrong_host_never_invokes_child(self):
        for flags in (
            ["--expect-host", HOST, "--capture"],
            ["--expect-host", "INCORRECT_HOST", "--dry-run"],
            ["--expect-host", HOST, "--dry-run", "--arm-seconds", "2"],
        ):
            with self.subTest(flags=flags):
                code, report, runner = self.call(flags, [])
                self.assertEqual(code, 1)
                self.assertEqual(report["status"], "refused")
                self.assertEqual(runner.calls, [])

    def test_invalid_helper_response_prevents_second_action(self):
        code, report, runner = self.call(
            ["--expect-host", HOST, "--capture", "--ack-single-screenshot"],
            [(0, {"schema": "unexpected", "status": "read_only_target_candidate"})],
        )
        self.assertEqual(code, 1)
        self.assertEqual(report["reason"], "unexpected_dotnet_helper_schema")
        self.assertEqual(len(runner.calls), 1)

    def test_incomplete_image_or_bad_baseline_never_returns_success(self):
        code, report, runner = self.call(
            ["--expect-host", HOST, "--capture", "--ack-single-screenshot"],
            [(0, PIN), (0, {
                "schema": PIN["schema"], "status": "windows_key_events_inserted",
                "gameInputSent": True, "baselineEpochNs": 1,
                "keyEventsInserted": 2,
            })],
        )
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "invalid_capture_baseline_after_key")
        self.assertTrue(report["gameInputSent"])
        self.assertFalse(report["screenshotFileVerified"])
        self.assertEqual(len(runner.calls), 2)


if __name__ == "__main__":
    unittest.main()
