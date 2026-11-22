# RCM — Separate Public-Channel Delivery Pipeline

**Saturday, November 21, 2026 · AMD-DESKTOP · Windows host-only development**
**Base commit:** 5061db9 · **Installed RIFT addon:** v0.2.23, unchanged
**Current public profile:** numbered public-channel slot 4, **Level 1-29**
**Physical public-import status:** NOT YET ACCEPTED

## Objective and design

The earlier physical RIFT session provided 20 authentic public-channel lines using:

    HH:MM:SS: [4. Level 1-29][Speaker@Shard]: message

That evidence established a current RIFT Live *parser format*, not the ability to insert the result into the RCM addon. This milestone adds a **separate, explicitly bounded public-only log follower and delivery coordinator**. It shares mature validation and persistence mechanisms with the physically proven Say workflow without broadening the Say capture rule.

### Profile isolation

| Component | Say | Public Level 1-29 |
|---|---|---|
| Read-only follower | tools/rcm-live-say-follow.cjs | tools/rcm-live-public-follow.cjs |
| Shared follower implementation | tools/rcm-live-social-follow-core.cjs | Same shared implementation |
| Observed event | say_observed | public_observed |
| Required format | rift-live-2026-say | rift-live-2026-numbered-public |
| Kind | general | public |
| Channel / slot | Say / none | Level 1-29 / 4 |
| Wire payload prefix | S | C |
| Delivery CLI | tools/rcm-say-delivery.cjs | tools/rcm-public-delivery.cjs |
| Shared coordinator | tools/rcm-delivery-coordinator-core.cjs | Same shared implementation |
| Private journal schema | RCM_SAY_DELIVERY_V1 | RCM_PUBLIC_DELIVERY_V1 |
| Private journal filename | rcm-say-delivery.json | rcm-public-delivery.json |

The existing tools/rcm-say-delivery-state.cjs provides a profile-specific journal factory. It still exports the original default **Say** behavior for compatibility, including the original journal schema and path. A second profile supplies the public queue. The two persistent files are never interchangeable. Invalid wire prefixes, mismatched channel names, incorrect channel slots, journal schema changes, bad SHA-256, repeated transfer IDs and ambiguous input are rejected.

**Cross-profile editor serialization:** Because the in-game RCM import receiver is global, Say and public journals also coordinate through an exclusive `rcm-global-editor-claim.lock` in their **shared private state directory**. Both `claim` and `dispatch` must acquire this lock, check the sibling journal for unresolved claimed transfers, and reject cross-profile token reuse before marking anything claimed. A stale lock fails closed; it must not be deleted without verifying the owner process ended. Do not move the two journals to different directories for concurrent RIFT use: they must share this lock domain.

The public import uses the RCM1-B64URL wire protocol. Its decoded four-field payload begins:

    C<NUL>Speaker@Shard<NUL>Level 1-29<NUL>Message

Here <NUL> denotes a binary NUL separator; it is not literal text typed by the player. The public-channel slot 4 belongs to the source-log proof metadata, not a fifth wire field. The RCM Lua receiver stores host provenance and public-channel identity; it does not pretend the record was intercepted through a native RIFT Lua event.

## Read-only follower

The shared bounded tailer retains source epoch and rolling hash checks around every poll, ignores the log before startup, requires a complete newline-terminated source record, and refuses file replacement, truncation, malformed/oversized lines and candidate overload. Message bodies are hidden in normal output. Explicit --prepare-import prepares full private Base64URL editor batches; the follower **never sends input**.

The public profile admits only the observed exact format / kind / normalized channel / slot:
- format = rift-live-2026-numbered-public
- kind = public
- channel = Level 1-29
- channelSlot = 4
- source = RIFT_Log.txt
- verifiedLiveFormat = true (shape only; physical file provenance must be proven separately)

New Say lines, other numbered channel slots (including unproven Events), historical guessed formats and all unsupported chat types are ignored. The Say follower remains Say-only.

## Public delivery coordinator

The public coordinator creates its *own* state file:

    C:\work\RiftChatModern\artifacts\rcm-private-queue\rcm-public-delivery.json

The artifacts directory is excluded from Git. The file contains **encoded but unencrypted** message bodies and must never be published, attached, pasted or logged. Ordinary status output is redacted.

Supported commands mirror the Say companion:
- capture: start one finite new-only log session, validate observed/batch pairs and atomically queue accepted records
- status: inspect redacted counts and outstanding token
- preflight: validate one eligible public batch with the actual .NET 10 Windows sender without keyboard input
- claim: atomically mark one public transfer claimed before printing its complete, private batch
- dispatch: on an unclaimed public batch, require fresh exact RIFT process identity and four explicit acknowledgments, then attempt one pinned sender delivery (no retry)
- verify-disk: require the exact claimed token in the real character SavedVariables file and a consistent checkpoint
- cancel: explicitly abandon a claimed transfer without replay
- recover: explicitly quarantine an abandoned capture session after verifying the capture process stopped

**Do not run claim before dispatch** when planning to let dispatch own the transfer; claim deliberately blocks further dispatch until resolved. A successful Windows SendInput report does not prove the RCM history row or disk save. The transfer stays claimed until independent disk verification or explicit cancellation.

## PowerShell reference (AMD-DESKTOP only)

From the repository root:

    cd C:\work\RiftChatModern
    node .\tools\rcm-public-delivery.cjs status
    node .\tools\rcm-live-public-follow.cjs --help
    node .\tools\rcm-public-delivery.cjs help

After verifying that the exact physical client and noncombat log are active, a supervised capture may be started with:

    node .\tools\rcm-public-delivery.cjs capture --path "C:\path\to\RIFT\Log.txt" --timeout-ms 60000 --poll-ms 100 --max-messages 1

The above command is a bounded host observation that writes to the **private journal**, not the game or its SavedVariables. It will not find messages emitted before capture started. Keep the game log disabled outside a controlled test if that was its original state: RIFT's /log **toggles** logging and must not be blindly invoked.

When a fresh public record is captured, validate the batch without game input:

    node .\tools\rcm-public-delivery.cjs preflight

Only after fresh window/process/executable pins and visibly confirmed RCM editor focus should a single explicit dispatch be considered; see the existing [Say coordinator's pinned-send procedure](SAY_DELIVERY_COORDINATOR_20261121.md) and substitute the public CLI name. The old PID/HWND/ticks from the Say experiment are **not valid reusable pins**. Never infer success without a separate in-game screenshot and an independent exact-token disk check.

## Offline tests

- tests/test_live_public_follow.cjs: new-only source, slot exclusion, private output, canonical editor preparation, truncated body, tampered/replaced file
- tests/test_public_delivery.cjs: public-only schema and wire, correct slot/format, separate state file, actual follower-to-coordinator capture, journal integrity, single claim, .NET 10 no-input preflight, fake-target input refusal with no retry, real Python disk verifier on a synthetic SavedVariables fixture, crash recovery, and **four additional cross-profile lock/collision checks**
- Existing Say-specific coordinator/follower tests also run against the shared implementations, including the real previously saved Say state file.

The public pathway has passed its focused offline tests. The project-wide regression suite and build/deployment audits are separately tracked in the main README.

## Physical environment checkpoint and limitation

At approximately 20:01 EST on November 21, the RIFT process on AMD-DESKTOP was still running (PID 32504 / HWND 0x60590). The configured Log.txt remained the unchanged 5,246-byte file from the earlier completed Say acceptance; the logged state had previously been restored to disabled. The public queue was empty.

A separate read-only follower smoke check against the real 5,246-byte log established EOF at byte 5246, completed nine bounded polls, and replayed no old records. One explicitly acknowledged /log enabling attempt **refused before input** because the exact RIFT foreground was not acquired. The tool reported zero key events, gameInputSent=false, and a follow-up read-only file audit confirmed the log had not changed. The game window was minimized on the subsequent inspection. The test was **not retried** and no public-channel capture was falsely claimed. This remains a **physical acceptance blocker**, not an offline correctness regression.

## Next development milestone

**P0: one independent public-channel import acceptance.** After RIFT is stably foregroundable and the prior logging state is known, run a bounded passive capture while a real Level 1-29 message arrives. Verify a new source line and exact public journal queue; preflight through .NET 10; focus RCM; dispatch once; confirm one HOST/PUBLIC or channel-specific host label; use /reloadui and verify the exact token on the actual character save. Restore the original logging state and record source/screen/disk receipts. Do not post public test messages or expose private speakers in a public repository.

**P1:** Once proven, investigate other public-channel indices/names from actual game-created bytes. Guild, Party, Tell and native social sending still require independent discovery and verification.
