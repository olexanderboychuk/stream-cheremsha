from __future__ import annotations

from stream_cheremsha.overlays.live_leaderboard_simple_config import (
    live_leaderboard_simple_config_defaults,
    live_leaderboard_simple_config_from_json_text,
    live_leaderboard_simple_config_to_json_text,
)
from stream_cheremsha.overlays.live_leaderboard_simple_controller import (
    LiveLeaderboardSimpleController,
)
from stream_cheremsha.overlays.live_leaderboard_simple_overlay import (
    LiveLeaderboardSimpleOverlayType,
)
from stream_cheremsha.overlays.registry import OverlayRegistry


def test_simple_defaults_are_calm() -> None:
    cfg = live_leaderboard_simple_config_defaults()
    assert cfg.transition == "fade"
    assert cfg.animation_intensity == "low"
    assert cfg.enable_crt is False
    assert cfg.enable_particles is False
    assert cfg.text_effect_username == "none"
    assert cfg.wave_enabled is False
    assert cfg.wave_speed == "normal"
    assert cfg.font_size_px == 15


def test_simple_config_roundtrip_with_effects() -> None:
    cfg = live_leaderboard_simple_config_defaults().replace(
        text_effect_username="rainbow",
        wave_enabled=True,
        wave_speed="fast",
        transition="slide",
    )
    txt = live_leaderboard_simple_config_to_json_text(cfg)
    cfg2 = live_leaderboard_simple_config_from_json_text(txt)
    assert cfg2.text_effect_username == "rainbow"
    assert cfg2.wave_enabled is True
    assert cfg2.wave_speed == "fast"
    assert cfg2.transition == "slide"


def test_simple_config_rejects_cyber_effect() -> None:
    cfg = live_leaderboard_simple_config_defaults().replace(text_effect_username="cyberpunk")  # type: ignore[arg-type]
    txt = live_leaderboard_simple_config_to_json_text(cfg)
    cfg2 = live_leaderboard_simple_config_from_json_text(txt)
    assert cfg2.text_effect_username == "none"


def test_simple_overlay_renders_scenes_effects_and_smooth_transitions() -> None:
    overlay = LiveLeaderboardSimpleOverlayType()
    html = overlay.render_html({"instance": "main"})
    low = html.lower()
    assert "<!doctype html>" in low
    assert "live_leaderboard_simple" in html
    assert "transition_token" in html
    # three scenes, neutral naming handled client-side via scene.* keys
    assert "scene.hall_of_fame" in html
    assert "scene.arena" in html
    assert "scene.energy_network" in html
    # top-likers-style text effects, no cyberpunk effect
    for fx in (
        "tfx-rainbow",
        "tfx-aurora",
        "tfx-fire",
        "tfx-ice",
        "tfx-cold",
        "tfx-freeze",
        "tfx-strong",
    ):
        assert fx in html
    assert "tfx-cyberpunk" not in html
    # wave animation + smooth stage transition, no glitch/crt/scanlines
    assert "waveY" in html
    assert "stageIn" in html
    assert "glitch" not in low
    assert "scanlines" not in low
    assert "press start 2p" not in low
    # background color/opacity applied in JS, 4 distinct themes, badge rank style
    assert "hexToRgba" in html
    assert "background_opacity" in html
    assert "linear-gradient(135deg" in html
    assert 'data-rankstyle="badge"' in html
    assert "font_size_px" in html
    assert "zoom" in html

    init_st = overlay.initial_state({"instance": "main"})
    assert init_st["presentation"]["scene_id"] == "hall_of_fame"
    assert init_st["config"]["transition"] == "fade"

    reg = OverlayRegistry()
    assert reg.get("live_leaderboard_simple").type == "live_leaderboard_simple"


def test_simple_trimmed_sequence_is_not_resurrected() -> None:
    """Regression: deleting steps must persist; the parser must not re-append
    hall-of-fame steps for enabled sources missing from the sequence."""
    import json

    payload = {
        "sequence": [
            {"source_id": "gifters", "scene_id": "arena", "duration_sec": 5},
            {"source_id": "likers", "scene_id": "hall_of_fame", "duration_sec": 8},
        ]
    }
    cfg = live_leaderboard_simple_config_from_json_text(json.dumps(payload))
    steps = json.loads(cfg.sequence_json)
    assert [(s["source_id"], s["scene_id"]) for s in steps] == [
        ("gifters", "arena"),
        ("likers", "hall_of_fame"),
    ]


def test_simple_controller_topic_and_scene_preserved_on_events() -> None:
    ctl = LiveLeaderboardSimpleController(pubsub=None, get_locale=lambda: "uk", instance="test")
    assert ctl.OVERLAY_TYPE == "live_leaderboard_simple"
    before = ctl.initial_state()["presentation"]
    ctl.on_like("kriss", 12400, user_key="k")
    ctl._ranking.flush_likes()
    after = ctl.initial_state()["presentation"]
    assert after["scene_id"] == before["scene_id"]
    assert after["transition_token"] == before["transition_token"]
    assert ctl.initial_state()["rankings"]["likers"][0]["value"] == 12400


def test_simple_neutral_scene_labels_localized() -> None:
    from stream_cheremsha import l10n

    assert l10n.tr("uk", "live_leaderboard_simple.scene.hall_of_fame") == "Лідери"
    assert l10n.tr("en", "live_leaderboard_simple.scene.arena") == "Top 3"
    assert l10n.tr("en", "live_leaderboard_simple.scene.energy_network") == "Overview"
