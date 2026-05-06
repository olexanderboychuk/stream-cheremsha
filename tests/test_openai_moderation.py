from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from stream_cheremsha import l10n
from stream_cheremsha.openai_moderation import (
    moderation_response_should_suppress_tts,
    openai_moderation_flagged,
)


@pytest.mark.asyncio
async def test_openai_moderation_flagged_true() -> None:
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value={"results": [{"flagged": True}]})
    inner = MagicMock()
    inner.post = AsyncMock(return_value=mock_resp)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=inner)
    cm.__aexit__ = AsyncMock(return_value=None)
    with patch("stream_cheremsha.openai_moderation.httpx.AsyncClient", return_value=cm):
        out = await openai_moderation_flagged("sk-test", "text")
    assert out is True


@pytest.mark.asyncio
async def test_openai_moderation_flagged_false() -> None:
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value={"results": [{"flagged": False}]})
    inner = MagicMock()
    inner.post = AsyncMock(return_value=mock_resp)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=inner)
    cm.__aexit__ = AsyncMock(return_value=None)
    with patch("stream_cheremsha.openai_moderation.httpx.AsyncClient", return_value=cm):
        out = await openai_moderation_flagged("sk-test", "nice")
    assert out is False


def test_moderation_blocked_for_tts_by_language() -> None:
    assert "Alice" in l10n.moderation_blocked_for_tts("uk-UA", "Alice")
    assert "Bob" in l10n.moderation_blocked_for_tts("en-US", "Bob")
    assert "Carol" in l10n.moderation_blocked_for_tts("de-DE", "Carol")


def test_tts_chat_author_lead_by_language() -> None:
    assert l10n.tts_chat_author_lead("uk-UA", "X") == "X пише: "
    assert l10n.tts_chat_author_lead("en-US", "X") == "X writes: "
    assert "schreibt" in l10n.tts_chat_author_lead("de-DE", "X")
    assert "pisze" in l10n.tts_chat_author_lead("pl-PL", "X")


# First ``results`` element shaped like omni-moderation-latest (image-linked violence).
_OMNI_IMAGE_VIOLENCE = {
    "flagged": True,
    "categories": {
        "sexual": False,
        "sexual/minors": False,
        "harassment": False,
        "harassment/threatening": False,
        "hate": False,
        "hate/threatening": False,
        "illicit": False,
        "illicit/violent": False,
        "self-harm": False,
        "self-harm/intent": False,
        "self-harm/instructions": False,
        "violence": True,
        "violence/graphic": False,
    },
    "category_scores": {
        "sexual": 2.3e-7,
        "hate": 3.2e-7,
        "harassment": 0.00116,
        "violence": 0.8599,
        "violence/graphic": 0.377,
    },
    "category_applied_input_types": {
        "hate": [],
        "violence": ["image"],
        "violence/graphic": ["image"],
    },
}


def test_moderation_ignores_image_only_violence_when_flagged() -> None:
    assert moderation_response_should_suppress_tts(_OMNI_IMAGE_VIOLENCE) is False


def test_moderation_suppresses_hate_on_text() -> None:
    assert (
        moderation_response_should_suppress_tts(
            {
                "flagged": True,
                "categories": {"hate": True, "violence": False},
                "category_scores": {"hate": 0.91, "violence": 0.01},
                "category_applied_input_types": {"hate": ["text"]},
            },
        )
        is True
    )


def test_moderation_suppresses_strong_hate_score_on_text() -> None:
    assert (
        moderation_response_should_suppress_tts(
            {
                "flagged": True,
                "categories": {"hate": False},
                "category_scores": {"hate": 0.55},
                "category_applied_input_types": {"hate": ["text"]},
            },
        )
        is True
    )


def test_moderation_legacy_flagged_only() -> None:
    assert moderation_response_should_suppress_tts({"flagged": True}) is True
