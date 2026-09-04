from __future__ import annotations

import json
from typing import Any

from stream_cheremsha import l10n
from stream_cheremsha.overlays.models import normalize_instance_id
from stream_cheremsha.overlays.ui_locale import load_ui_locale
from stream_cheremsha.overlays.webcam_frame_overlay_config import (
    load_webcam_frame_overlay_config,
    webcam_frame_overlay_config_to_public_dict,
)

_I18N_KEYS = (
    "status.online",
    "status.offline",
    "status.live",
    "boot.online",
)


def _overlay_i18n_bundle() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {"uk": {}, "en": {}}
    for short in _I18N_KEYS:
        key = f"webcam_frame.{short}"
        out["uk"][short] = l10n.tr("uk", key)
        out["en"][short] = l10n.tr("en", key)
    return out


def _json_for_script(value: Any) -> str:
    s = json.dumps(value, ensure_ascii=False)
    return s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


class WebcamFrameOverlayType:
    type = "webcam_frame"

    def render_html(self, params: dict[str, Any]) -> str:
        raw_instance = params.get("instance")
        try:
            instance = normalize_instance_id(str(raw_instance or ""))
        except ValueError:
            instance = "default"

        cfg = load_webcam_frame_overlay_config()
        locale = load_ui_locale()
        initial = {
            "config": webcam_frame_overlay_config_to_public_dict(cfg),
            "locale": locale,
        }
        subscribe_msg = {
            "op": "subscribe",
            "type": "webcam_frame",
            "instance": instance,
            "params": {},
        }
        i18n = _overlay_i18n_bundle()

        doc = _DOCUMENT_TEMPLATE
        doc = doc.replace("__WF_CSS__", _CSS)
        doc = doc.replace("__WF_STATE_JSON__", _json_for_script(initial))
        doc = doc.replace("__WF_I18N_JSON__", _json_for_script(i18n))
        doc = doc.replace("__WF_SUBSCRIBE_JSON__", _json_for_script(subscribe_msg))
        doc = doc.replace("__WF_JS__", _JS)
        return doc

    def initial_state(self, params: dict[str, Any]) -> dict[str, Any]:
        _ = normalize_instance_id(str(params.get("instance") or ""))
        cfg = load_webcam_frame_overlay_config()
        return {
            "config": webcam_frame_overlay_config_to_public_dict(cfg),
            "locale": load_ui_locale(),
        }


_CSS = r"""
* { box-sizing: border-box; }
html, body {
  margin: 0; padding: 0; width: 100%; height: 100%;
  background: transparent !important;
  overflow: hidden;
}
body { position: relative; }

.root {
  position: absolute; inset: 0;
  background: transparent;
  font-family: 'VT323', 'Segoe UI', system-ui, sans-serif;
  --wf-scale: 1;
  --wf-corner-base: clamp(24px, min(3.6vw, 6.4vh), 46px);
  --wf-corner: calc(var(--wf-corner-base) * var(--wf-scale));
  --wf-band: calc(clamp(11px, 1.15vw, 17px) * var(--wf-scale));
  --wf-rail-thick: calc(clamp(2px, 0.22vw, 3px) * var(--wf-scale));
  --wf-hair-thick: 1px;
  --wf-loop-dur: 11s;
  --wf-glow-a: 0.36;

  /* NEON CYBER (default) */
  --wf-accent-rgb: 0, 232, 255;
  --wf-secondary-rgb: 255, 43, 214;
  --wf-warn-rgb: 255, 207, 77;
  opacity: 1;
  transition: opacity .5s ease;
}
.root.hidden { opacity: 0; pointer-events: none; }

.root.theme-synthwave { --wf-accent-rgb: 255, 110, 199; --wf-secondary-rgb: 155, 92, 255; --wf-warn-rgb: 94, 200, 255; }
.root.theme-toxic     { --wf-accent-rgb: 186, 255, 41; --wf-secondary-rgb: 57, 255, 136; --wf-warn-rgb: 234, 255, 107; }
.root.theme-ice        { --wf-accent-rgb: 126, 240, 255; --wf-secondary-rgb: 160, 196, 255; --wf-warn-rgb: 255, 255, 255; }
.root.theme-amber      { --wf-accent-rgb: 255, 176, 32; --wf-secondary-rgb: 255, 122, 48; --wf-warn-rgb: 255, 224, 102; }
.root.theme-critical   { --wf-accent-rgb: 255, 59, 59; --wf-secondary-rgb: 255, 138, 0; --wf-warn-rgb: 255, 222, 89; }

.root.intensity-low    { --wf-glow-a: 0.22; --wf-loop-dur: 15s; }
.root.intensity-medium { --wf-glow-a: 0.36; --wf-loop-dur: 11s; }
.root.intensity-high   { --wf-glow-a: 0.5;  --wf-loop-dur: 8s; }

.wf-glow-ambient {
  position: absolute; inset: 0; pointer-events: none;
  box-shadow: inset 0 0 calc(38px * var(--wf-scale)) rgba(var(--wf-accent-rgb), calc(var(--wf-glow-a) * 0.16));
  opacity: 0.85;
  animation: wfBreathe 5.4s ease-in-out infinite;
}
@keyframes wfBreathe {
  0%, 100% { opacity: 0.55; }
  50% { opacity: 1; }
}
.root.no-breathe .wf-glow-ambient { animation: none; opacity: 0.7; }

.wf-frame { position: absolute; inset: 0; pointer-events: none; }

/* ---------- RAILS (stretch between fixed-size corners) ---------- */
.rail { position: absolute; pointer-events: none; }
.rail-top, .rail-bottom { left: var(--wf-corner); right: var(--wf-corner); height: var(--wf-band); }
.rail-left, .rail-right { top: var(--wf-corner); bottom: var(--wf-corner); width: var(--wf-band); }
.rail-top { top: 0; }
.rail-bottom { bottom: 0; }
.rail-left { left: 0; }
.rail-right { right: 0; }

.rail-struct {
  position: absolute; background: rgba(var(--wf-secondary-rgb), 0.32);
}
.rail-top .rail-struct, .rail-bottom .rail-struct { left: 0; right: 0; height: var(--wf-hair-thick); }
.rail-left .rail-struct, .rail-right .rail-struct { top: 0; bottom: 0; width: var(--wf-hair-thick); }
.rail-top .rail-struct { top: 0; }
.rail-bottom .rail-struct { bottom: 0; }
.rail-left .rail-struct { left: 0; }
.rail-right .rail-struct { right: 0; }

.rail-accent {
  position: absolute; background: rgb(var(--wf-accent-rgb));
  filter:
    drop-shadow(0 0 calc(2px * var(--wf-scale)) rgba(var(--wf-accent-rgb), 0.95))
    drop-shadow(0 0 calc(7px * var(--wf-scale)) rgba(var(--wf-accent-rgb), 0.55))
    drop-shadow(0 0 calc(16px * var(--wf-scale)) rgba(var(--wf-accent-rgb), 0.22));
  opacity: 0.92;
}
.rail-top .rail-accent, .rail-bottom .rail-accent { left: 0; right: 0; height: var(--wf-rail-thick); }
.rail-left .rail-accent, .rail-right .rail-accent { top: 0; bottom: 0; width: var(--wf-rail-thick); }
.rail-top .rail-accent { top: calc(var(--wf-band) * 0.28); }
.rail-bottom .rail-accent { bottom: calc(var(--wf-band) * 0.28); }
.rail-left .rail-accent { left: calc(var(--wf-band) * 0.28); }
.rail-right .rail-accent { right: calc(var(--wf-band) * 0.28); }

.rail-inner {
  position: absolute; opacity: 0.42;
}
.rail-top .rail-inner, .rail-bottom .rail-inner {
  left: 6%; right: 6%; height: 1px;
  background: repeating-linear-gradient(90deg, rgba(var(--wf-secondary-rgb), 0.8) 0 5px, transparent 5px 13px);
}
.rail-left .rail-inner, .rail-right .rail-inner {
  top: 6%; bottom: 6%; width: 1px;
  background: repeating-linear-gradient(180deg, rgba(var(--wf-secondary-rgb), 0.8) 0 5px, transparent 5px 13px);
}
.rail-top .rail-inner { top: calc(var(--wf-band) * 0.72); }
.rail-bottom .rail-inner { bottom: calc(var(--wf-band) * 0.72); }
.rail-left .rail-inner { left: calc(var(--wf-band) * 0.72); }
.rail-right .rail-inner { right: calc(var(--wf-band) * 0.72); }

.rail-scan {
  position: absolute; inset: 0; opacity: 0.16; mix-blend-mode: screen;
}
.rail-top .rail-scan, .rail-bottom .rail-scan {
  background: repeating-linear-gradient(180deg, rgba(255,255,255,0.5) 0 1px, transparent 1px 3px);
}
.rail-left .rail-scan, .rail-right .rail-scan {
  background: repeating-linear-gradient(90deg, rgba(255,255,255,0.5) 0 1px, transparent 1px 3px);
}
.root.no-crt .rail-scan { display: none; }

/* ---------- ENERGY FLOW (single packet touring the whole perimeter) ---------- */
.rail-energy {
  position: absolute;
  border-radius: 999px;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.95), transparent);
  filter: drop-shadow(0 0 calc(5px * var(--wf-scale)) rgba(var(--wf-accent-rgb), 0.95))
          drop-shadow(0 0 calc(12px * var(--wf-scale)) rgba(var(--wf-accent-rgb), 0.6));
  opacity: 0;
  will-change: transform, opacity;
}
.rail-top .rail-energy, .rail-bottom .rail-energy {
  width: 14%; height: calc(var(--wf-rail-thick) + 1px);
}
.rail-left .rail-energy, .rail-right .rail-energy {
  height: 14%; width: calc(var(--wf-rail-thick) + 1px);
}
.rail-top .rail-energy { top: calc(var(--wf-band) * 0.28); }
.rail-bottom .rail-energy { bottom: calc(var(--wf-band) * 0.28); }
.rail-left .rail-energy { left: calc(var(--wf-band) * 0.28); }
.rail-right .rail-energy { right: calc(var(--wf-band) * 0.28); }

.root.online.energy-on .rail-top .rail-energy { animation: wfEnergyTop var(--wf-loop-dur) linear infinite; }
.root.online.energy-on .rail-right .rail-energy { animation: wfEnergyRight var(--wf-loop-dur) linear infinite; }
.root.online.energy-on .rail-bottom .rail-energy { animation: wfEnergyBottom var(--wf-loop-dur) linear infinite; }
.root.online.energy-on .rail-left .rail-energy { animation: wfEnergyLeft var(--wf-loop-dur) linear infinite; }

@keyframes wfEnergyTop {
  0%     { left: -14%; opacity: 0; }
  1%     { opacity: 1; }
  24%    { left: 100%; opacity: 1; }
  26%    { opacity: 0; left: 100%; }
  100%   { opacity: 0; left: 100%; }
}
@keyframes wfEnergyRight {
  0%, 25%   { opacity: 0; top: -14%; }
  26%       { opacity: 1; top: -14%; }
  49%       { top: 100%; opacity: 1; }
  51%, 100% { opacity: 0; top: 100%; }
}
@keyframes wfEnergyBottom {
  0%, 50%   { opacity: 0; right: -14%; }
  51%       { opacity: 1; right: -14%; }
  74%       { right: 100%; opacity: 1; }
  76%, 100% { opacity: 0; right: 100%; }
}
@keyframes wfEnergyLeft {
  0%, 75%   { opacity: 0; bottom: -14%; }
  76%       { opacity: 1; bottom: -14%; }
  99%       { bottom: 100%; opacity: 1; }
  100%      { opacity: 0; bottom: 100%; }
}

/* ---------- LIGHT SWEEP (rare, confined to one edge at a time) ---------- */
.rail-sweep {
  position: absolute; inset: 0; opacity: 0;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.85), transparent);
  will-change: transform, opacity;
}
.rail-left .rail-sweep, .rail-right .rail-sweep {
  background: linear-gradient(180deg, transparent, rgba(255,255,255,0.85), transparent);
}
.root.online.sweep-on .rail-top .rail-sweep { animation: wfSweepH 17s ease-in-out infinite; }
.root.online.sweep-on .rail-bottom .rail-sweep { animation: wfSweepH 23s ease-in-out infinite; animation-delay: 9s; }
.root.online.sweep-on .rail-left .rail-sweep { animation: wfSweepV 29s ease-in-out infinite; animation-delay: 4s; }
.root.online.sweep-on .rail-right .rail-sweep { animation: wfSweepV 31s ease-in-out infinite; animation-delay: 16s; }
@keyframes wfSweepH {
  0%, 92% { opacity: 0; transform: translateX(-30%); }
  94%     { opacity: 0.9; }
  99%     { opacity: 0; transform: translateX(130%); }
  100%    { opacity: 0; transform: translateX(-30%); }
}
@keyframes wfSweepV {
  0%, 92% { opacity: 0; transform: translateY(-30%); }
  94%     { opacity: 0.9; }
  99%     { opacity: 0; transform: translateY(130%); }
  100%    { opacity: 0; transform: translateY(-30%); }
}

/* ---------- CORNERS (fixed size, unique per-corner detail) ---------- */
.corner { position: absolute; width: var(--wf-corner); height: var(--wf-corner); }
.corner-tl { top: 0; left: 0; }
.corner-tr { top: 0; right: 0; }
.corner-bl { bottom: 0; left: 0; }
.corner-br { bottom: 0; right: 0; }

.corner-bracket {
  position: absolute; inset: 0;
  filter:
    drop-shadow(0 0 calc(2px * var(--wf-scale)) rgba(var(--wf-accent-rgb), 0.95))
    drop-shadow(0 0 calc(8px * var(--wf-scale)) rgba(var(--wf-accent-rgb), 0.5))
    drop-shadow(0 0 calc(18px * var(--wf-scale)) rgba(var(--wf-accent-rgb), 0.22));
}
.corner-tl .corner-bracket { border-top: var(--wf-rail-thick) solid rgb(var(--wf-accent-rgb)); border-left: var(--wf-rail-thick) solid rgb(var(--wf-accent-rgb)); clip-path: polygon(0 26%, 26% 0, 100% 0, 100% 100%, 0 100%); }
.corner-tr .corner-bracket { border-top: var(--wf-rail-thick) solid rgb(var(--wf-accent-rgb)); border-right: var(--wf-rail-thick) solid rgb(var(--wf-accent-rgb)); clip-path: polygon(0 0, 74% 0, 100% 26%, 100% 100%, 0 100%); }
.corner-bl .corner-bracket { border-bottom: var(--wf-rail-thick) solid rgb(var(--wf-accent-rgb)); border-left: var(--wf-rail-thick) solid rgb(var(--wf-accent-rgb)); clip-path: polygon(0 0, 100% 0, 100% 100%, 26% 100%, 0 74%); }
.corner-br .corner-bracket { border-bottom: var(--wf-rail-thick) solid rgb(var(--wf-accent-rgb)); border-right: var(--wf-rail-thick) solid rgb(var(--wf-accent-rgb)); clip-path: polygon(0 0, 100% 0, 100% 74%, 74% 100%, 0 100%); }

.corner-pulse {
  position: absolute; inset: 8%; border-radius: 40%;
  background: radial-gradient(circle, rgba(var(--wf-accent-rgb), 0.55), transparent 70%);
  opacity: 0;
}
.root.online.energy-on .corner-tl .corner-pulse { animation: wfPulseTL var(--wf-loop-dur) ease-in-out infinite; }
.root.online.energy-on .corner-tr .corner-pulse { animation: wfPulseTR var(--wf-loop-dur) ease-in-out infinite; }
.root.online.energy-on .corner-bl .corner-pulse { animation: wfPulseBL var(--wf-loop-dur) ease-in-out infinite; }
.root.online.energy-on .corner-br .corner-pulse { animation: wfPulseBR var(--wf-loop-dur) ease-in-out infinite; }
@keyframes wfPulseTL { 0% { opacity: .85; } 4% { opacity: 0; } 97% { opacity: 0; } 100% { opacity: .85; } }
@keyframes wfPulseTR { 0%, 22% { opacity: 0; } 26% { opacity: .85; } 31% { opacity: 0; } 100% { opacity: 0; } }
@keyframes wfPulseBL { 0%, 47% { opacity: 0; } 51% { opacity: .85; } 56% { opacity: 0; } 100% { opacity: 0; } }
@keyframes wfPulseBR { 0%, 72% { opacity: 0; } 76% { opacity: .85; } 81% { opacity: 0; } 100% { opacity: 0; } }

/* Micro HUD details, unique per corner */
.corner-detail { position: absolute; }
.corner-node {
  width: calc(6px * var(--wf-scale)); height: calc(6px * var(--wf-scale));
  background: rgb(var(--wf-warn-rgb));
  transform: rotate(45deg);
  top: calc(34% - 3px * var(--wf-scale)); left: calc(34% - 3px * var(--wf-scale));
  box-shadow: 0 0 6px rgba(var(--wf-warn-rgb), 0.9);
  animation: wfNodeBlink 3.1s ease-in-out infinite;
}
@keyframes wfNodeBlink { 0%, 100% { opacity: .55; } 50% { opacity: 1; } }
.corner-dots { top: 30%; right: 22%; display: flex; flex-direction: column; gap: calc(3px * var(--wf-scale)); align-items: flex-end; }
.corner-dots span {
  width: calc(4px * var(--wf-scale)); height: calc(4px * var(--wf-scale)); border-radius: 50%;
  background: rgb(var(--wf-secondary-rgb)); box-shadow: 0 0 5px rgba(var(--wf-secondary-rgb), 0.85);
  display: block; opacity: .8;
}
.corner-ticks { bottom: 24%; left: 22%; display: flex; flex-direction: column; gap: calc(2px * var(--wf-scale)); }
.corner-ticks span {
  display: block; height: 1.5px; background: rgb(var(--wf-secondary-rgb));
  box-shadow: 0 0 4px rgba(var(--wf-secondary-rgb), 0.7); opacity: .75;
}
.corner-ticks span:nth-child(1) { width: calc(6px * var(--wf-scale)); }
.corner-ticks span:nth-child(2) { width: calc(10px * var(--wf-scale)); }
.corner-ticks span:nth-child(3) { width: calc(14px * var(--wf-scale)); }
.corner-vents { bottom: 26%; right: 24%; display: flex; gap: calc(2px * var(--wf-scale)); }
.corner-vents span {
  display: block; width: 1.5px; height: calc(11px * var(--wf-scale));
  background: rgb(var(--wf-warn-rgb)); opacity: .55; transform: rotate(24deg);
}

/* ---------- STATUS INDICATORS (secondary, unobtrusive) ---------- */
.hud-status {
  position: absolute; display: flex; align-items: center; gap: calc(6px * var(--wf-scale));
  font-size: calc(13px * var(--wf-scale)); letter-spacing: 0.08em; color: rgba(255,255,255,0.82);
  text-shadow: 0 0 6px rgba(var(--wf-accent-rgb), 0.5);
  white-space: nowrap; opacity: 0.92;
}
.hud-status-left {
  top: calc(var(--wf-corner) * 0.62); left: calc(var(--wf-corner) * 1.15);
}
.hud-status-right {
  top: calc(var(--wf-corner) * 0.62); right: calc(var(--wf-corner) * 1.15);
}
.hud-status .dot {
  width: calc(6px * var(--wf-scale)); height: calc(6px * var(--wf-scale)); border-radius: 50%;
  background: rgb(57, 255, 136); box-shadow: 0 0 6px rgba(57, 255, 136, 0.9);
  animation: wfDotPulse 2.4s ease-in-out infinite;
}
@keyframes wfDotPulse { 0%, 100% { opacity: .5; } 50% { opacity: 1; } }
.root.no-status .hud-status { display: none; }
.root.narrow-xs .hud-status { display: none; }

/* ---------- SPARKS (bounded pool of 4, GPU-cheap) ---------- */
.spark {
  position: absolute; width: calc(3px * var(--wf-scale)); height: calc(3px * var(--wf-scale));
  border-radius: 50%; background: #fff; opacity: 0; pointer-events: none;
  box-shadow: 0 0 6px rgba(255,255,255,0.9), 0 0 12px rgba(var(--wf-accent-rgb), 0.8);
}
.spark.spark-active {
  animation: wfSparkFly 0.9s ease-out forwards;
}
@keyframes wfSparkFly {
  0%   { opacity: 0; transform: translate(0, 0) scale(0.6); }
  15%  { opacity: 1; }
  100% { opacity: 0; transform: translate(var(--wf-spark-dx, 10px), var(--wf-spark-dy, -10px)) scale(1); }
}

/* ---------- MICRO GLITCH (rare, short, controlled) ---------- */
.glitch-frag {
  position: absolute; opacity: 0; background: #fff; mix-blend-mode: screen; pointer-events: none;
}
.root.glitch-active .rail-accent { animation: wfGlitchShift 0.14s steps(2, end); }
.root.glitch-active .corner-bracket { animation: wfGlitchShift 0.14s steps(2, end); }
.root.glitch-active .glitch-frag { animation: wfGlitchFrag 0.16s steps(2, end); }
@keyframes wfGlitchShift {
  0%   { transform: translate(0, 0); filter: none; }
  40%  { transform: translate(2px, -1px); filter: drop-shadow(-2px 0 rgba(255,0,120,0.6)) drop-shadow(2px 0 rgba(0,255,255,0.6)); }
  70%  { transform: translate(-1px, 1px); }
  100% { transform: translate(0, 0); filter: none; }
}
@keyframes wfGlitchFrag {
  0%   { opacity: 0; }
  30%  { opacity: 0.8; }
  100% { opacity: 0; }
}

/* ---------- BOOT SEQUENCE ---------- */
.root.booting .rail-struct,
.root.booting .rail-inner,
.root.booting .rail-scan { opacity: 0 !important; }
.root.booting .rail-accent { opacity: 0; transform: scaleX(0); transform-origin: left center; }
.root.booting .rail-left .rail-accent, .root.booting .rail-right .rail-accent { transform: scaleY(0); transform-origin: top center; }
.root.booting .corner-bracket { opacity: 0; transform: scale(0.5); }
.root.booting .corner-detail, .root.booting .hud-status, .root.booting .corner-pulse { opacity: 0; }

.root.boot-line .rail-top .rail-accent { animation: wfBootDraw 0.16s ease-out forwards; }
.root.boot-rail-right .rail-right .rail-accent { animation: wfBootDrawV 0.16s ease-out forwards; }
.root.boot-rail-bottom .rail-bottom .rail-accent { animation: wfBootDraw 0.16s ease-out forwards; }
.root.boot-rail-left .rail-left .rail-accent { animation: wfBootDrawV 0.16s ease-out forwards; }
@keyframes wfBootDraw { 0% { opacity: 0.9; transform: scaleX(0); } 100% { opacity: 0.92; transform: scaleX(1); } }
@keyframes wfBootDrawV { 0% { opacity: 0.9; transform: scaleY(0); } 100% { opacity: 0.92; transform: scaleY(1); } }

.root.boot-corners .corner-bracket { opacity: 1; transform: scale(1); transition: opacity .18s ease, transform .18s cubic-bezier(.2,1.6,.4,1); }
.root.boot-corners .corner-detail, .root.boot-corners .hud-status { opacity: 1; transition: opacity .25s ease .05s; }
.root.boot-corners .corner-pulse { transition: none; }

.root.boot-flash .wf-glow-ambient { animation: none; opacity: 1; box-shadow: inset 0 0 calc(60px * var(--wf-scale)) rgba(var(--wf-accent-rgb), 0.55); transition: box-shadow .35s ease, opacity .35s ease; }

.wf-boot-label {
  position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%);
  font-family: 'Press Start 2P', 'VT323', monospace; font-size: calc(11px * var(--wf-scale));
  letter-spacing: 0.12em; color: rgb(var(--wf-accent-rgb));
  text-shadow: 0 0 10px rgba(var(--wf-accent-rgb), 0.8);
  opacity: 0; pointer-events: none; white-space: nowrap;
}
.root.boot-label .wf-boot-label { animation: wfBootLabel 0.9s ease-out forwards; }
@keyframes wfBootLabel {
  0%   { opacity: 0; letter-spacing: 0.4em; }
  30%  { opacity: 1; letter-spacing: 0.12em; }
  75%  { opacity: 1; }
  100% { opacity: 0; }
}

/* ---------- FRAME STYLES ---------- */
/* style-primary is the base look defined above - no overrides needed. */

/* MINIMAL: corner brackets only, no edge rails, quiet ambience */
.root.style-minimal .rail { display: none; }
.root.style-minimal .corner { width: calc(var(--wf-corner) * 0.52); height: calc(var(--wf-corner) * 0.52); }
.root.style-minimal .corner-bracket { clip-path: none; border-width: calc(var(--wf-rail-thick) * 0.85); opacity: 0.85; }
.root.style-minimal .corner-pulse,
.root.style-minimal .corner-detail { display: none; }
.root.style-minimal .wf-glow-ambient { opacity: 0.55; }

/* TACTICAL: thin dashed perimeter + reticle ticks at edge midpoints */
.root.style-tactical .rail-struct,
.root.style-tactical .rail-inner,
.root.style-tactical .rail-scan { display: none; }
.root.style-tactical .rail-top .rail-accent, .root.style-tactical .rail-bottom .rail-accent {
  height: var(--wf-hair-thick); opacity: 0.8;
}
.root.style-tactical .rail-left .rail-accent, .root.style-tactical .rail-right .rail-accent {
  width: var(--wf-hair-thick); opacity: 0.8;
}
.root.style-tactical .rail-top .rail-accent { top: 0; }
.root.style-tactical .rail-bottom .rail-accent { bottom: 0; }
.root.style-tactical .rail-left .rail-accent { left: 0; }
.root.style-tactical .rail-right .rail-accent { right: 0; }
.root.style-tactical .rail-top::after, .root.style-tactical .rail-bottom::after {
  content: ""; position: absolute; left: 50%; top: 0; bottom: 0; width: var(--wf-hair-thick);
  background: rgba(var(--wf-accent-rgb), 0.75); transform: translateX(-50%);
}
.root.style-tactical .rail-left::after, .root.style-tactical .rail-right::after {
  content: ""; position: absolute; top: 50%; left: 0; right: 0; height: var(--wf-hair-thick);
  background: rgba(var(--wf-accent-rgb), 0.75); transform: translateY(-50%);
}
.root.style-tactical .corner-bracket { clip-path: none; border-style: dashed; }
.root.style-tactical .corner-pulse { border-radius: 15%; }
.root.style-tactical .wf-frame::before {
  content: ""; position: absolute; inset: calc(var(--wf-band) * 0.34); pointer-events: none;
  border: var(--wf-hair-thick) dashed rgba(var(--wf-accent-rgb), 0.4);
}

/* BROADCAST: thick top/bottom bars, no side rails or corner brackets */
.root.style-broadcast .rail-left,
.root.style-broadcast .rail-right { display: none; }
.root.style-broadcast .rail-top,
.root.style-broadcast .rail-bottom { height: calc(var(--wf-band) * 2.1); }
.root.style-broadcast .rail-inner,
.root.style-broadcast .rail-scan { display: none; }
.root.style-broadcast .rail-top .rail-struct, .root.style-broadcast .rail-bottom .rail-struct {
  height: 100%; opacity: 1;
  background: linear-gradient(180deg, rgba(var(--wf-accent-rgb), 0.22), rgba(var(--wf-accent-rgb), 0.02) 70%, transparent);
}
.root.style-broadcast .rail-bottom .rail-struct {
  background: linear-gradient(0deg, rgba(var(--wf-accent-rgb), 0.22), rgba(var(--wf-accent-rgb), 0.02) 70%, transparent);
}
.root.style-broadcast .rail-top .rail-accent, .root.style-broadcast .rail-bottom .rail-accent {
  height: calc(var(--wf-rail-thick) * 2.2);
}
.root.style-broadcast .rail-top .rail-accent { top: 0; }
.root.style-broadcast .rail-bottom .rail-accent { bottom: 0; }
.root.style-broadcast .corner-bracket,
.root.style-broadcast .corner-pulse,
.root.style-broadcast .corner-detail { display: none; }

/* HOLOGRAM: dashed glowing rails + rounded pulsing corner nodes */
.root.style-hologram .rail-struct,
.root.style-hologram .rail-inner,
.root.style-hologram .rail-scan { display: none; }
.root.style-hologram .rail-top .rail-accent, .root.style-hologram .rail-bottom .rail-accent {
  background: repeating-linear-gradient(90deg, rgb(var(--wf-accent-rgb)) 0 8px, transparent 8px 15px);
}
.root.style-hologram .rail-left .rail-accent, .root.style-hologram .rail-right .rail-accent {
  background: repeating-linear-gradient(180deg, rgb(var(--wf-accent-rgb)) 0 8px, transparent 8px 15px);
}
.root.style-hologram .corner-bracket {
  border-radius: 50%; clip-path: none; opacity: 0.85;
  animation: wfHoloRing 2.8s ease-in-out infinite;
}
.root.style-hologram .corner-pulse { border-radius: 50%; }
@keyframes wfHoloRing {
  0%, 100% { opacity: 0.5; transform: scale(0.94); }
  50%      { opacity: 1;   transform: scale(1.04); }
}

/* ---------- SHUTDOWN ---------- */
.root.shutting-down .rail-accent,
.root.shutting-down .corner-bracket { transition: opacity .5s ease; opacity: 0.08; }
.root.shutting-down .corner-detail,
.root.shutting-down .hud-status,
.root.shutting-down .rail-energy,
.root.shutting-down .rail-sweep,
.root.shutting-down .corner-pulse { transition: opacity .3s ease; opacity: 0; }
.root.shutting-down .wf-glow-ambient { transition: opacity .5s ease; opacity: 0; }

@media (prefers-reduced-motion: reduce) {
  .wf-glow-ambient { animation: none !important; opacity: 0.6; }
  .rail-energy, .corner-pulse, .rail-sweep { animation: none !important; opacity: 0 !important; }
  .hud-status .dot { animation: none !important; opacity: .8; }
  .corner-node { animation: none !important; opacity: .8; }
  .root.style-hologram .corner-bracket { animation: none !important; opacity: 0.75; }
}

/* ---------- ACTIVITY STATE MODULATION ---------- */
.root { transition: --wf-glow-a 0.3s ease, --wf-loop-dur 0.3s ease; }

/* Glow opacity modulated by activity score (0-100),
   blended with the intensity base via clamp(). */
.wf-glow-ambient {
  box-shadow: inset 0 0 calc(38px * var(--wf-scale))
    rgba(var(--wf-accent-rgb),
      calc(var(--wf-glow-a) * 0.16 * clamp(0.5, 0.5 + var(--wf-activity-score) * 0.015, 1.0)));
}

/* Activity state classes — toggled via JS.  These override the
   intensity-* classes when active (they appear later in the
   stylesheet, so same-specificity rules win when present). */
.root.activity-idle     { --wf-loop-dur: 15s; --wf-glow-a: 0.22; }
.root.activity-active   { --wf-loop-dur: 12s; --wf-glow-a: 0.30; }
.root.activity-hyped    { --wf-loop-dur: 9s;  --wf-glow-a: 0.42; }
.root.activity-overdrive{ --wf-loop-dur: 7s;  --wf-glow-a: 0.52; }
.root.activity-surge    { --wf-loop-dur: 5s;  --wf-glow-a: 0.65; }

/* Surge transient — applied briefly by JS; overrides loop-dur/glow
   for the duration of the surge, then the activity-state class
   resumes. */
.root .surge-active .rail-energy {
  animation: wfSurgePulse 0.6s ease-out forwards;
}
.root .surge-active .corner-pulse {
  animation: wfSurgeCorner 0.6s ease-out forwards;
}
@keyframes wfSurgePulse {
  0%   { opacity: 0.4; transform: scale(0.8); }
  50%  { opacity: 1;  transform: scale(1.2); }
  100% { opacity: 0.4; transform: scale(0.8); }
}
@keyframes wfSurgeCorner {
  0%   { opacity: 0.3; }
  50%  { opacity: 1; }
  100% { opacity: 0.3; }
}

/* Micro-glitch probability modulated by activity score */
.root:not(.glitch-active) .rail-accent,
.root:not(.glitch-active) .corner-bracket {
  transition: filter 0.08s ease;
}
"""

_DOCUMENT_TEMPLATE = """<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>CAM // LINK — Live Webcam Frame</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=VT323&display=swap" rel="stylesheet" />
    <style>__WF_CSS__</style>
  </head>
  <body>
    <div id="root" class="root theme-neon_cyber intensity-medium">
      <div class="wf-glow-ambient"></div>
      <div class="wf-frame">
        <div class="rail rail-top" id="railTop">
          <div class="rail-struct"></div>
          <div class="rail-inner"></div>
          <div class="rail-scan"></div>
          <div class="rail-accent"></div>
          <div class="rail-energy"></div>
          <div class="rail-sweep"></div>
        </div>
        <div class="rail rail-right" id="railRight">
          <div class="rail-struct"></div>
          <div class="rail-inner"></div>
          <div class="rail-scan"></div>
          <div class="rail-accent"></div>
          <div class="rail-energy"></div>
          <div class="rail-sweep"></div>
        </div>
        <div class="rail rail-bottom" id="railBottom">
          <div class="rail-struct"></div>
          <div class="rail-inner"></div>
          <div class="rail-scan"></div>
          <div class="rail-accent"></div>
          <div class="rail-energy"></div>
          <div class="rail-sweep"></div>
        </div>
        <div class="rail rail-left" id="railLeft">
          <div class="rail-struct"></div>
          <div class="rail-inner"></div>
          <div class="rail-scan"></div>
          <div class="rail-accent"></div>
          <div class="rail-energy"></div>
          <div class="rail-sweep"></div>
        </div>

        <div class="corner corner-tl">
          <div class="corner-pulse"></div>
          <div class="corner-bracket"></div>
          <div class="corner-detail corner-node"></div>
        </div>
        <div class="corner corner-tr">
          <div class="corner-pulse"></div>
          <div class="corner-bracket"></div>
          <div class="corner-detail corner-dots"><span></span><span></span></div>
        </div>
        <div class="corner corner-bl">
          <div class="corner-pulse"></div>
          <div class="corner-bracket"></div>
          <div class="corner-detail corner-ticks"><span></span><span></span><span></span></div>
        </div>
        <div class="corner corner-br">
          <div class="corner-pulse"></div>
          <div class="corner-bracket"></div>
          <div class="corner-detail corner-vents"><span></span><span></span><span></span></div>
        </div>

        <div class="hud-status hud-status-left" id="statusLeft">
          <span class="dot"></span><span id="camLabel">CAM // 01</span>
        </div>
        <div class="hud-status hud-status-right" id="statusRight">
          <span id="signalLabel">SIGNAL // ONLINE</span>
        </div>

        <div class="spark" data-spark="0"></div>
        <div class="spark" data-spark="1"></div>
        <div class="spark" data-spark="2"></div>
        <div class="spark" data-spark="3"></div>

        <div class="glitch-frag" id="glitchFrag"></div>
      </div>
      <div class="wf-boot-label" id="bootLabel">SYSTEM ONLINE</div>
    </div>
    <script>
      (function() {
        const STATE = __WF_STATE_JSON__;
        const I18N = __WF_I18N_JSON__;
        const SUBSCRIBE_MSG = __WF_SUBSCRIBE_JSON__;
        __WF_JS__
      })();
    </script>
  </body>
</html>"""

_JS = r"""
let config = STATE.config || {};
let locale = String(STATE.locale || 'uk');
const rootEl = document.getElementById('root');
const camLabelEl = document.getElementById('camLabel');
const signalLabelEl = document.getElementById('signalLabel');
const bootLabelEl = document.getElementById('bootLabel');
const glitchFragEl = document.getElementById('glitchFrag');
const sparkEls = Array.prototype.slice.call(document.querySelectorAll('.spark'));
const reducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

let bootTimers = [];
let glitchInterval = null;
let sparkInterval = null;
let bootStarted = false;
let hasBooted = false;
let isOnline = false;

let activityScore = 0;          // 0-100 from state/patch, drives visual modulation
let currentState = "idle";      // idle | active | hyped | overdrive | surge
let lastEmittedState = "idle"; // hysteresis buffer prevents jittery flapping
const hysteresis = 3;          // activity-score points needed to cross state boundary

function tr(key) {
  const pack = I18N[locale] || I18N.uk || {};
  const v = pack[key];
  if (v === undefined || v === null || v === '') {
    return (I18N.en && I18N.en[key]) || key;
  }
  return v;
}

function clearBootTimers() {
  bootTimers.forEach(function(id) { clearTimeout(id); });
  bootTimers = [];
}

function updateActivityState(score) {
  // Clamp and store the score.
  activityScore = Math.max(0, Math.min(100, Number(score) || 0));

  // Determine the conceptual state from the score.
  let newState;
  if (activityScore <= 20) newState = "idle";
  else if (activityScore <= 45) newState = "active";
  else if (activityScore <= 70) newState = "hyped";
  else if (activityScore <= 90) newState = "overdrive";
  else newState = "surge";

  // Hysteresis: only transition if the score crosses a threshold with buffer.
  const crossed =
    newState !== lastEmittedState &&
    // IDLE -> ACTIVE: score must exceed 20 + hysteresis
    (newState === "active" && activityScore > 20 + hysteresis) ||
    // ACTIVE -> IDLE: score must fall below 20 - hysteresis
    (newState === "idle" && activityScore < 20 - hysteresis) ||
    // ACTIVE -> HYPED: score must exceed 45 + hysteresis
    (newState === "hyped" && activityScore > 45 + hysteresis) ||
    // HYPED -> ACTIVE: score must fall below 45 - hysteresis
    (newState === "active" && activityScore < 45 - hysteresis) ||
    // HYPED -> OVERDRIVE: score must exceed 70 + hysteresis
    (newState === "overdrive" && activityScore > 70 + hysteresis) ||
    // OVERDRIVE -> HYPED: score must fall below 70 - hysteresis
    (newState === "hyped" && activityScore < 70 - hysteresis) ||
    // OVERDRIVE -> SURGE: score must exceed 90 + hysteresis
    (newState === "surge" && activityScore > 90 + hysteresis) ||
    // SURGE -> OVERDRIVE: score must fall below 90 - hysteresis
    (newState === "overdrive" && activityScore < 90 - hysteresis);

  if (!crossed) return;

  // Remove the previous state class and emit the new one.
  rootEl.classList.remove(`activity-${lastEmittedState}`);
  lastEmittedState = newState;
  rootEl.classList.add(`activity-${newState}`);

  // If we just entered SURGE, trigger the transient surge effect.
  if (newState === "surge") {
    triggerSurgeEffect();
  }
}

function applyTheme() {
  const validThemes = ['neon_cyber', 'synthwave', 'toxic', 'ice', 'amber', 'critical'];
  const theme = validThemes.indexOf(config.theme) >= 0 ? config.theme : 'neon_cyber';
  validThemes.forEach(function(t) { rootEl.classList.remove('theme-' + t); });
  rootEl.classList.add('theme-' + theme);

  const validIntensity = ['low', 'medium', 'high'];
  const intensity = validIntensity.indexOf(config.intensity) >= 0 ? config.intensity : 'medium';
  validIntensity.forEach(function(i) { rootEl.classList.remove('intensity-' + i); });
  rootEl.classList.add('intensity-' + intensity);

  const validStyles = ['primary', 'minimal', 'tactical', 'broadcast', 'hologram'];
  const frameStyle = validStyles.indexOf(config.frame_style) >= 0 ? config.frame_style : 'primary';
  validStyles.forEach(function(s) { rootEl.classList.remove('style-' + s); });
  rootEl.classList.add('style-' + frameStyle);

  let scale = Number(config.scale_percent);
  if (!Number.isFinite(scale)) scale = 100;
  scale = Math.max(40, Math.min(250, scale)) / 100;
  rootEl.style.setProperty('--wf-scale', String(scale));

  rootEl.classList.toggle('no-crt', config.enable_crt === false || reducedMotion);
  rootEl.classList.toggle('no-status', config.enable_status_indicator === false);
  rootEl.classList.toggle('no-breathe', config.enable_breathing_glow === false || reducedMotion);
  rootEl.classList.toggle('energy-on', config.enable_energy_flow !== false && !reducedMotion);
  rootEl.classList.toggle('sweep-on', config.enable_light_sweep !== false && !reducedMotion);

  const camLabel = String(config.cam_label || 'CAM // 01').slice(0, 24);
  if (camLabelEl) camLabelEl.textContent = camLabel;
  if (signalLabelEl) signalLabelEl.textContent = tr('status.online');
  if (bootLabelEl) bootLabelEl.textContent = tr('boot.online');
}

function updateResponsiveClasses() {
  const w = rootEl.clientWidth || window.innerWidth || 0;
  rootEl.classList.toggle('narrow-xs', w > 0 && w < 260);
}

function stopMicroEffects() {
  if (glitchInterval) { clearInterval(glitchInterval); glitchInterval = null; }
  if (sparkInterval) { clearInterval(sparkInterval); sparkInterval = null; }
}

function scheduleMicroGlitch() {
  if (glitchInterval) clearInterval(glitchInterval);
  glitchInterval = setInterval(function() {
    if (reducedMotion || !isOnline) return;
    if (config.enable_micro_glitch === false) return;
    const intensity = String(config.intensity || 'medium');
    const chance = intensity === 'high' ? 0.10 : intensity === 'low' ? 0.03 : 0.06;
    if (Math.random() > chance) return;
    triggerMicroGlitch();
  }, 2000);
}

function triggerMicroGlitch() {
  const band = rootEl.querySelector('.rail-top') ? rootEl.getBoundingClientRect() : null;
  if (glitchFragEl && band) {
    const onTop = Math.random() < 0.5;
    const w = Math.max(20, band.width * (0.06 + Math.random() * 0.1));
    const h = 2 + Math.random() * 2;
    glitchFragEl.style.width = w + 'px';
    glitchFragEl.style.height = h + 'px';
    glitchFragEl.style.left = (Math.random() * Math.max(1, band.width - w)) + 'px';
    glitchFragEl.style.top = onTop ? '0px' : (band.height - h) + 'px';
  }
  rootEl.classList.add('glitch-active');
  const dur = 80 + Math.random() * 120;
  setTimeout(function() { rootEl.classList.remove('glitch-active'); }, dur);
}

function triggerSurgeEffect() {
  // Add surge-active class on a transient wrapper; the CSS keyframes
  // will pulse briefly, then the activity-state class resumes.
  rootEl.classList.add('surge-active');
  // Remove surge transient after the animation completes (600ms),
  // then return to the appropriate activity state.
  const surgeTimeout = setTimeout(function() {
    rootEl.classList.remove('surge-active');
    // Re-evaluate state based on the current score so we return
    // to the correct steady state (overdrive / hype / etc.).
    updateActivityState(activityScore);
  }, 600);
}

function scheduleSparks() {
  if (sparkInterval) clearInterval(sparkInterval);
  sparkInterval = setInterval(function() {
    if (reducedMotion || !isOnline) return;
    if (config.enable_sparks === false) return;
    const intensity = String(config.intensity || 'medium');
    const chance = intensity === 'high' ? 0.22 : intensity === 'low' ? 0.06 : 0.13;
    if (Math.random() > chance) return;
    fireSpark();
  }, 3000);
}

function fireSpark() {
  const idle = sparkEls.find(function(el) { return !el.classList.contains('spark-active'); });
  if (!idle) return;
  const corners = [
    { top: '18%', left: '18%', dx: 14, dy: 10 },
    { top: '18%', right: '18%', dx: -14, dy: 10 },
    { bottom: '18%', left: '18%', dx: 14, dy: -10 },
    { bottom: '18%', right: '18%', dx: -14, dy: -10 }
  ];
  const c = corners[Math.floor(Math.random() * corners.length)];
  idle.style.top = c.top || '';
  idle.style.bottom = c.bottom || '';
  idle.style.left = c.left || '';
  idle.style.right = c.right || '';
  idle.style.setProperty('--wf-spark-dx', c.dx + 'px');
  idle.style.setProperty('--wf-spark-dy', c.dy + 'px');
  idle.classList.add('spark-active');
  const onEnd = function() {
    idle.classList.remove('spark-active');
    idle.removeEventListener('animationend', onEnd);
  };
  idle.addEventListener('animationend', onEnd);
}

function handleLikeMicroReaction() {
  // Very small: a tiny pulse on a nearby corner segment.
  // High-frequency likes are aggregated, so this fires once per call.
  const corner = rootEl.querySelector('.corner-tl, .corner-tr, .corner-bl, .corner-br');
  if (!corner) return;
  const seg = corner.querySelector('.corner-pulse');
  if (!seg) return;
  seg.style.opacity = '1';
  seg.style.transition = 'opacity 0.15s ease';
  setTimeout(function() { seg.style.opacity = '0'; }, 120);
}

function handleCommentMicroReaction() {
  // Small signal tick: briefly activate a rail segment.
  const rail = rootEl.querySelector('.rail-top, .rail-right, .rail-bottom, .rail-left');
  if (!rail) return;
  const seg = rail.querySelector('.rail-accent');
  if (!seg) return;
  seg.style.opacity = '0.9';
  setTimeout(function() { seg.style.opacity = ''; }, 80);
}

function handleFollowMicroReaction() {
  // Stronger perimeter pulse: energize one rail section.
  const rail = rootEl.querySelector('.rail-top, .rail-right, .rail-bottom, .rail-left');
  if (!rail) return;
  rail.classList.add('rail-energy');
  setTimeout(function() { rail.classList.remove('rail-energy'); }, 400);
}

function handleShareMicroReaction() {
  // Directional signal: activate a perimeter sweep on one side.
  const dirs = ['top', 'right', 'bottom', 'left'];
  const dir = dirs[Math.floor(Math.random() * dirs.length)];
  const rail = rootEl.querySelector(`.rail-${dir} .rail-sweep`);
  if (!rail) return;
  rail.style.opacity = '0.9';
  rail.style.transition = 'opacity 1.5s ease';
  setTimeout(function() { rail.style.opacity = '0'; }, 1500);
}

function handleGiftMicroReaction() {
  // Strongest normal event: short corner impact + perimeter pulse.
  // Activate all corner pulses briefly.
  const corners = rootEl.querySelectorAll('.corner-pulse');
  corners.forEach(function(c, i) {
    c.style.opacity = '1';
    setTimeout(function() {
      c.style.opacity = '0';
    }, i * 40 + 120);
  });
  // Also briefly brighten the glow.
  const baseGlow = Number(getComputedStyle(rootEl).getPropertyValue('--wf-glow-a')) || 0.36;
  rootEl.style.setProperty('--wf-glow-a', Math.min(1.0, baseGlow + 0.15));
  setTimeout(function() {
    rootEl.style.removeProperty('--wf-glow-a');
  }, 300);
}

function runBootSequence() {
  clearBootTimers();
  if (reducedMotion || config.enable_boot_animation === false) {
    rootEl.classList.remove('booting', 'boot-line', 'boot-rail-right', 'boot-rail-bottom', 'boot-rail-left', 'boot-corners', 'boot-flash', 'boot-label');
    finishBoot();
    return;
  }
  rootEl.classList.add('booting');
  rootEl.classList.remove('online', 'shutting-down', 'hidden');
  const steps = [
    [80,  function() { rootEl.classList.add('boot-line'); }],
    [230, function() { rootEl.classList.add('boot-rail-right'); }],
    [380, function() { rootEl.classList.add('boot-rail-bottom'); }],
    [530, function() { rootEl.classList.add('boot-rail-left'); }],
    [680, function() { rootEl.classList.add('boot-corners'); }],
    [780, function() { rootEl.classList.add('boot-flash'); }],
    [820, function() { rootEl.classList.add('boot-label'); }],
    [1150, function() { finishBoot(); }]
  ];
  steps.forEach(function(step) {
    bootTimers.push(setTimeout(step[1], step[0]));
  });
}

function finishBoot() {
  rootEl.classList.remove('booting', 'boot-line', 'boot-rail-right', 'boot-rail-bottom', 'boot-rail-left', 'boot-flash');
  rootEl.classList.add('boot-corners', 'online');
  isOnline = true;
  hasBooted = true;
  scheduleMicroGlitch();
  scheduleSparks();
}

function runShutdown() {
  clearBootTimers();
  stopMicroEffects();
  isOnline = false;
  rootEl.classList.remove('online', 'boot-label');
  if (reducedMotion || config.enable_shutdown_animation === false) {
    rootEl.classList.add('hidden');
    return;
  }
  rootEl.classList.add('shutting-down');
  bootTimers.push(setTimeout(function() {
    rootEl.classList.add('hidden');
    rootEl.classList.remove('shutting-down', 'booting', 'boot-corners');
  }, 550));
}

function applyState(st) {
  if (!st) return;
  if (st.locale) {
    const next = String(st.locale || '').trim().toLowerCase();
    if (next === 'en' || next === 'uk') locale = next;
  }
  const wasEnabled = config.enabled !== false;
  if (st.config) config = Object.assign(config || {}, st.config);
  applyTheme();

  // Handle activity score from state/patch — this drives the visual modulation.
  if (st.activity_score !== undefined) {
    updateActivityState(st.activity_score);
  }

  if (!bootStarted && nowEnabled) {
    bootStarted = true;
    runBootSequence();
    return;
  }
  if (wasEnabled && !nowEnabled) {
    runShutdown();
    return;
  }
  if (!wasEnabled && nowEnabled && hasBooted) {
    rootEl.classList.remove('hidden');
    runBootSequence();
  }
}

function handleMsg(data) {
  if (!data || !data.op) return;
  if (data.op === 'initial_state') { applyState(data.state || {}); return; }
  if (data.op === 'patch') { applyState(data.patch || {}); }
}

function connect() {
  let tries = 0;
  function doConnect() {
    tries += 1;
    const backoff = Math.min(5000, 250 + Math.floor(Math.random() * 250) + (tries * 350));
    const wsUrl = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws';
    let ws;
    try { ws = new WebSocket(wsUrl); }
    catch (e) { setTimeout(doConnect, backoff); return; }
    ws.onopen = function() { tries = 0; ws.send(JSON.stringify(SUBSCRIBE_MSG)); };
    ws.onmessage = function(ev) {
      try { handleMsg(JSON.parse(ev.data)); } catch (e) {}
    };
    ws.onclose = function() { setTimeout(doConnect, backoff); };
    ws.onerror = function() { try { ws.close(); } catch (e) {} };
  }
  doConnect();
}

applyTheme();
updateResponsiveClasses();
applyState(STATE);
window.addEventListener('resize', updateResponsiveClasses);
if (typeof ResizeObserver !== 'undefined') {
  new ResizeObserver(updateResponsiveClasses).observe(rootEl);
}
connect();
"""
