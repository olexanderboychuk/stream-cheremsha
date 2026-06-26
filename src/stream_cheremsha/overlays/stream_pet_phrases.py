from __future__ import annotations

from typing import Any

_MAX_LEVEL = 3


def _keys(prefix: str, count: int) -> tuple[str, ...]:
    return tuple(f"{prefix}.{i}" for i in range(1, count + 1))


HUNGRY_PHRASE_KEYS: tuple[str, ...] = _keys("stream_pet.hungry", 12)
HUNGRY_DONOR_PHRASE_KEY = "stream_pet.hungry.3"
HUNGRY_DONOR_FALLBACK_KEY = "stream_pet.hungry.3_fallback"

CHILL_PHRASE_KEYS: tuple[str, ...] = _keys("stream_pet.chill", 12)
HYPER_PHRASE_KEYS: tuple[str, ...] = _keys("stream_pet.hyper", 10)
SLEEP_PHRASE_KEYS: tuple[str, ...] = _keys("stream_pet.sleep", 8)

GENERAL_THANKS_KEYS: tuple[str, ...] = _keys("stream_pet.thanks", 12)
HYPE_THANKS_KEYS: tuple[str, ...] = _keys("stream_pet.thanks.hype", 10)

LEVEL1_IDLE_KEYS: tuple[str, ...] = _keys("stream_pet.l1.idle", 8)
LEVEL1_THANKS_KEYS: tuple[str, ...] = _keys("stream_pet.l1.thanks", 8)
LEVEL2_IDLE_KEYS: tuple[str, ...] = _keys("stream_pet.l2.idle", 8)
LEVEL2_THANKS_KEYS: tuple[str, ...] = _keys("stream_pet.l2.thanks", 8)
LEVEL3_IDLE_KEYS: tuple[str, ...] = _keys("stream_pet.l3.idle", 8)
LEVEL3_THANKS_KEYS: tuple[str, ...] = _keys("stream_pet.l3.thanks", 8)
LEVEL3_VIP_KEYS: tuple[str, ...] = _keys("stream_pet.l3.vip", 8)

EVOLVE_PHRASE_KEYS: dict[int, str] = {
    2: "stream_pet.evolve.2",
    3: "stream_pet.evolve.3",
}

EVENT_THANKS_KEYS: dict[str, tuple[str, ...]] = {
    "chat": _keys("stream_pet.thanks.chat", 10),
    "like": _keys("stream_pet.thanks.like", 10),
    "follow": _keys("stream_pet.thanks.follow", 10),
    "join": _keys("stream_pet.thanks.join", 8),
    "gift": _keys("stream_pet.thanks.gift", 10),
    "gift_large": _keys("stream_pet.thanks.gift_large", 10),
    "member": _keys("stream_pet.thanks.member", 8),
    "spam": _keys("stream_pet.thanks.spam", 8),
    "chat_burst": _keys("stream_pet.thanks.chat_burst", 8),
}

HYPE_EVENT_KIND_VALUES: frozenset[str] = frozenset({"gift_large", "chat_burst"})

MOOD_PHRASE_KEYS: dict[str, tuple[str, ...]] = {
    "hungry": tuple(k for k in HUNGRY_PHRASE_KEYS if k != HUNGRY_DONOR_PHRASE_KEY),
    "chill": CHILL_PHRASE_KEYS,
    "hyper": HYPER_PHRASE_KEYS,
    "sleep": SLEEP_PHRASE_KEYS,
}

_LEVEL_IDLE_KEYS: dict[int, tuple[str, ...]] = {
    1: LEVEL1_IDLE_KEYS,
    2: LEVEL2_IDLE_KEYS,
    3: LEVEL3_IDLE_KEYS,
}

_LEVEL_THANKS_KEYS: dict[int, tuple[str, ...]] = {
    1: LEVEL1_THANKS_KEYS,
    2: LEVEL2_THANKS_KEYS,
    3: LEVEL3_THANKS_KEYS,
}


def _clamp_level(level: int) -> int:
    return max(1, min(_MAX_LEVEL, int(level)))


def _event_kind_value(kind: Any) -> str:
    value = getattr(kind, "value", kind)
    return str(value or "").strip().lower()


def idle_phrase_keys(level: int, mood: str) -> tuple[str, ...]:
    lvl = _clamp_level(level)
    mood_keys = MOOD_PHRASE_KEYS.get(str(mood), ())
    level_keys = _LEVEL_IDLE_KEYS.get(lvl, ())
    if lvl >= 2:
        return level_keys + mood_keys
    return mood_keys + level_keys


def thanks_templates_for(kind: Any, level: int = 1) -> tuple[str, ...]:
    kind_val = _event_kind_value(kind)
    lvl = _clamp_level(level)
    level_pool = _LEVEL_THANKS_KEYS.get(lvl, ())
    event_pool = EVENT_THANKS_KEYS.get(kind_val, ())
    if kind_val in HYPE_EVENT_KIND_VALUES:
        return level_pool + event_pool + HYPE_THANKS_KEYS + GENERAL_THANKS_KEYS
    if event_pool:
        return level_pool + event_pool + GENERAL_THANKS_KEYS
    return level_pool + GENERAL_THANKS_KEYS
