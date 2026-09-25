# Gift Rush Widget — Design Spec

**Date:** 2026-09-26
**Status:** Approved (approach + decisions D1–D5 confirmed by user on 2026-09-26)
**Source spec:** user request "Implement a new Cheremsha widget: GIFT RUSH" (42-section visual/behavior spec in conversation, sections §1–§42)

---

## 1. Goal

Add a `gift_rush` overlay widget to Cheremsha. When a viewer sends a gift, the overlay produces a highly visible, **transparent**, physical, premium VFX reaction: the gift flies in on a curved, eased path, compresses for a 50–100 ms micro-pause, **impacts**, and bursts into coins (gravity), ribbons, sparks, expanding rings, a `+VALUE` popup, and a `COMBO xN` counter. Rapid consecutive gifts overlap and escalate (x1 → x2 → x3 → x5 → x10 → x20+ = epic). The stream stays visible behind the effect — no dark dashboard panel.

Visual language: **live sports broadcast + premium arcade + streamer event VFX** — physical mass, momentum, celebration. **Explicitly NOT:** cyberpunk, sci-fi energy cores, holograms, portals, neon circuits, white full-screen flashes, casino slot graphics, generic particle spam, emoji graphics.

---

## 2. Scope

### In scope (v1)

- New widget type **`gift_rush`** via the standard 5-step overlay integration (config file, controller, overlay type, registry, `widget_instances.py` metadata, `main_window.py` wiring + fan-out, editor preview).
- Config: `gift_rush_overlay_config.py` with clamped dataclass schema (theme, scale, target mode, per-effect toggles, combo window, max simultaneous events, reduced effects mode).
- Gift event wiring: `main_window.py` fan-out block (`_on_tiktok_gift`, lines ~7410–7470) gains `self._gift_rush_group.on_gift(...)`.
- VFX engine (inline HTML/CSS/JS in `render_html()`):
  - Gift projectile: curved `offset-path` flight, 450–900 ms, eased (no linear), spawn scale/opacity/rotation in.
  - Micro-pause: 50–100 ms compression at impact point before burst.
  - Impact: expanding ring + radial glow.
  - Coin burst: inline-SVG coins rotate, fly outward with gravity, fall, fade; counts 4–8 / 8–14 / 14–24 by intensity tier.
  - Ribbon/streamer burst: 3–5 ribbons per medium+, arc + drift + fade.
  - Spark burst: small star glyphs, fast, die quickly.
  - Score/value popup: `+N` (and `xN` quantity when `count > 1`), scale-in + rise + glow + fade, 500–900 ms.
  - Combo counter: `COMBO xN` shown when combo > 1, scale 0.8 → 1.1 → 1.0, opacity in/out, 700–1200 ms.
  - Intensity labels: `BIG GIFT` (HIGH), `EPIC` (EPIC) as a short emphasis badge near impact.
  - Target modes: `center` (default), `left`, `right`, `random` — normalized coordinates, computed from element bounds (no hardcoded pixels).
  - Subtle camera micro-impact: **EPIC only**, container scale 1.00 → 1.01 → 1.00 (or 1–2 px offset shake), never for normal gifts.
  - Multiple overlapping gifts: active visual events capped at 8–12; excess low-value events aggregated; never unbounded DOM.
  - Reduced effects mode: fewer particles, no camera impact, shorter durations.
  - Three themes: `cheremsha` (cyan/pink/purple), `celebration` (gold/white/magenta), `arcade` (saturated, punchier).
  - Gift image from event (`icon_url`) is the hero visual when present and valid; inline-SVG Cheremsha gift fallback otherwise. Never emoji.
  - Platform-agnostic controller payload (`platform` field, no hardcoded TikTok gift names).
  - Transparent root (`background: transparent`); VFX elements only.
- Tests: `tests/test_gift_rush_config.py`, `tests/test_gift_rush_controller.py`, `tests/test_gift_rush_overlay.py` following the `test_battle_overlay_event_reactions.py` structural + JS-identifier pattern.

### Out of scope (v1)

- Multi-platform gift fan-out: v1 wires only into the **existing TikTok fan-out** (same as battle). The controller payload is platform-agnostic; other platforms are a follow-up when their fan-out exists.
- Live battle-participant targeting: gift_rush works standalone. Battle wiring (gift → left/right participant) is a separate follow-up plan.
- Sound effects.
- External asset files: all glyphs are inline SVG inside the overlay HTML (self-contained, no remote dependency beyond the event-provided gift image, which is existing platform behavior).
- 2v2 layout, casino graphics, new domain models.

---

## 3. Architecture

Reuses the standard `OverlayType` + controller + pubsub pattern (battle, stream_goal, king_of_live).

```
TikTokSource (GiftEvent)  [other platforms: follow-up]
        │
        ▼
main_window.py _on_tiktok_gift fan-out
   sender, gift_name, gift_id, count, tiktok_coin_each,
   icon_url, sender_avatar_url, sender_user_key, platform
        │
        ▼  self._gift_rush_group.on_gift(...)
GiftRushController  (InstanceControllerGroup "gift_rush")
   - normalize payload → event dict {type:"gift", at, payload}
   - global combo window (config, default 10 s)
   - intensity: LOW/MEDIUM/HIGH/EPIC from value + combo
   - aggregation of rapid identical low-value gifts (visual only)
   - capped event list, debounced publish (200 ms)
        │
        ▼  pubsub.publish_sync("overlay:gift_rush:{instance}", state)
state = {config, locale, events:[...]}
        │
        ▼
GiftRushOverlayType.render_html() → inline HTML/CSS/JS (transparent root)
   - <div id="grRoot">  (opacity 0.99 transparent)
   - <div id="grLayer">  projectile / rings / coins / ribbons / sparks / popups
   - <script> GiftRushVFX IIFE: processEvents(), pools, CSS custom props +
     keyframes, animationend cleanup, lastSeenAt dedup
        │
        ▼
Chromium (OBS browser source / editor preview URL)
```

**Files:**

| File | Created/Modified | Responsibility |
|------|-----------------|----------------|
| `overlays/gift_rush_config.py` | create | `GiftRushOverlayConfig` dataclass, schema v1, clamped defaults, to/from JSON, `load_`/`save_`, `_DEFAULTS_LOADERS` target `gift_rush_overlay_config_defaults`/`_to_json_text` |
| `overlays/gift_rush_controller.py` | create | `GiftRushController` (QObject, `set_pubsub`, `set_event_loop`, `start`, `stop`, `reload_config`, `schedule_publish`, `initial_state`, `on_gift`) |
| `overlays/gift_rush_overlay.py` | create | `GiftRushOverlayType`: `type = "gift_rush"`, `render_html(params)`, `initial_state(params)` |
| `registry.py` | modify | `self.register(GiftRushOverlayType())` |
| `widget_instances.py` | modify | `WIDGET_TYPES["gift_rush"]` meta (name, description, icon `🎁`, `icon_svg`, accent, platforms `["tiktok"]`) + `_DEFAULTS_LOADERS["gift_rush"]` |
| `ui/main_window.py` | modify | `_gift_rush_group = InstanceControllerGroup("gift_rush", _make_gift_rush_controller)` + `sync_instances(start=False)` + fan-out call + `reset_for_new_stream` fan-out |
| `ui/widgets_qml_api.py` | modify | `set_gift_rush_controller`, config load/save, preview (mirroring existing widgets) |
| `tests/test_gift_rush_config.py` | create | defaults, round-trip, clamping, invalid JSON fallback |
| `tests/test_gift_rush_controller.py` | create | on_gift → state events, combo window, intensity, aggregation, publish, reduced mode |
| `tests/test_gift_rush_overlay.py` | create | structural HTML + JS identifiers, pool caps, no rAF/canvas/WebEngine, transparent root, theme variables |

---

## 4. Data & event contract

### 4.1 Controller `on_gift` signature (mirrors battle's group fan-out kwargs)

```python
def on_gift(
    self,
    sender: str = "",
    gift_name: str = "",
    gift_id: str = "",
    count: int = 1,
    tiktok_coin_each: int = 0,
    icon_url: str = "",
    sender_avatar_url: str = "",
    sender_user_key: str = "",
    platform: str = "tiktok",
) -> None
```

Derived, **computed in controller only, never persisted or authoritative**:

- `c = max(1, int(count))`; `each = max(0, int(coin_each or 0))`
- `value = each * c if each else c` (mirrors battle's `coins = c * each if each > 0 else c`)
- If `value <= 0` and `gift_name` is set → still emit (visual-only, value 0 → LOW intensity, no score float)
- `combo = current global combo count` (window = cfg.combo_window_s, default 10 s; reset when gap > window)
- `intensity` from §6.2
- `aggregated_count` = number of gifts in this aggregation batch (1 if standalone)

### 4.2 Emitted state (published to `overlay:gift_rush:{instance}`)

```json
{
  "config": { ...GiftRushOverlayConfig public dict... },
  "locale": "uk",
  "events": [
    {
      "type": "gift",
      "at": 1758900000.123,          // time.time(); JS dedup key
      "payload": {
        "sender": "name",
        "gift_name": "Rose",
        "gift_id": "gift-123",
        "count": 3,
        "aggregated_count": 3,
        "value": 75,
        "icon_url": "https://.../rose.png",
        "sender_avatar_url": "https://...",
        "platform": "tiktok",
        "combo": 4,
        "intensity": "MEDIUM",
        "target": "center"
      }
    }
  ]
}
```

- Controller keeps `self._events: list[dict]`, capped at **32** (drops oldest) — safe because JS dedupes on `at`.
- `schedule_publish()` debounces 200 ms (matches `_PUBLISH_DEBOUNCE_MS` convention); `initial_state()` = fresh state with empty `events`.
- JS mirrors battle: `processEvents()` per patch, `lastSeenAt` pointer, `at <= lastSeenAt + 1e-4 → skip`.

### 4.3 Reset behavior

`reset_for_new_stream()` (fan-out on stream change) → clear `_events`, reset combo, publish. `reload_config()` → re-read config, publish.

---

## 5. Components

### 5.1 `GiftRushOverlayConfig` (schema v1)

| Field | Type | Default | Range/allowed |
|-------|------|---------|---------------|
| `schema_version` | int | 1 | — |
| `theme` | str | `cheremsha` | {cheremsha, celebration, arcade} |
| `target_mode` | str | `center` | {center, left, right, random} |
| `scale_percent` | int | 100 | 40–250 |
| `intensity_percent` | int | 100 | 25–200 (overall burst scale) |
| `event_animations` | bool | true | — |
| `show_gift_image` | bool | true | — |
| `show_value` | bool | true | — |
| `show_sender` | bool | true | — |
| `show_combo` | bool | true | — |
| `show_intensity_badge` | bool | true | — |
| `effects_coins` | bool | true | — |
| `effects_ribbons` | bool | true | — |
| `effects_sparks` | bool | true | — |
| `effects_impact_ring` | bool | true | — |
| `camera_impact` | bool | true | EPIC only; forced off in reduced mode |
| `combo_enabled` | bool | true | — |
| `combo_window_s` | int | 10 | 3–30 |
| `combo_escalation` | bool | true | x1→x20 tiering on/off |
| `max_simultaneous_events` | int | 10 | 4–12 |
| `reduced_effects` | bool | false | — |

Clamped in `_ensure_*` helpers; invalid JSON → defaults. Public dict via `to_json_text` (sorted, compact, same as battle config).

### 5.2 `GiftRushController`

- Constructor: `(pubsub, get_locale, instance)` → QObject, stores debounced publish handle, combo window state (`self._gift_timestamps: list[float]` — kept small, O(n) filter over window).
- `on_gift(...)`:
  1. Skip if `cfg.event_animations == false` (widget still publishes nothing — idle).
  2. Now = `time.time()`; `self._gift_timestamps = [t for t in self._gift_timestamps if t > now - window]`; append now; `combo = len(self._gift_timestamps)`.
  3. Aggregation: if same `gift_id` + same `sender_user_key` arrived within the last 2 s and `intensity in {LOW}` → increment `aggregated_count` on the pending last event (if exists in `_events` and `at` within 2 s) instead of a new event; skip if pending batch already EPIC. Preserve the original `sender`/`value` accumulation.
  4. Emit event dict (§4.2). Cap `_events` at 32.
  5. `schedule_publish()`.
- **Active-event cap (JS enforces the visual side)**: `max_simultaneous_events` is read by JS and gates spawn; Python event list is capped separately. Both bounded → no unbounded DOM.
- `initial_state()` → `{"config": public_dict, "locale": locale, "events": []}`.
- `stop()` → cancel publish handle.

### 5.3 `GiftRushOverlayType`

- `render_html(params)` returns full `<!doctype html>` doc, **`html,body {margin:0;padding:0;background:transparent;pointer-events:none;}`** and `#grRoot { background: transparent; overflow: hidden; }`.
- Inline CSS: theme variables per `--theme-*` class set by JS from `config.theme`:

```css
/* root always transparent */
html, body { margin:0; padding:0; background:transparent; }
#grRoot { position:relative; width:100vw; height:100vh; overflow:hidden; background:transparent; pointer-events:none; }
/* theme: cheremsha */
.gr-theme-cheremsha { --gr-acc1:#22d3ee; --gr-acc2:#ec4899; --gr-acc3:#a78bfa; --gr-glow:#22d3eecc; --gr-coin:#facc15; --gr-ribbon:#ec4899; }
.gr-theme-celebration { --gr-acc1:#fde68a; --gr-acc2:#fbbff5; --gr-acc3:#ffffff; --gr-glow:#fde68acc; --gr-coin:#fbbf24; --gr-ribbon:#f472b6; }
.gr-theme-arcade { --gr-acc1:#4ade80; --gr-acc2:#60a5fa; --gr-acc3:#facc15; --gr-glow:#4ade8acc; --gr-coin:#facc15; --gr-ribbon:#4ade80; }
```

- Layers (all `position:absolute; inset:0; pointer-events:none`): `#grRoot` → `#grCam` (camera micro-impact wrapper) → `#grLayer` (projectiles) + `#grBurst` (rings/coins/ribbons/sparks) + `#grPopup` (score/combo badges, `z-index` on top).
- Inline SVG glyphs (gift, coin, spark, ribbon) — small `viewBox="0 0 24 24"` paths, defined once in a `<style>`/`<defs>` or inlined per element; colors from CSS variables so themes apply.
- JS IIFE `GiftRushVFX`:
  - `init()`: bind DOM, read `state.config`, apply theme class, size vars.
  - `processEvents()`: dedup, dispatch to `spawnGift(e.payload)`.
  - `spawnGift(p)`: respects `config` toggles + active-event count (`grVfx.activeEvents` counter, decremented on `finish`); if over `max_simultaneous_events` and intensity LOW → aggregate/skip.
  - **Flight**: create `.gr-projectile` at source (bottom-left/bottom-right/random-bottom by target mode, 5–15 % random jitter), set CSS custom properties `--proj-x0/--proj-y0/--proj-x1/--proj-y1`, `duration`, `ease`. Use `offset-path: path(...)` curved path (battle-proven), fallback to transform transition if unsupported. Spawn 150–250 ms fade/scale in.
  - **Micro-pause**: at path end, gift holds 50–100 ms with `scale(0.9)` compression (`--pause-ms` custom prop read by a short CSS keyframe on `.is-impacting`) before burst.
  - **Impact**: remove projectile, spawn at `(x1,y1)`: 1–2 expanding rings (`.gr-ring`, `scale` + fade, 600–900 ms), radial glow flash (600 ms), then intensity-tiered particles (§5.4).
  - **Coins** (`p.count`-scaled count 4–8/8–14/14–24 by tier, reduced mode /2): each coin gets random angle θ (±90° from horizontal bias), speed v (tier-scaled), gravity g, `--cx/--cy/--cz` (z for depth 0.6–1.4 scale). CSS keyframe `grCoinFly` uses `translate(calc(...))` from custom props: outward arc + downward fall + rotate (flip 0→720°) + fade. 700–1400 ms.
  - **Ribbons** (tier MEDIUM+; 3–6): long thin rounded rects with `border-radius`, random hue from theme, `--rx/--ry` arc + drift + rotate + fade. 900–1800 ms.
  - **Sparks** (all tiers; 8–24): tiny 4-point star SVG, fast radial out + shrink + fade, 300–700 ms.
  - **Score popup** (if `show_value`): `.gr-value` = `+N` (N = `value`) + optional `xCount` when `count > 1` and `show_sender`? no — sender is separate. Scale-in (0.6→1.1→1) + rise (−40 px) + glow + fade, 500–900 ms, positioned above impact.
  - **Sender line** (if `show_sender`): small `.gr-sender` "from `sender`" under value, 500–900 ms.
  - **Combo counter** (if `combo_enabled` and `combo > 1` and `show_combo`): `.gr-combo` = `COMBO xN` near impact, scale 0.8→1.1→1, opacity 0→1→0, 700–1200 ms; stronger emphasis (larger, brighter) at x10+.
  - **Intensity badge** (if `show_intensity_badge`): HIGH → `BIG GIFT`, EPIC → `EPIC`, short pulse 800 ms at impact.
  - **Camera micro-impact** (if `camera_impact` and intensity EPIC): `.gr-cam` scale 1.00 → 1.01 → 1.00 over ~120 ms (subtle). Never for normal gifts.
  - **Cleanup**: every spawned node has an `animationend` listener → remove from DOM + decrement `grVfx.activeEvents`. Timeout safety-net (2× duration) to guard against missed events.
  - **Reduced mode**: `config.reduced_effects` halves particle counts, disables camera impact, shortens durations 30%.
  - **No**: `requestAnimationFrame`, `canvas`, `WebEngine`, per-frame JS, unbounded timers, `setInterval` loops. All motion is CSS.

---

## 6. Visual system

### 6.1 Physics feel (per element, different motion characteristics — §22)

| Element | Motion | Duration |
|---------|--------|----------|
| Gift projectile | Curved `offset-path`, ease-in-out, 450–900 ms scaled by distance + intensity | 450–900 ms |
| Micro-pause | `scale(0.92)` compression + slight rotation | 50–100 ms |
| Impact ring | `scale(0.3 → 2.2)`, opacity 1→0, ease-out | 600–900 ms |
| Coins | Radial out + gravity fall + 720° flip + fade | 700–1400 ms |
| Ribbons | Arc out + drift + rotate + fade | 900–1800 ms |
| Sparks | Fast radial, shrink, fade | 300–700 ms |
| Score popup | Scale 0.6→1.1→1 + rise + glow + fade | 500–900 ms |
| Combo counter | Scale 0.8→1.1→1 + opacity in/out | 700–1200 ms |
| Camera micro-impact | Scale 1.00→1.01→1.00 (EPIC only) | ~120 ms |

### 6.2 Intensity tiers (normalized, no hardcoded gift names — §20, §21)

| Intensity | Conditions (value = normalized diamonds*multiplier) | Visual |
|-----------|---------------------------------------------------|--------|
| LOW | `value < 10` and `combo < 3` | Small impact: ring + 4–8 coins + 6–10 sparks |
| MEDIUM | `10 ≤ value < 50` or `combo ≥ 3` | Bigger: ring + 8–14 coins + ribbons(3–5) + 12–16 sparks + value popup |
| HIGH | `50 ≤ value < 200` or `combo ≥ 5` | Strong: double ring + 14–24 coins + ribbons(4–6) + 16–24 sparks + `BIG GIFT` badge + stronger value |
| EPIC | `value ≥ 200` or `combo ≥ 10` | Large: multi-ring + max coins + ribbons(5–8) + max sparks + `EPIC` badge + camera micro-impact + longer flight (dramatic arc) + stronger combo emphasis |

Combo ≥ 20 always at least EPIC visual weight.

### 6.3 Target modes (normalized — §25)

Impact point `(x,y)` in `[0,1]`:
- `center`: `x = 0.5`, `y = 0.45`
- `left`: `x = 0.2`, `y = 0.45`
- `right`: `x = 0.8`, `y = 0.45`
- `random`: `x = 0.35 + random()*0.3`, `y = 0.4 + random()*0.15`

Source: bottom-left (x=0.12,y=0.88) / bottom-right (x=0.88,y=0.88) chosen opposite to target. All computed from element bounds where possible; constants are normalized ratios, not pixels (responsive at 1920x480 / 1600x400 / 1280x360).

---

## 7. Performance & invariants (§32, §33, §22)

- **Idle**: zero active animations, zero timers, `grVfx.activeEvents == 0`. No `requestAnimationFrame`, no `setInterval`, no canvas, no WebEngine, no continuous shaders.
- **Bounded pools** (JS counters, hard caps):
  - Projectiles ≤ 12
  - Coins per burst ≤ 24 (tier), total on-screen ≤ 32
  - Sparks per burst ≤ 24, total on-screen ≤ 48
  - Ribbons per burst ≤ 8, total on-screen ≤ 24
  - Active simultaneous visual events ≤ 12 (`max_simultaneous_events` config, default 10, range 4–12)
- **Cleanup**: `animationend` removes every node; 2×-duration safety-net `setTimeout` per event (bounded, self-cancelling on finish).
- **Throttle**: pubsub publish debounced 200 ms.
- **DOM size**: at peak, total live nodes ≤ ~120; verified by test counting.

---

## 8. Integration (5-step + fan-out)

1. `gift_rush_config.py` created (config dataclass + defaults + JSON).
2. `registry.py`: `self.register(GiftRushOverlayType())`.
3. `widget_instances.py`:
   ```python
   "gift_rush": {
       "name": "Gift Rush",
       "description": "Живі реакції на подарунки: кошині, стрічки, іскри.",
       "icon": "🎁",
       "icon_svg": "icons/gift.svg",
       "accent": "#f472b6",
       "platforms": ["tiktok"],
   }
   ```
   `_DEFAULTS_LOADERS["gift_rush"] = "stream_cheremsha.overlays.gift_rush_config:gift_rush_overlay_config_defaults:gift_rush_overlay_config_to_json_text"`
4. `main_window.py`:
   - `self._gift_rush_group = InstanceControllerGroup("gift_rush", _make_gift_rush_controller)` + `sync_instances(start=False)` (near battle group, ~line 1242).
   - Fan-out in `_on_tiktok_gift`: `self._gift_rush_group.on_gift(sender=..., gift_name=..., gift_id=..., count=..., tiktok_coin_each=..., icon_url=..., sender_avatar_url=..., sender_user_key=..., platform=ChatPlatform.TIKTOK.value)` (wrapped in try/except like battle).
   - `reset_for_new_stream` fan-out block includes `_gift_rush_group.reset_for_new_stream()`.
   - `widgets_qml_api.py`: `set_gift_rush_group(...)`, config load/save/preview methods (mirrors `set_battle_controller` + battle preview).
5. Editor: widget type appears in create list; settings form renders config fields; preview opens `/overlay/by-id/{id}` in external browser (existing architecture, no WebEngine).

---

## 9. Testing strategy (mirrors `test_battle_overlay_event_reactions.py`)

**`test_gift_rush_config.py`**
- `test_defaults` — every field present with documented default.
- `test_json_round_trip` — `from_json_text(to_json_text(cfg)) == cfg`.
- `test_clamping` — out-of-range values clamp to documented bounds.
- `test_invalid_json` — malformed → defaults, no raise.
- `test_theme_allowed` — unknown theme → `cheremsha`.

**`test_gift_rush_controller.py`**
- `test_on_gift_emits_event` — payload fields present, `at` increasing.
- `test_combo_window` — gifts within window increment combo; gap resets.
- `test_intensity_tiers` — value/combo matrix yields LOW/MEDIUM/HIGH/EPIC.
- `test_aggregation` — rapid identical LOW gifts → single event with `aggregated_count`.
- `test_event_cap` — 40 rapid gifts → `len(events) <= 32`.
- `test_reduced_effects_in_config` — flag round-trips.
- `test_reset` — `reset_for_new_stream` clears events + combo.
- `test_publish_debounce` — publish called (stub pubsub), debounced.

**`test_gift_rush_overlay.py`** (render HTML, assert substrings / regex)
- `test_html_transparent_root` — `background:transparent` present, no opaque panel class.
- `test_html_contains_layers` — `grRoot`, `grLayer`, `grBurst`, `grPopup` ids.
- `test_js_no_rAF` — `'requestAnimationFrame' not in script`.
- `test_js_no_canvas` — `'canvas' not in script`.
- `test_js_no_webengine` — `'WebEngine' not in script`.
- `test_js_contains_offset_path` — `'offset-path' in script`.
- `test_js_pool_caps` — `MAX_PROJECTILES`, `MAX_COINS`, `MAX_SPARKS`, `MAX_RIBBONS` constants present with expected values.
- `test_js_active_event_cap` — `max_simultaneous_events` read from config.
- `test_theme_variables` — all three theme variable blocks present.
- `test_integrity` — `render_html` returns valid HTML (starts with `<!doctype`), no unbalanced tags (basic).

**Run:** `PYTHONPATH=. .venv/bin/pytest tests/test_gift_rush_config.py tests/test_gift_rush_controller.py tests/test_gift_rush_overlay.py -v`
**Regression:** existing overlay tests pass unchanged.

---

## 10. Acceptance criteria

1. `WIDGET_TYPES` contains `gift_rush`; editor lists it; creating an instance saves a UUID + settings; `/overlay/by-id/{id}` serves the transparent VFX page.
2. A single `gift_received` → gift flies in (curved, eased, 450–900 ms), micro-pause, impact ring, coins/sparks burst, `+N` rises, fades, then idle (no lingering DOM nodes).
3. 10 rapid gifts → overlapping bursts, `COMBO xN` counter visible, `max_simultaneous_events` respected (no DOM explosion), low-value gifts aggregate.
4. EPIC gift → multi-ring, camera micro-impact (subtle), `EPIC` badge, larger flight.
5. `reduced_effects: true` → visibly fewer particles, no camera impact.
6. Each theme applies distinct colors via CSS variables.
7. Target modes center/left/right/random place impact correctly; no clipping at 1920x480 / 1600x400 / 1280x360.
8. No `requestAnimationFrame` / `canvas` / `WebEngine` in overlay JS.
9. All existing tests pass unchanged.
10. No new remote asset dependencies; gift image only from event payload, SVG fallback always available.

---

## 11. Key decisions (confirmed)

| ID | Decision | Status |
|----|----------|--------|
| D1 | Platform scope v1 = TikTok only (existing fan-out); controller payload platform-agnostic | ✅ Confirmed |
| D2 | JS engine = CSS custom properties + keyframes; JS parameterizes once, cleans up on `animationend`; no rAF/canvas/WebEngine | ✅ Confirmed |
| D3 | Assets = inline SVG in HTML string (self-contained); event `icon_url` used when present/valid; SVG gift fallback | ✅ Confirmed |
| D4 | Battle integration = standalone now; `target_mode` config; live participant targeting is follow-up | ✅ Confirmed |
| D5 | Aggregation = visual-only; authoritative score untouched | ✅ Confirmed |
| D6 | Combo = **global** gift streak within `combo_window_s` (default 10 s), not per-gifter (v1). Per-gifter combo is a possible follow-up. | Assumed — flag if wrong |
| D7 | `show_sender` default = **true** (small "from `sender`" line under value); disableable. | Assumed — flag if wrong |
| D8 | `random` target mode included (spec lists it); impact X in central band, Y slight random. | Assumed — flag if wrong |
| D9 | Intensity thresholds: LOW <10 / MEDIUM <50 / HIGH <200 / EPIC ≥200 (normalized value), OR combo ≥3/≥5/≥10/≥20 respectively — whichever is higher. | Assumed — flag if wrong |

---

## 12. Risks & mitigations

| Risk | Mitigation |
|------|-----------|
| `offset-path` unsupported in older Chromium → projectiles fall back to linear | Fallback transform-transition branch in JS (`try` + feature check) — battle-proven. |
| Remote `icon_url` fails to load | `<img onerror>` → swap to inline SVG gift; no blank hole. |
| Rapid gift spam floods DOM | Hard JS caps + `animationend` cleanup + safety-net timeout; `max_simultaneous_events` config. |
| `time.time()` monotonic drift between publish/JS | JS dedup uses `at` pointer; controller `at = time.time()`; 200 ms debounce absorbs. |
| Theme variables not applied on config change | JS `render()` re-applies theme class on every patch (battle pattern). |
| Editor preview shows blank (no real gifts) | `render_html` includes a hidden "demo" toggle for preview only (optional, behind `config.preview_demo`); otherwise preview shows idle transparent state + static sample impact via a `preview` param. |
