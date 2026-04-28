from __future__ import annotations

import asyncio
import html
import json
import logging
import os
import threading
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from xml.sax.saxutils import quoteattr

import httpx
import shiboken6
from PySide6.QtCore import (
    QEvent,
    QObject,
    QSettings,
    QSize,
    Qt,
    QTimer,
    QUrl,
    QVariantAnimation,
    Signal,
    Slot,
)
from PySide6.QtGui import QCloseEvent, QColor, QFont, QIcon, QTextCursor
from PySide6.QtQuick import QQuickView
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFontComboBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QStyle,
    QTextBrowser,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from stream_cheremsha import l10n
from stream_cheremsha.audio.qt_sink import QtAudioSink
from stream_cheremsha.chat import twitch_credentials, twitch_oauth_device
from stream_cheremsha.chat.tiktok_source import TikTokChatSource
from stream_cheremsha.actions.engine import PlatformActionsEngine
from stream_cheremsha.actions.events import ChatMessageEvent, GiftReceivedEvent
from stream_cheremsha.actions.store import (
    actions_rules_key_is_set,
    load_rules,
    save_rules,
)
from stream_cheremsha.ui.actions_qml_api import ActionsQmlApi
from stream_cheremsha.chat.twitch_source import TwitchSource
from stream_cheremsha.chat.youtube_source import (
    YouTubeChatSource,
    clear_youtube_user_session,
    is_google_account_linked,
    parse_google_desktop_client_json,
)
from stream_cheremsha.config import constants, keyring_store
from stream_cheremsha.domain.models import ChatMessage, ChatPlatform
from stream_cheremsha.domain.protocols import TextToSpeech
from stream_cheremsha.overlays.chat_overlay import chat_message_to_patch
from stream_cheremsha.overlays.registry import OverlayRegistry
from stream_cheremsha.overlays.server import OverlayServer
from stream_cheremsha.pipeline.coordinator import StreamCoordinator
from stream_cheremsha.tts.google_translate_tts import GoogleTranslateTts
from stream_cheremsha.tts.piper_voices import TTS_LANG_OPTIONS
from stream_cheremsha.tts.rvc_wav import (
    RvcRuntime,
    apply_rvc_if_active,
    rvc_runtime_cancel_pending,
    rvc_runtime_queue_size,
    rvc_runtime_stop_dispatcher,
)
from stream_cheremsha.ui.chat_formatting import (
    CHAT_DEFAULT_FONT_FAMILY,
    chat_font_stack_css,
    format_chat_message_html,
    load_platform_icon_data_uris,
)
from stream_cheremsha.ui.chat_popout import ChatPopoutWindow
from stream_cheremsha.ui.donations_qml_api import DonationsQmlApi
from stream_cheremsha.ui.qml_api import StreamCheremshaQmlApi
from stream_cheremsha.ui.window_geometry import (
    KEY_MAIN_WINDOW,
    KEY_PIPER_HELP_DIALOG,
    restore_window_geometry,
    save_window_geometry,
)

logger = logging.getLogger(__name__)

_STREAM_ROOT = Path(__file__).resolve().parent.parent


def _qml_path(name: str) -> Path:
    return _STREAM_ROOT / "qml" / name


def _asset_path(name: str) -> Path:
    return _STREAM_ROOT / "assets" / name


def _should_activate_window() -> bool:
    """
    Avoid stealing focus on Windows when the user is working in another app.
    We only explicitly activate/raise when our app is already active.
    """
    return QApplication.instance() is not None and (
        QApplication.applicationState() == Qt.ApplicationState.ApplicationActive
    )


def _footer_richtext_img(name: str, px: int) -> str:
    path = _asset_path(name)
    if not path.is_file():
        return ""
    url = QUrl.fromLocalFile(str(path.resolve())).toString()
    return f"<img width='{px}' height='{px}' src={quoteattr(url)} /> "


_MAX_LOG_DOCUMENT_BLOCKS = 3500
_MAX_CHAT_DOCUMENT_BLOCKS = 450
_SETTINGS_CHAT_FONT_PT = "ui/chat_font_pt"
_SETTINGS_CHAT_FONT_FAMILY = "ui/chat_font_family"

_TWITCH_APPS_URL = "https://dev.twitch.tv/console/apps"
_GOOGLE_CREDS_URL = "https://console.cloud.google.com/apis/credentials"
_YOUTUBE_API_LIB_URL = "https://console.cloud.google.com/apis/library/youtube.googleapis.com"
_FORM_LABEL_MIN_WIDTH = 260
_SETTINGS_AUTOSTART_TWITCH = "startup/auto_start_twitch"
_SETTINGS_AUTOSTART_YOUTUBE = "startup/auto_start_youtube"
_SETTINGS_GAME_MODE = "ui/game_mode"
_SETTINGS_TTS_GAIN_DB = "audio/tts_gain_db"
_TTS_ENGINE_GOOGLE = "google"
_TTS_ENGINE_PIPER = "piper"
_SETTINGS_TTS_ENGINE = "tts/engine"
_SETTINGS_PIPER_MODEL = "tts/piper_model_path"
_SETTINGS_TTS_LANG = "tts/output_language"
_SETTINGS_PIPER_CUDA = "tts/piper_use_cuda"
_SETTINGS_RVC_ENABLED = "tts/rvc_enabled"
_SETTINGS_RVC_MODEL = "tts/rvc_model_path"
_SETTINGS_RVC_INDEX = "tts/rvc_index_path"
_SETTINGS_RVC_CUDA = "tts/rvc_use_cuda"
_LEGACY_RVC_ENABLED = "tts/piper_rvc_enabled"
_LEGACY_RVC_MODEL = "tts/piper_rvc_model_path"
_LEGACY_RVC_INDEX = "tts/piper_rvc_index_path"
_SETTINGS_TTS_CHAT_TWITCH = "tts_chat/twitch_enabled"
_SETTINGS_TTS_CHAT_YOUTUBE = "tts_chat/youtube_enabled"
_SETTINGS_TTS_CHAT_TIKTOK = "tts_chat/tiktok_enabled"


class UiBridge(QObject):
    append_chat = Signal(str)
    append_log = Signal(str)


class QtLogHandler(logging.Handler):
    """Send ``stream_cheremsha`` log records to the UI via :class:`UiBridge` (thread-safe)."""

    def __init__(self, bridge: UiBridge) -> None:
        super().__init__(level=logging.INFO)
        self._bridge = bridge
        self.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%H:%M:%S",
            ),
        )

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._bridge.append_log.emit(self.format(record))
        except (RuntimeError, ValueError, TypeError):
            self.handleError(record)


class MainWindow(QWidget):
    """MVP: stacked panes (connections, settings, chat, audio, logs) + status."""

    startup_finished = Signal()

    # QStackedWidget indices (order must match _build_ui addWidget sequence).
    _IX_CONN = 0
    _IX_SETTINGS = 1
    _IX_CHAT = 2
    _IX_AUDIO = 3
    _IX_LOGS = 4
    _IX_DONATIONS = 5

    @staticmethod
    def _external_link_label(html: str) -> QLabel:
        lab = QLabel(html)
        lab.setOpenExternalLinks(True)
        lab.setWordWrap(True)
        lab.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse)
        return lab

    @staticmethod
    def _form_label(text: str) -> QLabel:
        lab = QLabel(text)
        lab.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lab.setMinimumWidth(_FORM_LABEL_MIN_WIDTH)
        lab.setWordWrap(True)
        return lab

    @staticmethod
    def _stretch_field(widget: QWidget) -> QWidget:
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return widget

    @staticmethod
    def _centered_row(inner: QWidget) -> QWidget:
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.addStretch(1)
        h.addWidget(inner, stretch=0)
        h.addStretch(1)
        return row

    def __init__(self) -> None:
        super().__init__()
        init_w, init_h = 1040, 780
        app_inst = QApplication.instance()
        if app_inst is not None:
            primary = app_inst.primaryScreen()
            if primary is not None:
                ag = primary.availableGeometry()
                init_w = max(560, ag.width() // 2)
                init_h = max(400, ag.height() // 2)
        self.resize(init_w, init_h)

        self._settings = QSettings("stream-cheremsha", "cheremsha")
        restore_window_geometry(KEY_MAIN_WINDOW, self)
        self._locale = l10n.normalize_locale(
            self._settings.value(l10n.SETTINGS_UI_LOCALE, l10n.DEFAULT_LOCALE, str),
        )
        self.setWindowTitle(l10n.tr(self._locale, "app.window_title"))
        app_ico = _asset_path("icon.png")
        if app_ico.is_file():
            self.setWindowIcon(QIcon(str(app_ico)))
        self._closing = False
        self._rvc_toggle_busy = False
        self._tiktok_toggle_busy = False
        self._tiktok_enabled = False
        self._overlay_registry = OverlayRegistry()
        self._overlay_server = OverlayServer(registry=self._overlay_registry, host="127.0.0.1", port=17171)
        self._status_app = l10n.tr(self._locale, "status.app_idle")
        self._status_twitch = "—"
        self._status_youtube = "—"
        self._status_tiktok = "—"
        self._tts_chat_platform_enabled: dict[ChatPlatform, bool] = {
            ChatPlatform.TWITCH: bool(self._settings.value(_SETTINGS_TTS_CHAT_TWITCH, True, bool)),
            ChatPlatform.YOUTUBE: bool(self._settings.value(_SETTINGS_TTS_CHAT_YOUTUBE, True, bool)),
            ChatPlatform.TIKTOK: bool(self._settings.value(_SETTINGS_TTS_CHAT_TIKTOK, True, bool)),
        }

        self._bridge = UiBridge(self)
        self._bridge.append_chat.connect(self._append_chat)
        self._log_handler: QtLogHandler | None = None

        self._tts = self._construct_initial_tts()
        self._sink = QtAudioSink(self)
        self._rvc_runtime = RvcRuntime()
        self._coordinator = StreamCoordinator(
            tts=self._tts,
            audio_sink=self._sink,
            on_chat=self._on_chat_message,
            on_status=self._on_user_status,
            should_tts=self._should_tts_for_message,
            get_locale=self._get_locale,
            rvc_runtime=self._rvc_runtime,
        )
        self._twitch = TwitchSource(
            self._coordinator,
            on_status=self._on_user_status,
            get_locale=self._get_locale,
        )
        self._youtube = YouTubeChatSource(
            self._coordinator,
            on_status=self._on_user_status,
            get_locale=self._get_locale,
        )
        self._tiktok = TikTokChatSource(
            self._coordinator,
            on_status=self._on_user_status,
            on_gift=self._on_tiktok_gift,
            get_locale=self._get_locale,
        )
        self._tiktok_username = QLineEdit()
        self._actions_qml_api = ActionsQmlApi(self)
        self._qml_actions: QQuickView | None = None
        self._actions_engines: dict[tuple[str, str], PlatformActionsEngine] = {}
        self._chat_ic_tw: str | None = None
        self._chat_ic_yt: str | None = None
        self._chat_ic_tk: str | None = None
        # Hard cap: no unbounded growth; eviction matches QTextDocument line trim below.
        self._chat_message_history: deque[ChatMessage] = deque(
            maxlen=_MAX_CHAT_DOCUMENT_BLOCKS,
        )
        self._chat_popout: ChatPopoutWindow | None = None

        self._build_ui()
        self._warm_chat_icons()
        self._bridge.append_log.connect(self._append_log_line)
        self._install_log_handler()
        self._load_settings_fields()
        self._refresh_audio_devices()
        self._refresh_connection_panels()

        self._queue_timer = QTimer(self)
        self._queue_timer.timeout.connect(self._refresh_footer)
        self._queue_timer.start(1000)

        # Apply game mode after UI is constructed and settings are loaded.
        self._apply_game_mode_from_settings()

    def _get_locale(self) -> str:
        return self._locale

    def _tr(self, key: str, **kwargs: object) -> str:
        return l10n.tr(self._locale, key, **kwargs)

    def _should_tts_for_message(self, msg: ChatMessage) -> bool:
        return self._chat_tts_enabled(msg.platform)

    def _chat_tts_enabled(self, platform: ChatPlatform) -> bool:
        return bool(self._tts_chat_platform_enabled.get(platform, True))

    def _set_chat_tts_enabled(self, platform: ChatPlatform, enabled: bool) -> None:
        self._tts_chat_platform_enabled[platform] = bool(enabled)
        key = {
            ChatPlatform.TWITCH: _SETTINGS_TTS_CHAT_TWITCH,
            ChatPlatform.YOUTUBE: _SETTINGS_TTS_CHAT_YOUTUBE,
            ChatPlatform.TIKTOK: _SETTINGS_TTS_CHAT_TIKTOK,
        }.get(platform)
        if key is not None:
            self._settings.setValue(key, bool(enabled))

    def _tts_language_from_settings(self) -> str:
        v = str(self._settings.value(_SETTINGS_TTS_LANG, "uk-UA", str)).strip()
        return v if v else "uk-UA"

    def _current_tts_language(self) -> str:
        if hasattr(self, "_combo_tts_lang"):
            d = self._combo_tts_lang.currentData()
            if isinstance(d, str) and d.strip():
                return d.strip()
        return self._tts_language_from_settings()

    def _migrate_rvc_from_legacy_if_needed(self) -> None:
        if self._settings.value("tts/rvc_did_migrate", False, bool):
            return
        self._settings.setValue("tts/rvc_did_migrate", True)
        if not str(self._settings.value(_SETTINGS_RVC_MODEL, "", str)).strip():
            lm = str(self._settings.value(_LEGACY_RVC_MODEL, "", str)).strip()
            if lm:
                self._settings.setValue(_SETTINGS_RVC_MODEL, lm)
        if not str(self._settings.value(_SETTINGS_RVC_INDEX, "", str)).strip():
            lix = str(self._settings.value(_LEGACY_RVC_INDEX, "", str)).strip()
            if lix:
                self._settings.setValue(_SETTINGS_RVC_INDEX, lix)
        if bool(self._settings.value(_LEGACY_RVC_ENABLED, False, bool)):
            self._settings.setValue(_SETTINGS_RVC_ENABLED, True)

    def _rebuild_rvc_chain(self) -> None:
        from stream_cheremsha.tts.rvc_wav import RvcChainRebuildParams, rvc_rebuild_chain

        self._migrate_rvc_from_legacy_if_needed()
        params = RvcChainRebuildParams(
            enabled=bool(self._settings.value(_SETTINGS_RVC_ENABLED, False, bool)),
            model_pth=str(self._settings.value(_SETTINGS_RVC_MODEL, "", str)).strip(),
            index_path=str(self._settings.value(_SETTINGS_RVC_INDEX, "", str)).strip(),
            use_cuda=bool(self._settings.value(_SETTINGS_RVC_CUDA, False, bool)),
        )
        prev = self._rvc_runtime.chain
        self._rvc_runtime.chain = None
        new_chain, err = rvc_rebuild_chain(prev, params)
        self._rvc_runtime.chain = new_chain
        if err is not None:
            logger.warning("RVC chain: %s", err)

    def _construct_initial_tts(self) -> TextToSpeech:
        """Lightweight TTS for startup; Piper loads in :meth:`run_startup` if selected."""
        lang = self._tts_language_from_settings()
        return GoogleTranslateTts(language=lang)

    def _build_ui(self) -> None:
        self._connections_root = self._build_connections_tab()
        self._connections_root.setParent(self)
        self._connections_root.hide()

        self._qml_api = StreamCheremshaQmlApi(self)
        self._qml_conn = QQuickWidget(self)
        self._qml_conn.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        self._qml_conn.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._qml_conn.setClearColor(QColor(10, 11, 14))
        qml_p = _qml_path("ConnectionsView.qml")
        if not qml_p.is_file():
            logger.error("QML not found: %s", qml_p)
        self._qml_conn.engine().rootContext().setContextProperty("api", self._qml_api)
        self._qml_conn.setSource(QUrl.fromLocalFile(str(qml_p)))

        # Actions editor window (created lazily).

        self._donations_qml_api = DonationsQmlApi(self)
        self._qml_donations = QQuickWidget(self)
        self._qml_donations.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        self._qml_donations.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._qml_donations.setClearColor(QColor(10, 11, 14))
        qml_don = _qml_path("DonationsView.qml")
        if not qml_don.is_file():
            logger.error("QML not found: %s", qml_don)
        don_ctx = self._qml_donations.engine().rootContext()
        don_ctx.setContextProperty("donApi", self._donations_qml_api)
        self._qml_donations.setSource(QUrl.fromLocalFile(str(qml_don)))

        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        self._stack = QStackedWidget()
        self._apply_dark_chrome()
        root.addWidget(self._stack, stretch=1)

        self._stack.addWidget(self._qml_conn)
        self._stack.addWidget(self._build_settings_tab())
        self._stack.addWidget(self._build_chat_tab())
        self._stack.addWidget(self._build_audio_tab())
        self._stack.addWidget(self._build_logs_tab())
        self._stack.addWidget(self._qml_donations)

        self._footer_frame = QFrame()
        self._footer_frame.setObjectName("appFooter")
        _foot = QHBoxLayout(self._footer_frame)
        _foot.setContentsMargins(12, 10, 12, 10)
        _foot.setSpacing(8)
        self._status_label = QLabel()
        self._status_label.setWordWrap(True)
        self._status_label.setTextFormat(Qt.TextFormat.RichText)
        self._status_label.setObjectName("footerStatus")
        _foot.addWidget(self._status_label, stretch=1, alignment=Qt.AlignmentFlag.AlignTop)

        self._btn_footer_logs = QToolButton()
        self._btn_footer_logs.setObjectName("footerNav")
        self._btn_footer_logs.setProperty("navId", "navLogs")
        self._btn_footer_logs.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView),
        )
        self._btn_footer_logs.setIconSize(QSize(18, 18))
        self._btn_footer_logs.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon,
        )
        self._btn_footer_logs.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._btn_footer_logs.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_footer_logs.clicked.connect(lambda: self._set_main_page(self._IX_LOGS))
        self._btn_footer_home = QToolButton()
        self._btn_footer_home.setObjectName("footerNav")
        self._btn_footer_home.setProperty("navId", "navHome")
        self._btn_footer_home.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DirHomeIcon),
        )
        self._btn_footer_home.setIconSize(QSize(18, 18))
        self._btn_footer_home.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._btn_footer_home.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._btn_footer_home.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_footer_home.clicked.connect(
            lambda: self._set_main_page(self._IX_CONN),
        )
        self._btn_footer_donations = QToolButton()
        self._btn_footer_donations.setObjectName("footerNav")
        self._btn_footer_donations.setProperty("navId", "navDonations")
        self._btn_footer_donations.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton),
        )
        self._btn_footer_donations.setIconSize(QSize(18, 18))
        self._btn_footer_donations.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon,
        )
        self._btn_footer_donations.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._btn_footer_donations.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_footer_donations.clicked.connect(
            lambda: self._set_main_page(self._IX_DONATIONS),
        )
        _foot.addWidget(
            self._btn_footer_home,
            0,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        _foot.addWidget(
            self._btn_footer_donations,
            0,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        _foot.addWidget(
            self._btn_footer_logs,
            0,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        self._btn_footer_settings = QToolButton()
        self._btn_footer_settings.setObjectName("footerSettings")
        self._btn_footer_settings.setAutoRaise(True)
        st_ico = QIcon.fromTheme(
            "preferences-system",
            self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogInfoView),
        )
        self._btn_footer_settings.setIcon(st_ico)
        self._btn_footer_settings.setIconSize(QSize(20, 20))
        self._btn_footer_settings.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self._btn_footer_settings.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._btn_footer_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_footer_settings.clicked.connect(
            lambda: self._set_main_page(self._IX_SETTINGS),
        )
        _foot.addWidget(
            self._btn_footer_settings,
            0,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        self._btn_footer_chat = QToolButton()
        self._btn_footer_tts = QToolButton()
        for b, name in ((self._btn_footer_chat, "navChat"), (self._btn_footer_tts, "navTts")):
            b.setObjectName("footerNav")
            b.setProperty("navId", name)
        self._btn_footer_chat.clicked.connect(
            lambda: self._set_main_page(self._IX_CHAT),
        )
        self._btn_footer_tts.clicked.connect(
            lambda: self._set_main_page(self._IX_AUDIO),
        )
        _foot.addWidget(
            self._btn_footer_chat,
            0,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        _foot.addWidget(
            self._btn_footer_tts,
            0,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        root.addWidget(self._footer_frame, 0)
        self._qml_api.refresh()
        self._refresh_footer()
        self._apply_in_app_chrome_texts()
        self._stack.currentChanged.connect(self._sync_footer_nav)
        self._sync_footer_nav()

    def _set_main_page(self, index: int) -> None:
        if not hasattr(self, "_stack") or not (0 <= index < self._stack.count()):
            return
        self._stack.setCurrentIndex(index)

    def _sync_footer_nav(self, _index: int = 0) -> None:
        """Subtle active state for Home / Chat / TTS when the stacked page matches."""
        if not hasattr(self, "_stack") or not hasattr(self, "_btn_footer_chat"):
            return
        on_conn = self._stack.currentIndex() == self._IX_CONN
        on_chat = self._stack.currentIndex() == self._IX_CHAT
        on_tts = self._stack.currentIndex() == self._IX_AUDIO
        on_logs = self._stack.currentIndex() == self._IX_LOGS
        on_don = self._stack.currentIndex() == self._IX_DONATIONS
        for b, active in (
            (getattr(self, "_btn_footer_home", None), on_conn),
            (getattr(self, "_btn_footer_donations", None), on_don),
            (getattr(self, "_btn_footer_logs", None), on_logs),
            (self._btn_footer_chat, on_chat),
            (self._btn_footer_tts, on_tts),
        ):
            if b is not None:
                b.setProperty("activeNav", "on" if active else "off")
                b.style().unpolish(b)
                b.style().polish(b)
                b.update()

    def _apply_in_app_chrome_texts(self) -> None:
        if hasattr(self, "_btn_footer_home"):
            th = self._tr("ui.nav_home")
            self._btn_footer_home.setText(th)
            self._btn_footer_home.setToolTip(self._tr("ui.nav_home_hint"))
            self._btn_footer_home.setAccessibleName(th)
        if hasattr(self, "_btn_footer_chat"):
            self._btn_footer_chat.setText(self._tr("ui.nav_chat"))
            self._btn_footer_tts.setText(self._tr("ui.nav_tts"))
            self._btn_footer_chat.setToolTip(self._tr("ui.nav_chat_hint"))
            self._btn_footer_tts.setToolTip(self._tr("ui.nav_tts_hint"))
        if hasattr(self, "_btn_footer_settings"):
            self._btn_footer_settings.setToolTip(self._tr("ui.open_settings_hint"))
            self._btn_footer_settings.setAccessibleName(self._tr("ui.open_settings"))
        if hasattr(self, "_btn_footer_logs"):
            tl = self._tr("ui.nav_logs")
            self._btn_footer_logs.setText(tl)
            self._btn_footer_logs.setToolTip(self._tr("ui.nav_logs_hint"))
            self._btn_footer_logs.setAccessibleName(tl)
        if hasattr(self, "_btn_footer_donations"):
            td = self._tr("ui.nav_donations")
            self._btn_footer_donations.setText(td)
            self._btn_footer_donations.setToolTip(self._tr("ui.nav_donations_hint"))
            self._btn_footer_donations.setAccessibleName(td)

    def _apply_dark_chrome(self) -> None:
        self.setStyleSheet(
            "MainWindow { background-color: #0d0f14; }"
            "QWidget { background-color: transparent; color: #e6e6e6; }"
            "QFrame#appFooter { background-color: #080a0e; border: none; "
            "border-top: 1px solid #1e2430; }"
            "QLabel#footerStatus { color: #b8c0ce; font-size: 11px; }"
            "QToolButton#footerSettings { min-width: 36px; min-height: 36px; background: #121720; "
            "color: #e2e8f0; border: 1px solid #2a3142; border-radius: 10px; padding: 4px; }"
            "QToolButton#footerSettings:hover { background: #1a2030; border-color: #3b4458; }"
            "QToolButton#footerNav { min-width: 64px; min-height: 36px; background: #121720; "
            "color: #e2e8f0; border: 1px solid #2a3142; border-radius: 10px; font-weight: 600; "
            "font-size: 12px; padding: 4px 10px; }"
            "QToolButton#footerNav:hover { background: #1a2030; border-color: #3b4458; }"
            "QToolButton#footerNav[activeNav=\"on\"] { background: #1a2540; "
            "border-color: #3d4f6a; }"
            "QGroupBox { border: 1px solid #2a3142; margin-top: 8px; font-weight: bold; }"
            "QScrollArea { border: none; background: transparent; }"
            "QScrollBar:vertical { width: 10px; background: #0f1219; margin: 4px 2px 4px 0; "
            "border-radius: 5px; border: 1px solid #1e2430; }"
            "QScrollBar::handle:vertical { background: #3d4a60; min-height: 32px; "
            "border-radius: 5px; margin: 2px; }"
            "QScrollBar::handle:vertical:hover { background: #52607a; }"
            "QScrollBar::handle:vertical:pressed { background: #0d9488; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; "
            "border: none; }"
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { "
            "background: transparent; }"
            "QScrollBar:horizontal { height: 10px; background: #0f1219; margin: 0 4px 2px 4px; "
            "border-radius: 5px; border: 1px solid #1e2430; }"
            "QScrollBar::handle:horizontal { background: #3d4a60; min-width: 32px; "
            "border-radius: 5px; margin: 2px; }"
            "QScrollBar::handle:horizontal:hover { background: #52607a; }"
            "QScrollBar::handle:horizontal:pressed { background: #0d9488; }"
            "QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; "
            "border: none; }"
            "QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { "
            "background: transparent; }"
            "QWidget#audioPageRoot { background-color: #0a0b0e; }"
            "QFrame#audioCard { background-color: #121620; border: 1px solid #2a3142; "
            "border-radius: 14px; }"
            "QLabel#audioCardTitle { color: #e8eaed; font-size: 16px; font-weight: 600; }"
            "QLabel#audioMutedCaption { color: #8b95a5; font-size: 12px; }"
            "QLineEdit, QComboBox, QSpinBox, QTextEdit, QPlainTextEdit {"
            " background: #10141c; color: #e6e6e6; border: 1px solid #2a3142; "
            "border-radius: 8px; padding: 6px; }"
            "QTextEdit#chatMessageView { background-color: #070910; color: #e2e8f0; "
            "border: none; border-radius: 0; padding: 6px 8px; "
            "selection-background-color: #1e3a5f; selection-color: #f8fafc; }"
            "QWidget#chatToolbar { background-color: #0a0b0e; border-bottom: 1px solid #1e2430; "
            "padding: 6px 10px; }"
            "QPushButton { background-color: #1a2130; color: #e6e6e6; "
            "border: 1px solid #2f3a4d; border-radius: 8px; padding: 8px 14px; }"
            "QPushButton:hover { background-color: #202a3a; border-color: #3b4458; }"
            "QPushButton:pressed { background-color: #2a3446; border-color: #4a5568; }"
            "QPushButton:focus { outline: none; }"
            "QCheckBox { color: #eef2f6; spacing: 10px; font-size: 13px; }"
            "QCheckBox:disabled { color: #9aa5b8; }"
            "QCheckBox::indicator { width: 20px; height: 20px; border-radius: 5px; "
            "border: 1px solid #5c677a; background: #1e2535; }"
            "QCheckBox::indicator:hover { border-color: #7c8aa0; background: #2a3348; }"
            "QCheckBox::indicator:checked { background: #0f766e; border: 1px solid #2dd4bf; }"
            "QCheckBox::indicator:checked:hover { background: #14b8a6; border-color: #5eead4; }"
            "QCheckBox::indicator:unchecked { border: 1px solid #5c677a; background: #1a2030; }"
            "QCheckBox::indicator:disabled { border: 1px solid #4a5568; background: #232b3d; }"
            "QCheckBox::indicator:checked:disabled { background: #1d4744; "
            "border: 1px solid #3f6d66; }",
        )

    def _build_settings_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lang_row = QHBoxLayout()
        self._lbl_locale = QLabel()
        self._combo_locale = QComboBox()
        self._combo_locale.addItem(self._tr("settings.lang.uk"), "uk")
        self._combo_locale.addItem(self._tr("settings.lang.en"), "en")
        self._combo_locale.currentIndexChanged.connect(self._on_locale_changed)
        lang_row.addWidget(self._lbl_locale)
        lang_row.addWidget(self._combo_locale, stretch=1)
        lay.addLayout(lang_row)

        self._settings_intro = QLabel()
        self._settings_intro.setWordWrap(True)
        lay.addWidget(self._settings_intro)

        self._cb_autostart_twitch = QCheckBox()
        self._cb_autostart_twitch.stateChanged.connect(self._persist_autostart_twitch)
        lay.addWidget(self._cb_autostart_twitch)

        self._cb_autostart_youtube = QCheckBox()
        self._cb_autostart_youtube.stateChanged.connect(self._persist_autostart_youtube)
        lay.addWidget(self._cb_autostart_youtube)

        self._cb_game_mode = QCheckBox()
        self._cb_game_mode.stateChanged.connect(self._persist_game_mode)
        lay.addWidget(self._cb_game_mode)

        lay.addStretch()
        self._apply_settings_tab_texts()
        return w

    def _apply_game_mode_from_settings(self) -> None:
        enabled = bool(self._settings.value(_SETTINGS_GAME_MODE, False, bool))
        self._apply_game_mode_enabled(enabled)

    def _apply_game_mode_enabled(self, enabled: bool) -> None:
        """Game mode: reduce GPU load by avoiding QML on Connections page."""
        if not hasattr(self, "_stack"):
            return
        # Prefer QWidget Connections tab in game mode, QML otherwise.
        target = self._connections_root if enabled else self._qml_conn
        # Already active
        if self._stack.widget(self._IX_CONN) is target:
            return
        cur = self._stack.currentIndex()
        old = self._stack.widget(self._IX_CONN)
        self._stack.removeWidget(old)
        self._stack.insertWidget(self._IX_CONN, target)
        # Keep the user on the same logical page.
        if cur == self._IX_CONN:
            self._stack.setCurrentIndex(self._IX_CONN)
        self._sync_footer_nav()

    @Slot(int)
    def _persist_game_mode(self, _state: int) -> None:
        enabled = bool(self._cb_game_mode.isChecked())
        self._settings.setValue(_SETTINGS_GAME_MODE, enabled)
        self._apply_game_mode_enabled(enabled)

    def _build_connections_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(16)

        self._gb_twitch = QGroupBox()
        tw_grid = QGridLayout(self._gb_twitch)
        tw_grid.setHorizontalSpacing(12)
        tw_grid.setVerticalSpacing(10)
        tw_grid.setColumnStretch(1, 1)
        tw_grid.setColumnMinimumWidth(0, _FORM_LABEL_MIN_WIDTH)

        self._tw_login_panel = QWidget()
        tw_in = QGridLayout(self._tw_login_panel)
        tw_in.setHorizontalSpacing(12)
        tw_in.setVerticalSpacing(10)
        tw_in.setColumnStretch(1, 1)
        tw_in.setColumnMinimumWidth(0, _FORM_LABEL_MIN_WIDTH)
        tr = 0
        self._lbl_tw_apps_help = self._external_link_label("")
        tw_in.addWidget(self._lbl_tw_apps_help, tr, 0, 1, 2)
        tr += 1
        self._twitch_client_id = QLineEdit()
        self._lbl_tw_client_id = self._form_label("")
        tw_in.addWidget(self._lbl_tw_client_id, tr, 0)
        tw_in.addWidget(self._stretch_field(self._twitch_client_id), tr, 1)
        tr += 1
        self._twitch_client_secret = QLineEdit()
        self._twitch_client_secret.setEchoMode(QLineEdit.EchoMode.Password)
        self._lbl_tw_client_secret = self._form_label("")
        tw_in.addWidget(self._lbl_tw_client_secret, tr, 0)
        tw_in.addWidget(self._stretch_field(self._twitch_client_secret), tr, 1)
        tr += 1
        self._btn_twitch_oauth = QPushButton()
        self._btn_twitch_oauth.clicked.connect(self._schedule_twitch_browser_login)
        self._lbl_tw_account = self._form_label("")
        tw_in.addWidget(self._lbl_tw_account, tr, 0)
        tw_in.addWidget(self._stretch_field(self._btn_twitch_oauth), tr, 1)
        tr += 1
        self._twitch_token = QLineEdit()
        self._twitch_token.setEchoMode(QLineEdit.EchoMode.Password)
        self._lbl_tw_token_manual = self._form_label("")
        tw_in.addWidget(self._lbl_tw_token_manual, tr, 0)
        tw_in.addWidget(self._stretch_field(self._twitch_token), tr, 1)
        tr += 1
        self._btn_save_tw = QPushButton()
        self._btn_save_tw.clicked.connect(self._save_twitch_keys)
        tw_in.addWidget(self._centered_row(self._btn_save_tw), tr, 0, 1, 2)

        self._tw_connected_panel = QWidget()
        tw_connected_lay = QVBoxLayout(self._tw_connected_panel)
        tw_connected_lay.setContentsMargins(0, 0, 0, 0)
        tw_connected_lay.setSpacing(10)
        self._twitch_logged_in_label = QLabel()
        self._twitch_logged_in_label.setWordWrap(True)
        f = self._twitch_logged_in_label.font()
        f.setBold(True)
        self._twitch_logged_in_label.setFont(f)
        tw_connected_lay.addWidget(self._twitch_logged_in_label)
        self._btn_tw_logout = QPushButton()
        self._btn_tw_logout.clicked.connect(self._logout_twitch)
        tw_connected_lay.addWidget(self._centered_row(self._btn_tw_logout))

        tw_grid.addWidget(self._tw_login_panel, 0, 0, 1, 2)
        tw_grid.addWidget(self._tw_connected_panel, 0, 0, 1, 2)

        self._twitch_channel = QLineEdit()
        self._lbl_twitch_channel = self._form_label("")
        tw_grid.addWidget(self._lbl_twitch_channel, 1, 0)
        tw_grid.addWidget(self._stretch_field(self._twitch_channel), 1, 1)

        tw_btns = QWidget()
        tw_btns_lay = QHBoxLayout(tw_btns)
        tw_btns_lay.setContentsMargins(0, 0, 0, 0)
        tw_btns_lay.setSpacing(10)
        self._btn_twitch_transport = QPushButton()
        self._btn_twitch_transport.clicked.connect(self._on_twitch_transport_clicked)
        tw_btns_lay.addWidget(self._btn_twitch_transport, stretch=1)
        tw_grid.addWidget(tw_btns, 2, 0, 1, 2)

        layout.addWidget(self._gb_twitch)

        self._gb_youtube = QGroupBox()
        yt_grid = QGridLayout(self._gb_youtube)
        yt_grid.setHorizontalSpacing(12)
        yt_grid.setVerticalSpacing(10)
        yt_grid.setColumnStretch(1, 1)
        yt_grid.setColumnMinimumWidth(0, _FORM_LABEL_MIN_WIDTH)

        self._yt_login_panel = QWidget()
        yt_in = QGridLayout(self._yt_login_panel)
        yt_in.setHorizontalSpacing(12)
        yt_in.setVerticalSpacing(10)
        yt_in.setColumnStretch(1, 1)
        yt_in.setColumnMinimumWidth(0, _FORM_LABEL_MIN_WIDTH)
        yr = 0
        self._lbl_yt_oauth_help = self._external_link_label("")
        yt_in.addWidget(self._lbl_yt_oauth_help, yr, 0, 1, 2)
        yr += 1
        self._btn_yt_oauth = QPushButton()
        self._btn_yt_oauth.clicked.connect(lambda: asyncio.ensure_future(self._run_youtube_oauth()))
        self._lbl_yt_account = self._form_label("")
        yt_in.addWidget(self._lbl_yt_account, yr, 0)
        yt_in.addWidget(self._stretch_field(self._btn_yt_oauth), yr, 1)
        yr += 1
        self._btn_yt_forget = QPushButton()
        self._btn_yt_forget.clicked.connect(self._forget_youtube_client_config)
        yt_in.addWidget(self._centered_row(self._btn_yt_forget), yr, 0, 1, 2)

        self._yt_connected_panel = QWidget()
        yt_connected_lay = QVBoxLayout(self._yt_connected_panel)
        yt_connected_lay.setContentsMargins(0, 0, 0, 0)
        yt_connected_lay.setSpacing(10)
        self._yt_logged_in_label = QLabel()
        self._yt_logged_in_label.setWordWrap(True)
        fy = self._yt_logged_in_label.font()
        fy.setBold(True)
        self._yt_logged_in_label.setFont(fy)
        yt_connected_lay.addWidget(self._yt_logged_in_label)
        self._btn_yt_logout = QPushButton()
        self._btn_yt_logout.clicked.connect(self._logout_youtube)
        yt_connected_lay.addWidget(self._centered_row(self._btn_yt_logout))

        yt_grid.addWidget(self._yt_login_panel, 0, 0, 1, 2)
        yt_grid.addWidget(self._yt_connected_panel, 0, 0, 1, 2)

        self._yt_video = QLineEdit()
        self._lbl_yt_video = self._form_label("")
        yt_grid.addWidget(self._lbl_yt_video, 1, 0)
        yt_grid.addWidget(self._stretch_field(self._yt_video), 1, 1)
        self._lbl_yt_studio = self._external_link_label("")
        yt_grid.addWidget(self._lbl_yt_studio, 2, 0, 1, 2)

        yt_btns = QWidget()
        yt_btns_lay = QHBoxLayout(yt_btns)
        yt_btns_lay.setContentsMargins(0, 0, 0, 0)
        yt_btns_lay.setSpacing(10)
        self._btn_youtube_transport = QPushButton()
        self._btn_youtube_transport.clicked.connect(self._on_youtube_transport_clicked)
        yt_btns_lay.addWidget(self._btn_youtube_transport, stretch=1)
        yt_grid.addWidget(yt_btns, 3, 0, 1, 2)

        layout.addWidget(self._gb_youtube)

        layout.addStretch()
        self._apply_connections_tab_texts()
        return w

    def _apply_settings_tab_texts(self) -> None:
        self._lbl_locale.setText(self._tr("settings.lang_label"))
        self._combo_locale.setItemText(0, self._tr("settings.lang.uk"))
        self._combo_locale.setItemText(1, self._tr("settings.lang.en"))
        self._settings_intro.setText(self._tr("settings.intro"))
        self._cb_autostart_twitch.setText(self._tr("settings.autostart_twitch"))
        self._cb_autostart_youtube.setText(self._tr("settings.autostart_youtube"))
        # No l10n key yet: keep explicit UA-focused label.
        self._cb_game_mode.setText("Game mode (менше навантаження на GPU / менше просідань FPS)")

    def _apply_connections_tab_texts(self) -> None:
        self._gb_twitch.setTitle(self._tr("tw.group"))
        self._lbl_tw_apps_help.setText(self._tr("tw.apps_help", url=_TWITCH_APPS_URL))
        self._lbl_tw_client_id.setText(self._tr("tw.client_id"))
        self._lbl_tw_client_secret.setText(self._tr("tw.client_secret"))
        self._lbl_tw_account.setText(self._tr("tw.account"))
        self._btn_twitch_oauth.setText(self._tr("tw.btn_browser"))
        self._twitch_token.setPlaceholderText(self._tr("tw.token_placeholder"))
        self._lbl_tw_token_manual.setText(self._tr("tw.token_manual"))
        self._btn_save_tw.setText(self._tr("tw.save_app"))
        self._btn_tw_logout.setText(self._tr("tw.logout"))
        self._twitch_channel.setPlaceholderText(self._tr("tw.channel_ph"))
        self._lbl_twitch_channel.setText(self._tr("tw.channel"))
        self._gb_youtube.setTitle(self._tr("yt.group"))
        self._lbl_yt_oauth_help.setText(
            self._tr(
                "yt.oauth_help",
                creds_url=_GOOGLE_CREDS_URL,
                api_url=_YOUTUBE_API_LIB_URL,
            ),
        )
        self._btn_yt_oauth.setText(self._tr("yt.btn_google"))
        self._lbl_yt_account.setText(self._tr("tw.account"))
        self._btn_yt_forget.setText(self._tr("yt.forget_json"))
        self._btn_yt_logout.setText(self._tr("yt.logout"))
        self._yt_video.setPlaceholderText(self._tr("yt.video_ph"))
        self._lbl_yt_video.setText(self._tr("yt.video_label"))
        self._lbl_yt_studio.setText(self._tr("yt.studio_link"))

    @Slot(int)
    def _on_locale_changed(self, _index: int) -> None:
        data = self._combo_locale.currentData()
        if not isinstance(data, str):
            return
        nl = l10n.normalize_locale(data)
        if nl == self._locale:
            return
        self._locale = nl
        self._settings.setValue(l10n.SETTINGS_UI_LOCALE, self._locale)
        self._retranslate_ui()
        self._refresh_footer()
        self._refresh_connection_panels()

    def _retranslate_ui(self) -> None:
        self.setWindowTitle(self._tr("app.window_title"))
        self._apply_settings_tab_texts()
        self._apply_connections_tab_texts()
        self._apply_audio_tab_texts()
        self._apply_logs_tab_texts()
        self._apply_chat_tab_texts()
        self._apply_in_app_chrome_texts()
        if hasattr(self, "_qml_api"):
            self._qml_api.refresh()
        if hasattr(self, "_donations_qml_api"):
            self._donations_qml_api.refreshUi()
        if self._chat_popout is not None:
            self._chat_popout.apply_texts()

    def _refresh_connection_panels(self) -> None:
        tw_in = twitch_credentials.twitch_keyring_has_session()
        self._tw_login_panel.setVisible(not tw_in)
        self._tw_connected_panel.setVisible(tw_in)
        if tw_in:
            bundle = twitch_credentials.load_oauth_bundle()
            manual = keyring_store.get_password(constants.KEY_TWITCH_TOKEN)
            if bundle and bundle.authorized_login:
                self._twitch_logged_in_label.setText(
                    self._tr("tw.connected_as", login=bundle.authorized_login),
                )
            elif bundle:
                self._twitch_logged_in_label.setText(self._tr("tw.connected_oauth"))
            elif manual:
                self._twitch_logged_in_label.setText(self._tr("tw.connected_token"))
            else:
                self._twitch_logged_in_label.setText(self._tr("tw.connected_generic"))

        yt_in = is_google_account_linked()
        self._yt_login_panel.setVisible(not yt_in)
        self._yt_connected_panel.setVisible(yt_in)
        if yt_in:
            self._yt_logged_in_label.setText(self._tr("yt.connected_default"))
        if hasattr(self, "_qml_api"):
            self._qml_api.refresh()

    @Slot()
    def _logout_twitch(self) -> None:
        asyncio.ensure_future(self._async_logout_twitch())

    async def _async_logout_twitch(self) -> None:
        await self._twitch.stop()
        twitch_credentials.clear_twitch_session()
        self._twitch_token.clear()
        self._on_user_status(self._tr("status.logout_twitch"))
        self._refresh_connection_panels()

    @Slot()
    def _logout_youtube(self) -> None:
        asyncio.ensure_future(self._async_logout_youtube())

    async def _async_logout_youtube(self) -> None:
        await self._youtube.stop()
        clear_youtube_user_session()
        self._on_user_status(self._tr("status.logout_youtube"))
        self._refresh_connection_panels()

    def _twitch_client_id_resolved(self) -> str:
        env_cid = os.environ.get(constants.ENV_TWITCH_CLIENT_ID, "").strip()
        if env_cid:
            return env_cid
        cid = keyring_store.get_password(constants.KEY_TWITCH_CLIENT_ID) or ""
        if cid.strip():
            return cid.strip()
        return self._twitch_client_id.text().strip()

    def _twitch_client_secret_resolved(self) -> str:
        t = self._twitch_client_secret.text().strip()
        if t:
            return t
        return keyring_store.get_password(constants.KEY_TWITCH_CLIENT_SECRET) or ""

    def _build_chat_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(0)
        lay.setContentsMargins(0, 0, 0, 0)

        bar = QWidget()
        bar.setObjectName("chatToolbar")
        bar_lay = QHBoxLayout(bar)
        bar_lay.setContentsMargins(8, 6, 8, 6)
        bar_lay.setSpacing(10)

        self._lbl_chat_font = QLabel()
        self._font_combo_chat = QFontComboBox()
        self._font_combo_chat.setMaxVisibleItems(14)
        self._font_combo_chat.setEditable(False)
        self._font_combo_chat.currentFontChanged.connect(self._persist_chat_appearance)

        self._lbl_chat_size = QLabel()
        self._spin_chat_font_pt = QSpinBox()
        self._spin_chat_font_pt.setRange(10, 28)
        self._spin_chat_font_pt.setValue(14)
        self._spin_chat_font_pt.setSuffix(" pt")
        self._spin_chat_font_pt.valueChanged.connect(self._persist_chat_appearance)

        self._btn_chat_test = QPushButton()
        self._btn_chat_test.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._btn_chat_test.clicked.connect(self._on_test_chat_message_clicked)

        self._btn_chat_clear = QPushButton()
        self._btn_chat_clear.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._btn_chat_clear.clicked.connect(self._clear_chat_view)

        self._btn_chat_popout = QPushButton()
        self._btn_chat_popout.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._btn_chat_popout.clicked.connect(self._open_or_raise_chat_popout)

        bar_lay.addWidget(self._lbl_chat_font)
        bar_lay.addWidget(self._font_combo_chat, stretch=1)
        bar_lay.addWidget(self._lbl_chat_size)
        bar_lay.addWidget(self._spin_chat_font_pt)
        bar_lay.addStretch(1)
        bar_lay.addWidget(self._btn_chat_popout)
        bar_lay.addWidget(self._btn_chat_test)
        bar_lay.addWidget(self._btn_chat_clear)

        self._chat_view = QTextEdit()
        self._chat_view.setObjectName("chatMessageView")
        self._chat_view.setReadOnly(True)
        self._chat_view.setAcceptRichText(True)
        self._chat_view.setUndoRedoEnabled(False)
        self._chat_view.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self._chat_view.document().setDefaultStyleSheet(
            "body { margin: 0; } a { color: #38bdf8; }",
        )
        lay.addWidget(bar)
        lay.addWidget(self._chat_view, stretch=1)
        self._apply_chat_tab_texts()
        return w

    def _build_logs_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self._logs_hint = QLabel()
        self._logs_hint.setWordWrap(True)
        self._logs_hint.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(self._logs_hint)
        bar = QHBoxLayout()
        bar.addStretch(1)
        self._btn_logs_clear = QPushButton()
        bar.addWidget(self._btn_logs_clear)
        lay.addLayout(bar)
        self._log_view = QTextEdit()
        self._btn_logs_clear.clicked.connect(self._log_view.clear)
        self._log_view.setReadOnly(True)
        self._log_view.setAcceptRichText(False)
        lf = self._log_view.font()
        lf.setFamilies(["monospace", "Consolas", "DejaVu Sans Mono"])
        self._log_view.setFont(lf)
        lay.addWidget(self._log_view, stretch=1)
        self._apply_logs_tab_texts()
        return w

    def _apply_logs_tab_texts(self) -> None:
        self._logs_hint.setText(self._tr("logs.hint"))
        self._btn_logs_clear.setText(self._tr("logs.clear"))

    def _apply_chat_tab_texts(self) -> None:
        if not hasattr(self, "_lbl_chat_font"):
            return
        self._lbl_chat_font.setText(self._tr("chat.font"))
        self._lbl_chat_size.setText(self._tr("chat.font_size"))
        if hasattr(self, "_btn_chat_popout"):
            self._btn_chat_popout.setText(self._tr("chat.open_popout"))
            self._btn_chat_popout.setToolTip(self._tr("chat.open_popout_hint"))
        self._btn_chat_clear.setText(self._tr("chat.clear"))
        self._btn_chat_clear.setToolTip(self._tr("chat.clear_hint"))
        self._btn_chat_test.setText(self._tr("chat.test_message"))
        self._btn_chat_test.setToolTip(self._tr("chat.test_hint"))

    def _warm_chat_icons(self) -> None:
        tw, yt, tk = load_platform_icon_data_uris(_STREAM_ROOT / "assets")
        self._chat_ic_tw = tw
        self._chat_ic_yt = yt
        self._chat_ic_tk = tk

    def _load_chat_font_from_settings(self) -> None:
        if not hasattr(self, "_spin_chat_font_pt"):
            return
        pt = int(self._settings.value(_SETTINGS_CHAT_FONT_PT, 14, int))
        pt = max(10, min(28, pt))
        fam = str(self._settings.value(_SETTINGS_CHAT_FONT_FAMILY, "", str)).strip()
        self._spin_chat_font_pt.blockSignals(True)
        self._spin_chat_font_pt.setValue(pt)
        self._spin_chat_font_pt.blockSignals(False)
        self._font_combo_chat.blockSignals(True)
        if fam:
            self._font_combo_chat.setCurrentFont(QFont(fam))
        else:
            self._font_combo_chat.setCurrentFont(QFont(CHAT_DEFAULT_FONT_FAMILY))
        self._font_combo_chat.blockSignals(False)

    def _persist_chat_appearance(self) -> None:
        if not hasattr(self, "_spin_chat_font_pt"):
            return
        self._settings.setValue(
            _SETTINGS_CHAT_FONT_FAMILY,
            self._font_combo_chat.currentFont().family(),
        )
        self._settings.setValue(_SETTINGS_CHAT_FONT_PT, self._spin_chat_font_pt.value())
        self._rebuild_chat_from_history()
        if self._chat_popout is not None:
            self._chat_popout.sync_from_main()

    def _open_or_raise_chat_popout(self) -> None:
        w = self._chat_popout
        if w is not None and shiboken6.isValid(w):
            w.show()
            if _should_activate_window():
                w.raise_()
                w.activateWindow()
            return
        self._chat_popout = None
        pop = ChatPopoutWindow(self)
        pop.destroyed.connect(self._clear_chat_popout_ref)
        self._chat_popout = pop
        pop.show()

    @Slot()
    def _clear_chat_popout_ref(self) -> None:
        self._chat_popout = None

    def _format_chat_message_fragment(self, message: ChatMessage) -> str:
        pt = self._spin_chat_font_pt.value() if hasattr(self, "_spin_chat_font_pt") else 14
        fam = (
            self._font_combo_chat.currentFont().family()
            if hasattr(self, "_font_combo_chat")
            else ""
        )
        stack = chat_font_stack_css(fam)
        return format_chat_message_html(
            message,
            font_pt=pt,
            font_stack_css=stack,
            twitch_icon_uri=self._chat_ic_tw,
            youtube_icon_uri=self._chat_ic_yt,
            tiktok_icon_uri=self._chat_ic_tk,
        )

    def _rebuild_chat_from_history(self) -> None:
        if not hasattr(self, "_chat_view"):
            return
        self._chat_view.clear()
        for message in self._chat_message_history:
            fr = self._format_chat_message_fragment(message)
            doc = self._chat_view.document()
            cur = self._chat_view.textCursor()
            cur.movePosition(QTextCursor.MoveOperation.End)
            if not doc.isEmpty():
                cur.insertBlock()
            cur.insertHtml(fr)
        self._chat_view.setTextCursor(cur)
        sb = self._chat_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _clear_chat_view(self) -> None:
        self._chat_view.clear()
        self._chat_message_history.clear()

    def _on_test_chat_message_clicked(self) -> None:
        """Preview-only samples (not sent to stream chat or TTS)."""
        author = self._tr("chat.test_author")
        now = datetime.now(UTC)
        self._on_chat_message(
            ChatMessage(
                author=author,
                text=self._tr("chat.test_body_twitch"),
                platform=ChatPlatform.TWITCH,
                received_at=now,
            ),
        )
        self._on_chat_message(
            ChatMessage(
                author=author,
                text=self._tr("chat.test_body_youtube"),
                platform=ChatPlatform.YOUTUBE,
                received_at=now,
            ),
        )

    def _install_log_handler(self) -> None:
        root = logging.getLogger("stream_cheremsha")
        if self._log_handler is not None:
            root.removeHandler(self._log_handler)
        self._log_handler = QtLogHandler(self._bridge)
        root.addHandler(self._log_handler)
        root.setLevel(logging.INFO)

    def _uninstall_log_handler(self) -> None:
        if self._log_handler is None:
            return
        logging.getLogger("stream_cheremsha").removeHandler(self._log_handler)
        self._log_handler = None

    def _make_audio_card(self, accent: str) -> tuple[QFrame, QVBoxLayout, QLabel]:
        """Rounded dark card with accent bar and title (Audio tab)."""
        card = QFrame()
        card.setObjectName("audioCard")
        root_lay = QVBoxLayout(card)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)
        head_wrap = QWidget()
        head = QHBoxLayout(head_wrap)
        head.setContentsMargins(16, 14, 16, 10)
        head.setSpacing(10)
        bar = QFrame()
        bar.setFixedSize(3, 22)
        bar.setStyleSheet(f"background-color: {accent}; border-radius: 1px;")
        title_lab = QLabel()
        title_lab.setObjectName("audioCardTitle")
        head.addWidget(bar, alignment=Qt.AlignmentFlag.AlignVCenter)
        head.addWidget(title_lab, alignment=Qt.AlignmentFlag.AlignVCenter)
        head.addStretch(1)
        root_lay.addWidget(head_wrap)
        body = QVBoxLayout()
        body.setContentsMargins(16, 4, 16, 16)
        body.setSpacing(10)
        body_w = QWidget()
        body_w.setLayout(body)
        root_lay.addWidget(body_w)
        return card, body, title_lab

    def _build_audio_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        inner = QWidget()
        inner.setObjectName("audioPageRoot")
        main_lay = QVBoxLayout(inner)
        main_lay.setContentsMargins(16, 12, 16, 20)
        main_lay.setSpacing(16)

        # --- Test card ---
        _t_card, t_body, self._lbl_audio_card_test_h = self._make_audio_card("#34d399")
        self._lbl_audio_test = QLabel()
        self._lbl_audio_test.setObjectName("audioMutedCaption")
        self._test_phrase = QLineEdit()
        self._btn_audio_speak = QPushButton()
        self._btn_audio_speak.setAutoDefault(False)
        self._btn_audio_speak.setDefault(False)
        self._btn_audio_speak.clicked.connect(lambda: asyncio.ensure_future(self._test_tts()))
        t_body.addWidget(self._lbl_audio_test)
        t_body.addWidget(self._test_phrase)
        t_body.addWidget(self._btn_audio_speak)
        main_lay.addWidget(_t_card)

        # --- TTS language & engine (always visible — must not live inside Piper-only card) ---
        self._frm_audio_tts, tts_body, self._lbl_audio_tts_card_h = self._make_audio_card(
            "#38bdf8",
        )
        self._lbl_tts_lang = QLabel()
        self._combo_tts_lang = QComboBox()
        for tag in TTS_LANG_OPTIONS:
            self._combo_tts_lang.addItem("", tag)
        self._combo_tts_lang.currentIndexChanged.connect(self._on_tts_language_changed)
        self._lbl_tts_engine = QLabel()
        self._combo_tts_engine = QComboBox()
        self._combo_tts_engine.addItem("", _TTS_ENGINE_GOOGLE)
        self._combo_tts_engine.addItem("", _TTS_ENGINE_PIPER)
        self._combo_tts_engine.currentIndexChanged.connect(self._on_tts_engine_changed)
        self._engine_row = QWidget()
        er = QHBoxLayout(self._engine_row)
        er.setContentsMargins(0, 0, 0, 0)
        er.addWidget(self._combo_tts_engine, stretch=1)
        self._btn_piper_help = QToolButton()
        self._btn_piper_help.setAutoRaise(True)
        self._btn_piper_help.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxQuestion),
        )
        self._btn_piper_help.clicked.connect(self._show_piper_help_dialog)
        er.addWidget(self._btn_piper_help)
        f_lang = QFormLayout()
        f_lang.setContentsMargins(0, 0, 0, 0)
        f_lang.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        f_lang.setHorizontalSpacing(8)
        f_lang.setVerticalSpacing(2)
        f_lang.addRow(self._lbl_tts_lang, self._combo_tts_lang)
        w_lang = QWidget()
        w_lang.setLayout(f_lang)
        f_eng = QFormLayout()
        f_eng.setContentsMargins(0, 0, 0, 0)
        f_eng.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        f_eng.setHorizontalSpacing(8)
        f_eng.setVerticalSpacing(2)
        f_eng.addRow(self._lbl_tts_engine, self._engine_row)
        w_eng = QWidget()
        w_eng.setLayout(f_eng)
        lang_engine = QWidget()
        le = QHBoxLayout(lang_engine)
        le.setContentsMargins(0, 0, 0, 0)
        le.setSpacing(16)
        le.addWidget(w_lang, stretch=1)
        le.addWidget(w_eng, stretch=1)
        tts_body.addWidget(lang_engine)

        self._btn_audio_flush_queues = QPushButton()
        self._btn_audio_flush_queues.setAutoDefault(False)
        self._btn_audio_flush_queues.setDefault(False)
        self._btn_audio_flush_queues.clicked.connect(
            lambda: asyncio.ensure_future(self._flush_tts_and_rvc_queues()),
        )
        tts_body.addWidget(self._btn_audio_flush_queues)
        main_lay.addWidget(self._frm_audio_tts)

        # --- Piper card (voice model + CUDA only) ---
        self._frm_piper_voice, piper_body, self._lbl_audio_piper_card_h = self._make_audio_card(
            "#7c3aed",
        )
        self._btn_piper_download = QPushButton()
        self._btn_piper_download.setAutoDefault(False)
        self._btn_piper_download.setDefault(False)
        self._btn_piper_download.clicked.connect(self._schedule_piper_voice_download)
        piper_body.addWidget(self._btn_piper_download)
        self._piper_model_edit = QLineEdit()
        self._piper_model_edit.setPlaceholderText("voice.onnx")
        self._piper_model_edit.editingFinished.connect(self._on_piper_model_commit)
        self._btn_piper_browse = QPushButton()
        self._btn_piper_browse.setAutoDefault(False)
        self._btn_piper_browse.setDefault(False)
        self._btn_piper_browse.clicked.connect(self._browse_piper_model)
        self._piper_browse_lbl = QLabel()
        pm_row = QHBoxLayout()
        pm_row.setSpacing(8)
        pm_row.addWidget(self._piper_browse_lbl)
        pm_row.addWidget(self._piper_model_edit, stretch=1)
        pm_row.addWidget(self._btn_piper_browse)
        self._piper_model_wrap = QWidget()
        self._piper_model_wrap.setLayout(pm_row)
        piper_body.addWidget(self._piper_model_wrap)
        self._cb_piper_cuda = QCheckBox()
        self._cb_piper_cuda.toggled.connect(self._on_piper_cuda_toggled)
        piper_body.addWidget(self._cb_piper_cuda)

        main_lay.addWidget(self._frm_piper_voice)
        self._setup_piper_loading_overlay()

        # --- RVC card ---
        self._frm_rvc, rvc_body, self._lbl_audio_rvc_card_h = self._make_audio_card("#f472b6")
        rvc_form_w = QWidget()
        rvc_form = QFormLayout(rvc_form_w)
        rvc_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        rvc_form.setVerticalSpacing(6)
        rvc_form.setContentsMargins(0, 0, 0, 0)
        self._cb_rvc = QCheckBox()
        self._cb_rvc.toggled.connect(self._on_rvc_toggled)
        rvc_form.addRow(self._cb_rvc)
        self._lbl_rvc_model = self._form_label("")
        rvc_m_row = QHBoxLayout()
        self._rvc_model_edit = QLineEdit()
        self._rvc_model_edit.setPlaceholderText("model.pth")
        self._rvc_model_edit.editingFinished.connect(self._on_rvc_model_commit)
        self._btn_rvc_browse = QPushButton()
        self._btn_rvc_browse.setAutoDefault(False)
        self._btn_rvc_browse.setDefault(False)
        self._btn_rvc_browse.clicked.connect(self._browse_rvc_model)
        rvc_m_row.addWidget(self._rvc_model_edit, stretch=1)
        rvc_m_row.addWidget(self._btn_rvc_browse)
        rvc_mw = QWidget()
        rvc_mw.setLayout(rvc_m_row)
        rvc_form.addRow(self._lbl_rvc_model, rvc_mw)
        self._lbl_rvc_index = self._form_label("")
        rvc_i_row = QHBoxLayout()
        self._rvc_index_edit = QLineEdit()
        self._rvc_index_edit.setPlaceholderText("model.index")
        self._rvc_index_edit.editingFinished.connect(self._on_rvc_index_commit)
        self._btn_rvc_index_browse = QPushButton()
        self._btn_rvc_index_browse.setAutoDefault(False)
        self._btn_rvc_index_browse.setDefault(False)
        self._btn_rvc_index_browse.clicked.connect(self._browse_rvc_index)
        rvc_i_row.addWidget(self._rvc_index_edit, stretch=1)
        rvc_i_row.addWidget(self._btn_rvc_index_browse)
        rvc_iw = QWidget()
        rvc_iw.setLayout(rvc_i_row)
        rvc_form.addRow(self._lbl_rvc_index, rvc_iw)
        self._cb_rvc_cuda = QCheckBox()
        self._cb_rvc_cuda.toggled.connect(self._on_rvc_cuda_toggled)
        rvc_form.addRow(self._cb_rvc_cuda)
        rvc_body.addWidget(rvc_form_w)
        main_lay.addWidget(self._frm_rvc)
        self._setup_rvc_loading_overlay()

        # --- Output & levels card ---
        _lv_card, lv_body, self._lbl_audio_levels_card_h = self._make_audio_card("#0ea5e9")
        self._lbl_audio_output = QLabel()
        self._audio_combo = QComboBox()
        self._audio_combo.currentIndexChanged.connect(self._apply_audio_device_selection)
        self._btn_audio_refresh = QPushButton()
        self._btn_audio_refresh.clicked.connect(self._refresh_audio_devices)
        out_row = QHBoxLayout()
        out_row.setSpacing(8)
        out_row.addWidget(self._audio_combo, stretch=1)
        out_row.addWidget(self._btn_audio_refresh)
        out_wrap = QWidget()
        out_wrap.setLayout(out_row)
        out_form = QFormLayout()
        out_form.setContentsMargins(0, 0, 0, 0)
        out_form.setHorizontalSpacing(10)
        out_form.setVerticalSpacing(8)
        out_form.addRow(self._lbl_audio_output, out_wrap)
        lv_body.addLayout(out_form)

        self._volume_slider = QSlider()
        self._volume_slider.setOrientation(Qt.Orientation.Horizontal)
        self._volume_slider.setRange(0, 100)
        self._volume_slider.setValue(int(self._settings.value("audio/volume", 100)))
        self._volume_slider.valueChanged.connect(self._on_volume_changed)
        self._lbl_audio_volume = QLabel()
        vol_form = QFormLayout()
        vol_form.setContentsMargins(0, 0, 0, 0)
        vol_form.setHorizontalSpacing(10)
        vol_form.setVerticalSpacing(8)
        vol_form.addRow(self._lbl_audio_volume, self._volume_slider)
        lv_body.addLayout(vol_form)

        self._tts_gain_spin = QSpinBox()
        self._tts_gain_spin.setRange(0, 36)
        self._tts_gain_spin.setSuffix(" dB")
        g0 = int(self._settings.value(_SETTINGS_TTS_GAIN_DB, 14))
        self._tts_gain_spin.setValue(max(0, min(36, g0)))
        self._tts_gain_spin.valueChanged.connect(self._on_tts_gain_changed)
        self._lbl_audio_tts_gain = QLabel()
        self._sink.set_tts_gain_db(self._tts_gain_spin.value())
        gain_form = QFormLayout()
        gain_form.setContentsMargins(0, 0, 0, 0)
        gain_form.setHorizontalSpacing(10)
        gain_form.setVerticalSpacing(8)
        gain_form.addRow(self._lbl_audio_tts_gain, self._tts_gain_spin)
        lv_body.addLayout(gain_form)

        main_lay.addWidget(_lv_card)
        main_lay.addStretch(1)

        self._apply_audio_tab_texts()
        scroll.setWidget(inner)
        return scroll

    def _apply_audio_tab_texts(self) -> None:
        self._lbl_audio_output.setText(self._tr("audio.output"))
        self._btn_audio_refresh.setText(self._tr("audio.refresh"))
        self._lbl_tts_lang.setText(self._tr("audio.tts_language"))
        for i in range(self._combo_tts_lang.count()):
            tag = self._combo_tts_lang.itemData(i)
            if isinstance(tag, str):
                key = "tts_lang." + tag.replace("-", "_")
                self._combo_tts_lang.setItemText(i, self._tr(key))
        self._lbl_tts_engine.setText(self._tr("audio.tts_engine"))
        self._combo_tts_engine.setItemText(0, self._tr("audio.tts_engine_google"))
        self._combo_tts_engine.setItemText(1, self._tr("audio.tts_engine_piper"))
        self._btn_piper_help.setToolTip(self._tr("audio.piper_help_tooltip"))
        self._btn_audio_flush_queues.setText(self._tr("audio.flush_queues"))
        self._btn_audio_flush_queues.setToolTip(self._tr("audio.flush_queues_hint"))
        self._lbl_audio_tts_card_h.setText(self._tr("audio.card_tts_title"))
        self._lbl_audio_piper_card_h.setText(self._tr("audio.piper_voice_group"))
        self._frm_piper_voice.setToolTip(
            "\n\n".join(
                [
                    self._tr("audio.piper_voice_intro"),
                    self._tr("audio.piper_option_download"),
                    self._tr("audio.piper_option_file"),
                ],
            ),
        )
        self._btn_piper_download.setText(self._tr("audio.piper_download"))
        self._btn_piper_download.setToolTip(self._tr("audio.piper_option_download"))
        self._piper_browse_lbl.setText(self._tr("audio.piper_path_short"))
        self._btn_piper_browse.setText(self._tr("audio.piper_browse"))
        self._cb_piper_cuda.setText(self._tr("audio.piper_cuda"))
        self._cb_piper_cuda.setToolTip(self._tr("audio.piper_cuda_tip"))
        self._lbl_audio_rvc_card_h.setText(self._tr("audio.rvc_group"))
        self._frm_rvc.setToolTip(self._tr("audio.rvc_intro"))
        self._cb_rvc.setText(self._tr("audio.rvc_enable"))
        self._lbl_rvc_model.setText(self._tr("audio.rvc_model"))
        self._lbl_rvc_index.setText(self._tr("audio.rvc_index"))
        self._cb_rvc_cuda.setText(self._tr("audio.rvc_cuda"))
        self._cb_rvc_cuda.setToolTip(self._tr("audio.rvc_cuda_tip"))
        self._btn_rvc_browse.setText(self._tr("audio.piper_browse"))
        self._btn_rvc_index_browse.setText(self._tr("audio.piper_browse"))
        if (
            hasattr(self, "_lbl_rvc_overlay_status")
            and hasattr(self, "_rvc_overlay")
            and self._rvc_overlay.isVisible()
        ):
            self._lbl_rvc_overlay_status.setText(
                self._tr("audio.rvc_loading")
                if getattr(self, "_rvc_overlay_enabling", True)
                else self._tr("audio.rvc_unloading"),
            )
        self._update_piper_related_visibility()
        self._update_rvc_field_enabled()
        self._lbl_audio_volume.setText(self._tr("audio.volume"))
        self._lbl_audio_tts_gain.setText(self._tr("audio.tts_gain"))
        _gain_help = f"{self._tr('audio.tts_gain_tip')}\n\n{self._tr('audio.tts_hint')}"
        self._tts_gain_spin.setToolTip(_gain_help)
        self._lbl_audio_tts_gain.setToolTip(_gain_help)
        self._volume_slider.setToolTip(self._tr("audio.volume_tip"))
        self._lbl_audio_card_test_h.setText(self._tr("audio.card_test_header"))
        self._lbl_audio_test.setText(self._tr("audio.test"))
        self._btn_audio_speak.setText(self._tr("audio.speak_test"))
        self._lbl_audio_levels_card_h.setText(self._tr("audio.card_levels_title"))
        if not self._test_phrase.text().strip():
            self._test_phrase.setText(self._tr("audio.test_phrase_default"))
        elif self._test_phrase.text().strip() in (
            l10n.tr("uk", "audio.test_phrase_default"),
            l10n.tr("en", "audio.test_phrase_default"),
        ):
            self._test_phrase.setText(self._tr("audio.test_phrase_default"))

    def _update_piper_related_visibility(self) -> None:
        use_piper = self._combo_tts_engine.currentData() == _TTS_ENGINE_PIPER
        self._frm_piper_voice.setVisible(use_piper)
        self._btn_piper_help.setVisible(use_piper)

    def _update_rvc_field_enabled(self) -> None:
        if not hasattr(self, "_cb_rvc"):
            return
        on = self._cb_rvc.isChecked()
        for w in (
            self._lbl_rvc_model,
            self._rvc_model_edit,
            self._btn_rvc_browse,
            self._lbl_rvc_index,
            self._rvc_index_edit,
            self._btn_rvc_index_browse,
            self._cb_rvc_cuda,
        ):
            w.setEnabled(on)

    def _sync_tts_engine_combo_to_backend(self) -> None:
        """Combo reflects saved engine (not live ``self._tts`` — Piper may load later)."""
        raw_eng = str(self._settings.value(_SETTINGS_TTS_ENGINE, _TTS_ENGINE_GOOGLE, str))
        gid = raw_eng.strip().lower()
        self._combo_tts_engine.blockSignals(True)
        self._combo_tts_engine.setCurrentIndex(1 if gid == _TTS_ENGINE_PIPER else 0)
        self._combo_tts_engine.blockSignals(False)
        self._update_piper_related_visibility()

    @Slot(int)
    def _on_tts_engine_changed(self, _index: int) -> None:
        eng = self._combo_tts_engine.currentData()
        self._settings.setValue(_SETTINGS_TTS_ENGINE, eng)
        self._update_piper_related_visibility()
        asyncio.ensure_future(self._swap_tts_backend())

    @Slot()
    def _on_piper_model_commit(self) -> None:
        self._settings.setValue(_SETTINGS_PIPER_MODEL, self._piper_model_edit.text().strip())
        if self._combo_tts_engine.currentData() == _TTS_ENGINE_PIPER:
            asyncio.ensure_future(self._swap_tts_backend())

    @Slot()
    def _browse_piper_model(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            self._tr("audio.piper_model"),
            str(Path.home()),
            "ONNX (*.onnx);;All files (*)",
        )
        if path:
            self._piper_model_edit.setText(path)
            self._settings.setValue(_SETTINGS_PIPER_MODEL, path)
            if self._combo_tts_engine.currentData() == _TTS_ENGINE_PIPER:
                asyncio.ensure_future(self._swap_tts_backend())

    @Slot(int)
    def _on_tts_language_changed(self, _index: int) -> None:
        tag = self._combo_tts_lang.currentData()
        if isinstance(tag, str) and tag.strip():
            self._settings.setValue(_SETTINGS_TTS_LANG, tag.strip())
        if self._combo_tts_engine.currentData() == _TTS_ENGINE_GOOGLE:
            asyncio.ensure_future(self._swap_tts_backend())

    @Slot(bool)
    def _on_piper_cuda_toggled(self, checked: bool) -> None:
        self._settings.setValue(_SETTINGS_PIPER_CUDA, bool(checked))
        if self._combo_tts_engine.currentData() == _TTS_ENGINE_PIPER:
            asyncio.ensure_future(self._swap_tts_backend())

    @Slot(bool)
    def _on_rvc_toggled(self, checked: bool) -> None:
        if checked:
            from stream_cheremsha.tts.rvc_wav import is_rvc_stack_available, rvc_stack_import_error

            if not is_rvc_stack_available():
                self._cb_rvc.blockSignals(True)
                self._cb_rvc.setChecked(False)
                self._cb_rvc.blockSignals(False)
                self._update_rvc_field_enabled()
                detail = rvc_stack_import_error()
                msg = (
                    self._tr("dlg.rvc_missing_detail", detail=detail)
                    if detail
                    else self._tr("dlg.rvc_missing")
                )
                QMessageBox.information(self, self._tr("dlg.tts"), msg)
                return
        asyncio.ensure_future(self._async_rvc_toggle_apply(checked))

    def _setup_rvc_loading_overlay(self) -> None:
        self._rvc_overlay = QFrame(self._frm_rvc)
        self._rvc_overlay.setObjectName("rvcLoadingOverlay")
        self._rvc_overlay.hide()
        ol = QVBoxLayout(self._rvc_overlay)
        ol.setContentsMargins(16, 16, 16, 16)
        ol.addStretch(1)
        mid = QHBoxLayout()
        mid.addStretch(1)
        col = QVBoxLayout()
        col.setSpacing(12)
        pulse_path = _asset_path("pulse.svg")
        self._rvc_overlay_pulse = QSvgWidget(str(pulse_path))
        self._rvc_overlay_pulse.setObjectName("rvcOverlayPulse")
        self._rvc_overlay_pulse.setFixedSize(46, 46)
        self._lbl_rvc_overlay_status = QLabel()
        self._lbl_rvc_overlay_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_rvc_overlay_status.setWordWrap(True)
        self._lbl_rvc_overlay_status.setObjectName("rvcOverlayStatus")

        self._rvc_overlay_pulse_anim = QVariantAnimation(self)
        self._rvc_overlay_pulse_anim.setDuration(900)
        self._rvc_overlay_pulse_anim.setLoopCount(-1)
        self._rvc_overlay_pulse_anim.setStartValue(0.55)
        self._rvc_overlay_pulse_anim.setEndValue(1.15)

        def _apply_pulse(v: object) -> None:
            try:
                x = float(v)
            except (TypeError, ValueError):
                x = 1.0
            size = int(46 * x)
            size = max(22, min(size, 90))
            self._rvc_overlay_pulse.setFixedSize(size, size)
            a = 1.0 - (x - 0.55) / (1.15 - 0.55)
            a = max(0.0, min(a, 1.0))
            self._rvc_overlay_pulse.setStyleSheet(
                f"color: rgba(232, 234, 237, {a:.3f});",
            )

        self._rvc_overlay_pulse_anim.valueChanged.connect(_apply_pulse)
        _apply_pulse(self._rvc_overlay_pulse_anim.startValue())

        col.addWidget(self._rvc_overlay_pulse, alignment=Qt.AlignmentFlag.AlignHCenter)
        col.addWidget(self._lbl_rvc_overlay_status)
        mid.addLayout(col)
        mid.addStretch(1)
        ol.addLayout(mid)
        ol.addStretch(1)
        self._rvc_overlay.setStyleSheet(
            "QFrame#rvcLoadingOverlay { background-color: rgba(10, 12, 18, 0.82); "
            "border-radius: 14px; }"
            "QLabel#rvcOverlayStatus { color: #e8eaed; font-weight: 600; }",
        )
        self._frm_rvc.installEventFilter(self)

    def _setup_piper_loading_overlay(self) -> None:
        self._piper_overlay = QFrame(self._frm_piper_voice)
        self._piper_overlay.setObjectName("piperLoadingOverlay")
        self._piper_overlay.hide()
        ol = QVBoxLayout(self._piper_overlay)
        ol.setContentsMargins(16, 16, 16, 16)
        ol.addStretch(1)
        mid = QHBoxLayout()
        mid.addStretch(1)
        col = QVBoxLayout()
        col.setSpacing(12)
        pulse_path = _asset_path("pulse.svg")
        self._piper_overlay_pulse = QSvgWidget(str(pulse_path))
        self._piper_overlay_pulse.setObjectName("piperOverlayPulse")
        self._piper_overlay_pulse.setFixedSize(46, 46)
        self._lbl_piper_overlay_status = QLabel()
        self._lbl_piper_overlay_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_piper_overlay_status.setWordWrap(True)
        self._lbl_piper_overlay_status.setObjectName("piperOverlayStatus")

        self._piper_overlay_pulse_anim = QVariantAnimation(self)
        self._piper_overlay_pulse_anim.setDuration(900)
        self._piper_overlay_pulse_anim.setLoopCount(-1)
        self._piper_overlay_pulse_anim.setStartValue(0.55)
        self._piper_overlay_pulse_anim.setEndValue(1.15)

        def _apply_pulse(v: object) -> None:
            try:
                x = float(v)
            except (TypeError, ValueError):
                x = 1.0
            size = int(46 * x)
            size = max(22, min(size, 90))
            self._piper_overlay_pulse.setFixedSize(size, size)
            a = 1.0 - (x - 0.55) / (1.15 - 0.55)
            a = max(0.0, min(a, 1.0))
            self._piper_overlay_pulse.setStyleSheet(
                f"color: rgba(232, 234, 237, {a:.3f});",
            )

        self._piper_overlay_pulse_anim.valueChanged.connect(_apply_pulse)
        _apply_pulse(self._piper_overlay_pulse_anim.startValue())

        col.addWidget(self._piper_overlay_pulse, alignment=Qt.AlignmentFlag.AlignHCenter)
        col.addWidget(self._lbl_piper_overlay_status)
        mid.addLayout(col)
        mid.addStretch(1)
        ol.addLayout(mid)
        ol.addStretch(1)
        self._piper_overlay.setStyleSheet(
            "QFrame#piperLoadingOverlay { background-color: rgba(10, 12, 18, 0.82); "
            "border-radius: 14px; }"
            "QLabel#piperOverlayStatus { color: #e8eaed; font-weight: 600; }",
        )
        self._frm_piper_voice.installEventFilter(self)

    def _sync_piper_overlay_geometry(self) -> None:
        if hasattr(self, "_piper_overlay"):
            self._piper_overlay.setGeometry(self._frm_piper_voice.rect())

    def _sync_rvc_overlay_geometry(self) -> None:
        if hasattr(self, "_rvc_overlay"):
            self._rvc_overlay.setGeometry(self._frm_rvc.rect())

    def eventFilter(self, watched: QObject, event: QEvent | None) -> bool:  # noqa: N802
        if (
            watched is getattr(self, "_frm_rvc", None)
            and event is not None
            and event.type() == QEvent.Type.Resize
            and hasattr(self, "_rvc_overlay")
        ):
            self._rvc_overlay.setGeometry(self._frm_rvc.rect())
        if (
            watched is getattr(self, "_frm_piper_voice", None)
            and event is not None
            and event.type() == QEvent.Type.Resize
            and hasattr(self, "_piper_overlay")
        ):
            self._piper_overlay.setGeometry(self._frm_piper_voice.rect())
        return super().eventFilter(watched, event)

    async def _async_rvc_toggle_apply(self, checked: bool) -> None:
        if self._rvc_toggle_busy:
            return
        from stream_cheremsha.tts.rvc_wav import RvcChainRebuildParams, rvc_rebuild_chain

        self._rvc_toggle_busy = True
        self._rvc_overlay_enabling = bool(checked)
        self._lbl_rvc_overlay_status.setText(
            self._tr("audio.rvc_loading") if checked else self._tr("audio.rvc_unloading"),
        )
        self._sync_rvc_overlay_geometry()
        self._rvc_overlay_pulse_anim.start()
        self._rvc_overlay.show()
        self._rvc_overlay.raise_()
        self._cb_rvc.setEnabled(False)
        try:
            await rvc_runtime_stop_dispatcher(self._rvc_runtime)
            rvc_runtime_cancel_pending(
                self._rvc_runtime,
                RuntimeError("RVC is restarting"),
            )
            self._migrate_rvc_from_legacy_if_needed()
            self._settings.setValue(_SETTINGS_RVC_ENABLED, bool(checked))
            params = RvcChainRebuildParams(
                enabled=bool(checked),
                model_pth=str(self._settings.value(_SETTINGS_RVC_MODEL, "", str)).strip(),
                index_path=str(self._settings.value(_SETTINGS_RVC_INDEX, "", str)).strip(),
                use_cuda=bool(self._settings.value(_SETTINGS_RVC_CUDA, False, bool)),
            )
            prev = self._rvc_runtime.chain
            self._rvc_runtime.chain = None
            try:
                new_chain, err = await asyncio.to_thread(rvc_rebuild_chain, prev, params)
            except Exception as e:
                logger.exception("RVC toggle (worker thread)")
                try:
                    if prev is not None:
                        prev.close()
                except Exception:
                    logger.exception("RVC: cleanup after toggle failure")
                self._settings.setValue(_SETTINGS_RVC_ENABLED, not bool(checked))
                self._cb_rvc.blockSignals(True)
                self._cb_rvc.setChecked(not bool(checked))
                self._cb_rvc.blockSignals(False)
                QMessageBox.warning(
                    self,
                    self._tr("dlg.tts"),
                    self._tr("dlg.rvc_toggle_failed", detail=str(e)),
                )
                self._rebuild_rvc_chain()
            else:
                self._rvc_runtime.chain = new_chain
                if err is not None:
                    self._settings.setValue(_SETTINGS_RVC_ENABLED, not bool(checked))
                    self._cb_rvc.blockSignals(True)
                    self._cb_rvc.setChecked(not bool(checked))
                    self._cb_rvc.blockSignals(False)
                    QMessageBox.warning(
                        self,
                        self._tr("dlg.tts"),
                        self._tr("dlg.rvc_toggle_failed", detail=str(err)),
                    )
            self._update_rvc_field_enabled()
        finally:
            self._rvc_overlay.hide()
            self._rvc_overlay_pulse_anim.stop()
            self._cb_rvc.setEnabled(True)
            self._rvc_toggle_busy = False

    @Slot(bool)
    def _on_rvc_cuda_toggled(self, checked: bool) -> None:
        self._settings.setValue(_SETTINGS_RVC_CUDA, bool(checked))
        if bool(self._settings.value(_SETTINGS_RVC_ENABLED, False, bool)):
            self._rebuild_rvc_chain()

    @Slot()
    def _on_rvc_model_commit(self) -> None:
        self._settings.setValue(_SETTINGS_RVC_MODEL, self._rvc_model_edit.text().strip())
        if bool(self._settings.value(_SETTINGS_RVC_ENABLED, False, bool)):
            self._rebuild_rvc_chain()

    @Slot()
    def _on_rvc_index_commit(self) -> None:
        self._settings.setValue(_SETTINGS_RVC_INDEX, self._rvc_index_edit.text().strip())
        if bool(self._settings.value(_SETTINGS_RVC_ENABLED, False, bool)):
            self._rebuild_rvc_chain()

    @Slot()
    def _browse_rvc_model(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            self._tr("audio.rvc_model"),
            str(Path.home()),
            "PyTorch (*.pth);;All files (*)",
        )
        if path:
            self._rvc_model_edit.setText(path)
            self._settings.setValue(_SETTINGS_RVC_MODEL, path)
            if bool(self._settings.value(_SETTINGS_RVC_ENABLED, False, bool)):
                self._rebuild_rvc_chain()

    @Slot()
    def _browse_rvc_index(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            self._tr("audio.rvc_index"),
            str(Path.home()),
            "RVC index (*.index);;All files (*)",
        )
        if path:
            self._rvc_index_edit.setText(path)
            self._settings.setValue(_SETTINGS_RVC_INDEX, path)
            if bool(self._settings.value(_SETTINGS_RVC_ENABLED, False, bool)):
                self._rebuild_rvc_chain()

    @Slot()
    def _show_piper_help_dialog(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle(self._tr("audio.piper_help_title"))
        layout = QVBoxLayout(dlg)
        browser = QTextBrowser()
        browser.setReadOnly(True)
        browser.setOpenExternalLinks(True)
        browser.setHtml(self._tr("help.piper_html"))
        layout.addWidget(browser)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(dlg.accept)
        layout.addWidget(buttons)
        if not restore_window_geometry(KEY_PIPER_HELP_DIALOG, dlg):
            dlg.resize(560, 440)

        def _save_piper_help_geometry() -> None:
            save_window_geometry(KEY_PIPER_HELP_DIALOG, dlg)

        dlg.finished.connect(_save_piper_help_geometry)
        dlg.exec()

    @Slot()
    def _schedule_piper_voice_download(self) -> None:
        asyncio.ensure_future(self._run_piper_voice_download())

    async def _run_piper_voice_download(self) -> None:
        from stream_cheremsha.tts.piper_download import download_piper_voice
        from stream_cheremsha.tts.piper_voices import (
            default_piper_download_root,
            piper_voice_id_for_tts_language,
        )

        lang = self._current_tts_language()
        voice = piper_voice_id_for_tts_language(lang)
        if not voice:
            QMessageBox.information(
                self,
                self._tr("dlg.tts"),
                self._tr("dlg.piper_voice_unknown"),
            )
            return
        self._lbl_piper_overlay_status.setText(self._tr("audio.piper_downloading"))
        self._sync_piper_overlay_geometry()
        self._piper_overlay_pulse_anim.start()
        self._piper_overlay.show()
        self._piper_overlay.raise_()
        self._btn_piper_download.setEnabled(False)
        self._piper_model_edit.setEnabled(False)
        self._btn_piper_browse.setEnabled(False)
        self._cb_piper_cuda.setEnabled(False)
        self._on_user_status(self._tr("status.piper_download_start", voice=voice))
        cache = default_piper_download_root()
        try:
            onnx = await download_piper_voice(voice, cache)
        except (OSError, RuntimeError) as e:
            QMessageBox.warning(self, self._tr("dlg.piper_download_failed"), str(e))
            return
        finally:
            self._piper_overlay.hide()
            self._piper_overlay_pulse_anim.stop()
            self._btn_piper_download.setEnabled(True)
            self._piper_model_edit.setEnabled(True)
            self._btn_piper_browse.setEnabled(True)
            self._cb_piper_cuda.setEnabled(True)
        self._piper_model_edit.setText(str(onnx))
        self._settings.setValue(_SETTINGS_PIPER_MODEL, str(onnx))
        self._on_user_status(self._tr("status.piper_download_ok", path=str(onnx)))
        if self._combo_tts_engine.currentData() == _TTS_ENGINE_PIPER:
            await self._swap_tts_backend()

    async def _swap_tts_backend(self) -> None:
        from stream_cheremsha.tts.bundled_piper import effective_piper_onnx_path
        from stream_cheremsha.tts.google_translate_tts import GoogleTranslateTts
        from stream_cheremsha.tts.piper_tts import PiperTts, is_piper_package_installed

        eng = self._combo_tts_engine.currentData()
        new_tts: TextToSpeech

        def _revert_to_google_combo() -> None:
            self._combo_tts_engine.blockSignals(True)
            self._combo_tts_engine.setCurrentIndex(0)
            self._combo_tts_engine.blockSignals(False)
            self._settings.setValue(_SETTINGS_TTS_ENGINE, _TTS_ENGINE_GOOGLE)
            self._update_piper_related_visibility()

        lang = self._current_tts_language()
        use_cuda = self._cb_piper_cuda.isChecked() if hasattr(self, "_cb_piper_cuda") else False

        if eng == _TTS_ENGINE_PIPER:
            raw = self._piper_model_edit.text()
            eff = effective_piper_onnx_path(raw, lang)
            if eff is not None and raw.strip() != str(eff):
                self._piper_model_edit.setText(str(eff))
                self._settings.setValue(_SETTINGS_PIPER_MODEL, str(eff))
            path = str(eff) if eff is not None else ""
            file_ok = bool(path) and Path(path).expanduser().is_file()
            if not file_ok:
                self._on_user_status(self._tr("status.piper_need_model"))
                new_tts = GoogleTranslateTts(language=lang)
            elif not is_piper_package_installed():
                QMessageBox.warning(
                    self,
                    self._tr("dlg.tts"),
                    self._tr("dlg.piper_not_installed"),
                )
                _revert_to_google_combo()
                new_tts = GoogleTranslateTts(language=lang)
            else:
                try:
                    new_tts = PiperTts(path, use_cuda=use_cuda)
                except (ImportError, ValueError, OSError) as e:
                    QMessageBox.warning(self, self._tr("dlg.tts"), str(e))
                    _revert_to_google_combo()
                    new_tts = GoogleTranslateTts(language=lang)
        else:
            new_tts = GoogleTranslateTts(language=lang)

        old = self._tts
        oid = getattr(old, "ENGINE_ID", "")
        nid = getattr(new_tts, "ENGINE_ID", "")
        if oid == nid == _TTS_ENGINE_GOOGLE:
            old_lang = getattr(old, "language", None)
            new_lang = getattr(new_tts, "language", None)
            if old_lang == new_lang:
                return
        if oid == nid == _TTS_ENGINE_PIPER:
            if (
                getattr(old, "model_path", None) == getattr(new_tts, "model_path", None)
                and getattr(old, "use_cuda", False) == getattr(new_tts, "use_cuda", False)
            ):
                return

        self._coordinator.set_tts(new_tts)
        self._tts = new_tts
        await old.aclose()

    def _load_settings_fields(self) -> None:
        env_cid = os.environ.get(constants.ENV_TWITCH_CLIENT_ID, "").strip()
        cid = env_cid or (keyring_store.get_password(constants.KEY_TWITCH_CLIENT_ID) or "")
        if cid.strip():
            self._twitch_client_id.setText(cid.strip())
        sec = keyring_store.get_password(constants.KEY_TWITCH_CLIENT_SECRET)
        if sec:
            self._twitch_client_secret.setText(sec)
        ch = keyring_store.get_password(constants.KEY_TWITCH_CHANNEL)
        if ch:
            self._twitch_channel.setText(ch)
        tk = keyring_store.get_password(constants.KEY_TIKTOK_USERNAME)
        if tk:
            self._tiktok_username.setText(tk.strip())
        tok = keyring_store.get_password(constants.KEY_TWITCH_TOKEN)
        if tok:
            self._twitch_token.setText(tok)

        self._cb_autostart_twitch.blockSignals(True)
        self._cb_autostart_twitch.setChecked(
            bool(self._settings.value(_SETTINGS_AUTOSTART_TWITCH, False, bool)),
        )
        self._cb_autostart_twitch.blockSignals(False)
        self._cb_autostart_youtube.blockSignals(True)
        self._cb_autostart_youtube.setChecked(
            bool(self._settings.value(_SETTINGS_AUTOSTART_YOUTUBE, False, bool)),
        )
        self._cb_autostart_youtube.blockSignals(False)

        if hasattr(self, "_cb_game_mode"):
            self._cb_game_mode.blockSignals(True)
            self._cb_game_mode.setChecked(bool(self._settings.value(_SETTINGS_GAME_MODE, False, bool)))
            self._cb_game_mode.blockSignals(False)

        self._combo_locale.blockSignals(True)
        idx = 0 if self._locale == "uk" else 1
        self._combo_locale.setCurrentIndex(idx)
        self._combo_locale.blockSignals(False)

        if hasattr(self, "_combo_tts_lang"):
            want_lang = self._tts_language_from_settings()
            self._combo_tts_lang.blockSignals(True)
            lang_idx = 0
            for j in range(self._combo_tts_lang.count()):
                if self._combo_tts_lang.itemData(j) == want_lang:
                    lang_idx = j
                    break
            self._combo_tts_lang.setCurrentIndex(lang_idx)
            self._combo_tts_lang.blockSignals(False)

        if hasattr(self, "_cb_piper_cuda"):
            self._cb_piper_cuda.blockSignals(True)
            cuda_on = bool(self._settings.value(_SETTINGS_PIPER_CUDA, False, bool))
            self._cb_piper_cuda.setChecked(cuda_on)
            self._cb_piper_cuda.blockSignals(False)

        if hasattr(self, "_combo_tts_engine"):
            from stream_cheremsha.tts.bundled_piper import effective_piper_onnx_path

            raw = str(self._settings.value(_SETTINGS_PIPER_MODEL, "", str))
            want_lang = self._tts_language_from_settings()
            eff = effective_piper_onnx_path(raw, want_lang)
            if eff is not None and raw.strip() != str(eff):
                self._settings.setValue(_SETTINGS_PIPER_MODEL, str(eff))
            pm = str(eff) if eff is not None else raw.strip()
            self._piper_model_edit.blockSignals(True)
            self._piper_model_edit.setText(pm)
            self._piper_model_edit.blockSignals(False)
            self._sync_tts_engine_combo_to_backend()

        if hasattr(self, "_tts_gain_spin"):
            gv = int(self._settings.value(_SETTINGS_TTS_GAIN_DB, 14))
            self._tts_gain_spin.blockSignals(True)
            self._tts_gain_spin.setValue(max(0, min(36, gv)))
            self._tts_gain_spin.blockSignals(False)
            self._sink.set_tts_gain_db(self._tts_gain_spin.value())

        if hasattr(self, "_cb_rvc"):
            self._migrate_rvc_from_legacy_if_needed()
            self._cb_rvc.blockSignals(True)
            self._cb_rvc.setChecked(bool(self._settings.value(_SETTINGS_RVC_ENABLED, False, bool)))
            self._cb_rvc.blockSignals(False)
            self._rvc_model_edit.blockSignals(True)
            self._rvc_model_edit.setText(str(self._settings.value(_SETTINGS_RVC_MODEL, "", str)))
            self._rvc_model_edit.blockSignals(False)
            self._rvc_index_edit.blockSignals(True)
            self._rvc_index_edit.setText(str(self._settings.value(_SETTINGS_RVC_INDEX, "", str)))
            self._rvc_index_edit.blockSignals(False)
            self._cb_rvc_cuda.blockSignals(True)
            rvc_cuda = bool(self._settings.value(_SETTINGS_RVC_CUDA, False, bool))
            self._cb_rvc_cuda.setChecked(rvc_cuda)
            self._cb_rvc_cuda.blockSignals(False)
            self._update_rvc_field_enabled()
        self._load_chat_font_from_settings()
        self._rebuild_rvc_chain()

    @Slot(int)
    def _on_tts_gain_changed(self, value: int) -> None:
        self._settings.setValue(_SETTINGS_TTS_GAIN_DB, value)
        self._sink.set_tts_gain_db(value)

    @Slot(int)
    def _persist_autostart_twitch(self, _state: int) -> None:
        self._settings.setValue(_SETTINGS_AUTOSTART_TWITCH, self._cb_autostart_twitch.isChecked())

    @Slot(int)
    def _persist_autostart_youtube(self, _state: int) -> None:
        self._settings.setValue(
            _SETTINGS_AUTOSTART_YOUTUBE,
            self._cb_autostart_youtube.isChecked(),
        )

    @Slot()
    def _schedule_twitch_browser_login(self) -> None:
        asyncio.ensure_future(self._twitch_browser_login())

    def _on_user_status(self, msg: str) -> None:
        self._apply_status_routes(msg.strip())
        self._refresh_footer()
        # QML bindings (Connections/Actions) are keyed off api.refreshCounter.
        # Refresh only when something meaningful changes (status text etc.),
        # not on a periodic timer, to avoid GPU/CPU wakeups while idle.
        self._qml_refresh_if_visible()
        self._bridge.append_log.emit(f"[status] {msg}")

    def _qml_refresh_if_visible(self) -> None:
        """Refresh QML bindings only when QML views are visible."""
        if not hasattr(self, "_qml_api"):
            return
        # QStackedWidget hides non-current pages, so isVisible() is a good proxy.
        if getattr(self, "_qml_conn", None) is not None and self._qml_conn.isVisible():
            self._qml_api.refresh()
            return
        if getattr(self, "_qml_donations", None) is not None and self._qml_donations.isVisible():
            self._qml_api.refresh()
            return
        # Separate Actions window is a QQuickView (not in the stack).
        if getattr(self, "_qml_actions", None) is not None and self._qml_actions.isVisible():
            self._qml_api.refresh()

    def _apply_status_routes(self, msg: str) -> None:
        """Keep separate footer lines so Twitch and YouTube statuses are not overwritten."""
        if msg.startswith(("Twitch:", "Twitch error")):
            rest = (
                msg.removeprefix("Twitch:")
                .removeprefix("Twitch error")
                .strip()
                .lstrip(":")
                .strip()
            )
            self._status_twitch = rest if rest else msg
            return
        if msg.startswith(("YouTube:", "YouTube HTTP", "YouTube API", "YouTube error")):
            for prefix in (
                "YouTube API",
                "YouTube HTTP error",
                "YouTube HTTP",
                "YouTube error",
                "YouTube:",
            ):
                if msg.startswith(prefix):
                    self._status_youtube = msg[len(prefix):].strip(" :") or msg
                    return
            self._status_youtube = msg.removeprefix("YouTube:").strip() or msg
            return
        if msg.startswith(("TikTok:", "TikTok error")):
            rest = (
                msg.removeprefix("TikTok:")
                .removeprefix("TikTok error")
                .strip()
                .lstrip(":")
                .strip()
            )
            self._status_tiktok = rest if rest else msg
            return
        if msg in l10n.all_locale_strings_many("status.logout_twitch", "status.twitch_keys_saved"):
            self._status_twitch = msg
            return
        if msg in l10n.all_locale_strings_many("status.logout_youtube"):
            self._status_youtube = msg
            return
        self._status_app = msg

    @Slot(str)
    def _append_log_line(self, line: str) -> None:
        self._log_view.append(line)
        doc = self._log_view.document()
        while doc.blockCount() > _MAX_LOG_DOCUMENT_BLOCKS:
            c = QTextCursor(doc)
            c.movePosition(QTextCursor.MoveOperation.Start)
            c.select(QTextCursor.SelectionType.BlockUnderCursor)
            c.removeSelectedText()
            c.deleteChar()

    @Slot()
    def _refresh_footer(self) -> None:
        cq = self._coordinator.chat_in.qsize()
        tq = self._coordinator.tts_jobs.qsize()
        rq = rvc_runtime_queue_size(self._rvc_runtime)
        e = html.escape
        tw_on = self._tr("footer.on") if self._twitch.running else self._tr("footer.off")
        yt_on = self._tr("footer.on") if self._youtube.running else self._tr("footer.off")
        tk_on = self._tr("footer.on") if self._tiktok.running else self._tr("footer.off")
        tw_c = "#34d399" if self._twitch.running else "#fb923c"
        yt_c = "#34d399" if self._youtube.running else "#fb923c"
        tk_c = "#34d399" if self._tiktok.running else "#fb923c"
        pl = e(self._tr("footer.pipeline"))
        ftw = e(self._tr("footer.twitch"))
        fyt = e(self._tr("footer.youtube"))
        ftk = e(self._tr("footer.tiktok"))
        fq = e(self._tr("footer.queues"))
        fchat = e(self._tr("footer.chat"))
        ftts = e(self._tr("footer.tts"))
        frvc = e(self._tr("footer.rvc"))
        h1 = (
            f'<span style="color:#4ade80">●</span> <span style="color:#cbd5e1;">{pl}:'
            f'</span> <span style="color:#f1f5f9;">{e(self._status_app)}</span>'
        )
        tw_ico = _footer_richtext_img("twitch.svg", 15)
        yt_ico = _footer_richtext_img("youtube.svg", 15)
        tk_ico = _footer_richtext_img("tiktok.svg", 15)
        h2 = (
            f'{tw_ico}<span style="color:{tw_c}">●</span> <span style="color:#cbd5e1;">{ftw}'
            f'</span> <span style="color:#94a3b8;">({e(tw_on)}):</span> '
            f'<span style="color:#e2e8f0;">{e(self._status_twitch)}</span>'
        )
        h3 = (
            f'{yt_ico}<span style="color:{yt_c}">●</span> <span style="color:#cbd5e1;">{fyt}'
            f'</span> <span style="color:#94a3b8;">({e(yt_on)}):</span> '
            f'<span style="color:#e2e8f0;">{e(self._status_youtube)}</span>'
        )
        h4 = (
            f'{tk_ico}<span style="color:{tk_c}">●</span> <span style="color:#cbd5e1;">{ftk}'
            f'</span> <span style="color:#94a3b8;">({e(tk_on)}):</span> '
            f'<span style="color:#e2e8f0;">{e(self._status_tiktok)}</span>'
        )
        h5 = (
            f'<span style="color:#94a3b8;">{fq}: {fchat}={cq} &nbsp; {ftts}={tq}'
            f" &nbsp; {frvc}={rq}</span>"
        )
        self._status_label.setText(f"{h1}<br/>{h2}<br/>{h3}<br/>{h4}<br/>{h5}")
        tw_btn = "tw.transport_stop" if self._twitch.running else "tw.transport_start"
        yt_btn = "yt.transport_stop" if self._youtube.running else "yt.transport_start"
        self._btn_twitch_transport.setText(self._tr(tw_btn))
        self._btn_youtube_transport.setText(self._tr(yt_btn))

    @Slot()
    def _on_tiktok_transport_clicked(self) -> None:
        self._qml_refresh_if_visible()
        asyncio.ensure_future(self._async_set_tiktok_enabled(not self._tiktok_enabled))

    def _request_tiktok_enabled(self, enabled: bool) -> None:
        self._qml_refresh_if_visible()
        asyncio.ensure_future(self._async_set_tiktok_enabled(bool(enabled)))

    async def _async_set_tiktok_enabled(self, enabled: bool) -> None:
        if self._tiktok_toggle_busy:
            return
        if bool(enabled) == bool(self._tiktok_enabled):
            return
        self._tiktok_toggle_busy = True
        try:
            self._tiktok_enabled = bool(enabled)
            if self._tiktok_enabled:
                await self._start_tiktok()
            else:
                await self._tiktok.stop()
        finally:
            self._tiktok_toggle_busy = False
            self._qml_refresh_if_visible()

    @Slot()
    def _on_twitch_transport_clicked(self) -> None:
        self._qml_refresh_if_visible()
        if self._twitch.running:
            asyncio.ensure_future(self._twitch.stop())
        else:
            asyncio.ensure_future(self._start_twitch())

    @Slot()
    def _on_youtube_transport_clicked(self) -> None:
        self._qml_refresh_if_visible()
        if self._youtube.running:
            asyncio.ensure_future(self._youtube.stop())
        else:
            asyncio.ensure_future(self._start_youtube())

    @Slot(str)
    def _append_chat(self, html_fragment: str) -> None:
        doc = self._chat_view.document()
        cursor = self._chat_view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        # insertHtml+several <p> in separate calls often merges into one line in QTextEdit.
        if not doc.isEmpty():
            cursor.insertBlock()
        cursor.insertHtml(html_fragment)
        self._chat_view.setTextCursor(cursor)
        sb = self._chat_view.verticalScrollBar()
        sb.setValue(sb.maximum())
        doc = self._chat_view.document()
        while doc.blockCount() > _MAX_CHAT_DOCUMENT_BLOCKS:
            c = QTextCursor(doc)
            c.movePosition(QTextCursor.MoveOperation.Start)
            c.select(QTextCursor.SelectionType.BlockUnderCursor)
            c.removeSelectedText()
            c.deleteChar()
            # Deque popleft happens in _on_chat_message on append; matches this doc trim.

    def _on_chat_message(self, message: ChatMessage) -> None:
        self._chat_message_history.append(message)
        fragment = self._format_chat_message_fragment(message)
        self._bridge.append_chat.emit(fragment)
        if not self._closing:
            t = asyncio.create_task(
                self._overlay_server.pubsub().publish(
                    "overlay:chat:main",
                    chat_message_to_patch(message),
                ),
            )
            # Ensure exceptions are retrieved to avoid "Task exception was never retrieved".
            t.add_done_callback(lambda _t: _t.exception())
        self._dispatch_actions_for_chat(message)

    def _actions_scope_key(self, platform: str, account_key: str) -> tuple[str, str]:
        return (platform.strip().lower(), account_key.strip())

    def _actions_account_key_for_platform(self, platform: ChatPlatform) -> str | None:
        if platform == ChatPlatform.TIKTOK:
            return constants.TIKTOK_ACTIONS_ACCOUNT_KEY
        if platform == ChatPlatform.TWITCH:
            v = (self._twitch_channel.text() or "").strip()
            return v or None
        if platform == ChatPlatform.YOUTUBE:
            v = (self._yt_video.text() or "").strip()
            return v or None
        return None

    def _maybe_migrate_tiktok_actions(self) -> None:
        """If the app-wide TikTok rules key is unset, copy from legacy .../tiktok/<nick>/."""
        if actions_rules_key_is_set("tiktok", constants.TIKTOK_ACTIONS_ACCOUNT_KEY):
            return
        user = (self._tiktok_username.text() or "").strip().lstrip("@").strip()
        if not user:
            t = keyring_store.get_password(constants.KEY_TIKTOK_USERNAME)
            user = (t or "").strip().lstrip("@").strip() if t else ""
        if not user or user == constants.TIKTOK_ACTIONS_ACCOUNT_KEY:
            return
        old = load_rules("tiktok", user)
        if not old:
            return
        save_rules("tiktok", constants.TIKTOK_ACTIONS_ACCOUNT_KEY, old)
        self._actions_reload_scope("tiktok", constants.TIKTOK_ACTIONS_ACCOUNT_KEY)

    def _get_actions_engine(self, platform: str, account_key: str) -> PlatformActionsEngine:
        p, a = self._actions_scope_key(platform, account_key)
        if p == "tiktok" and a == constants.TIKTOK_ACTIONS_ACCOUNT_KEY:
            self._maybe_migrate_tiktok_actions()
        k = (p, a)
        eng = self._actions_engines.get(k)
        if eng is None:
            eng = PlatformActionsEngine(
                self._sink,
                load_rules(k[0], k[1]),
                status_callback=self._on_user_status,
                tts_speak=self.speak_action_tts,
            )
            self._actions_engines[k] = eng
        return eng

    def _actions_reload_scope(self, platform: str, account_key: str) -> None:
        k = self._actions_scope_key(platform, account_key)
        eng = self._actions_engines.get(k)
        if eng is not None:
            eng.set_rules(load_rules(k[0], k[1]))

    def _dispatch_actions_for_chat(self, message: ChatMessage) -> None:
        ak = self._actions_account_key_for_platform(message.platform)
        if not ak:
            return
        eng = self._get_actions_engine(message.platform.value, ak)
        ev = ChatMessageEvent(
            platform=message.platform,
            author=message.author,
            text=message.text,
            received_at=message.received_at,
        )
        asyncio.ensure_future(eng.on_chat_message(ev))

    def _on_tiktok_gift(self, sender: str, gift_id: str, gift_name: str, count: int) -> None:
        logger.info(
            "TikTok gift dispatch: sender=%s gift_id=%s gift_name=%s count=%s enabled=%s user=%s",
            sender,
            gift_id,
            gift_name,
            count,
            self._tiktok_enabled,
            (self._tiktok_username.text() or "").strip(),
        )
        eng = self._get_actions_engine(
            ChatPlatform.TIKTOK.value,
            constants.TIKTOK_ACTIONS_ACCOUNT_KEY,
        )
        ev = GiftReceivedEvent(
            platform=ChatPlatform.TIKTOK,
            sender=sender,
            gift_id=gift_id,
            gift_name=gift_name,
            count=count,
            received_at=datetime.now(UTC),
        )
        asyncio.ensure_future(eng.on_gift_received(ev))

    def _ensure_actions_window(self) -> QQuickView:
        # Re-create on each open so QML reloads cleanly (avoids stale bindings during development,
        # and simplifies ensuring fresh model state per platform/account_key).
        if self._qml_actions is not None:
            try:
                self._qml_actions.close()
            except RuntimeError:
                pass
            self._qml_actions = None
        view = QQuickView()
        # Helper/auxiliary window: only close, no minimize/maximize, tied to the main window.
        view.setFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowCloseButtonHint,
        )
        try:
            # Keep it associated with the main window so it doesn't randomly de-focus/minimize.
            if self.windowHandle() is not None:
                view.setTransientParent(self.windowHandle())
        except RuntimeError:
            pass
        # Let the window drive the QML root size (adaptive on resize).
        view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        view.setMinimumSize(QSize(760, 520))
        # Initial size; user can resize freely.
        view.resize(QSize(980, 620))
        ctx = view.engine().rootContext()
        # Reuse main API for localization.
        ctx.setContextProperty("api", self._qml_api)
        ctx.setContextProperty("actApi", self._actions_qml_api)
        qml_p = _qml_path("ActionsView.qml")
        view.setSource(QUrl.fromLocalFile(str(qml_p)))
        self._qml_actions = view
        return view

    def _open_tiktok_actions(self) -> None:
        v = self._ensure_actions_window()
        root = v.rootObject()
        if root is not None:
            root.setProperty("platform", "tiktok")
            root.setProperty("accountKey", constants.TIKTOK_ACTIONS_ACCOUNT_KEY)
        v.setTitle(self._tr("actions.window_title"))
        v.show()
        if _should_activate_window():
            v.raise_()

    @Slot()
    def _save_twitch_keys(self) -> None:
        token = self._twitch_token.text().strip()
        cid = self._twitch_client_id.text().strip()
        sec = self._twitch_client_secret.text().strip()
        ch = self._twitch_channel.text().strip()
        try:
            if token:
                keyring_store.set_password(constants.KEY_TWITCH_TOKEN, token)
            if cid:
                keyring_store.set_password(constants.KEY_TWITCH_CLIENT_ID, cid)
            if sec:
                keyring_store.set_password(constants.KEY_TWITCH_CLIENT_SECRET, sec)
            else:
                keyring_store.delete_password(constants.KEY_TWITCH_CLIENT_SECRET)
            if ch:
                keyring_store.set_password(constants.KEY_TWITCH_CHANNEL, ch)
        except RuntimeError as e:
            QMessageBox.warning(self, self._tr("dlg.keyring"), str(e))
            return
        self._on_user_status(self._tr("status.twitch_keys_saved"))
        self._refresh_connection_panels()

    async def _twitch_browser_login(self) -> None:
        client_id = self._twitch_client_id_resolved()
        if not client_id:
            QMessageBox.warning(self, self._tr("dlg.twitch"), self._tr("dlg.twitch_need_client_id"))
            return
        try:
            token_payload = await twitch_oauth_device.run_device_code_flow(
                client_id,
                status=self._on_user_status,
                locale=self._locale,
            )
            twitch_credentials.save_oauth_bundle(token_payload, client_id=client_id)
            keyring_store.set_password(constants.KEY_TWITCH_CLIENT_ID, client_id)
            sec = self._twitch_client_secret.text().strip()
            if sec:
                keyring_store.set_password(constants.KEY_TWITCH_CLIENT_SECRET, sec)
            keyring_store.delete_password(constants.KEY_TWITCH_TOKEN)
            self._twitch_token.clear()
            access = token_payload.get("access_token")
            if isinstance(access, str) and access:
                info = await twitch_oauth_device.validate_token(access)
                login = info.get("login")
                if isinstance(login, str) and login:
                    ln = login.strip().lower()
                    twitch_credentials.set_authorized_login(ln)
                    self._twitch_channel.setText(ln)
            self._on_user_status(self._tr("status.twitch_browser_ok"))
            self._refresh_connection_panels()
        except (httpx.HTTPError, ValueError, TimeoutError, OSError, RuntimeError) as e:
            QMessageBox.warning(self, self._tr("dlg.twitch_oauth"), str(e))

    async def _start_twitch(self) -> None:
        channel = self._twitch_channel.text().strip()
        if not channel:
            QMessageBox.warning(self, self._tr("dlg.twitch"), self._tr("dlg.twitch_need_channel"))
            return

        manual = self._twitch_token.text().strip()
        if not manual:
            manual = keyring_store.get_password(constants.KEY_TWITCH_TOKEN) or ""

        client_id = self._twitch_client_id_resolved()
        client_secret = self._twitch_client_secret_resolved()

        token = manual.strip()
        if not token:
            token = await twitch_credentials.ensure_fresh_access_token(
                client_id,
                client_secret or None,
            )
        if not token:
            QMessageBox.warning(self, self._tr("dlg.twitch"), self._tr("dlg.twitch_need_token"))
            return

        await self._twitch.start(token, channel)

    @Slot()
    def _forget_youtube_client_config(self) -> None:
        keyring_store.delete_password(constants.KEY_YOUTUBE_CLIENT_CONFIG)
        self._on_user_status(self._tr("status.youtube_json_removed"))
        self._refresh_connection_panels()
        QMessageBox.information(
            self,
            self._tr("dlg.youtube"),
            self._tr("dlg.youtube_next_json"),
        )

    @Slot()
    def _yt_oauth_from_qml(self) -> None:
        asyncio.ensure_future(self._run_youtube_oauth())

    async def _run_youtube_oauth(self) -> None:
        """OAuth uses a Google *Desktop* client JSON once (keyring), then only the browser."""
        raw = os.environ.get("GOOGLE_OAUTH_CLIENT_JSON", "").strip()
        if not raw:
            raw = keyring_store.get_password(constants.KEY_YOUTUBE_CLIENT_CONFIG) or ""

        if not raw:
            path, _ = QFileDialog.getOpenFileName(
                self,
                self._tr("dlg.google_json_title"),
                str(Path.home()),
                self._tr("dlg.json_filter"),
            )
            if not path:
                return
            try:
                raw = Path(path).read_text(encoding="utf-8")
            except OSError as e:
                QMessageBox.critical(self, self._tr("dlg.youtube"), str(e))
                return
            try:
                parse_google_desktop_client_json(raw)
            except (json.JSONDecodeError, ValueError) as e:
                QMessageBox.warning(self, self._tr("dlg.youtube"), str(e))
                return
            try:
                keyring_store.set_password(constants.KEY_YOUTUBE_CLIENT_CONFIG, raw)
            except RuntimeError as e:
                QMessageBox.warning(self, self._tr("dlg.keyring"), str(e))
                return

        try:
            client_cfg = parse_google_desktop_client_json(raw)
        except (json.JSONDecodeError, ValueError) as e:
            QMessageBox.warning(self, self._tr("dlg.youtube"), str(e))
            return

        try:
            await self._youtube.browser_login(client_cfg)
        except (OSError, RuntimeError, ValueError) as e:
            QMessageBox.critical(self, self._tr("dlg.youtube"), str(e))
        else:
            self._on_user_status(self._tr("status.youtube_signed_in"))
            self._refresh_connection_panels()

    async def _start_youtube(self) -> None:
        url = self._yt_video.text().strip()
        await self._youtube.start(url if url else None)

    async def _start_tiktok(self) -> None:
        user = self._tiktok_username.text().strip()
        if not user:
            QMessageBox.warning(self, self._tr("dlg.tiktok"), self._tr("dlg.tiktok_need_username"))
            self._tiktok_enabled = False
            return
        await self._tiktok.start(user)

    @Slot()
    def _refresh_audio_devices(self) -> None:
        from PySide6.QtMultimedia import QMediaDevices

        self._audio_combo.blockSignals(True)
        current = self._settings.value("audio/device_description", "", str)
        self._audio_combo.clear()
        for dev in QMediaDevices.audioOutputs():
            self._audio_combo.addItem(dev.description())
        idx = self._audio_combo.findText(current)
        if idx >= 0:
            self._audio_combo.setCurrentIndex(idx)
        self._audio_combo.blockSignals(False)
        self._apply_audio_device_selection()

    @Slot()
    def _apply_audio_device_selection(self) -> None:
        desc = self._audio_combo.currentText()
        self._sink.set_output_device_by_description(desc or None)
        self._settings.setValue("audio/device_description", desc)

    @Slot(int)
    def _on_volume_changed(self, value: int) -> None:
        self._sink.set_volume(value / 100.0)
        self._settings.setValue("audio/volume", value)

    async def announce_donation_tts(self, line: str) -> None:
        """Speak one donation line (used by Donations live TTS). Errors are logged, not modal."""
        text = (line or "").strip()
        if not text:
            return
        self._apply_audio_device_selection()
        try:
            audio = await self._tts.synthesize(text)
            try:
                audio = await apply_rvc_if_active(self._rvc_runtime, audio, priority=0)
            except (OSError, ValueError, RuntimeError) as e:
                logger.warning("RVC donation TTS: %s", e)
            await self._sink.play_mp3(audio)
        except (OSError, ValueError) as e:
            logger.warning("Donation TTS: %s", e)

    async def speak_action_tts(self, text: str) -> None:
        """Speak text from platform Actions; errors propagate to the actions engine."""
        line = (text or "").strip()
        if not line:
            return
        self._apply_audio_device_selection()
        audio = await self._tts.synthesize(line)
        try:
            audio = await apply_rvc_if_active(self._rvc_runtime, audio, priority=0)
        except (OSError, ValueError, RuntimeError) as e:
            logger.warning("RVC action TTS: %s", e)
        await self._sink.play_mp3(audio)

    async def _test_tts(self) -> None:
        text = self._test_phrase.text().strip()
        if not text:
            return
        self._apply_audio_device_selection()
        try:
            audio = await self._tts.synthesize(text)
            try:
                audio = await apply_rvc_if_active(self._rvc_runtime, audio, priority=0)
            except (OSError, ValueError, RuntimeError) as e:
                logger.warning("RVC test: %s", e)
            await self._sink.play_mp3(audio)
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, self._tr("dlg.tts"), str(e))

    async def _flush_tts_and_rvc_queues(self) -> None:
        """Force-stop pending TTS/RVC work and current playback."""
        # Stop playback ASAP (even if synth is still running).
        try:
            self._sink.shutdown()
        except RuntimeError:
            # Qt objects may already be shutting down; ignore.
            pass
        # Cancel in-flight TTS/RVC processing + drop queued work.
        await self._coordinator.flush_tts()
        self._on_user_status(self._tr("audio.flush_queues"))

    async def run_startup(self) -> None:
        try:
            self._on_user_status(self._tr("startup.workers"))
            await self._overlay_server.start()
            logger.info("Overlay server: %s", self._overlay_server.base_url())
            await self._swap_tts_backend()
            await self._coordinator.start_workers()
            vol = int(self._settings.value("audio/volume", 100))
            self._sink.set_volume(vol / 100.0)
            self._apply_audio_device_selection()
            self._on_user_status(self._tr("startup.ready"))
            await self._maybe_auto_start_platforms()
        finally:
            self.startup_finished.emit()

    async def _maybe_auto_start_platforms(self) -> None:
        if (
            bool(self._settings.value(_SETTINGS_AUTOSTART_TWITCH, False, bool))
            and twitch_credentials.twitch_keyring_has_session()
            and not self._twitch.running
        ):
            await self._start_twitch()
        if (
            bool(self._settings.value(_SETTINGS_AUTOSTART_YOUTUBE, False, bool))
            and is_google_account_linked()
            and not self._youtube.running
        ):
            await self._start_youtube()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._closing:
            event.accept()
            return
        save_window_geometry(KEY_MAIN_WINDOW, self)
        self._closing = True
        event.ignore()
        asyncio.ensure_future(self._async_shutdown())

    def _release_rvc_gpu(self) -> None:
        """Unload RVC / torch weights so CUDA threads do not keep the process alive."""
        rvc_runtime_cancel_pending(self._rvc_runtime)
        chain = self._rvc_runtime.chain
        if chain is None:
            return
        try:
            chain.close()
        except (OSError, RuntimeError, TypeError, ValueError) as e:
            logger.debug("RVC release: %s", e)
        self._rvc_runtime.chain = None

    async def _async_shutdown(self) -> None:
        """Tear down chat, workers, TTS, audio, GPU; always quit Qt even on errors."""
        app = QApplication.instance()
        watchdog = threading.Timer(6.0, os._exit, args=(0,))
        watchdog.daemon = True
        watchdog.start()
        try:
            try:
                self._queue_timer.stop()
            except RuntimeError:
                logger.debug("Shutdown: queue timer already stopped")

            try:
                self._uninstall_log_handler()
            except RuntimeError:
                logger.debug("Shutdown: log handler already uninstalled")

            for name, coro in (
                ("overlay_server.stop", self._overlay_server.stop()),
                ("twitch.stop", self._twitch.stop()),
                ("youtube.stop", self._youtube.stop()),
                ("tiktok.stop", self._tiktok.stop()),
                ("coordinator.stop_workers", self._coordinator.stop_workers()),
                ("tts.aclose", self._tts.aclose()),
                ("rvc.stop_dispatcher", rvc_runtime_stop_dispatcher(self._rvc_runtime)),
            ):
                try:
                    await coro
                except (OSError, RuntimeError, ValueError, TypeError) as e:
                    logger.exception("Shutdown step failed (%s): %s", name, e)
                except asyncio.CancelledError:
                    raise

            try:
                self._release_rvc_gpu()
            except (OSError, RuntimeError, ValueError, TypeError) as e:
                logger.exception("Shutdown step failed (rvc.release): %s", e)

            try:
                self._sink.shutdown()
            except (OSError, RuntimeError, ValueError, TypeError) as e:
                logger.exception("Shutdown step failed (audio.shutdown): %s", e)

            loop = asyncio.get_running_loop()
            shutdown_exec = getattr(loop, "shutdown_default_executor", None)
            if callable(shutdown_exec):
                try:
                    await shutdown_exec()
                except (OSError, RuntimeError) as e:
                    logger.debug("Shutdown: default executor did not shut down cleanly: %s", e)
        finally:
            watchdog.cancel()
            if app is not None:
                app.quit()
