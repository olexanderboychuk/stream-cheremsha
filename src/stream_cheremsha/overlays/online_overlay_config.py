from __future__ import annotations

import json
from dataclasses import dataclass, replace

from PySide6.QtCore import QSettings

ONLINE_OVERLAY_CONFIG_SCHEMA_VERSION = 1
ONLINE_OVERLAY_CONFIG_QSETTINGS_KEY = "overlays/online/main/config_json"
_ONLINE_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY = "overlays/online/main/config_json_backup"


@dataclass(frozen=True, slots=True)
class OnlineOverlayConfig:
    schema_version: int

    layout_mode: str

    platform_twitch_enabled: bool
    platform_tiktok_enabled: bool
    platform_youtube_enabled: bool

    font_family: str
    font_size_px: int
    font_line_spacing_px: int
    font_letter_spacing_px: int

    text_shadow_enabled: bool
    text_shadow_color: str
    text_color: str

    font_border_enabled: bool
    font_border_color: str

    text_effect: str

    platform_icon_size_px: int
    icon_number_gap_px: int

    bubble_bg_enabled: bool
    bubble_bg_alpha: float
    bubble_radius_px: int

    def replace(self, **kwargs: object) -> OnlineOverlayConfig:
        return replace(self, **kwargs)


def online_overlay_config_defaults() -> OnlineOverlayConfig:
    return OnlineOverlayConfig(
        schema_version=ONLINE_OVERLAY_CONFIG_SCHEMA_VERSION,
        layout_mode="combined",
        platform_twitch_enabled=True,
        platform_tiktok_enabled=True,
        platform_youtube_enabled=True,
        font_family="Segoe UI",
        font_size_px=36,
        font_line_spacing_px=0,
        font_letter_spacing_px=0,
        text_shadow_enabled=False,
        text_shadow_color="#000000",
        text_color="#e5e7eb",
        font_border_enabled=False,
        font_border_color="#242424",
        text_effect="none",
        platform_icon_size_px=28,
        icon_number_gap_px=12,
        bubble_bg_enabled=True,
        bubble_bg_alpha=0.45,
        bubble_radius_px=14,
    )


def _ensure_int(v: object, *, default: int) -> int:
    try:
        out = int(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return out


def _ensure_bool(v: object, *, default: bool) -> bool:
    if v is None:
        return default
    return bool(v)


def _ensure_float(v: object, *, default: float) -> float:
    try:
        out = float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return out


def online_overlay_config_to_json_text(cfg: OnlineOverlayConfig) -> str:
    obj = {
        "schema_version": int(cfg.schema_version),
        "layout_mode": str(cfg.layout_mode),
        "platform_twitch_enabled": bool(cfg.platform_twitch_enabled),
        "platform_tiktok_enabled": bool(cfg.platform_tiktok_enabled),
        "platform_youtube_enabled": bool(cfg.platform_youtube_enabled),
        "font_family": str(cfg.font_family),
        "font_size_px": int(cfg.font_size_px),
        "font_line_spacing_px": int(cfg.font_line_spacing_px),
        "font_letter_spacing_px": int(cfg.font_letter_spacing_px),
        "text_shadow_enabled": bool(cfg.text_shadow_enabled),
        "text_shadow_color": str(cfg.text_shadow_color),
        "text_color": str(cfg.text_color),
        "font_border_enabled": bool(cfg.font_border_enabled),
        "font_border_color": str(cfg.font_border_color),
        "text_effect": str(cfg.text_effect),
        "platform_icon_size_px": int(cfg.platform_icon_size_px),
        "icon_number_gap_px": int(cfg.icon_number_gap_px),
        "bubble_bg_enabled": bool(cfg.bubble_bg_enabled),
        "bubble_bg_alpha": float(cfg.bubble_bg_alpha),
        "bubble_radius_px": int(cfg.bubble_radius_px),
    }
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def online_overlay_config_from_json_text(text: str) -> OnlineOverlayConfig:
    raw = json.loads(text)
    if not isinstance(raw, dict):
        raise ValueError("Invalid online overlay config JSON")

    d = online_overlay_config_defaults()

    layout_mode = str(raw.get("layout_mode") or d.layout_mode).strip().lower()
    if layout_mode not in ("combined", "per_platform"):
        layout_mode = d.layout_mode

    platform_twitch_enabled = _ensure_bool(
        raw.get("platform_twitch_enabled"), default=d.platform_twitch_enabled
    )
    platform_tiktok_enabled = _ensure_bool(
        raw.get("platform_tiktok_enabled"), default=d.platform_tiktok_enabled
    )
    platform_youtube_enabled = _ensure_bool(
        raw.get("platform_youtube_enabled"), default=d.platform_youtube_enabled
    )

    font_family = str(raw.get("font_family") or d.font_family)
    font_size_px = max(8, _ensure_int(raw.get("font_size_px"), default=d.font_size_px))
    font_size_px = min(200, font_size_px)
    font_line_spacing_px = _ensure_int(
        raw.get("font_line_spacing_px"),
        default=d.font_line_spacing_px,
    )
    font_line_spacing_px = max(0, min(200, font_line_spacing_px))
    font_letter_spacing_px = _ensure_int(
        raw.get("font_letter_spacing_px"),
        default=d.font_letter_spacing_px,
    )
    font_letter_spacing_px = max(-200, min(200, font_letter_spacing_px))

    text_shadow_enabled = _ensure_bool(
        raw.get("text_shadow_enabled"),
        default=d.text_shadow_enabled,
    )
    text_shadow_color = str(raw.get("text_shadow_color") or d.text_shadow_color)
    text_color = str(raw.get("text_color") or d.text_color)

    font_border_enabled = _ensure_bool(
        raw.get("font_border_enabled"),
        default=d.font_border_enabled,
    )
    font_border_color = str(raw.get("font_border_color") or d.font_border_color)

    text_effect = str(raw.get("text_effect") or d.text_effect).strip().lower()
    if text_effect not in ("none", "glow", "neon", "rainbow", "aurora", "fire"):
        text_effect = d.text_effect

    platform_icon_size_px = max(
        16, _ensure_int(raw.get("platform_icon_size_px"), default=d.platform_icon_size_px)
    )
    platform_icon_size_px = min(128, platform_icon_size_px)
    icon_number_gap_px = _ensure_int(raw.get("icon_number_gap_px"), default=d.icon_number_gap_px)
    icon_number_gap_px = max(0, min(80, icon_number_gap_px))

    bubble_bg_enabled = _ensure_bool(raw.get("bubble_bg_enabled"), default=d.bubble_bg_enabled)
    bubble_bg_alpha = _ensure_float(raw.get("bubble_bg_alpha"), default=d.bubble_bg_alpha)
    if bubble_bg_alpha != bubble_bg_alpha:  # NaN
        bubble_bg_alpha = d.bubble_bg_alpha
    bubble_bg_alpha = max(0.0, min(1.0, bubble_bg_alpha))
    bubble_radius_px = _ensure_int(raw.get("bubble_radius_px"), default=d.bubble_radius_px)
    bubble_radius_px = max(0, min(60, bubble_radius_px))

    return OnlineOverlayConfig(
        schema_version=ONLINE_OVERLAY_CONFIG_SCHEMA_VERSION,
        layout_mode=layout_mode,
        platform_twitch_enabled=platform_twitch_enabled,
        platform_tiktok_enabled=platform_tiktok_enabled,
        platform_youtube_enabled=platform_youtube_enabled,
        font_family=font_family,
        font_size_px=font_size_px,
        font_line_spacing_px=font_line_spacing_px,
        font_letter_spacing_px=font_letter_spacing_px,
        text_shadow_enabled=text_shadow_enabled,
        text_shadow_color=text_shadow_color,
        text_color=text_color,
        font_border_enabled=font_border_enabled,
        font_border_color=font_border_color,
        text_effect=text_effect,
        platform_icon_size_px=platform_icon_size_px,
        icon_number_gap_px=icon_number_gap_px,
        bubble_bg_enabled=bubble_bg_enabled,
        bubble_bg_alpha=bubble_bg_alpha,
        bubble_radius_px=bubble_radius_px,
    )


def load_online_overlay_config(settings: QSettings | None = None) -> OnlineOverlayConfig:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    raw = (s.value(ONLINE_OVERLAY_CONFIG_QSETTINGS_KEY, "", str) or "").strip()
    if not raw:
        return online_overlay_config_defaults()
    try:
        return online_overlay_config_from_json_text(raw)
    except (ValueError, TypeError, json.JSONDecodeError):
        bak = (s.value(_ONLINE_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY, "", str) or "").strip()
        if bak:
            try:
                cfg = online_overlay_config_from_json_text(bak)
            except (ValueError, TypeError, json.JSONDecodeError):
                return online_overlay_config_defaults()
            s.setValue(ONLINE_OVERLAY_CONFIG_QSETTINGS_KEY, online_overlay_config_to_json_text(cfg))
            return cfg
        return online_overlay_config_defaults()


def save_online_overlay_config(cfg: OnlineOverlayConfig, settings: QSettings | None = None) -> None:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    txt = online_overlay_config_to_json_text(cfg)
    s.setValue(ONLINE_OVERLAY_CONFIG_QSETTINGS_KEY, txt)
    s.setValue(_ONLINE_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY, txt)
    s.sync()
