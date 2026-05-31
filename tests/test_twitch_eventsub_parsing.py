from stream_cheremsha.chat.twitch_eventsub import (
    TwitchEventSubCallbacks,
    TwitchNotifiedUser,
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
    seen: list[TwitchNotifiedUser] = []
    cb = TwitchEventSubCallbacks(on_follow=seen.append)
    _dispatch_notification(
        "channel.follow",
        {"user_name": "alice", "user_id": "42", "user_login": "alice"},
        cb,
    )
    assert len(seen) == 1
    assert seen[0].display_name == "alice"
    assert seen[0].user_id == "42"
    assert seen[0].login == "alice"


def test_dispatch_follow_falls_back_to_user_login() -> None:
    seen: list[TwitchNotifiedUser] = []
    cb = TwitchEventSubCallbacks(on_follow=seen.append)
    _dispatch_notification("channel.follow", {"user_login": "alice"}, cb)
    assert len(seen) == 1
    assert seen[0].display_name == "alice"
    assert seen[0].login == "alice"


def test_dispatch_sub_resub_passes_message() -> None:
    seen: list[tuple[TwitchNotifiedUser, str, int, str]] = []

    def _on_sub(tu: TwitchNotifiedUser, st: str, m: int, msg: str) -> None:
        seen.append((tu, st, m, msg))

    cb = TwitchEventSubCallbacks(on_sub=_on_sub)
    _dispatch_notification(
        "channel.subscription.message",
        {
            "user_name": "bob",
            "user_id": "9",
            "user_login": "bob",
            "cumulative_months": 6,
            "message": {"text": "Still here!"},
        },
        cb,
    )
    assert len(seen) == 1
    assert seen[0][0].display_name == "bob"
    assert seen[0][0].user_id == "9"
    assert seen[0][1:] == ("resub", 6, "Still here!")
