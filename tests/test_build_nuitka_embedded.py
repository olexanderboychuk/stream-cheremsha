"""Tests for cheremsha-build's optional embedded_local.py materialization."""

from __future__ import annotations

from pathlib import Path

import pytest

from stream_cheremsha import build_nuitka


def test_write_embedded_local_from_env(monkeypatch, tmp_path: Path) -> None:
    embedded_path = tmp_path / "embedded_local.py"
    monkeypatch.setattr(build_nuitka, "_EMBEDDED_LOCAL", embedded_path)
    monkeypatch.setenv("STREAM_CHEREMSHA_CLOUDFLARE_TUNNEL_TOKEN", "tok")
    monkeypatch.setenv("STREAM_CHEREMSHA_CLOUDFLARE_TUNNEL_HOSTNAME", "widgets.example.com")
    monkeypatch.setenv("STREAM_CHEREMSHA_CLOUD_API_URL", "https://api.cheremsha.app")

    written = build_nuitka._write_embedded_local()

    assert written is True
    text = embedded_path.read_text(encoding="utf-8")
    assert "CLOUDFLARE_TUNNEL_TOKEN = 'tok'" in text
    assert "CLOUDFLARE_TUNNEL_HOSTNAME = 'widgets.example.com'" in text
    assert "KICK_CLIENT" not in text
    assert "CHEREMSHA_CLOUD_API_URL = 'https://api.cheremsha.app'" in text
    build_nuitka._remove_embedded_local(True)
    assert not embedded_path.is_file()


def test_write_embedded_local_ignores_kick_secrets(monkeypatch, tmp_path: Path) -> None:
    """Kick OAuth secrets are never baked into the binary (cloud-only)."""
    embedded_path = tmp_path / "embedded_local.py"
    monkeypatch.setattr(build_nuitka, "_EMBEDDED_LOCAL", embedded_path)
    monkeypatch.setenv("STREAM_CHEREMSHA_KICK_CLIENT_ID", "kick-cid")
    monkeypatch.setenv("STREAM_CHEREMSHA_KICK_CLIENT_SECRET", "kick-sec")

    written = build_nuitka._write_embedded_local()

    assert written is False
    assert not embedded_path.is_file()


def test_write_embedded_local_cloud_url_defaults_to_localhost(monkeypatch, tmp_path: Path) -> None:
    embedded_path = tmp_path / "embedded_local.py"
    monkeypatch.setattr(build_nuitka, "_EMBEDDED_LOCAL", embedded_path)
    # Force any deeper "always-present" env vars to be absent so Cloud URL
    # alone still triggers a write.
    monkeypatch.delenv("STREAM_CHEREMSHA_CLOUD_API_URL", raising=False)
    monkeypatch.setenv("STREAM_CHEREMSHA_CLOUDFLARE_TUNNEL_TOKEN", "tok")

    written = build_nuitka._write_embedded_local()

    assert written is True
    text = embedded_path.read_text(encoding="utf-8")
    assert "CHEREMSHA_CLOUD_API_URL = 'http://127.0.0.1:8000'" in text
    build_nuitka._remove_embedded_local(True)


def test_write_embedded_local_rejects_non_url_cloud(monkeypatch, tmp_path: Path) -> None:
    embedded_path = tmp_path / "embedded_local.py"
    monkeypatch.setattr(build_nuitka, "_EMBEDDED_LOCAL", embedded_path)
    monkeypatch.setenv("STREAM_CHEREMSHA_CLOUD_API_URL", "not-a-url")
    monkeypatch.setenv("STREAM_CHEREMSHA_CLOUDFLARE_TUNNEL_TOKEN", "tok")

    with pytest.raises(SystemExit):
        build_nuitka._write_embedded_local()
    build_nuitka._remove_embedded_local(False)


def test_write_embedded_local_clears_when_env_missing(monkeypatch, tmp_path: Path) -> None:
    embedded_path = tmp_path / "embedded_local.py"
    embedded_path.write_text("old", encoding="utf-8")
    monkeypatch.setattr(build_nuitka, "_EMBEDDED_LOCAL", embedded_path)
    monkeypatch.delenv("STREAM_CHEREMSHA_CLOUDFLARE_TUNNEL_TOKEN", raising=False)
    monkeypatch.delenv("STREAM_CHEREMSHA_CLOUDFLARE_TUNNEL_HOSTNAME", raising=False)
    monkeypatch.delenv("STREAM_CHEREMSHA_CLOUD_API_URL", raising=False)

    written = build_nuitka._write_embedded_local()

    assert written is False
    assert not embedded_path.is_file()


def test_write_embedded_local_reads_overlay_tls_files(monkeypatch, tmp_path: Path) -> None:
    embedded_path = tmp_path / "embedded_local.py"
    cert_path = tmp_path / "fullchain.pem"
    key_path = tmp_path / "key.pem"
    cert_path.write_text("CERTIFICATE PEM", encoding="utf-8")
    key_path.write_text("PRIVATE KEY PEM", encoding="utf-8")
    monkeypatch.setattr(build_nuitka, "_EMBEDDED_LOCAL", embedded_path)

    written = build_nuitka._write_embedded_local(
        overlay_cert_path=str(cert_path), overlay_key_path=str(key_path)
    )

    assert written is True
    text = embedded_path.read_text(encoding="utf-8")
    assert "OVERLAY_CERTIFICATE = 'CERTIFICATE PEM'" in text
    assert "OVERLAY_PRIVATE_KEY = 'PRIVATE KEY PEM'" in text
