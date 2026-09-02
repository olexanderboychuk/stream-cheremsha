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


def normalize_tts_whitelist_name(name: str) -> str:
    """Normalize a chat nick / @handle for whitelist comparison."""
    return (name or "").strip().lstrip("@").casefold()


def parse_tts_whitelist(raw: str) -> set[str]:
    """Parse comma- or newline-separated usernames into a normalized set."""
    text = (raw or "").strip()
    if not text:
        return set()
    parts = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", ",").split(",")
    return {normalize_tts_whitelist_name(p) for p in parts if p.strip()}


def message_allowed_by_tts_whitelist(message: ChatMessage, raw_whitelist: str) -> bool:
    """True if whitelist is empty or the message author (or TikTok handle) is listed."""
    allowed = parse_tts_whitelist(raw_whitelist)
    if not allowed:
        return True
    candidates = {
        normalize_tts_whitelist_name(message.author),
        normalize_tts_whitelist_name(message.tiktok_unique_id),
    }
    candidates.discard("")
    return bool(candidates & allowed)
