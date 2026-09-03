# Universal Social Rotator — Design Spec

**Date:** 2026-09-04  
**Status:** Approved for planning  
**Widget type:** `social_rotator`  
**Approach:** Full sibling of Live Leaderboard / Stream Goal (Approach 1)

## 1. Goal

Ship one reusable OBS/browser-source overlay that:

1. Rotates through creator-configured social platforms on a fixed timeline.
2. Presents them as a cyberpunk broadcast HUD matching the provided visual reference.
3. Includes the reference’s bottom stats strip as part of the same widget.
4. Fits the existing Stream Cheremsha overlay stack (config, controller, HTML HUD, QML settings).

This is **not** a set of per-platform widgets and **not** a generic social card.

## 2. Visual target

Primary visual reference: creator-provided mockup (Twitch hero + NEXT countdown + secondary platforms + bottom stats).

Must match as closely as possible:

- Wide, short horizontal HUD proportions
- Hero icon holographic treatment (frame, orbital ring, glow, restrained particles/scan)
- Typography hierarchy: `LIVE SOCIAL` → platform → **username** → URL
- Center `NEXT / NN / SEC` secondary indicator
- Right-side secondary platform cards with pagination when needed
- Thin neon HUD frame, dark glass interior, cyan/magenta/green energy language
- Bottom five-cell stats strip

**Typography decision:** match existing product fonts strictly — **Press Start 2P** + **VT323** (same as Stream Goal / Live Leaderboard). Do not introduce random web fonts.

**Themes** (HUD chrome only; never erase platform brand identity):

- `neon_cyber` (default)
- `synthwave`
- `toxic`
- `ice`
- `amber`

Platform accent colors affect icon glow, accent lines, energy, active state, and transitions — not a full-panel brand flood fill.

## 3. Architecture

Mirror Live Leaderboard:

| Module | Responsibility |
| --- | --- |
| `social_platforms.py` | Central `PlatformDefinition` registry |
| `social_rotator_overlay_config.py` | QSettings JSON load/save/migrate/defaults |
| `social_rotator_rotation.py` | Timeline engine over enabled platforms |
| `social_rotator_stats.py` | Session stats aggregation |
| `social_rotator_controller.py` | Timers, ingest hooks, WS publish |
| `social_rotator_overlay.py` | HTML/CSS/JS render (`type = "social_rotator"`) |
| `widgets_qml_api.py` + `WidgetsView.qml` | Settings + preview |
| `registry.py` + `main_window.py` | Register + wire events |

Hard boundaries:

- Rotation is timeline-only. TikTok ranking/event traffic never interrupts it.
- Stats update independently and only refresh their cells.
- Theme accents HUD; platform identity stays on icon/glow/accents.

## 4. Data model

### PlatformDefinition (code-owned)

```text
id, name, accent, icon_key, url_template
```

Built-ins: Twitch, YouTube, Kick, Telegram, TikTok, Instagram, Discord, X, Facebook.

### SocialPlatformEntry (user config)

```text
id, platform, username, url (optional override), enabled, order
```

Empty `url` → generate from `url_template` + normalized username.

### SocialRotatorConfig

```text
platforms[]
rotation_interval_ms              # default 8000
transition                        # glitch_morph | data_stream | energy_burst | scan | pixel_dissolve | fade
theme                             # neon_cyber | synthwave | toxic | ice | amber
show_url
show_countdown
show_secondary_platforms
enable_glow
enable_particles
enable_crt
show_latest_follower
show_latest_donation
show_stream_time
show_top_donator
show_online
tiktok_coin_to_value_rate         # default 1.0; coins * rate → comparable value units
scale_percent                     # default 100
accent_color                      # HUD theme accent; default #00ffff
```

Default first-run `platforms[]` mirrors the reference (all enabled): Twitch, YouTube, Kick, Telegram, TikTok — empty usernames until the creator fills them (rotation stays paused until ≥1 enabled entry has a username).

### Public WS state

```text
config
rotation: {
  active_index, platform_id, started_at_ms, interval_ms,
  transition_token, remaining_ms
}
platforms_enabled: [{ id, platform, username, url, order }]
stats: {
  latest_follower: { name } | null
  latest_donation: { name, value, source } | null
  top_donator: { name, value } | null
  stream_started_at_ms | null
  viewers_by_platform: { tiktok, twitch, kick, youtube, ... }
  viewers_total
}
```

Donation/gift `value` is already converted. UI renders `name - N ◆` with **no real currency labels**.

## 5. Rotation logic

Deterministic server-owned timeline (same ownership model as Live Leaderboard):

1. Build ordered list of **enabled** platforms with non-empty usernames.
2. Controller `QTimer` (~250ms) derives `remaining_ms` from `started_at_ms + rotation_interval_ms`.
3. On expiry: advance index, increment `transition_token`, republish.
4. Overlay triggers transition on `transition_token` change.
5. Config patches **preserve** active platform + `started_at_ms` when the active entry still exists; reset only if it was removed/disabled.
6. Platform/social events never reset the rotation clock.

Edge cases:

- 0 enabled platforms → empty/awaiting state; rotation paused.
- 1 enabled platform → no auto-advance; hide countdown.
- Unknown platform id on load → drop entry.
- Require username on save (invalid entries rejected).

## 6. Transitions & idle motion

### Transition presets

Default: `glitch_morph`.

Also: `data_stream`, `energy_burst`, `scan`, `pixel_dissolve`, `fade`.

Duration ~500–1000ms. Reuse existing overlay CSS/JS VFX patterns (class toggles, short sequences). Clean up before starting the next transition.

### Idle

Restrained only: breathing glow, slow orbital ring, capped particles, light scan drift, rare HUD flicker. Safe for hours in OBS.

### Performance

- Cap particle count
- Prefer CSS transforms/opacity
- No accumulating DOM / leaked timers
- Single rotation ownership in controller

## 7. Bottom stats strip

Part of the same widget. Each cell independently toggleable.

| Cell | Source |
| --- | --- |
| Latest Follower | TikTok follow events |
| Latest Donation | Most recent among Donatello, Donatik, TikTok gifts |
| Stream Time | Elapsed since TikTok live/room connected this session |
| Top Donator | Highest converted value this session across Donatello + Donatik + TikTok gifts |
| Online | Sum of last-known viewers across connected platforms (TikTok + Twitch + Kick + YouTube; 0 if disconnected) |

### Value conversion

- Donatello / Donatik: use the numeric donation amount as value units 1:1 (ignore currency code in display and ranking).
- TikTok gifts: `coins * tiktok_coin_to_value_rate` (default rate `1.0`; creator-adjustable in settings).
- Display: rounded numeric amount + diamond ◆ icon (no UAH/USD/etc.).
- Ranking/latest comparison always uses the converted numeric `value` field.

Null stats show muted placeholders (`—`), never crash the overlay.

## 8. Settings UI

Follow existing QML conventions in `WidgetsView.qml` (no drag-and-drop):

- Platform list with Add / Remove / Enable / Edit / Up / Down
- Rotation interval
- Transition preset
- Theme
- Toggles: URL, secondary platforms, countdown, glow, particles, CRT
- Per-stat toggles for all five bottom cells
- TikTok coin→value rate
- Scale / accent as with sibling widgets

## 9. Responsive behavior

One widget, responsive sizing:

1. Hide URL before shrinking hero username
2. Shrink / auto-scroll / paginate secondary platforms before crushing primary content
3. Never allow username overlap or horizontal overflow
4. Keep active icon recognizable on narrow layouts

## 10. Integration points

Wire from `main_window.py` alongside existing overlay controllers:

- TikTok follow → latest follower
- TikTok gift → latest donation + top donator (converted)
- Donatello / Donatik donation signals → same donation pool
- TikTok room connect/disconnect → `stream_started_at_ms`
- Per-platform viewer updates → `viewers_by_platform` / `viewers_total`

Register in `OverlayRegistry`. Expose config/preview via `widgets_qml_api.py`.

## 11. Testing & acceptance

### Automated

- Config round-trip, migrate, corrupt → defaults + backup
- Platform URL generation / username normalization
- Rotation preserve-on-patch, loop, 0/1 platform behavior
- Stats conversion, ranking, viewer sum, stream timer
- Registry + QML API smoke

### Visual acceptance

- Matches reference composition and hierarchy
- Hero username dominant; holographic icon; HUD frame
- Secondary platforms feel integrated
- Countdown correct but secondary
- Transitions premium and short
- Idle safe for long OBS runs
- Looks coherent next to Stream Goal and Live Leaderboard

## 12. Out of scope (v1)

- Separate `twitch_widget` / `youtube_widget` / etc.
- Drag-and-drop platform reordering
- Bottom strip as a separate overlay type
- Real currency labels on donation cells
- Event-driven interruption of social rotation

## 13. Decisions log

| Topic | Decision |
| --- | --- |
| Scope | Top rotator **and** bottom stats strip in one widget |
| Architecture | Full Live Leaderboard sibling |
| Latest Follower | TikTok follow |
| Latest Donation | Donatello + Donatik + TikTok gift |
| Stream Time | Elapsed since TikTok live connect |
| Top Donator | Max converted value this stream (same donation pool) |
| Online | Sum across connected platforms |
| Gift vs money | Configurable coin→value rate (default 1.0); display ◆ not currency names |
| Typography | Press Start 2P + VT323 only |
| Stats toggles | Each bottom cell independently toggleable |
| Default transition | Glitch Morph |
| Default platforms | Twitch, YouTube, Kick, Telegram, TikTok (usernames empty until set) |
