"""QML smoke: ComboBox must show displayText with object model + textRole (ConnComboBox contract)."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtWidgets import QApplication


@pytest.fixture()
def qapplication() -> QApplication:
    app = QApplication.instance()
    if app is None:
        return QApplication([])
    return app


@pytest.mark.usefixtures("qapplication")
def test_conn_combobox_smoke_shows_display_text(qapplication: QApplication) -> None:
    engine = QQmlEngine()
    qml_path = Path(__file__).resolve().parent / "qml" / "conn_combobox_smoke.qml"
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml_path)))
    assert component.isReady(), [str(e) for e in component.errors()]

    root = component.create()
    assert root is not None

    assert root.property("probeModelCount") == 2
    assert root.property("probeCurrentIndex") == 0
    assert root.property("probeDisplayText") == "Kick"

    combo = root.findChild(type(root), "probeCombo")
    assert combo is not None
    assert combo.property("displayText") == "Kick"
    assert combo.property("count") == 2
