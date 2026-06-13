from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from stream_cheremsha.overlays.ngrok_domain import (
    fetch_ngrok_dev_domain,
    is_ngrok_dev_domain,
    normalize_ngrok_domain,
    validate_ngrok_domain,
)
from stream_cheremsha.overlays.tunnel import OverlayTunnel, _local_port, _resolve_ngrok_domain
from stream_cheremsha.overlays.tunnel_types import TunnelProvider


def test_normalize_ngrok_domain() -> None:
    assert normalize_ngrok_domain("https://abc.ngrok-free.dev/path") == "abc.ngrok-free.dev"
    assert is_ngrok_dev_domain("abc.ngrok-free.dev") is True
    assert is_ngrok_dev_domain("abc.ngrok.app") is False


def test_validate_ngrok_domain() -> None:
    assert validate_ngrok_domain("abc.ngrok-free.dev") == "abc.ngrok-free.dev"
    with pytest.raises(ValueError, match="must look like"):
        validate_ngrok_domain("not-a-domain")


def test_local_port_parses_url() -> None:
    assert _local_port("http://127.0.0.1:17171") == 17171


def test_resolve_ngrok_domain_prefers_configured() -> None:
    assert (
        _resolve_ngrok_domain(authtoken="tok", configured_domain="mine.ngrok-free.dev")
        == "mine.ngrok-free.dev"
    )


def test_resolve_ngrok_domain_fetches_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "stream_cheremsha.overlays.tunnel.fetch_ngrok_dev_domain",
        lambda _token: "auto.ngrok-free.dev",
    )
    assert _resolve_ngrok_domain(authtoken="tok", configured_domain="") == "auto.ngrok-free.dev"


def test_fetch_ngrok_dev_domain_picks_free_dev_suffix() -> None:
    class _Resp:
        status_code = 200

        @staticmethod
        def json() -> dict[str, object]:
            return {
                "reserved_domains": [
                    {"domain": "paid.ngrok.app"},
                    {"domain": "stable.ngrok-free.dev"},
                ],
            }

    with patch("stream_cheremsha.overlays.ngrok_domain.httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value.get.return_value = _Resp()
        assert fetch_ngrok_dev_domain("tok") == "stable.ngrok-free.dev"


@pytest.mark.asyncio
async def test_custom_tunnel_returns_url() -> None:
    tunnel = OverlayTunnel()
    url = await tunnel.start(
        provider=TunnelProvider.CUSTOM,
        local_url="http://127.0.0.1:17171",
        custom_url="https://example.ngrok.app",
    )
    assert url == "https://example.ngrok.app"
    await tunnel.stop()


@pytest.mark.asyncio
async def test_ngrok_requires_authtoken() -> None:
    tunnel = OverlayTunnel()
    with pytest.raises(RuntimeError, match="authtoken"):
        await tunnel.start(
            provider=TunnelProvider.NGROK,
            local_url="http://127.0.0.1:17171",
            ngrok_authtoken="",
            ngrok_domain="mine.ngrok-free.dev",
        )
    assert tunnel.state().status == "error"


@pytest.mark.asyncio
async def test_ngrok_start_uses_dev_domain() -> None:
    tunnel = OverlayTunnel()
    fake_tunnel = MagicMock(public_url="https://mine.ngrok-free.dev")

    with patch(
        "stream_cheremsha.overlays.tunnel._ngrok_connect",
        return_value=(fake_tunnel, "https://mine.ngrok-free.dev"),
    ) as connect:
        url = await tunnel.start(
            provider=TunnelProvider.NGROK,
            local_url="http://127.0.0.1:17171",
            ngrok_authtoken="tok",
            ngrok_domain="mine.ngrok-free.dev",
        )

    connect.assert_called_once_with(17171, "tok", "mine.ngrok-free.dev")
    assert url == "https://mine.ngrok-free.dev"
    assert tunnel.ngrok_domain_used() == "mine.ngrok-free.dev"
    await tunnel.stop()


@pytest.mark.asyncio
async def test_cloudflare_start_with_token() -> None:
    tunnel = OverlayTunnel()
    fake_proc = MagicMock()
    fake_proc.poll.return_value = None

    with patch(
        "stream_cheremsha.overlays.tunnel.start_cloudflared_process",
        return_value=fake_proc,
    ) as start_proc:
        url = await tunnel.start(
            provider=TunnelProvider.CLOUDFLARE,
            local_url="http://127.0.0.1:17171",
            cloudflare_hostname="widgets.example.com",
            cloudflare_tunnel_token="eyJ-token",
            cloudflared_executable=r"C:\tools\cloudflared.exe",
        )

    start_proc.assert_called_once()
    assert url == "https://widgets.example.com"
    await tunnel.stop()


@pytest.mark.asyncio
async def test_cloudflare_requires_token() -> None:
    tunnel = OverlayTunnel()
    with pytest.raises(RuntimeError, match="tunnel token is required"):
        await tunnel.start(
            provider=TunnelProvider.CLOUDFLARE,
            local_url="http://127.0.0.1:17171",
            cloudflare_hostname="widgets.example.com",
            cloudflared_executable=r"C:\tools\cloudflared.exe",
        )
    assert tunnel.state().status == "error"


@pytest.mark.asyncio
async def test_stop_clears_state() -> None:
    tunnel = OverlayTunnel()
    await tunnel.start(
        provider=TunnelProvider.CUSTOM,
        local_url="http://127.0.0.1:17171",
        custom_url="https://example.com",
    )
    await tunnel.stop()
    assert tunnel.state().status == "idle"
    assert tunnel.state().public_url == ""
