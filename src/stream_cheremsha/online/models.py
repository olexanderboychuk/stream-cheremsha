from __future__ import annotations

from datetime import datetime
from typing import Any, TypedDict


class TwitchOnline(TypedDict):
    current: int
    peak: int


class TikTokOnline(TypedDict):
    current: int
    total: int
    gifts: int
    diamonds: int


class YouTubeOnline(TypedDict):
    current: int
    peak: int
    messages: int
    unique: int
    superchats: int
    memberships: int


class KickOnline(TypedDict):
    current: int
    peak: int
    messages: int
    follows: int
    subscriptions: int
    gift_subs: int
    kicks: int


class OnlineState(TypedDict):
    twitch: TwitchOnline
    tiktok: TikTokOnline
    youtube: YouTubeOnline
    kick: KickOnline
    updated_at: str


def now_hms() -> str:
    return datetime.now().strftime("%H:%M:%S")


def online_state_patch(state: OnlineState) -> dict[str, Any]:
    return {"online": state}
