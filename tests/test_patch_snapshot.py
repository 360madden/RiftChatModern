"""Regression tests for RCM's private, non-mutating patch backup."""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import rcm_patch_snapshot as gate


class PatchSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / "RIFT"
        self.addon = self.root / "Interface" / "AddOns" / gate.ADDON
        self.addon.mkdir(parents=True)
        self.toc = self.addon / "RiftAddon.toc"
        self.toc.write_bytes(b'Identifier = "RiftChatModern"\nVersion = "0.2.23"\n')
        self.lua = self.addon / "Core.lua"
        self.lua.write_bytes(b"-- installed version")
        self.save = self.root / "Interface" / "Saved" / "private" / "shard" / "character" / "SavedVariables" / gate.SAVE_NAME
        self.save.parent.mkdir(parents=True)
        self.save.write_bytes(b"private saved bytes")
        self.other = self.save.with_name("OtherAddon.lua")
        self.other.write_bytes(b"not RCM")
        self.output = self.base / "snapshots"

    def capture(self, phase="before"):
        return gate.snapshot(self.root, self.output, phase, "LEGION", "0.2.26")

    def test_exact_backup_redacted_summary_and_unique_attempts(self):
        result = self.capture()
        backup = self.output / result["artifactDirectory"]
        private = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(result["installedVersion"], "0.2.23")
        self.assertEqual(result["sourceVersion"], "0.2.26")
        self.assertEqual(result["addonFiles"], 2)
        self.assertEqual(result["savedVariableFiles"], 1)
        self.assertNotIn("private", json.dumps(result))
        self.assertFalse(result["runtimeVerified"])
        self.assertFalse(result["gameSaveTriggered"])
        self.assertEqual(gate.digest((backup / "manifest.json").read_bytes()), result["manifestSha256"])
        for row in private["files"]:
            source = self.root / row["relative"]
            copied = backup / "files" / row["relative"]
            self.assertEqual(source.read_bytes(), copied.read_bytes())
            self.assertEqual(row["sha256"], gate.digest(copied.read_bytes()))
        self.assertFalse((backup / "files" / self.other.relative_to(self.root)).exists())
        second = self.capture("after")
        self.assertNotEqual(result["artifactDirectory"], second["artifactDirectory"])
        self.assertTrue(backup.exists())

    def test_refuse_wrong_manifest(self):
        self.toc.write_bytes(b'Identifier = "Unrelated"\nVersion = "0.2.23"\n')
        with self.assertRaisesRegex(ValueError, "unexpected_installed_identifier"):
            self.capture()
        self.assertFalse(self.output.exists())

    def test_refuse_changed_source(self):
        original = gate.stable_bytes
        count = 0
        def unstable(path):
            nonlocal count
            data = original(path)
            if path == self.lua:
                count += 1
                if count == 2:
                    return data + b"changed"
            return data
        with patch.object(gate, "stable_bytes", side_effect=unstable):
            with self.assertRaisesRegex(ValueError, "file_changed_during_snapshot"):
                self.capture()
        self.assertEqual(list(self.output.rglob("manifest.json")), [])

    def test_wrong_host_does_not_collect(self):
        out = io.StringIO()
        with patch.object(gate.socket, "gethostname", return_value="LEGION"), \
             patch.object(gate, "snapshot") as snapshot, contextlib.redirect_stdout(out):
            self.assertEqual(gate.main(["--expect-host", "AMD-DESKTOP", "--phase", "before"]), 2)
        snapshot.assert_not_called()
        self.assertEqual(json.loads(out.getvalue())["reason"], "host_mismatch")

    def test_refuse_output_inside_game_root(self):
        with self.assertRaisesRegex(ValueError, "output_overlaps_game_documents"):
            gate.snapshot(self.root, self.root / "backup", "before", "LEGION", "0.2.26")
        self.assertFalse((self.root / "backup").exists())

    def test_missing_savedvariables_is_not_invented(self):
        self.save.unlink()
        result = self.capture()
        self.assertEqual(result["savedVariableFiles"], 0)

    def test_fresh_clone_without_artifacts_parent(self):
        self.output = self.base / "artifacts" / "patch-snapshots"
        self.assertEqual(self.capture()["savedVariableFiles"], 1)

    def test_manifest_write_failure_leaves_no_success_marker(self):
        # Simulate a disk-full/interrupt error after partial JSON was written.
        def interrupted(report, writer, **kwargs):
            writer.write('{"schema":')
            raise OSError("fixture write interrupted")
        with patch.object(gate.json, "dump", side_effect=interrupted):
            with self.assertRaises(OSError):
                self.capture()
        self.assertEqual(list(self.output.rglob("manifest.json")), [])

    def test_verify_retained_snapshot_and_detect_tampered_copy(self):
        result = self.capture()
        directory = self.output / result["artifactDirectory"]
        verified = gate.verify_snapshot(directory, "LEGION", result["manifestSha256"])
        self.assertEqual(verified["status"], "verified")
        self.assertFalse(verified["restored"])
        self.assertFalse(verified["runtimeVerified"])
        with self.assertRaisesRegex(ValueError, "manifest_hash_mismatch"):
            gate.verify_snapshot(directory, "LEGION", "0" * 64)
        with self.assertRaisesRegex(ValueError, "invalid_snapshot_manifest"):
            gate.verify_snapshot(directory, "AMD-DESKTOP", result["manifestSha256"])
        copied = directory / "files" / self.lua.relative_to(self.root)
        copied.write_bytes(b"tampered backup")
        with self.assertRaisesRegex(ValueError, "snapshot_file_hash_mismatch"):
            gate.verify_snapshot(directory, "LEGION", result["manifestSha256"])

    def test_verify_rejects_missing_backup_file(self):
        result = self.capture()
        directory = self.output / result["artifactDirectory"]
        (directory / "files" / self.save.relative_to(self.root)).unlink()
        with self.assertRaisesRegex(ValueError, "snapshot_inventory_mismatch"):
            gate.verify_snapshot(directory, "LEGION", result["manifestSha256"])

    def test_size_limit_blocks_success_receipt(self):
        with patch.object(gate, "MAX_TOTAL", 10):
            with self.assertRaisesRegex(ValueError, "total_size_limit"):
                self.capture()
        self.assertEqual(list(self.output.rglob("manifest.json")), [])


if __name__ == "__main__":
    unittest.main()
