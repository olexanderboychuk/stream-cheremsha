from __future__ import annotations

from stream_cheremsha.overlays.ngrok_domain import normalize_ngrok_domain, validate_ngrok_domain


def test_validate_accepts_ngrok_free_dev() -> None:
    assert validate_ngrok_domain("abc123.ngrok-free.dev") == "abc123.ngrok-free.dev"


def test_normalize_strips_scheme() -> None:
    assert normalize_ngrok_domain("HTTPS://ABC.NGROK-FREE.DEV/") == "abc.ngrok-free.dev"
