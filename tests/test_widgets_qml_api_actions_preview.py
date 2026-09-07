from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
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


def test_save_chat_config_json_publishes_config_patch() -> None:
    async def _run() -> dict[str, object]:
        ps = OverlayPubSub()
        q = ps.subscribe("overlay:chat:main")
        changed = chat_config_defaults().replace(max_items=25)
        with patch("stream_cheremsha.ui.widgets_qml_api.save_chat_config"):
            api = WidgetsQmlApi(pubsub=ps)
            api.saveChatConfigJson(chat_config_to_json_text(changed))
        got = await asyncio.wait_for(q.get(), timeout=1.0)
        return got

    out = asyncio.run(_run())
    assert "config" in out
    assert out["config"]["max_items"] == 25


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


def test_widget_preview_opens_instance_url_externally() -> None:
    api = WidgetsQmlApi()

    with (
        patch("stream_cheremsha.ui.widgets_qml_api.QDesktopServices.openUrl") as open_url,
        patch.object(api, "previewWidgetInstance") as preview,
    ):
        api.set_overlay_base_url("http://127.0.0.1:17171")
        api.openWidgetInstanceUrl("instance-1")

    open_url.assert_called_once()
    assert open_url.call_args.args[0].toString() == (
        "http://127.0.0.1:17171/overlay/by-id/instance-1"
    )
    preview.assert_called_once_with("instance-1")


def test_widget_preview_updates_only_the_explicitly_opened_instance() -> None:
    api = WidgetsQmlApi()
    with patch.object(api, "previewWidgetInstance") as preview:
        api._preview_instance_id = "instance-1"  # noqa: SLF001
        api.updateWidgetPreview("other-instance")
        api.updateWidgetPreview("instance-1")

    preview.assert_called_once_with("instance-1")


def test_preview_config_reads_authoritative_instance_settings() -> None:
    instance = SimpleNamespace(id="instance-1")
    current = {"title": "new value", "color": "#14b8a6"}

    with (
        patch(
            "stream_cheremsha.overlays.widget_instances.find_by_ws_token",
            return_value=instance,
        ),
        patch(
            "stream_cheremsha.overlays.widget_instances.merged_settings",
            return_value=current,
        ),
    ):
        result = WidgetsQmlApi._preview_config(  # noqa: SLF001
            "test_widget",
            "instance-1",
            lambda: {"title": "old value"},
            json.loads,
        )

    assert result == current
