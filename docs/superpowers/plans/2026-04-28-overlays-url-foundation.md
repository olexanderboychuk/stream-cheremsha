# Overlay URLs (OBS) Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local HTTP overlay server with live updates so OBS can add overlays via `http://127.0.0.1:<port>/overlay/<type>?instance=...`.

**Architecture:** A small in-process server (localhost-only) serves overlay HTML + static assets and provides a WebSocket endpoint for `initial_state` + `patch` updates. Overlay pages are defined via a registry of overlay types with `render_html`, `initial_state`, and `subscribe`.

**Tech Stack:** Python 3.11, asyncio, existing Stream Cheremsha app lifecycle (PySide6 + qasync), pytest. Prefer minimal deps; if a web framework is introduced, keep it lightweight and Nuitka-friendly.

---

## File map (what we will touch)

**Create (overlays core):**

- `src/stream_cheremsha/overlays/__init__.py`
- `src/stream_cheremsha/overlays/models.py` — typed message envelopes + params parsing helpers
- `src/stream_cheremsha/overlays/registry.py` — overlay type registry + a built-in `debug` overlay type
- `src/stream_cheremsha/overlays/server.py` — HTTP server + static assets + WS subscriptions + lifecycle helpers
- `src/stream_cheremsha/overlays/pubsub.py` — minimal in-process pubsub to publish events and drive patches

**Create (tests):**

- `tests/test_overlays_registry.py`
- `tests/test_overlays_server_integration.py`

**Modify (app lifecycle):**

- `src/stream_cheremsha/ui/main_window.py` — start/stop overlay server with the app (initially always-on, or behind a simple setting)
- `src/stream_cheremsha/config/constants.py` — (optional) add settings keys: overlay enabled/port/token

**Notes:**

- Keep the foundation independent of QML/UI rendering. UI wiring (copy URL buttons etc.) is a follow-up once the server works.

---

## Task 1: Overlay message envelopes + params normalization

**Files:**
- Create: `src/stream_cheremsha/overlays/models.py`
- Create: `src/stream_cheremsha/overlays/__init__.py`
- Test: `tests/test_overlays_registry.py`

- [ ] **Step 1: Write failing tests for message envelopes and params normalization**

```python
import pytest

from stream_cheremsha.overlays.models import (
    normalize_instance_id,
    overlays_initial_state_msg,
    overlays_patch_msg,
)


def test_normalize_instance_id_default() -> None:
    assert normalize_instance_id("") == "default"
    assert normalize_instance_id("   ") == "default"


def test_normalize_instance_id_trim() -> None:
    assert normalize_instance_id(" main ") == "main"


def test_envelopes_shape() -> None:
    assert overlays_initial_state_msg({"a": 1}) == {"op": "initial_state", "state": {"a": 1}}
    assert overlays_patch_msg({"x": "y"}) == {"op": "patch", "patch": {"x": "y"}}


def test_normalize_instance_id_rejects_bad_chars() -> None:
    with pytest.raises(ValueError):
        normalize_instance_id("../x")
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_overlays_registry.py -q
```

Expected: FAIL (`stream_cheremsha.overlays` missing).

- [ ] **Step 3: Implement minimal models/helpers**

Create `src/stream_cheremsha/overlays/__init__.py`:

```python
from __future__ import annotations
```

Create `src/stream_cheremsha/overlays/models.py`:

```python
from __future__ import annotations

import re
from typing import Any

_INSTANCE_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$")


def normalize_instance_id(v: str) -> str:
    s = (v or "").strip()
    if not s:
        return "default"
    if not _INSTANCE_RE.match(s):
        raise ValueError("Invalid overlay instance id")
    return s


def overlays_initial_state_msg(state: dict[str, Any]) -> dict[str, Any]:
    return {"op": "initial_state", "state": dict(state)}


def overlays_patch_msg(patch: dict[str, Any]) -> dict[str, Any]:
    return {"op": "patch", "patch": dict(patch)}
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest tests/test_overlays_registry.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/stream_cheremsha/overlays/__init__.py src/stream_cheremsha/overlays/models.py tests/test_overlays_registry.py
git commit -m "feat: add overlay message envelopes and params helpers"
```

---

## Task 2: Overlay type registry + built-in debug overlay

**Files:**
- Create: `src/stream_cheremsha/overlays/registry.py`
- Test: `tests/test_overlays_registry.py`

- [ ] **Step 1: Write failing tests for registry and debug overlay**

```python
import pytest

from stream_cheremsha.overlays.registry import OverlayRegistry, UnknownOverlayTypeError


def test_registry_register_and_get() -> None:
    reg = OverlayRegistry()
    t = reg.get("debug")
    assert t.type == "debug"


def test_registry_unknown_type() -> None:
    reg = OverlayRegistry()
    with pytest.raises(UnknownOverlayTypeError):
        reg.get("missing")


def test_debug_overlay_renders_html() -> None:
    reg = OverlayRegistry()
    t = reg.get("debug")
    html = t.render_html({"instance": "default"})
    assert "<html" in html.lower()
    assert "ws" in html.lower() or "websocket" in html.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_overlays_registry.py -q
```

Expected: FAIL (`registry.py` missing).

- [ ] **Step 3: Implement the registry + debug overlay**

Create `src/stream_cheremsha/overlays/registry.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class UnknownOverlayTypeError(KeyError):
    pass


class OverlayType(Protocol):
    type: str

    def render_html(self, params: dict[str, Any]) -> str: ...

    def initial_state(self, params: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class _DebugOverlay:
    type: str = "debug"

    def render_html(self, params: dict[str, Any]) -> str:
        # Minimal HTML that connects to /ws and subscribes.
        # Keep it dependency-free; real overlay types can replace the UI later.
        overlay_type = self.type
        instance = str(params.get("instance") or "default")
        return f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Overlay Debug</title>
    <style>
      html, body {{ margin: 0; padding: 0; background: transparent; color: #e5e7eb; font-family: system-ui, sans-serif; }}
      .box {{ padding: 10px; background: rgba(10,12,18,0.60); border: 1px solid rgba(148,163,184,0.25); }}
      pre {{ white-space: pre-wrap; word-break: break-word; }}
    </style>
  </head>
  <body>
    <div class="box">
      <div><strong>overlay:</strong> {overlay_type}</div>
      <div><strong>instance:</strong> {instance}</div>
      <pre id="log">connecting…</pre>
    </div>
    <script>
      (function() {{
        const log = document.getElementById('log');
        const wsUrl = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws';
        const ws = new WebSocket(wsUrl);
        ws.onopen = () => {{
          ws.send(JSON.stringify({{ op: 'subscribe', type: '{overlay_type}', instance: '{instance}', params: {{}} }}));
        }};
        ws.onmessage = (ev) => {{
          log.textContent = ev.data;
        }};
        ws.onerror = () => {{
          log.textContent = 'ws error';
        }};
        ws.onclose = () => {{
          log.textContent = 'ws closed';
        }};
      }})();
    </script>
  </body>
</html>"""

    def initial_state(self, params: dict[str, Any]) -> dict[str, Any]:
        return {"hello": "world", "params": dict(params)}


class OverlayRegistry:
    def __init__(self) -> None:
        self._types: dict[str, OverlayType] = {}
        self.register(_DebugOverlay())

    def register(self, t: OverlayType) -> None:
        self._types[str(t.type)] = t

    def get(self, overlay_type: str) -> OverlayType:
        k = str(overlay_type or "").strip()
        t = self._types.get(k)
        if t is None:
            raise UnknownOverlayTypeError(k)
        return t
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest tests/test_overlays_registry.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/stream_cheremsha/overlays/registry.py tests/test_overlays_registry.py
git commit -m "feat: add overlay registry with debug overlay type"
```

---

## Task 3: Minimal in-process pubsub (foundation for patches)

**Files:**
- Create: `src/stream_cheremsha/overlays/pubsub.py`
- Test: `tests/test_overlays_registry.py` (append new test)

- [ ] **Step 1: Add failing test for pubsub fan-out**

Append to `tests/test_overlays_registry.py`:

```python
import asyncio

import pytest

from stream_cheremsha.overlays.pubsub import OverlayPubSub


@pytest.mark.asyncio
async def test_pubsub_publishes_to_subscribers() -> None:
    ps = OverlayPubSub()
    q = ps.subscribe(topic="t")
    await ps.publish(topic="t", patch={"x": 1})
    got = await asyncio.wait_for(q.get(), timeout=1.0)
    assert got == {"x": 1}
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_overlays_registry.py -q
```

Expected: FAIL (`pubsub.py` missing).

- [ ] **Step 3: Implement `OverlayPubSub`**

Create `src/stream_cheremsha/overlays/pubsub.py`:

```python
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class _Sub:
    topic: str
    q: asyncio.Queue[dict[str, Any]]


class OverlayPubSub:
    def __init__(self) -> None:
        self._subs: list[_Sub] = []

    def subscribe(self, *, topic: str, maxsize: int = 100) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=maxsize)
        self._subs.append(_Sub(topic=topic, q=q))
        return q

    async def publish(self, *, topic: str, patch: dict[str, Any]) -> None:
        # Best-effort fan-out: drop if subscriber queue is full (avoid blocking the producer).
        for s in list(self._subs):
            if s.topic != topic:
                continue
            try:
                s.q.put_nowait(dict(patch))
            except asyncio.QueueFull:
                # Dropped patch; future overlays can do coalescing.
                continue
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest tests/test_overlays_registry.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/stream_cheremsha/overlays/pubsub.py tests/test_overlays_registry.py
git commit -m "feat: add minimal overlays pubsub for patch delivery"
```

---

## Task 4: Overlay server (HTTP + WS) with debug overlay end-to-end

**Files:**
- Create: `src/stream_cheremsha/overlays/server.py`
- Test: `tests/test_overlays_server_integration.py`

- [ ] **Step 1: Add failing integration test (GET + WS subscribe)**

Create `tests/test_overlays_server_integration.py`:

```python
import asyncio
import json

import pytest

from stream_cheremsha.overlays.registry import OverlayRegistry
from stream_cheremsha.overlays.server import OverlayServer


@pytest.mark.asyncio
async def test_overlay_server_health_and_debug_html() -> None:
    reg = OverlayRegistry()
    srv = OverlayServer(registry=reg, host="127.0.0.1", port=0)
    await srv.start()
    try:
        base = srv.base_url()
        import aiohttp

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
async def test_overlay_server_ws_initial_state() -> None:
    reg = OverlayRegistry()
    srv = OverlayServer(registry=reg, host="127.0.0.1", port=0)
    await srv.start()
    try:
        base = srv.base_url()
        import aiohttp

        ws_url = base.replace("http://", "ws://") + "/ws"
        async with aiohttp.ClientSession() as s:
            async with s.ws_connect(ws_url) as ws:
                await ws.send_str(
                    json.dumps({"op": "subscribe", "type": "debug", "instance": "default", "params": {}})
                )
                msg = await ws.receive(timeout=2.0)
                assert msg.type == aiohttp.WSMsgType.TEXT
                obj = json.loads(msg.data)
                assert obj["op"] == "initial_state"
                assert "state" in obj
    finally:
        await srv.stop()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_overlays_server_integration.py -q
```

Expected: FAIL (`OverlayServer` missing, and `aiohttp` possibly missing in dev deps).

- [ ] **Step 3: Add minimal dependency if needed**

If `aiohttp` is not already present in your dev dependencies, add it to `pyproject.toml` under the dev/test extra used by pytest.

Then verify:

```bash
python -c "import aiohttp; print(aiohttp.__version__)"
```

Expected: prints version, no import error.

- [ ] **Step 4: Implement `OverlayServer` using aiohttp.web**

Create `src/stream_cheremsha/overlays/server.py`:

```python
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from aiohttp import web

from stream_cheremsha.overlays.models import normalize_instance_id, overlays_initial_state_msg
from stream_cheremsha.overlays.registry import OverlayRegistry, UnknownOverlayTypeError


@dataclass(slots=True)
class _Running:
    runner: web.AppRunner
    site: web.TCPSite
    port: int


class OverlayServer:
    def __init__(self, *, registry: OverlayRegistry, host: str = "127.0.0.1", port: int = 17171) -> None:
        self._registry = registry
        self._host = host
        self._port = int(port)
        self._running: _Running | None = None

    def base_url(self) -> str:
        if self._running is None:
            raise RuntimeError("OverlayServer is not running")
        return f"http://{self._host}:{self._running.port}"

    async def start(self) -> None:
        if self._running is not None:
            return

        app = web.Application()
        app.router.add_get("/health", self._health)
        app.router.add_get("/overlay/{overlay_type}", self._overlay_page)
        app.router.add_get("/ws", self._ws)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=self._host, port=self._port)
        await site.start()

        # Find the actual port when binding to 0.
        sockets = getattr(site, "_server", None).sockets  # type: ignore[attr-defined]
        bound_port = int(sockets[0].getsockname()[1]) if sockets else self._port

        self._running = _Running(runner=runner, site=site, port=bound_port)

    async def stop(self) -> None:
        r = self._running
        if r is None:
            return
        self._running = None
        await r.runner.cleanup()

    async def _health(self, _req: web.Request) -> web.Response:
        return web.Response(text="ok", content_type="text/plain")

    async def _overlay_page(self, req: web.Request) -> web.Response:
        overlay_type = str(req.match_info.get("overlay_type") or "").strip()
        try:
            t = self._registry.get(overlay_type)
        except UnknownOverlayTypeError:
            raise web.HTTPNotFound(text="unknown overlay type")

        instance = normalize_instance_id(req.query.get("instance", ""))
        params: dict[str, Any] = {"instance": instance}
        html = t.render_html(params)
        return web.Response(text=html, content_type="text/html; charset=utf-8")

    async def _ws(self, req: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(req)

        msg = await ws.receive()
        if msg.type != web.WSMsgType.TEXT:
            await ws.close()
            return ws

        try:
            data = json.loads(msg.data)
        except json.JSONDecodeError:
            await ws.close()
            return ws

        if not isinstance(data, dict) or data.get("op") != "subscribe":
            await ws.close()
            return ws

        overlay_type = str(data.get("type") or "").strip()
        instance = normalize_instance_id(str(data.get("instance") or ""))
        params = data.get("params")
        if not isinstance(params, dict):
            params = {}
        params = dict(params)
        params["instance"] = instance

        try:
            t = self._registry.get(overlay_type)
        except UnknownOverlayTypeError:
            await ws.send_str(json.dumps({"op": "error", "message": "unknown overlay type"}))
            await ws.close()
            return ws

        state = t.initial_state(params)
        await ws.send_str(json.dumps(overlays_initial_state_msg(state), ensure_ascii=False))

        # Keep connection open (future: stream patches). For now, idle.
        while not ws.closed:
            nxt = await ws.receive()
            if nxt.type in (web.WSMsgType.CLOSE, web.WSMsgType.CLOSED, web.WSMsgType.ERROR):
                break
            await asyncio.sleep(0)

        return ws
```

- [ ] **Step 5: Run integration tests to verify they pass**

Run:

```bash
python -m pytest tests/test_overlays_server_integration.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/stream_cheremsha/overlays/server.py tests/test_overlays_server_integration.py pyproject.toml
git commit -m "feat: add localhost overlay server with debug overlay page and ws"
```

---

## Task 5: Wire overlay server into app lifecycle (start/stop)

**Files:**
- Modify: `src/stream_cheremsha/ui/main_window.py`
- (Optional) Modify: `src/stream_cheremsha/config/constants.py`

- [ ] **Step 1: Add overlay server fields to `MainWindow`**

In `MainWindow.__init__`, add:

- `self._overlay_registry = OverlayRegistry()`
- `self._overlay_server = OverlayServer(registry=self._overlay_registry, host="127.0.0.1", port=<default>)`

- [ ] **Step 2: Start overlay server during startup**

Where `MainWindow.run_startup()` or equivalent async startup exists, add:

```python
await self._overlay_server.start()
```

Expected: app starts with overlay server running.

- [ ] **Step 3: Stop overlay server on quit**

Hook into existing shutdown flow. If no explicit shutdown exists, connect to `aboutToQuit` and schedule `stop()` on the qasync loop.

Expected: process exits cleanly without dangling tasks.

- [ ] **Step 4: Manual smoke**

Run app, then open in browser:

- `http://127.0.0.1:<port>/health` → `ok`
- `http://127.0.0.1:<port>/overlay/debug?instance=default` → page loads

In OBS, add Browser Source with the debug overlay URL and confirm it renders.

- [ ] **Step 5: Commit**

```bash
git add src/stream_cheremsha/ui/main_window.py src/stream_cheremsha/config/constants.py
git commit -m "feat: start overlay server with app lifecycle"
```

---

## Task 6: Stream patches (WS) from pubsub (first real “live”)

**Files:**
- Modify: `src/stream_cheremsha/overlays/server.py`
- Modify: `src/stream_cheremsha/overlays/registry.py` (debug overlay subscribes)
- Modify: `src/stream_cheremsha/overlays/pubsub.py` (optional: unsubscribe hook)
- Test: `tests/test_overlays_server_integration.py`

- [ ] **Step 1: Extend integration test to expect at least one patch**

In `test_overlay_server_ws_initial_state`, after receiving `initial_state`, publish a patch into pubsub and assert WS receives it.

Example expected message:

```json
{ "op": "patch", "patch": { "tick": 1 } }
```

- [ ] **Step 2: Implement server-side streaming loop**

When a client subscribes, the server:

- sends `initial_state`
- subscribes to a pubsub topic such as `overlay:{type}:{instance}`
- forwards pubsub patches as `{"op":"patch","patch":...}` to WS

Ensure no deadlocks: publishing should never block the rest of the app.

- [ ] **Step 3: Implement debug overlay patch generator**

E.g. a small task in the server that periodically publishes a tick to `overlay:debug:<instance>` while there is at least one subscriber (or simply on a timer for v1).

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_overlays_server_integration.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/stream_cheremsha/overlays/server.py src/stream_cheremsha/overlays/registry.py tests/test_overlays_server_integration.py
git commit -m "feat: stream overlay patches over websocket"
```

---

## Task 7: Nuitka packaging verification (assets + aiohttp)

**Files:**
- Modify (if needed): `src/stream_cheremsha/build_nuitka.py`
- (Optional): add a small static asset under `src/stream_cheremsha/overlays/assets/` and include it

- [ ] **Step 1: Build a standalone binary**

Run:

```bash
cheremsha-build
```

Expected: build completes.

- [ ] **Step 2: Run the built app and verify overlay endpoints**

Run the binary, then open:

- `/health`
- `/overlay/debug?instance=default`

Expected: both work in the standalone distribution.

- [ ] **Step 3: If assets are missing, include them in Nuitka build rules**

Update the build script to include overlay assets/templates if you add them later (v1 debug overlay is inline, so this is mostly a future-proof step).

- [ ] **Step 4: Commit (only if changes needed)**

```bash
git add src/stream_cheremsha/build_nuitka.py src/stream_cheremsha/overlays/assets
git commit -m "build: include overlay server assets in Nuitka dist"
```

---

## Plan self-review (against spec)

- Spec coverage:
  - localhost-only: enforced by `host="127.0.0.1"` in `OverlayServer`
  - URL pages: `/overlay/<type>?instance=...` implemented in Task 4
  - health: `/health` implemented in Task 4
  - live updates: WS endpoint `/ws` implemented in Task 4 and patch streaming in Task 6
  - extensibility: registry + `debug` overlay in Task 2
  - tests: unit + integration in Tasks 1–4 and Task 6
- Placeholder scan:
  - No “TBD/TODO” steps; dependency addition guarded by an explicit check in Task 4.
  - Patch semantics are “shallow dict payload” for v1; future overlays can refine.

