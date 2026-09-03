from __future__ import annotations

from stream_cheremsha.overlays.social_rotator_stats import SocialRotatorStatsSession


def test_follow_and_donations_rank() -> None:
    s = SocialRotatorStatsSession()
    s.on_follow("kittencat_42")
    s.on_donation(name="A", amount=100, source="donatik")
    s.on_donation(name="B", amount=50, source="donatello")
    s.on_donation(name="C", amount=200, source="tiktok_gift", coin_rate=1.0)
    d = s.to_public_dict()
    assert d["latest_follower"]["name"] == "kittencat_42"
    assert d["latest_donation"]["name"] == "C"
    assert d["latest_donation"]["value"] == 200
    assert d["top_donator"]["name"] == "C"
    assert d["top_donator"]["value"] == 200


def test_tiktok_rate_and_top_keeps_max() -> None:
    s = SocialRotatorStatsSession()
    s.on_donation(name="A", amount=1000, source="tiktok_gift", coin_rate=0.5)
    s.on_donation(name="B", amount=400, source="donatik")
    d = s.to_public_dict()
    assert d["latest_donation"]["name"] == "B"
    assert d["top_donator"]["name"] == "A"
    assert d["top_donator"]["value"] == 500


def test_viewers_sum() -> None:
    s = SocialRotatorStatsSession()
    s.set_viewers("tiktok", 100)
    s.set_viewers("twitch", 40)
    s.set_viewers("kick", 12)
    s.set_viewers("youtube", 0)
    d = s.to_public_dict()
    assert d["viewers_total"] == 152
    s.clear_viewers("twitch")
    assert s.to_public_dict()["viewers_total"] == 112


def test_stream_timer() -> None:
    s = SocialRotatorStatsSession()
    assert s.to_public_dict()["stream_started_at_ms"] is None
    s.set_stream_started_at_ms(123)
    assert s.to_public_dict()["stream_started_at_ms"] == 123
    s.reset()
    assert s.to_public_dict()["latest_follower"] is None
