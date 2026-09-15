from __future__ import annotations

from datetime import UTC, datetime

from stream_cheremsha.actions.action_placeholders import apply_action_placeholders
from stream_cheremsha.actions.events import (
    ChatMessageEvent,
    GiftReceivedEvent,
    TikTokFirstActivityEvent,
    TikTokFollowedEvent,
    TikTokJoinedEvent,
    TikTokLikesReceivedEvent,
    TikTokPaidSubscribedEvent,
    TikTokSharedEvent,
    TwitchCheerEvent,
    YouTubeMemberEvent,
    YouTubeSuperChatEvent,
)
from stream_cheremsha.domain.models import ChatPlatform


def test_gift_placeholders_giftcount_and_names() -> None:
    ev = GiftReceivedEvent(
        platform=ChatPlatform.TIKTOK,
        sender="viewer1",
        gift_id="gid",
        gift_name="Rose",
        count=7,
        gift_icon_url="",
        received_at=datetime.now(tz=UTC),
    )
    assert apply_action_placeholders('--preset "x" --n {giftcount}', ev) == '--preset "x" --n 7'
    assert apply_action_placeholders("{giftname} {GIFT_NAME}", ev) == "Rose Rose"
    assert apply_action_placeholders("{sender} {platform}", ev) == "viewer1 tiktok"
    assert apply_action_placeholders("{giftcount-1}", ev) == "6"
    assert apply_action_placeholders("{giftcount-1*2}", ev) == "5"
    assert apply_action_placeholders("{(giftcount-1)*2}", ev) == "12"
    assert apply_action_placeholders("{giftcount/2}", ev) == "3"
    assert apply_action_placeholders("{giftname-1}", ev) == "{giftname-1}"


def test_chat_placeholders() -> None:
    ev = ChatMessageEvent(
        platform=ChatPlatform.TWITCH,
        author="bob",
        text="hello",
        received_at=datetime.now(tz=UTC),
    )
    assert apply_action_placeholders("{author}: {text}", ev) == "bob: hello"
    assert apply_action_placeholders("{giftcount}", ev) == "{giftcount}"


def test_tiktok_likes_placeholders() -> None:
    ev = TikTokLikesReceivedEvent(
        platform=ChatPlatform.TIKTOK,
        user="bob",
        likes_in_batch=5,
        likes_total_for_scope=120,
        received_at=datetime.now(tz=UTC),
    )
    assert (
        apply_action_placeholders("{sender} +{likebatch} total {liketotal}", ev)
        == "bob +5 total 120"
    )


def test_tiktok_joined_placeholders() -> None:
    ev = TikTokJoinedEvent(
        platform=ChatPlatform.TIKTOK,
        user="bob",
        received_at=datetime.now(tz=UTC),
    )
    assert apply_action_placeholders("{user} {sender} {platform}", ev) == "bob bob tiktok"


def test_tiktok_followed_placeholders() -> None:
    ev = TikTokFollowedEvent(
        platform=ChatPlatform.TIKTOK,
        user="bob",
        received_at=datetime.now(tz=UTC),
    )
    assert apply_action_placeholders("{user} {sender} {platform}", ev) == "bob bob tiktok"


def test_tiktok_shared_placeholders_count() -> None:
    ev = TikTokSharedEvent(
        platform=ChatPlatform.TIKTOK,
        user="bob",
        count=3,
        received_at=datetime.now(tz=UTC),
    )
    assert apply_action_placeholders("{user} x{count} {platform}", ev) == "bob x3 tiktok"


def test_tiktok_paid_subscribed_placeholders() -> None:
    ev = TikTokPaidSubscribedEvent(
        platform=ChatPlatform.TIKTOK,
        user="bob",
        received_at=datetime.now(tz=UTC),
    )
    assert apply_action_placeholders("{user} {sender} {platform}", ev) == "bob bob tiktok"


def test_twitch_cheer_placeholders() -> None:
    ev = TwitchCheerEvent(
        platform=ChatPlatform.TWITCH,
        user="alice",
        bits=100,
        received_at=datetime.now(tz=UTC),
    )
    assert apply_action_placeholders("{user} {bits} {platform}", ev) == "alice 100 twitch"


def test_tiktok_first_activity_placeholders_kind() -> None:
    ev = TikTokFirstActivityEvent(
        platform=ChatPlatform.TIKTOK,
        kind="share",
        user="bob",
        count=3,
        received_at=datetime.now(tz=UTC),
    )
    assert apply_action_placeholders("{kind} {user} {count}", ev) == "share bob 3"


def test_gift_username_repeatcount_aliases() -> None:
    ev = GiftReceivedEvent(
        platform=ChatPlatform.TIKTOK,
        sender="viewer1",
        gift_id="gid",
        gift_name="Rose",
        count=7,
        gift_icon_url="",
        received_at=datetime.now(tz=UTC),
    )
    assert (
        apply_action_placeholders("{username} {nickname} {repeatcount}", ev) == "viewer1 viewer1 7"
    )


def test_chat_comment_username_aliases() -> None:
    ev = ChatMessageEvent(
        platform=ChatPlatform.TWITCH,
        author="bob",
        text="hello",
        received_at=datetime.now(tz=UTC),
    )
    assert apply_action_placeholders("{comment} {username}", ev) == "hello bob"


def test_youtube_superchat_placeholders() -> None:
    ev = YouTubeSuperChatEvent(
        platform=ChatPlatform.YOUTUBE,
        user="alice",
        amount_micros=5_000_000,
        currency="USD",
        amount_display="$5.00",
        message="great stream",
        received_at=datetime.now(tz=UTC),
    )
    assert (
        apply_action_placeholders("{user} {amount} {amount_value} {currency} {platform}", ev)
        == "alice $5.00 5 USD youtube"
    )
    assert apply_action_placeholders("{message}", ev) == "great stream"


def test_youtube_member_placeholders() -> None:
    ev = YouTubeMemberEvent(
        platform=ChatPlatform.YOUTUBE,
        user="bob",
        months=3,
        level="Gold",
        received_at=datetime.now(tz=UTC),
    )
    assert (
        apply_action_placeholders("{user} {months} {level} {platform}", ev) == "bob 3 Gold youtube"
    )


def test_kick_placeholders() -> None:
    from stream_cheremsha.actions.events import (
        KickFollowEvent,
        KickGiftEvent,
        KickGiftSubscriptionEvent,
        KickSubscriptionEvent,
    )

    now = datetime.now(tz=UTC)
    assert (
        apply_action_placeholders(
            "{user} {platform}",
            KickFollowEvent(platform=ChatPlatform.KICK, user="k", received_at=now),
        )
        == "k kick"
    )
    assert (
        apply_action_placeholders(
            "{user} {months} {submonth}",
            KickSubscriptionEvent(platform=ChatPlatform.KICK, user="k", months=2, received_at=now),
        )
        == "k 2 2"
    )
    assert (
        apply_action_placeholders(
            "{user} {count}",
            KickGiftSubscriptionEvent(platform=ChatPlatform.KICK, user="k", count=3, received_at=now),
        )
        == "k 3"
    )
    assert (
        apply_action_placeholders(
            "{user} {amount} {count}",
            KickGiftEvent(platform=ChatPlatform.KICK, user="k", amount=50, received_at=now),
        )
        == "k 50 50"
    )


def test_placeholder_reference_covers_all_context_branches() -> None:
    from stream_cheremsha.actions import action_placeholders as ap
    from stream_cheremsha.actions.events import (
        DonateReceivedEvent,
        KickFollowEvent,
        TikTokJoinedEvent,
        TikTokSharedEvent,
        TwitchRaidEvent,
        TwitchResubscribeEvent,
        TwitchSubscribeEvent,
    )

    ref = ap.placeholder_reference("uk")
    assert len(ref) >= 10
    triggers_text = " ".join(str(c["triggers"]) for c in ref)
    for token in (
        "chat_keyword",
        "gift_received",
        "tiktok_likes_received",
        "twitch_cheer",
        "twitch_raid",
        "youtube_superchat",
        "donate",
        "kick_gift",
    ):
        assert token in triggers_text
    # Every key produced by build_placeholder_context must be documented.
    documented: set[str] = set()
    for cat in ref:
        for v in cat["vars"]:
            assert isinstance(v, dict) and v["names"] and (v.get("uk") or v.get("en"))
            documented.update(str(n).strip("{}") for n in v["names"])
    now = datetime.now(tz=UTC)
    samples = [
        ChatMessageEvent(platform=ChatPlatform.TIKTOK, author="a", text="t", received_at=now),
        GiftReceivedEvent(
            platform=ChatPlatform.TIKTOK,
            sender="s",
            gift_id="g",
            gift_name="n",
            count=1,
            gift_icon_url="",
            received_at=now,
        ),
        TikTokLikesReceivedEvent(
            platform=ChatPlatform.TIKTOK,
            user="u",
            likes_in_batch=1,
            likes_total_for_scope=2,
            received_at=now,
        ),
        TikTokJoinedEvent(platform=ChatPlatform.TIKTOK, user="u", received_at=now),
        TikTokSharedEvent(platform=ChatPlatform.TIKTOK, user="u", count=1, received_at=now),
        TwitchSubscribeEvent(
            platform=ChatPlatform.TWITCH, user="u", months=1, received_at=now
        ),
        TwitchResubscribeEvent(
            platform=ChatPlatform.TWITCH, user="u", months=1, message="m", received_at=now
        ),
        TwitchRaidEvent(platform=ChatPlatform.TWITCH, raider="r", viewers=5, received_at=now),
        DonateReceivedEvent(
            platform=ChatPlatform.DONATIK,
            user="u",
            amount=10.0,
            currency="UAH",
            message="m",
            received_at=now,
        ),
        KickFollowEvent(platform=ChatPlatform.KICK, user="u", received_at=now),
    ]
    for ev in samples:
        missing = set(ap.build_placeholder_context(ev)) - documented
        assert not missing, f"undocumented placeholders for {type(ev).__name__}: {missing}"
