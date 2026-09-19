"""Sync manager (QObject).

Responsibilities:
- subscribe to CheremshaAuthState.statusChanged; kick the first pull when
  the user becomes authenticated
- debounce local changes (~1.5 s) and push to the cloud
- apply remote changes under a guard so they do NOT generate outbound ops
- expose ``syncState``, ``lastSyncedAt``, ``lastError``, ``conflictsJson`` to QML
- allow QML to call ``pullNow/pushNow/resolveConflict``
"""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
import time
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from stream_cheremsha.cloud.client import CloudApiError
from stream_cheremsha.sync import drive
from stream_cheremsha.sync.allowlist import (
    ALLOWLISTED_QSETTINGS_KEYS,
    SYNC_KIND_ACCOUNT_SETTINGS,
    SYNC_KIND_ACTIONS,
    SYNC_KIND_LAYOUTS,
    SYNC_KIND_WIDGET,
    is_audio_key,
    redact_dangerous_blob,
)
from stream_cheremsha.sync.queue import PendingChange, SyncQueue

logger = logging.getLogger(__name__)

DEVICE_ID_PATH = "/tmp/cheremsha-desktop-device-id"  # not used; see _get_or_create_device_id

_STATE_IDLE = "idle"
_STATE_PULLING = "pulling"
_STATE_PUSHING = "pushing"
_STATE_OFFLINE = "offline"
_STATE_ERROR = "error"
_STATE_CONFLICT = "conflict"


class CheremshaSyncManager(QObject):
    syncStateChanged = Signal()
    lastSyncedAtChanged = Signal()
    lastErrorChanged = Signal()
    conflictsChanged = Signal()
    pendingSizeChanged = Signal()

    def __init__(
        self,
        auth: QObject,
        network_post: Any,
        network_get: Any,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._auth = auth
        self._post = network_post
        self._get = network_get
        self._state = _STATE_IDLE
        self._last_synced_at = ""
        self._last_error = ""
        self._conflicts: list[dict] = []
        self._pending_size = 0
        self._device_id = _get_or_create_device_id()
        self._cursor = ""
        self._task: asyncio.Task | None = None
        self._debounce: float = 1.5
        self._queue = SyncQueue()
        # Updated base_version cache for the next push (per entity).
        self._base_versions: dict[tuple[str, str], int] = {}
        try:
            auth.statusChanged.connect(self._on_auth_status)  # type: ignore[union-attr]
        except Exception:
            logger.debug("auth statusChanged unavailable (test fixture?); skipping wiring")

        self._refresh_state()

    # -- Qt properties ----------------------------------------------------
    def _get_state_prop(self) -> str:  # noqa: D401
        return self._state

    syncState = Property(str, _get_state_prop, notify=syncStateChanged)

    def _get_last_synced(self) -> str:
        return self._last_synced_at

    lastSyncedAt = Property(str, _get_last_synced, notify=lastSyncedAtChanged)

    def _get_last_error(self) -> str:
        return self._last_error

    lastError = Property(str, _get_last_error, notify=lastErrorChanged)

    def _get_pending_size(self) -> int:
        return self._queue.size()

    pendingSize = Property(int, _get_pending_size, notify=pendingSizeChanged)

    def _get_conflicts(self) -> str:
        return json.dumps(self._conflicts, ensure_ascii=False)

    conflictsJson = Property(str, _get_conflicts, notify=conflictsChanged)

    # -- public slots -----------------------------------------------------
    @Slot()
    def pullNow(self) -> None:  # noqa: N802
        self._trigger_loop(reason="pull-now")

    @Slot()
    def pushNow(self) -> None:  # noqa: N802
        self._trigger_loop(reason="push-now")

    @Slot(int, str)
    def resolveConflict(self, idx: int, choice: str) -> None:
        """Resolve a pending conflict by ``choice`` = 'local' or 'remote'.
        For V1 we only acknowledge; the conflict stays serialised for the
        user to fix in the Settings UI."""
        if choice not in ("local", "remote"):
            return
        if not (0 <= int(idx) < len(self._conflicts)):
            return
        item = self._conflicts[int(idx)]
        kind = str(item.get("kind") or "")
        entity_id = str(item.get("entity_id") or "")
        if not kind or not entity_id:
            return
        if choice == "local":
            # Re-queue with a forced overwrite (base_version=current
            # server's ``server_base_version`` would be safer; for V1 we
            # push with base_version=0 so the server will surface the
            # conflict again until the user explicitly accepts remote).
            self._queue.enqueue(
                kind=kind,
                entity_id=entity_id,
                op="upsert",
                base_version=0,
                data=item.get("local_data") or item.get("data") or {},
            )
        self._conflicts.pop(int(idx))
        self.conflictsChanged.emit()
        self._refresh_state()
        if choice == "remote":
            self._trigger_loop(reason="apply-remote")

    # -- enqueue hooks (called from storage layers) -----------------------
    def enqueue_widget_change(self, inst_id: str, data: dict, *, base_version: int = 0) -> None:
        if drive.is_remote_applying():
            return  # loop prevention
        if not inst_id:
            return
        safe = redact_dangerous_blob(data or {})
        self._queue.enqueue(
            kind=SYNC_KIND_WIDGET,
            entity_id=inst_id,
            op="upsert",
            base_version=base_version,
            data=safe,
        )
        self._schedule_debounced_push()

    def enqueue_actions_change(self, entity_id: str, data: dict, *, base_version: int = 0) -> None:
        if drive.is_remote_applying():
            return
        if not entity_id:
            return
        safe = redact_dangerous_blob(data or {})
        self._queue.enqueue(
            kind=SYNC_KIND_ACTIONS,
            entity_id=entity_id,
            op="upsert",
            base_version=base_version,
            data=safe,
        )
        self._schedule_debounced_push()

    def enqueue_settings_change(self, key: str, value: Any, *, base_version: int = 0) -> None:
        """Collected by the manager: settings are coalesced into a single
        ``account_settings`` blob on push."""
        if drive.is_remote_applying():
            return
        if not key or is_audio_key(key):
            return
        if key not in ALLOWLISTED_QSETTINGS_KEYS:
            return  # explicitly NOT synced; also blocks tokens/audio/etc.
        # We do not enqueue per-key entries; instead we rely on the
        # next push to gather the full blob via ``drive.collect_account_settings``.
        # This still prevents the loop: any local write triggers a debounced push.
        self._schedule_debounced_push()

    def enqueue_layouts_change(self, entity_id: str, data: dict) -> None:
        if drive.is_remote_applying():
            return
        safe = redact_dangerous_blob(data or {})
        self._queue.enqueue(
            kind=SYNC_KIND_LAYOUTS,
            entity_id=entity_id,
            op="upsert",
            base_version=0,
            data=safe,
        )
        self._schedule_debounced_push()

    # -- status hookups ---------------------------------------------------
    def _on_auth_status(self, new_status: str) -> None:
        if new_status == "authenticated":
            self._trigger_loop(reason="login")

    # -- internal ---------------------------------------------------------
    def _refresh_state(self) -> None:
        if self._last_error:
            self._state = _STATE_ERROR if self._conflicts else _STATE_ERROR
        if self._conflicts:
            self._state = _STATE_CONFLICT
        if self._queue.size() > 0 and self._state == _STATE_IDLE:
            self._state = _STATE_PUSHING
        self.syncStateChanged.emit()
        self.pendingSizeChanged.emit()

    def _schedule_debounced_push(self) -> None:
        # Single shared task: cancel any prior and re-schedule.
        if self._task is not None and not self._task.done():
            # Do NOT cancel mid-flight: we wait for it to finish.
            return
        try:
            self._task = asyncio.get_event_loop().create_task(self._debounced_loop())
        except RuntimeError:
            # No running loop yet (during tests). Caller will push manually.
            pass

    async def _debounced_loop(self) -> None:
        await asyncio.sleep(self._debounce)
        if not is_authenticated(self._auth):
            return
        await self._do_push()

    def _trigger_loop(self, *, reason: str) -> None:
        logger.debug("sync trigger: %s", reason)
        try:
            self._task = asyncio.get_event_loop().create_task(self._sync_loop())
        except RuntimeError:
            pass

    async def _sync_loop(self) -> None:
        if not is_authenticated(self._auth):
            return
        await self._do_pull(apply=True)
        if self._queue.size() > 0:
            await self._do_push()

    async def _do_push(self) -> None:
        if not is_authenticated(self._auth):
            self._state = _STATE_OFFLINE
            self.syncStateChanged.emit()
            return
        pending = self._queue.drain()
        if not pending:
            return
        # Always include the latest account-settings snapshot to coalesce.
        snap = drive.collect_account_settings(ALLOWLISTED_QSETTINGS_KEYS)
        snap = redact_dangerous_blob(snap)
        if snap:
            pending.insert(
                0,
                PendingChange(
                    kind=SYNC_KIND_ACCOUNT_SETTINGS,
                    entity_id="default",
                    op="upsert",
                    base_version=self._base_versions.get(
                        (SYNC_KIND_ACCOUNT_SETTINGS, "default"), 0
                    ),
                    data=snap,
                    ts=time.time(),
                ),
            )
        try:
            resp = await self._post(
                {
                    "device_id": self._device_id,
                    "cursor": self._cursor,
                    "changes": [_serialise_change(c) for c in pending],
                }
            )
        except CloudApiError as exc:
            # Re-enqueue with the same versions (next tick will retry).
            self._queue.replace_with(
                sorted(
                    [*pending, *self._queue.peek()],
                    key=lambda c: c.ts,
                )
            )
            self._last_error = f"push: {exc}"
            self._state = _STATE_ERROR
            self.lastErrorChanged.emit()
            self.syncStateChanged.emit()
            return
        except Exception as exc:
            self._last_error = f"push: {type(exc).__name__}"
            self._state = _STATE_ERROR
            self.lastErrorChanged.emit()
            self.syncStateChanged.emit()
            return

        # Update server-known base versions for accepted items.
        for res in resp.get("accepted", []):
            kind = str(res.get("kind") or "")
            entity_id = str(res.get("entity_id") or "")
            if res.get("version") is not None:
                self._base_versions[(kind, entity_id)] = int(res["version"])

        # Re-enqueue conflicts with their server base_version so the
        # user can retry after explicit compare/resolve.
        for conflict in resp.get("conflicts", []):
            self._queue.enqueue(
                kind=str(conflict.get("kind") or ""),
                entity_id=str(conflict.get("entity_id") or ""),
                op="upsert",
                base_version=int(conflict.get("server_base_version") or 0),
                data=self._find_pending_data(
                    pending,
                    str(conflict.get("kind") or ""),
                    str(conflict.get("entity_id") or ""),
                ),
            )
            self._conflicts.append(
                {
                    "kind": conflict.get("kind"),
                    "entity_id": conflict.get("entity_id"),
                    "local_data": self._find_pending_data(
                        pending,
                        str(conflict.get("kind") or ""),
                        str(conflict.get("entity_id") or ""),
                    ),
                    "server_data": conflict.get("server_data") or {},
                }
            )

        self._cursor = str(resp.get("cursor") or self._cursor or "")
        self._conflicts_changed()
        self._last_synced_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
        self.lastSyncedAtChanged.emit()
        self._last_error = ""
        self._state = _STATE_IDLE
        self.syncStateChanged.emit()
        self.pendingSizeChanged.emit()

    async def _do_pull(self, *, apply: bool) -> None:
        if not is_authenticated(self._auth):
            return
        try:
            # Pull = a push with zero changes.
            resp = await self._post(
                {
                    "device_id": self._device_id,
                    "cursor": self._cursor,
                    "changes": [],
                }
            )
        except CloudApiError as exc:
            self._last_error = f"pull: {exc}"
            self._state = _STATE_ERROR
            self.lastErrorChanged.emit()
            self.syncStateChanged.emit()
            return
        except Exception as exc:
            self._last_error = f"pull: {type(exc).__name__}"
            self._state = _STATE_ERROR
            self.lastErrorChanged.emit()
            self.syncStateChanged.emit()
            return

        if apply:
            self._apply_remote_changes(resp.get("remote_changes", []))
        for change in resp.get("remote_changes", []):
            kind = str(change.get("kind") or "")
            entity_id = str(change.get("entity_id") or "")
            if change.get("version") is not None:
                self._base_versions[(kind, entity_id)] = int(change["version"])
        self._cursor = str(resp.get("cursor") or self._cursor or "")
        self._last_synced_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
        self.lastSyncedAtChanged.emit()
        self._last_error = ""
        self._state = _STATE_IDLE
        self.syncStateChanged.emit()
        self.pendingSizeChanged.emit()

    def _apply_remote_changes(self, changes: list[dict]) -> None:
        with drive.begin_remote_apply():
            for change in changes:
                kind = str(change.get("kind") or "")
                entity_id = str(change.get("entity_id") or "")
                data = change.get("data") or {}
                op = str(change.get("op") or "upsert")
                if op == "delete":
                    continue
                try:
                    if kind == SYNC_KIND_WIDGET:
                        drive.apply_widget_change(
                            {"kind": kind, "entity_id": entity_id, "op": op, "data": data}
                        )
                    elif kind == SYNC_KIND_ACTIONS:
                        drive.apply_actions_change(
                            {"kind": kind, "entity_id": entity_id, "op": op, "data": data}
                        )
                    elif kind == SYNC_KIND_ACCOUNT_SETTINGS:
                        drive.apply_account_settings(data, ALLOWLISTED_QSETTINGS_KEYS)
                except Exception as exc:
                    logger.debug("apply %s %s failed: %s", kind, entity_id, type(exc).__name__)

    def _find_pending_data(self, pending: list[PendingChange], kind: str, entity_id: str) -> dict:
        for item in pending:
            if item.kind == kind and item.entity_id == entity_id:
                return dict(item.data)
        return {}

    def _conflicts_changed(self) -> None:
        self.conflictsChanged.emit()


def _serialise_change(c: PendingChange) -> dict:
    return {
        "kind": c.kind,
        "entity_id": c.entity_id,
        "op": c.op,
        "base_version": c.base_version,
        "data": c.data,
    }


def _get_or_create_device_id() -> str:
    """A stable per-machine device identifier; never sent alongside tokens."""
    from PySide6.QtCore import QStandardPaths

    loc = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
    base = str(loc or "/tmp")
    try:
        path = f"{base}/stream-cheremsha/device-id"
        try:
            with open(path, encoding="utf-8") as f:
                value = f.read().strip()
                if value:
                    return value
        except FileNotFoundError:
            pass
        value = secrets.token_hex(16)
        import os as _os

        _os.makedirs(f"{base}/stream-cheremsha", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(value)
        return value
    except Exception:
        # Fallback in-memory id; it will not survive restart but the
        # protocol is still well-defined.
        return secrets.token_hex(16)


def is_authenticated(auth: QObject) -> bool:
    try:
        s = auth.status  # type: ignore[attr-defined]
        return s == "authenticated"
    except Exception:
        return False
