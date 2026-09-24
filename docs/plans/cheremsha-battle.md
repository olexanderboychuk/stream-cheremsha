# Cheremsha Battle Implementation Plan

**Goal:** Add a reusable platform-independent Battle Engine + Cheremsha-native `battle` overlay widget (1v1 now, 2v2-compatible data model) integrated into the existing widget/overlay/QML architecture.
**Tech stack:** Python 3.11, PySide6 6.11 (QObject/QSettings), qasync/asyncio, aiohttp overlay server, QML (WidgetsView + UniversalWidgetEditor), QSettings persistence.
**Existing behavior:** `battle_royale` is a singleton HP-duel (gift-ID-matched heal/crit, `overlay:battle_royale:*` broadcast, singleton QSettings `overlays/battle_royale/main/config_json`); `king_of_live` is a singleton SQLite-driven king display; `live_leaderboard_simple` is the canonical per-instance pattern (`InstanceControllerGroup` + per-instance topics `overlay:{type}:{instance_id}`). No `battle` type exists today.
**Locked requirements:**
1. New widget `type_id=battle` creatable via Create Widget → Battle, with own UUID/settings, served at `/overlay/by-id/{id}`, real-time WS updates, no WebEngine, no polling, no per-frame JS.
2. Participants = (C) first 2 distinct TikTok gifters meeting threshold in window auto-lock left/right slots; slot owners' subsequent gifts score; non-participant gifts during ACTIVE are ignored for scoring (documented, overturnable).
3. Scoring v1 = (A) TikTok gifts only: `points = int(diamonds_total * gift_multiplier)` when `gifts_enabled`; likes/follows have config + engine methods but are disabled by default and NOT wired in `MainWindow` v1 (interface-ready for later platforms).
4. Lifecycle = (B) multi-round best-of-N + auto-start on threshold; countdown → active → round finished → next round or battle finished → auto-reset to IDLE (in-memory live state, config persisted).
5. Deterministic engine owns scoring/combo/comeback/close/final-push; overlay only reacts to normalized state/events.
6. One `Battle` widget + data-driven `theme` (`cheremsha_neon|cyber|arcade|minimal`); responsive 1920x480 → 1024x300, never hide a participant, no `width:0`/`visible:false` layout hacks.
7. Decision/Jev/Laya layer is an optional disabled-by-default hook; never required, never called per score update unless enabled.
8. Backward compatible: no changes to `battle_royale`, `king_of_live`, existing instances/URLs/settings; additive migration only.
9. Performance: reuse existing 1s tick timer, 200ms publish debounce, lazy aiohttp intact, no new always-running worker, no QML page-count increase, event-driven CSS only.
**Out of scope:** Twitch/YouTube/Kick scoring wiring (engine interface only); spectator-to-team support gifts; manual participant editor; 2v2/FFA UI (data model only); new SVG assets; AI auto-decisions; battle history SQLite; win-reward/VIP hooks; layout-canvas changes; TTS/pipeline changes.
**Plan path / date:** `docs/plans/cheremsha-battle.md` / 2026-09-24.

## Context

User request, quoted verbatim (truncated to the binding scope): "You are implementing a new production-quality streaming widget for Stream Cheremsha. FEATURE NAME: Cheremsha Battle ... Build a reusable, data-driven Battle Widget + Battle Engine ... separated from presentation: Battle Engine ↓ normalized battle state/events ↓ Battle Widget UI ... persistent configuration ... real-time updates ... widget URL ... browser-source compatible ... existing Cheremsha widget architecture ... backwards-compatible ... [plus §§2–30: performance, engine, events, scoring, combo, comeback, final push, optional AI layer, visual states, themes, responsive, integration, URL, editor, icons, safety, tests, order, acceptance]".

Reference image is visual inspiration only — original Cheremsha styling, no clone. User interview answers locked: (1C) auto top-2 gifters; (2A) TikTok-only v1; (3B) multi-round best-of-N + auto-start.

## Decisions

| # | Decision | Reasoning | What-if-changed |
|---|----------|-----------|-----------------|
| D1 | New `type_id=battle`, new `src/stream_cheremsha/battle/` engine; do NOT generalize `battle_royale/` | `battle_royale` is HP/crit/support-gift duel singleton; Battle is score-race best-of-N per-instance. Merging would break existing behavior and singleton assumptions | If merged, `battle_royale` tests/behavior change; plan steps 1–5 collapse into a risky refactor |
| D2 | During ACTIVE only slot owners score; spectator gifts ignored for scoring | Deterministic 1v1 with locked slots; no team-join UX in v1. Engine `team_id` field keeps 2v2/spectator-support possible later | If spectator-support wanted, add `support_mode: off\|slot_owner\|team_vote` config + `on_gift` team-resolution step; overlay unchanged |
| D3 | Per-instance controllers via `InstanceControllerGroup("battle", factory)` (like leaderboard), NOT singleton (unlike BattleRoyale) | Requirement: each Battle instance has own UUID/settings and isolated state/topics. Singleton would stomp instances | If singleton, steps 5/8 simplify but per-instance settings isolation fails; must revert to `overlay:battle:*` broadcast |
| D4 | Reuse existing 1s `_battle_tick_timer` in `MainWindow` to drive both royale + battle group; no new QTimer | Performance acceptance: no new always-running worker. 1s granularity matches royale + battle timer display | If sub-second timer wanted, add per-group `QTimer(500ms)` started only while any member is non-idle; steps 8/12 change |
| D5 | Scoring `points = int(diamonds_total * gift_multiplier)` counting ALL gifts from slot owners (no catalog match) | Battle is a score race (like `top_gifters`), not royale gift-ID-matched heal. Simpler, matches "top-2 gifters" semantics | If catalog-matched wanted, import `actions/tiktok_gifts.TIKTOK_GIFTS` + `fighter_index_for_gift` analog; engine step 2 changes |
| D6 | Combo multiplier applies to gifts arriving WHILE combo active; defaults threshold 5 events / 5s / x2, 10 events / x3, max x3 | Reward bursts without retroactive rescoring; deterministic and testable | If retroactive, engine must rewrite `score` history; tests + snapshot change |
| D7 | Comeback = was trailing by ≥20% (leader score ≥50 noise floor) then overtake or gap ≤10%; one-shot per lead change. Final push = remaining ≤10s AND gap ≤15% AND both ≥20pts, once per round | Event-driven, threshold-configurable, no AI. Noise floors prevent 2-vs-1 false positives | If thresholds change, only config defaults + 2 engine constants change |
| D8 | Live battle state is in-memory only; restart resets to IDLE. Only config + widget instances persist | Matches royale/leaderboard runtime behavior; avoids corrupt-state migration. "Persistent battle state where appropriate" = config + round config, not live scores | If live persistence wanted, add SQLite `battle_sessions` table + load/save in controller; new migration step required |
| D9 | Single overlay file with CSS-variable themes; reuse `icons/web_swords.svg` with accent `#a855f7` (royale keeps `#ef4444`) | No new asset/packaging change (`pyproject` `assets/*` untouched); visual distinction via accent + theme vars | If new icon wanted, add `assets/icons/web_versus.svg` + packaging check + QML `iconName` change |
| D10 | AI hook = injected `decision_hook(event_dict) -> dict` in controller, default `None`, config `decision_layer_enabled=False`. Engine never imports AI | Core works without AI; no per-update LLM calls; hook point satisfies §9/§10 without dependency | If enabled by default, add `battle/decision.py:HeuristicDecisionLayer` call in step 5 + tests |
| D11 | `hide_when_idle` default `False` for battle (royale defaults `True`) | New widget should show an IDLE card so creators see it works pre-battle; royale hides to reduce clutter for an established widget | If `True`, overlay initial render hides root; one config default + test expectation change |

## Files To Modify

| Path | Target (class/fn) | What changes | Why | What stays unchanged |
|------|-------------------|--------------|-----|----------------------|
| `src/stream_cheremsha/overlays/registry.py` | import + `OverlayRegistry.__init__` | Add `from ...battle_overlay import BattleOverlayType` and `self.register(BattleOverlayType())` after `BattleRoyaleOverlayType` line | Expose `battle` renderer via existing registry; generic `server.py` routes pick it up with zero server change | All 19 existing registrations, `_DebugOverlayType`, `_json_for_script`, `get/registered_types` logic |
| `src/stream_cheremsha/overlays/widget_instances.py` | `WIDGET_TYPES`, `_DEFAULTS_LOADERS` | Add `"battle"` meta entry + `"battle": "stream_cheremsha.overlays.battle_overlay_config:battle_overlay_config_defaults:battle_overlay_config_to_json_text"` loader entry | Creation wizard/gallery/persistence/defaults flow works through existing CRUD; `SCHEMA_VERSION` untouched | Every other type entry, `WidgetInstance` CRUD, `merged_settings/resolve_ws_params/typed_config_for_type`, backup-key logic |
| `src/stream_cheremsha/ui/main_window.py` | imports, `__init__` group setup (~L1170–1212), `_on_battle_tick/_schedule_battle_overlay_publish` (~L6625–6665), `_on_tiktok_gift` fan-out (~L7375–7415), `reset_for_new_stream` (~L6933–6941) | Init `InstanceControllerGroup("battle", factory)` with `instance_config_loader`; extend 1s tick to drive battle group; fan out gifts to battle group; reset group on new stream | Wire engine into existing event/timer/lifecycle without new threads/timers | `BattleRoyaleController` singleton, all other groups, royale publish topics/timers, points/SQLite logic |
| `src/stream_cheremsha/ui/widgets_qml_api.py` | `previewLayoutWidget`, `previewBattleOverlay` (new), `load/saveBattleOverlayConfigMap/Json` (new), `_save_cfg_to_instance` reload list, `set_battle_controller` (new setter) | Dispatch `battle` previews to instance topic; instance-aware load/save mirroring royale wrappers; include battle group in reload list | Editor + preview work for instances through established patterns | All existing per-type preview/copy/URL methods, `widgetInstanceUrl` (generic, untouched), `previewBattleRoyaleOverlay` |
| `src/stream_cheremsha/qml/WidgetsView.qml` | `layoutWidgetTypes`, `defaultWidgetSize`, `widgetMode` comment (L613), `universalSchema`, `universalConfig`, `selectPreviewSpec` | Add `battle` entries/branches; `battle → {kind:"battle"}` reuses existing `WidgetBattlePreview` + `pvBattle` | Gallery, layout canvas, editor schema, and card previews cover the new type | All other type branches, `WidgetBattlePreview` component itself, editor shell, navigation/caching |
| `src/stream_cheremsha/l10n.py` | `widgets.type.battle.*` + `widgets.battle.*` dict entries | Add ~2 type keys + ~28 editor keys (uk+en) next to `battle_royale` block | Localized gallery + editor labels via existing `tr()` | All existing keys, dict style, fallback behavior |
| `src/stream_cheremsha/overlays/server.py` | — (no change) | No edit; verified generic `/overlay/by-id/{id}` + `/ws` already serve any registered type | Avoid high-blast-radius server change | Entire file |

## Files To Create

| Path | Responsibility | Interface | Dependencies | Integration point |
|------|---------------|-----------|--------------|-------------------|
| `src/stream_cheremsha/battle/__init__.py` | Package marker + re-exports | `from stream_cheremsha.battle.models import …; from stream_cheremsha.battle.engine import BattleEngine` | none | imported by controller/tests |
| `src/stream_cheremsha/battle/models.py` | Platform-independent data model (1v1 now, 2v2-ready) | `BattleStatus(StrEnum: idle/countdown/active/finished)`, `Participant dataclass(id,name,avatar_url,team_id,score)`, `Team(id,score,round_wins)`, `BattleEvent(type,team_id,payload,at)`, `BattleState(battle_id,status,round,best_of,participants,teams,combo,events,winner,deadlines; to_dict())`, `ComboState(team_id,count,multiplier,window_start)` | stdlib only | engine + controller + tests |
| `src/stream_cheremsha/battle/engine.py` | Deterministic battle logic, no Qt, no I/O, injectable clock | `BattleEngine(cfg_provider)`: `reset()`, `on_gift(*,user_key,display,avatar_url,diamonds,now)->list[dict]`, `on_like/on_follow(...)->list[dict]` (disabled-path, interface-ready), `tick(now)->list[dict]`, `snapshot()->dict`, `start_manual(participants,cfg)->bool` | `battle.models`, config object (duck-typed fields) | owned by `overlays/battle_controller.py` |
| `src/stream_cheremsha/battle/decision.py` | Optional decision-layer hook point, disabled default | `BattleDecision(is_big_moment,is_close,is_comeback,should_special)->dict`, `NullDecisionLayer.decide(event)->BattleDecision` (all False), `HEURISTIC_KIND = "heuristic_v1"` | none | controller calls only if `decision_layer_enabled` |
| `src/stream_cheremsha/overlays/battle_overlay_config.py` | Per-instance config + validation + QSettings singleton fallback (mirrors royale config module) | `BATTLE_THEMES=frozenset({cheremsha_neon,cyber,arcade,minimal})`, `BattleOverlayConfig` frozen dataclass (fields in Step 4), `battle_overlay_config_defaults/to_json_text/from_json_text/load_/save_`, `battle_overlay_config_to_public_dict` | `PySide6.QtCore.QSettings`, stdlib json | `widget_instances._DEFAULTS_LOADERS`, `instance_config_loader`, overlay `initial_state` |
| `src/stream_cheremsha/overlays/battle_controller.py` | Per-instance QObject bridging engine ↔ pubsub (mirrors `live_leaderboard_controller.py`) | `BattleController(QObject)`: `OVERLAY_TYPE="battle"`, `__init__(*,pubsub,get_locale,instance,parent,config_loader)`, `start/stop/reload_config/initial_state/on_gift/reset_for_new_stream/schedule_publish/tick_advance/set_pubsub/set_event_loop`, `_build_state()->dict`, `_publish_patch_sync()` → `overlay:battle:{instance}` | `battle.engine`, `battle_overlay_config`, `overlays.pubsub` | `InstanceControllerGroup("battle", factory)` in `main_window.py` |
| `src/stream_cheremsha/overlays/battle_overlay.py` | Inline HTML/CSS/JS browser-source renderer (mirrors `battle_royale_overlay.py` structure) | `BattleOverlayType`: `type="battle"`, `render_html(params)->str`, `initial_state(params)->dict` | `battle_overlay_config`, `overlays.models.normalize_instance_id`, `ui_locale.load_ui_locale` | `registry.py` registration; served by generic `server.py` |
| `tests/test_battle_engine.py` | Engine unit tests (no Qt, no QSettings) | 14 test fns (see Testing) | `battle.engine`, `battle.models` | `pytest tests/test_battle_engine.py -q` |
| `tests/test_battle_overlay_config.py` | Config defaults/round-trip/clamp tests | 6 test fns | `overlays.battle_overlay_config` | `pytest tests/test_battle_overlay_config.py -q` |
| `tests/test_battle_controller.py` | Per-instance isolation + publish + reset tests | 5 test fns (uses `OverlayPubSub`, no `MainWindow`) | `overlays.battle_controller`, `overlays.pubsub` | `pytest tests/test_battle_controller.py -q` |
| `tests/test_widgets_qml_api_battle_overlay.py` | QML API wiring: preview topic, load/save round-trip | 4 test fns (mirrors `test_widgets_qml_api_battle_royale_overlay.py`) | `ui.widgets_qml_api`, `overlays.pubsub` | `pytest tests/test_widgets_qml_api_battle_overlay.py -q` |

## Data / State Changes

- New persisted state (QSettings, existing systems only):
  - Widget instances: existing `overlays/widget_instances/config_json` gains `{"type_id":"battle",…,"settings":{BattleOverlayConfig JSON}}` rows. No schema bump (`SCHEMA_VERSION=1` unchanged, additive key). Cleanup: existing `delete_instance` path.
  - Type singleton fallback: `overlays/battle/main/config_json (+_backup)` used only when no instance injected (preview/legacy path), mirroring royale keys. Never read for instance rendering when `instance_settings` present.
- New in-memory state (per `BattleController` member, never persisted):
  - `BattleEngine._state: BattleState` (status, round, participants[2], teams[2], combo, recent events ring max 10, winner, deadlines via `time.monotonic()`), `_auto_buffer: list[_AutoGiftEntry]` (user_key/display/avatar/diamonds/ts), `_round_wins: {left:int,right:int}` inside `BattleState.teams`, one-shot flags `_comeback_armed/_final_push_fired` per round.
- State transitions (per round; `best_of` N → majority M=`N//2+1`):

| State | Trigger | Preconditions | Effect | Invalid → |
|-------|---------|---------------|--------|-----------|
| `idle` | 2 distinct users each ≥`auto_threshold_each` within `auto_window_s` (or `start_manual` with 2 rows) | `auto_start` true (or manual call), status `idle` | lock slots (higher diamonds → left), `battle_id=uuid4hex[:12]`, `round=1`, scores 0, status `countdown`, `countdown_deadline=now+countdown_s`, emit `battle_started+round_started` | `on_gift` with diamonds≤0 / blank key ignored; 3rd distinct user does not create slot; gifts while `countdown` buffered for auto-arm only, not scored |
| `countdown` | `tick` passes deadline | status `countdown` | status `active`, `round_deadline=now+round_duration_s`, emit `round_started` | `on_gift` from anyone ignored for scoring (no points); `stop()` → `idle` full clear |
| `active` | slot-owner gift | status `active`, sender is locked participant, `gifts_enabled`, diamonds>0 | `points=int(diamonds*multiplier[combo])`; team+participant score += points; combo window update → maybe `combo_started/updated`; comeback/close/final-push evaluation → append events; round timer continues | non-participant gift → `[]` no state change; negative/NaN diamonds → `[]`; like/follow → `[]` (disabled path, no wiring) |
| `active` | `tick` passes `round_deadline` | status `active` | round winner = higher score (tie → left? Decision: tie keeps left as winner only if scores>0 else draw → no round win, replay round; documented in engine); `round_wins[winner]++`; emit `round_finished`; if `round_wins==M` → status `finished`, overall `winner`, `victory_deadline=now+victory_display_s`, emit `battle_finished`; else scores reset, `round++`, status `countdown` for next round | `tick` early → only `remaining_seconds` update, no event |
| `finished` | `tick` passes `victory_deadline` | status `finished` | if `auto_reset` → full `reset()` to `idle` (clear participants/scores/round_wins/flags, new empty `battle_id` on next arm); else stay `finished` showing winner until `stop()`/new manual start | `on_gift` ignored while `finished`; `start_manual` allowed only from `idle`/`finished` |
| any | `stop()` / `reset_for_new_stream()` | — | full clear to `idle`, buffers cleared | never raises; idempotent |

- Persistence: live scores/rounds do NOT survive restart (fresh `idle` on boot; `sync_instances(start=False)` then tick drives). Config survives via instance settings.
- Failure behavior per transition: malformed gift (missing key, diamonds≤0, non-numeric) → return `[]`, no mutation, no publish. Config parse failure → fallback to defaults (loader never raises). Publish failure (no pubsub/loop) → state already mutated, publish skipped silently (same as leaderboard `schedule_publish` guard).

## Data / Control Flow

```
TikTok gift (chat/tiktok_source.py:_on_gift, normalized diamonds_total)
 -> ui/main_window.py:_on_tiktok_gift (existing; total_coins=count*coin_each)
 -> [NEW fan-out line] self._battle_group.on_gift(sender,count,tiktok_coin_each,
        sender_avatar_url,sender_user_key)   # every member; Royale/top_gifters lines untouched
 -> overlays/instance_groups.py:InstanceControllerGroup._each("on_gift",…)
 -> overlays/battle_controller.py:BattleController.on_gift
      -> config_loader() (instance merged settings via instance_config_loader)
      -> battle/engine.py:BattleEngine.on_gift → points/combo/comeback/final-push → list[BattleEvent]
      -> schedule_publish() (200ms debounce via loop.call_later, same as leaderboard)
      -> _publish_patch_sync() → OverlayPubSub.publish_sync("overlay:battle:{instance_id}", snapshot)
 -> overlays/server.py:_ws (existing generic) forwards {"op":"patch"} to subscribed OBS/browser source
 -> overlays/battle_overlay.py JS: subscribe{type:"battle",instance} → initial_state → applyPatch(patch) → render()
      status idle|countdown|active|finished + flags is_close/combo/final_push drive CSS classes/badges (event-driven, no rAF)

Timer path (shared 1s tick, no new worker):
 MainWindow._battle_tick_timer (QTimer 1000ms, existing)
 -> _on_battle_tick (extended): royale.tick() (unchanged) + self._battle_group tick via new tick_advance_all()
 -> BattleController.tick_advance() → engine.tick(monotonic) → schedule_publish() only if events or second-changed
 -> publish_sync per dirty member only (idle members with no change publish nothing)

Config/save path (existing patterns):
 WidgetsView universalSchema("battle") edit → api.saveWidgetInstanceSettingsJson(id, json) (generic)
 -> widget_instances.update_instance_settings + publish {"config":…} to overlay:battle:{id}
 -> _save_cfg_to_instance reload list (extended with "_battle_controller") → group.reload_instance(id)
Preview path: api.openWidgetInstanceUrl(id) → previewWidgetInstance → previewLayoutWidget("battle", id)
 -> previewBattleOverlay(id): _preview_config("battle",…) + demo ACTIVE snapshot → publish to overlay:battle:{id}
```

State persisted at: widget instance row (config only). Cleanup at: `stop()`/`reset_for_new_stream()` clears engine state; `InstanceControllerGroup.sync_instances` drops removed members via `stop()`.

## Edge Cases

| Case | Behavior | Handler | User-visible outcome |
|------|----------|---------|----------------------|
| Empty/blank user_key + display | key fallback `display.casefold()`; both blank → gift ignored (`[]`) | `BattleEngine.on_gift` validation | No score change, no badge |
| diamonds ≤0 / NaN / non-numeric count | ignored, no mutation | engine + controller `try int()` guards (mirror leaderboard `on_gift`) | Silent; no patch |
| Gift during `countdown`/`finished`/`idle`-unarmed | not scored; idle feeds auto-arm buffer only | engine phase gate | Timer continues; no score jump |
| Non-participant gift during `active` | ignored for scoring | engine slot check | No change (documented D2) |
| Tie at round end (scores equal) | if both 0 → draw, replay round (no win, emit `round_finished{draw:true}`); else higher wins, exact tie → left wins (deterministic, documented) | engine `_resolve_round` | Winner banner or "DRAW — replay" badge |
| Duplicate rapid gifts (streak/repeat) | each normalized gift counts once upstream dedupe already in `tiktok_source`; engine applies every call (idempotency = additive, not deduped) | upstream `tiktok_source` dedupe; engine additive | Scores track diamonds exactly |
| Burst (50 gifts in 1s) | single debounced patch per 200ms window; `fx_seq` increments; floating `+N` deltas coalesced to latest per team in overlay (max 2 DOM nodes reused) | controller debounce + overlay delta reuse | One smooth update, no object leak |
| Config invalid (negative duration, unknown theme, multiplier 0) | clamped to ranges / fallback to defaults; loader never raises | `battle_overlay_config_from_json_text` validators | Widget renders with sane values |
| Instance deleted mid-battle | `sync_instances` stops/drops member; topic goes silent; server `by-id` 404s | `InstanceControllerGroup.sync_instances` | OBS source freezes last frame until removed; no crash |
| Restart mid-battle | fresh `idle`, empty participants | boot `sync_instances(start=False)` | IDLE card "Waiting for 2 gifters" |
| Missing/invalid avatar URL | `onerror` hides `img`, fallback SVG crown/initials div shows | overlay `BattleParticipant` markup | Clean fallback avatar, no broken icon |
| Narrow width (1024x300) | flex row shrinks: avatar 64→40px, name ellipsis, timer preserved, both sides kept via `minmax(0,1fr)` grid | responsive CSS (no fixed coords) | Both participants + score + timer visible |
| Decision layer enabled but hook raises | caught, logged, hook result discarded; core events already emitted | controller `try/except` around hook | Battle continues; no overlay stall |
| `battle_royale` regression | zero edits to royale files/topics/timers | additive-only change | Royale URLs/topics/behavior byte-identical |

## Error Handling

- Gift validation: blank key, diamonds≤0, unknown phase → return `[]`, no publish. Controller catches `Exception` per member via `_each` (existing group guard) so one bad instance never blocks others.
- Config load: `from_json_text` raises `ValueError` on non-object; `load_*` catches `ValueError/TypeError/JSONDecodeError`, tries backup key, else defaults. `instance_config_loader` catches all, returns type defaults. Overlay `initial_state` never raises (falls back to defaults + empty fighters).
- Publish: `schedule_publish` no-ops when `loop/pubsub` is `None` (preview/test safe). `_publish_patch_sync` wraps `publish_sync` in no-throw path (state mutation already done).
- WS/server: generic paths unchanged; unknown `battle` instance → existing 404 (`_overlay_by_id`) / preview-tolerant `resolve_ws_params` (renders defaults). Malformed client `subscribe` → existing close codes.
- QML: `universalSchema("battle")` reads `cfg[key] ?? fallback` via existing `value()` helper; unknown keys ignored. Save path validates JSON object before `update_instance_settings`.
- Decision hook: disabled default; when enabled, exceptions are swallowed with `_LOG.warning`, core patch still publishes.

## Testing

Run commands use repo conventions (`pyproject` `testpaths=["tests"]`, `pythonpath=["src"]`; lint `ruff check src tests`, format `ruff format .`).

- `tests/test_battle_engine.py` (new, pure Python, no Qt):

```
Test: test_create_idle_snapshot
Given: engine with defaults (best_of=3, threshold=100)
When: snapshot()
Then: status=="idle", participants==[], teams scores 0, remaining==duration, events==[]

Test: test_auto_arm_top_two_lock_slots
Given: idle engine
When: on_gift(A, diamonds=150) then on_gift(B, diamonds=120) (same monotonic window)
Then: status=="countdown", participants [A(left),B(right)], battle_id non-empty, events contain battle_started

Test: test_1v1_data_model_has_teams_and_team_ids
Given: armed engine
When: snapshot()
Then: teams==[{id:left,…},{id:right,…}], each participant team_id in {left,right}, score fields ints

Test: test_tick_countdown_to_active
Given: countdown engine with countdown_s=2
When: tick(deadline+0.1)
Then: status=="active", round==1, remaining==round_duration_s

Test: test_gift_scoring_with_multiplier
Given: active engine, gift_multiplier=2.0, A score 0
When: on_gift(A, diamonds=100)
Then: A score==200, team left==200, event score_changed present

Test: test_like_scoring_disabled_by_default
Given: active engine defaults
When: on_like(A, count=500)
Then: returns [], scores unchanged

Test: test_combo_threshold_and_expiry
Given: active, combo_threshold=5, window=5s
When: 5 gifts from A within 5s
Then: combo=={team_id:left,count:5,multiplier:2.0}, combo_started emitted
When: tick(+6s) with no gifts
Then: combo cleared, combo_broken emitted

Test: test_comeback_detection
Given: active, A=200 B=40 (B trails >20%, leader≥50)
When: B gifts to 210 (overtake)
Then: comeback event emitted once; further gifts without new deficit emit none

Test: test_close_battle_flag
Given: active A=100 B=95 (gap 5% ≤10%)
When: snapshot()
Then: flags.is_close True, close_battle event present (once per approach)

Test: test_final_push
Given: active, remaining≤10s, gap≤15%, both≥20
When: tick into window
Then: final_push event once; flags.final_push True

Test: test_round_finish_and_best_of
Given: best_of=3, A leads at deadline
When: tick(deadline+0.1)
Then: round_finished, round_wins left==1, status==countdown round 2 (not finished)
When: A wins 2nd round similarly
Then: status==finished, winner left, battle_finished emitted

Test: test_reset_clears_all
Given: finished engine
When: reset()
Then: idle, participants [], scores 0, round_wins 0, events []

Test: test_invalid_gifts_ignored
Given: active engine, scores S
When: on_gift(blank key, 0), on_gift(A, -5), on_gift(spectator Z, 999)
Then: all return [], scores==S
```

- `tests/test_battle_overlay_config.py` (new):

```
Test: test_defaults_round_trip
Given: defaults()
When: to_json_text → from_json_text
Then: equal dataclass; theme==cheremsha_neon; gifts_enabled True; likes/follows False; combo True

Test: test_clamping_and_theme_fallback
Given: JSON {round_duration_s:-5, gift_multiplier:99, theme:"nope", scale_percent:999}
When: from_json_text
Then: duration==30 (min), multiplier==10.0 (max), theme==cheremsha_neon, scale==250

Test: test_invalid_json_raises_and_load_falls_back
Given: "not json" / "[1,2]"
When: from_json_text → raises ValueError; load_* with corrupt QSettings → defaults (backup path)
Then: no exception escapes load_*
```

- `tests/test_battle_controller.py` (new, Qt-free except QObject; uses `OverlayPubSub`):

```
Test: test_per_instance_isolation
Given: two controllers instance a/b, same pubsub+loop stub
When: gift to A-participant on ctl-a only
Then: ctl-a snapshot scores>0, ctl-b stays idle/zero

Test: test_publish_topic_is_per_instance
Given: subscribed overlay:battle:{id}
When: on_gift + explicit _publish_patch_sync (or loop run)
Then: patch received on exact topic with participants/teams/config keys; no overlay:battle:* broadcast

Test: test_reset_for_new_stream
Given: active controller
When: reset_for_new_stream()
Then: snapshot idle + patch published
```

- `tests/test_widgets_qml_api_battle_overlay.py` (new, mirrors royale API test):

```
Test: test_preview_battle_publishes_to_instance_topic
Given: OverlayPubSub + WidgetsQmlApi, subscribe overlay:battle:testinst123
When: previewBattleOverlay("testinst123") / previewLayoutWidget("battle","testinst123")
Then: patch has status active, 2 participants, config.theme present

Test: test_battle_config_load_save_round_trip_via_instance
Given: created battle instance via create_instance("battle",…)
When: saveWidgetInstanceSettingsJson(id, modified theme cyber) → loadWidgetInstanceSettingsJson(id)
Then: theme persists; instance type still battle; widgetInstanceUrl(id) endswith /overlay/by-id/{id}
```

- Regression (must all pass, unchanged expectations):
  - `pytest tests/test_widget_instances.py tests/test_overlays_registry.py tests/test_widgets_preview_all_types.py tests/test_battle_royale_controller.py tests/test_battle_royale_gifts.py tests/test_battle_royale_overlay_config.py tests/test_widgets_qml_api_battle_royale_overlay.py tests/test_overlays_server_integration.py tests/test_pubsub_instance_routing.py -q` → all pass. Note `test_widgets_preview_all_types` auto-covers `battle` (iterates `WIDGET_TYPES`) — after step 9 it must include `battle` with non-empty patch.
  - `ruff check src/stream_cheremsha/battle src/stream_cheremsha/overlays/battle_* src/stream_cheremsha/ui/main_window.py src/stream_cheremsha/ui/widgets_qml_api.py src/stream_cheremsha/l10n.py tests/test_battle_* tests/test_widgets_qml_api_battle_overlay.py` → clean. `ruff format --check` on new files → clean.
  - Perf: `pytest tests/test_settings_lazy_warm.py -q` still passes (no nav/startup change); manual audit in step 12.

## Configuration / Deployment

No env vars, no feature flags, no DB migration, no server route change. Config surface is the new `BattleOverlayConfig` (all keys live inside widget-instance `settings`, plus singleton fallback `overlays/battle/main/config_json`):

```
battle_name="BATTLE" best_of=3 round_duration_s=60 countdown_s=5 victory_display_s=8
auto_start=true auto_threshold_each=100 auto_window_s=30 auto_reset=true auto_reset_delay_s=10
gifts_enabled=true gift_multiplier=1.0 likes_enabled=false likes_per_point=100
follows_enabled=false follow_points=10
combo_enabled=true combo_threshold=5 combo_window_s=5 combo_multiplier_step=1.0 combo_max_multiplier=3.0
comeback_enabled=true comeback_threshold_pct=20 close_threshold_pct=10
theme="cheremsha_neon" layout_mode="normal" show_avatars=true show_event_badges=true
show_winner_screen=true event_animations=true animation_intensity_pct=100
scale_percent=100 hide_when_idle=false font_family="Segoe UI" base_font_size_px=14
final_push_seconds=10 decision_layer_enabled=false schema_version=1
```

Ranges enforced in `from_json_text` (see Step 4 code). Up/down migration: none required (additive `WIDGET_TYPES` + new QSettings keys). Verify: create Battle instance → `widgetInstancesJson` contains it → restart app → instance + settings + URL identical.

## Compatibility

- Existing widgets/instances/UUIDs/URLs untouched: `widget_instances.py` change is additive dict entries; `SCHEMA_VERSION` stays 1; `list_instances` parse path unchanged.
- `battle_royale` files, topics (`overlay:battle_royale:*`), timers, and QML branches untouched; royale tests must pass unmodified.
- `server.py`, `pubsub.py`, `event_bus.py`, `models.py` untouched.
- Platforms: pure Qt/aiohttp, no OS-specific code; overlay HTML works in OBS/Streamlabs/vMix/browser.
- What breaks: nothing. New QML branches default to fallbacks for unknown types; old clients ignore unknown `battle` patches.

## Acceptance Criteria

- When Create Widget → Battle with name X is submitted, `widgetInstancesJson` contains `{type_id:"battle", name:X}` with fresh UUID and full defaults; gallery shows card with swords icon + purple accent.
- When `/overlay/by-id/{battle_id}` is opened in a browser, IDLE card renders ("Waiting for 2 gifters") with transparent background and no JS errors.
- When two distinct TikTok users gift ≥threshold within window, status transitions idle→countdown→active; left/right lock by diamonds; timer counts down each second.
- When a slot owner gifts during active, their score increases by `int(diamonds*multiplier)` within 200–1200ms on the overlay; spectator gifts change nothing.
- When 5 gifts arrive within 5s, `COMBO x2` badge appears; when leader overtaken after ≥20% deficit, `COMEBACK` banner appears once; when ≤10s remains and close, timer + bar intensify (`final_push`).
- When round timer expires, round winner increments `round_wins`, next round auto-starts; at majority, `WINNER` screen shows `742 vs 691`-style final + optional stats; auto-reset returns to IDLE after delay.
- When width is 1024x300, both participants + scores + timer remain visible; no participant hidden, no horizontal overflow.
- When theme is switched cyber/arcade/minimal/neon, same state renders with different accents via CSS vars (one widget, no duplicate code).
- When AI hook disabled (default), zero decision-layer calls occur; engine tests pass with no AI import.
- `pytest` full relevant set + `ruff check` clean; startup QML page count unchanged; no WebEngine import; no new QTimer; idle battle publishes nothing.

## Implementation Steps

### Step 1 — Battle domain models (pure Python, no Qt)

**Files:** `src/stream_cheremsha/battle/__init__.py` (new), `src/stream_cheremsha/battle/models.py` (new)
**Target:** `BattleStatus, Participant, Team, BattleEvent, ComboState, BattleState.to_dict`
**Purpose:** Platform-independent 1v1-now/2v2-ready schema the overlay, controller, and future themes share.
**Implementation:** Create package + models exactly:

```python
# src/stream_cheremsha/battle/__init__.py
from stream_cheremsha.battle.engine import BattleEngine
from stream_cheremsha.battle.models import (
    BattleEvent, BattleState, BattleStatus, ComboState, Participant, Team,
)
__all__ = ["BattleEngine", "BattleEvent", "BattleState", "BattleStatus", "ComboState", "Participant", "Team"]
```

```python
# src/stream_cheremsha/battle/models.py
from __future__ import annotations
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

class BattleStatus(StrEnum):
    IDLE = "idle"
    COUNTDOWN = "countdown"
    ACTIVE = "active"
    FINISHED = "finished"

@dataclass(slots=True)
class Participant:
    id: str            # stable user key
    name: str          # display name
    avatar_url: str = ""
    team_id: str = "left"   # left | right | team_<n> (2v2-ready)
    score: int = 0
    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "avatar_url": self.avatar_url,
                "team_id": self.team_id, "score": int(self.score)}

@dataclass(slots=True)
class Team:
    id: str
    score: int = 0
    round_wins: int = 0
    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "score": int(self.score), "round_wins": int(self.round_wins)}

@dataclass(slots=True)
class BattleEvent:
    type: str          # gift_received|score_changed|combo_started|combo_updated|combo_broken|
                       # big_gift|comeback|close_battle|final_push|round_started|round_finished|
                       # battle_started|battle_finished
    team_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    at: float = 0.0    # time.monotonic()
    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "team_id": self.team_id, "payload": dict(self.payload), "at": float(self.at)}

@dataclass(slots=True)
class ComboState:
    team_id: str | None = None
    count: int = 0
    multiplier: float = 1.0
    window_start: float = 0.0
    def to_dict(self) -> dict[str, Any]:
        return {"team_id": self.team_id, "count": int(self.count),
                "multiplier": float(self.multiplier)}

@dataclass(slots=True)
class BattleState:
    battle_id: str = ""
    status: BattleStatus = BattleStatus.IDLE
    round: int = 1
    best_of: int = 3
    participants: list[Participant] = field(default_factory=list)
    teams: list[Team] = field(default_factory=list)
    combo: ComboState = field(default_factory=ComboState)
    events: list[BattleEvent] = field(default_factory=list)  # ring, max 10
    winner_team_id: str | None = None
    remaining_seconds: int = 0
    countdown_remaining_s: int = 0
    is_close: bool = False
    is_comeback: bool = False
    final_push: bool = False
    countdown_deadline: float | None = None
    round_deadline: float | None = None
    victory_deadline: float | None = None
    def push_event(self, ev: BattleEvent) -> None:
        self.events.append(ev)
        if len(self.events) > 10:
            del self.events[: len(self.events) - 10]
    def team(self, tid: str) -> Team | None:
        for t in self.teams:
            if t.id == tid:
                return t
        return None
    def participant(self, uid: str) -> Participant | None:
        for p in self.participants:
            if p.id == uid:
                return p
        return None
```

**Inputs / Outputs:** In: none. Out: importable `stream_cheremsha.battle.models`.
**State:** None (plain dataclasses).
**Side effects:** None.
**Error handling:** None (no parsing here).
**Dependencies:** None.
**Do:** Keep field names EXACT (`team_id`, `round_wins`, `remaining_seconds`) — steps 2/5/6 reference them verbatim.
**Do NOT:** Add Qt/aiohttp imports; add TikTok/Twitch concepts; rename `FINISHED` to `victory`.
**Verification:** `python3 -c "from stream_cheremsha.battle.models import BattleStatus, BattleState; print(BattleStatus.ACTIVE.value, BattleState().status.value)"` → `active idle`. `ruff check src/stream_cheremsha/battle` → clean.

### Step 2 — Deterministic BattleEngine (scoring, combo, comeback, rounds, timer)

**Files:** `src/stream_cheremsha/battle/engine.py` (new)
**Target:** `class BattleEngine`
**Purpose:** All deterministic battle rules; no Qt, no I/O, injectable `now` for tests.
**Implementation:** Create file with this exact public surface and semantics (internal helpers may vary but behavior must match):

```python
from __future__ import annotations
import time, uuid
from dataclasses import dataclass
from typing import Any
from stream_cheremsha.battle.models import BattleEvent, BattleState, BattleStatus, ComboState, Participant, Team

@dataclass(slots=True)
class _AutoEntry:
    key: str; name: str; avatar: str; diamonds: int; ts: float

class BattleEngine:
    def __init__(self, cfg_provider) -> None:  # cfg_provider: () -> config object with fields from Step 4
        self._cfg = cfg_provider
        self._state = BattleState(teams=[Team(id="left"), Team(id="right")])
        self._auto: list[_AutoEntry] = []
        self._combo_hits: dict[str, list[float]] = {"left": [], "right": []}
        self._comeback_armed: bool = False
        self._close_fired: bool = False
        self._final_push_fired: bool = False
        self._trailer: str | None = None

    def reset(self) -> None:
        best = int(getattr(self._cfg(), "best_of", 3))
        self._state = BattleState(best_of=best, teams=[Team(id="left"), Team(id="right")])
        self._auto.clear(); self._combo_hits = {"left": [], "right": []}
        self._comeback_armed = False; self._close_fired = False
        self._final_push_fired = False; self._trailer = None

    def snapshot(self) -> dict[str, Any]: ...
    def start_manual(self, rows: list[dict[str, str]], *, now: float | None = None) -> bool: ...
    def on_gift(self, *, user_key: str, display: str, avatar_url: str,
                diamonds: int, now: float | None = None) -> list[dict[str, Any]]: ...
    def on_like(self, *, user_key: str, count: int, now: float | None = None) -> list[dict[str, Any]]:
        return []  # v1 disabled-path interface (config likes_enabled respected when wired later)
    def on_follow(self, *, user_key: str, now: float | None = None) -> list[dict[str, Any]]:
        return []
    def tick(self, now: float | None = None) -> list[dict[str, Any]]: ...
```

Required semantics (implement exactly):
- `on_gift`: validate (`diamonds=int(diamonds)`; `<=0` → `[]`; key=`user_key.strip() or display.casefold()`; blank → `[]`). `IDLE` + `auto_start` → append `_AutoEntry`, prune older than `auto_window_s`, if ≥2 distinct keys each with single-gift `diamonds >= auto_threshold_each` → lock top-2 by max single gift (higher→left), `battle_id=uuid4().hex[:12]`, `round=1`, `best_of=cfg.best_of`, scores 0, `status=COUNTDOWN`, `countdown_deadline=now+countdown_s`, `countdown_remaining_s=countdown_s`, emit `[battle_started, round_started]`, clear `_auto`. `COUNTDOWN/FINISHED` → `[]`. `ACTIVE` → sender must be locked participant else `[]`; if not `gifts_enabled` → `[]`; combo update (prune team hits older than `combo_window_s`; append now; `count=len`; if `combo_enabled` and `count>=threshold`: `mult=min(max_mult, 2.0 if count<2*threshold else 3.0)`; emit `combo_started` (first) / `combo_updated`; else `mult=1.0`); `points=int(diamonds*float(gift_multiplier)*mult)` (min 0 → `[]`); add to participant+team; emit `gift_received{points,mult}`, `score_changed{left,right}`, `big_gift` if `diamonds>=500` (fixed v1 threshold, documented); evaluate comeback/close (see below); return event dicts.
- Comeback/close (only when `comeback_enabled`, both teams exist): `pct_gap=abs(a-b)/max(1,max(a,b))`. If not armed and leader≥50 and trailer gap≥`comeback_threshold_pct/100` → arm (`_trailer`=trailing id). If armed and trailer overtakes → emit `comeback{winner:trailer}`, `is_comeback=True` (sticky till round end), disarm. If gap≤`close_threshold_pct/100` and max(score)≥20 and not `_close_fired` → emit `close_battle`, `is_close=True`, `_close_fired=True`. Reset `is_close` False when gap widens (re-arm allowed once per approach: clear `_close_fired` when gap > threshold*1.5).
- `tick`: `COUNTDOWN` past deadline → `ACTIVE`, `round_deadline=now+round_duration_s`, emit `round_started`. `ACTIVE`: update `remaining_seconds`; if `remaining<=final_push_seconds` and gap≤`close_threshold_pct` and both≥20 and not fired and `comeback_enabled` → emit `final_push`, `final_push=True`; past deadline → resolve round (higher wins; 0–0 draw → replay same round, emit `round_finished{draw:true}`, reset scores, back to `COUNTDOWN`; else `round_wins[w]++`, emit `round_finished{winner}`; majority `M=best_of//2+1` reached → `FINISHED`, `winner_team_id`, `victory_deadline=now+victory_display_s`, emit `battle_finished`; else `round++`, scores 0, combo cleared, one-shot flags reset, `COUNTDOWN`). Past `victory_deadline` in `FINISHED` → if `auto_reset` → `reset()` (emit nothing; snapshot shows idle) else stay. Second-boundary changes return `[]` but caller treats remaining-change as dirty (controller compares).
- `snapshot()`: return `{"battle_id","status":value,"round","best_of","round_wins":{"left":..,"right":..},"duration_s":round_duration_s,"remaining_seconds","countdown_remaining_s","participants":[p.to_dict()…],"teams":[t.to_dict()…],"combo":combo.to_dict(),"flags":{"is_close","is_comeback","final_push"},"events":[e.to_dict() for last 10],"winner":{"team_id":…, "name":…}|None}`. Tie-break winner name lookup from participants.
- `start_manual(rows, now)`: allowed from `idle|finished`; need ≥2 unique keys (same key derivation); lock first 2 as left/right; same countdown init; return True/False.

**Inputs / Outputs:** In: config object + gift/tick calls. Out: `list[dict]` events (JSON-serializable) + `snapshot()` dict.
**State:** `_state/_auto/_combo_hits/one-shot flags` in memory.
**Side effects:** None (no I/O).
**Error handling:** All invalid input → `[]`, never raises (except `cfg_provider` raising → let controller fallback; engine itself try/wraps int conversions).
**Dependencies:** Step 1.
**Do:** Use `time.monotonic()` when `now is None`; keep events ring ≤10; keep tie-break deterministic (left on exact tie >0).
**Do NOT:** Import Qt/aiohttp/QSettings/TikTok gifts catalog; call decision layer; persist anything.
**Verification:** `pytest tests/test_battle_engine.py -q` (written in Step 12, but engine must import cleanly now): `python3 -c "from stream_cheremsha.battle.engine import BattleEngine; print('ok')"` → `ok`.

### Step 3 — Optional decision-layer hook (disabled default)

**Files:** `src/stream_cheremsha/battle/decision.py` (new)
**Target:** `BattleDecision`, `NullDecisionLayer`
**Purpose:** Clean Jev/Laya integration point without making AI required.
**Implementation:**

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(slots=True, frozen=True)
class BattleDecision:
    is_big_moment: bool = False
    is_high_priority: bool = False
    is_highlight_candidate: bool = False
    is_close_battle: bool = False
    is_comeback: bool = False
    should_trigger_special_animation: bool = False
    def to_dict(self) -> dict[str, Any]:
        return {"is_big_moment": self.is_big_moment, ...}

class NullDecisionLayer:
    kind = "null"
    def decide(self, event: dict[str, Any]) -> BattleDecision:
        return BattleDecision()
```

Controller (Step 5) holds `self._decision = None`; only when `cfg.decision_layer_enabled` True AND `self._decision is not None` does it call `decide()` on `battle_finished/comeback/final_push/big_gift` events (max 1 call per engine batch), merges `decision.to_dict()` into that event's payload under `decision`, wrapped in try/except. Never call per `score_changed`.

**Verification:** `python3 -c "from stream_cheremsha.battle.decision import NullDecisionLayer; print(NullDecisionLayer().decide({}).to_dict())"` → all False.

### Step 4 — Battle overlay config (validation mirrors royale module)

**Files:** `src/stream_cheremsha/overlays/battle_overlay_config.py` (new)
**Target:** `BattleOverlayConfig`, `BATTLE_THEMES`, `battle_overlay_config_defaults/to_json_text/from_json_text/load_/save_`, `battle_overlay_config_to_public_dict`
**Purpose:** Persisted per-instance settings with strict clamping; single source for engine + overlay + QML schema keys.
**Implementation:** Frozen dataclass with EXACT fields/defaults (do not rename — QML + engine reference them):

```python
BATTLE_OVERLAY_CONFIG_SCHEMA_VERSION = 1
BATTLE_OVERLAY_CONFIG_QSETTINGS_KEY = "overlays/battle/main/config_json"
_BATTLE_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY = "overlays/battle/main/config_json_backup"
BATTLE_THEMES = frozenset({"cheremsha_neon", "cyber", "arcade", "minimal"})
BATTLE_LAYOUTS = frozenset({"normal", "compact"})

@dataclass(frozen=True, slots=True)
class BattleOverlayConfig:
    schema_version: int
    battle_name: str            # default "BATTLE"
    best_of: int                # 1|3|5 default 3
    round_duration_s: int       # 30..300 default 60
    countdown_s: int            # 1..10 default 5
    victory_display_s: int      # 3..15 default 8
    auto_start: bool            # True
    auto_threshold_each: int    # 1..10000 default 100
    auto_window_s: int          # 5..120 default 30
    auto_reset: bool            # True
    auto_reset_delay_s: int     # 5..60 default 10 (reserved; victory_display_s drives timing v1)
    gifts_enabled: bool         # True
    gift_multiplier: float      # 0.1..10.0 default 1.0
    likes_enabled: bool         # False (unwired v1)
    likes_per_point: int        # 1..10000 default 100
    follows_enabled: bool       # False (unwired v1)
    follow_points: int          # 0..1000 default 10
    combo_enabled: bool         # True
    combo_threshold: int        # 2..20 default 5
    combo_window_s: int         # 1..30 default 5
    combo_multiplier_step: float# 1.0..2.0 default 1.0 (informational; engine uses x2/x3 ladder)
    combo_max_multiplier: float # 1.0..5.0 default 3.0
    comeback_enabled: bool      # True
    comeback_threshold_pct: int # 5..50 default 20
    close_threshold_pct: int    # 1..30 default 10
    theme: str                  # BATTLE_THEMES default cheremsha_neon
    layout_mode: str            # BATTLE_LAYOUTS default normal
    show_avatars: bool          # True
    show_event_badges: bool     # True
    show_winner_screen: bool    # True
    event_animations: bool      # True
    animation_intensity_pct: int# 25..200 default 100
    scale_percent: int          # 40..250 default 100
    hide_when_idle: bool        # False (D11)
    font_family: str            # "Segoe UI"
    base_font_size_px: int      # 10..32 default 14
    final_push_seconds: int     # 3..30 default 10
    decision_layer_enabled: bool# False
```

Copy `_ensure_int/_ensure_float/_ensure_bool/_ensure_theme` helpers + `to/from/load/save` from `battle_royale_overlay_config.py` (same backup-key pattern, same `separators=(",",":")`, `sort_keys=True`). `from_json_text` clamps every numeric, validates `best_of in (1,3,5) else 3`, theme/layout fallback. `to_public_dict(cfg)` returns plain dict + `ui_locale` is added by overlay (not here).

**Verification:** `python3 -c "from stream_cheremsha.overlays.battle_overlay_config import battle_overlay_config_defaults as d, battle_overlay_config_to_json_text as t, battle_overlay_config_from_json_text as f; print(f(t(d())).theme)"` → `cheremsha_neon`.

### Step 5 — Per-instance BattleController (QObject, debounced publish)

**Files:** `src/stream_cheremsha/overlays/battle_controller.py` (new)
**Target:** `class BattleController(QObject)`, `OVERLAY_TYPE="battle"`
**Purpose:** Own one `BattleEngine` per widget instance; publish `overlay:battle:{instance}` with 200ms debounce (identical to leaderboard pattern).
**Implementation:** Mirror `live_leaderboard_controller.py` structure exactly (same ctor/kw names so `InstanceControllerGroup` works unmodified):

```python
class BattleController(QObject):
    OVERLAY_TYPE = "battle"
    def __init__(self, *, pubsub, get_locale, instance="main", parent=None, config_loader=None):
        super().__init__(parent)
        self._pubsub = pubsub; self._get_locale = get_locale
        self._instance = str(instance or "main").strip() or "main"
        self._config_loader = config_loader
        self._engine = BattleEngine(self._load_cfg)
        self._publish_handle = None; self._loop = None
        self._decision = None
        self._last_remaining = -1; self._last_countdown = -1
    def _load_cfg(self):  # instance loader or singleton fallback
        if self._config_loader is not None: return self._config_loader()
        from stream_cheremsha.overlays.battle_overlay_config import load_battle_overlay_config
        return load_battle_overlay_config()
    # start/stop/set_pubsub/set_event_loop/reload_config/initial_state/reset_for_new_stream/
    # schedule_publish/_publish_patch_sync/_build_state/tick_advance/on_gift
```

- `on_gift(sender, count, tiktok_coin_each=0, sender_avatar_url="", sender_user_key="")`: `c=int(count)` clamp ≥1, `each=int(tiktok_coin_each or 0)`, `coins=c*each if each>0 else c`; validate display/key non-blank else return; call `engine.on_gift(user_key=key or display, display=sender or "?", avatar_url=…, diamonds=coins)`; if events non-empty → `schedule_publish()` + immediate `_publish_patch_sync()` on `battle_finished/round_finished` (same urgency as royale hit path); decision hook only for big/close/comeback/final/finished when enabled.
- `_build_state()`: `cfg=self._load_cfg()`; `snap=engine.snapshot()`; return `{"config": public_dict(cfg), "locale": get_locale(), **snap}` — keys match Step 2 snapshot verbatim plus config/locale.
- `tick_advance(now=None)`: `t=monotonic`; `events=engine.tick(t)`; dirty = bool(events) or remaining/countdown changed (`_last_remaining` compare); if dirty → `schedule_publish()`; if `battle_finished` in events → immediate publish. Return dirty bool (driven by MainWindow tick).
- `start/stop`: `start()` → `reload_config` + `schedule_publish()` (no QTimer owned); `stop()` → cancel handle. `reload_config()` → re-clamp `best_of` into engine (`engine.reset()` ONLY if `best_of` changed and status idle, else keep live battle — document), then publish.
- Publish: identical debounce to leaderboard (`_PUBLISH_DEBOUNCE_MS=200`, `loop.call_later`, `publish_sync(f"overlay:battle:{self._instance}", patch)`).

**Do:** Keep method names/signatures identical to leaderboard (`on_gift`, `schedule_publish`, `initial_state`, `reload_config`, `reset_for_new_stream`) so group fan-out works with zero `instance_groups.py` change.
**Do NOT:** Create own QTimer/thread; broadcast to `*`; import TikTok/chat modules.
**Verification:** `python3 -c "from stream_cheremsha.overlays.battle_controller import BattleController; print(BattleController.OVERLAY_TYPE)"` → `battle`.

### Step 6 — Battle overlay renderer (one file, themed, responsive, event-driven)

**Files:** `src/stream_cheremsha/overlays/battle_overlay.py` (new)
**Target:** `class BattleOverlayType`
**Purpose:** Browser-source HTML served by generic routes; reacts to normalized state only.
**Implementation:** Structure mirrors `battle_royale_overlay.py:24-44 + 778-801`:
- `type = "battle"`. `render_html(params)`: `normalize_instance_id`, `subscribe_msg={op:subscribe,type:"battle",instance,params:{}}`, `initial_scale` from `instance_settings.scale_percent` clamp 40–250, root CSS var `--bt-scale`. Return single inline `<!doctype html>` with:
  - Layout: `.bt-root` grid `1fr auto 1fr` (left participant | center VS+timer | right participant) + full-width `.bt-bar` below (left fill vs right fill, leader side glows). Flex/grid only, no absolute coords for the whole layout; `minmax(0,1fr)` columns so 1024px never collapses; media query `<700px`: avatar 64→40, hide subtitle, keep names/scores/timer.
  - Themes via `[data-theme]` vars: `cheremsha_neon` (purple `#a855f7`/cyan `#22d3ee`/magenta `#f472b6`, dark navy `#0b0e1a`), `cyber` (blue/violet HUD `#38bdf8/#8b5cf6`), `arcade` (amber/red energetic `#fbbf24/#ef4444`), `minimal` (slate monochrome `#e2e8f0`, no glow). Set `document.body.dataset.theme = cfg.theme`.
  - States as classes on root: `is-idle/is-countdown/is-active/is-close/is-combo/is-comeback/is-final/is-finished` derived from `status + flags + combo`. Timer emphasized in `is-final` (scale pulse 0.6s once, not looped). Score bar width transition `0.35s ease` (event-driven). Event badges: `#badge` single reused node showing `COMBO xN / COMEBACK / FINAL PUSH / +250` for 1.2s then fade (no unbounded nodes). Big-gift pulse: avatar `pulse` class 0.5s. Winner: centered `WINNER name 742 vs 691` + optional `round_wins` dots; respects `show_winner_screen`, `hide_when_idle` (hide root when idle only if true).
  - Avatar: `<img onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">` + fallback div with initials + local `../assets/icons/web_swords.svg`-tinted ring. No emoji icons; gift/timer/trophy/combo icons as inline SVG paths (stroke currentColor, 16px) or local `/assets/icons/*.svg` refs (gift=`web_event_gift.svg`, timer=`web_online.svg`? use text timer + trophy `web_trophy.svg`, crown `web_crown.svg`).
  - JS: same WS backoff as royale (`min(5000,250+rand250+tries*350)`), `subscribe`, `handleMsg` (`initial_state` → `applyPatch+render`; `patch` → `applyPatch+render`). `applyPatch` assigns `config/status/round/best_of/round_wins/participants/teams/combo/flags/events/winner/remaining/countdown`. `render()` rebuilds text/widths/classes only (no `requestAnimationFrame`, no polling, no blur/shader).
- `initial_state(params)`: `typed_config_for_type("battle", params, load_battle_overlay_config, battle_overlay_config_from_json_text)` → `to_json` + `ui_locale` → return `{"config":…, "status":"idle","round":1,"best_of":cfg.best_of,"round_wins":{"left":0,"right":0},"duration_s":cfg.round_duration_s,"remaining_seconds":cfg.round_duration_s,"countdown_remaining_s":0,"participants":[],"teams":[{"id":"left","score":0},{"id":"right","score":0}],"combo":{"team_id":None,"count":0,"multiplier":1.0},"flags":{"is_close":False,"is_comeback":False,"final_push":False},"events":[],"winner":None}`.
- File header `# ruff: noqa: E501` (same as royale, required by per-file-ignores convention).

**Verification:** `python3 -c "from stream_cheremsha.overlays.battle_overlay import BattleOverlayType; h=BattleOverlayType().render_html({'instance':'x'}); print('battle' in h and 'ws://' in h and 'requestAnimationFrame' not in h)"` → `True`.

### Step 7 — Register widget type (registry + instances)

**Files:** `src/stream_cheremsha/overlays/registry.py`, `src/stream_cheremsha/overlays/widget_instances.py`
**Target:** `OverlayRegistry.__init__`, `WIDGET_TYPES`, `_DEFAULTS_LOADERS`
**Purpose:** Make `battle` creatable, persistable, servable.
**Implementation:**
- `registry.py`: add `from stream_cheremsha.overlays.battle_overlay import BattleOverlayType` (keep import sort order: after `actions_overlay`, before `chat_overlay`? match ruff `I` — place alphabetically: `battle_overlay` sorts before `chat_overlay`; put line 8) + `self.register(BattleOverlayType())` immediately after `self.register(BattleRoyaleOverlayType())`.
- `widget_instances.py`: in `WIDGET_TYPES` after `"battle_royale"` block insert:

```python
    "battle": {
        "name": "Battle",
        "description": "Битва 1v1: топ-2 GIFтери, раунди best-of.",
        "icon": "⚔️",
        "icon_svg": "icons/web_swords.svg",
        "accent": "#a855f7",
        "platforms": ["tiktok"],
    },
```

  in `_DEFAULTS_LOADERS` after `"battle_royale"` line insert `"battle": "stream_cheremsha.overlays.battle_overlay_config:battle_overlay_config_defaults:battle_overlay_config_to_json_text",`.
**Do NOT:** Bump `SCHEMA_VERSION`; touch backup logic; rename existing keys.
**Verification:** `python3 -c "from stream_cheremsha.overlays.registry import OverlayRegistry; print('battle' in OverlayRegistry().registered_types())"` → `True`. `python3 -c "from stream_cheremsha.overlays.widget_instances import default_settings_for; print(default_settings_for('battle')['theme'])"` → `cheremsha_neon`.

### Step 8 — MainWindow wiring (group + shared tick + gift fan-out + reset)

**Files:** `src/stream_cheremsha/ui/main_window.py`
**Target:** imports, group init, tick, `_on_tiktok_gift`, `reset_for_new_stream`
**Purpose:** Drive per-instance battles from existing events/timer.
**Implementation:**
- (a) Imports: after `from stream_cheremsha.overlays.battle_royale_overlay_config import (` block add `from stream_cheremsha.overlays.battle_controller import BattleController` and `from stream_cheremsha.overlays.battle_overlay_config import (battle_overlay_config_defaults, battle_overlay_config_from_json_text,)`. Keep `I`-sort.
- (b) Group init directly after `_live_leaderboard_simple.sync_instances(start=False)` (~L1212):

```python
        from stream_cheremsha.overlays.instance_groups import instance_config_loader as _battle_cfg_loader

        def _make_battle_controller(instance_id: str) -> BattleController:
            return BattleController(
                pubsub=self._overlay_server.pubsub(),
                get_locale=lambda: self._locale,
                instance=instance_id,
                parent=self,
                config_loader=_battle_cfg_loader(
                    "battle",
                    instance_id,
                    battle_overlay_config_from_json_text,
                    battle_overlay_config_defaults,
                ),
            )

        self._battle_group = InstanceControllerGroup("battle", _make_battle_controller)
        self._battle_group.sync_instances(start=False)
```

  plus `self._widgets_qml_api.set_battle_controller(self._battle_group)` next to `set_live_leaderboard_simple_controller` (~L1567).
- (c) Tick: extend `_on_battle_tick` (~L6625) to also drive the group using an inline member loop (no new timer, no `instance_groups.py` change — touching that shared file is prohibited):

```python
    def _on_battle_tick(self) -> None:
        if self._battle_controller.tick():
            self._schedule_battle_overlay_publish()
        grp = getattr(self, "_battle_group", None)
        members = getattr(grp, "_members", None) or {}
        try:
            ctls = list(members.values())
        except Exception:
            ctls = []
        for ctl in ctls:
            try:
                ctl.tick_advance()
            except Exception:
                continue
```
- (d) Gift fan-out after `self._live_leaderboard_simple.on_gift(…)` block (~L7382–7388) insert:

```python
            try:
                self._battle_group.on_gift(
                    sender=sender,
                    count=count,
                    tiktok_coin_each=tiktok_coin_each,
                    sender_avatar_url=str(sender_avatar_url or ""),
                    sender_user_key=sender_user_key,
                )
            except Exception:
                pass
```

  (Royale/top_gifters lines above stay byte-identical.)
- (e) Reset: in `reset_for_new_stream` next to `self._live_leaderboard_simple.reset_for_new_stream()` (~L6941) add `try: self._battle_group.reset_for_new_stream()\nexcept Exception: pass`.
- Lazy perf: group starts empty → tick loop iterates zero members (no cost); `sync_instances` must be re-called when instances change — hook into existing widget-instances-changed path that already re-syncs leaderboard groups (find `sync_instances` callers for leaderboard and mirror for battle; typically in widget save/create handlers — add `self._battle_group.sync_instances(start=True)` alongside each leaderboard `sync_instances` call, no new signal).

**Verification:** `python3 -c "import ast; t=ast.parse(open('src/stream_cheremsha/ui/main_window.py').read()); s=open('src/stream_cheremsha/ui/main_window.py').read(); assert '_battle_group' in s and '_make_battle_controller' in s; print('ok')"` → `ok`.

### Step 9 — WidgetsQmlApi (preview + instance-aware load/save)

**Files:** `src/stream_cheremsha/ui/widgets_qml_api.py`
**Target:** `set_battle_controller`, `previewBattleOverlay`, `previewLayoutWidget` branch, `load/saveBattleOverlayConfigMap/Json`
**Purpose:** Editor + live preview for battle instances.
**Implementation:**
- Add setter next to `set_live_leaderboard_simple_controller` (~L247):

```python
    def set_battle_controller(self, controller: Any) -> None:
        self._battle_controller = controller
```

  init `self._battle_controller: Any = None` in `__init__` alongside other controllers.
- `previewBattleOverlay(instance)` mirroring `previewBattleRoyaleOverlay` but with battle snapshot keys:

```python
    @Slot(str)
    @Slot()
    def previewBattleOverlay(self, instance: str | None = None) -> None:
        token = str(instance or "").strip()
        if not token:
            return
        topic = f"overlay:battle:{token}"
        cfg = self._preview_config("battle", token, load_battle_overlay_config, battle_overlay_config_from_json_text)
        patch = {"config": json.loads(battle_overlay_config_to_json_text(cfg)),
                 "battle_id": "preview1", "status": "active", "round": 2, "best_of": 3,
                 "round_wins": {"left": 1, "right": 0},
                 "duration_s": int(getattr(cfg, "round_duration_s", 60)),
                 "remaining_seconds": 43, "countdown_remaining_s": 0,
                 "participants": [{"id": "mira", "name": "Mira", "avatar_url": "", "team_id": "left", "score": 62},
                                  {"id": "lera", "name": "Lera", "avatar_url": "", "team_id": "right", "score": 102}],
                 "teams": [{"id": "left", "score": 62, "round_wins": 1}, {"id": "right", "score": 102, "round_wins": 0}],
                 "combo": {"team_id": "right", "count": 6, "multiplier": 2.0},
                 "flags": {"is_close": False, "is_comeback": False, "final_push": False},
                 "events": [{"type": "combo_updated", "team_id": "right", "payload": {"count": 6}, "at": 0.0}],
                 "winner": None, "locale": _ui_locale()}
        self._publish_patch(topic=topic, patch=patch)
```

  imports for `load_battle_overlay_config…` at top alongside royale imports.
- `previewLayoutWidget`: add `elif typ == "battle": self.previewBattleOverlay(inst)` after royale branch.
- `load/saveBattleOverlayConfigMap/Json` for battle with instance-first routing (full bodies, mirroring the royale wrappers at L1838–1895 with `battle` names — do not abbreviate when implementing):

```python
    def loadBattleOverlayConfigMap(self) -> dict[str, Any]:
        routed = self._load_cfg_or_instance("battle")
        if routed is not None:
            return routed
        cfg = load_battle_overlay_config()
        return json.loads(battle_overlay_config_to_json_text(cfg))

    def loadBattleOverlayConfigJson(self) -> str:
        cfg = load_battle_overlay_config()
        return battle_overlay_config_to_json_text(cfg)

    def saveBattleOverlayConfigJson(self, cfg_json: str) -> None:
        from stream_cheremsha.overlays import widget_instances as _wi
        txt = str(cfg_json or "").strip()
        if not txt:
            return
        try:
            cfg = battle_overlay_config_from_json_text(txt)
        except (ValueError, TypeError, json.JSONDecodeError):
            return
        if self._save_cfg_to_instance("battle", json.loads(battle_overlay_config_to_json_text(cfg))):
            return
        save_battle_overlay_config(cfg)
        _LOG.info("widgets overlay persisted: battle")
        # No singleton-topic publish here: battle has no singleton instance attr.
        # Per-instance saves publish via _save_cfg_to_instance above.

    def saveBattleOverlayConfigMap(self, cfg_js: QJSValue) -> None:
        try:
            plain = cfg_js.toVariant()
        except Exception:
            _LOG.warning("widgets ConfigMap save: battle rejected (null/undefined)")
            return
        try:
            txt = json.dumps(plain, ensure_ascii=False)
        except (TypeError, ValueError):
            _LOG.warning("widgets ConfigMap save: battle rejected empty_or_non_serializable")
            return
        _LOG.info("widgets ConfigMap save: battle ok json_len=%d", len(txt))
        self.saveBattleOverlayConfigJson(txt)
```
- `_save_cfg_to_instance` reload tuple: append `"_battle_controller"` to the `_attr` list so instance saves hot-reload battle members.

**Verification:** `pytest tests/test_widgets_qml_api_battle_overlay.py tests/test_widgets_preview_all_types.py -q` → pass (after Step 12 tests exist; preview-all must show `battle`).

### Step 10 — QML gallery, canvas, editor schema, preview spec

**Files:** `src/stream_cheremsha/qml/WidgetsView.qml`
**Target:** `layoutWidgetTypes`, `defaultWidgetSize`, `widgetMode` comment, `universalSchema`, `universalConfig`, `selectPreviewSpec`
**Purpose:** Creator flow: find → create → configure → preview Battle.
**Implementation (exact edits):**
- `layoutWidgetTypes` after battle_royale line: `{type: "battle", label: "Battle", iconName: "web_swords.svg"},`.
- `defaultWidgetSize`: after `case "battle_royale": return {w: 420, h: 280};` add `case "battle": return {w: 640, h: 220};` (battle bar is wide/short; 1920x480 scales down cleanly).
- L613 `widgetMode` comment: append `| battle` to the type union comment.
- `universalSchema`: add branch (place right after battle_royale `else if` block ends ~L766, before stream_pet):

```qml
        } else if (typeId === "battle") {
            var bt = function(key) { return root.loc("widgets.battle." + key); };
            general = [c(bt("battle_name"), "battle_name", "text", "BATTLE"), c(bt("best_of"), "best_of", "select", 3, {options: [1, 3, 5]}), c(bt("round_duration"), "round_duration_s", "number", 60, {minimum: 30, maximum: 300}), c(bt("countdown"), "countdown_s", "number", 5, {minimum: 1, maximum: 10}), c(bt("auto_start"), "auto_start", "toggle", true), c(bt("auto_threshold"), "auto_threshold_each", "number", 100, {minimum: 1, maximum: 10000}), c(bt("auto_window"), "auto_window_s", "number", 30, {minimum: 5, maximum: 120}), c(bt("auto_reset"), "auto_reset", "toggle", true)];
            appearance = [c(bt("theme"), "theme", "select", "cheremsha_neon", {options: ["cheremsha_neon", "cyber", "arcade", "minimal"]}), c(bt("layout_mode"), "layout_mode", "select", "normal", {options: ["normal", "compact"]}), c(bt("show_avatars"), "show_avatars", "toggle", true), c(bt("scale"), "scale_percent", "number", 100, {minimum: 40, maximum: 250}), c(bt("font_size"), "base_font_size_px", "number", 14, {minimum: 10, maximum: 32})];
            behavior = [c(bt("gift_multiplier"), "gift_multiplier", "number", 1.0, {minimum: 0.1, maximum: 10}), c(bt("combo_enabled"), "combo_enabled", "toggle", true), c(bt("combo_threshold"), "combo_threshold", "number", 5, {minimum: 2, maximum: 20}), c(bt("comeback_enabled"), "comeback_enabled", "toggle", true), c(bt("final_push"), "final_push_seconds", "number", 10, {minimum: 3, maximum: 30})];
            animation = [c(bt("event_animations"), "event_animations", "toggle", true), c(bt("animation_intensity"), "animation_intensity_pct", "number", 100, {minimum: 25, maximum: 200}), c(bt("show_badges"), "show_event_badges", "toggle", true), c(bt("show_winner"), "show_winner_screen", "toggle", true)];
            advanced = [c(bt("victory_display"), "victory_display_s", "number", 8, {minimum: 3, maximum: 15}), c(bt("hide_when_idle"), "hide_when_idle", "toggle", false), c(bt("font_family"), "font_family", "text", "Segoe UI"), c(bt("decision_layer"), "decision_layer_enabled", "toggle", false)];
```

  Note: schema field keys MUST equal Step 4 dataclass fields. The snippet above already uses exact names.
- Section titles: extend the three `typeId === "battle_royale" ? bl(…) :` ternaries (~L837–841) to also match `"battle"` with `bt(…)` labels (same section-key names: `section_general/desc_general/section_appearance/…` under `widgets.battle.*`).
- `universalConfig`: after `if (root.widgetMode === "battle_royale") return root.battleCfg;` add `if (root.widgetMode === "battle") return root.battleCfg2;` — Decision: reuse `battleCfg` property? BattleRoyale editor already owns `root.battleCfg`. To avoid QML property collision, add new `property var battleCfg2: null` next to `battleCfg` declaration + mirror its load/save wiring (find `battleCfg` assignments for royale and duplicate for battle with `loadBattleOverlayConfigMap/saveBattleOverlayConfigMap` renamed to battle variants + `battleRoyaleStartFromLeaders` untouched). Simpler alternative the executor MUST follow: instance-mode editor uses generic `loadWidgetInstanceSettingsJson/saveWidgetInstanceSettingsJson`, so `battleCfg2` is populated from instance JSON, not singleton. Document both paths in code comment.
- `selectPreviewSpec`: after `case "battle_royale": return {kind: "battle"};` add `case "battle": return {kind: "battle"};` (reuses `pvBattle`/`WidgetBattlePreview`, zero new components).

**Do:** Keep all edits additive; never rename royale branches.
**Do NOT:** Create new preview component; use `visible:false` for responsive collapse; add WebEngine imports.
**Verification:** `rg -n '"battle"|battleCfg2|previewBattle' src/stream_cheremsha/qml/WidgetsView.qml` → hits in all 6 targets. QML syntax check via existing styled-combobox test pattern (no QApplication run needed).

### Step 11 — Localization keys

**Files:** `src/stream_cheremsha/l10n.py`
**Target:** dict entries after `widgets.battle_royale.*` block (~L2880) and `widgets.type.battle_royale.*` (~L3013)
**Purpose:** Gallery + editor strings for both locales.
**Implementation:** Insert after royale preset line:

```python
    "widgets.type.battle.name": {"uk": "Battle", "en": "Battle"},
    "widgets.type.battle.desc": {"uk": "Битва 1v1: топ-2 GIFтери, раунди best-of.", "en": "1v1 battle: top-2 gifters, best-of rounds."},
```

and after `widgets.battle_royale.preset_minimal_brawl` block a `widgets.battle.*` group with EXACT keys used in Step 10 (`section_general/desc_general/section_appearance/desc_appearance/section_behavior/desc_behavior/section_advanced/desc_advanced/battle_name/best_of/round_duration/countdown/auto_start/auto_threshold/auto_window/auto_reset/theme/layout_mode/show_avatars/scale/font_size/gift_multiplier/combo_enabled/combo_threshold/comeback_enabled/final_push/event_animations/animation_intensity/show_badges/show_winner/victory_display/hide_when_idle/font_family/decision_layer`), each `{"uk": "…", "en": "…"}` (Ukrainian first, mirroring file style).

**Verification:** `python3 -c "from stream_cheremsha import l10n; print(l10n.tr('uk','widgets.type.battle.name'), '|', l10n.tr('en','widgets.battle.theme'))"` → `Battle | Theme`.

### Step 12 — Tests, regression, performance audit

**Files:** `tests/test_battle_engine.py`, `tests/test_battle_overlay_config.py`, `tests/test_battle_controller.py`, `tests/test_widgets_qml_api_battle_overlay.py` (all new)
**Target:** per Testing section; follow `tests/conftest.py` QSettings guard (never touch production `QSettings("stream-cheremsha","cheremsha")`; use `QSettings("stream-cheremsha-test", …)` + `s.clear()`).
**Purpose:** Pin every locked requirement + prove no regression + prove perf budget.
**Implementation:**
- Write the four files with the Given/When/Then tests listed under Testing (engine 14, config 3 groups/6 fns, controller 3, api 2 + preview-all reliance). Engine tests use injected `now=time.monotonic()` values, never sleep. Controller tests construct `BattleController(pubsub=OverlayPubSub(), get_locale=lambda: "uk", instance="t1", config_loader=lambda: defaults())`, call `on_gift` with `sender/count/tiktok_coin_each/sender_user_key`, subscribe `overlay:battle:t1` and `await asyncio.wait_for(q.get(), 2.0)`. API tests mirror `test_widgets_qml_api_battle_royale_overlay.py` structure (read it first, copy bodies, rename `battle_royale→battle`, snapshot keys per Step 9).
- Run order: `pytest tests/test_battle_engine.py tests/test_battle_overlay_config.py -q` → pass; then controller/api; then full regression set from Testing; then `ruff check src tests` + `ruff format --check` (or `ruff format .` if drift, then re-run tests).
- Performance audit (no code change unless violation): assert (a) `rg -n "QTimer|QWebEngine|requestAnimationFrame|setInterval.*publish|call_later.*0\.05" src/stream_cheremsha/overlays/battle_* src/stream_cheremsha/battle` → no new timers/loops (only MainWindow's existing 1s timer drives); (b) `rg -n "WebEngine" src/stream_cheremsha` → no new hits; (c) overlay HTML contains no `requestAnimationFrame`, no `setInterval` faster than 1000ms, no `filter: blur(` larger than 8px, no external URLs except local `/assets`; (d) `warm_secondary_pages`/lazy QML untouched (`pytest tests/test_settings_lazy_warm.py -q` passes); (e) burst test: 50 rapid `on_gift` → ≤6 published patches (debounce proof) and `len(controller snapshot events) ≤ 10`.
**Verification:** `pytest tests/test_battle_engine.py tests/test_battle_overlay_config.py tests/test_battle_controller.py tests/test_widgets_qml_api_battle_overlay.py tests/test_widget_instances.py tests/test_overlays_registry.py tests/test_widgets_preview_all_types.py tests/test_battle_royale_controller.py tests/test_widgets_qml_api_battle_royale_overlay.py tests/test_overlays_server_integration.py tests/test_pubsub_instance_routing.py -q` → all pass. `ruff check src tests` → clean.
