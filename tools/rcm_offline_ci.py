"""RCM offline qualification gate for Windows runners and development PCs.

This invokes the existing fixture suites, not a physical RIFT acceptance test.
Do not treat successful builds, mocks or fixtures as proof of runtime behavior.
Run with the isolated Python 3.14 environment and Node/.NET 10 on PATH.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
# November 28 packaging baseline: 399 compatibility methods + 10
# addon package regressions; 152 existing Node tests.
# A silently skipped or missing suite must not qualify as a clean result.
MIN_PYTHON_TESTS = 409
MIN_NODE_TESTS = 152


def node_summary_ok(output: str) -> bool:
    """Require one complete TAP summary, a meaningful count and zero skips."""
    counts = {}
    for key in ("tests", "pass", "fail", "skipped", "todo"):
        values = re.findall(r"(?m)^# " + key + r" (\d+)\r?$", output)
        if len(values) != 1:
            return False
        counts[key] = int(values[0])
    return (counts["tests"] >= MIN_NODE_TESTS
            and counts["pass"] == counts["tests"]
            and counts["fail"] == counts["skipped"] == counts["todo"] == 0)


def main() -> int:
    if os.name != "nt" or sys.version_info[:2] != (3, 14):
        print("Full RCM offline gate requires Windows and Python 3.14.", file=sys.stderr)
        return 2
    node = shutil.which("node")
    dotnet = shutil.which("dotnet")
    if not node or not dotnet:
        print("Missing Node or .NET SDK on PATH.", file=sys.stderr)
        return 2
    os.chdir(ROOT)
    # Use the same verified interpreter in Node's Python-backed fixtures,
    # rather than silently depending on a sibling repository's environment.
    os.environ["RCM_TEST_PYTHON"] = str(Path(sys.executable).absolute())
    os.environ["RCM_DOTNET"] = str(Path(dotnet).absolute())
    try:
        # Build serially; Python and Node fixtures consume Release outputs.
        for project in ("RcmEditorInput", "RcmEditorSender", "RcmScreenshotKey"):
            subprocess.run([dotnet, "build", str(ROOT / "tools" / project / (project + ".csproj")),
                            "-c", "Release", "--nologo"], check=True, timeout=300)
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        python_ok = (result.wasSuccessful() and result.testsRun >= MIN_PYTHON_TESTS
                     and not result.skipped and not result.expectedFailures)
        print(f"Python/Lua qualification: {result.testsRun} tests; "
              f"{len(result.skipped)} skipped; gate={'pass' if python_ok else 'fail'}", flush=True)
        files = sorted((ROOT / "tests").glob("test_*.cjs"))
        if not files:
            raise RuntimeError("No Node test files discovered")
        # Explicit paths work in PowerShell and avoid glob expansion differences.
        node_result = subprocess.run([node, "--test", "--test-reporter=tap",
                                      *map(str, files)], stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, text=True,
                                     encoding="utf-8", errors="replace", timeout=300)
        print(node_result.stdout, flush=True)
        node_ok = node_result.returncode == 0 and node_summary_ok(node_result.stdout)
        print("Node qualification: " + ("pass" if node_ok else "fail"), flush=True)
        return 0 if python_ok and node_ok else 1
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Offline gate blocked: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
