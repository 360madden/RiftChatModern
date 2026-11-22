# RCM — Serialized Say Delivery Coordinator

**Saturday, November 21, 2026 · AMD-DESKTOP**  
**Scope:** Windows host helper only; existing RIFT addon stays at v0.2.23  
**Implementation:** tools/rcm-say-delivery.cjs and tools/rcm-say-delivery-state.cjs. A later shared-core refactor introduced tools/rcm-delivery-coordinator-core.cjs while retaining the same Say CLI, journal format and source-policy validation; see [separate public pipeline](PUBLIC_CHANNEL_DELIVERY_20261121.md).

**Tests:** tests/test_say_delivery.cjs

> **Later physical update (evening, November 21):** One supervised real Say transfer through this exact coordinator has now passed actual RIFT log capture, pinned .NET sender delivery, visible RCM HOST/SAY receipt, /reloadui and independent matching SavedVariables token verification. Read [the physical acceptance](COORDINATOR_PHYSICAL_ACCEPTANCE_20261121.md). The original notes below document implementation-time uncertainty; unattended delivery remains unverified.

## Engineering result

The bounded read-only Say follower can now feed a **serialized, durable private import queue**, instead of publishing unrelated import batches to a console without a coordinator. Only one delivery may be claimed or dispatched at a time. Recovery from uncertain Windows input never automatically resubmits the same message.

The host tool has commands for:

| Stage | Command | Behavior |
|---|---|---|
| Capture | capture | Launches the bounded Say follower; pairs each redacted Say observation with its validated one-message RCM editor batch; persists each pair in a private journal |
| Inspect | status | Reads sanitized counts, session states and active token; does not reveal message text |
| Validate | preflight | Sends **one** queued or claimed batch to the existing .NET 10 sender in validation-only mode; sends **zero game keys** |
| Reserve | claim | Atomically marks the next eligible transfer claimed **before** printing its one complete editor batch; does **not** send input |
| Dispatch | dispatch | With all six fresh RIFT process/window/executable pins **and four explicit acknowledgments**, reserves one batch before asking the .NET sender to insert keys into the already-focused RCM editor; no automatic retries |
| Confirm disk | verify-disk | Calls the existing Python read-only SavedVariables auditor for the **exact** claimed token, consistent checkpoint, and same machine; only then marks disk_saved |
| Give up | cancel | Explicitly marks a claimed transfer cancelled; never requeues it |
| Recover interrupted capture | recover | After the operator confirms the prior capture process is gone, quarantines unfinished capture records instead of replaying them |

## Proven versus unproven

**Implemented and offline verified:** real bounded follower subprocess, new-only Say detection, multi-message queueing, private atomic journal, exclusive lock, source/batch validation, .NET dry-run validation, sequential claim, explicit pinned dispatch refusal for deliberately impossible target pins, and Python disk-token auditing against a synthetic SavedVariables fixture.

**Previously physically verified in v0.2.23:** one real game-produced Say line, one guarded editor import displayed as HOST/SAY, and the exact imported token retained on disk after /reloadui.

**NOT yet physically verified for this coordinator:** successful automatic dispatch to the live game, unattended delivery, RCM editor focus during every real transfer, an in-game receipt for a new coordinator transfer, any new Guild/Tell/Party/public message format, or native Lua social-channel interception/sending. Even a successful Windows SendInput report is *not* a game-acceptance receipt.

## Storage and fault policy

Default private file:

    C:\work\RiftChatModern\artifacts\rcm-private-queue\rcm-say-delivery.json

The entire artifacts directory is already excluded by .gitignore. The journal contains **Base64URL transfer data, NOT encrypted data**. It can be decoded to expose chat senders and message bodies. Never publish, attach, sync, or log this private journal. The status command prints only bounded metadata.

The journal is bounded to 200 entries, 50 capture sessions and 2 MiB. Each transfer has an independently validated exact uppercase 12-hex token and SHA-256 of the validated wire payload. Every write uses a unique temporary file, flush, then atomic same-directory rename. An exclusive lock blocks concurrent state-changing commands, including another capture. An abandoned lock requires an explicit operator process-liveness check before manual cleanup.

State transitions:

    completed capture: queued -> claimed -> disk_saved
                                   \-> cancelled
    failed/ambiguous capture: queued -> quarantined
    crashed capture: capturing until explicit recovery -> failed/quarantined

A later public-channel companion also shares one **global editor claim lock** with this Say journal. `claim` and `dispatch` refuse if the other channel has an unresolved claimed transfer or a colliding token, preventing cross-profile interleaving into RCM's single editor. The two journals must be in the same private directory; see [public delivery pipeline](PUBLIC_CHANNEL_DELIVERY_20261121.md). There is **no claimed -> queued transition**. If a sender call fails before input, may have partially inserted input, times out, or crashes, the token stays claimed. The operator must independently inspect the game or its persisted token; the system does not guess whether resending is safe. New capture sessions never replay old log history from before start; a crash can therefore leave gaps, which must not be misrepresented as lossless streaming.

## Typical PowerShell commands (AMD-DESKTOP)

Preflight build; this does not enter game input:

    cd C:\work\RiftChatModern
    dotnet build .\tools\RcmEditorSender\RcmEditorSender.csproj -c Release --nologo

Inspect private queue status:

    node .\tools\rcm-say-delivery.cjs status

Start an explicitly bounded session against the **verified actual** RIFT Log.txt; this command creates a private journal but **does not type into RIFT**:

    node .\tools\rcm-say-delivery.cjs capture --path "C:\path\to\RIFT\Log.txt" --timeout-ms 30000 --poll-ms 100 --max-messages 20

RIFT noncombat logging must already be active for new lines. The original /log command is a **toggle**, not an idempotent enable action. This helper never invokes /log or changes Rift.cfg.

Validate the next batch without input, then optionally reserve one batch for separate manual entry:

    node .\tools\rcm-say-delivery.cjs preflight
    node .\tools\rcm-say-delivery.cjs claim

**Warning:** claim atomically marks the batch in-flight before printing it; do not invoke casually or rerun it expecting the same batch. Its printed Base64URL data includes private message content. The external .NET sender accepts the exact one-batch JSON from claim; normal console status output should never be piped into the sender.

### Explicit live dispatch (not executed during this milestone)

**Warning:** dispatch can type text and Enter into the running RIFT client. It must be used only after a fresh host/process/window/executable inspection, physical confirmation that RCM's editor has focus, and the four acknowledgments below. Do **not** reuse example pins or the PID/HWND/ticks from historical documentation.

    node .\tools\rcm-say-delivery.cjs dispatch --expect-host AMD-DESKTOP --pid LIVE_PID --hwnd 0xLIVE_HWND --start-ticks LIVE_PROCESS_START_TICKS --exe-path "FULL_RIFT_EXE_PATH" --exe-sha256 LIVE_EXE_SHA256 --ack-send-in-game --ack-editor-focused --ack-submit --ack-batch

The .NET sender independently validates the pinned foreground RIFT process and executable SHA before any input, rechecking window ownership before each key sequence. It never activates the game window on its own, touches the clipboard, or retries partial insertion. Its Win32 receipt does not prove an imported RCM history row.

After independently confirming the matching token in-game and saving through RIFT's normal /reloadui lifecycle, check the correct character-specific SavedVariables file:

    node .\tools\rcm-say-delivery.cjs verify-disk --file "C:\path\to\SavedVariables\RiftChatModern.lua" --python "C:\work\riftreader2\.venv\Scripts\python.exe"

This verification is strictly read-only and requires a matching imported token on the same retained row and a consistent RIFT save checkpoint. A missing/stale/mismatched receipt leaves the transfer claimed. It does not trigger /reloadui, change the installed addon, or declare native social-chat capture.

Cancel an unresolved transfer without resending:

    node .\tools\rcm-say-delivery.cjs cancel --token A1B2C3D4E5F6 --ack-discard

Use the **actual active token** from status; the token above is fictional and is not an instruction to cancel any live item. Cancel can discard a potentially unsaved message. It cannot undo text already entered in RIFT.

## Verification approach

Automated Node tests use synthetic, temporary Log.txt files; they exercise the actual follower subprocess, two new messages queued in order, no stale replay, no Guild guesses, canonical Base64URL and token pairing, journal corruption, lock contention, one-in-flight serialization, no automatic resend, exact-token audit using the genuine Python disk auditor, successful .NET 10 no-input preflight, dispatch flag validation, and .NET's refusal of **impossible fake target pins before input**.

No real game keyboard dispatch, /reloadui, clipboard operation, or real SavedVariables write was conducted in the coordinator's test run.

## Remaining P0

Physically qualify one new supervised real Say import **through the coordinator**: start capture after log/host qualification, type one real Say using native chat, preflight the queued transfer, focus the RCM editor, dispatch using newly pinned process identity, inspect a unique HOST/SAY row, /reloadui and verify exact disk token. Only then can the new end-to-end coordinator be called physically accepted. Next qualify a second *different* social chat type from original RIFT file bytes before expanding supported parser formats.
