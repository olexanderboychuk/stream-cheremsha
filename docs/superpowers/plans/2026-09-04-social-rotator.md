# Universal Social Rotator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship one `social_rotator` OBS overlay that rotates creator social platforms on a server timeline and shows a matching cyberpunk HUD plus bottom stats strip.

**Architecture:** Full sibling of Live Leaderboard — QSettings config, platform registry, rotation engine, stats session, controller + WS publish, HTML HUD, QML settings, `main_window` event wiring. Rotation is timeline-only; stats update independently.

**Tech Stack:** Python 3.11, PySide6/QML, existing OverlayRegistry/WebSocket/pubsub, VT323 + Press Start 2P (Google Fonts, same as Stream Goal / Live Leaderboard), pytest.

**Spec:** `docs/superpowers/specs/2026-09-04-social-rotator-design.md`

## Global Constraints

- Widget type id: `social_rotator` only (no per-platform widget types)
- Fonts: Press Start 2P + VT323 only
- Default transition: `glitch_morph`; duration ~500–1000ms
- Themes: `neon_cyber` | `synthwave` | `toxic` | `ice` | `amber`
- Donation display: numeric value + ◆ (no currency codes)
- TikTok coin rate default: `1.0`
- Rotation must not reset on unrelated TikTok ranking/events
- Bottom stats cells independently toggleable
- Python: no `try/except Exception: pass`
- Match visual reference proportions (hero left, NEXT center, secondary right, stats row below)
- Follow existing overlay file patterns under `src/stream_cheremsha/overlays/`

## File map

| File | Responsibility |
| --- | --- |
| `src/stream_cheremsha/overlays/social_platforms.py` | PlatformDefinition registry + URL build |
| `src/stream_cheremsha/overlays/social_rotator_rotation.py` | Timeline over enabled entries |
| `src/stream_cheremsha/overlays/social_rotator_overlay_config.py` | Config dataclass + QSettings |
| `src/stream_cheremsha/overlays/social_rotator_stats.py` | Session stats aggregation |
| `src/stream_cheremsha/overlays/social_rotator_controller.py` | Timers, ingest, publish |
| `src/stream_cheremsha/overlays/social_rotator_overlay.py` | HTML/CSS/JS HUD |
| `src/stream_cheremsha/overlays/registry.py` | Register type |
| `src/stream_cheremsha/ui/widgets_qml_api.py` | URL/config API |
| `src/stream_cheremsha/qml/WidgetsView.qml` | Settings UI |
| `src/stream_cheremsha/ui/main_window.py` | Wire controller + events |
| `src/stream_cheremsha/ui/donations_qml_api.py` | Notify on new Donatik/Donatello rows |
| `tests/test_social_rotator_*.py` | Unit/integration tests |
| `tests/test_overlays_registry.py` | Registry assertion |
| `CHANGELOG.md` | User-facing note |

---

### Task 1: Platform registry

**Files:**
- Create: `src/stream_cheremsha/overlays/social_platforms.py`
- Test: `tests/test_social_rotator_platforms.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True, slots=True) class PlatformDefinition: id: str; name: str; accent: str; icon_key: str; url_template: str`
  - `PLATFORM_DEFINITIONS: dict[str, PlatformDefinition]`
  - `ALL_PLATFORM_IDS: tuple[str, ...]`
  - `def get_platform(platform_id: str) -> PlatformDefinition | None`
  - `def normalize_username(platform_id: str, username: str) -> str`
  - `def build_platform_url(platform_id: str, username: str, url_override: str = "") -> str`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

from stream_cheremsha.overlays.social_platforms import (
    ALL_PLATFORM_IDS,
    build_platform_url,
    get_platform,
    normalize_username,
)


def test_builtin_platforms_present() -> None:
    for pid in (
        "twitch",
        "youtube",
        "kick",
        "telegram",
        "tiktok",
        "instagram",
        "discord",
        "x",
        "facebook",
    ):
        assert pid in ALL_PLATFORM_IDS
        p = get_platform(pid)
        assert p is not None
        assert p.name
        assert p.accent.startswith("#")
        assert "{username}" in p.url_template or p.url_template == ""


def test_normalize_and_url_twitch() -> None:
    assert normalize_username("twitch", "@Kodi_The_Cat") == "kodi_the_cat"
    assert build_platform_url("twitch", "Kodi_The_Cat") == "https://twitch.tv/kodi_the_cat"


def test_url_override_wins() -> None:
    assert (
        build_platform_url("twitch", "x", url_override="https://example.com/me")
        == "https://example.com/me"
    )


def test_unknown_platform() -> None:
    assert get_platform("nope") is None
    assert build_platform_url("nope", "x") == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_social_rotator_platforms.py -v`  
Expected: FAIL (module not found)

- [ ] **Step 3: Write minimal implementation**

Create `social_platforms.py` with definitions:

| id | name | accent | url_template |
| --- | --- | --- | --- |
| twitch | TWITCH | #9146FF | `https://twitch.tv/{username}` |
| youtube | YOUTUBE | #FF0000 | `https://youtube.com/@{username}` |
| kick | KICK | #53FC18 | `https://kick.com/{username}` |
| telegram | TELEGRAM | #29B6F6 | `https://t.me/{username}` |
| tiktok | TIKTOK | #69C9D0 | `https://tiktok.com/@{username}` |
| instagram | INSTAGRAM | #E1306C | `https://instagram.com/{username}` |
| discord | DISCORD | #5865F2 | `` (empty — invite URLs are overrides) |
| x | X | #FFFFFF | `https://x.com/{username}` |
| facebook | FACEBOOK | #1877F2 | `https://facebook.com/{username}` |

`normalize_username`: strip, remove leading `@` for twitch/youtube/tiktok/telegram/kick/x/instagram; lowercase for twitch/kick; keep YouTube casing after stripping `@`.

`build_platform_url`: if override non-empty after strip, return it; else format template with normalized username; empty template → `""`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_social_rotator_platforms.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/stream_cheremsha/overlays/social_platforms.py tests/test_social_rotator_platforms.py
git commit -m "feat(social-rotator): add platform registry and URL builders"
```

---

### Task 2: Rotation engine

**Files:**
- Create: `src/stream_cheremsha/overlays/social_rotator_rotation.py`
- Test: `tests/test_social_rotator_rotation.py`

**Interfaces:**
- Consumes: platform entry dicts with `id`, `platform`, `username`, `url`, `enabled`, `order`
- Produces:
  - `@dataclass(frozen=True, slots=True) class SocialRotationEntry: entry_id: str; platform: str; username: str; url: str`
  - `@dataclass(slots=True) class SocialRotatorRotationEngine` with:
    - `entries: list[SocialRotationEntry]`
    - `active_index: int`
    - `transition_token: int`
    - `started_at_ms: int`
    - `interval_ms: int`
    - `classmethod from_entries(entries, *, interval_ms: int, now_ms: int | None = None) -> SocialRotatorRotationEngine`
    - `current_entry -> SocialRotationEntry | None`
    - `replace_entries(entries, *, interval_ms: int, now_ms: int | None = None, preserve_position: bool = True) -> None`
    - `advance(*, now_ms: int | None = None) -> SocialRotationEntry | None`
    - `tick(*, now_ms: int | None = None) -> bool`
    - `remaining_ms(*, now_ms: int | None = None) -> int`
    - `presentation_dict(*, server_now_ms: int | None = None) -> dict[str, object]`
  - `def enabled_rotation_entries(platforms: list[dict[str, object]]) -> list[SocialRotationEntry]`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

from stream_cheremsha.overlays.social_rotator_rotation import (
    SocialRotatorRotationEngine,
    enabled_rotation_entries,
)


def _plats() -> list[dict[str, object]]:
    return [
        {"id": "1", "platform": "twitch", "username": "a", "url": "", "enabled": True, "order": 0},
        {"id": "2", "platform": "youtube", "username": "b", "url": "", "enabled": True, "order": 1},
        {"id": "3", "platform": "kick", "username": "", "url": "", "enabled": True, "order": 2},
        {"id": "4", "platform": "telegram", "username": "c", "url": "", "enabled": False, "order": 3},
    ]


def test_enabled_entries_skip_disabled_and_empty_username() -> None:
    ents = enabled_rotation_entries(_plats())
    assert [e.platform for e in ents] == ["twitch", "youtube"]


def test_advance_and_token() -> None:
    ents = enabled_rotation_entries(_plats())
    rot = SocialRotatorRotationEngine.from_entries(ents, interval_ms=8000, now_ms=1000)
    assert rot.transition_token == 1
    assert rot.current_entry is not None
    assert rot.current_entry.platform == "twitch"
    rot.advance(now_ms=2000)
    assert rot.transition_token == 2
    assert rot.current_entry.platform == "youtube"
    rot.advance(now_ms=3000)
    assert rot.current_entry.platform == "twitch"


def test_tick_respects_interval() -> None:
    ents = enabled_rotation_entries(_plats())
    rot = SocialRotatorRotationEngine.from_entries(ents, interval_ms=5000, now_ms=10_000)
    assert rot.tick(now_ms=12_000) is False
    assert rot.tick(now_ms=15_000) is True
    assert rot.current_entry.platform == "youtube"


def test_preserve_position_on_replace() -> None:
    ents = enabled_rotation_entries(_plats())
    rot = SocialRotatorRotationEngine.from_entries(ents, interval_ms=8000, now_ms=1000)
    rot.advance(now_ms=2000)
    token = rot.transition_token
    started = rot.started_at_ms
    rot.replace_entries(ents, interval_ms=8000, now_ms=9000, preserve_position=True)
    assert rot.current_entry.platform == "youtube"
    assert rot.transition_token == token
    assert rot.started_at_ms == started


def test_single_entry_no_auto_advance() -> None:
    ents = enabled_rotation_entries(
        [{"id": "1", "platform": "twitch", "username": "a", "url": "", "enabled": True, "order": 0}]
    )
    rot = SocialRotatorRotationEngine.from_entries(ents, interval_ms=1000, now_ms=0)
    assert rot.tick(now_ms=5000) is False
    assert rot.remaining_ms(now_ms=5000) == 0


def test_empty_entries_paused() -> None:
    rot = SocialRotatorRotationEngine.from_entries([], interval_ms=8000, now_ms=0)
    assert rot.current_entry is None
    assert rot.tick(now_ms=99999) is False
    assert rot.presentation_dict(server_now_ms=100)["active_index"] == -1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_social_rotator_rotation.py -v`  
Expected: FAIL (module not found)

- [ ] **Step 3: Write minimal implementation**

Mirror `live_leaderboard_rotation.py` patterns:

- `enabled_rotation_entries`: sort by `order`, keep `enabled` and non-empty username; resolve URL via `build_platform_url`
- `from_entries`: empty list OK; `interval_ms` clamped to `[1000, 120000]`
- `tick`: if `len(entries) < 2`, return False; else advance when elapsed ≥ interval
- `remaining_ms`: 0 when `< 2` entries; else `max(0, interval_ms - elapsed)`
- `presentation_dict` keys: `active_index`, `platform_id` (entry platform), `entry_id`, `started_at_ms`, `interval_ms`, `transition_token`, `remaining_ms`, `server_now_ms`

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_social_rotator_rotation.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/stream_cheremsha/overlays/social_rotator_rotation.py tests/test_social_rotator_rotation.py
git commit -m "feat(social-rotator): add timeline rotation engine"
```

---

### Task 3: Overlay config

**Files:**
- Create: `src/stream_cheremsha/overlays/social_rotator_overlay_config.py`
- Test: `tests/test_social_rotator_overlay_config.py`

**Interfaces:**
- Produces:
  - `SOCIAL_ROTATOR_OVERLAY_CONFIG_SCHEMA_VERSION = 1`
  - `SOCIAL_ROTATOR_OVERLAY_CONFIG_QSETTINGS_KEY = "overlays/social_rotator/main/config_json"`
  - `@dataclass(frozen=True, slots=True) class SocialRotatorOverlayConfig` with fields from the spec
  - `social_rotator_overlay_config_defaults() -> SocialRotatorOverlayConfig`
  - `social_rotator_overlay_config_from_json_text(text: str) -> SocialRotatorOverlayConfig`
  - `social_rotator_overlay_config_to_public_dict(cfg) -> dict[str, object]`
  - `social_rotator_overlay_config_to_json_text(cfg) -> str`
  - `load_social_rotator_overlay_config(settings: QSettings | None = None) -> SocialRotatorOverlayConfig`
  - `save_social_rotator_overlay_config(cfg, settings: QSettings | None = None) -> None`
  - `parse_platforms(cfg) -> list[dict[str, object]]`
  - `VALID_TRANSITIONS`, `VALID_THEMES` frozensets

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

import json

from PySide6.QtCore import QSettings

from stream_cheremsha.overlays.social_rotator_overlay_config import (
    load_social_rotator_overlay_config,
    parse_platforms,
    save_social_rotator_overlay_config,
    social_rotator_overlay_config_defaults,
    social_rotator_overlay_config_from_json_text,
    social_rotator_overlay_config_to_json_text,
)


def test_defaults_have_five_platforms() -> None:
    cfg = social_rotator_overlay_config_defaults()
    plats = parse_platforms(cfg)
    assert [p["platform"] for p in plats] == [
        "twitch",
        "youtube",
        "kick",
        "telegram",
        "tiktok",
    ]
    assert cfg.rotation_interval_ms == 8000
    assert cfg.transition == "glitch_morph"
    assert cfg.theme == "neon_cyber"
    assert cfg.tiktok_coin_to_value_rate == 1.0


def test_roundtrip_clamps() -> None:
    cfg = social_rotator_overlay_config_defaults().replace(
        rotation_interval_ms=50,
        scale_percent=10,
        transition="nope",
        theme="nope",
        tiktok_coin_to_value_rate=-1,
    )
    cfg2 = social_rotator_overlay_config_from_json_text(
        social_rotator_overlay_config_to_json_text(cfg)
    )
    assert cfg2.rotation_interval_ms == 1000
    assert cfg2.scale_percent == 40
    assert cfg2.transition == "glitch_morph"
    assert cfg2.theme == "neon_cyber"
    assert cfg2.tiktok_coin_to_value_rate == 0.0


def test_drops_unknown_platform_entries() -> None:
    raw = {
        "schema_version": 1,
        "platforms": [
            {"id": "1", "platform": "twitch", "username": "a", "enabled": True, "order": 0},
            {"id": "2", "platform": "myspace", "username": "x", "enabled": True, "order": 1},
        ],
    }
    cfg = social_rotator_overlay_config_from_json_text(json.dumps(raw))
    plats = parse_platforms(cfg)
    assert len(plats) == 1
    assert plats[0]["platform"] == "twitch"


def test_qsettings_roundtrip(tmp_path) -> None:  # type: ignore[no-untyped-def]
    ini = str(tmp_path / "sr.ini")
    settings = QSettings(ini, QSettings.Format.IniFormat)
    cfg = social_rotator_overlay_config_defaults().replace(show_url=False)
    save_social_rotator_overlay_config(cfg, settings)
    loaded = load_social_rotator_overlay_config(settings)
    assert loaded.show_url is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_social_rotator_overlay_config.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement config module**

Follow `live_leaderboard_overlay_config.py` / `stream_goal_overlay_config.py` exactly for backup key, JSON parse, clamp patterns.

`SocialRotatorOverlayConfig` fields:

```python
schema_version: int
enabled: bool
platforms_json: str
rotation_interval_ms: int
transition: str
theme: str
show_url: bool
show_countdown: bool
show_secondary_platforms: bool
enable_glow: bool
enable_particles: bool
enable_crt: bool
show_latest_follower: bool
show_latest_donation: bool
show_stream_time: bool
show_top_donator: bool
show_online: bool
tiktok_coin_to_value_rate: float
scale_percent: int
accent_color: str
```

Defaults: five platforms enabled with empty usernames; all show_* / enable_* True; `accent_color="#00ffff"`; `scale_percent=100` clamped later to `[40, 250]` like siblings.

Public dict exposes `platforms` as a list (not raw JSON string), same as Live Leaderboard’s `sequence`.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_social_rotator_overlay_config.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/stream_cheremsha/overlays/social_rotator_overlay_config.py tests/test_social_rotator_overlay_config.py
git commit -m "feat(social-rotator): add overlay config persistence"
```

---

### Task 4: Stats session

**Files:**
- Create: `src/stream_cheremsha/overlays/social_rotator_stats.py`
- Test: `tests/test_social_rotator_stats.py`

**Interfaces:**
- Produces:
  - `@dataclass(slots=True) class SocialRotatorStatsSession`
  - Methods:
    - `reset() -> None`
    - `set_stream_started_at_ms(ms: int | None) -> None`
    - `on_follow(name: str) -> None`
    - `on_donation(*, name: str, amount: float, source: str, coin_rate: float = 1.0) -> None`  
      For `source=="tiktok_gift"`, `amount` is **coins**; value = `coins * coin_rate`.  
      For `donatik` / `donatello`, `amount` is numeric money 1:1.
    - `set_viewers(platform: str, count: int) -> None`
    - `clear_viewers(platform: str) -> None`
    - `to_public_dict() -> dict[str, object]`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

from stream_cheremsha.overlays.social_rotator_stats import SocialRotatorStatsSession


def test_follow_and_donations_rank() -> None:
    s = SocialRotatorStatsSession()
    s.on_follow("kittencat_42")
    s.on_donation(name="A", amount=100, source="donatik")
    s.on_donation(name="B", amount=50, source="donatello")
    s.on_donation(name="C", amount=200, source="tiktok_gift", coin_rate=1.0)
    d = s.to_public_dict()
    assert d["latest_follower"]["name"] == "kittencat_42"
    assert d["latest_donation"]["name"] == "C"
    assert d["latest_donation"]["value"] == 200
    assert d["top_donator"]["name"] == "C"
    assert d["top_donator"]["value"] == 200


def test_tiktok_rate_and_top_keeps_max() -> None:
    s = SocialRotatorStatsSession()
    s.on_donation(name="A", amount=1000, source="tiktok_gift", coin_rate=0.5)
    s.on_donation(name="B", amount=400, source="donatik")
    d = s.to_public_dict()
    assert d["latest_donation"]["name"] == "B"
    assert d["top_donator"]["name"] == "A"
    assert d["top_donator"]["value"] == 500


def test_viewers_sum() -> None:
    s = SocialRotatorStatsSession()
    s.set_viewers("tiktok", 100)
    s.set_viewers("twitch", 40)
    s.set_viewers("kick", 12)
    s.set_viewers("youtube", 0)
    d = s.to_public_dict()
    assert d["viewers_total"] == 152
    s.clear_viewers("twitch")
    assert s.to_public_dict()["viewers_total"] == 112


def test_stream_timer() -> None:
    s = SocialRotatorStatsSession()
    assert s.to_public_dict()["stream_started_at_ms"] is None
    s.set_stream_started_at_ms(123)
    assert s.to_public_dict()["stream_started_at_ms"] == 123
    s.reset()
    assert s.to_public_dict()["latest_follower"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_social_rotator_stats.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement stats session**

Keep last-follow name; last donation `{name,value,source}`; top `{name,value}` by max value; `viewers_by_platform` dict with non-negative ints; `viewers_total` = sum. Round displayed values with `int(round(value))` in public dict.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_social_rotator_stats.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/stream_cheremsha/overlays/social_rotator_stats.py tests/test_social_rotator_stats.py
git commit -m "feat(social-rotator): add session stats aggregator"
```

---

### Task 5: Controller

**Files:**
- Create: `src/stream_cheremsha/overlays/social_rotator_controller.py`
- Test: `tests/test_social_rotator_controller.py`

**Interfaces:**
- Consumes: config, rotation, stats, `OverlayPubSub`
- Produces `SocialRotatorController(QObject)` with:
  - `__init__(*, pubsub, get_locale, instance="main", parent=None)`
  - `set_pubsub`, `set_event_loop`, `start`, `stop`, `reload_config`, `reset_for_new_stream`, `initial_state`
  - `on_follow(user: str, ...)`, `on_tiktok_gift(...)`, `on_donation(name, amount, source)`
  - `on_viewers(platform: str, count: int)`, `on_stream_live(started: bool)`
  - Topic: `overlay:social_rotator:{instance}`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

from stream_cheremsha.overlays.social_rotator_controller import SocialRotatorController


def test_events_do_not_advance_rotation() -> None:
    ctl = SocialRotatorController(pubsub=None, get_locale=lambda: "en", instance="test")
    # Seed two platforms with usernames via internal reload after mutating config is heavy;
    # instead set rotation entries directly for isolation:
    from stream_cheremsha.overlays.social_rotator_rotation import (
        SocialRotationEntry,
        SocialRotatorRotationEngine,
    )

    ctl._rotation = SocialRotatorRotationEngine.from_entries(
        [
            SocialRotationEntry("1", "twitch", "a", "https://twitch.tv/a"),
            SocialRotationEntry("2", "youtube", "b", "https://youtube.com/@b"),
        ],
        interval_ms=60_000,
        now_ms=1000,
    )
    before = ctl.initial_state()["rotation"]["transition_token"]
    ctl.on_follow("X")
    ctl.on_tiktok_gift(sender="Y", count=1, tiktok_coin_each=10)
    ctl.on_donation(name="Z", amount=5, source="donatik")
    ctl.on_viewers("tiktok", 9)
    after = ctl.initial_state()["rotation"]["transition_token"]
    assert after == before
    assert ctl.initial_state()["stats"]["latest_follower"]["name"] == "X"
    assert ctl.initial_state()["stats"]["viewers_total"] == 9


def test_rotation_tick_advances() -> None:
    ctl = SocialRotatorController(pubsub=None, get_locale=lambda: "en", instance="test")
    from stream_cheremsha.overlays.social_rotator_rotation import (
        SocialRotationEntry,
        SocialRotatorRotationEngine,
    )

    ctl._rotation = SocialRotatorRotationEngine.from_entries(
        [
            SocialRotationEntry("1", "twitch", "a", "u1"),
            SocialRotationEntry("2", "youtube", "b", "u2"),
        ],
        interval_ms=1000,
        now_ms=0,
    )
    before = ctl._rotation.transition_token
    assert ctl._rotation.tick(now_ms=2000) is True
    assert ctl._rotation.transition_token == before + 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_social_rotator_controller.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement controller**

Copy structure from `live_leaderboard_controller.py`:

- `_ROTATION_TICK_MS = 250`, publish debounce 200ms
- `start()` starts rotation timer; `stop()` cancels
- `_reload_config(reset_rotation: bool)` loads config, `replace_entries(..., preserve_position=not reset_rotation)`
- `_build_state()` returns `{config, rotation, platforms_enabled, stats, locale}`
- Gift path: `coins = count * tiktok_coin_each`; call stats with `source="tiktok_gift"` and config rate
- `on_stream_live(True)` sets `stream_started_at_ms=now`; `False` clears it and optionally keeps other stats (match Stream Goal “new stream” reset via `reset_for_new_stream` clearing stats)

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_social_rotator_controller.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/stream_cheremsha/overlays/social_rotator_controller.py tests/test_social_rotator_controller.py
git commit -m "feat(social-rotator): add controller with timeline publish"
```

---

### Task 6: Overlay HTML HUD + registry

**Files:**
- Create: `src/stream_cheremsha/overlays/social_rotator_overlay.py`
- Modify: `src/stream_cheremsha/overlays/registry.py`
- Modify: `tests/test_overlays_registry.py`
- Test: `tests/test_social_rotator_overlay.py`

**Interfaces:**
- Produces `SocialRotatorOverlayType` with `type = "social_rotator"`, `render_html`, `initial_state`
- Visual DOM contracts (asserted in tests):
  - Classes: `root`, `hud-frame`, `panel-top`, `hero`, `hero-icon`, `orbit-ring`, `hero-text`, `kicker`, `platform-name`, `username`, `url`, `next-box`, `secondary`, `sec-card`, `pager-dots`, `panel-stats`, `stat-cell`, `scanlines`, `particles`
  - Fonts: Press Start 2P + VT323 links
  - CSS vars: `--sr-accent`, `--sr-widget-scale`, `--sr-platform`, `--sr-read`
  - JS: `applyState`, `applyScale`, `updateReadableScale`, `playTransition`, transition presets including `glitch_morph`
  - WS subscribe `type: "social_rotator"`

- [ ] **Step 1: Write the failing tests**

```python
from __future__ import annotations

from stream_cheremsha.overlays.registry import OverlayRegistry
from stream_cheremsha.overlays.social_rotator_overlay import SocialRotatorOverlayType


def test_overlay_renderer_and_registry() -> None:
    overlay = SocialRotatorOverlayType()
    html = overlay.render_html({"instance": "main"})
    assert "<!doctype html>" in html.lower()
    assert "Social Rotator" in html or "LIVE SOCIAL" in html
    assert "hud-frame" in html
    assert "hero-icon" in html
    assert "next-box" in html
    assert "secondary" in html
    assert "panel-stats" in html
    assert "orbit-ring" in html
    assert "glitch_morph" in html
    assert "playTransition" in html
    assert "transition_token" in html
    assert "--sr-widget-scale" in html
    assert "Press+Start+2P" in html
    assert "VT323" in html
    assert "transform: scale(var(--sr-widget-scale))" not in html
    st = overlay.initial_state({"instance": "main"})
    assert "config" in st
    assert "rotation" in st
    assert "stats" in st
    reg = OverlayRegistry()
    assert reg.get("social_rotator").type == "social_rotator"


def test_registry_has_social_rotator_overlay() -> None:
    reg = OverlayRegistry()
    t = reg.get("social_rotator")
    assert t.type == "social_rotator"
    html = t.render_html({"instance": "main"})
    assert "/ws" in html
```

Add the second test into `tests/test_overlays_registry.py` as well (or only keep it there — prefer both files stay green).

- [ ] **Step 2: Run tests to verify fail**

Run: `pytest tests/test_social_rotator_overlay.py tests/test_overlays_registry.py::test_registry_has_social_rotator_overlay -v`  
Expected: FAIL

- [ ] **Step 3: Implement overlay + register**

Build HTML by adapting `live_leaderboard_overlay.py` patterns:

**Layout structure:**

```html
<div class="root theme-neon_cyber" id="root">
  <div class="scanlines"></div>
  <div class="particles" id="particles"></div>
  <div class="hud-frame">
    <div class="panel-top">
      <div class="hero">
        <div class="hero-icon-wrap">
          <div class="orbit-ring"></div>
          <div class="hero-icon" id="heroIcon"></div>
        </div>
        <div class="hero-text">
          <div class="kicker">LIVE SOCIAL</div>
          <div class="platform-name" id="platformName"></div>
          <div class="username" id="username"></div>
          <div class="url" id="url"></div>
        </div>
      </div>
      <div class="next-box" id="nextBox">
        <div class="next-label">NEXT</div>
        <div class="next-num" id="nextNum">00</div>
        <div class="next-sec">SEC</div>
      </div>
      <div class="secondary" id="secondary"></div>
      <div class="pager-dots" id="pager"></div>
    </div>
    <div class="panel-stats" id="stats">
      <!-- five stat-cell nodes -->
    </div>
  </div>
</div>
```

**Visual requirements (must match reference):**
- Wide short top bar; hero icon large with purple/platform glow + glitch slices + cyan orbital base
- Username largest / most readable
- NEXT compact center
- Secondary cards with brand-colored icon frames + name + handle
- Bottom neon gradient border cyan→magenta→green
- Stats row: Latest Follower / Latest Donation / Stream Time / Top Donator / Online with ◆ for amounts
- Idle animations restrained; particle cap ≤ 12
- Responsive: hide `.url` first; secondary scroll; never overflow username
- SVG or CSS platform glyphs kept recognizable (simple official-shape marks OK; do not heavily distort logos)

Register in `OverlayRegistry.__init__`.

`initial_state`: if controller not available at render time, build from config + empty stats + rotation from enabled entries (same pattern as other overlays that load config in `render_html` / `initial_state`).

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_social_rotator_overlay.py tests/test_overlays_registry.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/stream_cheremsha/overlays/social_rotator_overlay.py src/stream_cheremsha/overlays/registry.py tests/test_social_rotator_overlay.py tests/test_overlays_registry.py
git commit -m "feat(social-rotator): add HUD overlay renderer and registry entry"
```

---

### Task 7: Widgets QML API

**Files:**
- Modify: `src/stream_cheremsha/ui/widgets_qml_api.py`
- Test: `tests/test_widgets_qml_api_social_rotator.py`

**Interfaces:**
- Produces (PySide Slot/Property naming like siblings):
  - `socialRotatorOverlayUrl() -> str` → `{base}/overlay/social_rotator?instance=main`
  - Properties: `socialRotatorOverlayUrlValue`
  - `copySocialRotatorOverlayUrl()`, `previewSocialRotatorOverlay()`
  - `loadSocialRotatorOverlayConfigMap() -> dict`
  - `loadSocialRotatorOverlayConfigJson() -> str`
  - `saveSocialRotatorOverlayConfigJson(text: str) -> bool`
  - `saveSocialRotatorOverlayConfigMap(cfg_map) -> bool`
  - `set_social_rotator_controller(controller)`
  - On save: `controller.reload_config()` + pubsub config patch

- [ ] **Step 1: Write failing test**

```python
from __future__ import annotations

from stream_cheremsha.ui.widgets_qml_api import WidgetsQmlApi


def test_widgets_api_social_rotator_url_and_config() -> None:
    api = WidgetsQmlApi(overlay_base_url="http://127.0.0.1:17171", pubsub=None)
    assert (
        api.socialRotatorOverlayUrl()
        == "http://127.0.0.1:17171/overlay/social_rotator?instance=main"
    )
    cfg = api.loadSocialRotatorOverlayConfigMap()
    assert cfg["enabled"] is True
    assert isinstance(cfg["platforms"], list)
    assert cfg["transition"] == "glitch_morph"
```

- [ ] **Step 2: Run test — expect FAIL**

Run: `pytest tests/test_widgets_qml_api_social_rotator.py -v`

- [ ] **Step 3: Implement API methods**

Mirror `liveLeaderboard*` / `streamGoal*` blocks in `widgets_qml_api.py` (imports, instance field, controller setter, Property, load/save JSON + Map via `_qml_cfg_map_to_json_text`).

- [ ] **Step 4: Run test — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/stream_cheremsha/ui/widgets_qml_api.py tests/test_widgets_qml_api_social_rotator.py
git commit -m "feat(social-rotator): expose widgets QML config and URL API"
```

---

### Task 8: QML settings UI

**Files:**
- Modify: `src/stream_cheremsha/qml/WidgetsView.qml`

**Interfaces:**
- Consumes: `api.loadSocialRotatorOverlayConfigMap`, `api.saveSocialRotatorOverlayConfigMap`, URL helpers
- Produces: grid card + settings pane `widgetMode === "social_rotator"`

- [ ] **Step 1: Extend state + load/save helpers**

Add beside live leaderboard:

```qml
property var socialRotatorCfg: null
property bool _loadingSocialRotatorCfg: false
property string widgetMode // include social_rotator in comment union
```

Implement `_loadSocialRotator`, `_saveSocialRotator` mirroring `_loadLiveLeaderboard` / `_saveLiveLeaderboard` (guard with `_loadingSocialRotatorCfg`).

Platform list helpers (no drag-drop):

```qml
function _srMovePlatform(index, delta) { /* swap order, renumber, save */ }
function _srRemovePlatform(index) { /* splice, save */ }
function _srAddPlatform(platformId) { /* push enabled entry with new id, save */ }
```

- [ ] **Step 2: Grid WidgetCard**

After Live Leaderboard card:

```qml
WidgetCard {
    title: "Social Rotator (Universal)"
    urlText: api ? api.socialRotatorOverlayUrlValue : ""
    onCopy: function() { if (api) api.copySocialRotatorOverlayUrl(); }
    onPlay: function() { if (api) api.previewSocialRotatorOverlay(); }
    onEdit: function() { root.widgetMode = "social_rotator"; }
}
```

Wire `widgetMode` visibility / syncGroup `"social_rotator"` the same way as `live_leaderboard` in existing `visible` / preview WebEngine branches.

- [ ] **Step 3: Settings pane**

Include:

- Enabled checkbox
- Platforms section: numbered rows with username field, enable checkbox, ↑ ↓ Edit(platform combo) Remove
- `+ ADD PLATFORM` (ComboBox of known platforms)
- Rotation interval (seconds spin → ms)
- Transition ComboBox: Glitch Morph / Data Stream / Energy Burst / Scan / Pixel Dissolve / Fade
- Theme ComboBox: Neon Cyber / Synthwave / Toxic / Ice / Amber
- Toggles: URL, secondary, countdown, glow, particles, CRT
- Stat toggles: five bottom cells
- Coin→value rate double spin
- Scale percent + accent color (reuse existing color/scale controls pattern)

- [ ] **Step 4: Manual smoke**

Run app (`cheremsha`), open Widgets → Social Rotator → set usernames → preview URL loads HUD.

- [ ] **Step 5: Commit**

```bash
git add src/stream_cheremsha/qml/WidgetsView.qml
git commit -m "feat(social-rotator): add QML settings and widget card"
```

---

### Task 9: Main window + donation wiring

**Files:**
- Modify: `src/stream_cheremsha/ui/main_window.py`
- Modify: `src/stream_cheremsha/ui/donations_qml_api.py`
- Test: extend `tests/test_social_rotator_controller.py` or add `tests/test_social_rotator_wiring_smoke.py` if needed for donation notify helper

**Interfaces:**
- `DonationsQmlApi`: on newly detected Donatik/Donatello rows (not only TTS), call optional callback:
  - `set_donation_listener(cb: Callable[[str, float, str], None] | None)`
  - Invoke `cb(name, amount, "donatik"|"donatello")` for each new id
- `MainWindow`: construct `SocialRotatorController`, `start()`, `set_social_rotator_controller`, wire:
  - TikTok follow → `on_follow`
  - TikTok gift → `on_tiktok_gift`
  - Donation listener → `on_donation`
  - Viewer updates → `on_viewers("tiktok"|"twitch"|"kick"|"youtube", n)`
  - TikTok live connect/disconnect → `on_stream_live(True/False)`
  - New stream reset → `reset_for_new_stream`

- [ ] **Step 1: Add donation listener hook**

In `_async_donatik_poll` / `_async_donatello_poll`, when `new_ids` detected (including when TTS is off), parse amount as float and notify listener. Do not break existing TTS flow.

- [ ] **Step 2: Wire MainWindow**

Mirror Live Leaderboard construction (~line 844) and follow/gift call sites. For viewers: wherever analytics enqueue viewers, also call social rotator (or poll from analytics getters on a light timer if that’s cleaner — prefer direct calls next to existing `enqueue_viewers` / room viewer callbacks).

- [ ] **Step 3: Test donation listener unit**

```python
def test_donation_listener_receives_new_rows(monkeypatch) -> None:
    # Construct DonationsQmlApi with a fake win if required pattern exists;
    # otherwise test a pure helper that extracts (name, amount, source) from a row.
    ...
```

If `DonationsQmlApi` is hard to unit-test without Qt window, extract:

```python
def donation_row_amount_name_donatik(row: dict) -> tuple[str, float]:
def donation_row_amount_name_donatello(row: dict) -> tuple[str, float]:
```

and test those + call them from the poll methods.

- [ ] **Step 4: Run focused tests**

Run: `pytest tests/test_social_rotator_controller.py tests/test_social_rotator_overlay.py tests/test_overlays_registry.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/stream_cheremsha/ui/main_window.py src/stream_cheremsha/ui/donations_qml_api.py tests/
git commit -m "feat(social-rotator): wire live events and donation listeners"
```

---

### Task 10: Visual polish pass + CHANGELOG

**Files:**
- Modify: `src/stream_cheremsha/overlays/social_rotator_overlay.py` (CSS/JS polish)
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Compare overlay preview to reference image**

Checklist (fix until yes):

- [ ] Hero username dominant and readable in Press Start 2P
- [ ] Icon holographic (orbit, glow, restrained glitch) without destroying logo
- [ ] NEXT secondary but correct
- [ ] Secondary cards integrated with brand frames
- [ ] HUD frame + bottom gradient present
- [ ] Stats strip matches five cells; ◆ amounts
- [ ] Glitch Morph transition 500–1000ms, cleans up
- [ ] Narrow width: no overflow/overlap
- [ ] Looks coherent next to Stream Goal / Live Leaderboard

- [ ] **Step 2: Update CHANGELOG under Unreleased**

```markdown
### Added
- Universal Social Rotator overlay (`social_rotator`): rotating social HUD + live stats strip.
```

- [ ] **Step 3: Run full related suite**

Run:

```bash
pytest tests/test_social_rotator_platforms.py tests/test_social_rotator_rotation.py tests/test_social_rotator_overlay_config.py tests/test_social_rotator_stats.py tests/test_social_rotator_controller.py tests/test_social_rotator_overlay.py tests/test_widgets_qml_api_social_rotator.py tests/test_overlays_registry.py -v
```

Expected: all PASS

- [ ] **Step 4: Commit**

```bash
git add src/stream_cheremsha/overlays/social_rotator_overlay.py CHANGELOG.md
git commit -m "feat(social-rotator): polish HUD visuals and document changelog"
```

---

## Plan self-review

**Spec coverage**

| Spec area | Task |
| --- | --- |
| PlatformDefinition / URLs | 1 |
| Rotation timeline / preserve | 2, 5 |
| Config / themes / transitions / toggles | 3, 8 |
| Stats sources + ◆ conversion | 4, 9 |
| HUD visual + transitions + idle/perf | 6, 10 |
| QML settings Add/Remove/Up/Down | 8 |
| Registry / OBS URL | 6, 7 |
| main_window wiring | 9 |
| Tests + acceptance | each task + 10 |

**Placeholder scan:** none intentional; overlay visual polish is explicit checklist against the reference, not “TBD”.

**Type consistency:** `SocialRotationEntry`, `SocialRotatorOverlayConfig`, `SocialRotatorStatsSession`, `SocialRotatorController`, public state keys `config` / `rotation` / `platforms_enabled` / `stats` used consistently across tasks.

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-04-social-rotator.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — execute tasks in this session with executing-plans checkpoints  

Which approach?
