from __future__ import annotations

import json
from dataclasses import dataclass, replace

from PySide6.QtCore import QSettings

TOPLIKERS_OVERLAY_CONFIG_SCHEMA_VERSION = 1
TOPLIKERS_OVERLAY_CONFIG_QSETTINGS_KEY = "overlays/top_likers/main/config_json"
_TOPLIKERS_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY = "overlays/top_likers/main/config_json_backup"

TOP_LIKERS_USERNAME_TEXT_EFFECTS = frozenset(
    (
        "none",
        "rainbow",
        "aurora",
        "cyberpunk",
        "fire",
        "ice",
        "cold",
        "freeze",
        "strong",
    )
)


@dataclass(frozen=True, slots=True)
class TopLikersOverlayConfig:
    schema_version: int

    font_family: str
    font_size_px: int
    font_line_spacing_px: int
    font_letter_spacing_px: int

    color_username: str
    color_points: str
    color_rank: str

    bg_shadow_enabled: bool
    bg_shadow_color: str

    username_text_shadow_enabled: bool
    username_text_shadow_color: str
    likes_text_shadow_enabled: bool
    likes_text_shadow_color: str
    leader_sort: str

    show_rank: bool
    show_likes: bool
    rtl: bool
    show_top1_crown: bool
    show_top3_medal: bool
    show_heart: bool
    heart_animated: bool
    heart_size_px: int

    text_effect_username: str
    wave_enabled: bool
    wave_speed: str

    font_border_enabled: bool
    font_border_color: str

    top_count: int
    avatar_size_px: int
    row_gap_px: int

    list_bg_enabled: bool
    list_bg_rgba: str
    list_radius_px: int
    # 0 = off. N>0: N s at top, scroll list down+up, N s at top, repeat.
    list_scroll_interval_sec: int

    def replace(self, **kwargs: object) -> TopLikersOverlayConfig:
        return replace(self, **kwargs)


def top_likers_overlay_config_defaults() -> TopLikersOverlayConfig:
    return TopLikersOverlayConfig(
        schema_version=TOPLIKERS_OVERLAY_CONFIG_SCHEMA_VERSION,
        font_family="Segoe UI",
        font_size_px=22,
        font_line_spacing_px=4,
        font_letter_spacing_px=0,
        color_username="#c4b5fd",
        color_points="#f4f4f5",
        color_rank="#d9d9d9",
        bg_shadow_enabled=False,
        bg_shadow_color="rgba(33,33,33,0.4)",
        username_text_shadow_enabled=False,
        username_text_shadow_color="#000000",
        likes_text_shadow_enabled=False,
        likes_text_shadow_color="#000000",
        leader_sort="likes_desc",
        show_rank=True,
        show_likes=True,
        rtl=False,
        show_top1_crown=True,
        show_top3_medal=True,
        show_heart=True,
        heart_animated=True,
        heart_size_px=14,
        text_effect_username="none",
        wave_enabled=False,
        wave_speed="normal",
        font_border_enabled=True,
        font_border_color="#242424",
        top_count=8,
        avatar_size_px=48,
        row_gap_px=10,
        list_bg_enabled=True,
        list_bg_rgba="rgba(18,20,28,0.72)",
        list_radius_px=12,
        list_scroll_interval_sec=0,
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


def top_likers_overlay_config_to_json_text(cfg: TopLikersOverlayConfig) -> str:
    obj = {
        "schema_version": int(cfg.schema_version),
        "font_family": str(cfg.font_family),
        "font_size_px": int(cfg.font_size_px),
        "font_line_spacing_px": int(cfg.font_line_spacing_px),
        "font_letter_spacing_px": int(cfg.font_letter_spacing_px),
        "color_username": str(cfg.color_username),
        "color_points": str(cfg.color_points),
        "color_rank": str(cfg.color_rank),
        "bg_shadow_enabled": bool(cfg.bg_shadow_enabled),
        "bg_shadow_color": str(cfg.bg_shadow_color),
        "username_text_shadow_enabled": bool(cfg.username_text_shadow_enabled),
        "username_text_shadow_color": str(cfg.username_text_shadow_color),
        "likes_text_shadow_enabled": bool(cfg.likes_text_shadow_enabled),
        "likes_text_shadow_color": str(cfg.likes_text_shadow_color),
        "leader_sort": str(cfg.leader_sort),
        "show_rank": bool(cfg.show_rank),
        "show_likes": bool(cfg.show_likes),
        "rtl": bool(cfg.rtl),
        "show_top1_crown": bool(cfg.show_top1_crown),
        "show_top3_medal": bool(cfg.show_top3_medal),
        "show_heart": bool(cfg.show_heart),
        "heart_animated": bool(cfg.heart_animated),
        "heart_size_px": int(cfg.heart_size_px),
        "text_effect_username": str(cfg.text_effect_username),
        "wave_enabled": bool(cfg.wave_enabled),
        "wave_speed": str(cfg.wave_speed),
        "font_border_enabled": bool(cfg.font_border_enabled),
        "font_border_color": str(cfg.font_border_color),
        "top_count": int(cfg.top_count),
        "avatar_size_px": int(cfg.avatar_size_px),
        "row_gap_px": int(cfg.row_gap_px),
        "list_bg_enabled": bool(cfg.list_bg_enabled),
        "list_bg_rgba": str(cfg.list_bg_rgba),
        "list_radius_px": int(cfg.list_radius_px),
        "list_scroll_interval_sec": int(cfg.list_scroll_interval_sec),
    }
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def top_likers_overlay_config_from_json_text(text: str) -> TopLikersOverlayConfig:
    raw = json.loads(text)
    if not isinstance(raw, dict):
        raise ValueError("Invalid top likers overlay config JSON")

    d = top_likers_overlay_config_defaults()

    font_family = str(raw.get("font_family") or d.font_family)
    font_size_px = max(8, min(120, _ensure_int(raw.get("font_size_px"), default=d.font_size_px)))
    font_line_spacing_px = max(
        0,
        min(80, _ensure_int(raw.get("font_line_spacing_px"), default=d.font_line_spacing_px)),
    )
    font_letter_spacing_px = max(
        -20,
        min(40, _ensure_int(raw.get("font_letter_spacing_px"), default=d.font_letter_spacing_px)),
    )

    color_username = str(raw.get("color_username") or d.color_username)
    color_points = str(raw.get("color_points") or d.color_points)
    color_rank = str(raw.get("color_rank") or d.color_rank)

    bg_shadow_enabled = _ensure_bool(raw.get("bg_shadow_enabled"), default=d.bg_shadow_enabled)
    bg_shadow_color = str(raw.get("bg_shadow_color") or d.bg_shadow_color)

    if "username_text_shadow_enabled" in raw:
        username_text_shadow_enabled = _ensure_bool(
            raw.get("username_text_shadow_enabled"),
            default=d.username_text_shadow_enabled,
        )
    else:
        username_text_shadow_enabled = _ensure_bool(
            raw.get("bg_shadow_enabled"),
            default=d.username_text_shadow_enabled,
        )
    if "username_text_shadow_color" in raw:
        username_text_shadow_color = str(
            raw.get("username_text_shadow_color") or d.username_text_shadow_color
        )
    else:
        username_text_shadow_color = str(raw.get("bg_shadow_color") or d.username_text_shadow_color)

    if "likes_text_shadow_enabled" in raw:
        likes_text_shadow_enabled = _ensure_bool(
            raw.get("likes_text_shadow_enabled"),
            default=d.likes_text_shadow_enabled,
        )
    else:
        likes_text_shadow_enabled = _ensure_bool(
            raw.get("bg_shadow_enabled"),
            default=d.likes_text_shadow_enabled,
        )
    if "likes_text_shadow_color" in raw:
        likes_text_shadow_color = str(
            raw.get("likes_text_shadow_color") or d.likes_text_shadow_color
        )
    else:
        likes_text_shadow_color = str(raw.get("bg_shadow_color") or d.likes_text_shadow_color)

    leader_sort = str(raw.get("leader_sort") or d.leader_sort).strip().lower()
    if leader_sort not in ("likes_desc", "likes_asc", "name_asc"):
        leader_sort = d.leader_sort

    show_rank = _ensure_bool(raw.get("show_rank"), default=d.show_rank)
    show_likes = _ensure_bool(raw.get("show_likes"), default=d.show_likes)
    rtl = _ensure_bool(raw.get("rtl"), default=d.rtl)
    show_top1_crown = _ensure_bool(raw.get("show_top1_crown"), default=d.show_top1_crown)
    show_top3_medal = _ensure_bool(raw.get("show_top3_medal"), default=d.show_top3_medal)
    show_heart = _ensure_bool(raw.get("show_heart"), default=d.show_heart)
    heart_animated = _ensure_bool(raw.get("heart_animated"), default=d.heart_animated)
    heart_size_px = max(
        8,
        min(48, _ensure_int(raw.get("heart_size_px"), default=d.heart_size_px)),
    )

    raw_tex = str(raw.get("text_effect_username") or d.text_effect_username)
    text_effect_username = raw_tex.strip().lower()
    if text_effect_username not in TOP_LIKERS_USERNAME_TEXT_EFFECTS:
        text_effect_username = d.text_effect_username

    wave_enabled = _ensure_bool(raw.get("wave_enabled"), default=d.wave_enabled)
    wave_speed = str(raw.get("wave_speed") or d.wave_speed).strip().lower()
    if wave_speed not in ("slow", "normal", "fast"):
        wave_speed = d.wave_speed

    font_border_enabled = _ensure_bool(
        raw.get("font_border_enabled"),
        default=d.font_border_enabled,
    )
    font_border_color = str(raw.get("font_border_color") or d.font_border_color)

    top_count = max(1, min(10, _ensure_int(raw.get("top_count"), default=d.top_count)))
    avatar_size_px = max(
        24,
        min(120, _ensure_int(raw.get("avatar_size_px"), default=d.avatar_size_px)),
    )
    row_gap_px = max(0, min(40, _ensure_int(raw.get("row_gap_px"), default=d.row_gap_px)))

    list_bg_enabled = _ensure_bool(raw.get("list_bg_enabled"), default=d.list_bg_enabled)
    list_bg_rgba = str(raw.get("list_bg_rgba") or d.list_bg_rgba)
    list_radius_px = max(
        0,
        min(40, _ensure_int(raw.get("list_radius_px"), default=d.list_radius_px)),
    )
    list_scroll_interval_sec = max(
        0,
        min(
            600,
            _ensure_int(
                raw.get("list_scroll_interval_sec"),
                default=d.list_scroll_interval_sec,
            ),
        ),
    )

    return TopLikersOverlayConfig(
        schema_version=TOPLIKERS_OVERLAY_CONFIG_SCHEMA_VERSION,
        font_family=font_family,
        font_size_px=font_size_px,
        font_line_spacing_px=font_line_spacing_px,
        font_letter_spacing_px=font_letter_spacing_px,
        color_username=color_username,
        color_points=color_points,
        color_rank=color_rank,
        bg_shadow_enabled=bg_shadow_enabled,
        bg_shadow_color=bg_shadow_color,
        username_text_shadow_enabled=username_text_shadow_enabled,
        username_text_shadow_color=username_text_shadow_color,
        likes_text_shadow_enabled=likes_text_shadow_enabled,
        likes_text_shadow_color=likes_text_shadow_color,
        leader_sort=leader_sort,
        show_rank=show_rank,
        show_likes=show_likes,
        rtl=rtl,
        show_top1_crown=show_top1_crown,
        show_top3_medal=show_top3_medal,
        show_heart=show_heart,
        heart_animated=heart_animated,
        heart_size_px=heart_size_px,
        text_effect_username=text_effect_username,
        wave_enabled=wave_enabled,
        wave_speed=wave_speed,
        font_border_enabled=font_border_enabled,
        font_border_color=font_border_color,
        top_count=top_count,
        avatar_size_px=avatar_size_px,
        row_gap_px=row_gap_px,
        list_bg_enabled=list_bg_enabled,
        list_bg_rgba=list_bg_rgba,
        list_radius_px=list_radius_px,
        list_scroll_interval_sec=list_scroll_interval_sec,
    )


def load_top_likers_overlay_config(settings: QSettings | None = None) -> TopLikersOverlayConfig:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    raw = (s.value(TOPLIKERS_OVERLAY_CONFIG_QSETTINGS_KEY, "", str) or "").strip()
    if not raw:
        return top_likers_overlay_config_defaults()
    try:
        return top_likers_overlay_config_from_json_text(raw)
    except (ValueError, TypeError, json.JSONDecodeError):
        bak = (s.value(_TOPLIKERS_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY, "", str) or "").strip()
        if bak:
            try:
                cfg = top_likers_overlay_config_from_json_text(bak)
            except (ValueError, TypeError, json.JSONDecodeError):
                return top_likers_overlay_config_defaults()
            s.setValue(
                TOPLIKERS_OVERLAY_CONFIG_QSETTINGS_KEY,
                top_likers_overlay_config_to_json_text(cfg),
            )
            return cfg
        return top_likers_overlay_config_defaults()


def save_top_likers_overlay_config(
    cfg: TopLikersOverlayConfig,
    settings: QSettings | None = None,
) -> None:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    txt = top_likers_overlay_config_to_json_text(cfg)
    s.setValue(TOPLIKERS_OVERLAY_CONFIG_QSETTINGS_KEY, txt)
    s.setValue(_TOPLIKERS_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY, txt)
    s.sync()
