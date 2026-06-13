"""Per-trigger platform metadata (optional `platform` on each rule event blob)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from stream_cheremsha.domain.models import ChatPlatform

ALLOWED_TRIGGER_PLATFORMS: frozenset[str] = frozenset({"all", "tiktok", "twitch", "youtube"})


def normalize_trigger_platform(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    s = raw.strip().lower()
    return s if s in ALLOWED_TRIGGER_PLATFORMS else None


def default_trigger_platform_for_event_type(event_type: str) -> str:
    t = (event_type or "").strip()
    if t == "chat_keyword":
        return "all"
    if t.startswith("twitch_"):
        return "twitch"
    if t.startswith("youtube_"):
        return "youtube"
    return "tiktok"


def trigger_platform_effective(ev_blob: Mapping[str, Any]) -> str:
    """Platform for matching: explicit JSON `platform` or legacy default by event type."""
    n = normalize_trigger_platform(ev_blob.get("platform"))
    if n is not None:
        return n
    return default_trigger_platform_for_event_type(str(ev_blob.get("type") or ""))


def trigger_platform_applies_to_chat(ev_blob: Mapping[str, Any], platform: ChatPlatform) -> bool:
    tp = trigger_platform_effective(ev_blob)
    if tp == "all":
        return True
    return tp == platform.value


def trigger_platform_applies_to_gift(ev_blob: Mapping[str, Any], ev_platform: ChatPlatform) -> bool:
    tp = trigger_platform_effective(ev_blob)
    if tp == "all":
        return True
    return tp == ev_platform.value


def trigger_platform_applies_to_tiktok_likes(ev_blob: Mapping[str, Any]) -> bool:
    """Likes pipeline is TikTok-only; `all` means the same for now."""
    tp = trigger_platform_effective(ev_blob)
    return tp in frozenset({"all", "tiktok"})


def trigger_platform_applies_to_twitch_channel_events(ev_blob: Mapping[str, Any]) -> bool:
    tp = trigger_platform_effective(ev_blob)
    return tp in frozenset({"all", "twitch"})


def trigger_platform_applies_to_youtube_channel_events(ev_blob: Mapping[str, Any]) -> bool:
    tp = trigger_platform_effective(ev_blob)
    return tp in frozenset({"all", "youtube"})


def chat_platform_for_preview(trigger_platform: str, *, store_platform: str) -> ChatPlatform:
    """Pick a concrete ChatPlatform for previewing chat_keyword."""
    tp = (trigger_platform or "all").strip().lower()
    if tp == "twitch":
        return ChatPlatform.TWITCH
    if tp == "youtube":
        return ChatPlatform.YOUTUBE
    if tp == "tiktok":
        return ChatPlatform.TIKTOK
    sp = (store_platform or "tiktok").strip().lower()
    if sp == "twitch":
        return ChatPlatform.TWITCH
    if sp == "youtube":
        return ChatPlatform.YOUTUBE
    return ChatPlatform.TIKTOK
