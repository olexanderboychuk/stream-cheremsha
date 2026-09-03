from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import QSettings

from stream_cheremsha.overlays.registry import OverlayRegistry
from stream_cheremsha.overlays.stream_goal_controller import StreamGoalController
from stream_cheremsha.overlays.stream_goal_overlay import StreamGoalOverlayType
from stream_cheremsha.overlays.stream_goal_overlay_config import (
    StreamGoalOverlayConfig,
    load_stream_goal_overlay_config,
    save_stream_goal_overlay_config,
    stream_goal_overlay_config_defaults,
    stream_goal_overlay_config_from_json_text,
    stream_goal_overlay_config_to_json_text,
)
from stream_cheremsha.overlays.stream_goal_session import StreamGoalSession
from stream_cheremsha.ui.widgets_qml_api import WidgetsQmlApi


def test_stream_goal_config_defaults() -> None:
    cfg = stream_goal_overlay_config_defaults()
    assert cfg.enabled is True
    assert cfg.goal_type == "followers"
    assert cfg.target_value == 10000
    assert cfg.skin == "digital_core"
    assert cfg.accent_color == "#00ffff"
    assert cfg.scale_percent == 100


def test_stream_goal_config_json_roundtrip() -> None:
    cfg = stream_goal_overlay_config_defaults().replace(
        title="EPIC LIKE GOAL",
        goal_type="likes",
        target_value=5000,
        current_value=1200,
        accent_color="#ff0055",
        scale_percent=125,
    )
    txt = stream_goal_overlay_config_to_json_text(cfg)
    cfg2 = stream_goal_overlay_config_from_json_text(txt)
    assert cfg2.title == "EPIC LIKE GOAL"
    assert cfg2.goal_type == "likes"
    assert cfg2.target_value == 5000
    assert cfg2.current_value == 1200
    assert cfg2.accent_color == "#ff0055"
    assert cfg2.scale_percent == 125


def test_stream_goal_scale_percent_clamped() -> None:
    cfg = stream_goal_overlay_config_from_json_text(
        stream_goal_overlay_config_to_json_text(
            stream_goal_overlay_config_defaults().replace(scale_percent=999)
        )
    )
    assert cfg.scale_percent == 250
    cfg2 = stream_goal_overlay_config_from_json_text('{"scale_percent": 10}')
    assert cfg2.scale_percent == 40


def test_stream_goal_config_qsettings(tmp_path: Any) -> None:
    ini = str(tmp_path / "test_settings.ini")
    settings = QSettings(ini, QSettings.Format.IniFormat)

    cfg = stream_goal_overlay_config_defaults().replace(title="CUSTOM GOAL", target_value=888)
    save_stream_goal_overlay_config(cfg, settings)

    loaded = load_stream_goal_overlay_config(settings)
    assert loaded.title == "CUSTOM GOAL"
    assert loaded.target_value == 888


def test_stream_goal_session_progress() -> None:
    cfg = stream_goal_overlay_config_defaults().replace(
        goal_type="followers", current_value=0, target_value=100
    )
    session = StreamGoalSession.from_config(cfg)

    assert session.current_value == 0
    assert session.progress == 0.0

    session.add_follow("alice")
    assert session.current_value == 1
    assert session.progress == 0.01

    session.add_follow("bob")
    assert session.current_value == 2
    assert session.progress == 0.02


def test_stream_goal_session_milestones() -> None:
    cfg = stream_goal_overlay_config_defaults().replace(
        goal_type="likes", current_value=0, target_value=100
    )
    session = StreamGoalSession.from_config(cfg)
    session.add_like(30)
    session.flush_likes()

    st = session.to_overlay_dict()
    assert st["progress_percent"] == 30
    # Milestone at 25% should be reached
    milestones = st["milestones"]
    ms25 = next(m for m in milestones if m["percent"] == 25)
    assert ms25["triggered"] is True


def test_stream_goal_session_combo_decay() -> None:
    cfg = stream_goal_overlay_config_defaults().replace(
        goal_type="likes", current_value=0, target_value=1000, combo_window_sec=2.0
    )
    session = StreamGoalSession.from_config(cfg)
    session.add_like(10)
    session.flush_likes()
    assert session.combo_count == 1

    session.add_like(10)
    session.flush_likes()
    assert session.combo_count == 2

    session.tick(session.combo_expires_at + 1.0)
    assert session.combo_count == 0


def test_stream_goal_controller_events() -> None:
    controller = StreamGoalController(
        pubsub=None, get_locale=lambda: "en", instance="test"
    )
    init_st = controller.initial_state()
    assert "goal_type" in init_st

    controller.on_follow("user1")
    state = controller._session.to_overlay_dict()
    assert isinstance(state["current_value"], int)


def test_stream_goal_overlay_renderer() -> None:
    overlay = StreamGoalOverlayType()
    html = overlay.render_html({"instance": "main"})
    assert "<!doctype html>" in html.lower()
    assert "Stream Goal" in html
    assert "subscribe" in html.lower()
    assert 'id="hdrTitle">FOLLOW GOAL</div>' in html
    assert "tier-idle" in html
    assert "CORE BREACH" in html  # present for completion anim only
    assert 'class="breach-text"' in html

    init_st = overlay.initial_state({"instance": "main"})
    assert "config" in init_st
    assert "goal_type" in init_st
    assert init_st["title"] != "CORE BREACH"


def test_widgets_qml_api_stream_goal() -> None:
    api = WidgetsQmlApi(overlay_base_url="http://localhost:8080")
    url = api.streamGoalOverlayUrl()
    assert url == "http://localhost:8080/overlay/stream_goal?instance=main"

    cfg_map = api.loadStreamGoalOverlayConfigMap()
    assert isinstance(cfg_map, dict)
    assert "goal_type" in cfg_map

    cfg_json = api.loadStreamGoalOverlayConfigJson()
    assert '"goal_type"' in cfg_json
