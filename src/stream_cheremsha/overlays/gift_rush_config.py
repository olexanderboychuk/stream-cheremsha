"""Config schema for the ``gift_rush`` overlay.

The ``gift_rush`` overlay is a transparent, premium VFX reaction layer: a
gift flies in on a curved ``offset-path`` and bursts into coins, ribbons,
sparks, an impact ring and a ``+VALUE`` popup on each gift event. Rapid
consecutive gifts overlap and escalate into a ``COMBO`` counter.

This module holds the frozen, schema-versioned config, its clamped JSON
round-trip, and the QSettings load/save pair — the same shape used by the
``battle`` and ``stream_goal`` overlays.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, fields
from typing import Any

from PySide6.QtCore import QSettings

_LOG = logging.getLogger(__name__)

GIFT_OVERLAY_CONFIG_SCHEMA_VERSION = 1

# QSettings key + a backup key. The backup survives a corrupted primary key
# the way it does for every other overlay type.
_QSET_KEY = "overlays/gift_rush/config"
_QSET_KEY_BACKUP = "overlays/gift_rush/config_backup"

_THEME_ALLOWED = frozenset({"cheremsha", "celebration", "arcade"})
_TARGET_MODES = frozenset({"center", "left", "right", "random"})

_SCALE_MIN, _SCALE_MAX = 40, 250
_INTENSITY_MIN, _INTENSITY_MAX = 25, 200
_COMBO_WINDOW_MIN, _COMBO_WINDOW_MAX = 3, 30
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


def _ensure_theme(value: Any) -> str:
    if not isinstance(value, str):
        return "cheremsha"
    value = value.strip().lower()
    if value not in _THEME_ALLOWED:
        return "cheremsha"
    return value


def _ensure_target_mode(value: Any) -> str:
    if not isinstance(value, str):
        return "center"
    value = value.strip().lower()
    if value not in _TARGET_MODES:
        return "center"
    return value


@dataclass(frozen=True, slots=True)
class GiftRushOverlayConfig:
    """Immutable config for one instance of the gift rush overlay."""

    schema_version: int = GIFT_OVERLAY_CONFIG_SCHEMA_VERSION
    theme: str = "cheremsha"
    target_mode: str = "center"
    scale_percent: int = 100
    intensity_percent: int = 100
    event_animations: bool = True
    show_gift_image: bool = True
    show_value: bool = True
    show_sender: bool = True
    show_combo: bool = True
    show_intensity_badge: bool = True
    effects_coins: bool = True
    effects_ribbons: bool = True
    effects_sparks: bool = True
    effects_impact_ring: bool = True
    camera_impact: bool = True
    combo_enabled: bool = True
    combo_window_s: int = 10
    combo_escalation: bool = True
    max_simultaneous_events: int = 10
    reduced_effects: bool = False

    def _ensure(self) -> GiftRushOverlayConfig:
        """Return a cloned instance with every field clamped / normalized."""
        return GiftRushOverlayConfig(
            schema_version=int(getattr(self, "schema_version", 1) or 1),
            theme=_ensure_theme(self.theme),
            target_mode=_ensure_target_mode(self.target_mode),
            scale_percent=_clamp_int(self.scale_percent, _SCALE_MIN, _SCALE_MAX),
            intensity_percent=_clamp_int(self.intensity_percent, _INTENSITY_MIN, _INTENSITY_MAX),
            event_animations=_clamp_bool(self.event_animations),
            show_gift_image=_clamp_bool(self.show_gift_image),
            show_value=_clamp_bool(self.show_value),
            show_sender=_clamp_bool(self.show_sender),
            show_combo=_clamp_bool(self.show_combo),
            show_intensity_badge=_clamp_bool(self.show_intensity_badge),
            effects_coins=_clamp_bool(self.effects_coins),
            effects_ribbons=_clamp_bool(self.effects_ribbons),
            effects_sparks=_clamp_bool(self.effects_sparks),
            effects_impact_ring=_clamp_bool(self.effects_impact_ring),
            camera_impact=_clamp_bool(self.camera_impact),
            combo_enabled=_clamp_bool(self.combo_enabled),
            combo_window_s=_clamp_int(self.combo_window_s, _COMBO_WINDOW_MIN, _COMBO_WINDOW_MAX),
            combo_escalation=_clamp_bool(self.combo_escalation),
            max_simultaneous_events=_clamp_int(
                self.max_simultaneous_events, _MAX_SIMUL_MIN, _MAX_SIMUL_MAX
            ),
            reduced_effects=_clamp_bool(self.reduced_effects),
        )

    def clamp(self) -> GiftRushOverlayConfig:
        return self._ensure()


def gift_rush_overlay_config_defaults() -> GiftRushOverlayConfig:
    """Fresh, fully-clamped defaults (schema v1)."""
    return GiftRushOverlayConfig().clamp()


def gift_rush_overlay_config_to_public_dict(
    cfg: GiftRushOverlayConfig | None,
) -> dict[str, Any]:
    """JSON-safe, sorted public representation (for QML + OBS preview)."""
    if cfg is None:
        return {}
    return asdict(cfg)


def gift_rush_overlay_config_to_json_text(
    cfg: GiftRushOverlayConfig | None,
) -> str:
    """Compact, sorted JSON text — stable for diffing / backup comparison."""
    if cfg is None:
        return "{}"
    return json.dumps(
        gift_rush_overlay_config_to_public_dict(cfg),
        sort_keys=True,
        separators=(",", ":"),
    )


def gift_rush_overlay_config_from_json_text(
    json_text: str | bytes | None,
    default_factory: callable | None = None,
) -> GiftRushOverlayConfig:
    """Parse raw JSON into a clamped config. Invalid input -> defaults."""
    if not json_text:
        return (default_factory or gift_rush_overlay_config_defaults)()

    try:
        data = json.loads(json_text if isinstance(json_text, bytes) else json_text)
        if not isinstance(data, dict):
            raise ValueError("config JSON must be an object")
        # Only override fields the JSON actually provides; missing keys take
        # the dataclass defaults and are clamped on the way through.
        raw: dict[str, Any] = {}
        for field in fields(GiftRushOverlayConfig):
            if field.name in data:
                raw[field.name] = data[field.name]
        return GiftRushOverlayConfig(**raw).clamp()
    except (json.JSONDecodeError, TypeError, ValueError):
        return (default_factory or gift_rush_overlay_config_defaults)()


def _settings_obj(settings: QSettings | None) -> QSettings:
    return settings or QSettings("stream-cheremsha", "cheremsha")


def load_gift_rush_overlay_config(
    settings: QSettings | None = None,
    backup: bool = True,
) -> GiftRushOverlayConfig:
    """Load the config; fall back to the backup key, then to defaults."""
    s = _settings_obj(settings)
    try:
        raw = str(s.value(_QSET_KEY, "", str) or "").strip()
        if raw:
            return gift_rush_overlay_config_from_json_text(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        if backup:
            try:
                raw = str(s.value(_QSET_KEY_BACKUP, "", str) or "").strip()
                if raw:
                    return gift_rush_overlay_config_from_json_text(raw)
            except (TypeError, ValueError, json.JSONDecodeError):
                _LOG.warning("gift_rush backup key unreadable; using defaults")
    return gift_rush_overlay_config_defaults()


def save_gift_rush_overlay_config(
    cfg: GiftRushOverlayConfig | None,
    settings: QSettings | None = None,
) -> None:
    """Write the config (primary + backup key)."""
    s = _settings_obj(settings)
    cfg = (cfg or gift_rush_overlay_config_defaults()).clamp()
    text = gift_rush_overlay_config_to_json_text(cfg)
    s.setValue(_QSET_KEY, text)
    s.setValue(_QSET_KEY_BACKUP, text)
    s.sync()
