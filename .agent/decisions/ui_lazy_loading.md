# Architectural Decision: UI Tab Lazy Loading & Splash Warm

## Context & Problem
`MainWindow` in `src/stream_cheremsha/ui/main_window.py` manages 11 tabs in a `QStackedWidget`. Historically, eager UI construction during startup instantiated every tab, reading credentials from the OS keyring and constructing heavy QML/QWidget trees on the main thread. This blocked the first paint and caused slow startup.

## Decision & Invariant Architecture
1. **Placeholder Pattern at Startup**:
   - `_build_ui()` MUST NOT eagerly construct secondary tabs (Settings, Widgets, Actions, Layouts, Donations, Docks).
   - Instead, it appends a lightweight placeholder `QWidget` to `_stack` so that stack indices (`_IX_CHAT = 0`, `_IX_SETTINGS = 1`, `_IX_WIDGETS = 2`, etc.) remain stable and immutable.
2. **Double-Path Ensuring**:
   - **Splash Warm Path (`warm_secondary_pages`)**: When the splash screen is visible, tabs are warmed sequentially in priority order with `await asyncio.sleep(0)` yields to keep the splash responsive.
   - **First-Open Fallback Path (`_set_main_page`)**: If the user navigates to a tab before warm-up completes (or if warm was skipped), `_set_main_page()` immediately builds the page synchronously via its dedicated `_ensure_*_widgets()` method.
3. **Placeholder-to-Real Swap Invariant**:
   - When replacing a placeholder with the real page in `QStackedWidget`, the swap MUST use the remove-first/insert pattern (remove placeholder, insert real page at target index) to preserve `currentIndex` and active navigation highlights.
4. **Navigation-First Rule**:
   - In `_set_main_page(index)`, the sidebar highlight and `_stack.setCurrentIndex(index)` MUST occur FIRST before invoking any heavy widget ensure/build logic. If building raises an exception, the user is not stuck in a broken navigation state.
5. **Keyring Isolation**:
   - Keyring reads for populating fields (e.g. `_load_settings_fields()`) must only run inside the ensure/warm path with an idempotent flag (`_settings_fields_loaded`). Never call keyring reads in eager constructor paths.

## What Must Never Happen
- DO NOT eagerly call heavy tab constructors (`_build_settings_tab()`, `_load_qml_page()`) inside `_build_ui()`.
- DO NOT modify stack index constants without updating every reference across `main_window.py`.
- DO NOT mix QWidget lazy state with QML lazy sets (`_qml_pages_loaded`).
