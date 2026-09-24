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
    html, body {{ margin:0; padding:0; background:transparent; overflow:hidden; height:100%; width:100%; }}
    * {{ box-sizing:border-box; }}
    .bt-root {{
      position:absolute; inset:0; pointer-events:none;
      font-family: var(--bfont, 'Segoe UI', system-ui, sans-serif);
      color:#f1f5f9;
      --bt-f: calc(var(--bt-u, 1) * 1.05vh);
      --lt-primary:#22d3ee; --lt-secondary:#3b82f6; --lt-glow:rgba(34,211,238,.55); --lt-soft:rgba(34,211,238,.16);
      --rt-primary:#f472b6; --rt-secondary:#a855f7; --rt-glow:rgba(244,114,182,.55); --rt-soft:rgba(244,114,182,.16);
      --bg-1:#0B0A14; --bg-2:#16112A; --accent:#a855f7; --line:rgba(168,85,247,.35);
      --text:#f1f5f9; --dim:rgba(226,232,240,.75);
    }}
    .bt-root[data-theme="cyber"] {{
      --lt-primary:#38bdf8; --lt-secondary:#60a5fa; --lt-glow:rgba(56,189,248,.55); --lt-soft:rgba(56,189,248,.16);
      --rt-primary:#a855f7; --rt-secondary:#c084fc; --rt-glow:rgba(168,85,247,.55); --rt-soft:rgba(168,85,247,.16);
      --bg-1:#060E1C; --bg-2:#0B1629; --accent:#38bdf8;
    }}
    .bt-root[data-theme="arcade"] {{
      --lt-primary:#fbbf24; --lt-secondary:#f97316; --lt-glow:rgba(251,191,36,.55); --lt-soft:rgba(251,191,36,.16);
      --rt-primary:#ef4444; --rt-secondary:#fb923c; --rt-glow:rgba(239,68,68,.55); --rt-soft:rgba(239,68,68,.16);
      --bg-1:#161008; --bg-2:#22150A; --accent:#fbbf24; --line:rgba(251,191,36,.4);
    }}
    .bt-root[data-theme="minimal"] {{
      --lt-primary:#e2e8f0; --lt-secondary:#94a3b8; --lt-glow:rgba(226,232,240,.18); --lt-soft:rgba(226,232,240,.08);
      --rt-primary:#cbd5e1; --rt-secondary:#64748b; --rt-glow:rgba(203,209,225,.18); --rt-soft:rgba(203,209,225,.08);
      --bg-1:#0A0C12; --bg-2:#11151E; --accent:#e2e8f0; --line:rgba(226,232,240,.18);
    }}
    .bt-card {{
      position:absolute; inset:0;
      background: linear-gradient(135deg, var(--bg-1), var(--bg-2));
      border: 1px solid var(--line); border-radius: calc(min(24px, 3.5 * var(--bt-f)));
      overflow:hidden; display:flex; flex-direction:column;
      box-shadow:
        inset 0 1px 0 rgba(255,255,255,.07),
        inset 0 0 calc(24 * var(--bt-f)) rgba(0,0,0,.45),
        0 8px 30px rgba(0,0,0,.5),
        0 0 calc(18 * var(--bt-f)) var(--lt-soft),
        0 0 calc(18 * var(--bt-f)) var(--rt-soft);
    }}
    .bt-card::before {{
      content:""; position:absolute; inset:0; pointer-events:none; z-index:0;
      background:
        radial-gradient(ellipse at 12% 50%, var(--lt-soft), transparent 58%),
        radial-gradient(ellipse at 88% 50%, var(--rt-soft), transparent 58%);
    }}
    .bt-main {{ position:relative; z-index:1; flex:1; min-height:0; display:flex; flex-direction:column; }}
    .bt-stage {{
      flex:1; min-height:0; display:grid; grid-template-columns: 1fr auto 1fr;
      gap: calc(3 * var(--bt-f)); align-items:center; padding: calc(2 * var(--bt-f)) calc(4 * var(--bt-f));
    }}
    .bt-side {{
      position:relative; z-index:1; min-width:0; min-height:0; display:flex; flex-direction:column;
      justify-content:center; align-items:center; gap: calc(1.1 * var(--bt-f));
    }}
    .bt-side--left {{ align-items:flex-start; text-align:left; }}
    .bt-side--right {{ align-items:flex-end; text-align:right; }}
    .bt-score {{ font-weight:900; font-size: calc(9 * var(--bt-f)); line-height:1.05; letter-spacing:.02em;
      min-width:0; text-shadow: 0 2px 0 #000, 0 2px 10px rgba(0,0,0,.9); }}
    .bt-score--left {{ color: var(--lt-primary); text-shadow: 0 2px 0 #000, 0 0 calc(9 * var(--bt-f)) var(--lt-glow); }}
    .bt-score--right {{ color: var(--rt-primary); text-shadow: 0 2px 0 #000, 0 0 calc(9 * var(--bt-f)) var(--rt-glow); }}
    .bt-name-wrap {{ display:flex; align-items:center; gap: calc(1.6 * var(--bt-f)); width:100%; min-width:0; }}
    .bt-name {{ font-weight:900; font-size: calc(5.5 * var(--bt-f)); line-height:1.05; letter-spacing:.01em;
      white-space:nowrap; overflow:hidden; text-overflow:ellipsis; min-width:0; flex:1 1 auto;
      text-shadow: 0 1px 0 #000, 0 2px 8px rgba(0,0,0,.9); }}
    .bt-name--left {{ color: var(--lt-primary); text-shadow: 0 1px 0 #000, 0 0 calc(8 * var(--bt-f)) var(--lt-glow); }}
    .bt-name--right {{ color: var(--rt-primary); text-shadow: 0 1px 0 #000, 0 0 calc(8 * var(--bt-f)) var(--rt-glow); }}
    .bt-avatar {{ width: calc(15 * var(--bt-f)); height: calc(15 * var(--bt-f)); border-radius:50%;
      border: calc(1.4 * var(--bt-f)) solid var(--line); overflow:hidden; position:relative;
      display:flex; align-items:center; justify-content:center; background: var(--bg-2);
      font-weight:900; font-size: calc(5.2 * var(--bt-f)); flex:0 0 auto;
      box-shadow: 0 0 calc(8 * var(--bt-f)) rgba(0,0,0,.6); }}
    .bt-avatar--left {{ border-color: var(--lt-primary); box-shadow: 0 0 calc(9 * var(--bt-f)) var(--lt-glow); }}
    .bt-avatar--right {{ border-color: var(--rt-primary); box-shadow: 0 0 calc(9 * var(--bt-f)) var(--rt-glow); }}
    .bt-avatar img {{ width:100%; height:100%; object-fit:cover; display:block; }}
    .bt-avatar .av-fallback {{ display:flex; align-items:center; justify-content:center; color: var(--text); }}
    .bt-avatar.pulse {{ animation: btPulse .5s ease-out; }}
    @keyframes btPulse {{ 0% {{ transform:scale(1); }} 40% {{ transform:scale(1.16); }} 100% {{ transform:scale(1); }} }}
    .bt-center {{ display:flex; flex-direction:column; align-items:center; justify-content:center;
      gap: calc(1.5 * var(--bt-f)); min-width: calc(10 * var(--bt-f)); }}
    .bt-center-label {{ font-weight:900; font-size: calc(3 * var(--bt-f)); letter-spacing:.34em;
      color: var(--accent); text-shadow: 0 0 calc(6 * var(--bt-f)) var(--accent); }}
    .bt-vs {{ font-weight:900; font-size: calc(4.8 * var(--bt-f)); letter-spacing:.12em; color:#F8FAFC;
      text-shadow: 0 2px 0 #000, 0 0 calc(9 * var(--bt-f)) rgba(168,85,247,.6); }}
    .bt-timer {{ font-weight:800; font-size: calc(5.8 * var(--bt-f)); font-variant-numeric: tabular-nums;
      color: var(--text); display:flex; align-items:center; justify-content:center; gap: calc(.9 * var(--bt-f));
      text-shadow: 0 2px 0 #000, 0 2px 10px rgba(0,0,0,.9); }}
    .bt-timer svg {{ width: calc(2.8 * var(--bt-f)); height: calc(2.8 * var(--bt-f)); stroke: currentColor; fill:none; stroke-width:2; }}
    .bt-round {{ font-weight:700; font-size: calc(2.3 * var(--bt-f)); letter-spacing:.2em; color: var(--dim); }}
    .bt-dots {{ display:flex; gap: calc(.9 * var(--bt-f)); justify-content:center; }}
    .bt-dots i {{ width: calc(1.5 * var(--bt-f)); height: calc(1.5 * var(--bt-f)); border-radius:50%;
      background: rgba(148,163,184,.3); }}
    .bt-dots i.won-left {{ background: var(--lt-primary); box-shadow: 0 0 calc(1.6 * var(--bt-f)) var(--lt-glow); }}
    .bt-dots i.won-right {{ background: var(--rt-primary); box-shadow: 0 0 calc(1.6 * var(--bt-f)) var(--rt-glow); }}
    .bt-final-label {{ font-weight:900; font-size: calc(2.2 * var(--bt-f)); letter-spacing:.3em; color:#FECACA; opacity:0; }}
    .is-final .bt-final-label {{ animation: btFinalPulse 1s ease-in-out infinite alternate; }}
    @keyframes btFinalPulse {{ 0% {{ opacity:.3; transform: scale(.98); }} 100% {{ opacity:.95; transform: scale(1.02); }} }}
    .is-final .bt-timer {{ color:#FECACA; text-shadow: 0 2px 0 #000, 0 0 calc(9 * var(--bt-f)) rgba(254,202,202,.7); }}
    .is-final .bt-bar-track {{ box-shadow: 0 0 calc(10 * var(--bt-f)) var(--lt-glow), 0 0 calc(10 * var(--bt-f)) var(--rt-glow); }}
    .is-final .fill-left, .is-final .fill-right {{ filter: brightness(1.15); }}
    .is-close .fill-left, .is-close .fill-right {{ filter: brightness(1.1); }}
    .bt-bar-wrap {{ padding: calc(1.2 * var(--bt-f)) calc(4 * var(--bt-f)); min-height:0; }}
    .bt-gift-prompt {{
      align-self:center; min-height:0; flex-shrink:0; justify-content:center; align-items:center;
      padding: calc(1.6 * var(--bt-f)) calc(4 * var(--bt-f)); gap: calc(3 * var(--bt-f));
    }}
    .bt-gift-prompt-inner {{
      display:inline-flex; align-items:center; justify-content:center; gap: calc(1.4 * var(--bt-f));
      min-width: 0; max-width: calc(640px); width: 100%; padding: calc(1.1 * var(--bt-f)) calc(3.6 * var(--bt-f));
      border-radius:999px; border:1px solid rgba(168,85,247,.38);
      background: rgba(0,0,0,.42); box-sizing:border-box;
      backdrop-filter: blur(6px);
    }}
    .bt-gift-prompt-inner .gift-ico {{
      display:inline-grid; place-items:center; flex:0 0 auto;
      width: calc(2.6 * var(--bt-f)); height: calc(2.6 * var(--bt-f));
      border-radius:18%; overflow:hidden;
      background: rgba(168,85,247,.16); border:1px solid rgba(168,85,247,.5);
      box-shadow: 0 0 calc(5 * var(--bt-f)) rgba(168,85,247,.35);
    }}
    .bt-gift-prompt-inner .gift-ico svg {{ width:100%; height:100%; stroke: currentColor; fill: none; stroke-width:2; stroke-linecap:round; stroke-linejoin:round; }}
    .bt-gift-prompt-inner .gift-msg {{
      font-weight:800; font-size: calc(2.5 * var(--bt-f)); letter-spacing:.04em; color: var(--accent);
      white-space:nowrap; overflow:hidden; text-overflow:ellipsis; min-width:0; flex:1 1 auto;
      text-shadow: 0 2px 8px rgba(0,0,0,.6);
    }}
    .bt-gift-prompt-inner .gift-hint {{
      font-weight:600; font-size: calc(1.8 * var(--bt-f)); color: var(--dim); letter-spacing:.02em;
      white-space:nowrap; overflow:hidden; text-overflow:ellipsis; min-width:0;
    }}
    .bt-gift-prompt-inner .gift-fx {{
      font-weight:900; font-size: calc(2.5 * var(--bt-f)); color: var(--accent);
      text-shadow: 0 0 calc(6 * var(--bt-f)) rgba(168,85,247,.8), 0 2px 8px rgba(0,0,0,.6);
    }}
    .is-giftpulse .bt-gift-prompt-inner {{
      border-color: var(--accent); box-shadow: 0 0 calc(10 * var(--bt-f)) var(--accent), 0 0 calc(14 * var(--bt-f)) rgba(168,85,247,.35);
    }}
    @keyframes btGiftPulse {{ 0% {{ transform: scale(1); opacity:.95; }} 35% {{ transform: scale(1.06); opacity:1; }} 100% {{ transform: scale(1); opacity:.95; }} }}
    .is-giftpulse .bt-gift-prompt-inner {{ animation: btGiftPulse .7s ease-out; }}
    @keyframes btGiftGlowPulse {{ 0% {{ opacity:.85; }} 50% {{ opacity:1; }} 100% {{ opacity:.85; }} }}
    .bt-gift-prompt-inner .gift-ico {{ opacity:.85; animation: btGiftGlowPulse 3.2s ease-in-out infinite; }}
    @keyframes btGiftFade {{ from {{ opacity:0; transform: translateY(3px); }} to {{ opacity:1; transform: translateY(0); }} }}
    .bt-gift-fade {{ animation: btGiftFade .3s ease-out; }}
    .bt-bar-track {{
      height: calc(2.6 * var(--bt-f)); border-radius:999px; background: rgba(255,255,255,.06);
      border:1px solid rgba(255,255,255,.06); overflow:hidden; display:flex; position:relative;
    }}
    .fill-left {{
      display:block; height:100%; width:50%; background: linear-gradient(90deg, var(--lt-primary), var(--lt-secondary), var(--accent));
      transition: width .4s ease, filter .3s, background .3s, box-shadow .3s;
    }}
    .fill-right {{
      display:block; height:100%; width:50%; margin-left:auto; background: linear-gradient(90deg, var(--accent), var(--rt-secondary), var(--rt-primary));
      transition: width .4s ease, filter .3s, background .3s, box-shadow .3s;
    }}
    .is-leader-left .fill-left {{ box-shadow: 0 0 calc(8 * var(--bt-f)) var(--lt-glow); filter: brightness(1.1); }}
    .is-leader-right .fill-right {{ box-shadow: 0 0 calc(8 * var(--bt-f)) var(--rt-glow); filter: brightness(1.1); }}
    .bt-zero .fill-left, .bt-zero .fill-right {{
      background: linear-gradient(90deg, rgba(148,163,184,.18), rgba(148,163,184,.12));
      filter:none !important; box-shadow:none !important;
    }}
    .is-zero-bar .bt-bar-track {{ box-shadow:none; border-color:rgba(148,163,184,.2); }}
    .bt-side::before {{
      content:""; position:absolute; z-index:-1; left:50%; top:50%; width:240px; height:240px;
      transform: translate(-50%, -50%); pointer-events:none;
      border-radius:50%; opacity:.55; filter: blur(calc(16 * var(--bt-f)));
    }}
    .bt-side--left::before {{ background: radial-gradient(ellipse at 50% 50%, var(--lt-glow), transparent 65%); }}
    .bt-side--right::before {{ background: radial-gradient(ellipse at 50% 50%, var(--rt-glow), transparent 65%); }}
    .bt-combo {{ position:absolute; height: calc(2.8 * var(--bt-f)); display:flex; align-items:center; gap: calc(.9 * var(--bt-f));
      background: rgba(0,0,0,.55); border: 1px solid var(--line); border-radius:999px; padding: 0 calc(1.8 * var(--bt-f));
      font-weight:900; font-size: calc(2.4 * var(--bt-f)); letter-spacing:.12em; opacity:0;
      transform: translateY(calc(2 * var(--bt-f))); transition: opacity .3s, transform .3s; z-index:2;
      top: calc(2.4 * var(--bt-f)); }}
    .bt-combo--left {{ left: calc(2.4 * var(--bt-f)); color: var(--lt-primary); border-color: var(--lt-primary);
      box-shadow: 0 0 calc(7 * var(--bt-f)) var(--lt-glow); }}
    .bt-combo--right {{ right: calc(2.4 * var(--bt-f)); color: var(--rt-primary); border-color: var(--rt-primary);
      box-shadow: 0 0 calc(7 * var(--bt-f)) var(--rt-glow); }}
    .bt-combo.show {{ opacity:1; transform: translateY(0); }}
    .bt-events {{ position:absolute; inset:0; pointer-events:none; overflow:hidden; z-index:3; }}
    .bt-float {{ position:absolute; bottom: calc(38%); left: 45%; font-weight:900; font-size: calc(3.4 * var(--bt-f));
      pointer-events:none; white-space:nowrap; animation: btFloat 1.15s ease-out forwards; }}
    .bt-float--left {{ color: var(--lt-primary); text-shadow: 0 0 calc(7 * var(--bt-f)) var(--lt-glow); }}
    .bt-float--right {{ color: var(--rt-primary); text-shadow: 0 0 calc(7 * var(--bt-f)) var(--rt-glow); }}
    @keyframes btFloat {{ 0% {{ transform: translateY(0) scale(1); opacity:1; }} 100% {{ transform: translateY(calc(-16 * var(--bt-f))) scale(.94); opacity:0; }} }}
    .bt-badge {{ position:absolute; left:50%; top: calc(1 * var(--bt-f)); transform: translateX(-50%);
      font-weight:900; letter-spacing:.14em; font-size: calc(2.4 * var(--bt-f)); background: rgba(0,0,0,.75);
      border: 1px solid var(--line); border-radius:999px; padding: calc(.5 * var(--bt-f)) calc(1.6 * var(--bt-f));
      opacity:0; transition:opacity .3s; white-space:nowrap; pointer-events:none; z-index:4; }}
    .bt-badge.show {{ opacity:1; }}
    .bt-comeback {{ position:absolute; top:50%; left:50%; transform: translate(-50%,-50%); font-weight:900;
      font-size: calc(7 * var(--bt-f)); letter-spacing:.3em; color:#FDE68A; pointer-events:none; z-index:4;
      text-shadow: 0 2px 0 #000, 0 0 calc(10 * var(--bt-f)) rgba(253,226,138,.8); opacity:0; }}
    .bt-comeback.show {{ animation: btComeback 1.5s ease-in-out forwards; }}
    @keyframes btComeback {{ 0% {{ transform: translate(-50%,-50%) scale(.7); opacity:0; }} 20% {{ transform: translate(-50%,-50%) scale(1.06); opacity:1; }}
      70% {{ transform: translate(-50%,-50%) scale(1.06); opacity:1; }} 100% {{ transform: translate(-50%,-50%) scale(.7); opacity:0; }} }}
    .bt-winner {{ position:absolute; inset:0; display:none; align-items:center; justify-content:center; flex-direction:column;
      gap: calc(2.2 * var(--bt-f)); padding: calc(6 * var(--bt-f)); border-radius: inherit; pointer-events:none; z-index:5;
      background: linear-gradient(135deg, rgba(11,10,20,.94), rgba(19,16,38,.96)); }}
    .bt-winner.show {{ display:flex; }}
    .bt-winner-label {{ font-weight:900; font-size: calc(3.4 * var(--bt-f)); letter-spacing:.4em; }}
    .bt-winner-avatar {{ width: calc(13 * var(--bt-f)); height: calc(13 * var(--bt-f)); border-radius:50%; object-fit:cover;
      display:flex; align-items:center; justify-content:center; font-weight:900; font-size: calc(4.2 * var(--bt-f));
      border: calc(1.6 * var(--bt-f)) solid currentColor; background: rgba(0,0,0,.35); }}
    .bt-winner-avatar img {{ width:100%; height:100%; object-fit:cover; display:block; }}
    .bt-winner-name {{ font-weight:900; font-size: calc(9 * var(--bt-f)); letter-spacing:.02em; text-shadow: 0 2px 0 #000; }}
    .bt-winner-score {{ font-weight:800; font-size: calc(4.2 * var(--bt-f)); color: var(--text); }}
    .bt-idle {{ position:absolute; inset:0; display:none; align-items:center; justify-content:center; font-weight:800;
      font-size: calc(3.2 * var(--bt-f)); color: var(--dim); letter-spacing:.18em; text-transform:uppercase; pointer-events:none; z-index:6; }}
    .is-idle .bt-stage, .is-idle .bt-bar-wrap, .is-idle .bt-gift-prompt {{ opacity:.14; }}
    .is-idle .bt-idle {{ display:flex; }}
    .hide-idle.is-idle .bt-card {{ opacity:0; transition: opacity .4s; }}
    @media (max-width:700px) {{
      .bt-avatar {{ width: calc(13 * var(--bt-f)); height: calc(13 * var(--bt-f)); font-size: calc(4.4 * var(--bt-f)); }}
      .bt-score {{ font-size: calc(9 * var(--bt-f)); }}
      .bt-vs {{ font-size: calc(4.2 * var(--bt-f)); }}
      .bt-name {{ font-size: calc(4.8 * var(--bt-f)); }}
      .bt-gift-prompt-inner {{ max-width: calc(760px); padding: calc(.8 * var(--bt-f)) calc(2.6 * var(--bt-f)); }}
      .bt-gift-prompt-inner .gift-msg {{ font-size: calc(2.1 * var(--bt-f)); }}
      .bt-gift-prompt-inner .gift-hint {{ font-size: calc(1.5 * var(--bt-f)); }}
    }}
  </style>
</head>
<body>
  <div class="bt-root is-idle" id="btRoot" data-theme="cheremsha_neon" style="{root_style}">
    <div class="bt-badge" id="btBadge"></div>
    <div class="bt-card" id="btCard">
      <div class="bt-main">
        <div class="bt-stage">
          <div class="bt-side bt-side--left" id="btLeft">
            <div class="bt-combo bt-combo--left" id="btComboL"></div>
            <div class="bt-score bt-score--left" id="btScoreL">0</div>
            <div class="bt-name-wrap">
              <div class="bt-name bt-name--left" id="btNameL">&mdash;</div>
              <div class="bt-avatar bt-avatar--left" id="btAvatarL"><span class="av-fallback" id="btInitL">?</span></div>
            </div>
            <div class="bt-events" id="btFloatsL"></div>
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
      <div class="bt-comeback" id="btComeback">COMEBACK</div>
      <div class="bt-winner" id="btWinner"></div>
      <div class="bt-idle" id="btIdle"></div>
    </div>
    <script>
      (function() {{
        const root = document.getElementById('btRoot');
        const $ = (id) => document.getElementById(id);
        let state = null;
        let badgeTimer = null;
        let lastDelta = {{left: 0, right: 0}};

      const I18N = {{
        'uk': {{ idle: 'Чекаємо на двох дарувальників…', start: 'СТАРТ' }}},
        'en': {{ idle: 'Waiting for 2 gifters…', start: 'START' }}},
        'default': {{ idle: 'Waiting for 2 gifters…', start: 'START' }}}
      }}};
      const LOCALE = function() {{
        return I18N[(state && state.locale) || 'default'] || I18N['default'];
      }}};

      function fmt(s) {{
        s = Math.max(0, Math.floor(Number(s || 0)));
        return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
      }}}
      function esc(s) {{
        return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
      }}}
      function initials(name) {{
        const t = String(name || '?').trim();
        return (t[0] || '?').toUpperCase();
      }}}

      /* BattleGiftPrompt — dynamic gift/support CTA. Display-only: reads battle state, never changes it. */
      const GIFT_STATE = {{
        root: $('btGiftPrompt'),
        inner: $('btGiftInner'),
        msg: $('btGiftMsg'),
        hint: $('btGiftHint'),
        index: 0,
        timer: null,
        overlayTimer: null,
        overlayIdx: -1,
        overlayTimerId: null,
        overlayText: null,
        overlayHint: null,
        overlayTimerId: null,
        lastIndex: -1,
        active: true
      }}};
      const GIFT_MESSAGES = {{
        neutral: {{
          uk: 'Підтримаєш свою команду?', en: 'Support your side', def: 'Support your side'
        }}},
        final: {{ uk: 'Фінальний ривок — підтримаєш свою команду?', en: 'FINAL PUSH — support your side', def: 'FINAL PUSH — support your side' }}},
        close: {{ uk: 'Кожен дарунок може змінити результат', en: 'Every gift can change the lead', def: 'Every gift can change the lead' }}},
        comeback: {{ uk: 'Підтримаєш свою команду під час ривка', en: 'Help your team complete the comeback', def: 'Help your team complete the comeback' }}},
        combo: {{ uk: 'Підтримаєш свою команду — тримайте комбо', en: 'Keep the combo alive', def: 'Keep the combo alive' }}}
      }}};
      const GIFT_DEFAULT_POOL = [ {{ uk: 'Підтримаєш свою команду?', en: 'Support your side', def: 'Support your side' }}}, {{ uk: 'Підтримаєш команду з іншим дарунком', en: 'Send a gift to support your side', def: 'Send a gift to support your side' }}}, {{ uk: 'Підтримаєш команду, яка втрачає', en: 'Help your team take the lead', def: 'Help your team take the lead' }}}, {{ uk: 'Підтримаєш команду, яка втрачає', en: 'Send a gift and change the score', def: 'Send a gift and change the score' }}} ];
      const GIFT_EVENT_POOL = {{
        normal: [ {{ uk: 'Підтримаєш свою команду?', en: 'Support your side', def: 'Support your side' }}}, {{ uk: 'Підтримаєш команду з іншим дарунком', en: 'Send a gift to support your side', def: 'Send a gift to support your side' }}}, {{ uk: 'Підтримаєш команду, яка втрачає', en: 'Help your team take the lead', def: 'Help your team take the lead' }}}, {{ uk: 'Підтримаєш команду, яка втрачає', en: 'Send a gift and change the score', def: 'Send a gift and change the score' }}} ],
        big: [ {{ uk: 'Підтримаєш команду з іншим дарунком', en: 'Big gift! Support your side', def: 'Big gift! Support your side' }}}, {{ uk: 'Підтримаєш команду з іншим дарунком', en: 'Big gift! Support your side', def: 'Big gift! Support your side' }}}, {{ uk: 'Підтримаєш команду з іншим дарунком', en: 'Big gift! Support your side', def: 'Big gift! Support your side' }}} ]
      }}};
      function resolveText(t) {{
        if (!t) return GIFT_DEFAULT_POOL[0].def;
        const key = (state && state.locale) || 'default';
        const val = t[key];
        return val || t.en || t.def || 'Support your side';
      }}}
      function resolvePool(key) {{
        return GIFT_MESSAGES[key].def;
      }}}
      function setGift(text, hint) {{
        if (!GIFT_STATE.root) return;
        GIFT_STATE.msg.textContent = text;
        GIFT_STATE.hint.textContent = hint;
      }}}
      function cycleGiftMessages() {{
        if (!GIFT_STATE.root) return;
        if (!GIFT_STATE.active) return;
        const cfg = state && state.config;
        const flags = state && state.flags || {{}}};
        const combo = state && state.combo || {{}}};
        let text = '';
        let hint = '';
        if (flags.final_push) {{
          text = GIFT_MESSAGES.final.def;
          hint = '';
        }}} else if (flags.is_close) {{
          text = GIFT_MESSAGES.close.def;
          hint = '';
        }}} else if (flags.is_comeback) {{
          text = GIFT_MESSAGES.comeback.def;
          hint = '';
        }}} else if (combo.count > 0 && combo.multiplier > 1) {{
          text = GIFT_MESSAGES.combo.def;
          hint = '';
        }}} else {{
          const pool = GIFT_DEFAULT_POOL;
          const key = (state && state.locale) || 'default';
          const item = pool[GIFT_STATE.index % pool.length];
          text = item[key] || item.en || item.def || 'Support your side';
          const giftsEnabled = cfg && cfg.gifts_enabled !== false && cfg.gifts_enabled === true;
          hint = giftsEnabled ? '+ points' : '';
        }}}
        setGift(text, hint);
        GIFT_STATE.lastIndex = GIFT_STATE.index;
        GIFT_STATE.index += 1;
        GIFT_STATE.msg.classList.remove('bt-gift-fade');
        void GIFT_STATE.msg.offsetWidth;
        GIFT_STATE.msg.classList.add('bt-gift-fade');
      }}}
      function startGiftRotation() {{
        if (GIFT_STATE.timer) clearInterval(GIFT_STATE.timer);
        GIFT_STATE.timer = setInterval(cycleGiftMessages, 5500);
      }}}
      function flashGift(state, p) {{
        if (!GIFT_STATE.root) return;
        const pts = p.points ? p.points : (p.diamonds || '');
        const text = 'Big gift! +' + pts;
        const hint = '';
        const overlay = {{ msg: text, hint: hint }}};
        if (GIFT_STATE.overlayTimerId) clearTimeout(GIFT_STATE.overlayTimerId);
        GIFT_STATE.overlayText = text;
        GIFT_STATE.overlayHint = hint;
        GIFT_STATE.msg.textContent = overlay.msg;
        GIFT_STATE.hint.textContent = overlay.hint;
        GIFT_STATE.root.classList.remove('is-giftpulse');
        void GIFT_STATE.root.offsetWidth;
        GIFT_STATE.root.classList.add('is-giftpulse');
        GIFT_STATE.msg.classList.remove('bt-gift-fade');
        void GIFT_STATE.msg.offsetWidth;
        GIFT_STATE.msg.classList.add('bt-gift-fade');
        GIFT_STATE.overlayTimerId = setTimeout(function() {{
          if (GIFT_STATE.overlayIdx >= 0) {{
            cycleGiftMessages();
          }}} else if (GIFT_STATE.overlayText) {{
            GIFT_STATE.msg.textContent = GIFT_STATE.overlayText;
            GIFT_STATE.hint.textContent = GIFT_STATE.overlayHint || '';
          }}} else if (GIFT_STATE.msg) {{
            GIFT_STATE.msg.textContent = GIFT_STATE.overlayText || 'Support your side';
            GIFT_STATE.hint.textContent = GIFT_STATE.overlayHint || '';
          }}}
          GIFT_STATE.overlayText = null;
          GIFT_STATE.overlayHint = null;
          GIFT_STATE.root.classList.remove('is-giftpulse');
        }}}, 1400);
      }}}
      function updateGiftPrompt(promptState) {{
        if (!promptState.root) return;
        const cfg = state && state.config || {{}}};
        const giftsEnabled = cfg.gifts_enabled !== false && cfg.gifts_enabled === true;
        if (!giftsEnabled) {{
          GIFT_STATE.msg.textContent = 'Support your side';
          GIFT_STATE.hint.textContent = '';
          return;
        }}}
        cycleGiftMessages();
      }}}

      function setAvatar(side, p, showAv) {{
        const av = side === 'left' ? $('btAvatarL') : $('btAvatarR');
        const init = side === 'left' ? $('btInitL') : $('btInitR');
        const oldImg = av.querySelector('img');
        if (oldImg) oldImg.remove();
        init.style.display = 'flex';
        init.textContent = initials(p ? p.name : '?');
        if (showAv && p && p.avatar_url) {{
          const img = document.createElement('img');
          img.alt = '';
          img.onerror = function() {{ img.style.display = 'none'; init.style.display = 'flex'; }}};
          img.src = p.avatar_url;
          init.style.display = 'none';
          av.prepend(img);
        }}}
      }}}

      function showBadge(text) {{
        const b = $('btBadge');
        if (!text) {{ b.classList.remove('show'); return; }}}
        b.textContent = text;
        b.classList.add('show');
        if (badgeTimer) clearTimeout(badgeTimer);
        badgeTimer = setTimeout(() => b.classList.remove('show'), 1400);
      }}}

      function flashComeback() {{
        const c = $('btComeback');
        c.classList.remove('show');
        void c.offsetWidth;
        c.classList.add('show');
      }}

      function spawnFloat(side, text) {{
        const h = side === 'left' ? $('btFloatsL') : $('btFloatsR');
        if (!h) return;
        while (h.children.length > 5) h.removeChild(h.firstElementChild);
        const el = document.createElement('span');
        el.className = 'bt-float bt-float--' + side;
        el.textContent = text;
        el.style.left = (34 + Math.random() * 44) + '%';
        if (side === 'right') {{ el.style.left = (34 + Math.random() * 44) + '%'; el.style.right = 'auto'; }}}
        el.addEventListener('animationend', () => {{ if (el.parentNode === h) h.removeChild(el); }}});
        h.appendChild(el);
      }}}

      function processEvents() {{
        if (!state || !Array.isArray(state.events)) return;
        for (const e of state.events) {{
          if (!(e && e.type)) continue;
          const at = Number(e.at) || 0;
          if (at <= lastSeenAt + 0.0001) continue;
          lastSeenAt = Math.max(lastSeenAt, at);
          if (e.type === 'comeback') {{ flashComeback(); continue; }}
          if (e.type === 'gift_received' || e.type === 'big_gift') {{
            const p = e.payload || {{}};
            const pts = p.points ? p.points : (p.diamonds || '');
            spawnFloat(e.team_id, '+' + pts);
            flashGift(promptState, p);
          }}}
        }}}
      }}}

      function applyPatch(patch) {{
        if (!patch || typeof patch !== 'object') return;
        if (!state) state = {{}}};
        const keys = ['config','status','round','best_of','round_wins','duration_s','remaining_seconds','countdown_remaining_s','participants','teams','combo','flags','events','winner','locale','battle_id'];
        for (const k of keys) {{ if (patch[k] !== undefined) state[k] = patch[k]; }}}
      }}}

      function render() {{
        if (!state) return;
        const cfg = state.config || {{}}};
        document.body.style.setProperty('--bfont', (cfg.font_family || 'Segoe UI') + ', system-ui, sans-serif');
        root.dataset.theme = cfg.theme || 'cheremsha_neon';
        const status = state.status || 'idle';
        const flags = state.flags || {{}}};
        const combo = state.combo || {{}}};
        const isFinished = status === 'finished';
        root.classList.toggle('is-idle', status === 'idle');
        root.classList.toggle('is-countdown', status === 'countdown');
        root.classList.toggle('is-active', status === 'active');
        root.classList.toggle('is-finished', isFinished);
        root.classList.toggle('is-close', !!flags.is_close);
        root.classList.toggle('is-combo', !!(combo && combo.count > 0 && combo.multiplier > 1));
        root.classList.toggle('is-comeback', !!flags.is_comeback);
        root.classList.toggle('is-final', !!flags.final_push);
        root.classList.toggle('hide-idle', !!cfg.hide_when_idle);

        const parts = state.participants || [];
        const teams = state.teams || [];
        const L = parts.find((p) => p.team_id === 'left') || null;
        const R = parts.find((p) => p.team_id === 'right') || null;
        const tL = teams.find((t) => t.id === 'left') || {{score: 0, round_wins: 0}}};
        const tR = teams.find((t) => t.id === 'right') || {{score: 0, round_wins: 0}}};
        const showAv = cfg.show_avatars !== false;

        $('btLabel').textContent = cfg.battle_name || 'BATTLE';
        $('btNameL').textContent = L ? esc(L.name) : '';
        $('btNameR').textContent = R ? esc(R.name) : '';
        $('btScoreL').textContent = tL.score || 0;
        $('btScoreR').textContent = tR.score || 0;
        setAvatar('left', L, showAv);
        setAvatar('right', R, showAv);

        const ls = tL.score || 0, rs = tR.score || 0;
        const total = Math.max(1, ls + rs);
        $('btFillL').style.width = ((ls / total) * 100).toFixed(1) + '%';
        $('btFillR').style.width = ((rs / total) * 100).toFixed(1) + '%';
        root.classList.toggle('is-leader-left', ls > rs);
        root.classList.toggle('is-leader-right', rs > ls);
        root.classList.toggle('is-zero-bar', ls === 0 && rs === 0);
        const barTrack = document.getElementById('btBar');
        if (barTrack) {{
          barTrack.classList.toggle('is-zero', ls === 0 && rs === 0);
        }}}

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

      function handleMsg(obj) {{
        if (!obj || typeof obj !== 'object') return;
        if (obj.op === 'initial_state' && obj.state) {{
          state = {{}}};
          lastSeenAt = 0;
          applyPatch(obj.state);
          render();
        }}} else if (obj.op === 'patch' && obj.patch) {{
          applyPatch(obj.patch);
          render();
        }}}
      }}}

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
