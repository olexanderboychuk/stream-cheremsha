# DOMAIN: OBS Studio & WebSocket v5 Integration

## Subsystem Responsibility
Manages real-time bi-directional communication with OBS Studio via the OBS WebSocket v5 protocol. Allows Stream Cheremsha to inspect scenes/sources, switch active scenes, toggle source visibility (e.g., mute alerts or show browser sources), and respond to OBS streaming state changes.

## Important Concepts
- **OBS WebSocket v5 Protocol**: Standard protocol for controlling OBS Studio remotely over a local WebSocket connection (default port `4455`).
- **Connection Lifecycle**: Maintains connection state, automatic reconnection on OBS restart, and authentication handshake.
- **Scene & Source Queries**: Fetches scene lists, current scene, and source visibility for automation actions and UI status docks.

## Important Files & Canonical Locations
- `src/stream_cheremsha/obs_ws/control.py`: Central client managing WebSocket v5 connection, requests, and event subscriptions.
- `src/stream_cheremsha/obs_ws/__init__.py`: Package entry points.
- `src/stream_cheremsha/actions/`: Platform actions that trigger OBS scene switches or source toggles.

## Important Symbols
- `ObsWsClient`:
  - `connect(host, port, password)`: Initiates handshake.
  - `set_current_program_scene(scene_name)`: Switches active scene.
  - `set_scene_item_enabled(scene_name, scene_item_id, enabled)`: Toggles source visibility.
  - `get_scene_list()`: Queries scenes.

## Relationships with Other Domains
- **Actions Engine**: Stream triggers (e.g. large donation, chat command) execute OBS commands via `ObsWsClient`.
- **Desktop UI**: Settings tab allows configuration of OBS host, port, and password; connection status shown in sidebar/connection panels.
- **Config & Keyring**: OBS password stored securely in `keyring_store.py`.

## Common Extension Points
1. **Adding a New OBS Remote Command**:
   - Implement method in `src/stream_cheremsha/obs_ws/control.py`.
   - Expose as an action in `src/stream_cheremsha/actions/` if user-triggerable.

## Relevant Invariants
- OBS WebSocket calls must be asynchronous and non-blocking.
- Connection drops or OBS restarts must not crash Cheremsha; reconnect logic must retry with backoff.
- Passwords must be fetched from keyring.

## Architectural Decisions
- See [.agent/decisions/keyring_and_secrets.md](file:///home/oleksandrboichuk/Dev/Self/stream-cheremsha/.agent/decisions/keyring_and_secrets.md)
