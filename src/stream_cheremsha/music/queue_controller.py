from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from stream_cheremsha.music.models import Track


@dataclass(slots=True)
class MusicQueueConfig:
    autoplay_muted: bool = False
    max_queue_items: int = 20


class MusicQueueController:
    """In-app music queue (no overlay playback).

    A separate player service consumes the queue and plays audio locally (yt-dlp).
    """

    def __init__(
        self,
        *,
        instance: str = "main",
        config: MusicQueueConfig | None = None,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        self._instance = (instance or "main").strip() or "main"
        self._config = config or MusicQueueConfig()
        self._lock = asyncio.Lock()
        self._changed = asyncio.Condition()
        self._queue: list[Track] = []
        self._current: Track | None = None
        self._loop = loop  # optional for external scheduling helpers

    @property
    def loop(self) -> asyncio.AbstractEventLoop | None:
        return self._loop

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def _now_iso(self) -> str:
        return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")

    def snapshot_state(self) -> dict[str, Any]:
        qcap = max(0, int(self._config.max_queue_items))
        q = self._queue[:qcap] if qcap else []
        return {
            "current": self._track_to_json(self._current),
            "queue": [self._track_to_json(t) for t in q],
            "config": {
                "autoplay_muted": bool(self._config.autoplay_muted),
                "max_queue_items": int(self._config.max_queue_items),
            },
        }

    @staticmethod
    def _track_to_json(t: Track | None) -> dict[str, Any] | None:
        if t is None:
            return None
        return {
            "id": t.id,
            "video_id": t.video_id,
            "requested_by": t.requested_by,
            "requested_at_iso": t.requested_at_iso,
            "title": t.title,
        }

    async def set_track_title(self, track_id: str, title: str) -> bool:
        tid = (track_id or "").strip()
        if not tid:
            return False
        t2 = (title or "").strip()
        async with self._lock:
            if self._current is not None and self._current.id == tid:
                self._current = Track(
                    id=self._current.id,
                    video_id=self._current.video_id,
                    requested_by=self._current.requested_by,
                    requested_at_iso=self._current.requested_at_iso,
                    title=t2,
                )
                await self._notify_changed()
                return True
            for i, tr in enumerate(self._queue):
                if tr.id == tid:
                    self._queue[i] = Track(
                        id=tr.id,
                        video_id=tr.video_id,
                        requested_by=tr.requested_by,
                        requested_at_iso=tr.requested_at_iso,
                        title=t2,
                    )
                    await self._notify_changed()
                    return True
        return False

    async def wait_changed(self) -> None:
        async with self._changed:
            await self._changed.wait()

    async def _notify_changed(self) -> None:
        async with self._changed:
            self._changed.notify_all()

    async def enqueue(self, *, video_id: str, requested_by: str) -> Track:
        v = (video_id or "").strip()
        rb = (requested_by or "").strip() or "?"
        tr = Track(
            id=str(uuid.uuid4()),
            video_id=v,
            requested_by=rb,
            requested_at_iso=self._now_iso(),
        )
        async with self._lock:
            if self._current is None:
                self._current = tr
            else:
                self._queue.append(tr)
        await self._notify_changed()
        return tr

    async def skip(self) -> None:
        async with self._lock:
            self._advance_locked()
        await self._notify_changed()

    async def remove_at(self, index: int) -> Track | None:
        async with self._lock:
            if index < 0 or index >= len(self._queue):
                return None
            tr = self._queue.pop(index)
        await self._notify_changed()
        return tr

    async def remove_by_id(self, track_id: str) -> Track | None:
        tid = (track_id or "").strip()
        if not tid:
            return None
        async with self._lock:
            for i, tr in enumerate(self._queue):
                if tr.id == tid:
                    out = self._queue.pop(i)
                    break
            else:
                return None
        await self._notify_changed()
        return out

    async def list_queue(self, limit: int = 20) -> tuple[Track | None, list[Track]]:
        lim = max(0, int(limit))
        async with self._lock:
            q = self._queue[:lim] if lim else []
            return (self._current, list(q))

    async def current_track(self) -> Track | None:
        async with self._lock:
            return self._current

    def _advance_locked(self) -> None:
        if self._queue:
            self._current = self._queue.pop(0)
        else:
            self._current = None
