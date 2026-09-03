from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Any

from PySide6.QtCore import QSettings


STREAM_GOAL_OVERLAY_CONFIG_SCHEMA_VERSION = 1
STREAM_GOAL_OVERLAY_CONFIG_QSETTINGS_KEY = "overlays/stream_goal/main/config_json"
_STREAM_GOAL_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY = "overlays/stream_goal/main/config_json_backup"


@dataclass(frozen=True, slots=True)
class StreamGoalOverlayConfig:
    schema_version: int

    enabled: bool
    goal_type: str
    current_value: int
    target_value: int
    title: str
    subtitle: str

    skin: str
    accent_color: str
    animation_intensity: str
    scale_percent: int

    enable_event_animations: bool
    enable_combo: bool
    enable_milestones: bool
    enable_completion_animation: bool
    enable_glitch: bool
    enable_particles: bool
    enable_sound: bool

    milestones_json: str
    gift_coin_per_progress: int
    combo_window_sec: float
    reset_behavior: str
    next_target_value: int

    def replace(self, **kwargs: object) -> StreamGoalOverlayConfig:
        return replace(self, **kwargs)


def _default_milestones() -> list[dict[str, object]]:
    return [
        {"percent": 25, "label": "CORE ONLINE", "effect": "pulse"},
        {"percent": 50, "label": "ENERGY STABLE", "effect": "rings"},
        {"percent": 75, "label": "CRITICAL ENERGY", "effect": "arcs"},
        {"percent": 90, "label": "CONTAINMENT FAILURE", "effect": "glitch"},
        {"percent": 100, "label": "CORE BREACH", "effect": "explosion"},
    ]


def stream_goal_overlay_config_defaults() -> StreamGoalOverlayConfig:
    return StreamGoalOverlayConfig(
        schema_version=STREAM_GOAL_OVERLAY_CONFIG_SCHEMA_VERSION,
        enabled=True,
        goal_type="followers",
        current_value=0,
        target_value=10000,
        title="FOLLOW GOAL",
        subtitle="",
        skin="digital_core",
        accent_color="#00ffff",
        animation_intensity="medium",
        scale_percent=100,
        enable_event_animations=True,
        enable_combo=True,
        enable_milestones=True,
        enable_completion_animation=True,
        enable_glitch=True,
        enable_particles=True,
        enable_sound=False,
        milestones_json=json.dumps(_default_milestones(), ensure_ascii=False),
        gift_coin_per_progress=10,
        combo_window_sec=3.0,
        reset_behavior="after_completion",
        next_target_value=25000,
    )


def _ensure_int(v: object, *, default: int) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _ensure_float(v: object, *, default: float) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


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


def _ensure_str(v: object, *, default: str) -> str:
    s = str(v or "").strip()
    return s if s else default


def _ensure_hex_color(v: object, *, default: str) -> str:
    s = str(v or "").strip()
    if s.startswith("#") and len(s) in (4, 7, 9):
        return s
    return default


def _validate_goal_type(v: object) -> str:
    s = _ensure_str(v, default="followers")
    valid = {"followers", "likes", "gifts", "shares", "comments"}
    return s if s in valid else "followers"


def _validate_skin(v: object) -> str:
    s = _ensure_str(v, default="digital_core")
    valid = {"digital_core", "boss", "reactor", "rocket", "vault", "tower", "creature"}
    return s if s in valid else "digital_core"


def _validate_animation_intensity(v: object) -> str:
    s = _ensure_str(v, default="medium")
    valid = {"low", "medium", "high"}
    return s if s in valid else "medium"


def _validate_scale_percent(v: object) -> int:
    n = _ensure_int(v, default=100)
    return max(40, min(250, n))


def _validate_reset_behavior(v: object) -> str:
    s = _ensure_str(v, default="after_completion")
    valid = {"manual", "after_completion", "new_stream", "daily"}
    return s if s in valid else "after_completion"


def _validate_milestones_json(v: object) -> str:
    s = _ensure_str(v, default="")
    if not s:
        return json.dumps(_default_milestones(), ensure_ascii=False)
    try:
        parsed = json.loads(s)
        if not isinstance(parsed, list):
            return json.dumps(_default_milestones(), ensure_ascii=False)
        for m in parsed:
            if not isinstance(m, dict):
                return json.dumps(_default_milestones(), ensure_ascii=False)
            if "percent" not in m or "label" not in m:
                return json.dumps(_default_milestones(), ensure_ascii=False)
        return s
    except (json.JSONDecodeError, TypeError, ValueError):
        return json.dumps(_default_milestones(), ensure_ascii=False)


def stream_goal_overlay_config_from_json_text(text: str) -> StreamGoalOverlayConfig:
    raw = json.loads(text)
    if not isinstance(raw, dict):
        raise ValueError("stream_goal overlay config must be a JSON object")
    d = raw
    defaults = stream_goal_overlay_config_defaults()
    return StreamGoalOverlayConfig(
        schema_version=_ensure_int(d.get("schema_version"), default=defaults.schema_version),
        enabled=_ensure_bool(d.get("enabled"), default=defaults.enabled),
        goal_type=_validate_goal_type(d.get("goal_type")),
        current_value=max(0, _ensure_int(d.get("current_value"), default=defaults.current_value)),
        target_value=max(1, _ensure_int(d.get("target_value"), default=defaults.target_value)),
        title=_ensure_str(d.get("title"), default=defaults.title),
        subtitle=_ensure_str(d.get("subtitle"), default=defaults.subtitle),
        skin=_validate_skin(d.get("skin")),
        accent_color=_ensure_hex_color(d.get("accent_color"), default=defaults.accent_color),
        animation_intensity=_validate_animation_intensity(d.get("animation_intensity")),
        scale_percent=_validate_scale_percent(d.get("scale_percent")),
        enable_event_animations=_ensure_bool(d.get("enable_event_animations"), default=defaults.enable_event_animations),
        enable_combo=_ensure_bool(d.get("enable_combo"), default=defaults.enable_combo),
        enable_milestones=_ensure_bool(d.get("enable_milestones"), default=defaults.enable_milestones),
        enable_completion_animation=_ensure_bool(d.get("enable_completion_animation"), default=defaults.enable_completion_animation),
        enable_glitch=_ensure_bool(d.get("enable_glitch"), default=defaults.enable_glitch),
        enable_particles=_ensure_bool(d.get("enable_particles"), default=defaults.enable_particles),
        enable_sound=_ensure_bool(d.get("enable_sound"), default=defaults.enable_sound),
        milestones_json=_validate_milestones_json(d.get("milestones_json")),
        gift_coin_per_progress=max(1, _ensure_int(d.get("gift_coin_per_progress"), default=defaults.gift_coin_per_progress)),
        combo_window_sec=max(0.5, min(30.0, _ensure_float(d.get("combo_window_sec"), default=defaults.combo_window_sec))),
        reset_behavior=_validate_reset_behavior(d.get("reset_behavior")),
        next_target_value=max(1, _ensure_int(d.get("next_target_value"), default=defaults.next_target_value)),
    )


def stream_goal_overlay_config_to_public_dict(cfg: StreamGoalOverlayConfig) -> dict[str, object]:
    return {
        "schema_version": int(cfg.schema_version),
        "enabled": bool(cfg.enabled),
        "goal_type": str(cfg.goal_type),
        "current_value": int(cfg.current_value),
        "target_value": int(cfg.target_value),
        "title": str(cfg.title),
        "subtitle": str(cfg.subtitle),
        "skin": str(cfg.skin),
        "accent_color": str(cfg.accent_color),
        "animation_intensity": str(cfg.animation_intensity),
        "scale_percent": int(cfg.scale_percent),
        "enable_event_animations": bool(cfg.enable_event_animations),
        "enable_combo": bool(cfg.enable_combo),
        "enable_milestones": bool(cfg.enable_milestones),
        "enable_completion_animation": bool(cfg.enable_completion_animation),
        "enable_glitch": bool(cfg.enable_glitch),
        "enable_particles": bool(cfg.enable_particles),
        "enable_sound": bool(cfg.enable_sound),
        "milestones_json": str(cfg.milestones_json),
        "gift_coin_per_progress": int(cfg.gift_coin_per_progress),
        "combo_window_sec": float(cfg.combo_window_sec),
        "reset_behavior": str(cfg.reset_behavior),
        "next_target_value": int(cfg.next_target_value),
    }


def stream_goal_overlay_config_to_json_text(cfg: StreamGoalOverlayConfig) -> str:
    return json.dumps(
        stream_goal_overlay_config_to_public_dict(cfg),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def load_stream_goal_overlay_config(settings: QSettings | None = None) -> StreamGoalOverlayConfig:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    raw = (s.value(STREAM_GOAL_OVERLAY_CONFIG_QSETTINGS_KEY, "", str) or "").strip()
    if not raw:
        return stream_goal_overlay_config_defaults()
    try:
        return stream_goal_overlay_config_from_json_text(raw)
    except (ValueError, TypeError, json.JSONDecodeError):
        bak = (s.value(_STREAM_GOAL_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY, "", str) or "").strip()
        if bak:
            try:
                cfg = stream_goal_overlay_config_from_json_text(bak)
            except (ValueError, TypeError, json.JSONDecodeError):
                return stream_goal_overlay_config_defaults()
            s.setValue(
                STREAM_GOAL_OVERLAY_CONFIG_QSETTINGS_KEY, stream_goal_overlay_config_to_json_text(cfg)
            )
            return cfg
        return stream_goal_overlay_config_defaults()


def save_stream_goal_overlay_config(
    cfg: StreamGoalOverlayConfig,
    settings: QSettings | None = None,
) -> None:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    txt = stream_goal_overlay_config_to_json_text(cfg)
    s.setValue(STREAM_GOAL_OVERLAY_CONFIG_QSETTINGS_KEY, txt)
    s.setValue(_STREAM_GOAL_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY, txt)
    s.sync()