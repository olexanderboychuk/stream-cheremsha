from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

_LOG = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class _Sub:
    topic: str
    q: asyncio.Queue[dict[str, Any]]


class OverlayPubSub:
    def __init__(self) -> None:
        self._subs: list[_Sub] = []

    def subscribe(self, topic: str, maxsize: int = 100) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=maxsize)
        self._subs.append(_Sub(topic=str(topic), q=q))
        return q

    def unsubscribe(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        self._subs = [s for s in self._subs if s.q is not q]

    async def publish(self, topic: str, patch: dict[str, Any]) -> None:
        self.publish_sync(topic, patch)

    def publish_sync(self, topic: str, patch: dict[str, Any]) -> None:
        """Put ``patch`` on subscriber queues immediately.

        GUI-thread safe; no event-loop deferral.
        """
        payload = dict(patch)
        for s in list(self._subs):
            if s.topic != topic:
                continue
            try:
                s.q.put_nowait(payload.copy())
            except asyncio.QueueFull:
                _LOG.warning("overlay pubsub: queue full topic=%s (patch dropped)", topic)
                continue
