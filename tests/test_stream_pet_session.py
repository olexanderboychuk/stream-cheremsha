from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from stream_cheremsha.overlays.stream_pet_overlay_config import (
    stream_pet_overlay_config_defaults,
    stream_pet_overlay_config_from_json_text,
    stream_pet_overlay_config_to_json_text,
)
from stream_cheremsha.overlays.stream_pet_session import (
    GiftTier,
    RecentChatMsg,
    StreamPetEventKind,
    StreamPetMood,
    StreamPetSession,
    StreamPetSpeechKind,
    classify_gift_tier,
    is_chat_spam,
    is_sleep_command,
    is_wake_command,
    mood_from_energy,
)


def test_config_roundtrip() -> None:
    cfg = stream_pet_overlay_config_defaults().replace(
        enabled=False,
        pet_sprite_url="https://example.com/pet.png",
        initial_energy=55.0,
    )
    txt = stream_pet_overlay_config_to_json_text(cfg)
    got = stream_pet_overlay_config_from_json_text(txt)
    assert got.enabled is False
    assert got.pet_sprite_url == "https://example.com/pet.png"
    assert got.initial_energy == 55.0


def test_mood_from_energy() -> None:
    assert mood_from_energy(10) == StreamPetMood.HUNGRY
    assert mood_from_energy(50) == StreamPetMood.CHILL
    assert mood_from_energy(90) == StreamPetMood.HYPER


def test_decay_reduces_energy() -> None:
    cfg = stream_pet_overlay_config_defaults()
    s = StreamPetSession.fresh(cfg)
    s.energy = 50.0
    now = datetime.now(UTC)
    assert s.tick_decay(now) is False
    assert s.energy == 49.5


def test_decay_stops_at_zero() -> None:
    cfg = stream_pet_overlay_config_defaults()
    s = StreamPetSession.fresh(cfg)
    s.energy = 0.2
    now = datetime.now(UTC)
    s.tick_decay(now)
    assert s.energy == 0.0
    s.tick_decay(now)
    assert s.energy == 0.0


def test_sleep_command_and_wake() -> None:
    cfg = stream_pet_overlay_config_defaults()
    s = StreamPetSession.fresh(cfg)
    now = datetime.now(UTC)
    assert is_sleep_command("!sleep")
    assert is_wake_command("!прокинься")
    assert s.force_sleep(now, phrase="zzz")
    assert s.sleeping is True
    assert s.mood == StreamPetMood.SLEEP
    changed, kind = s.on_chat(author="u", text="hello", now=now)
    assert changed is True
    assert kind == StreamPetEventKind.CHAT
    assert s.sleeping is False


def test_gift_boosts_energy_and_sets_donor() -> None:
    cfg = stream_pet_overlay_config_defaults()
    s = StreamPetSession.fresh(cfg)
    now = datetime.now(UTC)
    start = s.energy
    assert s.on_gift(
        user="Gifter",
        tier=GiftTier.SMALL,
        gift_name="Rose",
        now=now,
        phrase="yum",
    )
    assert s.energy == start + 5.0
    assert s.last_donor_name == "Gifter"
    assert s.speech is not None
    assert s.speech.kind == StreamPetSpeechKind.REACTION


def test_follow_reaction() -> None:
    cfg = stream_pet_overlay_config_defaults()
    s = StreamPetSession.fresh(cfg)
    now = datetime.now(UTC)
    assert s.on_follow(user="NewFan", now=now, phrase="hi")
    assert s.speech is not None
    assert s.speech.text == "hi"


def test_classify_gift_tiers() -> None:
    cfg = stream_pet_overlay_config_defaults()
    assert classify_gift_tier(platform="tiktok", cfg=cfg, tiktok_coins=1) == GiftTier.SMALL
    assert classify_gift_tier(platform="tiktok", cfg=cfg, tiktok_coins=50) == GiftTier.MEDIUM
    assert classify_gift_tier(platform="tiktok", cfg=cfg, tiktok_coins=100) == GiftTier.LARGE
    assert classify_gift_tier(platform="twitch", cfg=cfg, twitch_bits=50) == GiftTier.SMALL
    assert classify_gift_tier(platform="twitch", cfg=cfg, twitch_bits=500) == GiftTier.LARGE
    assert (
        classify_gift_tier(platform="youtube", cfg=cfg, youtube_amount_micros=1_000_000)
        == GiftTier.SMALL
    )
    assert (
        classify_gift_tier(platform="youtube", cfg=cfg, youtube_amount_micros=6_000_000)
        == GiftTier.LARGE
    )


def test_spam_detection_caps() -> None:
    from collections import deque

    now = datetime.now(UTC)
    recent: deque[RecentChatMsg] = deque(maxlen=16)
    assert is_chat_spam("HELLO WORLD!!!", recent, author_key="a", now=now) is True


def test_auto_sleep_after_idle() -> None:
    cfg = stream_pet_overlay_config_defaults().replace(sleep_idle_sec=60)
    s = StreamPetSession.fresh(cfg)
    now = datetime.now(UTC)
    s.last_activity_at = now - timedelta(seconds=120)
    assert s.check_auto_sleep(now) is True
    assert s.sleeping is True


def test_mood_transition_on_large_gift() -> None:
    cfg = stream_pet_overlay_config_defaults()
    s = StreamPetSession.fresh(cfg)
    s.energy = 40.0
    now = datetime.now(UTC)
    s.on_gift(
        user="Whale",
        tier=GiftTier.LARGE,
        gift_name="Galaxy",
        now=now,
        phrase="wow",
    )
    assert s.energy == 70.0
    assert s.mood == StreamPetMood.CHILL


def test_chat_returns_reaction_kind() -> None:
    cfg = stream_pet_overlay_config_defaults()
    s = StreamPetSession.fresh(cfg)
    now = datetime.now(UTC)
    changed, kind = s.on_chat(author="Chatter", text="привіт!", now=now)
    assert changed is True
    assert kind == StreamPetEventKind.CHAT
    s.emit_reaction(now, author="Chatter", phrase="test", anim="walk")
    assert s.speech is not None
    assert s.speech.text == "test"


def test_like_reaction_with_user() -> None:
    cfg = stream_pet_overlay_config_defaults()
    s = StreamPetSession.fresh(cfg)
    now = datetime.now(UTC)
    assert s.on_like(user="Liker", now=now, phrase="thanks for likes")
    assert s.speech is not None
    assert s.speech.text == "thanks for likes"


def test_config_rejects_non_object() -> None:
    with pytest.raises(ValueError):
        stream_pet_overlay_config_from_json_text("[]")
