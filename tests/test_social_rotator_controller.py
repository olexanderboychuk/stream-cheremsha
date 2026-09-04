from __future__ import annotations

from stream_cheremsha.overlays.social_rotator_controller import SocialRotatorController
from stream_cheremsha.overlays.social_rotator_rotation import (
    SocialRotationEntry,
    SocialRotatorRotationEngine,
)


def test_events_do_not_advance_rotation() -> None:
    ctl = SocialRotatorController(pubsub=None, get_locale=lambda: "en", instance="test")
    ctl._rotation = SocialRotatorRotationEngine.from_entries(
        [
            SocialRotationEntry("1", "twitch", "a", "https://twitch.tv/a"),
            SocialRotationEntry("2", "youtube", "b", "https://youtube.com/@b"),
        ],
        interval_ms=60_000,
        now_ms=1000,
    )
    before = ctl.initial_state()["rotation"]["transition_token"]
    ctl.on_follow("X")
    ctl.on_tiktok_gift(sender="Y", count=1, tiktok_coin_each=10)
    ctl.on_donation(name="Z", amount=5, source="donatik")
    ctl.on_viewers("tiktok", 9)
    after = ctl.initial_state()["rotation"]["transition_token"]
    assert after == before
    assert ctl.initial_state()["stats"]["latest_follower"]["name"] == "X"
    assert ctl.initial_state()["stats"]["viewers_total"] == 9


def test_reset_for_new_stream_starts_stream_timer() -> None:
    ctl = SocialRotatorController(pubsub=None, get_locale=lambda: "en", instance="test")
    ctl.on_follow("old")
    ctl.on_stream_live(False)
    assert ctl.initial_state()["stats"]["stream_started_at_ms"] is None
    ctl.reset_for_new_stream()
    st = ctl.initial_state()["stats"]
    assert st["latest_follower"] is None
    assert isinstance(st["stream_started_at_ms"], int)
    assert st["stream_started_at_ms"] > 0


def test_on_stream_live_sets_and_clears_timer() -> None:
    ctl = SocialRotatorController(pubsub=None, get_locale=lambda: "en", instance="test")
    ctl.on_stream_live(True)
    assert isinstance(ctl.initial_state()["stats"]["stream_started_at_ms"], int)
    ctl.on_stream_live(False)
    assert ctl.initial_state()["stats"]["stream_started_at_ms"] is None


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
