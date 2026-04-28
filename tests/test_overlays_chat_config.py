import json

import pytest

from stream_cheremsha.overlays.chat_config import (
    CHAT_CONFIG_SCHEMA_VERSION,
    ChatOverlayConfig,
    chat_config_defaults,
    chat_config_from_json_text,
    chat_config_to_json_text,
)


def test_chat_config_defaults_are_valid() -> None:
    cfg = chat_config_defaults()
    assert isinstance(cfg, ChatOverlayConfig)
    assert cfg.schema_version == CHAT_CONFIG_SCHEMA_VERSION
    assert cfg.max_items >= 1
    assert cfg.font_size_px >= 8
    assert cfg.show_platform in (True, False)


def test_chat_config_json_roundtrip() -> None:
    cfg = chat_config_defaults().replace(max_items=7, show_platform=False)
    txt = chat_config_to_json_text(cfg)
    obj = json.loads(txt)
    assert obj["schema_version"] == CHAT_CONFIG_SCHEMA_VERSION
    out = chat_config_from_json_text(txt)
    assert out.max_items == 7
    assert out.show_platform is False


def test_chat_config_rejects_bad_schema_version() -> None:
    with pytest.raises(ValueError):
        chat_config_from_json_text('{"schema_version":999,"max_items":1}')
