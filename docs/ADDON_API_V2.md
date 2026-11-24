# RCM addon API — interface version 2

**Current source:** v0.2.26 (November 23, 2026). **Physical baseline:** v0.2.23. This reference describes the source contract verified in Lua 5.1/RIFT API mocks, not an independently verified v0.2.26 game session.

## Dependency and readiness

Declare the dependency in a consumer's RIFT manifest:

~~~lua
Dependencies = { RiftChatModern = {"required", "before"} }
~~~

Use direct dot calls, not colon calls, to the global API table. Check the interface and readiness during the consumer's `Event.Addon.Load.End` callback. The global table can exist before its SavedVariables have loaded, or after those variables were rejected.

~~~lua
local api = _G.RiftChatModernAPI
if type(api) == "table" and api.interfaceVersion == 2
    and type(api.GetStatus) == "function"
    and api.GetStatus().ready then
    local row, why = api.Publish("addons", "Sampler ready", "MyAddon")
    if not row then
        -- Report why locally; do not claim RCM retained a failed publication.
    end
end
~~~

See the complete, independently installable [RCMIntegrationDemo](../examples/RCMIntegrationDemo/README.md). It uses lifecycle events, checks return values and interface compatibility, avoids duplicate initialization, and does not require an external executable.

## API conventions

- `interfaceVersion` is numeric 2. `version` is the source release string. Additive methods may be introduced within interface 2; feature-detect them when supporting older releases.
- Mutating model operations generally return a true value or result table on success and `nil, error_code` on rejection. Do not treat a rejected call as success. UI functions may have additional focus/window preconditions.
- History, status, color and visibility results are copies or scalar values. Do not mutate the internal addon model or its character SavedVariables.
- The API is synchronous Lua, not a Windows CLI, socket interface, native chat receiver or automatic save service.

## History and local command surface

| Method | Contract |
|---|---|
| `Publish(kind, message, source)` | Return a copied retained row. Supported external kinds: system, npc, addons, dev, combat. Ordinary player-chat kinds are rejected; external publishers cannot mint a native chat row or a host import token. |
| `GetHistory(filter, search, limit, offset)` | Return a list of copied rows and matching total. Nil defaults: current filter/search, limit 50, offset 0. Explicit false or malformed inputs are rejected. Results are chronological within a newest-first page selection. Offset counts backwards from newest matching row. Includes retained rows hidden by the graphical visibility preference. |
| `GetMessage(id)` | Return a copied retained row by stable positive integer ID; return nil/error if invalid or evicted. |
| `OpenMessage(id)` | Open the full-text reader for a retained ID; palette-active view rejects this action. Does not establish native chat focus. |
| `GetSelectedMessage()` | Return copied selected row or nil/error. |
| `CopySelectedMessage()` | Copy the full selected text through the RIFT clipboard API, when available. |
| `CloseMessage()` | Close message detail view. |
| `RegisterCommand(name, callback)` | Register a unique local colon-command. Names must start with a lowercase letter, contain lowercase letters/digits/underscores, and be at most 24 bytes. Built-ins and duplicate names are rejected. The callback receives the argument string. |
| `Submit(text)` | Run a local colon-command; does not transmit ordinary native social chat. Supports local palette commands and explicitly framed manual import commands as well. Do not use for arbitrary native slash commands. |
| `Copy()` | Copy current filtered, visible history (up to 48,000 bytes) through the RIFT clipboard API. |

The history is capped at 240 rows. Each message is 1–512 bytes and each source is 1–40 bytes. Search is at most 60 bytes. Limit is an integer 1–240 and offset a nonnegative integer. Supported filters are all, chat (legacy Imports alias), imports, system, npc, addons, dev and combat. Queries reject invalid arguments rather than silently broadening them. CR/LF in accepted messages are converted to single-line spaces.

A copied row contains `id`, `at`, `kind`, `source`, `text`, `origin`, and optional `channelKind`, `channelName`, `importToken`; `nativePlayerChatVerified` is false. A row ID is unique within retained history and monotonically assigned under the saved sequence contract. Eviction can remove older IDs.

Command registration is session-local (48 total command slots, including registered built-in extensions). A callback may return a response string, false to refuse, or another value to acknowledge without proving an external effect. Exceptions are contained as `extension_error`. A response string is bounded and retained as a local dev/Console record. Prefix command names with a unique addon identifier to avoid collisions.

## Subscriber lifecycle — v0.2.26

| Method | Contract |
|---|---|
| `Subscribe(name, callback)` | Register a named local callback; maximum 48 simultaneous subscriptions. Unique names are 1–40 bytes. |
| `Unsubscribe(name)` | Remove the named subscription; invalid or unknown names are rejected. |
| `GetStatus()` | Return model readiness, version, session listenerCount/listenerErrors, history count, revision, active filter/search, UI geometry, focus, transport/save status and capability boundaries. Native social capture/send flags remain false before and after readiness. |

Callbacks receive separate copied rows. Delivery uses a bounded snapshot of registration identities, sorted by name. A subscription added during dispatch begins on the next top-level publication; a removed or replaced subscription does not receive the pending event. Self-unsubscription is allowed. Callback exceptions increment the session-only error counter and do not stop peers. Reentrant publications are retained but do not recursively fan out to subscribers. Neither registration changes nor error counters mutate SavedVariables. Subscribers should stay fast and avoid side effects that republish indefinitely.

## UI and presentation

| Method | Contract |
|---|---|
| `Show()` / `Hide()` | Show/hide RCM's own window. Showing does not automatically focus chat input. |
| `FocusEditor()` / `FocusSearch()` | Explicitly request and verify addon-owned field focus. Require a visible initialized window. |
| `GetFocusState()` | Current own-window focus classification: focused, search, palette, palette_open, unfocused, unavailable or hidden. Does not infer native RIFT chat focus. |
| `SetWindowSize(width, height)` | Apply finite dimensions, clamp to viewport, persist geometry. |
| `GetChannelColors()` | Fresh map of effective color hex strings for 15 fixed presentation categories. Added v0.2.24. |
| `SetChannelColor(key, value)` | Set validated bright six-digit RGB hex (optional leading #). |
| `ResetChannelColor(key)` | Restore one default or all. |
| `GetChannelVisibility()` | Fresh map of visible boolean preferences. Added v0.2.25. |
| `SetChannelVisible(key, visible)` | Change view-only visibility; strict boolean. Retained history and token reconciliation unchanged. |
| `ResetChannelVisibility()` | Restore all categories. |

Colors, visible history and geometry are character-local. Successful mutations change the model's save revision; no-ops do not. The 15 keys and exact presentation behavior are in the [palette panel contract](V0_2_25_PALETTE_PANEL_20261123.md). A host channel presentation category is not evidence that its corresponding native player-chat feed is supported.

## Optional runtime surfaces

| Method | Contract |
|---|---|
| `GetSaveCheckpointStatus()` | Read Save.Begin/End observation, stored checkpoint and pending changes. Never establishes disk persistence on its own. |
| `GetHostIngressStatus()` | Manual host ingress counters/availability plus retained import count/last ID. Does not prove automatic or native chat reception. |
| `GetNativeConsoles()` | Read-only native console subscription metadata. Not a chat transcript. |
| `GetConsoleMirrorStatus()` | Inspect optional addon-console-output mirroring and hook state. |
| `SetConsoleMirror(enabled)` | Explicit boolean control for optional addon console mirroring. |
| `GetAddonTransportStatus()` | Addon-data transport readiness, queue/acknowledgment counters and pending state. |
| `SendAddon(target, message)` | Submit explicitly addressed addon-data traffic to the RIFT API, if enabled. A server acknowledgment is not peer delivery. Not ordinary player chat. |

## Error handling and compatibility

Check readiness for model methods; handle not_ready, invalid_query, invalid_kind, native_chat_not_available, invalid_text, invalid_source, invalid_command, unknown_local_command, extension_error, extension_refused, invalid_listener, listener_limit and not_found as applicable. Other methods provide specific input/focus/runtime errors. Error codes are not player-visible chat messages. The existing interfaceVersion=2, history schemaVersion=2, host import wire format and original chat fallback remain unchanged.

**Example acceptance:** Lua 5.1 tests load the actual RCM scripts and actual demo Main.lua, simulate lifecycle readiness, verify one startup event, local command response, subscription mutation/cleanup, duplicate-name refusal and provenance. These tests do not demonstrate physical addon-to-addon delivery. See the [v0.2.26 evidence report](V0_2_26_API_INTEGRATION_20261123.md).
