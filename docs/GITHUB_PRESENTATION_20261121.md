# GitHub presentation and maintenance

[← Project homepage](../README.md)

## Public-facing assets

| File | Purpose |
|---|---|
| [`assets/rcm-banner.svg`](../assets/rcm-banner.svg) | Wide, editable vector banner at the top of the README |
| [`assets/rcm-logo.svg`](../assets/rcm-logo.svg) | Reusable square RCM identity mark |
| [`assets/screenshots/rcm-v0.2.2-physical-names-redacted.png`](../assets/screenshots/rcm-v0.2.2-physical-names-redacted.png) | Genuine historical RIFT Live screenshot; labeled **v0.2.2** |
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

## Future screenshot refresh

When v0.2.19 is physically verified in-game, take a fresh screenshot using
RIFT's native screenshot function. Replace the **homepage screenshot path
and caption only after checking the image and exact running version**.
Retain the older v0.2.2 screenshot as historical evidence.

The original detailed README was archived as
[`ENGINEERING_ARCHIVE_README_THROUGH_20261121.md`](ENGINEERING_ARCHIVE_README_THROUGH_20261121.md).
