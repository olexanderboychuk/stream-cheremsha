from __future__ import annotations

import html
import json
from typing import Any
from urllib.parse import quote

from stream_cheremsha.overlays.layout import load_layouts, normalize_layout_id


class LayoutOverlayType:
    type = "layout"

    def render_html(self, params: dict[str, Any]) -> str:
        instance = str(params.get("instance") or "main")
        requested = normalize_layout_id(str(params.get("layout") or "default"))
        layouts = load_layouts()
        layout = next((x for x in layouts if x.id == requested), None) or layouts[0]
        frames: list[str] = []
        signal_system_instances: list[str] = []
        for widget in sorted(layout.widgets, key=lambda x: x.z_index):
            if not widget.visible:
                continue
            widget_instance = quote(widget.instance or instance, safe="")
            src = f"/overlay/{quote(widget.type, safe='')}?instance={widget_instance}"
            frames.append(
                f'<iframe class="widget" title="{html.escape(widget.id)}" '
                f'style="left:{widget.x}px;top:{widget.y}px;width:{widget.width}px;'
                f'height:{widget.height}px;z-index:{widget.z_index}" src="{src}"></iframe>'
            )
            if widget.type == "signal_system":
                signal_system_instances.append(widget_instance)
        safe_instances_json = json.dumps(signal_system_instances)
        safe_instance = html.escape(instance)
        safe_requested = html.escape(requested)
        return f"""<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width={layout.width},height={layout.height}">
<title>{html.escape(layout.name)}</title>
<style>
html,body {{ margin:0; width:100%; height:100%; overflow:hidden; background:transparent; }}
.canvas {{ position:relative; width:{layout.width}px; height:{layout.height}px;
 transform-origin:top left; }}
.widget {{ position:absolute; display:block; border:0; background:transparent; overflow:hidden; }}
</style></head><body><div class="canvas">{"".join(frames)}</div>
<script>
const canvas = document.querySelector('.canvas');
function scale() {{
 const s=Math.min(innerWidth/{layout.width}, innerHeight/{layout.height});
 canvas.style.transform=`scale(${{s}})`;
}}
addEventListener('resize', scale); scale();

(function() {{
  var signalSystemInstances = {safe_instances_json};
  var proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  var wsUrl = proto + '//' + location.host + '/ws';
  var ws;
  function connect() {{
    ws = new WebSocket(wsUrl);
    ws.onopen = function() {{
      ws.send(JSON.stringify({{op: "subscribe", type: "layout", instance: "{safe_instance}", params: {{layout: "{safe_requested}"}}}}));
    }};
    ws.onmessage = function(ev) {{
      try {{
        var msg = JSON.parse(ev.data);
        if (msg && msg.op === 'patch') {{
          var forwarded = false;
          var widgets = document.querySelectorAll('.widget');
          for (var i = 0; i < widgets.length; i++) {{
            var w = widgets[i];
            try {{
              var wSrc = w.getAttribute('src') || '';
              if (wSrc.indexOf('/overlay/signal_system') === 0) {{
                try {{ w.contentWindow.postMessage({{op: 'patch', patch: msg.patch}}, '*'); forwarded = true; }} catch(e) {{}}
              }}
            }} catch(e) {{}}
          }}
          if (!forwarded) {{
            location.reload();
          }}
        }}
      }} catch(e) {{}}
    }};
    ws.onclose = function() {{
      setTimeout(connect, 2000);
    }};
  }}
  connect();
}})();
</script></body></html>"""

    def initial_state(self, params: dict[str, Any]) -> dict[str, Any]:
        return {"params": dict(params)}
