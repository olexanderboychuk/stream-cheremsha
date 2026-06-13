from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from stream_cheremsha.overlays.tunnel_install import (
    install_prompt_labels,
    is_tunnel_cli_installed,
    is_winget_available,
    missing_cli_status_message,
    provider_auto_installs_cli,
    provider_needs_cli,
    winget_package_id,
)
from stream_cheremsha.overlays.tunnel_types import TunnelProvider


def test_provider_auto_installs_cli() -> None:
    assert provider_auto_installs_cli(TunnelProvider.CLOUDFLARE) is True
    assert provider_auto_installs_cli(TunnelProvider.NGROK) is False


def test_winget_package_id_cloudflare() -> None:
    assert winget_package_id(TunnelProvider.CLOUDFLARE) == "Cloudflare.cloudflared"


def test_winget_package_id_ngrok_only() -> None:
    assert winget_package_id(TunnelProvider.NGROK) == "Ngrok.Ngrok"
    assert winget_package_id(TunnelProvider.CUSTOM) is None


def test_provider_needs_cli() -> None:
    assert provider_needs_cli(TunnelProvider.NGROK) is True
    assert provider_needs_cli(TunnelProvider.CLOUDFLARE) is True
    assert provider_needs_cli(TunnelProvider.CUSTOM) is False


def test_install_prompt_labels_uk() -> None:
    title, text = install_prompt_labels(TunnelProvider.NGROK, locale="uk")
    assert "ngrok" in title.lower()
    assert "winget" in text.lower()


def test_missing_cli_status_message_en() -> None:
    msg = missing_cli_status_message(TunnelProvider.NGROK, locale="en")
    assert "ngrok" in msg.lower()


@pytest.mark.asyncio
async def test_install_via_winget_success() -> None:
    from stream_cheremsha.overlays import tunnel_install

    proc = AsyncMock()
    proc.stdout = AsyncMock()
    proc.stdout.read = AsyncMock(side_effect=[b"Installed", b""])
    proc.wait = AsyncMock(return_value=0)

    with (
        patch.object(tunnel_install, "winget_executable", return_value="winget"),
        patch(
            "asyncio.create_subprocess_exec",
            return_value=proc,
        ),
        patch.object(tunnel_install, "is_tunnel_cli_installed", return_value=True),
        patch.object(
            tunnel_install,
            "refresh_windows_path",
        ),
    ):
        ok, err = await tunnel_install.install_tunnel_tool_via_winget(TunnelProvider.NGROK)

    assert ok is True
    assert err == ""


def test_is_tunnel_cli_installed_ngrok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "stream_cheremsha.overlays.tunnel_install.find_ngrok_executable",
        lambda: r"C:\tools\ngrok.exe",
    )
    assert is_tunnel_cli_installed(TunnelProvider.NGROK) is True


def test_is_winget_available_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("stream_cheremsha.overlays.tunnel_install.winget_executable", lambda: None)
    assert is_winget_available() is False
