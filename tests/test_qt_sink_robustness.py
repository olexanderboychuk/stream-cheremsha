from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest
from PySide6.QtMultimedia import QMediaPlayer

from stream_cheremsha.audio import qt_sink


@pytest.mark.asyncio
async def test_safe_resolve_fut_result() -> None:
    loop = asyncio.get_running_loop()
    fut: asyncio.Future[None] = loop.create_future()
    qt_sink.QtAudioSink._safe_resolve_fut(fut)
    await fut
    assert fut.done() and not fut.cancelled()


@pytest.mark.asyncio
async def test_safe_resolve_fut_exception() -> None:
    loop = asyncio.get_running_loop()
    fut: asyncio.Future[None] = loop.create_future()
    qt_sink.QtAudioSink._safe_resolve_fut(fut, exception=RuntimeError("test-err"))
    with pytest.raises(RuntimeError, match="test-err"):
        await fut


@pytest.mark.asyncio
async def test_media_status_invalid_media_sets_exception() -> None:
    sink = qt_sink.QtAudioSink()
    loop = asyncio.get_running_loop()
    fut: asyncio.Future[None] = loop.create_future()
    sink._pending_fut = fut

    sink._on_media_status(QMediaPlayer.MediaStatus.InvalidMedia)
    with pytest.raises(RuntimeError, match="InvalidMedia"):
        await fut


@pytest.mark.asyncio
async def test_media_status_end_of_media_resolves_future() -> None:
    sink = qt_sink.QtAudioSink()
    loop = asyncio.get_running_loop()
    fut: asyncio.Future[None] = loop.create_future()
    sink._pending_fut = fut

    sink._on_media_status(QMediaPlayer.MediaStatus.EndOfMedia)
    await fut
    assert fut.done() and not fut.cancelled()


@pytest.mark.asyncio
async def test_playback_state_stopped_resolves_future() -> None:
    sink = qt_sink.QtAudioSink()
    loop = asyncio.get_running_loop()
    fut: asyncio.Future[None] = loop.create_future()
    sink._pending_fut = fut
    sink._tts_play_started = True  # simulate play() was called

    sink._on_playback_state(QMediaPlayer.PlaybackState.StoppedState)
    await fut
    assert fut.done() and not fut.cancelled()


@pytest.mark.asyncio
async def test_playback_state_stopped_does_not_resolve_before_play() -> None:
    """StoppedState fired by setSource() before play() must NOT resolve the future."""
    sink = qt_sink.QtAudioSink()
    loop = asyncio.get_running_loop()
    fut: asyncio.Future[None] = loop.create_future()
    sink._pending_fut = fut
    sink._tts_play_started = False  # play() not yet called

    sink._on_playback_state(QMediaPlayer.PlaybackState.StoppedState)
    assert not fut.done(), "Future must not be resolved by StoppedState before play() is called"


@pytest.mark.asyncio
async def test_shutdown_cancels_pending_future() -> None:
    sink = qt_sink.QtAudioSink()
    loop = asyncio.get_running_loop()
    fut: asyncio.Future[None] = loop.create_future()
    sink._pending_fut = fut

    fake_player = MagicMock()
    sink._player = fake_player

    sink.shutdown()

    assert sink._pending_fut is None
    assert fut.cancelled()
    fake_player.stop.assert_called_once()


@pytest.mark.asyncio
async def test_play_mp3_locked_watchdog_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    sink = qt_sink.QtAudioSink()
    fake_player = MagicMock()
    fake_player.audioOutput.return_value = MagicMock()
    sink._player = fake_player
    sink._audio = fake_player.audioOutput.return_value

    monkeypatch.setattr(sink, "ensure_ready", lambda: None)
    monkeypatch.setattr(qt_sink, "_try_louder_mp3", lambda data, _g: data)
    monkeypatch.setattr(qt_sink, "_write_temp_audio", lambda _d: MagicMock())

    # Replace asyncio.wait_for with a mock that triggers TimeoutError immediately
    async def fake_wait_for(fut, timeout):
        raise TimeoutError()

    monkeypatch.setattr(asyncio, "wait_for", fake_wait_for)

    # Should not raise TimeoutError or hang, must cleanly stop player and return
    await sink._play_mp3_locked(b"fake-mp3-bytes")

    assert sink._pending_fut is None
    fake_player.stop.assert_called()


def test_ensure_ready_creates_distinct_sfx_player() -> None:
    sink = qt_sink.QtAudioSink()
    sink.ensure_ready()
    assert sink._player is not None
    assert sink._audio is not None
    assert sink._sfx_player is not None
    assert sink._sfx_audio is not None
    # Verify SFX player has its own distinct audio output and does not hijack _audio
    assert sink._player.audioOutput() is sink._audio
    assert sink._sfx_player.audioOutput() is sink._sfx_audio
    assert sink._audio is not sink._sfx_audio
    sink.shutdown()
