from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from typing import Any

from PySide6.QtCore import QSettings

LAYOUT_SCHEMA_VERSION = 1
LAYOUTS_QSETTINGS_KEY = "overlays/layouts/config_json"
_LAYOUTS_BACKUP_QSETTINGS_KEY = "overlays/layouts/config_json_backup"
_LAYOUT_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$")

SUPPORTED_LAYOUT_WIDGETS = (
    "chat",
    "actions",
    "activity",
    "online",
    "top_likers",
    "top_gifters",
    "king_of_live",
    "battle_royale",
    "stream_pet",
    "community_world",
    "stream_goal",
    "live_leaderboard",
    "social_rotator",
    "webcam_frame",
    "music",
    "signal_system",
)


@dataclass(frozen=True, slots=True)
class LayoutWidget:
    id: str
    type: str
    instance: str
    x: int
    y: int
    width: int
    height: int
    z_index: int = 0
    visible: bool = True
    locked: bool = False

    def replace(self, **kwargs: object) -> LayoutWidget:
        return replace(self, **kwargs)


@dataclass(frozen=True, slots=True)
class StreamLayout:
    id: str
    name: str
    width: int
    height: int
    widgets: tuple[LayoutWidget, ...]
    schema_version: int = LAYOUT_SCHEMA_VERSION


def _int(value: object, default: int, minimum: int = 0, maximum: int = 10000) -> int:
    try:
        value = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, value))


def normalize_layout_id(value: str) -> str:
    value = str(value or "").strip()
    if not value:
        return "default"
    if not _LAYOUT_ID_RE.fullmatch(value):
        raise ValueError("Invalid layout id")
    return value


def default_layout() -> StreamLayout:
    return StreamLayout(
        id="default",
        name="Основна сцена",
        width=1920,
        height=1080,
        widgets=(
            LayoutWidget("chat-main", "chat", "main", 1450, 80, 420, 700, 10),
            LayoutWidget("actions-main", "actions", "main", 550, 820, 820, 180, 20),
        ),
    )


def layout_to_dict(layout: StreamLayout) -> dict[str, Any]:
    return {
        "schema_version": layout.schema_version,
        "id": layout.id,
        "name": layout.name,
        "width": layout.width,
        "height": layout.height,
        "widgets": [
            {
                "id": w.id,
                "type": w.type,
                "instance": w.instance,
                "x": w.x,
                "y": w.y,
                "width": w.width,
                "height": w.height,
                "z_index": w.z_index,
                "visible": w.visible,
                "locked": w.locked,
            }
            for w in layout.widgets
        ],
    }


def layout_from_dict(raw: object, *, layout_id: str | None = None) -> StreamLayout:
    if not isinstance(raw, dict):
        raise ValueError("Layout must be an object")
    ident = normalize_layout_id(str(layout_id or raw.get("id") or "default"))
    widgets: list[LayoutWidget] = []
    raw_widgets = raw.get("widgets", [])
    if not isinstance(raw_widgets, list):
        raise ValueError("Layout widgets must be a list")
    for index, item in enumerate(raw_widgets):
        if not isinstance(item, dict):
            continue
        typ = str(item.get("type") or "").strip()
        if typ not in SUPPORTED_LAYOUT_WIDGETS:
            continue
        widget_id = str(item.get("id") or f"{typ}-{index}").strip()
        instance = str(item.get("instance") or "main").strip() or "main"
        widgets.append(
            LayoutWidget(
                id=widget_id[:80],
                type=typ,
                instance=instance[:64],
                x=_int(item.get("x"), 0, 0, 10000),
                y=_int(item.get("y"), 0, 0, 10000),
                width=_int(item.get("width"), 320, 1, 10000),
                height=_int(item.get("height"), 180, 1, 10000),
                z_index=_int(item.get("z_index"), index, -10000, 10000),
                visible=bool(item.get("visible", True)),
                locked=bool(item.get("locked", False)),
            )
        )
    return StreamLayout(
        id=ident,
        name=str(raw.get("name") or ident)[:120],
        width=_int(raw.get("width"), 1920, 320, 10000),
        height=_int(raw.get("height"), 1080, 180, 10000),
        widgets=tuple(widgets),
        schema_version=LAYOUT_SCHEMA_VERSION,
    )


def layouts_to_json_text(layouts: list[StreamLayout]) -> str:
    return json.dumps(
        {"schema_version": LAYOUT_SCHEMA_VERSION, "layouts": [layout_to_dict(x) for x in layouts]},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def layouts_from_json_text(text: str) -> list[StreamLayout]:
    raw = json.loads(text)
    if not isinstance(raw, dict):
        raise ValueError("Invalid layouts JSON")
    items = raw.get("layouts", [])
    if not isinstance(items, list):
        raise ValueError("Invalid layouts list")
    result = [layout_from_dict(item) for item in items]
    return result or [default_layout()]


def load_layouts(settings: QSettings | None = None) -> list[StreamLayout]:
    settings = settings or QSettings("stream-cheremsha", "cheremsha")
    text = str(settings.value(LAYOUTS_QSETTINGS_KEY, "", str) or "").strip()
    if not text:
        return [default_layout()]
    try:
        return layouts_from_json_text(text)
    except (ValueError, TypeError, json.JSONDecodeError):
        backup = str(settings.value(_LAYOUTS_BACKUP_QSETTINGS_KEY, "", str) or "").strip()
        try:
            return layouts_from_json_text(backup)
        except (ValueError, TypeError, json.JSONDecodeError):
            return [default_layout()]


def save_layouts(layouts: list[StreamLayout], settings: QSettings | None = None) -> None:
    settings = settings or QSettings("stream-cheremsha", "cheremsha")
    text = layouts_to_json_text(layouts)
    settings.setValue(LAYOUTS_QSETTINGS_KEY, text)
    settings.setValue(_LAYOUTS_BACKUP_QSETTINGS_KEY, text)
    settings.sync()
