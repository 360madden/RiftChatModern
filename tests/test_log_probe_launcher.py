"""PowerShell RCM log-probe entrypoint, real Windows process, fixture-only log.

These tests exercise the launcher and existing Node observer without RIFT,
game input, character files, or an enabled logging setting.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "tools" / "rcm-log-probe.ps1"
PS = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")


@unittest.skipUnless(sys.platform == "win32" and PS.is_file(),
                     "Windows PowerShell 5.1 required")
class RcmLogProbeLauncherTests(unittest.TestCase):
    def invoke(self, args, *, env=None):
        return subprocess.run(
            [str(PS), "-NoProfile", "-NonInteractive", "-ExecutionPolicy",
             "Bypass", "-File", str(LAUNCHER), *args],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=20, env=env, check=False)

    def test_preview_selects_rcm_observer_and_explicit_raw_sample_only(self):
        result = self.invoke(["-Preview", "-Nonce", "RCM_PROBE_20261120",
                              "-SampleRawLines", "3", "-RequireChatAfterMarker"])
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout.strip())
        self.assertEqual(receipt["event"], "preview")
        self.assertTrue(receipt["watcher"].endswith("rcm-chat-observer.cjs"))
        self.assertIn("Rift.cfg", receipt["pathSelectionPolicy"])
        self.assertEqual(receipt["rawSampleLines"], 3)
        self.assertTrue(receipt["requireChatAfterMarker"])
        self.assertIn("chat_phase_armed", receipt["instruction"])
        self.assertFalse(receipt["gameInputSent"])
        self.assertFalse(receipt["loggingChanged"])
        self.assertFalse(receipt["transportVerified"])
        self.assertEqual(receipt["rcmEditorCommand"], ":logprobe RCM_PROBE_20261120")
        self.assertNotIn("LuaPad snippet", result.stdout)

    def test_invalid_nonce_and_relative_log_path_refused(self):
        for extra in (["-Nonce", "bad nonce"],
                      ["-Nonce", "RCM_PROBE_20261120",
                       "-LogPath", "relative\\Log.txt"]):
            with self.subTest(extra=extra):
                result = self.invoke(["-Preview", *extra])
                self.assertEqual(result.returncode, 1)
                self.assertNotIn('"event":"watcher_starting"', result.stdout)

    def test_live_bounded_observer_honors_fixture_rift_cfg_directory(self):
        with tempfile.TemporaryDirectory(prefix="rcm-probe-path-") as folder:
            base = Path(folder)
            appdata = base / "Roaming"
            cfg = appdata / "RIFT" / "Rift.cfg"
            cfg.parent.mkdir(parents=True)
            docs = base / "ConfiguredRiftDocuments"
            docs.mkdir()
            cfg.write_text("[Client]\nDocumentsDirectory = " +
                           str(docs).replace("\\", "/") + "\n",
                           encoding="utf-8")
            env = os.environ.copy()
            env["APPDATA"] = str(appdata)
            result = self.invoke(
                ["-Nonce", "RCM_PROBE_20261120", "-TimeoutSeconds", "1",
                 "-RequireChatAfterMarker"],
                env=env)
            self.assertEqual(result.returncode, 2, result.stderr)
            lines = [json.loads(line) for line in result.stdout.splitlines()
                     if line.startswith("{")]
            started = next(row for row in lines if row.get("event") == "started")
            stopped = next(row for row in lines if row.get("event") == "finished")
            self.assertEqual(started["pathSelection"],
                             "rift_cfg_documents_directory")
            self.assertTrue(started["requireChatAfterMarker"])
            self.assertEqual(Path(started["path"]),
                             docs / "Log.txt")
            self.assertFalse(started["transportVerified"])
            self.assertFalse(started["gameInputSent"])
            self.assertEqual(stopped["reason"], "timeout")
            self.assertFalse((docs / "Log.txt").exists())


if __name__ == "__main__":
    unittest.main()
