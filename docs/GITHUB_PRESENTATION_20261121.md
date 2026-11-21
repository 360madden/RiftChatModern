# GitHub presentation and maintenance

[← Project homepage](../README.md)

## Public-facing assets

| File | Purpose |
|---|---|
| [`assets/rcm-banner.svg`](../assets/rcm-banner.svg) | Wide, editable vector banner at the top of the README |
| [`assets/rcm-logo.svg`](../assets/rcm-logo.svg) | Reusable square RCM identity mark |
| [`assets/screenshots/rcm-v0.2.21-live-ui-cropped.jpg`](../assets/screenshots/rcm-v0.2.21-live-ui-cropped.jpg) | **Current homepage image:** genuine physical RIFT Live v0.2.21 screenshot, cropped to the chat window; player name and HUD excluded |
| [`assets/screenshots/rcm-v0.2.2-physical-names-redacted.png`](../assets/screenshots/rcm-v0.2.2-physical-names-redacted.png) | Historical v0.2.2 physical screenshot; player-name regions blurred; retained for comparison |
| [`assets/rcm-social-preview.png`](../assets/rcm-social-preview.png) | 1280×640 GitHub social sharing image, ready for upload |
| [`tools/create_social_preview.py`](../tools/create_social_preview.py) | Reproducible social-preview generator (optional Pillow dependency) |

## GitHub About

The repository description and topics were updated using the authenticated
GitHub CLI and independently read back.

**Description:** Modern dark-mode chat-style console and addon diagnostics
hub for RIFT Live. Lua 5.1 • searchable history • developer API.

**Topics:** `rift`, `rift-mmo`, `lua`, `lua51`, `game-addon`,
`chat-ui`, `developer-tools`.

## GitHub social preview

GitHub does not expose a supported repository social-preview upload through
the available repository CLI/API commands. The **image has been generated**,
but setting it as the actual GitHub social preview remains a manual repository
settings action:

1. Open `https://github.com/360madden/RiftChatModern/settings`.
2. Under **General → Social preview**, choose **Edit** or **Upload an image**.
3. Upload `assets/rcm-social-preview.png` from the local repository.
4. Save and confirm the preview on the repository settings page.

Do not report this setting as applied until it has been verified in GitHub.

## Content policy for the README

- Lead with what RCM is and what the player can do now.
- Keep the original RIFT chat limitations visible near the top.
- Label historical screenshots with their exact release.
- Do not conflate Lua 5.1 mocked tests, Windows tool tests, and physical
  RIFT acceptance.
- Put technical investigations in `docs/`, not in the README hero.
- Do not create a license without the owner's explicit choice. The code is
  public, but a general software license has not yet been selected.

## Screenshot refresh completed: v0.2.21

RCM v0.2.21 was verified running in the real RIFT client. The native JPEG
`2026-11-21_101443.jpg` was inspected at 2560×1369 (SHA-256
`607acec1d8e64449e4c321540781caa009f63514987ca313a4dd388b4ca227da`).
A 992×820 pixel crop `(1523,342,2515,1162)` was saved as the public
`rcm-v0.2.21-live-ui-cropped.jpg` image. Only the RCM window and surrounding
background are included; the user's name-bearing HUD and native chat area are
outside the crop. The image is an actual game screenshot, **not a mockup**.
The previous v0.2.2 screenshot remains in the repository and linked from
README history. Future visual updates should follow the same physical
verification and privacy review before publishing.

The original detailed README was archived as
[`ENGINEERING_ARCHIVE_README_THROUGH_20261121.md`](ENGINEERING_ARCHIVE_README_THROUGH_20261121.md).
