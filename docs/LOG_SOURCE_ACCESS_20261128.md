# RCM — log readability, refusal diagnostics and capture deadlines

**Date:** November 28, 2026 (Asia/Manila / PHT). **Baseline:** `64e81806a9c295a55dac553e6e91f2f6b81c6f66`. This change addresses the source-access failure recorded in the [Saturday LEGION handoff](HANDOFF_20261128_SATURDAY_LEGION.md).

## Observed failure and root causes

The configured noncombat `Log.txt` existed and Windows could read its size and modification time, but opening its bytes failed. The original session preflight therefore incorrectly reported `canAttemptSupervisedLogTest: true`. The follower then refused its EOF baseline, and the delivery coordinator reduced the failure to `follower_failed_or_interrupted`, losing the available read-error code.

At 06:52 PHT, LEGION's existing OneDrive process was running. A fresh isolated Python byte read failed with `errno=22` and no Windows error code. At 06:57 PHT, an independent .NET read again failed with HRESULT **0x8007016A**, while OneDrive and the Windows cloud-file filter driver were both running. The .NET result confirms the source-access problem remains. Python `errno=22` and Node `UNKNOWN` alone do not identify its cause.

The startup failure also exposed two related defects: raw startup exceptions could include account paths in stderr, and the follower's own timer could not fire while its synchronous file read was stalled. Its timer also started only after the baseline read.

## Preflight contract

Candidate inspection still collects metadata only. Readiness now requires a separate byte probe of an eligible noncombat log. With an explicit client `DocumentsDirectory`, only its exact `Log.txt` is eligible; a readable old file elsewhere cannot qualify the configured source.

The probe runs in an isolated Python child with a **three-second execution timeout**. It checks the leaf and opened object are regular files, reads at most **one unbuffered byte**, closes the descriptor, and discards the byte. Empty files are readable. Leaf symlinks are refused, matching the follower's existing policy. Child failure, timeout, malformed JSON, unexpected fields and contradictory results all block readiness.

Reports include fixed `readError` tokens and available numeric `readErrno` / `readWinerror` values, never raw exception text or log content. A Windows error of 362 or HRESULT 0x8007016A can identify `cloud_file_provider_not_running`; a generic error without that Windows code remains `unavailable`.

| Observation | Preflight result |
|---|---|
| Configured file exists and passes the byte probe | May attempt a supervised log test if other prerequisites pass |
| Configured file exists but cannot be read | `configured_log_not_readable` blocker |
| No configured file exists | Existing configured-source missing blocker |
| No explicit root and all existing noncombat candidates fail reading | `no_readable_log_file_found_in_known_paths` blocker |
| Probe does not finish within three seconds | `probe_timeout`; readiness remains false |

A successful probe proves basic readability at that moment. It does not prove log freshness, current runtime logging state, a clean follower EOF baseline, authentic chat reception or game acceptance. Existing parent-process configuration reads and candidate-metadata checks remain outside the child timeout; the entire preflight does not have a new global deadline.

## Capture diagnostics and deadlines

The follower emits a structured `refused` receipt for startup failures. It contains the exact profile, fixed source label, allowlisted reason and read-error code, and false input/delivery/save flags. Startup errors are sanitized and any opened tailer is closed. The coordinator accepts one exact-schema refusal only before `started`; malformed, duplicate, wrong-profile or later refusals cannot authorize observations or transfers. The validated reason and read code appear in `capture_finished`. Raw stderr remains private and is not copied into the public receipt.

Coordinator capture now supervises the child independently. Its deadline is **the requested `--timeout-ms` plus 5,000 ms for startup and exit**. It remains active until child closure, including after a `finished` receipt. Expiry forces a failed session and quarantines any batches already received. The coordinator requests forced termination, then allows **2,000 ms** to observe closure. If closure remains unconfirmed, it detaches the read-only child's pipes, records failure and reports `followerTerminationConfirmed: false`. No automatic retry or dispatch occurs.

These deadlines apply to coordinator `capture`. Direct standalone follower invocations retain their own event-loop timer and should be externally supervised when diagnosing stalled storage. Parent journal/lock filesystem operations are also outside the child-capture deadline.

## Verification

- Four preflight regression methods reproduced false readiness against the previous code. All **30 preflight tests** passed after the correction; the combined deployment and preflight suites passed **60/60**.
- Five Node diagnostic/privacy/cleanup regressions failed against the previous code. Three additional deadline regressions cover a child stalled before startup, a child that queues a batch and reports finished but never exits, and termination that cannot be confirmed.
- All **eight new Node tests** passed without skips in the targeted portable run, and an independent reviewer checked the error and deadline boundaries.
- At **07:01:39 PHT on LEGION**, the corrected preflight returned exit 2 and `canAttemptSupervisedLogTest: false` for the actual configured 5,246-byte log, with blocker `configured_log_not_readable`, `readError: unavailable` and `readErrno: 22`. Input, logging-change and live-reception flags were false. This confirms the original false-readiness defect is fixed on the affected machine.
- The Windows offline gate now requires at least **395 Python/Lua and 152 Node tests**, with no skipped/todo acceptance. Complete Windows qualification is recorded in the [offline CI report](OFFLINE_CI.md).

The installed addon, source addon version and SavedVariables contract are outside this host-tool change. Current source access must become readable before another supervised logging or live import acceptance session.
