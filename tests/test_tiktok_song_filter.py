from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from stream_cheremsha.telegram.tiktok_song_filter import (
    TikTokLyricsCheckError,
    TikTokLyricsVerdict,
    _extract_json_object,
    analyze_lyrics_with_groq,
    fetch_lyrics_for_youtube_title,
    format_tiktok_reject_reason,
)


def test_extract_json_object_plain() -> None:
    raw = '{"status": "Safe", "risk_score": 5, "violations": [], "dangerous_segments": []}'
    d = _extract_json_object(raw)
    assert d is not None
    assert d.get("status") == "Safe"


def test_extract_json_object_fenced() -> None:
    raw = '```json\n{"status": "Banned"}\n```'
    d = _extract_json_object(raw)
    assert d is not None
    assert d.get("status") == "Banned"


def test_format_tiktok_reject_reason_risky_en() -> None:
    v = TikTokLyricsVerdict(
        status="Risky",
        risk_score=42,
        violations=["x"],
        dangerous_segments=[],
    )
    s = format_tiktok_reject_reason(v, ui_locale="en")
    assert "add this track" in s.lower()
    assert "risky" not in s.lower()


def test_format_tiktok_reject_reason_banned_uk() -> None:
    v = TikTokLyricsVerdict(
        status="Banned",
        risk_score=None,
        violations=[],
        dangerous_segments=[],
    )
    s = format_tiktok_reject_reason(v, ui_locale="uk")
    assert "не додали" in s.lower() or "Не додали" in s
    assert "banned" not in s.lower()


@pytest.mark.asyncio
async def test_analyze_lyrics_with_groq_success() -> None:
    inner_json = json.dumps(
        {
            "status": "Safe",
            "risk_score": 3,
            "violations": [],
            "dangerous_segments": [],
        },
    )
    payload = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": inner_json,
                },
            },
        ],
    }
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value=payload)
    inner = MagicMock()
    inner.post = AsyncMock(return_value=mock_resp)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=inner)
    cm.__aexit__ = AsyncMock(return_value=None)
    with patch("stream_cheremsha.telegram.tiktok_song_filter.httpx.AsyncClient", return_value=cm):
        out = await analyze_lyrics_with_groq("gsk-test", "la la la", "en", youtube_title="A - B")
    assert out.status == "Safe"
    assert out.allows_enqueue() is True


@pytest.mark.asyncio
async def test_analyze_lyrics_with_groq_title_only() -> None:
    inner_json = json.dumps(
        {
            "status": "Risky",
            "risk_score": 55,
            "violations": ["uncertain"],
            "dangerous_segments": [],
        },
    )
    payload = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": inner_json,
                },
            },
        ],
    }
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value=payload)
    inner = MagicMock()
    inner.post = AsyncMock(return_value=mock_resp)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=inner)
    cm.__aexit__ = AsyncMock(return_value=None)
    with patch("stream_cheremsha.telegram.tiktok_song_filter.httpx.AsyncClient", return_value=cm):
        out = await analyze_lyrics_with_groq(
            "gsk-test",
            "",
            "en",
            youtube_title="Some Artist - Track Name",
        )
    assert out.status == "Risky"
    assert out.allows_enqueue() is False
    sent = inner.post.await_args
    assert sent is not None
    user_msg = sent.kwargs["json"]["messages"][1]["content"]
    assert "No lyrics" in user_msg
    assert "Some Artist - Track Name" in user_msg


@pytest.mark.asyncio
async def test_analyze_lyrics_groq_429_message_en() -> None:
    err_body = json.dumps({"error": {"message": "Rate limit exceeded"}})
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = err_body
    mock_resp.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "x",
            request=MagicMock(),
            response=mock_resp,
        ),
    )
    inner = MagicMock()
    inner.post = AsyncMock(return_value=mock_resp)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=inner)
    cm.__aexit__ = AsyncMock(return_value=None)
    with patch("stream_cheremsha.telegram.tiktok_song_filter.httpx.AsyncClient", return_value=cm):
        with pytest.raises(TikTokLyricsCheckError) as ei:
            await analyze_lyrics_with_groq("gsk-test", "lyrics", "en")
    msg = str(ei.value).lower()
    assert "429" not in msg
    assert "busy" in msg or "wait" in msg or "minute" in msg


@pytest.mark.asyncio
async def test_analyze_lyrics_with_groq_http_error() -> None:
    mock_resp = MagicMock()
    mock_resp.is_success = False
    mock_resp.status_code = 400
    mock_resp.text = "bad"
    mock_resp.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "x",
            request=MagicMock(),
            response=mock_resp,
        ),
    )
    inner = MagicMock()
    inner.post = AsyncMock(return_value=mock_resp)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=inner)
    cm.__aexit__ = AsyncMock(return_value=None)
    with patch("stream_cheremsha.telegram.tiktok_song_filter.httpx.AsyncClient", return_value=cm):
        with pytest.raises(TikTokLyricsCheckError) as ei:
            await analyze_lyrics_with_groq("gsk", "lyrics", "en")
    assert "400" not in str(ei.value)
    assert "wrong" in str(ei.value).lower() or "something" in str(ei.value).lower()


def test_fetch_lyrics_for_youtube_title_empty_token() -> None:
    assert fetch_lyrics_for_youtube_title("", "Some - Title") is None
