# ARCHITECTURE

## SYSTEM ARCHITECTURE
Cheremsha is a multi-threaded, asynchronous desktop application built with **PySide6 (Qt 6)** and **qasync**. It follows a modular architecture where core services are decoupled from the UI.

### Layers:
1.  **UI Layer**: PySide6/QML components for user interaction.
2.  **Application Core**: Manages the main event loop, service lifecycle, and high-level coordination (`app/`).
3.  **Service Layer**: Independent modules for Chat Aggregation, TTS Pipeline, Music Player, and Overlay Server.
4.  **Infrastructure Layer**: Handles persistence (SQLite/QSettings), configuration (Keyring), and low-level platform actions.

---

## REQUEST LIFECYCLE (Overlay Web Request)
1.  **Browser Source** requests URL (`http://127.0.0.1:17171/...`).
2.  **aiohttp Server** (`overlays/server.py`) receives request.
3.  **Widget Controller** identifies the requested widget and fetches state from `widget_instances.py`.
4.  **Data Fetching**: If needed, queries internal services (e.g., Music Player for "Now Playing").
5.  **Response**: Server renders HTML/JS template and returns it to OBS.

---

## ASYNC LIFECYCLE (Chat Message $\rightarrow$ TTS)
1.  **Source Ingestion**: `chat/*.py` receives message from platform WebSocket/API.
2.  **Pipeline Entry**: Message is passed to `pipeline/coordinator.py`.
3.  **Sanitization & Filtering**: `pipeline/tts_sanitize.py` and `filters.py` process the text.
4.  **Chunking**: `pipeline/chunking.py` splits long text into manageable TTS segments.
5.  **TTS Generation**: `tts/*.py` calls Edge TTS / Google Translate.
6.  **Audio Playback**: Audio is normalized via `ffmpeg` and played to the system output.

---

## DATA FLOW
- **Secrets**: UI $\rightarrow$ Keyring Store $\rightarrow$ OS Secret Service/Credential Manager.
- **Music Requests**: Telegram Bot $\rightarrow$ Music Queue Controller $\rightarrow$ yt-dlp Resolver $\rightarrow$ Player.
- **Actions**: UI Trigger $\rightarrow$ Action Registry $\rightarrow$ Platform Engine (Simulated Keystrokes, etc.).

---

## BUSINESS LOGIC
- **Chat Aggregation**: Normalizes different platform message formats into a common internal model.
- **Music Filtering**: Uses MusicBrainz to filter out specific artists/countries before requesting lyrics.
- **TTS Queueing**: Ensures messages are played in order and prevents pile-ups during high activity.

---

## DATABASE ARCHITECTURE
- **SQLite**: Used for persistent storage of widget instances, music history, and local settings.
- **QSettings**: Used for non-sensitive application preferences.

---

## INTEGRATIONS
- **Twitch/YouTube/TikTok/Kick**: Real-time chat ingestion via WebSockets or REST APIs.
- **OBS WebSocket v5**: Remote control of scenes and sources.
- **Telegram Bot**: External trigger for music queue management.
- **Edge TTS / Google Translate**: Cloud-based text-to-speech services.

---

## ARCHITECTURAL INVARIANTS
- **Asyncio Everywhere**: All I/O bound operations must be non-blocking using `qasync`.
- **Keyring First**: No secrets in plain text; always use the OS keyring for tokens and passwords.
- **Modular Isolation**: Services should communicate via defined interfaces or an internal event bus where appropriate.

---

## LEGACY AREAS
- Some older QML components may still exist but are being migrated to the new widget system.
