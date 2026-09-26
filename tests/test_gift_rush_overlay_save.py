"""Tests for the ``gift_rush`` overlay config save → preview publish.

Mirrors the singleton save path of ``stream_goal`` / ``stream_pet`` /
``community_world``: saving the config must publish a live patch to the
preview topic so the ``Scale`` option updates the running preview widget.
The per-instance path is covered by ``_save_cfg_to_instance`` (instance
topic) and is verified separately.
"""
from __future__ import annotations

import json

import pytest
from PySide6.QtCore import QSettings

from stream_cheremsha.overlays.pubsub import OverlayPubSub
from stream_cheremsha.ui.widgets_qml_api import WidgetsQmlApi


@pytest.fixture
def gift_rush_api(monkeypatch):
    """API wired to an in-memory pubsub + isolated settings store."""
    import stream_cheremsha.overlays.gift_rush_config as grc
    import stream_cheremsha.overlays.widget_instances as wi

    s = QSettings("stream-cheremsha-test", "gift-rush-api-test")
    s.clear()
    monkeypatch.setattr(wi, "_settings_obj", lambda settings=None: s)
    monkeypatch.setattr(grc, "_settings_obj", lambda settings=None: s)

    ps = OverlayPubSub()
    api = WidgetsQmlApi(overlay_base_url="http://127.0.0.1:17171", pubsub=ps)
    return api, ps


def test_gift_rush_save_publishes_preview_patch_with_scale(gift_rush_api) -> None:
    """Saving the config must publish a patch to the singleton preview topic
    whose config carries the edited ``scale_percent`` (and other fields)."""
    api, ps = gift_rush_api
    q = ps.subscribe("overlay:gift_rush:main")

    api.saveGiftRushOverlayConfigJson(json.dumps({"scale_percent": 220, "theme": "celebration"}))

    patch = q.get_nowait()
    assert patch["config"]["scale_percent"] == 220
    assert patch["config"]["theme"] == "celebration"
    # Defaults still present in the public dict.
    assert "intensity_percent" in patch["config"]
    assert "event_animations" in patch["config"]


def test_gift_rush_save_scale_clamped_in_patch(gift_rush_api) -> None:
    """The published scale must be clamped to [40, 250] like every other type."""
    api, ps = gift_rush_api

    q_hi = ps.subscribe("overlay:gift_rush:main")
    api.saveGiftRushOverlayConfigJson(json.dumps({"scale_percent": 999}))
    assert q_hi.get_nowait()["config"]["scale_percent"] == 250

    q_lo = ps.subscribe("overlay:gift_rush:main")
    api.saveGiftRushOverlayConfigJson(json.dumps({"scale_percent": 10}))
    assert q_lo.get_nowait()["config"]["scale_percent"] == 40


def test_gift_rush_save_malformed_falls_back_to_defaults(gift_rush_api) -> None:
    """Malformed config falls back to defaults (lenient parser, per the
    ``gift_rush_overlay_config`` contract) and still publishes a patch with
    the default scale — same lenient-parse behaviour as every other save."""
    api, ps = gift_rush_api
    q = ps.subscribe("overlay:gift_rush:main")
    api.saveGiftRushOverlayConfigJson("not valid json {")
    patch = q.get_nowait()
    assert patch["config"]["scale_percent"] == 100
    assert patch["config"]["theme"] == "cheremsha"


def test_gift_rush_save_empty_payload_publishes_nothing(gift_rush_api) -> None:
    api, ps = gift_rush_api
    q = ps.subscribe("overlay:gift_rush:main")
    api.saveGiftRushOverlayConfigJson("")
    api.saveGiftRushOverlayConfigJson("   ")
    assert q.empty()


def test_gift_rush_save_when_pubsub_none_does_not_crash(gift_rush_api) -> None:
    """A None pubsub must be tolerated (matches the rest of the API)."""
    api, _ = gift_rush_api
    # Re-bind the api's pubsub to None after the fixture (fixture is a fresh
    # object, so this is safe).
    api._pubsub = None
    api.saveGiftRushOverlayConfigJson(json.dumps({"scale_percent": 150}))
    # No crash; nothing to assert on the (non-existent) topic.
