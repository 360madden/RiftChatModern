"""Offline gate summary tests; no builds, real game or subprocesses."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from rcm_offline_ci import node_summary_ok


class OfflineGateTests(unittest.TestCase):
    def test_complete_baseline(self):
        self.assertTrue(node_summary_ok(
            "# tests 144\n# pass 144\n# fail 0\n# skipped 0\n# todo 0\n"))

    def test_missing_duplicate_skipped_or_truncated_summary(self):
        baseline = "# tests 144\n# pass 144\n# fail 0\n# skipped 0\n# todo 0\n"
        for report in (baseline.replace("# skipped 0\n", ""),
                       baseline + "# skipped 0\n",
                       baseline.replace("# skipped 0", "# skipped 1"),
                       baseline.replace("# todo 0", "# todo 1"),
                       baseline.replace("# pass 144", "# pass 143"),
                       baseline.replace("144", "143"),
                       baseline.replace("# fail 0", "# fail 1")):
            with self.subTest(report=report):
                self.assertFalse(node_summary_ok(report))


if __name__ == "__main__":
    unittest.main()
