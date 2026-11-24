# RCM Integration Demo

An optional, separate RIFT addon that demonstrates the RCM interfaceVersion 2 API. It is **not** bundled into the main addon package or automatically deployed.

## Installation and acceptance

1. Install RCM v0.2.26 (or a compatible API v2 release) in the verified active RIFT AddOns directory.
2. Copy only this `RCMIntegrationDemo` folder to the same AddOns directory, alongside—not inside—RiftChatModern. The manifest explicitly declares the RCM dependency.
3. Use RIFT's original chat to issue `/reloadui`, then open RCM with `/rcm`.
4. Find exactly one diagnostic **RCM integration demo ready** in the ADDONS tab. It is an addon diagnostic with source RCMIntegrationDemo, not native chat.
5. Use the RCM editor:

| Local command | Result |
|---|---|
| `:rcmdemo status` | Show subscription state, own observed diagnostic count and last retained ID |
| `:rcmdemo ping` | Publish a local diagnostic and report its retained history ID |
| `:rcmdemo stop` | Unsubscribe without deleting retained messages |
| `:rcmdemo start` | Re-enable observation |

The demo waits for a ready compatible interface, never takes over a conflicting command, and tracks only its own diagnostic counts and IDs. It does not post to social channels, change game controls, or collect private message content. Observation state is session-only.

The example's actual scripts are exercised in Lua 5.1 mocks by `tests/test_api_consumer.py`. **Physical RIFT acceptance remains pending.** See [API reference](../../docs/ADDON_API_V2.md) and [development roadmap](../../ROADMAP.md). To remove the example, remove/disable only its own addon through normal game addon management; leave RCM and its character saves intact.
