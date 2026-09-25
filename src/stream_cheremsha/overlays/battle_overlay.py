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
      margin: 0; padding: 0;
      background: transparent;
      overflow: hidden;
      height: 100%; width: 100%;
    }}
    * {{ box-sizing: border-box; }}
    .bt-root {{
      position: absolute; inset: 0;
      pointer-events: none;
      font-family: var(--bfont, 'Segoe UI', system-ui, sans-serif);
      color: #f1f5f9;
      --bt-f: calc(var(--bt-u, 1) * 1.05vh);
      --lt-primary: #22d3ee; --lt-secondary: #3b82f6;
      --lt-glow: rgba(34, 211, 238, 0.55); --lt-soft: rgba(34, 211, 238, 0.12);
      --rt-primary: #f472b6; --rt-secondary: #a855f7;
      --rt-glow: rgba(244, 114, 182, 0.55); --rt-soft: rgba(244, 114, 182, 0.12);
      --center-primary: #a855f7; --center-glow: rgba(168, 85, 247, 0.6);
      --bg-1: #0B0A14; --bg-2: #16112A;
      --line: rgba(168, 85, 247, 0.35);
      --text: #f1f5f9; --dim: rgba(226, 232, 240, 0.75);
      --gold: #fde68a;
    }}
    .bt-root[data-theme="cyber"] {{
      --lt-primary: #38bdf8; --lt-secondary: #60a5fa;
      --lt-glow: rgba(56, 189, 248, 0.55); --lt-soft: rgba(56, 189, 248, 0.12);
      --rt-primary: #a855f7; --rt-secondary: #c084fc;
      --rt-glow: rgba(168, 85, 247, 0.55); --rt-soft: rgba(168, 85, 247, 0.12);
      --center-primary: #38bdf8; --center-glow: rgba(56, 189, 248, 0.6);
      --bg-1: #060E1C; --bg-2: #0B1629;
    }}
    .bt-root[data-theme="arcade"] {{
      --lt-primary: #fbbf24; --lt-secondary: #f97316;
      --lt-glow: rgba(251, 191, 36, 0.55); --lt-soft: rgba(251, 191, 36, 0.12);
      --rt-primary: #ef4444; --rt-secondary: #fb923c;
      --rt-glow: rgba(239, 68, 68, 0.55); --rt-soft: rgba(239, 68, 68, 0.12);
      --center-primary: #fbbf24; --center-glow: rgba(251, 191, 36, 0.6);
      --bg-1: #161008; --bg-2: #22150A;
      --line: rgba(251, 191, 36, 0.4);
    }}
    .bt-root[data-theme="minimal"] {{
      --lt-primary: #e2e8f0; --lt-secondary: #94a3b8;
      --lt-glow: rgba(226, 232, 240, 0.18); --lt-soft: rgba(226, 232, 240, 0.08);
      --rt-primary: #cbd5e1; --rt-secondary: #64748b;
      --rt-glow: rgba(203, 209, 225, 0.18); --rt-soft: rgba(203, 209, 225, 0.08);
      --center-primary: #e2e8f0; --center-glow: rgba(226, 232, 240, 0.18);
      --bg-1: #0A0C12; --bg-2: #11151E;
      --line: rgba(226, 232, 240, 0.18);
    }}
    .bt-card {{
      position: absolute; inset: 0;
      background: linear-gradient(135deg, var(--bg-1), var(--bg-2));
      border: 1px solid var(--line);
      border-radius: calc(min(24px, 3.5 * var(--bt-f)));
      overflow: hidden; display: flex; flex-direction: column;
      box-shadow:
        inset 0 1px 0 rgba(255,255,255,0.07),
        inset 0 0 calc(24 * var(--bt-f)) rgba(0,0,0,0.45),
        0 8px 30px rgba(0,0,0,0.5);
    }}
    .bt-card::before {{
      content:"";
      position:absolute; inset:0; pointer-events:none; z-index:0;
      background:
        radial-gradient(ellipse at 12% 50%, var(--lt-soft), transparent 58%),
        radial-gradient(ellipse at 88% 50%, var(--rt-soft), transparent 58%);
    }}
    .bt-main {{ position:relative; z-index:1; flex:1; min-height:0; display:flex; flex-direction:column; }}
    .bt-title-row {{
      display:flex; justify-content:space-between; align-items:center;
      padding: calc(2.5 * var(--bt-f)) calc(5 * var(--bt-f));
      border-bottom: 1px solid var(--line);
    }}
    .bt-title {{
      font-weight:900; font-size:calc(3.2 * var(--bt-f));
      letter-spacing:0.34em; text-transform:uppercase;
      color:var(--center-primary);
      text-shadow:0 2px 0 #000, 0 0 calc(8 * var(--bt-f)) var(--center-glow);
    }}
    .bt-round-label {{ font-weight:700; font-size:calc(1.8 * var(--bt-f)); letter-spacing:0.2em; color:var(--dim); }}
    .bt-stage {{
      position:relative; z-index:1;
      flex:1; min-height:0;
      display:grid; grid-template-columns:1fr auto 1fr;
      gap:calc(3 * var(--bt-f)); align-items:center;
      padding:calc(2 * var(--bt-f)) calc(5 * var(--bt-f));
    }}
    .bt-side {{
      position:relative;
      display:flex; flex-direction:column; justify-content:center;
      align-items:center; gap:calc(1.1 * var(--bt-f));
      min-width:0; min-height:0;
    }}
    .bt-side--left {{ align-items:flex-end; text-align:right; }}
    .bt-side--right {{ align-items:flex-start; text-align:left; }}
    .bt-avatar {{
      width:calc(15 * var(--bt-f)); height:calc(15 * var(--bt-f));
      border-radius:50%;
      border:calc(1.4 * var(--bt-f)) solid var(--line);
      overflow:hidden; position:relative;
      display:flex; align-items:center; justify-content:center;
      background:var(--bg-2);
      font-weight:900; font-size:calc(5.2 * var(--bt-f));
      flex:0 0 auto;
      box-shadow:0 0 calc(8 * var(--bt-f)) rgba(0,0,0,0.6);
      transition:transform 0.15s ease, box-shadow 0.15s ease;
    }}
    .bt-avatar--left {{
      border-color:var(--lt-primary);
      box-shadow:0 0 calc(8 * var(--bt-f)) rgba(0,0,0,0.6), 0 0 calc(12 * var(--bt-f)) var(--lt-glow);
    }}
    .bt-avatar--right {{
      border-color:var(--rt-primary);
      box-shadow:0 0 calc(8 * var(--bt-f)) rgba(0,0,0,0.6), 0 0 calc(12 * var(--bt-f)) var(--rt-glow);
    }}
    .bt-avatar img {{ width:100%; height:100%; object-fit:cover; display:block; }}
    .bt-avatar .av-fallback {{ display:flex; align-items:center; justify-content:center; color:var(--text); }}
    .bt-avatar.pulse {{ animation:btPulse 0.5s ease-out; }}
    @keyframes btPulse {{ 0% {{ transform:scale(1); }} 40% {{ transform:scale(1.16); }} 100% {{ transform:scale(1); }} }}
    .bt-participant-info {{ display:flex; flex-direction:column; align-items:center; gap:calc(0.8 * var(--bt-f)); min-width:calc(16 * var(--bt-f)); }}
    .bt-name {{
      font-weight:900; font-size:calc(5.5 * var(--bt-f)); line-height:1.05;
      letter-spacing:0.01em; white-space:nowrap; overflow:hidden;
      text-overflow:ellipsis;
      text-shadow:0 1px 0 #000, 0 2px 8px rgba(0,0,0,0.9);
    }}
    .bt-name--left  {{ color:var(--lt-primary); text-shadow:0 1px 0 #000, 0 0 calc(8 * var(--bt-f)) var(--lt-glow); }}
    .bt-name--right {{ color:var(--rt-primary); text-shadow:0 1px 0 #000, 0 0 calc(8 * var(--bt-f)) var(--rt-glow); }}
    .bt-score {{
      font-weight:900; font-size:calc(9 * var(--bt-f)); line-height:1.05;
      letter-spacing:0.02em; font-variant-numeric:tabular-nums;
      text-shadow:0 2px 0 #000, 0 2px 10px rgba(0,0,0,0.9);
    }}
    .bt-score--left  {{ color:var(--lt-primary); text-shadow:0 2px 0 #000, 0 0 calc(9 * var(--bt-f)) var(--lt-glow); }}
    .bt-score--right {{ color:var(--rt-primary); text-shadow:0 2px 0 #000, 0 0 calc(9 * var(--bt-f)) var(--rt-glow); }}
    .bt-combo {{
      font-weight:900; font-size:calc(2.2 * var(--bt-f));
      letter-spacing:0.08em;
      padding:calc(0.5 * var(--bt-f)) calc(1.8 * var(--bt-f));
      border-radius:999px;
      background:rgba(0,0,0,0.5); border:1px solid rgba(255,255,255,0.15);
      color:var(--gold);
      opacity:0; transition:opacity 0.25s ease, transform 0.25s ease;
      transform:scale(0.85); white-space:nowrap;
    }}
    .bt-combo.show {{ opacity:1; transform:scale(1); }}
    .bt-combo--left  {{ border-color:var(--lt-primary); color:var(--lt-primary); box-shadow:0 0 calc(6 * var(--bt-f)) var(--lt-glow); }}
    .bt-combo--right {{ border-color:var(--rt-primary); color:var(--rt-primary); box-shadow:0 0 calc(6 * var(--bt-f)) var(--rt-glow); }}
    .bt-center {{ display:flex; flex-direction:column; align-items:center; justify-content:center; gap:calc(1.5 * var(--bt-f)); min-width:calc(12 * var(--bt-f)); }}
    .bt-vs {{
      font-weight:900; font-size:calc(4.8 * var(--bt-f));
      letter-spacing:0.12em; color:#F8FAFC;
      text-shadow:0 2px 0 #000, 0 0 calc(9 * var(--bt-f)) var(--center-glow);
    }}
    .bt-timer {{
      font-weight:800; font-size:calc(5.8 * var(--bt-f));
      font-variant-numeric:tabular-nums;
      color:var(--text);
      display:flex; align-items:center; justify-content:center; gap:calc(0.9 * var(--bt-f));
      text-shadow:0 2px 0 #000, 0 2px 10px rgba(0,0,0,0.9);
      transition:color 0.3s ease;
    }}
    .bt-timer svg {{ width:calc(2.8 * var(--bt-f)); height:calc(2.8 * var(--bt-f)); stroke:currentColor; fill:none; stroke-width:2; }}
    .bt-round {{ font-weight:700; font-size:calc(2.3 * var(--bt-f)); letter-spacing:0.2em; color:var(--dim); }}
    .bt-dots {{ display:flex; gap:calc(0.9 * var(--bt-f)); justify-content:center; }}
    .bt-dots i {{
      width:calc(1.5 * var(--bt-f)); height:calc(1.5 * var(--bt-f));
      border-radius:50%; background:rgba(148,163,184,0.3);
      display:block; transition:background 0.3s ease, box-shadow 0.3s ease;
    }}
    .bt-dots i.won-left  {{ background:var(--lt-primary); box-shadow:0 0 calc(1.6 * var(--bt-f)) var(--lt-glow); }}
    .bt-dots i.won-right {{ background:var(--rt-primary); box-shadow:0 0 calc(1.6 * var(--bt-f)) var(--rt-glow); }}
    .bt-final-label {{ font-weight:900; font-size:calc(2.2 * var(--bt-f)); letter-spacing:0.3em; color:#FECACA; opacity:0; }}
    .is-final .bt-final-label {{ animation:btFinalPulse 1s ease-in-out infinite alternate; }}
    @keyframes btFinalPulse {{ 0% {{ opacity:0.3; transform:scale(0.98); }} 100% {{ opacity:0.95; transform:scale(1.02); }} }}
    .is-final .bt-timer {{ color:#FECACA; text-shadow:0 2px 0 #000, 0 0 calc(9 * var(--bt-f)) rgba(254,202,202,0.7); }}
    .is-final .bt-bar-track {{ box-shadow:0 0 calc(10 * var(--bt-f)) var(--lt-glow), 0 0 calc(10 * var(--bt-f)) var(--rt-glow); }}
    .is-final .fill-left, .is-final .fill-right {{ filter:brightness(1.15); }}
    .is-close .fill-left, .is-close .fill-right {{ filter:brightness(1.1); }}
    .bt-bar-wrap {{ padding:calc(1.5 * var(--bt-f)) calc(5 * var(--bt-f)); }}
    .bt-bar-track {{
      height:calc(2.6 * var(--bt-f)); border-radius:999px;
      background:rgba(255,255,255,0.06);
      border:1px solid rgba(255,255,255,0.06);
      overflow:hidden; display:flex; position:relative;
    }}
    .fill-left {{
      display:block; height:100%; width:50%;
      background:linear-gradient(90deg, var(--lt-primary), var(--lt-secondary), var(--center-primary));
      transition:width 0.35s ease, box-shadow 0.35s ease;
      position:relative; z-index:1;
    }}
    .fill-right {{
      display:block; height:100%; width:50%;
      background:linear-gradient(270deg, var(--rt-primary), var(--rt-secondary), var(--center-primary));
      transition:width 0.35s ease, box-shadow 0.35s ease;
      position:relative; z-index:1;
    }}
    .fill-left  {{ box-shadow:0 0 calc(6 * var(--bt-f)) var(--lt-glow); }}
    .fill-right {{ box-shadow:0 0 calc(6 * var(--bt-f)) var(--rt-glow); }}
    .bt-gift-prompt {{
      align-self:center; min-height:0; flex-shrink:0;
      justify-content:center; align-items:center;
      padding:calc(1.5 * var(--bt-f)) calc(4 * var(--bt-f));
      gap:calc(2 * var(--bt-f));
    }}
    .bt-gift-prompt-inner {{
      display:inline-flex; align-items:center; justify-content:center; gap:calc(1.4 * var(--bt-f));
      min-width:0; max-width:calc(640px); width:100%;
      padding:calc(1.1 * var(--bt-f)) calc(3.6 * var(--bt-f));
      border-radius:999px; border:1px solid rgba(168,85,247,0.38);
      background:rgba(0,0,0,0.42);
      backdrop-filter:blur(6px);
    }}
    .bt-gift-prompt-inner .gift-ico {{
      display:inline-grid; place-items:center; flex:0 0 auto;
      width:calc(2.6 * var(--bt-f)); height:calc(2.6 * var(--bt-f));
      border-radius:18%; overflow:hidden;
      background:rgba(168,85,247,0.16); border:1px solid rgba(168,85,247,0.5);
      box-shadow:0 0 calc(5 * var(--bt-f)) rgba(168,85,247,0.35);
    }}
    .bt-gift-prompt-inner .gift-ico svg {{
      width:100%; height:100%; stroke:currentColor; fill:none;
      stroke-width:2; stroke-linecap:round; stroke-linejoin:round;
    }}
    .bt-gift-prompt-inner .gift-msg {{
      font-weight:800; font-size:calc(2.5 * var(--bt-f));
      letter-spacing:0.04em; color:var(--center-primary);
      white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
      min-width:0; flex:1 1 auto;
      text-shadow:0 2px 8px rgba(0,0,0,0.6);
    }}
    .bt-gift-prompt-inner .gift-fx {{
      font-weight:900; font-size:calc(2.5 * var(--bt-f));
      color:var(--center-primary);
      text-shadow:0 0 calc(6 * var(--bt-f)) rgba(168,85,247,0.8), 0 2px 8px rgba(0,0,0,0.6);
    }}
    .is-giftpulse .bt-gift-prompt-inner {{
      border-color:var(--center-primary);
      box-shadow:0 0 calc(10 * var(--bt-f)) var(--center-primary), 0 0 calc(14 * var(--bt-f)) rgba(168,85,247,0.35);
    }}
    @keyframes btGiftPulse {{ 0% {{ transform:scale(1); opacity:0.95; }} 35% {{ transform:scale(1.06); opacity:1; }} 100% {{ transform:scale(1); opacity:0.95; }} }}
    .is-giftpulse .bt-gift-prompt-inner {{ animation:btGiftPulse 0.7s ease-out; }}
    @keyframes btGiftGlowPulse {{ 0% {{ opacity:0.85; }} 50% {{ opacity:1; }} 100% {{ opacity:0.85; }} }}
    .bt-gift-prompt-inner .gift-ico {{ opacity:0.85; animation:btGiftGlowPulse 3.2s ease-in-out infinite; }}
    @keyframes btGiftFade {{ from {{ opacity:0; transform:translateY(3px); }} to {{ opacity:1; transform:translateY(0); }} }}
    .bt-gift-fade {{ animation:btGiftFade 0.3s ease-out; }}
    .bt-badge {{
      position:absolute; top:0; left:50%;
      transform:translateX(-50%) translateY(calc(1.5 * var(--bt-f)));
      z-index:5;
      font-weight:900; letter-spacing:0.14em; font-size:calc(1.8 * var(--bt-f));
      background:rgba(0,0,0,0.72); border:1px solid var(--line); border-radius:999px;
      padding:calc(0.8 * var(--bt-f)) calc(1.8 * var(--bt-f));
      opacity:0; transition:opacity 0.25s ease;
      white-space:nowrap; text-shadow:0 1px 0 #000;
      pointer-events:none;
    }}
    .bt-badge.show {{ opacity:1; }}
    .bt-badge--comeback {{ border-color:var(--gold); color:var(--gold); box-shadow:0 0 calc(8 * var(--bt-f)) rgba(251,191,36,0.6); }}
    .bt-badge--combo {{ border-color:var(--lt-primary); color:var(--lt-primary); box-shadow:0 0 calc(8 * var(--bt-f)) var(--lt-glow); }}
    .bt-badge--final {{ border-color:#FECACA; color:#FECACA; box-shadow:0 0 calc(8 * var(--bt-f)) rgba(254,202,202,0.6); }}
    .bt-badge--biggift {{ border-color:var(--gold); color:var(--gold); }}
    .bt-winner {{
      position:absolute; inset:0; z-index:3;
      display:flex; flex-direction:column; align-items:center; justify-content:center; gap:calc(1.5 * var(--bt-f));
      background:rgba(0,0,0,0.75);
      border-radius:calc(min(24px, 3.5 * var(--bt-f)));
    }}
    .bt-winner-label {{ font-weight:900; font-size:calc(2 * var(--bt-f)); letter-spacing:0.34em; text-transform:uppercase; color:var(--dim); }}
    .bt-winner-name {{
      font-weight:900; font-size:calc(8 * var(--bt-f)); color:var(--gold);
      text-shadow:0 2px 0 #000, 0 0 calc(12 * var(--bt-f)) rgba(251,191,36,0.7);
      white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
    }}
    .bt-winner-score {{ font-weight:800; font-size:calc(3.2 * var(--bt-f)); color:var(--text); font-variant-numeric:tabular-nums; }}
    .bt-idle-msg {{ font-weight:600; font-size:calc(2.5 * var(--bt-f)); color:var(--dim); text-align:center; padding:calc(2 * var(--bt-f)); letter-spacing:0.05em; }}
    .bt-countdown {{ font-weight:900; font-size:calc(8 * var(--bt-f)); color:var(--gold); text-shadow:0 0 calc(12 * var(--bt-f)) rgba(251,191,36,0.7); text-align:center; }}
    .is-idle .bt-stage, .is-idle .bt-bar-wrap {{ opacity:0.25; transition:opacity 0.4s ease; }}
    .is-countdown .bt-stage, .is-countdown .bt-bar-wrap {{ opacity:0.25; transition:opacity 0.4s ease; }}
    .is-countdown .bt-countdown {{ display:block; }}
    .hide-idle.is-idle .bt-card {{ display:none; }}
    @media (max-width:1600px) {{
      .bt-avatar {{ width:calc(13 * var(--bt-f)); height:calc(13 * var(--bt-f)); }}
      .bt-score {{ font-size:calc(8 * var(--bt-f)); }}
      .bt-name {{ font-size:calc(4.8 * var(--bt-f)); }}
    }}
    @media (max-width:1280px) {{
      .bt-avatar {{ width:calc(12 * var(--bt-f)); height:calc(12 * var(--bt-f)); }}
      .bt-score {{ font-size:calc(7 * var(--bt-f)); }}
      .bt-name {{ font-size:calc(4.2 * var(--bt-f)); }}
      .bt-timer {{ font-size:calc(5 * var(--bt-f)); }}
      .bt-vs {{ font-size:calc(4 * var(--bt-f)); }}
    }}
    @media (max-width:1024px) {{
      .bt-avatar {{ width:calc(10 * var(--bt-f)); height:calc(10 * var(--bt-f)); }}
      .bt-score {{ font-size:calc(6 * var(--bt-f)); }}
      .bt-name {{ font-size:calc(3.5 * var(--bt-f)); }}
      .bt-timer {{ font-size:calc(4.2 * var(--bt-f)); }}
      .bt-vs {{ font-size:calc(3.4 * var(--bt-f)); }}
      .bt-title {{ font-size:calc(2.6 * var(--bt-f)); }}
      .bt-center {{ gap:calc(1 * var(--bt-f)); }}
    }}
    @media (max-width:700px) {{
      .bt-avatar {{ width:calc(9 * var(--bt-f)); height:calc(9 * var(--bt-f)); }}
      .bt-score {{ font-size:calc(5.2 * var(--bt-f)); }}
      .bt-name {{ font-size:calc(3 * var(--bt-f)); }}
      .bt-timer {{ font-size:calc(3.5 * var(--bt-f)); }}
      .bt-vs {{ font-size:calc(3 * var(--bt-f)); }}
      .bt-stage {{ gap:calc(2 * var(--bt-f)); padding:calc(1.5 * var(--bt-f)) calc(3 * var(--bt-f)); }}
      .bt-bar-wrap {{ padding:calc(1 * var(--bt-f)) calc(3 * var(--bt-f)); }}
    }}
  </style>
</head>
<body>
  <div class="bt-root is-idle" id="btRoot" data-theme="cheremsha_neon" style="{root_style}">
    <div class="bt-badge" id="btBadge"></div>
    <div class="bt-card" id="btCard">
      <div class="bt-title-row">
        <div class="bt-title" id="btTitle">BATTLE</div>
        <div class="bt-round-label" id="btTitleSub">ROUND 1 &#8226; BO3</div>
      </div>
      <div class="bt-main">
        <div class="bt-stage">
          <div class="bt-side bt-side--left" id="btLeft">
            <div class="bt-avatar bt-avatar--left" id="btAvatarL"><span class="av-fallback" id="btInitL">?</span></div>
            <div class="bt-participant-info">
              <div class="bt-name bt-name--left" id="btNameL"></div>
              <div class="bt-score bt-score--left" id="btScoreL">0</div>
              <div class="bt-combo" id="btComboL"></div>
            </div>
          </div>
          <div class="bt-center" id="btCenter">
            <div class="bt-vs">VS</div>
            <div class="bt-timer" id="btTimer">
              <svg viewBox="0 0 24 24"><circle cx="12" cy="13" r="8"/><path d="M12 9v4l2.5 2.5M9 2h6"/></svg>
              <span id="btTimerText">0:00</span>
            </div>
            <div class="bt-round" id="btRound">ROUND 1 &#8226; BO3</div>
            <div class="bt-dots" id="btDots"></div>
            <div class="bt-final-label" id="btFinalLabel"></div>
          </div>
          <div class="bt-side bt-side--right" id="btRight">
            <div class="bt-avatar bt-avatar--right" id="btAvatarR"><span class="av-fallback" id="btInitR">?</span></div>
            <div class="bt-participant-info">
              <div class="bt-name bt-name--right" id="btNameR"></div>
              <div class="bt-score bt-score--right" id="btScoreR">0</div>
              <div class="bt-combo" id="btComboR"></div>
            </div>
          </div>
        </div>
        <div class="bt-gift-prompt" id="btGiftPrompt" style="display:none">
          <div class="bt-gift-prompt-inner">
            <span class="gift-ico">
              <svg viewBox="0 0 24 24"><path d="M12 4l-7 7h14z" transform="scale(-1,1) translate(24 0)"/></svg>
            </span>
            <span class="gift-msg" id="btGiftMsg"></span>
            <span class="gift-fx" id="btGiftFx"></span>
          </div>
        </div>
        <div class="bt-bar-wrap">
          <div class="bt-bar-track">
            <i class="fill-left" id="btFillL" style="width:50%"></i>
            <i class="fill-right" id="btFillR" style="width:50%"></i>
          </div>
        </div>
        <div class="bt-idle-msg" id="btIdle"></div>
        <div class="bt-countdown" id="btCountdown" style="display:none"></div>
        <div class="bt-winner" id="btWinner" style="display:none">
          <div class="bt-winner-label">WINNER</div>
          <div class="bt-winner-name" id="btWinnerName"></div>
          <div class="bt-winner-score" id="btWinnerScore"></div>
        </div>
      </div>
    </div>
    <script>
      (function() {{
        const root = document.getElementById('btRoot');
        const $ = (id) => document.getElementById(id);
        const rootStyleU = parseFloat(getComputedStyle(root).getPropertyValue('--bt-u')) || 1;
        const currentColor = 'var(--lt-glow)';
        let state = null;
        let badgeTimer = null;
        let lastDelta = {{ left: 0, right: 0 }};
        let giftPulseTimer = null;
        const GIFT_MSGS = {{
          uk: {{ idle: 'Chekaemo na dvokh daruvalknykh\u2026', start: 'START', gift: 'Novy darunok!' }},
          en: {{ idle: 'Waiting for 2 gifters\u2026', start: 'START', gift: 'New gift!' }},
          default: {{ idle: 'Waiting for 2 gifters\u2026', start: 'START', gift: 'New gift!' }},
        }};
        const I18N = {{ uk: GIFT_MSGS.uk, en: GIFT_MSGS.en, default: GIFT_MSGS.default }};
        const LOCALE = function() {{ return I18N[(state && state.locale) || 'default'] || I18N['default']; }};
        function fmt(s) {{
          s = Math.max(0, parseInt(s || 0, 10));
          return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
        }}
        function initials(name) {{
          const t = String(name || '?').trim();
          return (t[0] || '?').toUpperCase();
        }}
        function esc(s) {{
          return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        }}
        function showBadge(text, cls) {{
          const b = $('btBadge');
          b.className = 'bt-badge';
          if (cls) b.classList.add('bt-badge--' + cls);
          if (!text) {{ b.classList.remove('show'); return; }}
          b.textContent = text;
          b.classList.add('show');
          if (badgeTimer) clearTimeout(badgeTimer);
          badgeTimer = setTimeout(() => b.classList.remove('show'), 2500);
        }}
        function flashGift(msg, fx) {{
          const prompt = $('btGiftPrompt');
          if (!prompt) return;
          prompt.style.display = 'block';
          const msgEl = $('btGiftMsg');
          const fxEl = $('btGiftFx');
          const locale = LOCALE();
          msgEl.textContent = msg || (locale.gift || 'New gift!');
          fxEl.textContent = fx || '';
          const inner = prompt.querySelector('.bt-gift-prompt-inner');
          if (inner) {{
            inner.classList.remove('bt-gift-fade');
            void inner.offsetWidth;
            inner.classList.add('bt-gift-fade');
          }}
          root.classList.remove('is-giftpulse');
          void root.offsetWidth;
          root.classList.add('is-giftpulse');
          if (giftPulseTimer) clearTimeout(giftPulseTimer);
          giftPulseTimer = setTimeout(() => root.classList.remove('is-giftpulse'), 700);
        }}
        function updateGiftPrompt() {{
          const prompt = $('btGiftPrompt');
          if (!prompt) return;
          const locale = LOCALE();
          if (!state || state.status === 'idle') {{
            prompt.style.display = 'block';
            const msgEl = $('btGiftMsg');
            if (msgEl) msgEl.textContent = locale.idle || 'Waiting for 2 gifters\u2026';
          }} else {{
            prompt.style.display = 'none';
          }}
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
          const status = state.status || 'idle';
          const flags = state.flags || {{}};
          const combo = state.combo || {{}};
          const isFinal = !!flags.final_push;
          root.classList.toggle('is-idle', status === 'idle');
          root.classList.toggle('is-countdown', status === 'countdown');
          root.classList.toggle('is-active', status === 'active');
          root.classList.toggle('is-finished', status === 'finished');
          root.classList.toggle('is-close', !!flags.is_close);
          root.classList.toggle('is-comeback', !!flags.is_comeback);
          root.classList.toggle('is-final', isFinal);
          root.classList.toggle('is-combo', !!combo.count && !!combo.multiplier > 1);
          root.classList.toggle('hide-idle', !!cfg.hide_when_idle);
          $('btTitle').textContent = cfg.battle_name || 'BATTLE';
          const roundLabel = 'ROUND ' + (state.round || 1) + ' \u00b7 BO' + (state.best_of || 3);
          $('btTitleSub').textContent = roundLabel;
          $('btRound').textContent = roundLabel;
          const parts = state.participants || [];
          const teams = state.teams || [];
          const L = parts.find((p) => p.team_id === 'left') || null;
          const R = parts.find((p) => p.team_id === 'right') || null;
          const tL = teams.find((t) => t.id === 'left') || {{ score: 0, round_wins: 0 }};
          const tR = teams.find((t) => t.id === 'right') || {{ score: 0, round_wins: 0 }};
          const showAv = cfg.show_avatars !== false;
          $('btNameL').textContent = L ? L.name : '';
          $('btNameR').textContent = R ? R.name : '';
          $('btScoreL').textContent = tL.score || 0;
          $('btScoreR').textContent = tR.score || 0;
          setAvatar('left', L, showAv);
          setAvatar('right', R, showAv);
          const total = Math.max(1, (tL.score || 0) + (tR.score || 0));
          $('btFillL').style.width = (((tL.score || 0) / total) * 100).toFixed(1) + '%';
          $('btFillR').style.width = (((tR.score || 0) / total) * 100).toFixed(1) + '%';
          if ((tL.score || 0) >= (tR.score || 0)) {{
            $('btFillL').style.boxShadow = '0 0 ' + (9 * rootStyleU) + 'px ' + currentColor;
            $('btFillR').style.boxShadow = 'none';
          }} else {{
            $('btFillR').style.boxShadow = '0 0 ' + (9 * rootStyleU) + 'px ' + currentColor;
            $('btFillL').style.boxShadow = 'none';
          }}
          let secs = state.remaining_seconds || 0;
          if (status === 'countdown') secs = state.countdown_remaining_s || 0;
          if (status === 'finished') secs = 0;
          const timerText = $('btTimerText');
          if (status === 'countdown') {{
            timerText.textContent = 'START ' + secs;
            const cd = $('btCountdown');
            cd.style.display = 'block';
            cd.textContent = secs <= 3 ? secs : '';
          }} else {{
            timerText.textContent = fmt(secs);
            $('btCountdown').style.display = 'none';
          }}
          const dots = $('btDots');
          dots.innerHTML = '';
          const wins = state.round_wins || {{ left: tL.round_wins || 0, right: tR.round_wins || 0 }};
          const need = Math.floor((state.best_of || 3) / 2) + 1;
          for (let i = 0; i < need; i++) {{
            const a = document.createElement('i');
            if ((wins.left || 0) > i) a.className = 'won-left';
            dots.appendChild(a);
            const b = document.createElement('i');
            if ((wins.right || 0) > i) b.className = 'won-right';
            dots.appendChild(b);
          }}
          const comboL = $('btComboL');
          const comboR = $('btComboR');
          if (combo.team_id === 'left' && combo.count > 0 && combo.multiplier > 1) {{
            comboL.textContent = 'COMBO x' + combo.multiplier.toFixed(1);
            comboL.className = 'bt-combo bt-combo--left show';
          }} else {{
            comboL.className = 'bt-combo';
          }}
          if (combo.team_id === 'right' && combo.count > 0 && combo.multiplier > 1) {{
            comboR.textContent = 'COMBO x' + combo.multiplier.toFixed(1);
            comboR.className = 'bt-combo bt-combo--right show';
          }} else {{
            comboR.className = 'bt-combo';
          }}
          $('btFinalLabel').textContent = isFinal ? 'FINAL PUSH' : '';
          const idleMsg = $('btIdle');
          const locale = LOCALE();
          if (status === 'idle') {{
            idleMsg.style.display = 'block';
            idleMsg.textContent = locale.idle || 'Waiting for 2 gifters\u2026';
          }} else {{
            idleMsg.style.display = 'none';
          }}
          updateGiftPrompt();
          const w = $('btWinner');
          if (status === 'finished' && cfg.show_winner_screen !== false && state.winner) {{
            w.style.display = 'flex';
            const nm = state.winner.name || state.winner.team_id || 'CHAMPION';
            $('btWinnerName').textContent = nm.toUpperCase().replace(/</g, '&lt;').replace(/>/g, '&gt;');
            $('btWinnerScore').textContent = (tL.score || 0) + ' vs ' + (tR.score || 0);
          }} else {{
            w.style.display = 'none';
          }}
          if (cfg.show_event_badges !== false) {{
            const evs = state.events || [];
            const last = evs.length ? evs[evs.length - 1] : null;
            if (combo && combo.count > 0 && combo.multiplier > 1) {{
              showBadge('COMBO x' + combo.multiplier.toFixed(1), 'combo');
            }} else if (last && last.type === 'comeback') {{
              showBadge('COMEBACK', 'comeback');
            }} else if (last && last.type === 'final_push') {{
              showBadge('FINAL PUSH', 'final');
            }} else if (last && last.type === 'big_gift') {{
              const pts = (last.payload && last.payload.diamonds) || '';
              showBadge('+' + pts, 'biggift');
            }}
          }}
          if ((tL.score || 0) !== lastDelta.left) {{
            lastDelta.left = tL.score || 0;
            const av = $('btAvatarL');
            av.classList.remove('pulse');
            void av.offsetWidth;
            av.classList.add('pulse');
          }}
          if ((tR.score || 0) !== lastDelta.right) {{
            lastDelta.right = tR.score || 0;
            const av = $('btAvatarR');
            av.classList.remove('pulse');
            void av.offsetWidth;
            av.classList.add('pulse');
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