# DOMAIN: Platform Actions & Automation Engine

## Subsystem Responsibility
Executes platform-specific automation triggers, such as simulating keystrokes, running external programs, writing logs/files, triggering OBS scene changes, or sending system notifications in response to stream events (chat commands, donations, TikTok gifts).

## Important Concepts
- **Action Models**: Declarative definitions of actions (e.g. `SimulateKeystrokesAction`, `LaunchProgramAction`).
- **Action Engine**: Executes actions asynchronously with thread pooling or subprocess isolation to keep the UI responsive.
- **Platform Matchers**: Adapts action execution depending on whether the host OS is Windows (using `interception` or win32 API) or Linux (using `pynput` or `xdotool`).
- **Action Registry**: Discovers and instantiates available action handlers by action type ID.

## Important Files & Canonical Locations
- `src/stream_cheremsha/actions/engine.py`: Central action dispatcher and execution manager.
- `src/stream_cheremsha/actions/registry.py`: Action type registry and factory functions.
- `src/stream_cheremsha/actions/models.py`: Data models defining action payloads and parameters.
- `src/stream_cheremsha/actions/actions_simulate_keystrokes.py`: Keyboard input simulation.
- `src/stream_cheremsha/actions/actions_launch_program.py`: Process spawning and management.

## Important Symbols
- `ActionEngine`:
  - `execute(action: ActionModel) -> asyncio.Task`: Runs an action in the background.
- `ActionRegistry`:
  - `register(action_type: str, handler_cls)`: Registers an action handler.

## Relationships with Other Domains
- **Chat & Donations**: Incoming events trigger configured actions based on streamer-defined rules.
- **Desktop UI**: `MainWindow` hosts the Actions tab (`_IX_ACTIONS = 3`) allowing streamers to create, test, and edit action triggers.
- **OBS WebSocket**: Actions can trigger OBS scene switches or audio mutes via `obs_ws/control.py`.

## Common Extension Points
1. **Adding a New Action Type**:
   - Define model in `src/stream_cheremsha/actions/models.py`.
   - Implement execution logic in `src/stream_cheremsha/actions/<new_action>.py`.
   - Register the handler in `src/stream_cheremsha/actions/registry.py`.
   - Add QML configuration editor fields in Actions view.

## Relevant Invariants
- Action execution must never block the main Qt event loop.
- Platform-specific code must check OS compatibility before executing.
- Process execution must sanitize arguments to avoid shell injection.
