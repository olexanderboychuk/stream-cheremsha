# Architectural Decision: Widget Instances & WebSocket PubSub Architecture

## Context & Problem
OBS overlays can be added as browser sources by streamers. Different widgets require independent instances (e.g. multiple distinct battle counters, chat displays, or goals), each with its own settings, layout parameters, and UUID, while some widgets are system singletons.

## Decision & Invariant Architecture
1. **Per-Instance Pattern (`InstanceControllerGroup`)**:
   - Widgets with multiple configurations (e.g., `battle`, `live_leaderboard_simple`, `chat_overlay`) MUST use `InstanceControllerGroup(type_id, factory)` in `MainWindow`.
   - Each instance receives its own UUID, configuration dictionary, and isolated state.
2. **WebSocket PubSub Scoping**:
   - Messages are routed through the internal pub/sub bus in `overlays/server.py`.
   - Per-instance widgets MUST publish to `overlay:{type}:{instance_id}`.
   - Browser source clients subscribe to the matching topic via the `/ws` endpoint when viewing `/overlay/by-id/{id}`.
   - Singleton widgets (e.g., `battle_royale`) publish to `overlay:{type}:*`.
3. **URL Route Immutability**:
   - The route `/overlay/by-id/{id}` is a stable public contract. It MUST NEVER change query parameter syntax or URL structure because OBS browser sources save this URL persistently.
4. **State Storage Partitioning**:
   - **Widget Configuration**: Saved in `QSettings` via `overlays/widget_instances.py` (`save_widget_instances_to_settings`).
   - **Live Ephemeral State**: Held strictly in-memory in the Python controller/engine; reset on application restart.
   - **Persistent Game/User History**: Saved in SQLite via `persistence/*_sqlite.py`.
5. **No Per-Frame Polling**:
   - Overlays must be event-driven. Controllers push updates over WebSocket debounced (typically ~100–200ms) or driven by a shared 1s tick (`_battle_tick_timer`). Never run unthrottled JavaScript loops or sub-millisecond polling.

## What Must Never Happen
- DO NOT register a multi-instance widget as a global singleton.
- DO NOT hardcode port or URL schemes in widget templates; use relative WebSocket connection URLs (`window.location.host`).
- DO NOT publish un-throttled high-frequency events directly from raw network packets to the overlay.
