# PROJECT MAP

## REPOSITORY TREE
- `src/stream_cheremsha/actions`: Automation actions (keystrokes, file writes, etc.)
- `src/stream_cheremsha/app`: Application entry point and main loop.
- `src/stream_cheremsha/chat`: Chat source implementations (Twitch, YouTube, TikTok, Kick).
- `src/stream_cheremsha/config`: Configuration management, keyring storage, secrets.
- `src/stream_cheremsha/domain`: Core domain models and protocols.
- `src/stream_cheremsha/donations`: Donation tracking (Donatik, Donatello).
- `src/stream_cheremsha/music`: Music player, queue management, Telegram bot integration.
- `src/stream_cheremsha/obs_ws`: OBS WebSocket v5 control logic.
- `src/stream_cheremsha/overlays`: Overlay server (aiohttp) and widget implementations.
- `src/stream_cheremsha/pipeline`: TTS processing pipeline (chunking, filtering).
- `src/stream_cheremsha/tts`: Text-to-Speech engine logic.

## ENTRY POINTS
- **Application**: `src/stream_cheremsha/app/main.py` (via `cheremsha` script)
- **Build System**: `src/stream_cheremsha/build_nuitka.py` (via `cheremsha-build`)
- **Scripts**: `scripts/` directory

## SUBSYSTEM MAP
| Subsystem | Location | Responsibility | Context |
| --------- | -------- | -------------- | ------- |
| Chat Aggregation | `src/stream_cheremsha/chat` | Multi-platform chat ingestion | `.agent/modules/chat.md` |
| TTS Pipeline | `src/stream_cheremsha/pipeline`, `src/stream_cheremsha/tts` | Audio generation & processing | `.agent/modules/tts.md` |
| Music Player | `src/stream_cheremsha/music` | Queue, Telegram bot, yt-dlp | `.agent/modules/music.md` |
| Overlays | `src/stream_cheremsha/overlays` | Web server & OBS widgets | `.agent/modules/overlays.md` |
| Actions Engine | `src/stream_cheremsha/actions` | Automation & platform actions | `.agent/modules/actions.md` |
| Config & Secrets | `src/stream_cheremsha/config` | Keyring, constants, env vars | `.agent/modules/config.md` |

## CHANGE → WHERE TO LOOK
- **Add API endpoint / New Widget** $\rightarrow$ `overlays/`, `app/main.py`
- **Change database entity** $\rightarrow$ `domain/models.py`, `persistence/` (if applicable)
- **Add background task** $\rightarrow$ `actions/`, `pipeline/`
- **Change authentication** $\rightarrow$ `chat/`, `config/keyring_store.py`
- **Modify frontend state** $\rightarrow$ `overlays/widget_instances.py`, `qml/`
- **Add new chat source** $\rightarrow$ `chat/`

## DATA OWNERSHIP
- **Database Entities**: `domain/models.py`
- **Business Rules**: `pipeline/`, `music/queue_controller.py`
- **External Integrations**: `chat/`, `donations/`, `music/yt_dlp_resolver.py`
- **Background Jobs**: `actions/`
- **API Contracts**: `overlays/server.py` (for internal web API)

## TEST MAP
- **Unit Tests**: `tests/test_*_*.py`
- **Integration Tests**: `tests/test_overlays_server_integration.py`, `tests/test_kick_integration.py`
- **Fixtures & Mocks**: `tests/fixtures/`

## INTEGRATION MAP
- **Twitch**: `chat/twitch_source.py` $\rightarrow$ Twitch IRC WebSocket
- **YouTube**: `chat/youtube_source.py` $\rightarrow$ YouTube Data API v3
- **TikTok**: `chat/tiktok_source.py` $\rightarrow$ TikTokLive library
- **Kick**: `chat/kick_pusher.py` $\rightarrow$ Kick Pusher WebSocket
- **Telegram**: `music/queue_controller.py` $\rightarrow$ Telegram Bot API
- **OBS Studio**: `obs_ws/control.py` $\rightarrow$ OBS WebSocket v5

## DEPENDENCY GRAPH
`app` $\rightarrow$ (`chat`, `tts`, `music`, `overlays`) $\rightarrow$ (`actions`, `config`, `domain`)

## HIGH-BLAST-RADIUS COMPONENTS
- `src/stream_cheremsha/pipeline`: Affects all audio output.
- `src/stream_cheremsha/overlays/server.py`: Can crash the web server for OBS sources.
- `src/stream_cheremsha/config/keyring_store.py`: Critical for secret management.

## TASK ROUTING
| TASK | MODULE CONTEXT | FLOW CONTEXT | PRIMARY FILES | TESTS |
| ----- | -------------- | ------------ | ----------- | ----- |
| Fix payment webhook | `.agent/modules/donations.md` | N/A | `donations/donatik_client.py` | `tests/test_donatello...` |
| Add new chat source | `.agent/modules/chat.md` | N/A | `chat/*.py` | `tests/test_*_source.py` |
| Modify TTS filters | `.agent/modules/tts.md` | N/A | `pipeline/filters.py` | `tests/test_filters_chunking.py` |
| Update music queue | `.agent/modules/music.md` | `.agent/flows/music_request.md` | `music/queue_controller.py` | `tests/test_music_queue...` |
| New OBS widget | `.agent/modules/overlays.md` | N/A | `overlays/*.py` | `tests/test_overlays_*...` |
