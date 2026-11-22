# RCM — First Physically Observed Numbered Public-Channel Log Format

**Saturday, November 21, 2026 · AMD-DESKTOP · RIFT Live client**  
**Code scope:** Windows host parser plus offline regression tests; RIFT Lua addon stays v0.2.23.  
**Evidence source:** the actual game-created noncombat Log.txt under the RIFT DocumentsDirectory. The original file and unredacted speaker/message bodies are deliberately not included in this Git repository.

## Discovery

While physically accepting the serialized Say coordinator, the temporary noncombat logging interval captured genuine public-channel chat from the running RIFT client. A privacy-redacted read-only audit of the final 5,246-byte game log (SHA-256 bfce641dafd38e532a775670afbe7dc099b40dbbc924912f8e53e4b5c2313e64) found **20** lines of this previously unrecognized shape:

    23:37:21: [4. Level 1-29][REDACTED_SPEAKER]: REDACTED_TEXT

All 20 observed records used the on-screen public-channel slot **4. Level 1-29**, between raw game log timestamps 23:37:21 and 23:42:30. The same real source contained two physically verified Say-shaped records. Native General chat had shown this numbered public channel as live player messages during the same game session.

This was more useful evidence than treating historical third-party RIFT logger bracket formats as current-client facts. The former observer incorrectly returned null for a sanitized reconstruction of the real numbered format because its historical branch expected the line to start with a bracket, not a timestamp followed by a colon and space.

**Evidence boundary:** Twenty numbered channel lines from **one** public channel establish the syntax for this observed channel. They do not prove the precise formatting of other channel names, other servers, Guild/Party/Tell traffic, nor game origin for any synthetic line that happens to match this pattern.

## Parser fix

The root-cause fix in tools/rcm-chat-observer.cjs adds one narrow, bounded branch **after** the physically proven Say branch but **before** historical-only bracket guesses:

| Field | Value from sanitized fixture |
|---|---|
| format | rift-live-2026-numbered-public |
| verifiedLiveFormat | true (verified shape, NOT verified origin for an arbitrary input) |
| source | RIFT_Log.txt |
| kind | public |
| channel | Level 1-29 |
| channelSlot | 4 |
| sender | EXAMPLE@SHARD (only a sanitized fixture) |
| gameTimestamp | unconverted HH:MM:SS source text |
| textBytes | full bounded UTF-8 source body length |
| truncated | true only when the source body exceeds the established 512-byte preview bound |

The numbered channel slot is retained separately from the normalized readable channel label. No shard suffix is invented for the channel just because the speaker might include @Shard. The public-channel name must satisfy the existing canonical channel classification; malformed time, absent or zero slot, invalid sender, control characters, unrelated System/Combat/Guild labels and incomplete bodies are rejected. An oversized message may be recognized as truncated, but the existing import encoder still refuses to silently persist shortened chat.

**Important:** The new format is deliberately **not** accepted by the Say-only delivery coordinator or its exact-match batch gate. The Say follower selects only rift-live-2026-say / general / Say. The batch gate accepts only its currently proven Say path when verifiedLiveFormat is true. This keeps the newly discovered public stream from being dispatched automatically or mislabeled HOST/SAY.

## Verification

- Confirmed the old parser failed to recognize a sanitized reconstruction of the actual new public format.
- Added failing-then-passing Node tests for exact public classification, slot and timestamp, malformed/unrelated input rejection, and the real bounded LogTailProbe transport with text redacted by default.
- Independently re-read the actual game-created Log.txt with the updated parser: **22 classified records** — two Say, twenty numbered public channel, zero invented Guild/Party/Tell rows. This aggregate audit emitted no sender names or chat bodies.
- Added explicit tests that the Say-only follower and exact-candidate gate continue rejecting the new verified-format public records.
- The new branch does not modify the in-game addon manifest, Lua files, existing SavedVariables or RIFT client state.

## Next acceptance boundary

**Later implementation update (same evening):** An independently bounded [public-channel follower and delivery coordinator](PUBLIC_CHANNEL_DELIVERY_20261121.md) now support this verified slot 4 / Level 1-29 format. They use separate journals and message policies while sharing the validated source-integrity and receipt code with the Say path. Synthetic follower-to-queue, .NET 10 no-input validation, disk-proof and refusal tests pass. **A supervised real public-channel import into the RCM editor remains pending** because the live logging activation attempt was refused before input while the RIFT window was not foregroundable. The original Say-only policies remain intact.

**Other channels (Guild/Party/Tell):** still require direct game-created bytes from a live RIFT client. Do not generalize their on-wire shapes from these public-channel lines.

## Cross-references

- COORDINATOR_PHYSICAL_ACCEPTANCE_20261121.md — first real Say capture through serialized coordinator, exact-token disk proof and restored /log state.
- V0_2_22_NATIVE_RIFT_CONSOLE_CATEGORIES_20261121.md — separate native settings categories versus actual message source content.
- V0_2_23_PHYSICAL_RIFT_SAY_LOG_IMPORT_20261121.md — original manual Say end-to-end acceptance.
- SAY_DELIVERY_COORDINATOR_20261121.md — serialized Say-only host delivery contract.
