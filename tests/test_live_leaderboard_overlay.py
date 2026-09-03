from __future__ import annotations

from stream_cheremsha.overlays.live_leaderboard_controller import LiveLeaderboardController
from stream_cheremsha.overlays.live_leaderboard_overlay import LiveLeaderboardOverlayType
from stream_cheremsha.overlays.registry import OverlayRegistry
from stream_cheremsha.ui.widgets_qml_api import WidgetsQmlApi


def test_controller_events_do_not_change_scene() -> None:
    ctl = LiveLeaderboardController(pubsub=None, get_locale=lambda: "en", instance="test")
    before = ctl.initial_state()["presentation"]
    token = before["transition_token"]
    scene = before["scene_id"]
    index = before["sequence_index"]

    ctl.on_like("Alice", 100, user_key="a")
    ctl._ranking.flush_likes()
    ctl.on_gift(sender="Bob", count=2, tiktok_coin_each=50, sender_user_key="b")
    ctl.on_share("Carol", 3, stable_key="c")
    ctl.on_comment("Dave", stable_key="d")

    after = ctl.initial_state()["presentation"]
    assert after["transition_token"] == token
    assert after["scene_id"] == scene
    assert after["sequence_index"] == index
    assert ctl.initial_state()["locale"] == "en"

    rankings = ctl.initial_state()["rankings"]
    assert rankings["likers"][0]["value"] == 100
    assert rankings["gifters"][0]["value"] == 100
    assert rankings["sharers"][0]["value"] == 3
    assert rankings["commenters"][0]["value"] == 1


def test_controller_rotation_tick_advances_token() -> None:
    ctl = LiveLeaderboardController(pubsub=None, get_locale=lambda: "en", instance="test")
    ctl._rotation.scene_started_at_ms = 0
    ctl._rotation.sequence[0] = ctl._rotation.sequence[0].__class__(
        source_id=ctl._rotation.sequence[0].source_id,
        scene_id=ctl._rotation.sequence[0].scene_id,
        duration_sec=1.0,
    )
    before = ctl._rotation.transition_token
    advanced = ctl._rotation.tick(now_ms=2000)
    assert advanced is True
    assert ctl._rotation.transition_token == before + 1


def test_overlay_renderer_and_registry() -> None:
    overlay = LiveLeaderboardOverlayType()
    html = overlay.render_html({"instance": "main"})
    assert "<!doctype html>" in html.lower()
    assert "Live Leaderboard" in html
    assert "subscribe" in html.lower()
    assert "hall_of_fame" in html
    assert "energy_network" in html
    assert "transition_token" in html
    assert "--ll-widget-scale" in html
    assert "applyScale" in html
    # Fill available browser-source box; scale via CSS vars (not transform zoom)
    assert "inset: 0" in html
    assert "transform: scale(var(--ll-widget-scale))" not in html
    assert "hud-frame" in html
    assert "hof-champ" in html
    assert "arena-field" in html
    assert "orbit-ring" in html
    assert "vignette" in html
    assert "strip-viewport" in html
    assert "updateReadableScale" in html
    assert "syncStripScrollers" in html
    assert "--ll-read" in html
    assert "narrow-xs" in html
    assert "I18N" in html
    assert "source.likers" in html
    assert "ЖИВИЙ РЕЙТИНГ" in html or "LIVE LEADERBOARD" in html
    assert "function tr(" in html

    init_st = overlay.initial_state({"instance": "main"})
    assert "config" in init_st
    assert "rankings" in init_st
    assert "presentation" in init_st
    assert "locale" in init_st
    assert init_st["locale"] in ("uk", "en")
    assert 40 <= int(init_st["config"]["scale_percent"]) <= 250

    reg = OverlayRegistry()
    assert reg.get("live_leaderboard").type == "live_leaderboard"


def test_widgets_api_url() -> None:
    api = WidgetsQmlApi(overlay_base_url="http://127.0.0.1:17171", pubsub=None)
    assert (
        api.liveLeaderboardOverlayUrl()
        == "http://127.0.0.1:17171/overlay/live_leaderboard?instance=main"
    )
    cfg = api.loadLiveLeaderboardOverlayConfigMap()
    assert cfg["enabled"] is True
    assert isinstance(cfg["sequence"], list)
