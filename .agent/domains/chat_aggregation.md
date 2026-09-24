# DOMAIN: Chat Aggregation

## Subsystem Responsibility
Ingests live chat messages, events, and gifts from multiple streaming platforms (Twitch, YouTube, TikTok, Kick), normalizes platform-specific payloads into standard domain models, and forwards them to the TTS pipeline and overlay docks.

## Important Concepts
- **Unified Message Model**: Normalizes badges, author names, avatars, plain text content, and platform identifiers so downstream consumers (TTS, docks, overlays) remain platform-agnostic.
- **Connection Lifecycle & Reconnect**: Maintains background WebSocket/HTTP streams with exponential backoff and connection state monitoring.
- **Gift Normalization**: TikTok gifts and Twitch bits are normalized into standard gift/tip event models.

## Important Files & Canonical Locations
- `src/stream_cheremsha/chat/twitch_source.py`: Twitch IRC WebSocket ingestion via `twitchio`.
- `src/stream_cheremsha/chat/youtube_source.py`: YouTube live chat polling via YouTube Data API v3.
- `src/stream_cheremsha/chat/tiktok_source.py`: TikTok live stream ingestion via `TikTokLive`.
- `src/stream_cheremsha/chat/kick_pusher.py`: Kick live chat via Pusher WebSocket.
- `src/stream_cheremsha/chat/twitch_credentials.py`: OAuth flow & token validation.
- `src/stream_cheremsha/domain/models.py`: Unified `ChatMessage`, `GiftEvent`, and `Author` models.

## Important Symbols
- `TwitchChatSource`, `YouTubeChatSource`, `TikTokChatSource`, `KickPusherSource`:
  - `start()` / `stop()`: Connection lifecycle.
  - `on_message` signal / callback: Dispatches normalized `ChatMessage`.
- `ChatMessage`: Unified dataclass containing `platform`, `author_name`, `text`, `badges`, `emotes`, `timestamp`.

## Relationships with Other Domains
- **TTS Pipeline**: Ingested messages are passed to `pipeline/coordinator.py` for speech synthesis.
- **Overlays & Games**: Gifts and chat commands trigger events in `battle/`, `battle_royale/`, and overlay chat docks.
- **Config & Keyring**: Reads platform credentials (tokens, client IDs) securely from `keyring_store.py`.

## Common Extension Points
1. **Adding a New Platform Source**:
   - Implement client in `src/stream_cheremsha/chat/<platform>_source.py`.
   - Map platform events to `ChatMessage` or `GiftEvent`.
   - Register source in `MainWindow` connection panel and start in `run_startup()`.
2. **Handling New Emotes or Badges**:
   - Update platform-specific parser in `*_source.py` before converting to `ChatMessage`.

## Relevant Invariants
- All platform messages must be normalized into `ChatMessage` before dispatching.
- Network reconnections must run asynchronously in background tasks without blocking the main event loop.
- Platform tokens must never be written to logs or plain text.

## Architectural Decisions
- See [.agent/decisions/keyring_and_secrets.md](file:///home/oleksandrboichuk/Dev/Self/stream-cheremsha/.agent/decisions/keyring_and_secrets.md)
