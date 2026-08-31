from __future__ import annotations

# ruff: noqa: E501
import base64
import json
from pathlib import Path
from typing import Any

from stream_cheremsha.overlays.actions_config import (
    actions_config_to_json_text,
    load_actions_config,
)
from stream_cheremsha.overlays.models import normalize_instance_id


def _json_for_script(value: Any) -> str:
    s = json.dumps(value, ensure_ascii=False)
    return s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def _platform_icons_data_uris() -> dict[str, str]:
    """Inline SVG as data URIs so OBS/Chromium always paints icons (no separate /assets fetch)."""
    base = Path(__file__).resolve().parents[1] / "assets"
    out: dict[str, str] = {}
    for slug in ("tiktok", "twitch", "youtube", "kick"):
        p = base / f"{slug}.svg"
        if not p.is_file():
            continue
        raw = p.read_bytes()
        b64 = base64.standard_b64encode(raw).decode("ascii")
        out[slug] = f"data:image/svg+xml;base64,{b64}"
    return out


class ActionsOverlayType:
    type = "actions"

    def render_html(self, params: dict[str, Any]) -> str:
        raw_instance = params.get("instance")
        try:
            instance = normalize_instance_id(str(raw_instance or ""))
        except ValueError:
            instance = "default"

        subscribe_msg = {"op": "subscribe", "type": "actions", "instance": instance, "params": {}}
        platform_icons_js = _json_for_script(_platform_icons_data_uris())

        return f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Actions Overlay</title>
    <style>
      html, body {{ margin: 0; padding: 0; background: transparent; overflow: hidden; height: 100%; }}
      body {{ font-family: system-ui, sans-serif; }}
      .wrap {{
        position: absolute;
        inset: 0;
        padding: 12px;
        box-sizing: border-box;
        overflow: hidden;
      }}
      .wrap.wrap--sequential .seq-host {{
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
      }}
      .wrap.wrap--parallel .seq-host {{ display: none; }}
      /* Anchor holds only position + centering transform. Inner .card gets motion FX (those overwrite transform). */
      .parallel-popup-anchor {{
        position: absolute;
        transform: translate(-50%, -50%);
        pointer-events: none;
        max-width: 100%;
        box-sizing: border-box;
        transition: opacity 180ms ease-out;
      }}
      .parallel-popup-anchor > .card {{
        width: min(720px, 100%);
        max-width: 100%;
        box-sizing: border-box;
      }}
      .card {{
        width: min(720px, calc(100vw - 24px));
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 10px;
        padding: 18px 18px;
        border-radius: 16px;
        background: rgba(10,12,18,0.55);
        border: 1px solid rgba(148,163,184,0.20);
        color: #e5e7eb;
        opacity: 1;
        transition: opacity 180ms ease-out;
      }}
      /* Size comes from JS (cfg.picture_size_px); fixed px here overrides OBS/Chromium inline sizing. */
      .avatar {{
        box-sizing: border-box;
        flex: 0 0 auto;
        border-radius: 999px;
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.12);
        overflow: hidden;
      }}
      .avatar img {{
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
      }}
      .platform-row {{
        margin-top: 12px;
        display: flex;
        justify-content: center;
        align-items: center;
        perspective: 240px;
      }}
      .platform-icon {{
        display: block;
        opacity: 0.92;
        transform-style: preserve-3d;
        backface-visibility: visible;
        -webkit-backface-visibility: visible;
        filter: drop-shadow(0 1px 2px rgba(0,0,0,0.35));
      }}
      /* Slow ease-in at start, fast snap to finish (segment timing via keyframes). */
      .platform-icon--flip {{
        animation: platformIconFlip 1.05s forwards;
      }}
      @keyframes platformIconFlip {{
        0% {{
          transform: rotateY(0deg);
          animation-timing-function: cubic-bezier(0.82, 0, 1, 1);
        }}
        68% {{
          transform: rotateY(48deg);
          animation-timing-function: cubic-bezier(0.18, 0.82, 0.35, 1);
        }}
        100% {{
          transform: rotateY(180deg) scaleX(-1);
        }}
      }}
      .name {{
        font-weight: 900;
        text-align: center;
      }}
      .text {{
        opacity: 0.95;
        text-align: center;
      }}
      .one {{ white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; }}
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
      .tfx-neon {{
        color: #67e8f9 !important;
        text-shadow: 0 0 6px rgba(103, 232, 249, 0.65), 0 0 16px rgba(99, 102, 241, 0.35);
        animation: neonPulse 1.8s ease-in-out infinite;
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

      /* Motion effects for the whole card (independent toggles). */
      @property --fx-move-x {{
        syntax: '<length>';
        inherits: true;
        initial-value: 0px;
      }}
      @property --fx-wave-y {{
        syntax: '<length>';
        inherits: true;
        initial-value: 0px;
      }}
      @property --fx-wiggle-rot {{
        syntax: '<angle>';
        inherits: true;
        initial-value: 0deg;
      }}
      @property --fx-rot-x {{
        syntax: '<angle>';
        inherits: true;
        initial-value: 0deg;
      }}
      @property --fx-rot-y {{
        syntax: '<angle>';
        inherits: true;
        initial-value: 0deg;
      }}

      .card.fx-wave, .card.fx-move, .card.fx-wiggle, .card.fx-3d {{
        transform:
          translateX(var(--fx-move-x))
          translateY(var(--fx-wave-y))
          rotate(var(--fx-wiggle-rot))
          rotateX(var(--fx-rot-x))
          rotateY(var(--fx-rot-y));
        transform-origin: 50% 50%;
        will-change: transform;
      }}
      .card.fx-3d {{
        perspective: 900px;
        transform-style: preserve-3d;
      }}

      @keyframes tfxShift {{
        0% {{ background-position: 0% 50%; }}
        50% {{ background-position: 100% 50%; }}
        100% {{ background-position: 0% 50%; }}
      }}

      @keyframes neonPulse {{
        0% {{
          filter: brightness(1.0);
          text-shadow: 0 0 5px rgba(103, 232, 249, 0.50), 0 0 12px rgba(99, 102, 241, 0.25);
        }}
        50% {{
          filter: brightness(1.15);
          text-shadow: 0 0 8px rgba(103, 232, 249, 0.80), 0 0 20px rgba(99, 102, 241, 0.42);
        }}
        100% {{
          filter: brightness(1.0);
          text-shadow: 0 0 5px rgba(103, 232, 249, 0.50), 0 0 12px rgba(99, 102, 241, 0.25);
        }}
      }}

      @keyframes fireRise {{
        0% {{ background-position: 50% 0%; }}
        50% {{ background-position: 50% 100%; }}
        100% {{ background-position: 50% 0%; }}
      }}

      @keyframes fxWave {{
        0% {{ --fx-wave-y: 0px; }}
        25% {{ --fx-wave-y: -4px; }}
        50% {{ --fx-wave-y: 0px; }}
        75% {{ --fx-wave-y: 4px; }}
        100% {{ --fx-wave-y: 0px; }}
      }}
      @keyframes fxMove {{
        0% {{ --fx-move-x: 0px; }}
        50% {{ --fx-move-x: 10px; }}
        100% {{ --fx-move-x: 0px; }}
      }}
      @keyframes fxWiggle {{
        0% {{ --fx-wiggle-rot: 0deg; }}
        20% {{ --fx-wiggle-rot: -1.2deg; }}
        40% {{ --fx-wiggle-rot: 1.2deg; }}
        60% {{ --fx-wiggle-rot: -0.8deg; }}
        80% {{ --fx-wiggle-rot: 0.8deg; }}
        100% {{ --fx-wiggle-rot: 0deg; }}
      }}
      @keyframes fx3d {{
        0% {{ --fx-rot-x: 0deg; --fx-rot-y: 0deg; }}
        25% {{ --fx-rot-x: 6deg; --fx-rot-y: -8deg; }}
        50% {{ --fx-rot-x: 0deg; --fx-rot-y: 0deg; }}
        75% {{ --fx-rot-x: -6deg; --fx-rot-y: 8deg; }}
        100% {{ --fx-rot-x: 0deg; --fx-rot-y: 0deg; }}
      }}
    </style>
  </head>
  <body>
    <div id="wrap" class="wrap wrap--sequential">
      <div class="seq-host">
        <div id="preview" class="card"></div>
      </div>
    </div>
    <script>
      (function() {{
        const PLATFORM_ICONS = {platform_icons_js};
        const wsUrl = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws';
        const wrap = document.getElementById('wrap');
        const root = document.getElementById('preview');
        let cfg = null;
        let lastAppend = null;
        let hideTimer = null;
        let ws = null;
        let tries = 0;
        let activeParallel = [];
        let popupIdSeq = 0;

        function clampInt(v, minV, maxV, defV) {{
          const n = Number(v);
          if (!Number.isFinite(n)) return defV;
          const i = Math.trunc(n);
          return Math.max(minV, Math.min(maxV, i));
        }}

        function platformIconDataUrl(slug) {{
          const s = String(slug || '').trim().toLowerCase();
          const icons = PLATFORM_ICONS || {{}};
          const u = icons[s];
          return (typeof u === 'string' && u.length) ? u : '';
        }}

        function isParallelMode() {{
          if (!cfg) return false;
          const v = cfg.parallel_popups_enabled;
          if (v !== undefined && v !== null) return !!v;
          return !!cfg.parallelPopupsEnabled;
        }}

        function syncWrapLayoutClass() {{
          if (!wrap) return;
          const par = isParallelMode();
          wrap.classList.toggle('wrap--parallel', par);
          wrap.classList.toggle('wrap--sequential', !par);
        }}

        function applyBodyFont() {{
          if (!cfg) return;
          document.body.style.fontFamily = cfg.font_family || 'system-ui';
          document.body.style.fontSize = clampInt(cfg.font_size_px, 8, 200, 40) + 'px';
          document.body.style.letterSpacing = clampInt(cfg.font_letter_spacing_px, -200, 200, 0) + 'px';
          document.body.style.lineHeight = 'normal';
        }}

        function applyCardChrome(cardEl) {{
          if (!cfg || !cardEl) return;
          cardEl.classList.toggle('fx-wave', !!cfg.wave_enabled);
          cardEl.classList.toggle('fx-move', !!cfg.move_enabled);
          cardEl.classList.toggle('fx-3d', !!cfg.effect_3d_enabled);
          cardEl.classList.toggle('fx-wiggle', !!cfg.wiggle_enabled);
          const anims = [];
          if (cfg.wave_enabled) anims.push('fxWave 1.25s ease-in-out infinite');
          if (cfg.move_enabled) anims.push('fxMove 1.8s ease-in-out infinite');
          if (cfg.wiggle_enabled) anims.push('fxWiggle 0.9s ease-in-out infinite');
          if (cfg.effect_3d_enabled) anims.push('fx3d 2.4s ease-in-out infinite');
          cardEl.style.animation = anims.join(', ');

          const bubbleOn = (cfg.bubble_bg_enabled !== undefined) ? !!cfg.bubble_bg_enabled : true;
          const alpha = Number(cfg.bubble_bg_alpha);
          const a = (Number.isFinite(alpha) ? Math.max(0, Math.min(1, alpha)) : 0.55);
          cardEl.style.background = bubbleOn ? ('rgba(10,12,18,' + a + ')') : 'transparent';
          cardEl.style.borderRadius = clampInt(cfg.bubble_radius_px, 0, 60, 16) + 'px';

          const borderOn = !!cfg.font_border_enabled;
          const borderCol = String(cfg.font_border_color || '#242424');
          if (!bubbleOn) {{
            cardEl.style.borderWidth = '0px';
            cardEl.style.borderStyle = 'solid';
            cardEl.style.borderColor = 'transparent';
          }} else {{
            cardEl.style.borderWidth = '1px';
            cardEl.style.borderStyle = 'solid';
            cardEl.style.borderColor = borderOn ? borderCol : 'rgba(148,163,184,0.20)';
          }}
        }}

        function applyCfg() {{
          if (!cfg) return;
          applyBodyFont();
          syncWrapLayoutClass();
          if (isParallelMode()) {{
            for (let i = 0; i < activeParallel.length; i++) {{
              const inn = activeParallel[i].inner;
              if (inn) applyCardChrome(inn);
            }}
          }} else {{
            applyCardChrome(root);
          }}
        }}

        function clearHideTimer() {{
          if (hideTimer) {{
            try {{ clearTimeout(hideTimer); }} catch (e) {{}}
            hideTimer = null;
          }}
        }}

        function clearParallelPopups() {{
          for (let i = 0; i < activeParallel.length; i++) {{
            const row = activeParallel[i];
            if (row.timer) {{
              try {{ clearTimeout(row.timer); }} catch (e) {{}}
            }}
            if (row.el && row.el.parentNode) row.el.parentNode.removeChild(row.el);
          }}
          activeParallel = [];
        }}

        function inflateRect(r, pad) {{
          return {{
            left: r.left - pad,
            top: r.top - pad,
            right: r.right + pad,
            bottom: r.bottom + pad,
          }};
        }}

        function rectsOverlap(a, b) {{
          return !(a.right < b.left || a.left > b.right || a.bottom < b.top || a.top > b.bottom);
        }}

        function setParallelCardCenterPercent(cardEl, cx, cy, wr) {{
          if (!wr || wr.width < 2 || wr.height < 2) return;
          const leftPct = ((cx - wr.left) / wr.width) * 100;
          const topPct = ((cy - wr.top) / wr.height) * 100;
          cardEl.style.left = leftPct + '%';
          cardEl.style.top = topPct + '%';
        }}

        function clampParallelCardIntoWrap(cardEl) {{
          if (!wrap || !cardEl) return;
          const margin = 6;
          void cardEl.offsetWidth;
          const wr = wrap.getBoundingClientRect();
          const r = cardEl.getBoundingClientRect();
          const halfW = r.width / 2;
          const halfH = r.height / 2;
          let cx = r.left + halfW;
          let cy = r.top + halfH;
          cx = Math.min(wr.right - margin - halfW, Math.max(wr.left + margin + halfW, cx));
          cy = Math.min(wr.bottom - margin - halfH, Math.max(wr.top + margin + halfH, cy));
          setParallelCardCenterPercent(cardEl, cx, cy, wr);
        }}

        function positionParallelCard(cardEl, existingEls, placementSlot) {{
          if (!wrap) return;
          const pad = 16;
          const margin = 6;
          const n = existingEls.length;
          void cardEl.offsetWidth;
          const r0 = cardEl.getBoundingClientRect();
          const halfW = r0.width / 2;
          const halfH = r0.height / 2;
          const wr = wrap.getBoundingClientRect();
          const minCx = wr.left + margin + halfW;
          const maxCx = wr.right - margin - halfW;
          const minCy = wr.top + margin + halfH;
          const maxCy = wr.bottom - margin - halfH;
          if (maxCx < minCx || maxCy < minCy) {{
            setParallelCardCenterPercent(cardEl, (wr.left + wr.right) / 2, (wr.top + wr.bottom) / 2, wr);
            clampParallelCardIntoWrap(cardEl);
            return;
          }}
          const midX = (minCx + maxCx) / 2;
          const midY = (minCy + maxCy) / 2;
          const rx = (maxCx - minCx) / 2;
          const ry = (maxCy - minCy) / 2;
          const golden = 2.3999632297286533;
          const slotRaw = Number(placementSlot);
          const slot = Number.isFinite(slotRaw) ? slotRaw : 0;

          function tryCenter(cx, cy) {{
            setParallelCardCenterPercent(cardEl, cx, cy, wr);
            void cardEl.offsetWidth;
            const r = cardEl.getBoundingClientRect();
            for (let j = 0; j < n; j++) {{
              const o = existingEls[j].getBoundingClientRect();
              if (rectsOverlap(inflateRect(r, pad), inflateRect(o, pad))) return false;
            }}
            return true;
          }}

          // Deterministic ring offsets first: rapid bursts share random() timing but get different angles per slot.
          for (let p = 0; p < 22; p++) {{
            const ang = golden * (slot * 47 + p * 13);
            const t = 0.2 + (p % 10) * 0.07;
            let cx = midX + Math.cos(ang) * rx * t;
            let cy = midY + Math.sin(ang) * ry * t;
            cx = Math.min(maxCx, Math.max(minCx, cx));
            cy = Math.min(maxCy, Math.max(minCy, cy));
            if (tryCenter(cx, cy)) {{
              clampParallelCardIntoWrap(cardEl);
              return;
            }}
          }}
          for (let attempt = 0; attempt < 56; attempt++) {{
            const cx = minCx + Math.random() * (maxCx - minCx);
            const cy = minCy + Math.random() * (maxCy - minCy);
            if (tryCenter(cx, cy)) {{
              clampParallelCardIntoWrap(cardEl);
              return;
            }}
          }}
          for (let p = 0; p < 40; p++) {{
            const ang = golden * (slot + p * 2.31);
            const t = 0.1 + (p % 12) * 0.065;
            let cx = midX + Math.cos(ang) * rx * Math.min(0.98, t);
            let cy = midY + Math.sin(ang) * ry * Math.min(0.98, t);
            cx = Math.min(maxCx, Math.max(minCx, cx));
            cy = Math.min(maxCy, Math.max(minCy, cy));
            if (tryCenter(cx, cy)) {{
              clampParallelCardIntoWrap(cardEl);
              return;
            }}
          }}
          setParallelCardCenterPercent(cardEl, midX, midY, wr);
          clampParallelCardIntoWrap(cardEl);
        }}

        function hideSecondsForAppend(ap) {{
          const secOverride = Number(ap.show_seconds ?? ap.showSeconds);
          const secCfg = Number(cfg.auto_hide_seconds || 0);
          return (Number.isFinite(secOverride) && secOverride > 0) ? secOverride : secCfg;
        }}

        function renderCardContent(cardEl, ap) {{
          cardEl.innerHTML = '';
          if (!cfg) return;
          if (!ap) {{
            cardEl.style.opacity = '0';
            return;
          }}
          const showProfile = !!cfg.show_profile_picture;
          const showGift = !!cfg.show_gift_picture;
          const picSize = clampInt(cfg.picture_size_px ?? cfg.pictureSizePx, 1, 512, 65);
          const userSize = clampInt(cfg.username_size_px ?? cfg.usernameSizePx, 1, 512, 65);
          const single = !!cfg.single_text_line;

          let avatarUrl = '';
          const giftU = ap.gift_picture_url ? String(ap.gift_picture_url).trim() : '';
          const profU = ap.profile_picture_url ? String(ap.profile_picture_url).trim() : '';
          if (showGift && giftU) avatarUrl = giftU;
          else if (showProfile && profU) avatarUrl = profU;

          if ((showProfile || showGift) && picSize > 0) {{
            const av = document.createElement('div');
            av.className = 'avatar';
            av.style.boxSizing = 'border-box';
            av.style.flexGrow = '0';
            av.style.flexShrink = '0';
            av.style.flexBasis = picSize + 'px';
            av.style.alignSelf = 'center';
            av.style.setProperty('width', picSize + 'px', 'important');
            av.style.setProperty('height', picSize + 'px', 'important');
            av.style.setProperty('min-width', picSize + 'px', 'important');
            av.style.setProperty('min-height', picSize + 'px', 'important');
            av.style.setProperty('max-width', picSize + 'px', 'important');
            av.style.setProperty('max-height', picSize + 'px', 'important');
            if (avatarUrl) {{
              const img = document.createElement('img');
              img.src = avatarUrl;
              img.alt = '';
              img.draggable = false;
              img.style.setProperty('width', picSize + 'px', 'important');
              img.style.setProperty('height', picSize + 'px', 'important');
              img.style.setProperty('max-width', picSize + 'px', 'important');
              img.style.setProperty('max-height', picSize + 'px', 'important');
              img.style.setProperty('object-fit', 'cover', 'important');
              img.style.boxSizing = 'border-box';
              av.appendChild(img);
            }}
            cardEl.appendChild(av);
          }}

          const name = document.createElement('div');
          name.className = 'name';
          name.textContent = ap.username ? String(ap.username) : 'username';
          name.style.fontSize = userSize + 'px';
          const fs0 = clampInt(cfg.font_size_px, 8, 200, 40);
          const ls0 = clampInt(cfg.font_line_spacing_px, 0, 200, 0);
          const nameLH = Math.max(userSize, Math.round(userSize * 1.18)) + ls0;
          name.style.lineHeight = nameLH + 'px';
          name.style.paddingTop = '2px';
          name.style.paddingBottom = '3px';
          if (cfg.username_custom_color_enabled) {{
            name.style.color = String(cfg.username_custom_color || '#32c3a6');
          }}
          const fx = String(cfg.username_text_effect || 'none').toLowerCase();
          if (fx === 'rainbow') name.classList.add('tfx-rainbow');
          else if (fx === 'aurora') name.classList.add('tfx-aurora');
          else if (fx === 'neon') name.classList.add('tfx-neon');
          else if (fx === 'fire') name.classList.add('tfx-fire');

          const text = document.createElement('div');
          text.className = 'text';
          text.textContent = ap.text ? String(ap.text) : 'action triggered';
          if (single) text.classList.add('one');
          text.style.color = String(cfg.text_color || '#e5e7eb');
          text.style.lineHeight = (fs0 + ls0) + 'px';
          const gap = clampInt(cfg.name_text_gap_px, 0, 80, 8);
          text.style.marginTop = gap + 'px';

          const shOn = !!cfg.text_shadow_enabled;
          const shCol = String(cfg.text_shadow_color || '#000000');
          const shVal = shOn ? ('0px 2px 0px ' + shCol) : '';
          name.style.textShadow = (fx === 'none') ? shVal : '';
          text.style.textShadow = shVal;

          const borderOn = !!cfg.font_border_enabled;
          const borderCol = String(cfg.font_border_color || '#242424');
          const stroke = borderOn ? ('1px ' + borderCol) : '0px transparent';
          name.style.webkitTextStroke = stroke;
          text.style.webkitTextStroke = stroke;

          cardEl.appendChild(name);
          cardEl.appendChild(text);

          const forcePlat = !!(ap.preview_force_platform_icon ?? ap.previewForcePlatformIcon);
          const cfgPlatRaw = (cfg.show_action_platform_icon ?? cfg.showActionPlatformIcon);
          const cfgPlatOn = (cfgPlatRaw === undefined || cfgPlatRaw === null) ? true : !!cfgPlatRaw;
          const showPlat = cfgPlatOn || forcePlat;
          if (showPlat) {{
            const slug = ap.platform ? String(ap.platform).trim().toLowerCase() : '';
            const dataUrl = platformIconDataUrl(slug);
            if (dataUrl) {{
              const prow = document.createElement('div');
              prow.className = 'platform-row';
              const img = document.createElement('img');
              const flipPlat = !!(cfg.platform_icon_flip_enabled ?? cfg.platformIconFlipEnabled);
              img.className = 'platform-icon' + (flipPlat ? ' platform-icon--flip' : '');
              img.draggable = false;
              img.alt = slug;
              img.src = dataUrl;
              const psz = clampInt(cfg.platform_icon_size_px ?? cfg.platformIconSizePx, 16, 128, 40);
              img.style.width = psz + 'px';
              img.style.height = psz + 'px';
              prow.appendChild(img);
              cardEl.appendChild(prow);
            }}
          }}

          cardEl.style.opacity = '1';
        }}

        function renderPreview() {{
          if (isParallelMode()) {{
            root.innerHTML = '';
            root.style.opacity = '0';
            return;
          }}
          renderCardContent(root, lastAppend);
        }}

        function pushParallelAppend(ap) {{
          if (!wrap || !cfg) return;
          const MAXP = 12;
          while (activeParallel.length >= MAXP) {{
            const old = activeParallel.shift();
            if (old.timer) {{
              try {{ clearTimeout(old.timer); }} catch (e) {{}}
            }}
            if (old.el && old.el.parentNode) old.el.parentNode.removeChild(old.el);
          }}
          const existingEls = activeParallel.map(function (r) {{ return r.el; }});
          const anchor = document.createElement('div');
          anchor.className = 'parallel-popup-anchor';
          const card = document.createElement('div');
          card.className = 'card';
          anchor.appendChild(card);
          popupIdSeq += 1;
          const myId = popupIdSeq;
          anchor.style.zIndex = String(10 + myId);
          wrap.appendChild(anchor);
          renderCardContent(card, ap);
          positionParallelCard(anchor, existingEls, myId);
          applyCardChrome(card);
          clampParallelCardIntoWrap(anchor);

          const sec = hideSecondsForAppend(ap);
          if (!Number.isFinite(sec) || sec <= 0) {{
            activeParallel.push({{ id: myId, el: anchor, inner: card, timer: null }});
            return;
          }}
          const ms = Math.max(0, Math.round(sec * 1000));
          const timer = setTimeout(() => {{
            anchor.style.opacity = '0';
            setTimeout(() => {{
              if (anchor.parentNode) anchor.parentNode.removeChild(anchor);
              activeParallel = activeParallel.filter(function (r) {{ return r.id !== myId; }});
            }}, 220);
          }}, ms);
          activeParallel.push({{ id: myId, el: anchor, inner: card, timer: timer }});
        }}

        function scheduleHide() {{
          clearHideTimer();
          if (!cfg || isParallelMode()) return;
          if (!lastAppend) return;
          const sec = hideSecondsForAppend(lastAppend);
          if (!Number.isFinite(sec) || sec <= 0) return;
          const ms = Math.max(0, Math.round(sec * 1000));
          hideTimer = setTimeout(() => {{
            root.style.opacity = '0';
            setTimeout(() => {{
              lastAppend = null;
              renderPreview();
            }}, 220);
          }}, ms);
        }}

        function handleMsg(data) {{
          if (!data || !data.op) return;
          if (data.op === 'initial_state') {{
            clearHideTimer();
            clearParallelPopups();
            lastAppend = null;
            cfg = (data.state && data.state.config) ? data.state.config : null;
            applyCfg();
            renderPreview();
            return;
          }}
          if (data.op === 'patch') {{
            const p = data.patch || {{}};
            if (p.config) {{
              const wasPar = isParallelMode();
              const incoming = p.config || {{}};
              cfg = cfg ? Object.assign({{}}, cfg, incoming) : incoming;
              const nowPar = isParallelMode();
              if (wasPar && !nowPar) clearParallelPopups();
              if (!wasPar && nowPar) {{
                clearHideTimer();
                lastAppend = null;
                root.innerHTML = '';
                root.style.opacity = '0';
              }}
              applyCfg();
              renderPreview();
            }}
            if (p.append) {{
              if (isParallelMode()) {{
                pushParallelAppend(p.append);
              }} else {{
                lastAppend = p.append;
                renderPreview();
                scheduleHide();
              }}
            }}
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
        cfg = load_actions_config()
        return {"config": json.loads(actions_config_to_json_text(cfg)), "items": []}
