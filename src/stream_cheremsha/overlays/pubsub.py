from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any


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

    async def publish(self, topic: str, patch: dict[str, Any]) -> None:
        payload = dict(patch)
        for s in list(self._subs):
            if s.topic != topic:
                continue
            try:
                s.q.put_nowait(payload.copy())
            except asyncio.QueueFull:
                continue
