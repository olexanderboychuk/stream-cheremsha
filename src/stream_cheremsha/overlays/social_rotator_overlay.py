from __future__ import annotations

import json
from typing import Any

from stream_cheremsha.overlays.models import normalize_instance_id
from stream_cheremsha.overlays.social_platforms import PLATFORM_DEFINITIONS
from stream_cheremsha.overlays.social_rotator_overlay_config import (
    load_social_rotator_overlay_config,
    parse_platforms,
    social_rotator_overlay_config_to_public_dict,
)
from stream_cheremsha.overlays.social_rotator_rotation import (
    SocialRotatorRotationEngine,
    enabled_rotation_entries,
)
from stream_cheremsha.overlays.social_rotator_stats import SocialRotatorStatsSession
from stream_cheremsha.overlays.ui_locale import load_ui_locale


def _json_for_script(value: Any) -> str:
    s = json.dumps(value, ensure_ascii=False)
    return s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def _platform_meta() -> dict[str, dict[str, str]]:
    return {
        pid: {"name": p.name, "accent": p.accent, "icon_key": p.icon_key}
        for pid, p in PLATFORM_DEFINITIONS.items()
    }


class SocialRotatorOverlayType:
    type = "social_rotator"

    def render_html(self, params: dict[str, Any]) -> str:
        raw_instance = params.get("instance")
        try:
            instance = normalize_instance_id(str(raw_instance or ""))
        except ValueError:
            instance = "default"

        cfg = load_social_rotator_overlay_config()
        cfg_dict = social_rotator_overlay_config_to_public_dict(cfg)
        accent = str(cfg.accent_color or "#00ffff")
        scale = max(40, min(250, int(cfg.scale_percent))) / 100.0
        locale = load_ui_locale()
        platforms_meta = _platform_meta()
        entries = enabled_rotation_entries(parse_platforms(cfg))
        rotation = SocialRotatorRotationEngine.from_entries(
            entries, interval_ms=cfg.rotation_interval_ms
        )
        initial = {
            "config": cfg_dict,
            "rotation": rotation.presentation_dict(),
            "platforms_enabled": [
                {
                    "id": e.entry_id,
                    "platform": e.platform,
                    "username": e.username,
                    "url": e.url,
                    "order": i,
                }
                for i, e in enumerate(entries)
            ],
            "stats": SocialRotatorStatsSession().to_public_dict(),
            "locale": locale,
        }
        subscribe_msg = {
            "op": "subscribe",
            "type": "social_rotator",
            "instance": instance,
            "params": {},
        }

        return f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Social Rotator</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=VT323&display=swap" rel="stylesheet" />
    <style>
      * {{ box-sizing: border-box; }}
      :root {{
        --sr-accent: {accent};
        --sr-magenta: #ff2bd6;
        --sr-purple: #9b5cff;
        --sr-ok: #39ff88;
        --sr-bg: #050507;
        --sr-platform: #9146FF;
        --sr-widget-scale: {scale:.4f};
        --sr-u: var(--sr-widget-scale);
        --sr-read: 1;
        --sr-glow: 0.28;
      }}
      html, body {{
        margin: 0; padding: 0; width: 100%; height: 100%;
        background: transparent; overflow: hidden;
      }}
      .root {{
        position: absolute; inset: 0;
        display: flex; align-items: center; justify-content: center;
        font-family: 'VT323', monospace;
        color: #e8f7ff;
        --sr-font-display: 'Press Start 2P', monospace;
      }}
      .root.theme-synthwave {{ --sr-accent: #ff71ce; --sr-magenta: #b967ff; }}
      .root.theme-toxic {{ --sr-accent: #b8ff00; --sr-magenta: #39ff88; }}
      .root.theme-ice {{ --sr-accent: #7ef9ff; --sr-magenta: #a0c4ff; }}
      .root.theme-amber {{ --sr-accent: #ffb000; --sr-magenta: #ff6b35; }}
      .hud-frame {{
        position: relative;
        width: min(96vw, calc(920px * var(--sr-u) * var(--sr-read)));
        max-width: 100%;
        padding: calc(10px * var(--sr-u) * var(--sr-read));
        background: linear-gradient(180deg, rgba(8,10,16,0.82), rgba(4,5,8,0.88));
        border: 1px solid color-mix(in srgb, var(--sr-accent) 55%, transparent);
        box-shadow:
          0 0 calc(18px * var(--sr-u)) color-mix(in srgb, var(--sr-accent) calc(var(--sr-glow) * 100%), transparent),
          inset 0 0 calc(24px * var(--sr-u)) rgba(0,255,255,0.04);
        border-radius: 2px;
      }}
      .hud-frame::after {{
        content: '';
        position: absolute; left: 0; right: 0; bottom: -1px; height: 2px;
        background: linear-gradient(90deg, #00e5ff, #ff2bd6 45%, #53fc18);
        box-shadow: 0 0 10px rgba(0,229,255,0.45);
        pointer-events: none;
      }}
      .hud-corner {{
        position: absolute; width: 14px; height: 14px;
        border: 2px solid var(--sr-accent);
        opacity: 0.85;
        pointer-events: none;
      }}
      .hud-corner.tl {{ top: -1px; left: -1px; border-right: 0; border-bottom: 0; }}
      .hud-corner.tr {{ top: -1px; right: -1px; border-left: 0; border-bottom: 0; }}
      .hud-corner.bl {{ bottom: -1px; left: -1px; border-right: 0; border-top: 0; }}
      .hud-corner.br {{ bottom: -1px; right: -1px; border-left: 0; border-top: 0; }}
      .scanlines {{
        pointer-events: none; position: absolute; inset: 0; opacity: 0.22;
        background: repeating-linear-gradient(
          0deg, transparent, transparent 2px, rgba(0,0,0,0.18) 3px
        );
        mix-blend-mode: soft-light;
        animation: scanDrift 9s linear infinite;
      }}
      .root.crt .scanlines {{ opacity: 0.42; }}
      @keyframes scanDrift {{
        from {{ background-position: 0 0; }}
        to {{ background-position: 0 24px; }}
      }}
      .particles {{ pointer-events: none; position: absolute; inset: 0; overflow: hidden; }}
      .fx-particle {{
        position: absolute; width: 3px; height: 3px; border-radius: 50%;
        background: var(--sr-accent);
        box-shadow: 0 0 6px var(--sr-accent);
        animation: rise 2.2s ease-out forwards;
        opacity: 0.7;
      }}
      @keyframes rise {{
        from {{ transform: translateY(0); opacity: 0.8; }}
        to {{ transform: translateY(-40px); opacity: 0; }}
      }}
      .panel-top {{
        position: relative; z-index: 2;
        display: grid;
        grid-template-columns: minmax(0, 1.35fr) auto minmax(0, 1.2fr);
        gap: calc(10px * var(--sr-u) * var(--sr-read));
        align-items: center;
        min-height: calc(118px * var(--sr-u) * var(--sr-read));
      }}
      .hero {{
        display: flex; align-items: center; gap: calc(14px * var(--sr-u) * var(--sr-read));
        min-width: 0;
        padding: calc(8px * var(--sr-u) * var(--sr-read));
        border: 1px solid color-mix(in srgb, var(--sr-accent) 35%, transparent);
        background: rgba(0,0,0,0.28);
      }}
      .hero-icon-wrap {{
        position: relative;
        width: calc(78px * var(--sr-u) * var(--sr-read));
        height: calc(78px * var(--sr-u) * var(--sr-read));
        flex: 0 0 auto;
      }}
      .orbit-ring {{
        position: absolute; left: 50%; bottom: -4px; transform: translateX(-50%);
        width: 86%; height: 28%;
        border-radius: 50%;
        border: 2px solid color-mix(in srgb, var(--sr-accent) 80%, white);
        box-shadow:
          0 0 12px color-mix(in srgb, var(--sr-accent) 70%, transparent),
          inset 0 0 10px color-mix(in srgb, var(--sr-accent) 40%, transparent);
        animation: orbitPulse 3.6s ease-in-out infinite;
      }}
      @keyframes orbitPulse {{
        0%, 100% {{ opacity: 0.55; transform: translateX(-50%) scaleX(1); }}
        50% {{ opacity: 1; transform: translateX(-50%) scaleX(1.06); }}
      }}
      .hero-icon {{
        position: absolute; inset: 6% 8% 18%;
        display: flex; align-items: center; justify-content: center;
        border-radius: 12px;
        border: 2px solid color-mix(in srgb, var(--sr-platform) 80%, white);
        background: radial-gradient(circle at 40% 30%, rgba(255,255,255,0.12), rgba(0,0,0,0.55));
        box-shadow:
          0 0 18px color-mix(in srgb, var(--sr-platform) calc(var(--sr-glow) * 140%), transparent),
          inset 0 0 12px color-mix(in srgb, var(--sr-platform) 35%, transparent);
        animation: iconBreathe 4s ease-in-out infinite;
        overflow: hidden;
      }}
      .hero-icon::before {{
        content: '';
        position: absolute; inset: 0;
        background: repeating-linear-gradient(
          90deg, transparent, transparent 6px,
          color-mix(in srgb, var(--sr-platform) 25%, transparent) 7px
        );
        opacity: 0.35; mix-blend-mode: screen; pointer-events: none;
      }}
      @keyframes iconBreathe {{
        0%, 100% {{ filter: brightness(1); }}
        50% {{ filter: brightness(1.12); }}
      }}
      .hero-icon svg {{ width: 58%; height: 58%; z-index: 1; }}
      .hero-text {{ min-width: 0; flex: 1; }}
      .kicker {{
        font-family: var(--sr-font-display);
        font-size: calc(7px * var(--sr-u) * var(--sr-read));
        color: var(--sr-accent);
        letter-spacing: 0.12em;
        text-shadow: 0 0 8px color-mix(in srgb, var(--sr-accent) 60%, transparent);
        margin-bottom: 6px;
      }}
      .platform-name {{
        font-family: var(--sr-font-display);
        font-size: calc(11px * var(--sr-u) * var(--sr-read));
        color: var(--sr-platform);
        text-shadow: 0 0 10px color-mix(in srgb, var(--sr-platform) 70%, transparent);
        margin-bottom: 8px;
      }}
      .username {{
        font-family: var(--sr-font-display);
        font-size: calc(16px * var(--sr-u) * var(--sr-read));
        color: #fff;
        line-height: 1.35;
        word-break: break-word;
        text-shadow: 0 0 12px rgba(255,255,255,0.25);
        margin-bottom: 6px;
      }}
      .url {{
        font-family: 'VT323', monospace;
        font-size: calc(16px * var(--sr-u) * var(--sr-read));
        color: var(--sr-magenta);
        opacity: 0.95;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }}
      .root.hide-url .url {{ display: none; }}
      .next-box {{
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        min-width: calc(54px * var(--sr-u) * var(--sr-read));
        padding: 4px 6px;
        border-left: 1px solid color-mix(in srgb, var(--sr-accent) 40%, transparent);
        border-right: 1px solid color-mix(in srgb, var(--sr-accent) 40%, transparent);
        color: var(--sr-accent);
        text-shadow: 0 0 8px color-mix(in srgb, var(--sr-accent) 55%, transparent);
      }}
      .root.hide-countdown .next-box {{ display: none; }}
      .next-label, .next-sec {{
        font-family: var(--sr-font-display);
        font-size: calc(7px * var(--sr-u) * var(--sr-read));
        letter-spacing: 0.08em;
      }}
      .next-num {{
        font-family: 'VT323', monospace;
        font-size: calc(34px * var(--sr-u) * var(--sr-read));
        line-height: 1;
        margin: 2px 0;
      }}
      .secondary-wrap {{ min-width: 0; position: relative; }}
      .root.hide-secondary .secondary-wrap {{ display: none; }}
      .secondary {{
        display: flex; gap: calc(8px * var(--sr-u) * var(--sr-read));
        overflow-x: auto; overflow-y: hidden;
        scrollbar-width: none;
        padding-bottom: 4px;
      }}
      .secondary::-webkit-scrollbar {{ display: none; }}
      .sec-card {{
        flex: 0 0 auto;
        width: calc(78px * var(--sr-u) * var(--sr-read));
        text-align: center;
        opacity: 0.72;
        transition: opacity 0.35s ease, transform 0.35s ease;
      }}
      .sec-card.active {{ opacity: 1; transform: translateY(-2px); }}
      .sec-icon {{
        width: calc(42px * var(--sr-u) * var(--sr-read));
        height: calc(42px * var(--sr-u) * var(--sr-read));
        margin: 0 auto 6px;
        border-radius: 10px;
        border: 2px solid var(--sec-accent, var(--sr-accent));
        display: flex; align-items: center; justify-content: center;
        background: rgba(0,0,0,0.45);
        box-shadow: 0 0 10px color-mix(in srgb, var(--sec-accent, var(--sr-accent)) 45%, transparent);
      }}
      .sec-icon svg {{ width: 55%; height: 55%; }}
      .sec-name {{
        font-family: var(--sr-font-display);
        font-size: calc(6px * var(--sr-u) * var(--sr-read));
        color: #fff;
        margin-bottom: 3px;
      }}
      .sec-user {{
        font-family: 'VT323', monospace;
        font-size: calc(12px * var(--sr-u) * var(--sr-read));
        color: rgba(255,255,255,0.75);
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
      }}
      .pager-dots {{
        display: flex; justify-content: center; gap: 5px; margin-top: 4px;
      }}
      .pager-dots span {{
        width: 5px; height: 5px; border-radius: 50%;
        background: rgba(255,255,255,0.25);
      }}
      .pager-dots span.on {{ background: var(--sr-accent); box-shadow: 0 0 6px var(--sr-accent); }}
      .panel-stats {{
        position: relative; z-index: 2;
        margin-top: calc(10px * var(--sr-u) * var(--sr-read));
        display: grid;
        grid-template-columns: repeat(5, minmax(0, 1fr));
        gap: calc(6px * var(--sr-u) * var(--sr-read));
      }}
      .stat-cell {{
        min-width: 0;
        padding: calc(6px * var(--sr-u) * var(--sr-read)) calc(8px * var(--sr-u) * var(--sr-read));
        border: 1px solid color-mix(in srgb, var(--sr-accent) 40%, transparent);
        background: rgba(0,0,0,0.35);
      }}
      .stat-cell.hidden {{ display: none; }}
      .stat-label {{
        font-family: var(--sr-font-display);
        font-size: calc(6px * var(--sr-u) * var(--sr-read));
        color: var(--sr-accent);
        margin-bottom: 4px;
        letter-spacing: 0.04em;
      }}
      .stat-value {{
        font-family: 'VT323', monospace;
        font-size: calc(18px * var(--sr-u) * var(--sr-read));
        color: #fff;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
      }}
      .stat-value.big {{
        color: var(--sr-accent);
        font-size: calc(24px * var(--sr-u) * var(--sr-read));
        text-shadow: 0 0 10px color-mix(in srgb, var(--sr-accent) 50%, transparent);
      }}
      .root.glitching .hero-icon,
      .root.glitching .username,
      .root.glitching .platform-name {{
        animation: glitchSlice 0.55s steps(2, end);
      }}
      @keyframes glitchSlice {{
        0% {{ transform: translate(0,0); filter: none; }}
        20% {{ transform: translate(-3px, 1px); filter: hue-rotate(20deg); }}
        40% {{ transform: translate(3px, -1px); clip-path: inset(20% 0 40% 0); }}
        60% {{ transform: translate(-2px, 0); filter: saturate(1.4); }}
        100% {{ transform: translate(0,0); filter: none; }}
      }}
      .root.trans-data_stream .hero {{ box-shadow: inset 40px 0 40px -20px var(--sr-accent); }}
      .root.trans-energy_burst .hero-icon {{
        box-shadow: 0 0 40px var(--sr-platform), 0 0 80px var(--sr-accent);
      }}
      .root.trans-scan .scanlines {{ opacity: 0.8; }}
      .root.trans-pixel_dissolve .username {{
        filter: contrast(1.4) blur(0.4px);
        letter-spacing: 0.2em;
      }}
      .root.trans-fade .hero {{ opacity: 0.35; transition: opacity 0.35s ease; }}
      .empty {{
        font-family: var(--sr-font-display);
        font-size: calc(9px * var(--sr-u) * var(--sr-read));
        color: var(--sr-accent);
        opacity: 0.7;
        padding: 18px;
        text-align: center;
      }}
      @media (max-width: 720px) {{
        .panel-top {{ grid-template-columns: 1fr; }}
        .next-box {{ flex-direction: row; gap: 8px; border: 0; }}
        .panel-stats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      }}
      .root.narrow-xs .url {{ display: none; }}
      .root.narrow-xs .username {{
        font-size: calc(13px * var(--sr-u) * var(--sr-read));
      }}
    </style>
  </head>
  <body>
    <div id="root" class="root crt theme-neon_cyber">
      <div class="particles" id="particles"></div>
      <div class="hud-frame">
        <div class="hud-corner tl"></div>
        <div class="hud-corner tr"></div>
        <div class="hud-corner bl"></div>
        <div class="hud-corner br"></div>
        <div class="scanlines"></div>
        <div class="panel-top" id="panelTop">
          <div class="hero" id="hero">
            <div class="hero-icon-wrap">
              <div class="orbit-ring"></div>
              <div class="hero-icon" id="heroIcon"></div>
            </div>
            <div class="hero-text">
              <div class="kicker">LIVE SOCIAL</div>
              <div class="platform-name" id="platformName">—</div>
              <div class="username" id="username">—</div>
              <div class="url" id="url"></div>
            </div>
          </div>
          <div class="next-box" id="nextBox">
            <div class="next-label">NEXT</div>
            <div class="next-num" id="nextNum">00</div>
            <div class="next-sec">SEC</div>
          </div>
          <div class="secondary-wrap">
            <div class="secondary" id="secondary"></div>
            <div class="pager-dots" id="pager"></div>
          </div>
        </div>
        <div class="panel-stats" id="stats">
          <div class="stat-cell" data-stat="latest_follower">
            <div class="stat-label">LATEST FOLLOWER</div>
            <div class="stat-value" id="statFollow">—</div>
          </div>
          <div class="stat-cell" data-stat="latest_donation">
            <div class="stat-label">LATEST DONATION</div>
            <div class="stat-value" id="statDonation">—</div>
          </div>
          <div class="stat-cell" data-stat="stream_time">
            <div class="stat-label">STREAM TIME</div>
            <div class="stat-value big" id="statTime">00:00:00</div>
          </div>
          <div class="stat-cell" data-stat="top_donator">
            <div class="stat-label">TOP DONATOR</div>
            <div class="stat-value" id="statTop">—</div>
          </div>
          <div class="stat-cell" data-stat="online">
            <div class="stat-label">ONLINE</div>
            <div class="stat-value big" id="statOnline">0</div>
          </div>
        </div>
        <div class="empty" id="empty" style="display:none">AWAITING PLATFORMS</div>
      </div>
    </div>
    <script>
      (function() {{
        const PLATFORMS = {_json_for_script(platforms_meta)};
        let state = {_json_for_script(initial)};
        let config = state.config || {{}};
        let rotation = state.rotation || {{}};
        let platformsEnabled = state.platforms_enabled || [];
        let stats = state.stats || {{}};
        let lastToken = -1;
        let transitionTimer = null;
        let particles = [];
        const MAX_PARTICLES = 12;
        let clockSkew = 0;
        let secPage = 0;

        const rootEl = document.getElementById('root');
        const heroIcon = document.getElementById('heroIcon');
        const platformName = document.getElementById('platformName');
        const usernameEl = document.getElementById('username');
        const urlEl = document.getElementById('url');
        const nextNum = document.getElementById('nextNum');
        const secondaryEl = document.getElementById('secondary');
        const pagerEl = document.getElementById('pager');
        const particlesEl = document.getElementById('particles');
        const emptyEl = document.getElementById('empty');
        const panelTop = document.getElementById('panelTop');
        const statsPanel = document.getElementById('stats');

        function esc(s) {{
          return String(s || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
        }}

        function iconSvg(pid) {{
          const a = (PLATFORMS[pid] && PLATFORMS[pid].accent) || '#fff';
          const common = ' xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="' + a + '"';
          if (pid === 'twitch') return '<svg' + common + '><path d="M4 2L2 6v14h5v2h3l3-2h4l5-5V2H4zm15 11l-3 3h-4l-3 2v-2H6V4h13v9z"/><path d="M15 7h2v5h-2zm-5 0h2v5h-2z" fill="#050507"/></svg>';
          if (pid === 'youtube') return '<svg' + common + '><path d="M23 8s-.2-1.5-.8-2.2c-.8-.8-1.7-.8-2.1-.9C17.1 4.7 12 4.7 12 4.7s-5.1 0-8.1.2c-.4 0-1.3.1-2.1.9C1.2 6.5 1 8 1 8S.8 9.8.8 11.5v1c0 1.8.2 3.5.2 3.5s.2 1.5.8 2.2c.8.8 1.9.8 2.4.9 1.7.2 7.8.2 7.8.2s5.1 0 8.1-.2c.4 0 1.3-.1 2.1-.9.6-.7.8-2.2.8-2.2s.2-1.8.2-3.5v-1C23.2 9.8 23 8 23 8zM9.8 14.8V7.7l6.5 3.6-6.5 3.5z"/></svg>';
          if (pid === 'kick') return '<svg' + common + '><path d="M3 3h6v6H3zm0 12h6v6H3zm8-6h4V3h6v6h-4v2h4v6h-6v-6h-4v6H9V9h2z"/></svg>';
          if (pid === 'telegram') return '<svg' + common + '><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2zm4.7 6.9l-1.6 7.6c-.1.5-.4.6-.9.4l-2.4-1.8-1.2 1.1c-.1.1-.3.3-.6.3l.2-2.7 4.9-4.4c.2-.2 0-.3-.3-.1l-6 3.8-2.6-.8c-.6-.2-.6-.6.1-.8l10.1-3.9c.5-.1.9.1.7.7z"/></svg>';
          if (pid === 'tiktok') return '<svg' + common + '><path d="M16.5 3c.4 2.3 1.8 3.9 4 4.3v2.7c-1.4 0-2.7-.4-4-1.1v5.6c0 3.5-2.8 6.4-6.3 6.5-3.5 0-6.4-2.9-6.4-6.4S7 8.2 10.2 8.1v2.8c-1.9.1-3.4 1.6-3.4 3.5s1.6 3.4 3.5 3.4 3.4-1.5 3.5-3.4V3h2.7z"/></svg>';
          return '<svg' + common + '><circle cx="12" cy="12" r="8"/></svg>';
        }}

        function applyScale(percent) {{
          var p = Number(percent);
          if (!Number.isFinite(p)) p = Number(config.scale_percent || 100);
          if (!Number.isFinite(p)) p = 100;
          p = Math.max(40, Math.min(250, Math.round(p)));
          rootEl.style.setProperty('--sr-widget-scale', String(p / 100));
        }}

        function updateReadableScale() {{
          const w = rootEl.clientWidth || 800;
          let read = 1;
          rootEl.classList.remove('narrow-xs');
          if (w < 560) {{ read = 0.92; rootEl.classList.add('narrow-xs'); }}
          else if (w < 720) read = 0.96;
          rootEl.style.setProperty('--sr-read', String(read));
        }}

        function clearTransitionClasses() {{
          rootEl.classList.remove(
            'glitching', 'trans-glitch_morph', 'trans-data_stream',
            'trans-energy_burst', 'trans-scan', 'trans-pixel_dissolve', 'trans-fade'
          );
        }}

        function spawnParticles(n) {{
          if (config.enable_particles === false) return;
          const count = Math.min(n, Math.max(0, MAX_PARTICLES - particles.length));
          for (let i = 0; i < count; i++) {{
            const el = document.createElement('div');
            el.className = 'fx-particle';
            el.style.left = (15 + Math.random() * 70) + '%';
            el.style.top = (40 + Math.random() * 35) + '%';
            particlesEl.appendChild(el);
            particles.push(el);
            setTimeout(function() {{
              try {{ el.remove(); }} catch (e) {{}}
              particles = particles.filter(function(p) {{ return p !== el; }});
            }}, 2200);
          }}
        }}

        function playTransition(name) {{
          const t = String(name || config.transition || 'glitch_morph');
          if (transitionTimer) {{
            clearTimeout(transitionTimer);
            transitionTimer = null;
          }}
          clearTransitionClasses();
          if (t === 'fade') {{
            rootEl.classList.add('trans-fade');
            transitionTimer = setTimeout(clearTransitionClasses, 500);
            return;
          }}
          if (t === 'glitch_morph') {{
            rootEl.classList.add('glitching', 'trans-glitch_morph');
            spawnParticles(5);
            transitionTimer = setTimeout(clearTransitionClasses, 650);
            return;
          }}
          rootEl.classList.add('trans-' + t);
          if (t === 'energy_burst') spawnParticles(8);
          transitionTimer = setTimeout(clearTransitionClasses, 750);
        }}

        function activeEntry() {{
          const id = rotation.entry_id || '';
          const pid = rotation.platform_id || '';
          for (let i = 0; i < platformsEnabled.length; i++) {{
            if (platformsEnabled[i].id === id) return platformsEnabled[i];
          }}
          for (let i = 0; i < platformsEnabled.length; i++) {{
            if (platformsEnabled[i].platform === pid) return platformsEnabled[i];
          }}
          return platformsEnabled[0] || null;
        }}

        function displayUrl(entry) {{
          if (!entry) return '';
          let u = String(entry.url || '');
          return u.replace(/^https?:\\/\\//i, '');
        }}

        function renderHero() {{
          const entry = activeEntry();
          const empty = !platformsEnabled.length || !entry;
          emptyEl.style.display = empty ? 'block' : 'none';
          panelTop.style.display = empty ? 'none' : 'grid';
          if (empty) return;
          const pid = entry.platform;
          const meta = PLATFORMS[pid] || {{ name: pid.toUpperCase(), accent: '#00ffff' }};
          rootEl.style.setProperty('--sr-platform', meta.accent || '#00ffff');
          heroIcon.innerHTML = iconSvg(pid);
          platformName.textContent = meta.name || pid.toUpperCase();
          usernameEl.textContent = entry.username || '—';
          urlEl.textContent = displayUrl(entry);
          urlEl.style.display = config.show_url === false ? 'none' : '';
        }}

        function renderSecondary() {{
          const entry = activeEntry();
          const activeId = entry ? entry.id : '';
          const others = platformsEnabled.filter(function(p) {{ return p.id !== activeId; }});
          const pageSize = 4;
          const pages = Math.max(1, Math.ceil(others.length / pageSize) || 1);
          if (secPage >= pages) secPage = 0;
          const slice = others.slice(secPage * pageSize, secPage * pageSize + pageSize);
          secondaryEl.innerHTML = slice.map(function(p) {{
            const meta = PLATFORMS[p.platform] || {{ name: p.platform, accent: '#888' }};
            const activeCls = (p.id === activeId) ? ' active' : '';
            return '<div class="sec-card' + activeCls + '" style="--sec-accent:' + esc(meta.accent) + '">' +
              '<div class="sec-icon">' + iconSvg(p.platform) + '</div>' +
              '<div class="sec-name">' + esc(meta.name || p.platform) + '</div>' +
              '<div class="sec-user">' + esc(p.username) + '</div></div>';
          }}).join('');
          let dots = '';
          for (let i = 0; i < pages; i++) {{
            dots += '<span class="' + (i === secPage ? 'on' : '') + '"></span>';
          }}
          pagerEl.innerHTML = dots;
          rootEl.classList.toggle('hide-secondary', config.show_secondary_platforms === false);
        }}

        function fmtDiamond(name, value) {{
          if (!name) return '—';
          return esc(name) + ' - ' + String(value != null ? value : 0) + ' ◆';
        }}

        function fmtTime(ms) {{
          if (!ms) return '00:00:00';
          const now = Date.now() + clockSkew;
          let sec = Math.max(0, Math.floor((now - Number(ms)) / 1000));
          const h = Math.floor(sec / 3600); sec %= 3600;
          const m = Math.floor(sec / 60); const s = sec % 60;
          return String(h).padStart(2,'0') + ':' + String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
        }}

        function renderStats() {{
          const st = stats || {{}};
          document.getElementById('statFollow').textContent =
            (st.latest_follower && st.latest_follower.name) ? st.latest_follower.name : '—';
          document.getElementById('statDonation').innerHTML =
            st.latest_donation ? fmtDiamond(st.latest_donation.name, st.latest_donation.value) : '—';
          document.getElementById('statTop').innerHTML =
            st.top_donator ? fmtDiamond(st.top_donator.name, st.top_donator.value) : '—';
          document.getElementById('statOnline').textContent = String(st.viewers_total || 0);
          document.getElementById('statTime').textContent = fmtTime(st.stream_started_at_ms);
          const map = {{
            latest_follower: config.show_latest_follower !== false,
            latest_donation: config.show_latest_donation !== false,
            stream_time: config.show_stream_time !== false,
            top_donator: config.show_top_donator !== false,
            online: config.show_online !== false
          }};
          Array.prototype.forEach.call(document.querySelectorAll('.stat-cell'), function(el) {{
            const key = el.getAttribute('data-stat');
            el.classList.toggle('hidden', map[key] === false);
          }});
        }}

        function remainingMs() {{
          if (!platformsEnabled || platformsEnabled.length < 2) return 0;
          const started = Number(rotation.started_at_ms || 0);
          const interval = Number(rotation.interval_ms || config.rotation_interval_ms || 8000);
          const now = Date.now() + clockSkew;
          return Math.max(0, started + interval - now);
        }}

        function renderCountdown() {{
          const multi = platformsEnabled.length >= 2;
          rootEl.classList.toggle('hide-countdown', !multi || config.show_countdown === false);
          const sec = Math.ceil(remainingMs() / 1000);
          nextNum.textContent = String(Math.max(0, sec)).padStart(2, '0');
        }}

        function applyLook() {{
          const theme = String(config.theme || 'neon_cyber');
          rootEl.classList.remove('theme-neon_cyber','theme-synthwave','theme-toxic','theme-ice','theme-amber');
          rootEl.classList.add('theme-' + theme);
          rootEl.style.setProperty('--sr-accent', String(config.accent_color || '#00ffff'));
          rootEl.classList.toggle('crt', config.enable_crt !== false);
          rootEl.classList.toggle('hide-url', config.show_url === false);
          applyScale(config.scale_percent);
          if (config.enable_glow === false) rootEl.style.setProperty('--sr-glow', '0.08');
          else rootEl.style.setProperty('--sr-glow', '0.28');
        }}

        function applyState(st) {{
          if (!st) return;
          if (st.config) config = Object.assign(config || {{}}, st.config);
          if (st.platforms_enabled) platformsEnabled = st.platforms_enabled;
          if (st.stats) stats = st.stats;
          let transitioned = false;
          if (st.rotation) {{
            rotation = st.rotation;
            if (typeof rotation.server_now_ms === 'number' && rotation.server_now_ms > 0) {{
              clockSkew = rotation.server_now_ms - Date.now();
            }}
            const tok = Number(rotation.transition_token || 0);
            if (lastToken >= 0 && tok !== lastToken) {{
              playTransition(config.transition || 'glitch_morph');
              transitioned = true;
              secPage = 0;
            }}
            lastToken = tok;
          }}
          applyLook();
          renderHero();
          renderSecondary();
          renderStats();
          renderCountdown();
          if (!transitioned && config.enable_particles !== false && Math.random() < 0.02) {{
            spawnParticles(1);
          }}
        }}

        function handleMsg(msg) {{
          if (!msg) return;
          if (msg.op === 'state' || msg.state) applyState(msg.state || msg);
          else if (msg.patch) applyState(msg.patch);
          else applyState(msg);
        }}

        function connect() {{
          let tries = 0;
          function doConnect() {{
            tries += 1;
            const backoff = Math.min(5000, 250 + Math.floor(Math.random() * 250) + (tries * 350));
            const wsUrl = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws';
            let ws;
            try {{ ws = new WebSocket(wsUrl); }}
            catch (e) {{ setTimeout(doConnect, backoff); return; }}
            ws.onopen = function() {{
              tries = 0;
              ws.send(JSON.stringify({_json_for_script(subscribe_msg)}));
            }};
            ws.onmessage = function(ev) {{
              try {{ handleMsg(JSON.parse(ev.data)); }} catch (e) {{}}
            }};
            ws.onclose = function() {{ setTimeout(doConnect, backoff); }};
            ws.onerror = function() {{ try {{ ws.close(); }} catch (e) {{}} }};
          }}
          doConnect();
        }}

        applyState(state);
        updateReadableScale();
        setInterval(function() {{
          renderCountdown();
          if (stats && stats.stream_started_at_ms) {{
            document.getElementById('statTime').textContent = fmtTime(stats.stream_started_at_ms);
          }}
        }}, 250);
        setInterval(function() {{
          const others = platformsEnabled.filter(function(p) {{
            const a = activeEntry();
            return a && p.id !== a.id;
          }});
          if (others.length > 4) {{
            secPage = (secPage + 1) % Math.ceil(others.length / 4);
            renderSecondary();
          }}
        }}, 5000);
        window.addEventListener('resize', function() {{ updateReadableScale(); }});
        if (typeof ResizeObserver !== 'undefined') {{
          new ResizeObserver(function() {{ updateReadableScale(); }}).observe(rootEl);
        }}
        connect();
      }})();
    </script>
  </body>
</html>"""

    def initial_state(self, params: dict[str, Any]) -> dict[str, Any]:
        cfg = load_social_rotator_overlay_config()
        entries = enabled_rotation_entries(parse_platforms(cfg))
        rotation = SocialRotatorRotationEngine.from_entries(
            entries, interval_ms=cfg.rotation_interval_ms
        )
        return {
            "config": social_rotator_overlay_config_to_public_dict(cfg),
            "rotation": rotation.presentation_dict(),
            "platforms_enabled": [
                {
                    "id": e.entry_id,
                    "platform": e.platform,
                    "username": e.username,
                    "url": e.url,
                    "order": i,
                }
                for i, e in enumerate(entries)
            ],
            "stats": SocialRotatorStatsSession().to_public_dict(),
            "locale": load_ui_locale(),
        }
