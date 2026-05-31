from __future__ import annotations

import random

from stream_cheremsha.actions.tiktok_gifts import (
    TIKTOK_GIFTS,
    TIKTOK_GIFTS_FALLBACK,
    TikTokGift,
    _load_packaged_catalog,
    tiktok_catalog_gift_image_url,
)
from stream_cheremsha.battle_royale.models import BattleFighter, BattleSupportGift

# Only 1-coin gifts are eligible for random battle support assignment.
BATTLE_SUPPORT_GIFT_COIN_PRICE = 1


def battle_gift_catalog() -> list[TikTokGift]:
    """Rich gift list for battle assignment (packaged assets preferred)."""
    packaged = _load_packaged_catalog()
    if packaged:
        return packaged
    if len(TIKTOK_GIFTS) > len(TIKTOK_GIFTS_FALLBACK):
        return list(TIKTOK_GIFTS)
    return list(TIKTOK_GIFTS_FALLBACK)


def _catalog_entry_to_support(g: TikTokGift) -> BattleSupportGift | None:
    name = str(g.get("name") or "").strip()
    if not name:
        return None
    gid = str(g.get("id") or "").strip()
    price = int(g.get("price") or 0)
    if price != BATTLE_SUPPORT_GIFT_COIN_PRICE:
        return None
    image_url = str(g.get("image_url") or "").strip()
    if not image_url:
        image_url = tiktok_catalog_gift_image_url(gift_id=gid, gift_name=name)
    if not image_url:
        return None
    return BattleSupportGift(gift_id=gid, name=name, image_url=image_url, price=price)


def _eligible_catalog(catalog: list[TikTokGift]) -> list[BattleSupportGift]:
    out: list[BattleSupportGift] = []
    seen_names: set[str] = set()
    for raw in catalog:
        g = _catalog_entry_to_support(raw)
        if g is None:
            continue
        key = g.name.casefold()
        if key in seen_names:
            continue
        seen_names.add(key)
        out.append(g)
    return out


def assign_support_gifts(
    fighters: list[BattleFighter],
    *,
    per_fighter: int,
    catalog: list[TikTokGift] | None = None,
    rng: random.Random | None = None,
) -> None:
    """Pick random distinct gifts per fighter from the TikTok catalog."""
    if per_fighter <= 0 or not fighters:
        for f in fighters:
            f.support_gifts = []
        return
    pool = _eligible_catalog(catalog or battle_gift_catalog())
    r = rng or random.Random()
    r.shuffle(pool)
    if not pool:
        for f in fighters:
            f.support_gifts = []
        return
    needed = len(fighters) * per_fighter
    picks: list[BattleSupportGift] = []
    while len(picks) < needed:
        if not pool:
            pool = _eligible_catalog(catalog or battle_gift_catalog())
            r.shuffle(pool)
            if not pool:
                break
        picks.append(pool.pop())
    idx = 0
    for f in fighters:
        chunk: list[BattleSupportGift] = []
        for _ in range(per_fighter):
            if idx >= len(picks):
                break
            chunk.append(picks[idx])
            idx += 1
        f.support_gifts = chunk


def gift_matches_fighter(
    gift_id: str,
    gift_name: str,
    fighter: BattleFighter,
) -> bool:
    gid = (gift_id or "").strip()
    name_cf = (gift_name or "").strip().casefold()
    for g in fighter.support_gifts:
        if gid and g.gift_id and gid == g.gift_id:
            return True
        if name_cf and g.name.casefold() == name_cf:
            return True
    return False


def fighter_index_for_gift(
    fighters: list[BattleFighter],
    *,
    gift_id: str,
    gift_name: str,
) -> int | None:
    for i, f in enumerate(fighters):
        if gift_matches_fighter(gift_id, gift_name, f):
            return i
    return None
