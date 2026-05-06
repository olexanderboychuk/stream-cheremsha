from __future__ import annotations

import asyncio
import json
from unittest.mock import patch

from stream_cheremsha.overlays.actions_config import (
    actions_config_defaults,
    actions_config_to_json_text,
)
from stream_cheremsha.overlays.chat_config import chat_config_defaults, chat_config_to_json_text
from stream_cheremsha.overlays.pubsub import OverlayPubSub
from stream_cheremsha.ui.widgets_qml_api import WidgetsQmlApi


def test_load_actions_config_map_matches_python_roundtrip() -> None:
    cfg = actions_config_defaults()
    with patch("stream_cheremsha.ui.widgets_qml_api.load_actions_config", return_value=cfg):
        api = WidgetsQmlApi()
        m = api.loadActionsConfigMap()
    assert m == json.loads(actions_config_to_json_text(cfg))


def test_load_chat_config_map_matches_python_roundtrip() -> None:
    cfg = chat_config_defaults()
    with patch("stream_cheremsha.ui.widgets_qml_api.load_chat_config", return_value=cfg):
        api = WidgetsQmlApi()
        m = api.loadChatConfigMap()
    assert m == json.loads(chat_config_to_json_text(cfg))


def test_preview_actions_overlay_publishes_append_patch() -> None:
    async def _run() -> dict[str, object]:
        ps = OverlayPubSub()
        q = ps.subscribe("overlay:actions:main")
        api = WidgetsQmlApi(pubsub=ps)
        api.previewActionsOverlay()
        got = await asyncio.wait_for(q.get(), timeout=1.0)
        return got

    out = asyncio.run(_run())
    assert "append" in out
    assert out["append"]["username"] == "username"
    assert out["append"]["platform"] == "tiktok"
    assert out["append"]["preview_force_platform_icon"] is True


def test_save_actions_config_publishes_config_patch() -> None:
    async def _run() -> dict[str, object]:
        ps = OverlayPubSub()
        q = ps.subscribe("overlay:actions:main")
        base = actions_config_defaults()
        # Isolate from host QSettings: equality short-circuit must not skip publish; never touch
        # disk.
        with (
            patch("stream_cheremsha.ui.widgets_qml_api.load_actions_config", return_value=base),
            patch("stream_cheremsha.ui.widgets_qml_api.save_actions_config"),
        ):
            api = WidgetsQmlApi(pubsub=ps)
            api.saveActionsConfigJson('{"schema_version":1,"auto_hide_seconds":3}')
        got = await asyncio.wait_for(q.get(), timeout=1.0)
        return got

    out = asyncio.run(_run())
    assert "config" in out
    assert out["config"]["auto_hide_seconds"] == 3.0


def test_save_actions_config_ignores_invalid_json_and_does_not_publish() -> None:
    async def _run() -> None:
        ps = OverlayPubSub()
        q = ps.subscribe("overlay:actions:main")
        api = WidgetsQmlApi(pubsub=ps)
        api.saveActionsConfigJson("{")  # invalid JSON
        try:
            await asyncio.wait_for(q.get(), timeout=0.15)
            assert False, "expected no published patch"
        except TimeoutError:
            return

    asyncio.run(_run())
