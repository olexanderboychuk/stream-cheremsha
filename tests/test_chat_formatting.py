"""Tests for chat HTML formatting (stdlib parts)."""

from __future__ import annotations

from datetime import UTC, datetime

from stream_cheremsha.domain.models import ChatMessage, ChatPlatform
from stream_cheremsha.ui.chat_formatting import (
    CHAT_DEFAULT_FONT_FAMILY,
    author_color_hex,
    chat_font_stack_css,
    format_chat_message_html,
)


def test_author_color_hex_stable() -> None:
    assert author_color_hex("SomeUser") == author_color_hex("SomeUser")
    assert author_color_hex("SomeUser") != author_color_hex("OtherUser")
    assert author_color_hex("USER") == author_color_hex("user")


def test_author_color_hex_format() -> None:
    c = author_color_hex("x")
    assert c.startswith("#")
    assert len(c) == 7


def test_chat_font_stack_css_quotes_primary() -> None:
    s = chat_font_stack_css("Segoe UI")
    assert "Segoe UI" in s
    assert "Segoe UI Emoji" in s


def test_chat_font_stack_css_default_when_empty() -> None:
    s = chat_font_stack_css("")
    assert CHAT_DEFAULT_FONT_FAMILY in s


def test_format_chat_message_html_escapes_markup() -> None:
    msg = ChatMessage(
        author="<b>x</b>",
        text='hello & "quotes"',
        platform=ChatPlatform.TWITCH,
        received_at=datetime(2026, 1, 2, 15, 4, 5, tzinfo=UTC),
    )
    html_out = format_chat_message_html(
        msg,
        font_pt=13,
        font_stack_css="'Segoe UI',sans-serif",
        twitch_icon_uri=None,
        youtube_icon_uri=None,
    )
    assert "<b>" not in html_out
    assert "&lt;b&gt;x&lt;/b&gt;" in html_out
    assert "hello &amp; &quot;quotes&quot;" in html_out


def test_format_chat_message_html_preserves_emoji() -> None:
    msg = ChatMessage(
        author="fan",
        text="GG \U0001f389",
        platform=ChatPlatform.YOUTUBE,
        received_at=datetime(2026, 1, 2, 12, 0, 0, tzinfo=UTC),
    )
    html_out = format_chat_message_html(
        msg,
        font_pt=12,
        font_stack_css="'Segoe UI',sans-serif",
        twitch_icon_uri=None,
        youtube_icon_uri=None,
    )
    assert "\U0001f389" in html_out
