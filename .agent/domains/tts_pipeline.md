# DOMAIN: TTS Pipeline & Audio Synthesis

## Subsystem Responsibility
Processes incoming text into synthesized speech. Responsibilities include text sanitization, moderation, profanity/language filtering, splitting text into sentence chunks, synthesizing audio via cloud engines, normalizing audio volume via FFmpeg, and queuing audio playback.

## Important Concepts
- **Coordinator Pattern**: `pipeline/coordinator.py` acts as the central orchestrator receiving text, passing it through filter chains, chunkers, and engine workers.
- **Content Filtering**: Filters check for blocked languages, blacklisted terms, or inappropriate content using local regex rules and optional Groq LLM moderation.
- **Sentence Chunking**: Long messages exceeding character limits are split into natural spoken clauses.
- **Audio Normalization**: All generated audio chunks pass through FFmpeg loudness normalization (EBU R128 standard) before hitting `audio/qt_sink.py`.

## Important Files & Canonical Locations
- `src/stream_cheremsha/pipeline/coordinator.py`: Core pipeline manager and audio playback queue.
- `src/stream_cheremsha/pipeline/tts_sanitize.py`: Emote stripping, URL replacement, text cleaning.
- `src/stream_cheremsha/pipeline/filters.py`: Language detection, moderation, and rule enforcement.
- `src/stream_cheremsha/pipeline/chunking.py`: Sentence splitting and character-boundary chunking.
- `src/stream_cheremsha/tts/edge_tts.py`: Microsoft Edge TTS engine integration.
- `src/stream_cheremsha/tts/google_tts.py`: Google Translate TTS engine integration.
- `src/stream_cheremsha/audio/qt_sink.py`: PySide6 audio sink and playback engine.

## Important Symbols
- `TTSCoordinator`:
  - `enqueue_message(message: ChatMessage)`: Main ingestion entry point.
  - `skip_current()`: Halts active audio playback and clears current chunk queue.
- `TTSEngine` (Protocol / Base):
  - `synthesize(text: str, voice: str) -> bytes`: Returns normalized audio bytes.

## Relationships with Other Domains
- **Chat Aggregation**: Receives messages from `chat/*_source.py`.
- **Donations**: Receives donation alerts and author notes for priority TTS synthesis.
- **Desktop UI**: `MainWindow` provides volume sliders, voice selection dropdowns, and skip shortcuts.

## Common Extension Points
1. **Adding a New TTS Engine**:
   - Implement engine wrapper in `src/stream_cheremsha/tts/<engine>_tts.py`.
   - Register engine in `TTSCoordinator` and add voice options to `constants.py` and UI dropdowns.
2. **Adding a Sanitization Filter**:
   - Add filter function in `src/stream_cheremsha/pipeline/tts_sanitize.py`.
   - Wire into the sanitization pipeline in `pipeline/coordinator.py`.

## Relevant Invariants
- Audio MUST be normalized before playback to ensure consistent stream volume.
- Long text MUST be chunked; passing oversized blocks directly to engines will fail.
- All TTS synthesis operations MUST be asynchronous; never synthesize on the Qt main thread.

## Architectural Decisions
- See [.agent/decisions/tts_audio_pipeline.md](file:///home/oleksandrboichuk/Dev/Self/stream-cheremsha/.agent/decisions/tts_audio_pipeline.md)
