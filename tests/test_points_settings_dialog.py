from __future__ import annotations

from PySide6.QtCore import QSettings

from stream_cheremsha.domain.points import PointsConfig
from stream_cheremsha.ui.points_settings_dialog import (
    SETTINGS_POINTS_SONG_COST,
    load_points_config_from_settings,
    save_points_config_to_settings,
)


def test_load_save_points_config_roundtrip() -> None:
    settings = QSettings("stream-cheremsha-test", "points-dialog")
    settings.clear()
    cfg = PointsConfig(
        song_cost=150,
        points_per_coin=2,
        likes_per_point=40,
        points_per_share=8,
        points_per_follow=20,
        watch_points_per_interval=4,
        watch_interval_minutes=15,
    )
    save_points_config_to_settings(settings, cfg)
    loaded = load_points_config_from_settings(settings)
    assert loaded == cfg.sanitized()
    assert int(settings.value(SETTINGS_POINTS_SONG_COST)) == 150
