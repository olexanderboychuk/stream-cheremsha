"""Config schema for the ``balloon_hunter`` overlay.

Transparent Canvas layer: balloons float upward continuously (client-side
ambient animation with object pools). Gift events pop a matching balloon
(NORMAL / GOLD / EPIC by coin value + combo) with flash, confetti particles
and a gift-icon popup.

Same shape as ``gift_rush`` / ``battle`` configs: frozen dataclass, clamped
JSON round-trip, QSettings load/save pair with backup key.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, fields
from typing import Any

from PySide6.QtCore import QSettings

_LOG = logging.getLogger(__name__)

BALLOON_HUNTER_CONFIG_SCHEMA_VERSION = 1

_QSET_KEY = "overlays/balloon_hunter/config"
_QSET_KEY_BACKUP = "overlays/balloon_hunter/config_backup"

_COUNT_MIN, _COUNT_MAX = 3, 20
_SPAWN_MS_MIN, _SPAWN_MS_MAX = 500, 5000
_SPEED_MIN, _SPEED_MAX = 40, 250
_COINS_MIN, _COINS_MAX = 1, 100000
_COMBO_WINDOW_MIN, _COMBO_WINDOW_MAX = 3, 30
_EFFECT_MS_MIN, _EFFECT_MS_MAX = 300, 2000
_PARTICLES_MIN, _PARTICLES_MAX = 50, 500
_MAX_SIMUL_MIN, _MAX_SIMUL_MAX = 4, 12


def _clamp_int(value: Any, minimum: int, maximum: int) -> int:
    try:
        ivalue = int(value)
    except (TypeError, ValueError):
        ivalue = 0
    if ivalue < minimum:
        return minimum
    if ivalue > maximum:
        return maximum
    return ivalue


def _clamp_bool(value: Any) -> bool:
    return bool(value)


@dataclass(frozen=True, slots=True)
class BalloonHunterOverlayConfig:
    """Immutable config for one instance of the balloon hunter overlay."""

    schema_version: int = BALLOON_HUNTER_CONFIG_SCHEMA_VERSION
    balloon_count: int = 8
    spawn_interval_ms: int = 1500
    float_speed_percent: int = 100
    gold_min_coins: int = 50
    epic_min_coins: int = 200
    combo_enabled: bool = True
    combo_window_s: int = 10
    show_sender: bool = True
    show_gift_icon: bool = True
    sound_enabled: bool = False
    event_animations: bool = True
    effect_duration_ms: int = 800
    max_particles: int = 200
    max_simultaneous_events: int = 10
    reduced_effects: bool = False

    def _ensure(self) -> BalloonHunterOverlayConfig:
        gold = _clamp_int(self.gold_min_coins, _COINS_MIN, _COINS_MAX)
        epic = _clamp_int(self.epic_min_coins, _COINS_MIN, _COINS_MAX)
        if epic <= gold:
            epic = min(_COINS_MAX, gold + 1)
        return BalloonHunterOverlayConfig(
            schema_version=int(getattr(self, "schema_version", 1) or 1),
            balloon_count=_clamp_int(self.balloon_count, _COUNT_MIN, _COUNT_MAX),
            spawn_interval_ms=_clamp_int(self.spawn_interval_ms, _SPAWN_MS_MIN, _SPAWN_MS_MAX),
            float_speed_percent=_clamp_int(self.float_speed_percent, _SPEED_MIN, _SPEED_MAX),
            gold_min_coins=gold,
            epic_min_coins=epic,
            combo_enabled=_clamp_bool(self.combo_enabled),
            combo_window_s=_clamp_int(self.combo_window_s, _COMBO_WINDOW_MIN, _COMBO_WINDOW_MAX),
            show_sender=_clamp_bool(self.show_sender),
            show_gift_icon=_clamp_bool(self.show_gift_icon),
            sound_enabled=_clamp_bool(self.sound_enabled),
            event_animations=_clamp_bool(self.event_animations),
            effect_duration_ms=_clamp_int(self.effect_duration_ms, _EFFECT_MS_MIN, _EFFECT_MS_MAX),
            max_particles=_clamp_int(self.max_particles, _PARTICLES_MIN, _PARTICLES_MAX),
            max_simultaneous_events=_clamp_int(
                self.max_simultaneous_events, _MAX_SIMUL_MIN, _MAX_SIMUL_MAX
            ),
            reduced_effects=_clamp_bool(self.reduced_effects),
        )

    def clamp(self) -> BalloonHunterOverlayConfig:
        return self._ensure()


def balloon_hunter_overlay_config_defaults() -> BalloonHunterOverlayConfig:
    """Fresh, fully-clamped defaults (schema v1)."""
    return BalloonHunterOverlayConfig().clamp()


def balloon_hunter_overlay_config_to_public_dict(
    cfg: BalloonHunterOverlayConfig | None,
) -> dict[str, Any]:
    """JSON-safe, sorted public representation (for QML + OBS preview)."""
    if cfg is None:
        return {}
    return asdict(cfg)


def balloon_hunter_overlay_config_to_json_text(
    cfg: BalloonHunterOverlayConfig | None,
) -> str:
    """Compact, sorted JSON text — stable for diffing / backup comparison."""
    if cfg is None:
        return "{}"
    return json.dumps(
        balloon_hunter_overlay_config_to_public_dict(cfg),
        sort_keys=True,
        separators=(",", ":"),
    )


def balloon_hunter_overlay_config_from_json_text(
    json_text: str | bytes | None,
    default_factory: callable | None = None,
) -> BalloonHunterOverlayConfig:
    """Parse raw JSON into a clamped config. Invalid input -> defaults."""
    if not json_text:
        return (default_factory or balloon_hunter_overlay_config_defaults)()

    try:
        data = json.loads(json_text if isinstance(json_text, bytes) else json_text)
        if not isinstance(data, dict):
            raise ValueError("config JSON must be an object")
        raw: dict[str, Any] = {}
        for field in fields(BalloonHunterOverlayConfig):
            if field.name in data:
                raw[field.name] = data[field.name]
        return BalloonHunterOverlayConfig(**raw).clamp()
    except (json.JSONDecodeError, TypeError, ValueError):
        return (default_factory or balloon_hunter_overlay_config_defaults)()


def _settings_obj(settings: QSettings | None) -> QSettings:
    return settings or QSettings("stream-cheremsha", "cheremsha")


def load_balloon_hunter_overlay_config(
    settings: QSettings | None = None,
    backup: bool = True,
) -> BalloonHunterOverlayConfig:
    """Load the config; fall back to the backup key, then to defaults."""
    s = _settings_obj(settings)
    try:
        raw = str(s.value(_QSET_KEY, "", str) or "").strip()
        if raw:
            return balloon_hunter_overlay_config_from_json_text(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        if backup:
            try:
                raw = str(s.value(_QSET_KEY_BACKUP, "", str) or "").strip()
                if raw:
                    return balloon_hunter_overlay_config_from_json_text(raw)
            except (TypeError, ValueError, json.JSONDecodeError):
                _LOG.warning("balloon_hunter backup key unreadable; using defaults")
    return balloon_hunter_overlay_config_defaults()


def save_balloon_hunter_overlay_config(
    cfg: BalloonHunterOverlayConfig | None,
    settings: QSettings | None = None,
) -> None:
    """Write the config (primary + backup key)."""
    s = _settings_obj(settings)
    cfg = (cfg or balloon_hunter_overlay_config_defaults()).clamp()
    text = balloon_hunter_overlay_config_to_json_text(cfg)
    s.setValue(_QSET_KEY, text)
    s.setValue(_QSET_KEY_BACKUP, text)
    s.sync()
