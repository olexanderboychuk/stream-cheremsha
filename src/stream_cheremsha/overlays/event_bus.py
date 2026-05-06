from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class _Sub:
    topic: str
    q: asyncio.Queue[dict[str, Any]]


class OverlayEventBus:
    """In-process event fanout for overlay -> server -> app control messages.

    Unlike OverlayPubSub (patches), events flow from the overlay client to the app.
    """

    def __init__(self) -> None:
        self._subs: list[_Sub] = []

    def subscribe(self, topic: str, maxsize: int = 200) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=maxsize)
        self._subs.append(_Sub(topic=str(topic), q=q))
        return q

    def unsubscribe(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        self._subs = [s for s in self._subs if s.q is not q]

    def publish_nowait(self, topic: str, event: dict[str, Any]) -> None:
        payload = dict(event)
        for s in list(self._subs):
            if s.topic != topic:
                continue
            try:
                s.q.put_nowait(payload.copy())
            except asyncio.QueueFull:
                continue

