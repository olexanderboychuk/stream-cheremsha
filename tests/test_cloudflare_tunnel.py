from __future__ import annotations

import json
from pathlib import Path

import pytest

from stream_cheremsha.overlays.cloudflare_tunnel import (
    normalize_cloudflare_hostname,
    public_url_for_hostname,
    validate_cloudflare_hostname,
    validate_credentials_file,
    validate_tunnel_id,
    write_tunnel_config,
)


def test_normalize_cloudflare_hostname() -> None:
    assert (
        normalize_cloudflare_hostname("https://Widgets.Example.com/path") == "widgets.example.com"
    )


def test_validate_cloudflare_hostname() -> None:
    assert validate_cloudflare_hostname("widgets.example.com") == "widgets.example.com"
    with pytest.raises(ValueError, match="must look like"):
        validate_cloudflare_hostname("not a host")


def test_validate_tunnel_id() -> None:
    tid = "6ff42ae2-765d-4adf-8112-31c55c1551ef"
    assert validate_tunnel_id(tid) == tid
    with pytest.raises(ValueError, match="UUID"):
        validate_tunnel_id("bad")


def test_validate_credentials_file(tmp_path: Path) -> None:
    creds = tmp_path / "tunnel.json"
    creds.write_text(
        json.dumps(
            {
                "AccountTag": "acct",
                "TunnelSecret": "secret",
                "TunnelID": "6ff42ae2-765d-4adf-8112-31c55c1551ef",
            }
        ),
        encoding="utf-8",
    )
    assert validate_credentials_file(str(creds)) == creds.resolve()
    with pytest.raises(ValueError, match="not found"):
        validate_credentials_file(str(tmp_path / "missing.json"))


def test_write_tunnel_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    creds = tmp_path / "6ff42ae2-765d-4adf-8112-31c55c1551ef.json"
    creds.write_text(
        json.dumps(
            {
                "AccountTag": "acct",
                "TunnelSecret": "secret",
                "TunnelID": "6ff42ae2-765d-4adf-8112-31c55c1551ef",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "stream_cheremsha.overlays.cloudflare_tunnel.tempfile.gettempdir",
        lambda: str(tmp_path),
    )
    config_path = write_tunnel_config(
        tunnel_id="6ff42ae2-765d-4adf-8112-31c55c1551ef",
        credentials_file=creds,
        hostname="widgets.example.com",
        local_port=17171,
    )
    text = config_path.read_text(encoding="utf-8")
    assert "hostname: widgets.example.com" in text
    assert "service: http://127.0.0.1:17171" in text
    assert "http_status:404" in text


def test_public_url_for_hostname() -> None:
    assert public_url_for_hostname("widgets.example.com") == "https://widgets.example.com"
