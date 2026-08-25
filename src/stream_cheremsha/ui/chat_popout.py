"""Detached chat: frameless (no DWM title bar), background-only rgba opacity, solid message pane."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, QPointF, QRect, QSettings, Qt, Slot
from PySide6.QtGui import QCloseEvent, QFont, QMouseEvent, QTextCursor
from PySide6.QtWidgets import (
    QDialog,
    QFontComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from stream_cheremsha.ui.main_window import MainWindow

from stream_cheremsha.domain.models import ChatMessage
from stream_cheremsha.ui.chat_formatting import (
    CHAT_DEFAULT_FONT_FAMILY,
    chat_font_stack_css,
    format_chat_message_html,
)
from stream_cheremsha.ui.window_geometry import (
    KEY_CHAT_POPOUT,
    restore_window_geometry,
    save_window_geometry,
)

_SETTINGS_POPOUT_OPACITY = "ui/chat_popout_opacity"
_SETTINGS_POPOUT_CONTROLS = "ui/chat_popout_controls_visible"
_SETTINGS_POPOUT_FONT_PT = "ui/chat_popout_font_pt"
_SETTINGS_POPOUT_FONT_FAMILY = "ui/chat_popout_font_family"
_MAX_CHAT_DOCUMENT_BLOCKS = 450


def _read_bool_settings(value: object, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in ("1", "true", "yes", "on"):
        return True
    if s in ("0", "false", "no", "off", ""):
        return False
    return default


def _build_popout_stylesheet(bg_opacity: float) -> str:
    """QDialog is transparent; title bar, toolbars, and chat body use the same alpha curve."""
    o = max(0.0, min(1.0, bg_opacity))
    a = int(round(o * 255))
    a_bar = int(round(max(0.15, o) * 255))
    return (
        f"QDialog#chatPopout {{ background-color: transparent; border: none; }}"
        f"QFrame#chatPopoutTitleBar {{ background-color: rgba(10, 12, 18, {a_bar}); "
        f"border-bottom: 1px solid #1e2430; min-height: 32px; }}"
        f"QWidget#chatPopoutBar {{ background-color: rgba(10, 11, 14, {a_bar}); "
        f"border: none; border-bottom: 1px solid #1e2430; }}"
        f"QWidget#chatToolbar {{ background-color: rgba(10, 11, 14, {a_bar}); border: none; "
        f"border-bottom: 1px solid #1e2430; padding: 6px 10px; }}"
        f"QLabel {{ color: #b8c0ce; }}"
        f"QTextEdit#chatMessageView {{ background-color: rgba(7, 9, 16, {a}); color: #e2e8f0; "
        f"border: none; border-radius: 0; padding: 6px 8px; "
        f"selection-background-color: #1e3a5f; selection-color: #f8fafc; }}"
        f"QLineEdit, QComboBox, QFontComboBox, QSpinBox {{ background: rgb(16, 20, 28); "
        f"color: #e6e6e6; border: 1px solid #2a3142; border-radius: 8px; padding: 4px; }}"
        f"QPushButton {{ background-color: #1a2130; color: #e6e6e6; "
        f"border: 1px solid #2f3a4d; border-radius: 8px; padding: 6px 12px; }}"
        f"QPushButton#chatPopoutCloseBtn, QPushButton#chatPopoutPanelBtn {{ "
        f"background: transparent; "
        f"border: 1px solid #3d4a5c; max-width: 40px; min-width: 36px; padding: 2px; }}"
        f"QPushButton#chatPopoutCloseBtn:hover, QPushButton#chatPopoutPanelBtn:hover {{ "
        f"background: #1e2535; border-color: #5c6a7d; }}"
        f"QPushButton:hover {{ background-color: #202a3a; border-color: #3b4458; }}"
        f"QSlider::groove:horizontal {{ height: 6px; background: #1e2430; border-radius: 3px; }}"
        f"QSlider::handle:horizontal {{ width: 16px; margin: -5px 0; background: #3d4a60; "
        f"border-radius: 7px; }}"
    )


# NCHitTest / edge widgets: keep in sync
_RESIZE_MARGIN = 8


def _resize_rect_by_delta(
    r0: QRect,
    d: QPoint,
    edges: Qt.Edge,
    min_w: int,
    min_h: int,
) -> QRect:
    L, R, T, B = (
        Qt.Edge.LeftEdge,
        Qt.Edge.RightEdge,
        Qt.Edge.TopEdge,
        Qt.Edge.BottomEdge,
    )
    e: Qt.Edge = edges
    r = QRect(r0)
    if e & L:
        r.setLeft(r0.left() + d.x())
    if e & R:
        r.setRight(r0.right() + d.x())
    if e & T:
        r.setTop(r0.top() + d.y())
    if e & B:
        r.setBottom(r0.bottom() + d.y())
    if r.width() < min_w:
        if e & L:
            r.setLeft(r.right() - min_w)
        else:
            r.setX(r0.x())
            r.setWidth(min_w)
    if r.height() < min_h:
        if e & T:
            r.setTop(r.bottom() - min_h)
        else:
            r.setY(r0.y())
            r.setHeight(min_h)
    return r


def _set_window_geometry_from_global(
    w: QWidget,
    global_rect: QRect,
) -> None:
    wh = w.windowHandle()
    if wh is not None:
        wh.setGeometry(global_rect)
        return
    p = w.parentWidget()
    if p is not None:
        tl = p.mapFromGlobal(global_rect.topLeft())
        w.setGeometry(tl.x(), tl.y(), global_rect.width(), global_rect.height())
    else:
        w.setGeometry(global_rect)


def _edge_resize_cursor(e: Qt.Edge) -> Qt.CursorShape | None:
    L, R, T, B = (
        Qt.Edge.LeftEdge,
        Qt.Edge.RightEdge,
        Qt.Edge.TopEdge,
        Qt.Edge.BottomEdge,
    )
    if e == (L | T):
        return Qt.CursorShape.SizeFDiagCursor
    if e == (R | T):
        return Qt.CursorShape.SizeBDiagCursor
    if e == (L | B):
        return Qt.CursorShape.SizeBDiagCursor
    if e == (R | B):
        return Qt.CursorShape.SizeFDiagCursor
    if e in (L, R):
        return Qt.CursorShape.SizeHorCursor
    if e in (T, B):
        return Qt.CursorShape.SizeVerCursor
    return None


class _EdgeResizeHandle(QFrame):
    def __init__(self, popout: ChatPopoutWindow, edges: Qt.Edge) -> None:
        super().__init__(popout)
        self._host = popout
        self._edges = edges
        self._manual = False
        self._press_global: QPointF | None = None
        self._ref_global: QRect | None = None
        L, R, T, B = (
            Qt.Edge.LeftEdge,
            Qt.Edge.RightEdge,
            Qt.Edge.TopEdge,
            Qt.Edge.BottomEdge,
        )
        e = self._edges
        self.setMouseTracking(True)
        # Fully transparent can fail hit-testing on Windows layered windows; keep tiny alpha.
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet("background: rgba(12, 14, 20, 12);")
        if e in (L | T, R | T, L | B, R | B):
            self.setFixedSize(_RESIZE_MARGIN, _RESIZE_MARGIN)
        elif e in (L, R):
            self.setFixedWidth(_RESIZE_MARGIN)
            self.setSizePolicy(
                QSizePolicy.Policy.Fixed,
                QSizePolicy.Policy.Expanding,
            )
        elif e in (T, B):
            self.setFixedHeight(_RESIZE_MARGIN)
            self.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )
        c = _edge_resize_cursor(self._edges)
        if c is not None:
            self.setCursor(c)

    def mousePressEvent(self, e: QMouseEvent) -> None:
        if e.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(e)
            return
        # QWindow::startSystemResize is unreliable for FramelessWindowHint (often false
        # or no-op on Windows); use manual geometry in screen space instead.
        self._manual = True
        self._press_global = e.globalPosition()
        g = self._host.mapToGlobal(QPoint(0, 0))
        self._ref_global = QRect(g, self._host.size())
        self.grabMouse()
        e.accept()

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        if (
            self._manual
            and (e.buttons() & Qt.MouseButton.LeftButton)
            and self._ref_global is not None
        ):
            if self._press_global is None:
                return
            d = (e.globalPosition() - self._press_global).toPoint()
            h = self._host
            new_g = _resize_rect_by_delta(
                self._ref_global,
                d,
                self._edges,
                h.minimumWidth(),
                h.minimumHeight(),
            )
            _set_window_geometry_from_global(h, new_g)
            e.accept()
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        if e.button() == Qt.MouseButton.LeftButton and self._manual:
            self._manual = False
            self._press_global = None
            self._ref_global = None
            self.releaseMouse()
            e.accept()
        super().mouseReleaseEvent(e)


class _PopoutTitleBar(QFrame):
    def __init__(self, popout: ChatPopoutWindow, *, controls_visible: bool) -> None:
        super().__init__(popout)
        self.setObjectName("chatPopoutTitleBar")
        self._win = popout
        self._drag_offset: QPoint | None = None
        h = QHBoxLayout(self)
        h.setContentsMargins(12, 6, 10, 6)
        self._title = QLabel()
        self._title.setObjectName("chatPopoutTitleLabel")
        self._title.setStyleSheet("color: #e8eaed; font-size: 13px; font-weight: 600;")
        h.addWidget(self._title, stretch=1)
        self._btn_controls = QPushButton("☰")
        self._btn_controls.setObjectName("chatPopoutPanelBtn")
        self._btn_controls.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._btn_controls.setCheckable(True)
        self._btn_controls.setChecked(controls_visible)
        self._btn_controls.toggled.connect(popout._on_controls_toggled)  # noqa: SLF001
        h.addWidget(self._btn_controls, 0, Qt.AlignmentFlag.AlignTop)
        self._close = QPushButton("×")
        self._close.setObjectName("chatPopoutCloseBtn")
        self._close.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._close.clicked.connect(popout.close)
        h.addWidget(self._close, 0, Qt.AlignmentFlag.AlignTop)

    def set_title(self, text: str) -> None:
        self._title.setText(text)

    def mousePressEvent(self, e: QMouseEvent) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = e.globalPosition().toPoint() - self._win.pos()
        else:
            self._drag_offset = None
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        if self._drag_offset is not None and (e.buttons() & Qt.MouseButton.LeftButton):
            self._win.move(e.globalPosition().toPoint() - self._drag_offset)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        self._drag_offset = None
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e: QMouseEvent) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            if self._win.isMaximized():
                self._win.showNormal()
            else:
                self._win.showMaximized()
        super().mouseDoubleClickEvent(e)


# Windows HT* from winuser.h (WM_NCHITTEST result lParam)
_HTC = 1
_HTL, _HTR = 10, 11
_HTB, _HTBL, _HTBR = 15, 16, 17


def _win32_nchit_result(pop: ChatPopoutWindow, p: QPoint) -> int:
    """Map client pt to a WM_NCHITTEST lResult (borders) or HTCLIENT for drag/interaction."""
    w = pop.width()
    h = pop.height()
    m = _RESIZE_MARGIN
    tbar = pop._title_bar.geometry()
    if tbar.contains(p):
        return _HTC
    if p.y() >= h - m:
        if p.x() < m:
            return _HTBL
        if p.x() >= w - m:
            return _HTBR
        return _HTB
    if p.x() < m and p.y() > tbar.bottom():
        return _HTL
    if p.x() >= w - m and p.y() > tbar.bottom():
        return _HTR
    return _HTC


class ChatPopoutWindow(QDialog):
    def __init__(self, main: MainWindow) -> None:
        # Top-level window: no Qt parent — otherwise Windows minimizes this with MainWindow.
        super().__init__(None)
        self._main = main
        self.setObjectName("chatPopout")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        # No native title / DWM buttons — transparency + custom chrome work reliably.
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setModal(False)
        st = QSettings("stream-cheremsha", "cheremsha")
        op = float(str(st.value(_SETTINGS_POPOUT_OPACITY, 1.0)))
        if op < 0.3 or op > 1.0 or op != op:
            op = 1.0
        self._bg_opacity = op
        self._controls_visible = _read_bool_settings(
            st.value(_SETTINGS_POPOUT_CONTROLS),
            default=True,
        )

        self.setMinimumSize(400, 280)
        self.resize(520, 420)
        restore_window_geometry(KEY_CHAT_POPOUT, self)
        self.setStyleSheet(_build_popout_stylesheet(self._bg_opacity))

        self._opacity_row = QWidget()
        self._opacity_row.setObjectName("chatPopoutBar")
        op_lay = QHBoxLayout(self._opacity_row)
        op_lay.setContentsMargins(10, 8, 10, 8)
        self._lbl_opacity = QLabel()
        self._op_slider = QSlider(Qt.Orientation.Horizontal)
        self._op_slider.setRange(30, 100)
        self._op_slider.setValue(int(op * 100))
        self._op_slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._op_percent = QLabel()
        self._op_slider.valueChanged.connect(self._on_opacity_value_changed)
        self._op_slider.sliderReleased.connect(self._persist_opacity)
        op_lay.addWidget(self._lbl_opacity)
        op_lay.addWidget(self._op_slider, stretch=1)
        op_lay.addWidget(self._op_percent)
        self._refresh_opacity_label()

        self._font_bar = QWidget()
        self._font_bar.setObjectName("chatToolbar")
        bar_lay = QHBoxLayout(self._font_bar)
        bar_lay.setContentsMargins(8, 6, 8, 6)
        bar_lay.setSpacing(10)

        self._lbl_font = QLabel()
        self._font = QFontComboBox()
        self._font.setMaxVisibleItems(14)
        self._font.setEditable(False)
        self._font.currentFontChanged.connect(self._on_popout_font_changed)

        self._lbl_size = QLabel()
        self._spin = QSpinBox()
        self._spin.setRange(10, 28)
        self._spin.setValue(14)
        self._spin.setSuffix(" pt")
        self._spin.valueChanged.connect(self._on_popout_size_changed)

        self._btn_test = QPushButton()
        self._btn_test.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._btn_test.clicked.connect(self._main._on_test_chat_message_clicked)  # noqa: SLF001

        self._btn_clear = QPushButton()
        self._btn_clear.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._btn_clear.clicked.connect(self._main._clear_chat_view)  # noqa: SLF001

        bar_lay.addWidget(self._lbl_font)
        bar_lay.addWidget(self._font, stretch=1)
        bar_lay.addWidget(self._lbl_size)
        bar_lay.addWidget(self._spin)
        bar_lay.addStretch(1)
        bar_lay.addWidget(self._btn_test)
        bar_lay.addWidget(self._btn_clear)

        self._title_bar = _PopoutTitleBar(self, controls_visible=self._controls_visible)
        self._opacity_row.setVisible(self._controls_visible)
        self._font_bar.setVisible(self._controls_visible)
        self._title_bar._btn_controls.blockSignals(True)  # noqa: SLF001
        self._title_bar._btn_controls.setChecked(self._controls_visible)  # noqa: SLF001
        self._title_bar._btn_controls.blockSignals(False)  # noqa: SLF001

        self._view = QTextEdit()
        self._view.setObjectName("chatMessageView")
        self._view.setReadOnly(True)
        self._view.setAcceptRichText(True)
        self._view.setUndoRedoEnabled(False)
        self._view.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self._view.document().setDefaultStyleSheet(
            "body { margin: 0; } a { color: #38bdf8; }",
        )
        self._view.setAutoFillBackground(False)

        inner = QWidget()
        inner.setObjectName("chatPopoutInner")
        inner_lay = QVBoxLayout(inner)
        inner_lay.setContentsMargins(0, 0, 0, 0)
        inner_lay.setSpacing(0)
        inner_lay.addWidget(self._opacity_row)
        inner_lay.addWidget(self._font_bar)
        inner_lay.addWidget(self._view, stretch=1)

        E = Qt.Edge
        bottom_w = QWidget()
        bottom_m = QHBoxLayout(bottom_w)
        bottom_m.setContentsMargins(0, 0, 0, 0)
        bottom_m.setSpacing(0)
        bottom_m.addWidget(_EdgeResizeHandle(self, E.LeftEdge | E.BottomEdge))
        bottom_m.addWidget(_EdgeResizeHandle(self, E.BottomEdge), 1)
        bottom_m.addWidget(_EdgeResizeHandle(self, E.RightEdge | E.BottomEdge))

        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(0)
        grid.setVerticalSpacing(0)
        grid.setRowStretch(1, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnMinimumWidth(0, _RESIZE_MARGIN)
        grid.setColumnMinimumWidth(2, _RESIZE_MARGIN)
        grid.setRowMinimumHeight(2, _RESIZE_MARGIN)
        grid.addWidget(self._title_bar, 0, 0, 1, 3)
        grid.addWidget(_EdgeResizeHandle(self, E.LeftEdge), 1, 0)
        grid.addWidget(inner, 1, 1)
        grid.addWidget(_EdgeResizeHandle(self, E.RightEdge), 1, 2)
        grid.addWidget(bottom_w, 2, 0, 1, 3)

        self.apply_texts()
        self._load_font_from_settings()
        self._rebuild_from_history()

    def append_message(self, message: ChatMessage) -> None:
        self._append_html(self._format_chat_message_fragment(message))

    def clear_view(self) -> None:
        self._view.clear()

    def _load_font_from_settings(self) -> None:
        st = QSettings("stream-cheremsha", "cheremsha")
        m = self._main
        if st.contains(_SETTINGS_POPOUT_FONT_PT):
            pt = int(st.value(_SETTINGS_POPOUT_FONT_PT, 14, int))
        else:
            pt = m._spin_chat_font_pt.value() if hasattr(m, "_spin_chat_font_pt") else 14  # noqa: SLF001
        pt = max(10, min(28, pt))
        if st.contains(_SETTINGS_POPOUT_FONT_FAMILY):
            fam = str(st.value(_SETTINGS_POPOUT_FONT_FAMILY, "", str)).strip()
        else:
            fam = (
                m._font_combo_chat.currentFont().family()  # noqa: SLF001
                if hasattr(m, "_font_combo_chat")
                else ""
            )
        self._font.blockSignals(True)
        self._spin.blockSignals(True)
        if fam:
            self._font.setCurrentFont(QFont(fam))
        else:
            self._font.setCurrentFont(QFont(CHAT_DEFAULT_FONT_FAMILY))
        self._spin.setValue(pt)
        self._font.blockSignals(False)
        self._spin.blockSignals(False)

    def _persist_font_appearance(self) -> None:
        st = QSettings("stream-cheremsha", "cheremsha")
        st.setValue(_SETTINGS_POPOUT_FONT_FAMILY, self._font.currentFont().family())
        st.setValue(_SETTINGS_POPOUT_FONT_PT, self._spin.value())
        self._rebuild_from_history()

    def _format_chat_message_fragment(self, message: ChatMessage) -> str:
        m = self._main
        pt = self._spin.value()
        fam = self._font.currentFont().family()
        stack = chat_font_stack_css(fam)
        return format_chat_message_html(
            message,
            font_pt=pt,
            font_stack_css=stack,
            twitch_icon_uri=m._chat_ic_tw,  # noqa: SLF001
            youtube_icon_uri=m._chat_ic_yt,  # noqa: SLF001
            tiktok_icon_uri=m._chat_ic_tk,  # noqa: SLF001
            kick_icon_uri=m._chat_ic_kk,  # noqa: SLF001
        )

    def _rebuild_from_history(self) -> None:
        self._view.clear()
        for message in self._main._chat_message_history:  # noqa: SLF001
            self._append_html(self._format_chat_message_fragment(message))

    def _append_html(self, html_fragment: str) -> None:
        doc = self._view.document()
        cursor = self._view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        if not doc.isEmpty():
            cursor.insertBlock()
        cursor.insertHtml(html_fragment)
        self._view.setTextCursor(cursor)
        sb = self._view.verticalScrollBar()
        sb.setValue(sb.maximum())
        doc = self._view.document()
        while doc.blockCount() > _MAX_CHAT_DOCUMENT_BLOCKS:
            c = QTextCursor(doc)
            c.movePosition(QTextCursor.MoveOperation.Start)
            c.select(QTextCursor.SelectionType.BlockUnderCursor)
            c.removeSelectedText()
            c.deleteChar()

    def closeEvent(self, event: QCloseEvent) -> None:
        save_window_geometry(KEY_CHAT_POPOUT, self)
        # Clear before C++ destruction so MainWindow does not keep a dead wrapper reference.
        self._main._clear_chat_popout_ref()  # noqa: SLF001
        super().closeEvent(event)

    def nativeEvent(self, eventType: object, message: int) -> object:  # noqa: PLR0911
        """Windows: WM_NCHITTEST for frameless resize; Qt mouse path often fails for borders."""
        if sys.platform != "win32":
            return super().nativeEvent(eventType, message)
        try:
            if not isinstance(eventType, (bytes, bytearray, memoryview)):
                event_type_bytes = bytes(eventType)
            else:
                event_type_bytes = eventType
        except (TypeError, ValueError, AttributeError):
            return super().nativeEvent(eventType, message)
        if b"windows" not in event_type_bytes and b"MSG" not in event_type_bytes:
            return super().nativeEvent(eventType, message)
        if not message:
            return super().nativeEvent(eventType, message)
        from ctypes.wintypes import MSG

        try:
            msg = MSG.from_address(int(message))
        except (OSError, TypeError, ValueError, OverflowError):
            return super().nativeEvent(eventType, message)
        if int(msg.message) != 0x0084:  # WM_NCHITTEST
            return super().nativeEvent(eventType, message)
        lp = int(msg.lParam) & 0xFFFFFFFF
        sx = lp & 0xFFFF
        if sx >= 0x8000:
            sx -= 0x10000
        sy = (lp >> 16) & 0xFFFF
        if sy >= 0x8000:
            sy -= 0x10000
        p = self.mapFromGlobal(QPoint(sx, sy))
        if not self.rect().contains(p):
            return super().nativeEvent(eventType, message)
        if self.isMaximized():
            return super().nativeEvent(eventType, message)
        return (True, _win32_nchit_result(self, p))

    def apply_texts(self) -> None:
        m = self._main
        title = m._tr("chat.popout_title")  # noqa: SLF001
        self.setWindowTitle(title)
        self._title_bar.set_title(title)
        self._title_bar._close.setToolTip(m._tr("chat.popout_close"))  # noqa: SLF001
        self._refresh_controls_toggle_tooltip()
        self._lbl_opacity.setText(m._tr("chat.popout_opacity"))  # noqa: SLF001
        self._lbl_font.setText(m._tr("chat.font"))  # noqa: SLF001
        self._lbl_size.setText(m._tr("chat.font_size"))  # noqa: SLF001
        self._btn_test.setText(m._tr("chat.test_message"))  # noqa: SLF001
        self._btn_test.setToolTip(m._tr("chat.test_hint"))  # noqa: SLF001
        self._btn_clear.setText(m._tr("chat.clear"))  # noqa: SLF001
        self._btn_clear.setToolTip(m._tr("chat.clear_hint"))  # noqa: SLF001
        self._refresh_opacity_label()

    @Slot(QFont)
    def _on_popout_font_changed(self, _font: QFont) -> None:
        self._persist_font_appearance()

    @Slot(int)
    def _on_popout_size_changed(self, _v: int) -> None:
        self._persist_font_appearance()

    def _on_opacity_value_changed(self) -> None:
        self._bg_opacity = self._op_slider.value() / 100.0
        self.setStyleSheet(_build_popout_stylesheet(self._bg_opacity))
        self._refresh_opacity_label()

    def _refresh_opacity_label(self) -> None:
        self._op_percent.setText(f"{self._op_slider.value()}%")

    @Slot()
    def _persist_opacity(self) -> None:
        v = self._op_slider.value() / 100.0
        QSettings("stream-cheremsha", "cheremsha").setValue(_SETTINGS_POPOUT_OPACITY, v)

    def _refresh_controls_toggle_tooltip(self) -> None:
        m = self._main
        b = self._title_bar._btn_controls  # noqa: SLF001
        b.setToolTip(
            m._tr("chat.popout_hide_controls")
            if b.isChecked()
            else m._tr("chat.popout_show_controls")
        )

    @Slot(bool)
    def _on_controls_toggled(self, checked: bool) -> None:
        self._controls_visible = checked
        self._opacity_row.setVisible(checked)
        self._font_bar.setVisible(checked)
        self._refresh_controls_toggle_tooltip()
        QSettings("stream-cheremsha", "cheremsha").setValue(
            _SETTINGS_POPOUT_CONTROLS,
            checked,
        )
