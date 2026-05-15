from __future__ import annotations

import json
from dataclasses import dataclass, replace

from PySide6.QtCore import QSettings

KING_OF_LIVE_OVERLAY_CONFIG_SCHEMA_VERSION = 1
KING_OF_LIVE_OVERLAY_CONFIG_QSETTINGS_KEY = "overlays/king_of_live/main/config_json"
_KING_OF_LIVE_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY = "overlays/king_of_live/main/config_json_backup"

KING_OF_LIVE_PRESETS = frozenset(
    ("imperial_gold", "cyber_king", "dark_overlord", "minimalist"),
)


@dataclass(frozen=True, slots=True)
class KingOfLiveOverlayConfig:
    schema_version: int

    preset: str
    title_text: str
    show_gap_strip: bool
    danger_threshold_pct: int
    avatar_size_px: int
    font_family: str
    backdrop_blur_px: int
    backdrop_bubble_blur_px: int
    rays_intensity_pct: int
    text_scale_pct: int
    anim_intensity_pct: int

    anim_avatar_motion: bool
    anim_crown_float: bool
    anim_rays_spin: bool
    anim_coins_fall: bool
    anim_gem_pulse: bool
    anim_title_shimmer: bool
    anim_fireworks_on_presence: bool

    def replace(self, **kwargs: object) -> KingOfLiveOverlayConfig:
        return replace(self, **kwargs)


def king_of_live_overlay_config_defaults() -> KingOfLiveOverlayConfig:
    return KingOfLiveOverlayConfig(
        schema_version=KING_OF_LIVE_OVERLAY_CONFIG_SCHEMA_VERSION,
        preset="imperial_gold",
        title_text="KING OF THE LIVE",
        show_gap_strip=True,
        danger_threshold_pct=90,
        avatar_size_px=120,
        font_family="Segoe UI",
        backdrop_blur_px=0,
        backdrop_bubble_blur_px=0,
        rays_intensity_pct=130,
        text_scale_pct=100,
        anim_intensity_pct=100,
        anim_avatar_motion=True,
        anim_crown_float=True,
        anim_rays_spin=True,
        anim_coins_fall=True,
        anim_gem_pulse=True,
        anim_title_shimmer=True,
        anim_fireworks_on_presence=True,
    )


def _ensure_int(v: object, *, default: int) -> int:
    try:
        return int(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _ensure_preset(v: object) -> str:
    s = str(v or "").strip().lower()
    if s in KING_OF_LIVE_PRESETS:
        return s
    return "imperial_gold"


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


def king_of_live_overlay_config_to_json_text(cfg: KingOfLiveOverlayConfig) -> str:
    obj = {
        "schema_version": int(cfg.schema_version),
        "preset": str(cfg.preset),
        "title_text": str(cfg.title_text),
        "show_gap_strip": bool(cfg.show_gap_strip),
        "danger_threshold_pct": int(cfg.danger_threshold_pct),
        "avatar_size_px": int(cfg.avatar_size_px),
        "font_family": str(cfg.font_family),
        "backdrop_blur_px": int(cfg.backdrop_blur_px),
        "backdrop_bubble_blur_px": int(cfg.backdrop_bubble_blur_px),
        "rays_intensity_pct": int(cfg.rays_intensity_pct),
        "text_scale_pct": int(cfg.text_scale_pct),
        "anim_intensity_pct": int(cfg.anim_intensity_pct),
        "anim_avatar_motion": bool(cfg.anim_avatar_motion),
        "anim_coins_fall": bool(cfg.anim_coins_fall),
        "anim_crown_float": bool(cfg.anim_crown_float),
        "anim_fireworks_on_presence": bool(cfg.anim_fireworks_on_presence),
        "anim_gem_pulse": bool(cfg.anim_gem_pulse),
        "anim_rays_spin": bool(cfg.anim_rays_spin),
        "anim_title_shimmer": bool(cfg.anim_title_shimmer),
    }
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def king_of_live_overlay_config_from_json_text(text: str) -> KingOfLiveOverlayConfig:
    raw = json.loads(text)
    if not isinstance(raw, dict):
        raise ValueError("king_of_live overlay config must be a JSON object")
    d = raw
    return KingOfLiveOverlayConfig(
        schema_version=_ensure_int(d.get("schema_version"), default=1),
        preset=_ensure_preset(d.get("preset")),
        title_text=(
            str(d.get("title_text") or king_of_live_overlay_config_defaults().title_text).strip()
            or king_of_live_overlay_config_defaults().title_text
        ),
        show_gap_strip=bool(d.get("show_gap_strip", True)),
        danger_threshold_pct=max(
            50,
            min(99, _ensure_int(d.get("danger_threshold_pct"), default=90)),
        ),
        avatar_size_px=max(
            64,
            min(220, _ensure_int(d.get("avatar_size_px"), default=120)),
        ),
        font_family=str(d.get("font_family") or "Segoe UI").strip() or "Segoe UI",
        backdrop_blur_px=max(
            0,
            min(48, _ensure_int(d.get("backdrop_blur_px"), default=0)),
        ),
        backdrop_bubble_blur_px=max(
            0,
            min(48, _ensure_int(d.get("backdrop_bubble_blur_px"), default=0)),
        ),
        rays_intensity_pct=max(
            40,
            min(200, _ensure_int(d.get("rays_intensity_pct"), default=130)),
        ),
        text_scale_pct=max(
            70,
            min(160, _ensure_int(d.get("text_scale_pct"), default=100)),
        ),
        anim_intensity_pct=max(
            25,
            min(200, _ensure_int(d.get("anim_intensity_pct"), default=100)),
        ),
        anim_avatar_motion=_ensure_bool(d.get("anim_avatar_motion"), default=True),
        anim_crown_float=_ensure_bool(d.get("anim_crown_float"), default=True),
        anim_rays_spin=_ensure_bool(d.get("anim_rays_spin"), default=True),
        anim_coins_fall=_ensure_bool(d.get("anim_coins_fall"), default=True),
        anim_gem_pulse=_ensure_bool(d.get("anim_gem_pulse"), default=True),
        anim_title_shimmer=_ensure_bool(d.get("anim_title_shimmer"), default=True),
        anim_fireworks_on_presence=_ensure_bool(d.get("anim_fireworks_on_presence"), default=True),
    )


def load_king_of_live_overlay_config(settings: QSettings | None = None) -> KingOfLiveOverlayConfig:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    raw = (s.value(KING_OF_LIVE_OVERLAY_CONFIG_QSETTINGS_KEY, "", str) or "").strip()
    if not raw:
        return king_of_live_overlay_config_defaults()
    try:
        return king_of_live_overlay_config_from_json_text(raw)
    except (ValueError, TypeError, json.JSONDecodeError):
        bak = (s.value(_KING_OF_LIVE_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY, "", str) or "").strip()
        if bak:
            try:
                cfg = king_of_live_overlay_config_from_json_text(bak)
            except (ValueError, TypeError, json.JSONDecodeError):
                return king_of_live_overlay_config_defaults()
            s.setValue(
                KING_OF_LIVE_OVERLAY_CONFIG_QSETTINGS_KEY,
                king_of_live_overlay_config_to_json_text(cfg),
            )
            return cfg
        return king_of_live_overlay_config_defaults()


def save_king_of_live_overlay_config(
    cfg: KingOfLiveOverlayConfig,
    settings: QSettings | None = None,
) -> None:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    txt = king_of_live_overlay_config_to_json_text(cfg)
    s.setValue(KING_OF_LIVE_OVERLAY_CONFIG_QSETTINGS_KEY, txt)
    s.setValue(_KING_OF_LIVE_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY, txt)
    s.sync()
