"""Read-only RIFT screenshot receipt tests; all images are temporary fixtures.

No RIFT input, focus, logging changes, SavedVariables edits, or source image
writes. Real game screenshots are checked separately without changing them.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
import unittest

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import rcm_game_screenshot_receipt as shot


class ScreenshotReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rcm-screenshot-fixture-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.folder = self.base / "Redirected Documents" / "RIFT" / "Screenshots"
        self.folder.mkdir(parents=True)
        self.config = self.base / "Roaming" / "RIFT" / "Rift.cfg"
        self.config.parent.mkdir(parents=True)
        self.config.write_text(
            "[Other]\nDocumentsDirectory = C:/Unrelated\n[Client]\n"
            "DocumentsDirectory = " +
            str(self.folder.parent).replace("\\", "/") + "\n",
            encoding="utf-8",
        )
        self.args = ["--expect-host", socket.gethostname(), "--config", str(self.config)]

    def image(self, name="2026-11-20_225100.jpg", fmt="JPEG"):
        file = self.folder / name
        Image.new("RGB", (420, 260), (90, 40, 120)).save(file, format=fmt)
        return file

    def invoke(self, *args):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            exit_code = shot.run([*self.args, *args])
        record = json.loads(stream.getvalue())
        self.assertFalse(record["gameInputSent"])
        self.assertFalse(record["filesChanged"])
        self.assertFalse(record["physicalRiftOriginVerified"])
        return exit_code, record

    def test_existing_image_inspects_real_jpeg_bytes_not_filename_only(self):
        file = self.image()
        data = file.read_bytes()
        rc, result = self.invoke()
        self.assertEqual(rc, 0)
        self.assertEqual(result["status"], "existing_screenshot_file")
        self.assertFalse(result["freshnessVerified"])
        self.assertEqual(result["screenshot"]["filename"], file.name)
        self.assertEqual((result["screenshot"]["width"], result["screenshot"]["height"]), (420, 260))
        self.assertEqual(result["screenshot"]["format"], "JPEG")
        import hashlib
        self.assertEqual(result["screenshot"]["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(file.read_bytes(), data)

    def test_baseline_and_require_new_are_distinct_operations(self):
        self.image()
        rc, baseline = self.invoke("--baseline")
        self.assertEqual(rc, 0)
        self.assertEqual(baseline["status"], "baseline_recorded")
        self.assertGreater(baseline["baselineEpochNs"], 0)
        rc, no_change = self.invoke("--after-ns", str(baseline["baselineEpochNs"]),
                                    "--require-new")
        self.assertEqual(rc, 2)
        self.assertEqual(no_change["status"], "no_new_screenshot")
        self.assertFalse(no_change["freshnessVerified"])
        time.sleep(.02)
        file = self.image("2026-11-20_225101.jpg")
        rc, newly_created = self.invoke("--after-ns", str(baseline["baselineEpochNs"]),
                                        "--require-new")
        self.assertEqual(rc, 0)
        self.assertTrue(newly_created["freshnessVerified"])
        self.assertEqual(newly_created["screenshot"]["filename"], file.name)

    def test_selects_newest_eligible_screenshot_not_oldest(self):
        old = self.image("2026-11-20_225100.jpg")
        time.sleep(.03)
        new = self.image("2026-11-20_225101.jpg")
        cutoff = old.stat().st_mtime_ns
        rc, result = self.invoke("--after-ns", str(cutoff), "--require-new")
        self.assertEqual(rc, 0)
        self.assertEqual(result["screenshot"]["filename"], new.name)
        self.assertGreater(result["screenshot"]["modifiedEpochNs"], cutoff)

    def test_unrelated_image_name_does_not_replace_rift_screenshot(self):
        valid = self.image("2026-11-20_225100.jpg")
        time.sleep(.03)
        self.image("personal_photo.jpg")
        rc, result = self.invoke()
        self.assertEqual(rc, 0)
        self.assertEqual(result["screenshot"]["filename"], valid.name)

    def test_corrupted_image_and_mismatched_format_fail_closed(self):
        file = self.folder / "2026-11-20_225100.jpg"
        file.write_bytes(b"not a real image" * 50)
        with self.assertRaisesRegex(shot.ScreenshotReceiptError, "corrupted"):
            shot.inspect_folder(self.folder)
        file.unlink()
        png = self.image("2026-11-20_225100.jpg", fmt="PNG")
        with self.assertRaisesRegex(shot.ScreenshotReceiptError, "extension_format_mismatch"):
            shot.inspect_folder(self.folder)
        self.assertTrue(png.is_file())

    def test_wait_for_new_image_after_boundary_works_with_real_file_creation(self):
        rc, baseline = self.invoke("--baseline")
        self.assertEqual(rc, 0)
        def create_later():
            time.sleep(.12)
            self.image("2026-11-20_225159.jpg")
        worker = threading.Thread(target=create_later)
        worker.start()
        try:
            code, result = self.invoke("--after-ns", str(baseline["baselineEpochNs"]),
                                       "--require-new", "--wait-ms", "1500")
        finally:
            worker.join(timeout=3)
        self.assertEqual(code, 0)
        self.assertTrue(result["freshnessVerified"])
        self.assertEqual(result["screenshot"]["filename"], "2026-11-20_225159.jpg")

    def test_refuses_unbound_or_untrusted_operations_without_writes(self):
        for switches in (
            ["--require-new"],
            ["--wait-ms", "10"],
            ["--baseline", "--after-ns", "2"],
            ["--wait-ms", "15001", "--after-ns", "2", "--require-new"],
        ):
            with self.subTest(switches=switches):
                code, result = self.invoke(*switches)
                self.assertEqual(code, 1)
                self.assertEqual(result["status"], "refused")
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = shot.run(["--expect-host", "INCORRECT-HOST", "--config", str(self.config)])
        self.assertEqual(code, 1)
        self.assertFalse(json.loads(stream.getvalue())["gameInputSent"])

    def test_invalid_config_and_missing_folder_do_not_fall_back_to_other_images(self):
        self.config.write_text("[Client]\nDocumentsDirectory = relative\n", encoding="utf-8")
        code, result = self.invoke()
        self.assertEqual(code, 1)
        self.assertEqual(result["reason"], "documents_directory_not_absolute")
        self.config.write_text("[Client]\nDocumentsDirectory = " +
                               str(self.base / "missing").replace("\\", "/") + "\n",
                               encoding="utf-8")
        code, result = self.invoke()
        self.assertEqual(code, 1)
        self.assertEqual(result["reason"], "screenshots_folder_not_available")


if __name__ == "__main__":
    unittest.main()
