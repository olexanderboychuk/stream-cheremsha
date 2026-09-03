from __future__ import annotations

import json
from typing import Any

from stream_cheremsha.overlays.models import normalize_instance_id
from stream_cheremsha.overlays.stream_goal_overlay_config import (
    load_stream_goal_overlay_config,
    stream_goal_overlay_config_to_public_dict,
)
from stream_cheremsha.overlays.ui_locale import load_ui_locale


def _json_for_script(value: Any) -> str:
    s = json.dumps(value, ensure_ascii=False)
    return s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def _goal_label(goal_type: str) -> str:
    labels = {
        "followers": "FOLLOW GOAL",
        "likes": "LIKE GOAL",
        "gifts": "GIFT GOAL",
        "shares": "SHARE GOAL",
        "comments": "COMMENT GOAL",
    }
    return labels.get(goal_type, "GOAL")


def _skin_palette(skin: str) -> dict[str, str]:
    palettes = {
        "digital_core": {
            "accent": "#00ffff",
            "magenta": "#ff2bd6",
            "purple": "#9b5cff",
            "warn": "#ffe066",
            "ok": "#39ff88",
            "bg": "#050507",
        },
        "boss": {
            "accent": "#ff3355",
            "magenta": "#ff0066",
            "purple": "#aa2244",
            "warn": "#ffcc33",
            "ok": "#44ff88",
            "bg": "#0a0406",
        },
        "reactor": {
            "accent": "#39ff88",
            "magenta": "#b8ff00",
            "purple": "#1faa66",
            "warn": "#ffe066",
            "ok": "#00ffcc",
            "bg": "#030806",
        },
        "rocket": {
            "accent": "#ff6600",
            "magenta": "#ff3366",
            "purple": "#ff9933",
            "warn": "#ffe066",
            "ok": "#66ccff",
            "bg": "#080503",
        },
        "vault": {
            "accent": "#88ff00",
            "magenta": "#33ff99",
            "purple": "#66aa00",
            "warn": "#ccff33",
            "ok": "#00ffaa",
            "bg": "#040805",
        },
        "tower": {
            "accent": "#ff00aa",
            "magenta": "#ff44ff",
            "purple": "#9b5cff",
            "warn": "#ffccff",
            "ok": "#00ffff",
            "bg": "#08040a",
        },
        "creature": {
            "accent": "#ff66cc",
            "magenta": "#ff99ff",
            "purple": "#cc44aa",
            "warn": "#ffe066",
            "ok": "#66ff99",
            "bg": "#0a0508",
        },
    }
    return palettes.get(skin, palettes["digital_core"])


class StreamGoalOverlayType:
    type = "stream_goal"

    def render_html(self, params: dict[str, Any]) -> str:
        raw_instance = params.get("instance")
        try:
            instance = normalize_instance_id(str(raw_instance or ""))
        except ValueError:
            instance = "default"

        subscribe_msg = {
            "op": "subscribe",
            "type": "stream_goal",
            "instance": instance,
            "params": {},
        }
        locale = load_ui_locale()
        cfg = load_stream_goal_overlay_config()
        return self._render_template(
            params, locale, subscribe_msg, cfg.accent_color, cfg.skin, cfg.scale_percent
        )

    def initial_state(self, params: dict[str, Any]) -> dict[str, Any]:
        _ = normalize_instance_id(str(params.get("instance") or ""))
        cfg = load_stream_goal_overlay_config()
        return {
            "config": stream_goal_overlay_config_to_public_dict(cfg),
            "goal_type": cfg.goal_type,
            "title": cfg.title,
            "subtitle": cfg.subtitle,
            "current_value": cfg.current_value,
            "target_value": cfg.target_value,
            "progress": 0.0 if cfg.target_value <= 0 else min(1.0, cfg.current_value / cfg.target_value),
            "progress_percent": (
                0 if cfg.target_value <= 0 else int(min(1.0, cfg.current_value / cfg.target_value) * 100)
            ),
            "remaining": max(0, cfg.target_value - cfg.current_value),
            "skin": cfg.skin,
            "accent_color": cfg.accent_color,
            "scale_percent": int(cfg.scale_percent),
            "animation_intensity": cfg.animation_intensity,
            "enable_particles": cfg.enable_particles,
            "enable_glitch": cfg.enable_glitch,
            "combo_count": 0,
            "combo_expires_at": 0.0,
            "core_level": 1,
            "completed_goals": 0,
            "is_completing": False,
            "completion_anim_seq": 0,
            "milestones": [],
            "visual_events": [],
        }

    def _render_template(
        self,
        params: dict[str, Any],
        locale: str,
        subscribe_msg: dict[str, Any],
        accent: str,
        skin: str = "digital_core",
        scale_percent: int = 100,
    ) -> str:
        _ = params
        html = """<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Stream Goal</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=VT323&display=swap" rel="stylesheet" />
    <style>
      html, body { margin: 0; padding: 0; background: transparent; overflow: hidden; height: 100%; }
      * { box-sizing: border-box; }
      :root {
        --sg-accent: #00ffff;
        --sg-magenta: #ff2bd6;
        --sg-purple: #9b5cff;
        --sg-warn: #ffe066;
        --sg-ok: #39ff88;
        --sg-bg: #050507;
        --sg-widget-scale: 1;
        --ring-speed: 14s;
        --ring-speed-2: 9s;
        --ring-speed-3: 6s;
        --glow-opacity: 0.22;
        --core-scale: 1;
        --float-amp: 3px;
        --arc-opacity: 0.15;
        --particle-opacity: 0.35;
      }

      .root {
        position: absolute; inset: 0;
        background: var(--sg-bg, #050507);
        font-family: 'VT323', monospace;
        color: #e0f0ff;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: calc(10px * var(--sg-widget-scale, 1)) calc(12px * var(--sg-widget-scale, 1)) calc(12px * var(--sg-widget-scale, 1));
        gap: 0;
        /* Size-scale inside the box — never transform-zoom past widget bounds */
        --sg-u: var(--sg-widget-scale, 1);
      }

      .hud-frame {
        position: absolute; inset: calc(3px * var(--sg-u));
        border: 1px solid color-mix(in srgb, var(--sg-accent) 22%, transparent);
        pointer-events: none;
      }
      .hud-corner {
        position: absolute;
        width: calc(14px * var(--sg-u));
        height: calc(14px * var(--sg-u));
        border-color: var(--sg-accent); border-style: solid; border-width: 0; opacity: 0.75;
      }
      .hud-corner.tl { top: 0; left: 0; border-top-width: 1px; border-left-width: 1px; }
      .hud-corner.tr { top: 0; right: 0; border-top-width: 1px; border-right-width: 1px; }
      .hud-corner.bl { bottom: 0; left: 0; border-bottom-width: 1px; border-left-width: 1px; }
      .hud-corner.br { bottom: 0; right: 0; border-bottom-width: 1px; border-right-width: 1px; }

      .scanlines {
        position: absolute; inset: 0;
        background: repeating-linear-gradient(
          0deg, transparent, transparent 2px, rgba(0,0,0,0.07) 2px, rgba(0,0,0,0.07) 4px
        );
        pointer-events: none; opacity: 0.35; z-index: 20;
      }
      .vignette {
        position: absolute; inset: 0; pointer-events: none; z-index: 19;
        background: radial-gradient(ellipse at center, transparent 45%, rgba(0,0,0,0.45) 100%);
      }

      .hdr {
        position: relative; z-index: 5;
        width: 100%;
        text-align: center;
        flex: 0 0 auto;
        padding: calc(2px * var(--sg-u)) calc(4px * var(--sg-u)) 0;
        pointer-events: none;
      }
      .hdr-title {
        font-family: 'Press Start 2P', monospace;
        font-size: calc(clamp(9px, 2.4vw, 12px) * var(--sg-u));
        color: var(--sg-accent);
        text-shadow: 0 0 calc(6px * var(--sg-u)) var(--sg-accent), 0 0 calc(14px * var(--sg-u)) color-mix(in srgb, var(--sg-accent) 35%, transparent);
        letter-spacing: calc(1px * var(--sg-u));
        line-height: 1.35;
      }
      .hdr-subtitle {
        margin-top: calc(2px * var(--sg-u));
        font-size: calc(12px * var(--sg-u));
        color: rgba(180, 200, 220, 0.4);
        letter-spacing: calc(0.5px * var(--sg-u));
        min-height: 0;
      }
      .hdr-subtitle:empty { display: none; }

      .core-stage {
        position: relative; z-index: 4;
        flex: 1 1 auto;
        width: 100%;
        min-height: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        pointer-events: none;
        overflow: hidden;
      }

      .core-area {
        position: relative;
        /* Prefer scaled size, but never leave the stage box */
        width: min(calc(340px * var(--sg-u)), 100%);
        height: min(calc(340px * var(--sg-u)), 100%);
        max-width: 100%;
        max-height: 100%;
        aspect-ratio: 1 / 1;
        transform: scale(var(--core-scale));
        animation: coreFloat 5.5s ease-in-out infinite;
        will-change: transform;
      }

      @keyframes coreFloat {
        0%, 100% { transform: scale(var(--core-scale)) translateY(0); }
        50% { transform: scale(var(--core-scale)) translateY(calc(var(--float-amp) * var(--sg-u) * -1)); }
      }

      .core-svg { width: 100%; height: 100%; overflow: visible; }

      .orbit { fill: none; transform-origin: 100px 100px; }
      .orbit-a {
        stroke: var(--sg-accent); stroke-width: 0.7; opacity: 0.38;
        stroke-dasharray: 4 6;
        animation: orbitSpin var(--ring-speed) linear infinite;
      }
      .orbit-b {
        stroke: var(--sg-magenta); stroke-width: 0.55; opacity: 0.32;
        stroke-dasharray: 2 8;
        animation: orbitSpin var(--ring-speed-2) linear infinite reverse;
      }
      .orbit-c {
        stroke: var(--sg-purple); stroke-width: 0.45; opacity: 0.28;
        animation: orbitSpin var(--ring-speed-3) linear infinite;
      }

      @keyframes orbitSpin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
      }

      .core-bloom {
        fill: var(--sg-accent);
        opacity: var(--glow-opacity);
        filter: url(#softBloom);
        animation: breathGlow 3.2s ease-in-out infinite;
        transform-origin: 100px 100px;
      }
      .core-bloom-mag {
        fill: var(--sg-magenta);
        opacity: calc(var(--glow-opacity) * 0.55);
        filter: url(#softBloom);
        animation: breathGlow 4s ease-in-out infinite reverse;
        transform-origin: 100px 100px;
      }

      @keyframes breathGlow {
        0%, 100% { opacity: var(--glow-opacity); transform: scale(1); }
        50% { opacity: calc(var(--glow-opacity) * 1.55); transform: scale(1.06); }
      }

      .crystal-group {
        transform-origin: 100px 100px;
        animation: crystalSpin 28s linear infinite;
      }
      @keyframes crystalSpin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
      }

      .facet-a { fill: var(--sg-accent); fill-opacity: 0.55; stroke: var(--sg-accent); stroke-width: 0.6; stroke-opacity: 0.85; }
      .facet-b { fill: var(--sg-accent); fill-opacity: 0.38; stroke: var(--sg-accent); stroke-width: 0.45; stroke-opacity: 0.55; }
      .facet-c { fill: var(--sg-magenta); fill-opacity: 0.42; stroke: var(--sg-magenta); stroke-width: 0.5; stroke-opacity: 0.7; }
      .facet-d { fill: var(--sg-purple); fill-opacity: 0.28; stroke: var(--sg-accent); stroke-width: 0.4; stroke-opacity: 0.4; }
      .facet-core {
        fill: var(--sg-accent);
        fill-opacity: 0.92;
        stroke: #fff;
        stroke-width: 0.35;
        filter: url(#innerGlow);
        animation: corePulse 2.4s ease-in-out infinite;
        transform-origin: 100px 100px;
      }
      @keyframes corePulse {
        0%, 100% { transform: scale(1); opacity: 0.9; }
        50% { transform: scale(1.08); opacity: 1; }
      }

      .energy-arc {
        fill: none;
        stroke: var(--sg-accent);
        stroke-width: 0.7;
        opacity: var(--arc-opacity);
        stroke-linecap: round;
        filter: url(#arcGlow);
      }
      .energy-arc.mag { stroke: var(--sg-magenta); }
      .energy-arc.pulse {
        animation: arcFlicker 1.8s ease-in-out infinite;
      }
      @keyframes arcFlicker {
        0%, 100% { opacity: var(--arc-opacity); }
        40% { opacity: calc(var(--arc-opacity) * 2.4); }
        55% { opacity: calc(var(--arc-opacity) * 0.4); }
      }

      .spark {
        fill: var(--sg-accent);
        opacity: var(--particle-opacity);
        filter: url(#arcGlow);
      }
      .spark.mag { fill: var(--sg-magenta); }
      .spark.y { fill: var(--sg-warn); }

      .warn-mark {
        fill: none;
        stroke: var(--sg-warn);
        stroke-width: 1.1;
        opacity: 0;
        pointer-events: none;
      }
      .warn-text {
        font-family: 'Press Start 2P', monospace;
        font-size: 5px;
        fill: var(--sg-warn);
        opacity: 0;
        letter-spacing: 0.5px;
      }

      /* Progress tiers */
      .root.tier-idle {
        --ring-speed: 16s; --ring-speed-2: 11s; --ring-speed-3: 8s;
        --glow-opacity: 0.16; --core-scale: 0.92; --float-amp: 2px;
        --arc-opacity: 0.08; --particle-opacity: 0.2;
      }
      .root.tier-low {
        --ring-speed: 13s; --ring-speed-2: 9s; --ring-speed-3: 7s;
        --glow-opacity: 0.22; --core-scale: 0.96; --float-amp: 3px;
        --arc-opacity: 0.14; --particle-opacity: 0.3;
      }
      .root.tier-mid {
        --ring-speed: 9s; --ring-speed-2: 6.5s; --ring-speed-3: 5s;
        --glow-opacity: 0.32; --core-scale: 1; --float-amp: 4px;
        --arc-opacity: 0.28; --particle-opacity: 0.5;
      }
      .root.tier-high {
        --ring-speed: 5.5s; --ring-speed-2: 4s; --ring-speed-3: 3s;
        --glow-opacity: 0.45; --core-scale: 1.04; --float-amp: 5px;
        --arc-opacity: 0.42; --particle-opacity: 0.7;
      }
      .root.tier-critical {
        --ring-speed: 2.8s; --ring-speed-2: 2s; --ring-speed-3: 1.5s;
        --glow-opacity: 0.58; --core-scale: 1.08; --float-amp: 1px;
        --arc-opacity: 0.55; --particle-opacity: 0.85;
      }
      .root.tier-critical .core-area {
        animation: coreUnstable 0.18s steps(2) infinite;
      }
      .root.tier-critical .warn-mark,
      .root.tier-critical .warn-text { opacity: 0.75; animation: warnBlink 0.7s steps(2) infinite; }
      .root.tier-critical .crystal-group { animation-duration: 10s; }

      @keyframes coreUnstable {
        0%, 100% { transform: scale(var(--core-scale)) translate(0, 0); }
        25% { transform: scale(var(--core-scale)) translate(-2px, 1px); }
        50% { transform: scale(var(--core-scale)) translate(2px, -1px); }
        75% { transform: scale(var(--core-scale)) translate(-1px, -2px); }
      }
      @keyframes warnBlink {
        0%, 100% { opacity: 0.8; }
        50% { opacity: 0.15; }
      }

      .root.tier-breach {
        --ring-speed: 0.6s; --ring-speed-2: 0.4s; --ring-speed-3: 0.3s;
        --glow-opacity: 0.9; --core-scale: 1.18; --float-amp: 0;
        --arc-opacity: 0.9; --particle-opacity: 1;
      }

      /* Event reaction classes */
      .core-area.rx-pulse .core-bloom { animation: rxPulse 0.45s ease-out; }
      .core-area.rx-pulse .facet-core { animation: rxPulse 0.45s ease-out; }
      @keyframes rxPulse {
        0% { transform: scale(1); opacity: var(--glow-opacity); }
        40% { transform: scale(1.25); opacity: 0.85; }
        100% { transform: scale(1); opacity: var(--glow-opacity); }
      }

      .core-area.rx-shake { animation: rxShake 0.35s ease-in-out; }
      @keyframes rxShake {
        0%, 100% { transform: scale(var(--core-scale)) translate(0,0); }
        20% { transform: scale(var(--core-scale)) translate(-4px, 2px); }
        40% { transform: scale(var(--core-scale)) translate(4px, -2px); }
        60% { transform: scale(var(--core-scale)) translate(-3px, -3px); }
        80% { transform: scale(var(--core-scale)) translate(3px, 1px); }
      }

      .core-area.rx-glitch .core-svg { animation: rxGlitch 0.22s steps(3); }
      @keyframes rxGlitch {
        0% { filter: none; opacity: 1; }
        30% { filter: hue-rotate(80deg) brightness(1.6); opacity: 0.7; transform: translate(3px, -1px); }
        60% { filter: hue-rotate(-70deg) brightness(1.3); opacity: 0.85; transform: translate(-2px, 2px); }
        100% { filter: none; opacity: 1; }
      }

      .shockwave {
        position: absolute; left: 50%; top: 50%;
        width: 20%; height: 20%;
        border: 1.5px solid var(--sg-accent);
        border-radius: 50%;
        transform: translate(-50%, -50%) scale(0.2);
        opacity: 0;
        pointer-events: none;
        box-shadow: 0 0 12px var(--sg-accent), inset 0 0 8px rgba(0,255,255,0.3);
      }
      .shockwave.go {
        animation: shockExpand 0.7s ease-out forwards;
      }
      .shockwave.gift {
        border-color: var(--sg-warn);
        box-shadow: 0 0 16px var(--sg-warn), inset 0 0 10px rgba(255,224,102,0.35);
      }
      .shockwave.share {
        border-color: var(--sg-ok);
        box-shadow: 0 0 14px var(--sg-ok);
      }
      @keyframes shockExpand {
        0% { opacity: 0.9; transform: translate(-50%, -50%) scale(0.25); }
        100% { opacity: 0; transform: translate(-50%, -50%) scale(3.2); }
      }

      .beam {
        position: absolute; left: 50%; top: 50%;
        width: 2px; height: 0;
        background: linear-gradient(to top, transparent, var(--sg-ok), transparent);
        transform-origin: bottom center;
        opacity: 0;
        pointer-events: none;
        box-shadow: 0 0 8px var(--sg-ok);
      }
      .beam.go { animation: beamFire 0.55s ease-out forwards; }
      @keyframes beamFire {
        0% { opacity: 0; height: 0; }
        30% { opacity: 1; height: 42%; }
        100% { opacity: 0; height: 55%; }
      }

      .stats {
        position: relative; z-index: 5;
        flex: 0 0 auto;
        width: 100%;
        text-align: center;
        padding: 0 calc(6px * var(--sg-u)) calc(2px * var(--sg-u));
        pointer-events: none;
        margin-top: calc(-2px * var(--sg-u));
      }
      .stat-current {
        font-family: 'Press Start 2P', monospace;
        font-size: calc(clamp(18px, 5.5vw, 28px) * var(--sg-u));
        color: var(--sg-accent);
        text-shadow: 0 0 calc(8px * var(--sg-u)) var(--sg-accent), 0 0 calc(18px * var(--sg-u)) color-mix(in srgb, var(--sg-accent) 30%, transparent);
        letter-spacing: calc(1px * var(--sg-u));
        line-height: 1.15;
        font-variant-numeric: tabular-nums;
        transition: transform 0.12s ease;
      }
      .stat-current.bump { transform: scale(1.08); color: #fff; }

      .stat-target-row {
        margin-top: calc(4px * var(--sg-u));
        font-family: 'Press Start 2P', monospace;
        font-size: calc(clamp(7px, 1.8vw, 9px) * var(--sg-u));
        color: rgba(180, 200, 220, 0.55);
        letter-spacing: calc(1px * var(--sg-u));
      }
      .stat-target-row .lbl { color: color-mix(in srgb, var(--sg-magenta) 75%, white); margin-right: calc(6px * var(--sg-u)); }
      .stat-target-row .val { color: rgba(200, 220, 240, 0.7); }

      .stat-pct {
        margin-top: calc(3px * var(--sg-u));
        font-family: 'VT323', monospace;
        font-size: calc(clamp(13px, 3.2vw, 18px) * var(--sg-u));
        color: rgba(180, 200, 220, 0.38);
        letter-spacing: calc(1px * var(--sg-u));
      }

      .energy-bar {
        position: relative; z-index: 5;
        flex: 0 0 auto;
        width: calc(100% - calc(20px * var(--sg-u)));
        max-width: min(100%, calc(280px * var(--sg-u)));
        height: calc(2px * var(--sg-u));
        margin-top: calc(6px * var(--sg-u));
        background: color-mix(in srgb, var(--sg-accent) 8%, transparent);
        border: 1px solid color-mix(in srgb, var(--sg-accent) 14%, transparent);
        overflow: hidden;
      }
      .energy-bar-fill {
        height: 100%; width: 0%;
        background: var(--sg-accent);
        box-shadow: 0 0 calc(4px * var(--sg-u)) var(--sg-accent);
        transition: width 0.45s ease;
        opacity: 0.7;
      }

      .notif-area {
        position: absolute; inset: 0; z-index: 12; pointer-events: none;
      }
      .notif {
        position: absolute;
        font-family: 'Press Start 2P', monospace;
        font-size: calc(9px * var(--sg-u));
        color: #fff;
        text-shadow: 0 0 calc(6px * var(--sg-u)) var(--sg-accent), 0 0 calc(12px * var(--sg-u)) color-mix(in srgb, var(--sg-accent) 45%, transparent);
        white-space: nowrap;
        animation: notifFly 0.95s ease-out forwards;
      }
      .notif.gift { color: var(--sg-warn); text-shadow: 0 0 calc(6px * var(--sg-u)) var(--sg-warn); font-size: calc(10px * var(--sg-u)); }
      .notif.share { color: var(--sg-ok); text-shadow: 0 0 calc(6px * var(--sg-u)) var(--sg-ok); }
      .notif.milestone { color: var(--sg-magenta); text-shadow: 0 0 calc(6px * var(--sg-u)) var(--sg-magenta); }
      .notif.combo { color: #ff8800; text-shadow: 0 0 calc(6px * var(--sg-u)) #ff8800; }
      @keyframes notifFly {
        0% { opacity: 1; transform: translateY(0) scale(1); }
        70% { opacity: 1; transform: translateY(calc(-28px * var(--sg-u))) scale(1.05); }
        100% { opacity: 0; transform: translateY(calc(-52px * var(--sg-u))) scale(0.85); }
      }

      .milestone-toast {
        position: absolute; top: 14%; left: 50%;
        transform: translateX(-50%);
        z-index: 14; pointer-events: none; text-align: center;
        font-family: 'Press Start 2P', monospace;
        opacity: 0; transition: opacity 0.25s ease;
      }
      .milestone-toast.show { opacity: 1; }
      .milestone-toast .mt-label {
        font-size: calc(10px * var(--sg-u)); color: var(--sg-magenta);
        text-shadow: 0 0 calc(8px * var(--sg-u)) var(--sg-magenta), 0 0 calc(18px * var(--sg-u)) color-mix(in srgb, var(--sg-magenta) 45%, transparent);
      }
      .milestone-toast .mt-percent {
        margin-top: calc(4px * var(--sg-u)); font-size: calc(8px * var(--sg-u)); color: rgba(200,220,240,0.45);
      }

      .breach-layer {
        position: absolute; inset: 0; z-index: 15; pointer-events: none;
        opacity: 0; background: radial-gradient(circle, color-mix(in srgb, var(--sg-accent) 20%, transparent) 0%, transparent 55%);
      }
      .breach-layer.active { opacity: 1; animation: breachFlicker 0.25s steps(2) infinite; }
      @keyframes breachFlicker {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.35; }
      }

      .breach-text {
        position: absolute; left: 50%; top: 46%;
        transform: translate(-50%, -50%);
        z-index: 16; pointer-events: none;
        font-family: 'Press Start 2P', monospace;
        font-size: calc(clamp(11px, 3.2vw, 15px) * var(--sg-u));
        color: #ff4488;
        letter-spacing: calc(3px * var(--sg-u));
        text-shadow: 0 0 calc(10px * var(--sg-u)) #ff4488, 0 0 calc(28px * var(--sg-u)) rgba(255,68,136,0.55);
        opacity: 0;
      }
      .breach-text.show {
        opacity: 1;
        animation: breachPulse 0.85s ease-in-out infinite;
      }
      @keyframes breachPulse {
        0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
        50% { transform: translate(-50%, -50%) scale(1.08); opacity: 0.65; }
      }

      .new-target-text {
        position: absolute; left: 50%; top: 56%;
        transform: translate(-50%, -50%);
        z-index: 16; pointer-events: none;
        font-family: 'VT323', monospace;
        font-size: calc(16px * var(--sg-u));
        color: color-mix(in srgb, var(--sg-accent) 75%, white);
        text-shadow: 0 0 calc(8px * var(--sg-u)) color-mix(in srgb, var(--sg-accent) 40%, transparent);
        opacity: 0;
      }
      .new-target-text.show { opacity: 1; }

      .combo-display {
        position: absolute;
        top: calc(8px * var(--sg-u));
        right: calc(12px * var(--sg-u));
        z-index: 10;
        font-family: 'Press Start 2P', monospace;
        font-size: calc(10px * var(--sg-u));
        color: #ff8800; text-shadow: 0 0 calc(6px * var(--sg-u)) #ff8800;
        opacity: 0; transition: opacity 0.2s ease; pointer-events: none;
      }
      .combo-display.show { opacity: 1; }

      .fx-particle {
        position: absolute;
        width: calc(2px * var(--sg-u));
        height: calc(2px * var(--sg-u));
        border-radius: 50%;
        background: var(--sg-accent); pointer-events: none; z-index: 11;
        box-shadow: 0 0 calc(4px * var(--sg-u)) var(--sg-accent);
      }
      .fx-particle.mag { background: var(--sg-magenta); box-shadow: 0 0 calc(4px * var(--sg-u)) var(--sg-magenta); }
      .fx-particle.warn { background: var(--sg-warn); box-shadow: 0 0 calc(4px * var(--sg-u)) var(--sg-warn); }

      .glitch-line {
        position: absolute; left: 0; right: 0;
        height: calc(2px * var(--sg-u));
        z-index: 17;
        background: color-mix(in srgb, var(--sg-accent) 14%, transparent); opacity: 0; pointer-events: none;
      }

      .root.skin-digital_core {
        --sg-accent: #00ffff; --sg-magenta: #ff2bd6; --sg-purple: #9b5cff;
        --sg-warn: #ffe066; --sg-ok: #39ff88; --sg-bg: #050507;
      }
      .root.skin-boss {
        --sg-accent: #ff3355; --sg-magenta: #ff0066; --sg-purple: #aa2244;
        --sg-warn: #ffcc33; --sg-ok: #44ff88; --sg-bg: #0a0406;
      }
      .root.skin-boss .energy-bar { height: calc(6px * var(--sg-u)); max-width: min(100%, calc(300px * var(--sg-u))); }
      .root.skin-boss .energy-bar-fill { opacity: 0.95; }
      .root.skin-boss .crystal-group { animation-duration: 18s; }
      .root.skin-boss .orbit-a { stroke-dasharray: none; }
      .root.skin-reactor {
        --sg-accent: #39ff88; --sg-magenta: #b8ff00; --sg-purple: #1faa66;
        --sg-warn: #ffe066; --sg-ok: #00ffcc; --sg-bg: #030806;
      }
      .root.skin-reactor .core-bloom { opacity: calc(var(--glow-opacity) * 1.35); }
      .root.skin-reactor .orbit-c { stroke-dasharray: 1 3; }
      .root.skin-rocket {
        --sg-accent: #ff6600; --sg-magenta: #ff3366; --sg-purple: #ff9933;
        --sg-warn: #ffe066; --sg-ok: #66ccff; --sg-bg: #080503;
      }
      .root.skin-rocket .crystal-group { animation-duration: 14s; }
      .root.skin-rocket .orbit-a { stroke-dasharray: 8 4; }
      .root.skin-vault {
        --sg-accent: #88ff00; --sg-magenta: #33ff99; --sg-purple: #66aa00;
        --sg-warn: #ccff33; --sg-ok: #00ffaa; --sg-bg: #040805;
      }
      .root.skin-vault .facet-a, .root.skin-vault .facet-b { fill-opacity: 0.7; }
      .root.skin-tower {
        --sg-accent: #ff00aa; --sg-magenta: #ff44ff; --sg-purple: #9b5cff;
        --sg-warn: #ffccff; --sg-ok: #00ffff; --sg-bg: #08040a;
      }
      .root.skin-tower .orbit-b { stroke-width: 1.1; opacity: 0.55; }
      .root.skin-creature {
        --sg-accent: #ff66cc; --sg-magenta: #ff99ff; --sg-purple: #cc44aa;
        --sg-warn: #ffe066; --sg-ok: #66ff99; --sg-bg: #0a0508;
      }
      .root.skin-creature .facet-core { fill-opacity: 1; }
      .root.skin-creature .crystal-group { animation-duration: 22s; }
    </style>
  </head>
  <body>
    <div class="root tier-idle" id="root" data-sg-root="1">
      <div class="scanlines" aria-hidden="true"></div>
      <div class="vignette" aria-hidden="true"></div>
      <div class="hud-frame" aria-hidden="true">
        <div class="hud-corner tl"></div>
        <div class="hud-corner tr"></div>
        <div class="hud-corner bl"></div>
        <div class="hud-corner br"></div>
      </div>

      <div class="hdr">
        <div class="hdr-title" id="hdrTitle">""" + _goal_label("followers") + """</div>
        <div class="hdr-subtitle" id="hdrSubtitle"></div>
      </div>

      <div class="core-stage">
        <div class="core-area" id="coreArea">
          <div class="shockwave" id="shockwave"></div>
          <div class="beam" id="beam"></div>
          <svg class="core-svg" viewBox="0 0 200 200" aria-hidden="true">
            <defs>
              <filter id="softBloom" x="-80%" y="-80%" width="260%" height="260%">
                <feGaussianBlur stdDeviation="6" result="b" />
                <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
              </filter>
              <filter id="innerGlow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="1.6" result="b" />
                <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
              </filter>
              <filter id="arcGlow" x="-40%" y="-40%" width="180%" height="180%">
                <feGaussianBlur stdDeviation="1.2" result="b" />
                <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
              </filter>
              <radialGradient id="coreGrad" cx="50%" cy="42%" r="55%">
                <stop offset="0%" stop-color="#e8ffff" stop-opacity="0.95" />
                <stop offset="35%" stop-color="#00ffff" stop-opacity="0.55" />
                <stop offset="70%" stop-color="#9b5cff" stop-opacity="0.25" />
                <stop offset="100%" stop-color="#00ffff" stop-opacity="0" />
              </radialGradient>
            </defs>

            <ellipse class="orbit orbit-a" cx="100" cy="100" rx="78" ry="42" transform="rotate(-18 100 100)" />
            <ellipse class="orbit orbit-b" cx="100" cy="100" rx="68" ry="58" transform="rotate(32 100 100)" />
            <ellipse class="orbit orbit-c" cx="100" cy="100" rx="52" ry="72" transform="rotate(-55 100 100)" />

            <circle class="core-bloom" cx="100" cy="100" r="48" />
            <circle class="core-bloom-mag" cx="100" cy="100" r="34" />

            <g class="crystal-group" id="crystalGroup">
              <polygon class="facet-d" points="100,28 128,70 100,92 72,70" />
              <polygon class="facet-a" points="100,28 128,70 100,55" />
              <polygon class="facet-b" points="100,28 72,70 100,55" />
              <polygon class="facet-c" points="128,70 148,100 118,108 100,92" />
              <polygon class="facet-a" points="72,70 52,100 82,108 100,92" />
              <polygon class="facet-b" points="148,100 128,130 100,145 118,108" />
              <polygon class="facet-c" points="52,100 72,130 100,145 82,108" />
              <polygon class="facet-d" points="128,130 100,172 72,130 100,145" />
              <polygon class="facet-a" points="100,145 128,130 100,172" />
              <polygon class="facet-b" points="100,145 72,130 100,172" />
              <polygon class="facet-core" points="100,78 112,100 100,122 88,100" />
              <line x1="100" y1="55" x2="100" y2="145" stroke="rgba(255,255,255,0.25)" stroke-width="0.4" />
              <line x1="72" y1="70" x2="128" y2="130" stroke="var(--sg-magenta)" stroke-opacity="0.35" stroke-width="0.35" />
              <line x1="128" y1="70" x2="72" y2="130" stroke="var(--sg-accent)" stroke-opacity="0.3" stroke-width="0.35" />
            </g>

            <path class="energy-arc pulse" d="M55 70 Q40 100 58 132" />
            <path class="energy-arc mag pulse" d="M145 68 Q162 100 142 134" style="animation-delay:-0.6s" />
            <path class="energy-arc pulse" d="M78 48 Q100 32 122 48" style="animation-delay:-1.1s" />

            <circle class="spark" cx="48" cy="88" r="1.2" />
            <circle class="spark mag" cx="156" cy="112" r="1.1" />
            <circle class="spark y" cx="118" cy="46" r="0.9" />
            <circle class="spark" cx="86" cy="158" r="1" />
            <circle class="spark mag" cx="64" cy="128" r="0.8" />
            <circle class="spark" cx="140" cy="78" r="0.9" />

            <polygon class="warn-mark" points="100,18 106,28 94,28" />
            <text class="warn-text" x="100" y="14" text-anchor="middle">UNSTABLE</text>
          </svg>
        </div>
      </div>

      <div class="stats">
        <div class="stat-current" id="hudCurrent">0</div>
        <div class="stat-target-row">
          <span class="lbl" id="targetLbl">TARGET</span>
          <span class="val" id="hudTarget">10,000</span>
        </div>
        <div class="stat-pct" id="hudPercent">0%</div>
      </div>

      <div class="energy-bar" aria-hidden="true">
        <div class="energy-bar-fill" id="energyBarFill"></div>
      </div>

      <div class="notif-area" id="notifArea"></div>
      <div class="milestone-toast" id="milestoneToast">
        <div class="mt-label" id="mtLabel"></div>
        <div class="mt-percent" id="mtPercent"></div>
      </div>
      <div class="breach-layer" id="breachOverlay"></div>
      <div class="breach-text" id="breachText">CORE BREACH</div>
      <div class="new-target-text" id="newTargetText"></div>
      <div class="combo-display" id="comboDisplay">COMBO x1</div>
      <div class="glitch-line" id="glitchLine"></div>
    </div>

    <script>
      (function() {
        var locale = """ + _json_for_script(locale) + """;
        var GOAL_LABELS = {
          followers: 'FOLLOW GOAL',
          likes: 'LIKE GOAL',
          gifts: 'GIFT GOAL',
          shares: 'SHARE GOAL',
          comments: 'COMMENT GOAL'
        };

        var root = document.getElementById('root');
        var coreArea = document.getElementById('coreArea');
        var hdrTitle = document.getElementById('hdrTitle');
        var hdrSubtitle = document.getElementById('hdrSubtitle');
        var hudCurrent = document.getElementById('hudCurrent');
        var hudTarget = document.getElementById('hudTarget');
        var hudPercent = document.getElementById('hudPercent');
        var energyBarFill = document.getElementById('energyBarFill');
        var notifArea = document.getElementById('notifArea');
        var comboDisplay = document.getElementById('comboDisplay');
        var milestoneToast = document.getElementById('milestoneToast');
        var mtLabel = document.getElementById('mtLabel');
        var mtPercent = document.getElementById('mtPercent');
        var breachText = document.getElementById('breachText');
        var breachOverlay = document.getElementById('breachOverlay');
        var newTargetText = document.getElementById('newTargetText');
        var shockwave = document.getElementById('shockwave');
        var beam = document.getElementById('beam');
        var glitchLine = document.getElementById('glitchLine');

        var accentColor = '#00ffff';
        var activeSkin = 'digital_core';
        var state = null;
        var config = null;
        var lastCombo = 0;
        var currentPct = 0;
        var isBreaching = false;
        var ambientTimer = null;
        var targetLbl = document.getElementById('targetLbl');

        var SKIN_PALETTES = {
          digital_core: { accent:'#00ffff', magenta:'#ff2bd6', purple:'#9b5cff', warn:'#ffe066', ok:'#39ff88', bg:'#050507', targetLbl:'TARGET' },
          boss:         { accent:'#ff3355', magenta:'#ff0066', purple:'#aa2244', warn:'#ffcc33', ok:'#44ff88', bg:'#0a0406', targetLbl:'HP MAX' },
          reactor:      { accent:'#39ff88', magenta:'#b8ff00', purple:'#1faa66', warn:'#ffe066', ok:'#00ffcc', bg:'#030806', targetLbl:'CAPACITY' },
          rocket:       { accent:'#ff6600', magenta:'#ff3366', purple:'#ff9933', warn:'#ffe066', ok:'#66ccff', bg:'#080503', targetLbl:'THRUST' },
          vault:        { accent:'#88ff00', magenta:'#33ff99', purple:'#66aa00', warn:'#ccff33', ok:'#00ffaa', bg:'#040805', targetLbl:'LOCK' },
          tower:        { accent:'#ff00aa', magenta:'#ff44ff', purple:'#9b5cff', warn:'#ffccff', ok:'#00ffff', bg:'#08040a', targetLbl:'HEIGHT' },
          creature:     { accent:'#ff66cc', magenta:'#ff99ff', purple:'#cc44aa', warn:'#ffe066', ok:'#66ff99', bg:'#0a0508', targetLbl:'BIOMASS' }
        };
        var SKIN_DEFAULT_ACCENTS = {};
        Object.keys(SKIN_PALETTES).forEach(function(k) {
          SKIN_DEFAULT_ACCENTS[SKIN_PALETTES[k].accent.toLowerCase()] = true;
        });

        function applyPaletteVars(pal, accentOverride) {
          if (!pal) return;
          var accent = accentOverride || pal.accent;
          root.style.setProperty('--sg-accent', accent);
          root.style.setProperty('--sg-magenta', pal.magenta);
          root.style.setProperty('--sg-purple', pal.purple);
          root.style.setProperty('--sg-warn', pal.warn);
          root.style.setProperty('--sg-ok', pal.ok);
          root.style.setProperty('--sg-bg', pal.bg);
          if (targetLbl) targetLbl.textContent = pal.targetLbl || 'TARGET';
          accentColor = accent;
        }

        function setAccent(color) {
          var c = color || accentColor || '#00ffff';
          accentColor = c;
          root.style.setProperty('--sg-accent', c);
        }

        function applyScale(percent) {
          var p = Number(percent);
          if (!Number.isFinite(p)) p = 100;
          p = Math.max(40, Math.min(250, Math.round(p)));
          root.style.setProperty('--sg-widget-scale', String(p / 100));
        }

        function fmtInt(n) {
          try { return Number(n).toLocaleString('en-US'); } catch (e) { return String(n); }
        }

        function clearTier() {
          root.classList.remove('tier-idle', 'tier-low', 'tier-mid', 'tier-high', 'tier-critical', 'tier-breach');
        }

        function setProgressTier(pct) {
          if (isBreaching) return;
          currentPct = pct;
          clearTier();
          if (pct >= 90) root.classList.add('tier-critical');
          else if (pct >= 70) root.classList.add('tier-high');
          else if (pct >= 35) root.classList.add('tier-mid');
          else if (pct >= 1) root.classList.add('tier-low');
          else root.classList.add('tier-idle');
        }

        function isStockGoalTitle(t) {
          var u = String(t || '').trim().toUpperCase();
          if (!u || u === 'CORE BREACH' || u === 'GOAL') return true;
          for (var k in GOAL_LABELS) {
            if (GOAL_LABELS[k] === u || GOAL_LABELS[k] === String(t || '').trim()) return true;
          }
          return false;
        }

        function goalTitleFromState(st, cfg) {
          var gt = st.goal_type !== undefined ? st.goal_type : (cfg && cfg.goal_type);
          var stock = GOAL_LABELS[gt] || ((gt ? String(gt).toUpperCase() + ' GOAL' : 'GOAL'));
          var titleVal = st.title !== undefined ? st.title : (cfg && cfg.title);
          if (titleVal !== undefined && titleVal !== null) {
            var t = String(titleVal).trim();
            if (t && !isStockGoalTitle(t)) return t;
          }
          return stock;
        }

        function applySkin(skinName, accentFromConfig) {
          if (!skinName) return;
          var skins = Object.keys(SKIN_PALETTES);
          if (skins.indexOf(skinName) < 0) skinName = 'digital_core';
          skins.forEach(function(s) { root.classList.remove('skin-' + s); });
          root.classList.add('skin-' + skinName);
          activeSkin = skinName;
          var pal = SKIN_PALETTES[skinName];
          var accent = accentFromConfig;
          // Stock accents follow the selected skin; custom accents are preserved.
          if (!accent || SKIN_DEFAULT_ACCENTS[String(accent).toLowerCase()]) {
            accent = pal.accent;
          }
          applyPaletteVars(pal, accent);
        }

        function bumpNumber() {
          hudCurrent.classList.add('bump');
          setTimeout(function() { hudCurrent.classList.remove('bump'); }, 140);
        }

        function applyState(st) {
          if (!st) return;
          var cfg = st.config || config || {};
          if (st.config) config = st.config;

          var skinName = st.skin !== undefined ? st.skin : (cfg && cfg.skin);
          var accentVal = st.accent_color !== undefined ? st.accent_color : (cfg && cfg.accent_color);
          if (skinName) applySkin(skinName, accentVal);
          else if (accentVal) setAccent(accentVal);

          var scaleVal = st.scale_percent !== undefined ? st.scale_percent : (cfg && cfg.scale_percent);
          if (scaleVal !== undefined && scaleVal !== null) applyScale(scaleVal);

          hdrTitle.textContent = goalTitleFromState(st, cfg);
          var subVal = st.subtitle !== undefined ? st.subtitle : cfg.subtitle;
          if (subVal !== undefined) hdrSubtitle.textContent = subVal || '';

          var curVal = st.current_value !== undefined ? st.current_value : cfg.current_value;
          var tgtVal = st.target_value !== undefined ? st.target_value : cfg.target_value;
          if (curVal !== undefined) {
            var prev = hudCurrent.textContent;
            hudCurrent.textContent = fmtInt(curVal);
            if (prev && prev !== hudCurrent.textContent) bumpNumber();
          }
          if (tgtVal !== undefined) hudTarget.textContent = fmtInt(tgtVal);

          var progVal = st.progress;
          if (progVal === undefined && curVal !== undefined && tgtVal !== undefined) {
            progVal = tgtVal > 0 ? (curVal / tgtVal) : 0;
          }
          if (st.progress_percent !== undefined) {
            var pctDirect = Math.max(0, Math.min(100, Number(st.progress_percent) || 0));
            hudPercent.textContent = pctDirect + '%';
            energyBarFill.style.width = pctDirect + '%';
            setProgressTier(pctDirect);
          } else if (progVal !== undefined) {
            var pct = Math.round(Math.max(0, Math.min(1, progVal)) * 100);
            hudPercent.textContent = pct + '%';
            energyBarFill.style.width = pct + '%';
            setProgressTier(pct);
          }
        }

        function addRx(cls, ms) {
          coreArea.classList.add(cls);
          setTimeout(function() { coreArea.classList.remove(cls); }, ms || 400);
        }

        function fireShock(kind) {
          shockwave.className = 'shockwave go' + (kind ? ' ' + kind : '');
          setTimeout(function() { shockwave.className = 'shockwave'; }, 750);
        }

        function fireBeam() {
          var ang = -20 + Math.random() * 40;
          beam.style.transform = 'translate(-50%, -100%) rotate(' + ang + 'deg)';
          beam.className = 'beam go';
          setTimeout(function() { beam.className = 'beam'; }, 600);
        }

        function spawnParticles(count, mode) {
          if (config && config.enable_particles === false) return;
          mode = mode || 'burst';
          var n = Math.max(1, count | 0);
          for (var i = 0; i < n; i++) {
            (function(idx) {
              setTimeout(function() {
                var p = document.createElement('div');
                var tone = (idx % 5 === 0) ? 'mag' : ((idx % 7 === 0) ? 'warn' : '');
                p.className = 'fx-particle' + (tone ? ' ' + tone : '');
                var rect = coreArea.getBoundingClientRect();
                var rootRect = root.getBoundingClientRect();
                var cx = rect.left - rootRect.left + rect.width / 2;
                var cy = rect.top - rootRect.top + rect.height / 2;

                if (mode === 'stream') {
                  var side = Math.random() < 0.5 ? -1 : 1;
                  var sx = cx + side * (rect.width * (0.55 + Math.random() * 0.35));
                  var sy = cy + (Math.random() - 0.5) * rect.height * 0.8;
                  p.style.left = sx + 'px';
                  p.style.top = sy + 'px';
                  root.appendChild(p);
                  var start = performance.now();
                  function anim(now) {
                    var t = (now - start) / 650;
                    if (t >= 1) { if (p.parentNode) p.remove(); return; }
                    var x = sx + (cx - sx) * t;
                    var y = sy + (cy - sy) * t;
                    p.style.left = x + 'px';
                    p.style.top = y + 'px';
                    p.style.opacity = String(1 - t * 0.2);
                    p.style.transform = 'scale(' + (1 - t * 0.4) + ')';
                    requestAnimationFrame(anim);
                  }
                  requestAnimationFrame(anim);
                } else {
                  var angle = (Math.PI * 2 / n) * idx + Math.random() * 0.4;
                  var dist = (mode === 'explode' ? 30 : 12) + Math.random() * (mode === 'explode' ? 90 : 50);
                  p.style.left = cx + 'px';
                  p.style.top = cy + 'px';
                  root.appendChild(p);
                  var start2 = performance.now();
                  function anim2(now) {
                    var t = (now - start2) / (mode === 'explode' ? 900 : 700);
                    if (t >= 1) { if (p.parentNode) p.remove(); return; }
                    var ease = 1 - Math.pow(1 - t, 2);
                    p.style.left = (cx + Math.cos(angle) * dist * ease) + 'px';
                    p.style.top = (cy + Math.sin(angle) * dist * ease) + 'px';
                    p.style.opacity = String(1 - t);
                    requestAnimationFrame(anim2);
                  }
                  requestAnimationFrame(anim2);
                }
              }, idx * 18);
            })(i);
          }
        }

        function triggerGlitch() {
          if (config && config.enable_glitch === false) return;
          addRx('rx-glitch', 220);
          glitchLine.style.top = (8 + Math.random() * 84) + '%';
          glitchLine.style.opacity = '1';
          setTimeout(function() { glitchLine.style.opacity = '0'; }, 140);
        }

        function showNotif(text, type) {
          var el = document.createElement('div');
          el.className = 'notif' + (type && type !== 'follow' && type !== 'like' ? ' ' + type : '');
          el.textContent = text;
          el.style.left = (28 + Math.random() * 44) + '%';
          el.style.top = (36 + Math.random() * 28) + '%';
          notifArea.appendChild(el);
          setTimeout(function() { if (el.parentNode) el.remove(); }, 1000);
        }

        function showCombo(count) {
          comboDisplay.textContent = 'COMBO x' + count;
          comboDisplay.classList.add('show');
          addRx('rx-pulse', 450);
          spawnParticles(12, 'burst');
          setTimeout(function() { comboDisplay.classList.remove('show'); }, 1400);
        }

        function showMilestone(label, percent) {
          // CORE BREACH is reserved for the completion sequence, not toast chrome.
          if (String(label || '').toUpperCase() === 'CORE BREACH') return;
          mtLabel.textContent = label || '';
          mtPercent.textContent = (percent || 0) + '%';
          milestoneToast.classList.add('show');
          addRx('rx-pulse', 600);
          fireShock('');
          spawnParticles(16, 'burst');
          setTimeout(function() { milestoneToast.classList.remove('show'); }, 1800);
        }

        function playBreachSequence(nextTarget) {
          if (isBreaching) return;
          isBreaching = true;
          clearTier();
          root.classList.add('tier-breach');

          // rapid pulse
          addRx('rx-pulse', 500);
          spawnParticles(10, 'burst');

          setTimeout(function() {
            addRx('rx-pulse', 400);
            fireShock('');
          }, 280);

          // ring acceleration already via tier-breach; distortion
          setTimeout(function() {
            triggerGlitch();
            addRx('rx-shake', 350);
            spawnParticles(18, 'burst');
          }, 550);

          // extreme brightness + explosion
          setTimeout(function() {
            breachOverlay.classList.add('active');
            breachText.classList.add('show');
            fireShock('gift');
            spawnParticles(36, 'explode');
            triggerGlitch();
          }, 900);

          setTimeout(function() {
            triggerGlitch();
            addRx('rx-shake', 400);
            spawnParticles(20, 'burst');
          }, 1400);

          // rebuild / reset
          setTimeout(function() {
            breachText.classList.remove('show');
            breachOverlay.classList.remove('active');
            if (nextTarget) {
              newTargetText.textContent = 'NEW TARGET ' + fmtInt(nextTarget);
              newTargetText.classList.add('show');
            }
          }, 2400);

          setTimeout(function() {
            newTargetText.classList.remove('show');
            isBreaching = false;
            clearTier();
            setProgressTier(currentPct >= 100 ? 0 : currentPct);
            addRx('rx-pulse', 500);
            spawnParticles(10, 'burst');
          }, 3800);
        }

        function processEvent(ev) {
          if (!ev) return;
          var t = ev.type;
          var payload = ev.payload || {};
          var meta = payload.metadata || {};

          if (t === 'goal_complete') {
            playBreachSequence(payload.next_target);
            return;
          }

          if (t === 'milestone_reached') {
            showMilestone(payload.label || '', payload.percent || 0);
            if (payload.effect === 'explosion' || payload.percent === 100) {
              playBreachSequence(null);
            } else if (payload.effect === 'glitch') {
              triggerGlitch();
              addRx('rx-shake', 300);
            } else {
              spawnParticles(14, 'burst');
              addRx('rx-pulse', 500);
            }
            return;
          }

          if (t === 'event_absorbed') {
            var type = payload.type || 'event';
            var amount = payload.amount || 1;
            var combo = payload.combo || 0;
            var batched = !!(payload.batched) || !!(meta.batched) || amount > 1;

            if (type === 'follow') {
              showNotif('+1 FOLLOW', 'follow');
              addRx('rx-pulse', 400);
              spawnParticles(6, 'burst');
            } else if (type === 'like') {
              var label = amount > 1 ? ('+' + amount + ' LIKES') : '+1 LIKE';
              showNotif(label, 'like');
              if (batched || amount > 5) {
                addRx('rx-pulse', 500);
                fireShock('');
                spawnParticles(Math.min(28, 10 + amount), 'stream');
              } else {
                spawnParticles(8, 'stream');
                addRx('rx-pulse', 350);
              }
              if (combo > 5) showCombo(combo);
            } else if (type === 'share') {
              showNotif('SHARE DETECTED', 'share');
              fireBeam();
              fireShock('share');
              spawnParticles(14, 'stream');
              addRx('rx-pulse', 450);
            } else if (type === 'gift') {
              var gname = payload.gift_name || meta.gift_name || 'Gift';
              showNotif('GIFT: ' + gname, 'gift');
              fireShock('gift');
              addRx('rx-shake', 400);
              spawnParticles(22, 'explode');
              triggerGlitch();
              if ((payload.total_coins || meta.total_coins || 0) > 1000) {
                setTimeout(function() { fireShock('gift'); triggerGlitch(); }, 180);
              }
            } else if (type === 'comment') {
              showNotif('COMMENT', 'like');
              spawnParticles(4, 'burst');
              addRx('rx-pulse', 300);
            }

            if (currentPct >= 90) {
              triggerGlitch();
            }
            return;
          }

          if (t === 'combo_update' && payload.combo > 3) {
            showCombo(payload.combo);
          }

          if (t === 'critical_state') {
            if (payload.level === 'extreme' || payload.level === 'high') {
              if (!isBreaching) triggerGlitch();
            }
          }

          if (t === 'core_evolved') {
            fireShock('');
            spawnParticles(20, 'explode');
            addRx('rx-pulse', 500);
          }

          if (t === 'goal_reset') {
            breachText.classList.remove('show');
            breachOverlay.classList.remove('active');
            isBreaching = false;
            setProgressTier(0);
          }
        }

        function handleMsg(data) {
          if (!data || !data.op) return;
          if (data.op === 'initial_state') {
            applyState(data.state || {});
            state = data.state || {};
            if (state.visual_events) {
              state.visual_events.forEach(function(ev) { processEvent(ev); });
            }
            return;
          }
          if (data.op === 'patch') {
            var p = data.patch || {};
            applyState(p);
            state = Object.assign(state || {}, p);
            if (p.visual_events) {
              p.visual_events.forEach(function(ev) { processEvent(ev); });
            }
            if (p.combo_count !== undefined && p.combo_count !== lastCombo) {
              lastCombo = p.combo_count;
              if (p.combo_count > 1) showCombo(p.combo_count);
              else comboDisplay.classList.remove('show');
            }
          }
        }

        function ambientTick() {
          if (isBreaching) return;
          if (currentPct >= 90 && config && config.enable_glitch !== false) {
            if (Math.random() < 0.35) triggerGlitch();
          } else if (currentPct >= 70) {
            if (Math.random() < 0.2) spawnParticles(3, 'burst');
          } else if (currentPct >= 35) {
            if (Math.random() < 0.12) spawnParticles(2, 'burst');
          }
        }

        ambientTimer = setInterval(ambientTick, 2200);

        function connect() {
          var tries = 0;
          var backoff = 500;
          var wsUrl = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws';
          var ws = null;

          function doConnect() {
            tries += 1;
            backoff = Math.min(5000, 250 + Math.floor(Math.random() * 250) + (tries * 350));
            try { ws = new WebSocket(wsUrl); }
            catch (e) { setTimeout(doConnect, backoff); return; }

            ws.onopen = function() {
              tries = 0;
              var subscribeMsg = """ + _json_for_script(subscribe_msg) + """;
              ws.send(JSON.stringify(subscribeMsg));
            };
            ws.onmessage = function(ev) {
              try { handleMsg(JSON.parse(ev.data)); } catch (e) {}
            };
            ws.onclose = function() { setTimeout(doConnect, backoff); };
            ws.onerror = function() { try { ws.close(); } catch (e) {} };
          }
          doConnect();
        }

        connect();
      })();
    </script>
  </body>
</html>"""
        safe_skin = skin if skin in {
            "digital_core", "boss", "reactor", "rocket", "vault", "tower", "creature",
        } else "digital_core"
        palette = _skin_palette(safe_skin)
        accent_use = (accent or "").strip()
        if not accent_use.startswith("#"):
            accent_use = palette["accent"]
        # If accent is still a stock skin default, follow the selected skin palette.
        stock_accents = {p["accent"].lower() for p in (
            _skin_palette(s) for s in (
                "digital_core", "boss", "reactor", "rocket", "vault", "tower", "creature",
            )
        )}
        if accent_use.lower() in stock_accents:
            accent_use = palette["accent"]
        root_style = (
            f"--sg-accent:{accent_use};"
            f"--sg-magenta:{palette['magenta']};"
            f"--sg-purple:{palette['purple']};"
            f"--sg-warn:{palette['warn']};"
            f"--sg-ok:{palette['ok']};"
            f"--sg-bg:{palette['bg']};"
            f"--sg-widget-scale:{max(40, min(250, int(scale_percent))) / 100:.4f};"
        )
        html = html.replace(
            'class="root tier-idle" id="root" data-sg-root="1"',
            f'class="root tier-idle skin-{safe_skin}" id="root" style="{root_style}"',
            1,
        )
        return html
