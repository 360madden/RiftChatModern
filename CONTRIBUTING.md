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

On the project's configured Windows development workstation:

```powershell
& "C:\work\riftreader2\.venv\Scripts\python.exe" -m unittest discover -s tests
node --test tests/test_chat_import.cjs tests/test_chat_observer.cjs tests/test_chat_observer_cli.cjs tests/test_chat_batch_gate.cjs
```

The Python path is specific to that workstation. The Python suite requires
Lua 5.1 support via Lupa; host tooling tests additionally use Node.js and
the .NET 10 SDK.

## Code ownership and licensing

The repository is publicly readable. No general-purpose software license
has been selected in this repository yet; do not assume permission to
redistribute derivative versions. Propose licensing changes separately so
the project owner can make that decision explicitly.
