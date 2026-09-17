"""Title-bar account pill for the Cheremsha Account (desktop side).

Compact footprint in both states (no large login buttons, no web-style UI):

* logged out: ``[icon] Увійти в Cheremsha`` — click opens a provider menu
  (Google / Twitch / TikTok / Kick); while busy the pill shows a small
  text state (``Відкриваємо браузер…`` / ``Очікуємо авторизацію…``) and
  ignores duplicate clicks (a click while awaiting cancels the login).
* logged in: ``[avatar] name / Cheremsha Account ∨`` — click opens a popover
  with the account header, platform count, settings/dashboard shortcuts and
  sign-out. ``Online``/green status is deliberately NOT shown here — it stays
  reserved for platform/stream state.

All strings come through the ``tr`` callable (l10n). All browser opens go
through ``QDesktopServices`` (system browser, never WebEngine).
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from PySide6.QtCore import QPoint, Qt, QUrl
from PySide6.QtGui import QAction, QColor, QDesktopServices, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMenu,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from stream_cheremsha.cloud import constants
from stream_cheremsha.cloud.auth_state import (
    STATUS_AUTHENTICATED,
    STATUS_AWAITING_CALLBACK,
    STATUS_RESTORING,
    STATUS_STARTING,
    CheremshaAuthState,
)

logger = logging.getLogger(__name__)

_BUSY_STATUSES = frozenset({STATUS_STARTING, STATUS_RESTORING})


class AvatarLabel(QLabel):
    """Fixed-size rounded avatar (downloaded bytes or initial-letter fallback)."""

    def __init__(self, size: int = 28, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        self._pixmap: QPixmap | None = None
        self._fallback = "?"

    def set_avatar(self, data: bytes | None, fallback_text: str) -> None:
        self._fallback = (fallback_text or "?").strip()[:1].upper() or "?"
        self._pixmap = None
        if data:
            pix = QPixmap()
            if pix.loadFromData(data):
                self._pixmap = pix
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = self.rect().adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, rect.width() / 2, rect.height() / 2)
        p.setClipPath(path)
        if self._pixmap is not None and not self._pixmap.isNull():
            p.drawPixmap(
                rect,
                self._pixmap.scaled(
                    rect.size() * 2,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                ),
            )
        else:
            p.fillRect(rect, QColor("#2b3350"))
            p.setPen(QColor("#9aa7c7"))
            font = p.font()
            font.setBold(True)
            font.setPixelSize(max(10, self._size // 2))
            p.setFont(font)
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._fallback)
        p.end()


class AccountPill(QWidget):
    """Clickable account pill for the title bar."""

    def __init__(
        self,
        auth: CheremshaAuthState,
        tr: Callable[[str], str],
        on_open_platforms: Callable[[], None],
        on_open_settings: Callable[[], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._auth = auth
        self._tr = tr
        self._on_open_platforms = on_open_platforms
        self._on_open_settings = on_open_settings
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tr("cloud.login"))

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(8)

        self._avatar = AvatarLabel(28, self)
        lay.addWidget(self._avatar)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(0)
        self._name = QLabel(self)
        self._name.setObjectName("accountPillName")
        self._sub = QLabel(self)
        self._sub.setObjectName("accountPillSub")
        text_col.addWidget(self._name)
        text_col.addWidget(self._sub)
        lay.addLayout(text_col)

        self._chevron = QLabel("﹀", self)
        self._chevron.setObjectName("accountPillChevron")
        lay.addWidget(self._chevron)

        self.setStyleSheet(
            """
            QWidget#accountPill {
              background: #1a2130;
              border: 1px solid #2a3142;
              border-radius: 8px;
            }
            QWidget#accountPill:hover { background: #263246; }
            QLabel#accountPillName {
              background: transparent; border: none;
              color: #e8eaed; font-size: 12px; font-weight: 600;
            }
            QLabel#accountPillSub {
              background: transparent; border: none;
              color: #8b94a7; font-size: 10px;
            }
            QLabel#accountPillChevron {
              background: transparent; border: none;
              color: #8b94a7; font-size: 10px;
            }
            """
        )
        self.setObjectName("accountPill")

        auth.statusChanged.connect(lambda _s: self._refresh())
        auth.userChanged.connect(self._refresh)
        auth.platformsChanged.connect(self._refresh)
        auth.avatarChanged.connect(self._refresh)
        self._refresh()

    # -- rendering ------------------------------------------------------
    def _refresh(self) -> None:
        status = self._auth.status
        if status == STATUS_AUTHENTICATED:
            name = self._auth.displayName or self._auth.email
            self._name.setText(name)
            self._sub.setText(self._tr("cloud.account"))
            self._sub.setVisible(True)
            self._chevron.setVisible(True)
            self._avatar.set_avatar(self._auth.avatar_bytes(), name)
            self.setToolTip(f"{name}\n{self._auth.email}")
        elif status == STATUS_AWAITING_CALLBACK:
            self._name.setText(self._tr("cloud.waiting_auth"))
            self._sub.setVisible(False)
            self._chevron.setVisible(False)
            self._avatar.set_avatar(None, "…")
            self.setToolTip(self._tr("cloud.waiting_auth"))
        elif status in _BUSY_STATUSES:
            self._name.setText(self._tr("cloud.starting"))
            self._sub.setVisible(False)
            self._chevron.setVisible(False)
            self._avatar.set_avatar(None, "…")
            self.setToolTip(self._tr("cloud.starting"))
        else:
            self._name.setText(self._tr("cloud.login"))
            self._sub.setVisible(False)
            self._chevron.setVisible(True)
            self._avatar.set_avatar(None, "◉")
            self.setToolTip(self._tr("cloud.login"))

    # -- interaction ----------------------------------------------------
    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            status = self._auth.status
            if status == STATUS_AWAITING_CALLBACK:
                self._auth.cancelLogin()
            elif status in _BUSY_STATUSES:
                event.ignore()
                return
            elif status == STATUS_AUTHENTICATED:
                self._show_account_menu()
            else:
                self._show_provider_menu()
        super().mousePressEvent(event)

    def _menu_style(self, menu: QMenu) -> None:
        menu.setStyleSheet(
            """
            QMenu {
              background: #161b28; border: 1px solid #2a3142;
              border-radius: 8px; padding: 6px; color: #e8eaed;
            }
            QMenu::item { padding: 8px 12px; border-radius: 6px; font-size: 12px; }
            QMenu::item:selected { background: #263246; }
            QMenu::separator { height: 1px; background: #2a3142; margin: 6px 4px; }
            """
        )

    def _show_provider_menu(self) -> None:
        menu = QMenu(self)
        self._menu_style(menu)
        for provider in constants.LOGIN_PROVIDERS:
            label = self._tr("cloud.login_with").replace("{provider}", provider.title())
            action = QAction(label, menu)
            action.triggered.connect(lambda _c=False, p=provider: self._auth.login(p))
            menu.addAction(action)
        menu.exec(self.mapToGlobal(QPoint(0, self.height())))

    def _show_account_menu(self) -> None:
        menu = QMenu(self)
        self._menu_style(menu)

        header = QWidget(menu)
        header_lay = QHBoxLayout(header)
        header_lay.setContentsMargins(8, 8, 8, 8)
        header_lay.setSpacing(10)
        big_avatar = AvatarLabel(40, header)
        big_avatar.set_avatar(self._auth.avatar_bytes(), self._auth.displayName or self._auth.email)
        header_lay.addWidget(big_avatar)
        info_lay = QVBoxLayout()
        info_lay.setSpacing(2)
        name_lbl = QLabel(self._auth.displayName or self._auth.email, header)
        name_lbl.setStyleSheet("color:#e8eaed;font-size:13px;font-weight:600;")
        email_lbl = QLabel(self._auth.email, header)
        email_lbl.setStyleSheet("color:#8b94a7;font-size:11px;")
        acct_lbl = QLabel("● " + self._tr("cloud.account"), header)
        acct_lbl.setStyleSheet("color:#7ee2a8;font-size:11px;")
        info_lay.addWidget(name_lbl)
        info_lay.addWidget(email_lbl)
        info_lay.addWidget(acct_lbl)
        header_lay.addLayout(info_lay)
        header_action = QWidgetAction(menu)
        header_action.setDefaultWidget(header)
        menu.addAction(header_action)
        menu.addSeparator()

        count = self._auth.connectedPlatformCount
        platforms_action = QAction(f"{self._tr('cloud.platforms')}  {count}", menu)
        platforms_action.triggered.connect(lambda: self._on_open_platforms())
        menu.addAction(platforms_action)

        settings_action = QAction(self._tr("cloud.settings"), menu)
        settings_action.triggered.connect(lambda: self._on_open_settings())
        menu.addAction(settings_action)

        dashboard_action = QAction(self._tr("cloud.dashboard"), menu)
        dashboard_action.triggered.connect(
            lambda: QDesktopServices.openUrl(QUrl(constants.dashboard_url()))
        )
        menu.addAction(dashboard_action)
        menu.addSeparator()

        logout_action = QAction(self._tr("cloud.logout"), menu)
        logout_action.triggered.connect(self._auth.logout)
        menu.addAction(logout_action)

        menu.exec(self.mapToGlobal(QPoint(0, self.height())))
