from __future__ import annotations

import json
from typing import Any

from stream_cheremsha import l10n
from stream_cheremsha.overlays.models import normalize_instance_id
from stream_cheremsha.overlays.social_rotator_stats import SocialRotatorStatsSession
from stream_cheremsha.overlays.stream_info_overlay_config import (
    load_stream_info_overlay_config,
    stream_info_overlay_config_from_json_text,
    stream_info_overlay_config_to_public_dict,
)
from stream_cheremsha.overlays.ui_locale import load_ui_locale

_I18N_KEYS = (
    "stat.latest_follower",
    "stat.latest_donation",
    "stat.stream_time",
    "stat.top_donator",
    "stat.online",
)


def _overlay_i18n_bundle() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {"uk": {}, "en": {}}
    for short in _I18N_KEYS:
        try:
            uk = l10n.tr("uk", f"stream_info.{short}")
            en = l10n.tr("en", f"stream_info.{short}")
        except KeyError:
            # stream_info.* keys may not exist yet; fall back to the shared
            # social_rotator strings so labels always render.
            uk = l10n.tr("uk", f"social_rotator.{short}")
            en = l10n.tr("en", f"social_rotator.{short}")
        out["uk"][short] = uk
        out["en"][short] = en
    return out


def _json_for_script(value: Any) -> str:
    s = json.dumps(value, ensure_ascii=False)
    return s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


class StreamInfoOverlayType:
    type = "stream_info"

    def render_html(self, params: dict[str, Any]) -> str:
        raw_instance = params.get("instance")
        try:
            instance = normalize_instance_id(str(raw_instance or ""))
        except ValueError:
            instance = "default"

        cfg = load_stream_info_overlay_config()
        cfg_dict = stream_info_overlay_config_to_public_dict(cfg)
        accent = str(cfg.accent_color or "#00ffff")
        scale = max(40, min(250, int(cfg.scale_percent))) / 100.0
        bg_a = max(0, min(100, int(cfg.background_opacity_percent))) / 100.0
        locale = load_ui_locale()
        i18n = _overlay_i18n_bundle()
        pack = i18n.get(locale) or i18n["uk"]
        initial = {
            "config": cfg_dict,
            "stats": SocialRotatorStatsSession().to_public_dict(),
            "locale": locale,
        }
        subscribe_msg = {
            "op": "subscribe",
            "type": "stream_info",
            "instance": instance,
            "params": {},
        }

        return f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Stream Info</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=VT323&display=swap" rel="stylesheet" />
    <style>
      * {{ box-sizing: border-box; }}
      :root {{
        --sr-accent: {accent};
        --sr-magenta: #ff2bd6;
        --sr-bg-a: {bg_a:.4f};
        --sr-widget-scale: {scale:.4f};
        --sr-u: var(--sr-widget-scale);
        --sr-read: 1;
      }}
      html, body {{
        margin: 0; padding: 0; width: 100%; height: 100%;
        background: transparent; overflow: hidden;
      }}
      .root {{
        position: absolute; inset: 0;
        display: flex; align-items: center; justify-content: center;
        font-family: 'VT323', monospace;
        padding: calc((4px + 0.3vw) * var(--sr-u));
      }}
      .scanlines {{
        pointer-events: none; position: absolute; inset: 0; opacity: 0.22; z-index: 5;
        background: repeating-linear-gradient(
          0deg, transparent, transparent 2px, rgba(0,0,0,0.18) 3px
        );
        mix-blend-mode: soft-light;
        animation: scanDrift 9s linear infinite;
      }}
      .root.crt .scanlines {{ opacity: 0.42; }}
      @keyframes scanDrift {{
        from {{ background-position: 0 0; }}
        to {{ background-position: 0 24px; }}
      }}
      .panel-stats {{
        position: relative; z-index: 2;
        flex: 1 1 auto;
        display: grid;
        grid-template-columns: minmax(0, 1.25fr) minmax(0, 1.35fr) minmax(0, 1.15fr) minmax(0, 1.35fr) minmax(0, 0.7fr);
        gap: clamp(6px, 0.7vw, 8px);
        width: 100%; height: 100%;
      }}
      .stat-cell {{
        min-width: 0;
        display: flex;
        flex-direction: column;
        justify-content: center;
        padding: calc((6px + 0.2vw) * var(--sr-u) * var(--sr-read))
                 calc((8px + 0.25vw) * var(--sr-u) * var(--sr-read));
        border: 1px solid color-mix(in srgb, var(--sr-accent) 40%, transparent);
        background: rgba(0,0,0,calc(var(--sr-bg-a) * 0.42));
      }}
      .stat-cell.hidden {{ display: none; }}
      .stat-label {{
        font-family: var(--sr-font-display, 'Press Start 2P', monospace);
        font-size: clamp(8px, calc((8px + 0.25vw) * var(--sr-u)), 11px);
        color: var(--sr-accent);
        margin-bottom: 3px;
        letter-spacing: 0.03em;
        line-height: 1.3;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
      }}
      .stat-value {{
        font-family: 'VT323', monospace;
        font-size: clamp(16px, calc((16px + 0.55vw) * var(--sr-u)), 23px);
        color: #fff;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        line-height: 1.1;
        min-width: 0;
      }}
      .stat-value.big {{
        color: var(--sr-accent);
        font-size: clamp(19px, calc((20px + 0.7vw) * var(--sr-u)), 28px);
        text-shadow: 0 0 10px color-mix(in srgb, var(--sr-accent) 50%, transparent);
      }}
      .stat-value.is-empty {{
        opacity: 0.55;
        text-align: left;
        letter-spacing: 0.15em;
      }}
      .stat-cell[data-stat="stream_time"] .stat-value {{ font-variant-numeric: tabular-nums; }}
      /* Width-driven breakpoints (set from JS measuring the widget box —
         reliable inside OBS browser sources where viewport queries misfire). */
      .root.w-sm .panel-stats {{
        grid-template-columns: repeat(3, minmax(0, 1fr));
      }}
      .root.w-xs .panel-stats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      @media (max-width: 720px) {{
        .panel-stats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      }}
    </style>
  </head>
  <body>
    <div id="root" class="root crt theme-neon_cyber">
      <div class="scanlines"></div>
      <div class="panel-stats" id="stats">
        <div class="stat-cell" data-stat="latest_follower">
          <div class="stat-label" data-i18n="stat.latest_follower">{pack.get("stat.latest_follower") or "LATEST FOLLOWER"}</div>
          <div class="stat-value" id="statFollow">—</div>
        </div>
        <div class="stat-cell" data-stat="latest_donation">
          <div class="stat-label" data-i18n="stat.latest_donation">{pack.get("stat.latest_donation") or "LATEST DONATION"}</div>
          <div class="stat-value" id="statDonation">—</div>
        </div>
        <div class="stat-cell" data-stat="stream_time">
          <div class="stat-label" data-i18n="stat.stream_time">{pack.get("stat.stream_time") or "STREAM TIME"}</div>
          <div class="stat-value big" id="statTime">00:00:00</div>
        </div>
        <div class="stat-cell" data-stat="top_donator">
          <div class="stat-label" data-i18n="stat.top_donator">{pack.get("stat.top_donator") or "TOP DONATOR"}</div>
          <div class="stat-value" id="statTop">—</div>
        </div>
        <div class="stat-cell" data-stat="online">
          <div class="stat-label" data-i18n="stat.online">{pack.get("stat.online") or "ONLINE"}</div>
          <div class="stat-value big" id="statOnline">0</div>
        </div>
      </div>
    </div>
    <script>
      (function() {{
        const I18N = {_json_for_script(i18n)};
        let state = {_json_for_script(initial)};
        let config = state.config || {{}};
        let stats = state.stats || {{}};
        let locale = String(state.locale || 'uk');

        const rootEl = document.getElementById('root');

        function esc(s) {{
          return String(s || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
        }}

        function fmtDiamond(name, value) {{
          if (!name) return '—';
          return esc(name) + ' - ' + String(value != null ? value : 0) + ' ◆';
        }}

        function fmtTime(ms) {{
          if (!ms) return '00:00:00';
          const now = Date.now();
          let sec = Math.max(0, Math.floor((now - Number(ms)) / 1000));
          const h = Math.floor(sec / 3600); sec %= 3600;
          const m = Math.floor(sec / 60); const s = sec % 60;
          return String(h).padStart(2,'0') + ':' + String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
        }}

        function setStat(el, text, isEmpty) {{
          el.textContent = text;
          el.classList.toggle('is-empty', !!isEmpty);
        }}
        function renderStats() {{
          const st = stats || {{}};
          const followName = (st.latest_follower && st.latest_follower.name) ? st.latest_follower.name : '';
          setStat(document.getElementById('statFollow'), followName || '—', !followName);
          const donationEl = document.getElementById('statDonation');
          if (st.latest_donation) {{
            donationEl.innerHTML = fmtDiamond(st.latest_donation.name, st.latest_donation.value);
            donationEl.classList.remove('is-empty');
          }} else {{
            donationEl.textContent = '—';
            donationEl.classList.add('is-empty');
          }}
          const topEl = document.getElementById('statTop');
          if (st.top_donator) {{
            topEl.innerHTML = fmtDiamond(st.top_donator.name, st.top_donator.value);
            topEl.classList.remove('is-empty');
          }} else {{
            topEl.textContent = '—';
            topEl.classList.add('is-empty');
          }}
          setStat(document.getElementById('statOnline'), String(st.viewers_total || 0), !st.viewers_total);
          document.getElementById('statTime').textContent = fmtTime(st.stream_started_at_ms);
          const map = {{
            latest_follower: config.show_latest_follower !== false,
            latest_donation: config.show_latest_donation !== false,
            stream_time: config.show_stream_time !== false,
            top_donator: config.show_top_donator !== false,
            online: config.show_online !== false
          }};
          Array.prototype.forEach.call(document.querySelectorAll('.stat-cell'), function(el) {{
            const key = el.getAttribute('data-stat');
            el.classList.toggle('hidden', map[key] === false);
          }});
        }}

        function applyScale(percent) {{
          var p = Number(percent);
          if (!Number.isFinite(p)) p = Number(config.scale_percent || 100);
          if (!Number.isFinite(p)) p = 100;
          p = Math.max(40, Math.min(250, Math.round(p)));
          rootEl.style.setProperty('--sr-widget-scale', String(p / 100));
        }}

        function applyBackgroundOpacity(percent) {{
          var p = Number(percent);
          if (!Number.isFinite(p)) p = Number(config.background_opacity_percent);
          if (!Number.isFinite(p)) p = 85;
          p = Math.max(0, Math.min(100, Math.round(p)));
          rootEl.style.setProperty('--sr-bg-a', String(p / 100));
        }}

        function updateReadableScale() {{
          const w = rootEl.clientWidth || 0;
          const h = rootEl.clientHeight || 0;
          // Enlarge type when the browser source is short (common OBS banner crop).
          let read = 1.15;
          if (h > 0) {{
            read = Math.max(read, Math.min(2.35, 300 / h));
          }}
          if (w > 0) {{
            read = Math.max(read, Math.min(1.55, w / 1000));
          }}
          if (w > 0 && h > 0 && (h / w) < 0.24) {{
            read = Math.max(read, Math.min(2.5, 320 / h));
          }}
          rootEl.classList.toggle('short', h > 0 && h < 300);
          rootEl.classList.toggle('w-sm', w > 0 && w < 1000);
          rootEl.classList.toggle('w-xs', w > 0 && w < 640);
          rootEl.style.setProperty('--sr-read', String(read));
        }}

        function applyLook() {{
          const themeAccents = {{
            neon_cyber: '#00ffff',
            synthwave: '#ff71ce',
            toxic: '#b8ff00',
            ice: '#7ef9ff',
            amber: '#ffb000'
          }};
          const themeMags = {{
            neon_cyber: '#ff2bd6',
            synthwave: '#b967ff',
            toxic: '#39ff88',
            ice: '#a0c4ff',
            amber: '#ff6b35'
          }};
          const theme = String(config.theme || 'neon_cyber');
          rootEl.classList.remove('theme-neon_cyber','theme-synthwave','theme-toxic','theme-ice','theme-amber');
          rootEl.classList.add('theme-' + theme);
          const accent = themeAccents[theme] || String(config.accent_color || '#00ffff');
          const magenta = themeMags[theme] || '#ff2bd6';
          rootEl.style.setProperty('--sr-accent', accent);
          rootEl.style.setProperty('--sr-magenta', magenta);
          rootEl.classList.toggle('crt', config.enable_crt !== false);
          applyScale(config.scale_percent);
          applyBackgroundOpacity(config.background_opacity_percent);
        }}

        function applyChromeI18n() {{
          const pack = I18N[locale] || I18N.uk || {{}};
          Array.prototype.forEach.call(document.querySelectorAll('[data-i18n]'), function(el) {{
            const key = el.getAttribute('data-i18n');
            if (pack[key]) el.textContent = pack[key];
          }});
        }}

        function applyState(st) {{
          if (!st) return;
          if (st.locale) {{
            const nextLocale = String(st.locale || '').trim().toLowerCase();
            if (nextLocale === 'en' || nextLocale === 'uk') {{
              locale = nextLocale;
              applyChromeI18n();
            }}
          }}
          if (st.config) config = Object.assign(config || {{}}, st.config);
          if (st.stats) stats = st.stats;
          applyLook();
          renderStats();
        }}

        function handleMsg(data) {{
          if (!data || !data.op) return;
          if (data.op === 'initial_state') {{
            applyState(data.state || {{}});
            return;
          }}
          if (data.op === 'patch') {{
            applyState(data.patch || {{}});
          }}
        }}

        function connect() {{
          let tries = 0;
          function doConnect() {{
            tries += 1;
            const backoff = Math.min(5000, 250 + Math.floor(Math.random() * 250) + (tries * 350));
            const wsUrl = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws';
            let ws;
            try {{ ws = new WebSocket(wsUrl); }}
            catch (e) {{ setTimeout(doConnect, backoff); return; }}
            ws.onopen = function() {{
              tries = 0;
              ws.send(JSON.stringify({_json_for_script(subscribe_msg)}));
            }};
            ws.onmessage = function(ev) {{
              try {{ handleMsg(JSON.parse(ev.data)); }} catch (e) {{}}
            }};
            ws.onclose = function() {{ setTimeout(doConnect, backoff); }};
            ws.onerror = function() {{ try {{ ws.close(); }} catch (e) {{}} }};
          }}
          doConnect();
        }}

        applyState(state);
        updateReadableScale();
        setInterval(function() {{
          if (stats && stats.stream_started_at_ms != null && Number(stats.stream_started_at_ms) > 0) {{
            document.getElementById('statTime').textContent = fmtTime(stats.stream_started_at_ms);
          }}
        }}, 250);
        window.addEventListener('resize', function() {{ updateReadableScale(); }});
        if (typeof ResizeObserver !== 'undefined') {{
          new ResizeObserver(function() {{ updateReadableScale(); }}).observe(rootEl);
        }}
        connect();
      }})();
    </script>
  </body>
</html>"""

    def initial_state(self, params: dict[str, Any]) -> dict[str, Any]:
        from stream_cheremsha.overlays.widget_instances import typed_config_for_type

        cfg = typed_config_for_type(
            "stream_info",
            params,
            load_stream_info_overlay_config,
            stream_info_overlay_config_from_json_text,
        )
        return {
            "config": stream_info_overlay_config_to_public_dict(cfg),
            "stats": SocialRotatorStatsSession().to_public_dict(),
            "locale": load_ui_locale(),
        }
