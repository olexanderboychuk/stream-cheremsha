from __future__ import annotations

import json

from PySide6.QtCore import QSettings

from stream_cheremsha.overlays.live_leaderboard_overlay_config import (
    enabled_scenes_from_config,
    enabled_sources_from_config,
    live_leaderboard_overlay_config_defaults,
    live_leaderboard_overlay_config_from_json_text,
    live_leaderboard_overlay_config_to_json_text,
    load_live_leaderboard_overlay_config,
    parse_sequence_steps,
    save_live_leaderboard_overlay_config,
)
from stream_cheremsha.overlays.live_leaderboard_ranking import LiveLeaderboardRankingEngine
from stream_cheremsha.overlays.live_leaderboard_rotation import (
    SCENE_ARENA,
    SCENE_ENERGY_NETWORK,
    SCENE_HALL_OF_FAME,
    SOURCE_GIFTERS,
    SOURCE_LIKERS,
    LiveLeaderboardRotationEngine,
    RotationStep,
    filter_sequence_for_config,
)


def test_rotation_advances_and_increments_token() -> None:
    rot = LiveLeaderboardRotationEngine.from_steps(
        [
            RotationStep(SOURCE_LIKERS, SCENE_HALL_OF_FAME, 8.0),
            RotationStep(SOURCE_LIKERS, SCENE_ARENA, 6.0),
        ],
        now_ms=1_000,
    )
    assert rot.transition_token == 1
    assert rot.current_step.scene_id == SCENE_HALL_OF_FAME
    rot.advance(now_ms=2_000)
    assert rot.transition_token == 2
    assert rot.current_step.scene_id == SCENE_ARENA
    rot.advance(now_ms=3_000)
    assert rot.transition_token == 3
    assert rot.current_step.scene_id == SCENE_HALL_OF_FAME
    assert rot.sequence_index == 0


def test_rotation_tick_respects_duration() -> None:
    rot = LiveLeaderboardRotationEngine.from_steps(
        [
            RotationStep(SOURCE_LIKERS, SCENE_HALL_OF_FAME, 5.0),
            RotationStep(SOURCE_GIFTERS, SCENE_ARENA, 5.0),
        ],
        now_ms=10_000,
    )
    assert rot.tick(now_ms=12_000) is False
    assert rot.transition_token == 1
    assert rot.tick(now_ms=15_000) is True
    assert rot.transition_token == 2
    assert rot.current_step.source_id == SOURCE_GIFTERS


def test_ranking_updates_do_not_change_presentation() -> None:
    rot = LiveLeaderboardRotationEngine.from_steps(
        [RotationStep(SOURCE_LIKERS, SCENE_HALL_OF_FAME, 8.0)],
        now_ms=1_000,
    )
    token_before = rot.transition_token
    scene_before = rot.current_step.scene_id
    index_before = rot.sequence_index

    eng = LiveLeaderboardRankingEngine()
    eng.add_likes(user_key="a", display_name="A", n=50, immediate=True)
    eng.add_gift_coins(user_key="b", display_name="B", coins=999)
    eng.flush_likes()
    _ = eng.all_rankings(limit=10)

    assert rot.transition_token == token_before
    assert rot.current_step.scene_id == scene_before
    assert rot.sequence_index == index_before


def test_filter_disabled_sources_and_scenes() -> None:
    steps = [
        RotationStep(SOURCE_LIKERS, SCENE_HALL_OF_FAME, 8.0),
        RotationStep(SOURCE_GIFTERS, SCENE_ARENA, 6.0),
        RotationStep(SOURCE_LIKERS, SCENE_ENERGY_NETWORK, 6.0),
    ]
    filtered = filter_sequence_for_config(
        steps,
        enabled_sources={SOURCE_LIKERS},
        enabled_scenes={SCENE_HALL_OF_FAME, SCENE_ARENA},
    )
    assert len(filtered) == 1
    assert filtered[0].source_id == SOURCE_LIKERS
    assert filtered[0].scene_id == SCENE_HALL_OF_FAME


def test_config_roundtrip_and_clamps() -> None:
    cfg = live_leaderboard_overlay_config_defaults().replace(
        top_n=99,
        scale_percent=10,
        enable_sharers=True,
        accent_color="#ff2bd6",
    )
    txt = live_leaderboard_overlay_config_to_json_text(cfg)
    cfg2 = live_leaderboard_overlay_config_from_json_text(txt)
    assert cfg2.top_n == 10
    assert cfg2.scale_percent == 40
    assert cfg2.enable_sharers is True
    assert cfg2.accent_color == "#ff2bd6"
    assert isinstance(json.loads(txt)["sequence"], list)


def test_config_qsettings(tmp_path) -> None:  # type: ignore[no-untyped-def]
    ini = str(tmp_path / "ll.ini")
    settings = QSettings(ini, QSettings.Format.IniFormat)
    cfg = live_leaderboard_overlay_config_defaults().replace(top_n=7)
    save_live_leaderboard_overlay_config(cfg, settings)
    loaded = load_live_leaderboard_overlay_config(settings)
    assert loaded.top_n == 7


def test_enabled_sets_from_config() -> None:
    cfg = live_leaderboard_overlay_config_defaults().replace(
        enable_likers=True,
        enable_gifters=False,
        enable_energy_network=False,
    )
    assert SOURCE_LIKERS in enabled_sources_from_config(cfg)
    assert SOURCE_GIFTERS not in enabled_sources_from_config(cfg)
    assert SCENE_ENERGY_NETWORK not in enabled_scenes_from_config(cfg)
    steps = parse_sequence_steps(cfg)
    assert steps


def test_ensure_enabled_sources_appends_missing_sequence_steps() -> None:
    from stream_cheremsha.overlays.live_leaderboard_overlay_config import (
        ensure_enabled_sources_in_sequence,
    )
    from stream_cheremsha.overlays.live_leaderboard_rotation import (
        SOURCE_COMMENTERS,
        SOURCE_CONTRIBUTORS,
        SOURCE_SHARERS,
    )

    cfg = live_leaderboard_overlay_config_defaults().replace(
        enable_sharers=True,
        enable_commenters=True,
        enable_contributors=True,
        sequence_json=json.dumps(
            [
                {"source_id": SOURCE_LIKERS, "scene_id": SCENE_HALL_OF_FAME, "duration_sec": 8},
                {"source_id": SOURCE_GIFTERS, "scene_id": SCENE_ARENA, "duration_sec": 6},
            ],
            ensure_ascii=False,
        ),
    )
    synced = ensure_enabled_sources_in_sequence(cfg)
    sources = {s.source_id for s in parse_sequence_steps(synced)}
    assert SOURCE_SHARERS in sources
    assert SOURCE_COMMENTERS in sources
    assert SOURCE_CONTRIBUTORS in sources
    filtered = filter_sequence_for_config(
        parse_sequence_steps(synced),
        enabled_sources=enabled_sources_from_config(synced),
        enabled_scenes=enabled_scenes_from_config(synced),
    )
    assert {s.source_id for s in filtered} >= {
        SOURCE_LIKERS,
        SOURCE_GIFTERS,
        SOURCE_SHARERS,
        SOURCE_COMMENTERS,
        SOURCE_CONTRIBUTORS,
    }


def test_migrate_legacy_optional_sources_off() -> None:
    from stream_cheremsha.overlays.live_leaderboard_overlay_config import (
        migrate_live_leaderboard_overlay_config,
    )
    from stream_cheremsha.overlays.live_leaderboard_rotation import (
        SOURCE_COMMENTERS,
        SOURCE_CONTRIBUTORS,
        SOURCE_SHARERS,
    )

    legacy = live_leaderboard_overlay_config_defaults().replace(
        enable_sharers=False,
        enable_commenters=False,
        enable_contributors=False,
        sequence_json=json.dumps(
            [
                {"source_id": SOURCE_LIKERS, "scene_id": SCENE_HALL_OF_FAME, "duration_sec": 8},
                {"source_id": SOURCE_GIFTERS, "scene_id": SCENE_ARENA, "duration_sec": 6},
            ],
            ensure_ascii=False,
        ),
    )
    migrated = migrate_live_leaderboard_overlay_config(legacy)
    assert migrated.enable_sharers is True
    assert migrated.enable_commenters is True
    assert migrated.enable_contributors is True
    sources = {s.source_id for s in parse_sequence_steps(migrated)}
    assert SOURCE_SHARERS in sources
    assert SOURCE_COMMENTERS in sources
    assert SOURCE_CONTRIBUTORS in sources
