from __future__ import annotations

from stream_cheremsha.domain.points import (
    PointsConfig,
    StreamEarnTracker,
    earn_rate_template_vars,
    normalize_tiktok_username,
)


def test_normalize_tiktok_username() -> None:
    assert normalize_tiktok_username("  @Alice  ") == "alice"
    assert normalize_tiktok_username("@@bob") == "bob"
    assert normalize_tiktok_username("") == ""
    assert normalize_tiktok_username("  ") == ""


def test_config_sanitized_clamps_negatives() -> None:
    cfg = PointsConfig(
        song_cost=-5,
        points_per_coin=-1,
        likes_per_point=0,
        watch_interval_minutes=0,
        follow_cooldown_sec=-1,
    ).sanitized()
    assert cfg.song_cost == 0
    assert cfg.points_per_coin == 0
    assert cfg.likes_per_point == 1
    assert cfg.watch_interval_minutes == 1
    assert cfg.follow_cooldown_sec == 0


def test_coins_to_points() -> None:
    cfg = PointsConfig(points_per_coin=2)
    assert cfg.coins_to_points(50) == 100
    assert cfg.coins_to_points(0) == 0
    assert cfg.coins_to_points(-10) == 0


def test_like_accumulation_uncapped() -> None:
    cfg = PointsConfig(likes_per_point=50)
    tracker = StreamEarnTracker(cfg)
    assert tracker.on_like("k", 49) == 0
    assert tracker.on_like("k", 1) == 1
    assert tracker.on_like("k", 120) == 2
    assert tracker.on_like("k", 500) == 10


def test_share_awards_each_event_when_allowed() -> None:
    cfg = PointsConfig(points_per_share=10)
    tracker = StreamEarnTracker(cfg)
    assert tracker.on_share("k", 1) == 10
    assert tracker.on_share("k", 1) == 10
    assert tracker.on_share("k", 3) == 30


def test_follow_once_per_stream() -> None:
    cfg = PointsConfig(points_per_follow=25)
    tracker = StreamEarnTracker(cfg)
    assert tracker.on_follow("k") == 25
    assert tracker.on_follow("k") == 0
    tracker.reset()
    assert tracker.on_follow("k") == 25


def test_follow_is_per_viewer() -> None:
    cfg = PointsConfig(points_per_follow=25)
    tracker = StreamEarnTracker(cfg)
    assert tracker.on_follow("a") == 25
    assert tracker.on_follow("b") == 25


def test_watch_tick_uncapped() -> None:
    cfg = PointsConfig(watch_points_per_interval=5)
    tracker = StreamEarnTracker(cfg)
    assert tracker.on_watch_tick("k") == 5
    assert tracker.on_watch_tick("k") == 5


def test_empty_key_awards_nothing() -> None:
    tracker = StreamEarnTracker(PointsConfig())
    assert tracker.on_like("", 100) == 0
    assert tracker.on_share("  ", 5) == 0
    assert tracker.on_follow("") == 0
    assert tracker.on_watch_tick("") == 0


def test_earn_rate_template_vars() -> None:
    cfg = PointsConfig(
        points_per_coin=2,
        likes_per_point=40,
        points_per_share=15,
        points_per_follow=30,
        watch_points_per_interval=7,
        watch_interval_minutes=5,
    )
    v = earn_rate_template_vars(cfg)
    assert v == {
        "per_coin": "2",
        "likes_per_point": "40",
        "per_share": "15",
        "per_follow": "30",
        "watch_points": "7",
        "watch_interval": "5",
    }


def test_reset_clears_like_and_follow_state() -> None:
    cfg = PointsConfig(likes_per_point=50, points_per_follow=25)
    tracker = StreamEarnTracker(cfg)
    assert tracker.on_like("k", 30) == 0
    assert tracker.on_follow("k") == 25
    tracker.reset()
    assert tracker.on_like("k", 30) == 0
    assert tracker.on_like("k", 20) == 1
    assert tracker.on_follow("k") == 25
