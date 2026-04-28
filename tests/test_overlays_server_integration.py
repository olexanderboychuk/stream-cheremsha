import json

import aiohttp
import pytest

from stream_cheremsha.overlays.pubsub import OverlayPubSub
from stream_cheremsha.overlays.registry import OverlayRegistry
from stream_cheremsha.overlays.server import OverlayServer


@pytest.mark.asyncio
async def test_overlay_server_health_and_debug_html() -> None:
    reg = OverlayRegistry()
    srv = OverlayServer(registry=reg, host="127.0.0.1", port=0)
    await srv.start()
    try:
        base = srv.base_url()

        async with aiohttp.ClientSession() as s:
            async with s.get(f"{base}/health") as r:
                assert r.status == 200
                assert (await r.text()).strip() == "ok"
            async with s.get(f"{base}/overlay/debug?instance=default") as r:
                assert r.status == 200
                body = await r.text()
                assert "<!doctype html>" in body.lower()
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
        async with aiohttp.ClientSession() as s:
            async with s.ws_connect(ws_url) as ws:
                await ws.send_str(json.dumps(_subscribe_debug_default()))
                msg = await ws.receive(timeout=2.0)
                assert msg.type == aiohttp.WSMsgType.TEXT
                obj = json.loads(msg.data)
                assert obj["op"] == "initial_state"
                assert "state" in obj

                await ps.publish("overlay:debug:default", {"tick": 999})
                while True:
                    msg2 = await ws.receive(timeout=2.0)
                    assert msg2.type == aiohttp.WSMsgType.TEXT
                    obj2 = json.loads(msg2.data)
                    if obj2.get("op") != "patch":
                        continue
                    if obj2.get("patch") == {"tick": 999}:
                        break
    finally:
        await srv.stop()


def _subscribe_debug_default() -> dict[str, object]:
    return {"op": "subscribe", "type": "debug", "instance": "default", "params": {}}

