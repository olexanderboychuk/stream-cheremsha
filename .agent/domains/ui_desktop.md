# DOMAIN: Desktop UI & Application Shell

## Subsystem Responsibility
Owns the desktop GUI lifecycle, main application window (`MainWindow`), sidebar navigation, `QStackedWidget` tab management, lazy-loading of secondary pages, splash screen warming sequence, QML bridge APIs, and native system tray.

## Important Concepts
- **QStackedWidget Indexing**: 11 tabs with fixed indices (`_IX_CHAT=0`, `_IX_SETTINGS=1`, `_IX_WIDGETS=2`, `_IX_ACTIONS=3`, `_IX_LAYOUTS=4`, etc.).
- **Lazy Load + Splash Warm**: Secondary tabs are initialized with inert placeholders at startup; real widgets are instantiated in the background during splash (`warm_secondary_pages`) or synchronously on first navigation (`_set_main_page`).
- **QML Integration**: QML views (`WidgetsView.qml`, `UniversalWidgetEditor.qml`) communicate with Python via `widgets_qml_api.py`.
- **Localization**: All UI labels use `l10n.tr("key")` and handle dynamic language switching via `_retranslate_ui()`.

## Important Files & Canonical Locations
- `src/stream_cheremsha/ui/main_window.py`: Core application window, tab coordination, and event fan-out (~7,500 lines; inspect only target methods).
- `src/stream_cheremsha/ui/widgets_qml_api.py`: PySide6 QObject bridge exposing widget CRUD, configs, and previews to QML.
- `src/stream_cheremsha/qml/WidgetsView.qml`: QML widget gallery, editor host, and layout canvas.
- `src/stream_cheremsha/l10n.py`: Multi-language dictionary (`uk`, `en`) and `tr()` lookup helper.

## Important Symbols
- `MainWindow`: Main application coordinator.
  - `_build_ui()`: Creates the shell and adds placeholders to `_stack`.
  - `_set_main_page(index)`: Navigates tabs; ensures real widget exists.
  - `warm_secondary_pages(status_cb)`: Background warming during splash.
  - `_ensure_*_widgets()`: Idempotent builders for lazy tabs.
- `WidgetsQmlApi`:
  - `load*ConfigJson(instance_id)` / `save*ConfigJson(instance_id, json_str)`
  - `preview*Overlay(instance_id)`: Dispatches live previews to WebSocket PubSub.

## Relationships with Other Domains
- **Overlays**: Manages `InstanceControllerGroup` and passes tick/gift events to overlay controllers.
- **Config & Keyring**: Populates fields in Settings tab via `keyring_store.py`.
- **TTS & Chat**: Displays live chat stream and audio controls in `ChatView`.

## Common Extension Points
1. **Adding a New Tab**:
   - Assign next index `_IX_NEW_TAB = N` in `main_window.py`.
   - Add placeholder `QWidget` in `_build_ui()`.
   - Implement idempotent `_ensure_new_tab_widgets() -> QWidget`.
   - Add first-open branch in `_set_main_page()`.
   - Append to `order` tuple in `warm_secondary_pages()` with l10n key.
2. **Connecting a New Widget to QML**:
   - Add config loader/saver and preview methods in `widgets_qml_api.py`.
   - Register editor and preview branches in `WidgetsView.qml`.

## Relevant Invariants
- Navigation highlight must update before invoking tab build (`Navigation-First`).
- Swapping placeholder with real widget must use remove-first/insert pattern.
- No blocking operations or heavy keyring reads during `_build_ui()`.

## Architectural Decisions
- See [.agent/decisions/ui_lazy_loading.md](file:///home/oleksandrboichuk/Dev/Self/stream-cheremsha/.agent/decisions/ui_lazy_loading.md)
