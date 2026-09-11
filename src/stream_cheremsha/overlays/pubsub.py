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


def _route_patch(
    sub_topic: str, pub_topic: str, payload: dict[str, Any]
) -> tuple[bool, dict[str, Any] | None]:
    if sub_topic == pub_topic:
        return True, payload

    # Broadcast routing for overlay topics: overlay:{type}:{instance}
    parts = pub_topic.split(":")
    if len(parts) == 3 and parts[0] == "overlay":
        ov_type, target = parts[1], parts[2]
        sub_parts = sub_topic.split(":")
        if len(sub_parts) == 3 and sub_parts[0] == "overlay" and sub_parts[1] == ov_type:
            if target == "*":
                return True, payload
            if target == "main":
                # Deliver to other instances only if this is a stream/runtime event,
                # not a config-only update for 'main'.
                has_event_keys = any(k not in ("config", "timestamp") for k in payload)
                if has_event_keys:
                    # Strip singleton config so instance custom settings are preserved.
                    inst_payload = {k: v for k, v in payload.items() if k != "config"}
                    return True, inst_payload

    return False, None


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
            should_deliver, inst_payload = _route_patch(s.topic, topic, payload)
            if not should_deliver or inst_payload is None:
                continue
            try:
                s.q.put_nowait(inst_payload.copy())
            except asyncio.QueueFull:
                _LOG.warning("overlay pubsub: queue full topic=%s (patch dropped)", s.topic)
                continue
