from __future__ import annotations

# ruff: noqa: E501
import json
from typing import Any

from stream_cheremsha.overlays.king_of_live_overlay_config import (
    king_of_live_overlay_config_to_json_text,
    load_king_of_live_overlay_config,
)
from stream_cheremsha.overlays.models import normalize_instance_id
from stream_cheremsha.persistence.tiktok_gifts_sqlite import fetch_all_time_gifter_totals


def _json_for_script(value: Any) -> str:
    s = json.dumps(value, ensure_ascii=False)
    return s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


class KingOfLiveOverlayType:
    type = "king_of_live"

    def render_html(self, params: dict[str, Any]) -> str:
        raw_instance = params.get("instance")
        try:
            instance = normalize_instance_id(str(raw_instance or ""))
        except ValueError:
            instance = "default"

        subscribe_msg = {
            "op": "subscribe",
            "type": "king_of_live",
            "instance": instance,
            "params": {},
        }

        return f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>King of the Live</title>
    <style>
      html, body {{ margin:0; padding:0; background:transparent; overflow:hidden; height:100%; }}
      * {{ box-sizing:border-box; }}
      .root {{
        position:absolute; inset:0;
        font-family: var(--kfont, system-ui, sans-serif);
        display:flex; align-items:center; justify-content:center;
        pointer-events:none;
      }}
      .root.presence .halo {{ opacity: 0.95; filter: brightness(1.35) saturate(1.2); }}
      .root.chatflash .frame {{ animation: frameFlash calc(0.9s / var(--anim-int, 1)) ease-out; }}
      .root.throne-danger .frame {{ animation: dangerPulse 1.1s ease-in-out infinite; box-shadow: 0 0 28px rgba(220,38,38,0.55); }}
      .root.throne-danger .nick {{ color: #fecaca !important; text-shadow: 0 0 12px rgba(239,68,68,0.7); }}
      @keyframes frameFlash {{
        0% {{ filter: brightness(2); }}
        100% {{ filter: brightness(1); }}
      }}
      @keyframes dangerPulse {{
        0%,100% {{ box-shadow: 0 0 18px rgba(220,38,38,0.35); }}
        50% {{ box-shadow: 0 0 36px rgba(239,68,68,0.75); }}
      }}
      .rays {{
        position:absolute; inset:-28%;
        background: conic-gradient(from 0deg, transparent 0deg, rgba(255,215,0,0.38) 22deg, transparent 52deg,
          transparent 118deg, rgba(255,200,80,0.32) 148deg, transparent 188deg,
          transparent 240deg, rgba(255,235,160,0.22) 268deg, transparent 310deg);
        animation: none;
        opacity: 0.72;
        pointer-events:none;
        mix-blend-mode: screen;
      }}
      .preset-cyber .rays {{
        background: conic-gradient(from 0deg, transparent 0deg, rgba(56,189,248,0.42) 22deg, transparent 52deg,
          transparent 118deg, rgba(147,197,253,0.34) 148deg, transparent 188deg,
          transparent 240deg, rgba(125,211,252,0.26) 268deg, transparent 310deg);
      }}
      .preset-dark .rays {{
        background: conic-gradient(from 0deg, transparent 0deg, rgba(248,113,113,0.4) 22deg, transparent 52deg,
          transparent 118deg, rgba(251,191,36,0.32) 148deg, transparent 188deg,
          transparent 240deg, rgba(252,165,165,0.24) 268deg, transparent 310deg);
      }}
      .preset-minimal .rays {{
        mix-blend-mode: normal;
        background: conic-gradient(from 0deg, transparent 0deg, rgba(250,250,250,0.2) 22deg, transparent 52deg,
          transparent 118deg, rgba(212,175,55,0.22) 148deg, transparent 188deg);
      }}
      .root.anim-rays .rays {{ animation: spinRays calc(22s / var(--anim-int, 1)) linear infinite; }}
      @keyframes spinRays {{ to {{ transform: rotate(360deg); }} }}
      .coins {{
        position:absolute; left:0; right:0; bottom:0; height:38%;
        overflow:hidden; pointer-events:none; opacity:0.55;
      }}
      .root:not(.anim-coins) .coins {{ display: none; }}
      .coin {{
        position:absolute; bottom:-12px; width:7px; height:7px; border-radius:999px;
        background: radial-gradient(circle at 30% 30%, #fff6bf, #d4af37 55%, #7a5c1a);
        animation: none;
      }}
      .root.anim-coins .coin {{ animation: fall linear infinite; }}
      @keyframes fall {{
        to {{ transform: translateY(-120vh) rotate(720deg); opacity: 0.15; }}
      }}
      .halo {{
        position:relative; padding: 18px 22px 14px;
        border-radius: 20px;
        transition: filter 0.6s ease, opacity 0.6s ease;
      }}
      .blur-bubble {{
        position:absolute; left:50%; top: 50%;
        width: min(96vw, 360px); height: min(78vh, 400px);
        transform: translate(-50%, -50%);
        border-radius: 46%;
        z-index: 0;
        pointer-events:none;
        background: rgba(0,0,0,0.04);
      }}
      .preset-imperial .halo {{
        background: radial-gradient(ellipse at 50% 0%, rgba(88,28,135,0.25), transparent 55%),
          linear-gradient(165deg, rgba(20,12,8,0.55), rgba(8,6,4,0.35));
      }}
      .preset-cyber .halo {{
        background: radial-gradient(ellipse at 50% 0%, rgba(56,189,248,0.2), transparent 50%),
          linear-gradient(165deg, rgba(10,8,30,0.65), rgba(4,2,20,0.4));
      }}
      .preset-dark .halo {{
        background: radial-gradient(ellipse at 50% 0%, rgba(220,38,38,0.22), transparent 50%),
          linear-gradient(165deg, rgba(8,4,4,0.75), rgba(2,0,0,0.5));
      }}
      .preset-minimal .halo {{
        background: linear-gradient(180deg, rgba(12,12,14,0.35), rgba(12,12,14,0.15));
      }}
      .title {{
        text-align:center; font-weight:900; letter-spacing:0.12em; font-size: calc(11px * var(--txt-scale, 1));
        margin-bottom:8px; text-transform:uppercase;
        opacity:0.92;
        animation: none;
      }}
      .root.anim-title .title {{ animation: titleShimmer calc(5s / var(--anim-int, 1)) ease-in-out infinite; }}
      @keyframes titleShimmer {{
        0%,100% {{ opacity: 0.88; filter: brightness(1); letter-spacing: 0.12em; }}
        50% {{ opacity: 1; filter: brightness(1.15); letter-spacing: 0.14em; }}
      }}
      .preset-imperial .title {{ color:#fde68a; text-shadow: 0 0 18px rgba(250,204,21,0.45); }}
      .preset-cyber .title {{ color:#7dd3fc; text-shadow: 0 0 16px rgba(56,189,248,0.55); }}
      .preset-dark .title {{ color:#fca5a5; text-shadow: 0 0 14px rgba(239,68,68,0.45); }}
      .preset-minimal .title {{ color:#e7e5e4; letter-spacing:0.18em; font-weight:700; }}
      .stage {{ display:flex; flex-direction:column; align-items:center; gap:6px; position:relative; z-index:2; }}
      .crown-wrap {{
        position:relative; height: calc(34px * var(--txt-scale, 1)); display:flex; align-items:flex-end; justify-content:center;
        margin-bottom:-6px; z-index:4;
      }}
      .crown {{
        font-size: calc(30px * var(--txt-scale, 1)); line-height:1; filter: drop-shadow(0 3px 6px rgba(0,0,0,0.55));
        transform-origin: 50% 100%;
        animation: none;
      }}
      .root.anim-crown .crown:not(.burst) {{ animation: crownFloat calc(3.2s / var(--anim-int, 1)) ease-in-out infinite; }}
      .crown.burst {{ animation: crownPop calc(0.85s / var(--anim-int, 1)) ease forwards; }}
      @keyframes crownFloat {{
        0%,100% {{ transform: translateY(0) rotate(calc(-2deg * var(--anim-amp, 1))) scale(1); }}
        50% {{ transform: translateY(calc(-5px * var(--anim-amp, 1))) rotate(calc(2deg * var(--anim-amp, 1))) scale(calc(1 + 0.04 * (var(--anim-amp, 1) - 1))); }}
      }}
      @keyframes crownPop {{
        0% {{ transform: scale(1) rotate(0); opacity:1; }}
        40% {{ transform: scale(calc(1.35 + 0.1 * (var(--anim-amp, 1) - 1))) rotate(calc(8deg * var(--anim-amp, 1))); opacity:0.2; }}
        100% {{ transform: scale(1) rotate(0); opacity:1; }}
      }}
      .frame {{
        position:relative; border-radius: 999px;
        padding: 5px;
        transition: box-shadow 0.4s ease;
      }}
      .preset-imperial .frame {{
        background: linear-gradient(145deg, #f5d889, #b8860b 40%, #6b4f1a 70%, #f8e6a8);
        box-shadow: 0 0 0 2px rgba(60,40,10,0.65), 0 12px 40px rgba(0,0,0,0.45), inset 0 0 12px rgba(255,255,255,0.35);
      }}
      .preset-cyber .frame {{
        background: linear-gradient(145deg, #22d3ee, #6366f1 45%, #a855f7 75%, #38bdf8);
        box-shadow: 0 0 0 2px rgba(30,64,175,0.5), 0 0 24px rgba(99,102,241,0.45), 0 10px 36px rgba(0,0,0,0.5);
      }}
      .preset-dark .frame {{
        background: linear-gradient(145deg, #44403c, #1c1917 50%, #7f1d1d 80%, #ca8a04);
        box-shadow: 0 0 0 2px rgba(127,29,29,0.55), 0 0 26px rgba(220,38,38,0.35), 0 12px 40px rgba(0,0,0,0.6);
      }}
      .preset-minimal .frame {{
        background: linear-gradient(145deg, rgba(212,175,55,0.55), rgba(212,175,55,0.15));
        box-shadow: 0 0 0 1px rgba(212,175,55,0.55), 0 8px 24px rgba(0,0,0,0.25);
      }}
      .avatar {{
        display:block; border-radius:999px; object-fit:cover;
        background: rgba(0,0,0,0.35);
        box-shadow: inset 0 0 18px rgba(0,0,0,0.35);
        animation: none;
      }}
      .root.anim-avatar .avatar {{ animation: avatarBob calc(3.8s / var(--anim-int, 1)) ease-in-out infinite; }}
      @keyframes avatarBob {{
        0%,100% {{ transform: translateY(0) scale(1); }}
        50% {{ transform: translateY(calc(-3px * var(--anim-amp, 1))) scale(calc(1 + 0.02 * var(--anim-amp, 1))); }}
      }}
      .nick {{
        max-width: 92vw; font-weight: 800; font-size: calc((13px + 0.35vw) * var(--txt-scale, 1));
        white-space:nowrap; overflow:hidden; text-overflow:ellipsis; text-align:center;
        margin-top: 4px;
      }}
      .preset-imperial .nick {{ color:#fffbeb; text-shadow: 0 2px 8px rgba(0,0,0,0.65); }}
      .preset-cyber .nick {{ color:#e0f2fe; text-shadow: 0 0 10px rgba(56,189,248,0.5); }}
      .preset-dark .nick {{ color:#fef2f2; text-shadow: 0 0 10px rgba(248,113,113,0.45); }}
      .preset-minimal .nick {{ color:#fafaf9; }}
      .gems {{
        font-weight:800; font-variant-numeric: tabular-nums; letter-spacing:0.04em;
        font-size: calc((15px + 0.4vw) * var(--txt-scale, 1)); display:flex; align-items:center; gap:6px;
        margin-top:2px;
      }}
      .preset-imperial .gems {{ color:#fef08a; text-shadow: 0 0 14px rgba(234,179,8,0.45); }}
      .preset-cyber .gems {{ color:#c4b5fd; text-shadow: 0 0 12px rgba(168,85,247,0.45); }}
      .preset-dark .gems {{ color:#fcd34d; text-shadow: 0 0 12px rgba(251,191,36,0.4); }}
      .preset-minimal .gems {{ color:#fde047; }}
      .gems .pulse {{
        animation: gemPulse calc(2.4s / var(--anim-int, 1)) ease-in-out infinite;
      }}
      .gems span:not(.pulse) {{
        animation: none;
      }}
      @keyframes gemPulse {{
        0%,100% {{ opacity:0.9; transform: scale(1); }}
        50% {{ opacity:1; transform: scale(calc(1 + 0.04 * var(--anim-amp, 1))); }}
      }}
      .gapstrip {{
        margin-top: 8px; padding: 6px 10px; border-radius: 10px;
        font-size: calc(12px * var(--txt-scale, 1)); font-weight: 700; text-align:center; max-width: 92vw;
        background: rgba(0,0,0,0.35); border: 1px solid rgba(255,255,255,0.12);
        color: #e7e5e4;
      }}
      .bar-wrap {{ width: min(280px, 88vw); height: 8px; border-radius: 999px; overflow:hidden;
        margin-top:6px; background: rgba(0,0,0,0.35); border:1px solid rgba(255,255,255,0.12); }}
      .bar {{ height:100%; border-radius:999px; width:0%; transition: width 0.35s ease, background 0.35s ease; }}
      .preset-imperial .bar {{ background: linear-gradient(90deg,#facc15,#f59e0b); }}
      .preset-cyber .bar {{ background: linear-gradient(90deg,#22d3ee,#a855f7); }}
      .preset-dark .bar {{ background: linear-gradient(90deg,#ef4444,#f97316); }}
      .preset-minimal .bar {{ background: linear-gradient(90deg,#eab308,#ca8a04); }}
      .empty {{
        color: rgba(255,255,255,0.55); font-weight:600; font-size: calc(14px * var(--txt-scale, 1)); text-align:center; padding: 20px;
        position:relative; z-index:1;
      }}
      .firework {{
        position:absolute; width:10px; height:10px; border-radius:2px;
        animation: fw 0.9s ease-out forwards; pointer-events:none; z-index: 6;
      }}
      @keyframes fw {{
        0% {{ transform: scale(0.2) translate(0,0); opacity:1; }}
        100% {{ transform: scale(1) translate(var(--dx), var(--dy)); opacity:0; }}
      }}
    </style>
  </head>
  <body>
    <div id="app" class="root preset-imperial"></div>
    <script>
      (function() {{
        const wsUrl = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws';
        let ws = null;
        let tries = 0;
        let cfg = null;
        let king = null;
        let gapDiamonds = 0;
        let runnerUpUser = '';
        let challenger = null;
        let throneDanger = false;
        let kingRevision = 0;
        let presenceSeq = 0;
        let chatSeq = 0;
        let lastPresenceSeq = 0;
        let lastChatSeq = 0;
        let lastKingKey = '';

        const app = document.getElementById('app');

        function animCfg(k) {{
          if (!cfg) return true;
          const v = cfg[k];
          if (v === false || v === 0 || v === '0') return false;
          return true;
        }}

        function animClassSuffix() {{
          let s = '';
          if (animCfg('anim_crown_float')) s += ' anim-crown';
          if (animCfg('anim_avatar_motion')) s += ' anim-avatar';
          if (animCfg('anim_rays_spin')) s += ' anim-rays';
          if (animCfg('anim_coins_fall')) s += ' anim-coins';
          if (animCfg('anim_title_shimmer')) s += ' anim-title';
          return s;
        }}

        function nclamp(v, lo, hi, def) {{
          let x = parseInt(v, 10);
          if (Number.isNaN(x)) x = def;
          return Math.max(lo, Math.min(hi, x));
        }}

        function animMul() {{
          if (!cfg) return 1;
          return Math.max(0.25, Math.min(2.25, nclamp(cfg.anim_intensity_pct, 25, 200, 100) / 100));
        }}

        function maybeAppendBlurBubble(halo) {{
          if (!cfg || !halo) return;
          const bbpx = nclamp(cfg.backdrop_bubble_blur_px, 0, 48, 0);
          if (bbpx <= 0) return;
          const bub = document.createElement('div');
          bub.className = 'blur-bubble';
          halo.appendChild(bub);
        }}

        function applyRootShell() {{
          if (!cfg) return;
          const pf = String(cfg.font_family || 'Segoe UI').replace(/[\"<>]/g, '');
          app.style.setProperty('--kfont', pf + ', system-ui, sans-serif');
          const txtScale = nclamp(cfg.text_scale_pct, 70, 160, 100) / 100;
          const aim = animMul();
          app.style.setProperty('--txt-scale', String(txtScale));
          app.style.setProperty('--anim-int', String(aim));
          app.style.setProperty('--anim-amp', String(aim));
          let cls = 'root ' + presetClass(cfg.preset) + animClassSuffix();
          if (throneDanger) cls += ' throne-danger';
          app.className = cls;
          let bpx = parseInt(cfg.backdrop_blur_px, 10);
          if (Number.isNaN(bpx)) bpx = 0;
          bpx = Math.max(0, Math.min(48, bpx));
          const halos = app.querySelectorAll('.halo');
          for (let i = 0; i < halos.length; i++) {{
            const h = halos[i];
            if (bpx <= 0) {{
              h.style.backdropFilter = '';
              h.style.webkitBackdropFilter = '';
            }} else {{
              const b = 'blur(' + bpx + 'px)';
              h.style.backdropFilter = b;
              h.style.webkitBackdropFilter = b;
            }}
          }}
          let bbpx = nclamp(cfg.backdrop_bubble_blur_px, 0, 48, 0);
          const bubbles = app.querySelectorAll('.blur-bubble');
          for (let j = 0; j < bubbles.length; j++) {{
            const u = bubbles[j];
            if (bbpx <= 0) {{
              u.style.backdropFilter = '';
              u.style.webkitBackdropFilter = '';
            }} else {{
              const bb = 'blur(' + bbpx + 'px)';
              u.style.backdropFilter = bb;
              u.style.webkitBackdropFilter = bb;
            }}
          }}
          const ri = nclamp(cfg.rays_intensity_pct, 40, 200, 130) / 100;
          const raysNodes = app.querySelectorAll('.rays');
          for (let k = 0; k < raysNodes.length; k++) {{
            const r = raysNodes[k];
            const op = Math.min(1, 0.34 + 0.58 * ri);
            r.style.opacity = op.toFixed(3);
            const br = 0.78 + 0.48 * ri;
            const sat = 0.82 + 0.52 * ri;
            r.style.filter = 'brightness(' + br.toFixed(2) + ') saturate(' + sat.toFixed(2) + ')';
          }}
        }}

        function fmtDiamonds(n) {{
          const x = Math.max(0, Number(n) || 0);
          if (x >= 1_000_000) return (x / 1_000_000).toFixed(x % 1_000_000 === 0 ? 0 : 1).replace(/\\.0$/, '') + 'M';
          if (x >= 1_000) return (x / 1_000).toFixed(x % 1_000 === 0 ? 0 : 1).replace(/\\.0$/, '') + 'K';
          return String(x);
        }}

        function presetClass(p) {{
          const v = String(p || 'imperial_gold').toLowerCase();
          if (v === 'cyber_king') return 'preset-cyber';
          if (v === 'dark_overlord') return 'preset-dark';
          if (v === 'minimalist') return 'preset-minimal';
          return 'preset-imperial';
        }}

        function spawnFireworks() {{
          const rect = app.getBoundingClientRect();
          const cx = rect.width * 0.5;
          const cy = rect.height * 0.35;
          const colors = ['#facc15','#f97316','#fb7185','#38bdf8','#a78bfa','#34d399'];
          for (let i = 0; i < 18; i++) {{
            const el = document.createElement('div');
            el.className = 'firework';
            const ang = (Math.PI * 2 * i) / 18;
            const dist = 40 + Math.random() * 70;
            el.style.left = (cx + Math.cos(ang) * 20) + 'px';
            el.style.top = (cy + Math.sin(ang) * 10) + 'px';
            el.style.background = colors[i % colors.length];
            el.style.setProperty('--dx', (Math.cos(ang) * dist).toFixed(1) + 'px');
            el.style.setProperty('--dy', (Math.sin(ang) * dist * 0.6).toFixed(1) + 'px');
            app.appendChild(el);
            setTimeout(function() {{ try {{ el.remove(); }} catch (e) {{}} }}, 950);
          }}
        }}

        function ensureCoins() {{
          if (app.querySelector('.coins')) return;
          const wrap = document.createElement('div');
          wrap.className = 'coins';
          const m = animMul();
          for (let i = 0; i < 26; i++) {{
            const c = document.createElement('div');
            c.className = 'coin';
            c.style.left = (Math.random() * 100).toFixed(2) + '%';
            c.style.animationDuration = ((4 + Math.random() * 6) / m).toFixed(2) + 's';
            c.style.animationDelay = (-Math.random() * 8).toFixed(2) + 's';
            wrap.appendChild(c);
          }}
          app.insertBefore(wrap, app.firstChild);
        }}

        function applyEphemeralFx(bumpPresence, bumpChat) {{
          if (bumpPresence) {{
            app.classList.add('presence');
            if (animCfg('anim_fireworks_on_presence')) spawnFireworks();
            setTimeout(function() {{ app.classList.remove('presence'); }}, 2400);
          }}
          if (bumpChat) {{
            app.classList.add('chatflash');
            setTimeout(function() {{ app.classList.remove('chatflash'); }}, 900);
          }}
        }}

        function render() {{
          if (!cfg) return;
          const bumpPresence = presenceSeq > lastPresenceSeq;
          const bumpChat = chatSeq > lastChatSeq;
          if (bumpPresence) lastPresenceSeq = presenceSeq;
          if (bumpChat) lastChatSeq = chatSeq;

          const avSize = Math.max(64, Math.min(220, parseInt(cfg.avatar_size_px, 10) || 120));

          if (!king || !king.user) {{
            app.innerHTML = '';
            const r = document.createElement('div'); r.className='rays'; app.appendChild(r);
            if (animCfg('anim_coins_fall')) ensureCoins();
            const haloE = document.createElement('div'); haloE.className='halo';
            maybeAppendBlurBubble(haloE);
            const e = document.createElement('div'); e.className='empty'; e.textContent = 'Ще немає короля подарунків';
            haloE.appendChild(e);
            app.appendChild(haloE);
            applyRootShell();
            applyEphemeralFx(bumpPresence, bumpChat);
            return;
          }}

          const kKey = king && king.key ? String(king.key) : '';
          const burst = !!(lastKingKey && kKey && kKey !== lastKingKey);
          lastKingKey = kKey || lastKingKey;

          const title = String(cfg.title_text || 'KING OF THE LIVE');
          const showGap = !!cfg.show_gap_strip;

          const ratio = challenger && king.diamonds > 0
            ? Math.min(1, Math.max(0, (challenger.coins || 0) / king.diamonds))
            : 0;
          const pct = Math.round(ratio * 1000) / 10;

          app.innerHTML = '';
          const r2 = document.createElement('div'); r2.className='rays'; app.appendChild(r2);
          if (animCfg('anim_coins_fall')) ensureCoins();

          const halo = document.createElement('div'); halo.className='halo';
          maybeAppendBlurBubble(halo);
          const stage = document.createElement('div'); stage.className='stage';

          const tEl = document.createElement('div'); tEl.className='title'; tEl.textContent = title;
          stage.appendChild(tEl);

          const cw = document.createElement('div'); cw.className='crown-wrap';
          const cr = document.createElement('div'); cr.className='crown' + (burst ? ' burst' : '');
          cr.textContent = '👑';
          cw.appendChild(cr);
          stage.appendChild(cw);

          const frame = document.createElement('div'); frame.className='frame';
          const img = document.createElement('img');
          img.className='avatar';
          img.width = avSize; img.height = avSize;
          img.alt = '';
          img.referrerPolicy = 'no-referrer';
          img.src = (king.avatar_url && String(king.avatar_url).trim()) ? king.avatar_url : '';
          img.onerror = function() {{ img.style.visibility = 'hidden'; }};
          frame.appendChild(img);
          stage.appendChild(frame);

          const nick = document.createElement('div'); nick.className='nick'; nick.textContent = king.user || '?';
          stage.appendChild(nick);

          const gems = document.createElement('div'); gems.className='gems';
          const span = document.createElement('span');
          if (animCfg('anim_gem_pulse')) span.className = 'pulse';
          span.textContent = fmtDiamonds(king.diamonds) + ' \\uD83D\\uDC8E';
          gems.appendChild(span);
          stage.appendChild(gems);

          if (showGap && gapDiamonds > 0 && runnerUpUser) {{
            const g = document.createElement('div'); g.className='gapstrip';
            g.textContent = 'До корони: ' + fmtDiamonds(gapDiamonds) + ' \\uD83D\\uDC8E (' + runnerUpUser + ')';
            stage.appendChild(g);
          }}

          if (king.diamonds > 0 && ratio > 0.05) {{
            const bw = document.createElement('div'); bw.className='bar-wrap';
            const b = document.createElement('div'); b.className='bar'; b.style.width = (ratio * 100).toFixed(1) + '%';
            bw.appendChild(b);
            stage.appendChild(bw);
            const lab = document.createElement('div'); lab.className='gapstrip';
            lab.textContent = (challenger && challenger.user ? challenger.user : 'Глядач') + ' — ' + pct + '% від рекорду';
            stage.appendChild(lab);
          }}

          halo.appendChild(stage);
          app.appendChild(halo);
          applyRootShell();
          applyEphemeralFx(bumpPresence, bumpChat);
        }}

        function applyPatch(p) {{
          if (!p) return;
          if (p.config) {{
            const incoming = p.config || {{}};
            cfg = cfg ? Object.assign({{}}, cfg, incoming) : incoming;
          }}
          if (p.king !== undefined) king = p.king;
          if (p.gap_diamonds !== undefined) gapDiamonds = p.gap_diamonds|0;
          if (p.runner_up_user !== undefined) runnerUpUser = String(p.runner_up_user||'');
          if (p.session_challenger !== undefined) challenger = p.session_challenger;
          if (p.throne_danger !== undefined) throneDanger = !!p.throne_danger;
          if (p.king_revision !== undefined) kingRevision = parseInt(p.king_revision,10)||0;
          if (p.king_presence_seq !== undefined) presenceSeq = parseInt(p.king_presence_seq,10)||0;
          if (p.chat_highlight_seq !== undefined) chatSeq = parseInt(p.chat_highlight_seq,10)||0;
        }}

        function handleMsg(data) {{
          if (!data || !data.op) return;
          if (data.op === 'initial_state') {{
            const st = data.state || {{}};
            cfg = st.config || null;
            king = st.king || null;
            gapDiamonds = st.gap_diamonds|0;
            runnerUpUser = String(st.runner_up_user||'');
            challenger = st.session_challenger || null;
            throneDanger = !!st.throne_danger;
            kingRevision = parseInt(st.king_revision,10)||0;
            presenceSeq = parseInt(st.king_presence_seq,10)||0;
            chatSeq = parseInt(st.chat_highlight_seq,10)||0;
            lastKingKey = '';
            lastPresenceSeq = 0;
            lastChatSeq = 0;
            render();
            return;
          }}
          if (data.op === 'patch') {{
            applyPatch(data.patch || {{}});
            if (cfg) render();
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
          ws.onerror = () => {{}};
        }}
        connect();
      }})();
    </script>
  </body>
</html>"""

    def initial_state(self, params: dict[str, Any]) -> dict[str, Any]:
        _ = normalize_instance_id(str(params.get("instance") or ""))
        cfg = load_king_of_live_overlay_config()
        tops = fetch_all_time_gifter_totals(limit=3)
        king = tops[0] if tops else None
        runner = tops[1] if len(tops) > 1 else None
        gap = 0
        runner_name = ""
        if king and runner and str(king.get("key")) != str(runner.get("key")):
            gap = max(0, int(king.get("diamonds") or 0) - int(runner.get("diamonds") or 0))
            runner_name = str(runner.get("user") or "")
        return {
            "config": json.loads(king_of_live_overlay_config_to_json_text(cfg)),
            "king": king,
            "gap_diamonds": gap,
            "runner_up_user": runner_name,
            "session_challenger": None,
            "throne_danger": False,
            "king_revision": 1 if king else 0,
            "king_presence_seq": 0,
            "chat_highlight_seq": 0,
        }
