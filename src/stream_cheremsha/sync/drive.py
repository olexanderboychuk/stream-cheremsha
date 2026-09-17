"""Desktop → Cloud sync: converts existing local persistence layers into
sync entities (push) and writes back remote changes into the same local
storage (pull).

Owns the "applying remote" guard so we never turn a remote writeback into
an outbound push (sync loop).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from PySide6.QtCore import QSettings

from stream_cheremsha.actions.models import (  # type: ignore
    ruleset_to_json_text,
)
from stream_cheremsha.actions.store import (
    DEFAULT_SETTINGS_APP,
    DEFAULT_SETTINGS_ORG,
    load_rules_bundle,
    save_rules_bundle,
)
from stream_cheremsha.overlays import widget_instances as widget_store

logger = logging.getLogger(__name__)

# The same QSettings scopes the app uses for normal configuration.
_APP_SCOPE = QSettings(DEFAULT_SETTINGS_ORG, DEFAULT_SETTINGS_APP)


class _RemoteApplyGuard:
    """Set True while a remote-server writeback is being applied locally."""

    def __init__(self) -> None:
        self._flag = False

    def __enter__(self) -> None:
        self._flag = True

    def __exit__(self, *exc) -> None:
        self._flag = False

    def open(self) -> _RemoteApplyGuard:
        self._flag = True
        return self

    def close(self) -> None:
        self._flag = False

    def active(self) -> bool:
        return self._flag


# Module-level singleton so ALL writers (legacy widgets callbacks, GUI
# hooks, restored widgets from sync) can check before enqueuing.
_applying_remote = _RemoteApplyGuard()


def is_remote_applying() -> bool:
    """Return True while a remote change is being applied locally.

    Hooks (widget store, actions store, settings wrappers) consult this
    flag before enqueueing a sync change so the same writeback does not
    create a new outbound sync operation.
    """
    return _applying_remote.active()


def begin_remote_apply() -> _RemoteApplyGuard:
    _applying_remote.open()
    return _applying_remote


def end_remote_apply() -> None:
    _applying_remote.close()


# ---------------------------------------------------------------- settings
def collect_account_settings(allow_list_keys: tuple[str, ...]) -> dict[str, Any]:
    """Read every allow-listed QSettings key for the AccountSettings
    entity. Only allow-listed keys are emitted; everything else is
    dropped (acts as a silent filter)."""
    out: dict[str, Any] = {}
    for key in allow_list_keys:
        try:
            v = _APP_SCOPE.value(key)
            if isinstance(v, str):
                try:
                    v = json.loads(v)
                except (ValueError, TypeError):
                    pass
            val = v
        except Exception:
            continue
        if val is None or val == "":
            continue
        out[key] = val
    return out


def apply_account_settings(data: dict[str, Any], allow_list_keys: tuple[str, ...]) -> None:
    """Restore the allow-listed AccountSettings on this device (pull path).
    Unrelated keys are untouched."""
    if not isinstance(data, dict):
        return
    for key in allow_list_keys:
        if key not in data:
            continue
        # Apply through the same QSettings the application reads from.
        _APP_SCOPE.setValue(key, data[key])
    _APP_SCOPE.sync()


# ---------------------------------------------------------------- widgets
def collect_widget_instances() -> list[dict]:
    """Serialize every widget instance for the cloud. UUIDs stay stable."""
    out: list[dict] = []
    for inst in widget_store.list_instances():
        out.append(
            {
                "kind": "widget",
                "entity_id": inst.id,
                "op": "upsert",
                "base_version": 0,
                "data": widget_instance_to_dict(inst),
            }
        )
    return out


def widget_instance_to_dict(inst: widget_store.WidgetInstance) -> dict:
    return {
        "id": inst.id,
        "type_id": inst.type_id,
        "name": inst.name,
        "settings": inst.settings or {},
        "enabled": inst.enabled,
        "created_at": inst.created_at,
        "updated_at": inst.updated_at,
        "legacy_key": inst.legacy_key,
    }


def apply_widget_change(change: dict) -> bool:
    """Apply a single widget change received from the cloud."""
    s = _settings_obj()
    if change.get("op") == "delete":
        try:
            widget_store.delete_instance(change["entity_id"], settings=s)
        except Exception:
            return False
        return True
    data = change.get("data") or {}
    if not isinstance(data, dict):
        return False
    inst_id = str(data.get("id") or change.get("entity_id") or "").strip()
    type_id = str(data.get("type_id") or "").strip()
    if not inst_id or not type_id:
        return False
    existing = widget_store.get_instance(inst_id, settings=s)
    if existing is None:
        # New from another device — adopt the existing UUID verbatim.
        new_inst = widget_store.WidgetInstance(
            id=inst_id,
            type_id=type_id,
            name=str(data.get("name") or widget_store.widget_type_name(type_id)),
            settings=data.get("settings") or {},
            enabled=bool(data.get("enabled", True)),
            legacy_key=data.get("legacy_key"),
            created_at=str(data.get("created_at") or widget_store._utcnow()),
            updated_at=str(data.get("updated_at") or widget_store._utcnow()),
        )
        widget_store.save_instances(
            [*widget_store.list_instances(settings=s), new_inst], settings=s
        )
        return True
    existing.name = str(data.get("name") or existing.name)
    existing.settings = data.get("settings") or existing.settings
    existing.enabled = bool(data.get("enabled", existing.enabled))
    existing.legacy_key = data.get("legacy_key", existing.legacy_key)
    existing.updated_at = str(data.get("updated_at") or widget_store._utcnow())
    # Re-save to persist the merged values; call list_instances to fetch a
    # fresh copy so the in-memory mutation is reflected on disk.
    merged = widget_store.list_instances(settings=s)
    for inst in merged:
        if inst.id == inst_id:
            inst.name = existing.name
            inst.settings = existing.settings
            inst.enabled = existing.enabled
            inst.legacy_key = existing.legacy_key
            inst.updated_at = existing.updated_at
            break
    widget_store.save_instances(merged, settings=s)
    return True


def _settings_obj() -> QSettings:
    return QSettings(DEFAULT_SETTINGS_ORG, DEFAULT_SETTINGS_APP)


# ---------------------------------------------------------------- actions
def collect_actions_bundles() -> list[dict]:
    """Serialize every per-(platform, account_key) actions bundle."""
    out: list[dict] = []
    scope = QSettings(DEFAULT_SETTINGS_ORG, DEFAULT_SETTINGS_APP)
    for platform in ("twitch", "tiktok", "kick", "youtube"):
        scope.beginGroup(f"actions/{platform}")
        try:
            keys = [k for k in scope.allKeys() if k.endswith("/rules_json")]
        finally:
            scope.endGroup()
        for k in keys:
            account_key = k[: -len("/rules_json")]
            rules, ui_layout = load_rules_bundle(platform, account_key)
            try:
                bundle_json = ruleset_to_json_text(rules, ui_layout=ui_layout)
            except Exception:
                continue
            try:
                bundle = json.loads(bundle_json)
            except ValueError:
                bundle = {"rules": [], "ui_layout": None}
            out.append(
                {
                    "kind": "actions",
                    "entity_id": f"{platform}:{account_key}",
                    "op": "upsert",
                    "base_version": 0,
                    "data": bundle,
                }
            )
    return out


def apply_actions_change(change: dict) -> bool:
    if change.get("op") == "delete":
        return False
    data = change.get("data") or {}
    if not isinstance(data, dict):
        return False
    entity_id = str(change.get("entity_id") or "").strip()
    if ":" not in entity_id:
        return False
    platform, account_key = entity_id.split(":", 1)
    rules = data.get("rules") or []
    ui_layout = data.get("ui_layout")
    try:
        save_rules_bundle(platform, account_key, rules, ui_layout)
    except Exception:
        return False
    return True
