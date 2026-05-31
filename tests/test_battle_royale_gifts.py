from __future__ import annotations

import random

from stream_cheremsha.battle_royale.controller import BattleRoyaleController
from stream_cheremsha.battle_royale.gifts import (
    assign_support_gifts,
    fighter_index_for_gift,
    gift_matches_fighter,
)
from stream_cheremsha.battle_royale.models import BattleFighter, BattlePhase, BattleSupportGift
from stream_cheremsha.overlays.battle_royale_overlay_config import (
    battle_royale_overlay_config_defaults,
)


def test_assign_support_gifts_distinct_per_fighter() -> None:
    fighters = [
        BattleFighter("a", "Alice", "", 1000, 1000, "left"),
        BattleFighter("b", "Bob", "", 1000, 1000, "right"),
    ]
    catalog = [
        {"name": "Rose", "price": 1, "image_url": "https://example.com/rose.png", "id": "1"},
        {"name": "TikTok", "price": 1, "image_url": "https://example.com/tt.png", "id": "2"},
        {"name": "GG", "price": 1, "image_url": "https://example.com/gg.png", "id": "3"},
        {"name": "Heart", "price": 5, "image_url": "https://example.com/h.png", "id": "4"},
    ]
    assign_support_gifts(fighters, per_fighter=2, catalog=catalog, rng=random.Random(0))
    assert len(fighters[0].support_gifts) == 2
    assert len(fighters[1].support_gifts) == 2
    names_a = {g.name for g in fighters[0].support_gifts}
    names_b = {g.name for g in fighters[1].support_gifts}
    assert names_a.isdisjoint(names_b)
    for g in fighters[0].support_gifts + fighters[1].support_gifts:
        assert g.price == 1
    assert "Heart" not in names_a and "Heart" not in names_b


def test_assign_support_gifts_only_one_coin_from_catalog() -> None:
    from stream_cheremsha.battle_royale.gifts import _eligible_catalog

    catalog = [
        {"name": "Rose", "price": 1, "image_url": "https://example.com/r.png"},
        {"name": "Corgi", "price": 299, "image_url": "https://example.com/c.png"},
    ]
    pool = _eligible_catalog(catalog)
    assert len(pool) == 1
    assert pool[0].name == "Rose"
    assert pool[0].price == 1


def test_gift_match_by_name() -> None:
    f = BattleFighter(
        "a",
        "Alice",
        "",
        100,
        100,
        "left",
        support_gifts=[BattleSupportGift("5655", "Rose", "https://x/rose.png", 1)],
    )
    assert gift_matches_fighter("", "Rose", f)
    assert gift_matches_fighter("5655", "", f)
    assert not gift_matches_fighter("", "Corgi", f)


def test_supporter_gift_heals_assigned_fighter() -> None:
    c = BattleRoyaleController()
    cfg = battle_royale_overlay_config_defaults().replace(countdown_s=0, gifts_per_fighter=1)
    c.start_manual(
        [
            {"user_key": "a", "user": "Alice", "avatar_url": ""},
            {"user_key": "b", "user": "Bob", "avatar_url": ""},
        ],
        cfg=cfg,
    )
    c.state().phase = BattlePhase.ACTIVE
    c.state().fighters[0].hp = 500
    gift = c.state().fighters[0].support_gifts[0]
    hit = c.on_gift(
        sender_user_key="fan",
        sender_display="Fan",
        sender_avatar_url="",
        diamonds=80,
        gift_name=gift.name,
    )
    assert hit is not None
    assert c.state().fighters[0].hp == 580


def test_wrong_gift_ignored() -> None:
    c = BattleRoyaleController()
    cfg = battle_royale_overlay_config_defaults().replace(countdown_s=0, gifts_per_fighter=1)
    c.start_manual(
        [
            {"user_key": "a", "user": "Alice", "avatar_url": ""},
            {"user_key": "b", "user": "Bob", "avatar_url": ""},
        ],
        cfg=cfg,
    )
    c.state().phase = BattlePhase.ACTIVE
    hp_before = c.state().fighters[0].hp
    hit = c.on_gift(
        sender_user_key="fan",
        sender_display="Fan",
        sender_avatar_url="",
        diamonds=50,
        gift_name="NotARealGiftNameXYZ",
    )
    assert hit is None
    assert c.state().fighters[0].hp == hp_before


def test_fighter_index_for_gift() -> None:
    fighters = [
        BattleFighter(
            "a",
            "Alice",
            "",
            100,
            100,
            "left",
            support_gifts=[BattleSupportGift("", "Rose", "https://x/r.png")],
        ),
        BattleFighter(
            "b",
            "Bob",
            "",
            100,
            100,
            "right",
            support_gifts=[BattleSupportGift("", "GG", "https://x/g.png")],
        ),
    ]
    assert fighter_index_for_gift(fighters, gift_id="", gift_name="Rose") == 0
    assert fighter_index_for_gift(fighters, gift_id="", gift_name="GG") == 1
