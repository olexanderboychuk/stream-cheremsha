from __future__ import annotations

from datetime import datetime, timezone

from stream_cheremsha.actions.action_placeholders import apply_action_placeholders
from stream_cheremsha.actions.events import ChatMessageEvent, GiftReceivedEvent
from stream_cheremsha.domain.models import ChatPlatform


def test_gift_placeholders_giftcount_and_names() -> None:
    ev = GiftReceivedEvent(
        platform=ChatPlatform.TIKTOK,
        sender="viewer1",
        gift_id="gid",
        gift_name="Rose",
        count=7,
        received_at=datetime.now(tz=timezone.utc),
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
        received_at=datetime.now(tz=timezone.utc),
    )
    assert apply_action_placeholders("{author}: {text}", ev) == "bob: hello"
    assert apply_action_placeholders("{giftcount}", ev) == "{giftcount}"
