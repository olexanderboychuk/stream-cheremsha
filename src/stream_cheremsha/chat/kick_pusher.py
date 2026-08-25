"""Kick realtime chat over Kick's Pusher WebSocket (compatibility transport).

Kick's official API delivers events via webhooks (requires a public endpoint),
which a local desktop app cannot host. This module instead connects *outbound*
to Kick's Pusher WebSocket used by the Kick web client and subscribes to a
public ``chatrooms.{id}.v2`` channel. It requires no tunnel or public URL.

⚠️ This is an unofficial, reverse-engineered transport and may change or break
without notice. All protocol specifics are isolated here so the rest of the app
is unaffected if Kick changes them.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import aiohttp

from stream_cheremsha import l10n

logger = logging.getLogger(__name__)

# Pusher endpoint for Kick chat (from the Kick web client). No auth required.
PUSHER_URL = (
    "wss://ws-us2.pusher.com/app/32cbd69e4b950bf97679"
    "?protocol=7&client=js&version=8.4.0&flash=false"
)
# Kick v2 channel endpoint exposes ``chatroom.id`` (different from broadcaster id).
CHANNEL_INFO_URL = "https://kick.com/api/v2/channels/{slug}"

KICK_RECONNECT_SEC = 10.0
KICK_PING_INTERVAL_SEC = 30.0

# Events we care about on the chatroom channel. Kick chat messages are delivered
# under ``App\\Events\\ChatMessageEvent`` with a double-encoded ``data`` string.
CHAT_EVENT = "App\\Events\\ChatMessageEvent"

# Chatroom channel event that carries follows/subs/gifts (best-effort).
# Some rooms emit ``App\\Events\\ChatroomFollowEvent`` style payloads.
CHATROOM_ACTION_EVENTS = (
    "App\\Events\\ChatroomFollowEvent",
    "App\\Events\\ChatroomGiftEvent",
    "App\\Events\\ChatroomSubEvent",
)


class KickChatroomResolveError(RuntimeError):
    """Failed to resolve a Kick chatroom id from a channel slug."""


async def resolve_chatroom_id(
    slug: str,
    *,
    session: aiohttp.ClientSession | None = None,
    timeout: float = 20.0,
) -> int:
    """Resolve the Pusher chatroom id for a Kick channel slug.

    Uses Kick's unofficial ``/api/v2/channels/{slug}`` endpoint, which returns
    ``chatroom.id`` (a different number from the broadcaster id). Cloudflare
    protection may reject plain HTTP clients, so a browser-like User-Agent is
    sent; callers may retry after a short delay on failure.
    """
    url = CHANNEL_INFO_URL.format(slug=str(slug or "").strip().lstrip("@").strip())
    owns_session = session is None
    s = session or aiohttp.ClientSession()
    try:
        async with s.get(
            url,
            timeout=aiohttp.ClientTimeout(total=timeout),
            headers={
                "Accept": "application/json",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
                ),
            },
        ) as resp:
            if resp.status != 200:
                raise KickChatroomResolveError(
                    f"channel lookup failed ({resp.status}) for {slug}"
                )
            try:
                data = await resp.json(content_type=None)
            except (json.JSONDecodeError, ValueError) as exc:
                raise KickChatroomResolveError(f"invalid channel payload for {slug}") from exc
    finally:
        if owns_session:
            await s.close()

    chatroom = data.get("chatroom") if isinstance(data, dict) else None
    if not isinstance(chatroom, dict):
        raise KickChatroomResolveError(f"no chatroom data for {slug}")
    raw = chatroom.get("id")
    try:
        cid = int(raw)
    except (TypeError, ValueError) as exc:
        raise KickChatroomResolveError(f"bad chatroom id for {slug}: {raw!r}") from exc
    if cid <= 0:
        raise KickChatroomResolveError(f"invalid chatroom id for {slug}")
    return cid


def parse_pusher_envelope(raw: str) -> tuple[str, str | None, str]:
    """Parse a Pusher frame into ``(event, channel, data_str)``.

    Pusher frames are ``{"event": ..., "data": <string>, "channel": ...}`` where
    ``data`` is itself a JSON string. Raises ``ValueError`` on invalid JSON.
    """
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise ValueError("pusher frame is not an object")
    event = str(obj.get("event") or "")
    channel = obj.get("channel")
    channel = str(channel) if channel is not None else None
    data = obj.get("data")
    data_str = data if isinstance(data, str) else json.dumps(data)
    return event, channel, data_str


def parse_chat_message(data_str: str) -> dict[str, Any] | None:
    """Decode a chat message payload. Returns a dict or None if unparseable."""
    try:
        obj = json.loads(data_str)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    sender = obj.get("sender")
    content = obj.get("content")
    if not isinstance(content, str) or not isinstance(sender, dict):
        return None
    return obj


def message_sender_name(payload: dict[str, Any]) -> str:
    sender = payload.get("sender")
    if isinstance(sender, dict):
        for key in ("username", "slug"):
            v = sender.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return "?"


def message_sender_avatar(payload: dict[str, Any]) -> str:
    sender = payload.get("sender")
    if not isinstance(sender, dict):
        return ""
    for key in ("avatar", "profile_picture", "profile_picture_url"):
        v = sender.get(key)
        if isinstance(v, str) and (v.startswith("http://") or v.startswith("https://")):
            return v.strip()
    return ""


def parse_iso_ts(value: object) -> datetime | None:
    """Best-effort parse of an ISO-8601 timestamp to an aware datetime."""
    if not isinstance(value, str) or not value.strip():
        return None
    s = value.strip()
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


class KickPusherClient:
    """Outbound Pusher WebSocket reader for one Kick chatroom.

    Lifecycle is task-based with automatic reconnect. Callers subscribe via
    callback properties. This class never requires an inbound/public URL.
    """

    def __init__(
        self,
        *,
        chatroom_id: int,
        on_message: Callable[[dict[str, Any]], None] | None = None,
        on_action: Callable[[str, dict[str, Any]], None] | None = None,
        on_status: Callable[[str], None] | None = None,
        get_locale: Callable[[], str] | None = None,
    ) -> None:
        self._chatroom_id = int(chatroom_id)
        self._on_message = on_message
        self._on_action = on_action
        self._on_status = on_status
        self._get_locale = get_locale or (lambda: l10n.DEFAULT_LOCALE)
        self._session: aiohttp.ClientSession | None = None
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._channel = f"chatrooms.{self._chatroom_id}.v2"

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def _status(self, msg: str) -> None:
        cb = self._on_status
        if cb is not None:
            cb(msg)

    async def start(self) -> None:
        if self.running:
            return
        self._running = True
        self._session = aiohttp.ClientSession()
        self._task = asyncio.create_task(self._run(), name="kick-pusher")

    async def stop(self) -> None:
        self._running = False
        task, self._task = self._task, None
        if task is not None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        session, self._session = self._session, None
        if session is not None:
            await session.close()

    async def _run(self) -> None:
        backoff = KICK_RECONNECT_SEC
        while self._running:
            try:
                await self._connect_once()
                backoff = KICK_RECONNECT_SEC
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("Kick Pusher error: %s", exc)
                self._status(f"Kick: {exc}")
            if not self._running:
                break
            try:
                await asyncio.sleep(backoff)
            except asyncio.CancelledError:
                raise
            backoff = min(backoff * 1.5, 30.0)

    async def _connect_once(self) -> None:
        session = self._session
        if session is None:
            session = self._session = aiohttp.ClientSession()
        self._status("Kick: connecting…")
        async with session.ws_connect(PUSHER_URL, heartbeat=30) as ws:
            await self._wait_for_connection(ws)
            await ws.send_str(
                json.dumps(
                    {
                        "event": "pusher:subscribe",
                        "data": {"auth": "", "channel": self._channel},
                    }
                )
            )
            await self._wait_for_subscription(ws)
            self._status(f"Kick: connected ({self._channel})")
            last_ping = time.monotonic()
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await self._handle_text(msg.data)
                elif msg.type == aiohttp.WSMsgType.BINARY:
                    text = msg.data.decode("utf-8", errors="replace")
                    await self._handle_text(text)
                elif msg.type in (
                    aiohttp.WSMsgType.CLOSED,
                    aiohttp.WSMsgType.CLOSE,
                    aiohttp.WSMsgType.ERROR,
                ):
                    break
                now = time.monotonic()
                if now - last_ping >= KICK_PING_INTERVAL_SEC:
                    await ws.send_str(json.dumps({"event": "pusher:ping", "data": {}}))
                    last_ping = now

    async def _wait_for_connection(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        while True:
            msg = await ws.receive()
            if msg.type == aiohttp.WSMsgType.TEXT:
                event, _ch, _data = parse_pusher_envelope(msg.data)
                if event == "pusher:connection_established":
                    return
            elif msg.type in (
                aiohttp.WSMsgType.CLOSED,
                aiohttp.WSMsgType.CLOSE,
                aiohttp.WSMsgType.ERROR,
            ):
                raise ConnectionError("Pusher closed before connection established")

    async def _wait_for_subscription(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        while True:
            msg = await ws.receive()
            if msg.type == aiohttp.WSMsgType.TEXT:
                event, _ch, _data = parse_pusher_envelope(msg.data)
                if event == "pusher_internal:subscription_succeeded":
                    return
                if event == "pusher:error":
                    raise ConnectionError(f"Pusher subscription error: {_data}")
            elif msg.type in (
                aiohttp.WSMsgType.CLOSED,
                aiohttp.WSMsgType.CLOSE,
                aiohttp.WSMsgType.ERROR,
            ):
                raise ConnectionError("Pusher closed before subscription confirmed")

    async def _handle_text(self, raw: str) -> None:
        try:
            event, channel, data_str = parse_pusher_envelope(raw)
        except ValueError:
            return
        if channel not in (None, self._channel):
            return
        if event == "pusher:ping":
            return
        if event.startswith("pusher:") or event.startswith("pusher_internal:"):
            return
        if event == CHAT_EVENT:
            payload = parse_chat_message(data_str)
            if payload is not None and self._on_message is not None:
                self._on_message(payload)
            return
        if event in CHATROOM_ACTION_EVENTS:
            payload = parse_chat_message(data_str)
            if payload is not None and self._on_action is not None:
                self._on_action(event, payload)
