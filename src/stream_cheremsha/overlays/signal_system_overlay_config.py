from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Any

from PySide6.QtCore import QSettings

SIGNAL_SYSTEM_OVERLAY_CONFIG_SCHEMA_VERSION = 1
SIGNAL_SYSTEM_OVERLAY_CONFIG_QSETTINGS_KEY = "overlays/signal_system/main/config_json"
_SIGNAL_SYSTEM_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY = (
    "overlays/signal_system/main/config_json_backup"
)

SIGNAL_SYSTEM_THEMES = frozenset(
    ("neon_cyber", "toxic_system", "ice_protocol", "amber_core", "critical"),
)


@dataclass(frozen=True, slots=True)
class SignalSystemOverlayConfig:
    schema_version: int

    enabled: bool
    theme: str
    idle_opacity_pct: int
    active_opacity_pct: int
    particles_enabled: bool
    glitch_enabled: bool
    perimeter_enabled: bool
    sound_enabled: bool
    cooldown_ms: int
    min_gift_coins_for_event: int
    ai_observations_enabled: bool
    unknown_signals_enabled: bool
    milestones_enabled: bool
    activity_surge_enabled: bool
    font_family: str
    custom_title: str
    scale_percent: int
    core_vertical_pct: int
    # Premium redesign additions (all optional with safe defaults)
    intensity_multiplier: float
    primary_accent: str
    secondary_accent: str
    frame_detail_level: str
    particle_density: str
    gift_icon_enabled: bool
    show_gift_quantity: bool
    show_coin_value: bool
    show_gift_name: bool
    reduced_motion: bool
    global_cooldown_ms: int
    ai_observation_cooldown_ms: int
    ai_observation_max_per_hour: int
    unknown_signal_cooldown_ms: int

    def replace(self, **kwargs: object) -> SignalSystemOverlayConfig:
        return replace(self, **kwargs)


def signal_system_overlay_config_defaults() -> SignalSystemOverlayConfig:
    return SignalSystemOverlayConfig(
        schema_version=SIGNAL_SYSTEM_OVERLAY_CONFIG_SCHEMA_VERSION,
        enabled=True,
        theme="neon_cyber",
        idle_opacity_pct=35,
        active_opacity_pct=100,
        particles_enabled=True,
        glitch_enabled=True,
        perimeter_enabled=True,
        sound_enabled=False,
        cooldown_ms=3000,
        min_gift_coins_for_event=100,
        ai_observations_enabled=True,
        unknown_signals_enabled=True,
        milestones_enabled=True,
        activity_surge_enabled=True,
        font_family="Share Tech Mono",
        custom_title="SIGNAL // SYSTEM",
        scale_percent=100,
        core_vertical_pct=50,
        intensity_multiplier=1.0,
        primary_accent="",
        secondary_accent="",
        frame_detail_level="full",
        particle_density="standard",
        gift_icon_enabled=True,
        show_gift_quantity=True,
        show_coin_value=True,
        show_gift_name=True,
        reduced_motion=False,
        global_cooldown_ms=8000,
        ai_observation_cooldown_ms=300000,
        ai_observation_max_per_hour=3,
        unknown_signal_cooldown_ms=900000,
    )


def _ensure_int(v: object, *, default: int) -> int:
    try:
        return int(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _ensure_theme(v: object) -> str:
    s = str(v or "").strip().lower()
    if s in SIGNAL_SYSTEM_THEMES:
        return s
    return "neon_cyber"


def _ensure_bool(v: object, *, default: bool) -> bool:
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    s = str(v).strip().lower()
    if s in ("0", "false", "no", "off", ""):
        return False
    if s in ("1", "true", "yes", "on"):
        return True
    return default


def _validate_scale_percent(v: object) -> int:
    n = _ensure_int(v, default=100)
    return max(40, min(250, n))


def _validate_core_vertical_pct(v: object) -> int:
    n = _ensure_int(v, default=50)
    return max(20, min(80, n))


def _ensure_float(v: object, *, default: float, lo: float, hi: float) -> float:
    try:
        f = float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    if f != f:  # NaN
        return default
    return max(lo, min(hi, f))


def _ensure_hex_color(v: object) -> str:
    s = str(v or "").strip()
    if not s:
        return ""
    if not s.startswith("#"):
        return ""
    h = s[1:]
    if len(h) not in (3, 6):
        return ""
    if any(c not in "0123456789abcdefABCDEF" for c in h):
        return ""
    return s.lower()


def _ensure_choice(v: object, *, options: frozenset[str], default: str) -> str:
    s = str(v or "").strip().lower()
    if s in options:
        return s
    return default


_FRAME_DETAIL_LEVELS = frozenset(("minimal", "standard", "full"))
_PARTICLE_DENSITIES = frozenset(("none", "low", "standard", "high"))


def signal_system_overlay_config_to_public_dict(cfg: SignalSystemOverlayConfig) -> dict[str, Any]:
    return {
        "schema_version": int(cfg.schema_version),
        "enabled": bool(getattr(cfg, "enabled", True)),
        "theme": str(cfg.theme),
        "idle_opacity_pct": int(cfg.idle_opacity_pct),
        "active_opacity_pct": int(cfg.active_opacity_pct),
        "particles_enabled": bool(cfg.particles_enabled),
        "glitch_enabled": bool(cfg.glitch_enabled),
        "perimeter_enabled": bool(cfg.perimeter_enabled),
        "sound_enabled": bool(cfg.sound_enabled),
        "cooldown_ms": int(cfg.cooldown_ms),
        "min_gift_coins_for_event": int(cfg.min_gift_coins_for_event),
        "ai_observations_enabled": bool(cfg.ai_observations_enabled),
        "unknown_signals_enabled": bool(cfg.unknown_signals_enabled),
        "milestones_enabled": bool(cfg.milestones_enabled),
        "activity_surge_enabled": bool(cfg.activity_surge_enabled),
        "font_family": str(cfg.font_family),
        "custom_title": str(cfg.custom_title),
        "scale_percent": int(cfg.scale_percent),
        "core_vertical_pct": int(getattr(cfg, "core_vertical_pct", 50)),
        "intensity_multiplier": float(getattr(cfg, "intensity_multiplier", 1.0)),
        "primary_accent": str(getattr(cfg, "primary_accent", "") or ""),
        "secondary_accent": str(getattr(cfg, "secondary_accent", "") or ""),
        "frame_detail_level": str(getattr(cfg, "frame_detail_level", "full") or "full"),
        "particle_density": str(getattr(cfg, "particle_density", "standard") or "standard"),
        "gift_icon_enabled": bool(getattr(cfg, "gift_icon_enabled", True)),
        "show_gift_quantity": bool(getattr(cfg, "show_gift_quantity", True)),
        "show_coin_value": bool(getattr(cfg, "show_coin_value", True)),
        "show_gift_name": bool(getattr(cfg, "show_gift_name", True)),
        "reduced_motion": bool(getattr(cfg, "reduced_motion", False)),
        "global_cooldown_ms": int(getattr(cfg, "global_cooldown_ms", 8000)),
        "ai_observation_cooldown_ms": int(getattr(cfg, "ai_observation_cooldown_ms", 300000)),
        "ai_observation_max_per_hour": int(getattr(cfg, "ai_observation_max_per_hour", 3)),
        "unknown_signal_cooldown_ms": int(getattr(cfg, "unknown_signal_cooldown_ms", 900000)),
    }


def signal_system_overlay_config_to_json_text(cfg: SignalSystemOverlayConfig) -> str:
    obj = signal_system_overlay_config_to_public_dict(cfg)
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def signal_system_overlay_config_from_json_text(text: str) -> SignalSystemOverlayConfig:
    raw = json.loads(text)
    if not isinstance(raw, dict):
        raise ValueError("signal_system overlay config must be a JSON object")
    d = raw
    return SignalSystemOverlayConfig(
        schema_version=_ensure_int(d.get("schema_version"), default=1),
        enabled=_ensure_bool(d.get("enabled"), default=True),
        theme=_ensure_theme(d.get("theme")),
        idle_opacity_pct=max(0, min(100, _ensure_int(d.get("idle_opacity_pct"), default=35))),
        active_opacity_pct=max(50, min(100, _ensure_int(d.get("active_opacity_pct"), default=100))),
        particles_enabled=_ensure_bool(d.get("particles_enabled"), default=True),
        glitch_enabled=_ensure_bool(d.get("glitch_enabled"), default=True),
        perimeter_enabled=_ensure_bool(d.get("perimeter_enabled"), default=True),
        sound_enabled=_ensure_bool(d.get("sound_enabled"), default=False),
        cooldown_ms=max(500, min(15000, _ensure_int(d.get("cooldown_ms"), default=3000))),
        min_gift_coins_for_event=max(
            1, min(10000, _ensure_int(d.get("min_gift_coins_for_event"), default=100))
        ),
        ai_observations_enabled=_ensure_bool(d.get("ai_observations_enabled"), default=True),
        unknown_signals_enabled=_ensure_bool(d.get("unknown_signals_enabled"), default=True),
        milestones_enabled=_ensure_bool(d.get("milestones_enabled"), default=True),
        activity_surge_enabled=_ensure_bool(d.get("activity_surge_enabled"), default=True),
        font_family=(
            str(d.get("font_family") or "Share Tech Mono").strip() or "Share Tech Mono"
        ),
        custom_title=(
            str(
                d.get("custom_title")
                or signal_system_overlay_config_defaults().custom_title
            ).strip()
            or signal_system_overlay_config_defaults().custom_title
        ),
        scale_percent=_validate_scale_percent(d.get("scale_percent")),
        core_vertical_pct=_validate_core_vertical_pct(d.get("core_vertical_pct", 50)),
        intensity_multiplier=_ensure_float(
            d.get("intensity_multiplier", 1.0), default=1.0, lo=0.5, hi=2.0
        ),
        primary_accent=_ensure_hex_color(d.get("primary_accent", "")),
        secondary_accent=_ensure_hex_color(d.get("secondary_accent", "")),
        frame_detail_level=_ensure_choice(
            d.get("frame_detail_level", "full"),
            options=_FRAME_DETAIL_LEVELS,
            default="full",
        ),
        particle_density=_ensure_choice(
            d.get("particle_density", "standard"),
            options=_PARTICLE_DENSITIES,
            default="standard",
        ),
        gift_icon_enabled=_ensure_bool(d.get("gift_icon_enabled", True), default=True),
        show_gift_quantity=_ensure_bool(d.get("show_gift_quantity", True), default=True),
        show_coin_value=_ensure_bool(d.get("show_coin_value", True), default=True),
        show_gift_name=_ensure_bool(d.get("show_gift_name", True), default=True),
        reduced_motion=_ensure_bool(d.get("reduced_motion", False), default=False),
        global_cooldown_ms=max(
            1000, min(30000, _ensure_int(d.get("global_cooldown_ms", 8000), default=8000))
        ),
        ai_observation_cooldown_ms=max(
            30000,
            min(
                3600000,
                _ensure_int(d.get("ai_observation_cooldown_ms", 300000), default=300000),
            ),
        ),
        ai_observation_max_per_hour=max(
            1,
            min(
                12,
                _ensure_int(d.get("ai_observation_max_per_hour", 3), default=3),
            ),
        ),
        unknown_signal_cooldown_ms=max(
            60000,
            min(
                3600000,
                _ensure_int(d.get("unknown_signal_cooldown_ms", 900000), default=900000),
            ),
        ),
    )


def load_signal_system_overlay_config(
    settings: QSettings | None = None,
) -> SignalSystemOverlayConfig:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    raw = (s.value(SIGNAL_SYSTEM_OVERLAY_CONFIG_QSETTINGS_KEY, "", str) or "").strip()
    if not raw:
        return signal_system_overlay_config_defaults()
    try:
        return signal_system_overlay_config_from_json_text(raw)
    except (ValueError, TypeError, json.JSONDecodeError):
        bak = (s.value(_SIGNAL_SYSTEM_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY, "", str) or "").strip()
        if bak:
            try:
                cfg = signal_system_overlay_config_from_json_text(bak)
            except (ValueError, TypeError, json.JSONDecodeError):
                return signal_system_overlay_config_defaults()
            s.setValue(
                SIGNAL_SYSTEM_OVERLAY_CONFIG_QSETTINGS_KEY,
                signal_system_overlay_config_to_json_text(cfg),
            )
            return cfg
        return signal_system_overlay_config_defaults()


def save_signal_system_overlay_config(
    cfg: SignalSystemOverlayConfig,
    settings: QSettings | None = None,
) -> None:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    txt = signal_system_overlay_config_to_json_text(cfg)
    s.setValue(SIGNAL_SYSTEM_OVERLAY_CONFIG_QSETTINGS_KEY, txt)
    s.setValue(_SIGNAL_SYSTEM_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY, txt)
    s.sync()
