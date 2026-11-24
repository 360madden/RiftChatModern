# RCM — automated offline qualification

Run from the repository root on Windows, using the validated Python 3.14 toolchain, Node 22 and .NET 10 SDK:

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --only-binary=:all: -r requirements-dev.txt
$env:PYTHONUTF8 = '1'
& .\.venv\Scripts\python.exe -B tools/rcm_offline_ci.py
```

The runner builds all three .NET projects serially, discovers Python/Lua and Node suites, requires at least the documented November 24 baseline (367 Python/Lua and 144 Node tests), and refuses skipped/todo tests or incomplete TAP summaries. This is fixture-only qualification. It must never substitute for the physical patch recovery gate, actual RIFT API/log receipts, or character save acceptance. It does not itself launch, deploy or input to RIFT. The CI configuration is intended for a disposable Windows runner with read-only repository permissions, not a self-hosted gaming PC. Adjust test-count floors explicitly only when changes to the documented baseline justify it.

The full runner is not qualified in this session: GitHub clone networking is unavailable in the local Linux environment, no .NET SDK is installed here, and LEGION is disconnected. The new summary parser has standalone regression coverage; integrated execution remains pending.
