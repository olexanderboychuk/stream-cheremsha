from __future__ import annotations

import pytest

import stream_cheremsha.music.musicbrainz as mb


def test_build_recording_query_artist_split() -> None:
    q = mb._build_recording_query("Artist Name - Track Title")
    assert q is not None
    assert "Artist Name" in q
    assert "Track Title" in q
    assert "artist:" in q
    assert "recording:" in q


def test_build_recording_query_single() -> None:
    q = mb._build_recording_query("Just a title")
    assert q is not None
    assert q.startswith("recording:")


@pytest.mark.asyncio
async def test_youtube_title_russian_area_true(monkeypatch: pytest.MonkeyPatch) -> None:
    class Resp:
        def __init__(self, code: int, data: dict) -> None:
            self.status_code = code
            self._data = data

        def json(self) -> dict:
            return self._data

    class Client:
        def __init__(self, **kwargs: object) -> None:
            pass

        async def __aenter__(self) -> Client:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def get(self, url: str, headers: object | None = None) -> Resp:
            if "/recording" in url:
                return Resp(
                    200,
                    {
                        "recordings": [
                            {
                                "artist-credit": [
                                    {"artist": {"id": "mbid-ru-1", "name": "RU Act"}},
                                ],
                            },
                        ],
                    },
                )
            if "/artist/mbid-ru-1" in url:
                return Resp(200, {"area": {"name": "Russia", "iso-3166-1-codes": ["RU"]}})
            return Resp(404, {})

    monkeypatch.setattr(
        "stream_cheremsha.music.musicbrainz.httpx.AsyncClient",
        lambda **kw: Client(),
    )
    assert await mb.youtube_title_indicates_russian_artist_area("RU Act - Song") is True


@pytest.mark.asyncio
async def test_youtube_title_uk_not_russia(monkeypatch: pytest.MonkeyPatch) -> None:
    class Resp:
        def __init__(self, code: int, data: dict) -> None:
            self.status_code = code
            self._data = data

        def json(self) -> dict:
            return self._data

    class Client:
        def __init__(self, **kwargs: object) -> None:
            pass

        async def __aenter__(self) -> Client:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def get(self, url: str, headers: object | None = None) -> Resp:
            if "/recording" in url:
                return Resp(
                    200,
                    {
                        "recordings": [
                            {
                                "artist-credit": [
                                    {"artist": {"id": "mbid-uk", "name": "UK Act"}},
                                ],
                            },
                        ],
                    },
                )
            if "/artist/mbid-uk" in url:
                return Resp(
                    200,
                    {"area": {"name": "United Kingdom", "iso-3166-1-codes": ["GB"]}},
                )
            return Resp(404, {})

    monkeypatch.setattr(
        "stream_cheremsha.music.musicbrainz.httpx.AsyncClient",
        lambda **kw: Client(),
    )
    assert await mb.youtube_title_indicates_russian_artist_area("UK Act - Song") is False


@pytest.mark.asyncio
async def test_youtube_title_empty_recordings(monkeypatch: pytest.MonkeyPatch) -> None:
    class Resp:
        def __init__(self, code: int, data: dict) -> None:
            self.status_code = code
            self._data = data

        def json(self) -> dict:
            return self._data

    class Client:
        def __init__(self, **kwargs: object) -> None:
            pass

        async def __aenter__(self) -> Client:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def get(self, url: str, headers: object | None = None) -> Resp:
            return Resp(200, {"recordings": []})

    monkeypatch.setattr(
        "stream_cheremsha.music.musicbrainz.httpx.AsyncClient",
        lambda **kw: Client(),
    )
    assert await mb.youtube_title_indicates_russian_artist_area("Unknown - Xyz") is False
