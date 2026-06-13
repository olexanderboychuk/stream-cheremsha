from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from stream_cheremsha.domain.models import ChatPlatform


@dataclass(frozen=True, slots=True)
class ChatMessageEvent:
    platform: ChatPlatform
    author: str
    text: str
    received_at: datetime
    profile_picture_url: str = ""


@dataclass(frozen=True, slots=True)
class GiftReceivedEvent:
    platform: ChatPlatform
    sender: str
    gift_id: str
    gift_name: str
    count: int
    gift_icon_url: str
    received_at: datetime
    sender_avatar_url: str = ""
    #: TikTok Live: diamonds/coins per gift unit from the stream when catalog lookup misses.
    tiktok_coin_each: int = 0


@dataclass(frozen=True, slots=True)
class TikTokLikesReceivedEvent:
    """Dispatched when a TikTok likes rule matches (batch size and scope total for placeholders)."""

    platform: ChatPlatform
    user: str
    likes_in_batch: int
    likes_total_for_scope: int
    received_at: datetime
    profile_picture_url: str = ""


@dataclass(frozen=True, slots=True)
class TikTokJoinedEvent:
    platform: ChatPlatform
    user: str
    received_at: datetime


@dataclass(frozen=True, slots=True)
class TikTokFollowedEvent:
    platform: ChatPlatform
    user: str
    received_at: datetime


@dataclass(frozen=True, slots=True)
class TikTokSharedEvent:
    platform: ChatPlatform
    user: str
    count: int
    received_at: datetime


@dataclass(frozen=True, slots=True)
class TikTokPaidSubscribedEvent:
    platform: ChatPlatform
    user: str
    received_at: datetime


@dataclass(frozen=True, slots=True)
class TikTokFirstActivityEvent:
    platform: ChatPlatform
    kind: str
    user: str
    count: int
    received_at: datetime


@dataclass(frozen=True, slots=True)
class TwitchFollowEvent:
    platform: ChatPlatform
    user: str
    received_at: datetime
    profile_picture_url: str = ""


@dataclass(frozen=True, slots=True)
class TwitchSubscribeEvent:
    """New channel subscription (channel.subscribe)."""

    platform: ChatPlatform
    user: str
    months: int
    received_at: datetime
    profile_picture_url: str = ""


@dataclass(frozen=True, slots=True)
class TwitchResubscribeEvent:
    """Resub with optional message (channel.subscription.message)."""

    platform: ChatPlatform
    user: str
    months: int
    message: str
    received_at: datetime
    profile_picture_url: str = ""


@dataclass(frozen=True, slots=True)
class TwitchSubscriptionGiftEvent:
    """Gift subscription (channel.subscription.gift); user is the gifter when known."""

    platform: ChatPlatform
    user: str
    months: int
    received_at: datetime
    profile_picture_url: str = ""


@dataclass(frozen=True, slots=True)
class TwitchCheerEvent:
    platform: ChatPlatform
    user: str
    bits: int
    received_at: datetime
    profile_picture_url: str = ""


@dataclass(frozen=True, slots=True)
class TwitchRaidEvent:
    platform: ChatPlatform
    raider: str
    viewers: int
    received_at: datetime
    profile_picture_url: str = ""


@dataclass(frozen=True, slots=True)
class YouTubeSuperChatEvent:
    """YouTube Super Chat (superChatEvent). `amount_micros` is the tip in currency micros."""

    platform: ChatPlatform
    user: str
    amount_micros: int
    currency: str
    amount_display: str
    message: str
    received_at: datetime
    profile_picture_url: str = ""


@dataclass(frozen=True, slots=True)
class YouTubeSuperStickerEvent:
    """YouTube Super Sticker (superStickerEvent). `amount_micros` is the tip in currency micros."""

    platform: ChatPlatform
    user: str
    amount_micros: int
    currency: str
    amount_display: str
    received_at: datetime
    profile_picture_url: str = ""


@dataclass(frozen=True, slots=True)
class YouTubeMemberEvent:
    """YouTube membership (newSponsorEvent / memberMilestoneChatEvent).

    `months` is the milestone month count (0 for a brand-new member); `level` is the membership
    tier name when YouTube provides it.
    """

    platform: ChatPlatform
    user: str
    months: int
    level: str
    received_at: datetime
    profile_picture_url: str = ""
