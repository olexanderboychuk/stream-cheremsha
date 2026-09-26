"""``gift_rush`` overlay — a transparent, premium VFX reaction layer.

A gift flies in on a curved ``offset-path`` and bursts into coins, ribbons,
sparks, an impact ring and a ``+VALUE`` popup on every gift event. Rapid
consecutive gifts overlap and escalate into a ``COMBO`` counter. All motion
is CSS (custom properties + keyframes + ``offset-path``); JS parameterizes
each spawn and cleans up on ``animationend``. No ``requestAnimationFrame``,
no ``canvas``, no WebEngine, no per-frame timers.

The layer is **fully transparent** — it sits over the stream with only VFX
elements visible.
"""

from __future__ import annotations

import json
from typing import Any

from stream_cheremsha.overlays.models import normalize_instance_id

# ---------------------------------------------------------------------------
# The page template. Exactly one <script> block; the instance id is injected
# as a JS string literal so the subscribe message is built client-side.
# ---------------------------------------------------------------------------
_HTML_TEMPLATE = """<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Cheremsha Gift Rush</title>
  <style>
    html, body {{
      margin: 0; padding: 0;
      background: transparent;
      overflow: hidden;
      height: 100%; width: 100%;
    }}
    * {{ box-sizing: border-box; }}
    #grRoot {{
      position: relative;
      width: 100vw; height: 100vh;
      overflow: hidden;
      background: transparent;
      pointer-events: none;
    }}
    #grCam {{
      position: absolute; inset: 0;
      pointer-events: none;
    }}
    #grCam.gr-cam-hit {{ animation: grCamShake 160ms ease-out; }}
    @keyframes grCamShake {{
      0%   {{ transform: scale(1) translateX(0); }}
      35%  {{ transform: scale(1.008) translateX(-3px); }}
      70%  {{ transform: scale(1.003) translateX(3px); }}
      100% {{ transform: scale(1) translateX(0); }}
    }}
    #grLayer, #grBurst, #grPopup {{
      position: absolute; inset: 0;
      pointer-events: none;
    }}
    #grLayer { z-index: 2; }
    #grBurst { z-index: 3; }
    #grPopup { z-index: 10; }

    /* ---- themes (applied to #grRoot) ---- */
    .gr-theme-cheremsha {{
      --gr-acc1:#22d3ee; --gr-acc2:#ec4899; --gr-acc3:#a78bfa;
      --gr-glow:rgba(34,211,238,0.55); --gr-coin:#facc15; --gr-ribbon:#ec4899;
    }}
    .gr-theme-celebration {{
      --gr-acc1:#fde68a; --gr-acc2:#fbbff5; --gr-acc3:#ffffff;
      --gr-glow:rgba(253,230,130,0.55); --gr-coin:#fbbf24; --gr-ribbon:#f472b6;
    }}
    .gr-theme-arcade {{
      --gr-acc1:#4ade80; --gr-acc2:#60a5fa; --gr-acc3:#facc15;
      --gr-glow:rgba(74,222,128,0.55); --gr-coin:#facc15; --gr-ribbon:#4ade80;
    }}

    /* ---- projectile ---- */
    .gr-projectile {{
      position: absolute;
      width: calc(56px * var(--gr-scale, 1));
      height: calc(56px * var(--gr-scale, 1));
      display: flex; align-items: center; justify-content: center;
      border-radius: 50%;
      opacity: 0;
      pointer-events: none;
      z-index: 2;
      will-change: offset-distance, opacity;
      filter: drop-shadow(0 0 calc(10px * var(--gr-scale, 1)) var(--gr-glow));
    }}
    .gr-projectile .gr-gift-img, .gr-projectile svg {{
      width: 100%; height: 100%; object-fit: cover; display: block;
    }}
    .gr-projectile.is-medium {{
      width: calc(66px * var(--gr-scale, 1)); height: calc(66px * var(--gr-scale, 1));
    }}
    .gr-projectile.is-high {{
      width: calc(76px * var(--gr-scale, 1)); height: calc(76px * var(--gr-scale, 1));
      filter: drop-shadow(0 0 calc(14px * var(--gr-scale, 1)) var(--gr-glow));
    }}
    .gr-projectile.is-epic {{
      width: calc(96px * var(--gr-scale, 1)); height: calc(96px * var(--gr-scale, 1));
      filter: drop-shadow(0 0 calc(20px * var(--gr-scale, 1)) var(--gr-glow)) brightness(1.2);
    }}

    /* ---- impact ring ---- */
    .gr-ring {{
      position: absolute;
      width: calc(90px * var(--gr-scale, 1)); height: calc(90px * var(--gr-scale, 1));
      margin-left: calc(-45px * var(--gr-scale, 1));
      margin-top: calc(-45px * var(--gr-scale, 1));
      border-radius: 50%;
      border: calc(2px * var(--gr-scale, 1)) solid var(--gr-acc1);
      box-shadow: 0 0 calc(10px * var(--gr-scale, 1)) var(--gr-glow);
      opacity: 0;
      animation: grRing 0.8s ease-out forwards;
      pointer-events: none;
    }}
    @keyframes grRing {{
      0%   {{ transform: scale(0.3); opacity: 1; }}
      100% {{ transform: scale(2.4); opacity: 0; }}
    }}

    /* ---- radial glow flash ---- */
    .gr-glow {{
      position: absolute;
      width: calc(240px * var(--gr-scale, 1)); height: calc(240px * var(--gr-scale, 1));
      margin-left: calc(-120px * var(--gr-scale, 1));
      margin-top: calc(-120px * var(--gr-scale, 1));
      border-radius: 50%;
      background: radial-gradient(circle, var(--gr-glow) 0%, rgba(0,0,0,0) 60%);
      animation: grGlow 0.7s ease-out forwards;
      pointer-events: none;
    }}
    .gr-glow.is-high   {{ animation-duration: 0.75s; }}
    .gr-glow.is-epic   {{ width: calc(320px * var(--gr-scale, 1)); height: calc(320px * var(--gr-scale, 1)); margin-left: calc(-160px * var(--gr-scale, 1)); margin-top: calc(-160px * var(--gr-scale, 1)); }}
    @keyframes grGlow {{
      0%   {{ transform: scale(0.4); opacity: 0.9; }}
      100% {{ transform: scale(2.0); opacity: 0; }}
    }}

    /* ---- coin ---- */
    .gr-coin {{
      position: absolute;
      width: calc(24px * var(--gr-scale, 1)); height: calc(24px * var(--gr-scale, 1));
      margin-left: calc(-12px * var(--gr-scale, 1));
      margin-top: calc(-12px * var(--gr-scale, 1));
      animation: grCoinFly linear forwards;
      pointer-events: none;
      will-change: transform;
    }}
    .gr-coin svg {{ width: 100%; height: 100%; display: block; }}
    @keyframes grCoinFly {{
      0%   {{ transform: translate(0, 0) rotate(0deg); opacity: 1; }}
      55%  {{ transform: translate(var(--gr-mx, 40px), var(--gr-my, -40px)) rotate(360deg); opacity: 1; }}
      100% {{ transform: translate(var(--gr-dx, 80px), var(--gr-dy, 90px)) rotate(720deg) scale(0.7); opacity: 0; }}
    }}

    /* ---- ribbon / streamer ---- */
    .gr-ribbon {{
      position: absolute;
      width: calc(140px * var(--gr-scale, 1));
      height: calc(8px * var(--gr-scale, 1));
      margin-left: calc(-70px * var(--gr-scale, 1));
      margin-top: calc(-4px * var(--gr-scale, 1));
      border-radius: 999px;
      background: linear-gradient(90deg, var(--gr-ribbon), var(--gr-acc1) 55%, var(--gr-acc3));
      opacity: 0.9;
      animation: grRibbonFly linear forwards;
      pointer-events: none;
      will-change: transform;
    }}
    @keyframes grRibbonFly {{
      0%   {{ transform: translate(0, 0) rotate(var(--gr-rot, 0deg)); opacity: 0.9; }}
      60%  {{ transform: translate(var(--gr-mx, 60px), var(--gr-my, -50px)) rotate(calc(var(--gr-rot, 0deg) + 90deg)); opacity: 0.85; }}
      100% {{ transform: translate(var(--gr-dx, 120px), var(--gr-dy, 80px)) rotate(calc(var(--gr-rot, 0deg) + 240deg)); opacity: 0; }}
    }}

    /* ---- spark ---- */
    .gr-spark {{
      position: absolute;
      width: calc(14px * var(--gr-scale, 1)); height: calc(14px * var(--gr-scale, 1));
      margin-left: calc(-7px * var(--gr-scale, 1));
      margin-top: calc(-7px * var(--gr-scale, 1));
      animation: grSpark linear forwards;
      pointer-events: none;
      will-change: transform;
    }}
    .gr-spark svg {{ width: 100%; height: 100%; display: block; }}
    @keyframes grSpark {{
      0%   {{ transform: translate(0, 0) scale(1); opacity: 1; }}
      100% {{ transform: translate(var(--gr-dx, 70px), var(--gr-dy, 60px)) scale(0.2); opacity: 0; }}
    }}

    /* ---- popups (score / sender / combo / badge) ---- */
    .gr-value {{
      position: absolute;
      transform: translate(-50%, -50%);
      color: #fff;
      font-family: system-ui, sans-serif;
      font-weight: 900;
      font-size: calc(40px * var(--gr-scale, 1));
      letter-spacing: 1px;
      text-shadow: 0 2px 0 rgba(0,0,0,0.55), 0 0 calc(14px * var(--gr-scale, 1)) var(--gr-glow);
      animation: grRise 0.8s ease-out forwards;
      pointer-events: none;
    }}
    .gr-value.is-epic {{ font-size: calc(54px * var(--gr-scale, 1)); }}
    .gr-value.is-high {{ font-size: calc(44px * var(--gr-scale, 1)); }}
    @keyframes grRise {{
      0%   {{ opacity: 0; transform: translate(-50%, -50%) scale(0.6); }}
      40%  {{ transform: translate(-50%, -50%) scale(1.15); }}
      70%  {{ transform: translate(-50%, -50%) scale(1) translateY(-12px); opacity: 1; }}
      100% {{ opacity: 0; transform: translate(-50%, -50%) translateY(-30px); }}
    }}
    .gr-sender {{
      position: absolute;
      transform: translate(-50%, -50%);
      color: rgba(255,255,255,0.75);
      font-family: system-ui, sans-serif;
      font-weight: 600;
      font-size: calc(14px * var(--gr-scale, 1));
      letter-spacing: 0.5px;
      text-shadow: 0 1px 3px rgba(0,0,0,0.7);
      animation: grRise 0.9s ease-out forwards;
      pointer-events: none;
    }}
    .gr-combo {{
      position: absolute;
      transform: translate(-50%, -50%);
      color: var(--gr-acc1);
      font-family: system-ui, sans-serif;
      font-weight: 900;
      font-size: calc(26px * var(--gr-scale, 1));
      letter-spacing: 2px;
      text-shadow: 0 0 calc(10px * var(--gr-scale, 1)) var(--gr-glow);
      animation: grComboPop 1.0s ease-out forwards;
      pointer-events: none;
    }}
    .gr-combo.is-combo-large {{ font-size: calc(36px * var(--gr-scale, 1)); }}
    .gr-combo.is-epic {{ color: #fff; text-shadow: 0 0 calc(18px * var(--gr-scale, 1)) var(--gr-acc1); }}
    @keyframes grComboPop {{
      0%   {{ opacity: 0; transform: translate(-50%, -50%) scale(0.8); }}
      45%  {{ transform: translate(-50%, -50%) scale(1.15); }}
      75%  {{ transform: translate(-50%, -50%) scale(1); opacity: 1; }}
      100% {{ opacity: 0; transform: translate(-50%, -50%) scale(0.9); }}
    }}
    .gr-badge {{
      position: absolute;
      transform: translate(-50%, -50%);
      color: #fff;
      font-family: system-ui, sans-serif;
      font-weight: 900;
      font-size: calc(22px * var(--gr-scale, 1));
      letter-spacing: 3px;
      padding: 4px 14px;
      border-radius: 999px;
      background: rgba(10, 10, 20, 0.55);
      box-shadow: 0 0 calc(12px * var(--gr-scale, 1)) var(--gr-glow);
      animation: grBadgePulse 0.8s ease-out forwards;
      pointer-events: none;
    }}
    .gr-badge.is-epic {{ font-size: calc(28px * var(--gr-scale, 1)); }}
    @keyframes grBadgePulse {{
      0%   {{ opacity: 0; transform: translate(-50%, -50%) scale(0.8); }}
      40%  {{ opacity: 1; transform: translate(-50%, -50%) scale(1.2); }}
      100% {{ opacity: 0; transform: translate(-50%, -50%) scale(0.9); }}
    }}

    /* reduced mode: shorter, subtler */
    .gr-reduced .gr-glow, .gr-reduced .gr-ring {{ opacity: 0.5; }}
  </style>
</head>
<body>
  <div id="grRoot">
    <div id="grCam">
      <div id="grLayer"></div>
      <div id="grBurst"></div>
      <div id="grPopup"></div>
    </div>
  </div>
  <script>
    (function() {{
      const root = document.getElementById('grRoot');
      const grCam = document.getElementById('grCam');
      const grLayer = document.getElementById('grLayer');
      const grBurst = document.getElementById('grBurst');
      const grPopup = document.getElementById('grPopup');
      const instance = __GR_INSTANCE__;

      let cfg = null;
      let locale = 'uk';
      let state = null;
      let lastSeenAt = 0;
      let reduced = false;
      let maxSimultaneous = 10;

      const MAX_PROJECTILES = 12;
      const MAX_COINS = 24;
      const MAX_COINS_ON_SCREEN = 32;
      const MAX_SPARKS = 24;
      const MAX_SPARKS_ON_SCREEN = 48;
      const MAX_RIBBONS = 8;
      const MAX_RIBBONS_ON_SCREEN = 24;

      let activeEvents = 0;
      let coinsOnScreen = 0;
      let sparksOnScreen = 0;
      let ribbonsOnScreen = 0;

      const GIFT_SVG = '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">' +
        '<rect x="4" y="9.5" width="16" height="11" rx="1" fill="var(--gr-acc1)"/>' +
        '<rect x="4" y="9.5" width="16" height="3" rx="0.5" fill="var(--gr-acc3)"/>' +
        '<path d="M12 9.5V20.5" stroke="var(--gr-acc2)" stroke-width="1.4"/>' +
        '<circle cx="8.6" cy="7" r="2.4" fill="var(--gr-acc2)"/>' +
        '<circle cx="12" cy="5.8" r="2.6" fill="var(--gr-acc2)"/>' +
        '<circle cx="15.4" cy="7" r="2.4" fill="var(--gr-acc2)"/>' +
        '</svg>';
      const COIN_SVG = '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">' +
        '<circle cx="12" cy="12" r="11" fill="var(--gr-coin)" stroke="rgba(0,0,0,0.25)" stroke-width="1"/>' +
        '<circle cx="12" cy="12" r="7.5" fill="none" stroke="rgba(0,0,0,0.25)" stroke-width="1.2"/>' +
        '<path d="M7.5 12a4.5 4.5 0 1 0 9 0" fill="none" stroke="rgba(0,0,0,0.2)" stroke-width="1.2"/>' +
        '</svg>';
      const SPARK_SVG = '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">' +
        '<path d="M12 2l3.4 6.9L22 10l-5.6 4.1L20 22l-5.6-3.9-5.6 3.9L12 13.9l-5.6 4.1 5.6-4.1-5.4-3.9z" fill="var(--gr-acc1)"/>' +
        '</svg>';

      function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
      function rand(a, b) { return a + Math.random() * (b - a); }

      function impactPoint(mode) {{
        const m = (mode || 'center').toString().toLowerCase();
        if (m === 'left') return {{ x: 0.2, y: 0.45 }};
        if (m === 'right') return {{ x: 0.8, y: 0.45 }};
        if (m === 'random') return {{ x: 0.35 + Math.random() * 0.3, y: 0.4 + Math.random() * 0.15 }};
        return {{ x: 0.5, y: 0.45 }};
      }}
      function sourcePoint(mode) {{
        const m = (mode || 'center').toString().toLowerCase();
        let x;
        if (m === 'left') x = 0.88;
        else if (m === 'right') x = 0.12;
        else x = Math.random() < 0.5 ? 0.12 : 0.88;
        return {{ x: clamp(x + rand(-0.03, 0.03), 0.04, 0.96), y: clamp(0.88 + rand(-0.02, 0.02), 0.8, 0.96) }};
      }}
      function intensityBadgeText(intensity) {{
        if (intensity === 'HIGH') return 'BIG GIFT';
        if (intensity === 'EPIC') return 'EPIC';
        return '';
      }}
      function tierCounts(intensity) {{
        let coins, sparks, ribbons, rings, flightMs, coinDist;
        if (intensity === 'EPIC') {{ coins = MAX_COINS; sparks = MAX_SPARKS; ribbons = 8; rings = 3; flightMs = 900; coinDist = 1.35; }}
        else if (intensity === 'HIGH') {{ coins = 18; sparks = 20; ribbons = 5; rings = 2; flightMs = 750; coinDist = 1.15; }}
        else if (intensity === 'MEDIUM') {{ coins = 11; sparks = 14; ribbons = 4; rings = 1; flightMs = 650; coinDist = 1.0; }}
        else {{ coins = 6; sparks = 8; ribbons = 0; rings = 1; flightMs = 520; coinDist = 0.8; }}
        if (reduced) {{
          coins = Math.ceil(coins / 2);
          sparks = Math.ceil(sparks / 2);
          ribbons = Math.ceil(ribbons / 2);
          rings = 1;
          flightMs = flightMs * 0.7;
        }}
        return {{ coins, sparks, ribbons, rings, flightMs, coinDist }};
      }}

      function nodeCleanup(el, durationMs, dec) {{
        let done = false;
        const finish = () => {{
          if (done) return;
          done = true;
          if (dec) dec();
          if (el.parentNode) el.parentNode.removeChild(el);
        }};
        el.addEventListener('animationend', finish);
        el.addEventListener('transitionend', finish);
        setTimeout(finish, durationMs);
        return finish;
      }}

      function init() {{
        const c = (state && state.config) ? state.config : {{}};
        cfg = c;
        reduced = !!c.reduced_effects;
        maxSimultaneous = clamp(Math.max(1, Math.min(999999, Math.floor(Number(c.max_simultaneous_events || 10)))) || 10, 4, 12);
        if (reduced) root.classList.add('gr-reduced');
        else root.classList.remove('gr-reduced');
        const theme = (c.theme || 'cheremsha').toString().toLowerCase();
        root.classList.remove('gr-theme-cheremsha', 'gr-theme-celebration', 'gr-theme-arcade');
        root.classList.add('gr-theme-' + theme);
        const scale = clamp(Math.floor(Number(c.scale_percent || 100)) || 100, 40, 250);
        root.style.setProperty('--gr-scale', (scale / 100).toFixed(4));
      }}

      function applyPatch(patch) {{
        if (!state) state = {{}};
        if (!patch || typeof patch !== 'object') return;
        if (patch.config && typeof patch.config === 'object') state.config = patch.config;
        if (patch.locale) state.locale = patch.locale;
        if (Array.isArray(patch.events)) state.events = patch.events.slice();
      }}

      function processEvents() {{
        if (!state || !Array.isArray(state.events)) return;
        for (const e of state.events) {{
          if (!(e && e.type)) continue;
          const at = Number(e.at) || 0;
          if (at <= lastSeenAt + 0.0001) continue;
          lastSeenAt = Math.max(lastSeenAt, at);
          const p = e.payload || {{}};
          if (e.type === 'gift') spawnGift(p);
        }}
      }}

      function spawnGift(p) {{
        if (cfg && cfg.event_animations === false) return;
        const intensity = p.intensity || 'LOW';
        if (activeEvents >= MAX_PROJECTILES) return;
        if (activeEvents >= maxSimultaneous && intensity === 'LOW') return;
        const mode = p.target || (cfg && cfg.target_mode) || 'center';
        const ip = impactPoint(mode);
        const sp = sourcePoint(mode);
        activeEvents++;
        const r = (grCam || root).getBoundingClientRect();
        const W = r.width || window.innerWidth;
        const H = r.height || window.innerHeight;
        const sx = sp.x * W;
        const sy = sp.y * H;
        const tx = ip.x * W;
        const ty = ip.y * H;
        const midX = (sx + tx) / 2;
        const arcLift = (intensity === 'EPIC' ? 0.10 : 0.06) * H;
        const midY = (sy + ty) / 2 - arcLift;
        const pathD = 'M ' + sx.toFixed(1) + ' ' + sy.toFixed(1) +
          ' Q ' + midX.toFixed(1) + ' ' + midY.toFixed(1) +
          ' ' + tx.toFixed(1) + ' ' + ty.toFixed(1);
        const tier = tierCounts(intensity);
        spawnProjectile(sx, sy, tx, ty, pathD, tier, intensity, p);
      }}

      function spawnProjectile(sx, sy, tx, ty, pathD, tier, intensity, p) {{
        if (!grLayer) return;
        const el = document.createElement('div');
        el.className = 'gr-projectile';
        if (intensity === 'MEDIUM') el.classList.add('is-medium');
        if (intensity === 'HIGH') el.classList.add('is-high');
        if (intensity === 'EPIC') el.classList.add('is-epic');
        if (cfg && cfg.show_gift_image !== false && p.icon_url) {{
          const img = document.createElement('img');
          img.className = 'gr-gift-img';
          img.src = p.icon_url;
          img.alt = '';
          el.appendChild(img);
        }} else {{
          const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
          svg.setAttribute('viewBox', '0 0 24 24');
          svg.innerHTML = GIFT_SVG;
          el.appendChild(svg);
        }}
        el.style.left = sx + 'px';
        el.style.top = sy + 'px';
        el.style.setProperty('offset-path', 'path("' + pathD + '")');
        el.style.setProperty('offset-distance', '0%');
        el.style.opacity = '0';
        el.style.transitionProperty = 'opacity';
        el.style.transitionDuration = '0s';
        grLayer.appendChild(el);
        void el.offsetWidth;
        el.style.opacity = '1';
        el.style.transitionProperty = 'offset-distance, opacity';
        el.style.transitionDuration = tier.flightMs + 'ms';
        el.style.transitionTimingFunction = 'cubic-bezier(0.34, 1.56, 0.64, 1)';
        el.style.setProperty('offset-distance', '100%');
        let done = false;
        const finishProj = () => {{
          if (done) return;
          done = true;
          activeEvents = Math.max(0, activeEvents - 1);
          if (el.parentNode) el.parentNode.removeChild(el);
          spawnBurst(tx, ty, p, tier, intensity);
        }};
        el.addEventListener('transitionend', function(ev) {{
          if (ev.propertyName !== 'offset-distance') return;
          finishProj();
        }});
        setTimeout(finishProj, tier.flightMs + 400);
      }}

      function spawnBurst(x, y, p, tier, intensity) {{
        if (cfg && cfg.effects_impact_ring !== false) spawnImpactRing(x, y, intensity, tier.rings);
        spawnGlowFlash(x, y, intensity);
        if (cfg && cfg.effects_coins !== false) spawnCoins(x, y, tier.coins, tier.coinDist);
        if (cfg && cfg.effects_ribbons !== false && tier.ribbons > 0) spawnRibbons(x, y, tier.ribbons);
        if (cfg && cfg.effects_sparks !== false) spawnSparks(x, y, tier.sparks, tier.coinDist);
        if (cfg && cfg.show_value !== false) spawnScorePopup(x, y, p, intensity);
        if (cfg && cfg.show_sender !== false) spawnSenderLine(x, y, p, intensity);
        if (cfg && cfg.show_combo !== false && cfg.combo_enabled !== false && (p.combo || 0) > 1) spawnComboCounter(x, y, p, intensity);
        const badge = cfg && cfg.show_intensity_badge !== false ? intensityBadgeText(intensity) : '';
        if (badge) spawnIntensityBadge(x, y, badge, intensity);
        if (cfg && cfg.camera_impact !== false && intensity === 'EPIC' && !reduced) flashCameraImpact();
      }}

      function spawnImpactRing(x, y, intensity, rings) {{
        if (!grBurst) return;
        for (let i = 0; i < rings; i++) {{
          const el = document.createElement('div');
          el.className = 'gr-ring';
          el.style.left = x + 'px';
          el.style.top = y + 'px';
          el.style.animationDelay = (i * 90) + 'ms';
          if (intensity === 'epic') el.classList.add('is-epic');
          else if (intensity === 'high') el.classList.add('is-high');
          grBurst.appendChild(el);
          const dur = 700 + (i * 90);
          nodeCleanup(el, dur);
        }}
      }}

      function spawnGlowFlash(x, y, intensity) {{
        if (!grBurst) return;
        const el = document.createElement('div');
        el.className = 'gr-glow';
        if (intensity === 'HIGH') el.classList.add('is-high');
        if (intensity === 'EPIC') el.classList.add('is-epic');
        el.style.left = x + 'px';
        el.style.top = y + 'px';
        grBurst.appendChild(el);
        nodeCleanup(el, 750);
      }}

      function spawnCoins(x, y, n, coinDist) {{
        if (!grBurst) return;
        for (let i = 0; i < n; i++) {{
          if (coinsOnScreen >= MAX_COINS_ON_SCREEN) break;
          if (n > MAX_COINS && i >= MAX_COINS) break;
          const el = document.createElement('div');
          el.className = 'gr-coin';
          el.style.left = x + 'px';
          el.style.top = y + 'px';
          el.innerHTML = COIN_SVG;
          const angle = rand(0, Math.PI * 2);
          const dist = rand(40, 100) * coinDist;
          const dx = Math.cos(angle) * dist;
          const dy = Math.sin(angle) * dist * 0.7 - dist * 0.25;
          const z = rand(0.6, 1.3);
          el.style.setProperty('--gr-dx', dx.toFixed(1) + 'px');
          el.style.setProperty('--gr-dy', dy.toFixed(1) + 'px');
          el.style.setProperty('--gr-mx', (dx * 0.5).toFixed(1) + 'px');
          el.style.setProperty('--gr-my', (-dist * 0.5).toFixed(1) + 'px');
          el.style.setProperty('--gr-z', z.toFixed(2));
          const dur = 700 + rand(0, 700);
          el.style.animationDuration = dur + 'ms';
          grBurst.appendChild(el);
          coinsOnScreen++;
          nodeCleanup(el, dur, function() { coinsOnScreen--; });
        }}
      }}

      function spawnRibbons(x, y, n) {{
        if (!grBurst) return;
        for (let i = 0; i < n; i++) {{
          if (ribbonsOnScreen >= MAX_RIBBONS_ON_SCREEN) break;
          if (n > MAX_RIBBONS && i >= MAX_RIBBONS) break;
          const el = document.createElement('div');
          el.className = 'gr-ribbon';
          el.style.left = x + 'px';
          el.style.top = y + 'px';
          const angle = rand(0, Math.PI * 2);
          const dist = rand(60, 160);
          el.style.setProperty('--gr-rot', (i * 30).toString());
          el.style.setProperty('--gr-dx', (Math.cos(angle) * dist).toFixed(1) + 'px');
          el.style.setProperty('--gr-dy', (Math.sin(angle) * dist * 0.7 - dist * 0.3).toFixed(1) + 'px');
          el.style.setProperty('--gr-mx', (Math.cos(angle) * dist * 0.5).toFixed(1) + 'px');
          el.style.setProperty('--gr-my', (Math.sin(angle) * dist * 0.4).toFixed(1) + 'px');
          const dur = 900 + rand(0, 900);
          el.style.animationDuration = dur + 'ms';
          grBurst.appendChild(el);
          ribbonsOnScreen++;
          nodeCleanup(el, dur, function() { ribbonsOnScreen--; });
        }}
      }}

      function spawnSparks(x, y, n, coinDist) {{
        if (!grBurst) return;
        for (let i = 0; i < n; i++) {{
          if (sparksOnScreen >= MAX_SPARKS_ON_SCREEN) break;
          if (n > MAX_SPARKS && i >= MAX_SPARKS) break;
          const el = document.createElement('div');
          el.className = 'gr-spark';
          el.style.left = x + 'px';
          el.style.top = y + 'px';
          el.innerHTML = SPARK_SVG;
          const angle = rand(0, Math.PI * 2);
          const dist = rand(30, 90) * coinDist;
          el.style.setProperty('--gr-dx', (Math.cos(angle) * dist).toFixed(1) + 'px');
          el.style.setProperty('--gr-dy', (Math.sin(angle) * dist * 0.6 - dist * 0.2).toFixed(1) + 'px');
          const dur = 300 + rand(0, 400);
          el.style.animationDuration = dur + 'ms';
          grBurst.appendChild(el);
          sparksOnScreen++;
          nodeCleanup(el, dur, function() { sparksOnScreen--; });
        }}
      }}

      function spawnScorePopup(x, y, p, intensity) {{
        if (!grPopup) return;
        const value = p.value || 0;
        const count = p.count || 1;
        const el = document.createElement('div');
        el.className = 'gr-value';
        if (intensity === 'EPIC') el.classList.add('is-epic');
        else if (intensity === 'HIGH') el.classList.add('is-high');
        let txt = '+' + value;
        if (count > 1) txt += ' x' + count;
        el.textContent = txt;
        el.style.left = x + 'px';
        el.style.top = (y - 40) + 'px';
        grPopup.appendChild(el);
        const dur = 600 + rand(0, 300);
        el.style.animationDuration = dur + 'ms';
        nodeCleanup(el, dur);
      }}

      function spawnSenderLine(x, y, p, intensity) {{
        if (!grPopup) return;
        const sender = p.sender || '';
        if (!sender) return;
        const el = document.createElement('div');
        el.className = 'gr-sender';
        el.textContent = 'from ' + sender;
        el.style.left = x + 'px';
        el.style.top = (y - 18) + 'px';
        grPopup.appendChild(el);
        const dur = 700 + rand(0, 300);
        el.style.animationDuration = dur + 'ms';
        nodeCleanup(el, dur);
      }}

      function spawnComboCounter(x, y, p, intensity) {{
        if (!grPopup) return;
        const combo = p.combo || 0;
        if (combo <= 1) return;
        const el = document.createElement('div');
        el.className = 'gr-combo';
        if (combo >= 10) el.classList.add('is-combo-large');
        if (intensity === 'EPIC') el.classList.add('is-epic');
        el.textContent = 'COMBO x' + combo;
        el.style.left = x + 'px';
        el.style.top = (y - 70) + 'px';
        grPopup.appendChild(el);
        const dur = 900 + rand(0, 300);
        el.style.animationDuration = dur + 'ms';
        nodeCleanup(el, dur);
      }}

      function spawnIntensityBadge(x, y, txt, intensity) {{
        if (!grPopup) return;
        const el = document.createElement('div');
        el.className = 'gr-badge';
        if (intensity === 'EPIC') el.classList.add('is-epic');
        el.textContent = txt;
        el.style.left = x + 'px';
        el.style.top = (y - 95) + 'px';
        grPopup.appendChild(el);
        nodeCleanup(el, 850);
      }}

      function flashCameraImpact() {{
        if (!grCam) return;
        grCam.classList.remove('gr-cam-hit');
        void grCam.offsetWidth;
        grCam.classList.add('gr-cam-hit');
      }}

      function handleMsg(obj) {{
        if (!obj || typeof obj !== 'object') return;
        if (obj.op === 'initial_state' && obj.state) {{
          state = {{}};
          lastSeenAt = 0;
          applyPatch(obj.state);
          init();
          processEvents();
        }} else if (obj.op === 'patch' && obj.patch) {{
          applyPatch(obj.patch);
          if (obj.patch && obj.patch.config) init();
          processEvents();
        }}
      }}

      const subscribeMsg = {{ op: 'subscribe', type: 'gift_rush', instance: instance, params: {{}} }};
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
          ws.send(JSON.stringify(subscribeMsg));
        }};
        ws.onmessage = (ev) => {{
          let obj = null;
          try {{ obj = JSON.parse(ev.data); }} catch (err) {{ return; }}
          handleMsg(obj);
        }};
        ws.onclose = () => setTimeout(connect, backoff);
      }}
      connect();
    }})();
  </script>
</body>
</html>
"""


class GiftRushOverlayType:
    """Overlay type serving the transparent gift-rush VFX page."""

    type = "gift_rush"

    def render_html(self, params: dict[str, Any]) -> str:
        raw_instance = params.get("instance")
        try:
            instance = normalize_instance_id(str(raw_instance or ""))
        except ValueError:
            instance = "default"
        # JSON-encode the instance so it is a safe JS string literal.
        instance_lit = json.dumps(instance)
        return _HTML_TEMPLATE.replace("__GR_INSTANCE__", instance_lit)

    def initial_state(self, params: dict[str, Any]) -> dict[str, Any]:
        from stream_cheremsha.overlays.gift_rush_config import (
            gift_rush_overlay_config_from_json_text,
            gift_rush_overlay_config_to_json_text,
            load_gift_rush_overlay_config,
        )
        from stream_cheremsha.overlays.widget_instances import typed_config_for_type

        cfg = typed_config_for_type(
            "gift_rush",
            params,
            load_gift_rush_overlay_config,
            gift_rush_overlay_config_from_json_text,
        )
        cfg_payload = json.loads(gift_rush_overlay_config_to_json_text(cfg))
        return {
            "config": cfg_payload,
            "locale": "uk",
            "events": [],
        }
