"""Widget-Type -> Widget-Instance system.

Instances live in QSettings under ``overlays/widget_instances/config_json``.
Each instance is addressed only by its id (``/overlay/by-id/{id}``).
"""

from __future__ import annotations

import copy
import json
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from PySide6.QtCore import QSettings

_LOG = logging.getLogger(__name__)

INSTANCES_QSETTINGS_KEY = "overlays/widget_instances/config_json"
_INSTANCES_BACKUP_KEY = "overlays/widget_instances/config_json_backup"
SCHEMA_VERSION = 1

# type_id -> meta (display name, description, icon, platforms).
# platforms: list of "tiktok" | "twitch" | "kick" | "youtube" | "all".
# A widget may list several platforms; "all" means platform-agnostic.
# accent: card accent color (hex) for the shared CheremshaSourceCard.
# icon_svg: local SVG asset (relative to src/stream_cheremsha/assets/) used
#   by the shared card instead of the emoji `icon`.
WIDGET_TYPES: dict[str, dict[str, Any]] = {
    "chat": {
        "name": "Чат",
        "description": "Оверлей чату трансляції.",
        "icon": "💬",
        "icon_svg": "icons/web_multichat.svg",
        "accent": "#8b5cf6",
        "platforms": ["tiktok", "twitch", "kick", "youtube"],
    },
    "actions": {
        "name": "Дії та алерти",
        "description": "Алерти та дії.",
        "icon": "⚡",
        "icon_svg": "icons/web_bolt.svg",
        "accent": "#fb923c",
        "platforms": ["all"],
    },
    "activity": {
        "name": "Активність",
        "description": "Стрічка активності.",
        "icon": "📊",
        "icon_svg": "icons/web_activity.svg",
        "accent": "#f59e0b",
        "platforms": ["all"],
    },
    "online": {
        "name": "Онлайн / глядачі",
        "description": "Лічильник онлайну.",
        "icon": "👥",
        "icon_svg": "icons/web_online.svg",
        "accent": "#06b6d4",
        "platforms": ["all"],
    },
    "top_likers": {
        "name": "Топ лайкерів",
        "description": "Рейтинг користувачів за лайками.",
        "icon": "👍",
        "icon_svg": "icons/heart.svg",
        "accent": "#f472b6",
        "platforms": ["tiktok"],
    },
    "top_gifters": {
        "name": "Топ GIFтерів",
        "description": "Рейтинг користувачів за подарунками.",
        "icon": "🎁",
        "icon_svg": "icons/web_event_gift.svg",
        "accent": "#fb7185",
        "platforms": ["tiktok"],
    },
    "king_of_live": {
        "name": "King of the Live",
        "description": "Король ефіру.",
        "icon": "👑",
        "icon_svg": "icons/web_crown.svg",
        "accent": "#eab308",
        "platforms": ["tiktok"],
    },
    "battle_royale": {
        "name": "Battle Royale",
        "description": "Битва глядачів.",
        "icon": "⚔️",
        "icon_svg": "icons/web_swords.svg",
        "accent": "#ef4444",
        "platforms": ["tiktok"],
    },
    "stream_pet": {
        "name": "Stream Pet",
        "description": "Пет стріму.",
        "icon": "🐾",
        "icon_svg": "icons/web_paw.svg",
        "accent": "#10b981",
        "platforms": ["all"],
    },
    "community_world": {
        "name": "Community World",
        "description": "Світ спільноти.",
        "icon": "🏘️",
        "icon_svg": "icons/web_globe.svg",
        "accent": "#60a5fa",
        "platforms": ["all"],
    },
    "stream_goal": {
        "name": "Stream Goal",
        "description": "Ціль стріму.",
        "icon": "🎯",
        "icon_svg": "icons/web_target.svg",
        "accent": "#34d399",
        "platforms": ["all"],
    },
    "live_leaderboard": {
        "name": "Live Leaderboard",
        "description": "Живий лідерборд.",
        "icon": "🏆",
        "icon_svg": "icons/web_trophy.svg",
        "accent": "#a78bfa",
        "platforms": ["all"],
    },
    "social_rotator": {
        "name": "Social Rotator",
        "description": "Ротація соцмереж.",
        "icon": "🔄",
        "icon_svg": "icons/web_refresh.svg",
        "accent": "#38bdf8",
        "platforms": ["all"],
    },
    "webcam_frame": {
        "name": "Webcam Frame",
        "description": "Рамка камери (CAM/LINK).",
        "icon": "📷",
        "icon_svg": "icons/web_camera.svg",
        "accent": "#94a3b8",
        "platforms": ["all"],
    },
    "signal_system": {
        "name": "Signal System",
        "description": "Сигнальна система.",
        "icon": "📡",
        "icon_svg": "icons/web_signal.svg",
        "accent": "#2dd4bf",
        "platforms": ["all"],
    },
    "music": {
        "name": "Музика",
        "description": "Музичний оверлей.",
        "icon": "🎵",
        "icon_svg": "icons/web_music.svg",
        "accent": "#e879f9",
        "platforms": ["all"],
    },
}

_DEFAULTS_LOADERS: dict[str, str] = {
    "chat": "stream_cheremsha.overlays.chat_config:chat_config_defaults:chat_config_to_json_text",
    "actions": "stream_cheremsha.overlays.actions_config:actions_config_defaults:actions_config_to_json_text",
    "online": "stream_cheremsha.overlays.online_overlay_config:online_overlay_config_defaults:online_overlay_config_to_json_text",
    "top_likers": "stream_cheremsha.overlays.top_likers_overlay_config:top_likers_overlay_config_defaults:top_likers_overlay_config_to_json_text",
    "top_gifters": "stream_cheremsha.overlays.top_gifters_overlay_config:top_gifters_overlay_config_defaults:top_gifters_overlay_config_to_json_text",
    "king_of_live": "stream_cheremsha.overlays.king_of_live_overlay_config:king_of_live_overlay_config_defaults:king_of_live_overlay_config_to_json_text",
    "battle_royale": "stream_cheremsha.overlays.battle_royale_overlay_config:battle_royale_overlay_config_defaults:battle_royale_overlay_config_to_json_text",
    "stream_pet": "stream_cheremsha.overlays.stream_pet_overlay_config:stream_pet_overlay_config_defaults:stream_pet_overlay_config_to_json_text",
    "community_world": "stream_cheremsha.overlays.community_world_config:community_world_overlay_config_defaults:community_world_overlay_config_to_json_text",
    "stream_goal": "stream_cheremsha.overlays.stream_goal_overlay_config:stream_goal_overlay_config_defaults:stream_goal_overlay_config_to_json_text",
    "live_leaderboard": "stream_cheremsha.overlays.live_leaderboard_overlay_config:live_leaderboard_overlay_config_defaults:live_leaderboard_overlay_config_to_json_text",
    "social_rotator": "stream_cheremsha.overlays.social_rotator_overlay_config:social_rotator_overlay_config_defaults:social_rotator_overlay_config_to_json_text",
    "webcam_frame": "stream_cheremsha.overlays.webcam_frame_overlay_config:webcam_frame_overlay_config_defaults:webcam_frame_overlay_config_to_json_text",
    "signal_system": "stream_cheremsha.overlays.signal_system_overlay_config:signal_system_overlay_config_defaults:signal_system_overlay_config_to_json_text",
}


def widget_type_name(type_id: str) -> str:
    """Localized widget type display name (falls back to the registered one)."""
    try:
        from stream_cheremsha import l10n
        from stream_cheremsha.overlays.ui_locale import load_ui_locale

        return l10n.tr(load_ui_locale(), f"widgets.type.{type_id}.name")
    except (KeyError, ValueError, TypeError):
        return WIDGET_TYPES.get(type_id, {}).get("name", type_id)


def widget_type_desc(type_id: str) -> str:
    """Localized widget type short description (falls back to the registered one)."""
    try:
        from stream_cheremsha import l10n
        from stream_cheremsha.overlays.ui_locale import load_ui_locale

        return l10n.tr(load_ui_locale(), f"widgets.type.{type_id}.desc")
    except (KeyError, ValueError, TypeError):
        return WIDGET_TYPES.get(type_id, {}).get("description", "")


def _utcnow() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _new_id() -> str:
    return uuid.uuid4().hex


@dataclass(slots=True)
class WidgetInstance:
    id: str
    type_id: str
    name: str
    settings: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    created_at: str = field(default_factory=_utcnow)
    updated_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type_id": self.type_id,
            "name": self.name,
            "settings": copy.deepcopy(self.settings),
            "enabled": bool(self.enabled),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> WidgetInstance:
        return WidgetInstance(
            id=str(raw.get("id") or _new_id()),
            type_id=str(raw.get("type_id") or "").strip(),
            name=str(raw.get("name") or "").strip() or str(raw.get("type_id") or ""),
            settings=dict(raw.get("settings") or {}),
            enabled=bool(raw.get("enabled", True)),
            created_at=str(raw.get("created_at") or _utcnow()),
            updated_at=str(raw.get("updated_at") or _utcnow()),
        )


def _settings_obj(settings: QSettings | None) -> QSettings:
    return settings or QSettings("stream-cheremsha", "cheremsha")


def default_settings_for(type_id: str) -> dict[str, Any]:
    """Deep-copied defaults for a type; {} if type has no config module."""
    spec = _DEFAULTS_LOADERS.get(type_id)
    if not spec:
        return {}
    try:
        mod_name, defaults_fn, to_json_fn = spec.split(":")
        import importlib

        mod = importlib.import_module(mod_name)
        defaults_obj = getattr(mod, defaults_fn)()
        text = getattr(mod, to_json_fn)(defaults_obj)
        return json.loads(text)
    except Exception:
        return {}


def list_instances(settings: QSettings | None = None) -> list[WidgetInstance]:
    s = _settings_obj(settings)
    raw = str(s.value(INSTANCES_QSETTINGS_KEY, "", str) or "").strip()
    if not raw:
        return []
    try:
        blob = json.loads(raw)
        items = blob.get("instances", [])
        return [WidgetInstance.from_dict(x) for x in items if isinstance(x, dict)]
    except (ValueError, TypeError, json.JSONDecodeError):
        bak = str(s.value(_INSTANCES_BACKUP_KEY, "", str) or "").strip()
        try:
            blob = json.loads(bak)
            items = blob.get("instances", [])
            return [WidgetInstance.from_dict(x) for x in items if isinstance(x, dict)]
        except (ValueError, TypeError, json.JSONDecodeError):
            return []


def save_instances(instances: list[WidgetInstance], settings: QSettings | None = None) -> None:
    s = _settings_obj(settings)
    text = json.dumps(
        {"schema_version": SCHEMA_VERSION, "instances": [x.to_dict() for x in instances]},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    s.setValue(INSTANCES_QSETTINGS_KEY, text)
    s.setValue(_INSTANCES_BACKUP_KEY, text)
    s.sync()


def get_instance(instance_id: str, settings: QSettings | None = None) -> WidgetInstance | None:
    for inst in list_instances(settings):
        if inst.id == instance_id:
            return inst
    return None


def get_by_id(instance_id: str, settings: QSettings | None = None) -> WidgetInstance | None:
    token = (instance_id or '').strip()
    if not token:
        return None
    return get_instance(token, settings)


def merged_settings(inst: WidgetInstance) -> dict[str, Any]:
    """defaults + saved (saved wins). Never mutates stored state."""
    merged = default_settings_for(inst.type_id)
    merged.update(copy.deepcopy(inst.settings))
    return merged


def resolve_ws_params(
    type_id: str, instance: str, settings: QSettings | None = None
) -> dict[str, Any] | None:
    inst = get_by_id(instance, settings)
    if inst is None or inst.type_id != type_id:
        return None
    return merged_settings(inst)


def create_instance(
    type_id: str,
    name: str,
    settings_override: dict[str, Any] | None = None,
    settings: QSettings | None = None,
) -> WidgetInstance:
    s = _settings_obj(settings)
    instances = list_instances(s)
    cfg = default_settings_for(type_id)
    if settings_override:
        cfg.update(copy.deepcopy(settings_override))
    inst = WidgetInstance(
        id=_new_id(),
        type_id=type_id,
        name=(name or "").strip() or widget_type_name(type_id),
        settings=cfg,
    )
    instances.append(inst)
    save_instances(instances, s)
    return inst


def update_instance_settings(
    instance_id: str, new_settings: dict[str, Any], settings: QSettings | None = None
) -> WidgetInstance | None:
    s = _settings_obj(settings)
    instances = list_instances(s)
    for inst in instances:
        if inst.id == instance_id:
            inst.settings = copy.deepcopy(dict(new_settings))
            inst.updated_at = _utcnow()
            save_instances(instances, s)
            return inst
    return None


def set_instance_enabled(
    instance_id: str, enabled: bool, settings: QSettings | None = None
) -> WidgetInstance | None:
    s = _settings_obj(settings)
    instances = list_instances(s)
    for inst in instances:
        if inst.id == instance_id:
            inst.enabled = bool(enabled)
            inst.updated_at = _utcnow()
            save_instances(instances, s)
            return inst
    return None


def rename_instance(
    instance_id: str, name: str, settings: QSettings | None = None
) -> WidgetInstance | None:
    s = _settings_obj(settings)
    instances = list_instances(s)
    for inst in instances:
        if inst.id == instance_id:
            inst.name = (name or "").strip() or inst.name
            inst.updated_at = _utcnow()
            save_instances(instances, s)
            return inst
    return None


def _duplicate_name(base: str, taken: list[str]) -> str:
    """Numbered duplicate name: ``<base> 2``, ``<base> 3``, ..."""
    import re

    clean = re.sub(r"\s+(?:\d+|Copy|Копія)$", "", (base or "").strip(), flags=re.IGNORECASE) or base
    used = set(taken)
    n = 2
    while f"{clean} {n}" in used:
        n += 1
    return f"{clean} {n}"


def duplicate_instance(
    instance_id: str, settings: QSettings | None = None
) -> WidgetInstance | None:
    s = _settings_obj(settings)
    instances = list_instances(s)
    for inst in instances:
        if inst.id == instance_id:
            dup = WidgetInstance(
                id=_new_id(),
                type_id=inst.type_id,
                name=_duplicate_name(inst.name, [x.name for x in instances]),
                settings=copy.deepcopy(inst.settings),
                enabled=inst.enabled,
            )
            instances.append(dup)
            save_instances(instances, s)
            return dup
    return None


def delete_instance(instance_id: str, settings: QSettings | None = None) -> bool:
    s = _settings_obj(settings)
    instances = list_instances(s)
    kept = [x for x in instances if x.id != instance_id]
    if len(kept) == len(instances):
        return False
    save_instances(kept, s)
    return True


def typed_config_for_type(
    type_id: str,
    params: dict[str, Any],
    legacy_loader: Callable[[], Any],
    legacy_from_json_text: Callable[[str], Any],
) -> Any:
    """Renderer helper returning the typed config object.

    Prefers instance settings injected by the server (merged over defaults,
    then parsed through the legacy ``*_from_json_text`` so validation stays
    identical); falls back to the type singleton loader.
    """
    injected = params.get("instance_settings")
    if isinstance(injected, dict) and injected:
        defaults = default_settings_for(type_id)
        merged = dict(defaults)
        merged.update(copy.deepcopy(injected))
        try:
            return legacy_from_json_text(json.dumps(merged))
        except Exception:
            pass
    return legacy_loader()


def config_for_type(
    type_id: str,
    params: dict[str, Any],
    legacy_loader: Callable[[], Any],
    legacy_to_json: Callable[[Any], str],
) -> dict[str, Any]:
    """Renderer helper: prefers instance settings injected by server, else type defaults loader."""
    injected = params.get("instance_settings")
    if isinstance(injected, dict) and injected:
        defaults: dict[str, Any] = {}
        try:
            defaults = json.loads(legacy_to_json(legacy_loader()))
        except Exception:
            defaults = default_settings_for(type_id)
        out = dict(defaults)
        out.update(copy.deepcopy(injected))
        return out
    cfg = legacy_loader()
    try:
        return json.loads(legacy_to_json(cfg))
    except Exception:
        return {}
