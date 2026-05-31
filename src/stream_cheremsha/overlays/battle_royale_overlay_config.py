from __future__ import annotations

import json
from dataclasses import dataclass, replace

from PySide6.QtCore import QSettings

BATTLE_ROYALE_OVERLAY_CONFIG_SCHEMA_VERSION = 1
BATTLE_ROYALE_OVERLAY_CONFIG_QSETTINGS_KEY = "overlays/battle_royale/main/config_json"
_BATTLE_ROYALE_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY = (
    "overlays/battle_royale/main/config_json_backup"
)

BATTLE_ROYALE_PRESETS = frozenset(("arcade_royale", "cyber_arena", "dark_fight", "minimal_brawl"))


@dataclass(frozen=True, slots=True)
class BattleRoyaleOverlayConfig:
    schema_version: int

    preset: str
    title_text: str
    max_hp: int
    round_duration_s: int
    countdown_s: int
    crit_threshold_diamonds: int
    crit_multiplier: float
    auto_arm_enabled: bool
    auto_threshold_each: int
    auto_window_s: int
    max_fighters: int
    gifts_per_fighter: int
    vip_chat_hours: int
    avatar_size_px: int
    font_family: str
    base_font_size_px: int
    anim_intensity_pct: int
    sfx_volume_pct: int

    hide_when_idle: bool
    anim_projectile: bool
    anim_shake: bool
    anim_crit_flash: bool
    anim_fatality: bool

    def replace(self, **kwargs: object) -> BattleRoyaleOverlayConfig:
        return replace(self, **kwargs)


def battle_royale_overlay_config_defaults() -> BattleRoyaleOverlayConfig:
    return BattleRoyaleOverlayConfig(
        schema_version=BATTLE_ROYALE_OVERLAY_CONFIG_SCHEMA_VERSION,
        preset="arcade_royale",
        title_text="BATTLE ROYALE",
        max_hp=1000,
        round_duration_s=120,
        countdown_s=5,
        crit_threshold_diamonds=500,
        crit_multiplier=1.5,
        auto_arm_enabled=True,
        auto_threshold_each=100,
        auto_window_s=30,
        max_fighters=4,
        gifts_per_fighter=3,
        vip_chat_hours=1,
        avatar_size_px=110,
        font_family="Segoe UI",
        base_font_size_px=14,
        anim_intensity_pct=100,
        sfx_volume_pct=80,
        hide_when_idle=True,
        anim_projectile=True,
        anim_shake=True,
        anim_crit_flash=True,
        anim_fatality=True,
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


def _ensure_preset(v: object) -> str:
    s = str(v or "").strip().lower()
    if s in BATTLE_ROYALE_PRESETS:
        return s
    return "arcade_royale"


def _resolve_base_font_size_px(d: dict[str, object], *, defaults: BattleRoyaleOverlayConfig) -> int:
    raw = _ensure_int(d.get("base_font_size_px"), default=0)
    if raw > 0:
        return max(10, min(32, raw))
    pct = _ensure_int(d.get("text_scale_pct"), default=0)
    if pct > 0:
        return max(10, min(32, round(14 * pct / 100)))
    return defaults.base_font_size_px


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


def battle_royale_overlay_config_to_json_text(cfg: BattleRoyaleOverlayConfig) -> str:
    obj = {
        "schema_version": int(cfg.schema_version),
        "preset": str(cfg.preset),
        "title_text": str(cfg.title_text),
        "max_hp": int(cfg.max_hp),
        "round_duration_s": int(cfg.round_duration_s),
        "countdown_s": int(cfg.countdown_s),
        "crit_threshold_diamonds": int(cfg.crit_threshold_diamonds),
        "crit_multiplier": float(cfg.crit_multiplier),
        "auto_arm_enabled": bool(cfg.auto_arm_enabled),
        "auto_threshold_each": int(cfg.auto_threshold_each),
        "auto_window_s": int(cfg.auto_window_s),
        "max_fighters": int(cfg.max_fighters),
        "gifts_per_fighter": int(cfg.gifts_per_fighter),
        "vip_chat_hours": int(cfg.vip_chat_hours),
        "avatar_size_px": int(cfg.avatar_size_px),
        "font_family": str(cfg.font_family),
        "base_font_size_px": int(cfg.base_font_size_px),
        "anim_intensity_pct": int(cfg.anim_intensity_pct),
        "sfx_volume_pct": int(cfg.sfx_volume_pct),
        "hide_when_idle": bool(cfg.hide_when_idle),
        "anim_projectile": bool(cfg.anim_projectile),
        "anim_shake": bool(cfg.anim_shake),
        "anim_crit_flash": bool(cfg.anim_crit_flash),
        "anim_fatality": bool(cfg.anim_fatality),
    }
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def battle_royale_overlay_config_from_json_text(text: str) -> BattleRoyaleOverlayConfig:
    raw = json.loads(text)
    if not isinstance(raw, dict):
        raise ValueError("battle_royale overlay config must be a JSON object")
    d = raw
    defaults = battle_royale_overlay_config_defaults()
    return BattleRoyaleOverlayConfig(
        schema_version=_ensure_int(d.get("schema_version"), default=1),
        preset=_ensure_preset(d.get("preset")),
        title_text=str(d.get("title_text") or defaults.title_text).strip() or defaults.title_text,
        max_hp=max(100, min(10000, _ensure_int(d.get("max_hp"), default=defaults.max_hp))),
        round_duration_s=max(30, min(600, _ensure_int(d.get("round_duration_s"), default=120))),
        countdown_s=max(1, min(30, _ensure_int(d.get("countdown_s"), default=5))),
        crit_threshold_diamonds=max(
            1, min(50000, _ensure_int(d.get("crit_threshold_diamonds"), default=500))
        ),
        crit_multiplier=max(1.0, min(5.0, _ensure_float(d.get("crit_multiplier"), default=1.5))),
        auto_arm_enabled=_ensure_bool(d.get("auto_arm_enabled"), default=True),
        auto_threshold_each=max(1, _ensure_int(d.get("auto_threshold_each"), default=100)),
        auto_window_s=max(5, min(120, _ensure_int(d.get("auto_window_s"), default=30))),
        max_fighters=max(2, min(4, _ensure_int(d.get("max_fighters"), default=4))),
        gifts_per_fighter=max(1, min(6, _ensure_int(d.get("gifts_per_fighter"), default=3))),
        vip_chat_hours=max(1, min(24, _ensure_int(d.get("vip_chat_hours"), default=1))),
        avatar_size_px=max(64, min(200, _ensure_int(d.get("avatar_size_px"), default=110))),
        font_family=str(d.get("font_family") or "Segoe UI").strip() or "Segoe UI",
        base_font_size_px=_resolve_base_font_size_px(d, defaults=defaults),
        anim_intensity_pct=max(25, min(200, _ensure_int(d.get("anim_intensity_pct"), default=100))),
        sfx_volume_pct=max(0, min(100, _ensure_int(d.get("sfx_volume_pct"), default=80))),
        hide_when_idle=_ensure_bool(d.get("hide_when_idle"), default=defaults.hide_when_idle),
        anim_projectile=_ensure_bool(d.get("anim_projectile"), default=True),
        anim_shake=_ensure_bool(d.get("anim_shake"), default=True),
        anim_crit_flash=_ensure_bool(d.get("anim_crit_flash"), default=True),
        anim_fatality=_ensure_bool(d.get("anim_fatality"), default=True),
    )


def load_battle_royale_overlay_config(
    settings: QSettings | None = None,
) -> BattleRoyaleOverlayConfig:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    raw = (s.value(BATTLE_ROYALE_OVERLAY_CONFIG_QSETTINGS_KEY, "", str) or "").strip()
    if not raw:
        return battle_royale_overlay_config_defaults()
    try:
        return battle_royale_overlay_config_from_json_text(raw)
    except (ValueError, TypeError, json.JSONDecodeError):
        bak = (s.value(_BATTLE_ROYALE_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY, "", str) or "").strip()
        if bak:
            try:
                cfg = battle_royale_overlay_config_from_json_text(bak)
            except (ValueError, TypeError, json.JSONDecodeError):
                return battle_royale_overlay_config_defaults()
            s.setValue(
                BATTLE_ROYALE_OVERLAY_CONFIG_QSETTINGS_KEY,
                battle_royale_overlay_config_to_json_text(cfg),
            )
            return cfg
        return battle_royale_overlay_config_defaults()


def save_battle_royale_overlay_config(
    cfg: BattleRoyaleOverlayConfig,
    settings: QSettings | None = None,
) -> None:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    txt = battle_royale_overlay_config_to_json_text(cfg)
    s.setValue(BATTLE_ROYALE_OVERLAY_CONFIG_QSETTINGS_KEY, txt)
    s.setValue(_BATTLE_ROYALE_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY, txt)
    s.sync()
