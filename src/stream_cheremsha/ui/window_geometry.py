"""Persistent window size/position via QSettings (Qt saveGeometry/restoreGeometry)."""

from __future__ import annotations

from PySide6.QtCore import QByteArray, QSettings
from PySide6.QtWidgets import QWidget

_QSETTINGS_ORG = "stream-cheremsha"
_QSETTINGS_APP = "cheremsha"

KEY_MAIN_WINDOW = "ui/main_window_geometry"
KEY_CHAT_POPOUT = "ui/chat_popout_geometry"
KEY_PIPER_HELP_DIALOG = "ui/piper_help_dialog_geometry"


def _as_qbytearray(v: object) -> QByteArray | None:
    if v is None:
        return None
    if isinstance(v, QByteArray):
        return v
    if isinstance(v, (bytes, bytearray, memoryview)):
        return QByteArray(bytes(v))
    return None


def restore_window_geometry(key: str, widget: QWidget) -> bool:
    s = QSettings(_QSETTINGS_ORG, _QSETTINGS_APP)
    ba = _as_qbytearray(s.value(key))
    if not ba or ba.isEmpty():
        return False
    return widget.restoreGeometry(ba)


def save_window_geometry(key: str, widget: QWidget) -> None:
    QSettings(_QSETTINGS_ORG, _QSETTINGS_APP).setValue(key, widget.saveGeometry())
