from __future__ import annotations

import time

from stream_cheremsha.battle_royale.controller import BattleRoyaleController
from stream_cheremsha.battle_royale.models import BattlePhase, BattleSupportGift
from stream_cheremsha.overlays.battle_royale_overlay_config import (
    BattleRoyaleOverlayConfig,
    battle_royale_overlay_config_defaults,
)


def _cfg(**kwargs: object) -> BattleRoyaleOverlayConfig:
    return battle_royale_overlay_config_defaults().replace(**kwargs)


def _fighters() -> list[dict[str, str]]:
    return [
        {"user_key": "a", "user": "Alice", "avatar_url": ""},
        {"user_key": "b", "user": "Bob", "avatar_url": ""},
    ]


def _support_gift(name: str = "Rose", gift_id: str = "5655") -> BattleSupportGift:
    return BattleSupportGift(
        gift_id=gift_id, name=name, image_url="https://example.com/g.png", price=1
    )


def _arm_active_with_gifts(c: BattleRoyaleController) -> None:
    c.state().phase = BattlePhase.ACTIVE
    c.state().fighters[0].support_gifts = [_support_gift("Rose", "5655")]
    c.state().fighters[1].support_gifts = [_support_gift("GG", "5585")]


def test_manual_start_countdown_then_active() -> None:
    c = BattleRoyaleController()
    cfg = _cfg(countdown_s=2, round_duration_s=60)
    assert c.start_manual(_fighters(), cfg=cfg)
    assert c.state().phase == BattlePhase.COUNTDOWN
    t0 = time.monotonic()
    c.state().countdown_deadline = t0 + 0.05
    assert c.tick(now=t0 + 0.1)
    assert c.state().phase == BattlePhase.ACTIVE
    assert c.state().timer_remaining_s == 60


def test_fighter_heal_and_crit_damage() -> None:
    c = BattleRoyaleController()
    cfg = _cfg(max_hp=1000, crit_threshold_diamonds=100, crit_multiplier=1.5, countdown_s=0)
    c.start_manual(_fighters(), cfg=cfg)
    _arm_active_with_gifts(c)
    c.state().fighters[0].hp = 500
    c.state().fighters[1].hp = 800
    hit = c.on_gift(
        sender_user_key="a",
        sender_display="Alice",
        sender_avatar_url="",
        diamonds=200,
        gift_name="Rose",
    )
    assert hit is not None
    assert hit.heal == 200
    assert c.state().fighters[0].hp == 700
    assert hit.crit is True
    assert c.state().fighters[1].hp < 800


def test_supporter_gift_heals_fighter() -> None:
    c = BattleRoyaleController()
    cfg = _cfg(countdown_s=0)
    c.start_manual(_fighters(), cfg=cfg)
    _arm_active_with_gifts(c)
    c.state().fighters[0].hp = 400
    hit = c.on_gift(
        sender_user_key="spectator",
        sender_display="Fan",
        sender_avatar_url="",
        diamonds=50,
        gift_name="Rose",
    )
    assert hit is not None
    assert hit.heal == 50
    assert c.state().fighters[0].hp == 450


def test_ko_ends_battle_with_winner() -> None:
    c = BattleRoyaleController()
    cfg = _cfg(countdown_s=0, max_hp=100, crit_threshold_diamonds=40, crit_multiplier=1.0)
    c.start_manual(_fighters(), cfg=cfg)
    _arm_active_with_gifts(c)
    c.state().fighters[1].hp = 30
    c.on_gift(
        sender_user_key="spectator",
        sender_display="Fan",
        sender_avatar_url="",
        diamonds=80,
        gift_name="Rose",
    )
    assert c.state().phase == BattlePhase.VICTORY
    assert c.state().winner_key == "a"


def test_timer_resolve_picks_max_hp() -> None:
    c = BattleRoyaleController()
    cfg = _cfg(countdown_s=0, round_duration_s=10)
    c.start_manual(_fighters(), cfg=cfg)
    st = c.state()
    st.phase = BattlePhase.ACTIVE
    st.fighters[0].hp = 400
    st.fighters[1].hp = 600
    t0 = time.monotonic()
    st.round_deadline = t0 + 0.01
    assert c.tick(now=t0 + 0.05)
    assert c.state().phase == BattlePhase.VICTORY
    assert c.state().winner_key == "b"


def test_auto_arm_after_two_qualified_gifts() -> None:
    c = BattleRoyaleController()
    cfg = _cfg(auto_arm_enabled=True, auto_threshold_each=50, auto_window_s=30, countdown_s=3)
    c.set_session_config(cfg)
    t0 = 1000.0
    c.on_gift(
        sender_user_key="a",
        sender_display="Alice",
        sender_avatar_url="",
        diamonds=60,
        now=t0,
    )
    c.on_gift(
        sender_user_key="b",
        sender_display="Bob",
        sender_avatar_url="",
        diamonds=80,
        now=t0 + 1,
    )
    assert c.state().phase == BattlePhase.COUNTDOWN
    assert len(c.state().fighters) == 2
