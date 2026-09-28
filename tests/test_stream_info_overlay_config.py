from __future__ import annotations

from PySide6.QtCore import QSettings

from stream_cheremsha.overlays.stream_info_overlay_config import (
    load_stream_info_overlay_config,
    save_stream_info_overlay_config,
    stream_info_overlay_config_defaults,
    stream_info_overlay_config_from_json_text,
    stream_info_overlay_config_to_json_text,
)


def test_stream_info_config_roundtrip(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    cfg = stream_info_overlay_config_defaults()
    assert cfg.show_stream_time is True
    assert cfg.show_top_donator is True
    assert cfg.show_online is True
    assert cfg.show_latest_follower is True
    assert cfg.show_latest_donation is True
    txt = stream_info_overlay_config_to_json_text(cfg)
    back = stream_info_overlay_config_from_json_text(txt)
    assert back.show_top_donator == cfg.show_top_donator
    assert back.tiktok_coin_to_value_rate == cfg.tiktok_coin_to_value_rate


def test_stream_info_config_rejects_bad_payload() -> None:
    bad = stream_info_overlay_config_from_json_text(
        '{"enabled": true, "theme": "nope", "scale_percent": 9999}'
    )
    assert bad.theme in ("neon_cyber", "synthwave", "toxic", "ice", "amber")
    assert 40 <= bad.scale_percent <= 250


def test_stream_info_qsettings_roundtrip(tmp_path) -> None:  # type: ignore[no-untyped-def]
    ini = str(tmp_path / "si.ini")
    settings = QSettings(ini, QSettings.Format.IniFormat)
    cfg = stream_info_overlay_config_defaults().replace(
        show_top_donator=False, background_opacity_percent=0
    )
    save_stream_info_overlay_config(cfg, settings)
    loaded = load_stream_info_overlay_config(settings)
    assert loaded.show_top_donator is False
    assert loaded.background_opacity_percent == 0
