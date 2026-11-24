# Contributing to RiftChatModern

Thanks for helping improve RCM. The project focuses on a modern in-game
diagnostics window and reusable RIFT Lua addon interfaces.

## Reporting bugs

Open a [GitHub issue](https://github.com/360madden/RiftChatModern/issues)
and include:

- RCM version (from `/rcm status`), RIFT client/build and Windows version.
- Exact steps to reproduce; expected result and actual result.
- Whether the result occurred **inside the physical game** or only in a
  mocked test. These are different evidence levels.
- Relevant addon error text or screenshots. Remove account, character,
  private-message, and personal details before sharing.

## Development workflow

1. Keep changes focused and preserve compatibility with **RIFT Lua 5.1**.
2. If modifying `addon/RiftChatModern`, keep `RiftAddon.toc`, startup
   order, version labels and SavedVariables contracts synchronized.
3. Add a regression test for each root-cause bug fix.
4. Do not describe simulated game behavior as physical acceptance.
5. Update the appropriate technical note in `docs/`.
6. For a live installation, use a verified RIFT addon folder and
   `/reloadui`; do not delete character SavedVariables.

## Running tests

From the repository root, create an isolated Python 3.14 environment and build the Windows sender. A compatible sibling `LuaPadModern` checkout must provide `tools/rift-log-probe.cjs` for host observer tests.

```powershell
py -3.14 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --only-binary=:all: -r requirements-dev.txt
dotnet build tools/RcmEditorSender/RcmEditorSender.csproj -c Release --nologo
& .\.venv\Scripts\python.exe -m unittest discover -s tests
node --test tests/test_chat_import.cjs tests/test_chat_observer.cjs tests/test_chat_observer_cli.cjs tests/test_chat_batch_gate.cjs tests/test_live_say_batch.cjs tests/test_live_say_follow.cjs tests/test_live_public_follow.cjs tests/test_say_delivery.cjs tests/test_public_delivery.cjs tests/test_test_python.cjs tests/test_dotnet_host.cjs tests/test_companion_health.cjs
```

Python 3.14, Node 24 and .NET 10 were verified on LEGION. Test Python can be overridden with an absolute `RCM_TEST_PYTHON` executable; the repo-local `.venv` takes precedence over the legacy sibling environment. The coordinator uses the standard Windows .NET installation, an absolute PATH entry, or an explicit absolute `RCM_DOTNET` override. Invalid explicit paths fail closed. Missing test prerequisites are reported as skips or failures, not silent passes. These developer dependencies are not required for the addon-only installation.

## Code ownership and licensing

The repository is publicly readable. No general-purpose software license
has been selected in this repository yet; do not assume permission to
redistribute derivative versions. Propose licensing changes separately so
the project owner can make that decision explicitly.
