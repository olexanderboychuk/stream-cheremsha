"""Modern toggle-switch control (Cheremsha visual language) for QWidget pages.

Drop-in replacement for a two-state QCheckBox where the design calls for a
pill toggle instead of a square checkbox. Same programmatic contract:

- ``setChecked(bool)`` / ``isChecked()`` / ``checkState()``
- ``toggled(bool)`` (inherited from QAbstractButton)
- ``stateChanged(int)`` with Qt.CheckState values (like QCheckBox)

The knob slides with a very short (~90 ms) one-shot animation on user
toggles. Programmatic changes (e.g. settings load with blocked signals)
snap instantly. No timers, no polling, nothing runs continuously.
"""

from __future__ import annotations

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QSize, Qt, Signal, Slot
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QAbstractButton, QSizePolicy, QWidget

_SWITCH_WIDTH = 38
_SWITCH_HEIGHT = 21
_SLIDE_MS = 90

_TRACK_OFF = QColor("#1a2130")
_TRACK_OFF_BORDER = QColor("#2a3142")
_TRACK_OFF_BORDER_HOVER = QColor("#3b475e")
_KNOB_OFF = QColor("#5c677a")
_TRACK_ON = QColor("#0d9488")
_TRACK_ON_BORDER = QColor("#2dd4bf")
_KNOB_ON = QColor("#ffffff")
_TRACK_DISABLED = QColor("#232b3d")
_TRACK_DISABLED_BORDER = QColor("#4a5568")
_KNOB_DISABLED = QColor("#5c677a")
_FOCUS_RING = QColor("#2dd4bf")


class CheremshaSwitch(QAbstractButton):
    """Pill-style on/off toggle with the QCheckBox two-state contract."""

    stateChanged = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._slide = 0.0
        self._anim = QPropertyAnimation(self, b"slide", self)
        self._anim.setDuration(_SLIDE_MS)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._emit_state_changed)

    def sizeHint(self) -> QSize:
        return QSize(_SWITCH_WIDTH, _SWITCH_HEIGHT)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def _get_slide(self) -> float:
        return self._slide

    def _set_slide(self, value: float) -> None:
        self._slide = max(0.0, min(1.0, float(value)))
        self.update()

    slide = Property(float, _get_slide, _set_slide)

    @Slot(bool)
    def _emit_state_changed(self, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        self.stateChanged.emit(state.value)
        self._anim.stop()
        self._anim.setStartValue(self._slide)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def _knob_x(self, checked: bool, x0: int, track_w: int, knob_d: int) -> float:
        off_x = x0 + 3
        on_x = x0 + track_w - knob_d - 3
        if self._anim.state() != QPropertyAnimation.State.Running:
            self._slide = 1.0 if checked else 0.0
        return off_x + (on_x - off_x) * self._slide

    def paintEvent(self, _event: object) -> None:  # noqa: ANN001
        w = self.width()
        h = self.height()
        track_h = min(_SWITCH_HEIGHT, h)
        track_w = min(_SWITCH_WIDTH, w)
        y0 = (h - track_h) // 2
        x0 = (w - track_w) // 2
        radius = track_h / 2.0
        checked = self.isChecked()
        enabled = self.isEnabled()

        if not enabled:
            track, border, knob_color = _TRACK_DISABLED, _TRACK_DISABLED_BORDER, _KNOB_DISABLED
        elif checked:
            track, border, knob_color = _TRACK_ON, _TRACK_ON_BORDER, _KNOB_ON
        else:
            hover_border = _TRACK_OFF_BORDER_HOVER if self.underMouse() else _TRACK_OFF_BORDER
            track, border, knob_color = _TRACK_OFF, hover_border, _KNOB_OFF

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        if self.hasFocus():
            p.setPen(_FOCUS_RING)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(x0 - 2, y0 - 2, track_w + 4, track_h + 4, radius + 2, radius + 2)

        p.setPen(border)
        p.setBrush(track)
        p.drawRoundedRect(x0, y0, track_w, track_h, radius, radius)

        knob_d = track_h - 6
        knob_y = y0 + 3
        knob_x = self._knob_x(checked, x0, track_w, knob_d)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(knob_color)
        p.drawEllipse(int(knob_x), int(knob_y), int(knob_d), int(knob_d))
        p.end()
