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
      --bt-f: calc(var(--bt-u, 1) * var(--bt-font-k, 1) * 1.05vh);
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
    .bt-root[data-theme="halloween"] {{
      --lt-primary: #fb923c; --lt-secondary: #ea580c;
      --lt-glow: rgba(251, 146, 60, 0.6); --lt-soft: rgba(251, 146, 60, 0.14);
      --rt-primary: #c084fc; --rt-secondary: #7c3aed;
      --rt-glow: rgba(192, 132, 252, 0.6); --rt-soft: rgba(192, 132, 252, 0.14);
      --center-primary: #a3e635; --center-glow: rgba(163, 230, 53, 0.6);
      --bg-1: #120A1E; --bg-2: #251032;
      --line: rgba(251, 146, 60, 0.45);
    }}
    .bt-root[data-theme="halloween"] .bt-title {{
      color: var(--lt-primary);
      text-shadow: 0 0 calc(3 * var(--bt-f)) var(--lt-glow), 0 2px 0 #000;
      animation: btHalloweenFlicker 3.7s steps(12) infinite;
    }}
    .bt-root[data-theme="halloween"] .bt-avatar--left {{
      box-shadow: 0 0 calc(9 * var(--bt-f)) var(--lt-glow), 0 0 calc(18 * var(--bt-f)) var(--lt-soft);
    }}
    .bt-root[data-theme="halloween"] .bt-avatar--right {{
      box-shadow: 0 0 calc(9 * var(--bt-f)) var(--rt-glow), 0 0 calc(18 * var(--bt-f)) var(--rt-soft);
    }}
    @keyframes btHalloweenFlicker {{
      0%, 100% {{ opacity: 1; }}
      8% {{ opacity: 0.82; }}
      10% {{ opacity: 1; }}
      46% {{ opacity: 0.9; }}
      48% {{ opacity: 1; }}
      74% {{ opacity: 0.84; }}
      76% {{ opacity: 1; }}
    }}
    .bt-root[data-theme="anime"] {{
      --lt-primary: #67e8f9; --lt-secondary: #0ea5e9;
      --lt-glow: rgba(103, 232, 249, 0.6); --lt-soft: rgba(103, 232, 249, 0.14);
      --rt-primary: #f9a8d4; --rt-secondary: #ec4899;
      --rt-glow: rgba(249, 168, 212, 0.6); --rt-soft: rgba(249, 168, 212, 0.14);
      --center-primary: #c4b5fd; --center-glow: rgba(196, 181, 253, 0.65);
      --bg-1: #131022; --bg-2: #251c4e;
      --line: rgba(249, 168, 212, 0.45);
    }}
    .bt-root[data-theme="anime"] .bt-vs {{
      animation: btAnimeBreathe 2.6s ease-in-out infinite alternate;
    }}
    .bt-root[data-theme="anime"] .bt-badge.show {{
      box-shadow: 0 0 calc(10 * var(--bt-f)) var(--center-glow);
    }}
    @keyframes btAnimeBreathe {{
      0% {{ transform: scale(1); filter: brightness(1); }}
      100% {{ transform: scale(1.05); filter: brightness(1.2); }}
    }}
    .bt-root[data-theme="glitch"] {{
      --lt-primary: #00f0ff; --lt-secondary: #0891b2;
      --lt-glow: rgba(0, 240, 255, 0.6); --lt-soft: rgba(0, 240, 255, 0.14);
      --rt-primary: #ff2d78; --rt-secondary: #b5179e;
      --rt-glow: rgba(255, 45, 120, 0.6); --rt-soft: rgba(255, 45, 120, 0.14);
      --center-primary: #ffffff; --center-glow: rgba(255, 255, 255, 0.5);
      --bg-1: #050508; --bg-2: #0e0e16;
      --line: rgba(255, 45, 120, 0.45);
    }}
    .bt-root[data-theme="glitch"] .bt-vs {{
      text-shadow:
        calc(-0.6 * var(--bt-f)) 0 0 var(--lt-primary),
        calc(0.6 * var(--bt-f)) 0 0 var(--rt-primary);
      animation: btGlitchShift 0.9s steps(2) infinite;
    }}
    .bt-root[data-theme="glitch"] .bt-bar-track {{
      animation: btGlitchBar 1.7s steps(3) infinite;
    }}
    @keyframes btGlitchShift {{
      0% {{ transform: translate(0, 0) skewX(0deg); }}
      25% {{ transform: translate(calc(-0.5 * var(--bt-f)), 0) skewX(-4deg); }}
      50% {{ transform: translate(calc(0.5 * var(--bt-f)), 0) skewX(3deg); }}
      75% {{ transform: translate(0, 0) skewX(0deg); }}
    }}
    @keyframes btGlitchBar {{
      0%, 100% {{ opacity: 1; }}
      50% {{ opacity: 0.86; }}
    }}
    .bt-root[data-theme="fantasy"] {{
      --lt-primary: #fcd34d; --lt-secondary: #b45309;
      --lt-glow: rgba(252, 211, 77, 0.6); --lt-soft: rgba(252, 211, 77, 0.14);
      --rt-primary: #6ee7b7; --rt-secondary: #047857;
      --rt-glow: rgba(110, 231, 183, 0.55); --rt-soft: rgba(110, 231, 183, 0.14);
      --center-primary: #a78bfa; --center-glow: rgba(167, 139, 250, 0.65);
      --bg-1: #0a1410; --bg-2: #16281d;
      --line: rgba(252, 211, 77, 0.45);
      --gold: #ffe9a8;
    }}
    .bt-root[data-theme="fantasy"] .bt-title {{
      color: var(--gold);
      letter-spacing: 0.3em;
      animation: btFantasyShine 3s ease-in-out infinite alternate;
    }}
    .bt-root[data-theme="fantasy"] .bt-avatar {{
      box-shadow: 0 0 0 calc(1 * var(--bt-f)) var(--line), 0 0 calc(10 * var(--bt-f)) var(--center-glow);
    }}
    @keyframes btFantasyShine {{
      0% {{ text-shadow: 0 0 calc(4 * var(--bt-f)) var(--lt-glow), 0 2px 0 #000; }}
      100% {{ text-shadow: 0 0 calc(10 * var(--bt-f)) var(--lt-glow), 0 0 calc(18 * var(--bt-f)) var(--lt-soft), 0 2px 0 #000; }}
    }}
    .bt-root[data-theme="newyear"] {{
      --lt-primary: #7dd3fc; --lt-secondary: #0369a1;
      --lt-glow: rgba(125, 211, 252, 0.6); --lt-soft: rgba(125, 211, 252, 0.14);
      --rt-primary: #fde68a; --rt-secondary: #d97706;
      --rt-glow: rgba(253, 230, 138, 0.6); --rt-soft: rgba(253, 230, 138, 0.14);
      --center-primary: #f87171; --center-glow: rgba(248, 113, 113, 0.65);
      --bg-1: #071120; --bg-2: #10283f;
      --line: rgba(125, 211, 252, 0.45);
    }}
    .bt-root[data-theme="newyear"] .fill-left,
    .bt-root[data-theme="newyear"] .fill-right {{
      animation: btNewYearShimmer 2.4s ease-in-out infinite alternate;
    }}
    .bt-root[data-theme="newyear"] .bt-timer {{
      text-shadow: 0 0 calc(6 * var(--bt-f)) var(--lt-glow);
    }}
    @keyframes btNewYearShimmer {{
      0% {{ filter: brightness(0.95); }}
      100% {{ filter: brightness(1.3); }}
    }}
    .bt-root.anim-off .bt-vs,
    .bt-root.anim-off .bt-title,
    .bt-root.anim-off .fill-left,
    .bt-root.anim-off .fill-right,
    .bt-root.anim-off .bt-bar-track {{
      animation: none !important;
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
    .bt-main {{
      position:relative; z-index:1;
      flex:1 1 auto; min-height:0;
      display:flex; flex-direction:column;
      gap:calc(2.5 * var(--bt-f));
    }}
    .bt-title-row {{
      display:flex; justify-content:space-between; align-items:center;
      padding: calc(2.2 * var(--bt-f)) calc(5 * var(--bt-f));
      border-bottom: 1px solid var(--line);
    }}
    .bt-title {{
      font-weight:900; font-size:calc(3.2 * var(--bt-f));
      letter-spacing:0.34em; text-transform:uppercase;
      color:var(--center-primary);
      text-shadow:0 2px 0 #000, 0 0 calc(8 * var(--bt-f)) var(--center-glow);
    }}
    .bt-stage {{
      position:relative; z-index:1;
      flex:1; min-height:0;
      display:grid; grid-template-columns:1fr auto 1fr;
      gap:calc(3 * var(--bt-f)); align-items:center;
      padding:calc(1.5 * var(--bt-f)) calc(5 * var(--bt-f));
    }}
    .bt-side {{
      position:relative;
      display:flex; flex-direction:column; justify-content:center;
      align-items:center; gap:calc(1.6 * var(--bt-f));
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
    .bt-avatar--left::after, .bt-avatar--right::after {{
      content:""; position:absolute; inset:-calc(4 * var(--bt-f)) -calc(4 * var(--bt-f));
      border-radius:50%; z-index:-1; pointer-events:none;
      background:radial-gradient(closest-side, rgba(255,255,255,0.05), transparent 70%);
    }}
    .bt-avatar--left::after {{ background:radial-gradient(closest-side, var(--lt-soft), transparent 72%); opacity:0.9; }}
    .bt-avatar--right::after {{ background:radial-gradient(closest-side, var(--rt-soft), transparent 72%); opacity:0.9; }}
    .bt-avatar.pulse {{ animation:btPulse 0.5s ease-out; }}
    @keyframes btPulse {{ 0% {{ transform:scale(1); }} 40% {{ transform:scale(1.16); }} 100% {{ transform:scale(1); }} }}
    .bt-participant-info {{
      display:flex; flex-direction:column; align-items:center;
      gap:calc(0.9 * var(--bt-f)); min-width:calc(18 * var(--bt-f));
      min-height:0;
      justify-content:flex-end;
    }}
    .bt-side--left .bt-participant-info {{ align-items:flex-end; }}
    .bt-side--right .bt-participant-info {{ align-items:flex-start; }}
    .bt-score-label {{
      font-weight:700; font-size:calc(1.6 * var(--bt-f));
      letter-spacing:0.28em; text-transform:uppercase;
      color:var(--dim);
    }}
    .bt-score-label--left  {{ color:var(--lt-primary); opacity:0.85; }}
    .bt-score-label--right {{ color:var(--rt-primary); opacity:0.85; }}
    .bt-name {{
      font-weight:900; font-size:calc(4.3 * var(--bt-f)); line-height:1.05;
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
    .bt-center {{
      display:flex; flex-direction:column; align-items:center; justify-content:center;
      gap:calc(1.1 * var(--bt-f)); min-width:calc(12 * var(--bt-f));
      justify-content:center;
    }}
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
      width:calc(1.6 * var(--bt-f)); height:calc(1.6 * var(--bt-f));
      border-radius:50%; background:rgba(64,73,92,0.45);
      display:block; transition:background 0.3s ease, box-shadow 0.3s ease;
    }}
    .bt-dots i.active  {{ background:var(--lt-primary); box-shadow:0 0 calc(1.6 * var(--bt-f)) var(--lt-glow); }}
    .bt-dots i.won-left {{ background:rgba(34,211,238,0.55); box-shadow:none; }}
    .bt-dots i.won-right {{ background:rgba(244,114,182,0.55); box-shadow:none; }}
    .bt-final-label {{ font-weight:900; font-size:calc(2.2 * var(--bt-f)); letter-spacing:0.3em; color:#FECACA; opacity:0; }}
    .is-final .bt-final-label {{ animation:btFinalPulse 1s ease-in-out infinite alternate; }}
    @keyframes btFinalPulse {{ 0% {{ opacity:0.3; transform:scale(0.98); }} 100% {{ opacity:0.95; transform:scale(1.02); }} }}
    .is-final .bt-timer {{ color:#FECACA; text-shadow:0 2px 0 #000, 0 0 calc(9 * var(--bt-f)) rgba(254,202,202,0.7); }}
    .is-final .bt-bar-track {{ box-shadow:0 0 calc(10 * var(--bt-f)) var(--lt-glow), 0 0 calc(10 * var(--bt-f)) var(--rt-glow); }}
    .is-final .fill-left, .is-final .fill-right {{ filter:brightness(1.15); }}
    .is-close .fill-left, .is-close .fill-right {{ filter:brightness(1.1); }}
    .bt-bar-wrap {{
      flex:0 0 auto;
      padding:calc(0.8 * var(--bt-f)) calc(5 * var(--bt-f)) calc(0.8 * var(--bt-f));
    }}
    .bt-bar-track {{
      height:calc(2.6 * var(--bt-f)); border-radius:999px;
      background:rgba(255,255,255,0.06);
      border:1px solid rgba(255,255,255,0.06);
      overflow:hidden; display:flex; position:relative;
    }}
    .bt-bar-track::before {{
      content:""; position:absolute; left:50%; top:0; bottom:0; width:1px;
      transform:translateX(-50%);
      background:linear-gradient(90deg, transparent, rgba(255,255,255,0.25), transparent);
      pointer-events:none;
    }}
    .fill-left {{
      display:block; height:100%; width:0%;
      background:linear-gradient(90deg, var(--lt-primary), var(--lt-secondary), var(--center-primary));
      transition:width 0.45s cubic-bezier(0.25, 0.8, 0.25, 1), box-shadow 0.45s ease;
      position:relative; z-index:1;
    }}
    .fill-right {{
      display:block; height:100%; width:0%;
      background:linear-gradient(270deg, var(--rt-primary), var(--rt-secondary), var(--center-primary));
      transition:width 0.45s cubic-bezier(0.25, 0.8, 0.25, 1), box-shadow 0.45s ease;
      position:relative; z-index:1;
    }}
    .fill-left  {{ box-shadow:0 0 calc(6 * var(--bt-f)) var(--lt-glow); }}
    .fill-right {{ box-shadow:0 0 calc(6 * var(--bt-f)) var(--rt-glow); }}
    .bt-bar-track.is-empty {{ background:rgba(255,255,255,0.04); border-color:rgba(255,255,255,0.04); }}
    .is-idle .bt-bar-track, .is-countdown .bt-bar-track {{
      background:rgba(255,255,255,0.04); border-color:rgba(255,255,255,0.04);
      box-shadow:none;
    }}
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
    .bt-event-row {{
      flex:0 0 auto; align-self:stretch;
      display:flex; align-items:center; justify-content:center; gap:calc(2 * var(--bt-f));
      padding:calc(0.6 * var(--bt-f)) calc(5 * var(--bt-f));
      border-top:1px solid rgba(255,255,255,0.05);
      opacity:0;
      transition:opacity 0.3s ease;
      min-height:calc(3.5 * var(--bt-f));
      white-space:nowrap;
    }}
    .bt-event-row.show {{ opacity:0.9; }}
    .is-idle .bt-event-row, .is-countdown .bt-event-row, .is-finished .bt-event-row {{ display:none; }}
    .ev-item {{
      display:inline-flex; align-items:center; gap:calc(1.2 * var(--bt-f));
      min-width:0; font-weight:800;
      font-size:calc(2.1 * var(--bt-f)); letter-spacing:0.02em;
      text-shadow:0 1px 0 #000;
    }}
    .ev-item .ev-av {{
      width:calc(1.7 * var(--bt-f)); height:calc(1.7 * var(--bt-f));
      border-radius:50%; object-fit:cover; object-position:center;
      flex:0 0 auto; background:var(--bg-2); border:1px solid var(--line);
      opacity:0.85;
    }}
    .ev-item .ev-name {{
      min-width:0; overflow:hidden; text-overflow:ellipsis;
      white-space:nowrap;
    }}
    .ev-item .ev-val {{ font-variant-numeric:tabular-nums; font-weight:900; color:var(--gold); }}
    .ev-item--left  {{ color:var(--lt-primary); opacity:0.95; }}
    .ev-item--right {{ color:var(--rt-primary); opacity:0.95; }}
    .ev-sep {{
      font-weight:900; color:var(--dim); opacity:0.5;
      font-size:calc(1.8 * var(--bt-f));
    }}
    .is-countdown .bt-stage, .is-countdown .bt-bar-wrap {{ opacity:0.25; transition:opacity 0.4s ease; }}
    .is-countdown .bt-countdown {{ display:block; }}
    .hide-idle.is-idle .bt-card {{ display:none; }}
    @media (max-width:1600px) {{
      .bt-avatar {{ width:calc(13 * var(--bt-f)); height:calc(13 * var(--bt-f)); }}
      .bt-score {{ font-size:calc(8 * var(--bt-f)); }}
      .bt-name {{ font-size:calc(3.8 * var(--bt-f)); }}
    }}
    @media (max-width:1280px) {{
      .bt-avatar {{ width:calc(12 * var(--bt-f)); height:calc(12 * var(--bt-f)); }}
      .bt-score {{ font-size:calc(7 * var(--bt-f)); }}
      .bt-name {{ font-size:calc(3.3 * var(--bt-f)); }}
      .bt-timer {{ font-size:calc(5 * var(--bt-f)); }}
      .bt-vs {{ font-size:calc(4 * var(--bt-f)); }}
    }}
    @media (max-width:1024px) {{
      .bt-avatar {{ width:calc(10 * var(--bt-f)); height:calc(10 * var(--bt-f)); }}
      .bt-score {{ font-size:calc(6 * var(--bt-f)); }}
      .bt-name {{ font-size:calc(2.8 * var(--bt-f)); }}
      .bt-timer {{ font-size:calc(4.2 * var(--bt-f)); }}
      .bt-vs {{ font-size:calc(3.4 * var(--bt-f)); }}
      .bt-title {{ font-size:calc(2.6 * var(--bt-f)); }}
      .bt-center {{ gap:calc(1 * var(--bt-f)); }}
    }}
    /* ====== Casino moments: jackpot flash, round spin, draw badge, idle coin ====== */
    .bt-jackpot-flash {{
      position:absolute; inset:0;
      border-radius:inherit; z-index:4;
      pointer-events:none;
      background:
        radial-gradient(ellipse at 50% 55%, rgba(253,218,113,0.5), transparent 62%),
        radial-gradient(ellipse at 50% 50%, rgba(245,158,11,0.18), transparent 80%);
      display:none;
    }}
    .bt-jackpot-flash.show {{
      display:block;
      animation:btJackpotFlash 0.9s ease-out forwards;
    }}
    @keyframes btJackpotFlash {{
      0% {{ opacity:0; transform:scale(0.92); }}
      35% {{ opacity:1; }}
      100% {{ opacity:0; transform:scale(1.15); }}
    }}
    @keyframes btRoundSpin {{
      0% {{ box-shadow:inset 0 1px 0 rgba(255,255,255,0.07),
           inset 0 0 calc(24 * var(--bt-f)) rgba(0,0,0,0.45),
           0 8px 30px rgba(0,0,0,0.5); }}
      35% {{ box-shadow:inset 0 1px 0 rgba(255,255,255,0.07),
           inset 0 0 calc(24 * var(--bt-f)) rgba(0,0,0,0.45),
           0 8px 30px rgba(0,0,0,0.5),
           0 0 calc(14 * var(--bt-f)) rgba(253,218,113,0.5),
           0 0 calc(28 * var(--bt-f)) rgba(251,191,36,0.25); }}
      100% {{ box-shadow:inset 0 1px 0 rgba(255,255,255,0.07),
           inset 0 0 calc(24 * var(--bt-f)) rgba(0,0,0,0.45),
           0 8px 30px rgba(0,0,0,0.5); }}
    }}
    .bt-card.round-pulse {{ animation:btRoundSpin 0.7s ease-out; }}
    .bt-badge--draw, .bt-badge--jackpot {{
      border-color:var(--gold);
      color:var(--gold);
      box-shadow:0 0 calc(8 * var(--bt-f)) rgba(251,191,36,0.6);
    }}
    @keyframes btJackpotBadge {{
      0% {{ transform:translateX(-50%) translateY(calc(1.5 * var(--bt-f))) scale(0.55); opacity:0; }}
      60% {{ transform:translateX(-50%) translateY(calc(1.5 * var(--bt-f))) scale(1.08); opacity:1; }}
      100% {{ transform:translateX(-50%) translateY(calc(1.5 * var(--bt-f))) scale(1); opacity:1; }}
    }}
    .bt-badge--jackpot.show {{ animation:btJackpotBadge 0.7s ease-out; }}
    .bt-idle-coin {{
      display:inline-block;
      vertical-align:middle;
      margin-right:calc(0.9 * var(--bt-f));
      width:calc(2.2 * var(--bt-f));
      height:calc(2.2 * var(--bt-f));
      border-radius:50%;
      background:linear-gradient(135deg, #fde68a 0%, #eab308 55%, #b45309 100%);
      box-shadow:0 0 calc(4 * var(--bt-f)) rgba(251,191,36,0.55);
      animation:btIdleCoinSpin 5s linear infinite;
    }}
    @keyframes btIdleCoinSpin {{
      from {{ transform:rotate(0deg) translateY(0); }}
      to {{ transform:rotate(360deg) translateY(calc(-0.5 * var(--bt-f))); }}
    }}
    .ev-item {{
      display:inline-flex; align-items:center; gap:calc(1.2 * var(--bt-f));
      min-width:0;
      padding:calc(0.45 * var(--bt-f)) calc(1.3 * var(--bt-f));
      border-radius:999px;
      background:rgba(253,218,113,0.06);
      border:1px solid rgba(253,218,113,0.16);
    }}
    .ev-item--left  {{ border-color:rgba(34,211,238,0.28); }}
    .ev-item--right {{ border-color:rgba(244,114,182,0.28); }}
    .ev-val {{
      color:#fde68a;
      text-shadow:0 0 calc(3 * var(--bt-f)) rgba(251,191,36,0.7);
    }}
    /* ====== Event Reactions Layer ====== */
    .bt-root.anim-off .gift-projectile,
    .bt-root.anim-off .gift-impact,
    .bt-root.anim-off .bt-avatar.pulse-enhanced,
    .bt-root.anim-off .bt-score.pulse-enhanced,
    .bt-root.anim-off .bt-combo.pulse-enhanced,
    .bt-root.anim-off .bt-badge,
    .bt-root.anim-off .bt-round-badge,
    .bt-root.anim-off .bt-idle-coin,
    .bt-root.anim-off .bt-card.round-pulse {{
      animation: none !important;
      transition: none !important;
    }}
    .bt-root.anim-off .gift-projectile {{ display: none !important; }}
    .bt-root.anim-off .bt-jackpot-flash.show {{ display:none; }}
    .bt-root.anim-off .bt-score-float,
    .bt-root.anim-off .fill-left,
    .bt-root.anim-off .fill-right {{ animation: none !important; }}
    /* Floating +points near the score (one reused node per side) */
    .bt-participant-info {{ position:relative; }}
    .bt-score-float {{
      position:absolute; left:50%; top:calc(6.5 * var(--bt-f));
      transform:translateX(-50%);
      font-weight:900; font-size:calc(3.4 * var(--bt-f)); font-variant-numeric:tabular-nums;
      color:var(--gold); text-shadow:0 2px 0 #000, 0 0 calc(8 * var(--bt-f)) rgba(251,191,36,0.7);
      opacity:0; pointer-events:none; white-space:nowrap; z-index:2;
    }}
    .bt-score-float.show {{ animation:btScoreFloat 0.75s ease-out forwards; }}
    .bt-score-float.is-big {{
      font-size:calc(4.4 * var(--bt-f));
      text-shadow:0 2px 0 #000, 0 0 calc(12 * var(--bt-f)) rgba(251,191,36,0.9);
    }}
    @keyframes btScoreFloat {{
      0% {{ opacity:0; transform:translateX(-50%) translateY(8px) scale(0.85); }}
      18% {{ opacity:1; transform:translateX(-50%) translateY(0) scale(1.06); }}
      100% {{ opacity:0; transform:translateX(-50%) translateY(calc(-7 * var(--bt-f))) scale(1); }}
    }}
    /* HIGH intensity projectile tier (between default and big) */
    .gift-projectile.is-high {{
      width: calc(5 * var(--bt-f)); height: calc(5 * var(--bt-f));
      filter: drop-shadow(0 0 calc(4 * var(--bt-f)) var(--proj-glow)) brightness(1.08);
    }}
    /* Receiving-side fill flash (only the scoring side glows) */
    .fill-left, .fill-right {{ transition:width 0.45s cubic-bezier(0.25, 0.8, 0.25, 1), box-shadow 0.45s ease, filter 0.45s ease; }}
    .fill-left.is-hit {{ filter:brightness(1.6); }}
    .fill-right.is-hit {{ filter:brightness(1.6); }}
    /* Winner / loser states on finish */
    .bt-side.is-loser {{ opacity:0.55; filter:saturate(0.7); transition:opacity 0.6s ease, filter 0.6s ease; }}
    .bt-side.is-winner .bt-avatar {{
      box-shadow:0 0 calc(14 * var(--bt-f)) var(--winner-glow, var(--lt-glow)), 0 0 calc(26 * var(--bt-f)) var(--winner-glow, var(--lt-glow));
    }}
    .bt-side--left.is-winner .bt-avatar {{ --winner-glow: var(--lt-glow); }}
    .bt-side--right.is-winner .bt-avatar {{ --winner-glow: var(--rt-glow); }}
    .is-final #btTimerText {{ animation:btFinalPulse 1s ease-in-out infinite alternate; }}
    .bt-projectile-layer {{
      position:absolute; inset:0; pointer-events:none; z-index:2; overflow:hidden;
    }}
    .gift-impact-layer {{
      position:absolute; inset:0; pointer-events:none; z-index:3; overflow:hidden;
    }}
    .gift-projectile {{
      position:absolute; width: calc(4 * var(--bt-f)); height: calc(4 * var(--bt-f));
      border-radius: 50%; display:flex; align-items:center; justify-content:center;
      opacity:0; pointer-events:none; z-index:2;
      filter: drop-shadow(0 0 calc(3 * var(--bt-f)) var(--proj-glow));
    }}
    .gift-projectile .gift-svg {{
      width:100%; height:100%; object-fit:cover; display:block;
    }}
    .gift-projectile .gift-fallback-svg {{
      width:100%; height:100%;
    }}
    .gift-projectile.is-big {{ width: calc(6 * var(--bt-f)); height: calc(6 * var(--bt-f)); }}
    .gift-projectile.is-epic {{
      width: calc(8 * var(--bt-f)); height: calc(8 * var(--bt-f));
      filter: drop-shadow(0 0 calc(5 * var(--bt-f)) var(--proj-glow)) brightness(1.15);
    }}
    .gift-impact {{
      position:absolute; width: calc(6 * var(--bt-f)); height: calc(6 * var(--bt-f));
      border-radius:50%; pointer-events:none; z-index:3;
      border: calc(2 * var(--bt-f)) solid var(--proj-accent);
      box-shadow: 0 0 calc(6 * var(--bt-f)) var(--proj-accent);
      opacity:0; transform: scale(0.3);
      animation: btImpactRing 0.5s ease-out forwards;
    }}
    .gift-impact.is-epic {{
      border-width: calc(2.5 * var(--bt-f));
      box-shadow: 0 0 calc(10 * var(--bt-f)) var(--proj-accent);
      animation: btImpactRingEpic 0.6s ease-out forwards;
    }}
    .gift-impact .spark {{
      position:absolute; width: calc(0.8 * var(--bt-f)); height: calc(0.8 * var(--bt-f));
      border-radius:50%; background: var(--proj-accent);
      animation: btSpark 0.45s ease-out forwards;
    }}
    @keyframes btImpactRing {{
      0% {{ transform: scale(0.3); opacity: 1; }}
      100% {{ transform: scale(2.2); opacity: 0; }}
    }}
    @keyframes btImpactRingEpic {{
      0% {{ transform: scale(0.3); opacity: 1; }}
      50% {{ transform: scale(1.8); opacity: 0.8; }}
      100% {{ transform: scale(2.5); opacity: 0; }}
    }}
    @keyframes btSpark {{
      0% {{ transform: scale(1) translate(0, 0); opacity: 1; }}
      100% {{ transform: scale(0.2) translate(var(--sx), var(--sy)); opacity: 0; }}
    }}
    .bt-avatar.pulse-enhanced {{
      animation: btAvatarImpact 0.45s ease-in-out;
    }}
    @keyframes btAvatarImpact {{
      0% {{ transform: scale(1); box-shadow: 0 0 calc(9 * var(--bt-f)) var(--avatar-glow); }}
      30% {{ transform: scale(1.12); box-shadow: 0 0 calc(14 * var(--bt-f)) var(--avatar-glow); }}
      55% {{ transform: scale(0.97); box-shadow: 0 0 calc(9 * var(--bt-f)) var(--avatar-glow); }}
      80% {{ transform: scale(1.04); box-shadow: 0 0 calc(12 * var(--bt-f)) var(--avatar-glow); }}
      100% {{ transform: scale(1); box-shadow: 0 0 calc(9 * var(--bt-f)) var(--avatar-glow); }}
    }}
    .bt-avatar--left.pulse-enhanced {{ --avatar-glow: var(--lt-glow); --proj-accent: var(--lt-primary); }}
    .bt-avatar--right.pulse-enhanced {{ --avatar-glow: var(--rt-glow); --proj-accent: var(--rt-primary); }}
    .bt-score.pulse-enhanced {{
      animation: btScorePulse 0.5s ease-out;
    }}
    @keyframes btScorePulse {{
      0% {{ transform: scale(1); filter: brightness(1); }}
      40% {{ transform: scale(1.08); filter: brightness(1.25); }}
      100% {{ transform: scale(1); filter: brightness(1); }}
    }}
    .bt-side.is-side-flash {{
      animation: btSideFlash 0.5s ease-out;
    }}
    @keyframes btSideFlash {{
      0% {{ background: transparent; }}
      30% {{ background: radial-gradient(ellipse at 50% 50%, var(--side-flash-glow) 30%, transparent 70%); }}
      100% {{ background: transparent; }}
    }}
    .bt-side--left.is-side-flash {{ --side-flash-glow: var(--lt-soft); }}
    .bt-side--right.is-side-flash {{ --side-flash-glow: var(--rt-soft); }}
    .bt-combo.pulse-enhanced {{
      animation: btComboPulse 0.35s ease-out;
    }}
    @keyframes btComboPulse {{
      0% {{ transform: translateY(0) scale(1); }}
      50% {{ transform: translateY(0) scale(1.15); }}
      100% {{ transform: translateY(0) scale(1); }}
    }}
    .bt-badge.bt-lead-change {{
      border-color: var(--center-primary);
      background: rgba(168,85,247,.35);
      color: #fff;
      animation: btLeadFlash 1.2s ease-out forwards;
    }}
    @keyframes btLeadFlash {{
      0% {{ transform: translateX(-50%) scale(0.8); opacity: 0; }}
      15% {{ transform: translateX(-50%) scale(1.05); opacity: 1; }}
      70% {{ transform: translateX(-50%) scale(1.05); opacity: 1; }}
      100% {{ transform: translateX(-50%) scale(0.9); opacity: 0; }}
    }}
    .bt-badge.bt-round-badge {{
      font-size: calc(2.0 * var(--bt-f));
      letter-spacing: .2em;
      animation: btRoundBadge 0.9s ease-out forwards;
    }}
    @keyframes btRoundBadge {{
      0% {{ transform: translateX(-50%) scale(0.7); opacity: 0; }}
      20% {{ transform: translateX(-50%) scale(1.05); opacity: 1; }}
      70% {{ transform: translateX(-50%) scale(1.05); opacity: 1; }}
      100% {{ transform: translateX(-50%) scale(0.95); opacity: 0; }}
    }}
    .is-close .bt-bar-track {{
      box-shadow: 0 0 calc(6 * var(--bt-f)) var(--lt-glow), 0 0 calc(6 * var(--bt-f)) var(--rt-glow);
    }}
    .is-final .fill-left, .is-final .fill-right {{
      filter: brightness(1.25);
      box-shadow: 0 0 calc(4 * var(--bt-f)) currentColor;
    }}
    .bt-winner.winner-pulse {{ animation: btWinnerPulse 2s ease-in-out infinite alternate; }}
    .bt-winner-avatar {{ animation: btWinnerPulse 2s ease-in-out infinite alternate; }}
    @keyframes btWinnerPulse {{
      0% {{ box-shadow: 0 0 calc(8 * var(--bt-f)) var(--winner-glow, var(--lt-glow)); }}
      100% {{ box-shadow: 0 0 calc(16 * var(--bt-f)) var(--winner-glow, var(--lt-glow)); }}
    }}
    @media (max-width:700px) {{
      .bt-avatar {{ width:calc(9 * var(--bt-f)); height:calc(9 * var(--bt-f)); }}
      .bt-score {{ font-size:calc(5.2 * var(--bt-f)); }}
      .bt-name {{ font-size:calc(2.4 * var(--bt-f)); }}
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
      </div>
      <div class="bt-main">
        <div class="bt-stage">
          <div class="bt-side bt-side--left" id="btLeft">
            <div class="bt-avatar bt-avatar--left" id="btAvatarL"><span class="av-fallback" id="btInitL">?</span></div>
            <div class="bt-participant-info">
              <div class="bt-name bt-name--left" id="btNameL"></div>
              <div class="bt-score-label bt-score-label--left">РАХУНОК</div>
              <div class="bt-score bt-score--left" id="btScoreL">0</div>
              <div class="bt-score-float" id="btFloatL"></div>
              <div class="bt-combo" id="btComboL"></div>
            </div>
          </div>
          <div class="bt-center" id="btCenter">
            <div class="bt-vs">VS</div>
            <div class="bt-timer" id="btTimer">
              <svg viewBox="0 0 24 24"><circle cx="12" cy="13" r="8"/><path d="M12 9v4l2.5 2.5M9 2h6"/></svg>
              <span id="btTimerText">0:00</span>
            </div>
            <div class="bt-round" id="btRound">РАУНД 1 &#8226; BO3</div>
            <div class="bt-dots" id="btDots"></div>
            <div class="bt-final-label" id="btFinalLabel"></div>
          </div>
          <div class="bt-side bt-side--right" id="btRight">
            <div class="bt-avatar bt-avatar--right" id="btAvatarR"><span class="av-fallback" id="btInitR">?</span></div>
            <div class="bt-participant-info">
              <div class="bt-name bt-name--right" id="btNameR"></div>
              <div class="bt-score-label bt-score-label--right">РАХУНОК</div>
              <div class="bt-score bt-score--right" id="btScoreR">0</div>
              <div class="bt-score-float" id="btFloatR"></div>
              <div class="bt-combo" id="btComboR"></div>
            </div>
          </div>
        </div>
        <div class="bt-event-row" id="btEventRow" style="display:none"></div>
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
          <div class="bt-bar-track" id="btBarTrack">
            <i class="fill-left" id="btFillL" style="width:50%"></i>
            <i class="fill-right" id="btFillR" style="width:50%"></i>
          </div>
        </div>
        <div class="bt-idle-msg" id="btIdle"></div>
        <div class="bt-countdown" id="btCountdown" style="display:none"></div>
        <div class="bt-winner" id="btWinner" style="display:none">
          <div class="bt-winner-label" id="btWinnerLabel">ПЕРЕМОЖЕЦЬ</div>
          <div class="bt-winner-name" id="btWinnerName"></div>
          <div class="bt-winner-score" id="btWinnerScore"></div>
        </div>
      </div>
      <div class="bt-projectile-layer" id="btProjectileLayer"></div>
      <div class="gift-impact-layer" id="btImpactLayer"></div>
      <div class="bt-jackpot-flash" id="btJackpotFlash"></div>
      <div class="bt-badge bt-lead-change" id="btLeadBadge" style="display:none"></div>
      <div class="bt-badge bt-round-badge" id="btRoundBadge" style="display:none"></div>
    </div>
    <script>
      (function() {{
        const root = document.getElementById('btRoot');
        const $ = (id) => document.getElementById(id);
        let rootStyleU = parseFloat(getComputedStyle(root).getPropertyValue('--bt-u')) || 1;
        const currentColor = 'var(--lt-glow)';
        let state = null;
        let badgeTimer = null;
        let lastDelta = {{ left: 0, right: 0 }};
        let giftPulseTimer = null;
        let lastSeenAt = 0;
        /* ====== BattleVisualController — bounded event reaction system ====== */
        const MAX_PROJECTILES = 8;
        const BVC = {{
          projectilePool: [],
          impactPool: [],
          currentLeader: null,
          ctaSuppressionTimer: null,
          ctaRotateTimer: null,
          ctaIndex: 0,
          scoreAnimTimerL: null,
          scoreAnimTimerR: null,
          lastRound: null,
          lastRoundWins: null,
          leadFlashTimer: null,
          roundFlashTimer: null,
          roundPulseTimer: null,
          suppressCTA(durationMs) {{
            const prompt = $('btGiftPrompt');
            if (!prompt) return;
            if (BVC.ctaRotateTimer) {{ clearTimeout(BVC.ctaRotateTimer); BVC.ctaRotateTimer = null; }}
            prompt.style.display = 'none';
            if (BVC.ctaSuppressionTimer) clearTimeout(BVC.ctaSuppressionTimer);
            BVC.ctaSuppressionTimer = setTimeout(() => {{
              BVC.ctaSuppressionTimer = null;
              updateGiftPrompt();
            }}, durationMs);
          }},
          holdCTA(durationMs) {{
            if (BVC.ctaRotateTimer) {{ clearTimeout(BVC.ctaRotateTimer); BVC.ctaRotateTimer = null; }}
            if (BVC.ctaSuppressionTimer) clearTimeout(BVC.ctaSuppressionTimer);
            BVC.ctaSuppressionTimer = setTimeout(() => {{
              BVC.ctaSuppressionTimer = null;
              updateGiftPrompt();
            }}, durationMs);
          }},
          reset() {{
            const layer = $('btProjectileLayer');
            if (layer) layer.innerHTML = '';
            const impactLayer = $('btImpactLayer');
            if (impactLayer) impactLayer.innerHTML = '';
            BVC.projectilePool.length = 0;
            BVC.impactPool.length = 0;
            if (BVC.leadFlashTimer) {{ clearTimeout(BVC.leadFlashTimer); BVC.leadFlashTimer = null; }}
            if (BVC.roundFlashTimer) {{ clearTimeout(BVC.roundFlashTimer); BVC.roundFlashTimer = null; }}
            if (BVC.roundPulseTimer) {{ clearTimeout(BVC.roundPulseTimer); BVC.roundPulseTimer = null; }}
            if (BVC.ctaSuppressionTimer) {{ clearTimeout(BVC.ctaSuppressionTimer); BVC.ctaSuppressionTimer = null; }}
            if (BVC.ctaRotateTimer) {{ clearTimeout(BVC.ctaRotateTimer); BVC.ctaRotateTimer = null; }}
            if (BVC.scoreAnimTimerL) {{ clearInterval(BVC.scoreAnimTimerL); BVC.scoreAnimTimerL = null; }}
            if (BVC.scoreAnimTimerR) {{ clearInterval(BVC.scoreAnimTimerR); BVC.scoreAnimTimerR = null; }}
          }},
          getIntensity(diamonds, multiplier) {{
            const dm = Number(diamonds || 0);
            const mult = Number(multiplier || 1) || 1;
            const effective = dm * mult;
            if (effective >= 200) return 'epic';
            if (effective >= 50) return 'big';
            if (effective >= 20) return 'high';
            if (effective >= 5) return 'medium';
            return 'low';
          }},
          getSideAccent(side) {{
            return side === 'left' ? 'var(--lt-primary)' : 'var(--rt-primary)';
          }},
          getSideGlow(side) {{
            return side === 'left' ? 'var(--lt-glow)' : 'var(--rt-glow)';
          }}
        }};
        let bvcInitialized = false;
        function initBVC() {{
          if (bvcInitialized) return;
          bvcInitialized = true;
          const root = $('btRoot');
          const cfg = state && state.config;
          if (cfg && cfg.event_animations === false) {{
            root.classList.add('anim-off');
          }}
          if (root) {{
            const intensity = cfg && cfg.animation_intensity_pct ? Number(cfg.animation_intensity_pct) : 100;
            root.style.setProperty('--proj-speed', (100 / intensity * 100).toFixed(1) + '%');
          }}
        }}
        const STR = {{
          uk: {{
            idle: 'Чекаємо на двох дарувальників…',
            start: 'СТАРТ',
            gift: 'Новий подарунок!',
            bigGift: 'ВЕЛИКИЙ ПОДАРУНОК!',
            round: 'РАУНД',
            combo: 'КОМБО',
            comeback: 'КАМБЕК',
            finalPush: 'ФІНАЛЬНИЙ РИВОК',
            leftLead: 'ВЕДУТЬ ЛІВІ',
            rightLead: 'ВЕДУТЬ ПРАВІ',
            winner: 'ПЕРЕМОЖЕЦЬ',
            score: 'РАХУНОК',
            draw: 'НІКТО НЕ ВІГРАВ',
            jackpot: 'ДЖЕКПОТ!',
            finalPushCta: 'ФІНАЛЬНИЙ РИВОК — ПІДТРИМАЙ СВОЇХ',
            cta: [
              'Підтримай свою сторону',
              'Надішли подарунок',
              'Допоможи команді вирватися вперед',
              'Кожен подарунок змінює битву',
              'Тримай темп',
              'Веди команду до перемоги',
              'Зроби камбек можливим',
            ],
            ctaScore: [
              'Надішли подарунок — підніми рахунок',
              'Кожен подарунок — це бали',
              'Веди команду до перемоги',
              'Зроби камбек можливим',
            ],
          }},
          en: {{
            idle: 'Waiting for 2 gifters…',
            start: 'START',
            gift: 'New gift!',
            bigGift: 'BIG GIFT!',
            round: 'ROUND',
            combo: 'COMBO',
            comeback: 'COMEBACK',
            finalPush: 'FINAL PUSH',
            leftLead: 'LEFT LEAD',
            rightLead: 'RIGHT LEAD',
            winner: 'WINNER',
            score: 'SCORE',
            draw: 'DRAW — NO WINNER',
            jackpot: 'JACKPOT!',
            finalPushCta: 'FINAL PUSH — SUPPORT YOUR SIDE',
            cta: [
              'Support your side',
              'Send a gift',
              'Help your team take the lead',
              'Every gift can change the battle',
              'Keep the momentum going',
              'Push your team to victory',
              'Make the comeback happen',
            ],
            ctaScore: [
              'Send a gift to boost your score',
              'Every gift scores points',
              'Push your team to victory',
              'Make the comeback happen',
            ],
          }},
        }};
        const LOCALE = function() {{
          const cfg = state && state.config;
          const loc = String((cfg && cfg.ui_locale) || (state && state.locale) || 'uk');
          return loc === 'en' ? STR.en : STR.uk;
        }};
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
        /* ====== Projectile Functions ====== */
        function spawnProjectile(side, payload, intensity) {{
          if (BVC.projectilePool.length >= MAX_PROJECTILES) return;
          const layer = $('btProjectileLayer');
          if (!layer) return;
          const avatar = side === 'left' ? $('btAvatarL') : $('btAvatarR');
          if (!avatar) return;
          const avRect = avatar.getBoundingClientRect();
          const card = $('btCard');
          if (!card) return;
          const cardRect = card.getBoundingClientRect();
          if (!cardRect.width || !cardRect.height) return;
          const cardW = cardRect.width;
          const cardH = cardRect.height;
          const sx = side === 'left' ? cardRect.left + cardW * 0.05 : cardRect.left + cardW * 0.95;
          const sy = cardRect.top + cardRect.height * 0.45;
          const tx = avRect.left - cardRect.left + avRect.width / 2;
          const ty = avRect.top - cardRect.top + avRect.height / 2;
          const midX = (sx + tx) / 2;
          const midY = Math.min(sy, ty) - cardH * 0.15;
          const relSx = sx - cardRect.left;
          const relSy = sy - cardRect.top;
          const relTx = tx;
          const relTy = ty;
          const relMidX = midX - cardRect.left;
          const relMidY = midY - cardRect.top;
          const pathD = 'M ' + relSx + ' ' + relSy +
                        ' Q ' + relMidX + ' ' + relMidY +
                        ' ' + relTx + ' ' + relTy;
          const el = document.createElement('div');
          el.className = 'gift-projectile';
          if (intensity === 'high') el.classList.add('is-high');
          if (intensity === 'big') el.classList.add('is-big');
          if (intensity === 'epic') el.classList.add('is-epic');
          el.style.left = relSx + 'px';
          el.style.top = relSy + 'px';
          el.style.setProperty('--proj-glow', BVC.getSideGlow(side));
          el.style.setProperty('--proj-accent', BVC.getSideAccent(side));
          const participant = side === 'left'
            ? (state && state.participants && state.participants.find(p => p.team_id === 'left'))
            : (state && state.participants && state.participants.find(p => p.team_id === 'right'));
          const giftImg = payload && (payload.gift_image || payload.image_url || payload.giftImage);
          if (giftImg) {{
            const img = document.createElement('img');
            img.className = 'gift-svg';
            img.src = giftImg;
            img.alt = '';
            el.appendChild(img);
          }} else if (participant && participant.avatar_url) {{
            const img = document.createElement('img');
            img.className = 'gift-svg';
            img.src = participant.avatar_url;
            img.alt = '';
            el.appendChild(img);
          }} else {{
            const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            svg.className = 'gift-fallback-svg';
            svg.setAttribute('viewBox', '0 0 24 24');
            svg.innerHTML = '<path d="M7.5 6.2H16.5M13 6.2V23M12 7.5V6.2M9 8H15M9 11H15M9 14H15M9 17H15M9 20H15" stroke="currentColor" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color:var(--proj-accent)"/>';
            el.appendChild(svg);
          }}
          const duration = 500 + (intensity === 'high' ? 60 : intensity === 'big' ? 100 : intensity === 'epic' ? 200 : 0);
          el.style.opacity = '0';
          el.style.transitionProperty = 'opacity';
          el.style.transitionDuration = '0s';
          /* Curved flight via offset-path: path(...) with offset-distance 0% -> 100%. */
          el.style.setProperty('offset-path', 'path("' + pathD + '")');
          el.style.setProperty('offset-distance', '0%');
          layer.appendChild(el);
          void el.offsetWidth;
          el.style.opacity = '1';
          el.style.transitionProperty = 'offset-distance, opacity';
          el.style.transitionDuration = duration + 'ms';
          el.style.transitionTimingFunction = 'cubic-bezier(0.34, 1.56, 0.64, 1)';
          el.style.setProperty('offset-distance', '100%');
          const proj = {{ el: el, side: side, intensity: intensity }};
          BVC.projectilePool.push(proj);
          let completed = false;
          const cleanup = () => {{
            if (completed) return;
            completed = true;
            BVC.projectilePool = BVC.projectilePool.filter(p => p !== proj);
            if (el.parentNode) el.parentNode.removeChild(el);
          }};
          el.addEventListener('transitionend', cleanup);
          setTimeout(cleanup, duration + 400);
          spawnImpact(relTx, relTy, side, intensity);
          flashSide(side);
        }}
        function spawnImpact(x, y, side, intensity) {{
          const layer = $('btImpactLayer');
          if (!layer) return;
          const el = document.createElement('div');
          el.className = 'gift-impact';
          if (intensity === 'epic') el.classList.add('is-epic');
          el.style.left = x + 'px';
          el.style.top = y + 'px';
          el.style.setProperty('--proj-accent', BVC.getSideAccent(side));
          layer.appendChild(el);
          BVC.impactPool.push(el);
          el.addEventListener('animationend', () => {{
            BVC.impactPool = BVC.impactPool.filter(p => p !== el);
            if (el.parentNode) el.parentNode.removeChild(el);
          }});
          for (let i = 0; i < 3; i++) {{
            const spark = document.createElement('span');
            spark.className = 'spark';
            spark.style.left = '50%';
            spark.style.top = '50%';
            const angle = (i * 120) + 45;
            const dist = 20 + (i * 7);
            spark.style.setProperty('--sx', (Math.cos(angle * Math.PI / 180) * dist) + 'px');
            spark.style.setProperty('--sy', (Math.sin(angle * Math.PI / 180) * dist) + 'px');
            el.appendChild(spark);
          }}
        }}
        function flashSide(side) {{
          const sideEl = side === 'left' ? $('btLeft') : $('btRight');
          if (!sideEl) return;
          sideEl.classList.remove('is-side-flash');
          void sideEl.offsetWidth;
          sideEl.classList.add('is-side-flash');
        }}
        /* Floating +points near the scoring side's score (reused node) */
        function spawnScoreFloat(side, text, intensity) {{
          const el = side === 'left' ? $('btFloatL') : $('btFloatR');
          if (!el || !text) return;
          el.textContent = text;
          el.classList.toggle('is-big', intensity === 'big' || intensity === 'epic');
          el.classList.remove('show');
          void el.offsetWidth;
          el.classList.add('show');
        }}
        /* Brief glow on the scoring side's bar fill only */
        function hitFill(side) {{
          const fill = side === 'left' ? $('btFillL') : $('btFillR');
          if (!fill) return;
          fill.classList.remove('is-hit');
          void fill.offsetWidth;
          fill.classList.add('is-hit');
          setTimeout(() => fill.classList.remove('is-hit'), 450);
        }}
        /* ====== Lead Change ====== */
        function flashLeadChange(newLeader) {{
          if (BVC.leadFlashTimer) return;
          const badge = $('btLeadBadge');
          if (!badge) return;
          const loc = LOCALE();
          badge.textContent = newLeader === 'left' ? loc.leftLead : loc.rightLead;
          badge.style.display = 'block';
          badge.classList.remove('show');
          void badge.offsetWidth;
          badge.classList.add('show');
          BVC.leadFlashTimer = setTimeout(() => {{
            badge.classList.remove('show');
            badge.style.display = 'none';
            BVC.leadFlashTimer = null;
          }}, 1200);
        }}
        /* ====== Round Start ====== */
        function flashRound(round, bestOf) {{
          const badge = $('btRoundBadge');
          if (!badge) return;
          const loc = LOCALE();
          badge.textContent = loc.round + ' ' + round + ' · BO' + bestOf;
          badge.style.display = 'block';
          badge.classList.remove('show');
          void badge.offsetWidth;
          badge.classList.add('show');
          if (BVC.roundFlashTimer) clearTimeout(BVC.roundFlashTimer);
          BVC.roundFlashTimer = setTimeout(() => {{
            badge.classList.remove('show');
            badge.style.display = 'none';
            BVC.roundFlashTimer = null;
          }}, 900);
        }}
        /* ====== Round Spin (casino spin-up) ====== */
        function flashRoundPulse() {{
          const card = $('btCard');
          if (!card) return;
          if (BVC.roundPulseTimer) {{ clearTimeout(BVC.roundPulseTimer); BVC.roundPulseTimer = null; }}
          card.classList.remove('round-pulse');
          void card.offsetWidth;
          card.classList.add('round-pulse');
          BVC.roundPulseTimer = setTimeout(() => {{
            card.classList.remove('round-pulse');
            BVC.roundPulseTimer = null;
          }}, 750);
        }}
        /* ====== Jackpot Moment ====== */
        function flashJackpot() {{
          const jf = $('btJackpotFlash');
          if (jf) {{
            jf.classList.remove('show');
            void jf.offsetWidth;
            jf.classList.add('show');
          }}
          const loc = LOCALE();
          const b = $('btBadge');
          b.className = 'bt-badge bt-badge--jackpot';
          b.textContent = loc.jackpot;
          if (!b.classList.contains('show')) b.classList.add('show');
          if (badgeTimer) clearTimeout(badgeTimer);
          badgeTimer = setTimeout(() => {{
            b.classList.remove('show');
          }}, 2500);
        }}
        /* ====== Comeback Enhancement ====== */
        function triggerComebackEnhance(side) {{
          flashSide(side);
          const avatar = side === 'left' ? $('btAvatarL') : $('btAvatarR');
          if (avatar) {{
            avatar.classList.remove('pulse-enhanced');
            void avatar.offsetWidth;
            avatar.classList.add('pulse-enhanced');
          }}
          BVC.suppressCTA(2000);
        }}
        /* ====== Final Push Enhancement ====== */
        function triggerFinalPushEnhance() {{
          BVC.suppressCTA(3000);
          flashSide('left');
          flashSide('right');
        }}
        /* ====== Battle Winner Enhancement ====== */
        function showBattleWinnerEnhance() {{
          const w = $('btWinner');
          const winnerAv = w && w.querySelector('.bt-winner-avatar');
          if (winnerAv) {{
            winnerAv.classList.add('winner-pulse');
            setTimeout(() => winnerAv.classList.remove('winner-pulse'), 2000);
          }} else if (w) {{
            w.classList.remove('winner-pulse');
            void w.offsetWidth;
            w.classList.add('winner-pulse');
          }}
          const winner = state && state.winner;
          if (winner) {{
            const side = winner.team_id === 'left' ? 'left' : 'right';
            flashSide(side);
          }}
          BVC.suppressCTA(4000);
        }}
        /* ====== Score Interpolation ====== */
        function animateScore(elementId, from, to) {{
          const el = $(elementId);
          if (!el) return;
          if (from === to) {{
            el.textContent = to;
            el.classList.remove('pulse-enhanced');
            void el.offsetWidth;
            el.classList.add('pulse-enhanced');
            return;
          }}
          if (elementId === 'btScoreL' && BVC.scoreAnimTimerL) {{ clearInterval(BVC.scoreAnimTimerL); BVC.scoreAnimTimerL = null; }}
          if (elementId === 'btScoreR' && BVC.scoreAnimTimerR) {{ clearInterval(BVC.scoreAnimTimerR); BVC.scoreAnimTimerR = null; }}
          let current = from;
          const step = Math.max(1, Math.ceil(Math.abs(to - from) / 12));
          const dir = to > from ? 1 : -1;
          const timer = setInterval(() => {{
            current += step * dir;
            if ((dir > 0 && current >= to) || (dir < 0 && current <= to)) {{
              current = to;
              clearInterval(timer);
              if (elementId === 'btScoreL') BVC.scoreAnimTimerL = null;
              if (elementId === 'btScoreR') BVC.scoreAnimTimerR = null;
            }}
            el.textContent = current;
          }}, 16);
          if (elementId === 'btScoreL') BVC.scoreAnimTimerL = timer;
          if (elementId === 'btScoreR') BVC.scoreAnimTimerR = timer;
        }}
        /* ====== Combo Pulse ====== */
        function pulseCombo(side, count) {{
          const comboEl = side === 'left' ? $('btComboL') : $('btComboR');
          if (!comboEl) return;
          comboEl.classList.remove('pulse-enhanced');
          void comboEl.offsetWidth;
          comboEl.classList.add('pulse-enhanced');
        }}
        /* ====== Event Dispatcher ====== */
        function processEvents() {{
          if (!state || !Array.isArray(state.events)) return;
          for (const e of state.events) {{
            if (!(e && e.type)) continue;
            const at = Number(e.at) || 0;
            if (at <= lastSeenAt + 0.0001) continue;
            lastSeenAt = Math.max(lastSeenAt, at);
            const p = e.payload || {{}};
            if (e.type === 'gift_received' || e.type === 'big_gift') {{
              const pts = p.points != null ? p.points : (p.diamonds || 0);
              const intensity = BVC.getIntensity(p.diamonds != null ? p.diamonds : (p.points || 0), p.multiplier || 1);
              spawnProjectile(e.team_id, p, intensity);
              const locale = LOCALE();
              const isBig = intensity === 'big' || intensity === 'epic';
              flashGift(isBig ? locale.bigGift : locale.gift, pts ? '+' + pts : '');
              if (pts) spawnScoreFloat(e.team_id, '+' + pts, intensity);
              hitFill(e.team_id);
              const team = (state.teams && state.teams.find(t => t.id === e.team_id)) || {{score: 0}};
              const to = team.score || 0;
              const from = lastDelta[e.team_id] || 0;
              if (from !== to) {{
                animateScore(e.team_id === 'left' ? 'btScoreL' : 'btScoreR', from, to);
              }}
              if (e.type === 'big_gift') {{
                flashJackpot();
              }}
            }} else if (e.type === 'combo_started' || e.type === 'combo_updated') {{
              const side = (p.team_id) || (state.combo && state.combo.team_id) || 'left';
              const count = p.count || (state.combo && state.combo.count) || 1;
              pulseCombo(side, count);
              const prompt = $('btGiftPrompt');
              const msgEl = $('btGiftMsg');
              if (prompt && msgEl) {{
                prompt.style.display = 'block';
                msgEl.textContent = LOCALE().combo + ' x' + count;
                BVC.holdCTA(1200);
              }}
            }} else if (e.type === 'comeback') {{
              if (typeof flashComeback === 'function') flashComeback();
              else showBadge(LOCALE().comeback, 'comeback');
              const side = e.team_id || p.team_id || 'left';
              triggerComebackEnhance(side);
            }} else if (e.type === 'final_push') {{
              triggerFinalPushEnhance();
            }} else if (e.type === 'round_started') {{
              const round = p.round || (state.round || 1);
              const bestOf = p.best_of || (state.best_of || 3);
              flashRound(round, bestOf);
              flashRoundPulse();
            }} else if (e.type === 'round_finished') {{
              if (p.draw === true) {{
                showBadge(LOCALE().draw, 'draw');
              }} else {{
                const winnerTeam = p.winner_team || p.winner || 'left';
                const winnerAv = winnerTeam === 'left' ? $('btAvatarL') : $('btAvatarR');
                if (winnerAv) {{
                  winnerAv.classList.remove('pulse-enhanced');
                  void winnerAv.offsetWidth;
                  winnerAv.classList.add('pulse-enhanced');
                }}
              }}
            }} else if (e.type === 'battle_finished') {{
              showBattleWinnerEnhance();
              flashJackpot();
            }}
          }}
        }}
        function flashGift(msg, fx) {{
          const prompt = $('btGiftPrompt');
          if (!prompt) return;
          prompt.style.display = 'block';
          const msgEl = $('btGiftMsg');
          const fxEl = $('btGiftFx');
          const locale = LOCALE();
          msgEl.textContent = msg || locale.gift;
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
          BVC.holdCTA(1400);
        }}
        function ctaPool() {{
          const loc = LOCALE();
          const cfg = state && state.config;
          if (cfg && cfg.gifts_enabled === false) return loc.cta;
          return loc.ctaScore;
        }}
        function rotateCTA() {{
          if (BVC.ctaRotateTimer) {{ clearTimeout(BVC.ctaRotateTimer); BVC.ctaRotateTimer = null; }}
          if (BVC.ctaSuppressionTimer) return;
          if (!state || (state.status !== 'active' && state.status !== 'countdown')) return;
          if (state.flags && state.flags.final_push) return;
          const pool = ctaPool();
          if (!pool || !pool.length) return;
          BVC.ctaIndex = (BVC.ctaIndex + 1) % pool.length;
          const msgEl = $('btGiftMsg');
          if (msgEl) msgEl.textContent = pool[BVC.ctaIndex];
          BVC.ctaRotateTimer = setTimeout(rotateCTA, 5000);
        }}
        function updateGiftPrompt() {{
          const prompt = $('btGiftPrompt');
          if (!prompt) return;
          if (BVC.ctaRotateTimer) {{ clearTimeout(BVC.ctaRotateTimer); BVC.ctaRotateTimer = null; }}
          if (BVC.ctaSuppressionTimer) return;
          const loc = LOCALE();
          prompt.style.display = 'block';
          const msgEl = $('btGiftMsg');
          const fxEl = $('btGiftFx');
          if (fxEl) fxEl.textContent = '';
          if (!state || state.status === 'idle') {{
            // Idle already shows the gentle waiting line (btIdle) — keep the
            // pill hidden here to avoid duplicating the same text twice.
            prompt.style.display = 'none';
          }} else if (state.status === 'finished') {{
            const nm = (state.winner && (state.winner.name || state.winner.team_id)) || '';
            if (msgEl) msgEl.textContent = nm ? (loc.winner + ' — ' + nm) : loc.winner;
          }} else if (state.flags && state.flags.final_push) {{
            if (msgEl) msgEl.textContent = loc.finalPushCta;
            BVC.ctaRotateTimer = setTimeout(rotateCTA, 5000);
          }} else {{
            const pool = ctaPool();
            if (msgEl && pool && pool.length) {{
              msgEl.textContent = pool[BVC.ctaIndex % pool.length];
            }}
            BVC.ctaRotateTimer = setTimeout(rotateCTA, 5000);
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
        const NEUTRAL_AV = 'data:image/svg+xml;'
          + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1">'
          + '<rect fill="%231e1b2a"/></svg>');
        const COIN_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
          + '<defs><linearGradient id="btCoinG" x1="0" y1="0" x2="1" y2="1">'
          + '<stop offset="0" stop-color="%23fde68a"/>'
          + '<stop offset="1" stop-color="%23b45309"/></linearGradient></defs>'
          + '<circle cx="12" cy="12" r="11" fill="url(#btCoinG)"/>'
          + '<circle cx="12" cy="12" r="7.2" fill="none" stroke="%2392400e" stroke-opacity="0.5" stroke-width="1.3"/>'
          + '<path d="M12 6.5l1.7 4.2 4.5.8-3.4 3.1 1.4 4.4-4.5-2.6-4.5 2.6 1.4-4.4 1.8-1.7z" fill="%2392400e" fill-opacity="0.6"/>'
          + '</svg>';
        function renderEventRow(row, state, L, R) {{
          if (!row) return;
          if (!state || state.status === 'idle' || state.status === 'countdown'
              || state.status === 'finished') {{
            row.innerHTML = '';
            row.style.display = 'none';
            return;
          }}
          const evs = state.events || [];
          const recent = evs.slice(-3);
          const items = [];
          for (const ev of recent) {{
            const type = ev.type || 'score';
            const teamId = ev.team_id || '';
            const side = teamId === 'left' ? 'left' : (teamId === 'right' ? 'right' : 'left');
            const p = teamId === 'left' ? L : teamId === 'right' ? R : null;
            const av = p && p.avatar_url ? p.avatar_url : NEUTRAL_AV;
            const pts = (ev.payload && (ev.payload.diamonds != null
                ? ev.payload.diamonds
                : (ev.payload.points != null ? ev.payload.points : '')));
            const name = p ? p.name : (teamId === 'left' ? 'LEFT' : 'RIGHT');
            const it = document.createElement('span');
            it.className = 'ev-item ev-item--' + side;
            const img = document.createElement('img');
            img.className = 'ev-av';
            img.src = av;
            img.onerror = function() {{ this.style.display = 'none'; }};
            it.appendChild(img);
            const nameEl = document.createElement('span');
            nameEl.className = 'ev-name';
            nameEl.textContent = name;
            it.appendChild(nameEl);
            if (pts !== '') {{
              const v = document.createElement('span');
              v.className = 'ev-val';
              v.textContent = '+' + pts;
              it.appendChild(v);
            }}
            items.push(it);
          }}
          row.innerHTML = '';
          if (items.length === 0) {{ row.style.display = 'none'; return; }}
          for (let i = 0; i < items.length; i++) {{
            row.appendChild(items[i]);
            if (i < items.length - 1) {{
              const sep = document.createElement('span');
              sep.className = 'ev-sep';
              sep.textContent = 'VS';
              row.appendChild(sep);
            }}
          }}
          row.style.display = 'flex';
        }}
        function render() {{
          if (!state) return;
          if (!bvcInitialized) initBVC();
          processEvents();
          const cfg = state.config || {{}};
          document.body.style.setProperty('--bfont', (cfg.font_family || 'Segoe UI') + ', system-ui, sans-serif');
          /* Live-apply scale + font size from config on every patch
             (mirrors stream_goal applyScale): editor changes arrive as
             config patches, so the widget must not rely on the static
             first-paint values alone. */
          const sc = Math.max(40, Math.min(250, parseInt(cfg.scale_percent, 10) || 100));
          root.style.setProperty('--bt-u', String(sc / 100));
          const fs = Math.max(10, Math.min(32, parseInt(cfg.base_font_size_px, 10) || 14));
          root.style.setProperty('--bt-font-k', String(fs / 14));
          rootStyleU = sc / 100;
          root.dataset.theme = cfg.theme || 'cheremsha_neon';
          const status = state.status || 'idle';
          const flags = state.flags || {{}};
          const combo = state.combo || {{}};
          const isFinal = !!flags.final_push;
          const t = LOCALE();
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
          const roundLabel = t.round + ' ' + (state.round || 1) + ' · BO' + (state.best_of || 3);
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
          const Lscore = (tL.score || 0) | 0;
          const Rscore = (tR.score || 0) | 0;
          const total = Math.max(0, Lscore + Rscore);
          const barTrack = $('btBarTrack');
          if (barTrack) {{
            barTrack.classList.toggle('is-empty', total <= 0);
            var leftRatio = total <= 0 ? 0 : (Lscore / total);
            $('btFillL').style.width = (leftRatio * 100).toFixed(2) + '%';
            $('btFillR').style.width = ((1 - leftRatio) * 100).toFixed(2) + '%';
            if (Lscore >= Rscore && Lscore > 0) {{
              $('btFillL').style.boxShadow = '0 0 ' + (9 * rootStyleU) + 'px ' + currentColor;
              $('btFillR').style.boxShadow = 'none';
            }} else if (Rscore > Lscore) {{
              $('btFillR').style.boxShadow = '0 0 ' + (9 * rootStyleU) + 'px ' + currentColor;
              $('btFillL').style.boxShadow = 'none';
            }} else {{
              $('btFillL').style.boxShadow = 'none';
              $('btFillR').style.boxShadow = 'none';
            }}
          }}
          /* Detect lead change */
          const newLeader = Lscore > Rscore ? 'left' : (Rscore > Lscore ? 'right' : null);
          if (newLeader && newLeader !== BVC.currentLeader && Lscore > 0 && Rscore > 0) {{
            flashLeadChange(newLeader);
          }}
          BVC.currentLeader = newLeader;
          /* Detect round change */
          const currentRound = state.round || 1;
          if (BVC.lastRound !== null && BVC.lastRound !== currentRound) {{
            flashRound(currentRound, state.best_of || 3);
          }}
          BVC.lastRound = currentRound;
          /* Detect round_wins change */
          const currentRoundWins = {{
            left: (state.round_wins && state.round_wins.left) || (tL.round_wins || 0),
            right: (state.round_wins && state.round_wins.right) || (tR.round_wins || 0)
          }};
          if (BVC.lastRoundWins) {{
            const prevL = BVC.lastRoundWins.left;
            const prevR = BVC.lastRoundWins.right;
            if (currentRoundWins.left !== prevL || currentRoundWins.right !== prevR) {{
              if (currentRoundWins.left > prevL) {{
                const avL = $('btAvatarL');
                if (avL) {{
                  avL.classList.remove('pulse-enhanced');
                  void avL.offsetWidth;
                  avL.classList.add('pulse-enhanced');
                }}
              }} else if (currentRoundWins.right > prevR) {{
                const avR = $('btAvatarR');
                if (avR) {{
                  avR.classList.remove('pulse-enhanced');
                  void avR.offsetWidth;
                  avR.classList.add('pulse-enhanced');
                }}
              }}
            }}
          }}
          BVC.lastRoundWins = currentRoundWins;
          let secs = state.remaining_seconds || 0;
          if (status === 'countdown') secs = state.countdown_remaining_s || 0;
          if (status === 'finished') secs = 0;
          const timerText = $('btTimerText');
          if (status === 'countdown') {{
            timerText.textContent = t.start + ' ' + secs;
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
          // Highlight the current round only while a battle is actually
          // running — in idle all dots stay neutral (nothing won yet).
          const inBattle = status === 'countdown' || status === 'active';
          for (let i = 0; i < need; i++) {{
            const a = document.createElement('i');
            if (inBattle) {{
              if (i === state.round - 1) a.className = 'active';
              else if ((wins.left || 0) > i) a.className = 'won-left';
            }} else if (status === 'finished' && (wins.left || 0) > i) {{
              a.className = 'won-left';
            }}
            dots.appendChild(a);
            const b = document.createElement('i');
            if (inBattle) {{
              if (i === state.round - 1) b.className = 'active';
              else if ((wins.right || 0) > i) b.className = 'won-right';
            }} else if (status === 'finished' && (wins.right || 0) > i) {{
              b.className = 'won-right';
            }}
            dots.appendChild(b);
          }}
          const eventRow = $('btEventRow');
          renderEventRow(eventRow, state, L, R);
          const comboL = $('btComboL');
          const comboR = $('btComboR');
          if (combo.team_id === 'left' && combo.count > 0 && combo.multiplier > 1) {{
            comboL.textContent = t.combo + ' x' + combo.multiplier.toFixed(1);
            comboL.className = 'bt-combo bt-combo--left show';
          }} else {{
            comboL.className = 'bt-combo';
          }}
          if (combo.team_id === 'right' && combo.count > 0 && combo.multiplier > 1) {{
            comboR.textContent = t.combo + ' x' + combo.multiplier.toFixed(1);
            comboR.className = 'bt-combo bt-combo--right show';
          }} else {{
            comboR.className = 'bt-combo';
          }}
          $('btFinalLabel').textContent = isFinal ? t.finalPush : '';
          const idleMsg = $('btIdle');
          if (status === 'idle') {{
            idleMsg.style.display = 'block';
            const idleText = idleMsg.querySelector('.bt-idle-text');
            if (!idleText) {{
              idleMsg.innerHTML = '';
              const coin = document.createElement('span');
              coin.className = 'bt-idle-coin';
              coin.innerHTML = COIN_SVG;
              const txt = document.createElement('span');
              txt.className = 'bt-idle-text';
              idleMsg.appendChild(coin);
              idleMsg.appendChild(txt);
            }}
            idleMsg.querySelector('.bt-idle-text').textContent = t.idle;
          }} else {{
            idleMsg.style.display = 'none';
          }}
          updateGiftPrompt();
          const scoreLabels = document.querySelectorAll('.bt-score-label');
          for (const sEl of scoreLabels) sEl.textContent = t.score;
          const wLabel = $('btWinnerLabel');
          if (wLabel) wLabel.textContent = t.winner;
          const w = $('btWinner');
          const hasWinner = status === 'finished' && cfg.show_winner_screen !== false && state.winner;
          const winnerSide = hasWinner ? (state.winner.team_id === 'right' ? 'right' : 'left') : null;
          const sideL = $('btLeft');
          const sideR = $('btRight');
          if (sideL) {{
            sideL.classList.toggle('is-winner', winnerSide === 'left');
            sideL.classList.toggle('is-loser', winnerSide === 'right');
          }}
          if (sideR) {{
            sideR.classList.toggle('is-winner', winnerSide === 'right');
            sideR.classList.toggle('is-loser', winnerSide === 'left');
          }}
          if (hasWinner) {{
            w.style.display = 'flex';
            const nm = state.winner.name || state.winner.team_id || t.winner;
            $('btWinnerName').textContent = nm.toUpperCase().replace(/</g, '&lt;').replace(/>/g, '&gt;');
            $('btWinnerScore').textContent = (tL.score || 0) + ' vs ' + (tR.score || 0);
          }} else {{
            w.style.display = 'none';
          }}
          if (cfg.show_event_badges !== false) {{
            const evs = state.events || [];
            const last = evs.length ? evs[evs.length - 1] : null;
            if (combo && combo.count > 0 && combo.multiplier > 1) {{
              showBadge(t.combo + ' x' + combo.multiplier.toFixed(1), 'combo');
            }} else if (last && last.type === 'comeback') {{
              showBadge(t.comeback, 'comeback');
            }} else if (last && last.type === 'final_push') {{
              showBadge(t.finalPush, 'final');
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
            lastSeenAt = 0;
            if (!bvcInitialized) initBVC();
            BVC.reset();
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
            "locale": load_ui_locale(),
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
