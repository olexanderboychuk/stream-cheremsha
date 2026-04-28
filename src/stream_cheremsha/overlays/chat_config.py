from __future__ import annotations

import json
from dataclasses import dataclass, replace

from PySide6.QtCore import QSettings

CHAT_CONFIG_SCHEMA_VERSION = 1
CHAT_CONFIG_QSETTINGS_KEY = "overlays/chat/main/config_json"


@dataclass(frozen=True, slots=True)
class ChatOverlayConfig:
    schema_version: int
    max_items: int
    font_family: str
    font_size_px: int
    author_color: str
    text_color: str
    bg_rgba: str
    show_platform: bool
    fade_seconds: float

    def replace(self, **kwargs: object) -> "ChatOverlayConfig":
        return replace(self, **kwargs)


def chat_config_defaults() -> ChatOverlayConfig:
    return ChatOverlayConfig(
        schema_version=CHAT_CONFIG_SCHEMA_VERSION,
        max_items=12,
        font_family="Segoe UI",
        font_size_px=18,
        author_color="#93c5fd",
        text_color="#e5e7eb",
        bg_rgba="rgba(10,12,18,0.55)",
        show_platform=True,
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
        "author_color": str(cfg.author_color),
        "text_color": str(cfg.text_color),
        "bg_rgba": str(cfg.bg_rgba),
        "show_platform": bool(cfg.show_platform),
        "fade_seconds": float(cfg.fade_seconds),
    }
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def chat_config_from_json_text(text: str) -> ChatOverlayConfig:
    raw = json.loads(text)
    if not isinstance(raw, dict):
        raise ValueError("Invalid chat config JSON")
    ver = _ensure_int(raw.get("schema_version"), default=0)
    if ver != CHAT_CONFIG_SCHEMA_VERSION:
        raise ValueError("Unsupported chat config schema_version")
    d = chat_config_defaults()
    max_items = max(1, _ensure_int(raw.get("max_items"), default=d.max_items))
    font_family = str(raw.get("font_family") or d.font_family)
    font_size_px = max(8, _ensure_int(raw.get("font_size_px"), default=d.font_size_px))
    author_color = str(raw.get("author_color") or d.author_color)
    text_color = str(raw.get("text_color") or d.text_color)
    bg_rgba = str(raw.get("bg_rgba") or d.bg_rgba)
    show_platform = bool(raw.get("show_platform", d.show_platform))
    fade_seconds = max(0.0, _ensure_float(raw.get("fade_seconds"), default=d.fade_seconds))
    return ChatOverlayConfig(
        schema_version=CHAT_CONFIG_SCHEMA_VERSION,
        max_items=max_items,
        font_family=font_family,
        font_size_px=font_size_px,
        author_color=author_color,
        text_color=text_color,
        bg_rgba=bg_rgba,
        show_platform=show_platform,
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
        return chat_config_defaults()


def save_chat_config(cfg: ChatOverlayConfig, settings: QSettings | None = None) -> None:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    s.setValue(CHAT_CONFIG_QSETTINGS_KEY, chat_config_to_json_text(cfg))
