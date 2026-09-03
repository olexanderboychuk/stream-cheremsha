from __future__ import annotations

from stream_cheremsha.overlays.social_rotator_rotation import (
    SocialRotatorRotationEngine,
    enabled_rotation_entries,
)


def _plats() -> list[dict[str, object]]:
    return [
        {"id": "1", "platform": "twitch", "username": "a", "url": "", "enabled": True, "order": 0},
        {"id": "2", "platform": "youtube", "username": "b", "url": "", "enabled": True, "order": 1},
        {"id": "3", "platform": "kick", "username": "", "url": "", "enabled": True, "order": 2},
        {
            "id": "4",
            "platform": "telegram",
            "username": "c",
            "url": "",
            "enabled": False,
            "order": 3,
        },
    ]


def test_enabled_entries_skip_disabled_and_empty_username() -> None:
    ents = enabled_rotation_entries(_plats())
    assert [e.platform for e in ents] == ["twitch", "youtube"]


def test_advance_and_token() -> None:
    ents = enabled_rotation_entries(_plats())
    rot = SocialRotatorRotationEngine.from_entries(ents, interval_ms=8000, now_ms=1000)
    assert rot.transition_token == 1
    assert rot.current_entry is not None
    assert rot.current_entry.platform == "twitch"
    rot.advance(now_ms=2000)
    assert rot.transition_token == 2
    assert rot.current_entry is not None
    assert rot.current_entry.platform == "youtube"
    rot.advance(now_ms=3000)
    assert rot.current_entry is not None
    assert rot.current_entry.platform == "twitch"


def test_tick_respects_interval() -> None:
    ents = enabled_rotation_entries(_plats())
    rot = SocialRotatorRotationEngine.from_entries(ents, interval_ms=5000, now_ms=10_000)
    assert rot.tick(now_ms=12_000) is False
    assert rot.tick(now_ms=15_000) is True
    assert rot.current_entry is not None
    assert rot.current_entry.platform == "youtube"


def test_preserve_position_on_replace() -> None:
    ents = enabled_rotation_entries(_plats())
    rot = SocialRotatorRotationEngine.from_entries(ents, interval_ms=8000, now_ms=1000)
    rot.advance(now_ms=2000)
    token = rot.transition_token
    started = rot.started_at_ms
    rot.replace_entries(ents, interval_ms=8000, now_ms=9000, preserve_position=True)
    assert rot.current_entry is not None
    assert rot.current_entry.platform == "youtube"
    assert rot.transition_token == token
    assert rot.started_at_ms == started


def test_single_entry_no_auto_advance() -> None:
    ents = enabled_rotation_entries(
        [{"id": "1", "platform": "twitch", "username": "a", "url": "", "enabled": True, "order": 0}]
    )
    rot = SocialRotatorRotationEngine.from_entries(ents, interval_ms=1000, now_ms=0)
    assert rot.tick(now_ms=5000) is False
    assert rot.remaining_ms(now_ms=5000) == 0


def test_empty_entries_paused() -> None:
    rot = SocialRotatorRotationEngine.from_entries([], interval_ms=8000, now_ms=0)
    assert rot.current_entry is None
    assert rot.tick(now_ms=99999) is False
    assert rot.presentation_dict(server_now_ms=100)["active_index"] == -1
