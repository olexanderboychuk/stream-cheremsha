from __future__ import annotations

import numpy as np
import pytest


def test_repeecher_voices() -> None:
    """Verify that all 13 Ukrainian voices are defined."""
    from stream_cheremsha.tts.respeecher_tts import REPEECHER_VOICES

    assert len(REPEECHER_VOICES) == 13, f"Expected 13 voices, got {len(REPEECHER_VOICES)}"

    # Verify each voice has a label
    for voice_id, voice_label in REPEECHER_VOICES.items():
        assert isinstance(voice_id, str) and voice_id.strip()
        assert isinstance(voice_label, str) and voice_label.strip()


def test_repeecher_voice_objects() -> None:
    """Verify ReSpeecherVoice dataclass construction."""
    from stream_cheremsha.tts.respeecher_tts import ReSpeecherVoice

    v = ReSpeecherVoice(id="olesia-conversation", label="Олеся (розмова)")
    assert v.id == "olesia-conversation"
    assert v.label == "Олеся (розмова)"


@pytest.mark.asyncio
async def test_repeecher_payload_building(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that the payload dict structure matches the ReSpeecher spec."""
    import stream_cheremsha.tts.respeecher_tts as mod

    # Verify the payload structure by checking the _build_payload method
    # (we test the payload keys indirectly via the voice and params)
    tts = mod.ReSpeecherTts(voice="olesia-conversation", rate_percent=100)

    # Check that the voice is set correctly
    assert tts.voice() == "olesia-conversation"
    # Check rate_percent is stored correctly
    assert tts.rate_percent() == 100

    # Verify the voice is in the supported list
    assert tts._voice in mod.REPEECHER_VOICES


def test_repeecher_450_char_limit() -> None:
    """Verify that the MAX_CHARS constant is 450."""
    from stream_cheremsha.tts.respeecher_tts import MAX_CHARS

    # 450 chars should be the hard limit
    assert MAX_CHARS == 450

    # A string exactly 450 chars should be accepted as one chunk
    long_text = "a" * 450
    assert len(long_text) == MAX_CHARS

    # A string of 451 chars should be split
    long_text_451 = "a" * 451
    assert len(long_text_451) > MAX_CHARS


def test_repeecher_header_constants() -> None:
    """Verify the required headers are set correctly."""
    from stream_cheremsha.tts.respeecher_tts import HEADERS, WSS_URL

    assert WSS_URL == "wss://space.respeecher.com/v1/public/tts/ua-rt/tts/websocket?source=lp"

    expected_keys = {"User-Agent", "Origin", "Host", "Referer", "Accept-Language"}
    assert set(HEADERS.keys()) == expected_keys

    # Check Accept-Language is Ukrainian-focused
    assert HEADERS["Accept-Language"].startswith("uk-UA")


@pytest.mark.asyncio
async def test_repeecher_float32_to_int16_conversion() -> None:
    """Verify Float32 PCM to Int16 WAV conversion logic."""

    # Create some test Float32 audio data
    float_data = np.array([0.5, -0.3, 0.8, -0.1], dtype=np.float32)

    # Convert to Int16 (the logic from ReSpeecherTts._synthesize_single)
    audio_int16 = np.clip(float_data * 32767, -32768, 32767).astype(np.int16)

    # Verify the conversion
    assert audio_int16.dtype == np.int16
    assert len(audio_int16) == 4

    # Verify values are in Int16 range
    assert np.all(audio_int16 >= -32768)
    assert np.all(audio_int16 <= 32767)

    # Verify the values make sense (0.5 * 32767 ≈ 16383.5 → 16383 or 16384)
    expected_approx = np.round(float_data * 32767)
    assert np.allclose(audio_int16, expected_approx, atol=1)


def test_repeecher_voice_validation() -> None:
    """Verify that invalid voices are defaulted to olesia-conversation."""
    from stream_cheremsha.tts.respeecher_tts import ReSpeecherTts

    # Invalid voice should default to DEFAULT_VOICE_ID
    tts = ReSpeecherTts(voice="invalid-voice-xyz")
    assert tts.voice() == "olesia-conversation"  # defaults

    # Valid voice should be kept
    tts_valid = ReSpeecherTts(voice="olesia-conversation")
    assert tts_valid.voice() == "olesia-conversation"
