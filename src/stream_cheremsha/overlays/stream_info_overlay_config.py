from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Any

from PySide6.QtCore import QSettings

STREAM_INFO_OVERLAY_CONFIG_SCHEMA_VERSION = 1
STREAM_INFO_OVERLAY_CONFIG_QSETTINGS_KEY = "overlays/stream_info/main/config_json"
_STREAM_INFO_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY = "overlays/stream_info/main/config_json_backup"

VALID_THEMES = frozenset({"neon_cyber", "synthwave", "toxic", "ice", "amber"})


@dataclass(frozen=True, slots=True)
class StreamInfoOverlayConfig:
    schema_version: int
    enabled: bool
    theme: str
    show_latest_follower: bool
    show_latest_donation: bool
    show_stream_time: bool
    show_top_donator: bool
    show_online: bool
    tiktok_coin_to_value_rate: float
    scale_percent: int
    accent_color: str
    enable_glow: bool
    enable_crt: bool
    background_opacity_percent: int

    def replace(self, **kwargs: object) -> StreamInfoOverlayConfig:
        return replace(self, **kwargs)


def stream_info_overlay_config_defaults() -> StreamInfoOverlayConfig:
    return StreamInfoOverlayConfig(
        schema_version=STREAM_INFO_OVERLAY_CONFIG_SCHEMA_VERSION,
        enabled=True,
        theme="neon_cyber",
        show_latest_follower=True,
        show_latest_donation=True,
        show_stream_time=True,
        show_top_donator=True,
        show_online=True,
        tiktok_coin_to_value_rate=1.0,
        scale_percent=100,
        accent_color="#00ffff",
        enable_glow=True,
        enable_crt=True,
        background_opacity_percent=85,
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


def _validate_theme(v: object) -> str:
    s = _ensure_str(v, default="neon_cyber")
    return s if s in VALID_THEMES else "neon_cyber"


def _validate_scale_percent(v: object) -> int:
    return max(40, min(250, _ensure_int(v, default=100)))


def _validate_background_opacity_percent(v: object) -> int:
    return max(0, min(100, _ensure_int(v, default=85)))


def _validate_coin_rate(v: object) -> float:
    return max(0.0, _ensure_float(v, default=1.0))


def stream_info_overlay_config_from_json_text(text: str) -> StreamInfoOverlayConfig:
    raw = json.loads(text)
    if not isinstance(raw, dict):
        raise ValueError("stream_info overlay config must be a JSON object")
    d: Any = raw
    defaults = stream_info_overlay_config_defaults()
    return StreamInfoOverlayConfig(
        schema_version=_ensure_int(d.get("schema_version"), default=defaults.schema_version),
        enabled=_ensure_bool(d.get("enabled"), default=defaults.enabled),
        theme=_validate_theme(d.get("theme")),
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
        enable_glow=_ensure_bool(d.get("enable_glow"), default=defaults.enable_glow),
        enable_crt=_ensure_bool(d.get("enable_crt"), default=defaults.enable_crt),
        background_opacity_percent=_validate_background_opacity_percent(
            d.get("background_opacity_percent", defaults.background_opacity_percent)
        ),
    )


def stream_info_overlay_config_to_public_dict(cfg: StreamInfoOverlayConfig) -> dict[str, object]:
    return {
        "schema_version": int(cfg.schema_version),
        "enabled": bool(cfg.enabled),
        "theme": str(cfg.theme),
        "show_latest_follower": bool(cfg.show_latest_follower),
        "show_latest_donation": bool(cfg.show_latest_donation),
        "show_stream_time": bool(cfg.show_stream_time),
        "show_top_donator": bool(cfg.show_top_donator),
        "show_online": bool(cfg.show_online),
        "tiktok_coin_to_value_rate": float(cfg.tiktok_coin_to_value_rate),
        "scale_percent": int(cfg.scale_percent),
        "accent_color": str(cfg.accent_color),
        "enable_glow": bool(cfg.enable_glow),
        "enable_crt": bool(cfg.enable_crt),
        "background_opacity_percent": int(cfg.background_opacity_percent),
    }


def stream_info_overlay_config_to_json_text(cfg: StreamInfoOverlayConfig) -> str:
    return json.dumps(
        stream_info_overlay_config_to_public_dict(cfg),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def load_stream_info_overlay_config(settings: QSettings | None = None) -> StreamInfoOverlayConfig:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    raw = (s.value(STREAM_INFO_OVERLAY_CONFIG_QSETTINGS_KEY, "", str) or "").strip()
    if not raw:
        return stream_info_overlay_config_defaults()
    try:
        return stream_info_overlay_config_from_json_text(raw)
    except (ValueError, TypeError, json.JSONDecodeError):
        bak = (s.value(_STREAM_INFO_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY, "", str) or "").strip()
        if bak:
            try:
                cfg = stream_info_overlay_config_from_json_text(bak)
            except (ValueError, TypeError, json.JSONDecodeError):
                return stream_info_overlay_config_defaults()
            s.setValue(
                STREAM_INFO_OVERLAY_CONFIG_QSETTINGS_KEY,
                stream_info_overlay_config_to_json_text(cfg),
            )
            return cfg
        return stream_info_overlay_config_defaults()


def save_stream_info_overlay_config(
    cfg: StreamInfoOverlayConfig,
    settings: QSettings | None = None,
) -> None:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    txt = stream_info_overlay_config_to_json_text(cfg)
    s.setValue(STREAM_INFO_OVERLAY_CONFIG_QSETTINGS_KEY, txt)
    s.setValue(_STREAM_INFO_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY, txt)
    s.sync()
