"""Build/normalize rule trigger event blobs (shared by QML editor + tests)."""

from __future__ import annotations

from typing import Any

from stream_cheremsha.actions.trigger_meta import (
    default_trigger_platform_for_event_type,
    normalize_trigger_platform,
)

_CHAT = "chat_keyword"
_GIFT = "gift_received"

_KIND_VALUES: dict[str, tuple[str, ...]] = {
    "all": (_CHAT,),
    "kick": (
        _CHAT,
        "kick_follow",
        "kick_subscription",
        "kick_gift_sub",
        "kick_gift",
    ),
    "twitch": (
        _CHAT,
        "twitch_follow",
        "twitch_subscribe",
        "twitch_resub",
        "twitch_sub_gift",
        "twitch_cheer",
        "twitch_raid",
    ),
    "youtube": (
        _CHAT,
        "youtube_superchat",
        "youtube_supersticker",
        "youtube_member",
    ),
    "tiktok": (
        _CHAT,
        _GIFT,
        "tiktok_any_gift_received",
        "tiktok_likes_received",
        "tiktok_joined",
        "tiktok_followed",
        "tiktok_shared",
        "tiktok_paid_subscribed",
        "tiktok_first_activity",
    ),
}

_SIMPLE_USER_TYPES = frozenset(
    {
        "twitch_follow",
        "twitch_subscribe",
        "twitch_resub",
        "twitch_sub_gift",
        "tiktok_joined",
        "tiktok_followed",
        "tiktok_paid_subscribed",
        "tiktok_first_activity",
        "youtube_member",
        "kick_follow",
        "kick_subscription",
        "kick_gift_sub",
        "kick_gift",
    }
)


def kind_values_for_platform(platform: str) -> tuple[str, ...]:
    p = normalize_trigger_platform(platform) or "all"
    return _KIND_VALUES.get(p, (_CHAT,))


def kind_allowed_on_platform(kind: str, platform: str) -> bool:
    k = (kind or "").strip()
    return k in kind_values_for_platform(platform)


def _resolved_platform(platform: str, event_type: str) -> str:
    p = normalize_trigger_platform(platform)
    if p is None or p == "all":
        return default_trigger_platform_for_event_type(event_type)
    return p


def _str_param(params: dict[str, Any], key: str, default: str = "") -> str:
    raw = params.get(key, default)
    if raw is None:
        return default
    return str(raw)


def _int_param(params: dict[str, Any], key: str, default: int) -> int:
    raw = params.get(key, default)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def build_trigger_event(
    event_type: str,
    platform: str,
    existing_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a fresh event blob for the Actions editor."""
    t = (event_type or _CHAT).strip()
    ep = dict(existing_params or {})
    plat = _resolved_platform(platform, t)

    if t == _CHAT:
        return {
            "type": _CHAT,
            "platform": plat,
            "params": {
                "text": _str_param(ep, "text"),
                "match": _str_param(ep, "match", "contains") or "contains",
                "case_sensitive": bool(ep.get("case_sensitive", False)),
            },
        }

    if t == _GIFT:
        return {
            "type": _GIFT,
            "platform": plat,
            "params": {
                "gift_id": _str_param(ep, "gift_id"),
                "gift_name": _str_param(ep, "gift_name"),
                "min_count": max(1, _int_param(ep, "min_count", 1)),
            },
        }

    if t == "tiktok_any_gift_received":
        return {
            "type": t,
            "platform": plat,
            "params": {
                "min_price": max(1, _int_param(ep, "min_price", 1)),
                "user": _str_param(ep, "user"),
                "exclude_gifts": list(ep.get("exclude_gifts") or []),
            },
        }

    if t == "tiktok_likes_received":
        return {
            "type": t,
            "platform": plat,
            "params": {
                "min_count": max(1, _int_param(ep, "min_count", 1)),
                "scope": _str_param(ep, "scope", "all_users") or "all_users",
                "user": _str_param(ep, "user"),
            },
        }

    if t == "tiktok_shared":
        return {
            "type": t,
            "platform": plat,
            "params": {
                "min_count": max(1, _int_param(ep, "min_count", 1)),
                "user": _str_param(ep, "user"),
            },
        }

    if t == "twitch_cheer":
        return {
            "type": t,
            "platform": plat,
            "params": {
                "min_bits": max(1, _int_param(ep, "min_bits", 1)),
                "user": _str_param(ep, "user"),
            },
        }

    if t == "twitch_raid":
        return {
            "type": t,
            "platform": plat,
            "params": {
                "min_viewers": max(1, _int_param(ep, "min_viewers", 1)),
                "user": _str_param(ep, "user"),
            },
        }

    if t in ("youtube_superchat", "youtube_supersticker"):
        return {
            "type": t,
            "platform": plat,
            "params": {
                "min_amount": max(0, _int_param(ep, "min_amount", 0)),
                "user": _str_param(ep, "user"),
            },
        }

    if t in _SIMPLE_USER_TYPES:
        return {
            "type": t,
            "platform": plat,
            "params": {"user": _str_param(ep, "user")},
        }

    return build_trigger_event(_CHAT, platform, ep)


def merge_platform_change(current: dict[str, Any], new_platform: str) -> dict[str, Any]:
    """Keep event kind when still valid on ``new_platform``, else reset to chat keyword."""
    cur_type = str(current.get("type") or _CHAT).strip()
    cur_params = current.get("params")
    if not isinstance(cur_params, dict):
        cur_params = {}
    plat = normalize_trigger_platform(new_platform) or "all"
    if kind_allowed_on_platform(cur_type, plat):
        out = dict(current)
        out["platform"] = plat
        return out
    return build_trigger_event(_CHAT, plat)
