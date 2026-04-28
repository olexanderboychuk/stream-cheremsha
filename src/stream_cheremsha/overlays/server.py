from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from aiohttp import WSCloseCode
from aiohttp import web

from stream_cheremsha.overlays.models import (
    normalize_instance_id,
    overlays_initial_state_msg,
    overlays_patch_msg,
)
from stream_cheremsha.overlays.pubsub import OverlayPubSub
from stream_cheremsha.overlays.registry import OverlayRegistry, UnknownOverlayTypeError


@dataclass(slots=True, frozen=True)
class _Running:
    runner: web.AppRunner
    site: web.TCPSite
    port: int


class OverlayServer:
    def __init__(
        self,
        *,
        registry: OverlayRegistry,
        pubsub: OverlayPubSub | None = None,
        host: str = "127.0.0.1",
        port: int = 17171,
    ) -> None:
        self._registry = registry
        self._pubsub = pubsub or OverlayPubSub()
        self._host = str(host)
        self._port = int(port)
        self._running: _Running | None = None

    def base_url(self) -> str:
        if self._running is None:
            raise RuntimeError("OverlayServer is not running")
        return f"http://{self._host}:{self._running.port}"

    def pubsub(self) -> OverlayPubSub:
        return self._pubsub

    async def start(self) -> None:
        if self._running is not None:
            return

        app = web.Application()
        app.router.add_get("/health", self._health)
        app.router.add_get("/assets/{path:.*}", self._assets)
        app.router.add_get("/overlay/{overlay_type}", self._overlay_page)
        app.router.add_get("/ws", self._ws)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=self._host, port=self._port)
        await site.start()

        bound_port = self._port
        server = getattr(site, "_server", None)
        sockets = getattr(server, "sockets", None)
        if sockets:
            bound_port = int(sockets[0].getsockname()[1])

        self._running = _Running(runner=runner, site=site, port=bound_port)

    async def stop(self) -> None:
        r = self._running
        if r is None:
            return
        self._running = None
        await r.runner.cleanup()

    async def _health(self, _req: web.Request) -> web.Response:
        return web.Response(text="ok", content_type="text/plain")

    async def _assets(self, _req: web.Request) -> web.Response:
        # Foundation route: real static assets can be added later. For now, return 404.
        raise web.HTTPNotFound(text="assets not found")

    async def _overlay_page(self, req: web.Request) -> web.Response:
        overlay_type = str(req.match_info.get("overlay_type") or "").strip()
        try:
            t = self._registry.get(overlay_type)
        except UnknownOverlayTypeError as e:
            raise web.HTTPNotFound(text=f"unknown overlay type: {e.args[0]}") from e

        try:
            instance = normalize_instance_id(str(req.query.get("instance", "")))
        except ValueError as e:
            raise web.HTTPBadRequest(text="invalid instance") from e

        params: dict[str, Any] = {"instance": instance}
        html = t.render_html(params)
        return web.Response(text=html, content_type="text/html", charset="utf-8")

    async def _ws(self, req: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(req)
        patch_task: asyncio.Task[None] | None = None
        patch_q: asyncio.Queue[dict[str, Any]] | None = None
        try:
            try:
                msg = await asyncio.wait_for(ws.receive(), timeout=5.0)
            except asyncio.TimeoutError:
                await ws.close(code=WSCloseCode.POLICY_VIOLATION, message=b"subscribe timeout")
                return ws
            if msg.type != web.WSMsgType.TEXT:
                await ws.close(code=WSCloseCode.PROTOCOL_ERROR, message=b"expected text")
                return ws

            try:
                data = json.loads(msg.data)
            except json.JSONDecodeError:
                await ws.close(code=WSCloseCode.INVALID_TEXT, message=b"invalid json")
                return ws

            if not isinstance(data, dict) or data.get("op") != "subscribe":
                await ws.close(code=WSCloseCode.PROTOCOL_ERROR, message=b"expected subscribe")
                return ws

            overlay_type = str(data.get("type") or "").strip()
            if not overlay_type:
                await ws.close(code=WSCloseCode.PROTOCOL_ERROR, message=b"missing overlay type")
                return ws

            try:
                instance = normalize_instance_id(str(data.get("instance") or ""))
            except ValueError:
                await ws.close(code=WSCloseCode.PROTOCOL_ERROR, message=b"invalid instance")
                return ws

            raw_params = data.get("params")
            params: dict[str, Any]
            if raw_params is None:
                params = {}
            elif isinstance(raw_params, dict):
                params = dict(raw_params)
            else:
                await ws.close(code=WSCloseCode.PROTOCOL_ERROR, message=b"params must be object")
                return ws
            params["instance"] = instance

            try:
                t = self._registry.get(overlay_type)
            except UnknownOverlayTypeError:
                await ws.send_str(json.dumps({"op": "error", "message": "unknown overlay type"}))
                await ws.close(code=WSCloseCode.PROTOCOL_ERROR, message=b"unknown overlay type")
                return ws

            state = t.initial_state(params)
            await ws.send_str(json.dumps(overlays_initial_state_msg(state), ensure_ascii=False))

            topic = f"overlay:{overlay_type}:{instance}"
            patch_q = self._pubsub.subscribe(topic)

            async def _forward_patches() -> None:
                assert patch_q is not None
                while True:
                    patch = await patch_q.get()
                    if ws.closed:
                        return
                    try:
                        await ws.send_str(json.dumps(overlays_patch_msg(patch), ensure_ascii=False))
                    except (ConnectionResetError, RuntimeError):
                        return

            patch_task = asyncio.create_task(_forward_patches())

            # Debug patch generator (at least one patch observable).
            if overlay_type == "debug":
                await self._pubsub.publish(topic, {"tick": 1})

            async for nxt in ws:
                if nxt.type in (web.WSMsgType.CLOSE, web.WSMsgType.CLOSED, web.WSMsgType.ERROR):
                    break
        finally:
            if patch_task is not None:
                patch_task.cancel()
                try:
                    await patch_task
                except asyncio.CancelledError:
                    pass
                except Exception:
                    # Connection lifecycle should not be dominated by forwarder failures.
                    # If forwarding failed unexpectedly, the websocket is already closing.
                    pass
            if patch_q is not None:
                self._pubsub.unsubscribe(patch_q)
            if not ws.closed:
                await ws.close()

        return ws
