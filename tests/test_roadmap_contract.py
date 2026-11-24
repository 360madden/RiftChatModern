"""Protect the canonical RCM roadmap and its key evidence/priority contracts."""
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROADMAP = ROOT / "ROADMAP.md"
README = ROOT / "README.md"
DOCS_INDEX = ROOT / "docs" / "README.md"
LATEST_HANDOFF = ROOT / "docs" / "HANDOFF_20261123_MONDAY_CLOSEOUT.md"
SUNDAY_HANDOFF = ROOT / "docs" / "HANDOFF_20261122_SUNDAY_CLOSEOUT.md"


def local_markdown_links(source: str):
    """Yield local Markdown link targets; URL fragments are not file paths."""
    for raw in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", source):
        path = raw.split("#", 1)[0].strip()
        if path and not path.startswith(("http://", "https://", "mailto:")):
            yield path


class RoadmapContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.body = ROADMAP.read_text(encoding="utf-8")

    def test_canonical_roadmap_is_discoverable(self):
        self.assertIn("# RiftChatModern (RCM) — Development Roadmap", self.body)
        self.assertIn("[Roadmap](ROADMAP.md)", README.read_text(encoding="utf-8"))
        self.assertIn("../ROADMAP.md", DOCS_INDEX.read_text(encoding="utf-8"))

    def test_referenced_local_evidence_exists(self):
        links = list(local_markdown_links(self.body))
        self.assertGreaterEqual(len(links), 7)
        for link in links:
            with self.subTest(link=link):
                self.assertTrue((ROOT / link).is_file(), link)

    def test_milestones_are_actionable_and_unique(self):
        for milestone in ("M0", "M1", "M2", "M3", "M4", "UX1", "API1", "REL1"):
            with self.subTest(milestone=milestone):
                self.assertRegex(self.body, r"(?m)^### " + re.escape(milestone) + r"\b")
        ids = re.findall(r"RCM-(\d{3}) ·", self.body)
        self.assertGreaterEqual(len(ids), 20)
        self.assertEqual(len(ids), len(set(ids)), "Backlog IDs must be unique")
        for required in ("RCM-010", "RCM-014", "RCM-070", "RCM-084"):
            self.assertIn(required, self.body)

    def test_unsupported_capabilities_are_not_mislabeled(self):
        for boundary in (
            "Full social-chat replacement (conditional stretch goal)",
            "native console setting labels",
            "Guild/Party/Tell",
            "TESTED-OFFLINE",
            "VERIFIED-LIVE",
            "VERIFIED-DISK",
            "physically",
            "NO-GO",
            "never blindly replay",
        ):
            with self.subTest(boundary=boundary):
                self.assertIn(boundary.lower(), self.body.lower())

    def test_latest_handoff_is_durable_and_linked(self):
        self.assertTrue(LATEST_HANDOFF.is_file())
        self.assertIn("docs/" + LATEST_HANDOFF.name, self.body)
        self.assertIn(LATEST_HANDOFF.name, DOCS_INDEX.read_text(encoding="utf-8"))
        self.assertIn("docs/" + LATEST_HANDOFF.name, README.read_text(encoding="utf-8"))
        self.assertTrue(SUNDAY_HANDOFF.is_file(), "Preserve historical handoff")
        handoff = LATEST_HANDOFF.read_text(encoding="utf-8")
        for link in local_markdown_links(handoff):
            with self.subTest(link=link):
                self.assertTrue((LATEST_HANDOFF.parent / link).is_file(), link)
        for expected in ("RCM-010", "RCM-015", "RCM-063", "497 passed", "353 passed", "144 passed", "AMD-DESKTOP", "NOT RUN", "single next success condition"):
            with self.subTest(expected=expected):
                self.assertIn(expected.lower(), handoff.lower())

    def test_roadmap_has_revision_and_operating_instructions(self):
        for label in (
            "2026-11-22",
            "Current project board",
            "Roadmap maintenance policy",
            "Repeatable workflow",
            "Critical path",
            "Acceptance",
        ):
            with self.subTest(label=label):
                self.assertIn(label.lower(), self.body.lower())


if __name__ == "__main__":
    unittest.main()
