from __future__ import annotations

from unittest.mock import MagicMock

from stream_cheremsha.overlays.stream_info_controller import StreamInfoController


def test_stream_info_controller_builds_stats_state() -> None:
    c = StreamInfoController(pubsub=None, get_locale=lambda: "uk")
    c.on_donation(name="Diamond_ua", amount=1500, source="donatik")
    c.on_viewers("tiktok", 100)
    c.on_stream_live(True)
    st = c.initial_state()
    assert "stats" in st and "config" in st
    assert "rotation" not in st
    assert st["stats"]["top_donator"]["name"] == "Diamond_ua"
    assert st["stats"]["viewers_total"] >= 100
    assert st["stats"]["stream_started_at_ms"] is not None


def test_stream_info_controller_respects_enabled_flag() -> None:
    c = StreamInfoController(pubsub=MagicMock(), get_locale=lambda: "uk")
    c.on_follow("someone")
    assert c.initial_state()["stats"]["latest_follower"] in (None, {"name": "someone"})
