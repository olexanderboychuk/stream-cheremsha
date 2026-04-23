from __future__ import annotations

from datetime import UTC, datetime

import pytest

from stream_cheremsha.chat.youtube_source import parse_google_desktop_client_json
from stream_cheremsha.domain.models import ChatMessage, ChatPlatform
from stream_cheremsha.pipeline.chunking import chunk_text, merge_short_subchunks
from stream_cheremsha.pipeline.filters import filter_for_tts


def test_filter_empty() -> None:
    m = ChatMessage(
        author="a",
        text="   ",
        platform=ChatPlatform.TWITCH,
        received_at=datetime.now(UTC),
    )
    assert filter_for_tts(m) is None


def test_filter_truncates() -> None:
    long = "x" * 500
    m = ChatMessage(
        author="a",
        text=long,
        platform=ChatPlatform.TWITCH,
        received_at=datetime.now(UTC),
    )
    out = filter_for_tts(m)
    assert out is not None
    assert len(out) == 400


def test_chunk_single() -> None:
    assert chunk_text("hello") == ["hello"]


def test_chunk_splits() -> None:
    parts = chunk_text("word " * 50, max_chars=40)
    assert len(parts) > 1
    assert all(len(p) <= 40 for p in parts)


def test_merge_combines_short_tails() -> None:
    parts = ["a" * 100, "b" * 5]
    m = merge_short_subchunks(parts, min_chars=40, max_chars=180)
    assert m == ["a" * 100 + " " + "b" * 5]


def test_merge_respects_max_len() -> None:
    a, b = "a" * 100, "b" * 100
    m = merge_short_subchunks([a, b], min_chars=40, max_chars=180)
    assert m == [a, b]


def test_merge_forward_fill_to_min() -> None:
    m = merge_short_subchunks(
        ["a" * 20, "b" * 20, "c" * 20],
        min_chars=40,
        max_chars=100,
    )
    assert len(m) == 1
    assert " " in m[0]


def test_youtube_client_json_requires_installed() -> None:
    with pytest.raises(ValueError, match="installed"):
        parse_google_desktop_client_json('{"web": {}}')
