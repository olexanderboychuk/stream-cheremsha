from __future__ import annotations

from stream_cheremsha.overlays.social_rotator_controller import SocialRotatorController
from stream_cheremsha.overlays.social_rotator_rotation import (
    SocialRotationEntry,
    SocialRotatorRotationEngine,
)


def test_initial_state_is_rotation_only() -> None:
    ctl = SocialRotatorController(pubsub=None, get_locale=lambda: "en", instance="test")
    st = ctl.initial_state()
    assert "rotation" in st
    assert "platforms_enabled" in st
    assert "stats" not in st


def test_reset_for_new_stream_restarts_rotation_timer() -> None:
    ctl = SocialRotatorController(pubsub=None, get_locale=lambda: "en", instance="test")
    ctl._rotation.started_at_ms = 0
    ctl.reset_for_new_stream()
    assert isinstance(ctl._rotation.started_at_ms, int)
    assert ctl._rotation.started_at_ms > 0


def test_rotation_tick_advances() -> None:
    ctl = SocialRotatorController(pubsub=None, get_locale=lambda: "en", instance="test")
    ctl._rotation = SocialRotatorRotationEngine.from_entries(
        [
            SocialRotationEntry("1", "twitch", "a", "u1"),
            SocialRotationEntry("2", "youtube", "b", "u2"),
        ],
        interval_ms=1000,
        now_ms=1000,
    )
    ctl._rotation.started_at_ms = 0
    before = ctl._rotation.transition_token
    assert ctl._rotation.tick(now_ms=2000) is True
    assert ctl._rotation.transition_token == before + 1
