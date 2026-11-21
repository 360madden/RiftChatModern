# RCM Coordinator — First Real-Game End-to-End Physical Acceptance

**Saturday, November 21, 2026 · AMD-DESKTOP · America/New_York**  
**In-game addon version:** 0.2.23 (no Lua or RiftAddon.toc change)  
**Repository baseline before this milestone:** 407bcbe  
**Live RIFT identity:** PID 32504, HWND 0x60590, SHA-256 of rift_x64.exe DF954B798331E18359BE62A31CC74B49FC3F50B87385EBB080A5448256322C01; process start ticks 639309007113358688.

## Result

**P0 physically accepted.** A NEW native RIFT Say, created while the game was running, was logged, picked up by the previously unverified bounded follower, journaled by the serialized coordinator, independently validated by the .NET 10 editor sender, delivered once to RCM, physically observed as a new HOST/SAY row, saved by the game's normal /reloadui cycle, verified on disk by exact transfer token, and marked disk_saved by the coordinator.

**Evidence boundary:** This proves one supervised, explicitly opted-in host-mediated Say transfer. It does not prove unattended streaming, no-loss delivery across crashes, native Lua social-chat interception, direct social sending from RCM, or Guild/Party/Tell import. A Windows SendInput success receipt was not treated as an in-game or persistence receipt.

## Preflight and actual logging state

- Verified AMD-DESKTOP, one RIFT window/process, in-world character, RCM v0.2.23 open, editor not focused, installed 23 files hash-identical to the repository, clean Git state synchronized at 407bcbe, and coordinator journal revision 0 with no claimed/queued transfers.
- Actual configured DocumentsDirectory resolves to the game's OneDrive Documents/RIFT tree. Initial Log.txt was 85 bytes, SHA-256 724d41f418cc4c86a8d48ea9b08b1ce6b9eb60b6e86fd9b95fdf9561dca406ea. The stored Rift.cfg LogConsole value was false (not by itself runtime proof).
- Sent one unique benign native Say probe while logging was untouched. A game screenshot confirmed the probe appeared in native General chat, but Log.txt was byte-for-byte unchanged. This established the logging dependency with more evidence than assuming the persisted flag controls runtime state.
- Submitted /log once using the existing pinned native-chat helper. Log.txt gained the game-produced noncombat logging enabled record at raw log time 23:37:03 and changed to 122 bytes. This was a controlled temporary toggle, not a configuration-file edit.
- The raw log clock differed from native local display by about five hours; preserve raw log timestamp and do not assume a timezone conversion.

## Exact coordinator capture

1. Started one bounded coordinator capture against the actual RIFT Log.txt after it was confirmed enabled, with timeout 45000 ms, poll 50 ms and max-messages 1. Readiness receipt: capture_started, sessionId 48E609EEA4B2, oldHistoryReplayed false, gameInputSent false.
2. Sent one NEW native /say test canary through original RIFT chat: RCM_COORD_P0_20261121_1838. The game-created file contained one matching exact Say record:

        23:37:31: [REDACTED_SPEAKER] says: RCM_COORD_P0_20261121_1838

3. The follower issued capture_queued with the only transfer token 8D612E8C1062, sequence 1. Capture completed normally via message_limit_reached; the coordinator reported queued 1, claimed 0 and quarantined 0.
4. The actual .NET 10 sender preflight reported batch_validated_no_input with one validated batch, token 8D612E8C1062, SHA-256 DB84207F351AF91F18CD82A670AAC3085CE434FB32D5783253C4F531A0018E57, and gameInputSent false.
5. The inspected exact RIFT identity supplied fresh host/PID/HWND/process-start ticks/executable path/SHA-256 to the dispatch. These values are ephemeral; NEVER reuse this handoff's PID/HWND/ticks for a future test.

## Physical editor delivery (one attempt)

- Reviewed the RCM in-game window geometry from actual RIFT screenshots. One native focused click at the then-current client coordinates (2100, 1030) used the existing tested RPT Win32Input helper and reported 3/3 inserted mouse events. A separate bounded Win32 on-screen capture confirmed the RCM header was green INPUT • FOCUSED before dispatch. Those coordinates are not a portable configuration or instruction for other window positions.
- A bounded Python wrapper temporarily foregrounded exactly the pinned RIFT client, synchronously invoked the existing Node coordinator dispatch with the complete .NET target pins and four acknowledgments, and restored the previous foreground.
- The sender reported windows_batch_and_enter_inserted_game_receipts_unverified, Windows input reported true, retryAllowed false, stillClaimed true. It was NOT retried.
- A separate physical visual inspection immediately afterward showed RCM v0.2.23 IMPORTS with exactly **two** rows: the earlier physical HOST/SAY test and the new RCM_COORD_P0_20261121_1838 HOST/SAY row. The footer reported the new import as RCM history message #142. That was an in-memory addon receipt, not yet disk proof.
- No synthetic fixture, typed-character count, or Windows input acknowledgment was substituted for the observed in-game row.

## Independent pre-save versus post-save evidence

| Stage | Exact physical result |
|---|---|
| Before /reloadui | Character SavedVariables file was 27,424 bytes, SHA-256 7443103aa627bd9df15a74d2879f5fdcc31cb3ba2bc856f38cfa9696bc14ff5b; required transfer token 8D612E8C1062 was ABSENT; only one older import row on disk |
| Defocus | One guarded native General tab click at then-current client coordinates (95, 815); separate screenshot confirmed INPUT • NOT FOCUSED |
| Save | One native /reloadui, sent through RIFT's original chat; no full game restart |
| After /reloadui | Actual character SavedVariables file changed to 27,843 bytes, SHA-256 c2b2e8ba85b89874e50c47b2070f8ab108d072958f59814e3cf71bd0851f9d8f |
| Read-only audit | The existing Python auditor verified the exact token on a retained imported history row and a consistent save checkpoint. Node verify-disk returned disk_saved_verified with diskReceiptVerified true |
| Durable queue | Journal revision 6; captured session completed, queued 0, claimed 0, disk_saved 1, cancelled 0, quarantined 0 |
| Post-reload UI | RCM window was reopened with /rcm; physical screenshot confirmed two retained HOST/SAY rows and the same new test text, version 0.2.23 |

A real native RIFT screenshot was recorded after the post-reload reopen as private evidence: 2026-11-21_184327.jpg, 2560x1369, SHA-256 0244748c4c51b27328d0213a6a3cc0bcdea67d42e0e7ae54402255066f93cbf4. Earlier native screenshot 2026-11-21_183416.jpg confirmed in-world RCM, and 2026-11-21_183633.jpg confirmed the pre-logging native Say probe. Additional bounded Windows on-screen crops independently showed the focused editor before dispatch, the two Imports rows after dispatch, and persisted rows after reload. The original images contain personal game UI/player identities and are deliberately **not** in Git.

## Logging cleanup

The initial runtime noncombat logging was off. The test enabled it temporarily with one /log command. After all receipts, one further /log command was issued through pinned native chat. A fresh actual game on-screen capture visibly reported **Noncombat logging disabled** at local 18:42:43, restoring the original observed behavior. Rift.cfg and unrelated addon installation files were not edited. The test itself used /reloadui to save the character's actual state.

## Lessons and next work

- The in-memory HOST import footer is intentionally distinct from a saved-file receipt. The before-save missing-token audit and after-save verified-token audit are necessary to prove persistence.
- The editor focus indicator must be physically checked before sending. Native RIFT chat must regain focus before /reloadui; otherwise keys can be swallowed by the RCM editor.
- One claim blocks a second dispatch. The coordinator reserves its transfer immediately before Windows input; no retry occurred.
- Current RCM addon remains 0.2.23. Host coordinator P0 acceptance does not require a Lua version bump.
- **P1:** The game-generated noncombat Log.txt also contained 20 numbered public-channel lines, which identified a second authentic current-client chat format. See LIVE_PUBLIC_CHANNEL_LOG_FORMAT_20261121.md. This is a separate parser-evidence milestone, not yet a verified public-channel import to RCM.
- **P2:** Investigate bounded opt-in automatic delivery with exact per-message receipts only after retaining the no-duplicate/no-retry invariant. Guild, Party, Tell and native social sending remain unverified.

Privacy rule: keep the original Log.txt, full character save, screenshot files, unredacted speaker identities, and ignored private coordinator journal out of the public repository. Only this redacted digest-based record and synthetic fixtures belong on GitHub.
