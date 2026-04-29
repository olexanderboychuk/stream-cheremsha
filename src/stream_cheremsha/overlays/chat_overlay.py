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
      html, body {{ margin: 0; padding: 0; background: transparent; overflow: hidden; height: 100%; }}
      body {{ font-family: system-ui, sans-serif; }}
      .wrap {{
        position: absolute;
        inset: 0;
        padding: 10px;
        box-sizing: border-box;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        justify-content: flex-end;
      }}
      .panel {{
        width: 100%;
        max-height: 100%;
        overflow: hidden;
        box-sizing: border-box;
      }}
      .msg {{ margin: 0 0 8px 0; padding: 8px 10px; border-radius: 10px; display:flex; }}
      .msg {{ gap:6px; align-items: baseline; }}
      .author {{ font-weight: 700; margin-right: 6px; }}
      .picon {{ width: 18px; height: 18px; display:inline-flex; flex:0 0 auto; }}
      .picon {{ align-items:center; justify-content:center; }}
      .pimg {{ width: 18px; height: 18px; display:block; opacity: 0.92; }}

      .enter {{ animation: enter 260ms cubic-bezier(0.2, 0.8, 0.2, 1) both; }}
      .exit {{ animation: exit 520ms cubic-bezier(0.4, 0, 0.2, 1) both; }}
      @keyframes enter {{
        from {{ transform: translateY(10px); opacity: 0; filter: blur(1px); }}
        to {{ transform: translateY(0); opacity: 1; }}
      }}
      @keyframes exit {{
        from {{ transform: translateY(0); opacity: 1; }}
        to {{ transform: translateY(-6px); opacity: 0; }}
      }}
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="panel" id="panel">
        <div id="root"></div>
      </div>
    </div>
    <script>
      (function() {{
        const root = document.getElementById('root');
        const panel = document.getElementById('panel');
        const wsUrl = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws';
        let ws = null;
        let tries = 0;
        let cfg = null;
        // items: array of message objects (id, author, text, platform, received_at)
        let items = [];
        const log = (...args) => {{ try {{ console.log('[chat-overlay]', ...args); }} catch (e) {{ }} }};
        let _id = 0;

        function ensureCompat() {{
          if (!Number.isFinite) {{
            Number.isFinite = function(n) {{ return typeof n === 'number' && isFinite(n); }};
          }}
          if (!Math.trunc) {{
            Math.trunc = function(n) {{ return n < 0 ? Math.ceil(n) : Math.floor(n); }};
          }}
        }}

        function showFatal(err) {{
          try {{
            const pre = document.createElement('pre');
            pre.style.position = 'absolute';
            pre.style.left = '0';
            pre.style.top = '0';
            pre.style.right = '0';
            pre.style.background = 'rgba(120,0,0,0.65)';
            pre.style.color = '#fff';
            pre.style.padding = '8px 10px';
            pre.style.margin = '0';
            pre.style.fontSize = '12px';
            pre.style.whiteSpace = 'pre-wrap';
            pre.textContent = 'chat overlay error: ' + String(err && (err.stack || err.message) || err);
            document.body.appendChild(pre);
          }} catch (e) {{ }}
        }}

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
          // Use legacy hsl() syntax for older embedded browsers (OBS CEF).
          return 'hsl(' + hue + ', ' + sat + '%, ' + light + '%)';
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

        function applyTextShadow(nodes) {{
          if (!cfg || !cfg.text_shadow_enabled) {{
            for (let i = 0; i < nodes.length; i++) {{
              const el = nodes[i];
              if (el && el.style) el.style.textShadow = '';
            }}
            return;
          }}
          const blur = clampInt(cfg.text_shadow_blur_px, 0, 24, 4);
          const ox = clampInt(cfg.text_shadow_offset_x_px, -12, 12, 0);
          const oy = clampInt(cfg.text_shadow_offset_y_px, -12, 12, 1);
          const col = String(cfg.text_shadow_rgba || 'rgba(0,0,0,0.65)');
          const ts = ox + 'px ' + oy + 'px ' + blur + 'px ' + col;
          for (let i = 0; i < nodes.length; i++) {{
            const el = nodes[i];
            if (el && el.style) el.style.textShadow = ts;
          }}
        }}

        function applyCfg() {{
          if (!cfg) return;
          document.body.style.fontFamily = cfg.font_family || 'system-ui';
          document.body.style.fontSize = clampInt(cfg.font_size_px, 8, 96, 18) + 'px';
          const on = !!cfg.widget_bg_enabled;
          const pad = on ? clampInt(cfg.widget_bg_padding_px, 0, 48, 10) : 0;
          const rad = on ? clampInt(cfg.widget_bg_radius_px, 0, 60, 14) : 0;
          panel.style.padding = pad + 'px';
          panel.style.borderRadius = rad + 'px';
          panel.style.background = on ? String(cfg.widget_bg_rgba || 'rgba(10,12,18,0.45)') : 'transparent';
        }}

        function render() {{
          root.innerHTML = '';
          if (!cfg) return;
          const maxItems = clampInt(cfg.max_items, 1, 200, 12);
          const bubbleBg = cfg.bubble_bg_rgba || 'rgba(10,12,18,0.55)';
          const bubbleRadius = clampInt(cfg.bubble_radius_px, 0, 60, 10);
          const textColor = cfg.text_color || '#e5e7eb';
          const showPlatformIcon = !!cfg.show_platform_icon;
          const view = items.slice(-maxItems);
          for (const it of view) {{
            const row = document.createElement('div');
            row.className = 'msg';
            row.dataset.mid = String(it.id || '');
            row.style.background = bubbleBg;
            row.style.borderRadius = bubbleRadius + 'px';
            row.style.color = textColor;

            if (showPlatformIcon) {{
              const ico = document.createElement('span');
              ico.className = 'picon';
              ico.appendChild(platformIconEl(it.platform));
              row.appendChild(ico);
            }}

            const a = document.createElement('span');
            a.className = 'author';
            a.style.color = usernameColor(it);
            a.textContent = (it.author || '—') + ':';
            row.appendChild(a);

            const t = document.createElement('span');
            t.textContent = it.text || '';
            row.appendChild(t);

            applyTextShadow([a, t]);

            root.appendChild(row);
          }}
        }}

        function findNodeById(id) {{
          const sid = String(id);
          for (let i = 0; i < root.children.length; i++) {{
            const node = root.children[i];
            if (node && node.dataset && node.dataset.mid === sid) return node;
          }}
          return null;
        }}

        function removeItemById(id) {{
          const sid = String(id);
          items = items.filter(x => String(x.id) !== sid);
        }}

        function scheduleExit(id) {{
          if (!cfg) return;
          const fadeSeconds = Number(cfg.fade_seconds || 0);
          if (!Number.isFinite(fadeSeconds) || fadeSeconds <= 0) return;
          const ms = Math.max(0, Math.round(fadeSeconds * 1000));
          setTimeout(() => {{
            // Mark exiting in-place so the animation can actually play in OBS.
            const node = findNodeById(id);
            if (node) {{
              node.classList.add('exit');
              setTimeout(() => {{
                try {{ if (node && node.parentNode) node.parentNode.removeChild(node); }} catch (e) {{ }}
                removeItemById(id);
              }}, 560);
              return;
            }}
            // Fallback: if node isn't found (e.g. rerendered), just drop the item.
            removeItemById(id);
          }}, ms);
        }}

        try {{
          ensureCompat();
          window.addEventListener('error', (ev) => {{
            showFatal(ev && (ev.error || ev.message) || 'unknown error');
          }});
        }} catch (e) {{ }}

        function connect() {{
          tries += 1;
          const backoff = Math.min(5000, 250 + Math.floor(Math.random() * 250) + (tries * 350));
          try {{
            ws = new WebSocket(wsUrl);
          }} catch (e) {{
            showFatal('ws create failed');
            setTimeout(connect, backoff);
            return;
          }}

          ws.onopen = () => {{
            try {{
              tries = 0;
              const subscribeMsg = {_json_for_script(subscribe_msg)};
              ws.send(JSON.stringify(subscribeMsg));
            }} catch (e) {{
              showFatal(e);
            }}
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
            setTimeout(connect, backoff);
          }};
        }}

        connect();
      }})();
    </script>
  </body>
</html>"""

    def initial_state(self, params: dict[str, Any]) -> dict[str, Any]:
        _ = params
        cfg = load_chat_config()
        return {"config": json.loads(chat_config_to_json_text(cfg)), "items": []}
