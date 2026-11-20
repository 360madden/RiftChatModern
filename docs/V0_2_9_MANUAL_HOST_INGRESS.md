# RCM v0.2.9 — Manual Host-to-Addon Chat Import

**Date:** Friday, November 20, 2026 (America/New_York)
**Host verified:** AMD-DESKTOP
**Canonical source:** `C:\work\RiftChatModern\addon\RiftChatModern`
**Physical install:** `C:\Users\mrkoo\OneDrive\Documents\RIFT\Interface\AddOns\RiftChatModern`
**Public repository:** https://github.com/360madden/RiftChatModern

## Milestone and exact scope

Rift Chat Modern (RCM) remains an independent RIFT MMO chat-style addon and cross-project diagnostics console. This release introduces the first **explicit Windows-to-RIFT addon record import path**. A Windows helper encodes an observed or manually supplied chat record as bounded, **manually pasteable native RIFT slash commands**; the in-game RCM addon validates, assembles, and stores the text under its existing chat history. The native chat box is not replaced and ordinary social-chat capture or send has **not** been verified.

No automatic game input, chat scraping, RIFT networking, encrypted datastream manipulation, or background host process is installed. Nothing reads the Windows clipboard or modifies unrelated addons. Imported records are clearly marked **[HOST? Channel]** so their source and unverified status remain visible even after saved chat history reload.

## Original discoveries and constraints

- The documented RIFT addon API and our own previous probes expose NPC speech, alerts, addon messages and native console metadata, **not a verified direct Lua callback for normal player chat**.
- LuaPadModern already has a tested bounded `Log.txt` reader. RCM's independent host observer reuses that decoder, and still needs a real log path and physical chat sample.
- RIFT's `/rcm` slash command was observed dispatching in-game for v0.2.2. We extend that known native command surface rather than pretending we can import from a Windows file directly into Lua.
- The existing RCM native slash adapter limits arguments to **160 bytes**. Each imported frame is constructed to be well below this bound. RIFT's own native chat input limit for such strings is still subject to physical verification.

## Addon implementation

**New startup file:** `HostIngress.lua`, registered in `RiftAddon.toc` before `Main.lua`. The addon manifest retains required Identifier, Name, Author, Email placeholder, Environment 4.3, and character-scoped `RiftChatModernSaved`. As with other RIFT RunOnStartup files, this module returns **no top-level Lua value**.

Protocol `RCM1-B64URL`:

1. Record bytes: one kind code (`S` general, `P` party, `G` guild, `T` tell, `C` public) followed by NUL-separated UTF-8 `sender`, `channel`, `text`.
2. Encode the bytes with URL-safe base64, no padding. Maximum sender 40 bytes, channel 72 bytes, original text 512 bytes, total decoded 780 bytes.
3. Split base64 text into chunks of at most 88 ASCII characters (maximum 12 parts). Use a 12-digit uppercase hexadecimal message identifier.
4. Each manual slash line is `/rcm import ID INDEX/TOTAL CHUNK`. The receiver accepts out-of-order parts; repeated identical parts are idempotent. Conflicting parts or concurrent incomplete sessions are refused.
5. A complete valid message appears in existing RCM history as the appropriate `general`, `party`, `guild`, or `tell` kind, with the player name as source and `[HOST? Channel] ` prepended to text. The prefix is UTF-8-safely bounded with the original 512-byte history limit.
6. Pending partial transfers are transient, bounded to one session, 45 seconds, and 12 parts. The latest 32 completed identifiers are held for replay suppression only in memory. No extra SavedVariables schema is created.

The receiver validates UTF-8 (including continuation, overlong encodings and invalid surrogate scalar ranges), fields, IDs, base64 bit tails, frame lengths and the publishing callback. Incoming text is **inert data** and never evaluated as Lua or executed as a command. Its status is exposed in `RiftChatModernAPI.GetHostIngressStatus()`: `imported`, `acceptedChunks`, `rejected`, `duplicates`, `expired`, `publishFailed`, and partial-progress counters. `GetStatus()` exposes `hostManualImportReady`, `hostAutoImportAvailable=false` and `hostImportNativeChatVerified=false`; the public API interfaceVersion remains 1.

## Windows utilities

**New:** `tools/rcm-chat-import.cjs` generates the manual slash lines. In Windows PowerShell, from the repository:

```powershell
node .\tools\rcm-chat-import.cjs --kind guild --sender Atank --channel Guild --text "Hello from host"
```

The output is JSON containing `commands`. Paste one **complete** `/rcm import ...` command at a time into **RIFT's native chat input** after RCM v0.2.9 is loaded. For a longer message, paste every part of the same identifier. The in-game addon reports only an import acknowledgement; verify the record in RCM's **CHAT** or **ALL** tab.

For a logfile observer that is already producing actual candidate chat records, the optional `--prepare-import` flag both includes message text and prints the human-pasteable commands directly:

```powershell
node .\tools\rcm-chat-observer.cjs --help
node .\tools\rcm-chat-observer.cjs --prepare-import --timeout-ms 120000
```

The observer remains read-only and bounded. It does **not** enable `/log`, send game input, or write to RIFT. **The common OneDrive and normal Documents `Log.txt` candidates remain absent in the last local preflight.** Without a genuine in-game log, any example is a synthetic/manual demonstration, not proof of social-chat capture. The `--prepare-import` option outputs message bodies by explicit request; the default observer remains metadata-only.

## Tests and failures retained

- **95/95 Lua 5.1 tests passed.** Eight new host-ingress tests include real Node-generated records injected through mocked native `/rcm` slash dispatch, single/multi-part UTF-8, out-of-order reception, replay suppression, conflicting sessions, corrupted payloads, malformed UTF-8, missing message publication, missing fields, expiry, and a full JSON-line observer → Node encoder → Lua history round trip.
- **22/22 Node.js tests passed.** The 8 new encoder tests cover message kind codes, maximum text lengths, field validation, exact base64url contract, bounded slash lengths, `--stdin-json` parsing, metadata-only skip and CLI help. The observer has a separate `--prepare-import` child-process fixture.
- **Compatibility bug caught before release:** initial Lua integration tests assumed `GetHistory("guild",...)` and `GetHistory("general",...)` were valid filter names. The existing model intentionally exposes only `chat` as the combined social-channel filter. Tests were corrected to `GetHistory("chat",...)`, without changing the production filter contract.
- **Loader tests updated:** six RunOnStartup modules must execute with zero returned values, and existing runtime harnesses now load `HostIngress.lua` in the proper order. This addresses earlier actual RIFT startup assertion failures and protects the correct .toc layout.
- **Import failure behavior:** malformed frames, broken UTF-8, conflicting chunks and publisher errors reject the message rather than acknowledging a delivery. Stale pending chunks expire without publication. Test-only fixtures have no claim to the physical game.

## Physical acceptance still required

1. Confirm the exact physical RIFT process and running version. Deploy the six-file manifest and verify all source-to-install hashes; **do not touch SavedVariables**.
2. Intentionally reload the actual game UI; check startup version and error panel. The old native chat fallback remains available.
3. Open `/rcm` and confirm the resizable dark window. Generate a one-part command using `rcm-chat-import.cjs`; paste it into native RIFT chat, then confirm RCM's CHAT tab displays a message with `HOST?` provenance.
4. Generate a long multi-chunk UTF-8 example; paste each chunk, verify only one assembled message, and inspect `GetHostIngressStatus()` if needed.
5. Separately verify RIFT's actual `Log.txt` output, player-chat format and delivery frequency before claiming normal chat interception. An emitted `:logprobe` marker alone does not establish that real player messages were received.
6. Automatic Windows-to-addon input is **not** implemented; a background host must not be described as a proven solution until live command/focus/receipt tests exist.

## Development handoff

The next strongest task is **physical manual slash-import acceptance and a real RIFT chat-log sample**. If the user's desktop input lock prevents screenshots or commands, keep further work offline and preserve the exact blocker. Once live sample data establishes true chat-format mapping, improve the host observer and only then investigate high-reliability automatic RCM import. Keep development focused on the full chat replica objective, not just addon telemetry or the RPT project.

## Deployment receipt — November 20, 2026

A fresh Workbridge host identity check confirmed **AMD-DESKTOP**. The manifest passed checks for Identifier, required Email metadata, Version 0.2.9, Environment 4.3, character-scoped SavedVariables and all six RunOnStartup modules (with `HostIngress.lua` before `Main.lua`).

Only four payloads required copying: `Core.lua`, newly added `HostIngress.lua`, `Main.lua` and `RiftAddon.toc`. Every deployed file, including bundled Lato fonts and license, was compared with the canonical source using SHA-256: **10/10 matched, zero mismatches**. No SavedVariables or unrelated addons were touched, and no client/UI reload was sent. This is an **on-disk deployment pass**, not physical RIFT loader or chat-input acceptance.

Final release validation: **95/95 Lua 5.1 tests and 22/22 Node tests passed**. `git diff --check` passed with only line-ending warnings.
