from __future__ import annotations

# ruff: noqa: E501
import json
from typing import Any

from stream_cheremsha.overlays.models import normalize_instance_id
from stream_cheremsha.overlays.top_likers_overlay_config import (
    load_top_likers_overlay_config,
    top_likers_overlay_config_to_json_text,
)


def _json_for_script(value: Any) -> str:
    s = json.dumps(value, ensure_ascii=False)
    return s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


class TopLikersOverlayType:
    type = "top_likers"

    def render_html(self, params: dict[str, Any]) -> str:
        raw_instance = params.get("instance")
        try:
            instance = normalize_instance_id(str(raw_instance or ""))
        except ValueError:
            instance = "default"

        subscribe_msg = {
            "op": "subscribe",
            "type": "top_likers",
            "instance": instance,
            "params": {},
        }

        return f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Top Likers</title>
    <style>
      html, body {{ margin: 0; padding: 0; background: transparent; overflow: hidden; height: 100%; }}
      body {{ font-family: system-ui, sans-serif; }}
      .wrap {{
        position: absolute;
        inset: 0;
        padding: 10px;
        box-sizing: border-box;
        display: flex;
        flex-direction: column;
        align-items: stretch;
        justify-content: flex-start;
        min-height: 0;
        height: 100%;
        max-height: 100%;
      }}
      .panel {{
        min-width: 0;
        min-height: 0;
        width: 100%;
        flex: 1 1 0%;
        overflow-x: hidden;
        overflow-y: auto;
        scrollbar-width: none;
        -ms-overflow-style: none;
        padding: 12px 14px;
        box-sizing: border-box;
      }}
      .panel::-webkit-scrollbar {{
        width: 0;
        height: 0;
      }}
      .rows {{
        display: flex;
        flex-direction: column;
        gap: 0;
        direction: ltr;
      }}
      .row {{
        display: flex;
        flex-direction: row;
        align-items: center;
        gap: 10px;
        min-width: 0;
      }}
      .rows.rtl .row {{
        flex-direction: row-reverse;
      }}
      .rankCol {{
        flex: 0 0 auto;
        width: 44px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        font-variant-numeric: tabular-nums;
        direction: ltr;
        unicode-bidi: isolate;
      }}
      .avatarWrap {{
        position: relative;
        flex: 0 0 auto;
      }}
      .avatar {{
        display: block;
        border-radius: 999px;
        object-fit: cover;
        background: rgba(148,163,184,0.18);
      }}
      .avatar.ph {{ background: rgba(148,163,184,0.25); }}
      .crown {{
        position: absolute;
        top: -10px;
        left: -4px;
        width: 26px;
        height: 22px;
        z-index: 2;
        filter: drop-shadow(0 1px 2px rgba(0,0,0,0.45));
      }}
      .medal {{
        width: 34px;
        height: 34px;
        flex: 0 0 auto;
      }}
      .textCol {{
        flex: 1 1 auto;
        min-width: 0;
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        gap: 2px;
      }}
      .rows.rtl .textCol {{
        direction: ltr;
        align-items: flex-end;
      }}
      .name {{
        font-weight: 700;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 100%;
      }}
      .likesRow {{
        display: flex;
        flex-direction: row;
        align-items: center;
        gap: 6px;
        font-weight: 700;
        font-variant-numeric: tabular-nums;
      }}
      .rows.rtl .likesRow {{
        flex-direction: row-reverse;
      }}
      .heart {{
        display: block;
        flex: 0 0 auto;
        filter: drop-shadow(0 0.5px 0 rgba(0,0,0,0.45));
      }}
      .heart.heartPulse {{
        transform-origin: center center;
        animation: heartPulse 1.2s cubic-bezier(0.42, 0, 0.58, 1) infinite;
      }}
      @keyframes heartPulse {{
        0%, 100% {{ transform: scale(1); }}
        50% {{ transform: scale(1.12); }}
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
      .tfx-cyberpunk {{
        background: linear-gradient(90deg, #22d3ee, #d946ef, #ec4899, #38bdf8, #22d3ee);
        background-size: 320% 100%;
        animation: tfxShift 2.1s linear infinite;
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent !important;
        text-shadow: 0 0 14px rgba(217, 70, 239, 0.4);
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
      .tfx-ice {{
        background: linear-gradient(180deg, #ffffff, #bae6fd, #38bdf8, #e0f2fe);
        background-size: 100% 220%;
        animation: tfxIceFlow 3.2s ease-in-out infinite;
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent !important;
        text-shadow: 0 0 12px rgba(56, 189, 248, 0.35);
      }}
      .tfx-cold {{
        background: linear-gradient(90deg, #e0f2fe, #93c5fd, #cbd5e1, #f1f5f9, #e0f2fe);
        background-size: 280% 100%;
        animation: tfxShift 5.5s ease-in-out infinite;
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent !important;
      }}
      .tfx-freeze {{
        background: linear-gradient(90deg, #f8fafc, #a5f3fc, #22d3ee, #0ea5e9, #0369a1);
        background-size: 240% 100%;
        animation: tfxShift 4.2s ease-in-out infinite;
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent !important;
        text-shadow: 0 0 10px rgba(14, 165, 233, 0.45);
      }}
      .tfx-strong {{
        background: linear-gradient(180deg, #f8fafc 0%, #cbd5e1 45%, #475569 55%, #94a3b8 100%);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent !important;
        text-shadow:
          0 1px 0 rgba(15, 23, 42, 0.9),
          0 2px 0 rgba(15, 23, 42, 0.65);
      }}
      @keyframes tfxShift {{
        0% {{ background-position: 0% 50%; }}
        50% {{ background-position: 100% 50%; }}
        100% {{ background-position: 0% 50%; }}
      }}
      @keyframes fireRise {{
        0% {{ background-position: 50% 0%; }}
        50% {{ background-position: 50% 100%; }}
        100% {{ background-position: 50% 0%; }}
      }}
      @keyframes tfxIceFlow {{
        0% {{ background-position: 50% 0%; }}
        50% {{ background-position: 50% 100%; }}
        100% {{ background-position: 50% 0%; }}
      }}
      .wave .name {{
        animation-name: waveY;
        animation-timing-function: ease-in-out;
        animation-iteration-count: infinite;
        animation-duration: var(--wave-dur, 1.15s);
      }}
      @keyframes waveY {{
        0%, 100% {{ transform: translateY(0); }}
        50% {{ transform: translateY(-3px); }}
      }}
    </style>
  </head>
  <body>
    <div class="wrap">
      <div id="panel" class="panel">
        <div id="rows" class="rows"></div>
      </div>
    </div>
    <script>
      (function() {{
        const wsUrl = (location.protocol === 'https:' ? 'wss:' : 'ws:') + '//' + location.host + '/ws';
        const panel = document.getElementById('panel');
        const rowsEl = document.getElementById('rows');
        let cfg = null;
        let leaders = [];
        let ws = null;
        let tries = 0;
        let scrollKickId = null;
        let scrollIntervalId = null;
        let scrollPulseReturnId = null;

        function clampInt(v, minV, maxV, defV) {{
          const n = Number(v);
          if (!Number.isFinite(n)) return defV;
          const i = Math.trunc(n);
          return Math.max(minV, Math.min(maxV, i));
        }}

        function stopListScrollTimer() {{
          if (scrollKickId !== null) {{
            clearTimeout(scrollKickId);
            scrollKickId = null;
          }}
          if (scrollIntervalId !== null) {{
            clearInterval(scrollIntervalId);
            scrollIntervalId = null;
          }}
          if (scrollPulseReturnId !== null) {{
            clearTimeout(scrollPulseReturnId);
            scrollPulseReturnId = null;
          }}
          if (panel) {{
            panel.style.overflowY = '';
            panel.style.overflowX = '';
            panel.scrollTop = 0;
          }}
          if (rowsEl) {{
            rowsEl.style.transform = '';
            rowsEl.style.transition = '';
          }}
        }}

        function getListScrollIntervalMs() {{
          if (!cfg) return 0;
          const s = clampInt(cfg.list_scroll_interval_sec, 0, 600, 0);
          return s > 0 ? s * 1000 : 0;
        }}

        const LIST_SCROLL_GAP_MS = 150;
        const LIST_SCROLL_TAIL_MS = 100;
        const LIST_SCROLL_DOWN_MIN_SEC = 2.5;
        const LIST_SCROLL_DOWN_MAX_SEC = 14;
        const LIST_SCROLL_DOWN_PX_PER_SEC = 95;
        const LIST_SCROLL_UP_MIN_SEC = 1.1;
        const LIST_SCROLL_UP_MAX_SEC = 2.8;
        const LIST_SCROLL_UP_PX_PER_SEC = 400;

        function listScrollDownSec(pan) {{
          const t = pan / LIST_SCROLL_DOWN_PX_PER_SEC;
          return Math.min(LIST_SCROLL_DOWN_MAX_SEC, Math.max(LIST_SCROLL_DOWN_MIN_SEC, t));
        }}

        function listScrollUpSec(pan) {{
          const t = pan / LIST_SCROLL_UP_PX_PER_SEC;
          return Math.min(LIST_SCROLL_UP_MAX_SEC, Math.max(LIST_SCROLL_UP_MIN_SEC, t));
        }}

        function listScrollPulseTotalMs(pan) {{
          const d = Math.ceil(listScrollDownSec(pan) * 1000);
          const u = Math.ceil(listScrollUpSec(pan) * 1000);
          return d + LIST_SCROLL_GAP_MS + u + LIST_SCROLL_TAIL_MS;
        }}

        function listScrollPanPx() {{
          if (!panel || !rowsEl) return 48;
          const ch = Math.max(0, Math.floor(panel.clientHeight || 0));
          const rh = Math.max(
            rowsEl.offsetHeight || 0,
            typeof rowsEl.scrollHeight === 'number' ? rowsEl.scrollHeight : 0,
          );
          const over = Math.max(0, Math.ceil(rh - ch) + 1);
          const minMove = Math.max(48, Math.round(Math.max(ch, 100) * 0.12));
          return over > 0 ? over : minMove;
        }}

        function listScrollPulseOnce() {{
          if (!panel || !rowsEl) return;
          if (scrollPulseReturnId !== null) {{
            clearTimeout(scrollPulseReturnId);
            scrollPulseReturnId = null;
          }}
          const pan = listScrollPanPx();
          panel.style.overflowY = 'hidden';
          panel.style.overflowX = 'hidden';
          panel.scrollTop = 0;
          const downSec = listScrollDownSec(pan);
          const upSec = listScrollUpSec(pan);
          const dDown = downSec.toFixed(2);
          const dUp = upSec.toFixed(2);
          const downMs = Math.ceil(downSec * 1000);
          const upMs = Math.ceil(upSec * 1000);
          rowsEl.style.transition = 'none';
          rowsEl.style.transform = 'translateY(0)';
          void rowsEl.offsetHeight;
          rowsEl.style.transition = 'transform ' + dDown + 's cubic-bezier(0.33, 0.02, 0.2, 1)';
          rowsEl.style.transform = 'translateY(-' + pan + 'px)';
          scrollPulseReturnId = setTimeout(function () {{
            scrollPulseReturnId = null;
            if (!rowsEl) return;
            rowsEl.style.transition = 'none';
            rowsEl.style.transform = 'translateY(-' + pan + 'px)';
            void rowsEl.offsetHeight;
            rowsEl.style.transition = 'transform ' + dUp + 's cubic-bezier(0.22, 1, 0.36, 1)';
            rowsEl.style.transform = 'translateY(0)';
          }}, downMs + LIST_SCROLL_GAP_MS);
        }}

        function syncListScrollTimer() {{
          stopListScrollTimer();
          if (!cfg || !panel || !rowsEl) return;
          const n = getListScrollIntervalMs();
          if (n <= 0) return;
          const pan0 = listScrollPanPx();
          const period = Math.max(n + listScrollPulseTotalMs(pan0), 2500);
          scrollKickId = setTimeout(function () {{
            scrollKickId = null;
            if (!cfg || getListScrollIntervalMs() <= 0) {{
              stopListScrollTimer();
              return;
            }}
            listScrollPulseOnce();
            scrollIntervalId = setInterval(function () {{
              if (!cfg || getListScrollIntervalMs() <= 0) {{
                stopListScrollTimer();
                return;
              }}
              listScrollPulseOnce();
            }}, period);
          }}, n);
        }}

        function wavePeriodSec() {{
          const sp = String((cfg && cfg.wave_speed) || 'normal').toLowerCase();
          if (sp === 'slow') return 1.8;
          if (sp === 'fast') return 0.75;
          return 1.15;
        }}

        function fmtInt(n) {{
          try {{ return Number(n).toLocaleString(); }} catch (e) {{ return String(n); }}
        }}

        function medalSvg(place) {{
          const colors =
            place === 1
              ? {{ ring: '#f5d742', fill1: '#fff7c2', fill2: '#e6b422', num: '#5c4300' }}
              : place === 2
                ? {{ ring: '#c0c6d4', fill1: '#f3f4f8', fill2: '#9aa3b5', num: '#2b3347' }}
                : {{ ring: '#cd7f32', fill1: '#ffd7b0', fill2: '#a65a1e', num: '#3b2208' }};
          const c = colors;
          const num = String(place);
          return (
            '<svg class="medal" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">' +
            '<circle cx="20" cy="20" r="17" fill="' + c.fill1 + '" stroke="' + c.ring + '" stroke-width="2"/>' +
            '<circle cx="20" cy="20" r="12" fill="' + c.fill2 + '" opacity="0.35"/>' +
            '<text x="20" y="25" text-anchor="middle" font-size="15" font-weight="900" fill="' +
            c.num +
            '">' +
            num +
            '</text></svg>'
          );
        }}

        function crownSvg() {{
          return (
            '<svg class="crown" viewBox="0 0 48 40" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">' +
            '<path fill="#f5d742" stroke="#b8860b" stroke-width="1" d="M6 28 L10 14 L18 20 L24 8 L30 20 L38 14 L42 28 Z"/>' +
            '<rect x="4" y="28" width="40" height="8" rx="2" fill="#e6b422" stroke="#a67c00" stroke-width="1"/></svg>'
          );
        }}

        function heartSvg(px) {{
          const s = clampInt(px, 8, 48, 14);
          return (
            '<svg class="heart" viewBox="0 0 24 24" width="' +
            s +
            '" height="' +
            s +
            '" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">' +
            '<path fill="#ef4444" stroke="#b91c1c" stroke-width="1.1" stroke-linejoin="round" ' +
            'd="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/>' +
            '</svg>'
          );
        }}

        function applyTextFxUsername(el, fxRaw) {{
          if (!el) return;
          el.classList.remove(
            'tfx-rainbow',
            'tfx-aurora',
            'tfx-cyberpunk',
            'tfx-fire',
            'tfx-ice',
            'tfx-cold',
            'tfx-freeze',
            'tfx-strong',
          );
          const fx = String(fxRaw || 'none').toLowerCase();
          const map = {{
            rainbow: 'tfx-rainbow',
            aurora: 'tfx-aurora',
            cyberpunk: 'tfx-cyberpunk',
            fire: 'tfx-fire',
            ice: 'tfx-ice',
            cold: 'tfx-cold',
            freeze: 'tfx-freeze',
            strong: 'tfx-strong',
          }};
          const cls = map[fx];
          if (cls) el.classList.add(cls);
        }}

        function applyReadabilityUsername(el, fx) {{
          if (!el) return;
          const shOn = !!(cfg && cfg.username_text_shadow_enabled);
          const shCol = String((cfg && cfg.username_text_shadow_color) || '#000000');
          const shVal = shOn ? ('0px 2px 0px ' + shCol) : '';
          const usePlainShadow = (fx === 'none');
          el.style.textShadow = usePlainShadow ? shVal : '';

          const borderOn = !!(cfg && cfg.font_border_enabled);
          const borderCol = String((cfg && cfg.font_border_color) || '#242424');
          const stroke = borderOn ? ('1px ' + borderCol) : '0px transparent';
          el.style.webkitTextStroke = stroke;

          const col = String((cfg && cfg.color_username) || '#e5e7eb');
          if (fx === 'none') {{
            el.style.color = col;
          }} else {{
            el.style.color = '';
          }}
        }}

        function applyPanel() {{
          if (!cfg) return;
          const r = clampInt(cfg.list_radius_px, 0, 40, 12);
          const on = cfg.list_bg_enabled !== undefined ? !!cfg.list_bg_enabled : true;
          const bg = String(cfg.list_bg_rgba || 'rgba(18,20,28,0.72)');
          panel.style.borderRadius = r + 'px';
          panel.style.background = on ? bg : 'transparent';
          const shadowOn = !!(cfg && cfg.bg_shadow_enabled);
          const shc = String((cfg && cfg.bg_shadow_color) || 'rgba(0,0,0,0.35)');
          panel.style.boxShadow = shadowOn ? ('0 8px 22px ' + shc) : 'none';
          rowsEl.classList.toggle(
            'rtl',
            !!(cfg && (cfg.rtl === true || cfg.rtl === 1 || String(cfg.rtl).toLowerCase() === 'true')),
          );
          const wave = !!(cfg && cfg.wave_enabled);
          rowsEl.classList.toggle('wave', wave);
          rowsEl.style.setProperty('--wave-dur', wavePeriodSec() + 's');
          const si = clampInt(cfg.list_scroll_interval_sec, 0, 600, 0);
          if (si <= 0) {{
            stopListScrollTimer();
          }}
        }}

        function leadersSortedForDisplay(raw, modeRaw) {{
          const arr = Array.isArray(raw) ? raw.slice() : [];
          const m = String(modeRaw || 'likes_desc').toLowerCase();
          arr.sort((a, b) => {{
            const la = clampInt((a && a.likes), 0, 2000000000, 0);
            const lb = clampInt((b && b.likes), 0, 2000000000, 0);
            const ua = String((a && a.user) || '?');
            const ub = String((b && b.user) || '?');
            if (m === 'likes_asc') {{
              if (la !== lb) return la - lb;
              return ua.localeCompare(ub, undefined, {{ sensitivity: 'base' }});
            }}
            if (m === 'name_asc') {{
              const c = ua.localeCompare(ub, undefined, {{ sensitivity: 'base' }});
              if (c !== 0) return c;
              return lb - la;
            }}
            if (lb !== la) return lb - la;
            return ua.localeCompare(ub, undefined, {{ sensitivity: 'base' }});
          }});
          for (let i = 0; i < arr.length; i++) {{
            arr[i] = Object.assign({{}}, arr[i], {{ rank: i + 1 }});
          }}
          return arr;
        }}

        function stableLeaderKey(L) {{
          const k = String((L && L.key) || '').trim();
          if (k) return k;
          return String((L && L.user) || '?').trim() + '\\x1f' + String((L && L.avatar_url) || '').trim();
        }}

        function wantsRankMedal(showRank, showMedal, rank) {{
          return !!showRank && !!showMedal && rank <= 3;
        }}

        function rankCellHasMedalSvg(cell) {{
          try {{
            return !!(cell && cell.querySelector('svg.medal'));
          }} catch (e) {{
            return false;
          }}
        }}

        function canPatchLeaderDom(list) {{
          try {{
            const rows = rowsEl.querySelectorAll(':scope > .row');
            if (!list || rows.length !== list.length) return false;
            const showRank = !!cfg.show_rank;
            const showMedal = !!cfg.show_top3_medal;
            const showCrown = !!cfg.show_top1_crown;
            for (let i = 0; i < list.length; i++) {{
              const row = rows[i];
              const L = list[i] || {{}};
              if (!row || row.dataset.tlKey !== stableLeaderKey(L)) return false;
              const rank = clampInt(L.rank, 1, 999, i + 1);
              const wantM = wantsRankMedal(showRank, showMedal, rank);
              const rankCell = row.children[0];
              if (wantM !== rankCellHasMedalSvg(rankCell)) return false;
              const avWrap = row.children[1];
              const wantCr = !!(showCrown && rank === 1);
              const hasCr = !!(avWrap && avWrap.querySelector('svg.crown'));
              if (wantCr !== hasCr) return false;
            }}
            return true;
          }} catch (e) {{
            return false;
          }}
        }}

        function patchLeaderDom(list) {{
          const fs = clampInt(cfg.font_size_px, 8, 120, 22);
          const showRank = !!cfg.show_rank;
          const showMedal = !!cfg.show_top3_medal;
          const showCrown = !!cfg.show_top1_crown;
          const showHeart = !!cfg.show_heart;
          const heartAnimated = cfg.heart_animated !== undefined ? !!cfg.heart_animated : true;
          const heartPx = clampInt(cfg.heart_size_px, 8, 48, 14);
          const rankCol = String((cfg && cfg.color_rank) || '#d9d9d9');
          const ptsCol = String((cfg && cfg.color_points) || '#f4f4f5');
          const ufx = String(cfg.text_effect_username || 'none').toLowerCase();
          const lshOn = !!(cfg && cfg.likes_text_shadow_enabled);
          const lshCol = String((cfg && cfg.likes_text_shadow_color) || '#000000');
          const av = clampInt(cfg.avatar_size_px, 24, 120, 48);
          const lh = fs + clampInt(cfg.font_line_spacing_px, 0, 80, 4);
          const rows = rowsEl.querySelectorAll(':scope > .row');
          for (let i = 0; i < list.length; i++) {{
            const row = rows[i];
            const L = list[i] || {{}};
            const rank = clampInt(L.rank, 1, 999, i + 1);
            const user = String(L.user || '?');
            const likes = clampInt(L.likes, 0, 2000000000, 0);
            const avu = String(L.avatar_url || '').trim();
            const rankCell = row.children[0];
            rankCell.style.color = rankCol;
            rankCell.style.fontSize = Math.max(14, Math.round(fs * 0.85)) + 'px';
            if (showRank) {{
              if (wantsRankMedal(showRank, showMedal, rank)) rankCell.innerHTML = medalSvg(rank);
              else rankCell.textContent = String(rank) + '.';
            }} else {{
              rankCell.innerHTML = '&nbsp;';
            }}
            const avWrap = row.children[1];
            const wantCrown = showCrown && rank === 1;
            const oldCrown = avWrap.querySelector('svg.crown');
            if (wantCrown && !oldCrown) avWrap.insertAdjacentHTML('beforeend', crownSvg());
            if (!wantCrown && oldCrown) oldCrown.remove();
            const img = avWrap.querySelector('img.avatar');
            if (img) {{
              img.className = 'avatar' + (avu ? '' : ' ph');
              img.width = av;
              img.height = av;
              if (avu) {{
                img.referrerPolicy = 'no-referrer';
                img.src = avu;
              }} else {{
                img.removeAttribute('src');
              }}
              const ring =
                showMedal && rank === 1
                  ? '2px solid #f5d742'
                  : showMedal && rank === 2
                    ? '2px solid #c0c6d4'
                    : showMedal && rank === 3
                      ? '2px solid #cd7f32'
                      : '1px solid rgba(148,163,184,0.25)';
              img.style.width = av + 'px';
              img.style.height = av + 'px';
              img.style.border = ring;
            }}
            const textCol = row.children[2];
            const nameEl = textCol.querySelector('.name');
            if (nameEl) {{
              nameEl.textContent = user;
              nameEl.style.fontSize = fs + 'px';
              nameEl.style.lineHeight = lh + 'px';
              if (cfg.wave_enabled) nameEl.style.animationDelay = (i * 0.07) + 's';
              applyTextFxUsername(nameEl, ufx);
              applyReadabilityUsername(nameEl, ufx);
            }}
            const lr = textCol.querySelector('.likesRow');
            if (lr) {{
              lr.style.fontSize = Math.max(12, Math.round(fs * 0.78)) + 'px';
              lr.style.color = ptsCol;
              lr.style.textShadow = lshOn ? ('0 1px 0 ' + lshCol) : 'none';
              const num = lr.querySelector('.tl-likes-num');
              if (num) num.textContent = fmtInt(likes);
              if (showHeart) {{
                let h = lr.querySelector('.heart');
                if (!h) {{
                  lr.insertAdjacentHTML('afterbegin', heartSvg(heartPx));
                  h = lr.querySelector('.heart');
                  if (heartAnimated && h) h.classList.add('heartPulse');
                }} else {{
                  h.setAttribute('width', String(heartPx));
                  h.setAttribute('height', String(heartPx));
                  h.classList.toggle('heartPulse', !!heartAnimated);
                }}
              }} else {{
                const hx = lr.querySelector('.heart');
                if (hx) hx.remove();
              }}
            }}
          }}
        }}

        function render(opts) {{
          const preferPatch = !!(opts && opts.patchOnly);
          applyPanel();
          if (!cfg) {{
            stopListScrollTimer();
            rowsEl.innerHTML = '';
            return;
          }}
          document.body.style.fontFamily = cfg.font_family || 'system-ui';
          document.body.style.letterSpacing = clampInt(cfg.font_letter_spacing_px, -20, 40, 0) + 'px';

          const fs = clampInt(cfg.font_size_px, 8, 120, 22);
          const vgap = clampInt(cfg.row_gap_px, 0, 40, 10);
          const av = clampInt(cfg.avatar_size_px, 24, 120, 48);
          const showRank = !!cfg.show_rank;
          const showLikes = !!cfg.show_likes;
          const showCrown = !!cfg.show_top1_crown;
          const showMedal = !!cfg.show_top3_medal;
          const showHeart = !!cfg.show_heart;
          const heartAnimated = cfg.heart_animated !== undefined ? !!cfg.heart_animated : true;
          const heartPx = clampInt(cfg.heart_size_px, 8, 48, 14);
          const rankCol = String((cfg && cfg.color_rank) || '#d9d9d9');
          const ptsCol = String((cfg && cfg.color_points) || '#f4f4f5');
          const ufx = String(cfg.text_effect_username || 'none').toLowerCase();

          const list = leadersSortedForDisplay(leaders, cfg && cfg.leader_sort);
          if (preferPatch && rowsEl.childElementCount > 0 && canPatchLeaderDom(list)) {{
            patchLeaderDom(list);
            return;
          }}
          stopListScrollTimer();
          rowsEl.innerHTML = '';
          for (let i = 0; i < list.length; i++) {{
            const L = list[i] || {{}};
            const rank = clampInt(L.rank, 1, 999, i + 1);
            const user = String(L.user || '?');
            const likes = clampInt(L.likes, 0, 2000000000, 0);
            const avu = String(L.avatar_url || '').trim();

            const row = document.createElement('div');
            row.className = 'row';
            row.dataset.tlKey = stableLeaderKey(L);
            row.style.marginBottom = (i < list.length - 1 ? vgap : 0) + 'px';
            const rankCell = document.createElement('div');
            rankCell.className = 'rankCol';
            rankCell.style.color = rankCol;
            rankCell.style.fontSize = Math.max(14, Math.round(fs * 0.85)) + 'px';
            if (showRank) {{
              if (wantsRankMedal(showRank, showMedal, rank)) {{
                rankCell.innerHTML = medalSvg(rank);
              }} else {{
                rankCell.textContent = String(rank) + '.';
              }}
            }} else {{
              rankCell.innerHTML = '&nbsp;';
            }}

            const avWrap = document.createElement('div');
            avWrap.className = 'avatarWrap';
            if (showCrown && rank === 1) {{
              avWrap.insertAdjacentHTML('beforeend', crownSvg());
            }}
            const img = document.createElement('img');
            img.className = 'avatar' + (avu ? '' : ' ph');
            img.alt = '';
            img.width = av;
            img.height = av;
            if (avu) {{
              img.referrerPolicy = 'no-referrer';
              img.src = avu;
            }} else {{
              img.removeAttribute('src');
            }}
            const ring =
              showMedal && rank === 1
                ? '2px solid #f5d742'
                : showMedal && rank === 2
                  ? '2px solid #c0c6d4'
                  : showMedal && rank === 3
                    ? '2px solid #cd7f32'
                    : '1px solid rgba(148,163,184,0.25)';
            img.style.width = av + 'px';
            img.style.height = av + 'px';
            img.style.border = ring;
            avWrap.appendChild(img);

            const textCol = document.createElement('div');
            textCol.className = 'textCol';

            const nameEl = document.createElement('div');
            nameEl.className = 'name';
            nameEl.textContent = user;
            const lh = fs + clampInt(cfg.font_line_spacing_px, 0, 80, 4);
            nameEl.style.fontSize = fs + 'px';
            nameEl.style.lineHeight = lh + 'px';
            if (cfg.wave_enabled) {{
              nameEl.style.animationDelay = (i * 0.07) + 's';
            }}
            applyTextFxUsername(nameEl, ufx);
            applyReadabilityUsername(nameEl, ufx);

            textCol.appendChild(nameEl);

            if (showLikes) {{
              const lr = document.createElement('div');
              lr.className = 'likesRow';
              lr.style.fontSize = Math.max(12, Math.round(fs * 0.78)) + 'px';
              lr.style.color = ptsCol;
              const lshOn = !!(cfg && cfg.likes_text_shadow_enabled);
              const lshCol = String((cfg && cfg.likes_text_shadow_color) || '#000000');
              lr.style.textShadow = lshOn ? ('0 1px 0 ' + lshCol) : 'none';
              if (showHeart) {{
                lr.insertAdjacentHTML('beforeend', heartSvg(heartPx));
                if (heartAnimated) {{
                  const h = lr.querySelector('.heart');
                  if (h) h.classList.add('heartPulse');
                }}
              }}
              const num = document.createElement('span');
              num.className = 'tl-likes-num';
              num.textContent = fmtInt(likes);
              lr.appendChild(num);
              textCol.appendChild(lr);
            }}

            row.appendChild(rankCell);
            row.appendChild(avWrap);
            row.appendChild(textCol);
            rowsEl.appendChild(row);
          }}
          panel.scrollTop = 0;
          setTimeout(syncListScrollTimer, 50);
        }}

        function handleMsg(data) {{
          if (!data || !data.op) return;
          if (data.op === 'initial_state') {{
            const st = data.state || {{}};
            cfg = st.config || null;
            leaders = st.leaders || [];
            render();
            return;
          }}
          if (data.op === 'patch') {{
            const p = data.patch || {{}};
            const hadCfg = !!p.config;
            if (p.config) {{
              const incoming = p.config || {{}};
              cfg = cfg ? Object.assign({{}}, cfg, incoming) : incoming;
            }}
            if (p.leaders) {{
              leaders = p.leaders;
            }}
            if (!cfg) return;
            if (hadCfg) render();
            else if (p.leaders) render({{ patchOnly: true }});
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
        cfg = load_top_likers_overlay_config()
        return {
            "config": json.loads(top_likers_overlay_config_to_json_text(cfg)),
            "leaders": [],
        }
