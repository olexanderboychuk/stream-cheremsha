from __future__ import annotations

import json
from typing import TypeAlias

from PySide6.QtCore import QSettings

from stream_cheremsha.overlays.top_likers_overlay_config import (
    TopLikersOverlayConfig,
    top_likers_overlay_config_defaults,
    top_likers_overlay_config_from_json_text,
    top_likers_overlay_config_to_json_text,
)

TOPGIFTERS_OVERLAY_CONFIG_QSETTINGS_KEY = "overlays/top_gifters/main/config_json"
_TOPGIFTERS_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY = "overlays/top_gifters/main/config_json_backup"

# Public type for GIFters UI/storage (JSON field set matches likers; QSettings keys do not).
TopGiftersOverlayConfig: TypeAlias = TopLikersOverlayConfig


def top_gifters_overlay_config_from_json_text(text: str) -> TopGiftersOverlayConfig:
    """Parse GIFters overlay JSON.

    Same keys as likers schema; persist only under GIFters QSettings paths.
    """
    return top_likers_overlay_config_from_json_text(text)


def top_gifters_overlay_config_to_json_text(cfg: TopGiftersOverlayConfig) -> str:
    """Canonical JSON for GIFters overlay."""
    return top_likers_overlay_config_to_json_text(cfg)


def top_gifters_overlay_config_defaults() -> TopGiftersOverlayConfig:
    return top_likers_overlay_config_defaults().replace(
        color_username="#ff69b4",
        color_points="#ffd700",
        color_rank="#f4f4f5",
        list_bg_rgba="rgba(26,26,26,0.92)",
    )


def load_top_gifters_overlay_config(settings: QSettings | None = None) -> TopGiftersOverlayConfig:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    raw = (s.value(TOPGIFTERS_OVERLAY_CONFIG_QSETTINGS_KEY, "", str) or "").strip()
    if not raw:
        return top_gifters_overlay_config_defaults()
    try:
        return top_gifters_overlay_config_from_json_text(raw)
    except (ValueError, TypeError, json.JSONDecodeError):
        bak = (s.value(_TOPGIFTERS_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY, "", str) or "").strip()
        if bak:
            try:
                cfg = top_gifters_overlay_config_from_json_text(bak)
            except (ValueError, TypeError, json.JSONDecodeError):
                return top_gifters_overlay_config_defaults()
            s.setValue(
                TOPGIFTERS_OVERLAY_CONFIG_QSETTINGS_KEY,
                top_gifters_overlay_config_to_json_text(cfg),
            )
            return cfg
        return top_gifters_overlay_config_defaults()


def save_top_gifters_overlay_config(
    cfg: TopGiftersOverlayConfig,
    settings: QSettings | None = None,
) -> None:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    txt = top_gifters_overlay_config_to_json_text(cfg)
    s.setValue(TOPGIFTERS_OVERLAY_CONFIG_QSETTINGS_KEY, txt)
    s.setValue(_TOPGIFTERS_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY, txt)
    s.sync()
