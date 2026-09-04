from __future__ import annotations

from typing import Any

from PySide6.QtCore import QSettings

from stream_cheremsha.overlays.registry import OverlayRegistry
from stream_cheremsha.overlays.webcam_frame_controller import WebcamFrameController
from stream_cheremsha.overlays.webcam_frame_overlay import WebcamFrameOverlayType
from stream_cheremsha.overlays.webcam_frame_overlay_config import (
    load_webcam_frame_overlay_config,
    save_webcam_frame_overlay_config,
    webcam_frame_overlay_config_defaults,
    webcam_frame_overlay_config_from_json_text,
    webcam_frame_overlay_config_to_json_text,
    webcam_frame_overlay_config_to_public_dict,
)
from stream_cheremsha.ui.widgets_qml_api import WidgetsQmlApi


def test_webcam_frame_config_defaults() -> None:
    cfg = webcam_frame_overlay_config_defaults()
    assert cfg.enabled is True
    assert cfg.theme == "neon_cyber"
    assert cfg.intensity == "medium"
    assert cfg.frame_style == "primary"
    assert cfg.scale_percent == 100
    assert cfg.cam_label == "CAM // 01"
    assert cfg.enable_energy_flow is True
    assert cfg.enable_boot_animation is True


def test_webcam_frame_config_json_roundtrip() -> None:
    cfg = webcam_frame_overlay_config_defaults().replace(
        theme="synthwave",
        intensity="high",
        scale_percent=150,
        cam_label="CAM // 02",
        enable_sparks=False,
    )
    txt = webcam_frame_overlay_config_to_json_text(cfg)
    cfg2 = webcam_frame_overlay_config_from_json_text(txt)
    assert cfg2.theme == "synthwave"
    assert cfg2.intensity == "high"
    assert cfg2.scale_percent == 150
    assert cfg2.cam_label == "CAM // 02"
    assert cfg2.enable_sparks is False


def test_webcam_frame_invalid_theme_falls_back() -> None:
    cfg = webcam_frame_overlay_config_from_json_text('{"theme": "not_a_theme"}')
    assert cfg.theme == "neon_cyber"


def test_webcam_frame_all_frame_styles_valid() -> None:
    for style in ("primary", "minimal", "tactical", "broadcast", "hologram"):
        cfg = webcam_frame_overlay_config_from_json_text(f'{{"frame_style": "{style}"}}')
        assert cfg.frame_style == style


def test_webcam_frame_invalid_frame_style_falls_back() -> None:
    cfg = webcam_frame_overlay_config_from_json_text('{"frame_style": "not_a_style"}')
    assert cfg.frame_style == "primary"


def test_webcam_frame_scale_percent_clamped() -> None:
    cfg = webcam_frame_overlay_config_from_json_text('{"scale_percent": 999}')
    assert cfg.scale_percent == 250
    cfg2 = webcam_frame_overlay_config_from_json_text('{"scale_percent": 1}')
    assert cfg2.scale_percent == 40


def test_webcam_frame_cam_label_truncated() -> None:
    cfg = webcam_frame_overlay_config_from_json_text(
        '{"cam_label": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"}'
    )
    assert len(cfg.cam_label) <= 24


def test_webcam_frame_config_qsettings(tmp_path: Any) -> None:
    ini = str(tmp_path / "test_settings.ini")
    settings = QSettings(ini, QSettings.Format.IniFormat)

    cfg = webcam_frame_overlay_config_defaults().replace(theme="critical", intensity="low")
    save_webcam_frame_overlay_config(cfg, settings)

    loaded = load_webcam_frame_overlay_config(settings)
    assert loaded.theme == "critical"
    assert loaded.intensity == "low"


def test_webcam_frame_controller_initial_state() -> None:
    controller = WebcamFrameController(pubsub=None, get_locale=lambda: "en", instance="test")
    st = controller.initial_state()
    assert "config" in st
    assert st["config"]["theme"] == "neon_cyber"
    assert st["locale"] == "en"
    # Should not raise even without a pubsub/event loop wired up.
    controller.start()
    controller.schedule_publish()
    controller.reload_config()
    controller.stop()


def test_webcam_frame_overlay_renderer() -> None:
    overlay = WebcamFrameOverlayType()
    html = overlay.render_html({"instance": "main"})
    assert "<!doctype html>" in html.lower()
    assert "webcam" in html.lower() or "cam" in html.lower()
    assert "subscribe" in html.lower()
    assert "background: transparent" in html
    assert "corner-tl" in html
    assert "rail-energy" in html

    init_st = overlay.initial_state({"instance": "main"})
    assert "config" in init_st
    assert init_st["config"]["theme"] == "neon_cyber"
    assert "locale" in init_st


def test_webcam_frame_overlay_renders_all_frame_style_css() -> None:
    overlay = WebcamFrameOverlayType()
    html = overlay.render_html({"instance": "main"})
    for style in ("minimal", "tactical", "broadcast", "hologram"):
        assert f"style-{style}" in html


def test_webcam_frame_registered_in_registry() -> None:
    registry = OverlayRegistry()
    t = registry.get("webcam_frame")
    assert t.type == "webcam_frame"
    html = t.render_html({"instance": "main"})
    assert "<!doctype html>" in html.lower()


def test_webcam_frame_config_to_public_dict_matches_schema() -> None:
    cfg = webcam_frame_overlay_config_defaults()
    d = webcam_frame_overlay_config_to_public_dict(cfg)
    assert d["theme"] == "neon_cyber"
    assert d["enable_status_indicator"] is True
    assert "frame_style" in d


def test_widgets_qml_api_webcam_frame() -> None:
    api = WidgetsQmlApi(overlay_base_url="http://localhost:8080")
    url = api.webcamFrameOverlayUrl()
    assert url == "http://localhost:8080/overlay/webcam_frame?instance=main"

    cfg_map = api.loadWebcamFrameOverlayConfigMap()
    assert isinstance(cfg_map, dict)
    assert "theme" in cfg_map

    cfg_json = api.loadWebcamFrameOverlayConfigJson()
    assert '"theme"' in cfg_json


def test_widgets_qml_api_webcam_frame_url_empty_when_base_missing() -> None:
    api = WidgetsQmlApi(overlay_base_url="")
    assert api.webcamFrameOverlayUrl() == ""
