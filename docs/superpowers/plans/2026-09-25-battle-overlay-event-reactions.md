# Battle Overlay Event Reactions Implementation Plan

**Goal:** Add a premium, event-reactive visual layer to the existing `battle` overlay (HTML/CSS/JS served via `/overlay/by-id/{id}`), so that gifts travel as animated projectiles to participant avatars with coordinated impact reactions, plus lead-change, combo, comeback, final-push, and finish effects — all bounded, performant, and responsive at 1920x480 / 1600x400 / 1280x360.

**Tech stack:** Python 3.11 (overlay server + engine unchanged), inline HTML/CSS/JS (Chromium in OBS browser source), no QML changes, no WebEngine, no per-frame JS, no canvas.

**Existing behavior:** `BattleOverlayType.render_html()` returns an HTML string with inline CSS + an IIFE JS that reads state via WebSocket (`initial_state`/`patch`). Today it has: `.pulse` avatar animation, `.bt-float` score floaters, `.bt-comeback` flash, `.is-final` timer emphasis, static score-bar width transitions (`.4s ease`), gift prompt CTA rotation. It does NOT have: animated gift projectiles, impact effects, score-number interpolation, lead-change flash, combo pulse, CTA reaction to events, or bounded event pooling.

**Locked requirements:**

1. Gift event: create a visual gift object, animate it along a curved path from the event side toward the receiving participant's avatar, on impact: avatar pulses, impact ring glows, score floats, score bar moves, side accent flashes, CTA shows +points/Big gift!. All settle and return to idle.
2. Projectile trajectory: curved (CSS `offset-path: path(...)`), duration 500-900ms (scaled by distance), uses participant `avatar_url` as gift image when available, falls back to an SVG gift shape. Target = actual avatar element bounding box (no hard-coded pixels).
3. Avatar impact: quick scale sequence 1.00 -> 1.12 -> 0.97 -> 1.04 -> 1.00 over ~400ms, accent color intensifies, returns to normal.
4. Impact effect: expanding ring + radial glow + 3 small spark particles, pure CSS keyframes, auto-removed on `animationend`.
5. Score: floating +N rises and fades (500-900ms). Displayed score smoothly interpolates via a short-lived JS interval (16ms, stops when settled; only runs during active animation, never idle).
6. Score bar: smooth fill movement already present; add a brief brightness/glow flash on the leading side after each score change.
7. Side-wide reaction: on gift, the receiving participant's side (avatar, name, score, background) flashes for 300-600ms; opposite side stays calm.
8. Big gift: larger projectile, stronger trail/glow, larger floating score, stronger avatar impact. Thresholds: normalized `diamonds * gift_multiplier >= 50` = BIG, `>= 200` = EPIC.
9. Gift intensity: LOW / MEDIUM / HIGH / EPIC based on normalized points = diamonds * gift_multiplier and multiplier from event payload.
10. Combo: when combo.count changes, pulse the combo pill (scale 1.0 -> 1.15 -> 1.0, 350ms, glow). Do NOT make it permanently large.
11. Combo chain: multiple rapid gifts can overlap; bounded to 8 simultaneous projectiles; low-value score updates coalesce; EPIC gifts always get priority.
12. Lead change: when actual leadership flips (both scores > 0, is-leader-* class changes), show a brief central flash for 1.2s; score bar smoothly crosses center.
13. Close battle: when flags.is_close is true, central glow slightly stronger, score bar fills slightly brighter; no constant animation.
14. Comeback: when flags.is_comeback true, stronger side glow on the coming-back participant, COMEBACK badge (already present), 1.5s total.
15. Final push: when flags.final_push true, timer emphasis, score bar glow stronger, CTA text changes to FINAL PUSH - support your side, event reactions slightly amplified.
16. Round start: when round changes, show ROUND N center badge for 800ms with a scale + fade transition.
17. Round win: when round_wins changes, winner's avatar flashes briefly, round dot updates (already present).
18. Battle finish: when status === finished, all live activity settles, then WINNER screen (already present) with winner avatar large glow + pulse, winner score large emphasis.
19. CTA integration: persistent gift prompt remains; during events, temporarily show +250 / Big gift!; return to normal CTA after 1400ms. Never competes with gift events.
20. Event priority: EPIC > HIGH > MEDIUM > LOW. A COMEBACK or FINAL PUSH suppresses the CTA rotation temporarily.
21. Event queue: Bounded array of active projectiles (max 8). New projectile beyond cap is skipped. No per-frame JS, no requestAnimationFrame, no unbounded timers.
22. Performance: no requestAnimationFrame, no canvas, no WebEngine, no per-frame loops. Idle widget = zero active animations. All DOM effects auto-removed on animationend.
23. Responsive: all positions computed from getBoundingClientRect() of the avatar element relative to the card; no hard-coded pixel values.
24. Tests: structural (HTML contains new anchors) + JS-identifier assertions + no requestAnimationFrame/canvas/WebEngine in JS. No headless-browser screenshot tests required.

**Out of scope:** QML preview widget changes; engine/controller/config changes; new SVG asset files; platform-specific gift name handling; confetti/explosion particles; sound effects; 2v2 layout; decision_layer_enabled.

**Plan path / date:** docs/superpowers/plans/2026-09-25-battle-overlay-event-reactions.md / 2026-09-25.

## Context

The user's request: transform the static battle overlay into a premium event-reactive HUD. The existing battle overlay is a single Python file that returns an HTML string with inline CSS + JS. The BattleEngine (already complete) emits all required event types: gift_received, big_gift, combo_started, combo_updated, combo_broken, comeback, final_push, close_battle, round_started, round_finished, battle_finished, battle_started. The overlay JS already reads state.events via processEvents() and state.flags via render(). No new Python files, no new dependencies.

## Decisions

| # | Decision | Reasoning | What-if-changed |
|---|----------|-----------|-----------------|
| D1 | All changes in render_html() HTML/CSS/JS only | Pipeline is HTML->OBS; engine/controller already emit all events needed; no new Python files reduces risk | If engine changes needed, add payload fields first (separate plan) |
| D2 | Use CSS offset-path: path(...) for curved projectile trajectory | Native Chromium support, no per-frame JS, no canvas; degrades to linear if unsupported | If offset-path unsupported, fallback to transform translate with cubic-bezier |
| D3 | Bounded projectile pool: max 8 simultaneous | Spec requires coalescing, prevents DOM explosion on rapid gift spam | If cap lower, more coalescing; if higher, risk of DOM bloat |
| D4 | Score interpolation via short-lived setInterval (stops when settled) | No requestAnimationFrame; text updates only during active animation; 16ms interval = 60fps ceiling; auto-stops | If requestAnimationFrame allowed, simpler but spec forbids it |
| D5 | CTA suppression during HIGH/EPIC events | Spec priority system; CTA must not compete with real events | If CTA should always rotate, remove suppression |
| D6 | Gift intensity from normalized points = diamonds * gift_multiplier | Uses existing config gift_multiplier; platform-agnostic | If platform-specific thresholds needed, add config field (separate plan) |
| D7 | Impact effect = CSS keyframes on 1 element (ring) + 3 spark divs | Lightweight; no particle engine; auto-removed | If heavy effects needed, use existing particle library if any |
| D8 | Lead-change flash on .btBadge (existing element, z-index 4) | Reuses existing badge; no new DOM; consistent with combo/comeback badge style | If separate badge needed, add .bt-lead-badge |
| D9 | Round-start badge on .btBadge with ROUND N text | Reuses badge; 800ms; no modal | If center scale needed, add .bt-round-badge |
| D10 | Battle-finish winner screen adds glow/pulse to existing .bt-winner-avatar | Reuses existing element; CSS-only; no DOM changes | If confetti needed, separate plan |

## Files To Modify

| Path | Target | What changes | Why | What stays unchanged |
|---|---|---|---|---|
| src/stream_cheremsha/overlays/battle_overlay.py | render_html() return string (HTML + inline CSS + inline JS) | Add: projectile container div, impact-effect container, lead-change badge, round badge; CSS keyframes for projectile flight, impact ring, avatar impact pulse, score pulse, combo pulse, side flash, bar flash; JS: BattleVisualController object, spawnProjectile, spawnImpact, flashSide, flashLeadChange, flashRound, triggerComebackEnhance, triggerFinalPushEnhance, showBattleWinnerEnhance, animateScore, BVC.suppressCTA, BVC.reset, BVC.getIntensity; wire into processEvents() and render() | Adds event-reactive layer without touching engine/controller/config | All existing CSS classes, existing JS functions, initial_state(), render_html signature, existing event handling, existing CSS variables, all existing DOM elements |

## Files To Create

| Path | Responsibility | Interface | Dependencies | Integration point |
|---|---|---|---|---|
| tests/test_battle_overlay_event_reactions.py | Structural + JS-identifier tests for the new event layer | test_html_contains_projectile_layer, test_html_contains_impact_container, test_html_contains_lead_badge, test_js_contains_spawn_projectile, test_js_contains_max_projectiles_cap, test_js_contains_gift_intensity, test_js_no_request_animation_frame, test_js_no_canvas, test_js_no_webengine, test_js_contains_offset_path | BattleOverlayType.render_html | Runs via pytest; no QSettings, no WS, no QML |

## Data / State Changes

New state (all in the JS IIFE, in-memory only, no persistence):

| State | Lives in | Initial value | Trigger to change | Cleanup |
|---|---|---|---|---|
| projectilePool | BVC | [] | spawnProjectile pushes a projectile element; max 8 | On animationend -> remove from DOM + pool |
| MAX_PROJECTILES | JS const | 8 | Never changes | Never changes |
| currentLeader | JS IIFE scope | null | render() computes from tL.score/tR.score; when it flips, flashLeadChange fires | Reset on battle reset |
| ctaSuppressionTimer | BVC + GIFT_STATE | null | suppressCTA sets GIFT_STATE.active = false + setTimeout to restore | Auto-restores after durationMs |
| scoreAnimTimerL/R | BVC | null | When score changes, start setInterval interpolation; stop when settled | Auto-stops when current === target |
| lastRound | JS IIFE scope | null | render() detects round change -> flashRound | Reset on new battle |
| lastRoundWins | JS IIFE scope | null | render() detects change -> flash winner avatar | Reset on new battle |

No Python state changes. No QSettings changes. No new config keys.

## Data / Control Flow

OBS source -> (WebSocket: initial_state / patch) -> BattleOverlayType.render_html() [Python — UNCHANGED except HTML/CSS/JS string] -> (HTML + inline JS loaded) -> Chromium (OBS browser source) -> (parse + execute) -> JS IIFE:

- state = {} (from WS)
- processEvents() [called from render()]
  - for e of state.events:
    - e.type === gift_received | big_gift:
      - BVC.getIntensity() -> intensity
      - spawnProjectile(side, p, intensity)
      - spawnFloat(side, '+' + pts) [existing]
      - flashGift(promptState, p) [existing]
      - animateScore(side, from, to) [new]
    - e.type === combo_started | combo_updated: pulse combo pill
    - e.type === comeback: flashComeback() [existing]; triggerComebackEnhance(side) [new]
    - e.type === final_push: triggerFinalPushEnhance() [new]
    - e.type === round_started: flashRound(round) [new]
    - e.type === round_finished: flash winner avatar
    - e.type === battle_finished: showBattleWinnerEnhance() [new]
- render() [called on each patch]
  - initBVC() [once]
  - update all existing DOM (scores, bar, avatars, timer, etc.)
  - detect lead change -> flashLeadChange() [new]
  - detect round change -> flashRound() [new]
  - detect round_wins change -> flash winner avatar [new]
  - update CTA based on flags (existing)
  - update GiftState suppression (new)

## Edge Cases

| Case | Behavior | Handler | User-visible outcome |
|---|---|---|---|
| gift_received with no diamonds/points | intensity = low; projectile still spawns with default SVG gift; float skipped | p.points ? p.points : (p.diamonds or 0); if 0, skip float | Gift animates; no misleading float |
| More than 8 projectiles in flight | 9th+ skipped | if BVC.projectilePool.length >= MAX_PROJECTILES return in spawnProjectile | Readable; no DOM bloat |
| event_animations: false | All new animations suppressed | if cfg.event_animations === false root.classList.add('anim-off') | Functional; no motion |
| animation_intensity_pct < 100 | Projectile duration scaled up | CSS variable --proj-speed used in duration | Adjustable speed |
| show_avatars: false | Projectiles target score area | if avatar not found, use btScoreL/R as target | Gift visible; targets score |
| show_event_badges: false | No floats, no badges, no projectiles | processEvents guard if cfg.show_event_badges === false | Widget shows only scores/bar |
| Battle resets mid-flight | BVC.reset() clears all projectiles + animations | BVC.reset() removes .gift-projectile and .gift-impact | No orphaned DOM |
| Multiple battle_finished in quick succession | Only last one shows winner | JS guard flag | No flicker |
| Lead change while both scores 0 | No flash | if ls <= 0 and rs <= 0 return | No false positives |
| Combo count increases rapidly | Combo pill pulses each; capped 1 pulse per 350ms | if comboPulseTimer return | No visual spam |

## Error Handling

| Failure | Handling |
|---|---|
| getBoundingClientRect() returns zero | Skip projectile; console.warn in dev |
| offset-path CSS not supported | Projectiles fall back to linear transform transition |
| WS disconnects mid-flight | Projectiles auto-remove on animationend |
| state.events undefined or not array | processEvents guard (existing) |
| state.participants empty | No projectiles spawned |
| Invalid diamonds value | giftIntensity coerces to Number; if NaN, treats as 0 |

## Testing

Test file: tests/test_battle_overlay_event_reactions.py

All tests render the HTML via BattleOverlayType.render_html() and assert on the resulting string. No QML, no WS, no QSettings.

Helper:

```python
def _render(params=None):
    from stream_cheremsha.overlays.battle_overlay import BattleOverlayType
    o = BattleOverlayType()
    html = o.render_html(params or {"instance": "test"})
    import re
    m = re.search(r"<script>(.*?)</script>", html, re.DOTALL)
    script = m.group(1) if m else ""
    return html, script
```

Structural tests:
- test_html_contains_projectile_layer: assert 'btProjectileLayer' in html
- test_html_contains_impact_container: assert 'btImpactLayer' in html
- test_html_contains_lead_badge: assert 'btLeadBadge' in html
- test_html_contains_round_badge: assert 'btRoundBadge' in html

JS identifier tests:
- test_js_contains_spawn_projectile: assert 'spawnProjectile' in script
- test_js_contains_max_projectiles_cap: assert 'MAX_PROJECTILES' in script
- test_js_max_projectiles_is_eight: assert "const MAX_PROJECTILES = 8" in script
- test_js_contains_gift_intensity: assert 'getIntensity' in script
- test_js_contains_flash_lead_change: assert 'flashLeadChange' in script
- test_js_contains_flash_round: assert 'flashRound' in script
- test_js_contains_trigger_comeback_enhance: assert 'triggerComebackEnhance' in script
- test_js_contains_trigger_final_push_enhance: assert 'triggerFinalPushEnhance' in script
- test_js_contains_show_battle_winner_enhance: assert 'showBattleWinnerEnhance' in script
- test_js_no_request_animation_frame: assert 'requestAnimationFrame' not in script
- test_js_no_canvas: assert 'canvas' not in script
- test_js_no_webengine: assert 'WebEngine' not in script
- test_js_contains_offset_path: assert 'offset-path' in script

Regression tests (existing must still pass):
- tests/test_battle_overlay_config.py — all tests
- tests/test_battle_engine.py — all tests
- tests/test_battle_controller.py — all tests
- tests/test_widgets_qml_api_battle_overlay.py — all tests

Run command:

```
python -m pytest tests/test_battle_overlay_event_reactions.py \
  tests/test_battle_overlay_config.py \
  tests/test_battle_engine.py \
  tests/test_battle_controller.py \
  tests/test_widgets_qml_api_battle_overlay.py -v
```

## Configuration / Deployment

No new config keys. No new env vars. No deployment steps. The change is purely in the HTML string returned by render_html().

## Compatibility

- No changes to existing event types, payload shapes, or state schema.
- No changes to initial_state() output shape.
- No changes to battle_overlay_config schema.
- No changes to QML preview.
- Existing CSS classes unchanged; new classes are additive.
- Existing JS functions unchanged; new functions are additive to the IIFE.

## Acceptance Criteria

1. render_html() returns HTML containing `<div id="btProjectileLayer">` and `<div id="btImpactLayer">`.
2. JS contains `const MAX_PROJECTILES = 8` and a function `spawnProjectile`.
3. JS does NOT contain `requestAnimationFrame`, `canvas`, or `WebEngine`.
4. JS contains `offset-path` (for curved projectile path).
5. When `event_animations: false`, the `.anim-off` class is added to `.bt-root` and all new CSS animations are suppressed.
6. When a gift_received event is processed, spawnProjectile is called with the correct side and a positive intensity.
7. When 10 gifts arrive in rapid succession, at most 8 projectiles are in the DOM at any time.
8. When a lead change is detected, flashLeadChange is called and the badge shows LEAD CHANGE for <= 1500ms.
9. When flags.is_comeback is true, the coming-back side gets the `.is-side-flash` class.
10. When flags.final_push is true, the CTA shows FINAL PUSH and the timer has `.is-final` class.
11. When status === finished and state.winner is set, the winner avatar has a glow/pulse animation class.
12. All existing tests pass unchanged.
13. The HTML renders correctly at 1920x480, 1600x400, and 1280x360 (manual verification via OBS).
14. No animation elements leak outside .bt-card.

## Implementation Steps

### Step 1 — Add new CSS keyframes and classes to the style block

**Files:** src/stream_cheremsha/overlays/battle_overlay.py
**Target:** The `<style>` block inside `render_html()`, immediately before the existing `@media (max-width:700px)` block.
**Purpose:** Add all CSS needed for the new event reactions.
**Implementation:**

Insert the following CSS block immediately before the existing `@media (max-width:700px)` block:

```css
/* ====== Event Reactions Layer ====== */
.bt-root.anim-off .gift-projectile,
.bt-root.anim-off .gift-impact,
.bt-root.anim-off .bt-avatar.pulse-enhanced,
.bt-root.anim-off .bt-score.pulse-enhanced,
.bt-root.anim-off .bt-combo.pulse-enhanced,
.bt-root.anim-off .bt-badge,
.bt-root.anim-off .bt-round-badge {
  animation: none !important;
  transition: none !important;
}
.bt-root.anim-off .gift-projectile { display: none !important; }

/* Projectile container: absolute overlay inside the card */
.bt-projectile-layer {
  position:absolute; inset:0; pointer-events:none; z-index:2; overflow:hidden;
}
/* The gift projectile */
.gift-projectile {
  position:absolute; width: calc(4 * var(--bt-f)); height: calc(4 * var(--bt-f));
  border-radius: 50%; display:flex; align-items:center; justify-content:center;
  opacity:0; pointer-events:none; z-index:2;
  filter: drop-shadow(0 0 calc(3 * var(--bt-f)) var(--proj-glow));
}
.gift-projectile .gift-svg {
  width:100%; height:100%; object-fit:cover; display:block;
}
.gift-projectile .gift-fallback-svg {
  width:100%; height:100%;
}
/* Big/EPIC gifts scale up */
.gift-projectile.is-big { width: calc(6 * var(--bt-f)); height: calc(6 * var(--bt-f)); }
.gift-projectile.is-epic {
  width: calc(8 * var(--bt-f)); height: calc(8 * var(--bt-f));
  filter: drop-shadow(0 0 calc(5 * var(--bt-f)) var(--proj-glow)) brightness(1.15);
}

/* Impact effect: expanding ring + glow at impact point */
.gift-impact {
  position:absolute; width: calc(6 * var(--bt-f)); height: calc(6 * var(--bt-f));
  border-radius:50%; pointer-events:none; z-index:3;
  border: calc(2 * var(--bt-f)) solid var(--proj-accent);
  box-shadow: 0 0 calc(6 * var(--bt-f)) var(--proj-accent);
  opacity:0; transform: scale(0.3);
  animation: btImpactRing 0.5s ease-out forwards;
}
.gift-impact.is-epic {
  border-width: calc(2.5 * var(--bt-f));
  box-shadow: 0 0 calc(10 * var(--bt-f)) var(--proj-accent);
  animation: btImpactRingEpic 0.6s ease-out forwards;
}
.gift-impact .spark {
  position:absolute; width: calc(0.8 * var(--bt-f)); height: calc(0.8 * var(--bt-f));
  border-radius:50%; background: var(--proj-accent);
  animation: btSpark 0.45s ease-out forwards;
}

@keyframes btImpactRing {
  0% { transform: scale(0.3); opacity: 1; }
  100% { transform: scale(2.2); opacity: 0; }
}
@keyframes btImpactRingEpic {
  0% { transform: scale(0.3); opacity: 1; }
  50% { transform: scale(1.8); opacity: 0.8; }
  100% { transform: scale(2.5); opacity: 0; }
}
@keyframes btSpark {
  0% { transform: scale(1) translate(0, 0); opacity: 1; }
  100% { transform: scale(0.2) translate(var(--sx), var(--sy)); opacity: 0; }
}

/* Avatar impact pulse */
.bt-avatar.pulse-enhanced {
  animation: btAvatarImpact 0.45s ease-in-out;
}
@keyframes btAvatarImpact {
  0% { transform: scale(1); box-shadow: 0 0 calc(9 * var(--bt-f)) var(--avatar-glow); }
  30% { transform: scale(1.12); box-shadow: 0 0 calc(14 * var(--bt-f)) var(--avatar-glow); }
  55% { transform: scale(0.97); box-shadow: 0 0 calc(9 * var(--bt-f)) var(--avatar-glow); }
  80% { transform: scale(1.04); box-shadow: 0 0 calc(12 * var(--bt-f)) var(--avatar-glow); }
  100% { transform: scale(1); box-shadow: 0 0 calc(9 * var(--bt-f)) var(--avatar-glow); }
}
.bt-avatar--left.pulse-enhanced { --avatar-glow: var(--lt-glow); --proj-accent: var(--lt-primary); }
.bt-avatar--right.pulse-enhanced { --avatar-glow: var(--rt-glow); --proj-accent: var(--rt-primary); }

/* Score pulse */
.bt-score.pulse-enhanced {
  animation: btScorePulse 0.5s ease-out;
}
@keyframes btScorePulse {
  0% { transform: scale(1); filter: brightness(1); }
  40% { transform: scale(1.08); filter: brightness(1.25); }
  100% { transform: scale(1); filter: brightness(1); }
}

/* Side flash */
.bt-side.is-side-flash {
  animation: btSideFlash 0.5s ease-out;
}
@keyframes btSideFlash {
  0% { background: transparent; }
  30% { background: radial-gradient(ellipse at 50% 50%, var(--side-flash-glow) 30%, transparent 70%); }
  100% { background: transparent; }
}
.bt-side--left.is-side-flash { --side-flash-glow: var(--lt-soft); }
.bt-side--right.is-side-flash { --side-flash-glow: var(--rt-soft); }

/* Combo pulse */
.bt-combo.pulse-enhanced {
  animation: btComboPulse 0.35s ease-out;
}
@keyframes btComboPulse {
  0% { transform: translateY(0) scale(1); }
  50% { transform: translateY(0) scale(1.15); }
  100% { transform: translateY(0) scale(1); }
}

/* Lead change flash on center badge */
.bt-badge.bt-lead-change {
  border-color: var(--accent);
  background: rgba(168,85,247,.35);
  color: #fff;
  animation: btLeadFlash 1.2s ease-out forwards;
}
@keyframes btLeadFlash {
  0% { transform: translateX(-50%) scale(0.8); opacity: 0; }
  15% { transform: translateX(-50%) scale(1.05); opacity: 1; }
  70% { transform: translateX(-50%) scale(1.05); opacity: 1; }
  100% { transform: translateX(-50%) scale(0.9); opacity: 0; }
}

/* Round start badge */
.bt-badge.bt-round-badge {
  font-size: calc(2.0 * var(--bt-f));
  letter-spacing: .2em;
  animation: btRoundBadge 0.9s ease-out forwards;
}
@keyframes btRoundBadge {
  0% { transform: translateX(-50%) scale(0.7); opacity: 0; }
  20% { transform: translateX(-50%) scale(1.05); opacity: 1; }
  70% { transform: translateX(-50%) scale(1.05); opacity: 1; }
  100% { transform: translateX(-50%) scale(0.95); opacity: 0; }
}

/* Close battle: stronger central glow */
.is-close .bt-bar-track {
  box-shadow: 0 0 calc(6 * var(--bt-f)) var(--lt-glow), 0 0 calc(6 * var(--bt-f)) var(--rt-glow);
}

/* Final push: stronger bar glow */
.is-final .fill-left, .is-final .fill-right {
  filter: brightness(1.25);
  box-shadow: 0 0 calc(4 * var(--bt-f)) currentColor;
}

/* Winner avatar glow/pulse on finish */
.bt-winner-avatar { animation: btWinnerPulse 2s ease-in-out infinite alternate; }
@keyframes btWinnerPulse {
  0% { box-shadow: 0 0 calc(8 * var(--bt-f)) var(--winner-glow, var(--lt-glow)); }
  100% { box-shadow: 0 0 calc(16 * var(--bt-f)) var(--winner-glow, var(--lt-glow)); }
}
```

**Do:** Insert CSS before `@media (max-width:700px)`. Use existing CSS variables; do NOT introduce new hardcoded colors. All new elements are `position:absolute` or overlay - no layout shift. Add `.anim-off` class rules to suppress all new animations when `event_animations: false`.
**Do NOT:** Change any existing CSS rule (only ADD new rules). Use `position: fixed`. Add any `position: relative` to existing elements. Change the `@media` breakpoint or existing responsive rules.
**Verification:** `grep -c "btAvatarImpact\|btImpactRing\|btScorePulse\|btSideFlash\|btComboPulse\|btLeadFlash\|btRoundBadge\|btWinnerPulse\|anim-off" src/stream_cheremsha/overlays/battle_overlay.py` -> expect 8+ matches.

### Step 2 — Add new DOM anchors to the HTML body

**Files:** src/stream_cheremsha/overlays/battle_overlay.py
**Target:** The `<body>` section of `render_html()`, after the existing `<div class="bt-idle" id="btIdle"></div>` and before the two closing `</div>` tags for `bt-card` and `bt-root` (around line 322-324).
**Purpose:** Add container divs for projectiles, impact effects, lead-change badge, and round badge.
**Implementation:**

After `<div class="bt-idle" id="btIdle"></div>`, insert:

```html
<div class="bt-projectile-layer" id="btProjectileLayer"></div>
<div class="gift-impact-layer" id="btImpactLayer"></div>
<div class="bt-badge bt-lead-change" id="btLeadBadge" style="display:none"></div>
<div class="bt-badge bt-round-badge" id="btRoundBadge" style="display:none"></div>
```

**Do:** Place all 4 new divs INSIDE `<div class="bt-card" id="btCard">`. Use id attributes that are unique. Use `display:none` for the two badge divs to hide initially.
**Do NOT:** Add any new elements outside `.bt-card`. Use `position: fixed`. Change the existing `<body>` structure or close tags.
**Verification:** `grep -c 'btProjectileLayer\|btImpactLayer\|btLeadBadge\|btRoundBadge' src/stream_cheremsha/overlays/battle_overlay.py` -> expect 4 matches.

### Step 3 — Add JS state variables and helper functions

**Files:** src/stream_cheremsha/overlays/battle_overlay.py
**Target:** The JS IIFE, after the existing `let lastSeenAt = 0;` declaration (line ~332) and before `const I18N` (line ~334).
**Purpose:** Initialize new state variables for the event reaction system.
**Implementation:**

After `let lastSeenAt = 0;`, insert:

```js
      /* ====== BattleVisualController — bounded event reaction system ====== */
      const MAX_PROJECTILES = 8;
      const BVC = {
        projectilePool: [],
        impactPool: [],
        currentLeader: null,
        ctaSuppressionTimer: null,
        scoreAnimTimerL: null,
        scoreAnimTimerR: null,
        lastRound: null,
        lastRoundWins: null,
        leadFlashTimer: null,
        roundFlashTimer: null,
        suppressCTA(durationMs) {
          if (!GIFT_STATE.root) return;
          GIFT_STATE.active = false;
          if (BVC.ctaSuppressionTimer) clearTimeout(BVC.ctaSuppressionTimer);
          BVC.ctaSuppressionTimer = setTimeout(() => {
            GIFT_STATE.active = true;
            if (GIFT_STATE.root && GIFT_STATE.msg) {
              cycleGiftMessages();
            }
          }, durationMs);
        },
        reset() {
          const layer = $('btProjectileLayer');
          if (layer) layer.innerHTML = '';
          const impactLayer = $('btImpactLayer');
          if (impactLayer) impactLayer.innerHTML = '';
          BVC.projectilePool.length = 0;
          BVC.impactPool.length = 0;
          if (BVC.leadFlashTimer) { clearTimeout(BVC.leadFlashTimer); BVC.leadFlashTimer = null; }
          if (BVC.roundFlashTimer) { clearTimeout(BVC.roundFlashTimer); BVC.roundFlashTimer = null; }
          if (BVC.ctaSuppressionTimer) { clearTimeout(BVC.ctaSuppressionTimer); BVC.ctaSuppressionTimer = null; }
          if (BVC.scoreAnimTimerL) { clearInterval(BVC.scoreAnimTimerL); BVC.scoreAnimTimerL = null; }
          if (BVC.scoreAnimTimerR) { clearInterval(BVC.scoreAnimTimerR); BVC.scoreAnimTimerR = null; }
        },
        getIntensity(diamonds, multiplier) {
          const dm = Number(diamonds || 0);
          const mult = Number(multiplier || 1) || 1;
          const effective = dm * mult;
          if (effective >= 200) return 'epic';
          if (effective >= 50) return 'big';
          if (effective >= 20) return 'high';
          if (effective >= 5) return 'medium';
          return 'low';
        },
        getSideAccent(side) {
          return side === 'left' ? 'var(--lt-primary)' : 'var(--rt-primary)';
        },
        getSideGlow(side) {
          return side === 'left' ? 'var(--lt-glow)' : 'var(--rt-glow)';
        }
      };

      let bvcInitialized = false;
      function initBVC() {
        if (bvcInitialized) return;
        bvcInitialized = true;
        const root = $('btRoot');
        const cfg = state && state.config;
        if (cfg && cfg.event_animations === false) {
          root.classList.add('anim-off');
        }
        if (root) {
          const intensity = cfg && cfg.animation_intensity_pct ? Number(cfg.animation_intensity_pct) : 100;
          root.style.setProperty('--proj-speed', (100 / intensity * 100).toFixed(1) + '%');
        }
      }
```

**Do:** Place BVC definition before any function that uses it. Place initBVC after BVC definition. Call initBVC() from render(). MAX_PROJECTILES = 8 exactly. All timers are cleared in reset().
**Do NOT:** Use requestAnimationFrame. Use canvas or WebEngine. Create any setTimeout/setInterval without a corresponding clearTimeout/clearInterval. Make BVC a global. Add any console.log.
**Verification:** `grep -n "const MAX_PROJECTILES = 8" src/stream_cheremsha/overlays/battle_overlay.py` -> expect 1 match.

### Step 4 — Add new JS reaction functions

**Files:** src/stream_cheremsha/overlays/battle_overlay.py
**Target:** The JS IIFE, after the existing `function showBadge(text)` and before `function flashComeback()`.
**Purpose:** Add all new event reaction functions.
**Implementation:**

After `function showBadge(text) { ... }` and before `function flashComeback() { ... }`, insert:

```js
      /* ====== Projectile Functions ====== */
      function spawnProjectile(side, payload, intensity) {
        if (BVC.projectilePool.length >= MAX_PROJECTILES) return;
        const layer = $('btProjectileLayer');
        if (!layer) return;

        const avatar = side === 'left' ? $('btAvatarL') : $('btAvatarR');
        if (!avatar) return;
        const avRect = avatar.getBoundingClientRect();
        const card = $('btCard');
        if (!card) return;
        const cardRect = card.getBoundingClientRect();

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
        if (intensity === 'big') el.classList.add('is-big');
        if (intensity === 'epic') el.classList.add('is-epic');
        el.style.left = relSx + 'px';
        el.style.top = relSy + 'px';
        el.style.setProperty('--proj-glow', BVC.getSideGlow(side));
        el.style.setProperty('--proj-accent', BVC.getSideAccent(side));

        const participant = side === 'left'
          ? (state && state.participants && state.participants.find(p => p.team_id === 'left'))
          : (state && state.participants && state.participants.find(p => p.team_id === 'right'));
        if (participant && participant.avatar_url) {
          const img = document.createElement('img');
          img.className = 'gift-svg';
          img.src = participant.avatar_url;
          img.alt = '';
          el.appendChild(img);
        } else {
          const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
          svg.className = 'gift-fallback-svg';
          svg.setAttribute('viewBox', '0 0 24 24');
          svg.innerHTML = '<path d="M7.5 6.2H16.5M13 6.2V23M12 7.5V6.2M9 8H15M9 11H15M9 14H15M9 17H15M9 20H15" stroke="currentColor" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color:var(--proj-accent)"/>';
          el.appendChild(svg);
        }

        const duration = 500 + (intensity === 'big' ? 100 : intensity === 'epic' ? 200 : 0);
        el.style.opacity = '0';

        el.style.transitionProperty = 'opacity';
        el.style.transitionDuration = '0s';
        el.style.offsetPath = 'path("' + pathD + '")';
        el.style.offsetDistance = '0%';

        void el.offsetWidth;
        el.style.opacity = '1';
        el.style.transitionDuration = duration + 'ms';
        el.style.transitionEasing = 'cubic-bezier(0.34, 1.56, 0.64, 1)';
        el.style.offsetDistance = '100%';

        const proj = { el: el, side: side, intensity: intensity };
        BVC.projectilePool.push(proj);

        let completed = false;
        const cleanup = () => {
          if (completed) return;
          completed = true;
          BVC.projectilePool = BVC.projectilePool.filter(p => p !== proj);
          if (el.parentNode) el.parentNode.removeChild(el);
        };
        el.addEventListener('transitionend', cleanup);
        setTimeout(cleanup, duration + 200);

        spawnImpact(relTx, relTy, side, intensity);
        flashSide(side);
      }

      function spawnImpact(x, y, side, intensity) {
        const layer = $('btImpactLayer');
        if (!layer) return;
        const cardRect = $('btCard').getBoundingClientRect();
        const el = document.createElement('div');
        el.className = 'gift-impact';
        if (intensity === 'epic') el.classList.add('is-epic');
        el.style.left = x + 'px';
        el.style.top = y + 'px';
        el.style.setProperty('--proj-accent', BVC.getSideAccent(side));
        layer.appendChild(el);
        BVC.impactPool.push(el);
        el.addEventListener('animationend', () => {
          BVC.impactPool = BVC.impactPool.filter(p => p !== el);
          if (el.parentNode) el.parentNode.removeChild(el);
        });
        for (let i = 0; i < 3; i++) {
          const spark = document.createElement('span');
          spark.className = 'spark';
          spark.style.left = '50%';
          spark.style.top = '50%';
          const angle = (i * 120) + 45;
          const dist = 20 + Math.random() * 15;
          spark.style.setProperty('--sx', (Math.cos(angle * Math.PI / 180) * dist) + 'px');
          spark.style.setProperty('--sy', (Math.sin(angle * Math.PI / 180) * dist) + 'px');
          el.appendChild(spark);
        }
      }

      function flashSide(side) {
        const sideEl = side === 'left' ? $('btLeft') : $('btRight');
        if (!sideEl) return;
        sideEl.classList.remove('is-side-flash');
        void sideEl.offsetWidth;
        sideEl.classList.add('is-side-flash');
      }

      /* ====== Lead Change ====== */
      function flashLeadChange(newLeader) {
        if (BVC.leadFlashTimer) return;
        const badge = $('btLeadBadge');
        if (!badge) return;
        badge.textContent = newLeader === 'left' ? 'LEFT LEAD' : 'RIGHT LEAD';
        badge.classList.remove('show');
        void badge.offsetWidth;
        badge.classList.add('show');
        BVC.leadFlashTimer = setTimeout(() => {
          badge.classList.remove('show');
          badge.classList.remove('bt-lead-change');
          BVC.leadFlashTimer = null;
        }, 1200);
      }

      /* ====== Round Start ====== */
      function flashRound(round, bestOf) {
        const badge = $('btRoundBadge');
        if (!badge) return;
        badge.textContent = 'ROUND ' + round + ' · BO' + bestOf;
        badge.classList.remove('show');
        void badge.offsetWidth;
        badge.classList.add('show');
        BVC.roundFlashTimer = setTimeout(() => {
          badge.classList.remove('show');
          badge.classList.remove('bt-round-badge');
          BVC.roundFlashTimer = null;
        }, 900);
      }

      /* ====== Comeback Enhancement ====== */
      function triggerComebackEnhance(side) {
        flashSide(side);
        const avatar = side === 'left' ? $('btAvatarL') : $('btAvatarR');
        if (avatar) {
          avatar.classList.remove('pulse-enhanced');
          void avatar.offsetWidth;
          avatar.classList.add('pulse-enhanced');
        }
        BVC.suppressCTA(2000);
      }

      /* ====== Final Push Enhancement ====== */
      function triggerFinalPushEnhance() {
        BVC.suppressCTA(3000);
        flashSide('left');
        flashSide('right');
      }

      /* ====== Battle Winner Enhancement ====== */
      function showBattleWinnerEnhance() {
        const winnerAv = $('btWinner') && $('btWinner').querySelector('.bt-winner-avatar');
        if (winnerAv) {
          winnerAv.classList.add('winner-pulse');
          setTimeout(() => winnerAv.classList.remove('winner-pulse'), 2000);
        }
        const winner = state && state.winner;
        if (winner) {
          const side = winner.team_id === 'left' ? 'left' : 'right';
          flashSide(side);
        }
        BVC.suppressCTA(4000);
      }

      /* ====== Score Interpolation ====== */
      function animateScore(elementId, from, to) {
        const el = $(elementId);
        if (!el) return;
        if (from === to) {
          el.textContent = to;
          el.classList.remove('pulse-enhanced');
          void el.offsetWidth;
          el.classList.add('pulse-enhanced');
          return;
        }
        if (elementId === 'btScoreL' && BVC.scoreAnimTimerL) { clearInterval(BVC.scoreAnimTimerL); }
        if (elementId === 'btScoreR' && BVC.scoreAnimTimerR) { clearInterval(BVC.scoreAnimTimerR); }
        let current = from;
        const step = 1;
        const timer = setInterval(() => {
          current += step;
          if (current >= to) {
            current = to;
            clearInterval(timer);
            if (elementId === 'btScoreL') BVC.scoreAnimTimerL = null;
            if (elementId === 'btScoreR') BVC.scoreAnimTimerR = null;
          }
          el.textContent = current;
        }, 16);
        if (elementId === 'btScoreL') BVC.scoreAnimTimerL = timer;
        if (elementId === 'btScoreR') BVC.scoreAnimTimerR = timer;
      }

      /* ====== Combo Pulse ====== */
      function pulseCombo(side, count) {
        const comboEl = side === 'left' ? $('btComboL') : $('btComboR');
        if (!comboEl) return;
        comboEl.classList.remove('pulse-enhanced');
        void comboEl.offsetWidth;
        comboEl.classList.add('pulse-enhanced');
      }
```

**Do:** Use `getBoundingClientRect()` for all positions (no hard-coded pixels). Use `offset-path` for curved trajectory. Cap projectiles at `MAX_PROJECTILES` (8). All elements auto-removed on `animationend`/`transitionend`. `BVC.reset()` clears ALL timers and DOM.
**Do NOT:** Use `requestAnimationFrame`. Use `canvas`. Use any `position: fixed`. Create more than 3 sparks per impact. Add any `console.log` (only `console.warn`).
**Verification:**
- `grep -n "function spawnProjectile" src/stream_cheremsha/overlays/battle_overlay.py` -> expect 1 match
- `grep -n "function spawnImpact" src/stream_cheremsha/overlays/battle_overlay.py` -> expect 1 match
- `grep -n "function flashLeadChange" src/stream_cheremsha/overlays/battle_overlay.py` -> expect 2+ matches
- `grep -n "function flashRound" src/stream_cheremsha/overlays/battle_overlay.py` -> expect 1 match
- `grep -n "function triggerComebackEnhance" src/stream_cheremsha/overlays/battle_overlay.py` -> expect 1 match
- `grep -n "function triggerFinalPushEnhance" src/stream_cheremsha/overlays/battle_overlay.py` -> expect 1 match
- `grep -n "function showBattleWinnerEnhance" src/stream_cheremsha/overlays/battle_overlay.py` -> expect 1 match
- `grep -n "function animateScore" src/stream_cheremsha/overlays/battle_overlay.py` -> expect 1 match
- `grep -n "function pulseCombo" src/stream_cheremsha/overlays/battle_overlay.py` -> expect 1 match

### Step 5 — Wire new functions into processEvents() and render()

**Files:** src/stream_cheremsha/overlays/battle_overlay.py
**Target:** The `processEvents()` function (lines ~529-544) and `render()` function (lines ~553-693).
**Purpose:** Call the new event reaction functions when the corresponding events arrive.
**Implementation:**

**A. Replace the existing processEvents() function (lines 529-544) with:**

```js
      function processEvents() {
        if (!state || !Array.isArray(state.events)) return;
        for (const e of state.events) {
          if (!(e && e.type)) continue;
          const at = Number(e.at) || 0;
          if (at <= lastSeenAt + 0.0001) continue;
          lastSeenAt = Math.max(lastSeenAt, at);
          const p = e.payload || {};

          if (e.type === 'gift_received' || e.type === 'big_gift') {
            const pts = p.points ? p.points : (p.diamonds || 0);
            const intensity = BVC.getIntensity(p.diamonds || p.points || 0, p.multiplier || 1);
            spawnProjectile(e.team_id, p, intensity);
            spawnFloat(e.team_id, '+' + pts);
            flashGift(promptState, p);
            const team = state.teams && state.teams.find(t => t.id === e.team_id) || {score: 0};
            const to = team.score || 0;
            const from = lastDelta[e.team_id] || 0;
            if (from !== to) {
              animateScore(e.team_id === 'left' ? 'btScoreL' : 'btScoreR', from, to);
              lastDelta[e.team_id] = to;
            }
          } else if (e.type === 'combo_started' || e.type === 'combo_updated') {
            const side = (p.team_id) || (state.combo && state.combo.team_id) || 'left';
            const count = p.count || (state.combo && state.combo.count) || 1;
            pulseCombo(side, count);
          } else if (e.type === 'comeback') {
            flashComeback();
            const side = p.team_id || 'left';
            triggerComebackEnhance(side);
          } else if (e.type === 'final_push') {
            triggerFinalPushEnhance();
          } else if (e.type === 'round_started') {
            const round = p.round || (state.round || 1);
            const bestOf = p.best_of || (state.best_of || 3);
            flashRound(round, bestOf);
          } else if (e.type === 'round_finished') {
            const winnerTeam = p.winner_team || 'left';
            const winnerAv = winnerTeam === 'left' ? $('btAvatarL') : $('btAvatarR');
            if (winnerAv) {
              winnerAv.classList.remove('pulse-enhanced');
              void winnerAv.offsetWidth;
              winnerAv.classList.add('pulse-enhanced');
            }
          } else if (e.type === 'battle_finished') {
            showBattleWinnerEnhance();
          }
        }
      }
```

**B. In render(), add lead-change detection and round tracking AFTER the existing score bar update section.**

Find in `render()` the block that ends with:

```js
        const barTrack = document.getElementById('btBar');
        if (barTrack) {
          barTrack.classList.toggle('is-zero', ls === 0 && rs === 0);
        }
```

Immediately after that block, insert:

```js
        /* Detect lead change */
        const newLeader = ls > rs ? 'left' : (rs > ls ? 'right' : null);
        if (newLeader && newLeader !== BVC.currentLeader && ls > 0 && rs > 0) {
          flashLeadChange(newLeader);
        }
        BVC.currentLeader = newLeader;

        /* Detect round change */
        const currentRound = state.round || 1;
        if (BVC.lastRound !== null && BVC.lastRound !== currentRound) {
          flashRound(currentRound, state.best_of || 3);
        }
        BVC.lastRound = currentRound;

        /* Detect round_wins change */
        const currentRoundWins = {
          left: (state.round_wins && state.round_wins.left) || (tL.round_wins || 0),
          right: (state.round_wins && state.round_wins.right) || (tR.round_wins || 0)
        };
        if (BVC.lastRoundWins) {
          const prevL = BVC.lastRoundWins.left;
          const prevR = BVC.lastRoundWins.right;
          if (currentRoundWins.left !== prevL || currentRoundWins.right !== prevR) {
            if (currentRoundWins.left > prevL) {
              const avL = $('btAvatarL');
              if (avL) {
                avL.classList.remove('pulse-enhanced');
                void avL.offsetWidth;
                avL.classList.add('pulse-enhanced');
              }
            } else if (currentRoundWins.right > prevR) {
              const avR = $('btAvatarR');
              if (avR) {
                avR.classList.remove('pulse-enhanced');
                void avR.offsetWidth;
                avR.classList.add('pulse-enhanced');
              }
            }
          }
        }
        BVC.lastRoundWins = currentRoundWins;
```

**C. In render(), add initBVC() call at the very beginning of the function.**

Find the first line of `render()`:

```js
      function render() {{
        if (!state) return;
```

Replace with:

```js
      function render() {{
        if (!state) return;
        if (!bvcInitialized) initBVC();
```

**D. In handleMsg(), add BVC.reset() call on initial_state.**

Find in `handleMsg()`:

```js
          state = {{}};
          lastSeenAt = 0;
          applyPatch(obj.state);
          render();
```

Replace with:

```js
          state = {{}};
          lastSeenAt = 0;
          if (!bvcInitialized) initBVC();
          BVC.reset();
          applyPatch(obj.state);
          render();
```

**Do:** Add lead-change detection AFTER existing score bar updates (so we have final scores). Call initBVC() exactly once (guard with bvcInitialized). Call BVC.reset() on initial_state. Do NOT change existing behavior of flashGift, spawnFloat, flashComeback. Keep the existing showBadge logic unchanged. Keep the existing processEvents guard.
**Do NOT:** Remove any existing event handling. Change the order of existing events in processEvents. Add any console.log. Change lastDelta semantics. Remove the existing processEvents guard.
**Verification:**
- `grep -n "flashLeadChange" src/stream_cheremsha/overlays/battle_overlay.py` -> expect 2+ matches (definition + call)
- `grep -n "initBVC" src/stream_cheremsha/overlays/battle_overlay.py` -> expect 3+ matches (definition, call in render, call in handleMsg)
- `grep -n "BVC.reset" src/stream_cheremsha/overlays/battle_overlay.py` -> expect 1 match
- `grep -n "bvcInitialized" src/stream_cheremsha/overlays/battle_overlay.py` -> expect 4+ matches

### Step 6 — Write tests

**Files:** tests/test_battle_overlay_event_reactions.py
**Target:** New test file.
**Purpose:** Verify the new event reaction layer is present in the HTML/JS.
**Implementation:**

Create the following test file:

```python
"""Tests for the ``battle`` overlay event reaction layer.

Verifies that the rendered HTML contains the new DOM anchors and that the
inline JS contains all required functions and does NOT use forbidden
techniques (requestAnimationFrame, canvas, WebEngine).
"""

from __future__ import annotations

import re

from stream_cheremsha.overlays.battle_overlay import BattleOverlayType


def _render(params=None):
    """Render the battle overlay and return (html, script_body)."""
    o = BattleOverlayType()
    html = o.render_html(params or {"instance": "test"})
    m = re.search(r"<script>(.*?)</script>", html, re.DOTALL)
    script = m.group(1) if m else ""
    return html, script


def test_html_contains_projectile_layer() -> None:
    html, _ = _render()
    assert "btProjectileLayer" in html


def test_html_contains_impact_container() -> None:
    html, _ = _render()
    assert "btImpactLayer" in html


def test_html_contains_lead_badge() -> None:
    html, _ = _render()
    assert "btLeadBadge" in html


def test_html_contains_round_badge() -> None:
    html, _ = _render()
    assert "btRoundBadge" in html


def test_js_contains_spawn_projectile() -> None:
    _, script = _render()
    assert "spawnProjectile" in script


def test_js_contains_max_projectiles_cap() -> None:
    _, script = _render()
    assert "MAX_PROJECTILES" in script


def test_js_max_projectiles_is_eight() -> None:
    _, script = _render()
    assert "const MAX_PROJECTILES = 8" in script


def test_js_contains_get_intensity() -> None:
    _, script = _render()
    assert "getIntensity" in script


def test_js_contains_flash_lead_change() -> None:
    _, script = _render()
    assert "flashLeadChange" in script


def test_js_contains_flash_round() -> None:
    _, script = _render()
    assert "flashRound" in script


def test_js_contains_trigger_comeback_enhance() -> None:
    _, script = _render()
    assert "triggerComebackEnhance" in script


def test_js_contains_trigger_final_push_enhance() -> None:
    _, script = _render()
    assert "triggerFinalPushEnhance" in script


def test_js_contains_show_battle_winner_enhance() -> None:
    _, script = _render()
    assert "showBattleWinnerEnhance" in script


def test_js_no_request_animation_frame() -> None:
    _, script = _render()
    assert "requestAnimationFrame" not in script


def test_js_no_canvas() -> None:
    _, script = _render()
    assert "canvas" not in script


def test_js_no_webengine() -> None:
    _, script = _render()
    assert "WebEngine" not in script


def test_js_contains_offset_path() -> None:
    _, script = _render()
    assert "offset-path" in script
```

**Do:** Create the test file exactly as specified. All tests are structural — no QML, no WS, no QSettings.
**Do NOT:** Add any tests that require a running application, headless browser, or external dependencies. Do NOT use QSettings.
**Verification:** `python -m pytest tests/test_battle_overlay_event_reactions.py -v` -> expect 18 passed.
