"""Bundled TikTok gift catalog image_url fallback."""

from __future__ import annotations

import stream_cheremsha.actions.tiktok_gifts as tg


def test_catalog_image_url_matches_id(monkeypatch) -> None:
    monkeypatch.setattr(
        tg,
        "TIKTOK_GIFTS",
        [{"id": "5655", "name": "Rose", "price": 1, "image_url": "https://cdn.example/rose.png"}],
    )
    assert tg.tiktok_catalog_gift_image_url(gift_id="5655") == "https://cdn.example/rose.png"


def test_catalog_image_url_matches_name_when_id_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        tg,
        "TIKTOK_GIFTS",
        [{"id": "", "name": "Finger Heart", "price": 5, "image_url": "https://cdn.example/fh.png"}],
    )
    assert tg.tiktok_catalog_gift_image_url(gift_name="finger heart") == "https://cdn.example/fh.png"


def test_catalog_returns_empty_when_no_image(monkeypatch) -> None:
    monkeypatch.setattr(
        tg,
        "TIKTOK_GIFTS",
        [{"id": "1", "name": "X", "price": 1}],
    )
    assert tg.tiktok_catalog_gift_image_url(gift_id="1") == ""
