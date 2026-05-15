from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from stream_cheremsha.overlays.top_gifters_overlay_config import (
    TOPGIFTERS_OVERLAY_CONFIG_QSETTINGS_KEY,
    load_top_gifters_overlay_config,
    save_top_gifters_overlay_config,
)
from stream_cheremsha.overlays.top_likers_overlay_config import (
    TOPLIKERS_OVERLAY_CONFIG_QSETTINGS_KEY,
    load_top_likers_overlay_config,
    save_top_likers_overlay_config,
)


@pytest.fixture()
def isolated_settings(tmp_path: Path) -> QSettings:
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path))
    org = f"iso-org-{uuid.uuid4().hex}"
    app = f"iso-app-{uuid.uuid4().hex}"
    s = QSettings(QSettings.IniFormat, QSettings.UserScope, org, app)
    s.clear()
    s.sync()
    return s


def test_qsettings_keys_are_distinct() -> None:
    assert TOPLIKERS_OVERLAY_CONFIG_QSETTINGS_KEY != TOPGIFTERS_OVERLAY_CONFIG_QSETTINGS_KEY
    assert "top_likers" in TOPLIKERS_OVERLAY_CONFIG_QSETTINGS_KEY
    assert "top_gifters" in TOPGIFTERS_OVERLAY_CONFIG_QSETTINGS_KEY


def test_likers_and_gifters_configs_do_not_clobber_each_other(isolated_settings: QSettings) -> None:
    lik = load_top_likers_overlay_config(settings=isolated_settings).replace(top_count=3)
    gif = load_top_gifters_overlay_config(settings=isolated_settings).replace(top_count=7)
    save_top_likers_overlay_config(lik, settings=isolated_settings)
    save_top_gifters_overlay_config(gif, settings=isolated_settings)

    lik2 = load_top_likers_overlay_config(settings=isolated_settings)
    gif2 = load_top_gifters_overlay_config(settings=isolated_settings)
    assert lik2.top_count == 3
    assert gif2.top_count == 7

    raw_l = (isolated_settings.value(TOPLIKERS_OVERLAY_CONFIG_QSETTINGS_KEY, "", str) or "").strip()
    raw_g = (
        isolated_settings.value(TOPGIFTERS_OVERLAY_CONFIG_QSETTINGS_KEY, "", str) or ""
    ).strip()
    assert raw_l != raw_g
    assert '"top_count":3' in raw_l
    assert '"top_count":7' in raw_g
