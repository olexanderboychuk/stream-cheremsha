# MODULE: TTS Pipeline & Engine

## Purpose
Responsible for converting text into spoken audio. This includes sanitizing input, filtering content (e.g., Russian language checks), chunking long text for the TTS engines, and managing the final audio playback with normalization.

## Canonical Locations
- `src/stream_cheremsha/pipeline/`: Core processing logic.
- `src/stream_cheremsha/tts/`: Engine-specific implementations.
- `src/stream_cheremsha/pipeline/coordinator.py`
- `src/stream_cheremsha/pipeline/chunking.py`
- `src/stream_cheremsha/pipeline/filters.py`
- `src/stream_cheremsha/pipeline/tts_sanitize.py`

## Public Surface
Consumes messages from the chat aggregation system and provides audio output to the application core.

## Internal Structure
- **Coordinator**: Orchestrates the flow from raw text to audio playback.
- **Chunking**: Splits long strings into segments that fit within TTS engine limits.
- **Filters**: Handles content moderation, language detection (MusicBrainz/Groq), and sanitization.
- **Engines**: Wrappers for Edge TTS and Google Translate TTS.

## Dependencies
- `edge-tts`
- `ffmpeg` (for audio normalization and playback)
- `groq` (for advanced filtering/moderation)
- `musicbrainz` (for artist/country checks)

## Tests
- `tests/test_filters_chunking.py`
- `tests/test_tts_sanitize.py`
- `tests/test_edge_tts.py`

## Change Guide
- **Add a new TTS engine**: Create a new wrapper in `src/stream_cheremsha/tts/` and update the coordinator to include it.
- **Modify filtering logic**: Update `pipeline/filters.py`. Be careful with language detection rules.
- **Adjust chunking behavior**: Modify `pipeline/chunking.py`.

## Invariants
- Audio must be normalized before playback to ensure consistent volume across different engines.
- Long messages MUST be chunked; sending them as a single block will cause engine errors.

## Pitfalls
- TTS latency: High-quality engines (Edge) have higher latency than others. The coordinator manages this via queues.
- Russian language filtering: This is a high-risk area for content moderation.

## Avoid
Do not modify `src/stream_cheremsha/pipeline/coordinator.py` without ensuring all downstream filters and chunkers are compatible.
