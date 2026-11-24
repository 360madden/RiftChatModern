# RCM v0.2.24 — Persistent channel palette foundation

**Date:** November 23, 2026 (EST) · **Development machine:** LEGION · **Base:** 11405efa37adc8d2e023f135c573889044a32501

## Scope and evidence

RCM-053 is partially implemented. The source release is v0.2.24; the last physically qualified RIFT addon remains v0.2.23. No physical deployment or game acceptance was attempted during this cycle because AMD-DESKTOP is unavailable. The new functionality is tested in actual Lua 5.1 with RIFT API mocks, not presented as a live-game screenshot or save receipt.

## User controls

Use RCM's local editor:

- `:color help` — syntax
- `:color list` — effective color values
- `:color show host_public` — inspect a single value
- `:color set host_public #F0E080` — apply a bright custom RGB color
- `:color reset host_public` — restore that default
- `:color reset all` — restore all defaults

The original RIFT chat also supports `/rcm color list` and the same show/set/reset arguments. The command path does not append diagnostic history rows; a successful mutation updates the saved-state revision, while a read or no-op does not.

## Model and rendering contract

- Fifteen fixed keys: system, npc, addons, dev, combat, import, host_general, host_say, host_yell, host_emote, host_local, host_public, host_party, host_guild, host_tell.
- Keys for host families are presentation categories only, not proof that RCM receives the corresponding live social channels.
- The optional character SavedVariables field `channelColors` stores only non-default overrides as uppercase six-digit hex strings. History schema remains 2.
- Malformed optional settings are repaired independently of history, import tokens, and other settings.
- Color validation accepts six RGB hex digits with an optional leading #. Colors below a conservative relative-luminance threshold of 0.25 are rejected for readability. Actual contrast on varying game backgrounds still requires physical review.
- Rows update the channel-label foreground and marker background immediately; message body, source, timestamp, and HOST/LEGACY/EXTERNAL provenance remain independent.
- Imported messages with non-host provenance use the generic import color. Unrecognized general host subtypes fall back to host_general.

## Additive API v2

`RiftChatModernAPI.GetChannelColors()` returns a fresh map of effective colors. `SetChannelColor(key, hex)` and `ResetChannelColor(key)` return true on success, otherwise nil and an error string. Reset accepts the explicit key all. Before initialization these methods return nil, not_ready. No API version bump is necessary for this additive surface.

## Validation and next steps

Nine focused Lua 5.1 tests passed, covering default initialization, normalization, sparse persistence, malformed/dark values, corrupted saved settings, provenance, history/revision isolation, immediate row rendering, and readiness.

Final complete Python/Lua regression: **330 passed, zero failures or skips** (34.699s). The Node host suite was unchanged in this cycle; its immediately preceding baseline was 129/129. Git diff check passed.

Remaining RCM-053 work: graphical swatch editor, visibility toggles, focus/geometry interaction checks, and physical RIFT screenshot plus independent character-save acceptance. The immediate critical-path M1 public-channel import remains blocked on the live workstation.
