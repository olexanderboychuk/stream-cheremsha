from __future__ import annotations

# ruff: noqa: E501
import json
from typing import Any

from stream_cheremsha.overlays.battle_overlay_config import (
    battle_overlay_config_from_json_text,
    battle_overlay_config_to_json_text,
    load_battle_overlay_config,
)
from stream_cheremsha.overlays.models import normalize_instance_id
from stream_cheremsha.overlays.ui_locale import load_ui_locale


def _json_for_script(value: Any) -> str:
    s = json.dumps(value, ensure_ascii=False)
    return s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


class BattleOverlayType:
    type = "battle"

    def render_html(self, params: dict[str, Any]) -> str:
        raw_instance = params.get("instance")
        try:
            instance = normalize_instance_id(str(raw_instance or ""))
        except ValueError:
            instance = "default"

        subscribe_msg = {
            "op": "subscribe",
            "type": "battle",
            "instance": instance,
            "params": {},
        }
        initial_scale = 100
        instance_settings = params.get("instance_settings")
        if isinstance(instance_settings, dict):
            try:
                initial_scale = max(40, min(250, int(instance_settings.get("scale_percent", 100))))
            except (TypeError, ValueError):
                initial_scale = 100
        root_style = f"--bt-scale:{initial_scale / 100:.4f};--bt-u:{initial_scale / 100:.4f};"

        return f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Cheremsha Battle</title>
    <style>
      html, body {{
        margin:0; padding:0; background:transparent; overflow:hidden;
        height:100%; width:100%;
      }}
      * {{ box-sizing:border-box; }}
      .bt-root {{
        position:absolute; inset:0;
        font-family: var(--bfont, 'Segoe UI', system-ui, sans-serif);
        pointer-events:none;
        display:flex; flex-direction:column; justify-content:center;
        padding: calc(8px * var(--bt-u, 1)) calc(14px * var(--bt-u, 1));
        color:#f1f5f9;
        --bt-scale:1; --bt-u: var(--bt-scale, 1);
        --bt-accent:#a855f7; --bt-accent2:#22d3ee; --bt-accent3:#f472b6;
        --bt-bg:rgba(11,14,26,0.72); --bt-panel:rgba(17,22,38,0.78);
        --bt-line:rgba(168,85,247,0.35); --bt-glow:0 0 18px rgba(168,85,247,0.55);
        --bt-text:#f1f5f9; --bt-dim:rgba(226,232,240,0.75);
      }}
      .bt-root[data-theme="cyber"] {{
        --bt-accent:#38bdf8; --bt-accent2:#8b5cf6; --bt-accent3:#38bdf8;
        --bt-bg:rgba(6,14,28,0.78); --bt-panel:rgba(8,20,40,0.82);
        --bt-line:rgba(56,189,248,0.4); --bt-glow:0 0 18px rgba(56,189,248,0.6);
      }}
      .bt-root[data-theme="arcade"] {{
        --bt-accent:#fbbf24; --bt-accent2:#ef4444; --bt-accent3:#fb923c;
        --bt-bg:rgba(24,12,8,0.78); --bt-panel:rgba(32,16,10,0.82);
        --bt-line:rgba(251,191,36,0.45); --bt-glow:0 0 18px rgba(251,191,36,0.6);
      }}
      .bt-root[data-theme="minimal"] {{
        --bt-accent:#e2e8f0; --bt-accent2:#94a3b8; --bt-accent3:#cbd5e1;
        --bt-bg:rgba(10,12,16,0.6); --bt-panel:rgba(15,18,24,0.65);
        --bt-line:rgba(226,232,240,0.25); --bt-glow:none;
      }}
      .bt-card {{
        background:var(--bt-bg); border:1px solid var(--bt-line); border-radius:14px;
        padding: calc(10px * var(--bt-u,1)) calc(16px * var(--bt-u,1));
        box-shadow:var(--bt-glow);
      }}
      .bt-title {{
        text-align:center; font-weight:900; letter-spacing:0.22em;
        font-size:calc(15px * var(--bt-u,1)); color:var(--bt-accent);
        text-shadow:0 1px 0 #000, 0 2px 8px rgba(0,0,0,0.9);
        margin-bottom:calc(8px * var(--bt-u,1));
      }}
      .bt-grid {{
        display:grid; grid-template-columns:minmax(0,1fr) auto minmax(0,1fr);
        gap:calc(12px * var(--bt-u,1)); align-items:center;
      }}
      .bt-side {{ min-width:0; text-align:center; }}
      .bt-side .bt-name {{
        font-weight:800; font-size:calc(16px * var(--bt-u,1));
        white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
        text-shadow:0 1px 0 #000, 0 2px 8px rgba(0,0,0,0.9);
      }}
      .bt-side .bt-score {{
        font-weight:900; font-size:calc(30px * var(--bt-u,1)); line-height:1.05;
        text-shadow:0 1px 0 #000, 0 2px 10px rgba(0,0,0,0.9);
      }}
      .bt-side.left .bt-score {{ color:var(--bt-accent2); }}
      .bt-side.right .bt-score {{ color:var(--bt-accent3); }}
      .bt-avatar {{
        width:calc(64px * var(--bt-u,1)); height:calc(64px * var(--bt-u,1));
        border-radius:50%; margin:0 auto calc(6px * var(--bt-u,1));
        border:2px solid var(--bt-line); overflow:hidden; position:relative;
        background:var(--bt-panel); display:flex; align-items:center; justify-content:center;
        font-weight:900; font-size:calc(22px * var(--bt-u,1));
      }}
      .bt-avatar img {{ width:100%; height:100%; object-fit:cover; display:block; }}
      .bt-avatar.pulse {{ animation:btPulse 0.5s ease-out; }}
      @keyframes btPulse {{ 0% {{ transform:scale(1); }} 40% {{ transform:scale(1.18); }} 100% {{ transform:scale(1); }} }}
      .bt-center {{ text-align:center; min-width:calc(120px * var(--bt-u,1)); }}
      .bt-vs {{
        font-weight:900; font-size:calc(26px * var(--bt-u,1)); letter-spacing:0.1em;
        color:var(--bt-accent); text-shadow:0 1px 0 #000, 0 0 16px currentColor;
      }}
      .bt-timer {{
        font-weight:800; font-size:calc(20px * var(--bt-u,1)); color:var(--bt-text);
        text-shadow:0 1px 0 #000, 0 2px 8px rgba(0,0,0,0.9);
        display:flex; align-items:center; justify-content:center; gap:6px;
      }}
      .bt-timer svg {{ width:16px; height:16px; stroke:currentColor; fill:none; stroke-width:2; }}
      .bt-round {{ font-size:calc(12px * var(--bt-u,1)); color:var(--bt-dim); letter-spacing:0.18em; margin-top:2px; }}
      .bt-dots {{ display:flex; gap:4px; justify-content:center; margin-top:4px; }}
      .bt-dots i {{ width:8px; height:8px; border-radius:50%; background:rgba(148,163,184,0.35); display:block; }}
      .bt-dots i.won-left {{ background:var(--bt-accent2); box-shadow:0 0 8px var(--bt-accent2); }}
      .bt-dots i.won-right {{ background:var(--bt-accent3); box-shadow:0 0 8px var(--bt-accent3); }}
      .bt-bar {{
        margin-top:calc(10px * var(--bt-u,1)); height:calc(12px * var(--bt-u,1));
        border-radius:99px; background:rgba(148,163,184,0.22); overflow:hidden;
        display:flex; border:1px solid rgba(0,0,0,0.5);
      }}
      .bt-bar i {{ display:block; height:100%; transition:width 0.35s ease; }}
      .bt-bar .fill-left {{ background:linear-gradient(90deg, var(--bt-accent2), var(--bt-accent)); }}
      .bt-bar .fill-right {{ background:linear-gradient(90deg, var(--bt-accent), var(--bt-accent3)); }}
      .bt-root.is-close .fill-left, .bt-root.is-close .fill-right {{ filter:brightness(1.25); }}
      .bt-badge {{
        position:absolute; left:50%; top:calc(6px * var(--bt-u,1)); transform:translateX(-50%);
        font-weight:900; letter-spacing:0.14em; font-size:calc(13px * var(--bt-u,1));
        background:rgba(0,0,0,0.72); border:1px solid var(--bt-line); border-radius:99px;
        padding:4px 14px; opacity:0; transition:opacity 0.3s ease; white-space:nowrap;
      }}
      .bt-badge.show {{ opacity:1; }}
      .bt-root.is-final .bt-timer {{ animation:btFinal 0.6s ease-out 1; color:#fecaca; }}
      @keyframes btFinal {{ 0% {{ transform:scale(1); }} 40% {{ transform:scale(1.25); }} 100% {{ transform:scale(1); }} }}
      .bt-winner {{
        text-align:center; font-weight:900; font-size:calc(24px * var(--bt-u,1));
        color:#fde68a; text-shadow:0 1px 0 #000, 0 0 18px rgba(251,191,36,0.8);
        margin-top:calc(6px * var(--bt-u,1));
      }}
      .bt-winner small {{ display:block; font-size:calc(14px * var(--bt-u,1)); color:var(--bt-text); font-weight:700; }}
      .bt-idle {{ text-align:center; color:var(--bt-dim); font-size:calc(14px * var(--bt-u,1)); padding:calc(6px * var(--bt-u,1)); }}
      .bt-root.hide-idle.is-idle .bt-card {{ display:none; }}
      @media (max-width:700px) {{
        .bt-avatar {{ width:40px; height:40px; font-size:15px; }}
        .bt-side .bt-score {{ font-size:22px; }}
        .bt-vs {{ font-size:19px; }}
        .bt-title {{ font-size:12px; }}
        .bt-subtitle {{ display:none; }}
      }}
    </style>
  </head>
  <body>
    <div class="bt-root is-idle" id="btRoot" data-theme="cheremsha_neon" style="{root_style}">
      <div class="bt-badge" id="btBadge"></div>
      <div class="bt-card" id="btCard">
        <div class="bt-title" id="btTitle">BATTLE</div>
        <div class="bt-grid">
          <div class="bt-side left" id="btLeft">
            <div class="bt-avatar" id="btAvatarL"><span id="btInitL">?</span></div>
            <div class="bt-name" id="btNameL">—</div>
            <div class="bt-score" id="btScoreL">0</div>
          </div>
          <div class="bt-center">
            <div class="bt-vs">VS</div>
            <div class="bt-timer" id="btTimer">
              <svg viewBox="0 0 24 24"><circle cx="12" cy="13" r="8"/><path d="M12 9v4l2.5 2.5M9 2h6"/></svg>
              <span id="btTimerText">0:00</span>
            </div>
            <div class="bt-round" id="btRound">ROUND 1 · BO3</div>
            <div class="bt-dots" id="btDots"></div>
          </div>
          <div class="bt-side right" id="btRight">
            <div class="bt-avatar" id="btAvatarR"><span id="btInitR">?</span></div>
            <div class="bt-name" id="btNameR">—</div>
            <div class="bt-score" id="btScoreR">0</div>
          </div>
        </div>
        <div class="bt-bar"><i class="fill-left" id="btFillL" style="width:50%"></i><i class="fill-right" id="btFillR" style="width:50%"></i></div>
        <div class="bt-winner" id="btWinner" style="display:none"></div>
        <div class="bt-idle" id="btIdle">Waiting for 2 gifters…</div>
      </div>
    </div>
    <script>
      (function() {{
        const root = document.getElementById('btRoot');
        const $ = (id) => document.getElementById(id);
        let state = null;
        let badgeTimer = null;
        let lastDelta = {{left: 0, right: 0}};

        function fmt(s) {{
          s = Math.max(0, parseInt(s || 0, 10));
          return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
        }}

        function initials(name) {{
          const t = String(name || '?').trim();
          return (t[0] || '?').toUpperCase();
        }}

        function showBadge(text) {{
          const b = $('btBadge');
          if (!text) {{ b.classList.remove('show'); return; }}
          b.textContent = text;
          b.classList.add('show');
          if (badgeTimer) clearTimeout(badgeTimer);
          badgeTimer = setTimeout(() => b.classList.remove('show'), 1200);
        }}

        function setAvatar(slot, p, showAvatars) {{
          const av = slot === 'left' ? $('btAvatarL') : $('btAvatarR');
          const init = slot === 'left' ? $('btInitL') : $('btInitR');
          const oldImg = av.querySelector('img');
          if (oldImg) oldImg.remove();
          init.style.display = 'flex';
          init.textContent = initials(p ? p.name : '?');
          if (showAvatars && p && p.avatar_url) {{
            const img = document.createElement('img');
            img.alt = '';
            img.onerror = () => {{ img.style.display = 'none'; init.style.display = 'flex'; }};
            img.src = p.avatar_url;
            init.style.display = 'none';
            av.prepend(img);
          }}
        }}

        function applyPatch(patch) {{
          if (!patch || typeof patch !== 'object') return;
          if (!state) state = {{}};
          for (const k of ['config','status','round','best_of','round_wins','duration_s','remaining_seconds','countdown_remaining_s','participants','teams','combo','flags','events','winner','locale','battle_id']) {{
            if (patch[k] !== undefined) state[k] = patch[k];
          }}
        }}

        function render() {{
          if (!state) return;
          const cfg = state.config || {{}};
          document.body.style.setProperty('--bfont', (cfg.font_family || 'Segoe UI') + ', system-ui, sans-serif');
          root.dataset.theme = cfg.theme || 'cheremsha_neon';
          $('btTitle').textContent = cfg.battle_name || 'BATTLE';
          const status = state.status || 'idle';
          const flags = state.flags || {{}};
          const combo = state.combo || {{}};
          root.classList.toggle('is-idle', status === 'idle');
          root.classList.toggle('is-countdown', status === 'countdown');
          root.classList.toggle('is-active', status === 'active');
          root.classList.toggle('is-finished', status === 'finished');
          root.classList.toggle('is-close', !!flags.is_close);
          root.classList.toggle('is-combo', !!(combo && combo.count > 0 && combo.multiplier > 1));
          root.classList.toggle('is-comeback', !!flags.is_comeback);
          root.classList.toggle('is-final', !!flags.final_push);
          root.classList.toggle('hide-idle', !!cfg.hide_when_idle);

          const parts = state.participants || [];
          const teams = state.teams || [];
          const L = parts.find((p) => p.team_id === 'left') || null;
          const R = parts.find((p) => p.team_id === 'right') || null;
          const tL = teams.find((t) => t.id === 'left') || {{score: 0, round_wins: 0}};
          const tR = teams.find((t) => t.id === 'right') || {{score: 0, round_wins: 0}};
          const showAv = cfg.show_avatars !== false;

          $('btNameL').textContent = L ? L.name : '—';
          $('btNameR').textContent = R ? R.name : '—';
          $('btScoreL').textContent = tL.score || 0;
          $('btScoreR').textContent = tR.score || 0;
          setAvatar('left', L, showAv);
          setAvatar('right', R, showAv);

          const total = Math.max(1, (tL.score || 0) + (tR.score || 0));
          $('btFillL').style.width = (((tL.score || 0) / total) * 100).toFixed(1) + '%';
          $('btFillR').style.width = (((tR.score || 0) / total) * 100).toFixed(1) + '%';
          if ((tL.score || 0) >= (tR.score || 0)) {{
            $('btFillL').style.boxShadow = '0 0 10px currentColor';
            $('btFillR').style.boxShadow = 'none';
          }} else {{
            $('btFillR').style.boxShadow = '0 0 10px currentColor';
            $('btFillL').style.boxShadow = 'none';
          }}

          let secs = state.remaining_seconds || 0;
          if (status === 'countdown') secs = state.countdown_remaining_s || 0;
          if (status === 'finished') secs = 0;
          $('btTimerText').textContent = status === 'countdown' ? ('START ' + secs) : fmt(secs);
          $('btRound').textContent = 'ROUND ' + (state.round || 1) + ' · BO' + (state.best_of || 3);

          const dots = $('btDots');
          dots.innerHTML = '';
          const wins = state.round_wins || {{left: tL.round_wins || 0, right: tR.round_wins || 0}};
          const need = Math.floor((state.best_of || 3) / 2) + 1;
          for (let i = 0; i < need; i++) {{
            const a = document.createElement('i');
            if ((wins.left || 0) > i) a.className = 'won-left';
            dots.appendChild(a);
            const b = document.createElement('i');
            if ((wins.right || 0) > i) b.className = 'won-right';
            dots.appendChild(b);
          }}

          $('btIdle').style.display = status === 'idle' ? 'block' : 'none';
          const w = $('btWinner');
          if (status === 'finished' && cfg.show_winner_screen !== false && state.winner) {{
            w.style.display = 'block';
            const nm = state.winner.name || state.winner.team_id;
            w.innerHTML = 'WINNER ' + String(nm).toUpperCase().replace(/</g, '&lt;') +
              '<small>' + (tL.score || 0) + ' vs ' + (tR.score || 0) + '</small>';
          }} else {{
            w.style.display = 'none';
            w.innerHTML = '';
          }}

          if (cfg.show_event_badges === false) {{ showBadge(''); return; }}
          const evs = state.events || [];
          const last = evs.length ? evs[evs.length - 1] : null;
          if (combo && combo.multiplier > 1) {{
            showBadge('COMBO x' + combo.multiplier);
          }} else if (last && last.type === 'comeback') {{
            showBadge('COMEBACK');
          }} else if (last && last.type === 'final_push') {{
            showBadge('FINAL PUSH');
          }} else if (last && last.type === 'big_gift') {{
            const pts = (last.payload && last.payload.diamonds) || '';
            showBadge('+' + pts);
          }}
          // Pulse avatar on fresh score change (max 2 DOM nodes reused).
          if ((tL.score || 0) !== lastDelta.left) {{
            lastDelta.left = tL.score || 0;
            const av = $('btAvatarL');
            av.classList.remove('pulse'); void av.offsetWidth; av.classList.add('pulse');
          }}
          if ((tR.score || 0) !== lastDelta.right) {{
            lastDelta.right = tR.score || 0;
            const av = $('btAvatarR');
            av.classList.remove('pulse'); void av.offsetWidth; av.classList.add('pulse');
          }}
        }}

        function handleMsg(obj) {{
          if (!obj || typeof obj !== 'object') return;
          if (obj.op === 'initial_state' && obj.state) {{
            state = {{}};
            applyPatch(obj.state);
            render();
          }} else if (obj.op === 'patch' && obj.patch) {{
            applyPatch(obj.patch);
            render();
          }}
        }}

        const wsUrl = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws';
        let ws = null;
        let tries = 0;
        function connect() {{
          tries += 1;
          const backoff = Math.min(5000, 250 + Math.floor(Math.random() * 250) + (tries * 350));
          try {{ ws = new WebSocket(wsUrl); }}
          catch (e) {{ setTimeout(connect, backoff); return; }}
          ws.onopen = () => {{
            tries = 0;
            ws.send(JSON.stringify({_json_for_script(subscribe_msg)}));
          }};
          ws.onmessage = (ev) => {{
            let obj = null;
            try {{ obj = JSON.parse(ev.data); }} catch (e) {{ return; }}
            handleMsg(obj);
          }};
          ws.onclose = () => setTimeout(connect, backoff);
        }}
        connect();
      }})();
    </script>
  </body>
</html>"""
    def initial_state(self, params: dict[str, Any]) -> dict[str, Any]:
        from stream_cheremsha.overlays.widget_instances import typed_config_for_type

        cfg = typed_config_for_type(
            "battle",
            params,
            load_battle_overlay_config,
            battle_overlay_config_from_json_text,
        )
        cfg_payload = json.loads(battle_overlay_config_to_json_text(cfg))
        cfg_payload["ui_locale"] = load_ui_locale()
        return {
            "config": cfg_payload,
            "status": "idle",
            "round": 1,
            "best_of": int(cfg.best_of),
            "round_wins": {"left": 0, "right": 0},
            "duration_s": int(cfg.round_duration_s),
            "remaining_seconds": int(cfg.round_duration_s),
            "countdown_remaining_s": 0,
            "participants": [],
            "teams": [
                {"id": "left", "score": 0, "round_wins": 0},
                {"id": "right", "score": 0, "round_wins": 0},
            ],
            "combo": {"team_id": None, "count": 0, "multiplier": 1.0},
            "flags": {"is_close": False, "is_comeback": False, "final_push": False},
            "events": [],
            "winner": None,
        }
