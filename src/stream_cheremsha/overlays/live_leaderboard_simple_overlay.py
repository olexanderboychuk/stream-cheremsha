from __future__ import annotations

import html
import json
from typing import Any

from stream_cheremsha import l10n
from stream_cheremsha.overlays.live_leaderboard_ranking import LiveLeaderboardRankingEngine
from stream_cheremsha.overlays.live_leaderboard_simple_config import (
    live_leaderboard_simple_config_from_json_text,
    live_leaderboard_simple_config_to_public_dict,
    load_live_leaderboard_simple_config,
)
from stream_cheremsha.overlays.models import normalize_instance_id
from stream_cheremsha.overlays.ui_locale import load_ui_locale

_I18N_KEYS = (
    "kicker",
    "source.likers",
    "source.gifters",
    "source.sharers",
    "source.commenters",
    "source.contributors",
    "empty.awaiting",
    "fallback",
)
_I18N_SCENE_KEYS = (
    "scene.hall_of_fame",
    "scene.arena",
    "scene.energy_network",
)


def _overlay_i18n_bundle() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {"uk": {}, "en": {}}
    for short in _I18N_KEYS:
        key = f"live_leaderboard.{short}"
        out["uk"][short] = l10n.tr("uk", key)
        out["en"][short] = l10n.tr("en", key)
    for short in _I18N_SCENE_KEYS:
        key = f"live_leaderboard_simple.{short}"
        out["uk"][short] = l10n.tr("uk", key)
        out["en"][short] = l10n.tr("en", key)
    return out


def _json_for_script(value: Any) -> str:
    s = json.dumps(value, ensure_ascii=False)
    return s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


class LiveLeaderboardSimpleOverlayType:
    type = "live_leaderboard_simple"

    def render_html(self, params: dict[str, Any]) -> str:
        raw_instance = params.get("instance")
        try:
            instance = normalize_instance_id(str(raw_instance or ""))
        except ValueError:
            instance = "default"
        cfg = load_live_leaderboard_simple_config()
        cfg_dict = live_leaderboard_simple_config_to_public_dict(cfg)
        locale = load_ui_locale()
        i18n = _overlay_i18n_bundle()
        pack = i18n.get(locale) or i18n["uk"]
        initial_kicker = html.escape(pack.get("kicker", "LIVE LEADERBOARD"))
        subscribe_msg = {
            "op": "subscribe",
            "type": "live_leaderboard_simple",
            "instance": instance,
            "params": {},
        }
        return f"""<!doctype html>
<html><head><meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>Live Leaderboard Simple</title>
<style>
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; background: transparent; overflow: hidden; }}
:root {{ --lls-scale: {max(40, min(250, int(cfg.scale_percent))) / 100.0:.4f}; }}
.root {{
  font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
  border-radius: 14px; padding: 10px 12px; width: 100%;
  background: rgba(11,14,20,0.72); color: #e8edf5;
}}
.root[data-theme="transparent"] {{
  background: transparent !important;
  text-shadow: 0 1px 6px rgba(0,0,0,0.7);
}}
.root[data-theme="transparent"] .row,
.root[data-theme="transparent"] .card {{
  background: transparent;
}}
.root[data-theme="light"] {{
  color: #1e293b;
  box-shadow: 0 6px 24px rgba(15,23,42,0.12);
  text-shadow: none;
}}
.root[data-theme="light"] .row {{ background: transparent; }}
.root[data-theme="light"] .card {{
  background: rgba(255,255,255,0.85);
  border: 1px solid rgba(15,23,42,0.08);
  box-shadow: 0 2px 10px rgba(15,23,42,0.08);
}}
.root[data-theme="light"] .vl {{ color: #0f766e; opacity: 1; }}
.root[data-theme="light"] .rank {{ background: rgba(15,23,42,0.07); color: #64748b; }}
.root[data-theme="light"] .bar-track {{ background: rgba(15,23,42,0.08); }}
.root[data-theme="neon"] {{
  background: linear-gradient(135deg, #312e81 0%, #7c3aed 48%, #db2777 100%) !important;
  color: #ffffff;
  border: 1px solid rgba(255,255,255,0.22);
  box-shadow: 0 6px 28px rgba(124,58,237,0.35);
}}
.root[data-theme="neon"] .row {{ background: transparent; }}
.root[data-theme="neon"] .card {{
  background: rgba(255,255,255,0.14);
  border: 1px solid rgba(255,255,255,0.25);
}}
.root[data-theme="neon"] .bar-track {{ background: rgba(255,255,255,0.16); }}
.root[data-theme="neon"] .bar-fill {{
  background: linear-gradient(90deg, rgba(255,255,255,0.75), rgba(255,255,255,0.35));
}}
.root[data-theme="neon"] .bar-fill .nm {{ color: #2e1065; font-weight: 700; }}
.root[data-theme="neon"] .rank {{ background: rgba(255,255,255,0.18); color: #fff; }}
.root[data-theme="neon"] .hdr, .root[data-theme="neon"] .sub {{ opacity: 0.85; }}
.root[data-rankstyle="badge"] .rank {{ border-radius: 6px; }}
.root[data-rankstyle="badge"] .rank.r1,
.root[data-rankstyle="badge"] .rank.r2,
.root[data-rankstyle="badge"] .rank.r3 {{
  border-radius: 6px;
  box-shadow: 0 0 0 2px rgba(255,255,255,0.25);
}}
.hdr {{ font-size: 0.75em; letter-spacing: 0.18em; opacity: 0.55; margin: 0 0 8px 2px; }}
.sub {{ font-size: 0.9em; font-weight: 700; opacity: 0.9; margin: 0 0 6px 2px; }}
.stage {{ transition: opacity 0.32s ease, transform 0.32s ease; }}
.stage.leaving {{ opacity: 0; transform: translateY(8px); }}
.stage.entering {{ animation: stageIn 0.38s ease; }}
@keyframes stageIn {{
  from {{ opacity: 0; transform: translateY(8px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}
.row {{
  display: grid; grid-template-columns: 26px 34px 1fr auto;
  align-items: center; gap: 8px; padding: 6px 2px;
  border-radius: 8px;
  transition: background-color 0.5s ease;
}}
.row.no-av {{ grid-template-columns: 26px 1fr auto; }}
.row.rank-flash {{ background-color: rgba(20,184,166,0.16); }}
.rank {{
  width: 22px; height: 22px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.8em; font-weight: 700; color: #9aa4b2; background: rgba(255,255,255,0.06);
}}
.rank.r1 {{ color: #1a1200; background: linear-gradient(180deg,#ffd75e,#f5a623); }}
.rank.r2 {{ color: #1a1200; background: linear-gradient(180deg,#ffe9a8,#f0b429); }}
.rank.r3 {{ color: #fff; background: linear-gradient(180deg,#e8933c,#b45309); }}
.root[data-rankstyle="number"] .rank {{ background: transparent; }}
.av {{ width: 30px; height: 30px; border-radius: 50%; object-fit: cover; background: #222; display: block; }}
.av-ph {{ width: 30px; height: 30px; border-radius: 50%; background: radial-gradient(circle at 35% 30%, #3b4763, #141a26); }}
.nm {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 1em; }}
.vl {{ font-variant-numeric: tabular-nums; font-weight: 700; font-size: 0.95em; opacity: 0.92; }}
.empty {{ text-align: center; opacity: 0.5; padding: 18px 0; font-size: 0.9em; }}
/* Spotlight (Top 3) scene */
.spot {{ display: flex; gap: 10px; justify-content: center; padding: 6px 0 2px; }}
.card {{
  flex: 1 1 0; min-width: 0; text-align: center;
  background: rgba(255,255,255,0.05); border-radius: 12px; padding: 10px 6px;
  animation: floaty 4s ease-in-out infinite;
}}
.card.c1 {{ animation-delay: 0s; }}
.card.c2 {{ animation-delay: 0.6s; }}
.card.c3 {{ animation-delay: 1.2s; }}
@keyframes floaty {{
  0%, 100% {{ transform: translateY(0); }}
  50% {{ transform: translateY(-4px); }}
}}
.card .av, .card .av-ph {{ width: 44px; height: 44px; margin: 0 auto; }}
.card .nm {{ font-size: 0.9em; font-weight: 700; margin-top: 6px; }}
.card .vl {{ font-size: 1em; margin-top: 2px; }}
.card .rk {{ font-size: 0.75em; font-weight: 800; opacity: 0.6; }}
/* Overview scene: value bars */
.bar-row {{ display: grid; grid-template-columns: 26px 1fr auto; gap: 8px; align-items: center; padding: 5px 2px; }}
.bar-track {{ height: 22px; border-radius: 6px; background: rgba(255,255,255,0.06); overflow: hidden; position: relative; }}
.bar-fill {{
  height: 100%; border-radius: 6px;
  background: linear-gradient(90deg, rgba(20,184,166,0.55), rgba(20,184,166,0.25));
  transition: width 0.6s ease;
  display: flex; align-items: center; padding: 0 8px;
}}
.bar-fill .nm {{ font-size: 0.8em; color: #e8edf5; }}
/* Username text effects (same family as Top Likers) */
.tfx-rainbow {{
  background: linear-gradient(90deg, #22c55e, #06b6d4, #3b82f6, #a855f7, #ec4899, #f97316);
  background-size: 320% 100%; animation: tfxShift 2.8s linear infinite;
  -webkit-background-clip: text; background-clip: text; color: transparent !important;
}}
.tfx-aurora {{
  background: linear-gradient(90deg, #22c55e, #34d399, #06b6d4, #3b82f6, #a78bfa);
  background-size: 320% 100%; animation: tfxShift 3.6s ease-in-out infinite;
  -webkit-background-clip: text; background-clip: text; color: transparent !important;
}}
.tfx-fire {{
  background: linear-gradient(180deg, #fde047, #f97316, #ef4444);
  background-size: 100% 240%; animation: fireRise 1.6s ease-in-out infinite;
  -webkit-background-clip: text; background-clip: text; color: transparent !important;
}}
.tfx-ice {{
  background: linear-gradient(180deg, #ffffff, #bae6fd, #38bdf8, #e0f2fe);
  background-size: 100% 220%; animation: tfxIceFlow 3.2s ease-in-out infinite;
  -webkit-background-clip: text; background-clip: text; color: transparent !important;
}}
.tfx-cold {{
  background: linear-gradient(90deg, #e0f2fe, #93c5fd, #cbd5e1, #f1f5f9, #e0f2fe);
  background-size: 280% 100%; animation: tfxShift 5.5s ease-in-out infinite;
  -webkit-background-clip: text; background-clip: text; color: transparent !important;
}}
.tfx-freeze {{
  background: linear-gradient(90deg, #f8fafc, #a5f3fc, #22d3ee, #0ea5e9, #0369a1);
  background-size: 240% 100%; animation: tfxShift 4.2s ease-in-out infinite;
  -webkit-background-clip: text; background-clip: text; color: transparent !important;
}}
.tfx-strong {{
  background: linear-gradient(180deg, #f8fafc 0%, #cbd5e1 45%, #475569 55%, #94a3b8 100%);
  -webkit-background-clip: text; background-clip: text; color: transparent !important;
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
.wave .nm {{
  animation-name: waveY; animation-timing-function: ease-in-out;
  animation-iteration-count: infinite; animation-duration: var(--wave-dur, 1.15s);
}}
@keyframes waveY {{
  0%, 100% {{ transform: translateY(0); }}
  50% {{ transform: translateY(-3px); }}
}}
</style></head>
<body><div id="root" class="root"><div class="hdr" id="hdr">{initial_kicker}</div><div class="sub" id="sub"></div><div class="stage" id="stage"><div id="list"></div></div></div>
<script>(function() {{
let config = {_json_for_script(cfg_dict)};
let locale = {_json_for_script(locale)};
const I18N = {_json_for_script(i18n)};
let rankings = {{ likers: [] }};
let presentation = {{ source_id: 'likers', scene_id: 'hall_of_fame', transition_token: 0 }};
let lastToken = -1;
let displayValues = {{}};
let lastRanks = {{}};
function tr(k) {{ const p = I18N[locale] || I18N.uk || {{}}; return p[k] || (I18N.uk||{{}})[k] || k; }}
function fmt(n) {{
  const f = String((config && config.value_format) || 'compact');
  const v = Math.round(Number(n) || 0);
  if (f === 'full') return String(v).replace(/\\B(?=(\\d{{3}})+(?!\\d))/g, ',');
  if (f === 'short') {{
    if (v >= 1000000) return (v/1000000).toFixed(1).replace(/\\.0$/,'') + 'M';
    if (v >= 1000) return Math.round(v/1000) + 'K';
    return String(v);
  }}
  if (v >= 1000000) return (v/1000000).toFixed(1).replace(/\\.0$/,'') + 'M';
  if (v >= 1000) return (v/1000).toFixed(1).replace(/\\.0$/,'') + 'K';
  return String(v);
}}
function esc(s) {{ return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }}
function keyOf(row) {{ return String(row.key || row.user || ''); }}
function tween(row) {{
  const k = keyOf(row);
  const target = Number(row.value) || 0;
  if (displayValues[k] === undefined) displayValues[k] = target;
  const cur = displayValues[k];
  const next = cur + (target - cur) * 0.22;
  displayValues[k] = Math.abs(target - next) < 0.5 ? target : next;
  return displayValues[k];
}}
function tfxClass() {{
  const fx = String((config && config.text_effect_username) || 'none').toLowerCase();
  const map = {{rainbow:'tfx-rainbow',aurora:'tfx-aurora',fire:'tfx-fire',ice:'tfx-ice',cold:'tfx-cold',freeze:'tfx-freeze',strong:'tfx-strong'}};
  return map[fx] || '';
}}
function waveDur() {{
  const sp = String((config && config.wave_speed) || 'normal').toLowerCase();
  if (sp === 'slow') return '1.8s';
  if (sp === 'fast') return '0.75s';
  return '1.15s';
}}
function hexToRgba(hex, alpha) {{
  let h = String(hex || '').trim();
  if (h.charAt(0) === '#') h = h.slice(1);
  if (h.length === 3) h = h.split('').map(function(c) {{ return c + c; }}).join('');
  if (h.length < 6) return 'rgba(11,14,20,' + alpha + ')';
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  let a = alpha;
  if (h.length >= 8) {{
    const ha = parseInt(h.slice(6, 8), 16) / 255;
    a = Math.round(alpha * ha * 100) / 100;
  }}
  if (isNaN(r) || isNaN(g) || isNaN(b)) return 'rgba(11,14,20,' + alpha + ')';
  return 'rgba(' + r + ',' + g + ',' + b + ',' + a + ')';
}}
function applyCfg() {{
  const r = document.getElementById('root');
  const theme = String(config.theme || 'dark');
  r.dataset.theme = theme;
  r.dataset.rankstyle = String(config.rank_style || 'medal');
  const opRaw = Number(config.background_opacity);
  const op = isNaN(opRaw) ? 0.72 : Math.max(0, Math.min(1, opRaw));
  if (theme === 'transparent' || theme === 'neon') {{
    r.style.background = '';
  }} else if (theme === 'light') {{
    r.style.background = 'rgba(255,255,255,' + op + ')';
  }} else {{
    r.style.background = hexToRgba(config.background_color, op);
  }}
  const fam = String(config.font_family || 'system-ui').replace(/["\\\\]/g, '').trim() || 'system-ui';
  r.style.fontFamily = "'" + fam + "', system-ui, sans-serif";
  const fsRaw = Number(config.font_size_px);
  const fs = isNaN(fsRaw) ? 15 : Math.max(8, Math.min(48, fsRaw));
  r.style.fontSize = fs + 'px';
  const scRaw = Number(config.scale_percent);
  const sc = (isNaN(scRaw) ? 100 : Math.max(40, Math.min(250, scRaw))) / 100;
  r.style.zoom = sc;
  document.getElementById('hdr').style.display = config.show_header === false ? 'none' : '';
  document.getElementById('sub').style.display = config.show_header === false ? 'none' : '';
  document.documentElement.style.setProperty('--wave-dur', waveDur());
}}
function avatarHtml(url, cls) {{
  const u = (url || '').trim();
  if (!u) return '<div class="' + cls + '-ph"></div>';
  return '<img class="' + cls + '" src="' + u.replace(/"/g,'') + '" alt="" />';
}}
function nameHtml(user, waveDelay) {{
  const fx = tfxClass();
  const style = waveDelay != null ? ' style="animation-delay:' + waveDelay + 's"' : '';
  return '<div class="nm' + (fx ? ' ' + fx : '') + '"' + style + '>@' + esc(user) + '</div>';
}}
function listHtml(list) {{
  const showAv = config.show_avatars !== false;
  const wave = config.wave_enabled === true;
  return list.map(function(row, i) {{
    const rk = Number(row.rank) || (i + 1);
    const cls = rk === 1 ? 'r1' : (rk === 2 ? 'r2' : (rk === 3 ? 'r3' : ''));
    const av = showAv ? avatarHtml(row.avatar_url, 'av') : '';
    return '<div class="row' + (showAv ? '' : ' no-av') + '" data-k="' + esc(keyOf(row)) + '">' +
      '<div class="rank ' + cls + '">' + String(rk) + '</div>' +
      av + nameHtml(row.user, wave ? (i * 0.07).toFixed(2) : null) +
      '<div class="vl" data-val="1">' + fmt(tween(row)) + '</div></div>';
  }}).join('');
}}
function spotlightHtml(list) {{
  const top = list.slice(0, 3);
  const wave = config.wave_enabled === true;
  return '<div class="spot">' + top.map(function(row, i) {{
    const rk = Number(row.rank) || (i + 1);
    return '<div class="card c' + rk + '" data-k="' + esc(keyOf(row)) + '">' +
      '<div class="rk">#' + String(rk).padStart(2,'0') + '</div>' +
      avatarHtml(row.avatar_url, 'av') +
      nameHtml(row.user, wave ? (i * 0.09).toFixed(2) : null) +
      '<div class="vl" data-val="1">' + fmt(tween(row)) + '</div></div>';
  }}).join('') + '</div>';
}}
function overviewHtml(list) {{
  const showAv = config.show_avatars !== false;
  const max = Math.max.apply(null, [1].concat(list.map(function(r) {{ return Number(r.value) || 0; }})));
  return list.map(function(row, i) {{
    const rk = Number(row.rank) || (i + 1);
    const pct = Math.max(4, Math.round(((Number(row.value) || 0) / max) * 100));
    return '<div class="bar-row" data-k="' + esc(keyOf(row)) + '">' +
      '<div class="rank">' + String(rk) + '</div>' +
      '<div class="bar-track"><div class="bar-fill" style="width:' + pct + '%">' +
      '<div class="nm">' + (showAv ? '' : '') + '@' + esc(row.user) + '</div></div></div>' +
      '<div class="vl" data-val="1">' + fmt(tween(row)) + '</div></div>';
  }}).join('');
}}
function currentLeaders() {{
  const src = presentation.source_id || 'leaders';
  const list = (rankings && rankings[src]) ? rankings[src] : [];
  return Array.isArray(list) ? list : [];
}}
function sceneOf() {{ return String(presentation.scene_id || 'hall_of_fame'); }}
function render(transitioned) {{
  applyCfg();
  const root = document.getElementById('root');
  const src = presentation.source_id || 'likers';
  const scene = sceneOf();
  document.getElementById('hdr').textContent = tr('source.' + src) || tr('fallback');
  document.getElementById('sub').textContent = tr('scene.' + scene) || '';
  const list = currentLeaders();
  const el = document.getElementById('list');
  const stage = document.getElementById('stage');
  const paint = function() {{
    if (!list.length) {{ el.innerHTML = '<div class="empty">' + esc(tr('empty.awaiting')) + '</div>'; }}
    else if (scene === 'arena') {{ el.innerHTML = spotlightHtml(list); }}
    else if (scene === 'energy_network') {{ el.innerHTML = overviewHtml(list); }}
    else {{ el.innerHTML = listHtml(list); }}
    root.classList.toggle('wave', config.wave_enabled === true);
    maybeRankFlash(list);
  }};
  if (transitioned) {{
    stage.classList.add('leaving');
    setTimeout(function() {{
      paint();
      stage.classList.remove('leaving');
      stage.classList.add('entering');
      setTimeout(function() {{ stage.classList.remove('entering'); }}, 400);
    }}, 300);
  }} else {{
    paint();
  }}
}}
function maybeRankFlash(list) {{
  if (config.enable_rank_change_anim === false) {{
    list.forEach(function(row) {{ lastRanks[keyOf(row)] = row.rank; }});
    return;
  }}
  list.forEach(function(row) {{
    const k = keyOf(row);
    const prev = lastRanks[k];
    if (prev !== undefined && prev !== row.rank) {{
      const els = document.querySelectorAll('[data-k="' + k.replace(/"/g,'') + '"]');
      els.forEach(function(el) {{
        el.classList.remove('rank-flash');
        void el.offsetWidth;
        el.classList.add('rank-flash');
      }});
    }}
    lastRanks[k] = row.rank;
  }});
}}
function tickValues() {{
  const list = currentLeaders();
  list.forEach(function(row) {{
    const v = tween(row);
    const els = document.querySelectorAll('[data-k="' + keyOf(row).replace(/"/g,'') + '"] [data-val="1"]');
    els.forEach(function(el) {{ el.textContent = fmt(v); }});
  }});
}}
function applyState(st) {{
  if (!st) return;
  if (st.config) config = Object.assign(config || {{}}, st.config);
  if (st.rankings) rankings = st.rankings;
  if (st.locale) locale = String(st.locale).toLowerCase() === 'en' ? 'en' : 'uk';
  let transitioned = false;
  if (st.presentation) {{
    const nextToken = Number(st.presentation.transition_token || 0);
    if (lastToken >= 0 && nextToken !== lastToken) transitioned = true;
    lastToken = nextToken;
    presentation = Object.assign(presentation || {{}}, st.presentation);
  }}
  render(transitioned);
}}
function handleMsg(d) {{
  if (!d || !d.op) return;
  if (d.op === 'initial_state') applyState(d.state || {{}});
  if (d.op === 'patch') applyState(d.patch || {{}});
}}
setInterval(tickValues, 140);
(function connect() {{
  let tries = 0;
  function go() {{
    tries++;
    let ws; try {{ ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws'); }}
    catch (e) {{ setTimeout(go, 1000); return; }}
    ws.onopen = function() {{ tries = 0; ws.send(JSON.stringify({_json_for_script(subscribe_msg)})); }};
    ws.onmessage = function(ev) {{ try {{ handleMsg(JSON.parse(ev.data)); }} catch (e) {{}} }};
    ws.onclose = function() {{ setTimeout(go, Math.min(5000, 300 + tries * 350)); }};
  }} go();
}})();
render(false);
}})();</script></body></html>"""

    def initial_state(self, params: dict[str, Any]) -> dict[str, Any]:
        from stream_cheremsha.overlays.widget_instances import typed_config_for_type

        cfg = typed_config_for_type(
            "live_leaderboard_simple",
            params,
            load_live_leaderboard_simple_config,
            live_leaderboard_simple_config_from_json_text,
        )
        return {
            "config": live_leaderboard_simple_config_to_public_dict(cfg),
            "rankings": LiveLeaderboardRankingEngine().all_rankings(limit=cfg.top_n),
            "locale": load_ui_locale(),
            "presentation": {
                "source_id": "likers",
                "scene_id": "hall_of_fame",
                "sequence_index": 0,
                "scene_started_at_ms": 0,
                "scene_duration_ms": 8000,
                "transition_token": 1,
                "server_now_ms": 0,
            },
        }
