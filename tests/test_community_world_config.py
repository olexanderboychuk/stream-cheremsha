import json

import pytest

from stream_cheremsha.overlays.community_world_config import (
    community_world_overlay_config_defaults,
    community_world_overlay_config_from_json_text,
    community_world_overlay_config_to_json_text,
    load_community_world_overlay_config,
    save_community_world_overlay_config,
)


def test_defaults_shape() -> None:
    cfg = community_world_overlay_config_defaults()
    assert cfg.enabled is True
    assert cfg.theme == "ukrainian"
    assert cfg.layout_mode == "full"
    assert cfg.quest1_type == "likes"
    assert cfg.quest2_type == "shares"
    assert cfg.quest3_type == "gifts"
    assert cfg.quest4_type == "follows"
    assert cfg.xp_follow == 40
    assert cfg.show_quests is True
    assert cfg.quiet_mode is False


def test_round_trip_preserves_values() -> None:
    cfg = community_world_overlay_config_defaults().replace(
        theme="cyber",
        layout_mode="compact",
        quest_likes_target=9999,
        xp_share=50,
        quiet_mode=True,
        font_family="Comic Sans MS",
    )
    txt = community_world_overlay_config_to_json_text(cfg)
    parsed = community_world_overlay_config_from_json_text(txt)
    assert parsed.theme == "cyber"
    assert parsed.layout_mode == "compact"
    assert parsed.quest_likes_target == 9999
    assert parsed.xp_share == 50
    assert parsed.quiet_mode is True
    assert parsed.font_family == "Comic Sans MS"


def test_from_json_clamps_and_falls_back() -> None:
    raw = {
        "theme": "banana",
        "layout_mode": "tiny",
        "quest1_type": "garbage",
        "quest_likes_target": -5,
        "scale_pct": 999,
        "xp_follow": -10,
        "font_family": "   ",
    }
    cfg = community_world_overlay_config_from_json_text(json.dumps(raw))
    assert cfg.theme == "ukrainian"
    assert cfg.layout_mode == "full"
    assert cfg.quest1_type == "likes"
    assert cfg.quest_likes_target >= 1
    assert cfg.scale_pct == 200
    assert cfg.xp_follow >= 0
    assert cfg.font_family == "Segoe UI"


def test_from_json_rejects_non_object() -> None:
    with pytest.raises(ValueError):
        community_world_overlay_config_from_json_text("[1,2,3]")


def test_save_load_qsettings(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    from PySide6.QtCore import QSettings

    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path))
    settings = QSettings(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        "stream-cheremsha-test",
        "cheremsha-test",
    )
    try:
        cfg = community_world_overlay_config_defaults().replace(theme="pixel")
        save_community_world_overlay_config(cfg, settings=settings)
        loaded = load_community_world_overlay_config(settings=settings)
        assert loaded.theme == "pixel"
    finally:
        settings.clear()
        settings.sync()