import asyncio
import base64
import hashlib
from datetime import UTC, datetime
from unittest.mock import AsyncMock

from stream_cheremsha.chat.kick_api import (
    KickApiClient,
    KickOAuthConfig,
    build_authorize_url,
    generate_pkce,
)
from stream_cheremsha.chat.kick_pusher import (
    parse_chat_message,
    parse_pusher_envelope,
    resolve_chatroom_id,
)
from stream_cheremsha.chat.kick_source import KickSource
from stream_cheremsha.domain.models import ChatMessage, ChatPlatform


def test_generate_pkce_s256_challenge_matches_verifier() -> None:
    pkce = generate_pkce()
    assert len(pkce.verifier) >= 43
    digest = hashlib.sha256(pkce.verifier.encode("ascii")).digest()
    expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    assert pkce.challenge == expected


def test_build_authorize_url_contains_required_params() -> None:
    cfg = KickOAuthConfig(
        client_id="cid",
        client_secret="sec",
        redirect_uri="http://localhost/callback",
    )
    pkce = generate_pkce()
    url = build_authorize_url(cfg, pkce, "state123")
    assert "response_type=code" in url
    assert "client_id=cid" in url
    assert "redirect_uri=http%3A%2F%2Flocalhost%2Fcallback" in url
    assert "code_challenge=" in url
    assert "code_challenge_method=S256" in url
    assert "state=state123" in url
    assert pkce.challenge in url


def test_oauth_config_from_env(monkeypatch) -> None:
    monkeypatch.setenv("STREAM_CHEREMSHA_KICK_CLIENT_ID", "c")
    monkeypatch.setenv("STREAM_CHEREMSHA_KICK_CLIENT_SECRET", "s")
    cfg = KickOAuthConfig.from_env()
    assert cfg is not None
    assert cfg.client_id == "c"
    assert cfg.client_secret == "s"
    assert cfg.redirect_uri == "http://localhost/callback"


def test_oauth_config_from_env_missing_returns_none(monkeypatch) -> None:
    monkeypatch.delenv("STREAM_CHEREMSHA_KICK_CLIENT_ID", raising=False)
    monkeypatch.delenv("STREAM_CHEREMSHA_KICK_CLIENT_SECRET", raising=False)
    assert KickOAuthConfig.from_env() is None


def test_parse_pusher_envelope_double_encoded() -> None:
    raw = (
        '{"event": "App\\\\Events\\\\ChatMessageEvent", '
        '"channel": "chatrooms.668.v2", "data": "{\\"a\\":1}"}'
    )
    event, channel, data = parse_pusher_envelope(raw)
    assert event == "App\\Events\\ChatMessageEvent"
    assert channel == "chatrooms.668.v2"
    assert data == '{"a":1}'


def test_parse_chat_message_extracts_sender() -> None:
    import json

    payload = {
        "id": "msg1",
        "content": "hello",
        "sender": {"id": 7, "username": "alice", "slug": "alice", "identity": {"color": "#fff"}},
        "created_at": "2025-01-01T00:00:00Z",
    }
    p = parse_chat_message(json.dumps(payload))
    assert p is not None
    assert p["content"] == "hello"


def test_parse_chat_message_invalid_returns_none() -> None:
    assert parse_chat_message("not-json") is None
    assert parse_chat_message('{"sender": {}}') is None


def test_kick_channel_info_parse() -> None:
    payload = {
        "broadcaster_user_id": 123,
        "slug": "xqc",
        "stream_title": "Live!",
        "stream": {"is_live": True, "viewer_count": 42},
    }
    info = KickApiClient.parse_channel_info(payload)
    assert info.broadcaster_user_id == 123
    assert info.slug == "xqc"
    assert info.is_live is True
    assert info.viewer_count == 42
    assert info.to_online_dict() == {"current": 42}


def test_kick_api_fetch_live_channel(monkeypatch) -> None:
    client = KickApiClient("tok", client=AsyncMock())

    async def fake_get(path, params=None, headers=None):
        _ = headers
        return [
            {
                "broadcaster_user_id": 1,
                "slug": "chan",
                "stream": {"is_live": True, "viewer_count": 9},
            }
        ]

    monkeypatch.setattr(client, "_get_json", fake_get)

    async def run():
        info = await client.fetch_live_channel("chan")
        await client.aclose()
        return info

    info = asyncio.run(run())
    assert info.viewer_count == 9


def test_resolve_chatroom_id(monkeypatch) -> None:
    class _CM:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        status = 200

        async def json(self, content_type=None):
            return {"chatroom": {"id": 668}}

    class _Session:
        def __init__(self) -> None:
            self.cm = _CM()

        def get(self, url, timeout=None, headers=None):
            return self.cm

        async def close(self) -> None:
            return None

    cid = asyncio.run(resolve_chatroom_id("xqc", session=_Session()))
    assert cid == 668


def test_online_models_include_kick() -> None:
    from stream_cheremsha.online.models import KickOnline

    state: KickOnline = {
        "current": 1,
        "peak": 2,
        "messages": 3,
        "follows": 4,
        "subscriptions": 5,
        "gift_subs": 6,
        "kicks": 7,
    }
    assert state["messages"] == 3


def test_activity_models_allow_kick_platform() -> None:
    from stream_cheremsha.activity.models import ActivityItem, now_hms

    item = ActivityItem(
        platform="kick",
        kind="follow",
        user="alice",
        detail="",
        count=1,
        icon_url="",
        time_hms=now_hms(),
    )
    assert item.to_dict()["platform"] == "kick"


def test_chat_formatting_kick_icon_used() -> None:
    from stream_cheremsha.ui.chat_formatting import format_chat_message_html

    msg = ChatMessage(
        author="alice",
        text="hi",
        platform=ChatPlatform.KICK,
        received_at=datetime.now(UTC),
    )
    out = format_chat_message_html(
        msg,
        font_pt=12,
        font_stack_css="sans-serif",
        twitch_icon_uri=None,
        youtube_icon_uri=None,
        tiktok_icon_uri=None,
        kick_icon_uri="data:image/png;base64,KICK",
    )
    assert "data:image/png;base64,KICK" in out


def test_trigger_meta_kick_platform() -> None:
    from stream_cheremsha.actions.trigger_meta import (
        chat_platform_for_preview,
        normalize_trigger_platform,
        trigger_platform_applies_to_kick_channel_events,
    )

    assert normalize_trigger_platform("kick") == "kick"
    assert normalize_trigger_platform("unknown") is None
    blob = {"type": "kick_follow", "platform": "kick"}
    assert trigger_platform_applies_to_kick_channel_events(blob) is True
    assert chat_platform_for_preview("kick", store_platform="all") is ChatPlatform.KICK


def test_kick_analytics_counters() -> None:
    import os

    from PySide6.QtWidgets import QApplication

    if (
        QApplication.instance() is None
        and not os.environ.get("DISPLAY")
        and not os.environ.get("WAYLAND_DISPLAY")
    ):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    inst = QApplication.instance()
    if inst is None:
        QApplication([])
    from stream_cheremsha.ui.kick_analytics_api import KickAnalyticsApi

    api = KickAnalyticsApi()
    api._apply_messages(3)
    api._apply_follow("alice")
    api._apply_sub("bob", 2)
    api._apply_gift_sub("carol", 2)
    api._apply_kick_gift("dave", 500)
    assert api.messagesSession == 3
    assert api.followsSession == 1
    assert api.subscriptionsSession == 1
    assert api.giftSubsSession == 2
    assert api.kicksSession == 500


def test_kick_source_dispatches_chat_message() -> None:
    class _Coord:
        def __init__(self) -> None:
            self.msgs: list[ChatMessage] = []

        async def enqueue_chat(self, msg: ChatMessage) -> None:
            self.msgs.append(msg)

    coord = _Coord()
    src = KickSource(coord, on_status=lambda _m: None)
    asyncio.run(
        src._on_message(
            {
                "id": "m",
                "content": "hello kick",
                "sender": {"id": 1, "username": "alice", "slug": "alice"},
                "created_at": "2025-01-01T00:00:00Z",
            }
        )
    )
    assert len(coord.msgs) == 1
    assert coord.msgs[0].platform is ChatPlatform.KICK
    assert coord.msgs[0].text == "hello kick"
    assert coord.msgs[0].author == "alice"
