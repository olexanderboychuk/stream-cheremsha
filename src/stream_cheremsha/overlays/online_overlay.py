from __future__ import annotations

# ruff: noqa: E501
import base64
import json
from pathlib import Path
from typing import Any

from stream_cheremsha.overlays.models import normalize_instance_id
from stream_cheremsha.overlays.online_overlay_config import (
    load_online_overlay_config,
    online_overlay_config_to_json_text,
)


def _json_for_script(value: Any) -> str:
    s = json.dumps(value, ensure_ascii=False)
    return s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def _platform_icons_data_uris() -> dict[str, str]:
    base = Path(__file__).resolve().parents[1] / "assets"
    out: dict[str, str] = {}
    for slug in ("tiktok", "twitch", "youtube", "kick"):
        p = base / f"{slug}.svg"
        if not p.is_file():
            continue
        raw = p.read_bytes()
        b64 = base64.standard_b64encode(raw).decode("ascii")
        out[slug] = f"data:image/svg+xml;base64,{b64}"
    return out


class OnlineOverlayType:
    type = "online"

    def render_html(self, params: dict[str, Any]) -> str:
        raw_instance = params.get("instance")
        try:
            instance = normalize_instance_id(str(raw_instance or ""))
        except ValueError:
            instance = "default"

        subscribe_msg = {"op": "subscribe", "type": "online", "instance": instance, "params": {}}
        platform_icons_js = _json_for_script(_platform_icons_data_uris())

        return f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Online Overlay</title>
    <style>
      html, body {{ margin: 0; padding: 0; background: transparent; overflow: hidden; height: 100%; }}
      body {{ font-family: system-ui, sans-serif; }}
      .wrap {{
        position: absolute;
        inset: 0;
        padding: 12px;
        box-sizing: border-box;
        display: flex;
        align-items: center;
        justify-content: center;
      }}
      .card {{
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 8px;
        padding: 14px 18px;
        border-radius: 14px;
        background: rgba(10,12,18,0.45);
        border: 1px solid rgba(148,163,184,0.20);
        color: #e5e7eb;
        min-width: 0;
      }}
      .row-combined {{
        display: flex;
        flex-direction: row;
        align-items: center;
        justify-content: center;
        gap: 0;
        flex-wrap: wrap;
      }}
      .icons {{
        display: flex;
        flex-direction: row;
        align-items: center;
        gap: 6px;
      }}
      .plat-icon {{
        display: block;
        opacity: 0.92;
        filter: drop-shadow(0 1px 2px rgba(0,0,0,0.35));
      }}
      .split-wrap {{
        display: flex;
        flex-direction: column;
        align-items: stretch;
        gap: 8px;
        width: 100%;
      }}
      .plat-row {{
        display: flex;
        flex-direction: row;
        align-items: center;
        justify-content: flex-start;
        gap: 10px;
      }}
      .num {{
        font-weight: 900;
        font-variant-numeric: tabular-nums;
        white-space: nowrap;
      }}

      .tfx-rainbow {{
        background: linear-gradient(90deg, #22c55e, #06b6d4, #3b82f6, #a855f7, #ec4899, #f97316);
        background-size: 320% 100%;
        animation: tfxShift 2.8s linear infinite;
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent !important;
      }}
      .tfx-aurora {{
        background: linear-gradient(90deg, #22c55e, #34d399, #06b6d4, #3b82f6, #a78bfa);
        background-size: 320% 100%;
        animation: tfxShift 3.6s ease-in-out infinite;
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent !important;
        text-shadow: 0 0 12px rgba(34, 211, 238, 0.25);
      }}
      .tfx-glow {{
        color: #e0f2fe !important;
        text-shadow: 0 0 10px rgba(56, 189, 248, 0.85), 0 0 26px rgba(99, 102, 241, 0.45);
      }}
      .tfx-neon {{
        color: #67e8f9 !important;
        text-shadow: 0 0 6px rgba(103, 232, 249, 0.65), 0 0 16px rgba(99, 102, 241, 0.35);
        animation: neonPulse 1.8s ease-in-out infinite;
      }}
      .tfx-fire {{
        background: linear-gradient(180deg, #fde047, #f97316, #ef4444);
        background-size: 100% 240%;
        animation: fireRise 1.6s ease-in-out infinite;
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent !important;
        text-shadow: 0 0 10px rgba(249, 115, 22, 0.35);
      }}

      @keyframes tfxShift {{
        0% {{ background-position: 0% 50%; }}
        50% {{ background-position: 100% 50%; }}
        100% {{ background-position: 0% 50%; }}
      }}

      @keyframes neonPulse {{
        0% {{
          filter: brightness(1.0);
          text-shadow: 0 0 5px rgba(103, 232, 249, 0.50), 0 0 12px rgba(99, 102, 241, 0.25);
        }}
        50% {{
          filter: brightness(1.15);
          text-shadow: 0 0 8px rgba(103, 232, 249, 0.80), 0 0 20px rgba(99, 102, 241, 0.42);
        }}
        100% {{
          filter: brightness(1.0);
          text-shadow: 0 0 5px rgba(103, 232, 249, 0.50), 0 0 12px rgba(99, 102, 241, 0.25);
        }}
      }}

      @keyframes fireRise {{
        0% {{ background-position: 50% 0%; }}
        50% {{ background-position: 50% 100%; }}
        100% {{ background-position: 50% 0%; }}
      }}
    </style>
  </head>
  <body>
    <div class="wrap">
      <div id="card" class="card"></div>
    </div>
    <script>
      (function() {{
        const PLATFORM_ICONS = {platform_icons_js};
        const wsUrl = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws';
        const card = document.getElementById('card');
        let cfg = null;
        let online = null;
        let ws = null;
        let tries = 0;

        function clampInt(v, minV, maxV, defV) {{
          const n = Number(v);
          if (!Number.isFinite(n)) return defV;
          const i = Math.trunc(n);
          return Math.max(minV, Math.min(maxV, i));
        }}

        function platformIconDataUrl(slug) {{
          const s = String(slug || '').trim().toLowerCase();
          const icons = PLATFORM_ICONS || {{}};
          const u = icons[s];
          return (typeof u === 'string' && u.length) ? u : '';
        }}

        function toInt(x) {{
          const n = Number(x);
          if (!Number.isFinite(n)) return 0;
          return Math.trunc(n);
        }}

        function twitchCount(o) {{
          const tw = (o && o.twitch) ? o.twitch : {{}};
          return toInt(tw.current);
        }}

        function tiktokCount(o) {{
          const tt = (o && o.tiktok) ? o.tiktok : {{}};
          return toInt(tt.current);
        }}

        function youtubeCount(o) {{
          const yt = (o && o.youtube) ? o.youtube : {{}};
          return toInt(yt.unique);
        }}

        function enabledSlugs(c) {{
          if (!c) return [];
          const out = [];
          if (c.platform_twitch_enabled) out.push('twitch');
          if (c.platform_tiktok_enabled) out.push('tiktok');
           if (c.platform_youtube_enabled) out.push('youtube');
           if (c.platform_kick_enabled) out.push('kick');
          return out;
        }}

        function countFor(slug, o) {{
          if (slug === 'twitch') return twitchCount(o);
          if (slug === 'tiktok') return tiktokCount(o);
           if (slug === 'youtube') return youtubeCount(o);
           if (slug === 'kick') return toInt((o && o.kick) ? o.kick.current : 0);
          return 0;
        }}

        function applyTextFx(el, fxRaw) {{
          if (!el) return;
          el.classList.remove('tfx-rainbow', 'tfx-aurora', 'tfx-glow', 'tfx-neon', 'tfx-fire');
          const fx = String(fxRaw || 'none').toLowerCase();
          if (fx === 'rainbow') el.classList.add('tfx-rainbow');
          else if (fx === 'aurora') el.classList.add('tfx-aurora');
          else if (fx === 'glow') el.classList.add('tfx-glow');
          else if (fx === 'neon') el.classList.add('tfx-neon');
          else if (fx === 'fire') el.classList.add('tfx-fire');
        }}

        function applyReadability(el, fx) {{
          const shOn = !!(cfg && cfg.text_shadow_enabled);
          const shCol = String((cfg && cfg.text_shadow_color) || '#000000');
          const shVal = shOn ? ('0px 2px 0px ' + shCol) : '';
          const usePlainShadow = (fx === 'none');
          el.style.textShadow = usePlainShadow ? shVal : '';

          const borderOn = !!(cfg && cfg.font_border_enabled);
          const borderCol = String((cfg && cfg.font_border_color) || '#242424');
          const stroke = borderOn ? ('1px ' + borderCol) : '0px transparent';
          el.style.webkitTextStroke = stroke;

          const col = String((cfg && cfg.text_color) || '#e5e7eb');
          if (fx === 'none' || fx === 'glow' || fx === 'neon') {{
            el.style.color = col;
          }} else {{
            el.style.color = '';
          }}
        }}

        function applyCfg() {{
          if (!cfg) return;
          document.body.style.fontFamily = cfg.font_family || 'system-ui';
          document.body.style.fontSize = clampInt(cfg.font_size_px, 8, 200, 36) + 'px';
          document.body.style.letterSpacing = clampInt(cfg.font_letter_spacing_px, -200, 200, 0) + 'px';
          document.body.style.lineHeight = 'normal';

          const bubbleOn = (cfg.bubble_bg_enabled !== undefined) ? !!cfg.bubble_bg_enabled : true;
          const alpha = Number(cfg.bubble_bg_alpha);
          const a = (Number.isFinite(alpha) ? Math.max(0, Math.min(1, alpha)) : 0.45);
          card.style.background = bubbleOn ? ('rgba(10,12,18,' + a + ')') : 'transparent';
          card.style.borderRadius = clampInt(cfg.bubble_radius_px, 0, 60, 14) + 'px';
          if (!bubbleOn) {{
            card.style.borderWidth = '0px';
            card.style.borderColor = 'transparent';
          }} else {{
            card.style.borderWidth = '1px';
            card.style.borderStyle = 'solid';
            card.style.borderColor = 'rgba(148,163,184,0.20)';
          }}
        }}

        function makeIcon(slug) {{
          const u = platformIconDataUrl(slug);
          if (!u) return null;
          const img = document.createElement('img');
          img.className = 'plat-icon';
          img.draggable = false;
          img.alt = slug;
          img.src = u;
          const psz = clampInt(cfg.platform_icon_size_px, 16, 128, 28);
          img.style.width = psz + 'px';
          img.style.height = psz + 'px';
          return img;
        }}

        function makeNumSpan(value) {{
          const span = document.createElement('span');
          span.className = 'num';
          const fs = clampInt(cfg.font_size_px, 8, 200, 36);
          const ls = clampInt(cfg.font_line_spacing_px, 0, 200, 0);
          span.style.fontSize = fs + 'px';
          span.style.lineHeight = (fs + ls) + 'px';
          span.textContent = String(toInt(value));
          const fx = String(cfg.text_effect || 'none').toLowerCase();
          applyTextFx(span, fx);
          applyReadability(span, fx);
          return span;
        }}

        function render() {{
          card.innerHTML = '';
          if (!cfg) return;

          const o = online || {{}};
          const slugs = enabledSlugs(cfg);
          const mode = String(cfg.layout_mode || 'combined').toLowerCase();
          const gap = clampInt(cfg.icon_number_gap_px, 0, 80, 12);

          if (!slugs.length) {{
            const hint = document.createElement('div');
            hint.className = 'num';
            hint.textContent = '—';
            const fs = clampInt(cfg.font_size_px, 8, 200, 36);
            hint.style.fontSize = fs + 'px';
            const fx = String(cfg.text_effect || 'none').toLowerCase();
            applyTextFx(hint, fx);
            applyReadability(hint, fx);
            card.appendChild(hint);
            return;
          }}

          if (mode === 'per_platform') {{
            const wrap = document.createElement('div');
            wrap.className = 'split-wrap';
            for (let i = 0; i < slugs.length; i++) {{
              const slug = slugs[i];
              const row = document.createElement('div');
              row.className = 'plat-row';
              row.style.gap = gap + 'px';
              const ic = makeIcon(slug);
              if (ic) row.appendChild(ic);
              row.appendChild(makeNumSpan(countFor(slug, o)));
              wrap.appendChild(row);
            }}
            card.appendChild(wrap);
            return;
          }}

          const row = document.createElement('div');
          row.className = 'row-combined';
          const icons = document.createElement('div');
          icons.className = 'icons';
          icons.style.marginRight = gap + 'px';
          let sum = 0;
          for (let i = 0; i < slugs.length; i++) {{
            const slug = slugs[i];
            sum += countFor(slug, o);
            const ic = makeIcon(slug);
            if (ic) icons.appendChild(ic);
          }}
          row.appendChild(icons);
          row.appendChild(makeNumSpan(sum));
          card.appendChild(row);
        }}

        function handleMsg(data) {{
          if (!data || !data.op) return;
          if (data.op === 'initial_state') {{
            const st = data.state || {{}};
            cfg = st.config || null;
            online = st.online || null;
            applyCfg();
            render();
            return;
          }}
          if (data.op === 'patch') {{
            const p = data.patch || {{}};
            if (p.config) {{
              const incoming = p.config || {{}};
              cfg = cfg ? Object.assign({{}}, cfg, incoming) : incoming;
              applyCfg();
              render();
            }}
            if (p.online) {{
              online = p.online;
              render();
            }}
          }}
        }}

        function connect() {{
          tries += 1;
          const backoff = Math.min(5000, 250 + Math.floor(Math.random() * 250) + (tries * 350));
          try {{ ws = new WebSocket(wsUrl); }}
          catch (e) {{ setTimeout(connect, backoff); return; }}
          ws.onopen = () => {{
            tries = 0;
            const subscribeMsg = {_json_for_script(subscribe_msg)};
            ws.send(JSON.stringify(subscribeMsg));
          }};
          ws.onmessage = (ev) => {{
            let obj = null;
            try {{ obj = JSON.parse(ev.data); }} catch (e) {{ return; }}
            handleMsg(obj);
          }};
          ws.onclose = () => setTimeout(connect, backoff);
          ws.onerror = () => {{}};
        }}

        connect();
      }})();
    </script>
  </body>
</html>"""

    def initial_state(self, params: dict[str, Any]) -> dict[str, Any]:
        _ = normalize_instance_id(str(params.get("instance") or ""))
        cfg = load_online_overlay_config()
        return {
            "config": json.loads(online_overlay_config_to_json_text(cfg)),
            "online": {
                "twitch": {"current": 0, "peak": 0},
                "tiktok": {"current": 0, "total": 0, "gifts": 0, "diamonds": 0},
                "youtube": {"messages": 0, "unique": 0, "superchats": 0, "memberships": 0},
                "updated_at": "00:00:00",
            },
        }
