"""Regression tests for RCM's opt-in Windows editor sender.

These tests NEVER authorize a successful --send: they exercise only validation,
a self-test, or intentionally invalid game pins, so no keyboard/game state changes.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "tools" / "RcmEditorSender" / "RcmEditorSender.csproj"
DLL = ROOT / "tools" / "RcmEditorSender" / "bin" / "Release" / "net10.0-windows" / "RcmEditorSender.dll"
DOTNET = shutil.which("dotnet")
VALID = ":import ABCDEF123456 1/1 QUJDRA"


@unittest.skipUnless(os.name == "nt" and DOTNET, "Requires Windows .NET 10 SDK")
class RcmEditorSenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.name != "nt" or not DOTNET:
            return
        build = subprocess.run(
            [DOTNET, "build", str(PROJECT), "--configuration", "Release", "--nologo"],
            cwd=ROOT, text=True, capture_output=True, timeout=60, check=False)
        if build.returncode:
            raise AssertionError(f"Editor sender build failed: {build.stdout}\n{build.stderr}")

    def run_sender(self, *flags: str, stdin: str | None = None):
        result = subprocess.run(
            [DOTNET, str(DLL), *flags], cwd=ROOT, input=stdin,
            text=True, capture_output=True, encoding="utf-8",
            timeout=20, check=False)
        try:
            payload = json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            self.fail(f"Non-JSON sender reply {result.stdout!r}: {result.stderr!r}")
        return result.returncode, payload

    def test_self_test_does_not_send_input(self):
        rc, p = self.run_sender("--self-test")
        self.assertEqual(rc, 0)
        self.assertEqual(p["status"], "self_tests_passed")
        self.assertGreaterEqual(p["checks"], 12)
        self.assertIs(p["gameInputSent"], False)
        self.assertIs(p["clipboardChanged"], False)

    def test_valid_explicit_command_is_plan_only(self):
        rc, p = self.run_sender("--command", VALID)
        self.assertEqual(rc, 0, p)
        self.assertEqual(p["schema"], "RCM_EDITOR_SEND_V1")
        self.assertEqual(p["status"], "validated_no_input")
        self.assertEqual(p["sha256"], hashlib.sha256(VALID.encode()).hexdigest().upper())
        self.assertEqual((p["part"], p["total"], p["chars"]), (1, 1, len(VALID)))
        self.assertIs(p["gameInputSent"], False)
        self.assertIs(p["addonAcceptedVerified"], False)
        self.assertIs(p["diskSavedVerified"], False)
        self.assertNotIn(VALID, json.dumps(p))
        self.assertNotIn("QUJDRA", json.dumps(p))

    def test_one_line_stdin_is_plan_only_and_never_echoes_message(self):
        rc, p = self.run_sender("--stdin-command", stdin=VALID + "\n")
        self.assertEqual(rc, 0, p)
        self.assertEqual(p["status"], "validated_no_input")
        self.assertEqual(p["sha256"], hashlib.sha256(VALID.encode()).hexdigest().upper())
        self.assertIs(p["gameInputSent"], False)
        self.assertNotIn(VALID, json.dumps(p))
        for invalid in ("", VALID + "\n" + VALID + "\n", "A" * 161 + "\n"):
            with self.subTest(length=len(invalid)):
                rc, p = self.run_sender("--stdin-command", stdin=invalid)
                self.assertEqual(rc, 1, p)
                self.assertEqual(p["status"], "refused_before_input")
                self.assertIs(p["gameInputSent"], False)

    def test_explicit_send_requires_focus_acknowledgment(self):
        for opts in (
            ("--command", VALID, "--send"),
            ("--command", VALID, "--submit", "--ack-submit"),
            ("--command", VALID, "--send", "--submit"),
            ("--command", VALID, "--send", "--ack-editor-focused", "--submit"),
        ):
            with self.subTest(opts=opts):
                rc, p = self.run_sender(*opts)
                self.assertEqual(rc, 1, p)
                self.assertEqual(p["status"], "refused_before_input")
                self.assertIs(p["gameInputSent"], False)

    def test_wrong_machine_pin_rejected_before_input(self):
        fake_target = (
            "--send", "--ack-editor-focused",
            "--expect-host", "INTENTIONALLY-WRONG-HOST",
            "--pid", "999999", "--hwnd", "0x1",
            "--start-ticks", "621355968000000001",
            "--exe-path", r"C:\Windows\System32\notepad.exe",
            "--exe-sha256", "A" * 64,
        )
        rc, p = self.run_sender("--stdin-command", *fake_target, stdin=VALID + "\n")
        self.assertEqual(rc, 1, p)
        self.assertEqual(p["status"], "refused_before_input")
        self.assertEqual(p["error"], "ArgumentException")
        self.assertIs(p["gameInputSent"], False)
        self.assertIs(p["clipboardChanged"], False)

    def test_stale_fake_window_refused_even_with_send_ack(self):
        fake_target = (
            "--send", "--ack-editor-focused",
            "--expect-host", socket.gethostname(),
            "--pid", "999999", "--hwnd", "0x1",
            "--start-ticks", "621355968000000001",
            "--exe-path", r"C:\Windows\System32\notepad.exe",
            "--exe-sha256", "A" * 64,
        )
        rc, p = self.run_sender("--command", VALID, *fake_target)
        self.assertEqual(rc, 1, p)
        self.assertEqual(p["status"], "refused_before_input")
        self.assertIs(p["gameInputSent"], False)

    def test_shared_parser_and_foreground_guards_are_not_bypassed(self):
        sender = (ROOT / "tools" / "RcmEditorSender" / "Program.cs").read_text(
            encoding="utf-8")
        csproj = PROJECT.read_text(encoding="utf-8")
        self.assertIn("RcmImportContract.Parse(command)", sender)
        self.assertIn("RcmImportContract.ReadOne(Console.In)", sender)
        self.assertIn("../RcmEditorInput/ImportContract.cs", csproj)
        self.assertIn("GetForegroundWindow() != pin.Hwnd", sender)
        self.assertIn("game.StartTime.ToUniversalTime().Ticks != pin.StartUtcTicks", sender)
        self.assertIn("RequireNoModifiers();", sender)
        self.assertIn("keyCallAttempted", sender)
        self.assertNotIn("SetForegroundWindow(", sender)
        self.assertNotIn("SetFocus(", sender)
        self.assertNotIn("Clipboard.SetText(", sender)


if __name__ == "__main__":
    unittest.main()
