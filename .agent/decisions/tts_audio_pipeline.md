# Architectural Decision: TTS Processing Pipeline & Audio Invariants

## Context & Problem
Incoming stream messages arrive irregularly: bursts of messages, long spam texts, profanity, or foreign language text. Sending raw text directly to cloud TTS engines causes timeouts, quota depletion, audio volume spikes, or stream disruption.

## Decision & Invariant Architecture
1. **Pipeline Ordering Contract**:
   - Ingestion (`chat/`, `donations/`) $\rightarrow$ Sanitization (`pipeline/tts_sanitize.py`) $\rightarrow$ Content Moderation & Language Filters (`pipeline/filters.py`) $\rightarrow$ Text Chunking (`pipeline/chunking.py`) $\rightarrow$ TTS Synthesis (`tts/*.py`) $\rightarrow$ FFmpeg Normalization $\rightarrow$ Audio Playback (`audio/qt_sink.py`).
2. **Mandatory Chunking**:
   - Cloud TTS engines (Edge TTS, Google) fail or reject texts over their character limits. Long messages MUST be split into manageable sentences/clauses via `pipeline/chunking.py` before synthesis.
3. **Audio Normalization**:
   - All audio synthesized by TTS or played from external media MUST pass through audio normalization (via `ffmpeg` / `audio/qt_sink.py`). This prevents volume discrepancies that hurt stream sound balance.
4. **Queue-Based Playback (FIFO)**:
   - Audio jobs must be sequenced in a non-blocking asyncio queue. Messages must not overlap or step on each other unless explicitly canceled by a skip command.
5. **Non-Blocking I/O**:
   - Network synthesis and audio decoding must never run synchronously on the Qt main thread. All I/O must be scheduled via `asyncio` / `qasync`.

## What Must Never Happen
- DO NOT pass raw unsanitized text directly to TTS engines.
- DO NOT synthesize audio on the Qt GUI thread.
- DO NOT bypass audio normalization when adding a new audio engine.
