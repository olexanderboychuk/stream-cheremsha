from stream_cheremsha.overlays.battle_royale_overlay_config import (
    battle_royale_overlay_config_defaults,
    battle_royale_overlay_config_from_json_text,
    battle_royale_overlay_config_to_json_text,
)


def test_battle_royale_config_roundtrip() -> None:
    cfg = battle_royale_overlay_config_defaults()
    txt = battle_royale_overlay_config_to_json_text(cfg)
    cfg2 = battle_royale_overlay_config_from_json_text(txt)
    assert cfg2.max_hp == cfg.max_hp
    assert cfg2.crit_threshold_diamonds == cfg.crit_threshold_diamonds
    assert cfg2.auto_arm_enabled is True
    assert cfg2.base_font_size_px == 14
    assert cfg2.hide_when_idle is True


def test_battle_royale_base_font_size_clamped() -> None:
    cfg = battle_royale_overlay_config_from_json_text('{"schema_version":1,"base_font_size_px":99}')
    assert cfg.base_font_size_px == 32


def test_battle_royale_legacy_text_scale_pct_migrates_to_px() -> None:
    cfg = battle_royale_overlay_config_from_json_text('{"schema_version":1,"text_scale_pct":160}')
    assert cfg.base_font_size_px == 22
