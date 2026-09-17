"""Persistent sync queue.

Atomic-write JSON file in ``QStandardPaths.AppLocalDataLocation/stream-cheremsha/sync-queue.json``.

Coalesces the same ``(kind, entity_id)`` so that a stream of edits
(e.g. ``tts/rate_percent = A → B → C``) keeps only the latest pending
operation, preserving the most-recent ``base_version`` for optimistic
concurrency.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

_PENDING_VERSION = 1


@dataclass(frozen=True, slots=True)
class PendingChange:
    kind: str
    entity_id: str
    op: str  # "upsert" | "delete"
    base_version: int
    data: dict
    ts: float  # monotonic-ish; float seconds (time.time)


def _queue_path() -> Path:
    from PySide6.QtCore import QStandardPaths

    loc = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
    base = Path(loc or str(Path.home()))
    base.mkdir(parents=True, exist_ok=True)
    return base / "stream-cheremsha" / "sync-queue.json"


def _atomic_write_json(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    os.replace(tmp, path)


class SyncQueue:
    """Process-local mirror of the persisted queue JSON.

    All mutations hold an instance lock so concurrent enqueues (which we
    expect from the GUI thread vs. the background sync loop) stay
    consistent.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._path = self._safe_path()
        self._items: list[PendingChange] = []
        self._load()

    @staticmethod
    def _safe_path() -> Path | None:
        try:
            return _queue_path()
        except Exception as exc:
            logger.debug("sync queue path unavailable: %s", type(exc).__name__)
            return None

    # ---- load / persist --------------------------------------------------
    def _load(self) -> None:
        if self._path is None or not self._path.exists():
            return
        try:
            raw = self._path.read_text(encoding="utf-8")
        except OSError:
            return
        try:
            payload = json.loads(raw)
            items = payload.get("items") or []
            for item in items:
                self._items.append(
                    PendingChange(
                        kind=str(item.get("kind") or ""),
                        entity_id=str(item.get("entity_id") or ""),
                        op=str(item.get("op") or "upsert"),
                        base_version=int(item.get("base_version") or 0),
                        data=item.get("data") or {},
                        ts=float(item.get("ts") or 0.0),
                    )
                )
        except (ValueError, TypeError) as exc:
            logger.debug("sync queue load failed: %s; resetting", type(exc).__name__)
            self._items = []

    def _persist(self) -> None:
        if self._path is None:
            return
        try:
            _atomic_write_json(
                self._path,
                {"version": _PENDING_VERSION, "items": [asdict(c) for c in self._items]},
            )
        except Exception as exc:
            logger.debug("sync queue persist failed: %s", type(exc).__name__)

    # ---- public interface ----------------------------------------------
    def enqueue(
        self,
        *,
        kind: str,
        entity_id: str,
        op: str = "upsert",
        base_version: int = 0,
        data: dict | None = None,
    ) -> None:
        with self._lock:
            new_item = PendingChange(
                kind=kind,
                entity_id=entity_id,
                op=op,
                base_version=base_version,
                data=dict(data or {}),
                ts=__import__("time").time(),
            )
            # Coalesce: replace any existing entry for this (kind, entity_id).
            kept: list[PendingChange] = []
            for existing in self._items:
                if existing.kind == new_item.kind and existing.entity_id == new_item.entity_id:
                    continue
                kept.append(existing)
            kept.append(new_item)
            self._items = kept
            self._persist()

    def dequeue_many(self) -> list[PendingChange]:
        with self._lock:
            items = list(self._items)
            self._items = []
            self._persist()
        return items

    def drain(self) -> list[PendingChange]:
        """Pop on success.  Preserve ordering by ``ts`` for predictable push."""
        with self._lock:
            items = sorted(self._items, key=lambda c: c.ts)
            self._items = []
            self._persist()
        return items

    def size(self) -> int:
        with self._lock:
            return len(self._items)

    def replace_with(self, items: list[PendingChange]) -> None:
        with self._lock:
            self._items = items
            self._persist()

    def peek(self) -> list[PendingChange]:
        with self._lock:
            return list(self._items)


def reset_for_tests() -> None:
    p = SyncQueue._safe_path()
    if p is not None and p.exists():
        try:
            p.unlink()
        except OSError:
            pass
