from __future__ import annotations

import json
from typing import Any

from stream_cheremsha.overlays.models import normalize_instance_id


def _json_for_script(value: Any) -> str:
    s = json.dumps(value, ensure_ascii=False)
    return s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


class ActivityOverlayType:
    type = "activity"

    def render_html(self, params: dict[str, Any]) -> str:
        raw_instance = str(params.get("instance") or "")
        instance = normalize_instance_id(raw_instance)
        sub = {"op": "subscribe", "type": "activity", "instance": instance, "params": {}}
        return f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Activity</title>
  </head>
  <body>
    <script>
      (function() {{
        const wsUrl = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws';
        const ws = new WebSocket(wsUrl);
        ws.onopen = () => ws.send(JSON.stringify({_json_for_script(sub)}));
      }})();
    </script>
  </body>
</html>"""

    def initial_state(self, params: dict[str, Any]) -> dict[str, Any]:
        _ = normalize_instance_id(str(params.get("instance") or ""))
        return {"items": []}

