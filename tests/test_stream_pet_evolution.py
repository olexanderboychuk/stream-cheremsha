from __future__ import annotations

from datetime import UTC, datetime

from stream_cheremsha.overlays.stream_pet_overlay_config import stream_pet_overlay_config_defaults
from stream_cheremsha.overlays.stream_pet_phrases import (
    LEVEL2_THANKS_KEYS,
    thanks_templates_for,
)
from stream_cheremsha.overlays.stream_pet_session import (
    GiftTier,
    StreamPetEventKind,
    StreamPetMood,
    StreamPetSession,
    truncate_stream_pet_phrase,
)


def test_evolution_at_full_energy() -> None:
    cfg = stream_pet_overlay_config_defaults()
    s = StreamPetSession.fresh(cfg)
    now = datetime.now(UTC)
    s.energy = 95.0
    s._add_energy(10.0, now)
    assert s.level == 2
    assert s.energy == 50.0
    assert s.mood == StreamPetMood.CHILL
    assert s.evolution_count == 1


def test_double_evolution_to_level_3() -> None:
    cfg = stream_pet_overlay_config_defaults()
    s = StreamPetSession.fresh(cfg)
    now = datetime.now(UTC)
    s.energy = 95.0
    s._add_energy(10.0, now)
    s.energy = 95.0
    s._add_energy(10.0, now)
    assert s.level == 3
    assert s.evolution_count == 2
    assert s.disco_until is not None
    assert s.vip_bonus_due is True


def test_level_3_caps_energy() -> None:
    cfg = stream_pet_overlay_config_defaults()
    s = StreamPetSession.fresh(cfg)
    now = datetime.now(UTC)
    s.level = 3
    s.energy = 95.0
    s._add_energy(30.0, now)
    assert s.level == 3
    assert s.energy == 100.0
    assert s.evolution_count == 0


def test_evolution_disabled() -> None:
    cfg = stream_pet_overlay_config_defaults().replace(evolution_enabled=False)
    s = StreamPetSession.fresh(cfg)
    now = datetime.now(UTC)
    s.energy = 95.0
    s._add_energy(20.0, now)
    assert s.level == 1
    assert s.energy == 100.0


def test_reset_for_new_stream() -> None:
    cfg = stream_pet_overlay_config_defaults()
    s = StreamPetSession.fresh(cfg)
    s.level = 3
    s.evolution_count = 2
    s.energy = 100.0
    s.reset_for_new_stream()
    assert s.level == 1
    assert s.evolution_count == 0
    assert s.energy == cfg.initial_energy
    assert s.disco_until is None


def test_thanks_templates_level_2() -> None:
    pool = thanks_templates_for(StreamPetEventKind.CHAT, 2)
    assert pool[0] in LEVEL2_THANKS_KEYS


def test_truncate_phrase() -> None:
    text = "a" * 150
    got = truncate_stream_pet_phrase(text, 110)
    assert len(got) == 110
    assert got.endswith("…")


def test_evolution_keeps_energy_remainder_above_floor() -> None:
    cfg = stream_pet_overlay_config_defaults().replace(post_evolution_energy=40.0)
    s = StreamPetSession.fresh(cfg)
    now = datetime.now(UTC)
    s.energy = 80.0
    s._add_energy(30.0, now)
    assert s.level == 2
    assert s.energy == 40.0


def test_evolution_does_not_trigger_hungry_mood() -> None:
    cfg = stream_pet_overlay_config_defaults()
    s = StreamPetSession.fresh(cfg)
    now = datetime.now(UTC)
    s.energy = 99.0
    s._mood = StreamPetMood.HYPER
    s._add_energy(5.0, now)
    assert s.level == 2
    assert s.mood == StreamPetMood.CHILL
    assert s.mood != StreamPetMood.HUNGRY


def test_large_gift_evolution_not_hungry() -> None:
    cfg = stream_pet_overlay_config_defaults()
    s = StreamPetSession.fresh(cfg)
    now = datetime.now(UTC)
    s.energy = 70.0
    s.on_gift(user="Whale", tier=GiftTier.LARGE, gift_name="Galaxy", now=now)
    assert s.level == 2
    assert s.energy == 50.0
    assert s.mood == StreamPetMood.CHILL
