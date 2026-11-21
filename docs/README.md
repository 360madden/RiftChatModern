# RiftChatModern · Engineering documentation

[← Return to the project homepage](../README.md)

This folder preserves RCM's technical decisions, failures, tests, physical
acceptance evidence, and release-by-release research. The public README is a
short product landing page; **the original detailed README was preserved**
as [the complete engineering archive](ENGINEERING_ARCHIVE_README_THROUGH_20261121.md).

## Getting started and architecture

- [Addon transport and RIFT messaging limitations](ADDON_TRANSPORT.md)
- [Original concept and early development history](DEVELOPMENT_HISTORY_CONCEPT_TO_V0_2_2.md)
- [v0.2.11 provenance and API v2 contract](V0_2_11_STRUCTURED_PROVENANCE.md)
- [Live deployment and `/reloadui` policy](LIVE_DEPLOYMENT_RELOADUI_POLICY_20261120.md)
- [Post-deployment disk-audit hardening](POST_DEPLOY_DISK_AUDIT_HARDENING_20261120.md)
- [GitHub presentation assets and social-preview setup](GITHUB_PRESENTATION_20261121.md)

## Releases and root-cause fixes

| Milestone | Technical record |
|---|---|
| v0.2.2 | [Physical startup fix](V0_2_2_LIVE_STARTUP_FIX.md) |
| v0.2.4 | [Resizable UI](V0_2_4_RESIZE.md) |
| v0.2.5 | [Codebase bug hunt](V0_2_5_CODEBASE_BUGHUNT.md) |
| v0.2.6 | [Editor history and search](V0_2_6_EDITOR_HISTORY_AND_SEARCH.md) |
| v0.2.11 | [Physical import acceptance](V0_2_11_PHYSICAL_ACCEPTANCE_20261120.md) |
| v0.2.12 | [Save checkpoints](V0_2_12_SAVE_CHECKPOINT_AND_DISK_AUDIT.md) |
| v0.2.15 | [Import receipt persistence](V0_2_15_IMPORT_RECEIPT_AND_RELOAD.md) |
| v0.2.16 | [Persistent transfer tokens](V0_2_16_PERSISTENT_IMPORT_TOKENS_20261120.md) |
| v0.2.17 | [RCM-owned editor import](V0_2_17_RCM_EDITOR_IMPORT_20261120.md) |
| v0.2.18 | [Focus and game screenshots](V0_2_18_FOCUS_AND_GAME_SCREENSHOTS_20261120.md) |
| v0.2.19 | [Progress-based multipart idle deadline](V0_2_19_MULTIPART_IDLE_TIMEOUT_20261120.md) |
| v0.2.20 | [Glass UI / reference-inspired skin](V0_2_20_GLASS_UI_20261121.md) |

All intermediate milestone reports remain in this directory. See the
[complete engineering archive](ENGINEERING_ARCHIVE_README_THROUGH_20261121.md)
for the historical timeline and cross-links.

## Windows companion and host import

- [Guarded editor sender prototype](EDITOR_SENDER_PROTOTYPE_20261120.md)
- [Complete multipart .NET 10 batch validation](RCM_MULTIPART_EDITOR_BATCH_20261121.md)
- [Exact-chat observer → batch gate](RCM_LOG_OBSERVER_BATCH_GATE_20261121.md)
- [Windows editor preflight](RCM_EDITOR_PREFLIGHT_DOTNET10_20261120.md)
- [Host observer design](HOST_CHAT_OBSERVER_20261120.md)
- [Host-observer editor output](HOST_OBSERVER_EDITOR_MODE_20261120.md)
- [Complete-message-only import guard](HOST_IMPORT_TRUNCATED_MESSAGE_FIX_20261120.md)

## RIFT native chat discovery

- [RIFT chat API capability audit](CHAT_API_CAPABILITY_CAPTURE_20261120.md)
- [Native player-chat transport alternatives](CHAT_TRANSPORT_ALTERNATIVES_20261120.md)
- [Two-phase marker and exact-text observer](CHAT_OBSERVER_TWO_PHASE_20261120.md)
- [Exact text acceptance procedure](EXACT_CHAT_TEXT_PROOF_20261120.md)
- [RIFT November 17 logging implementation](RIFT_NOV17_LOGGING_IMPLEMENTATION_20261120.md)
- [Exact-build noncombat line writer](RIFT_NOV17_NONCOMBAT_LINE_WRITER_20261120.md)

**Evidence boundary:** the noncombat file-writing path is statically verified
for one executable build; ordinary native player chat capture is not yet
physically verified. Host-imported chat remains labeled as host-origin data.

## Screenshot and physical acceptance

- [Early physical UI acceptance](LIVE_ACCEPTANCE_V0_2_2_20261120.md)
- [One-command screenshot workflow](RCM_ONE_COMMAND_SCREENSHOT_20261120.md)
- [RIFT screenshot trigger](RCM_NUMPAD_SCREENSHOT_TRIGGER_20261120.md)

The public homepage includes a genuine historical v0.2.2 game screenshot
with an explicit version caption; it does not claim that screenshot represents
the current v0.2.20 UI.
