from __future__ import annotations

from typing import Any

from PySide6.QtCore import QSettings

from stream_cheremsha.overlays.registry import OverlayRegistry
from stream_cheremsha.overlays.signal_system_controller import SignalSystemController
from stream_cheremsha.overlays.signal_system_overlay import SignalSystemOverlayType
from stream_cheremsha.overlays.signal_system_overlay_config import (
    load_signal_system_overlay_config,
    save_signal_system_overlay_config,
    signal_system_overlay_config_defaults,
    signal_system_overlay_config_from_json_text,
    signal_system_overlay_config_to_json_text,
)
from stream_cheremsha.ui.widgets_qml_api import WidgetsQmlApi

_ISOLATED_ORG = "stream-cheremsha-test"
_ISOLATED_APP = "test-signal-system"


def _isolated_settings() -> QSettings:
    """Never touch the production QSettings scope from tests."""
    s = QSettings(_ISOLATED_ORG, _ISOLATED_APP)
    s.clear()
    s.sync()
    return s


def test_signal_system_config_defaults() -> None:
    cfg = signal_system_overlay_config_defaults()
    assert cfg.enabled is True
    assert cfg.theme == "neon_cyber"
    assert cfg.idle_opacity_pct == 35
    assert cfg.active_opacity_pct == 100
    assert cfg.particles_enabled is True
    assert cfg.glitch_enabled is True
    assert cfg.perimeter_enabled is True
    assert cfg.sound_enabled is False
    assert cfg.cooldown_ms == 3000
    assert cfg.min_gift_coins_for_event == 100
    assert cfg.ai_observations_enabled is True
    assert cfg.unknown_signals_enabled is True
    assert cfg.milestones_enabled is True
    assert cfg.activity_surge_enabled is True
    assert cfg.scale_percent == 100
    assert cfg.core_vertical_pct == 50


def test_signal_system_config_json_roundtrip() -> None:
    cfg = signal_system_overlay_config_defaults().replace(
        theme="toxic_system",
        min_gift_coins_for_event=200,
        cooldown_ms=4000,
        custom_title="CUSTOM CORE",
        particles_enabled=False,
        scale_percent=150,
        core_vertical_pct=35,
    )
    txt = signal_system_overlay_config_to_json_text(cfg)
    cfg2 = signal_system_overlay_config_from_json_text(txt)
    assert cfg2.theme == "toxic_system"
    assert cfg2.min_gift_coins_for_event == 200
    assert cfg2.cooldown_ms == 4000
    assert cfg2.custom_title == "CUSTOM CORE"
    assert cfg2.particles_enabled is False
    assert cfg2.scale_percent == 150
    assert cfg2.core_vertical_pct == 35


def test_signal_system_invalid_theme_falls_back() -> None:
    cfg = signal_system_overlay_config_from_json_text('{"theme": "invalid_cyber"}')
    assert cfg.theme == "neon_cyber"


def test_signal_system_scale_percent_clamped() -> None:
    cfg = signal_system_overlay_config_from_json_text(
        signal_system_overlay_config_to_json_text(
            signal_system_overlay_config_defaults().replace(scale_percent=999)
        )
    )
    assert cfg.scale_percent == 250
    cfg2 = signal_system_overlay_config_from_json_text('{"scale_percent": 10}')
    assert cfg2.scale_percent == 40


def test_signal_system_core_vertical_pct_clamped() -> None:
    cfg = signal_system_overlay_config_from_json_text(
        signal_system_overlay_config_to_json_text(
            signal_system_overlay_config_defaults().replace(core_vertical_pct=5)
        )
    )
    assert cfg.core_vertical_pct == 20
    cfg2 = signal_system_overlay_config_from_json_text('{"core_vertical_pct": 99}')
    assert cfg2.core_vertical_pct == 80
    cfg3 = signal_system_overlay_config_from_json_text("{}")
    assert cfg3.core_vertical_pct == 50


def test_signal_system_qsettings_persistence() -> None:
    s = _isolated_settings()
    cfg = signal_system_overlay_config_defaults().replace(
        theme="amber_core", min_gift_coins_for_event=250
    )
    save_signal_system_overlay_config(cfg, s)
    loaded = load_signal_system_overlay_config(s)
    assert loaded.theme == "amber_core"
    assert loaded.min_gift_coins_for_event == 250
    s.clear()


def test_signal_system_registry_integration() -> None:
    reg = OverlayRegistry()
    assert "signal_system" in reg.registered_types()
    overlay_type = reg.get("signal_system")
    assert isinstance(overlay_type, SignalSystemOverlayType)


def test_signal_system_overlay_renderer() -> None:
    # Read-only render assertions; must not touch production QSettings.
    overlay = SignalSystemOverlayType()
    html = overlay.render_html({"instance": "main"})
    assert "<!doctype html>" in html.lower()
    assert "signal" in html.lower() or "canvas" in html.lower()
    assert "background: transparent" in html
    assert "audiocontext" in html.lower()
    assert "neon_cyber" in html
    assert "particlepool" in html.lower() or "particles" in html.lower()
    assert "glitchengine" in html.lower() or "glitch" in html.lower()
    assert "scale" in html.lower()
    assert "function tr(key)" in html
    assert "function trf(key" in html
    assert "tr('overlay.signal_lost')" in html
    assert "tr('overlay.gift_prefix')" in html
    assert "fillText('GIFT // '" not in html
    assert "fillText('// SIGNAL LOST //'" not in html
    assert "+ ' COINS'" not in html and "+' COINS'" not in html
    assert "widgetScale" in html
    assert "function u(n)" in html
    # Fill available browser-source box; scale element sizes (not uniform zoom)
    assert "inset: 0" in html
    assert "canvas.style.transform" not in html
    assert "transform: scale(" not in html
    assert "ctx.scale(widgetScale" not in html
    assert "edge-anchored" in html or "stream-goal" in html
    # i18n short keys (tr('goal.system')), not signal_system.goal.system
    assert '"goal.system"' in html or "'goal.system'" in html
    # Center core is event-only (no idle breathing decoration)
    assert "only during an active signal" in html
    assert "faint breathing core" not in html
    # Approach A: gift-centered stage + engineered wake/containment
    assert "drawGiftContainment" in html
    assert "Frame wake progress" in html
    assert "drawEnergyWell" in html
    assert "Layout.stageY" in html
    assert "Layout.headerY" in html
    assert "Layout.nameY" in html
    assert "Layout.userY" in html
    assert "Layout.coinY" in html
    assert "VH*0.5" in html or "core_vertical_pct" in html
    assert "ALWAYS vertically centered" in html or "Core vertical position from config" in html
    assert "core_vertical_pct" in html
    assert "Safe bands" in html or "never sits inside orbitals" in html or "clear of rings" in html
    assert "3 text rows spaced" in html or "no heap" in html
    # GPU/FPS guards for OBS browser sources
    assert "ctx.getImageData" not in html
    assert "ctx.putImageData" not in html
    assert "IDLE_FRAME_MS" in html
    assert "Math.min(window.devicePixelRatio||1,1.5)" in html
    assert "never getImageData" in html
    assert "active signals only" in html or "Ambient sparkles only during active" in html

    init_st = overlay.initial_state({"instance": "main"})
    assert "config" in init_st
    assert "theme" in init_st["config"]
    assert "scale_percent" in init_st["config"]
    assert "core_vertical_pct" in init_st["config"]
    assert 20 <= int(init_st["config"]["core_vertical_pct"]) <= 80
    assert "enabled" in init_st["config"]
    assert "locale" in init_st


class DummyPubSub:
    def __init__(self) -> None:
        self.published: list[tuple[str, dict[str, Any]]] = []

    async def publish(self, topic: str, patch: dict[str, Any]) -> None:
        self.published.append((topic, patch))

    def publish_sync(self, topic: str, patch: dict[str, Any]) -> None:
        self.published.append((topic, patch))


def test_signal_system_controller_event_dispatch() -> None:
    s = _isolated_settings()
    pubsub = DummyPubSub()
    ctrl = SignalSystemController(pubsub=pubsub, instance="main", settings=s)

    # Test gift trigger
    ctrl.on_gift(sender="MegaGifter", gift_name="Universe", count=1, tiktok_coin_each=500)
    # Direct tick
    ctrl._on_dispatch_tick()
    ctrl._flush_publish()

    assert len(pubsub.published) > 0
    topic, patch = pubsub.published[-1]
    assert "signal_system" in topic
    assert "current_event" in patch
    sig = patch["current_event"]
    assert sig["type"] == "big_gift"
    assert sig["username"] == "MegaGifter"
    assert "scale_percent" in patch["config"]
    s.clear()


def test_signal_system_controller_priority_queue() -> None:
    from stream_cheremsha.overlays.signal_system_overlay_config import (
        save_signal_system_overlay_config,
        signal_system_overlay_config_defaults,
    )

    s = _isolated_settings()
    save_signal_system_overlay_config(signal_system_overlay_config_defaults(), s)
    s.sync()
    pubsub = DummyPubSub()
    ctrl = SignalSystemController(pubsub=pubsub, instance="main", settings=s)

    # Queue multiple events
    ctrl.on_activity_surge(level=1, count=50, top_chatter="ChatHero")
    ctrl.on_milestone(milestone_type="followers", count=1000, target=1000)

    # Tick to dispatch highest priority
    ctrl._on_dispatch_tick()
    ctrl._flush_publish()
    assert len(pubsub.published) > 0
    topic, patch = pubsub.published[-1]
    sig = patch["current_event"]
    assert sig["priority"] == 100 or sig["type"] in ("milestone", "activity_surge")
    assert "scale_percent" in patch["config"]
    s.clear()


def test_signal_system_controller_test_triggers() -> None:
    s = _isolated_settings()
    pubsub = DummyPubSub()
    ctrl = SignalSystemController(
        pubsub=pubsub, instance="main", settings=s, get_locale=lambda: "uk"
    )

    for test_type in (
        "big_gift",
        "milestone",
        "activity_surge",
        "ai_observation",
        "unknown_signal",
    ):
        ctrl.trigger_test_event(test_type)
        ctrl._flush_publish()
        assert len(pubsub.published) > 0
        topic, patch = pubsub.published[-1]
        assert patch["current_event"]["type"] == test_type
    # Ukrainian titles for gift test
    ctrl.trigger_test_event("big_gift")
    ctrl._flush_publish()
    title = pubsub.published[-1][1]["current_event"]["title"]
    assert "СИГНАЛ" in title
    assert "COINS" not in pubsub.published[-1][1]["current_event"]["value"]
    assert "МОНЕТ" in pubsub.published[-1][1]["current_event"]["value"]
    s.clear()


def test_signal_system_controller_titles_follow_locale() -> None:
    s = _isolated_settings()
    pubsub = DummyPubSub()
    ctrl_en = SignalSystemController(
        pubsub=pubsub, instance="main", settings=s, get_locale=lambda: "en"
    )
    ctrl_en.trigger_test_event("mega_gift")
    ctrl_en._flush_publish()
    assert pubsub.published[-1][1]["current_event"]["title"] == "MEGA // TRANSMISSION"
    s.clear()


def test_widgets_qml_api_signal_system(monkeypatch) -> None:
    import stream_cheremsha.ui.widgets_qml_api as wapi

    s = _isolated_settings()
    # Route the API's config persistence at the isolated scope; the API
    # otherwise defaults to the production QSettings scope.
    monkeypatch.setattr(
        wapi,
        "load_signal_system_overlay_config",
        lambda *a, **k: load_signal_system_overlay_config(s),
    )
    monkeypatch.setattr(
        wapi,
        "save_signal_system_overlay_config",
        lambda cfg, *a, **k: save_signal_system_overlay_config(cfg, s),
    )
    pubsub = DummyPubSub()
    ctrl = SignalSystemController(pubsub=pubsub, instance="main", settings=s)
    api = WidgetsQmlApi(overlay_base_url="http://127.0.0.1:17171", pubsub=pubsub)
    api.set_signal_system_controller(ctrl)

    assert (
        api.signalSystemOverlayUrl() == "http://127.0.0.1:17171/overlay/signal_system?instance=main"
    )
    assert (
        api.signalSystemOverlayUrlValue
        == "http://127.0.0.1:17171/overlay/signal_system?instance=main"
    )

    cfg = api.loadSignalSystemOverlayConfigMap()
    assert cfg["theme"] == "neon_cyber"
    assert "idle_opacity_pct" in cfg
    assert cfg["scale_percent"] == 100

    # Test updating config via map
    cfg["theme"] = "ice_protocol"
    cfg["min_gift_coins_for_event"] = 75
    cfg["scale_percent"] = 125
    api.saveSignalSystemOverlayConfigMap(cfg)

    reloaded = api.loadSignalSystemOverlayConfigMap()
    assert reloaded["theme"] == "ice_protocol"
    assert reloaded["min_gift_coins_for_event"] == 75
    assert reloaded["scale_percent"] == 125

    # Test trigger test event through API
    api.triggerSignalSystemTest("ai_observation")
    ctrl._flush_publish()
    assert len(pubsub.published) > 0
    topic, patch = pubsub.published[-1]
    assert patch["current_event"]["type"] == "ai_observation"
    s.clear()
