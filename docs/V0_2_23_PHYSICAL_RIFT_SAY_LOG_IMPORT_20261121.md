# RCM v0.2.23 — First real RIFT Say → Log.txt → Imports → SavedVariables proof

**Date:** November 21, 2026 · America/New_York

**Verified host:** AMD-DESKTOP · **Repository:** `C:\work\RiftChatModern`

**Game:** RIFT Live, process PID 37676, HWND `0x360BC4`, exact client SHA-256 `df954b798331e18359be62a31cc74b49fc3f50b87385ebb080a5448256322c01`

## Outcome and precise scope

**Physically verified for one controlled Say message:** a player-message command submitted in RIFT's **original native chat window** was written to the real game-produced noncombat `Log.txt`, parsed by the Windows RCM observer, encoded as one bounded RCM editor import, inserted into the **physical RCM v0.2.22 editor**, shown in the in-game **IMPORTS** history, then persisted by the game's normal `/reloadui` save cycle. An independent read of the actual character SavedVariables file confirmed the **exact transfer token**, one retained import row, and consistent save checkpoint.

The test token was `RCM_CHAT_TEST_20261121`. The real character identity and unrelated RIFT chat/history were deliberately omitted from public code, records and screenshots.

**Still unverified:** Guild, Tell, Party, Raid or named public channel message-log formats; unattended continuous observation/delivery; production automatic chat replacement; independent social-message transmission through RCM itself. Import provenance must remain `HOST`.

## Preflight and reversible logging experiment

1. Verified AMD-DESKTOP, live exact RIFT executable process and window. The saved config `LogConsole=False`; `DocumentsDirectory` points to the OneDrive Documents/RIFT root; noncombat `Log.txt` was absent in all known candidates.
2. Added an **allowlisted and separately acknowledged** `/log` action to the existing native slash sender, plus strict single `/say RCM_...` canaries. These cannot be used as arbitrary typing/send APIs. Test-first regressions for both actions passed before physical input.
3. Sent `/log` **once**; RIFT created `Log.txt`. Sent one `/say RCM_CHAT_TEST_20261121` through the original RIFT native chat. Sent `/log` once again, to restore the previous state.
4. A real RIFT native screenshot, **`2026-11-21_122204.jpg`**, shows both **“Noncombat logging enabled”** and **“Noncombat logging disabled”**, with the exact Say canary between them. This is stronger than keyboard event insertion alone.
5. The private complete `Log.txt` was 85 bytes, two newline-terminated records, SHA-256 `724d41f418cc4c86a8d48ea9b08b1ce6b9eb60b6e86fd9b95fdf9561dca406ea`. It is **not** committed. No external app or extra RIFT configuration was changed.

The single verified Say record's **shape**, with speaker redacted, is:

```text
17:17:23: [REDACTED_CHARACTER] says: RCM_CHAT_TEST_20261121
```

The bracketed field is the **speaker**, not the channel. The literal verb `says` identifies **Say**. The log's `17:17:23` and native chat window's `12:17:23` differed by five hours in this sample, so their timezone relation requires qualification. Preserve `gameTimestamp` as source text; do not convert arbitrarily.

## Parser and encoder root-cause changes

The previous observer recognized only historical `[Channel][Sender]: message` candidate shapes. It therefore **could not recognize the actual November 2026 game line**.

`tools/rcm-chat-observer.cjs` now handles this **exact narrow Say format first**, with bounded sender/message bytes and strict timestamp range. It reports:

| Field | Value |
|---|---|
| `format` | `rift-live-2026-say` |
| `verifiedLiveFormat` | `true` (syntax independently observed in a game-created file) |
| `kind` | `general` (RCM transfer family) |
| `channel` | `Say` |
| `source` | `RIFT_Log.txt` |
| `text` | full bounded source text (redacted from observer output unless explicitly requested) |

**Important evidence distinction:** a synthetic fixture with the same pattern has a verified *syntax* but does not thereby have verified game origin. A real-game proof needs an independently identified RIFT process plus real file bytes/receipt. Historical Guild/Party/Tell parser branches remain **unverified**.

Added `tools/rcm-live-say-batch.cjs` as an explicit, one-message, read-only log-to-editor converter. It requires the **exact current SHA-256 of the bounded Log.txt**, exactly one complete canary occurrence, the verified narrow Say pattern, and exact message bytes. It refuses duplicate/stale/mismatched hashes, malformed fields, truncated values and noncanonical path/arguments. It does not focus the game or type keys. The existing Node encoder and .NET 10 Windows editor batch validator continue enforcing their independent bounds.

The downstream `rcm-chat-batch-gate.cjs` formerly refused all `verifiedLiveFormat=true` records because no live format had been proven. It now permits **only** `rift-live-2026-say` with the confirmed general/Say attributes, and still refuses invented verified formats. Its existing marker and source identity checks remain unchanged.

## Physical host → RCM editor acceptance

1. The exact real log was parsed by Node with one matching Say canary. The local encoder emitted one `RCM1-B64URL` editor transfer; the unchanged .NET batch validator independently reported `batch_validated_no_input`.
2. Focused **RCM's own RiftTextfield** using the already-proven client-coordinate click and visually confirmed green `INPUT • FOCUSED` inside the real v0.2.22 UI.
3. Submitted exactly one pinned .NET sender `--stdin-batch` transfer with the documented additional focus, submission and batch acknowledgments, exact host/PID/HWND/process epoch/executable SHA pins. Windows reported 71 characters, one part and one Enter submission; no automatic retry. The actual game receipt was checked separately.
4. Clicked the real IMPORTS tab. A read-only physical RIFT screen capture showed **one** imported row, with the exact test text and sender. Initially the narrow Say message appeared under `[HOST/GENERAL]` because the compact label used only the transport family.
5. Independently audited the actual character SavedVariables *before* `/reloadui`: the transfer token was absent, and there were no stored imported rows.
6. Defocused RCM's editor by clicking the original RIFT General console tab, visually confirmed `INPUT • NOT FOCUSED`, and submitted `/reloadui` **through native RIFT chat**. No game restart.
7. After RIFT's normal save lifecycle, the separate file auditor found one imported row, token `71CA8D77702F` **on disk**, matching retained import identity, consistent checkpoint and `diskReceiptVerified=true`. The audit was read-only and did not mutate SavedVariables.

One RIFT Numpad screenshot key attempt while the RCM editor had focus produced **no image** (the editor can consume the `*` key). Read-only bound Windows screen capture was used instead. Do not claim this unsuccessful key attempt created a game screenshot.

### Fix in v0.2.23

`Core.rowShortLabel()` now displays `[HOST/SAY]` for an imported `channelKind="general", channelName="Say"` record. It also distinguishes Yell, Emote and Local when their explicit name is retained. Legacy general imports without a more specific name remain `[HOST/GENERAL]`. The `kind`, `channelKind`, `channelName`, `origin` and schema version **are not modified**. A new failing-then-passing Lua 5.1 regression confirms exact subtype display without forging native reception.

**Physical v0.2.23 acceptance:** The verified AMD-DESKTOP addon installer copied exactly `Core.lua`, `Main.lua` and `RiftAddon.toc`, with a rollback backup and no SavedVariables changes. The existing RIFT game was reloaded with `/reloadui`, then `/rcm` opened the UI. A bounded read-only capture of the actual client at PID 37676 and HWND `0x360BC4` showed the version `v0.2.23`, the IMPORTS tab selected, **exactly one** retained Say canary row and the corrected **`[HOST/SAY]`** label. The row's original text and speaker persisted across the reload. The in-game screenshot/crop containing a real player name was **not** added to GitHub. The real-game proof is separate from mocked Lua tests and independent of the Windows sender's keyboard event receipt.

## Verification limits and next work

The complete tests include:
- Real Lua 5.1 provenance/loader/version compatibility regressions.
- Parser-format tests for physical Say syntax, invalid timestamps and hostile/unrelated formats.
- Actual Node file tailer and CLI fixture tests, with bodies redacted by default.
- Exact log-hash/source selection → bounded encoder; no duplicate/truncated record accepted.
- .NET 10 one-batch validation against real game-created file output.
- Exact marker gate accepting only qualified verified Say and rejecting fabricated or mismatched source formats.

**P0 next:** qualify a second, different actual social type (Guild, Party, Tell or public channel) through real RIFT `Log.txt` before expanding parser assumptions. For continuous import, build a bounded explicitly opt-in host observer → editor route with per-message receipts, fault recovery and provenance. Never claim continuous player-chat reception based only on this single qualified Say import.

**Privacy:** Keep the original game `Log.txt`, player names, original screenshots and full character save out of the public repository. Only anonymized fixture data and summary digests belong in GitHub.
