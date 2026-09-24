# DOMAIN: Battle Games & Interactive Overlays

## Subsystem Responsibility
Manages interactive real-time stream mini-games driven by viewer interactions (TikTok gifts, chat commands, donations). Includes the deterministic 1v1/2v2 `battle` engine and the HP-duel `battle_royale` engine, alongside their corresponding OBS overlay renderers.

## Important Concepts
- **Deterministic Battle Engine (`src/stream_cheremsha/battle/engine.py`)**: Pure Python engine without Qt or I/O dependencies. Tracks rounds (best-of-N), auto-locks top gifters as participants, calculates points, combo multipliers, comebacks, and close-finish states with an injectable clock.
- **Battle Royale (`src/stream_cheremsha/battle_royale/`)**: Singleton HP-duel system where viewer gifts heal or damage competing fighters.
- **Overlay State Sync**: Game engines emit normalized event/state snapshots that controllers broadcast over WebSocket to overlay browser sources.
- **Participant Locking**: Auto-locks the first qualifying viewers into fighter slots; spectator gifts during active rounds do not alter fighter scores.

## Important Files & Canonical Locations
- `src/stream_cheremsha/battle/engine.py`: Core deterministic 1v1/2v2 battle engine.
- `src/stream_cheremsha/battle/models.py`: Dataclasses (`BattleState`, `Participant`, `Team`, `BattleEvent`, `ComboState`).
- `src/stream_cheremsha/battle/decision.py`: Optional hook layer for game moments / decisions.
- `src/stream_cheremsha/battle_royale/controller.py`: Battle royale duel controller and state manager.
- `src/stream_cheremsha/overlays/battle_overlay.py`: Web overlay implementation for the Battle widget.
- `src/stream_cheremsha/persistence/battle_royale_wins_sqlite.py`: SQLite persistence for historical win records.

## Important Symbols
- `BattleEngine`:
  - `on_gift(*, user_key, display, avatar_url, diamonds, now) -> list[dict]`: Processes a gift and returns state events.
  - `tick(now) -> list[dict]`: Advances countdowns/timers.
  - `snapshot() -> dict`: Returns complete normalized state for overlay initialization.
- `BattleController` / `InstanceControllerGroup("battle", ...)`:
  - Connects `BattleEngine` events to WebSocket topic `overlay:battle:{instance_id}`.

## Relationships with Other Domains
- **Chat & Gifts**: Ingests TikTok gift events forwarded from `MainWindow` or `chat/tiktok_source.py`.
- **Overlays**: Integrates into `OverlayRegistry` and `widget_instances.py`.
- **Persistence**: Records player win totals and historical scoreboards in SQLite.

## Common Extension Points
1. **Adding a New Scoring Rule / Combo Multiplier**:
   - Update scoring calculations in `src/stream_cheremsha/battle/engine.py`.
   - Add unit tests verifying state transitions in `tests/test_battle_engine.py`.
2. **Adding a New Visual Theme**:
   - Add CSS variable preset in `src/stream_cheremsha/overlays/battle_overlay.py` (`theme` config).

## Relevant Invariants
- `BattleEngine` must remain deterministic and isolated from Qt/network I/O.
- Live battle state is in-memory only; restarts reset to IDLE. Only configuration and win stats persist.
- Updates to overlays must be event-driven or driven by the shared 1s tick (`_battle_tick_timer`).

## Architectural Decisions
- See [.agent/decisions/widget_instances_pubsub.md](file:///home/oleksandrboichuk/Dev/Self/stream-cheremsha/.agent/decisions/widget_instances_pubsub.md)
