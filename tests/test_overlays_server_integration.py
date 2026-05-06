import json

import aiohttp
import pytest

from stream_cheremsha.overlays.pubsub import OverlayPubSub
from stream_cheremsha.overlays.registry import OverlayRegistry
from stream_cheremsha.overlays.server import OverlayServer


async def _ws_next_text(
    ws: aiohttp.ClientWebSocketResponse,
    *,
    timeout: float = 2.0,
) -> aiohttp.WSMessage:
    """Receive next TEXT frame, skipping ping/pong; fail on close/error."""
    while True:
        msg = await ws.receive(timeout=timeout)
        if msg.type in (aiohttp.WSMsgType.PING, aiohttp.WSMsgType.PONG):
            continue
        if msg.type in (
            aiohttp.WSMsgType.CLOSE,
            aiohttp.WSMsgType.CLOSED,
            aiohttp.WSMsgType.ERROR,
        ):
            raise AssertionError(f"websocket closed/error: {msg.type} {ws.exception()!r}")
        if msg.type == aiohttp.WSMsgType.TEXT:
            return msg
        # Ignore other frame types.


@pytest.mark.asyncio
async def test_overlay_server_health_and_debug_html() -> None:
    reg = OverlayRegistry()
    srv = OverlayServer(registry=reg, host="127.0.0.1", port=0)
    await srv.start()
    try:
        base = srv.base_url()

        timeout = aiohttp.ClientTimeout(total=2.0)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.get(f"{base}/health") as r:
                assert r.status == 200
                assert (await r.text()).strip() == "ok"
            async with s.get(f"{base}/overlay/debug?instance=default") as r:
                assert r.status == 200
                body = await r.text()
                assert "<!doctype html>" in body.lower()
            async with s.get(f"{base}/assets/twitch.svg") as r:
                assert r.status == 200
                assert "svg" in (r.headers.get("Content-Type") or "").lower()
    finally:
        await srv.stop()


@pytest.mark.asyncio
async def test_overlay_server_ws_initial_state_and_patch() -> None:
    reg = OverlayRegistry()
    ps = OverlayPubSub()
    srv = OverlayServer(registry=reg, pubsub=ps, host="127.0.0.1", port=0)
    await srv.start()
    try:
        base = srv.base_url()

        ws_url = base.replace("http://", "ws://") + "/ws"
        timeout = aiohttp.ClientTimeout(total=2.0)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.ws_connect(ws_url) as ws:
                await ws.send_str(json.dumps(_subscribe_debug_default()))
                msg = await _ws_next_text(ws)
                obj = json.loads(msg.data)
                assert obj["op"] == "initial_state"
                assert "state" in obj

                await ps.publish("overlay:debug:default", {"tick": 999})
                while True:
                    msg2 = await _ws_next_text(ws)
                    obj2 = json.loads(msg2.data)
                    if obj2.get("op") != "patch":
                        continue
                    if obj2.get("patch") == {"tick": 999}:
                        break
    finally:
        await srv.stop()


@pytest.mark.asyncio
async def test_chat_overlay_ws_receives_append_patch() -> None:
    reg = OverlayRegistry()
    ps = OverlayPubSub()
    srv = OverlayServer(registry=reg, pubsub=ps, host="127.0.0.1", port=0)
    await srv.start()
    try:
        ws_url = srv.base_url().replace("http://", "ws://") + "/ws"
        timeout = aiohttp.ClientTimeout(total=2.0)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.ws_connect(ws_url) as ws:
                await ws.send_str(
                    json.dumps(
                        {
                            "op": "subscribe",
                            "type": "chat",
                            "instance": "main",
                            "params": {},
                        }
                    )
                )
                msg = await _ws_next_text(ws)
                obj = json.loads(msg.data)
                assert obj["op"] == "initial_state"
                assert "state" in obj

                await ps.publish(
                    "overlay:chat:main",
                    {
                        "append": {
                            "author": "a",
                            "text": "t",
                            "platform": "twitch",
                            "received_at": "x",
                        }
                    },
                )
                while True:
                    m2 = await _ws_next_text(ws)
                    o2 = json.loads(m2.data)
                    if (
                        o2.get("op") == "patch"
                        and o2.get("patch", {}).get("append", {}).get("author") == "a"
                    ):
                        break
    finally:
        await srv.stop()


@pytest.mark.asyncio
async def test_actions_overlay_ws_initial_state_has_config() -> None:
    reg = OverlayRegistry()
    ps = OverlayPubSub()
    srv = OverlayServer(registry=reg, pubsub=ps, host="127.0.0.1", port=0)
    await srv.start()
    try:
        ws_url = srv.base_url().replace("http://", "ws://") + "/ws"
        timeout = aiohttp.ClientTimeout(total=2.0)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.ws_connect(ws_url) as ws:
                await ws.send_str(
                    json.dumps(
                        {
                            "op": "subscribe",
                            "type": "actions",
                            "instance": "main",
                            "params": {},
                        }
                    )
                )
                msg = await _ws_next_text(ws)
                obj = json.loads(msg.data)
                assert obj["op"] == "initial_state"
                assert "state" in obj
                assert "config" in obj["state"]
    finally:
        await srv.stop()


@pytest.mark.asyncio
async def test_overlay_server_dock_multichat_html() -> None:
    reg = OverlayRegistry()
    srv = OverlayServer(registry=reg, host="127.0.0.1", port=0)
    await srv.start()
    try:
        base = srv.base_url()
        timeout = aiohttp.ClientTimeout(total=2.0)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.get(f"{base}/dock/multichat") as r:
                assert r.status == 200
                body = await r.text()
                assert "<!doctype html>" in body.lower()
                assert "/ws" in body
                assert "subscribe" in body.lower()
                assert "multichat" in body.lower()
    finally:
        await srv.stop()


@pytest.mark.asyncio
async def test_overlay_server_dock_activity_html() -> None:
    reg = OverlayRegistry()
    srv = OverlayServer(registry=reg, host="127.0.0.1", port=0)
    await srv.start()
    try:
        base = srv.base_url()
        timeout = aiohttp.ClientTimeout(total=2.0)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.get(f"{base}/dock/activity") as r:
                assert r.status == 200
                body = await r.text()
                assert "<!doctype html>" in body.lower()
                assert "/ws" in body
                assert "activity" in body.lower()
    finally:
        await srv.stop()


@pytest.mark.asyncio
async def test_overlay_server_dock_online_html() -> None:
    reg = OverlayRegistry()
    srv = OverlayServer(registry=reg, host="127.0.0.1", port=0)
    await srv.start()
    try:
        base = srv.base_url()
        timeout = aiohttp.ClientTimeout(total=2.0)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.get(f"{base}/dock/online") as r:
                assert r.status == 200
                body = await r.text()
                assert "<!doctype html>" in body.lower()
                assert "/ws" in body
                assert "online" in body.lower()
    finally:
        await srv.stop()


@pytest.mark.asyncio
async def test_activity_overlay_ws_receives_append_patch() -> None:
    reg = OverlayRegistry()
    ps = OverlayPubSub()
    srv = OverlayServer(registry=reg, pubsub=ps, host="127.0.0.1", port=0)
    await srv.start()
    try:
        ws_url = srv.base_url().replace("http://", "ws://") + "/ws"
        timeout = aiohttp.ClientTimeout(total=2.0)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.ws_connect(ws_url) as ws:
                await ws.send_str(
                    json.dumps(
                        {
                            "op": "subscribe",
                            "type": "activity",
                            "instance": "main",
                            "params": {},
                        }
                    )
                )
                msg = await _ws_next_text(ws)
                obj = json.loads(msg.data)
                assert obj["op"] == "initial_state"

                await ps.publish(
                    "overlay:activity:main",
                    {
                        "append": {
                            "platform": "twitch",
                            "kind": "follow",
                            "user": "a",
                            "detail": "",
                            "count": 1,
                            "icon_url": "",
                            "time": "00:00:01",
                        }
                    },
                )
                while True:
                    m2 = await _ws_next_text(ws)
                    o2 = json.loads(m2.data)
                    if (
                        o2.get("op") == "patch"
                        and o2.get("patch", {}).get("append", {}).get("user") == "a"
                    ):
                        break
    finally:
        await srv.stop()


@pytest.mark.asyncio
async def test_online_overlay_ws_receives_online_state_patch() -> None:
    reg = OverlayRegistry()
    ps = OverlayPubSub()
    srv = OverlayServer(registry=reg, pubsub=ps, host="127.0.0.1", port=0)
    await srv.start()
    try:
        ws_url = srv.base_url().replace("http://", "ws://") + "/ws"
        timeout = aiohttp.ClientTimeout(total=2.0)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.ws_connect(ws_url) as ws:
                await ws.send_str(
                    json.dumps(
                        {
                            "op": "subscribe",
                            "type": "online",
                            "instance": "main",
                            "params": {},
                        }
                    )
                )
                msg = await _ws_next_text(ws)
                obj = json.loads(msg.data)
                assert obj["op"] == "initial_state"

                state = {
                    "twitch": {"current": 7, "peak": 9},
                    "tiktok": {
                        "current": 11,
                        "total": 100,
                        "gifts": 3,
                        "diamonds": 25,
                    },
                    "updated_at": "00:00:02",
                }
                expected_patch = {"online": state}
                await ps.publish("overlay:online:main", expected_patch)

                while True:
                    m2 = await _ws_next_text(ws)
                    o2 = json.loads(m2.data)
                    if o2.get("op") != "patch":
                        continue
                    if o2.get("patch") == expected_patch:
                        break
    finally:
        await srv.stop()


def _subscribe_debug_default() -> dict[str, object]:
    return {"op": "subscribe", "type": "debug", "instance": "default", "params": {}}

