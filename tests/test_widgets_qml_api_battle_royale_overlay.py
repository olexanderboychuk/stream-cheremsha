import json

from PySide6.QtCore import QSettings

from stream_cheremsha.overlays.battle_royale_overlay_config import (
    BATTLE_ROYALE_OVERLAY_CONFIG_QSETTINGS_KEY,
    load_battle_royale_overlay_config,
)
from stream_cheremsha.overlays.pubsub import OverlayPubSub
from stream_cheremsha.ui.widgets_qml_api import WidgetsQmlApi


def test_battle_royale_overlay_url() -> None:
    api = WidgetsQmlApi(overlay_base_url="http://127.0.0.1:17171", pubsub=OverlayPubSub())
    assert (
        api.battleRoyaleOverlayUrl() == "http://127.0.0.1:17171/overlay/battle_royale?instance=main"
    )


def test_save_battle_royale_overlay_config_json_persists(tmp_path) -> None:
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path))
    api = WidgetsQmlApi(overlay_base_url="http://127.0.0.1:17171", pubsub=OverlayPubSub())
    partial = {
        "schema_version": 1,
        "max_hp": 800,
        "auto_threshold_each": 1,
        "auto_arm_enabled": True,
    }
    api.saveBattleRoyaleOverlayConfigJson(json.dumps(partial))
    s = QSettings("stream-cheremsha", "cheremsha")
    raw = (s.value(BATTLE_ROYALE_OVERLAY_CONFIG_QSETTINGS_KEY, "", str) or "").strip()
    assert raw
    cfg = load_battle_royale_overlay_config(s)
    assert cfg.max_hp == 800
    assert cfg.auto_threshold_each == 1
