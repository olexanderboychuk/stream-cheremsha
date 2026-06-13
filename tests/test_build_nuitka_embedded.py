from __future__ import annotations

from pathlib import Path

from stream_cheremsha import build_nuitka


def test_write_embedded_local_from_env(monkeypatch, tmp_path: Path) -> None:
    embedded_path = tmp_path / "embedded_local.py"
    monkeypatch.setattr(build_nuitka, "_EMBEDDED_LOCAL", embedded_path)
    monkeypatch.setenv("STREAM_CHEREMSHA_CLOUDFLARE_TUNNEL_TOKEN", "tok")
    monkeypatch.setenv("STREAM_CHEREMSHA_CLOUDFLARE_TUNNEL_HOSTNAME", "widgets.example.com")

    written = build_nuitka._write_embedded_local()

    assert written is True
    text = embedded_path.read_text(encoding="utf-8")
    assert "CLOUDFLARE_TUNNEL_TOKEN = 'tok'" in text
    assert "CLOUDFLARE_TUNNEL_HOSTNAME = 'widgets.example.com'" in text
    build_nuitka._remove_embedded_local(True)
    assert not embedded_path.is_file()


def test_write_embedded_local_clears_when_env_missing(monkeypatch, tmp_path: Path) -> None:
    embedded_path = tmp_path / "embedded_local.py"
    embedded_path.write_text("old", encoding="utf-8")
    monkeypatch.setattr(build_nuitka, "_EMBEDDED_LOCAL", embedded_path)
    monkeypatch.delenv("STREAM_CHEREMSHA_CLOUDFLARE_TUNNEL_TOKEN", raising=False)
    monkeypatch.delenv("STREAM_CHEREMSHA_CLOUDFLARE_TUNNEL_HOSTNAME", raising=False)

    written = build_nuitka._write_embedded_local()

    assert written is False
    assert not embedded_path.is_file()
