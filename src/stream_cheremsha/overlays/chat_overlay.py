from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, TypedDict

from stream_cheremsha.domain.models import ChatMessage
from stream_cheremsha.overlays.chat_config import chat_config_to_json_text, load_chat_config
from stream_cheremsha.overlays.models import normalize_instance_id


class _ChatAppendPatch(TypedDict):
    author: str
    text: str
    platform: str
    received_at: str


class ChatPatch(TypedDict):
    append: _ChatAppendPatch


def _json_for_script(value: Any) -> str:
    s = json.dumps(value, ensure_ascii=False)
    return s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def _iso_utc_z(dt: datetime) -> str:
    # Defensive: treat naive datetimes as UTC rather than crashing on astimezone().
    if dt.tzinfo is None or dt.utcoffset() is None:
        dtu = dt.replace(tzinfo=UTC)
    else:
        dtu = dt.astimezone(UTC)
    return dtu.isoformat(timespec="seconds").replace("+00:00", "Z")


def chat_message_to_patch(msg: ChatMessage) -> ChatPatch:
    return {
        "append": {
            "author": str(msg.author),
            "text": str(msg.text),
            "platform": str(msg.platform.value),
            "received_at": _iso_utc_z(msg.received_at),
        }
    }


class ChatOverlayType:
    type = "chat"

    def render_html(self, params: dict[str, Any]) -> str:
        raw_instance = params.get("instance")
        try:
            instance = normalize_instance_id(str(raw_instance or ""))
        except ValueError:
            instance = "default"

        subscribe_msg = {"op": "subscribe", "type": "chat", "instance": instance, "params": {}}

        return f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Chat Overlay</title>
    <style>
      html, body {{ margin: 0; padding: 0; background: transparent; overflow: hidden; }}
      body {{ font-family: system-ui, sans-serif; }}
      .wrap {{ padding: 10px; }}
      .msg {{ margin: 0 0 8px 0; padding: 8px 10px; border-radius: 10px; }}
      .author {{ font-weight: 700; margin-right: 6px; }}
      .platform {{ opacity: 0.85; margin-right: 6px; }}
    </style>
  </head>
  <body>
    <div class="wrap" id="root"></div>
    <script>
      (function() {{
        const root = document.getElementById('root');
        const wsUrl = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws';
        const ws = new WebSocket(wsUrl);
        let cfg = null;
        let items = [];

        function applyCfg() {{
          if (!cfg) return;
          document.body.style.fontFamily = cfg.font_family || 'system-ui';
          document.body.style.fontSize = (cfg.font_size_px || 18) + 'px';
        }}

        function render() {{
          root.innerHTML = '';
          if (!cfg) return;
          const maxItems = Math.max(1, cfg.max_items || 12);
          const bg = cfg.bg_rgba || 'rgba(10,12,18,0.55)';
          const authorColor = cfg.author_color || '#93c5fd';
          const textColor = cfg.text_color || '#e5e7eb';
          const showPlatform = !!cfg.show_platform;
          const view = items.slice(-maxItems);
          for (const it of view) {{
            const row = document.createElement('div');
            row.className = 'msg';
            row.style.background = bg;
            row.style.color = textColor;

            if (showPlatform) {{
              const pl = document.createElement('span');
              pl.className = 'platform';
              pl.textContent = '[' + (it.platform || '?') + ']';
              row.appendChild(pl);
            }}

            const a = document.createElement('span');
            a.className = 'author';
            a.style.color = authorColor;
            a.textContent = (it.author || '—') + ':';
            row.appendChild(a);

            const t = document.createElement('span');
            t.textContent = it.text || '';
            row.appendChild(t);

            root.appendChild(row);
          }}
        }}

        ws.onopen = () => {{
          const subscribeMsg = {_json_for_script(subscribe_msg)};
          ws.send(JSON.stringify(subscribeMsg));
        }};

        ws.onmessage = (ev) => {{
          let obj = null;
          try {{ obj = JSON.parse(ev.data); }} catch (e) {{ return; }}
          if (!obj || !obj.op) return;
          if (obj.op === 'initial_state') {{
            cfg = (obj.state && obj.state.config) ? obj.state.config : null;
            items = (obj.state && obj.state.items) ? obj.state.items : [];
            applyCfg();
            render();
            return;
          }}
          if (obj.op === 'patch') {{
            const p = obj.patch || {{}};
            if (p.append) {{
              items.push(p.append);
              render();
            }}
            if (p.config) {{
              cfg = p.config;
              applyCfg();
              render();
            }}
          }}
        }};
      }})();
    </script>
  </body>
</html>"""

    def initial_state(self, params: dict[str, Any]) -> dict[str, Any]:
        _ = params
        cfg = load_chat_config()
        return {"config": json.loads(chat_config_to_json_text(cfg)), "items": []}
