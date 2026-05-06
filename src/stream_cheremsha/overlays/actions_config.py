from __future__ import annotations

import json
from dataclasses import dataclass, replace

from PySide6.QtCore import QSettings

ACTIONS_CONFIG_SCHEMA_VERSION = 1
ACTIONS_CONFIG_QSETTINGS_KEY = "overlays/actions/main/config_json"
_ACTIONS_CONFIG_QSETTINGS_BACKUP_KEY = "overlays/actions/main/config_json_backup"


@dataclass(frozen=True, slots=True)
class ActionsOverlayConfig:
    schema_version: int

    font_family: str
    font_size_px: int
    font_line_spacing_px: int
    font_letter_spacing_px: int

    wave_enabled: bool
    move_enabled: bool
    effect_3d_enabled: bool
    wiggle_enabled: bool

    text_shadow_enabled: bool
    text_shadow_color: str
    text_color: str

    font_border_enabled: bool
    font_border_color: str

    username_custom_color_enabled: bool
    username_custom_color: str
    username_text_effect: str

    picture_size_px: int
    username_size_px: int
    name_text_gap_px: int

    show_profile_picture: bool
    show_gift_picture: bool
    show_action_platform_icon: bool
    platform_icon_flip_enabled: bool
    platform_icon_size_px: int
    single_text_line: bool
    auto_hide_seconds: float
    parallel_popups_enabled: bool

    bubble_bg_enabled: bool
    bubble_bg_alpha: float
    bubble_radius_px: int

    def replace(self, **kwargs: object) -> ActionsOverlayConfig:
        return replace(self, **kwargs)


def actions_config_defaults() -> ActionsOverlayConfig:
    return ActionsOverlayConfig(
        schema_version=ACTIONS_CONFIG_SCHEMA_VERSION,
        font_family="Segoe UI",
        font_size_px=40,
        font_line_spacing_px=0,
        font_letter_spacing_px=0,
        wave_enabled=False,
        move_enabled=False,
        effect_3d_enabled=False,
        wiggle_enabled=False,
        text_shadow_enabled=False,
        text_shadow_color="#000000",
        text_color="#e5e7eb",
        font_border_enabled=False,
        font_border_color="#242424",
        username_custom_color_enabled=False,
        username_custom_color="#32c3a6",
        username_text_effect="none",
        picture_size_px=65,
        username_size_px=65,
        name_text_gap_px=8,
        show_profile_picture=True,
        show_gift_picture=True,
        show_action_platform_icon=True,
        platform_icon_flip_enabled=False,
        platform_icon_size_px=40,
        single_text_line=False,
        auto_hide_seconds=0.0,
        parallel_popups_enabled=False,
        bubble_bg_enabled=True,
        bubble_bg_alpha=0.55,
        bubble_radius_px=16,
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


def actions_config_to_json_text(cfg: ActionsOverlayConfig) -> str:
    obj = {
        "schema_version": int(cfg.schema_version),
        "font_family": str(cfg.font_family),
        "font_size_px": int(cfg.font_size_px),
        "font_line_spacing_px": int(cfg.font_line_spacing_px),
        "font_letter_spacing_px": int(cfg.font_letter_spacing_px),
        "wave_enabled": bool(cfg.wave_enabled),
        "move_enabled": bool(cfg.move_enabled),
        "effect_3d_enabled": bool(cfg.effect_3d_enabled),
        "wiggle_enabled": bool(cfg.wiggle_enabled),
        "text_shadow_enabled": bool(cfg.text_shadow_enabled),
        "text_shadow_color": str(cfg.text_shadow_color),
        "text_color": str(cfg.text_color),
        "font_border_enabled": bool(cfg.font_border_enabled),
        "font_border_color": str(cfg.font_border_color),
        "username_custom_color_enabled": bool(cfg.username_custom_color_enabled),
        "username_custom_color": str(cfg.username_custom_color),
        "username_text_effect": str(cfg.username_text_effect),
        "picture_size_px": int(cfg.picture_size_px),
        "username_size_px": int(cfg.username_size_px),
        "name_text_gap_px": int(cfg.name_text_gap_px),
        "show_profile_picture": bool(cfg.show_profile_picture),
        "show_gift_picture": bool(cfg.show_gift_picture),
        "show_action_platform_icon": bool(cfg.show_action_platform_icon),
        "platform_icon_flip_enabled": bool(cfg.platform_icon_flip_enabled),
        "platform_icon_size_px": int(cfg.platform_icon_size_px),
        "single_text_line": bool(cfg.single_text_line),
        "auto_hide_seconds": float(cfg.auto_hide_seconds),
        "parallel_popups_enabled": bool(cfg.parallel_popups_enabled),
        "bubble_bg_enabled": bool(cfg.bubble_bg_enabled),
        "bubble_bg_alpha": float(cfg.bubble_bg_alpha),
        "bubble_radius_px": int(cfg.bubble_radius_px),
    }
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def actions_config_from_json_text(text: str) -> ActionsOverlayConfig:
    raw = json.loads(text)
    if not isinstance(raw, dict):
        raise ValueError("Invalid actions config JSON")
    # schema_version is informational only: never discard the whole blob because of an
    # unknown/future tag (upgrade/downgrade cycles otherwise reset users to defaults).

    d = actions_config_defaults()

    font_family = str(raw.get("font_family") or d.font_family)
    font_size_px = max(8, _ensure_int(raw.get("font_size_px"), default=d.font_size_px))
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

    wave_enabled = _ensure_bool(raw.get("wave_enabled"), default=d.wave_enabled)
    move_enabled = _ensure_bool(raw.get("move_enabled"), default=d.move_enabled)
    effect_3d_enabled = _ensure_bool(raw.get("effect_3d_enabled"), default=d.effect_3d_enabled)
    wiggle_enabled = _ensure_bool(raw.get("wiggle_enabled"), default=d.wiggle_enabled)

    text_shadow_enabled = _ensure_bool(raw.get("text_shadow_enabled"), default=d.text_shadow_enabled)
    text_shadow_color = str(raw.get("text_shadow_color") or d.text_shadow_color)
    text_color = str(raw.get("text_color") or d.text_color)

    font_border_enabled = _ensure_bool(raw.get("font_border_enabled"), default=d.font_border_enabled)
    font_border_color = str(raw.get("font_border_color") or d.font_border_color)

    username_custom_color_enabled = _ensure_bool(
        raw.get("username_custom_color_enabled"),
        default=d.username_custom_color_enabled,
    )
    username_custom_color = str(raw.get("username_custom_color") or d.username_custom_color)
    username_text_effect = str(raw.get("username_text_effect") or d.username_text_effect)
    if username_text_effect not in ("none", "rainbow", "aurora", "neon", "fire"):
        username_text_effect = d.username_text_effect

    picture_size_px = max(1, _ensure_int(raw.get("picture_size_px"), default=d.picture_size_px))
    picture_size_px = min(512, picture_size_px)
    username_size_px = max(1, _ensure_int(raw.get("username_size_px"), default=d.username_size_px))
    username_size_px = min(512, username_size_px)
    name_text_gap_px = _ensure_int(raw.get("name_text_gap_px"), default=d.name_text_gap_px)
    name_text_gap_px = max(0, min(80, name_text_gap_px))

    show_profile_picture = _ensure_bool(raw.get("show_profile_picture"), default=d.show_profile_picture)
    show_gift_picture = _ensure_bool(raw.get("show_gift_picture"), default=d.show_gift_picture)
    show_action_platform_icon = _ensure_bool(
        raw.get("show_action_platform_icon"),
        default=d.show_action_platform_icon,
    )
    platform_icon_flip_enabled = _ensure_bool(
        raw.get("platform_icon_flip_enabled"),
        default=d.platform_icon_flip_enabled,
    )
    platform_icon_size_px = max(16, _ensure_int(raw.get("platform_icon_size_px"), default=d.platform_icon_size_px))
    platform_icon_size_px = min(128, platform_icon_size_px)
    single_text_line = _ensure_bool(raw.get("single_text_line"), default=d.single_text_line)
    parallel_popups_enabled = _ensure_bool(
        raw.get("parallel_popups_enabled", raw.get("parallelPopupsEnabled")),
        default=d.parallel_popups_enabled,
    )
    auto_hide_seconds = max(0.0, _ensure_float(raw.get("auto_hide_seconds"), default=d.auto_hide_seconds))
    auto_hide_seconds = min(600.0, auto_hide_seconds)

    bubble_bg_enabled = _ensure_bool(raw.get("bubble_bg_enabled"), default=d.bubble_bg_enabled)
    bubble_bg_alpha = _ensure_float(raw.get("bubble_bg_alpha"), default=d.bubble_bg_alpha)
    if not (bubble_bg_alpha == bubble_bg_alpha):  # NaN
        bubble_bg_alpha = d.bubble_bg_alpha
    bubble_bg_alpha = max(0.0, min(1.0, bubble_bg_alpha))
    bubble_radius_px = _ensure_int(raw.get("bubble_radius_px"), default=d.bubble_radius_px)
    bubble_radius_px = max(0, min(60, bubble_radius_px))

    return ActionsOverlayConfig(
        schema_version=ACTIONS_CONFIG_SCHEMA_VERSION,
        font_family=font_family,
        font_size_px=font_size_px,
        font_line_spacing_px=font_line_spacing_px,
        font_letter_spacing_px=font_letter_spacing_px,
        wave_enabled=wave_enabled,
        move_enabled=move_enabled,
        effect_3d_enabled=effect_3d_enabled,
        wiggle_enabled=wiggle_enabled,
        text_shadow_enabled=text_shadow_enabled,
        text_shadow_color=text_shadow_color,
        text_color=text_color,
        font_border_enabled=font_border_enabled,
        font_border_color=font_border_color,
        username_custom_color_enabled=username_custom_color_enabled,
        username_custom_color=username_custom_color,
        username_text_effect=username_text_effect,
        picture_size_px=picture_size_px,
        username_size_px=username_size_px,
        name_text_gap_px=name_text_gap_px,
        show_profile_picture=show_profile_picture,
        show_gift_picture=show_gift_picture,
        show_action_platform_icon=show_action_platform_icon,
        platform_icon_flip_enabled=platform_icon_flip_enabled,
        platform_icon_size_px=platform_icon_size_px,
        single_text_line=single_text_line,
        auto_hide_seconds=auto_hide_seconds,
        parallel_popups_enabled=parallel_popups_enabled,
        bubble_bg_enabled=bubble_bg_enabled,
        bubble_bg_alpha=bubble_bg_alpha,
        bubble_radius_px=bubble_radius_px,
    )


def load_actions_config(settings: QSettings | None = None) -> ActionsOverlayConfig:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    raw = (s.value(ACTIONS_CONFIG_QSETTINGS_KEY, "", str) or "").strip()
    if not raw:
        return actions_config_defaults()
    try:
        return actions_config_from_json_text(raw)
    except (ValueError, TypeError, json.JSONDecodeError):
        # Try backup key as self-healing against partial writes / legacy invalid values.
        bak = (s.value(_ACTIONS_CONFIG_QSETTINGS_BACKUP_KEY, "", str) or "").strip()
        if bak:
            try:
                cfg = actions_config_from_json_text(bak)
            except (ValueError, TypeError, json.JSONDecodeError):
                return actions_config_defaults()
            # Repair primary key for future runs.
            s.setValue(ACTIONS_CONFIG_QSETTINGS_KEY, actions_config_to_json_text(cfg))
            return cfg
        return actions_config_defaults()


def save_actions_config(cfg: ActionsOverlayConfig, settings: QSettings | None = None) -> None:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    txt = actions_config_to_json_text(cfg)
    s.setValue(ACTIONS_CONFIG_QSETTINGS_KEY, txt)
    s.setValue(_ACTIONS_CONFIG_QSETTINGS_BACKUP_KEY, txt)
    s.sync()
