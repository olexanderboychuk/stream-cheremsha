from __future__ import annotations

import asyncio
import threading
import time
from unittest.mock import MagicMock

from google.oauth2.credentials import Credentials

from stream_cheremsha.chat.youtube_source import _YouTubeDataApiRunner


def _fake_creds() -> Credentials:
    return Credentials(
        token="tok",
        refresh_token="ref",
        token_uri="https://oauth2.googleapis.com/token",
        client_id="cid",
        client_secret="sec",
        scopes=["https://www.googleapis.com/auth/youtube.readonly"],
    )


def test_data_api_runner_serializes_concurrent_invokes(monkeypatch) -> None:
    """Two asyncio tasks must not execute API work on the runner thread at once."""
    runner = _YouTubeDataApiRunner()
    creds = _fake_creds()
    active = 0
    peak = 0
    lock = threading.Lock()

    def slow_api(_service: object, label: str) -> str:
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.05)
        with lock:
            active -= 1
        return label

    monkeypatch.setattr(
        "stream_cheremsha.chat.youtube_source._build_youtube_service",
        lambda _c: MagicMock(name="youtube-service"),
    )

    async def _run() -> None:
        results = await asyncio.gather(
            runner.invoke(creds, slow_api, "a"),
            runner.invoke(creds, slow_api, "b"),
        )
        assert sorted(results) == ["a", "b"]

    asyncio.run(_run())
    assert peak == 1
    runner.shutdown()


def test_data_api_runner_reuses_service_for_same_creds(monkeypatch) -> None:
    runner = _YouTubeDataApiRunner()
    creds = _fake_creds()
    builds = 0

    def fake_build(c: Credentials) -> object:
        nonlocal builds
        builds += 1
        assert c is creds
        return MagicMock(name=f"service-{builds}")

    monkeypatch.setattr(
        "stream_cheremsha.chat.youtube_source._build_youtube_service",
        fake_build,
    )

    async def _run() -> None:
        await runner.invoke(creds, lambda s: s)
        await runner.invoke(creds, lambda s: s)

    asyncio.run(_run())
    assert builds == 1
    runner.shutdown()
