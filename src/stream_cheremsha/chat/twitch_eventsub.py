from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import aiohttp

from stream_cheremsha.chat.twitch_helix import TwitchHelixClient

logger = logging.getLogger(__name__)

_EVENTSUB_WS = "wss://eventsub.wss.twitch.tv/ws"


@dataclass(frozen=True, slots=True)
class TwitchNotifiedUser:
    """User identity from an EventSub notification (for Helix profile lookup)."""

    display_name: str
    user_id: str = ""
    login: str = ""


@dataclass(frozen=True, slots=True)
class TwitchEventSubCallbacks:
    on_follow: Callable[[TwitchNotifiedUser], None] | None = None
    on_sub: Callable[[TwitchNotifiedUser, str, int, str], None] | None = (
        None  # user, type, months, msg
    )
    on_cheer: Callable[[TwitchNotifiedUser, int], None] | None = None  # user, bits
    on_raid: Callable[[TwitchNotifiedUser, int], None] | None = None  # raider, viewers
    on_status: Callable[[str], None] | None = None


class TwitchEventSubClient:
    """EventSub WebSocket client (creates subscriptions via Helix; consumes notifications)."""

    def __init__(
        self,
        *,
        helix: TwitchHelixClient,
        broadcaster_id: str,
        callbacks: TwitchEventSubCallbacks,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._helix = helix
        self._broadcaster_id = broadcaster_id.strip()
        self._cb = callbacks
        self._session = session or aiohttp.ClientSession()
        self._owns_session = session is None
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._last_keepalive = 0.0

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        if self.running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run(), name="twitch-eventsub")

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
        if self._owns_session:
            await self._session.close()

    def _status(self, msg: str) -> None:
        cb = self._cb.on_status
        if cb is not None:
            cb(msg)

    async def _run(self) -> None:
        backoff = 2.0
        while self._running:
            try:
                await self._connect_once()
                backoff = 2.0
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("EventSub run error: %s", exc)
                self._status(f"Twitch EventSub: error: {exc}")
            if not self._running:
                break
            await asyncio.sleep(backoff)
            backoff = min(backoff * 1.6, 20.0)

    async def _connect_once(self) -> None:
        async with self._session.ws_connect(_EVENTSUB_WS, heartbeat=25) as ws:
            self._status("Twitch EventSub: connected")
            session_id: str | None = None
            self._last_keepalive = time.monotonic()

            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    raw = msg.data
                elif msg.type == aiohttp.WSMsgType.BINARY:
                    raw = msg.data.decode("utf-8", errors="replace")
                elif msg.type in (
                    aiohttp.WSMsgType.CLOSED,
                    aiohttp.WSMsgType.CLOSE,
                    aiohttp.WSMsgType.ERROR,
                ):
                    break
                else:
                    continue

                parsed = _parse_eventsub_ws_message(raw)
                if parsed is None:
                    continue

                if parsed.kind == "keepalive":
                    self._last_keepalive = time.monotonic()
                    continue

                if parsed.kind == "welcome":
                    session_id = parsed.session_id
                    self._last_keepalive = time.monotonic()
                    if session_id:
                        await self._ensure_subscriptions(session_id)
                    continue

                if parsed.kind == "reconnect":
                    # Twitch suggests a new URL to reconnect to.
                    url = parsed.reconnect_url
                    if url:
                        self._status("Twitch EventSub: reconnecting")
                        await ws.close()
                        await self._connect_reconnect_url(url)
                        return
                    continue

                if parsed.kind == "notification":
                    _dispatch_notification(parsed.subscription_type, parsed.event, self._cb)
                    continue

    async def _connect_reconnect_url(self, url: str) -> None:
        async with self._session.ws_connect(url, heartbeat=25) as ws:
            async for msg in ws:
                if msg.type != aiohttp.WSMsgType.TEXT:
                    continue
                parsed = _parse_eventsub_ws_message(msg.data)
                if parsed and parsed.kind == "welcome" and parsed.session_id:
                    await self._ensure_subscriptions(parsed.session_id)
                elif parsed and parsed.kind == "notification":
                    _dispatch_notification(parsed.subscription_type, parsed.event, self._cb)

    async def _ensure_subscriptions(self, session_id: str) -> None:
        b = self._broadcaster_id
        if not b:
            return
        # Follow event requires moderator_id; broadcaster can act as moderator for own channel.
        await self._helix.create_eventsub_subscription(
            type_name="channel.follow",
            version="2",
            condition={"broadcaster_user_id": b, "moderator_user_id": b},
            session_id=session_id,
        )
        await self._helix.create_eventsub_subscription(
            type_name="channel.subscribe",
            version="1",
            condition={"broadcaster_user_id": b},
            session_id=session_id,
        )
        await self._helix.create_eventsub_subscription(
            type_name="channel.subscription.gift",
            version="1",
            condition={"broadcaster_user_id": b},
            session_id=session_id,
        )
        await self._helix.create_eventsub_subscription(
            type_name="channel.subscription.message",
            version="1",
            condition={"broadcaster_user_id": b},
            session_id=session_id,
        )
        await self._helix.create_eventsub_subscription(
            type_name="channel.cheer",
            version="1",
            condition={"broadcaster_user_id": b},
            session_id=session_id,
        )
        await self._helix.create_eventsub_subscription(
            type_name="channel.raid",
            version="1",
            condition={"to_broadcaster_user_id": b},
            session_id=session_id,
        )
        self._status("Twitch EventSub: subscriptions active")


@dataclass(frozen=True, slots=True)
class _ParsedEventSub:
    kind: str
    session_id: str | None = None
    reconnect_url: str | None = None
    subscription_type: str | None = None
    event: dict[str, Any] | None = None


def _parse_eventsub_ws_message(raw: str) -> _ParsedEventSub | None:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    meta = payload.get("metadata")
    if not isinstance(meta, dict):
        return None
    msg_type = meta.get("message_type")
    if not isinstance(msg_type, str):
        return None
    p = payload.get("payload")
    if not isinstance(p, dict):
        p = {}

    if msg_type == "session_keepalive":
        return _ParsedEventSub(kind="keepalive")
    if msg_type == "session_welcome":
        sess = p.get("session")
        if isinstance(sess, dict):
            sid = sess.get("id")
            return _ParsedEventSub(kind="welcome", session_id=sid if isinstance(sid, str) else None)
        return _ParsedEventSub(kind="welcome", session_id=None)
    if msg_type == "session_reconnect":
        sess = p.get("session")
        if isinstance(sess, dict):
            url = sess.get("reconnect_url")
            return _ParsedEventSub(
                kind="reconnect",
                reconnect_url=url if isinstance(url, str) else None,
            )
        return _ParsedEventSub(kind="reconnect", reconnect_url=None)
    if msg_type == "notification":
        sub = p.get("subscription")
        ev = p.get("event")
        st = None
        if isinstance(sub, dict):
            t = sub.get("type")
            st = t if isinstance(t, str) else None
        return _ParsedEventSub(
            kind="notification",
            subscription_type=st,
            event=ev if isinstance(ev, dict) else None,
        )
    return None


def _event_str(event: dict[str, Any], key: str) -> str:
    v = event.get(key)
    return v.strip() if isinstance(v, str) else ""


def _notified_user(
    event: dict[str, Any],
    *,
    display: str = "",
    user_id_key: str = "user_id",
    login_key: str = "user_login",
) -> TwitchNotifiedUser:
    disp = (
        (display or "").strip()
        or _event_str(event, "user_name")
        or _event_str(event, "gifter_name")
        or _event_str(event, "from_broadcaster_user_name")
        or _event_str(event, "user_login")
        or _event_str(event, "gifter_user_login")
        or _event_str(event, "from_broadcaster_user_login")
    )
    return TwitchNotifiedUser(
        display_name=disp or "?",
        user_id=_event_str(event, user_id_key),
        login=_event_str(event, login_key),
    )


def _dispatch_notification(
    sub_type: str | None,
    event: dict[str, Any] | None,
    cb: TwitchEventSubCallbacks,
) -> None:
    if not sub_type or not event:
        return

    if sub_type == "channel.follow":
        tu = _notified_user(event)
        if tu.display_name != "?" and cb.on_follow is not None:
            cb.on_follow(tu)
        return

    if sub_type in (
        "channel.subscribe",
        "channel.subscription.gift",
        "channel.subscription.message",
    ):
        if sub_type == "channel.subscription.gift":
            tu = _notified_user(
                event,
                user_id_key="gifter_user_id",
                login_key="gifter_user_login",
            )
        else:
            tu = _notified_user(event)
        st = "sub"
        if sub_type == "channel.subscription.gift":
            st = "gift"
        elif sub_type == "channel.subscription.message":
            st = "resub"
        months = event.get("cumulative_months")
        m = int(months) if isinstance(months, int) else 0
        msg_text = ""
        if sub_type == "channel.subscription.message":
            mo = event.get("message")
            if isinstance(mo, dict):
                tx = mo.get("text")
                if isinstance(tx, str):
                    msg_text = tx
        if cb.on_sub is not None:
            cb.on_sub(tu, st, m, msg_text)
        return

    if sub_type == "channel.cheer":
        tu = _notified_user(event)
        bits = event.get("bits")
        if tu.display_name != "?" and isinstance(bits, int) and cb.on_cheer is not None:
            cb.on_cheer(tu, bits)
        return

    if sub_type == "channel.raid":
        tu = _notified_user(
            event,
            user_id_key="from_broadcaster_user_id",
            login_key="from_broadcaster_user_login",
        )
        viewers = event.get("viewers")
        if tu.display_name != "?" and isinstance(viewers, int) and cb.on_raid is not None:
            cb.on_raid(tu, viewers)
        return
