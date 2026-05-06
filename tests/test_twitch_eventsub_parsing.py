from stream_cheremsha.chat.twitch_eventsub import (
    TwitchEventSubCallbacks,
    _dispatch_notification,
    _parse_eventsub_ws_message,
)


def test_parse_welcome_extracts_session_id() -> None:
    raw = '{"metadata":{"message_type":"session_welcome"},"payload":{"session":{"id":"abc123"}}}'
    p = _parse_eventsub_ws_message(raw)
    assert p is not None
    assert p.kind == "welcome"
    assert p.session_id == "abc123"


def test_dispatch_follow_calls_callback() -> None:
    seen: list[str] = []
    cb = TwitchEventSubCallbacks(on_follow=seen.append)
    _dispatch_notification("channel.follow", {"user_name": "alice"}, cb)
    assert seen == ["alice"]


def test_dispatch_sub_resub_passes_message() -> None:
    seen: list[tuple[str, str, int, str]] = []

    def _on_sub(user: str, st: str, m: int, msg: str) -> None:
        seen.append((user, st, m, msg))

    cb = TwitchEventSubCallbacks(on_sub=_on_sub)
    _dispatch_notification(
        "channel.subscription.message",
        {
            "user_name": "bob",
            "cumulative_months": 6,
            "message": {"text": "Still here!"},
        },
        cb,
    )
    assert seen == [("bob", "resub", 6, "Still here!")]
