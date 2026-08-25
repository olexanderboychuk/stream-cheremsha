from __future__ import annotations

import json
from dataclasses import dataclass, replace

from PySide6.QtCore import QSettings

COMMUNITY_WORLD_OVERLAY_CONFIG_SCHEMA_VERSION = 1
COMMUNITY_WORLD_OVERLAY_CONFIG_QSETTINGS_KEY = "overlays/community_world/main/config_json"
_COMMUNITY_WORLD_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY = (
    "overlays/community_world/main/config_json_backup"
)

# Quest slot types allowed in the four quest slots.
COMMUNITY_WORLD_QUEST_TYPES: frozenset[str] = frozenset(
    ("none", "likes", "shares", "gifts", "follows")
)

# Visual themes for the world (drives overlay palette/building style).
COMMUNITY_WORLD_THEMES: frozenset[str] = frozenset(
    ("pixel", "fantasy", "cyber", "ukrainian")
)

# Overlay layouts: "full" immersive world or "compact" vertical widget.
COMMUNITY_WORLD_LAYOUT_MODES: frozenset[str] = frozenset(("full", "compact"))


@dataclass(frozen=True, slots=True)
class CommunityWorldOverlayConfig:
    schema_version: int

    enabled: bool

    # Theme ("pixel" | "fantasy" | "cyber" | "ukrainian").
    theme: str

    # Layout ("full" | "compact").
    layout_mode: str

    # XP earned per engagement event.
    xp_follow: int
    xp_join: int
    xp_chat: int
    xp_like_per_10: int
    xp_share: int
    xp_gift_coin_per_10: int
    xp_battle_win: int

    # Four live quest slots.
    quest1_type: str
    quest2_type: str
    quest3_type: str
    quest4_type: str
    quest_likes_target: int
    quest_shares_target: int
    quest_gifts_target: int
    quest_follows_target: int

    # Display toggles.
    show_level: bool
    show_quests: bool
    show_recognition: bool
    show_passports: bool
    show_buildings: bool
    show_elders: bool
    quiet_mode: bool

    feed_max_items: int
    font_family: str
    font_size_px: int
    scale_pct: int

    color_title: str
    color_progress: str
    color_quest_bg: str
    color_text: str
    color_accent: str

    def replace(self, **kwargs: object) -> CommunityWorldOverlayConfig:
        return replace(self, **kwargs)


def community_world_overlay_config_defaults() -> CommunityWorldOverlayConfig:
    return CommunityWorldOverlayConfig(
        schema_version=COMMUNITY_WORLD_OVERLAY_CONFIG_SCHEMA_VERSION,
        enabled=True,
        theme="ukrainian",
        layout_mode="full",
        xp_follow=40,
        xp_join=5,
        xp_chat=2,
        xp_like_per_10=2,
        xp_share=25,
        xp_gift_coin_per_10=1,
        xp_battle_win=150,
        quest1_type="likes",
        quest2_type="shares",
        quest3_type="gifts",
        quest4_type="follows",
        quest_likes_target=5000,
        quest_shares_target=50,
        quest_gifts_target=1000,
        quest_follows_target=100,
        show_level=True,
        show_quests=True,
        show_recognition=True,
        show_passports=True,
        show_buildings=True,
        show_elders=True,
        quiet_mode=False,
        feed_max_items=12,
        font_family="Segoe UI",
        font_size_px=16,
        scale_pct=100,
        color_title="#fde047",
        color_progress="#4ade80",
        color_quest_bg="rgba(15,23,42,0.55)",
        color_text="#f1f5f9",
        color_accent="#a78bfa",
    )


def _ensure_int(v: object, *, default: int, lo: int | None = None, hi: int | None = None) -> int:
    try:
        out = int(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        out = default
    if lo is not None:
        out = max(lo, out)
    if hi is not None:
        out = min(hi, out)
    return out


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


def _ensure_quest_type(v: object, *, default: str) -> str:
    s = str(v or "").strip().lower()
    if s in COMMUNITY_WORLD_QUEST_TYPES:
        return s
    return default


def _ensure_theme(v: object) -> str:
    s = str(v or "").strip().lower()
    if s in COMMUNITY_WORLD_THEMES:
        return s
    return "ukrainian"


def _ensure_layout_mode(v: object) -> str:
    s = str(v or "").strip().lower()
    if s in COMMUNITY_WORLD_LAYOUT_MODES:
        return s
    return "full"


def community_world_overlay_config_to_json_text(cfg: CommunityWorldOverlayConfig) -> str:
    obj = {
        "schema_version": int(cfg.schema_version),
        "enabled": bool(cfg.enabled),
        "theme": str(cfg.theme),
        "layout_mode": str(cfg.layout_mode),
        "xp_follow": int(cfg.xp_follow),
        "xp_join": int(cfg.xp_join),
        "xp_chat": int(cfg.xp_chat),
        "xp_like_per_10": int(cfg.xp_like_per_10),
        "xp_share": int(cfg.xp_share),
        "xp_gift_coin_per_10": int(cfg.xp_gift_coin_per_10),
        "xp_battle_win": int(cfg.xp_battle_win),
        "quest1_type": str(cfg.quest1_type),
        "quest2_type": str(cfg.quest2_type),
        "quest3_type": str(cfg.quest3_type),
        "quest4_type": str(cfg.quest4_type),
        "quest_likes_target": int(cfg.quest_likes_target),
        "quest_shares_target": int(cfg.quest_shares_target),
        "quest_gifts_target": int(cfg.quest_gifts_target),
        "quest_follows_target": int(cfg.quest_follows_target),
        "show_level": bool(cfg.show_level),
        "show_quests": bool(cfg.show_quests),
        "show_recognition": bool(cfg.show_recognition),
        "show_passports": bool(cfg.show_passports),
        "show_buildings": bool(cfg.show_buildings),
        "show_elders": bool(cfg.show_elders),
        "quiet_mode": bool(cfg.quiet_mode),
        "feed_max_items": int(cfg.feed_max_items),
        "font_family": str(cfg.font_family),
        "font_size_px": int(cfg.font_size_px),
        "scale_pct": int(cfg.scale_pct),
        "color_title": str(cfg.color_title),
        "color_progress": str(cfg.color_progress),
        "color_quest_bg": str(cfg.color_quest_bg),
        "color_text": str(cfg.color_text),
        "color_accent": str(cfg.color_accent),
    }
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def community_world_overlay_config_from_json_text(
    text: str,
) -> CommunityWorldOverlayConfig:
    raw = json.loads(text)
    if not isinstance(raw, dict):
        raise ValueError("community_world overlay config must be a JSON object")
    d = raw
    de = community_world_overlay_config_defaults()
    return CommunityWorldOverlayConfig(
        schema_version=_ensure_int(d.get("schema_version"), default=de.schema_version),
        enabled=_ensure_bool(d.get("enabled"), default=de.enabled),
        theme=_ensure_theme(d.get("theme")),
        layout_mode=_ensure_layout_mode(d.get("layout_mode")),
        xp_follow=_ensure_int(d.get("xp_follow"), default=de.xp_follow, lo=0, hi=1000),
        xp_join=_ensure_int(d.get("xp_join"), default=de.xp_join, lo=0, hi=1000),
        xp_chat=_ensure_int(d.get("xp_chat"), default=de.xp_chat, lo=0, hi=1000),
        xp_like_per_10=_ensure_int(
            d.get("xp_like_per_10"), default=de.xp_like_per_10, lo=0, hi=1000
        ),
        xp_share=_ensure_int(d.get("xp_share"), default=de.xp_share, lo=0, hi=1000),
        xp_gift_coin_per_10=_ensure_int(
            d.get("xp_gift_coin_per_10"), default=de.xp_gift_coin_per_10, lo=0, hi=1000
        ),
        xp_battle_win=_ensure_int(
            d.get("xp_battle_win"), default=de.xp_battle_win, lo=0, hi=10000
        ),
        quest1_type=_ensure_quest_type(d.get("quest1_type"), default=de.quest1_type),
        quest2_type=_ensure_quest_type(d.get("quest2_type"), default=de.quest2_type),
        quest3_type=_ensure_quest_type(d.get("quest3_type"), default=de.quest3_type),
        quest4_type=_ensure_quest_type(d.get("quest4_type"), default=de.quest4_type),
        quest_likes_target=_ensure_int(
            d.get("quest_likes_target"), default=de.quest_likes_target, lo=1, hi=100_000_000
        ),
        quest_shares_target=_ensure_int(
            d.get("quest_shares_target"), default=de.quest_shares_target, lo=1, hi=1_000_000
        ),
        quest_gifts_target=_ensure_int(
            d.get("quest_gifts_target"), default=de.quest_gifts_target, lo=1, hi=100_000_000
        ),
        quest_follows_target=_ensure_int(
            d.get("quest_follows_target"), default=de.quest_follows_target, lo=1, hi=1_000_000
        ),
        show_level=_ensure_bool(d.get("show_level"), default=de.show_level),
        show_quests=_ensure_bool(d.get("show_quests"), default=de.show_quests),
        show_recognition=_ensure_bool(d.get("show_recognition"), default=de.show_recognition),
        show_passports=_ensure_bool(d.get("show_passports"), default=de.show_passports),
        show_buildings=_ensure_bool(d.get("show_buildings"), default=de.show_buildings),
        show_elders=_ensure_bool(d.get("show_elders"), default=de.show_elders),
        quiet_mode=_ensure_bool(d.get("quiet_mode"), default=de.quiet_mode),
        feed_max_items=_ensure_int(d.get("feed_max_items"), default=de.feed_max_items, lo=1, hi=50),
        font_family=str(d.get("font_family") or de.font_family).strip() or de.font_family,
        font_size_px=_ensure_int(d.get("font_size_px"), default=de.font_size_px, lo=8, hi=120),
        scale_pct=_ensure_int(d.get("scale_pct"), default=de.scale_pct, lo=40, hi=200),
        color_title=str(d.get("color_title") or de.color_title),
        color_progress=str(d.get("color_progress") or de.color_progress),
        color_quest_bg=str(d.get("color_quest_bg") or de.color_quest_bg),
        color_text=str(d.get("color_text") or de.color_text),
        color_accent=str(d.get("color_accent") or de.color_accent),
    )


def community_world_overlay_config_to_public_dict(cfg: CommunityWorldOverlayConfig) -> dict:
    """Dict sent to the overlay JS (no internal-only keys)."""
    return json.loads(community_world_overlay_config_to_json_text(cfg))


def load_community_world_overlay_config(
    settings: QSettings | None = None,
) -> CommunityWorldOverlayConfig:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    raw = (
        s.value(COMMUNITY_WORLD_OVERLAY_CONFIG_QSETTINGS_KEY, "", str) or ""
    ).strip()
    if not raw:
        return community_world_overlay_config_defaults()
    try:
        return community_world_overlay_config_from_json_text(raw)
    except (ValueError, TypeError, json.JSONDecodeError):
        bak = (
            s.value(_COMMUNITY_WORLD_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY, "", str) or ""
        ).strip()
        if bak:
            try:
                cfg = community_world_overlay_config_from_json_text(bak)
            except (ValueError, TypeError, json.JSONDecodeError):
                return community_world_overlay_config_defaults()
            s.setValue(
                COMMUNITY_WORLD_OVERLAY_CONFIG_QSETTINGS_KEY,
                community_world_overlay_config_to_json_text(cfg),
            )
            return cfg
        return community_world_overlay_config_defaults()


def save_community_world_overlay_config(
    cfg: CommunityWorldOverlayConfig,
    settings: QSettings | None = None,
) -> None:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    txt = community_world_overlay_config_to_json_text(cfg)
    s.setValue(COMMUNITY_WORLD_OVERLAY_CONFIG_QSETTINGS_KEY, txt)
    s.setValue(_COMMUNITY_WORLD_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY, txt)
    s.sync()
