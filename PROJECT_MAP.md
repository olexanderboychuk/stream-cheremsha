# PROJECT MAP

## L0 — PROJECT IDENTITY

- **Project Type**: Desktop streaming assistant aggregating live chat, Ukrainian TTS, music queue management, platform automation actions, OBS browser source overlays, and OBS WebSocket integration.
- **Tech Stack**: Python 3.11, PySide6 (Qt 6.8+), qasync (asyncio loop integration), aiohttp (overlay web server), QML + CSS/HTML overlays.
- **Entry Points**:
  - Desktop Application: `src/stream_cheremsha/app/main.py` (CLI: `cheremsha`)
  - Standalone Nuitka Builder: `src/stream_cheremsha/build_nuitka.py` (CLI: `cheremsha-build`)
- **High-Level Architecture**:
  - UI runs on the PySide6 main thread with `qasync` event loop.
  - Background services (Chat, TTS, Music, Overlays) communicate asynchronously via signals and PubSub.
  - Overlays are served locally at `http://127.0.0.1:17171` to OBS Studio browser sources.
- **Global Constraints**:
  - **Main Thread Safety**: Never execute blocking I/O on the Qt GUI thread.
  - **Keyring First**: Sensitive secrets (tokens, passwords) must only be stored in the OS keyring (`config/keyring_store.py`).
  - **Tab Lazy Loading**: Secondary UI tabs must use placeholder initialization and be warmed via splash or first navigation.
  - **URL Immutability**: OBS overlay routes (`/overlay/by-id/{id}`, `/ws`) must remain backward-compatible.
- **How to Run & Test**:
  - Run Application: `.venv/bin/python -m stream_cheremsha`
  - Run Tests: `PYTHONPATH=. .venv/bin/pytest tests/test_<target>.py`
  - Linting: `.venv/bin/ruff check src tests`
  - Formatting: `.venv/bin/ruff format src tests`

---

## L1 — ARCHITECTURE MAP

### DesktopUI
- **Responsibility**: Application window, QStackedWidget tab lifecycle, lazy loading, splash warming, QML bridge.
- **Location**: `src/stream_cheremsha/ui/main_window.py`, `src/stream_cheremsha/ui/widgets_qml_api.py`, `src/stream_cheremsha/qml/`
- **Important Symbols**: `MainWindow`, `WidgetsQmlApi`, `_build_ui`, `_set_main_page`, `warm_secondary_pages`
- **Depends On**: `OverlayServer`, `InstanceControllerGroup`, `TTSCoordinator`, `KeyringStore`
- **Related Domains**: `OverlaysWidgets`, `ConfigKeyring`
- **Domain Guide**: [.agent/domains/ui_desktop.md](file:///home/oleksandrboichuk/Dev/Self/stream-cheremsha/.agent/domains/ui_desktop.md)

### OverlaysWidgets
- **Responsibility**: Local web server, widget instances, WebSocket PubSub bus, OBS browser source rendering.
- **Location**: `src/stream_cheremsha/overlays/server.py`, `registry.py`, `widget_instances.py`
- **Important Symbols**: `OverlayServer`, `OverlayRegistry`, `InstanceControllerGroup`, `WidgetInstance`
- **Depends On**: `aiohttp`, `QSettings`
- **Related Domains**: `DesktopUI`, `BattleGames`
- **Domain Guide**: [.agent/domains/overlays_widgets.md](file:///home/oleksandrboichuk/Dev/Self/stream-cheremsha/.agent/domains/overlays_widgets.md)

### ChatAggregation
- **Responsibility**: Multi-platform chat ingestion (Twitch, YouTube, TikTok, Kick), message normalization.
- **Location**: `src/stream_cheremsha/chat/`
- **Important Symbols**: `TwitchChatSource`, `YouTubeChatSource`, `TikTokChatSource`, `KickPusherSource`, `ChatMessage`
- **Depends On**: `twitchio`, `TikTokLive`, `httpx`, `websockets`, `KeyringStore`
- **Related Domains**: `TTSPipeline`, `BattleGames`, `DesktopUI`
- **Domain Guide**: [.agent/domains/chat_aggregation.md](file:///home/oleksandrboichuk/Dev/Self/stream-cheremsha/.agent/domains/chat_aggregation.md)

### TTSPipeline
- **Responsibility**: Sanitization, moderation/language filtering, text chunking, cloud speech synthesis, audio normalization.
- **Location**: `src/stream_cheremsha/pipeline/coordinator.py`, `src/stream_cheremsha/tts/`, `src/stream_cheremsha/audio/`
- **Important Symbols**: `TTSCoordinator`, `TTSEngine`, `edge_tts`, `chunking`, `filters`, `QtAudioSink`
- **Depends On**: `edge-tts`, `ffmpeg`, `groq`, `PySide6.QtMultimedia`
- **Related Domains**: `ChatAggregation`, `Donations`, `DesktopUI`
- **Domain Guide**: [.agent/domains/tts_pipeline.md](file:///home/oleksandrboichuk/Dev/Self/stream-cheremsha/.agent/domains/tts_pipeline.md)

### MusicPlayer
- **Responsibility**: Telegram bot requests, YouTube track resolving via yt-dlp, MusicBrainz filtering, FIFO playback queue.
- **Location**: `src/stream_cheremsha/music/queue_controller.py`, `player.py`, `yt_dlp_resolver.py`
- **Important Symbols**: `MusicQueueController`, `YtDlpResolver`, `MusicPlayer`, `ResolvedTrack`
- **Depends On**: `python-telegram-bot`, `yt-dlp`, `musicbrainzngs`, `mpv` / `ffmpeg`
- **Related Domains**: `DesktopUI`, `OverlaysWidgets`, `ConfigKeyring`
- **Domain Guide**: [.agent/domains/music_player.md](file:///home/oleksandrboichuk/Dev/Self/stream-cheremsha/.agent/domains/music_player.md)

### Donations
- **Responsibility**: Payment platform polling (Donatello, Donatik), deduplication, tip alert dispatching.
- **Location**: `src/stream_cheremsha/donations/donatello_client.py`, `donatik_client.py`, `tts_seen_store.py`
- **Important Symbols**: `DonatelloClient`, `DonatikClient`, `TtsSeenStore`, `DonationEvent`
- **Depends On**: `httpx`, `SQLite`, `KeyringStore`
- **Related Domains**: `TTSPipeline`, `ActionsEngine`, `OverlaysWidgets`
- **Domain Guide**: [.agent/domains/donations.md](file:///home/oleksandrboichuk/Dev/Self/stream-cheremsha/.agent/domains/donations.md)

### ActionsEngine
- **Responsibility**: Event-triggered platform automation (keystrokes, application execution, script launching).
- **Location**: `src/stream_cheremsha/actions/engine.py`, `registry.py`, `models.py`
- **Important Symbols**: `ActionEngine`, `ActionRegistry`, `SimulateKeystrokesAction`, `LaunchProgramAction`
- **Depends On**: `pynput`, OS input drivers
- **Related Domains**: `ChatAggregation`, `Donations`, `OBSIntegration`
- **Domain Guide**: [.agent/domains/actions_engine.md](file:///home/oleksandrboichuk/Dev/Self/stream-cheremsha/.agent/domains/actions_engine.md)

### BattleGames
- **Responsibility**: Interactive viewer mini-games (1v1/2v2 Battle score races, Battle Royale HP duels).
- **Location**: `src/stream_cheremsha/battle/engine.py`, `src/stream_cheremsha/battle_royale/controller.py`
- **Important Symbols**: `BattleEngine`, `BattleRoyaleController`, `BattleState`, `Participant`
- **Depends On**: Pure Python models, `InstanceControllerGroup`
- **Related Domains**: `ChatAggregation`, `OverlaysWidgets`, `Persistence`
- **Domain Guide**: [.agent/domains/battle_games.md](file:///home/oleksandrboichuk/Dev/Self/stream-cheremsha/.agent/domains/battle_games.md)

### ConfigKeyring
- **Responsibility**: OS Keyring secrets storage, constants, embedded build settings, Cloudflare tunnel tokens.
- **Location**: `src/stream_cheremsha/config/keyring_store.py`, `constants.py`, `embedded.py`
- **Important Symbols**: `KeyringStore`, `get_secret`, `set_secret`
- **Depends On**: `keyring`
- **Related Domains**: All domains
- **Domain Guide**: [.agent/domains/config_keyring.md](file:///home/oleksandrboichuk/Dev/Self/stream-cheremsha/.agent/domains/config_keyring.md)

### OBSIntegration
- **Responsibility**: Bi-directional remote control with OBS Studio via OBS WebSocket v5.
- **Location**: `src/stream_cheremsha/obs_ws/control.py`
- **Important Symbols**: `ObsWsClient`, `set_current_program_scene`, `set_scene_item_enabled`
- **Depends On**: `obsws-python` / `websockets`
- **Related Domains**: `ActionsEngine`, `DesktopUI`
- **Domain Guide**: [.agent/domains/obs_integration.md](file:///home/oleksandrboichuk/Dev/Self/stream-cheremsha/.agent/domains/obs_integration.md)

---

## Quick Navigation: Where is X?
Consult the symbol index for immediate class/file/topic lookups:
- **Symbol & Pattern Index**: [.agent/index.md](file:///home/oleksandrboichuk/Dev/Self/stream-cheremsha/.agent/index.md)
