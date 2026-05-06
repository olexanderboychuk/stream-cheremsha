from __future__ import annotations

import json
from dataclasses import dataclass, replace

from PySide6.QtCore import QSettings

CHAT_CONFIG_SCHEMA_VERSION = 1
CHAT_CONFIG_QSETTINGS_KEY = "overlays/chat/main/config_json"
_CHAT_CONFIG_QSETTINGS_BACKUP_KEY = "overlays/chat/main/config_json_backup"


@dataclass(frozen=True, slots=True)
class ChatOverlayConfig:
    schema_version: int
    max_items: int
    font_family: str
    font_size_px: int
    username_color_mode: str
    username_color_custom: str
    text_color: str
    text_shadow_enabled: bool
    text_shadow_rgba: str
    text_shadow_blur_px: int
    text_shadow_offset_x_px: int
    text_shadow_offset_y_px: int
    widget_bg_enabled: bool
    widget_bg_rgba: str
    widget_bg_radius_px: int
    widget_bg_padding_px: int
    show_platform: bool
    show_platform_icon: bool
    bubble_bg_enabled: bool
    bubble_bg_rgba: str
    bubble_radius_px: int
    fade_seconds: float

    def replace(self, **kwargs: object) -> ChatOverlayConfig:
        return replace(self, **kwargs)


def chat_config_defaults() -> ChatOverlayConfig:
    return ChatOverlayConfig(
        schema_version=CHAT_CONFIG_SCHEMA_VERSION,
        max_items=12,
        font_family="Segoe UI",
        font_size_px=18,
        username_color_mode="auto",
        username_color_custom="#93c5fd",
        text_color="#e5e7eb",
        text_shadow_enabled=False,
        text_shadow_rgba="rgba(0,0,0,0.65)",
        text_shadow_blur_px=4,
        text_shadow_offset_x_px=0,
        text_shadow_offset_y_px=1,
        widget_bg_enabled=False,
        widget_bg_rgba="rgba(10,12,18,0.45)",
        widget_bg_radius_px=14,
        widget_bg_padding_px=10,
        show_platform=True,
        show_platform_icon=True,
        bubble_bg_enabled=True,
        bubble_bg_rgba="rgba(10,12,18,0.55)",
        bubble_radius_px=10,
        fade_seconds=0.0,
    )


def _ensure_int(v: object, *, default: int) -> int:
    try:
        out = int(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return out


def _ensure_float(v: object, *, default: float) -> float:
    try:
        out = float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return out


def chat_config_to_json_text(cfg: ChatOverlayConfig) -> str:
    obj = {
        "schema_version": int(cfg.schema_version),
        "max_items": int(cfg.max_items),
        "font_family": str(cfg.font_family),
        "font_size_px": int(cfg.font_size_px),
        "username_color_mode": str(cfg.username_color_mode),
        "username_color_custom": str(cfg.username_color_custom),
        "text_color": str(cfg.text_color),
        "text_shadow_enabled": bool(cfg.text_shadow_enabled),
        "text_shadow_rgba": str(cfg.text_shadow_rgba),
        "text_shadow_blur_px": int(cfg.text_shadow_blur_px),
        "text_shadow_offset_x_px": int(cfg.text_shadow_offset_x_px),
        "text_shadow_offset_y_px": int(cfg.text_shadow_offset_y_px),
        "widget_bg_enabled": bool(cfg.widget_bg_enabled),
        "widget_bg_rgba": str(cfg.widget_bg_rgba),
        "widget_bg_radius_px": int(cfg.widget_bg_radius_px),
        "widget_bg_padding_px": int(cfg.widget_bg_padding_px),
        "show_platform": bool(cfg.show_platform),
        "show_platform_icon": bool(cfg.show_platform_icon),
        "bubble_bg_enabled": bool(cfg.bubble_bg_enabled),
        "bubble_bg_rgba": str(cfg.bubble_bg_rgba),
        "bubble_radius_px": int(cfg.bubble_radius_px),
        "fade_seconds": float(cfg.fade_seconds),
    }
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def chat_config_from_json_text(text: str) -> ChatOverlayConfig:
    raw = json.loads(text)
    if not isinstance(raw, dict):
        raise ValueError("Invalid chat config JSON")
    # schema_version is informational only; merge keys we understand across versions.

    d = chat_config_defaults()
    max_items = max(1, _ensure_int(raw.get("max_items"), default=d.max_items))
    font_family = str(raw.get("font_family") or d.font_family)
    font_size_px = max(8, _ensure_int(raw.get("font_size_px"), default=d.font_size_px))
    username_color_mode = str(raw.get("username_color_mode") or d.username_color_mode)
    if username_color_mode not in ("auto", "platform", "custom"):
        username_color_mode = d.username_color_mode
    username_color_custom = str(raw.get("username_color_custom") or d.username_color_custom)
    text_color = str(raw.get("text_color") or d.text_color)
    text_shadow_enabled = bool(raw.get("text_shadow_enabled", d.text_shadow_enabled))
    text_shadow_rgba = str(raw.get("text_shadow_rgba") or d.text_shadow_rgba)
    text_shadow_blur_px = max(
        0,
        min(24, _ensure_int(raw.get("text_shadow_blur_px"), default=d.text_shadow_blur_px)),
    )
    text_shadow_offset_x_px = _ensure_int(
        raw.get("text_shadow_offset_x_px"),
        default=d.text_shadow_offset_x_px,
    )
    text_shadow_offset_x_px = max(-12, min(12, text_shadow_offset_x_px))
    text_shadow_offset_y_px = _ensure_int(
        raw.get("text_shadow_offset_y_px"),
        default=d.text_shadow_offset_y_px,
    )
    text_shadow_offset_y_px = max(-12, min(12, text_shadow_offset_y_px))
    widget_bg_enabled = bool(raw.get("widget_bg_enabled", d.widget_bg_enabled))
    widget_bg_rgba = str(raw.get("widget_bg_rgba") or d.widget_bg_rgba)
    widget_bg_radius_px = max(0, _ensure_int(raw.get("widget_bg_radius_px"), default=d.widget_bg_radius_px))
    widget_bg_radius_px = min(60, widget_bg_radius_px)
    widget_bg_padding_px = max(0, _ensure_int(raw.get("widget_bg_padding_px"), default=d.widget_bg_padding_px))
    widget_bg_padding_px = min(48, widget_bg_padding_px)
    show_platform = bool(raw.get("show_platform", d.show_platform))
    show_platform_icon = bool(raw.get("show_platform_icon", d.show_platform_icon))
    bubble_bg_enabled = bool(raw.get("bubble_bg_enabled", d.bubble_bg_enabled))
    bubble_bg_rgba = str(raw.get("bubble_bg_rgba") or d.bubble_bg_rgba)
    bubble_radius_px = max(0, _ensure_int(raw.get("bubble_radius_px"), default=d.bubble_radius_px))
    fade_seconds = max(0.0, _ensure_float(raw.get("fade_seconds"), default=d.fade_seconds))
    return ChatOverlayConfig(
        schema_version=CHAT_CONFIG_SCHEMA_VERSION,
        max_items=max_items,
        font_family=font_family,
        font_size_px=font_size_px,
        username_color_mode=username_color_mode,
        username_color_custom=username_color_custom,
        text_color=text_color,
        text_shadow_enabled=text_shadow_enabled,
        text_shadow_rgba=text_shadow_rgba,
        text_shadow_blur_px=text_shadow_blur_px,
        text_shadow_offset_x_px=text_shadow_offset_x_px,
        text_shadow_offset_y_px=text_shadow_offset_y_px,
        widget_bg_enabled=widget_bg_enabled,
        widget_bg_rgba=widget_bg_rgba,
        widget_bg_radius_px=widget_bg_radius_px,
        widget_bg_padding_px=widget_bg_padding_px,
        show_platform=show_platform,
        show_platform_icon=show_platform_icon,
        bubble_bg_enabled=bubble_bg_enabled,
        bubble_bg_rgba=bubble_bg_rgba,
        bubble_radius_px=bubble_radius_px,
        fade_seconds=fade_seconds,
    )


def load_chat_config(settings: QSettings | None = None) -> ChatOverlayConfig:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    raw = (s.value(CHAT_CONFIG_QSETTINGS_KEY, "", str) or "").strip()
    if not raw:
        return chat_config_defaults()
    try:
        return chat_config_from_json_text(raw)
    except (ValueError, TypeError, json.JSONDecodeError):
        bak = (s.value(_CHAT_CONFIG_QSETTINGS_BACKUP_KEY, "", str) or "").strip()
        if bak:
            try:
                cfg = chat_config_from_json_text(bak)
            except (ValueError, TypeError, json.JSONDecodeError):
                return chat_config_defaults()
            s.setValue(CHAT_CONFIG_QSETTINGS_KEY, chat_config_to_json_text(cfg))
            return cfg
        return chat_config_defaults()


def save_chat_config(cfg: ChatOverlayConfig, settings: QSettings | None = None) -> None:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    txt = chat_config_to_json_text(cfg)
    s.setValue(CHAT_CONFIG_QSETTINGS_KEY, txt)
    s.setValue(_CHAT_CONFIG_QSETTINGS_BACKUP_KEY, txt)
    s.sync()
