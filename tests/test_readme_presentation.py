"""Public GitHub landing page: local links, branding, real screenshot and docs."""
from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree
import unittest
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
DOCS = ROOT / "docs" / "README.md"
BANNER = ROOT / "assets" / "rcm-banner.svg"
LOGO = ROOT / "assets" / "rcm-logo.svg"
SCREENSHOT = ROOT / "assets" / "screenshots" / "rcm-v0.2.2-physical-names-redacted.png"
CURRENT_SCREENSHOT = ROOT / "assets" / "screenshots" / "rcm-v0.2.22-native-console-live-cropped.jpg"
ARCHIVE = ROOT / "docs" / "ENGINEERING_ARCHIVE_README_THROUGH_20261121.md"


def local_links(markdown: str):
    # GitHub Markdown links, excluding remote and fragment-only URLs.
    for target in re.findall(r"!?(?:\[[^\]]*\])\(([^)]+)\)", markdown):
        target = target.split("#", 1)[0]
        if target and not target.startswith(("https://", "http://", "mailto:")):
            yield target


class ReadmePresentationTests(unittest.TestCase):
    def test_every_local_readme_link_exists(self):
        for document in (README, DOCS):
            with self.subTest(document=document.name):
                body = document.read_text(encoding="utf-8")
                for target in local_links(body):
                    with self.subTest(target=target):
                        self.assertTrue((document.parent / target).exists(), target)

    def test_svg_branding_is_valid_and_accessible(self):
        for file in (BANNER, LOGO):
            with self.subTest(asset=file.name):
                root = ElementTree.parse(file).getroot()
                self.assertTrue(root.tag.endswith("svg"))
                self.assertTrue(root.attrib.get("viewBox"))
                self.assertTrue(root.attrib.get("role") or root.attrib.get("aria-label"))
                self.assertLess(file.stat().st_size, 20000)

    def test_historical_screenshot_is_retained_but_not_homepage_image(self):
        self.assertTrue(SCREENSHOT.is_file())
        with SCREENSHOT.open("rb") as image:
            self.assertEqual(image.read(8), bytes([137, 80, 78, 71, 13, 10, 26, 10]))
        body = README.read_text(encoding="utf-8")
        self.assertIn("redacted v0.2.2 image", body)
        self.assertIn("rcm-v0.2.2-physical-names-redacted.png", body)
        self.assertNotIn('src="assets/screenshots/rcm-v0.2.2-physical-names-redacted.png"', body)
        self.assertNotIn('src="assets/screenshots/rcm-v0.2.2-physical.png"', body)

    def test_current_homepage_is_real_privacy_cropped_v022_jpeg(self):
        self.assertTrue(CURRENT_SCREENSHOT.is_file())
        with Image.open(CURRENT_SCREENSHOT) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertEqual(image.size, (975, 810))
            image.verify()
        body = README.read_text(encoding="utf-8")
        self.assertIn('src="assets/screenshots/rcm-v0.2.22-native-console-live-cropped.jpg"', body)
        self.assertIn("v0.2.22", body)
        self.assertIn("exclude the player name and private HUD", body)
        self.assertIn("Historical real RIFT Live screenshot", body)

    def test_social_preview_png_is_valid_size(self):
        preview = ROOT / "assets" / "rcm-social-preview.png"
        self.assertTrue(preview.is_file())
        with preview.open("rb") as image:
            header = image.read(24)
        self.assertEqual(header[:8], bytes([137, 80, 78, 71, 13, 10, 26, 10]))
        self.assertEqual(int.from_bytes(header[16:20], "big"), 1280)
        self.assertEqual(int.from_bytes(header[20:24], "big"), 640)

    def test_engineering_history_was_preserved(self):
        self.assertTrue(ARCHIVE.is_file())
        text = ARCHIVE.read_text(encoding="utf-8")
        self.assertIn("## v0.2.19", text)
        self.assertIn("## Universal addon API", text)
        self.assertGreater(len(text), 50000)
        self.assertIn("docs/ENGINEERING_ARCHIVE_README_THROUGH_20261121.md",
                      README.read_text(encoding="utf-8"))

    def test_product_limitations_are_clear_on_homepage(self):
        body = README.read_text(encoding="utf-8")
        self.assertIn("not yet a complete replacement", body)
        self.assertIn("Native player social chat", body)
        self.assertIn("not yet", body)


if __name__ == "__main__":
    unittest.main()
