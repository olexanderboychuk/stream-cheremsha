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
      .msg {{ margin: 0 0 8px 0; padding: 8px 10px; border-radius: 10px; display:flex; }}
      .msg {{ gap:6px; align-items: baseline; }}
      .author {{ font-weight: 700; margin-right: 6px; }}
      .platform {{ opacity: 0.9; margin-right: 2px; }}
      .picon {{ width: 14px; height: 14px; display:inline-flex; flex:0 0 auto; }}
      .picon {{ align-items:center; justify-content:center; }}
      .pimg {{ width: 14px; height: 14px; display:block; opacity: 0.92; }}

      .enter {{ animation: enter 180ms ease-out both; }}
      .exit {{ animation: exit 320ms ease-in both; }}
      @keyframes enter {{
        from {{ transform: translateY(6px); opacity: 0; }}
        to {{ transform: translateY(0); opacity: 1; }}
      }}
      @keyframes exit {{
        from {{ opacity: 1; }}
        to {{ opacity: 0; }}
      }}
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
        // items: array of message objects (id, author, text, platform, received_at)
        let items = [];
        const log = (...args) => {{ try {{ console.log('[chat-overlay]', ...args); }} catch (e) {{ }} }};
        let _id = 0;

        function clampInt(v, minV, maxV, defV) {{
          const n = Number(v);
          if (!Number.isFinite(n)) return defV;
          const i = Math.trunc(n);
          return Math.max(minV, Math.min(maxV, i));
        }}

        function hash32(s) {{
          // FNV-1a
          let h = 2166136261;
          for (let i = 0; i < s.length; i++) {{
            h ^= s.charCodeAt(i);
            h = Math.imul(h, 16777619);
          }}
          return h >>> 0;
        }}

        function autoUserColor(author) {{
          const h = hash32(String(author || ''));
          const hue = (h % 360);
          const sat = 72;
          const light = 62;
          return 'hsl(' + hue + 'deg ' + sat + '% ' + light + '%)';
        }}

        function platformColor(platform) {{
          const p = String(platform || '').toLowerCase();
          if (p === 'twitch') return '#a78bfa';
          if (p === 'youtube') return '#f87171';
          if (p === 'tiktok') return '#7dd3fc';
          return '#93c5fd';
        }}

        function usernameColor(it) {{
          const mode = String(cfg && cfg.username_color_mode || 'auto');
          if (mode === 'platform') return platformColor(it.platform);
          if (mode === 'custom') return String(cfg && cfg.username_color_custom || '#93c5fd');
          return autoUserColor(it.author);
        }}

        function platformIconEl(platform) {{
          const p = String(platform || '').toLowerCase();
          const img = document.createElement('img');
          img.className = 'pimg';
          const name = (p === 'twitch' || p === 'youtube' || p === 'tiktok') ? p : 'pulse';
          img.src = '/assets/' + name + '.svg';
          img.alt = p;
          return img;
        }}

        function applyCfg() {{
          if (!cfg) return;
          document.body.style.fontFamily = cfg.font_family || 'system-ui';
          document.body.style.fontSize = clampInt(cfg.font_size_px, 8, 96, 18) + 'px';
        }}

        function render() {{
          root.innerHTML = '';
          if (!cfg) return;
          const maxItems = clampInt(cfg.max_items, 1, 200, 12);
          const bubbleBg = cfg.bubble_bg_rgba || 'rgba(10,12,18,0.55)';
          const bubbleRadius = clampInt(cfg.bubble_radius_px, 0, 60, 10);
          const textColor = cfg.text_color || '#e5e7eb';
          const showPlatform = !!cfg.show_platform;
          const showPlatformIcon = !!cfg.show_platform_icon;
          const view = items.slice(-maxItems);
          for (const it of view) {{
            const row = document.createElement('div');
            row.className = 'msg';
            row.style.background = bubbleBg;
            row.style.borderRadius = bubbleRadius + 'px';
            row.style.color = textColor;

            if (showPlatformIcon) {{
              const ico = document.createElement('span');
              ico.className = 'picon';
              ico.appendChild(platformIconEl(it.platform));
              row.appendChild(ico);
            }}

            if (showPlatform) {{
              const pl = document.createElement('span');
              pl.className = 'platform';
              pl.textContent = '[' + (it.platform || '?') + ']';
              row.appendChild(pl);
            }}

            const a = document.createElement('span');
            a.className = 'author';
            a.style.color = usernameColor(it);
            a.textContent = (it.author || '—') + ':';
            row.appendChild(a);

            const t = document.createElement('span');
            t.textContent = it.text || '';
            row.appendChild(t);

            root.appendChild(row);
          }}
        }}

        function scheduleExit(id) {{
          if (!cfg) return;
          const fadeSeconds = Number(cfg.fade_seconds || 0);
          if (!Number.isFinite(fadeSeconds) || fadeSeconds <= 0) return;
          const ms = Math.max(0, Math.round(fadeSeconds * 1000));
          setTimeout(() => {{
            // Mark exiting, then remove.
            for (const node of root.children) {{
              if (node && node.dataset && node.dataset.mid === String(id)) {{
                node.classList.add('exit');
              }}
            }}
            setTimeout(() => {{
              items = items.filter(x => x.id !== id);
              render();
            }}, 360);
          }}, ms);
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
              const it = Object.assign({{}}, p.append);
              it.id = (++_id);
              items.push(it);
              // Prevent unbounded growth: keep a small buffer beyond visible window.
              const maxItems = Math.max(1, (cfg && cfg.max_items) ? cfg.max_items : 12);
              const cap = Math.max(25, maxItems * 5);
              if (items.length > cap) items = items.slice(-cap);
              render();
              // Add enter animation to last item.
              const last = root.lastElementChild;
              if (last) {{
                last.classList.add('enter');
                last.dataset.mid = String(it.id);
                requestAnimationFrame(() => {{
                  // Let animation play; keep class.
                }});
              }}
              scheduleExit(it.id);
            }}
            if (p.config) {{
              cfg = p.config;
              applyCfg();
              render();
            }}
          }}
        }};

        ws.onerror = () => {{
          log('ws error');
        }};
        ws.onclose = () => {{
          log('ws closed');
        }};
      }})();
    </script>
  </body>
</html>"""

    def initial_state(self, params: dict[str, Any]) -> dict[str, Any]:
        _ = params
        cfg = load_chat_config()
        return {"config": json.loads(chat_config_to_json_text(cfg)), "items": []}
