# RCM — automated offline qualification

Run from the repository root on Windows, using Python 3.14, Node 24 and .NET 10 SDK. A sibling `LuaPadModern` directory must provide `tools/rift-log-probe.cjs`; the observer imports this existing decoder directly.

GitHub Actions checks out both repositories side by side. Its decoder is pinned to public LuaPadModern commit `9c65386489f8d1e4c8d81b9ed01c6c22b98e4ecc` (blob `f2b1f6c5565e52c429b23a73d6ae97681e3e2fa2`). This CI candidate differs from the decoder last qualified on LEGION; CI does not change the production companion-health baseline or establish live decoder compatibility.

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --only-binary=:all: -r requirements-dev.txt
$env:PYTHONUTF8 = '1'
& .\.venv\Scripts\python.exe -B tools/rcm_offline_ci.py
```

The runner builds all three .NET projects serially, discovers Python/Lua and Node suites, requires at least the documented November 24 baseline (367 Python/Lua and 144 Node tests), and refuses skipped/todo tests or incomplete TAP summaries. This is fixture-only qualification. It must never substitute for the physical patch recovery gate, actual RIFT API/log receipts, or character save acceptance. It does not itself launch, deploy or input to RIFT. The CI configuration is intended for a disposable Windows runner with read-only repository permissions, not a self-hosted gaming PC. Adjust test-count floors explicitly only when changes to the documented baseline justify it.

The first workflow attempt, [run 45493512689](https://github.com/360madden/RiftChatModern/actions/runs/45493512689), was rejected before jobs started because an unquoted pip command contained a YAML-significant colon. The command now uses a block scalar, and the required sibling checkout is explicit. Integrated Windows execution remains pending until a complete run is recorded. Local Linux checks are supporting evidence and do not replace this gate.
