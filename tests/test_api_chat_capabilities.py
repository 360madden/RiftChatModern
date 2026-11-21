"""Fixture-only tests for persisted RIFT API chat/console capability projection.

The target tool must read API Atlas's normalized JSON without executing
addon code, exposing user chat, or modifying RIFT or source snapshots.
"""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import rcm_api_chat_capabilities as audit


def sample(*, extra_events=(), capture_status="complete", kind="rift-client"):
    names = [
        "Command.Console.Display",
        "Event.Chat.Npc", "Event.Chat.Notify",
        "Event.Message.Receive",
        "Inspect.Console.List", "Inspect.Console.Detail",
        "UI.Native.Console1",
        "Command.Message.Send",
        *extra_events,
    ]
    return {
        "atlas_version": "0.3",
        "schema_version": 1,
        "capture": {"status": capture_status},
        "source": {
            "kind": kind,
            "captured_at": "2026-10-28T15:15:25Z",
            "client_version": "RIFT-BUILD-12 fixture",
        },
        "entries": [
            {"name": name, "kind": "event" if name.startswith("Event.") else "function",
             "documentation": {"summary": "fixture only",
                               "readable": "private fixture text should never leak"}}
            for name in names
        ],
    }


class RcmChatApiCapabilityTests(unittest.TestCase):
    def test_complete_capture_reports_only_documented_api_names(self):
        result = audit.inspect_snapshot(sample())
        self.assertEqual(result["schema"], "RCM_CHAT_API_CAPABILITIES_V1")
        self.assertEqual(result["sourceCaptureAt"], "2026-10-28T15:15:25Z")
        self.assertTrue(result["captureComplete"])
        self.assertEqual(result["documentedChatEvents"],
                         ["Event.Chat.Notify", "Event.Chat.Npc"])
        self.assertEqual(result["possiblePlayerChatEventCandidates"], [])
        self.assertEqual(result["documentedConsoleInspection"],
                         ["Inspect.Console.Detail", "Inspect.Console.List"])
        self.assertEqual(result["addonMessageReceive"],
                         "Event.Message.Receive")
        self.assertFalse(result["nativePlayerChatReceptionVerified"])
        self.assertTrue(result["snapshotOnlyNotLive"])
        self.assertNotIn("private fixture text", json.dumps(result))

    def test_new_future_chat_event_is_a_candidate_not_runtime_proof(self):
        result = audit.inspect_snapshot(
            sample(extra_events=("Event.Chat.PlayerMessage",
                                 "Event.Chat.Channel")))
        self.assertEqual(result["possiblePlayerChatEventCandidates"],
                         ["Event.Chat.Channel", "Event.Chat.PlayerMessage"])
        self.assertFalse(result["nativePlayerChatReceptionVerified"])
        self.assertFalse(result["generalPlayerChatCaptureEstablished"])

    def test_incomplete_capture_cannot_pass_require_complete(self):
        data = sample(capture_status="collecting")
        report = audit.inspect_snapshot(data)
        self.assertFalse(report["captureComplete"])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snapshot.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = audit.run(["--snapshot", str(path), "--require-complete"])
            self.assertEqual(rc, 2)
            self.assertFalse(json.loads(out.getvalue())["captureComplete"])

    def test_invalid_and_duplicate_catalog_entries_rejected(self):
        data = sample()
        data["entries"].append(dict(data["entries"][0]))
        with self.assertRaisesRegex(audit.CapabilityAuditError,
                                    "duplicate_api_name"):
            audit.inspect_snapshot(data)
        with self.assertRaisesRegex(audit.CapabilityAuditError,
                                    "not_rift_client"):
            audit.inspect_snapshot(sample(kind="other-app"))

    def test_cli_is_read_only_and_does_not_emit_documentation_bodies(self):
        data = sample()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snapshot.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            prior = path.read_bytes()
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = audit.run(["--snapshot", str(path), "--require-complete"])
            self.assertEqual(rc, 0)
            result = json.loads(out.getvalue())
            self.assertEqual(result["entriesScanned"], len(data["entries"]))
            self.assertFalse(result["snapshotChanged"])
            self.assertEqual(path.read_bytes(), prior)
            self.assertNotIn("private fixture text", out.getvalue())


if __name__ == "__main__":
    unittest.main()
