"""RCM's opt-in *Numpad Multiply* RIFT screenshot trigger.

Source is intentionally a separate .NET 10 project from the strictly
read-only editor-input preflight. All integration tests below avoid --capture
on a real RIFT target and therefore NEVER send input to the game.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "tools" / "RcmScreenshotKey" / "RcmScreenshotKey.csproj"
DLL = ROOT / "tools" / "RcmScreenshotKey" / "bin" / "Release" / "net10.0-windows" / "RcmScreenshotKey.dll"
DOTNET = shutil.which("dotnet")


@unittest.skipUnless(os.name == "nt" and DOTNET, "Requires Windows/.NET 10")
class RcmScreenshotKeyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not DOTNET or os.name != "nt":
            return
        compile = subprocess.run([DOTNET, "build", str(PROJECT),
                                  "--configuration", "Release", "--nologo"],
                                 capture_output=True, text=True, timeout=45, check=False)
        if compile.returncode:
            raise AssertionError("dotnet build failed: " + compile.stdout + compile.stderr)

    def run_key(self, *args):
        result = subprocess.run([DOTNET, str(DLL), *args],
                                capture_output=True, text=True,
                                encoding="utf-8", errors="replace",
                                timeout=20, check=False)
        try:
            report = json.loads(result.stdout.strip())
        except json.JSONDecodeError as exc:
            raise AssertionError(f"invalid JSON: {result.stdout!r} {result.stderr!r}") from exc
        return result.returncode, report

    def assert_no_key(self, report):
        self.assertFalse(report.get("gameInputSent", False))
        self.assertFalse(report.get("screenshotFileVerified", False))

    def test_internal_key_pair_and_input_layout(self):
        code, report = self.run_key("--self-test")
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "self_tests_passed")
        self.assertGreaterEqual(report["assertions"], 13)
        self.assert_no_key(report)

    def test_capture_requires_explicit_ack_and_six_identifiers(self):
        for opts in (("--capture",), ("--ack-single-screenshot",),
                     ("--capture", "--ack-single-screenshot"),
                     ("--dry-run", "--ack-single-screenshot"),
                     ("--dry-run", "--capture"),
                     ("--capture", "--ack-single-screenshot", "--arbitrary-key", "Q")):
            with self.subTest(opts=opts):
                code, report = self.run_key(*opts)
                self.assertEqual(code, 1)
                self.assertEqual(report["status"], "refused")
                self.assert_no_key(report)

    def test_wrong_machine_is_refused_before_any_windows_input(self):
        pin = ("--expect-host", "WRONG-COMPUTER",
               "--pid", "1",
               "--hwnd", "0x1",
               "--start-ticks", "639308249563595623",
               "--exe-path", r"C:\Windows\System32\notepad.exe",
               "--exe-sha256", "A" * 64)
        for mode in (("--dry-run",), ("--capture", "--ack-single-screenshot")):
            with self.subTest(mode=mode):
                code, report = self.run_key(*mode, *pin)
                self.assertEqual(code, 1)
                self.assertEqual(report["status"], "refused")
                self.assert_no_key(report)

    def test_wrong_pid_and_window_pins_fail_closed_even_with_ack(self):
        pin = ("--expect-host", os.environ["COMPUTERNAME"],
               "--pid", "2147483647",
               "--hwnd", "0x1",
               "--start-ticks", "639308249563595623",
               "--exe-path", r"C:\Windows\System32\notepad.exe",
               "--exe-sha256", "A" * 64)
        code, report = self.run_key("--capture", "--ack-single-screenshot", *pin)
        self.assertIn(code, (1, 2))
        self.assertIn(report["status"], ("refused", "refused_before_keypress"))
        self.assert_no_key(report)

    def test_readonly_inspection_with_nonexistent_pid(self):
        code, report = self.run_key("--inspect", "--pid", "2147483647")
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "game_process_absent")
        self.assert_no_key(report)

    def test_live_pinned_dry_run_never_sends_key(self):
        """This performs read-only inspection whether RIFT is foreground or not."""
        code, report = self.run_key("--inspect")
        if code != 0:
            self.assertEqual(code, 2)
            self.assert_no_key(report)
            return
        self.assertEqual(report["status"], "read_only_target_candidate")
        pin = ("--expect-host", report["machine"],
               "--pid", str(report["pid"]),
               "--hwnd", report["hwnd"],
               "--start-ticks", str(report["startUtcTicks"]),
               "--exe-path", report["exePath"],
               "--exe-sha256", report["exeSha256"])
        code, dry = self.run_key("--dry-run", *pin)
        self.assertIn(code, (0, 2))
        self.assertIn(dry["status"], ("ready_no_input",
                                     "game_not_foreground_no_input",
                                     "refused_before_keypress"))
        self.assert_no_key(dry)

    def test_only_multiply_key_is_permitted_in_source(self):
        source = (ROOT / "tools" / "RcmScreenshotKey" / "Program.cs").read_text(
            encoding="utf-8")
        self.assertIn("VkMultiply = 0x6A;", source)
        self.assertIn("SendInput(2, pair, Marshal.SizeOf<WinInput>())", source)
        self.assertNotIn("SetForegroundWindow(", source)
        self.assertNotIn("OpenClipboard(", source)
        self.assertNotIn("WriteProcessMemory(", source)
        self.assertNotIn("SendInput(1,", source)


if __name__ == "__main__":
    unittest.main()
