from __future__ import annotations

import json
from pathlib import Path
from typing import Final, TypedDict


class TikTokGift(TypedDict, total=False):
    id: str
    name: str
    price: int
    image_url: str


def _repo_root() -> Path:
    # .../src/stream_cheremsha/actions/tiktok_gifts.py -> repo root
    return Path(__file__).resolve().parents[3]


def _load_streamtoearn_ua() -> list[TikTokGift]:
    """
    Prefer the scraped UA list (name/price/image_url) if available in the repo.
    This keeps the in-app list rich without hardcoding a huge Python constant.
    """
    p = _repo_root() / "artifacts" / "tiktok_gifts_ua_streamtoearn.json"
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []
    if not isinstance(raw, list):
        return []
    out: list[TikTokGift] = []
    for it in raw:
        if not isinstance(it, dict):
            continue
        name = it.get("name")
        price = it.get("price")
        image_url = it.get("image_url")
        if not isinstance(name, str) or not name.strip():
            continue
        if not isinstance(price, int):
            continue
        gift: TikTokGift = {"id": "", "name": name.strip(), "price": price}
        if isinstance(image_url, str) and image_url.strip():
            gift["image_url"] = image_url.strip()
        out.append(gift)
    return out


# Fallback curated list (minimal) if artifacts aren't present.
TIKTOK_GIFTS_FALLBACK: Final[list[TikTokGift]] = [
    {"id": "5655", "name": "Rose", "price": 1},
    {"id": "5585", "name": "TikTok", "price": 1},
    {"id": "7934", "name": "Finger Heart", "price": 5},
    {"id": "5879", "name": "Perfume", "price": 20},
    {"id": "5269", "name": "Corgi", "price": 299},
]


TIKTOK_GIFTS: Final[list[TikTokGift]] = _load_streamtoearn_ua() or TIKTOK_GIFTS_FALLBACK
