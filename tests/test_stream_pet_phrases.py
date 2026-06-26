from __future__ import annotations

from stream_cheremsha import l10n
from stream_cheremsha.overlays.stream_pet_phrases import (
    CHILL_PHRASE_KEYS,
    EVENT_THANKS_KEYS,
    GENERAL_THANKS_KEYS,
    HUNGRY_PHRASE_KEYS,
    HYPE_THANKS_KEYS,
    HYPER_PHRASE_KEYS,
    LEVEL1_IDLE_KEYS,
    LEVEL2_THANKS_KEYS,
    LEVEL3_VIP_KEYS,
    MOOD_PHRASE_KEYS,
    SLEEP_PHRASE_KEYS,
    thanks_templates_for,
)
from stream_cheremsha.overlays.stream_pet_session import StreamPetEventKind, StreamPetMood


def test_mood_phrase_pool_sizes() -> None:
    assert len(HUNGRY_PHRASE_KEYS) == 12
    assert len(CHILL_PHRASE_KEYS) == 12
    assert len(HYPER_PHRASE_KEYS) == 10
    assert len(SLEEP_PHRASE_KEYS) == 8
    assert len(MOOD_PHRASE_KEYS["hungry"]) == 11


def test_event_thanks_pools_exist() -> None:
    assert len(EVENT_THANKS_KEYS["chat"]) == 10
    assert len(EVENT_THANKS_KEYS["gift_large"]) == 10


def test_thanks_templates_merge_event_and_general() -> None:
    pool = thanks_templates_for(StreamPetEventKind.CHAT, 1)
    assert any(k.startswith("stream_pet.thanks.chat.") for k in pool)
    assert GENERAL_THANKS_KEYS[-1] in pool


def test_thanks_templates_level_2_prioritizes_level_pool() -> None:
    pool = thanks_templates_for(StreamPetEventKind.CHAT, 2)
    assert pool[0] in LEVEL2_THANKS_KEYS


def test_thanks_templates_hype_includes_hype_pool() -> None:
    pool = thanks_templates_for(StreamPetEventKind.GIFT_LARGE, 1)
    assert any(k.startswith("stream_pet.thanks.gift_large.") for k in pool)
    assert any(k.startswith("stream_pet.thanks.hype.") for k in pool)


def test_all_phrase_keys_exist_in_l10n() -> None:
    keys: set[str] = set()
    keys.update(HUNGRY_PHRASE_KEYS)
    keys.update(CHILL_PHRASE_KEYS)
    keys.update(HYPER_PHRASE_KEYS)
    keys.update(SLEEP_PHRASE_KEYS)
    keys.update(GENERAL_THANKS_KEYS)
    keys.update(HYPE_THANKS_KEYS)
    keys.update(LEVEL1_IDLE_KEYS)
    keys.update(LEVEL2_THANKS_KEYS)
    keys.update(LEVEL3_VIP_KEYS)
    keys.add("stream_pet.evolve.2")
    keys.add("stream_pet.evolve.3")
    for event_keys in EVENT_THANKS_KEYS.values():
        keys.update(event_keys)
    keys.add("stream_pet.hungry.3_fallback")

    for key in keys:
        uk = l10n.tr("uk", key, user="@test", event="test", last_donor="Donor")
        en = l10n.tr("en", key, user="@test", event="test", last_donor="Donor")
        assert uk
        assert en


def test_mood_keys_cover_all_moods() -> None:
    for mood in StreamPetMood:
        assert mood.value in MOOD_PHRASE_KEYS
        assert MOOD_PHRASE_KEYS[mood.value]
