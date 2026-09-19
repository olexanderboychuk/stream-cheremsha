"""YouTube broker-token path: in-memory cloud creds, keyring untouched."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from google.oauth2.credentials import Credentials

import stream_cheremsha.chat.youtube_source as yt_mod
from stream_cheremsha.chat.youtube_source import YouTubeChatSource


def _make_source(**kw) -> YouTubeChatSource:
    return YouTubeChatSource(
        coordinator=MagicMock(),
        on_status=kw.get("on_status", lambda _s: None),
        get_locale=lambda: "uk",
    )


def test_broker_credentials_construction(monkeypatch) -> None:
    monkeypatch.setattr(yt_mod.keyring_store, "get_password", lambda _k: None)
    src = _make_source()
    future = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    src.set_broker_token("broker-AT", future, "broker-cid")
    creds = src._broker_credentials()
    assert isinstance(creds, Credentials)
    assert creds.token == "broker-AT"
    assert creds.client_id == "broker-cid"
    assert creds.refresh_token is None
    assert creds.expired is False


def test_broker_credentials_expired_in_past(monkeypatch) -> None:
    monkeypatch.setattr(yt_mod.keyring_store, "get_password", lambda _k: None)
    src = _make_source()
    past = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
    src.set_broker_token("broker-AT", past, "broker-cid")
    creds = src._broker_credentials()
    assert creds is not None and creds.expired is True


def test_credentials_prefers_broker_over_keyring(monkeypatch) -> None:
    monkeypatch.setattr(yt_mod.keyring_store, "get_password", lambda _k: None)
    src = _make_source()
    assert src._credentials() is None  # no usable keyring session
    future = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    src.set_broker_token("broker-AT", future, "broker-cid")
    creds = src._credentials()
    assert creds is not None and creds.token == "broker-AT"


def test_broker_wait_needed_only_for_broker_without_refresh() -> None:
    from google.oauth2.credentials import Credentials as _RealCreds

    past = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=5)
    src = _make_source()
    assert src._broker_wait_needed(None) is False
    keyring_creds = _RealCreds(token="k", expiry=past)
    assert src._broker_wait_needed(keyring_creds) is False
    src.set_broker_token("broker-AT", None, "")
    assert src._broker_wait_needed(keyring_creds) is True
    with_refresh = _RealCreds(token="k", refresh_token="r", expiry=past)
    assert src._broker_wait_needed(with_refresh) is False


def test_stop_clears_broker_token() -> None:
    src = _make_source()
    src.set_broker_token("broker-AT", None, "")
    assert src._broker_token is not None

    async def _run() -> None:
        await src.stop()

    asyncio.run(_run())
    assert src._broker_token is None


def test_set_broker_token_empty_clears() -> None:
    src = _make_source()
    src.set_broker_token("broker-AT", None, "")
    src.set_broker_token("", None, "")
    assert src._broker_token is None
