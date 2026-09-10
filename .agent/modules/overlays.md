# MODULE: Overlays & Widgets

## Purpose
Provides a local web server that serves HTML/JS overlays for OBS Browser Sources and Docks. It manages the state of various widgets (Chat, Activity, Social Rotator, etc.) and handles real-time updates via an internal event bus or pub/sub system.

## Canonical Locations
- `src/stream_cheremsha/overlays/`: Main overlay logic.
- `src/stream_cheremsha/overlays/server.py` (aiohttp server)
- `src/stream_cheremsha/overlays/widget_instances.py` (State management)
- `src/stream_cheremsha/overlays/registry.py` (Widget registration)

## Public Surface
Exposes a web API on `http://127.0.0.1:17171`. Provides URLs for OBS Browser Sources and Docks.

## Internal Structure
- **Server**: Handles HTTP requests, renders templates, and manages sessions.
- **Widget Registry**: Maps widget types to their respective controller/overlay logic.
- **Signal System / PubSub**: Coordinates updates between different widgets (e.g., a donation event triggering an overlay update).
- **Controllers**: Specific logic for complex widgets like Social Rotator or Stream Goal.

## Dependencies
- `aiohttp` (Web server)
- `PySide6` (UI components used in some overlays)

## Tests
- `tests/test_overlays_server_integration.py`
- `tests/test_widgets_qml_api_*...`

## Change Guide
- **Add a new widget**: Create a new overlay file, register it in `registry.py`, and add its state to `widget_instances.py`.
- **Modify an existing widget's UI**: Update the corresponding HTML/JS template or QML component.
- **Update shared data**: Modify `widget_instances.py` (e.g., adding a new global counter).

## Invariants
- The overlay server must remain responsive even if individual widgets have errors.
- Widget state should be consistent across all browser sources.

## Pitfalls
- High frequency of updates can cause high CPU usage in the browser source.
- Cross-origin issues when using Cloudflare Tunnels (handled via `tunnel.py`).

## Avoid
Do not modify `src/stream_cheremsha/overlays/server.py` unless changing the core web server logic.
