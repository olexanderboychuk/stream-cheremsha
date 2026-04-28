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
                    json.dumps({"op": "subscribe", "type": "chat", "instance": "main", "params": {}})
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


def _subscribe_debug_default() -> dict[str, object]:
    return {"op": "subscribe", "type": "debug", "instance": "default", "params": {}}

