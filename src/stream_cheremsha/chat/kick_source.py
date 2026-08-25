"""Kick chat source: outbound Pusher WebSocket -> coordinator + action events.

Combines the Pusher reader with chatroom resolution, normalization into
``ChatMessage``, and callback hooks for follows/subs/gifts (best-effort from
the unofficial channel actions). Official REST (viewers/auth) is wired by the
main window via ``kick_api``.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from stream_cheremsha import l10n
from stream_cheremsha.chat.kick_pusher import (
    KickChatroomResolveError,
    KickPusherClient,
    message_sender_avatar,
    message_sender_name,
    parse_iso_ts,
    resolve_chatroom_id,
)
from stream_cheremsha.domain.models import ChatMessage, ChatPlatform
from stream_cheremsha.pipeline.coordinator import StreamCoordinator

logger = logging.getLogger(__name__)


class KickSource:
    """Lifecycle wrapper around :class:`KickPusherClient` + chatroom resolution."""

    def __init__(
        self,
        coordinator: StreamCoordinator,
        on_status: Callable[[str], None],
        get_locale: Callable[[], str] | None = None,
        on_follow: Callable[[str, str], None] | None = None,
        on_sub: Callable[[str, int], None] | None = None,
        on_gift_sub: Callable[[str, int], None] | None = None,
        on_kick_gift: Callable[[str, int], None] | None = None,
    ) -> None:
        self._coordinator = coordinator
        self._on_status = on_status
        self._get_locale = get_locale or (lambda: l10n.DEFAULT_LOCALE)
        self._on_follow = on_follow
        self._on_sub = on_sub
        self._on_gift_sub = on_gift_sub
        self._on_kick_gift = on_kick_gift
        self._client: KickPusherClient | None = None
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._chatroom_id: int = 0

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self, channel: str, chatroom_id: int | None = None) -> None:
        await self.stop()
        self._running = True
        self._task = asyncio.create_task(
            self._run_until_stopped(channel, chatroom_id),
            name="kick-source",
        )

    async def _run_until_stopped(self, channel: str, chatroom_id: int | None) -> None:
        cid = int(chatroom_id) if chatroom_id else 0
        if cid <= 0:
            try:
                self._on_status("Kick: resolving chatroom…")
                cid = await resolve_chatroom_id(channel)
            except (KickChatroomResolveError, OSError, RuntimeError, ValueError) as exc:
                logger.warning("Kick chatroom resolve failed: %s", exc)
                self._on_status(f"Kick: chatroom resolve failed: {exc}")
                return
        self._chatroom_id = cid

        client = KickPusherClient(
            chatroom_id=cid,
            on_message=self._on_message,
            on_action=self._on_action,
            on_status=self._on_status,
            get_locale=self._get_locale,
        )
        self._client = client
        try:
            await client.start()
            while self._running:
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            raise
        finally:
            await client.stop()

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
        if self._client is not None:
            await self._client.stop()
            self._client = None
        self._on_status(l10n.tr(self._get_locale(), "kick.stopped"))

    async def _on_message(self, payload: dict[str, Any]) -> None:
        author = message_sender_name(payload)
        text = str(payload.get("content") or "").strip()
        if not text:
            return
        received_at = parse_iso_ts(payload.get("created_at")) or datetime.now(UTC)
        msg = ChatMessage(
            author=author,
            text=text,
            platform=ChatPlatform.KICK,
            received_at=received_at,
            author_avatar_url=message_sender_avatar(payload),
        )
        await self._coordinator.enqueue_chat(msg)

    async def _on_action(self, event: str, payload: dict[str, Any]) -> None:
        name = (event or "").lower()
        user = message_sender_name(payload)
        if "follow" in name:
            cb = self._on_follow
            if cb is not None:
                cb(user, "")
        elif "gift" in name:
            amount = _int_field(payload, ("amount", "kicks", "count"))
            if "sub" in name:
                cb = self._on_gift_sub
                if cb is not None:
                    cb(user, amount or 1)
            else:
                cb = self._on_kick_gift
                if cb is not None:
                    cb(user, amount)
        elif "sub" in name:
            duration = _int_field(payload, ("duration", "months"))
            cb = self._on_sub
            if cb is not None:
                cb(user, duration or 1)


def _int_field(payload: dict[str, Any], keys: tuple[str, ...]) -> int:
    for key in keys:
        try:
            return max(0, int(payload.get(key) or 0))
        except (TypeError, ValueError):
            continue
    return 0
