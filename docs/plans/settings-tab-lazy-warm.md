# Settings Tab Lazy Load + Splash Warm Implementation Plan

**Goal:** Build the Settings tab lazily (placeholder at startup) and pre-build it during the splash warm-up phase, matching the existing QML-tab lazy + warm pattern.
**Tech stack:** Python, PySide6 (QWidget/QStackedWidget), qasync/asyncio, QSettings + OS keyring.
**Existing behavior:** `_build_ui()` eagerly calls `_build_settings_tab()` at `_IX_SETTINGS=1`; `_load_settings_fields()` (~10 keyring reads) runs post-show via `_post_show_startup_ui`; `warm_secondary_pages()` warms only Widgets → Actions → Layouts → Donations → Docks.
**Locked requirements:**
1. `_build_ui()` must NOT call `_build_settings_tab()`; a lightweight placeholder `QWidget` occupies `_IX_SETTINGS` so stack indices 0–10 are unchanged.
2. New `_ensure_settings_widgets() -> QWidget` builds the real page exactly once via `_build_settings_tab()`, swaps placeholder→real preserving current index/widget (same remove-first/insert pattern as `_ensure_actions_widgets`), then populates fields via `_load_settings_fields()` once (idempotent flag).
3. `warm_secondary_pages()` warms Settings LAST after Docks (smallest diff), with per-page `try/except` + `await asyncio.sleep(0)` yields, reporting `splash.settings` status.
4. First navigation to `_IX_SETTINGS` in `_set_main_page()` builds synchronously inline (no loading veil, no deferred timer).
5. `_load_settings_fields()` moves into the ensure/warm path only; `_post_show_startup_ui()` no longer calls it (keeps only connection-panel refresh).
6. `_apply_settings_tab_texts()` and `_load_settings_fields()` early-return when Settings is not built yet; `_retranslate_ui()` stays safe pre-build.
7. New l10n keys `splash.settings` (`uk` + `en`).
8. No change to Settings content, persist slots, search filter, nav categories, or any other tab.
**Out of scope:** Lazy-loading chat/audio/music QWidget tabs; adding a loading veil for Settings; splash time budgets; refactoring `_build_settings_tab()` internals; changing persist/keyring logic.
**Plan path / date:** `docs/plans/settings-tab-lazy-warm.md` / 2026-09-24.

## Context
User request, quoted verbatim: "make settings tab lazy loaded and warm during splash screen like other tabs". QML tabs already defer `_load_qml_page()` to first open with splash pre-warm; Settings (QWidget) is still eager and blocks first paint.

## Decisions
| # | Decision | Reasoning | What-if-changed |
|---|----------|-----------|-----------------|
| D1 | Warm Settings LAST (after Docks), per user pick 1C smallest-diff | Appends one tuple entry; no reorder risk to current splash timing | If moved early, splash status order and time-to-first-warmed-page change; plan steps 3–4 order text must change |
| D2 | First-open builds synchronously inline (user pick 2A), no veil | `_build_settings_tab()` is synchronous QWidget code; veil+defer adds complexity with no benefit since warm covers the common path | If veil wanted, add `_pending_settings_token` + `_show_qml_loading_veil` path mirroring `_ensure_qml_page_visible` |
| D3 | Move `_load_settings_fields()` into ensure/warm path (user pick 3A); `_post_show_startup_ui` drops its direct call | Populated values ride with the build; avoids empty-field flash and duplicate keyring reads | If kept post-show, warmed page could show empty fields until post-show timer fires; would need a second populate call |
| D4 | Separate `_settings_fields_loaded` flag; do NOT reuse `_qml_pages_loaded` or `_QML_STACK_INDICES` | Settings is QWidget, not QML; mixing sets would make `_ensure_qml_page_visible` treat it as QML and misroute | If added to QML set, `_qml_widget_for_stack_index(1)` returns None and warm/first-open breaks |
| D5 | Placeholder swap mirrors `_ensure_actions_widgets` remove-first/insert pattern exactly | Proven pattern preserves `currentIndex`/`currentWidget` when the visible page is replaced | Any other swap (e.g. insert-then-remove) shifts currentIndex onto the neighbour tab |

## Files To Modify
| Path | Target (class/fn) | What changes | Why | What stays unchanged |
|------|-------------------|--------------|-----|----------------------|
| `src/stream_cheremsha/ui/main_window.py` | `MainWindow.__init__` (~L1289–1300) | Add `_settings_page: QWidget \| None = None`, `_settings_placeholder: QWidget \| None`, `_settings_fields_loaded: bool = False` next to `_qml_actions` lazy state | Track lazy Settings instance without touching QML state | All existing field shells, `_qml_*` inits, `_qml_pages_loaded` set |
| `src/stream_cheremsha/ui/main_window.py` | `MainWindow._build_ui` (~L1783–1793) | Replace `self._stack.addWidget(self._build_settings_tab())` with placeholder `QWidget`; store as `_settings_placeholder`; add comment | Defer heavy build off first-paint path; keep `_IX_SETTINGS=1` stable | Stack order/count (11 pages), all other `addWidget` lines, veil setup |
| `src/stream_cheremsha/ui/main_window.py` | `MainWindow._ensure_settings_widgets` (new, place directly after `_ensure_actions_widgets` ~L2195) | Build-once + placeholder swap + `_load_settings_fields()` once; return real page | Single choke point for warm + first-open + post-show safety | `_ensure_actions_widgets`, `_qml_widget_for_stack_index` (no Settings entry added) |
| `src/stream_cheremsha/ui/main_window.py` | `MainWindow._set_main_page` (~L2288–2307) | After `setCurrentIndex`, if `index == self._IX_SETTINGS`: call `self._ensure_settings_widgets()` in `try/except` (log `debug` on failure) | Synchronous first-open fallback when warm didn't run/failed | Nav-first ordering, audio-device branch, `_ensure_qml_page_visible` call |
| `src/stream_cheremsha/ui/main_window.py` | `MainWindow.warm_secondary_pages` (~L2386–2438) | Append `(self._IX_SETTINGS, "splash.settings")` LAST to `order`; extend docstring priority sentence; add `elif qml_index == self._IX_SETTINGS: self._ensure_settings_widgets()` branch inside the `try` (do NOT call `_load_qml_page` for it) | Warm Settings behind splash with status text; per-page failure isolation already handles fallback | Existing 5 entries + order, yields, status_cb protocol, overlay-server separation |
| `src/stream_cheremsha/ui/main_window.py` | `MainWindow._apply_settings_tab_texts` (~L4014) | Early-return guard when Settings not built | `_retranslate_ui` runs pre-build at startup/locale change | All `setText`/`setTitle` lines when built |
| `src/stream_cheremsha/ui/main_window.py` | `MainWindow._post_show_startup_ui` (~L4159–4167) | Remove direct `self._load_settings_fields()` call + its try/except; keep `_refresh_connection_panels_after_show()` | Field loads now ride with ensure/warm (Req 5) | Method still exists; connection refresh untouched |
| `src/stream_cheremsha/ui/main_window.py` | `MainWindow._load_settings_fields` (~L5391) | Early-return guard when Settings not built; docstring notes idempotent + called once from `_ensure_settings_widgets` | Safe if called pre-build; documents single-caller contract | All field-population logic |
| `src/stream_cheremsha/l10n.py` | splash dict (~L3426–3427) | Add `"splash.settings": {"uk": "Завантаження налаштувань…", "en": "Loading settings…"}` | Status text for new warm step | All other keys/translations |

## Files To Create
| Path | Responsibility | Interface | Dependencies | Integration point |
|------|---------------|-----------|--------------|-------------------|
| `tests/test_settings_lazy_warm.py` | Regression: l10n key + static source-structure (placeholder, ensure-once, warm-last, guards, no eager build, no QML-set pollution) without instantiating `MainWindow` (no QApplication needed) | 7 test functions (see Testing) importing `pathlib` + `stream_cheremsha.l10n` only | `tests/conftest.py` QSettings guard (must NOT construct production scope) | `pytest tests/test_settings_lazy_warm.py` |

## Data / State Changes
- New state on `MainWindow` (all in-memory, none persisted, no cleanup beyond existing window teardown):
  - `_settings_page: QWidget | None` — real page once built, kept alive forever (never unloaded, same as QML cache).
  - `_settings_placeholder: QWidget | None` — placeholder until swapped, then set to `None` (deleted via `deleteLater`, same as actions placeholder).
  - `_settings_fields_loaded: bool` — `False` → `True` after first `_load_settings_fields()` inside ensure; guards duplicate keyring reads.
- State transitions:
| State | Trigger | Preconditions | Effect | Invalid -> |
|-------|---------|---------------|--------|------------|
| placeholder | `_build_ui` | `_stack` exists | `_IX_SETTINGS` holds inert `QWidget` | never rebuild placeholder |
| building | `_ensure_settings_widgets` (warm or first-open) | `_settings_page is None`, not `_closing` | `_build_settings_tab()` + swap + `_load_settings_fields()` + flag `True` | concurrent re-entry returns existing/partial once (single-threaded Qt; warm and nav can't interleave mid-call) |
| ready | build done | placeholder removed, page at index 1 | opens instantly | never unload; never rebuild |
| failed | exception in build | any | log + keep placeholder; retry on next warm/first-open | must NOT mark `_settings_fields_loaded`, must NOT cache partial page |

## Data / Control Flow
```
Splash visible (app/main.py _start_main_window)
 -> MainWindow() constructs: _build_ui inserts SETTINGS PLACEHOLDER (no _build_settings_tab, no keyring)
 -> window.show() behind splash
 -> _warm_and_reveal: warm_overlay_server() [unchanged]
 -> warm_secondary_pages(status_cb): Widgets -> Actions -> Layouts -> Donations -> Docks -> SETTINGS(LAST)
      -> status_cb("Loading settings…") -> await asyncio.sleep(0) [splash paints]
      -> _ensure_settings_widgets(): _build_settings_tab() + stack swap + _load_settings_fields() [blocking, cached]
      -> await asyncio.sleep(0) [splash repaints]
 -> splash.close(); run_startup() [unchanged; skips overlay block as before]
 -> _post_show_startup_ui: connection panels only (no settings fields work)
First-open fallback (warm skipped/failed):
 sidebar Settings click -> _set_main_page(_IX_SETTINGS): setCurrentIndex(1) FIRST
      -> _ensure_settings_widgets() synchronously -> page visible already populated
Locale change pre-build: _on_locale_changed -> _retranslate_ui -> _apply_settings_tab_texts no-ops (guard)
Locale change post-build: texts apply normally; future builds use current locale via _tr
```

## Edge Cases
| Case | Behavior | Handler | User-visible outcome |
|------|----------|---------|----------------------|
| Warm build raises | Caught by per-page `except` in `warm_secondary_pages`; placeholder kept | `warm_secondary_pages` (existing `logger.exception` line) | Splash continues; first-open retries synchronously |
| First-open build raises | Caught in `_set_main_page`; placeholder stays visible | `_set_main_page` new try/except (`logger.debug`) | Empty placeholder page instead of crash; retry on next click |
| `_closing` True during warm | `warm_secondary_pages` loop checks `self._closing` before each page (existing) | existing guard | No build attempted on shutdown path |
| Locale changed before first build | `_apply_settings_tab_texts` no-ops; `_build_settings_tab` later reads current locale | new guard | No crash; built page uses current language |
| `_load_settings_fields` called pre-build | Early-returns; fields populate on ensure | new guard | No `AttributeError` on missing widgets |
| Rapid double-click Settings pre-build | Second `_ensure_settings_widgets` sees `_settings_page is not None`, returns cached | idempotent ensure | One build, second open instant |
| `run_startup` / tunnel / autostart reads settings | Unaffected: they read `QSettings`/keyring directly, never widget state | — | No behavior change |

## Error Handling
- Warm failure: existing per-page `try/except Exception → logger.exception("QML warm-up failed for page %s")` covers the new Settings branch identically; warm continues to next page (none after, then reveal). No splash abort.
- First-open failure: new `try/except (RuntimeError, AttributeError, OSError, Exception)` around `_ensure_settings_widgets()` in `_set_main_page`, `logger.debug("Lazy settings build failed", exc_info=True)`; navigation highlight already moved (nav-first invariant preserved).
- Post-show: no settings work remains, so no new failure path there.
- L10n missing key: `tr()` falls back to key string (existing `l10n.tr` behavior); test pins both locales non-empty.

## Testing
New file `tests/test_settings_lazy_warm.py` (no QApplication; source-structure + l10n only, following `test_production_qsettings_guard.py` static-tripwire style and `test_l10n.py` key style):

```
Test: test_splash_settings_l10n_both_locales
Given: l10n module imported
When:  tr("uk"/"en", "splash.settings")
Then:  both non-empty; uk contains "налаштувань", en contains "Settings"
```
```
Test: test_settings_not_built_eagerly_in_build_ui
Given: main_window.py source text
When:  scanning _build_ui stack sequence
Then:  contains "_settings_placeholder" addWidget at settings slot; no "addWidget(self._build_settings_tab())" call
```
```
Test: test_ensure_settings_builds_once_and_loads_fields
Given: source of _ensure_settings_widgets
When:  inspected
Then:  early-returns cached `_settings_page`; calls `_build_settings_tab()` once; calls `_load_settings_fields()` guarded by `_settings_fields_loaded`; swaps placeholder with remove-first/insertWidget(_IX_SETTINGS) + deleteLater + currentWidget restore
```
```
Test: test_warm_secondary_pages_includes_settings_last
Given: source of warm_secondary_pages
When:  inspected
Then:  order tuple ends with (self._IX_SETTINGS, "splash.settings"); branch calls _ensure_settings_widgets (not _load_qml_page) for _IX_SETTINGS
```
```
Test: test_set_main_page_ensures_settings_synchronously
Given: source of _set_main_page
When:  inspected
Then:  contains "if index == self._IX_SETTINGS:" + "_ensure_settings_widgets()" with no "singleShot"/"veil" in that branch
```
```
Test: test_settings_texts_and_fields_guarded_prebuild
Given: sources of _apply_settings_tab_texts + _load_settings_fields
When:  inspected
Then:  both early-return when settings page/placeholder state indicates unbuilt (getattr(_settings_page, None) is None)
```
```
Test: test_settings_excluded_from_qml_indices
Given: source
When:  inspected
Then:  _QML_STACK_INDICES has no _IX_SETTINGS; _qml_pages_loaded never assigned _IX_SETTINGS
```
- Run: `pytest tests/test_settings_lazy_warm.py tests/test_l10n.py -q` (expected: all pass).
- Lint: `ruff check src/stream_cheremsha/ui/main_window.py src/stream_cheremsha/l10n.py tests/test_settings_lazy_warm.py` (expected: clean).
- Manual (optional, needs display): `QT_QPA_PLATFORM=offscreen` cannot validate QML warm; on a dev machine run app, confirm splash shows "Loading settings…" last and Settings opens instantly with populated fields.

## Configuration / Deployment
None. No config keys, env vars, flags, or migrations. QSettings/keyring keys unchanged.

## Compatibility
- Existing user settings/QSettings/keyring data untouched; populate logic byte-identical, only timing moves (splash-warm/first-open vs post-show timer).
- Platforms: no OS-specific path; placeholder swap is pure Qt Widgets (same as Actions placeholder on all OSes).
- What breaks: code that assumed settings widgets exist immediately after `MainWindow()` construction (e.g. direct `window._combo_locale` access in scripts/tests) will now find them missing until warm/first-open — accepted: internal callers are guarded in this plan; external automation must open/warm Settings first.

## Acceptance Criteria
- When the app starts, `_build_settings_tab()` is not called during `_build_ui`; `_stack` index 1 holds the placeholder.
- When splash warms, status shows the settings string last and the real Settings page (populated) exists before `splash.close()`.
- When Settings is clicked before/failed warm, the real page builds synchronously and shows populated values with no crash.
- When locale changes before first build, no exception; built page uses the current locale.
- When warm/first-open build fails, placeholder remains, error is logged, next open retries.
- `_QML_STACK_INDICES` and QML warm/veil behavior for other tabs remain unchanged.
- `pytest tests/test_settings_lazy_warm.py tests/test_l10n.py -q` passes; `ruff check` on touched files is clean.

## Implementation Steps
### Step 1 — Add `splash.settings` l10n keys
**Files:** `src/stream_cheremsha/l10n.py`
**Target:** splash dict (~L3426–3427)
**Purpose:** Status text for the new last warm step (Req 7).
**Implementation:** Insert after the `splash.docks` entry, keeping alphabetical-ish splash.* grouping and exact dict style:
```python
    "splash.docks": {"uk": "Завантаження доків…", "en": "Loading docks…"},
    "splash.settings": {"uk": "Завантаження налаштувань…", "en": "Loading settings…"},
    "splash.overlay": {"uk": "Запуск оверлей-сервера…", "en": "Starting overlay server…"},
```
**Inputs / Outputs:** In: locale code; Out: localized warm status string.
**State:** None.
**Side effects:** None.
**Error handling:** None (static dict).
**Dependencies:** None.
**Do:** Match existing `"key": {"uk": ..., "en": ...}` formatting exactly.
**Do NOT:** Rename existing splash keys or touch overlay keys.
**Verification:** `python3 -c "from stream_cheremsha import l10n; print(l10n.tr('uk','splash.settings')); print(l10n.tr('en','splash.settings'))"` → prints `Завантаження налаштувань…` and `Loading settings…`.

### Step 2 — Add lazy Settings state in `__init__`
**Files:** `src/stream_cheremsha/ui/main_window.py`
**Target:** `MainWindow.__init__` lazy-tab state block (~L1289–1300)
**Purpose:** Track placeholder/real page + one-shot field load (Req 2).
**Implementation:** Directly after the `_qml_actions: QQuickWidget | None = None` line, insert:
```python
        # Settings tab is lazy like the heavy QML tabs: a placeholder keeps
        # _IX_SETTINGS stable; the real page is built on first open or
        # splash warm-up (see _ensure_settings_widgets), never in _build_ui.
        self._settings_page: QWidget | None = None
        self._settings_placeholder: QWidget | None = None
        self._settings_fields_loaded: bool = False
```
**Inputs / Outputs:** None.
**State:** New `None/None/False` initial state.
**Side effects:** None.
**Error handling:** None.
**Dependencies:** Step 1 (unrelated, any order OK but keep numeric order).
**Do:** Place with the other lazy-tab attrs so future readers find it.
**Do NOT:** Touch `_qml_pages_loaded`, `_QML_STACK_INDICES`, or field-shell (`_obs_ws_host`, …) creation.
**Verification:** `rg -n "_settings_placeholder|_settings_page|_settings_fields_loaded" src/stream_cheremsha/ui/main_window.py` → 3+ hits in `__init__` plus later steps.

### Step 3 — Placeholder in `_build_ui`, stop eager build
**Files:** `src/stream_cheremsha/ui/main_window.py`
**Target:** `MainWindow._build_ui` stack assembly (~L1783–1793)
**Purpose:** Remove heavy build from first-paint path; keep index stability (Req 1).
**Implementation:** Replace exactly:
```python
        self._stack.addWidget(self._qml_conn)
        self._stack.addWidget(self._build_settings_tab())
```
with:
```python
        self._stack.addWidget(self._qml_conn)
        # Lazy Settings: placeholder keeps _IX_SETTINGS stable; real page via
        # _ensure_settings_widgets() on first open / splash warm-up.
        self._settings_placeholder = QWidget(self)
        self._stack.addWidget(self._settings_placeholder)
```
**Inputs / Outputs:** Stack count/order unchanged (11 widgets, Settings still index 1).
**State:** `_settings_placeholder` set; `_settings_page` stays None.
**Side effects:** Settings UI absent until ensure runs (intended).
**Error handling:** None.
**Dependencies:** Step 2 (attrs must exist).
**Do:** Keep surrounding `addWidget` lines byte-identical.
**Do NOT:** Call `_build_settings_tab()`, `_apply_settings_tab_texts()`, or `_load_settings_fields()` here.
**Verification:** `rg -n "build_settings_tab\(\)" src/stream_cheremsha/ui/main_window.py` → hits only inside `_ensure_settings_widgets` (Step 4), NOT in `_build_ui`.

### Step 4 — Add `_ensure_settings_widgets()` after `_ensure_actions_widgets`
**Files:** `src/stream_cheremsha/ui/main_window.py`
**Target:** new `MainWindow._ensure_settings_widgets` inserted between `_ensure_actions_widgets` (ends ~L2194) and `_qml_widget_for_stack_index` (~L2196)
**Purpose:** Single build-once choke point for warm + first-open (Req 2, D5).
**Implementation:**
```python
    def _ensure_settings_widgets(self) -> QWidget:
        """Lazily build the Settings page (first open / splash warm-up only)."""
        if self._settings_page is not None:
            return self._settings_page
        page = self._build_settings_tab()
        placeholder = getattr(self, "_settings_placeholder", None)
        if placeholder is not None and hasattr(self, "_stack"):
            idx = self._stack.indexOf(placeholder)
            if idx == self._IX_SETTINGS:
                # Remove first, then insert: insert-then-remove shifts
                # currentIndex onto the neighbour tab. Restore explicitly.
                showing_placeholder = self._stack.currentIndex() == idx
                current_widget = self._stack.currentWidget()
                self._stack.removeWidget(placeholder)
                placeholder.setParent(None)
                placeholder.deleteLater()
                self._stack.insertWidget(self._IX_SETTINGS, page)
                if showing_placeholder:
                    self._stack.setCurrentIndex(self._IX_SETTINGS)
                elif current_widget is not None:
                    self._stack.setCurrentWidget(current_widget)
                self._settings_placeholder = None
            else:
                self._stack.addWidget(page)
        self._settings_page = page
        if not self._settings_fields_loaded:
            try:
                self._load_settings_fields()
            except (RuntimeError, AttributeError, OSError):
                logger.debug("Lazy settings fields load failed", exc_info=True)
            else:
                self._settings_fields_loaded = True
        return page
```
**Inputs / Outputs:** In: none; Out: real Settings `QWidget`.
**State:** Sets `_settings_page`; clears `_settings_placeholder`; flips `_settings_fields_loaded` only on success (retry on failure per Edge table).
**Side effects:** `_build_settings_tab()` runs once; `_load_settings_fields()` keyring reads run once here (Req 5).
**Error handling:** Field-load failure logged at `debug`, flag stays `False` so next ensure retries; build exceptions propagate to caller (warm/first-open handlers catch).
**Dependencies:** Steps 2–3.
**Do:** Mirror `_ensure_actions_widgets` swap lines exactly (remove-first pattern).
**Do NOT:** Add Settings to `_qml_pages_loaded`; do NOT call `_load_qml_page`; do NOT show any veil.
**Verification:** `python3 -c "import ast; t=ast.parse(open('src/stream_cheremsha/ui/main_window.py').read()); f=[n.name for n in ast.walk(t) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]; assert '_ensure_settings_widgets' in f; print('ok')"` → `ok`.

### Step 5 — Synchronous ensure on first navigation
**Files:** `src/stream_cheremsha/ui/main_window.py`
**Target:** `MainWindow._set_main_page` (~L2288–2307)
**Purpose:** First-open fallback when warm skipped/failed (Req 4, pick 2A).
**Implementation:** After the `setCurrentIndex` block and BEFORE the audio-device branch, insert:
```python
        # Settings is a lazy QWidget tab (not QML): build it synchronously
        # on first open so the already-visible index shows real content.
        if index == self._IX_SETTINGS:
            try:
                self._ensure_settings_widgets()
            except Exception:
                logger.debug("Lazy settings build failed", exc_info=True)
```
**Inputs / Outputs:** In: stack index; Out: none (page swapped in place).
**State:** Triggers Step 4 transition placeholder→ready on first nav.
**Side effects:** One-time synchronous build cost on first Settings open only if warm missed.
**Error handling:** All exceptions caught; placeholder remains visible; retry next click.
**Dependencies:** Step 4.
**Do:** Keep nav-first (`setCurrentIndex` before ensure) invariant.
**Do NOT:** Add veil/`singleShot`/token logic; do NOT touch the audio or QML branches.
**Verification:** `rg -n -A3 "index == self._IX_SETTINGS" src/stream_cheremsha/ui/main_window.py` → shows `_ensure_settings_widgets()` call inside `_set_main_page` with no `singleShot` nearby.

### Step 6 — Warm Settings LAST in `warm_secondary_pages`
**Files:** `src/stream_cheremsha/ui/main_window.py`
**Target:** `MainWindow.warm_secondary_pages` (~L2386–2438)
**Purpose:** Pre-build Settings behind splash (Req 3, pick 1C).
**Implementation:** (a) Update docstring first sentence from "Priority order is Widgets, then Actions … and Docks." to "Priority order is Widgets, then Actions …, Layouts, Donations, Docks, and Settings last.". (b) Append to `order`:
```python
        order = (
            (self._IX_WIDGETS, "splash.widgets"),
            (self._IX_ACTIONS, "splash.actions"),
            (self._IX_LAYOUTS, "splash.layouts"),
            (self._IX_DONATIONS, "splash.donations"),
            (self._IX_DOCKS, "splash.docks"),
            (self._IX_SETTINGS, "splash.settings"),
        )
```
(c) Inside the loop's `try:` replace `self._load_qml_page(qml_index)` with:
```python
                if qml_index == self._IX_SETTINGS:
                    self._ensure_settings_widgets()
                else:
                    self._load_qml_page(qml_index)
```
Keep surrounding `await asyncio.sleep(0)` yields and `except Exception: logger.exception(...)` untouched.
**Inputs / Outputs:** Same `status_cb(text, progress)` protocol; `total` becomes 6 so progress fractions shift (intended).
**State:** Placeholder→ready before `splash.close()` in the common path.
**Side effects:** One blocking QWidget build during splash (same class of cost as each QML compile, amortized behind splash).
**Error handling:** Existing per-page isolation: failure logs and falls back to Step 5 lazy open.
**Dependencies:** Steps 4–5.
**Do:** Branch on `_IX_SETTINGS`; never pass it to `_load_qml_page`.
**Do NOT:** Reorder the existing five entries; do NOT add `_IX_SETTINGS` to `_QML_STACK_INDICES`.
**Verification:** `rg -n "splash.settings|_IX_SETTINGS, \"splash" src/stream_cheremsha/ui/main_window.py src/stream_cheremsha/l10n.py` → hits in `l10n.py` dict + `warm_secondary_pages` order tuple.

### Step 7 — Guards + drop post-show settings load
**Files:** `src/stream_cheremsha/ui/main_window.py`
**Target:** `_apply_settings_tab_texts` (~L4014), `_load_settings_fields` (~L5391), `_post_show_startup_ui` (~L4159–4167)
**Purpose:** Pre-build safety + single field-load owner (Req 5–6).
**Implementation:** (a) First line of `_apply_settings_tab_texts`:
```python
        if getattr(self, "_settings_page", None) is None:
            return
```
(b) First line of `_load_settings_fields` (+ docstring note):
```python
        """Populate settings widgets from QSettings/keyring (once, via _ensure_settings_widgets)."""
        if getattr(self, "_settings_page", None) is None:
            return
```
(c) In `_post_show_startup_ui`, delete:
```python
        try:
            self._load_settings_fields()
        except (RuntimeError, AttributeError, OSError):
            logger.debug("Deferred settings fields load failed", exc_info=True)
```
keeping `self._refresh_connection_panels_after_show()`. Update its docstring from "(secondary pages; never blocks first paint)" to "(connection panels; never blocks first paint — settings loads with its lazy build)".
**Inputs / Outputs:** No signature changes.
**State:** Guards keyed on `_settings_page is None`.
**Side effects:** None when built; no-op when unbuilt.
**Error handling:** Unchanged elsewhere.
**Dependencies:** Steps 2–4 (state + ensure exist).
**Do:** Use `getattr(..., None)` (not `hasattr` + direct access) so partially-constructed windows can't raise.
**Do NOT:** Guard `_retranslate_ui` separately (callee guard suffices); do NOT delete `_refresh_connection_panels_after_show`.
**Verification:** `rg -n "_load_settings_fields\(\)" src/stream_cheremsha/ui/main_window.py` → exactly ONE call site (inside `_ensure_settings_widgets`); `rg -n "Deferred settings fields load failed" src/stream_cheremsha/ui/main_window.py` → zero hits.

### Step 8 — Add regression tests + run suite
**Files:** `tests/test_settings_lazy_warm.py` (new), plus commands
**Target:** 7 tests listed in Testing section
**Purpose:** Pin every locked requirement without a QApplication.
**Implementation:** Create the file with l10n test + six AST/source-structure tests; follow `test_production_qsettings_guard.py` file-reading style; NEVER construct `QSettings("stream-cheremsha", "cheremsha")` (guard tripwire). Skeleton:
```python
"""Settings lazy + splash-warm regression (no QApplication)."""
from __future__ import annotations
import pathlib
from stream_cheremsha import l10n

MW = pathlib.Path(__file__).resolve().parents[1] / "src" / "stream_cheremsha" / "ui" / "main_window.py"

def _src() -> str:
    return MW.read_text(encoding="utf-8")

def test_splash_settings_l10n_both_locales() -> None:
    uk = l10n.tr("uk", "splash.settings"); en = l10n.tr("en", "splash.settings")
    assert uk.strip() and en.strip()
    assert "налаштувань" in uk.lower(); assert "settings" in en.lower()

def test_settings_not_built_eagerly_in_build_ui() -> None: ...
def test_ensure_settings_builds_once_and_loads_fields() -> None: ...
def test_warm_secondary_pages_includes_settings_last() -> None: ...
def test_set_main_page_ensures_settings_synchronously() -> None: ...
def test_settings_texts_and_fields_guarded_prebuild() -> None: ...
def test_settings_excluded_from_qml_indices() -> None: ...
```
(each `...` asserts the exact strings from Steps 3–7).
**Dependencies:** Steps 1–7 implemented.
**Do:** Keep tests display-free (source text + l10n only).
**Do NOT:** Instantiate `MainWindow`/`QApplication` in tests.
**Verification:** `pytest tests/test_settings_lazy_warm.py tests/test_l10n.py -q` → all pass; `ruff check src/stream_cheremsha/ui/main_window.py src/stream_cheremsha/l10n.py tests/test_settings_lazy_warm.py` → clean.
