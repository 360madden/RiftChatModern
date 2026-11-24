# RCM — automated offline qualification

Run from the repository root on Windows, using Python 3.14, Node 24 and .NET 10 SDK. A sibling `LuaPadModern` directory must provide `tools/rift-log-probe.cjs`; the observer imports this existing decoder directly.

GitHub Actions checks out both repositories side by side. Its decoder is pinned to public LuaPadModern commit `9c65386489f8d1e4c8d81b9ed01c6c22b98e4ecc` (blob `f2b1f6c5565e52c429b23a73d6ae97681e3e2fa2`). This decoder passed the complete offline suites below. It differs from the decoder last qualified on LEGION; CI does not change the production companion-health baseline or establish live decoder compatibility.

```powershell
py -3.14 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --only-binary=:all: -r requirements-dev.txt
$env:PYTHONUTF8 = '1'
& .\.venv\Scripts\python.exe -B tools/rcm_offline_ci.py
```

The runner builds all three .NET projects serially, discovers Python/Lua and Node suites, requires at least the November 24 recovery baseline (387 Python/Lua and 144 Node tests), and refuses skipped/todo tests or incomplete TAP summaries. The Python floor includes 367 prior tests, ten target/config guards, two CI-summary methods, five rollback cases and three backend-factory cases. This is fixture-only qualification. It must never substitute for the physical patch recovery gate, actual RIFT API/log receipts, or character save acceptance. It does not itself launch, deploy or input to RIFT. The CI configuration is intended for a disposable Windows runner with read-only repository permissions, not a self-hosted gaming PC. Adjust test-count floors explicitly only when changes to the documented baseline justify it.

## Verified November 24 Windows result

Code commit [`bd8d40a1ee4ed71b4b676b01e085e1db77ccc8cd`](https://github.com/360madden/RiftChatModern/commit/bd8d40a1ee4ed71b4b676b01e085e1db77ccc8cd) passed both the [pull-request run](https://github.com/360madden/RiftChatModern/actions/runs/45496085182) and the [push run](https://github.com/360madden/RiftChatModern/actions/runs/45496076722), with terminal `success` conclusions.

| Check | Result |
|---|---|
| `RcmEditorInput`, `RcmEditorSender`, `RcmScreenshotKey` | Three Release builds passed; zero warnings/errors |
| Python / Lua 5.1 | 387 passed; zero failures, errors or skips |
| Node | 144 passed; zero failures, cancellations, skips or todo |
| Total | **531 passed** |
| Runner | Windows Server 2025; CPython 3.14.10; Node 24.22.3; .NET SDK 10.0.404 |

The initial [run 45493512689](https://github.com/360madden/RiftChatModern/actions/runs/45493512689) was rejected before jobs started because an unquoted pip command contained a YAML-significant colon. After that and the sibling checkout were corrected, [run 45494659151](https://github.com/360madden/RiftChatModern/actions/runs/45494659151) exposed six native-slash fixture failures from event construction importing an undeclared private module. Event construction now uses the supplied backend's own factory; a complete inert event plan is prepared before focus. No private source was added to CI. The successful runs above include these corrections and the guarded deployment rollback regressions.

The optional live focus/input adapter is still required for actual desktop operations. CI uses injected fixture backends and never establishes physical RIFT acceptance. See the [Tuesday handoff](HANDOFF_20261124_TUESDAY_RECOVERY.md) for the separate patch and installed-addon gates.
