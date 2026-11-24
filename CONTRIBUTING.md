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

From the repository root, create an isolated Python 3.14 environment and run the Windows qualification gate. A compatible sibling `LuaPadModern` checkout must provide `tools/rift-log-probe.cjs` for host observer tests. See [offline qualification](docs/OFFLINE_CI.md) for the pinned CI dependency and current results.

```powershell
py -3.14 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --only-binary=:all: -r requirements-dev.txt
& .\.venv\Scripts\python.exe -B tools/rcm_offline_ci.py
```

The gate builds all three .NET 10 Release helpers, sets the actual Python/.NET executable paths for subprocess fixtures, and runs every Python/Lua and Node test. It requires complete results without skips or expected failures. Python 3.14 and Node 24 are the Windows toolchain families. Live focus/input helpers require their separately installed backend; offline fixtures inject an inert backend and do not use the real desktop. These developer dependencies are not required for the addon-only installation.

## Code ownership and licensing

The repository is publicly readable. No general-purpose software license
has been selected in this repository yet; do not assume permission to
redistribute derivative versions. Propose licensing changes separately so
the project owner can make that decision explicitly.
