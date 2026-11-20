# RiftChatModern v0.2.2 — live RIFT addon startup error recovery

AMD-DESKTOP · November 20, 2026

## First physical acceptance failure

The player supplied RIFT screenshots after loading RiftChatModern 0.2.1. The native addon error dialog and chat showed exactly four startup-file errors, all with:

- Error: Unknown: assertion failed!
- Stack traceback [C]: in function 'assert'
- Source modules: Core.lua, AddonMessages.lua, NativeChatProbe.lua, ConsoleMirror.lua.

The real game's same-session SavedVariables file contained the RiftChatModern "Modern chat window ready" startup message, confirming that the main addon loaded and initialized its history model. Thus a startup chat message alone does not mean a zero-error addon load.

## Fault isolation

All four error-producing source files had one common startup pattern: they assigned their module to a named global and then ended with a top-level return of a module table. RIFT RunOnStartup scripts are not Lua require() modules. Working installed addons RiftReader2 and RRECollector export via shared private/global scope without returning module tables.

The RIFT loader's internal assertion logic is not visible, so this is a strong compatibility hypothesis, **not yet a live-proven root cause**.

## v0.2.2 change

All four helper files still export the same global symbols but now return no values when executed as startup chunks. The public RiftChatModernAPI interface, draggable window, fonts, message history and UI, SavedVariables schema, addon-data identifier, and opt-in console mirror remain unchanged.

A new test file, tests/test_rift_startup_contract.py, executes the five manifest RunOnStartup chunks with the actual two addon arguments and verifies each returns nil; it also verifies the named globals and model initialization.

## Physical acceptance still pending

After deploying v0.2.2, the game must load the new files. An actual fix is confirmed only when those four startup assertions no longer appear, the v0.2.2 chat initialization appears, and /rcm can show its window.

Offline Lua 5.1 tests cannot prove the game's loader behavior. No native RIFT data, chat history, or SavedVariables need removal. The original v0.2.1 source files remain recoverable in local Git commit 42bfdad.

No game input or /reloadui was executed as part of the source changes.
