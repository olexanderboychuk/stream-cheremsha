from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import patch

import pytest
from PySide6.QtQml import QQmlEngine
from PySide6.QtWidgets import QApplication

from stream_cheremsha.overlays.chat_config import (
    chat_config_defaults,
    chat_config_from_json_text,
    chat_config_to_json_text,
)
from stream_cheremsha.overlays.pubsub import OverlayPubSub
from stream_cheremsha.overlays.top_gifters_overlay_config import (
    top_gifters_overlay_config_to_json_text,
)
from stream_cheremsha.overlays.top_likers_overlay_config import top_likers_overlay_config_defaults
from stream_cheremsha.ui import widgets_qml_api as wqa
from stream_cheremsha.ui.widgets_qml_api import WidgetsQmlApi


@pytest.fixture
def qml_engine() -> QQmlEngine:
    _ = QApplication.instance() or QApplication([])
    return QQmlEngine()


def _dict_as_qjsvalue(engine: QQmlEngine, d: dict[str, Any]) -> Any:
    return engine.evaluate("JSON.parse(" + json.dumps(json.dumps(d)) + ")")


def test_qml_cfg_map_to_json_text_coerces_non_str_dict_keys() -> None:
    txt = wqa._qml_cfg_map_to_json_text({1: "x", "schema_version": 1, "font_family": "Segoe UI"})
    assert txt is not None and txt != "{}"
    assert '"1":"x"' in txt
    assert "schema_version" in txt


def test_qml_cfg_map_to_json_text_roundtrips_chat_config() -> None:
    cfg = chat_config_defaults().replace(max_items=33, font_family="Arial")
    m = {
        "schema_version": cfg.schema_version,
        "max_items": cfg.max_items,
        "font_family": cfg.font_family,
    }
    txt = wqa._qml_cfg_map_to_json_text(m)
    assert txt is not None and txt != "{}"
    parsed = chat_config_from_json_text(txt)
    assert parsed.max_items == 33
    assert parsed.font_family == "Arial"


def test_save_chat_config_map_delegates_to_save_chat_config(qml_engine: QQmlEngine) -> None:
    seen: list[object] = []

    def grab(cfg, settings=None):
        _ = settings
        seen.append(cfg)

    changed = chat_config_defaults().replace(max_items=99)
    d = json.loads(chat_config_to_json_text(changed))
    js = _dict_as_qjsvalue(qml_engine, d)
    with patch("stream_cheremsha.ui.widgets_qml_api.save_chat_config", side_effect=grab):
        api = WidgetsQmlApi()
        api.saveChatConfigMap(js)
    assert len(seen) == 1
    assert seen[0].max_items == 99


def test_save_chat_config_map_publishes_config_patch(qml_engine: QQmlEngine) -> None:
    async def _run() -> dict[str, object]:
        ps = OverlayPubSub()
        q = ps.subscribe("overlay:chat:main")
        changed = chat_config_defaults().replace(max_items=26)
        d = json.loads(chat_config_to_json_text(changed))
        js = _dict_as_qjsvalue(qml_engine, d)
        with patch("stream_cheremsha.ui.widgets_qml_api.save_chat_config"):
            api = WidgetsQmlApi(pubsub=ps)
            api.saveChatConfigMap(js)
        return await asyncio.wait_for(q.get(), timeout=1.0)

    out = asyncio.run(_run())
    assert out["config"]["max_items"] == 26


def test_save_top_gifters_overlay_config_map_delegates(qml_engine: QQmlEngine) -> None:
    seen: list[object] = []

    def grab(cfg, settings=None):
        _ = settings
        seen.append(cfg)

    base = top_likers_overlay_config_defaults().replace(top_count=9)
    d = json.loads(top_gifters_overlay_config_to_json_text(base))
    js = _dict_as_qjsvalue(qml_engine, d)
    with patch(
        "stream_cheremsha.ui.widgets_qml_api.save_top_gifters_overlay_config", side_effect=grab
    ):
        api = WidgetsQmlApi()
        api.saveTopGiftersOverlayConfigMap(js)
    assert len(seen) == 1
    assert seen[0].top_count == 9
