from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from stream_cheremsha.overlays.chat_config import (
    chat_config_defaults,
    load_chat_config,
    save_chat_config,
)


@pytest.fixture()
def ini_settings(tmp_path: Path) -> QSettings:
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path))
    org = f"test-org-{uuid.uuid4()}"
    app = f"test-app-{uuid.uuid4()}"
    s = QSettings(QSettings.IniFormat, QSettings.UserScope, org, app)
    s.clear()
    s.sync()
    return s


def test_load_uses_backup_when_primary_is_invalid(ini_settings: QSettings) -> None:
    cfg = chat_config_defaults()
    save_chat_config(cfg, settings=ini_settings)
    ini_settings.setValue("overlays/chat/main/config_json", "{")
    ini_settings.sync()
    out = load_chat_config(settings=ini_settings)
    assert out.schema_version == cfg.schema_version
