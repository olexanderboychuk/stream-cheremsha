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
      html, body {{
        margin: 0; padding: 0; background: transparent; overflow: hidden; height: 100%;
      }}
      body {{ font-family: system-ui, sans-serif; position: relative; }}
      .wrap {{
        position: absolute; inset: 0; padding: 10px; box-sizing: border-box;
        overflow: hidden; display: flex; flex-direction: column; justify-content: flex-end;
      }}
      .panel {{
        flex: 1 1 auto; width: 100%; height: 100%; max-height: 100%; overflow: hidden;
        box-sizing: border-box; display: flex; flex-direction: column; justify-content: flex-end;
      }}
      .msg {{ margin: 0 0 8px 0; padding: 8px 10px; border-radius: 10px; display:flex; gap:6px; align-items: baseline; }}
      .author {{ font-weight: 700; margin-right: 6px; }}
      .author.vip-gold {{
        color: #fde68a !important;
        text-shadow: 0 0 10px rgba(250,204,21,0.85), 0 0 18px rgba(234,179,8,0.55);
      }}
      .picon {{ width: 18px; height: 18px; display:inline-flex; flex:0 0 auto; align-items:center; justify-content:center; }}
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

      /* === THEME: INFERNO === */
      body[data-theme="inferno"] {{
        font-family: 'Impact', 'Arial Black', sans-serif;
        text-transform: uppercase;
        letter-spacing: 1px;
      }}
      body[data-theme="inferno"] .msg {{
        background: linear-gradient(135deg, rgba(30,0,0,0.85) 0%, rgba(80,20,0,0.7) 100%) !important;
        border: 1px solid rgba(255,80,0,0.4);
        border-left: 3px solid #ff4500;
        border-radius: 2px 8px 8px 2px;
        box-shadow: 0 0 12px rgba(255,60,0,0.3), inset 0 0 20px rgba(255,40,0,0.08);
        margin: 0 0 10px 0; padding: 10px 14px;
      }}
      body[data-theme="inferno"] .author {{
        color: #ff6a00 !important;
        text-shadow: 0 0 8px rgba(255,100,0,0.8), 0 0 16px rgba(255,50,0,0.4);
      }}
      body[data-theme="inferno"] .msg span:not(.author) {{
        color: #ffe0c0;
        text-shadow: 0 0 4px rgba(255,140,0,0.3);
      }}
      body[data-theme="inferno"] .panel::before {{
        content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 120px;
        background: linear-gradient(to top, rgba(255,60,0,0.08) 0%, transparent 100%);
        pointer-events: none;
      }}
      body[data-theme="inferno"] .enter {{
        animation: infernoEnter 300ms cubic-bezier(0.2, 0.8, 0.2, 1) both;
      }}
      @keyframes infernoEnter {{
        from {{ transform: translateY(14px) scale(0.97); opacity: 0; filter: blur(2px) brightness(2); }}
        to {{ transform: translateY(0) scale(1); opacity: 1; filter: blur(0) brightness(1); }}
      }}

      /* === THEME: ABYSS === */
      body[data-theme="abyss"] {{
        font-family: 'Georgia', 'Palatino', serif;
        letter-spacing: 0.5px;
      }}
      body[data-theme="abyss"] .msg {{
        background: linear-gradient(180deg, rgba(5,10,30,0.7) 0%, rgba(10,20,50,0.5) 100%) !important;
        border: 1px solid rgba(0,200,255,0.15);
        border-radius: 20px;
        box-shadow: 0 4px 30px rgba(0,100,200,0.15), inset 0 1px 0 rgba(0,200,255,0.1);
        margin: 0 0 12px 0; padding: 12px 16px;
      }}
      body[data-theme="abyss"] .author {{
        color: #00d4ff !important;
        font-style: italic;
        text-shadow: 0 0 12px rgba(0,200,255,0.6), 0 0 24px rgba(0,150,255,0.3);
      }}
      body[data-theme="abyss"] .msg span:not(.author) {{
        color: #c8e8ff;
        text-shadow: 0 0 6px rgba(100,180,255,0.2);
      }}
      body[data-theme="abyss"] .panel::before {{
        content: ''; position: absolute; inset: 0;
        background: radial-gradient(ellipse at 50% 100%, rgba(0,100,200,0.06) 0%, transparent 60%);
        pointer-events: none;
      }}
      body[data-theme="abyss"] .panel::after {{
        content: ''; position: absolute; inset: 0;
        background: radial-gradient(ellipse at 30% 20%, rgba(100,0,200,0.04) 0%, transparent 50%);
        pointer-events: none;
      }}
      body[data-theme="abyss"] .enter {{
        animation: abyssEnter 400ms cubic-bezier(0.16, 1, 0.3, 1) both;
      }}
      @keyframes abyssEnter {{
        from {{ transform: translateY(20px); opacity: 0; filter: blur(4px); }}
        to {{ transform: translateY(0); opacity: 1; filter: blur(0); }}
      }}

      /* === THEME: IMPERIAL === */
      body[data-theme="imperial"] {{
        font-family: 'Georgia', 'Times New Roman', serif;
        letter-spacing: 0.3px;
      }}
      body[data-theme="imperial"] .msg {{
        background: linear-gradient(135deg, rgba(20,10,40,0.85) 0%, rgba(35,20,60,0.7) 100%) !important;
        border: 1px solid rgba(212,175,55,0.35);
        border-radius: 4px;
        box-shadow: 0 2px 12px rgba(212,175,55,0.1), inset 0 1px 0 rgba(255,255,255,0.05);
        margin: 0 0 10px 0; padding: 10px 16px;
        position: relative;
      }}
      body[data-theme="imperial"] .msg::before {{
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
        background: linear-gradient(90deg, transparent 0%, rgba(212,175,55,0.5) 50%, transparent 100%);
      }}
      body[data-theme="imperial"] .author {{
        color: #d4af37 !important;
        text-shadow: 0 0 6px rgba(212,175,55,0.4);
      }}
      body[data-theme="imperial"] .msg span:not(.author) {{
        color: #f0e6d2;
      }}
      body[data-theme="imperial"] .panel::before {{
        content: ''; position: absolute; inset: 8px; pointer-events: none;
        border: 1px solid rgba(212,175,55,0.12); border-radius: 6px;
      }}
      body[data-theme="imperial"] .enter {{
        animation: imperialEnter 350ms cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
      }}
      @keyframes imperialEnter {{
        from {{ transform: translateY(8px); opacity: 0; }}
        to {{ transform: translateY(0); opacity: 1; }}
      }}

      /* === THEME: CYBER === */
      body[data-theme="cyber"] {{
        font-family: 'Courier New', 'Consolas', monospace;
        text-transform: lowercase;
      }}
      body[data-theme="cyber"] .msg {{
        background: rgba(0,5,0,0.75) !important;
        border: none;
        border-left: 2px solid #00ff41;
        border-radius: 0;
        box-shadow: none;
        margin: 0 0 6px 0; padding: 6px 12px;
        position: relative;
      }}
      body[data-theme="cyber"] .msg::after {{
        content: '>_'; position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
        color: rgba(0,255,65,0.3); font-size: 0.7em;
      }}
      body[data-theme="cyber"] .author {{
        color: #00ff41 !important;
        text-shadow: 0 0 6px rgba(0,255,65,0.6);
      }}
      body[data-theme="cyber"] .msg span:not(.author) {{
        color: #b0ffb0;
      }}
      body[data-theme="cyber"] .panel::before {{
        content: ''; position: absolute; inset: 0; pointer-events: none;
        background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,255,65,0.015) 2px, rgba(0,255,65,0.015) 4px);
      }}
      body[data-theme="cyber"] .panel::after {{
        content: ''; position: absolute; inset: 0; pointer-events: none;
        background: linear-gradient(90deg, transparent 0%, rgba(255,0,255,0.03) 50%, transparent 100%);
      }}
      body[data-theme="cyber"] .enter {{
        animation: cyberEnter 180ms steps(3, end) both;
      }}
      @keyframes cyberEnter {{
        from {{ opacity: 0; clip-path: inset(0 100% 0 0); }}
        to {{ opacity: 1; clip-path: inset(0 0 0 0); }}
      }}

      /* === THEME: FROST === */
      body[data-theme="frost"] {{
        font-family: 'Segoe UI', 'Helvetica Neue', sans-serif;
        letter-spacing: 0.5px;
      }}
      body[data-theme="frost"] .msg {{
        background: linear-gradient(135deg, rgba(200,230,255,0.12) 0%, rgba(180,210,240,0.06) 100%) !important;
        border: 1px solid rgba(200,230,255,0.25);
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(150,200,255,0.1), inset 0 1px 0 rgba(255,255,255,0.15);
        margin: 0 0 10px 0; padding: 10px 16px;
        backdrop-filter: blur(4px);
      }}
      body[data-theme="frost"] .author {{
        color: #87ceeb !important;
        text-shadow: 0 0 8px rgba(135,206,235,0.5), 0 0 16px rgba(100,180,255,0.2);
      }}
      body[data-theme="frost"] .msg span:not(.author) {{
        color: #e8f4ff;
        text-shadow: 0 1px 2px rgba(0,0,0,0.3);
      }}
      body[data-theme="frost"] .panel::before {{
        content: ''; position: absolute; inset: 0; pointer-events: none;
        background: radial-gradient(ellipse at 50% 50%, rgba(200,230,255,0.03) 0%, transparent 70%);
      }}
      body[data-theme="frost"] .enter {{
        animation: frostEnter 350ms cubic-bezier(0.34, 1.56, 0.64, 1) both;
      }}
      @keyframes frostEnter {{
        from {{ transform: translateY(12px) scale(0.98); opacity: 0; filter: blur(3px); }}
        to {{ transform: translateY(0) scale(1); opacity: 1; filter: blur(0); }}
      }}

      /* === THEME: BLOODMOON === */
      body[data-theme="bloodmoon"] {{
        font-family: 'Georgia', 'Palatino Linotype', serif;
        letter-spacing: 0.5px;
      }}
      body[data-theme="bloodmoon"] .msg {{
        background: linear-gradient(180deg, rgba(20,0,5,0.9) 0%, rgba(40,0,10,0.7) 100%) !important;
        border: 1px solid rgba(139,0,0,0.4);
        border-radius: 2px;
        box-shadow: 0 2px 16px rgba(139,0,0,0.2), inset 0 -8px 16px rgba(80,0,0,0.1);
        margin: 0 0 10px 0; padding: 10px 14px;
      }}
      body[data-theme="bloodmoon"] .msg::after {{
        content: ''; position: absolute; bottom: -2px; left: 10%; width: 80%; height: 3px;
        background: linear-gradient(90deg, transparent 0%, rgba(139,0,0,0.4) 50%, transparent 100%);
        border-radius: 50%;
      }}
      body[data-theme="bloodmoon"] .author {{
        color: #dc143c !important;
        text-shadow: 0 0 8px rgba(220,20,60,0.5), 0 2px 4px rgba(0,0,0,0.8);
      }}
      body[data-theme="bloodmoon"] .msg span:not(.author) {{
        color: #d4c4c4;
        text-shadow: 0 1px 3px rgba(0,0,0,0.6);
      }}
      body[data-theme="bloodmoon"] .panel::before {{
        content: ''; position: absolute; inset: 0; pointer-events: none;
        background: radial-gradient(ellipse at 50% 0%, rgba(139,0,0,0.06) 0%, transparent 50%);
      }}
      body[data-theme="bloodmoon"] .enter {{
        animation: bloodmoonEnter 300ms cubic-bezier(0.2, 0.8, 0.2, 1) both;
      }}
      @keyframes bloodmoonEnter {{
        from {{ transform: translateY(6px); opacity: 0; filter: blur(1px) saturate(0.5); }}
        to {{ transform: translateY(0); opacity: 1; filter: blur(0) saturate(1); }}
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
        const wsUrl =
          (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws';
        let ws = null;
        const RECONNECT_MS = 5000;
        let cfg = null;
        // items: array of message objects (id, author, text, platform, received_at)
        let items = [];
        const log = (...args) => {{
          try {{ console.log('[chat-overlay]', ...args); }}
          catch (e) {{ }}
        }};
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
            pre.textContent = 'chat overlay error: '
              + String(err && (err.stack || err.message) || err);
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

        function platformAllowed(platform) {{
          const p = String(platform || '').toLowerCase();
          if (!cfg) return true;
          const key = 'platform_' + p + '_enabled';
          if (Object.prototype.hasOwnProperty.call(cfg, key)) return !!cfg[key];
          return true;
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
          const theme = String(cfg.theme || 'classic');
          document.body.dataset.theme = theme;
          if (theme === 'classic') {{
            document.body.style.fontFamily = cfg.font_family || 'system-ui';
          }}
          document.body.style.fontSize = clampInt(cfg.font_size_px, 8, 96, 18) + 'px';
          const on = !!cfg.widget_bg_enabled;
          const pad = on ? clampInt(cfg.widget_bg_padding_px, 0, 48, 10) : 0;
          const rad = on ? clampInt(cfg.widget_bg_radius_px, 0, 60, 14) : 0;
          panel.style.width = '100%';
          panel.style.height = '100%';
          panel.style.padding = pad + 'px';
          panel.style.borderRadius = rad + 'px';
          panel.style.background = on
            ? String(cfg.widget_bg_rgba || 'rgba(10,12,18,0.45)')
            : 'transparent';
        }}

        function render() {{
          root.innerHTML = '';
          if (!cfg) return;
          const maxItems = clampInt(cfg.max_items, 1, 200, 12);
          const bubbleOn = (cfg.bubble_bg_enabled !== undefined) ? !!cfg.bubble_bg_enabled : true;
          const bubbleBg = bubbleOn ? (cfg.bubble_bg_rgba || 'rgba(10,12,18,0.55)') : 'transparent';
          const bubbleRadius = bubbleOn ? clampInt(cfg.bubble_radius_px, 0, 60, 10) : 0;
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
            a.className = 'author' + (it.vip_gold ? ' vip-gold' : '');
            if (!it.vip_gold) a.style.color = usernameColor(it);
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
                try {{
                  if (node && node.parentNode) node.parentNode.removeChild(node);
                }} catch (e) {{ }}
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
          try {{
            ws = new WebSocket(wsUrl);
          }} catch (e) {{
            showFatal('ws create failed');
            setTimeout(connect, RECONNECT_MS);
            return;
          }}

          ws.onopen = () => {{
            try {{
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
              items = items.filter(x => platformAllowed(x.platform));
              applyCfg();
              render();
              return;
            }}
            if (obj.op === 'patch') {{
              const p = obj.patch || {{}};
              if (p.append) {{
                const it = Object.assign({{}}, p.append);
                if (!platformAllowed(it.platform)) return;
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
                items = items.filter(x => platformAllowed(x.platform));
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
            setTimeout(connect, RECONNECT_MS);
          }};
        }}

        connect();
      }})();
    </script>
  </body>
</html>"""

    def initial_state(self, params: dict[str, Any]) -> dict[str, Any]:
        from stream_cheremsha.overlays.widget_instances import config_for_type

        cfg_dict = config_for_type("chat", params, load_chat_config, chat_config_to_json_text)
        return {"config": cfg_dict, "items": []}
