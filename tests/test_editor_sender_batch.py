"""RCM batch sender: real Node record -> .NET strict preflight, no game input.

Each runtime test deliberately omits a valid focused game pin. No test can
invoke a successful batch SendInput path.
"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import os
import shutil
import socket
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")
DOTNET = shutil.which("dotnet")
ENCODER = ROOT / "tools" / "rcm-chat-import.cjs"
PROJECT = ROOT / "tools" / "RcmEditorSender" / "RcmEditorSender.csproj"
DLL = ROOT / "tools" / "RcmEditorSender" / "bin" / "Release" / "net10.0-windows" / "RcmEditorSender.dll"


@unittest.skipUnless(os.name == "nt" and NODE and DOTNET, "Requires Node and Windows .NET 10 SDK")
class BatchSenderContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.name != "nt" or not NODE or not DOTNET:
            return
        build = subprocess.run(
            [DOTNET, "build", str(PROJECT), "-c", "Release", "--nologo"],
            cwd=ROOT, text=True, capture_output=True, timeout=60, check=False)
        if build.returncode:
            raise AssertionError(f"Batch sender build failed: {build.stdout}\n{build.stderr}")

    def encode(self, text="RIFT batch editor test", kind="guild", token="A1B2C3D4E5F6"):
        proc = subprocess.run(
            [NODE, str(ENCODER), "--kind", kind,
             "--sender", "BatchProbe", "--channel", "Guild" if kind == "guild" else "Party",
             "--text", text, "--id", token, "--input-mode", "editor"],
            cwd=ROOT, text=True, encoding="utf-8",
            capture_output=True, timeout=20, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def sender(self, payload, *flags):
        body = payload if isinstance(payload, str) else json.dumps(
            payload, ensure_ascii=False, separators=(",", ":"))
        proc = subprocess.run(
            [DOTNET, str(DLL), "--stdin-batch", *flags],
            cwd=ROOT, input=body, capture_output=True, text=True,
            encoding="utf-8", timeout=25, check=False)
        try:
            result = json.loads(proc.stdout.strip())
        except json.JSONDecodeError:
            self.fail(f"Invalid sender JSON {proc.stdout!r}, stderr={proc.stderr!r}")
        return proc.returncode, result, proc.stdout, body

    def assert_refused_no_input(self, data, *flags):
        rc, result, printed, _ = self.sender(data, *flags)
        self.assertEqual(rc, 1, printed)
        self.assertEqual(result["status"], "refused_before_input", printed)
        self.assertIs(result["gameInputSent"], False)
        self.assertIs(result["clipboardChanged"], False)

    def test_single_real_node_encoder_record_validation_only(self):
        record = self.encode(text="BATCH_ONE_REAL_ENCODER")
        rc, p, stdout, source = self.sender(record)
        self.assertEqual(rc, 0, p)
        self.assertEqual(p["status"], "batch_validated_no_input")
        self.assertEqual((p["token"], p["kind"], p["parts"]),
                         ("A1B2C3D4E5F6", "guild", 1))
        self.assertEqual(p["chars"], sum(map(len, record["commands"])))
        self.assertEqual(p["sha256"], hashlib.sha256(source.encode("utf-8")).hexdigest().upper())
        self.assertIs(p["gameInputSent"], False)
        self.assertIs(p["addonAcceptedVerified"], False)
        self.assertIs(p["diskSavedVerified"], False)
        self.assertNotIn("BATCH_ONE_REAL_ENCODER", stdout)
        self.assertNotIn(record["commands"][0], stdout)

    def test_real_multipart_unicode_is_validated_as_one_bounded_batch(self):
        record = self.encode(text=("RIFT Unicode café✓ 🎮 " * 13) + "FINAL", kind="party")
        self.assertGreaterEqual(record["parts"], 3)
        rc, p, printed, _ = self.sender(record)
        self.assertEqual(rc, 0, printed)
        self.assertEqual(p["status"], "batch_validated_no_input")
        self.assertEqual((p["parts"], p["kind"]), (record["parts"], "party"))
        self.assertIs(p["gameInputSent"], False)

    def test_incomplete_reordered_or_mixed_tokens_rejected_before_input(self):
        good = self.encode(text=("Long multipart transfer " * 16))
        self.assertGreaterEqual(good["parts"], 3)
        incomplete = dict(good, commands=good["commands"][:-1])
        reordered = dict(good, commands=list(reversed(good["commands"])))
        conflicting = dict(good, commands=list(good["commands"]))
        conflicting["commands"][1] = conflicting["commands"][1].replace(
            good["id"], "ABABABABABAB")
        wrong_total = dict(good, parts=good["parts"] - 1)
        for candidate in (incomplete, reordered, conflicting, wrong_total):
            with self.subTest(candidate=str(candidate["commands"][0])[:16]):
                self.assert_refused_no_input(candidate)

    def test_malformed_header_metadata_or_json_rejected(self):
        good = self.encode()
        variants = [
            dict(good, inputMode="native"),
            dict(good, protocol="OTHER"),
            dict(good, event="candidate_chat"),
            dict(good, kind="party"),
            dict(good, automaticGameInput=True),
            dict(good, liveGameDeliveryVerified=True),
            dict(good, requiresManualEntry=False),
            dict(good, surprise="unrecognized"),
            dict(good, source="made_up_source"),
            dict(good, id="abcdefgh1234"),
        ]
        for value in variants:
            with self.subTest(keys=[k for k in value if value[k] != good.get(k)]):
                self.assert_refused_no_input(value)
        raw = json.dumps(good, separators=(",", ":"))
        for invalid in (raw + raw, raw.replace('"parts":', '"parts":1,"parts":'),
                        raw + "\n{}\n", "[" + raw + "]", "x" * 8200):
            with self.subTest(invalid=invalid[:40]):
                self.assert_refused_no_input(invalid)

    def test_host_rejects_invalid_binary_utf8_and_control_chars(self):
        good = self.encode()
        for raw in (
            b"G\0BatchProbe\0Guild\0bad\x01control",
            b"G\0BatchProbe\0Guild\0bad\xffutf8",
            b"P\0BatchProbe\0Guild\0wrongKind",
            b"G\0BatchProbe\0Guild\0hi\0extra",
        ):
            base = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
            fake = dict(good, commands=[
                ":import " + good["id"] + " 1/1 " + base])
            self.assert_refused_no_input(fake)

    def test_send_requires_all_batch_specific_acknowledgments(self):
        record = self.encode()
        for flags in (
            ("--send",),
            ("--send", "--ack-editor-focused"),
            ("--send", "--ack-editor-focused", "--submit", "--ack-submit"),
            ("--send", "--ack-editor-focused", "--ack-batch"),
            ("--send", "--ack-editor-focused", "--submit", "--ack-batch"),
        ):
            with self.subTest(flags=flags):
                self.assert_refused_no_input(record, *flags)

    def test_fake_process_window_refused_even_with_every_ack(self):
        record = self.encode()
        pins = (
            "--send", "--ack-editor-focused", "--submit", "--ack-submit", "--ack-batch",
            "--expect-host", socket.gethostname(),
            "--pid", "999999", "--hwnd", "0x1",
            "--start-ticks", "621355968000000001",
            "--exe-path", r"C:\Windows\System32\notepad.exe",
            "--exe-sha256", "A" * 64,
        )
        self.assert_refused_no_input(record, *pins)

    def test_invalid_flag_mix_never_reaches_any_input(self):
        good = self.encode()
        self.assert_refused_no_input(good, "--command", good["commands"][0])
        self.assert_refused_no_input(good, "--ack-batch")
        self.assert_refused_no_input(good, "--submit", "--ack-submit")

    def test_sender_reuses_shared_parser_and_retains_pinned_foreground(self):
        code = (ROOT / "tools" / "RcmEditorSender" / "Program.cs").read_text(
            encoding="utf-8")
        contract = (ROOT / "tools" / "RcmEditorSender" / "ImportBatchContract.cs").read_text(
            encoding="utf-8")
        self.assertIn("RcmImportBatchContract.ReadOne(Console.In)", code)
        self.assertIn("RcmImportContract.Parse(line)", contract)
        self.assertIn("GetForegroundWindow() != pin.Hwnd", code)
        self.assertIn("RequireTarget(target, hashExecutable: false);", code)
        self.assertIn("if (batch is not null && (!submit || !ackBatch))", code)
        self.assertNotIn("SetForegroundWindow(", code)


if __name__ == "__main__":
    unittest.main()
