"""Windows .NET 10 RCM editor-import preflight integration tests.

This helper validates inputs and optionally inspects process identity; it NEVER
sends keys, changes window focus, touches the clipboard or edits RIFT files.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "tools" / "RcmEditorInput" / "RcmEditorInput.csproj"
DLL = ROOT / "tools" / "RcmEditorInput" / "bin" / "Release" / "net10.0-windows" / "RcmEditorInput.dll"
DOTNET = shutil.which("dotnet")
VALID = ":import ABCDEF123456 1/1 QUJDRA"


@unittest.skipUnless(os.name == "nt" and DOTNET, "Requires Windows .NET 10 SDK")
class RcmEditorPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.name != "nt" or not DOTNET:
            return
        assert DOTNET is not None
        build = subprocess.run(
            [DOTNET, "build", str(PROJECT), "--configuration", "Release", "--nologo"],
            text=True, capture_output=True, timeout=45, check=False)
        if build.returncode != 0:
            raise AssertionError(f"RCM read-only preflight failed to build: {build.stdout}\n{build.stderr}")

    def run_helper(self, *args: str, input_text: str | None = None):
        result = subprocess.run([DOTNET, str(DLL), *args],
                                input=input_text, text=True, capture_output=True,
                                encoding="utf-8", timeout=20, check=False)
        try:
            payload = json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            self.fail(f"Invalid JSON response: {result.stdout!r}; stderr={result.stderr!r}")
        return result.returncode, payload

    def test_builtin_pure_contract_suite_has_no_game_actions(self):
        rc, result = self.run_helper("--self-test")
        self.assertEqual(rc, 0)
        self.assertEqual(result["status"], "self_tests_passed")
        self.assertGreaterEqual(result["tests"], 20)
        self.assertFalse(result["gameInputSent"])
        self.assertFalse(result["clipboardModified"])

    def test_valid_editor_plan_outputs_digest_not_chat_body(self):
        rc, result = self.run_helper("--command", VALID)
        self.assertEqual(rc, 0)
        self.assertEqual(result["status"], "command_validated_no_input")
        self.assertEqual(result["commandChars"], len(VALID))
        self.assertEqual(result["commandSha256"],
                         hashlib.sha256(VALID.encode()).hexdigest().upper())
        self.assertEqual((result["part"], result["total"]), (1, 1))
        self.assertEqual(result["source"], "operator_supplied")
        self.assertFalse(result["gameInputSent"])
        self.assertFalse(result["addonImportAcceptedVerified"])
        self.assertNotIn("ABCDEF123456", json.dumps(result))
        self.assertNotIn("QUJDRA", json.dumps(result))

    def test_stdin_avoids_encoded_command_in_arguments_and_matches_digest(self):
        # subprocess text=True translates a single LF to Windows CRLF.
        rc, result = self.run_helper("--stdin-command", input_text=VALID + "\n")
        self.assertEqual(rc, 0, result)
        self.assertEqual(result["source"], "stdin")
        self.assertEqual(result["commandSha256"],
                         hashlib.sha256(VALID.encode()).hexdigest().upper())
        self.assertFalse(result["gameInputSent"])
        self.assertNotIn(VALID, json.dumps(result))

    def test_stdin_refuses_missing_multiline_and_oversized_commands(self):
        for body in ("", VALID + "\n" + VALID + "\n", "A" * 161 + "\n"):
            with self.subTest(length=len(body)):
                rc, result = self.run_helper("--stdin-command", input_text=body)
                self.assertEqual(rc, 1)
                self.assertEqual(result["status"], "refused")
                self.assertFalse(result["gameInputSent"])

    def test_invalid_payload_and_native_chat_form_refused(self):
        for command in (":import abcdef123456 1/1 AAA",
                        ":import ABCDEF123456 2/1 AAA",
                        ":import ABCDEF123456 1/1 AAA\n",
                        "/rcm import ABCDEF123456 1/1 AAA",
                        ":import ABCDEF123456 1/1 " + "A" * 125):
            with self.subTest(command=command[:28]):
                rc, result = self.run_helper("--command", command)
                self.assertEqual(rc, 1)
                self.assertEqual(result["status"], "refused")
                self.assertFalse(result["gameInputSent"])

    def test_source_keeps_the_preflight_read_only(self):
        code=(ROOT / "tools" / "RcmEditorInput" / "Program.cs").read_text(
            encoding="utf-8")
        # This component must not become an unreviewed desktop sender.
        for api in ("DllImport", "LibraryImport", "SendInput",
                    "SetForegroundWindow", "keybd_event", "mouse_event",
                    "File.WriteAllText", "File.AppendAllText", "Process.Start"):
            with self.subTest(api=api):
                self.assertNotRegex(code, rf"\b{api.replace('.', r'\.')}\s*\(")

    def test_mixed_options_and_unknown_flags_rejected(self):
        for flags in (("--inspect", "--command", VALID),
                      ("--command", VALID, "--stdin-command"),
                      ("--help", "--command", VALID),
                      ("--command", VALID, "--command", VALID),
                      ("--execute", "--command", VALID)):
            with self.subTest(flags=flags):
                rc, result = self.run_helper(*flags)
                self.assertEqual(rc, 1)
                self.assertEqual(result["status"], "refused")
                self.assertFalse(result["gameInputSent"])


if __name__ == "__main__":
    unittest.main()
