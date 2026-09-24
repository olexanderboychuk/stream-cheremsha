from __future__ import annotations

import json
from dataclasses import dataclass, replace

from PySide6.QtCore import QSettings

BATTLE_OVERLAY_CONFIG_SCHEMA_VERSION = 1
BATTLE_OVERLAY_CONFIG_QSETTINGS_KEY = "overlays/battle/main/config_json"
_BATTLE_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY = "overlays/battle/main/config_json_backup"

BATTLE_THEMES = frozenset({"cheremsha_neon", "cyber", "arcade", "minimal"})
BATTLE_LAYOUTS = frozenset({"normal", "compact"})


@dataclass(frozen=True, slots=True)
class BattleOverlayConfig:
    schema_version: int
    battle_name: str
    best_of: int
    round_duration_s: int
    countdown_s: int
    victory_display_s: int
    auto_start: bool
    auto_threshold_each: int
    auto_window_s: int
    auto_reset: bool
    auto_reset_delay_s: int
    gifts_enabled: bool
    gift_multiplier: float
    likes_enabled: bool
    likes_per_point: int
    follows_enabled: bool
    follow_points: int
    combo_enabled: bool
    combo_threshold: int
    combo_window_s: int
    combo_multiplier_step: float
    combo_max_multiplier: float
    comeback_enabled: bool
    comeback_threshold_pct: int
    close_threshold_pct: int
    theme: str
    layout_mode: str
    show_avatars: bool
    show_event_badges: bool
    show_winner_screen: bool
    event_animations: bool
    animation_intensity_pct: int
    scale_percent: int
    hide_when_idle: bool
    font_family: str
    base_font_size_px: int
    final_push_seconds: int
    decision_layer_enabled: bool

    def replace(self, **kwargs: object) -> BattleOverlayConfig:
        return replace(self, **kwargs)


def battle_overlay_config_defaults() -> BattleOverlayConfig:
    return BattleOverlayConfig(
        schema_version=BATTLE_OVERLAY_CONFIG_SCHEMA_VERSION,
        battle_name="BATTLE",
        best_of=3,
        round_duration_s=60,
        countdown_s=5,
        victory_display_s=8,
        auto_start=True,
        auto_threshold_each=100,
        auto_window_s=30,
        auto_reset=True,
        auto_reset_delay_s=10,
        gifts_enabled=True,
        gift_multiplier=1.0,
        likes_enabled=False,
        likes_per_point=100,
        follows_enabled=False,
        follow_points=10,
        combo_enabled=True,
        combo_threshold=5,
        combo_window_s=5,
        combo_multiplier_step=1.0,
        combo_max_multiplier=3.0,
        comeback_enabled=True,
        comeback_threshold_pct=20,
        close_threshold_pct=10,
        theme="cheremsha_neon",
        layout_mode="normal",
        show_avatars=True,
        show_event_badges=True,
        show_winner_screen=True,
        event_animations=True,
        animation_intensity_pct=100,
        scale_percent=100,
        hide_when_idle=False,
        font_family="Segoe UI",
        base_font_size_px=14,
        final_push_seconds=10,
        decision_layer_enabled=False,
    )


def _ensure_int(v: object, *, default: int) -> int:
    try:
        return int(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _ensure_float(v: object, *, default: float) -> float:
    try:
        f = float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    if f != f:  # NaN → default
        return default
    return f


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


def _ensure_theme(v: object) -> str:
    s = str(v or "").strip().lower()
    if s in BATTLE_THEMES:
        return s
    return "cheremsha_neon"


def _ensure_layout(v: object) -> str:
    s = str(v or "").strip().lower()
    if s in BATTLE_LAYOUTS:
        return s
    return "normal"


def battle_overlay_config_to_json_text(cfg: BattleOverlayConfig) -> str:
    obj = {
        "schema_version": int(cfg.schema_version),
        "battle_name": str(cfg.battle_name),
        "best_of": int(cfg.best_of),
        "round_duration_s": int(cfg.round_duration_s),
        "countdown_s": int(cfg.countdown_s),
        "victory_display_s": int(cfg.victory_display_s),
        "auto_start": bool(cfg.auto_start),
        "auto_threshold_each": int(cfg.auto_threshold_each),
        "auto_window_s": int(cfg.auto_window_s),
        "auto_reset": bool(cfg.auto_reset),
        "auto_reset_delay_s": int(cfg.auto_reset_delay_s),
        "gifts_enabled": bool(cfg.gifts_enabled),
        "gift_multiplier": float(cfg.gift_multiplier),
        "likes_enabled": bool(cfg.likes_enabled),
        "likes_per_point": int(cfg.likes_per_point),
        "follows_enabled": bool(cfg.follows_enabled),
        "follow_points": int(cfg.follow_points),
        "combo_enabled": bool(cfg.combo_enabled),
        "combo_threshold": int(cfg.combo_threshold),
        "combo_window_s": int(cfg.combo_window_s),
        "combo_multiplier_step": float(cfg.combo_multiplier_step),
        "combo_max_multiplier": float(cfg.combo_max_multiplier),
        "comeback_enabled": bool(cfg.comeback_enabled),
        "comeback_threshold_pct": int(cfg.comeback_threshold_pct),
        "close_threshold_pct": int(cfg.close_threshold_pct),
        "theme": str(cfg.theme),
        "layout_mode": str(cfg.layout_mode),
        "show_avatars": bool(cfg.show_avatars),
        "show_event_badges": bool(cfg.show_event_badges),
        "show_winner_screen": bool(cfg.show_winner_screen),
        "event_animations": bool(cfg.event_animations),
        "animation_intensity_pct": int(cfg.animation_intensity_pct),
        "scale_percent": int(cfg.scale_percent),
        "hide_when_idle": bool(cfg.hide_when_idle),
        "font_family": str(cfg.font_family),
        "base_font_size_px": int(cfg.base_font_size_px),
        "final_push_seconds": int(cfg.final_push_seconds),
        "decision_layer_enabled": bool(cfg.decision_layer_enabled),
    }
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def battle_overlay_config_from_json_text(text: str) -> BattleOverlayConfig:
    raw = json.loads(text)
    if not isinstance(raw, dict):
        raise ValueError("battle overlay config must be a JSON object")
    d = raw
    defaults = battle_overlay_config_defaults()
    best_of = _ensure_int(d.get("best_of"), default=3)
    if best_of not in (1, 3, 5):
        best_of = 3
    return BattleOverlayConfig(
        schema_version=_ensure_int(d.get("schema_version"), default=1),
        battle_name=str(d.get("battle_name") or defaults.battle_name).strip()
        or defaults.battle_name,
        best_of=best_of,
        round_duration_s=max(30, min(300, _ensure_int(d.get("round_duration_s"), default=60))),
        countdown_s=max(1, min(10, _ensure_int(d.get("countdown_s"), default=5))),
        victory_display_s=max(3, min(15, _ensure_int(d.get("victory_display_s"), default=8))),
        auto_start=_ensure_bool(d.get("auto_start"), default=True),
        auto_threshold_each=max(
            1, min(10000, _ensure_int(d.get("auto_threshold_each"), default=100))
        ),
        auto_window_s=max(5, min(120, _ensure_int(d.get("auto_window_s"), default=30))),
        auto_reset=_ensure_bool(d.get("auto_reset"), default=True),
        auto_reset_delay_s=max(5, min(60, _ensure_int(d.get("auto_reset_delay_s"), default=10))),
        gifts_enabled=_ensure_bool(d.get("gifts_enabled"), default=True),
        gift_multiplier=max(0.1, min(10.0, _ensure_float(d.get("gift_multiplier"), default=1.0))),
        likes_enabled=_ensure_bool(d.get("likes_enabled"), default=False),
        likes_per_point=max(1, min(10000, _ensure_int(d.get("likes_per_point"), default=100))),
        follows_enabled=_ensure_bool(d.get("follows_enabled"), default=False),
        follow_points=max(0, min(1000, _ensure_int(d.get("follow_points"), default=10))),
        combo_enabled=_ensure_bool(d.get("combo_enabled"), default=True),
        combo_threshold=max(2, min(20, _ensure_int(d.get("combo_threshold"), default=5))),
        combo_window_s=max(1, min(30, _ensure_int(d.get("combo_window_s"), default=5))),
        combo_multiplier_step=max(
            1.0, min(2.0, _ensure_float(d.get("combo_multiplier_step"), default=1.0))
        ),
        combo_max_multiplier=max(
            1.0, min(5.0, _ensure_float(d.get("combo_max_multiplier"), default=3.0))
        ),
        comeback_enabled=_ensure_bool(d.get("comeback_enabled"), default=True),
        comeback_threshold_pct=max(
            5, min(50, _ensure_int(d.get("comeback_threshold_pct"), default=20))
        ),
        close_threshold_pct=max(1, min(30, _ensure_int(d.get("close_threshold_pct"), default=10))),
        theme=_ensure_theme(d.get("theme")),
        layout_mode=_ensure_layout(d.get("layout_mode")),
        show_avatars=_ensure_bool(d.get("show_avatars"), default=True),
        show_event_badges=_ensure_bool(d.get("show_event_badges"), default=True),
        show_winner_screen=_ensure_bool(d.get("show_winner_screen"), default=True),
        event_animations=_ensure_bool(d.get("event_animations"), default=True),
        animation_intensity_pct=max(
            25, min(200, _ensure_int(d.get("animation_intensity_pct"), default=100))
        ),
        scale_percent=max(40, min(250, _ensure_int(d.get("scale_percent"), default=100))),
        hide_when_idle=_ensure_bool(d.get("hide_when_idle"), default=False),
        font_family=str(d.get("font_family") or "Segoe UI").strip() or "Segoe UI",
        base_font_size_px=max(10, min(32, _ensure_int(d.get("base_font_size_px"), default=14))),
        final_push_seconds=max(3, min(30, _ensure_int(d.get("final_push_seconds"), default=10))),
        decision_layer_enabled=_ensure_bool(d.get("decision_layer_enabled"), default=False),
    )


def load_battle_overlay_config(
    settings: QSettings | None = None,
) -> BattleOverlayConfig:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    raw = (s.value(BATTLE_OVERLAY_CONFIG_QSETTINGS_KEY, "", str) or "").strip()
    if not raw:
        return battle_overlay_config_defaults()
    try:
        return battle_overlay_config_from_json_text(raw)
    except (ValueError, TypeError, json.JSONDecodeError):
        bak = (s.value(_BATTLE_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY, "", str) or "").strip()
        if bak:
            try:
                cfg = battle_overlay_config_from_json_text(bak)
            except (ValueError, TypeError, json.JSONDecodeError):
                return battle_overlay_config_defaults()
            s.setValue(
                BATTLE_OVERLAY_CONFIG_QSETTINGS_KEY,
                battle_overlay_config_to_json_text(cfg),
            )
            return cfg
        return battle_overlay_config_defaults()


def save_battle_overlay_config(
    cfg: BattleOverlayConfig,
    settings: QSettings | None = None,
) -> None:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    txt = battle_overlay_config_to_json_text(cfg)
    s.setValue(BATTLE_OVERLAY_CONFIG_QSETTINGS_KEY, txt)
    s.setValue(_BATTLE_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY, txt)
    s.sync()


def battle_overlay_config_to_public_dict(cfg: BattleOverlayConfig) -> dict:
    import json as _json

    return _json.loads(battle_overlay_config_to_json_text(cfg))
