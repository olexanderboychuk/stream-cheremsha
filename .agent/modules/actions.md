# MODULE: Actions Engine

## Purpose
Provides a system for executing platform-specific automation actions, such as simulating keystrokes, launching programs, writing files, or triggering events in the application.

## Canonical Locations
- `src/stream_cheremsha/actions/`: Main action logic.
- `src/stream_cheremsha/actions/engine.py` (Core execution engine)
- `src/stream_cheremsha/actions/registry.py` (Action registration)
- `src/stream_cheremsha/actions/models.py` (Data models for actions)

## Public Surface
Exposed via the UI and can be triggered by events from other modules (e.g., a donation triggering an action).

## Internal Structure
- **Engine**: Handles the execution of actions, including threading and platform-specific calls.
- **Registry**: Maps action types to their implementation logic.
- **Store**: Manages persistent state for certain actions if required.
- **Platform Matchers**: Logic to determine which action is appropriate for the current OS/environment.

## Dependencies
- `pynput` (Keystrokes/Mouse)
- `interception-python` (Low-level input on Windows)

## Tests
- `tests/test_platform_actions_*...`
- `tests/test_simulate_keystrokes.py`

## Change Guide
- **Add a new action**: Create an implementation file in `src/stream_cheremsha/actions/`, register it in `registry.py`, and add the corresponding model to `models.py`.
- **Modify existing action logic**: Update the specific implementation file (e.g., `actions_launch_program.py`).

## Invariants
- Actions should not block the main application thread.
- Platform-specific actions must be guarded against execution on unsupported OSs.

## Pitfalls
- Low-level input drivers (`interception`) may require administrative privileges or specific driver installations.
- Simulating keystrokes can sometimes conflict with other system inputs.

## Avoid
Do not modify `src/stream_cheremsha/actions/engine.py` unless changing the core execution flow.
