from __future__ import annotations

import html
import json
from typing import Any

from stream_cheremsha import l10n
from stream_cheremsha.overlays.live_leaderboard_overlay_config import (
    live_leaderboard_overlay_config_to_public_dict,
    load_live_leaderboard_overlay_config,
)
from stream_cheremsha.overlays.live_leaderboard_ranking import LiveLeaderboardRankingEngine
from stream_cheremsha.overlays.models import normalize_instance_id
from stream_cheremsha.overlays.ui_locale import load_ui_locale

_I18N_KEYS = (
    "kicker",
    "source.likers",
    "source.gifters",
    "source.sharers",
    "source.commenters",
    "source.contributors",
    "scene.hall_of_fame",
    "scene.arena",
    "scene.energy_network",
    "empty.awaiting",
    "empty.arena",
    "fallback",
)


def _overlay_i18n_bundle() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {"uk": {}, "en": {}}
    for short in _I18N_KEYS:
        key = f"live_leaderboard.{short}"
        out["uk"][short] = l10n.tr("uk", key)
        out["en"][short] = l10n.tr("en", key)
    return out


def _json_for_script(value: Any) -> str:
    s = json.dumps(value, ensure_ascii=False)
    return s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


class LiveLeaderboardOverlayType:
    type = "live_leaderboard"

    def render_html(self, params: dict[str, Any]) -> str:
        raw_instance = params.get("instance")
        try:
            instance = normalize_instance_id(str(raw_instance or ""))
        except ValueError:
            instance = "default"

        cfg = load_live_leaderboard_overlay_config()
        cfg_dict = live_leaderboard_overlay_config_to_public_dict(cfg)
        accent = str(cfg.accent_color or "#00ffff")
        scale = max(40, min(250, int(cfg.scale_percent))) / 100.0
        locale = load_ui_locale()
        i18n = _overlay_i18n_bundle()
        pack = i18n.get(locale) or i18n["uk"]
        initial_kicker = html.escape(pack.get("kicker", "LIVE LEADERBOARD"))
        initial_source = html.escape(pack.get("source.likers", "TOP LIKERS"))
        initial_scene = html.escape(pack.get("scene.hall_of_fame", "HALL OF FAME"))
        subscribe_msg = {
            "op": "subscribe",
            "type": "live_leaderboard",
            "instance": instance,
            "params": {},
        }

        return f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Live Leaderboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=VT323&display=swap" rel="stylesheet" />
    <style>
      * {{ box-sizing: border-box; }}
      :root {{
        --ll-accent: {accent};
        --ll-magenta: #ff2bd6;
        --ll-purple: #9b5cff;
        --ll-warn: #ffe066;
        --ll-ok: #39ff88;
        --ll-bg: #050507;
        --ll-widget-scale: {scale:.4f};
        --ll-u: var(--ll-widget-scale);
        --ll-read: 1;
        --ll-glow: 0.22;
      }}
      html, body {{
        margin: 0; padding: 0; width: 100%; height: 100%;
        background: transparent; overflow: hidden;
      }}
      .root {{
        position: absolute; inset: 0;
        background: var(--ll-bg);
        font-family: 'VT323', monospace;
        color: #e0f0ff;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: calc(10px * var(--ll-u)) calc(12px * var(--ll-u));
        --ll-widget-scale: {scale:.4f};
        --ll-u: var(--ll-widget-scale);
        --ll-read: 1;
        pointer-events: none;
      }}
      .hud-frame {{
        position: absolute; inset: calc(3px * var(--ll-u));
        border: 1px solid color-mix(in srgb, var(--ll-accent) 22%, transparent);
        pointer-events: none; z-index: 2;
      }}
      .hud-corner {{
        position: absolute;
        width: calc(14px * var(--ll-u));
        height: calc(14px * var(--ll-u));
        border-color: var(--ll-accent);
        border-style: solid;
        border-width: 0;
        opacity: 0.75;
      }}
      .hud-corner.tl {{ top: 0; left: 0; border-top-width: 1px; border-left-width: 1px; }}
      .hud-corner.tr {{ top: 0; right: 0; border-top-width: 1px; border-right-width: 1px; }}
      .hud-corner.bl {{ bottom: 0; left: 0; border-bottom-width: 1px; border-left-width: 1px; }}
      .hud-corner.br {{ bottom: 0; right: 0; border-bottom-width: 1px; border-right-width: 1px; }}
      .scanlines {{
        position: absolute; inset: 0; z-index: 20; pointer-events: none;
        background: repeating-linear-gradient(
          0deg, transparent, transparent 2px, rgba(0,0,0,0.07) 2px, rgba(0,0,0,0.07) 4px
        );
        opacity: 0.35;
      }}
      .root.crt .scanlines {{ opacity: 0.48; }}
      .vignette {{
        position: absolute; inset: 0; z-index: 19; pointer-events: none;
        background: radial-gradient(ellipse at center, transparent 42%, rgba(0,0,0,0.5) 100%);
      }}
      .particles {{
        position: absolute; inset: 0; overflow: hidden; pointer-events: none; z-index: 11;
      }}
      .fx-particle {{
        position: absolute;
        width: calc(2px * var(--ll-u));
        height: calc(2px * var(--ll-u));
        border-radius: 50%;
        background: var(--ll-accent);
        box-shadow: 0 0 calc(4px * var(--ll-u)) var(--ll-accent);
        animation: pRise 2.2s linear forwards;
      }}
      .fx-particle.mag {{ background: var(--ll-magenta); box-shadow: 0 0 calc(4px * var(--ll-u)) var(--ll-magenta); }}
      @keyframes pRise {{
        0% {{ opacity: 0.85; transform: translateY(0) scale(1); }}
        100% {{ opacity: 0; transform: translateY(calc(-70px * var(--ll-u))) scale(0.4); }}
      }}
      .hdr {{
        position: relative; z-index: 5;
        width: 100%;
        text-align: center;
        flex: 0 0 auto;
        padding: calc(2px * var(--ll-u)) 0 0;
      }}
      .hdr-kicker {{
        font-family: 'Press Start 2P', monospace;
        font-size: calc(max(7px, clamp(6px, 1.1vw, 8px)) * var(--ll-u) * var(--ll-read));
        letter-spacing: calc(2px * var(--ll-u));
        color: rgba(180, 200, 220, 0.42);
      }}
      .hdr-title {{
        margin-top: calc(4px * var(--ll-u));
        font-family: 'Press Start 2P', monospace;
        font-size: calc(max(10px, clamp(9px, 2.4vw, 13px)) * var(--ll-u) * var(--ll-read));
        color: var(--ll-accent);
        text-shadow:
          0 0 calc(6px * var(--ll-u)) var(--ll-accent),
          0 0 calc(14px * var(--ll-u)) color-mix(in srgb, var(--ll-accent) 35%, transparent);
        letter-spacing: calc(1px * var(--ll-u));
        line-height: 1.35;
      }}
      .hdr-scene {{
        margin-top: calc(3px * var(--ll-u));
        font-size: calc(max(14px, clamp(12px, 2.2vw, 16px)) * var(--ll-u) * var(--ll-read));
        color: color-mix(in srgb, var(--ll-magenta) 55%, rgba(180,200,220,0.55));
        letter-spacing: calc(2px * var(--ll-u));
        opacity: 0.75;
      }}
      .stage {{
        position: relative; z-index: 4;
        flex: 1 1 auto;
        width: 100%;
        min-height: 0;
        display: flex;
        flex-direction: column;
        overflow: hidden;
      }}
      .scene {{ display: none; width: 100%; height: 100%; min-height: 0; }}
      .scene.active {{ display: flex; flex-direction: column; }}
      .root.glitching .stage {{
        animation: rxGlitch 0.42s steps(2, end);
        filter: contrast(1.15) saturate(1.25);
      }}
      @keyframes rxGlitch {{
        0% {{ transform: translate(0,0); }}
        25% {{ transform: translate(-2px,1px); }}
        50% {{ transform: translate(2px,-1px); }}
        75% {{ transform: translate(-1px,0); }}
        100% {{ transform: translate(0,0); }}
      }}
      .empty {{
        margin: auto;
        font-family: 'Press Start 2P', monospace;
        font-size: calc(clamp(7px, 1.3vw, 9px) * var(--ll-u));
        color: color-mix(in srgb, var(--ll-accent) 55%, #666);
        letter-spacing: 0.14em;
        text-align: center;
      }}

      /* —— Hall of Fame —— */
      .hof {{
        flex: 1 1 auto;
        min-height: 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: calc(10px * var(--ll-u));
        padding: calc(4px * var(--ll-u)) calc(6px * var(--ll-u)) 0;
      }}
      .hof-champ {{
        position: relative;
        flex: 0 0 auto;
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        padding-top: calc(4px * var(--ll-u));
        animation: champFloat 5.5s ease-in-out infinite;
      }}
      @keyframes champFloat {{
        0%, 100% {{ transform: translateY(0); }}
        50% {{ transform: translateY(calc(-3px * var(--ll-u))); }}
      }}
      .hof-orbit {{
        position: relative;
        width: min(calc(150px * var(--ll-u)), 42vw);
        height: min(calc(150px * var(--ll-u)), 42vw);
        display: flex;
        align-items: center;
        justify-content: center;
      }}
      .hof-orbit svg {{
        position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible;
      }}
      .orbit-ring {{
        fill: none;
        stroke: var(--ll-accent);
        stroke-width: 0.8;
        opacity: 0.35;
        transform-origin: 50% 50%;
      }}
      .orbit-ring.a {{
        stroke-dasharray: 3 5;
        animation: orbitSpin 14s linear infinite;
      }}
      .orbit-ring.b {{
        stroke: var(--ll-magenta);
        stroke-width: 0.55;
        opacity: 0.28;
        stroke-dasharray: 2 7;
        animation: orbitSpin 9s linear infinite reverse;
      }}
      .orbit-ring.c {{
        stroke: var(--ll-ok);
        stroke-width: 0.45;
        opacity: 0.22;
        animation: orbitSpin 6s linear infinite;
      }}
      @keyframes orbitSpin {{
        from {{ transform: rotate(0deg); }}
        to {{ transform: rotate(360deg); }}
      }}
      .av-wrap {{
        position: relative;
        border-radius: 50%;
        overflow: hidden;
        background: #0a0c12;
        flex-shrink: 0;
      }}
      .av-wrap::after {{
        content: '';
        position: absolute; inset: 0;
        border-radius: 50%;
        border: 1px solid color-mix(in srgb, var(--ll-accent) 55%, transparent);
        box-shadow:
          0 0 calc(10px * var(--ll-u)) color-mix(in srgb, var(--ll-accent) 35%, transparent),
          inset 0 0 calc(8px * var(--ll-u)) color-mix(in srgb, var(--ll-accent) 12%, transparent);
        pointer-events: none;
      }}
      .av-wrap.champ {{
        width: 55%; height: 55%;
        box-shadow: 0 0 calc(22px * var(--ll-u)) color-mix(in srgb, var(--ll-accent) 40%, transparent);
        animation: breathAura 3.2s ease-in-out infinite;
      }}
      .av-wrap.mid {{
        width: calc(max(40px, clamp(36px, 7vw, 52px)) * var(--ll-u) * var(--ll-read));
        height: calc(max(40px, clamp(36px, 7vw, 52px)) * var(--ll-u) * var(--ll-read));
        box-shadow: 0 0 calc(10px * var(--ll-u)) color-mix(in srgb, var(--ll-ok) 28%, transparent);
      }}
      .av-wrap.mid::after {{ border-color: color-mix(in srgb, var(--ll-ok) 50%, transparent); }}
      .av-wrap.sm {{
        width: calc(max(22px, clamp(18px, 3.2vw, 24px)) * var(--ll-u) * var(--ll-read));
        height: calc(max(22px, clamp(18px, 3.2vw, 24px)) * var(--ll-u) * var(--ll-read));
        opacity: 0.9;
      }}
      .av-wrap.sm::after {{ border-color: color-mix(in srgb, var(--ll-accent) 28%, transparent); box-shadow: none; }}
      @keyframes breathAura {{
        0%, 100% {{ box-shadow: 0 0 calc(16px * var(--ll-u)) color-mix(in srgb, var(--ll-accent) 32%, transparent); }}
        50% {{ box-shadow: 0 0 calc(26px * var(--ll-u)) color-mix(in srgb, var(--ll-accent) 52%, transparent); }}
      }}
      .av-wrap img, .av-ph {{
        width: 100%; height: 100%;
        object-fit: cover;
        display: block;
        border-radius: 50%;
      }}
      .av-ph {{
        background: radial-gradient(circle at 35% 30%, color-mix(in srgb, var(--ll-accent) 35%, #222), #0a0c12 70%);
      }}
      .hof-rank {{
        margin-top: calc(6px * var(--ll-u));
        font-family: 'Press Start 2P', monospace;
        font-size: calc(max(10px, clamp(8px, 1.6vw, 11px)) * var(--ll-u) * var(--ll-read));
        color: var(--ll-warn);
        text-shadow: 0 0 calc(8px * var(--ll-u)) color-mix(in srgb, var(--ll-warn) 45%, transparent);
        letter-spacing: 0.12em;
      }}
      .hof-name {{
        margin-top: calc(4px * var(--ll-u));
        font-family: 'Press Start 2P', monospace;
        font-size: calc(max(11px, clamp(8px, 1.8vw, 11px)) * var(--ll-u) * var(--ll-read));
        color: #f0fffb;
        max-width: min(92%, calc(280px * var(--ll-u)));
        overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
      }}
      .hof-val {{
        margin-top: calc(4px * var(--ll-u));
        font-family: 'Press Start 2P', monospace;
        font-size: calc(max(20px, clamp(16px, 4.5vw, 26px)) * var(--ll-u) * var(--ll-read));
        color: var(--ll-accent);
        text-shadow:
          0 0 calc(8px * var(--ll-u)) var(--ll-accent),
          0 0 calc(18px * var(--ll-u)) color-mix(in srgb, var(--ll-accent) 30%, transparent);
        letter-spacing: calc(1px * var(--ll-u));
      }}
      .hof-duo {{
        flex: 0 0 auto;
        width: 100%;
        max-width: min(100%, calc(420px * var(--ll-u)));
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: calc(18px * var(--ll-u));
        align-items: start;
        padding: 0 calc(8px * var(--ll-u));
      }}
      .hof-side {{
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        gap: calc(3px * var(--ll-u));
        min-width: 0;
      }}
      .hof-side .rk {{
        font-family: 'Press Start 2P', monospace;
        font-size: calc(max(9px, clamp(7px, 1.2vw, 9px)) * var(--ll-u) * var(--ll-read));
        color: var(--ll-ok);
        text-shadow: 0 0 calc(6px * var(--ll-u)) color-mix(in srgb, var(--ll-ok) 35%, transparent);
      }}
      .hof-side .nm {{
        font-family: 'Press Start 2P', monospace;
        font-size: calc(max(9px, clamp(6px, 1.1vw, 8px)) * var(--ll-u) * var(--ll-read));
        color: rgba(230, 245, 255, 0.88);
        max-width: 100%;
        overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
      }}
      .hof-side .vl {{
        font-size: calc(max(17px, clamp(14px, 2.6vw, 20px)) * var(--ll-u) * var(--ll-read));
        color: color-mix(in srgb, var(--ll-accent) 85%, white);
        text-shadow: 0 0 calc(6px * var(--ll-u)) color-mix(in srgb, var(--ll-accent) 25%, transparent);
      }}
      .hof-strip, .arena-strip {{
        flex: 1 1 auto;
        min-height: 0;
        width: 100%;
        max-width: min(100%, calc(440px * var(--ll-u)));
        overflow: hidden;
        padding-top: calc(4px * var(--ll-u));
        border-top: 1px solid color-mix(in srgb, var(--ll-accent) 12%, transparent);
        position: relative;
      }}
      .strip-viewport {{
        height: 100%;
        min-height: 0;
        overflow: hidden;
        position: relative;
      }}
      .strip-track {{
        will-change: transform;
        transform: translate3d(0, 0, 0);
      }}
      .strip-row {{
        display: grid;
        grid-template-columns: calc(38px * var(--ll-u) * var(--ll-read)) auto 1fr auto;
        gap: calc(8px * var(--ll-u));
        align-items: center;
        padding: calc(5px * var(--ll-u) * var(--ll-read)) calc(4px * var(--ll-u));
        font-size: calc(max(15px, clamp(13px, 2.1vw, 17px)) * var(--ll-u) * var(--ll-read));
      }}
      .strip-row .rk {{
        font-family: 'Press Start 2P', monospace;
        font-size: calc(max(8px, clamp(6px, 1vw, 8px)) * var(--ll-u) * var(--ll-read));
        color: rgba(180, 200, 220, 0.7);
      }}
      .strip-row .nm {{
        color: rgba(220, 235, 250, 0.88);
        overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        letter-spacing: 0.03em;
      }}
      .strip-row .vl {{
        color: color-mix(in srgb, var(--ll-accent) 80%, #9ab);
        font-variant-numeric: tabular-nums;
        font-size: 1.05em;
      }}
      .strip-row.rank-flash .rk,
      .hof-side.rank-flash .rk,
      .hof-champ.rank-flash .hof-rank {{
        color: var(--ll-warn);
        animation: rankPulse 0.7s ease;
      }}
      @keyframes rankPulse {{
        0% {{ filter: brightness(1); }}
        40% {{ filter: brightness(1.7); }}
        100% {{ filter: brightness(1); }}
      }}

      /* Narrow / mobile readability: raise floors without new layout */
      .root.narrow {{
        --ll-read: 1.22;
      }}
      .root.narrow-xs {{
        --ll-read: 1.34;
      }}
      .root.narrow .hof-orbit {{
        width: min(calc(160px * var(--ll-u) * var(--ll-read)), 58%);
        height: min(calc(160px * var(--ll-u) * var(--ll-read)), 58%);
      }}
      .root.narrow .fighter .av-wrap.champ {{
        width: calc(max(64px, clamp(56px, 12vw, 84px)) * var(--ll-u) * var(--ll-read));
        height: calc(max(64px, clamp(56px, 12vw, 84px)) * var(--ll-u) * var(--ll-read));
      }}
      .root.narrow .fighter .nm,
      .root.narrow .fighter .rk {{
        font-size: calc(max(9px, 8px) * var(--ll-u) * var(--ll-read));
      }}
      .root.narrow .fighter .vl {{
        font-size: calc(max(18px, clamp(14px, 2.8vw, 22px)) * var(--ll-u) * var(--ll-read));
      }}
      .root.narrow .fighter.f1 .vl {{
        font-size: calc(max(14px, clamp(12px, 2.6vw, 18px)) * var(--ll-u) * var(--ll-read));
      }}

      /* —— Arena —— */
      .arena {{
        flex: 1 1 auto;
        min-height: 0;
        display: flex;
        flex-direction: column;
        width: 100%;
      }}
      .arena-field {{
        position: relative;
        flex: 1 1 auto;
        min-height: calc(160px * var(--ll-u));
        overflow: hidden;
      }}
      .arena-glow {{
        position: absolute;
        left: 50%; top: 58%;
        width: min(70%, calc(320px * var(--ll-u)));
        height: min(55%, calc(160px * var(--ll-u)));
        transform: translate(-50%, -50%);
        background: radial-gradient(ellipse at center,
          color-mix(in srgb, var(--ll-accent) 18%, transparent) 0%,
          color-mix(in srgb, var(--ll-purple) 8%, transparent) 42%,
          transparent 72%);
        pointer-events: none;
        animation: fieldPulse 4s ease-in-out infinite;
      }}
      @keyframes fieldPulse {{
        0%, 100% {{ opacity: 0.7; transform: translate(-50%, -50%) scale(1); }}
        50% {{ opacity: 1; transform: translate(-50%, -50%) scale(1.04); }}
      }}
      .arena-floor {{
        position: absolute;
        left: 50%; bottom: 8%;
        width: min(78%, calc(360px * var(--ll-u)));
        height: 1px;
        transform: translateX(-50%);
        background: linear-gradient(90deg,
          transparent,
          color-mix(in srgb, var(--ll-accent) 35%, transparent) 20%,
          color-mix(in srgb, var(--ll-accent) 55%, transparent) 50%,
          color-mix(in srgb, var(--ll-accent) 35%, transparent) 80%,
          transparent);
        box-shadow: 0 0 calc(12px * var(--ll-u)) color-mix(in srgb, var(--ll-accent) 25%, transparent);
      }}
      .fighter {{
        position: absolute;
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        gap: calc(3px * var(--ll-u));
        transition: left 0.55s ease, top 0.55s ease, transform 0.55s ease;
        min-width: 0;
      }}
      .fighter.f1 {{
        left: 50%; top: 10%;
        transform: translateX(-50%);
        z-index: 3;
      }}
      .fighter.f2 {{
        left: 16%; top: 42%;
        z-index: 2;
      }}
      .fighter.f3 {{
        right: 16%; left: auto; top: 42%;
        z-index: 2;
      }}
      .fighter .plat {{
        position: absolute;
        bottom: calc(-6px * var(--ll-u));
        width: calc(48px * var(--ll-u));
        height: calc(10px * var(--ll-u));
        border-radius: 50%;
        border: 1px solid color-mix(in srgb, var(--ll-accent) 30%, transparent);
        box-shadow: 0 0 calc(10px * var(--ll-u)) color-mix(in srgb, var(--ll-accent) 18%, transparent);
        opacity: 0.7;
      }}
      .fighter.f1 .plat {{
        width: calc(70px * var(--ll-u));
        height: calc(14px * var(--ll-u));
        border-color: color-mix(in srgb, var(--ll-warn) 40%, transparent);
        box-shadow: 0 0 calc(14px * var(--ll-u)) color-mix(in srgb, var(--ll-warn) 25%, transparent);
      }}
      .fighter .rk {{
        font-family: 'Press Start 2P', monospace;
        font-size: calc(max(9px, clamp(7px, 1.3vw, 9px)) * var(--ll-u) * var(--ll-read));
        color: var(--ll-magenta);
        text-shadow: 0 0 calc(6px * var(--ll-u)) color-mix(in srgb, var(--ll-magenta) 40%, transparent);
      }}
      .fighter.f1 .rk {{ color: var(--ll-warn); }}
      .fighter .nm {{
        font-family: 'Press Start 2P', monospace;
        font-size: calc(max(9px, clamp(6px, 1.1vw, 8px)) * var(--ll-u) * var(--ll-read));
        color: #eef8ff;
        max-width: calc(120px * var(--ll-u) * var(--ll-read));
        overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
      }}
      .fighter.f1 .nm {{ font-size: calc(max(10px, clamp(7px, 1.3vw, 9px)) * var(--ll-u) * var(--ll-read)); }}
      .fighter .vl {{
        font-size: calc(max(17px, clamp(14px, 2.8vw, 22px)) * var(--ll-u) * var(--ll-read));
        color: var(--ll-accent);
        text-shadow: 0 0 calc(8px * var(--ll-u)) color-mix(in srgb, var(--ll-accent) 35%, transparent);
      }}
      .fighter.f1 .vl {{
        font-family: 'Press Start 2P', monospace;
        font-size: calc(max(13px, clamp(12px, 2.6vw, 18px)) * var(--ll-u) * var(--ll-read));
      }}
      .fighter .av-wrap.champ {{
        width: calc(max(58px, clamp(56px, 12vw, 84px)) * var(--ll-u) * var(--ll-read));
        height: calc(max(58px, clamp(56px, 12vw, 84px)) * var(--ll-u) * var(--ll-read));
      }}
      .arena-strip {{
        flex: 0 1 auto;
        max-height: 36%;
        min-height: 0;
      }}

      /* —— Energy Network —— */
      .net-wrap {{
        position: relative;
        flex: 1 1 auto;
        width: 100%;
        height: 100%;
        min-height: 0;
      }}
      .net-wrap canvas {{ width: 100%; height: 100%; display: block; }}

      .root.intensity-low {{ --ll-glow: 0.14; }}
      .root.intensity-low .scanlines {{ opacity: 0.18; }}
      .root.intensity-medium {{ --ll-glow: 0.22; }}
      .root.intensity-high {{ --ll-glow: 0.34; }}
      .root.intensity-high .scanlines {{ opacity: 0.55; }}
    </style>
  </head>
  <body>
    <div id="root" class="root crt">
      <div class="hud-frame">
        <div class="hud-corner tl"></div>
        <div class="hud-corner tr"></div>
        <div class="hud-corner bl"></div>
        <div class="hud-corner br"></div>
      </div>
      <div class="scanlines" id="scan"></div>
      <div class="vignette"></div>
      <div class="particles" id="particles"></div>
      <div class="hdr">
        <div class="hdr-kicker" id="hdrKicker">{initial_kicker}</div>
        <div class="hdr-title" id="hdrTitle">{initial_source}</div>
        <div class="hdr-scene" id="hdrScene">{initial_scene}</div>
      </div>
      <div class="stage" id="stage">
        <div class="scene active" id="sceneHof"></div>
        <div class="scene" id="sceneArena"></div>
        <div class="scene" id="sceneNet"><div class="net-wrap"><canvas id="netCanvas"></canvas></div></div>
      </div>
    </div>
    <script>
      (function() {{
        let config = {_json_for_script(cfg_dict)};
        let locale = {_json_for_script(locale)};
        const I18N = {_json_for_script(i18n)};
        function tr(key) {{
          const pack = I18N[locale] || I18N.uk || {{}};
          if (pack[key]) return pack[key];
          if (I18N.uk && I18N.uk[key]) return I18N.uk[key];
          return key;
        }}
        function sourceLabel(id) {{
          return tr('source.' + id) || tr('fallback');
        }}
        function sceneLabel(id) {{
          return tr('scene.' + id) || '';
        }}

        let rankings = {{ likers: [], gifters: [], sharers: [], commenters: [], contributors: [] }};
        let presentation = {{
          source_id: 'likers',
          scene_id: 'hall_of_fame',
          sequence_index: 0,
          scene_started_at_ms: 0,
          scene_duration_ms: 8000,
          transition_token: 0,
          server_now_ms: 0
        }};
        let lastTransitionToken = -1;
        let displayValues = {{}};
        let lastRanks = {{}};
        let particles = [];
        const MAX_PARTICLES = 20;
        let netAnim = null;
        let netNodes = [];
        let netPulses = [];
        let avatarCache = {{}};
        let lastDomSig = '';
        let stripScrollers = [];
        let stripRaf = 0;

        const rootEl = document.getElementById('root');
        const hdrKicker = document.getElementById('hdrKicker');
        const hdrTitle = document.getElementById('hdrTitle');
        const hdrScene = document.getElementById('hdrScene');
        const sceneHof = document.getElementById('sceneHof');
        const sceneArena = document.getElementById('sceneArena');
        const sceneNet = document.getElementById('sceneNet');
        const particlesEl = document.getElementById('particles');
        const netCanvas = document.getElementById('netCanvas');
        const netCtx = netCanvas.getContext('2d');

        function applyScale(percent) {{
          var p = Number(percent);
          if (!Number.isFinite(p)) p = Number(config.scale_percent || 100);
          if (!Number.isFinite(p)) p = 100;
          p = Math.max(40, Math.min(250, Math.round(p)));
          rootEl.style.setProperty('--ll-widget-scale', String(p / 100));
        }}

        function applyLook(st) {{
          st = st || {{}};
          if (st.config) config = Object.assign(config || {{}}, st.config);
          const accent = String(
            (st.accent_color != null ? st.accent_color : null) ||
            (config && config.accent_color) || '#00ffff'
          );
          rootEl.style.setProperty('--ll-accent', accent);
          rootEl.classList.toggle('crt', (st.enable_crt !== undefined ? st.enable_crt : config.enable_crt) !== false);
          rootEl.classList.remove('intensity-low', 'intensity-medium', 'intensity-high');
          const inten = String(
            (st.animation_intensity != null ? st.animation_intensity : null) ||
            (config && config.animation_intensity) || 'medium'
          );
          rootEl.classList.add('intensity-' + inten);
          applyScale(st.scale_percent !== undefined ? st.scale_percent : (config && config.scale_percent));
        }}

        function fmt(n) {{
          const v = Math.round(Number(n) || 0);
          if (v >= 1000000) return (v / 1000000).toFixed(1).replace(/\\.0$/, '') + 'M';
          if (v >= 10000) return (v / 1000).toFixed(1).replace(/\\.0$/, '') + 'K';
          return String(v).replace(/\\B(?=(\\d{{3}})+(?!\\d))/g, ',');
        }}

        function esc(s) {{
          return String(s || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
        }}

        function currentLeaders() {{
          const src = presentation.source_id || 'likers';
          const list = (rankings && rankings[src]) ? rankings[src] : [];
          return Array.isArray(list) ? list : [];
        }}

        function tweenKey(row) {{
          return String(row.key || row.user || '');
        }}

        function displayValueFor(row) {{
          const k = tweenKey(row);
          if (displayValues[k] === undefined) displayValues[k] = Number(row.value) || 0;
          const target = Number(row.value) || 0;
          const cur = displayValues[k];
          const next = cur + (target - cur) * 0.22;
          displayValues[k] = Math.abs(target - next) < 0.5 ? target : next;
          return displayValues[k];
        }}

        function avatarHtml(url, sizeClass) {{
          const u = (url || '').trim();
          if (!u) return '<div class="av-wrap ' + sizeClass + '"><div class="av-ph"></div></div>';
          return '<div class="av-wrap ' + sizeClass + '"><img src="' + u.replace(/"/g, '') + '" alt="" /></div>';
        }}

        function orbitSvg() {{
          return '<svg viewBox="0 0 100 100" aria-hidden="true">' +
            '<circle class="orbit-ring a" cx="50" cy="50" r="46" />' +
            '<circle class="orbit-ring b" cx="50" cy="50" r="38" />' +
            '<circle class="orbit-ring c" cx="50" cy="50" r="30" />' +
            '</svg>';
        }}

        function stripMarkup(list) {{
          return '<div class="strip-viewport"><div class="strip-track">' + stripRows(list) + '</div></div>';
        }}

        function stripRows(list) {{
          let html = '';
          list.forEach(function(row) {{
            html += '<div class="strip-row" data-k="' + esc(tweenKey(row)) + '">' +
              '<div class="rk">#' + String(row.rank).padStart(2, '0') + '</div>' +
              avatarHtml(row.avatar_url, 'sm') +
              '<div class="nm">' + esc(row.user) + '</div>' +
              '<div class="vl" data-val="1">' + fmt(displayValueFor(row)) + '</div></div>';
          }});
          return html;
        }}

        function stopStripScrollers() {{
          if (stripRaf) {{
            cancelAnimationFrame(stripRaf);
            stripRaf = 0;
          }}
          stripScrollers = [];
        }}

        function syncStripScrollers() {{
          stopStripScrollers();
          const nodes = rootEl.querySelectorAll('.strip-viewport');
          nodes.forEach(function(viewport) {{
            const track = viewport.querySelector('.strip-track');
            if (!track) return;
            const overflow = track.scrollHeight - viewport.clientHeight;
            if (overflow <= 4) {{
              track.style.transform = 'translate3d(0,0,0)';
              return;
            }}
            stripScrollers.push({{
              viewport: viewport,
              track: track,
              overflow: overflow,
              y: 0,
              dir: 1,
              pauseUntil: performance.now() + 1600,
              speed: Math.max(12, Math.min(28, overflow * 0.035))
            }});
          }});
          if (stripScrollers.length) stripRaf = requestAnimationFrame(tickStripScroll);
        }}

        function tickStripScroll(now) {{
          stripRaf = 0;
          let active = false;
          stripScrollers.forEach(function(sc) {{
            const overflow = sc.track.scrollHeight - sc.viewport.clientHeight;
            if (overflow <= 4) {{
              sc.y = 0;
              sc.track.style.transform = 'translate3d(0,0,0)';
              return;
            }}
            sc.overflow = overflow;
            active = true;
            if (now < sc.pauseUntil) {{
              sc.track.style.transform = 'translate3d(0,' + (-sc.y) + 'px,0)';
              return;
            }}
            const dt = Math.min(0.05, (sc._last ? (now - sc._last) : 16) / 1000);
            sc._last = now;
            sc.y += sc.dir * sc.speed * dt;
            if (sc.y >= sc.overflow) {{
              sc.y = sc.overflow;
              sc.dir = -1;
              sc.pauseUntil = now + 1600;
            }} else if (sc.y <= 0) {{
              sc.y = 0;
              sc.dir = 1;
              sc.pauseUntil = now + 1600;
            }}
            sc.track.style.transform = 'translate3d(0,' + (-sc.y) + 'px,0)';
          }});
          if (active) stripRaf = requestAnimationFrame(tickStripScroll);
        }}

        function updateReadableScale() {{
          const w = rootEl.clientWidth || 0;
          const h = rootEl.clientHeight || 0;
          // Prefer container size; boost readability as width shrinks (do not shrink text with vw).
          let read = 1;
          if (w > 0 && w < 560) read = 1.1;
          if (w > 0 && w < 440) read = 1.22;
          if (w > 0 && w < 360) read = 1.34;
          if (w > 0 && w < 300) read = 1.42;
          // Tall portrait boxes: a bit more reading size.
          if (w > 0 && h > 0 && h / Math.max(w, 1) > 1.45 && w < 480) {{
            read = Math.max(read, 1.28);
          }}
          rootEl.style.setProperty('--ll-read', String(read));
          rootEl.classList.toggle('narrow', w > 0 && w < 480);
          rootEl.classList.toggle('narrow-xs', w > 0 && w < 340);
        }}

        function leadersSig(list) {{
          return (presentation.scene_id || '') + '|' + (presentation.source_id || '') + '|' +
            list.map(function(r) {{ return tweenKey(r) + ':' + r.rank; }}).join(',');
        }}

        function tickDisplayedValues(list) {{
          list.forEach(function(row) {{
            const k = tweenKey(row);
            const val = displayValueFor(row);
            const nodes = rootEl.querySelectorAll('[data-k="' + String(k).replace(/"/g, '') + '"]');
            nodes.forEach(function(el) {{
              const vl = el.querySelector('.vl, .hof-val, [data-val="1"]');
              if (vl) vl.textContent = fmt(val);
              if (el.classList.contains('hof-champ')) {{
                const hv = el.querySelector('.hof-val');
                if (hv) hv.textContent = fmt(val);
              }}
            }});
          }});
          // Network labels refresh via drawNet loop using displayValues.
        }}

        function renderHof(list) {{
          if (!list.length) {{
            sceneHof.innerHTML = '<div class="empty">' + esc(tr('empty.awaiting')) + '</div>';
            return;
          }}
          const lead = list[0];
          const s2 = list[1];
          const s3 = list[2];
          let html = '<div class="hof">';
          html += '<div class="hof-champ" data-k="' + esc(tweenKey(lead)) + '">' +
            '<div class="hof-orbit">' + orbitSvg() + avatarHtml(lead.avatar_url, 'champ') + '</div>' +
            '<div class="hof-rank">#01</div>' +
            '<div class="hof-name">' + esc(lead.user) + '</div>' +
            '<div class="hof-val">' + fmt(displayValueFor(lead)) + '</div></div>';
          if (s2 || s3) {{
            html += '<div class="hof-duo">';
            [s2, s3].forEach(function(row) {{
              if (!row) {{
                html += '<div class="hof-side"></div>';
                return;
              }}
              html += '<div class="hof-side" data-k="' + esc(tweenKey(row)) + '">' +
                '<div class="rk">#' + String(row.rank).padStart(2, '0') + '</div>' +
                avatarHtml(row.avatar_url, 'mid') +
                '<div class="nm">' + esc(row.user) + '</div>' +
                '<div class="vl">' + fmt(displayValueFor(row)) + '</div></div>';
            }});
            html += '</div>';
          }}
          if (list.length > 3) {{
            html += '<div class="hof-strip">' + stripMarkup(list.slice(3)) + '</div>';
          }}
          html += '</div>';
          sceneHof.innerHTML = html;
          maybeRankFlash(list);
          requestAnimationFrame(syncStripScrollers);
        }}

        function renderArena(list) {{
          if (!list.length) {{
            sceneArena.innerHTML = '<div class="empty">' + esc(tr('empty.arena')) + '</div>';
            return;
          }}
          function fighter(row, cls, rk) {{
            if (!row) return '';
            const av = cls === 'f1' ? 'champ' : 'mid';
            return '<div class="fighter ' + cls + '" data-k="' + esc(tweenKey(row)) + '">' +
              '<div class="rk">' + rk + '</div>' +
              avatarHtml(row.avatar_url, av) +
              '<div class="plat"></div>' +
              '<div class="nm">' + esc(row.user) + '</div>' +
              '<div class="vl">' + fmt(displayValueFor(row)) + '</div></div>';
          }}
          let html = '<div class="arena"><div class="arena-field">' +
            '<div class="arena-glow"></div><div class="arena-floor"></div>' +
            fighter(list[0], 'f1', '#01') +
            fighter(list[1], 'f2', '#02') +
            fighter(list[2], 'f3', '#03') +
            '</div>';
          if (list.length > 3) {{
            html += '<div class="arena-strip">' + stripMarkup(list.slice(3)) + '</div>';
          }}
          html += '</div>';
          sceneArena.innerHTML = html;
          maybeRankFlash(list);
          requestAnimationFrame(syncStripScrollers);
        }}

        function loadAvatar(url, cb) {{
          const u = (url || '').trim();
          if (!u) {{ cb(null); return; }}
          if (avatarCache[u] === false) {{ cb(null); return; }}
          if (avatarCache[u] instanceof HTMLImageElement) {{
            if (avatarCache[u].complete) cb(avatarCache[u]);
            else avatarCache[u].addEventListener('load', function() {{ cb(avatarCache[u]); }});
            return;
          }}
          const img = new Image();
          img.crossOrigin = 'anonymous';
          avatarCache[u] = img;
          img.onload = function() {{ cb(img); }};
          img.onerror = function() {{ avatarCache[u] = false; cb(null); }};
          img.src = u;
        }}

        function layoutNet(list) {{
          const wrap = sceneNet.querySelector('.net-wrap');
          const w = (wrap && wrap.clientWidth) || netCanvas.clientWidth || 400;
          const h = (wrap && wrap.clientHeight) || netCanvas.clientHeight || 260;
          if (netCanvas.width !== w || netCanvas.height !== h) {{
            netCanvas.width = w;
            netCanvas.height = h;
          }}
          const n = Math.min(list.length, 10);
          const cx = w * 0.5;
          const cy = h * 0.42;
          const prev = {{}};
          netNodes.forEach(function(node) {{ prev[node.key] = node; }});
          netNodes = [];
          for (let i = 0; i < n; i++) {{
            const row = list[i];
            let x, y;
            if (i === 0) {{ x = cx; y = cy * 0.85; }}
            else if (i <= 3) {{
              const ang = Math.PI * 0.2 + (i - 1) * (Math.PI * 0.6 / Math.max(1, Math.min(2, n - 2)));
              const rad = Math.min(w, h) * 0.30;
              x = cx + Math.cos(ang - Math.PI / 2) * rad;
              y = cy + Math.sin(ang - Math.PI / 2) * rad * 0.9 + h * 0.02;
            }} else {{
              const count = n - 4;
              const idx = i - 4;
              const ang = (idx / Math.max(1, count)) * Math.PI * 1.5 - Math.PI * 0.75;
              const rad = Math.min(w, h) * 0.42;
              x = cx + Math.cos(ang) * rad;
              y = cy + Math.sin(ang) * rad * 0.78 + h * 0.08;
            }}
            const size = i === 0 ? Math.min(w, h) * 0.075 : (i < 3 ? Math.min(w, h) * 0.048 : Math.min(w, h) * 0.032);
            const key = tweenKey(row);
            const old = prev[key];
            netNodes.push({{
              key: key,
              user: row.user,
              value: Number(row.value) || 0,
              avatar_url: row.avatar_url || '',
              rank: row.rank,
              x: old ? old.x : x,
              y: old ? old.y : y,
              tx: x, ty: y,
              size: size,
              phase: i * 0.85,
              img: null
            }});
            loadAvatar(row.avatar_url, function(img) {{
              const node = netNodes.find(function(nn) {{ return nn.key === key; }});
              if (node) node.img = img;
            }});
          }}
          if (netPulses.length > 8) netPulses = netPulses.slice(-4);
        }}

        function drawNet(t) {{
          const w = netCanvas.width, h = netCanvas.height;
          netCtx.clearRect(0, 0, w, h);
          if (!netNodes.length) return;

          const accent = getComputedStyle(rootEl).getPropertyValue('--ll-accent').trim() || '#00ffff';
          const ok = '#39ff88';
          const mag = '#ff2bd6';
          const purple = '#9b5cff';

          // ambient field
          const g = netCtx.createRadialGradient(w * 0.5, h * 0.42, 4, w * 0.5, h * 0.42, Math.min(w, h) * 0.45);
          g.addColorStop(0, 'rgba(0,255,255,0.07)');
          g.addColorStop(0.55, 'rgba(155,92,255,0.04)');
          g.addColorStop(1, 'rgba(0,0,0,0)');
          netCtx.fillStyle = g;
          netCtx.fillRect(0, 0, w, h);

          // soft orbit rings around hub
          if (netNodes[0]) {{
            const hub = netNodes[0];
            for (let r = 0; r < 3; r++) {{
              netCtx.beginPath();
              netCtx.strokeStyle = r === 1 ? 'rgba(255,43,214,0.12)' : 'rgba(0,255,255,0.10)';
              netCtx.lineWidth = 1;
              netCtx.setLineDash(r === 0 ? [3, 6] : [2, 8]);
              netCtx.arc(hub.x, hub.y, hub.size * (2.2 + r * 0.85), 0, Math.PI * 2);
              netCtx.stroke();
            }}
            netCtx.setLineDash([]);
          }}

          // settle positions gently
          netNodes.forEach(function(node) {{
            node.x += (node.tx - node.x) * 0.06;
            node.y += (node.ty - node.y) * 0.06;
            node.x += Math.cos(t * 0.00055 + node.phase) * 0.35;
            node.y += Math.sin(t * 0.0007 + node.phase) * 0.28;
          }});

          // connections hub → others
          for (let i = 1; i < netNodes.length; i++) {{
            const a = netNodes[0], b = netNodes[i];
            const alpha = i < 3 ? 0.28 : 0.14;
            netCtx.strokeStyle = i < 3 ? 'rgba(0,255,255,' + alpha + ')' : 'rgba(155,92,255,' + (alpha) + ')';
            netCtx.lineWidth = i < 3 ? 1.25 : 0.8;
            netCtx.beginPath();
            netCtx.moveTo(a.x, a.y);
            const mx = (a.x + b.x) / 2 + Math.sin(t * 0.001 + i) * 6;
            const my = (a.y + b.y) / 2 + Math.cos(t * 0.0012 + i) * 4;
            netCtx.quadraticCurveTo(mx, my, b.x, b.y);
            netCtx.stroke();
          }}
          // faint links among #2/#3
          if (netNodes.length >= 3) {{
            netCtx.strokeStyle = 'rgba(57,255,136,0.14)';
            netCtx.lineWidth = 0.8;
            netCtx.beginPath();
            netCtx.moveTo(netNodes[1].x, netNodes[1].y);
            netCtx.lineTo(netNodes[2].x, netNodes[2].y);
            netCtx.stroke();
          }}
          if (netNodes.length >= 4) {{
            netCtx.beginPath();
            netCtx.moveTo(netNodes[2].x, netNodes[2].y);
            netCtx.lineTo(netNodes[3].x, netNodes[3].y);
            netCtx.stroke();
          }}

          // spawn occasional pulses
          if (config.enable_particles !== false && netNodes.length > 1 && Math.random() < 0.02 && netPulses.length < 6) {{
            const ti = 1 + Math.floor(Math.random() * (netNodes.length - 1));
            netPulses.push({{ from: 0, to: ti, u: 0, speed: 0.008 + Math.random() * 0.006 }});
          }}
          netPulses = netPulses.filter(function(p) {{
            p.u += p.speed;
            if (p.u > 1) return false;
            const a = netNodes[p.from], b = netNodes[p.to];
            if (!a || !b) return false;
            const mx = (a.x + b.x) / 2;
            const my = (a.y + b.y) / 2;
            const t1 = 1 - p.u;
            const x = t1 * t1 * a.x + 2 * t1 * p.u * mx + p.u * p.u * b.x;
            const y = t1 * t1 * a.y + 2 * t1 * p.u * my + p.u * p.u * b.y;
            netCtx.beginPath();
            netCtx.fillStyle = mag;
            netCtx.shadowColor = mag;
            netCtx.shadowBlur = 8;
            netCtx.arc(x, y, 2.2, 0, Math.PI * 2);
            netCtx.fill();
            netCtx.shadowBlur = 0;
            return true;
          }});

          // sparse ambient dust
          if (config.enable_particles !== false) {{
            for (let d = 0; d < 8; d++) {{
              const px = (Math.sin(t * 0.0003 + d * 1.7) * 0.5 + 0.5) * w;
              const py = (Math.cos(t * 0.0004 + d * 2.1) * 0.5 + 0.5) * h;
              netCtx.fillStyle = 'rgba(0,255,255,' + (0.08 + (d % 3) * 0.03) + ')';
              netCtx.fillRect(px, py, 1.5, 1.5);
            }}
          }}

          netNodes.forEach(function(node, i) {{
            const r = node.size * (1 + (i === 0 ? 0.08 * Math.sin(t * 0.002) : 0));
            // aura
            const aura = netCtx.createRadialGradient(node.x, node.y, r * 0.2, node.x, node.y, r * 2.1);
            if (i === 0) {{
              aura.addColorStop(0, 'rgba(0,255,255,0.35)');
              aura.addColorStop(0.5, 'rgba(0,255,255,0.10)');
              aura.addColorStop(1, 'rgba(0,255,255,0)');
            }} else if (i < 3) {{
              aura.addColorStop(0, 'rgba(57,255,136,0.22)');
              aura.addColorStop(1, 'rgba(57,255,136,0)');
            }} else {{
              aura.addColorStop(0, 'rgba(155,92,255,0.14)');
              aura.addColorStop(1, 'rgba(155,92,255,0)');
            }}
            netCtx.fillStyle = aura;
            netCtx.beginPath();
            netCtx.arc(node.x, node.y, r * 2.1, 0, Math.PI * 2);
            netCtx.fill();

            // node body / avatar
            netCtx.save();
            netCtx.beginPath();
            netCtx.arc(node.x, node.y, r, 0, Math.PI * 2);
            netCtx.closePath();
            netCtx.clip();
            if (node.img) {{
              netCtx.drawImage(node.img, node.x - r, node.y - r, r * 2, r * 2);
            }} else {{
              netCtx.fillStyle = i === 0 ? accent : (i < 3 ? ok : purple);
              netCtx.fillRect(node.x - r, node.y - r, r * 2, r * 2);
            }}
            netCtx.restore();

            netCtx.beginPath();
            netCtx.arc(node.x, node.y, r, 0, Math.PI * 2);
            netCtx.strokeStyle = i === 0 ? accent : (i < 3 ? ok : purple);
            netCtx.lineWidth = i === 0 ? 1.6 : 1;
            netCtx.shadowColor = i === 0 ? accent : (i < 3 ? ok : purple);
            netCtx.shadowBlur = i === 0 ? 12 : 5;
            netCtx.stroke();
            netCtx.shadowBlur = 0;

            // labels
            const read = parseFloat(getComputedStyle(rootEl).getPropertyValue('--ll-read')) || 1;
            const namePx = Math.max(11, Math.round((i === 0 ? 12 : 11) * read));
            const valPx = Math.max(12, Math.round((i === 0 ? 13 : 12) * read));
            netCtx.textAlign = 'center';
            netCtx.fillStyle = 'rgba(224,240,255,0.92)';
            netCtx.font = (i === 0 ? 'bold ' : '') + namePx + 'px VT323, monospace';
            const labelY = node.y + r + 12;
            netCtx.fillText(String(node.user || '').slice(0, i === 0 ? 14 : 10), node.x, labelY);
            netCtx.fillStyle = accent;
            netCtx.font = valPx + 'px VT323, monospace';
            const val = displayValues[node.key] !== undefined ? displayValues[node.key] : node.value;
            netCtx.fillText(fmt(val), node.x, labelY + 12);
            if (i === 0) {{
              netCtx.fillStyle = '#ffe066';
              netCtx.font = Math.max(8, Math.round(8 * read)) + 'px "Press Start 2P", monospace';
              netCtx.fillText('#01', node.x, node.y - r - 8);
            }}
          }});
        }}

        function ensureNetLoop() {{
          if (netAnim) return;
          const loop = function(ts) {{
            if (presentation.scene_id !== 'energy_network') {{
              netAnim = null;
              return;
            }}
            drawNet(ts || 0);
            netAnim = requestAnimationFrame(loop);
          }};
          netAnim = requestAnimationFrame(loop);
        }}

        function renderNet(list) {{
          if (!list.length) {{
            if (netCtx) netCtx.clearRect(0, 0, netCanvas.width, netCanvas.height);
            layoutNet([]);
            return;
          }}
          list.forEach(function(row) {{ displayValueFor(row); }});
          layoutNet(list);
          ensureNetLoop();
        }}

        function maybeRankFlash(list) {{
          if (config.enable_rank_change_anim === false) {{
            list.forEach(function(row) {{ lastRanks[tweenKey(row)] = row.rank; }});
            return;
          }}
          list.forEach(function(row) {{
            const k = tweenKey(row);
            const prev = lastRanks[k];
            if (prev !== undefined && prev !== row.rank) {{
              const el = rootEl.querySelector('[data-k="' + String(k).replace(/"/g, '') + '"]');
              if (el) {{
                el.classList.remove('rank-flash');
                void el.offsetWidth;
                el.classList.add('rank-flash');
              }}
            }}
            lastRanks[k] = row.rank;
          }});
        }}

        function spawnParticles(n) {{
          if (config.enable_particles === false) return;
          const inten = String(config.animation_intensity || 'medium');
          const cap = inten === 'low' ? 6 : (inten === 'high' ? MAX_PARTICLES : 12);
          const count = Math.min(n, Math.max(0, cap - particles.length));
          for (let i = 0; i < count; i++) {{
            const el = document.createElement('div');
            el.className = 'fx-particle' + (Math.random() > 0.7 ? ' mag' : '');
            el.style.left = (12 + Math.random() * 76) + '%';
            el.style.top = (55 + Math.random() * 30) + '%';
            particlesEl.appendChild(el);
            particles.push(el);
            setTimeout(function() {{
              try {{ el.remove(); }} catch (e) {{}}
              particles = particles.filter(function(p) {{ return p !== el; }});
            }}, 2200);
          }}
        }}

        function triggerGlitch() {{
          rootEl.classList.add('glitching');
          spawnParticles(5);
          setTimeout(function() {{ rootEl.classList.remove('glitching'); }}, 450);
        }}

        function setActiveScene(sceneId, withTransition) {{
          const map = {{
            hall_of_fame: sceneHof,
            arena: sceneArena,
            energy_network: sceneNet
          }};
          if (withTransition) triggerGlitch();
          stopStripScrollers();
          Object.keys(map).forEach(function(k) {{
            map[k].classList.toggle('active', k === sceneId);
          }});
        }}

        function renderAll(force) {{
          updateReadableScale();
          if (hdrKicker) hdrKicker.textContent = tr('kicker');
          hdrTitle.textContent = sourceLabel(presentation.source_id || 'likers');
          hdrScene.textContent = sceneLabel(presentation.scene_id || 'hall_of_fame');
          const list = currentLeaders();
          const sig = leadersSig(list) + '|' + locale;
          const scene = presentation.scene_id || 'hall_of_fame';
          if (!force && sig === lastDomSig && scene !== 'energy_network') {{
            tickDisplayedValues(list);
            return;
          }}
          lastDomSig = sig;
          if (scene === 'hall_of_fame') renderHof(list);
          else if (scene === 'arena') renderArena(list);
          else renderNet(list);
        }}

        function applyState(st) {{
          if (!st) return;
          if (st.config) config = Object.assign(config || {{}}, st.config);
          if (st.rankings) rankings = st.rankings;
          if (st.locale) {{
            const nextLocale = String(st.locale || '').trim().toLowerCase();
            if (nextLocale === 'en' || nextLocale === 'uk') locale = nextLocale;
          }}
          let transitioned = false;
          if (st.presentation) {{
            const nextToken = Number(st.presentation.transition_token || 0);
            if (lastTransitionToken >= 0 && nextToken !== lastTransitionToken) transitioned = true;
            presentation = Object.assign(presentation || {{}}, st.presentation);
            setActiveScene(presentation.scene_id, transitioned);
            lastTransitionToken = nextToken;
          }}
          applyLook(Object.assign({{}}, config || {{}}, st.config || {{}}, {{
            scale_percent: st.scale_percent !== undefined ? st.scale_percent : (config && config.scale_percent),
            accent_color: st.accent_color !== undefined ? st.accent_color : (config && config.accent_color)
          }}));
          renderAll(true);
        }}

        function handleMsg(data) {{
          if (!data || !data.op) return;
          if (data.op === 'initial_state') {{ applyState(data.state || {{}}); return; }}
          if (data.op === 'patch') applyState(data.patch || {{}});
        }}

        setInterval(function() {{
          if (!presentation) return;
          renderAll(false);
        }}, 140);

        setInterval(function() {{
          if (config.enable_particles === false) return;
          if (Math.random() < 0.2) spawnParticles(1);
        }}, 3200);

        function connect() {{
          var tries = 0;
          var backoff = 500;
          var wsUrl = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws';
          function doConnect() {{
            tries += 1;
            backoff = Math.min(5000, 250 + Math.floor(Math.random() * 250) + (tries * 350));
            var ws;
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

        applyLook(config);
        updateReadableScale();
        setActiveScene('hall_of_fame', false);
        renderAll(true);
        window.addEventListener('resize', function() {{
          updateReadableScale();
          if (presentation.scene_id === 'energy_network') layoutNet(currentLeaders());
          else requestAnimationFrame(syncStripScrollers);
        }});
        if (typeof ResizeObserver !== 'undefined') {{
          const ro = new ResizeObserver(function() {{
            updateReadableScale();
            if (presentation.scene_id === 'energy_network') layoutNet(currentLeaders());
            else requestAnimationFrame(syncStripScrollers);
          }});
          ro.observe(rootEl);
        }}
        connect();
      }})();
    </script>
  </body>
</html>"""

    def initial_state(self, params: dict[str, Any]) -> dict[str, Any]:
        cfg = load_live_leaderboard_overlay_config()
        return {
            "config": live_leaderboard_overlay_config_to_public_dict(cfg),
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
