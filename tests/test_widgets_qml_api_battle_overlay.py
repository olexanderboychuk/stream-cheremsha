"""Tests for the ``WidgetsQmlApi`` battle overlay integration.

Covers the 1v1 battle widget (type_id ``battle``):

* ``previewBattleOverlay(instance)`` publishes a representative patch to exactly
  ``overlay:battle:{instance}``,
* widget-instance settings for ``battle`` round-trip through
  ``saveWidgetInstanceSettingsJson`` / ``loadWidgetInstanceSettingsJson``
  with the type defaults merged in,
* ``widgetInstanceUrl(instance_id)`` yields ``{base}/overlay/by-id/{id}``.

Instances are persisted via ``stream_cheremsha.overlays.widget_instances``;
tests route that module's QSettings factory to an isolated
``QSettings("stream-cheremsha-test", "battle-api-test")`` scope, so the
production user settings (``stream-cheremsha`` / ``cheremsha``) are never
touched.
"""

from __future__ import annotations

import json

import pytest
from PySide6.QtCore import QSettings

from stream_cheremsha.overlays.battle_overlay_config import (
    BATTLE_THEMES,
    battle_overlay_config_defaults,
    battle_overlay_config_to_json_text,
)
from stream_cheremsha.overlays.pubsub import OverlayPubSub
from stream_cheremsha.ui.widgets_qml_api import WidgetsQmlApi


@pytest.fixture
def battle_api(monkeypatch):
    """API wired to an in-memory pubsub + isolated widget-instance store."""
    import stream_cheremsha.overlays.widget_instances as wi

    s = QSettings("stream-cheremsha-test", "battle-api-test")
    s.clear()
    monkeypatch.setattr(wi, "_settings_obj", lambda settings=None: s)

    ps = OverlayPubSub()
    api = WidgetsQmlApi(overlay_base_url="http://127.0.0.1:17171", pubsub=ps)
    return api, ps, s


def test_battle_preview_publishes_to_instance_topic(battle_api) -> None:
    api, ps, _ = battle_api
    q = ps.subscribe("overlay:battle:testinst123")

    api.previewBattleOverlay("testinst123")

    patch = q.get_nowait()
    assert patch["status"] == "active"
    assert len(patch["participants"]) == 2
    assert {p["team_id"] for p in patch["participants"]} == {"left", "right"}
    assert patch["config"]["theme"] in BATTLE_THEMES
    assert patch["best_of"] == 3


def test_widget_instance_settings_roundtrip(battle_api) -> None:
    api, ps, _ = battle_api

    instance_id = api.createWidgetInstance("battle", "Test Battle")
    assert instance_id
    q = ps.subscribe(f"overlay:battle:{instance_id}")

    saved = json.loads(battle_overlay_config_to_json_text(battle_overlay_config_defaults()))
    saved["theme"] = "cyber"
    saved["best_of"] = 5

    assert api.saveWidgetInstanceSettingsJson(instance_id, json.dumps(saved)) is True

    loaded = json.loads(api.loadWidgetInstanceSettingsJson(instance_id))
    assert loaded["theme"] == "cyber"
    assert loaded["best_of"] == 5
    assert loaded["round_duration_s"] == 60  # type defaults still merged
    assert loaded["schema_version"] == 1

    # Saving live-reloads the exact instance topic.
    patch = q.get_nowait()
    assert patch["config"]["theme"] == "cyber"

    url = api.widgetInstanceUrl(instance_id)
    assert url == f"http://127.0.0.1:17171/overlay/by-id/{instance_id}"


def test_save_widget_instance_settings_rejects_malformed_json(battle_api) -> None:
    api, _, _ = battle_api
    instance_id = api.createWidgetInstance("battle", "Test")
    assert api.saveWidgetInstanceSettingsJson(instance_id, "not json") is False
    assert api.saveWidgetInstanceSettingsJson(instance_id, "[1,2,3]") is False

    # Rejected saves must not corrupt the instance; defaults remain.
    loaded = json.loads(api.loadWidgetInstanceSettingsJson(instance_id))
    assert loaded["theme"] == "cheremsha_neon"
    assert loaded["best_of"] == 3
