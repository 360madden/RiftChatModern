# RCM v0.2.26 — API v2 integration and subscriber correctness

**Date:** November 23, 2026 (EST) · **Host:** LEGION · **Base:** da7c77d24a5784fb00c2fcac30a572e633b4af71

## Scope

RCM-060: document the actual exported API and provide a runnable separate addon consumer. Physical game qualification remains blocked by AMD-DESKTOP connectivity. The last physically accepted RCM addon is v0.2.23; no new game input or deployment occurred.

## Reproduced defects and corrections

- The v0.2.25 listener registry iterated a mutable table while running external callbacks. A red test observed a newly registered subscriber receiving the very same event: first:one,new:one,second:one. Snapshot registration identity now makes callbacks deterministic, prevents same-event delivery to replacements/additions, and preserves removal and reentrant-publication semantics.
- Session-only listenerCount and listenerErrors expose subscription health without changing history or saved revision. A throwing callback cannot interrupt subsequent peers.
- Invalid explicit false history-query arguments previously became defaults. Only nil now requests defaults; disallowed search control bytes are rejected.
- GetStatus now explicitly reports native social receive/send as false even before SavedVariables readiness, and initializes listener diagnostics.
- Source release increments to v0.2.26. The public interfaceVersion and history schemaVersion remain 2.

## Delivered integration assets

- [Current API v2 reference](ADDON_API_V2.md): all exported methods, lifecycle/readiness, provenance, input bounds, presentation, error and optional transport semantics.
- [Standalone consumer](../examples/RCMIntegrationDemo/README.md): manifest dependency, local diagnostics, local commands, duplicate-safe initialization, subscription start/stop, own-event counts. This example is not included in the normal RCM deployment.
- New tests execute actual Lua modules, including the example. Five initial regression tests reproduced the old behavior or missing diagnostic contract before the fixes. All 12 focused tests passed. Final full regression: **353 Python/Lua + 129 Node = 482 passed, zero failures or skips**. Python/Lua completed in 47.553s, Node in 7.393s. Git diff check passed. This is source/mock/host-fixture evidence only; no physical RIFT deployment or integration acceptance is implied.

## Next

RCM-060 source/API documentation and consumer testing are the offline deliverables. RCM-061 requires a real addon-to-addon game smoke test. Preserve the original chat fallback and independent disk acceptance. M1 remains the highest-impact physical gate.
