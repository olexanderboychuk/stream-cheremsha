from __future__ import annotations

import pytest

from stream_cheremsha.config import constants, embedded, keyring_store
from stream_cheremsha.config import tunnel_secrets as ts


def test_resolve_cloudflare_tunnel_token_prefers_keyring(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(embedded, "CLOUDFLARE_TUNNEL_TOKEN", "embedded")
    monkeypatch.setenv(constants.ENV_CLOUDFLARE_TUNNEL_TOKEN, "env-token")
    monkeypatch.setattr(keyring_store, "get_password", lambda _key: "keyring-token")
    assert ts.resolve_cloudflare_tunnel_token() == "keyring-token"


def test_resolve_cloudflare_tunnel_token_env_over_embedded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(keyring_store, "get_password", lambda _key: None)
    monkeypatch.setattr(embedded, "CLOUDFLARE_TUNNEL_TOKEN", "embedded")
    monkeypatch.setenv(constants.ENV_CLOUDFLARE_TUNNEL_TOKEN, "env-token")
    assert ts.resolve_cloudflare_tunnel_token() == "env-token"


def test_resolve_cloudflare_tunnel_token_embedded_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(keyring_store, "get_password", lambda _key: None)
    monkeypatch.delenv(constants.ENV_CLOUDFLARE_TUNNEL_TOKEN, raising=False)
    monkeypatch.setattr(embedded, "CLOUDFLARE_TUNNEL_TOKEN", "embedded")
    assert ts.resolve_cloudflare_tunnel_token() == "embedded"


def test_resolve_cloudflare_tunnel_hostname_prefers_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(embedded, "CLOUDFLARE_TUNNEL_HOSTNAME", "embedded.example.com")
    monkeypatch.setenv(constants.ENV_CLOUDFLARE_TUNNEL_HOSTNAME, "env.example.com")
    assert (
        ts.resolve_cloudflare_tunnel_hostname(settings_value="settings.example.com")
        == "settings.example.com"
    )
