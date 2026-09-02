from __future__ import annotations

from datetime import UTC, datetime

from stream_cheremsha.domain.models import ChatMessage, ChatPlatform
from stream_cheremsha.pipeline.filters import (
    message_allowed_by_tts_whitelist,
    parse_tts_whitelist,
)


def _msg(
    author: str,
    *,
    platform: ChatPlatform = ChatPlatform.TWITCH,
    tiktok_unique_id: str = "",
) -> ChatMessage:
    return ChatMessage(
        author=author,
        text="hi",
        platform=platform,
        received_at=datetime.now(UTC),
        tiktok_unique_id=tiktok_unique_id,
    )


def test_parse_tts_whitelist_comma_and_newlines() -> None:
    assert parse_tts_whitelist("Alice, @Bob\nCharlie") == {"alice", "bob", "charlie"}
    assert parse_tts_whitelist("  \n  ") == set()


def test_empty_whitelist_allows_everyone() -> None:
    assert message_allowed_by_tts_whitelist(_msg("anyone"), "") is True


def test_whitelist_matches_author_casefold() -> None:
    assert message_allowed_by_tts_whitelist(_msg("Kodi"), "kodi, other") is True
    assert message_allowed_by_tts_whitelist(_msg("nope"), "kodi") is False


def test_tiktok_whitelist_matches_unique_id_not_only_nickname() -> None:
    msg = _msg(
        "🐱 Kodi",
        platform=ChatPlatform.TIKTOK,
        tiktok_unique_id="kodi_the_cat",
    )
    assert message_allowed_by_tts_whitelist(msg, "kodi_the_cat") is True
    assert message_allowed_by_tts_whitelist(msg, "@Kodi_The_Cat") is True
    assert message_allowed_by_tts_whitelist(msg, "someone_else") is False
