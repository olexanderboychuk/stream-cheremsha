# DOMAIN: Overlays & Browser Source Widgets

## Subsystem Responsibility
Serves web-based widgets and OBS browser source overlays via an internal `aiohttp` web server (default port `17171`), manages widget instance lifecycles, and broadcasts real-time events over a WebSocket PubSub bus.

## Important Concepts
- **Overlay Type vs Widget Instance**: An `OverlayType` defines the HTML template and default parameters. A `WidgetInstance` is a user-created entity with a unique UUID, display name, and custom `settings` stored in `QSettings`.
- **InstanceControllerGroup**: Manages instances of a given widget type (`battle`, `live_leaderboard_simple`, etc.), ensuring isolated state, per-instance config, and topic routing.
- **WebSocket PubSub Bus**: Clients subscribe to `/ws?topic=overlay:{type}:{instance_id}`. Controllers broadcast state JSON to this topic.
- **URL Schema**: OBS loads `/overlay/by-id/{id}`. The server resolves the instance ID, reads its type from `widget_instances.py`, and renders the corresponding HTML template.

## Important Files & Canonical Locations
- `src/stream_cheremsha/overlays/server.py`: `aiohttp` web server, route definitions, and WebSocket connection handling.
- `src/stream_cheremsha/overlays/registry.py`: `OverlayRegistry` mapping `type_id` strings to `OverlayType` handlers.
- `src/stream_cheremsha/overlays/widget_instances.py`: CRUD operations, `WIDGET_TYPES` registry, schema validation, and persistence to `QSettings`.
- `src/stream_cheremsha/overlays/*_overlay.py`: Individual widget type definitions (HTML rendering, JS assets).
- `src/stream_cheremsha/overlays/*_controller.py`: Business logic coordinating state updates with overlay topics.

## Important Symbols
- `OverlayRegistry`:
  - `register(overlay_type: OverlayType)`: Registers a renderer.
- `widget_instances`:
  - `WIDGET_TYPES`: Global dictionary of supported widget metadata.
  - `load_widget_instances()` / `save_widget_instances_to_settings()`: Serialization.
- `InstanceControllerGroup`:
  - `get_or_create(instance_id)`: Retrieves the active controller for an instance.
  - `broadcast_to_instance(instance_id, payload)`: Publishes to `overlay:{type}:{instance_id}`.

## Relationships with Other Domains
- **Desktop UI**: `MainWindow` initializes `InstanceControllerGroup` and feeds external events (gifts, ticks, chat) to controllers.
- **QML Editor**: `widgets_qml_api.py` interacts with `widget_instances.py` to create, edit, and preview instances.
- **Chat / Donations**: Ingested events trigger state mutations in active widget controllers.

## Common Extension Points
1. **Adding a New Widget Type (5-step checklist)**:
   - Step 1: Create `src/stream_cheremsha/overlays/<name>_overlay.py` implementing `OverlayType`.
   - Step 2: Register in `src/stream_cheremsha/overlays/registry.py` inside `OverlayRegistry.__init__`.
   - Step 3: Add type metadata and defaults loader to `WIDGET_TYPES` in `src/stream_cheremsha/overlays/widget_instances.py`.
   - Step 4: Wire controller group and event fan-out in `src/stream_cheremsha/ui/main_window.py`.
   - Step 5: Expose config load/save and preview methods in `widgets_qml_api.py` and editor in `WidgetsView.qml`.

## Relevant Invariants
- Browser source URLs (`/overlay/by-id/{id}`) must remain backward-compatible.
- PubSub updates must be throttled/debounced (100–200ms) to prevent OBS browser source rendering bottlenecks.
- Never block the `aiohttp` event loop with synchronous disk or network calls.

## Architectural Decisions
- See [.agent/decisions/widget_instances_pubsub.md](file:///home/oleksandrboichuk/Dev/Self/stream-cheremsha/.agent/decisions/widget_instances_pubsub.md)
