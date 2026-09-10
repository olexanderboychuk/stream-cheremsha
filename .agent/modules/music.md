# MODULE: Music Player & Queue

## Purpose
Manages the music lifecycle: requesting songs via a Telegram bot, downloading them from YouTube using `yt-dlp`, managing an ordered playback queue, and handling audio playback with smooth transitions.

## Canonical Locations
- `src/stream_cheremsha/music/`: Main music subsystem.
- `src/stream_cheremsha/music/player.py`
- `src/stream_cheremsha/music/queue_controller.py`
- `src/stream_cheremsha/music/yt_dlp_resolver.py`
- `src/stream_cheremsha/music/musicbrainz.py`

## Public Surface
Provides a Telegram bot interface for remote requests and an internal API for the UI to manage the queue (skip, clear, etc.).

## Internal Structure
- **Queue Controller**: Manages the list of pending songs and current playback state.
- **Player**: Handles the actual audio stream using `ffmpeg` or other backends.
- **yt_dlp Resolver**: Downloads music from YouTube URLs.
- **MusicBrainz**: Filters out specific artists/countries (e.g., blocking Russian performers).

## Dependencies
- `python-telegram-bot` (Telegram Bot)
- `yt-dlp` (YouTube downloads)
- `ffmpeg` (Audio processing)
- `musicbrainz` (Filtering)

## Tests
- `tests/test_music_queue_controller.py`
- `tests/test_musicbrainz.py`
- `tests/test_music_player_mpv.py`

## Change Guide
- **Add a new music source**: Update `yt_dlp_resolver.py`.
- **Modify Telegram bot commands**: Update the bot handler in `queue_controller.py`.
- **Change filtering rules**: Modify `musicbrainz.py`.

## Invariants
- The queue must be strictly ordered (FIFO).
- Music downloads should not block the main application thread.

## Pitfalls
- YouTube download limits: Frequent requests can lead to IP blocks or quota issues.
- MusicBrainz API limits: Ensure proper User-Agent and rate limiting.

## Avoid
Do not modify `src/stream_cheremsha/music/player.py` unless you are changing the core audio backend.
