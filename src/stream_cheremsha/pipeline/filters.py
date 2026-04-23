from __future__ import annotations

from stream_cheremsha.config.constants import MAX_MESSAGE_CHARS
from stream_cheremsha.domain.models import ChatMessage


def filter_for_tts(message: ChatMessage) -> str | None:
    """Return text to speak, or None if the message should be skipped (MVP rules)."""
    text = (message.text or "").strip()
    if not text:
        return None
    if len(text) > MAX_MESSAGE_CHARS:
        text = text[:MAX_MESSAGE_CHARS]
    return text
