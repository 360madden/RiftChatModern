# RiftChatModern · Engineering documentation

[← Return to the project homepage](../README.md)

This folder preserves RCM's technical decisions, failures, tests, physical
acceptance evidence, and release-by-release research. The public README is a
short product landing page; **the original detailed README was preserved**
as [the complete engineering archive](ENGINEERING_ARCHIVE_README_THROUGH_20261121.md).

## Getting started and architecture

- **[Saturday November 21 engineering handoff](HANDOFF_20261121_SATURDAY.md)** — most recent verified status, source map, test commands, remaining limitations, P0 physical acceptance plan and remote publication context
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
| v0.2.21 | [Independent timestamp/channel/sender/body columns](V0_2_21_MESSAGE_COLUMNS_20261121.md) |
| v0.2.22 | [Native console subscription categories and provenance fixes](V0_2_22_NATIVE_RIFT_CONSOLE_CATEGORIES_20261121.md) |
| v0.2.23 | [Physical RIFT Say → Log.txt → RCM Imports → SavedVariables](V0_2_23_PHYSICAL_RIFT_SAY_LOG_IMPORT_20261121.md) |

All intermediate milestone reports remain in this directory. See the
[complete engineering archive](ENGINEERING_ARCHIVE_README_THROUGH_20261121.md)
for the historical timeline and cross-links.

## Windows companion and host import

- [Physically verified real Say message and disk persistence](V0_2_23_PHYSICAL_RIFT_SAY_LOG_IMPORT_20261121.md)
- [Bounded read-only Say follower (Windows host, not automatic game delivery)](BOUNDED_SAY_FOLLOW_20261121.md)
- [Serialized Say delivery coordinator, private state and exact-token receipts](SAY_DELIVERY_COORDINATOR_20261121.md)
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

**Evidence boundary:** one controlled Say message is now physically verified
in the game-created noncombat Log.txt, in RCM's own Imports UI, and in the
character's persisted SavedVariables. **Guild/Party/Tell/public capture,
continuous delivery and native social sending are not yet verified.**
Host-imported chat remains labeled as host-origin data.

## Screenshot and physical acceptance

- [Early physical UI acceptance](LIVE_ACCEPTANCE_V0_2_2_20261120.md)
- [Physical v0.2.22 Game, Loot, Player, and Channel subscription acceptance](V0_2_22_NATIVE_RIFT_CONSOLE_CATEGORIES_20261121.md)
- [Physical v0.2.21 drag/resize, editor input and persistence proof](V0_2_21_UI_INTERACTION_ACCEPTANCE_20261121.md)
- [Physical v0.2.21 columns, tabs and modal acceptance](V0_2_21_PHYSICAL_ACCEPTANCE_20261121.md)
- [Physical v0.2.20 screenshot and managed foreground acceptance](V0_2_20_NATIVE_SCREENSHOT_ACCEPTANCE_20261121.md)
- [One-command screenshot workflow](RCM_ONE_COMMAND_SCREENSHOT_20261120.md)
- [RIFT screenshot trigger](RCM_NUMPAD_SCREENSHOT_TRIGGER_20261120.md)

The public homepage displays a genuine, privacy-safe cropped
v0.2.22 CONSOLE inspector screenshot from the physical RIFT client.
The historical v0.2.21 and v0.2.2 images are retained and labeled. See
[GitHub presentation and screenshot provenance](GITHUB_PRESENTATION_20261121.md).
