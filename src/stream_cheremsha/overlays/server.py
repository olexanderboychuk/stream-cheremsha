from __future__ import annotations

import asyncio
import json
import mimetypes
import ssl
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aiohttp import WSCloseCode, web

from stream_cheremsha.docks.activity_dock import render_activity_dock_html
from stream_cheremsha.docks.multichat_dock import render_multichat_dock_html
from stream_cheremsha.docks.online_dock import render_online_dock_html
from stream_cheremsha.overlays.event_bus import OverlayEventBus
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
        events: OverlayEventBus | None = None,
        host: str = "127.0.0.1",
        port: int = 17171,
        certificate_pem: str = "",
        private_key_pem: str = "",
    ) -> None:
        self._registry = registry
        self._pubsub = pubsub or OverlayPubSub()
        self._events = events or OverlayEventBus()
        self._host = str(host)
        self._port = int(port)
        self._certificate_pem = str(certificate_pem).strip()
        self._private_key_pem = str(private_key_pem).strip()
        self._tls_dir: tempfile.TemporaryDirectory[str] | None = None
        self._running: _Running | None = None

    def base_url(self) -> str:
        if self._running is None:
            raise RuntimeError("OverlayServer is not running")
        scheme = "https" if self._certificate_pem else "http"
        return f"{scheme}://{self._host}:{self._running.port}"

    def pubsub(self) -> OverlayPubSub:
        return self._pubsub

    def set_tls_files(self, certificate_path: Path, private_key_path: Path) -> None:
        """Load certificate material before the server is started."""
        self._certificate_pem = certificate_path.read_text(encoding="utf-8").strip()
        self._private_key_pem = private_key_path.read_text(encoding="utf-8").strip()

    def events(self) -> OverlayEventBus:
        return self._events

    async def start(self) -> None:
        if self._running is not None:
            return

        @web.middleware
        async def _security_headers_mw(
            _req: web.Request,
            handler: web.Handler,
        ) -> web.StreamResponse:
            resp = await handler(_req)
            # Helps YouTube embeds behave consistently across browsers/CEF.
            resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            return resp

        app = web.Application(middlewares=[_security_headers_mw])
        app.router.add_get("/health", self._health)
        app.router.add_get("/assets/{path:.*}", self._assets)
        app.router.add_get("/overlay/{overlay_type}", self._overlay_page)
        app.router.add_get("/dock/multichat", self._dock_multichat)
        app.router.add_get("/dock/activity", self._dock_activity)
        app.router.add_get("/dock/online", self._dock_online)
        app.router.add_get("/ws", self._ws)

        if bool(self._certificate_pem) != bool(self._private_key_pem):
            raise RuntimeError("Overlay HTTPS requires both a certificate and a private key")

        ssl_context: ssl.SSLContext | None = None
        if self._certificate_pem:
            self._tls_dir = tempfile.TemporaryDirectory(prefix="cheremsha-tls-")
            cert_path = Path(self._tls_dir.name) / "cert.pem"
            key_path = Path(self._tls_dir.name) / "key.pem"
            cert_path.write_text(self._certificate_pem + "\n", encoding="utf-8")
            key_path.write_text(self._private_key_pem + "\n", encoding="utf-8")
            key_path.chmod(0o600)
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(certfile=cert_path, keyfile=key_path)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=self._host, port=self._port, ssl_context=ssl_context)
        try:
            await site.start()
        except BaseException:
            await runner.cleanup()
            self._cleanup_tls()
            raise

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
        self._cleanup_tls()

    def _cleanup_tls(self) -> None:
        if self._tls_dir is not None:
            self._tls_dir.cleanup()
            self._tls_dir = None

    async def _health(self, _req: web.Request) -> web.Response:
        return web.Response(text="ok", content_type="text/plain")

    async def _assets(self, _req: web.Request) -> web.Response:
        rel = str(_req.match_info.get("path") or "").lstrip("/")
        if not rel:
            raise web.HTTPNotFound(text="asset not found")
        # Prevent path traversal.
        if "\\" in rel or ":" in rel:
            raise web.HTTPNotFound(text="asset not found")
        base = Path(__file__).resolve().parents[1] / "assets"
        p = (base / rel).resolve()
        try:
            p.relative_to(base)
        except ValueError as e:
            raise web.HTTPNotFound(text="asset not found") from e
        if not p.is_file():
            raise web.HTTPNotFound(text="asset not found")
        ctype, _enc = mimetypes.guess_type(str(p))
        if p.suffix.lower() == ".svg":
            ctype = "image/svg+xml"
        return web.FileResponse(
            path=p,
            headers={"Content-Type": ctype or "application/octet-stream"},
        )

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
        anchor = str(req.query.get("anchor", "")).strip().lstrip("@").strip()
        if anchor:
            params["anchor"] = anchor
        html = t.render_html(params)
        return web.Response(text=html, content_type="text/html", charset="utf-8")

    async def _dock_multichat(self, _req: web.Request) -> web.Response:
        html = render_multichat_dock_html()
        return web.Response(text=html, content_type="text/html", charset="utf-8")

    async def _dock_activity(self, _req: web.Request) -> web.Response:
        html = render_activity_dock_html()
        return web.Response(text=html, content_type="text/html", charset="utf-8")

    async def _dock_online(self, _req: web.Request) -> web.Response:
        html = render_online_dock_html()
        return web.Response(text=html, content_type="text/html", charset="utf-8")

    async def _ws(self, req: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(req)
        patch_task: asyncio.Task[None] | None = None
        patch_q: asyncio.Queue[dict[str, Any]] | None = None
        try:
            try:
                msg = await asyncio.wait_for(ws.receive(), timeout=5.0)
            except TimeoutError:
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
                if nxt.type != web.WSMsgType.TEXT:
                    continue
                try:
                    obj = json.loads(nxt.data)
                except json.JSONDecodeError:
                    continue
                if not isinstance(obj, dict):
                    continue
                if obj.get("op") != "event":
                    continue
                if str(obj.get("type") or "").strip() != overlay_type:
                    continue
                try:
                    inst2 = normalize_instance_id(str(obj.get("instance") or ""))
                except ValueError:
                    continue
                if inst2 != instance:
                    continue
                event_name = str(obj.get("event") or "").strip()
                if not event_name:
                    continue
                payload = obj.get("payload")
                if payload is None:
                    payload_obj: dict[str, Any] = {}
                elif isinstance(payload, dict):
                    payload_obj = dict(payload)
                else:
                    continue
                self._events.publish_nowait(
                    f"event:{overlay_type}:{instance}",
                    {
                        "event": event_name,
                        "payload": payload_obj,
                        "type": overlay_type,
                        "instance": instance,
                    },
                )
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
