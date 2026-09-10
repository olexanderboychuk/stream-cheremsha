# MODULE: Chat Aggregation

## Purpose
Handles real-time ingestion of chat messages from Twitch, YouTube, TikTok, and Kick. It normalizes these different platform formats into a unified internal message structure for the TTS pipeline and overlays.

## Canonical Locations
- `src/stream_cheremsha/chat/`: Main source implementations.
- `src/stream_cheremsha/chat/twitch_source.py`
- `src/stream_cheremsha/chat/youtube_source.py`
- `src/stream_cheremsha/chat/tiktok_source.py`
- `src/stream_cheremsha/chat/kick_pusher.py`

## Public Surface
Exposes a unified stream of messages to the `pipeline/coordinator.py`.

## Internal Structure
- **Credentials**: Handles OAuth flows and token storage in keyring (`twitch_credentials.py`, etc.).
- **Sources**: Platform-specific logic for connecting, heartbeating, and message parsing.
- **Video IDs**: Helper for YouTube video identification.

## Dependencies
- `twitchio` (Twitch)
- `google-api-python-client` (YouTube)
- `TikTokLive` (TikTok)
- `httpx`, `websockets` (Kick/General)

## Tests
- `tests/test_chat_*_*.py`
- `tests/test_kick_integration.py`

## Change Guide
- **Add new chat source**: Create a new file in `src/stream_cheremsha/chat/`, implement the connection logic, and register it with the coordinator.
- **Modify message parsing**: Update the specific source file (e.g., `tiktok_source.py`) to handle new platform fields.

## Invariants
- Messages must be normalized into a common format before reaching the pipeline.
- Connection drops must trigger automatic reconnection logic.

## Pitfalls
- Kick's Pusher WebSocket is a compatibility transport; changes in their web client may affect ingestion.
- TikTokLive can be sensitive to account permissions and username formats.

## Avoid
Do not modify `src/stream_cheremsha/chat/__init__.py` unless adding global chat state.
