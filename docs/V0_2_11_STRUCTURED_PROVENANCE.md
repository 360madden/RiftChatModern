# RCM v0.2.11 — Fix the source/channel classification at the data-model boundary

**Date:** Friday, November 20, 2026 (America/New_York)
**Canonical project:** `C:\work\RiftChatModern`
**Verified Windows host:** AMD-DESKTOP
**Original live issue:** A manually imported `RCMTest` message was stored as `kind="guild"`, so RCM's transcript, filters, callbacks and exports could misleadingly identify it as native Guild chat. The live screenshot and chat export demonstrated that the import itself worked, not that normal Guild reception worked.

## Root cause

RCM v0.2.10 had only one field for two independent facts:

- **Message origin:** a manually pasted Windows host record with no verified native game-chat reception.
- **Claimed social channel:** `Guild`, `Party`, `Tell` or another channel supplied within the host import.

The host-to-Lua `HostIngress.lua` decoder mapped incoming channel code `G` directly to `kind="guild"`, prepended `[HOST? Guild]` to the body text, and published that string as a normal Guild row. Changing only the UI label would leave wrong data for all subscribers, saved history, filters, clipboard exports and dependent addons.

## New canonical representation

**SavedVariables schemaVersion 2** stores structured provenance and keeps the *message family* distinct from the *claimed channel*.

For manually imported Guild data:

```lua
{
  kind = "import",
  origin = "host_manual",
  channelKind = "guild",
  channelName = "Guild",
  source = "RCMTest",
  text = "RCM 0.2.10 live import check"
}
```

The previous `kind="guild"` is no longer emitted for a host import. A channel name does not grant native-chat credibility. The new model's `publish("guild", ...)`, `publish("party", ...)`, `publish("tell", ...)` and `publish("general", ...)` all reject with `native_chat_not_available` until genuine native player-chat reception is implemented.

The canonical `kind="import"` is returned by `GetHistory`, `GetMessage`, and `Subscribe` listeners. A row returned by the model includes `origin`, `channelKind`, `channelName`, and `nativePlayerChatVerified=false`; callers get isolated copies, not mutable saved history.

Other producers preserve explicit origin where appropriate: `game_event` for NPC/notify callbacks, `local_addon` for RCM startup and internal commands, `addon_data` for RIFT addon messages, and `external_api` for ordinary third-party publication. `legacy_unknown` labels pre-existing records that never carried dependable provenance. No source can imply unverified ordinary social-chat reception is genuine.

## Visual, clipboard and filter behavior

- Normal compact rows: `SYSTEM`, `NPC`, `ADDONS`, `DEV`, etc.
- Host-imported rows: **`HOST/GUILD`**, **`HOST/PARTY`**, **`HOST/TELL`**, **`HOST/PUBLIC`**. These are concise, not truncated `HOST IMPORT / Gui...` labels.
- A message detail title and history export use the full **`HOST IMPORT / Guild`** label; native-style `[guild]` is never emitted for imported data.
- A **separate IMPORTS tab** filters explicit imported records. The CHAT tab includes imported conversation *content*, but every row clearly carries its unverified origin. Searching by channel or provenance works.
- Copying an imported record adds its structured provenance label; it does not silently convert it back to Guild chat.

## Migration and dependencies

**One-way, validated migration from schema 1 to schema 2**, performed only when RCM actually loads the new Core module:

1. Validate every stored record, sequence and limit before changing anything.
2. Existing schema-1 `[HOST? Guild] ...` rows become `kind="import"`, `origin="host_manual"`, `channelKind="guild"`, `channelName="Guild"`, with the original body preserved and old prefix removed.
3. Schema-1 social rows without that known import marker become `kind="import"` with `origin="legacy_unknown"` instead of claiming verified player chat.
4. Other valid schema-1 records retain their original ID, timestamp, source, kind and body; their origin becomes `legacy_unknown`.
5. After **all** records validate, the model installs the migrated array and advances to schemaVersion 2 in one step. Any malformed saved history returns a failure **without editing the schema or history**.
6. Reopening schemaVersion 2 is idempotent. Character UI geometry, search/filter preferences, extra user data and Next ID remain preserved.

**Breaking consumer contract:** `RiftChatModernAPI.interfaceVersion` advances to **2**, since `kind="guild"` previously carried ambiguous meaning. Existing consumers should check `interfaceVersion==2`, use `GetHistory("imports",...)` or the CHAT filter, and inspect `kind`, `origin`, `channelKind` and `channelName`. Do not filter `GetHistory("guild")` or publish `kind="guild"` through the generic API. The manual Windows JSON/base64url/RCM slash protocol remains unchanged.

RR2 and LuaPadModern source scans found **no direct `RiftChatModernAPI` consumers**, but this does not rule out all third-party code; public interface version 2 explicitly communicates the change.

## SavedVariables protection

Before starting work, a SHA-256-verified backup of the **existing on-disk file** was made under the ignored local project directory:

`artifacts/savedvariables-backups/RiftChatModern-before-origin-migration-20261120T182455Z.lua`

This is a backup of the disk contents as they existed at that time, **not a snapshot of unsaved live RIFT memory**. The user provided the current 35-message clipboard export, including the imported Guild test, and we added a synthetic 35-record regression fixture with that provenance shape.

The migration changes the RIFT character's persisted schema. **Do not downgrade to RCM v0.2.10 without restoring a compatible pre-migration SavedVariables backup.** Rollback needs to account for messages generated after that backup and could lose newer rows; do not overwrite the live saved file casually.

## Validation and acceptance

- **138/138 Python/Lua 5.1 tests** and **27/27 Node.js tests** passed against the versioned v0.2.11 source (165 total).
- Six new provenance-specific tests cover 35-record migration, timestamp/source/ID preservation, fail-closed atomic migration, legacy uncertainty, input validation, front-end labels, clipboard, filters, and immutable subscriber copies.
- Existing import tests were updated to validate `kind="import"` and separate claimed channels instead of asserting misleading Guild/Party/Tell kinds.
- An unrelated real Windows dependency defect was also corrected in the test harness: its Node subprocess now explicitly uses UTF-8 for input/output instead of the default Windows code page, preventing silent Unicode corruption in fixtures.
- Correct Lua 5.1 `RunOnStartup` no-return-value behavior and the RIFT six-file `.toc` metadata are preserved.
- **Physical v0.2.10 manual import acceptance already passed**, with a screenshot held locally and excluded from GitHub. **v0.2.11 migration/live UI acceptance is a separate checkpoint.**

## Physical acceptance procedure

After deployment and a deliberate RIFT `/reloadui`, check:

1. `Rift Chat Modern v0.2.11` loads without addon error.
2. Existing 35-message history is retained, and the imported RCMTest record is shown as **HOST/GUILD**, not **GUILD**.
3. IMPORTS contains the record; CHAT includes it as imported content.
4. Detail view and copy/export use **HOST IMPORT / Guild**.
5. `GetMessage` and `GetHistory` report `kind="import"`, `origin="host_manual"`, `channelKind="guild"`, `channelName="Guild"`.
6. RIFT native chat and other RIFT addons still work; this milestone does not claim normal player social-chat reception.

Do not claim physical acceptance until the actual v0.2.11 client visibly confirms it. No new automatic chat reader or social-chat sender is enabled by this release.
