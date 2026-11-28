# RCM — automated offline qualification

Run from the repository root on Windows, using Python 3.14, Node 24 and .NET 10 SDK. A sibling `LuaPadModern` directory must provide `tools/rift-log-probe.cjs`; the observer imports this existing decoder directly.

GitHub Actions checks out both repositories side by side. Its decoder is pinned to public LuaPadModern commit `9c65386489f8d1e4c8d81b9ed01c6c22b98e4ecc` (blob `f2b1f6c5565e52c429b23a73d6ae97681e3e2fa2`). This decoder passed the complete offline suites below. It differs from the decoder last qualified on LEGION; CI does not change the production companion-health baseline or establish live decoder compatibility.

```powershell
py -3.14 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --only-binary=:all: -r requirements-dev.txt
$env:PYTHONUTF8 = '1'
& .\.venv\Scripts\python.exe -B tools/rcm_offline_ci.py
```

The runner builds all three .NET projects serially, discovers Python/Lua and Node suites, requires at least the November 28 packaging baseline (**409 Python/Lua and 152 Node tests**), and refuses skipped/todo tests or incomplete TAP summaries. This includes the source-access and historical-release compatibility guards below plus ten [addon packaging regressions](ADDON_PACKAGE.md). After the regression gate passes, GitHub CI builds and rechecks the addon-only ZIP and retains it with its checksum. The previous LEGION and hosted results remain historical; verify the new workflow result independently. This is fixture-only qualification. It must never substitute for the physical patch recovery gate, actual RIFT API/log receipts, or character save acceptance. It does not itself launch, deploy or input to RIFT. The CI configuration is intended for a disposable Windows runner with read-only repository permissions, not a self-hosted gaming PC. Adjust test-count floors explicitly only when changes to the documented baseline justify it.

## Verified November 28 compatibility result

At 07:27:39 PHT, the full LEGION Windows gate passed on the compatibility candidate based on `7dd85d2`: **399 Python/Lua + 152 Node = 551 tests**, zero failures/skips/todo, and all three Release builds with zero warnings/errors. Historical fixture regeneration matched the committed fixture bytes. Job: `rcm-20261128-release-compat-full-gate`. See [release compatibility](RELEASE_COMPATIBILITY_20261128.md). Prior source-access qualification remains recorded below. Hosted CI for the subsequent commit must be checked independently.

## Verified November 28 LEGION result

The [source-access corrections](LOG_SOURCE_ACCESS_20261128.md), based on `64e81806a9c295a55dac553e6e91f2f6b81c6f66`, passed the complete gate on LEGION from **07:01:41 to 07:03:35 PHT**. Durable validation job: `rcm-20261128-source-gate-01`; applied source patch: `rcm-20261128-source-access-01`. Exit code was 0 and the retained output was complete.

| Check | Result |
|---|---|
| `RcmEditorInput`, `RcmEditorSender`, `RcmScreenshotKey` | Three Release builds passed; zero warnings/errors |
| Python / Lua 5.1 | **395 passed**; zero failures, errors or skips |
| Node | **152 passed**; zero failures, cancellations, skips or todo |
| Total | **547 passed** |
| LEGION toolchain | CPython 3.14.10; Node 24.20.0; .NET SDK 10.0.403 |

A separate read-only check at 07:01:39 PHT verified the corrected preflight against the actual inaccessible configured log: exit 2, `configured_log_not_readable`, `canAttemptSupervisedLogTest: false`. This is physical source-access evidence, not successful log reception or imported-chat acceptance.

The prior published checkpoint `64e8180` also passed [GitHub run 46077473266](https://github.com/360madden/RiftChatModern/actions/runs/46077473266): 387 Python/Lua and 144 Node tests, with three clean builds. The 547-test result above is the new LEGION qualification; hosted results for subsequent commits are listed in the [offline workflow](https://github.com/360madden/RiftChatModern/actions/workflows/offline-regression.yml).

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

The optional live focus/input adapter is still required for actual desktop operations. CI uses injected fixture backends and never establishes physical RIFT acceptance. See the [Saturday handoff](HANDOFF_20261128_SATURDAY_LEGION.md) for current source-access and installed-addon gates; the [Tuesday handoff](HANDOFF_20261124_TUESDAY_RECOVERY.md) preserves the earlier recovery evidence.
