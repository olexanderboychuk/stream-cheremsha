from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, replace
from typing import Any

from PySide6.QtCore import QSettings

from stream_cheremsha.overlays.social_platforms import ALL_PLATFORM_IDS, get_platform

SOCIAL_ROTATOR_OVERLAY_CONFIG_SCHEMA_VERSION = 1
SOCIAL_ROTATOR_OVERLAY_CONFIG_QSETTINGS_KEY = "overlays/social_rotator/main/config_json"
_SOCIAL_ROTATOR_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY = (
    "overlays/social_rotator/main/config_json_backup"
)

VALID_TRANSITIONS = frozenset(
    {
        "glitch_morph",
        "data_stream",
        "energy_burst",
        "scan",
        "pixel_dissolve",
        "fade",
    }
)
VALID_THEMES = frozenset({"neon_cyber", "synthwave", "toxic", "ice", "amber"})


def _default_platforms() -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for i, pid in enumerate(("twitch", "youtube", "kick", "telegram", "tiktok")):
        out.append(
            {
                "id": str(uuid.uuid4()),
                "platform": pid,
                "username": "",
                "url": "",
                "enabled": True,
                "order": i,
            }
        )
    return out


@dataclass(frozen=True, slots=True)
class SocialRotatorOverlayConfig:
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
    background_opacity_percent: int
    show_latest_follower: bool
    show_latest_donation: bool
    show_stream_time: bool
    show_top_donator: bool
    show_online: bool
    tiktok_coin_to_value_rate: float
    scale_percent: int
    accent_color: str

    def replace(self, **kwargs: object) -> SocialRotatorOverlayConfig:
        return replace(self, **kwargs)


def social_rotator_overlay_config_defaults() -> SocialRotatorOverlayConfig:
    return SocialRotatorOverlayConfig(
        schema_version=SOCIAL_ROTATOR_OVERLAY_CONFIG_SCHEMA_VERSION,
        enabled=True,
        platforms_json=json.dumps(_default_platforms(), ensure_ascii=False),
        rotation_interval_ms=8000,
        transition="glitch_morph",
        theme="neon_cyber",
        show_url=True,
        show_countdown=True,
        show_secondary_platforms=True,
        enable_glow=True,
        enable_particles=True,
        enable_crt=True,
        background_opacity_percent=85,
        show_latest_follower=True,
        show_latest_donation=True,
        show_stream_time=True,
        show_top_donator=True,
        show_online=True,
        tiktok_coin_to_value_rate=1.0,
        scale_percent=100,
        accent_color="#00ffff",
    )


def _ensure_int(v: object, *, default: int) -> int:
    try:
        return int(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _ensure_float(v: object, *, default: float) -> float:
    try:
        return float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _ensure_bool(v: object, *, default: bool) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("1", "true", "yes", "on"):
            return True
        if s in ("0", "false", "no", "off"):
            return False
    return default


def _ensure_str(v: object, *, default: str) -> str:
    s = str(v or "").strip()
    return s if s else default


def _ensure_hex_color(v: object, *, default: str) -> str:
    s = str(v or "").strip()
    if s.startswith("#") and len(s) in (4, 7, 9):
        return s
    return default


def _validate_transition(v: object) -> str:
    s = _ensure_str(v, default="glitch_morph")
    return s if s in VALID_TRANSITIONS else "glitch_morph"


def _validate_theme(v: object) -> str:
    s = _ensure_str(v, default="neon_cyber")
    return s if s in VALID_THEMES else "neon_cyber"


def _validate_scale_percent(v: object) -> int:
    return max(40, min(250, _ensure_int(v, default=100)))


def _validate_background_opacity_percent(v: object) -> int:
    return max(0, min(100, _ensure_int(v, default=85)))


def _validate_interval_ms(v: object) -> int:
    return max(1000, min(120_000, _ensure_int(v, default=8000)))


def _validate_coin_rate(v: object) -> float:
    return max(0.0, _ensure_float(v, default=1.0))


def _normalize_platform_row(raw: object, *, order_fallback: int) -> dict[str, object] | None:
    if not isinstance(raw, dict):
        return None
    platform = str(raw.get("platform") or "").strip().lower()
    if get_platform(platform) is None:
        return None
    entry_id = str(raw.get("id") or "").strip() or str(uuid.uuid4())
    try:
        order = int(raw.get("order", order_fallback))
    except (TypeError, ValueError):
        order = order_fallback
    return {
        "id": entry_id,
        "platform": platform,
        "username": str(raw.get("username") or "").strip(),
        "url": str(raw.get("url") or "").strip(),
        "enabled": _ensure_bool(raw.get("enabled"), default=True),
        "order": order,
    }


def _validate_platforms_payload(v: object) -> str:
    defaults = _default_platforms()
    if isinstance(v, str):
        try:
            parsed: Any = json.loads(v)
        except (json.JSONDecodeError, TypeError, ValueError):
            return json.dumps(defaults, ensure_ascii=False)
    else:
        parsed = v
    if not isinstance(parsed, list):
        return json.dumps(defaults, ensure_ascii=False)
    out: list[dict[str, object]] = []
    for i, row in enumerate(parsed):
        norm = _normalize_platform_row(row, order_fallback=i)
        if norm is not None:
            out.append(norm)
    if not out:
        return json.dumps(defaults, ensure_ascii=False)
    out.sort(key=lambda r: int(r.get("order", 0)))
    for i, row in enumerate(out):
        row["order"] = i
    return json.dumps(out, ensure_ascii=False)


def parse_platforms(cfg: SocialRotatorOverlayConfig) -> list[dict[str, object]]:
    try:
        raw = json.loads(cfg.platforms_json)
    except (json.JSONDecodeError, TypeError, ValueError):
        return _default_platforms()
    if not isinstance(raw, list):
        return _default_platforms()
    out: list[dict[str, object]] = []
    for i, row in enumerate(raw):
        norm = _normalize_platform_row(row, order_fallback=i)
        if norm is not None:
            out.append(norm)
    out.sort(key=lambda r: int(r.get("order", 0)))
    return out


def social_rotator_overlay_config_from_json_text(text: str) -> SocialRotatorOverlayConfig:
    raw = json.loads(text)
    if not isinstance(raw, dict):
        raise ValueError("social_rotator overlay config must be a JSON object")
    d = raw
    defaults = social_rotator_overlay_config_defaults()
    platforms_src = d.get("platforms", d.get("platforms_json", defaults.platforms_json))
    return SocialRotatorOverlayConfig(
        schema_version=_ensure_int(d.get("schema_version"), default=defaults.schema_version),
        enabled=_ensure_bool(d.get("enabled"), default=defaults.enabled),
        platforms_json=_validate_platforms_payload(platforms_src),
        rotation_interval_ms=_validate_interval_ms(
            d.get("rotation_interval_ms", defaults.rotation_interval_ms)
        ),
        transition=_validate_transition(d.get("transition")),
        theme=_validate_theme(d.get("theme")),
        show_url=_ensure_bool(d.get("show_url"), default=defaults.show_url),
        show_countdown=_ensure_bool(d.get("show_countdown"), default=defaults.show_countdown),
        show_secondary_platforms=_ensure_bool(
            d.get("show_secondary_platforms"), default=defaults.show_secondary_platforms
        ),
        enable_glow=_ensure_bool(d.get("enable_glow"), default=defaults.enable_glow),
        enable_particles=_ensure_bool(d.get("enable_particles"), default=defaults.enable_particles),
        enable_crt=_ensure_bool(d.get("enable_crt"), default=defaults.enable_crt),
        background_opacity_percent=_validate_background_opacity_percent(
            d.get("background_opacity_percent", defaults.background_opacity_percent)
        ),
        show_latest_follower=_ensure_bool(
            d.get("show_latest_follower"), default=defaults.show_latest_follower
        ),
        show_latest_donation=_ensure_bool(
            d.get("show_latest_donation"), default=defaults.show_latest_donation
        ),
        show_stream_time=_ensure_bool(d.get("show_stream_time"), default=defaults.show_stream_time),
        show_top_donator=_ensure_bool(d.get("show_top_donator"), default=defaults.show_top_donator),
        show_online=_ensure_bool(d.get("show_online"), default=defaults.show_online),
        tiktok_coin_to_value_rate=_validate_coin_rate(
            d.get("tiktok_coin_to_value_rate", defaults.tiktok_coin_to_value_rate)
        ),
        scale_percent=_validate_scale_percent(d.get("scale_percent")),
        accent_color=_ensure_hex_color(d.get("accent_color"), default=defaults.accent_color),
    )


def social_rotator_overlay_config_to_public_dict(
    cfg: SocialRotatorOverlayConfig,
) -> dict[str, object]:
    return {
        "schema_version": int(cfg.schema_version),
        "enabled": bool(cfg.enabled),
        "platforms": parse_platforms(cfg),
        "rotation_interval_ms": int(cfg.rotation_interval_ms),
        "transition": str(cfg.transition),
        "theme": str(cfg.theme),
        "show_url": bool(cfg.show_url),
        "show_countdown": bool(cfg.show_countdown),
        "show_secondary_platforms": bool(cfg.show_secondary_platforms),
        "enable_glow": bool(cfg.enable_glow),
        "enable_particles": bool(cfg.enable_particles),
        "enable_crt": bool(cfg.enable_crt),
        "background_opacity_percent": int(cfg.background_opacity_percent),
        "show_latest_follower": bool(cfg.show_latest_follower),
        "show_latest_donation": bool(cfg.show_latest_donation),
        "show_stream_time": bool(cfg.show_stream_time),
        "show_top_donator": bool(cfg.show_top_donator),
        "show_online": bool(cfg.show_online),
        "tiktok_coin_to_value_rate": float(cfg.tiktok_coin_to_value_rate),
        "scale_percent": int(cfg.scale_percent),
        "accent_color": str(cfg.accent_color),
        "known_platforms": list(ALL_PLATFORM_IDS),
    }


def social_rotator_overlay_config_to_json_text(cfg: SocialRotatorOverlayConfig) -> str:
    return json.dumps(
        social_rotator_overlay_config_to_public_dict(cfg),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def load_social_rotator_overlay_config(
    settings: QSettings | None = None,
) -> SocialRotatorOverlayConfig:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    raw = (s.value(SOCIAL_ROTATOR_OVERLAY_CONFIG_QSETTINGS_KEY, "", str) or "").strip()
    if not raw:
        return social_rotator_overlay_config_defaults()
    try:
        return social_rotator_overlay_config_from_json_text(raw)
    except (ValueError, TypeError, json.JSONDecodeError):
        bak = (s.value(_SOCIAL_ROTATOR_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY, "", str) or "").strip()
        if bak:
            try:
                cfg = social_rotator_overlay_config_from_json_text(bak)
            except (ValueError, TypeError, json.JSONDecodeError):
                return social_rotator_overlay_config_defaults()
            s.setValue(
                SOCIAL_ROTATOR_OVERLAY_CONFIG_QSETTINGS_KEY,
                social_rotator_overlay_config_to_json_text(cfg),
            )
            return cfg
        return social_rotator_overlay_config_defaults()


def save_social_rotator_overlay_config(
    cfg: SocialRotatorOverlayConfig,
    settings: QSettings | None = None,
) -> None:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    txt = social_rotator_overlay_config_to_json_text(cfg)
    s.setValue(SOCIAL_ROTATOR_OVERLAY_CONFIG_QSETTINGS_KEY, txt)
    s.setValue(_SOCIAL_ROTATOR_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY, txt)
    s.sync()
