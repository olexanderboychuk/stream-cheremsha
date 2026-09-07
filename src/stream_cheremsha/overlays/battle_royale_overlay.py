from __future__ import annotations

# ruff: noqa: E501
import json
from typing import Any

from stream_cheremsha.overlays.battle_royale_overlay_config import (
    battle_royale_overlay_config_from_json_text,
    battle_royale_overlay_config_to_json_text,
    load_battle_royale_overlay_config,
)
from stream_cheremsha.overlays.models import normalize_instance_id
from stream_cheremsha.overlays.ui_locale import load_ui_locale


def _json_for_script(value: Any) -> str:
    s = json.dumps(value, ensure_ascii=False)
    return s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


class BattleRoyaleOverlayType:
    type = "battle_royale"

    def render_html(self, params: dict[str, Any]) -> str:
        raw_instance = params.get("instance")
        try:
            instance = normalize_instance_id(str(raw_instance or ""))
        except ValueError:
            instance = "default"

        subscribe_msg = {
            "op": "subscribe",
            "type": "battle_royale",
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
        root_style = f"--br-widget-scale:{initial_scale / 100:.4f};--br-u:{initial_scale / 100:.4f};"

        return f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Battle Royale</title>
    <style>
      html, body {{
        margin:0; padding:0; background:transparent; overflow:hidden;
        height:100%; width:100%;
      }}
      * {{ box-sizing:border-box; }}
      .root {{
        position:absolute; inset:0;
        font-family: var(--bfont, 'Segoe UI', system-ui, sans-serif);
         pointer-events:none;
         display:flex; flex-direction:column;
         padding: calc(8px * var(--br-u, 1)) calc(14px * var(--br-u, 1)) calc(10px * var(--br-u, 1));
         color: #f1f5f9;
         --txt-sharp: 0 1px 0 #000, 0 2px 0 #000, 0 3px 10px rgba(0,0,0,0.95), 0 0 2px rgba(0,0,0,0.9);
         --txt-sharp-glow: 0 1px 0 #000, 0 2px 0 #000, 0 3px 12px rgba(0,0,0,0.95), 0 0 18px currentColor;
         --anim-speed: 1;
         --br-widget-scale: 1;
         --br-u: var(--br-widget-scale, 1);
      }}
      .root.crit-flash::after {{
        content:''; position:absolute; inset:0;
         background: rgba(255,255,255,0.35);
         animation: critFlash 0.4s ease-out forwards;
         animation-duration: calc(0.4s / var(--anim-speed, 1));
        pointer-events:none; z-index: 50;
      }}
      @keyframes critFlash {{
        0% {{ opacity:1; }} 100% {{ opacity:0; }}
      }}
      .hdr {{
         text-align:center; margin-bottom: calc(6px * var(--br-u, 1)); flex: 0 0 auto;
      }}
      .hdr-main {{
        font-family: var(--bfont, 'Segoe UI', system-ui);
        font-weight:900; letter-spacing:0.14em;
        font-size: 1.43em;
        background: linear-gradient(180deg, #fde68a 0%, #f59e0b 55%, #b45309 100%);
        -webkit-background-clip: text; background-clip: text;
        color: transparent;
        filter:
          drop-shadow(0 1px 0 #000)
          drop-shadow(0 2px 0 #000)
          drop-shadow(0 3px 10px rgba(0,0,0,0.95))
          drop-shadow(0 0 14px rgba(251,191,36,0.75));
         line-height: 1.1;
       }}
       .root.preset-cyber .hdr-main {{
         background: linear-gradient(180deg, #a5f3fc 0%, #22d3ee 55%, #2563eb 100%);
         -webkit-background-clip: text; background-clip: text;
         filter: drop-shadow(0 1px 0 #000) drop-shadow(0 0 16px rgba(34,211,238,0.8));
       }}
       .root.preset-dark .hdr-main {{
         background: linear-gradient(180deg, #fecaca 0%, #ef4444 55%, #991b1b 100%);
         -webkit-background-clip: text; background-clip: text;
         filter: drop-shadow(0 1px 0 #000) drop-shadow(0 0 16px rgba(239,68,68,0.8));
       }}
       .root.preset-minimal .hdr-main {{
         background: linear-gradient(180deg, #f8fafc 0%, #cbd5e1 100%);
         -webkit-background-clip: text; background-clip: text;
         filter: drop-shadow(0 1px 0 #000) drop-shadow(0 0 8px rgba(226,232,240,0.45));
       }}
      .hdr-sub {{
        font-size: 0.79em;
        letter-spacing:0.35em; color: rgba(253,230,138,0.95);
         margin-top: calc(2px * var(--br-u, 1));
        text-shadow: var(--txt-sharp);
      }}
      .hint {{
        text-align:center; color: rgba(226,232,240,0.95);
        font-size: 0.93em;
         padding: calc(24px * var(--br-u, 1)) calc(12px * var(--br-u, 1)); flex: 1;
        text-shadow: var(--txt-sharp);
      }}
       .stage {{
         flex: 1 1 auto; display:flex; flex-direction:row;
         align-items:stretch; justify-content:center;
         gap: calc(8px * var(--br-u, 1)); min-height: calc(200px * var(--br-u, 1));
         position:relative;
       }}
       .stage.multi {{
         display:grid; grid-template-columns:repeat(2, minmax(0, 1fr));
         align-content:start; align-items:stretch;
       }}
       .stage.multi .card {{
         width:100%; max-width:none; flex:none;
       }}
       .stage.multi .center {{
         grid-column:1 / -1; min-width:0; min-height:92px;
       }}
      .card {{
        flex: 0 0 26%; max-width: 220px;
        display:flex; flex-direction:column; align-items:center;
         padding: calc(10px * var(--br-u, 1)) calc(10px * var(--br-u, 1)) calc(8px * var(--br-u, 1));
         border-radius: calc(14px * var(--br-u, 1));
        background: linear-gradient(165deg, rgba(8,12,22,0.92), rgba(15,23,42,0.78));
        position:relative; z-index: 2;
        transition: opacity 0.5s ease, filter 0.5s ease, transform 0.35s ease;
      }}
      .card.ko {{
        opacity: 0.25; filter: grayscale(1) brightness(0.6);
        transform: scale(0.92);
      }}
       .card.shake {{
         animation: shake 0.45s ease;
         animation-duration: calc(0.45s / var(--anim-speed, 1));
       }}
      @keyframes shake {{
        0%,100% {{ transform: translateX(0); }}
        25% {{ transform: translateX(-6px); }}
        50% {{ transform: translateX(6px); }}
        75% {{ transform: translateX(-4px); }}
      }}
      .card.left {{
        border: 2px solid rgba(56,189,248,0.85);
        box-shadow: 0 0 28px rgba(37,99,235,0.55), inset 0 0 24px rgba(56,189,248,0.12);
      }}
      .card.right {{
        border: 2px solid rgba(249,115,22,0.9);
        box-shadow: 0 0 28px rgba(234,88,12,0.55), inset 0 0 24px rgba(249,115,22,0.12);
      }}
      .ch-label {{
        font-family: var(--bfont, 'Segoe UI', system-ui);
        font-size: 0.71em;
        letter-spacing:0.2em; font-weight:700;
         margin-bottom: calc(8px * var(--br-u, 1)); opacity: 0.95;
        text-shadow: var(--txt-sharp);
      }}
      .card.left .ch-label {{ color: #7dd3fc; }}
      .card.right .ch-label {{ color: #fdba74; }}
      .av-wrap {{
         position:relative; padding: calc(4px * var(--br-u, 1));
         border-radius: calc(16px * var(--br-u, 1));
      }}
      .card.left .av-wrap {{
        box-shadow: 0 0 22px rgba(59,130,246,0.7);
        background: linear-gradient(135deg, rgba(59,130,246,0.35), transparent);
      }}
      .card.right .av-wrap {{
        box-shadow: 0 0 22px rgba(249,115,22,0.65);
        background: linear-gradient(135deg, rgba(249,115,22,0.35), transparent);
      }}
       .avatar {{
         display:block; border-radius: calc(12px * var(--br-u, 1)); object-fit:cover;
        background: rgba(30,41,59,0.8);
      }}
      .nick {{
         margin-top: calc(8px * var(--br-u, 1)); font-weight:700; font-size: 1.07em;
        max-width: 100%; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
        text-shadow: var(--txt-sharp);
      }}
      .card.left .nick {{ color: #bae6fd; }}
      .card.right .nick {{ color: #fed7aa; }}
      .hp-label {{
         margin-top: calc(10px * var(--br-u, 1)); font-size: 0.79em;
        font-weight:700; letter-spacing:0.06em; opacity: 0.95;
        color: #f8fafc;
        text-shadow: var(--txt-sharp);
      }}
      .hp-wrap {{
         width: 100%; height: calc(14px * var(--br-u, 1)); margin-top: calc(4px * var(--br-u, 1));
         background: rgba(0,0,0,0.45); border-radius: 999px;
        overflow:hidden; border: 1px solid rgba(255,255,255,0.15);
      }}
      .card.left .hp-fill {{
        height:100%; border-radius:999px;
        background: linear-gradient(90deg, #6366f1, #22d3ee);
        box-shadow: 0 0 12px rgba(34,211,238,0.65);
        transition: width 0.3s ease;
      }}
      .card.right .hp-fill {{
        height:100%; border-radius:999px;
        background: linear-gradient(90deg, #ef4444, #f97316);
        box-shadow: 0 0 12px rgba(249,115,22,0.65);
        transition: width 0.3s ease;
      }}
      .donated {{
         margin-top: calc(8px * var(--br-u, 1)); font-size: 0.79em;
        font-weight:700; letter-spacing:0.08em;
        color: #f1f5f9;
        text-shadow: var(--txt-sharp);
      }}
      .card-foot {{
         margin-top: calc(10px * var(--br-u, 1)); width: 100%;
        display:flex; justify-content:space-between;
        font-size: 0.71em;
        color: #e2e8f0;
         gap: calc(6px * var(--br-u, 1));
        text-shadow: var(--txt-sharp);
      }}
      .support-gifts {{
         margin-top: calc(8px * var(--br-u, 1)); width: 100%;
         display:flex; flex-direction:column; align-items:center; gap: calc(4px * var(--br-u, 1));
      }}
      .support-label {{
        font-size: 0.64em;
        font-weight:700; letter-spacing:0.12em;
        color: #e2e8f0;
        text-shadow: var(--txt-sharp);
      }}
      .gift-row {{
         display:flex; flex-wrap:wrap; justify-content:center; gap: calc(5px * var(--br-u, 1));
      }}
      .gift-icon {{
         width: calc(30px * var(--br-u, 1)); height: calc(30px * var(--br-u, 1)); object-fit:contain;
         border-radius: calc(8px * var(--br-u, 1)); padding: calc(2px * var(--br-u, 1));
        background: rgba(15,23,42,0.75);
        border: 1px solid rgba(255,255,255,0.22);
        box-shadow: 0 0 8px rgba(0,0,0,0.45);
      }}
      .center {{
         flex: 1 1 auto; min-width: calc(120px * var(--br-u, 1));
        display:flex; flex-direction:column;
        align-items:center; justify-content:center;
        position:relative; z-index: 3;
      }}
      .timer {{
        font-family: var(--bfont, 'Segoe UI', system-ui);
        font-size: 2em;
        font-weight:900; color: #fef3c7;
        text-shadow: 0 1px 0 #000, 0 2px 0 #000, 0 4px 14px rgba(0,0,0,0.95), 0 0 20px rgba(250,204,21,0.85);
         margin-bottom: calc(8px * var(--br-u, 1)); font-variant-numeric: tabular-nums;
      }}
      .clash {{
         position:relative; width: 100%; height: calc(72px * var(--br-u, 1));
        display:flex; align-items:center; justify-content:center;
      }}
       .beam {{
         position:absolute; top:50%; height: calc(18px * var(--br-u, 1));
        transform: translateY(-50%);
        border-radius: 999px;
        filter: blur(0.3px);
         transition: width 0.35s ease, opacity 0.35s ease;
         animation: beamPulse 1.1s ease-in-out infinite;
         animation-duration: calc(1.1s / var(--anim-speed, 1));
       }}
       .root.projectile-off .beam {{ animation: none; }}
       @keyframes beamPulse {{
         0%,100% {{ opacity: 0.78; }}
         50% {{ opacity: 1; }}
       }}
      .beam-left {{
         right: 50%; margin-right: calc(28px * var(--br-u, 1));
        background: linear-gradient(270deg, rgba(255,255,255,0.95), #38bdf8 40%, #2563eb 100%);
        box-shadow: 0 0 20px rgba(56,189,248,0.9);
        transform-origin: right center;
      }}
      .beam-right {{
         left: 50%; margin-left: calc(28px * var(--br-u, 1));
        background: linear-gradient(90deg, rgba(255,255,255,0.95), #fb923c 40%, #ea580c 100%);
        box-shadow: 0 0 20px rgba(249,115,22,0.9);
        transform-origin: left center;
      }}
      .clash-core {{
        position:absolute; left:50%; top:50%;
         width: calc(56px * var(--br-u, 1)); height: calc(56px * var(--br-u, 1));
        transform: translate(-50%, -50%);
        border-radius: 50%;
        background: radial-gradient(circle, #fff 0%, #fde047 25%, #f97316 55%, transparent 72%);
         box-shadow: 0 0 36px rgba(255,255,255,0.95), 0 0 60px rgba(251,191,36,0.6);
         animation: corePulse 1.2s ease-in-out infinite;
         animation-duration: calc(1.2s / var(--anim-speed, 1));
      }}
      @keyframes corePulse {{
        0%,100% {{ transform: translate(-50%,-50%) scale(1); opacity: 1; }}
        50% {{ transform: translate(-50%,-50%) scale(1.12); opacity: 0.88; }}
      }}
      .tug {{
         width: 92%; height: calc(10px * var(--br-u, 1)); margin-top: calc(10px * var(--br-u, 1));
        background: rgba(0,0,0,0.5); border-radius: 999px;
        overflow:hidden; border: 1px solid rgba(255,255,255,0.12);
      }}
      .tug-fill {{
        height:100%; border-radius:999px;
        background: linear-gradient(90deg, #3b82f6, #fbbf24 48%, #f97316);
        box-shadow: 0 0 10px rgba(251,191,36,0.5);
        transition: width 0.35s ease;
      }}
      .dmg-pop {{
        position:absolute; left:50%; top: 18%;
        transform: translateX(-50%);
        font-family: var(--bfont, 'Segoe UI', system-ui);
        font-weight:900; font-size: 1.57em;
        color: #fecaca;
         text-shadow: 0 1px 0 #000, 0 2px 0 #000, 0 4px 12px rgba(0,0,0,0.95), 0 0 14px rgba(239,68,68,0.95);
         animation: dmgFloat 1.1s ease-out forwards;
         animation-duration: calc(1.1s / var(--anim-speed, 1));
        pointer-events:none; z-index: 20;
      }}
      @keyframes dmgFloat {{
        0% {{ opacity:0; transform: translate(-50%, 12px) scale(0.7); }}
        15% {{ opacity:1; transform: translate(-50%, 0) scale(1.1); }}
        100% {{ opacity:0; transform: translate(-50%, -48px) scale(0.95); }}
      }}
       .countdown-overlay {{
        position:absolute; inset:0; display:flex; align-items:center; justify-content:center;
        font-family: var(--bfont, 'Segoe UI', system-ui);
        font-size: 4.57em; font-weight:900;
        color: #fde68a;
        text-shadow: 0 2px 0 #000, 0 4px 0 #000, 0 6px 20px rgba(0,0,0,0.95), 0 0 32px rgba(250,204,21,0.95);
        z-index: 40; background: rgba(0,0,0,0.35);
         animation: countPulse 0.7s ease infinite;
         animation-duration: calc(0.7s / var(--anim-speed, 1));
      }}
      @keyframes countPulse {{
        0%,100% {{ transform: scale(1); }} 50% {{ transform: scale(1.06); }}
      }}
      .info-panel {{
         flex: 0 0 auto; margin-top: calc(8px * var(--br-u, 1));
         padding: calc(10px * var(--br-u, 1)) calc(14px * var(--br-u, 1));
         border-radius: calc(12px * var(--br-u, 1));
        background: linear-gradient(180deg, rgba(10,14,24,0.88), rgba(6,8,14,0.92));
        border: 1px solid rgba(148,163,184,0.25);
        font-size: 0.86em;
        line-height: 1.45;
      }}
       .info-panel .row {{ margin: calc(2px * var(--br-u, 1)) 0; text-shadow: var(--txt-sharp); }}
      .info-panel .label {{ color: #cbd5e1; font-weight:600; }}
      .info-panel .val {{ color: #f8fafc; font-weight:700; }}
      .info-panel .dmg {{ color: #fca5a5; font-weight:800; }}
       .victory-banner {{
        position:absolute; top: 42%; left:50%; transform: translate(-50%, -50%);
         padding: calc(14px * var(--br-u, 1)) calc(28px * var(--br-u, 1)); border-radius: calc(14px * var(--br-u, 1)); z-index: 45;
        background: rgba(8,10,18,0.9);
        border: 2px solid rgba(250,204,21,0.85);
        font-family: var(--bfont, 'Segoe UI', system-ui);
        font-weight:900; font-size: 1.43em;
        color: #fde68a;
        text-shadow: 0 2px 0 #000, 0 4px 0 #000, 0 6px 18px rgba(0,0,0,0.95), 0 0 24px rgba(250,204,21,0.9);
        box-shadow: 0 0 32px rgba(250,204,21,0.55);
         white-space:nowrap;
         animation: victoryPop 0.65s ease-out both;
         animation-duration: calc(0.65s / var(--anim-speed, 1));
       }}
       .root.fatality-off .victory-banner {{ animation: none; }}
       @keyframes victoryPop {{
         0% {{ opacity: 0; transform: translate(-50%, -50%) scale(0.7); }}
         70% {{ opacity: 1; transform: translate(-50%, -50%) scale(1.06); }}
         100% {{ opacity: 1; transform: translate(-50%, -50%) scale(1); }}
       }}
      .root.idle-empty .hdr,
      .root.idle-empty .stars,
      .root.idle-empty .hint,
      .root.idle-empty .stage,
      .root.idle-empty .info-panel {{
        display: none !important;
      }}
      .stars {{
        position:absolute; inset:0; pointer-events:none; z-index:0;
        background:
          radial-gradient(1px 1px at 10% 20%, rgba(255,255,255,0.5), transparent),
          radial-gradient(1px 1px at 80% 30%, rgba(255,255,255,0.4), transparent),
          radial-gradient(1.5px 1.5px at 50% 80%, rgba(255,255,255,0.35), transparent),
          radial-gradient(1px 1px at 30% 60%, rgba(255,255,255,0.3), transparent);
      }}
    </style>
  </head>
  <body>
     <div id="root" class="root" style="{root_style}">
      <div class="stars"></div>
      <div class="hdr">
        <div id="hdrMain" class="hdr-main">BATTLE ROYALE</div>
        <div id="hdrSub" class="hdr-sub">THE DONOR DUEL</div>
      </div>
      <div id="stage" class="stage" style="display:none"></div>
      <div id="hint" class="hint"></div>
      <div id="infoPanel" class="info-panel" style="display:none"></div>
    </div>
    <script>
      (function() {{
        const root = document.getElementById('root');
        const hdrMain = document.getElementById('hdrMain');
        const hdrSub = document.getElementById('hdrSub');
        const stage = document.getElementById('stage');
        const hintEl = document.getElementById('hint');
        const infoPanel = document.getElementById('infoPanel');
        const wsUrl = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws';
        let ws = null, tries = 0;
        let cfg = null, phase = 'idle', fighters = [], timerRemaining = 0, countdownRemaining = 0;
        let lastHit = null, lastAttack = null, fxSeq = 0, lastFxSeq = 0, winner = null, autoArmCandidates = 0;

        function fmtTime(sec) {{
          const s = Math.max(0, sec|0);
          const m = Math.floor(s / 60);
          const r = s % 60;
          return (m < 10 ? '0' : '') + m + ':' + (r < 10 ? '0' : '') + r;
        }}
        function fmtNum(n) {{
          const x = n|0;
          if (x >= 1000) return (x/1000).toFixed(1).replace(/\\.0$/, '') + 'K';
          return String(x);
        }}
        function nickAt(f) {{
          const u = String(f.user || '?').trim();
          return u.startsWith('@') ? u : ('@' + u);
        }}
        function duelPower() {{
          if (fighters.length < 2) return 0.5;
          const a = fighters[0].session_donated|0;
          const b = fighters[1].session_donated|0;
          const tot = a + b;
          if (tot > 0) return a / tot;
          const hpA = Math.max(0, fighters[0].hp|0);
          const hpB = Math.max(0, fighters[1].hp|0);
          return hpA / Math.max(1, hpA + hpB);
        }}
        function animOn(k) {{ return !cfg || cfg[k] !== false; }}
        function L() {{
          const uk = String((cfg && cfg.ui_locale) || 'uk') !== 'en';
          return uk ? {{
            sub: 'ДУЕЛЬ ДОНАТЕРІВ',
            support: 'ПІДТРИМКА',
            challenger1: 'БОЄЦЬ 1',
            challenger2: 'БОЄЦЬ 2',
            donated: 'ДОНАТ',
            wins: 'Перемоги',
            rank: 'Ранг',
            lastAttack: 'ОСТАННЯ АТАКА: ',
            duelLive: 'ДУЕЛЬ ТРИВАЄ',
            fight: 'БІЙ!',
            koWins: (nick) => 'K.O. — перемагає ' + nick,
            waiting: (thr) => '\\u26A1 Очікування дуелі: 2 різні глядачі \\u2265 ' + thr + ' \\uD83D\\uDC8E',
            pressStart: 'Натисніть «Старт» у Віджетах Cheremsha',
          }} : {{
            sub: 'THE DONOR DUEL',
            support: 'SUPPORT',
            challenger1: 'CHALLENGER 1',
            challenger2: 'CHALLENGER 2',
            donated: 'DONATED',
            wins: 'Wins',
            rank: 'Rank',
            lastAttack: 'LAST ATTACK: ',
            duelLive: 'DUEL LIVE',
            fight: 'FIGHT!',
            koWins: (nick) => 'K.O. — ' + nick + ' WINS',
            waiting: (thr) => '\\u26A1 Waiting for a duel: 2 different viewers \\u2265 ' + thr + ' \\uD83D\\uDC8E',
            pressStart: 'Press "Start" in Cheremsha Widgets',
          }};
        }}
        function sfxVol() {{
          return cfg && cfg.sfx_volume_pct != null ? Math.max(0, Math.min(1, cfg.sfx_volume_pct/100)) : 0.8;
        }}
        function nclamp(v, lo, hi, def) {{
          let x = parseInt(v, 10);
          if (Number.isNaN(x)) x = def;
          return Math.max(lo, Math.min(hi, x));
        }}
        function playTone(freq, dur) {{
          try {{
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const o = ctx.createOscillator();
            const g = ctx.createGain();
            o.frequency.value = freq;
            g.gain.value = sfxVol() * 0.14;
            o.connect(g); g.connect(ctx.destination);
            o.start();
            setTimeout(() => {{ o.stop(); ctx.close(); }}, dur);
          }} catch (e) {{}}
        }}
        function baseFontPx() {{
          if (!cfg) return 14;
          if (cfg.base_font_size_px != null)
            return nclamp(cfg.base_font_size_px, 10, 32, 14);
          const pct = nclamp(cfg.text_scale_pct, 70, 160, 100);
          return nclamp(Math.round(14 * pct / 100), 10, 32, 14);
        }}
        function widgetScale() {{
          return nclamp(cfg && cfg.scale_percent, 40, 250, 100) / 100;
        }}
         function applyCfg() {{
           if (!cfg) return;
           const px = baseFontPx();
           const scale = widgetScale();
           const speed = nclamp(cfg.anim_intensity_pct, 25, 200, 100) / 100;
           const preset = String(cfg.preset || 'arcade_royale').toLowerCase();
           const presetClass = preset === 'cyber_arena' ? 'preset-cyber'
             : preset === 'dark_fight' ? 'preset-dark'
             : preset === 'minimal_brawl' ? 'preset-minimal' : 'preset-arcade';
           document.documentElement.style.fontSize = (px * scale) + 'px';
           root.style.fontSize = (px * scale) + 'px';
           root.style.setProperty('--bfont', cfg.font_family || 'Rajdhani, system-ui');
           root.style.setProperty('--br-widget-scale', String(scale));
           root.style.setProperty('--anim-speed', String(speed));
           root.classList.remove('preset-arcade', 'preset-cyber', 'preset-dark', 'preset-minimal');
           root.classList.add(presetClass);
           if (cfg.anim_projectile === false) root.classList.add('projectile-off');
           else root.classList.remove('projectile-off');
           if (cfg.anim_fatality === false) root.classList.add('fatality-off');
           else root.classList.remove('fatality-off');
           hdrMain.textContent = String(cfg.title_text || 'BATTLE ROYALE').toUpperCase();
           hdrSub.textContent = L().sub;
         }}
        function escAttr(s) {{
          return String(s || '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
        }}
        function buildGiftIcons(gifts) {{
          if (!gifts || !gifts.length) return '';
          let icons = '';
          for (let i = 0; i < gifts.length; i++) {{
            const g = gifts[i];
            const url = String(g.image_url || '').trim();
            if (!url) continue;
            const title = escAttr(g.name || '');
            icons += '<img class="gift-icon" referrerpolicy="no-referrer" src="' + escAttr(url)
              + '" title="' + title + '" alt="" />';
          }}
          if (!icons) return '';
          return '<div class="support-gifts"><div class="support-label">' + L().support + '</div>'
            + '<div class="gift-row">' + icons + '</div></div>';
        }}
        function buildCard(f, side, label, avSize) {{
          const pct = Math.max(0, Math.min(100, Math.round((f.hp|0) * 100 / Math.max(1, f.max_hp|0))));
          const ko = (f.hp|0) <= 0;
          const wins = f.wins|0;
          const rank = f.rank|0;
          const rankTxt = rank > 0 ? String(rank) : '\\u2014';
          const giftsHtml = buildGiftIcons(f.support_gifts);
          return ''
            + '<div class="card ' + side + (ko ? ' ko' : '') + '" data-side="' + side + '">'
            + '<div class="ch-label">' + label + '</div>'
            + '<div class="av-wrap"><img class="avatar" width="' + avSize + '" height="' + avSize + '" '
            + 'referrerpolicy="no-referrer" src="' + (f.avatar_url || '') + '" alt="" /></div>'
            + '<div class="nick">' + nickAt(f) + '</div>'
            + '<div class="hp-label">HP: ' + (f.hp|0) + '/' + (f.max_hp|0) + '</div>'
            + '<div class="hp-wrap"><div class="hp-fill" style="width:' + pct + '%"></div></div>'
            + giftsHtml
            + '<div class="donated">' + L().donated + ': ' + fmtNum(f.session_donated|0) + ' \\uD83D\\uDC8E</div>'
            + '<div class="card-foot">'
            + '<span>\\uD83C\\uDFC6 ' + wins + '</span>'
            + '<span>' + L().rank + ': ' + rankTxt + '</span>'
            + '</div></div>';
        }}
        function spawnDmgPop(dmg) {{
          if (!dmg || dmg <= 0) return;
          const el = document.createElement('div');
          el.className = 'dmg-pop';
          el.textContent = '-' + dmg + ' HP';
          const clash = stage.querySelector('.clash');
          if (clash) clash.appendChild(el);
          else stage.appendChild(el);
          setTimeout(() => {{ try {{ el.remove(); }} catch (e) {{}} }}, 1100);
        }}
        function renderInfoPanel() {{
          if (fighters.length < 2) {{
            infoPanel.style.display = 'none';
            return;
          }}
          infoPanel.style.display = 'block';
          let html = '';
          if (lastAttack && lastAttack.damage > 0) {{
            html += '<div class="row"><span class="label">' + L().lastAttack + '</span>'
              + '<span class="val">' + nickAt({{user: lastAttack.attacker}}) + ' (' + (lastAttack.amount|0) + ' \\uD83D\\uDC8E)</span></div>';
            html += '<div class="row"><span class="label"></span>'
              + '<span class="dmg">' + nickAt({{user: lastAttack.target}}) + ': -' + (lastAttack.damage|0) + ' HP</span></div>';
          }} else {{
         html += '<div class="row"><span class="label">' + L().duelLive + '</span></div>';
           }}
           for (let i = 0; i < fighters.length; i++) {{
             html += '<div class="row"><span class="label">' + nickAt(fighters[i]) + ' </span>'
               + '<span class="val">' + L().wins + ' ' + (fighters[i].wins|0) + ' \\u2022 ' + L().rank + ' ' + ((fighters[i].rank|0) || '\\u2014') + '</span></div>';
           }}
           infoPanel.innerHTML = html;
         }}
         function renderDuel() {{
           const avSize = Math.round((cfg && cfg.avatar_size_px ? cfg.avatar_size_px : 100) * widgetScale());
           if (fighters.length > 2) {{
             stage.classList.add('multi');
             let html = '';
             for (let i = 0; i < fighters.length; i++) {{
               const side = String(fighters[i].side || ('slot' + i));
               const label = i === 0 ? L().challenger1 : i === 1 ? L().challenger2 : ('FIGHTER ' + (i + 1));
               html += buildCard(fighters[i], side, label, avSize);
             }}
             html += '<div class="center multi-center">';
             if (phase === 'active' || phase === 'victory')
               html += '<div class="timer">' + fmtTime(timerRemaining) + '</div>';
             html += '<div class="clash"><div class="clash-core"></div></div></div>';
             stage.innerHTML = html;
           }} else {{
             stage.classList.remove('multi');
           const power = duelPower();
           const leftW = Math.round(power * 100);
           const rightW = 100 - leftW;
          const beamScaleL = 0.45 + power * 0.55;
          const beamScaleR = 0.45 + (1 - power) * 0.55;

          let html = buildCard(fighters[0], 'left', L().challenger1, avSize);
          html += '<div class="center">';
          if (phase === 'active' || phase === 'victory') {{
            html += '<div class="timer">' + fmtTime(timerRemaining) + '</div>';
          }}
          html += '<div class="clash">'
            + '<div class="beam beam-left" style="width:' + Math.round(38 * beamScaleL) + '%"></div>'
            + '<div class="beam beam-right" style="width:' + Math.round(38 * beamScaleR) + '%"></div>'
            + '<div class="clash-core"></div>'
            + '</div>'
            + '<div class="tug"><div class="tug-fill" style="width:' + leftW + '%"></div></div>'
            + '</div>';
           html += buildCard(fighters[1], 'right', L().challenger2, avSize);
           stage.innerHTML = html;
           }}
           stage.querySelectorAll('.avatar').forEach(img => {{
            img.onerror = () => {{ img.style.visibility = 'hidden'; }};
          }});
          renderInfoPanel();
        }}
        function hideWhenIdle() {{
          return phase === 'idle' && cfg && cfg.hide_when_idle !== false;
        }}
        function render() {{
          applyCfg();
          root.querySelectorAll('.countdown-overlay,.victory-banner,.dmg-pop').forEach(el => el.remove());

          if (phase === 'idle') {{
            if (hideWhenIdle()) {{
              root.classList.add('idle-empty');
              stage.style.display = 'none';
              infoPanel.style.display = 'none';
              hintEl.style.display = 'none';
              return;
            }}
            root.classList.remove('idle-empty');
            stage.style.display = 'none';
            infoPanel.style.display = 'none';
            hintEl.style.display = 'block';
            const thr = cfg && cfg.auto_threshold_each != null ? cfg.auto_threshold_each : 100;
            const autoOn = !cfg || cfg.auto_arm_enabled !== false;
            let t = autoOn ? L().waiting(thr) : L().pressStart;
            if (autoOn && autoArmCandidates === 1) t += ' (1/2)';
            hintEl.textContent = t;
            return;
          }}

          root.classList.remove('idle-empty');
          hintEl.style.display = 'none';
          if (phase === 'countdown') {{
            stage.style.display = 'none';
            infoPanel.style.display = 'none';
            const co = document.createElement('div');
            co.className = 'countdown-overlay';
            co.textContent = countdownRemaining > 0 ? String(countdownRemaining) : L().fight;
            root.appendChild(co);
            return;
          }}

          if (fighters.length >= 2) {{
            stage.style.display = 'flex';
            renderDuel();
            if (lastHit && fxSeq !== lastFxSeq) {{
              lastFxSeq = fxSeq;
              const toIdx = lastHit.to >= 0 ? lastHit.to : 0;
              const cards = stage.querySelectorAll('.card');
              const toCard = cards[toIdx];
              if (lastHit.damage > 0 && animOn('anim_shake') && toCard) toCard.classList.add('shake');
              if (lastHit.crit && animOn('anim_crit_flash')) {{
                root.classList.add('crit-flash');
                setTimeout(() => root.classList.remove('crit-flash'), 420);
                playTone(880, 90);
              }} else if (lastHit.damage > 0) playTone(240, 55);
              if (lastHit.damage > 0) spawnDmgPop(lastHit.damage);
            }}
          }} else {{
            stage.style.display = 'none';
          }}

          if (phase === 'victory' && winner) {{
            const vb = document.createElement('div');
            vb.className = 'victory-banner';
            vb.textContent = L().koWins(nickAt(winner));
            root.appendChild(vb);
            playTone(440, 130);
          }}
        }}

        function applyPatch(p) {{
          if (!p) return;
          if (p.config) {{
            cfg = Object.assign({{}}, cfg || {{}}, p.config);
            applyCfg();
          }}
          if (p.phase !== undefined) phase = String(p.phase);
          if (p.fighters !== undefined) fighters = p.fighters || [];
          if (p.timer_remaining_s !== undefined) timerRemaining = p.timer_remaining_s|0;
          if (p.countdown_remaining_s !== undefined) countdownRemaining = p.countdown_remaining_s|0;
          if (p.last_hit !== undefined) lastHit = p.last_hit;
          if (p.last_attack !== undefined) lastAttack = p.last_attack;
          if (p.fx_seq !== undefined) fxSeq = p.fx_seq|0;
          if (p.winner !== undefined) winner = p.winner;
          if (p.auto_arm_candidates !== undefined) autoArmCandidates = p.auto_arm_candidates|0;
        }}

        function handleMsg(data) {{
          if (!data || !data.op) return;
          if (data.op === 'initial_state') {{
            cfg = (data.state && data.state.config) || null;
            applyPatch(data.state || {{}});
            render();
            return;
          }}
          if (data.op === 'patch') {{
            applyPatch(data.patch || {{}});
            render();
          }}
        }}

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
        _ = normalize_instance_id(str(params.get("instance") or ""))
        from stream_cheremsha.overlays.widget_instances import typed_config_for_type

        cfg = typed_config_for_type(
            "battle_royale",
            params,
            load_battle_royale_overlay_config,
            battle_royale_overlay_config_from_json_text,
        )
        cfg_payload = json.loads(battle_royale_overlay_config_to_json_text(cfg))
        cfg_payload["ui_locale"] = load_ui_locale()
        return {
            "config": cfg_payload,
            "phase": "idle",
            "fighters": [],
            "timer_remaining_s": 0,
            "countdown_remaining_s": 0,
            "last_hit": None,
            "last_attack": None,
            "fx_seq": 0,
            "winner": None,
            "auto_arm_candidates": 0,
        }
