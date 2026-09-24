# L4: Symbol & Pattern Index

Lightweight index of architectural symbols, interfaces, and patterns to answer *"Where is X implemented?"* without scanning the repository.

---

## 1. Core Classes & Coordinators

| Symbol | File Location | Responsibility |
|--------|---------------|----------------|
| `MainWindow` | `src/stream_cheremsha/ui/main_window.py` | Main GUI coordinator, tab manager, event bus |
| `WidgetsQmlApi` | `src/stream_cheremsha/ui/widgets_qml_api.py` | PySide6 bridge between QML views and Python services |
| `OverlayRegistry` | `src/stream_cheremsha/overlays/registry.py` | Maps `type_id` strings to `OverlayType` renderers |
| `InstanceControllerGroup` | `src/stream_cheremsha/overlays/widget_instances.py` | Multi-instance controller lifecycle and topic isolation |
| `OverlayServer` | `src/stream_cheremsha/overlays/server.py` | aiohttp web server (`/overlay/by-id/{id}`, `/ws`) |
| `TTSCoordinator` | `src/stream_cheremsha/pipeline/coordinator.py` | Text ingestion, filtering, chunking, and speech queue |
| `MusicQueueController` | `src/stream_cheremsha/music/queue_controller.py` | FIFO track queue, state transitions, Telegram bot handler |
| `ActionEngine` | `src/stream_cheremsha/actions/engine.py` | Asynchronous trigger execution (keystrokes, commands) |
| `ActionRegistry` | `src/stream_cheremsha/actions/registry.py` | Type registry for automation action models |
| `BattleEngine` | `src/stream_cheremsha/battle/engine.py` | Deterministic 1v1/2v2 score, combo, and comeback state machine |
| `BattleRoyaleController` | `src/stream_cheremsha/battle_royale/controller.py` | Singleton HP duel game controller |
| `ObsWsClient` | `src/stream_cheremsha/obs_ws/control.py` | OBS WebSocket v5 client for scenes and sources |
| `KeyringStore` | `src/stream_cheremsha/config/keyring_store.py` | Secure OS Keyring abstraction for tokens and passwords |

---

## 2. Models & Data Structures

| Model | File Location | Description |
|-------|---------------|-------------|
| `ChatMessage` | `src/stream_cheremsha/domain/models.py` | Normalized chat message (author, platform, text, badges) |
| `GiftEvent` | `src/stream_cheremsha/domain/models.py` | Normalized gift/tip event (diamonds, sender, value) |
| `DonationEvent` | `src/stream_cheremsha/domain/models.py` | Normalized tip alert (Donatello, Donatik) |
| `WidgetInstance` | `src/stream_cheremsha/overlays/widget_instances.py` | Configured overlay instance (id, type, name, settings) |
| `BattleState` / `Participant` | `src/stream_cheremsha/battle/models.py` | State snapshots for live 1v1/2v2 games |
| `ResolvedTrack` | `src/stream_cheremsha/music/yt_dlp_resolver.py` | YouTube track metadata (title, url, duration) |

---

## 3. QStackedWidget Tab Indices (`MainWindow`)

Located in `src/stream_cheremsha/ui/main_window.py`:

| Index | Constant | Tab Name | Load Mode | Ensure Method |
|-------|----------|----------|-----------|---------------|
| 0 | `_IX_CHAT` | Chat | Eager | Default |
| 1 | `_IX_SETTINGS` | Settings | Lazy / Warm | `_ensure_settings_widgets()` |
| 2 | `_IX_WIDGETS` | Widgets | Lazy / Warm | `_ensure_qml_page_visible(_IX_WIDGETS)` |
| 3 | `_IX_ACTIONS` | Actions | Lazy / Warm | `_ensure_actions_widgets()` |
| 4 | `_IX_LAYOUTS` | Layouts | Lazy / Warm | `_ensure_qml_page_visible(_IX_LAYOUTS)` |
| 5 | `_IX_DONATIONS`| Donations| Lazy / Warm | `_ensure_qml_page_visible(_IX_DONATIONS)` |
| 6 | `_IX_DOCKS` | Docks | Lazy / Warm | `_ensure_qml_page_visible(_IX_DOCKS)` |
| 7 | `_IX_AUDIO` | Audio | Eager | Default |
| 8 | `_IX_MUSIC` | Music | Eager | Default |

---

## 4. WebSocket PubSub Topics (`overlays/server.py`)

| Topic Format | Emitter | Subscriber | Purpose |
|--------------|---------|------------|---------|
| `overlay:{type}:{instance_id}` | `InstanceControllerGroup` | OBS Browser Source | Per-instance real-time state sync (battle, leaderboard) |
| `overlay:battle_royale:*` | `BattleRoyaleController` | OBS Browser Source | Singleton battle royale HP & events |
| `overlay:chat:*` | Chat dock / controllers | OBS Browser Source | Real-time chat messages |
| `overlay:now_playing:*` | `MusicQueueController` | OBS Browser Source | Album art, title, and playback state |

---

## 5. Storage & Persistence Layout

| Store | Location | Usage |
|-------|----------|-------|
| OS Keyring | `config/keyring_store.py` | Twitch/YouTube/TikTok/Telegram tokens, passwords |
| QSettings | `overlays/widget_instances.py` | Widget instances, positions, settings dictionaries |
| SQLite (Points) | `persistence/points_sqlite.py` | Viewer loyalty points database |
| SQLite (Battles) | `persistence/battle_royale_wins_sqlite.py` | Win/loss stats for battle royale |
| SQLite (Gifts) | `persistence/tiktok_gifts_sqlite.py` | Seen TikTok gift transactions |
| SQLite (Donations) | `donations/tts_seen_store.py` | Deduplication store for Donatello/Donatik tips |

---

## 6. Entry Points & CLI

| Target | Command | Implementation |
|--------|---------|----------------|
| App Run | `python -m stream_cheremsha` | `src/stream_cheremsha/app/main.py` |
| Fast Run | `bin/cheremsha` | Shell launcher script |
| App Build | `cheremsha-build` | `src/stream_cheremsha/build_nuitka.py` |
| Tests | `PYTHONPATH=. .venv/bin/pytest tests/test_<name>.py` | Pytest suite |
| Linter | `.venv/bin/ruff check src tests` | Ruff |
