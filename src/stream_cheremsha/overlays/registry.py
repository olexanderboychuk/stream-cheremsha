from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

from stream_cheremsha.overlays.models import normalize_instance_id


class UnknownOverlayTypeError(KeyError):
    pass


class OverlayType(Protocol):
    type: str

    def render_html(self, params: dict[str, Any]) -> str: ...

    def initial_state(self, params: dict[str, Any]) -> dict[str, Any]: ...


def _json_for_script(value: Any) -> str:
    s = json.dumps(value, ensure_ascii=False)
    # Prevent `</script>` termination and other HTML parser edge-cases.
    return s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


@dataclass(frozen=True, slots=True)
class _DebugOverlayType:
    type: str = "debug"

    def render_html(self, params: dict[str, Any]) -> str:
        raw_instance = params.get("instance")
        try:
            instance = normalize_instance_id(str(raw_instance or ""))
        except ValueError:
            instance = "default"

        subscribe_msg = {"op": "subscribe", "type": "debug", "instance": instance, "params": {}}

        return f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Overlay Debug</title>
    <style>
      html, body {{ margin: 0; padding: 0; background: transparent; color: #e5e7eb;
        font-family: system-ui, sans-serif; }}
      .box {{ padding: 10px; background: rgba(10,12,18,0.60); border: 1px solid rgba(148,163,184,0.25); }}
      pre {{ white-space: pre-wrap; word-break: break-word; margin: 8px 0 0; }}
    </style>
  </head>
  <body>
    <div class="box">
      <div><strong>overlay:</strong> debug</div>
      <div><strong>instance:</strong> <span id="instance"></span></div>
      <pre id="log">connecting…</pre>
    </div>
    <script>
      (function() {{
        const instance = {_json_for_script(instance)};
        document.getElementById('instance').textContent = instance;

        const log = document.getElementById('log');
        const wsUrl = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws';
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {{
          const subscribeMsg = {_json_for_script(subscribe_msg)};
          ws.send(JSON.stringify(subscribeMsg));
          log.textContent = 'connected';
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
        return {"params": dict(params)}


class OverlayRegistry:
    def __init__(self) -> None:
        self._types: dict[str, OverlayType] = {}
        self.register(_DebugOverlayType())

    def register(self, t: OverlayType) -> None:
        self._types[str(t.type)] = t

    def get(self, overlay_type: str) -> OverlayType:
        k = str(overlay_type or "").strip()
        t = self._types.get(k)
        if t is None:
            raise UnknownOverlayTypeError(k)
        return t
