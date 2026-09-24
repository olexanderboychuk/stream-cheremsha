# DOMAIN: Music Player & Queue Management

## Subsystem Responsibility
Manages music playback requests from viewers via a Telegram bot, resolves and downloads tracks from YouTube using `yt-dlp`, enforces artist/country filtering via MusicBrainz, manages an ordered FIFO playback queue, and interfaces with the audio playback engine.

## Important Concepts
- **Queue Controller**: Coordinates incoming track requests, validates permissions/limits, and manages playback states (`IDLE`, `PLAYING`, `PAUSED`).
- **yt-dlp Resolver**: Extracts audio metadata, stream URLs, or temporary cached audio files from YouTube links or search queries.
- **MusicBrainz Moderation**: Queries MusicBrainz API to filter out restricted artists or music originating from specified regions.
- **Telegram Bot Integration**: Listens for `/song <query>`, `/skip`, `/queue` commands and sends status updates back to viewers.

## Important Files & Canonical Locations
- `src/stream_cheremsha/music/queue_controller.py`: Central music queue, command handlers, and track state machine.
- `src/stream_cheremsha/music/player.py`: Low-level audio player interface (mpv / ffmpeg backend).
- `src/stream_cheremsha/music/yt_dlp_resolver.py`: Audio stream extraction and URL resolving.
- `src/stream_cheremsha/music/musicbrainz.py`: Artist metadata and country-of-origin filtering.
- `src/stream_cheremsha/telegram/bot.py`: Telegram Bot client and message listeners.

## Important Symbols
- `MusicQueueController`:
  - `add_request(requester: str, query: str) -> QueueItem`: Validates and appends song to queue.
  - `skip()`: Stops current track and plays next in queue.
  - `get_now_playing() -> TrackInfo | None`: Current playback metadata.
- `YtDlpResolver`:
  - `resolve(query: str) -> ResolvedTrack`: Fetches title, duration, and stream URL.

## Relationships with Other Domains
- **Desktop UI**: `MainWindow` displays the active track, playback controls (play/pause/skip), volume, and queue list in the Music tab.
- **Overlays**: "Now Playing" overlay widget reads track metadata from `MusicQueueController` to show on-stream album art and titles.
- **Config & Keyring**: Reads Telegram bot token securely from `keyring_store.py`.

## Common Extension Points
1. **Adding a New Command to the Telegram Bot**:
   - Add command handler in `src/stream_cheremsha/music/queue_controller.py` or `src/stream_cheremsha/telegram/bot.py`.
2. **Modifying Content / Artist Restrictions**:
   - Update lookup logic in `src/stream_cheremsha/music/musicbrainz.py`.

## Relevant Invariants
- Queue order must be strictly preserved (FIFO).
- Music downloading must run in background threads/tasks and never block the Qt event loop.
- Media player process / socket cleanup must happen gracefully during application exit.

## Architectural Decisions
- See [.agent/decisions/keyring_and_secrets.md](file:///home/oleksandrboichuk/Dev/Self/stream-cheremsha/.agent/decisions/keyring_and_secrets.md)
