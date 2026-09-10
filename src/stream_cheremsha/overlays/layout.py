from __future__ import annotations

import copy
import json
import re
import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any, cast

from PySide6.QtCore import QSettings

LAYOUT_SCHEMA_VERSION = 1
LAYOUTS_QSETTINGS_KEY = "overlays/layouts/config_json"
_LAYOUTS_BACKUP_QSETTINGS_KEY = "overlays/layouts/config_json_backup"
_ACTIVE_LAYOUT_QSETTINGS_KEY = "overlays/layouts/active_id"
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
    # Optional WidgetInstance id (see overlays/widget_instances.py).
    # When set and resolvable, renderers/embeds address the instance
    # via /overlay/by-id/{id}; otherwise the legacy type+instance URL.
    widget_instance_id: str = ""

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


def _tr(key: str, **kwargs: object) -> str | None:
    try:
        from stream_cheremsha import l10n
        from stream_cheremsha.overlays.ui_locale import load_ui_locale

        return l10n.tr(load_ui_locale(), key, **kwargs)
    except (KeyError, ValueError, TypeError):
        return None


def layout_default_name() -> str:
    return _tr("widgets.layouts.default_name") or "Основна сцена"


def layout_new_name(n: int) -> str:
    return _tr("widgets.layouts.new_name", n=n) or f"Сцена {n}"


def layout_copy_suffix() -> str:
    return _tr("widgets.layouts.copy_suffix") or " Copy"


def default_layout() -> StreamLayout:
    return StreamLayout(
        id="default",
        name=layout_default_name(),
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
                "widget_instance_id": w.widget_instance_id,
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
        widget_instance_id = str(item.get("widget_instance_id") or "").strip()[:64]
        widgets.append(
            LayoutWidget(
                id=widget_id[:80],
                type=typ,
                instance=instance[:64],
                widget_instance_id=widget_instance_id,
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


def _layout_collection_items(raw: object) -> list[object]:
    """Return layout records from current and pre-collection payloads.

    The first layout editor stored one layout object directly.  The current
    format stores ``{"layouts": [...]}``; accepting both here keeps existing
    user data intact while ensuring the rest of the application only deals in
    the collection model.
    """
    if isinstance(raw, list):
        return raw
    if not isinstance(raw, dict):
        raise ValueError("Invalid layouts JSON")
    items = raw.get("layouts")
    if items is None:
        legacy = raw.get("layout")
        items = [legacy if legacy is not None else raw]
    if not isinstance(items, list):
        raise ValueError("Invalid layouts list")
    return cast(list[object], items)


def _parse_layout_collection(items: list[object]) -> list[StreamLayout]:
    result: list[StreamLayout] = []
    seen_ids: set[str] = set()
    for item in items:
        layout = layout_from_dict(item)
        # IDs are the object identity used by the selector and overlay URL.
        # Repair duplicate IDs during migration rather than allowing edits to
        # one object to replace another object with the same identity.
        if layout.id in seen_ids:
            layout = replace(layout, id=uuid.uuid4().hex)
        seen_ids.add(layout.id)
        result.append(layout)
    return result or [default_layout()]


def layouts_from_json_text(text: str) -> list[StreamLayout]:
    return _parse_layout_collection(_layout_collection_items(json.loads(text)))


def _load_and_migrate_layouts(text: str, settings: QSettings) -> list[StreamLayout]:
    layouts = layouts_from_json_text(text)
    # Rewrite legacy/sanitized payloads once. This migrates the former single
    # layout object to the canonical collection and makes repaired IDs stable.
    try:
        if json.loads(text) != json.loads(layouts_to_json_text(layouts)):
            save_layouts(layouts, settings)
    except (TypeError, json.JSONDecodeError):
        save_layouts(layouts, settings)
    if get_active_layout_id(settings) not in {layout.id for layout in layouts}:
        set_active_layout_id(layouts[0].id, settings)
    return layouts


def load_layouts(settings: QSettings | None = None) -> list[StreamLayout]:
    settings = settings or QSettings("stream-cheremsha", "cheremsha")
    text = str(settings.value(LAYOUTS_QSETTINGS_KEY, "", str) or "").strip()
    if not text:
        return [default_layout()]
    try:
        return _load_and_migrate_layouts(text, settings)
    except (ValueError, TypeError, json.JSONDecodeError):
        backup = str(settings.value(_LAYOUTS_BACKUP_QSETTINGS_KEY, "", str) or "").strip()
        try:
            return _load_and_migrate_layouts(backup, settings)
        except (ValueError, TypeError, json.JSONDecodeError):
            return [default_layout()]


def save_layouts(layouts: list[StreamLayout], settings: QSettings | None = None) -> None:
    settings = settings or QSettings("stream-cheremsha", "cheremsha")
    text = layouts_to_json_text(layouts)
    settings.setValue(LAYOUTS_QSETTINGS_KEY, text)
    settings.setValue(_LAYOUTS_BACKUP_QSETTINGS_KEY, text)
    settings.sync()


def _utcnow() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _new_layout_id() -> str:
    return uuid.uuid4().hex


def get_layout(layout_id: str, settings: QSettings | None = None) -> StreamLayout | None:
    ident = normalize_layout_id(str(layout_id or "default"))
    for layout in load_layouts(settings):
        if layout.id == ident:
            return layout
    return None


def upsert_layout(layout: StreamLayout, settings: QSettings | None = None) -> StreamLayout:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    layouts = load_layouts(s)
    layouts = [x for x in layouts if x.id != layout.id] + [layout]
    save_layouts(layouts, s)
    return layout


def create_layout(
    name: str = "", *, width: int = 1920, height: int = 1080, settings: QSettings | None = None
) -> StreamLayout:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    layouts = load_layouts(s)
    base = default_layout()
    layout = StreamLayout(
        id=_new_layout_id(),
        name=(str(name or "").strip() or layout_new_name(len(layouts) + 1))[:120],
        width=max(320, min(10000, int(width or 1920))),
        height=max(180, min(10000, int(height or 1080))),
        widgets=tuple(copy.deepcopy(base.widgets)),
    )
    layouts.append(layout)
    save_layouts(layouts, s)
    return layout


def rename_layout(
    layout_id: str, name: str, settings: QSettings | None = None
) -> StreamLayout | None:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    ident = normalize_layout_id(str(layout_id or "default"))
    changed: StreamLayout | None = None
    out: list[StreamLayout] = []
    for layout in load_layouts(s):
        if layout.id == ident:
            layout = StreamLayout(
                id=layout.id,
                name=(str(name or "").strip() or layout.name)[:120],
                width=layout.width,
                height=layout.height,
                widgets=layout.widgets,
                schema_version=layout.schema_version,
            )
            changed = layout
        out.append(layout)
    if changed is None:
        return None
    save_layouts(out, s)
    return changed


def duplicate_layout(layout_id: str, settings: QSettings | None = None) -> StreamLayout | None:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    ident = normalize_layout_id(str(layout_id or "default"))
    layouts = load_layouts(s)
    src = next((x for x in layouts if x.id == ident), None)
    if src is None:
        return None
    dup = StreamLayout(
        id=_new_layout_id(),
        name=f"{src.name}{layout_copy_suffix()}"[:120],
        width=src.width,
        height=src.height,
        widgets=tuple(copy.deepcopy(src.widgets)),
    )
    layouts.append(dup)
    save_layouts(layouts, s)
    return dup


def delete_layout(layout_id: str, settings: QSettings | None = None) -> bool:
    """Delete a layout; refuses to delete the last remaining one."""
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    ident = normalize_layout_id(str(layout_id or "default"))
    layouts = load_layouts(s)
    if len(layouts) <= 1:
        return False
    kept = [x for x in layouts if x.id != ident]
    if len(kept) == len(layouts):
        return False
    save_layouts(kept, s)
    if get_active_layout_id(s) == ident:
        set_active_layout_id(kept[0].id, s)
    return True


def ensure_layouts(settings: QSettings | None = None) -> list[StreamLayout]:
    """Persist the default layout when nothing is stored yet (idempotent)."""
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    raw = str(s.value(LAYOUTS_QSETTINGS_KEY, "", str) or "").strip()
    if raw:
        return load_layouts(s)
    layouts = [default_layout()]
    save_layouts(layouts, s)
    return layouts


def get_active_layout_id(settings: QSettings | None = None) -> str:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    try:
        return normalize_layout_id(
            str(s.value(_ACTIVE_LAYOUT_QSETTINGS_KEY, "default", str) or "default")
        )
    except ValueError:
        return "default"


def set_active_layout_id(layout_id: str, settings: QSettings | None = None) -> str:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    ident = normalize_layout_id(str(layout_id or "default"))
    s.setValue(_ACTIVE_LAYOUT_QSETTINGS_KEY, ident)
    s.sync()
    return ident


def resolve_active_layout(settings: QSettings | None = None) -> StreamLayout:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    layouts = ensure_layouts(s)
    active = get_active_layout_id(s)
    return next((x for x in layouts if x.id == active), layouts[0])
