from __future__ import annotations

import asyncio
import html
import json
import logging
import os
import secrets
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, NamedTuple
from xml.sax.saxutils import quoteattr

import httpx
import shiboken6
from PySide6.QtCore import (
    QByteArray,
    QEvent,
    QObject,
    QSettings,
    QSize,
    Qt,
    QTimer,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import (
    QCloseEvent,
    QColor,
    QDesktopServices,
    QFont,
    QIcon,
    QKeySequence,
    QPainter,
    QPen,
    QPixmap,
    QShortcut,
    QTextCursor,
)
from PySide6.QtQuick import QQuickView
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFontComboBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QStyle,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from qframelesswindow import FramelessWindow, StandardTitleBar

from stream_cheremsha.overlays.activity_engine import ActivityEngine

if sys.platform == "win32":
    try:
        import win32con
        import win32gui
    except ImportError:
        win32con = None  # type: ignore[misc, assignment]
        win32gui = None  # type: ignore[misc, assignment]

from stream_cheremsha import l10n
from stream_cheremsha.actions.engine import PlatformActionsEngine
from stream_cheremsha.actions.events import ChatMessageEvent, GiftReceivedEvent
from stream_cheremsha.actions.store import (
    actions_rules_key_is_set,
    load_rules,
    save_rules,
)
from stream_cheremsha.actions.tiktok_gifts import tiktok_catalog_gift_image_url
from stream_cheremsha.activity.aggregator import LikeShareAggregator
from stream_cheremsha.activity.models import (
    ActivityItem,
    activity_append_patch,
    activity_join_ticker_patch,
    now_hms,
)
from stream_cheremsha.audio.qt_sink import QtAudioSink
from stream_cheremsha.battle_royale.controller import BattleRoyaleController
from stream_cheremsha.battle_royale.models import BattleFighter, BattlePhase
from stream_cheremsha.chat import kick_credentials, twitch_credentials, twitch_oauth_device
from stream_cheremsha.chat.kick_api import (
    KickApiClient,
    KickOAuthConfig,
    exchange_code,
)
from stream_cheremsha.chat.kick_source import KickSource
from stream_cheremsha.chat.tiktok_source import TikTokChatSource
from stream_cheremsha.chat.twitch_eventsub import (
    TwitchEventSubCallbacks,
    TwitchEventSubClient,
    TwitchNotifiedUser,
)
from stream_cheremsha.chat.twitch_helix import TwitchHelixClient
from stream_cheremsha.chat.twitch_source import TwitchSource
from stream_cheremsha.chat.youtube_source import (
    YouTubeActionSignal,
    YouTubeChatSource,
    clear_youtube_user_session,
    is_google_account_linked,
    parse_google_desktop_client_json,
)
from stream_cheremsha.config import constants, embedded, keyring_store
from stream_cheremsha.domain.models import ChatMessage, ChatPlatform
from stream_cheremsha.domain.points import (
    PointsConfig,
    StreamEarnTracker,
    earn_rate_template_vars,
    normalize_tiktok_username,
)
from stream_cheremsha.domain.protocols import TextToSpeech
from stream_cheremsha.domain.tiktok_link_challenge import extract_link_code_from_comment
from stream_cheremsha.music.musicbrainz import youtube_title_indicates_russian_artist_area
from stream_cheremsha.music.player import MusicPlayer
from stream_cheremsha.music.queue_controller import MusicQueueController
from stream_cheremsha.music.yt_dlp_resolver import fetch_youtube_meta, fetch_youtube_title
from stream_cheremsha.online.models import now_hms as online_now_hms
from stream_cheremsha.online.models import online_state_patch
from stream_cheremsha.openai_moderation import openai_moderation_flagged
from stream_cheremsha.overlays.battle_royale_overlay_config import (
    battle_royale_overlay_config_to_json_text,
    load_battle_royale_overlay_config,
)
from stream_cheremsha.overlays.chat_overlay import chat_message_to_patch
from stream_cheremsha.overlays.community_world_controller import CommunityWorldController
from stream_cheremsha.overlays.king_of_live_overlay_config import (
    king_of_live_overlay_config_to_json_text,
    load_king_of_live_overlay_config,
)
from stream_cheremsha.overlays.live_leaderboard_controller import LiveLeaderboardController
from stream_cheremsha.overlays.registry import OverlayRegistry
from stream_cheremsha.overlays.server import OverlayServer
from stream_cheremsha.overlays.signal_system_controller import SignalSystemController
from stream_cheremsha.overlays.social_rotator_controller import SocialRotatorController
from stream_cheremsha.overlays.stream_goal_controller import StreamGoalController
from stream_cheremsha.overlays.stream_pet_controller import StreamPetController
from stream_cheremsha.overlays.top_gifters_overlay_config import load_top_gifters_overlay_config
from stream_cheremsha.overlays.top_gifters_session import TikTokSessionTopGifters
from stream_cheremsha.overlays.top_likers_overlay_config import load_top_likers_overlay_config
from stream_cheremsha.overlays.top_likers_session import TikTokSessionTopLikers
from stream_cheremsha.overlays.tunnel import OverlayTunnel
from stream_cheremsha.overlays.tunnel_install import (
    install_prompt_labels,
    install_status_message,
    install_tunnel_tool_via_winget,
    is_tunnel_cli_installed,
    is_winget_available,
    provider_auto_installs_cli,
    provider_needs_cli,
    tunnel_cli_title,
)
from stream_cheremsha.overlays.webcam_frame_controller import WebcamFrameController
from stream_cheremsha.paths import stream_cheremsha_root
from stream_cheremsha.persistence.battle_royale_wins_sqlite import (
    fetch_hall_of_fame,
    record_battle_win,
)
from stream_cheremsha.persistence.points_sqlite import (
    add_points,
    cancel_telegram_link_challenge,
    create_telegram_link_challenge,
    engagement_cooldown_remaining_sec,
    get_balance_for_unique_id,
    get_telegram_id_for_unique_id,
    get_telegram_link,
    get_wallet_for_stable_key,
    refund_for_unique_id,
    try_complete_telegram_link_challenge,
    try_spend_for_unique_id,
)
from stream_cheremsha.persistence.tiktok_gifts_sqlite import (
    append_tiktok_gift_event,
    fetch_all_time_gifter_totals,
    unique_id_from_user_bundle,
)
from stream_cheremsha.pipeline.coordinator import StreamCoordinator
from stream_cheremsha.pipeline.filters import message_allowed_by_tts_whitelist
from stream_cheremsha.pipeline.tts_sanitize import strip_non_alphabetic_for_tts
from stream_cheremsha.ssl_manager import ensure_valid_ssl
from stream_cheremsha.telegram.bot_service import RiskyDecisionResult, TelegramBotService
from stream_cheremsha.telegram.tiktok_song_filter import (
    TikTokLyricsCheckError,
    analyze_lyrics_with_groq,
    fetch_lyrics_for_youtube_title,
    format_tiktok_reject_reason,
)
from stream_cheremsha.tts.edge_tts import (
    EdgeTts,
    filter_edge_voices_for_locale,
    list_edge_voices_cached,
)
from stream_cheremsha.tts.google_translate_tts import GoogleTranslateTts
from stream_cheremsha.tts.respeecher_tts import REPEECHER_VOICES, ReSpeecherTts
from stream_cheremsha.ui.actions_qml_api import ActionsQmlApi
from stream_cheremsha.ui.chat_formatting import (
    CHAT_DEFAULT_FONT_FAMILY,
    chat_font_stack_css,
    format_chat_message_html,
    load_platform_icon_data_uris,
)
from stream_cheremsha.ui.chat_popout import ChatPopoutWindow
from stream_cheremsha.ui.docks_qml_api import DocksQmlApi
from stream_cheremsha.ui.donations_qml_api import DonationsQmlApi
from stream_cheremsha.ui.kick_analytics_api import KickAnalyticsApi
from stream_cheremsha.ui.overlay_tunnel_qml_api import OverlayTunnelQmlApi
from stream_cheremsha.ui.points_settings_dialog import (
    SETTINGS_POINTS_ENABLED,
    PointsSettingsDialog,
    load_points_config_from_settings,
)
from stream_cheremsha.ui.qml_api import StreamCheremshaQmlApi
from stream_cheremsha.ui.qt_async_dialog import async_dialog_code
from stream_cheremsha.ui.tiktok_analytics_api import TikTokAnalyticsApi
from stream_cheremsha.ui.twitch_analytics_api import TwitchAnalyticsApi
from stream_cheremsha.ui.widgets_qml_api import WidgetsQmlApi, WidgetsWindowQmlApi
from stream_cheremsha.ui.window_geometry import (
    KEY_MAIN_WINDOW,
    restore_window_geometry,
    save_window_geometry,
)
from stream_cheremsha.ui.youtube_analytics_api import YouTubeAnalyticsApi

logger = logging.getLogger(__name__)

_STREAM_ROOT = stream_cheremsha_root()


def _qml_path(name: str) -> Path:
    return _STREAM_ROOT / "qml" / name


def _setup_qml_import_path(widget: QQuickWidget) -> None:
    widget.engine().addImportPath(str(_STREAM_ROOT / "qml"))


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
_SETTINGS_AUTOSTART_TIKTOK = "startup/auto_start_tiktok"
_SETTINGS_AUTOSTART_KICK = "startup/auto_start_kick"
_SETTINGS_TTS_GAIN_DB = "audio/tts_gain_db"
_TTS_ENGINE_GOOGLE = "google"
_TTS_ENGINE_EDGE = "edge"
_TTS_ENGINE_RESPEECHER = "respeecher"
_TTS_DEFAULT_VOICE_ID = "olesia-conversation"
_SETTINGS_TTS_ENGINE = "tts/engine"
_SETTINGS_TTS_LANG = "tts/output_language"
_SETTINGS_EDGE_VOICE_BY_LANG = "tts/edge_voice_by_lang"

# Languages supported by the UI TTS language picker (Google/Edge backends).
TTS_LANG_OPTIONS: tuple[str, ...] = ("uk-UA", "en-US", "en-GB", "de-DE", "pl-PL")
_SETTINGS_TTS_CHAT_TWITCH = "tts_chat/twitch_enabled"
_SETTINGS_TTS_CHAT_YOUTUBE = "tts_chat/youtube_enabled"
_SETTINGS_TTS_CHAT_TIKTOK = "tts_chat/tiktok_enabled"
_SETTINGS_TTS_CHAT_KICK = "tts_chat/kick_enabled"
_SETTINGS_TTS_OPENAI_MODERATE = "tts/openai_moderate_enabled"
_SETTINGS_TTS_SPEAK_AUTHOR = "tts/speak_chat_author_name"
_SETTINGS_TTS_STRIP_NON_ALPHA = "tts/strip_non_alphabetic"
_SETTINGS_TTS_WHITELIST = "tts/whitelist"
# TTS playback speed as a percentage (100 = normal); 50..200 maps to 0.5x..2.0x.
_SETTINGS_TTS_RATE_PERCENT = "tts/rate_percent"
_TTS_RATE_MIN = 50
_TTS_RATE_MAX = 200
_TTS_RATE_DEFAULT = 100
_SETTINGS_TTS_MIN_INTERVAL_SEC = "tts/min_interval_sec"
_SETTINGS_TTS_RANDOMIZE_EDGE = "tts/randomize_edge"
_SETTINGS_TTS_RANDOMIZE_RESPEECHER = "tts/randomize_respeecher"

_SETTINGS_TELEGRAM_ENABLED = "telegram/enabled"
_SETTINGS_TELEGRAM_ADMIN_ID = "telegram/admin_id"
_SETTINGS_TELEGRAM_SONG_REQUESTS_ENABLED = "telegram/song_requests_enabled"
_SETTINGS_TELEGRAM_TIKTOK_LYRICS_FILTER = "telegram/tiktok_live_lyrics_filter_enabled"

_SETTINGS_MUSIC_BACKEND = "music/backend"  # "app" | "mpv"
_SETTINGS_MUSIC_MAX_DURATION_MIN = "music/max_duration_minutes"

_SETTINGS_UPDATES_CHECK_ON_STARTUP = "updates/check_on_startup"
_SETTINGS_UPDATES_IGNORED_VERSION = "updates/ignored_version"
_SETTINGS_UPDATES_LAST_CHECKED_AT = "updates/last_checked_at_utc"

# If you don't have an Authenticode cert yet, keep this off.
_UPDATES_REQUIRE_SIGNATURE = False
_UPDATES_EXPECTED_PUBLISHER_SUBJECT_CONTAINS = "Cheremsha"


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


class _TitleBar(QFrame):
    def __init__(self, owner: QWidget) -> None:
        super().__init__(owner)
        self.setObjectName("appTitleBar")
        self.setFixedHeight(44)

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 10, 12, 10)
        row.setSpacing(10)

        self._title = QLabel()
        self._title.setObjectName("titleBarTitle")
        self._title.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        row.addWidget(self._title, stretch=1, alignment=Qt.AlignmentFlag.AlignVCenter)

        def _mk_btn(*, glyph: str, danger: bool = False) -> QToolButton:
            b = QToolButton()
            b.setObjectName("titleBarBtnDanger" if danger else "titleBarBtn")
            b.setText(glyph)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFixedSize(34, 28)
            return b

        self.btn_min = _mk_btn(glyph="—")
        self.btn_max = _mk_btn(glyph="□")
        self.btn_close = _mk_btn(glyph="×", danger=True)
        row.addWidget(self.btn_min, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self.btn_max, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self.btn_close, 0, Qt.AlignmentFlag.AlignVCenter)

        self.setStyleSheet(
            """
            QFrame#appTitleBar {
              background: #121620;
              border-bottom: 1px solid #2a3142;
            }
            QLabel#titleBarTitle {
              color: #e8eaed;
              font-size: 13px;
              font-weight: 600;
            }
            QToolButton#titleBarBtn, QToolButton#titleBarBtnDanger {
              background: #1c2434;
              border: 1px solid #2a3142;
              border-radius: 8px;
              color: #e8eaed;
              padding: 0px;
            }
            QToolButton#titleBarBtn:hover, QToolButton#titleBarBtn[ncHover="true"] {
              background: #263246;
              border-color: #3b4458;
            }
            QToolButton#titleBarBtn:pressed, QToolButton#titleBarBtn[ncPressed="true"] {
              background: #303a50;
            }
            QToolButton#titleBarBtnDanger:hover, QToolButton#titleBarBtnDanger[ncHover="true"] {
              background: #991b1b;
              border-color: #3b4458;
            }
            QToolButton#titleBarBtnDanger:pressed, QToolButton#titleBarBtnDanger[ncPressed="true"] {
              background: #7f1d1d;
            }
            """,
        )

    def set_title(self, text: str) -> None:
        self._title.setText(text or "")

    def mouseDoubleClickEvent(self, e) -> None:  # type: ignore[override]
        w = self.window()
        if isinstance(w, QWidget):
            if w.isMaximized():
                w.showNormal()
            else:
                w.showMaximized()
        e.accept()

    def mousePressEvent(self, e) -> None:  # type: ignore[override]
        if e.button() == Qt.MouseButton.LeftButton:
            w = self.window()
            try:
                w.windowHandle().startSystemMove()  # type: ignore[union-attr]
                e.accept()
                return
            except (AttributeError, RuntimeError):
                pass
        super().mousePressEvent(e)


class _CheremshaTitleBar(StandardTitleBar):
    def __init__(self, owner: QWidget) -> None:
        super().__init__(owner)
        self.setObjectName("cheremshaTitleBar")
        self.setFixedHeight(44)

        self.titleLabel.setStyleSheet(
            """
            QLabel{
                background: transparent;
                color: #e8eaed;
                font-size: 13px;
                font-weight: 600;
                padding: 0 6px;
            }
            """,
        )

        # Make caption buttons visible on dark chrome.
        ink = QColor("#e8eaed")
        self.minBtn.setNormalColor(ink)
        self.minBtn.setHoverColor(ink)
        self.minBtn.setPressedColor(ink)
        self.maxBtn.setNormalColor(ink)
        self.maxBtn.setHoverColor(ink)
        self.maxBtn.setPressedColor(ink)
        self.closeBtn.setNormalColor(ink)

        # Big Picture mode toggle (before settings).
        self.bigPictureBtn = QToolButton(self)
        self.bigPictureBtn.setObjectName("titleBigPicture")
        self.bigPictureBtn.setAutoRaise(True)
        self.bigPictureBtn.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMaxButton),
        )
        self.bigPictureBtn.setIconSize(QSize(18, 18))
        self.bigPictureBtn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.bigPictureBtn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.bigPictureBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bigPictureBtn.setCheckable(True)
        self.bigPictureBtn.setToolTip("Big Picture")
        self.bigPictureBtn.clicked.connect(
            lambda: self.window()._toggle_big_picture(),  # noqa: SLF001
        )

        # Settings button (moved from footer).
        self.settingsBtn = QToolButton(self)
        self.settingsBtn.setObjectName("titleSettings")
        self.settingsBtn.setAutoRaise(True)
        st_path = _asset_path("settings.png")
        if st_path.is_file():
            self.settingsBtn.setIcon(QIcon(str(st_path)))
        else:
            self.settingsBtn.setIcon(
                QIcon.fromTheme(
                    "preferences-system",
                    self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogInfoView),
                ),
            )
        self.settingsBtn.setIconSize(QSize(18, 18))
        self.settingsBtn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.settingsBtn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.settingsBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        # Locale is initialized later by MainWindow; set translated tooltip after init.
        self.settingsBtn.setToolTip("Settings")
        self.settingsBtn.clicked.connect(
            lambda: self.window()._set_main_page(self.window()._IX_SETTINGS),  # noqa: SLF001
        )

        # Insert right before min/max/close buttons (settings, then Big Picture).
        self.hBoxLayout.insertWidget(
            self.hBoxLayout.count() - 3,
            self.settingsBtn,
            0,
            Qt.AlignRight,
        )
        self.hBoxLayout.insertWidget(
            self.hBoxLayout.count() - 4,
            self.bigPictureBtn,
            0,
            Qt.AlignRight,
        )

        self.setStyleSheet(
            """
            QWidget#cheremshaTitleBar {
              background: #121620;
              border-bottom: 1px solid #2a3142;
            }

            QToolButton#titleSettings {
              background: rgba(0, 0, 0, 0);
              border: none;
              border-radius: 8px;
              padding: 0px;
              margin-right: 4px;
            }
            QToolButton#titleSettings:hover { background: #263246; }
            QToolButton#titleSettings:pressed { background: #303a50; }

            QToolButton#titleBigPicture {
              background: rgba(0, 0, 0, 0);
              border: none;
              border-radius: 8px;
              padding: 0px;
              margin-right: 4px;
            }
            QToolButton#titleBigPicture:hover { background: #263246; }
            QToolButton#titleBigPicture:pressed { background: #303a50; }
            QToolButton#titleBigPicture:checked { background: #1e3a5f; }

            TitleBarButton {
              qproperty-normalColor: #e8eaed;
              qproperty-hoverColor: #e8eaed;
              qproperty-pressedColor: #e8eaed;
              qproperty-normalBackgroundColor: rgba(0, 0, 0, 0);
              qproperty-hoverBackgroundColor: #263246;
              qproperty-pressedBackgroundColor: #303a50;
            }

            CloseButton {
              qproperty-normalColor: #e8eaed;
              qproperty-hoverColor: #e8eaed;
              qproperty-pressedColor: #e8eaed;
              qproperty-normalBackgroundColor: rgba(0, 0, 0, 0);
              qproperty-hoverBackgroundColor: #991b1b;
              qproperty-pressedBackgroundColor: #7f1d1d;
            }
            """,
        )

    def canDrag(self, pos):  # type: ignore[override]
        # Avoid starting system move when interacting with title-bar controls.
        try:
            for btn in (getattr(self, "bigPictureBtn", None), self.settingsBtn):
                if btn is not None and btn.isVisible() and btn.geometry().contains(pos):
                    return False
        except RuntimeError:
            return False
        return super().canDrag(pos)

    def paintEvent(self, e) -> None:  # type: ignore[override]
        # Force a non-transparent dark chrome background regardless of the app-wide
        # stylesheet (which sets QWidget backgrounds to transparent).
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#121620"))
        pen = QPen(QColor("#2a3142"))
        pen.setCosmetic(True)
        p.setPen(pen)
        y = self.height() - 1
        p.drawLine(0, y, self.width(), y)
        super().paintEvent(e)


class _RiskyPendingTrack(NamedTuple):
    video_id: str
    requested_by: str
    title: str
    requester_chat_id: int
    # Points already reserved (debited) for this order; refunded if the admin denies
    # or the enqueue ultimately fails. ``charged_unique_id`` is empty when the points
    # economy is disabled (no charge was made).
    charged_unique_id: str = ""
    charged_amount: int = 0


class _PointsNotifyPending(NamedTuple):
    delta: int
    reasons: frozenset[str]
    balance: int


_POINTS_EARN_REASON_ORDER = ("gift", "like", "share", "follow", "watch")


class MainWindow(FramelessWindow):
    """MVP: stacked panes (connections, settings, chat, audio, logs) + status."""

    startup_finished = Signal()

    # QStackedWidget indices (order must match _build_ui addWidget sequence).
    _IX_CONN = 0
    _IX_SETTINGS = 1
    _IX_CHAT = 2
    _IX_AUDIO = 3
    _IX_LOGS = 4
    _IX_DONATIONS = 5
    _IX_WIDGETS = 6
    _IX_DOCKS = 7
    _IX_ACTIONS = 8
    _IX_MUSIC = 9
    _IX_BIG_PICTURE = 10
    _QML_STACK_INDICES = frozenset(
        {_IX_CONN, _IX_DONATIONS, _IX_WIDGETS, _IX_DOCKS, _IX_ACTIONS},
    )

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
        lab.setContentsMargins(0, 0, 6, 0)
        return lab

    @staticmethod
    def _obs_settings_label(text: str) -> QLabel:
        """Narrow settings form: short right-aligned labels (OBS host/port/password)."""
        lab = QLabel(text)
        lab.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lab.setWordWrap(True)
        lab.setMinimumWidth(118)
        lab.setContentsMargins(0, 0, 6, 0)
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
        self.setTitleBar(_CheremshaTitleBar(self))
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
        self.titleBar.raise_()
        self._win_anim_applied = False
        self._closing = False
        self._tiktok_toggle_busy = False
        self._tiktok_enabled = False
        self._kick_enabled = False
        self._kick_toggle_busy = False
        self._overlay_registry = OverlayRegistry()
        self._overlay_server = OverlayServer(
            registry=self._overlay_registry,
            host="127.0.0.1",
            port=17171,
            certificate_pem=embedded.OVERLAY_CERTIFICATE,
            private_key_pem=embedded.OVERLAY_PRIVATE_KEY,
        )
        self._overlay_tunnel = OverlayTunnel()
        self._asyncio_loop: asyncio.AbstractEventLoop | None = None
        self._music_queue = MusicQueueController(instance="main")
        self._music_player: MusicPlayer | None = None
        self._music_title_cache: dict[str, str] = {}
        self._telegram: TelegramBotService | None = None
        self._telegram_risky_pending: dict[str, _RiskyPendingTrack] = {}
        self._status_app = l10n.tr(self._locale, "status.app_idle")
        self._edge_voices_refresh_lock = asyncio.Lock()
        self._status_twitch = "—"
        self._status_youtube = "—"
        self._status_tiktok = "—"
        self._status_kick = "—"
        self._tts_chat_platform_enabled: dict[ChatPlatform, bool] = {
            ChatPlatform.TWITCH: bool(self._settings.value(_SETTINGS_TTS_CHAT_TWITCH, True, bool)),
            ChatPlatform.YOUTUBE: bool(
                self._settings.value(_SETTINGS_TTS_CHAT_YOUTUBE, True, bool),
            ),
            ChatPlatform.TIKTOK: bool(self._settings.value(_SETTINGS_TTS_CHAT_TIKTOK, True, bool)),
            ChatPlatform.KICK: bool(self._settings.value(_SETTINGS_TTS_CHAT_KICK, True, bool)),
        }

        self._bridge = UiBridge(self)
        self._bridge.append_chat.connect(self._append_chat)
        self._log_handler: QtLogHandler | None = None

        self._tts = self._construct_initial_tts()
        self._fallback_tts = None
        self._sink = QtAudioSink(self)
        self._coordinator = StreamCoordinator(
            tts=self._tts,
            audio_sink=self._sink,
            on_chat=self._on_chat_message,
            on_status=self._on_user_status,
            should_tts=self._should_tts_for_message,
            get_locale=self._get_locale,
            pre_tts=self._pre_tts_chat,
        )
        self._twitch = TwitchSource(
            self._coordinator,
            on_status=self._on_user_status,
            get_locale=self._get_locale,
        )
        self._twitch_analytics = TwitchAnalyticsApi(self)
        self._twitch_eventsub: TwitchEventSubClient | None = None
        self._twitch_helix: TwitchHelixClient | None = None
        self._twitch_viewers_task: asyncio.Task[None] | None = None
        self._online_publish_task: asyncio.Task[None] | None = None
        self._youtube_analytics = YouTubeAnalyticsApi(self)
        self._youtube = YouTubeChatSource(
            self._coordinator,
            on_status=self._on_user_status,
            on_analytics_event=self._on_youtube_analytics_event,
            get_locale=self._get_locale,
            on_viewers_current=self._on_youtube_viewers_current,
            on_action_event=self._on_youtube_action_event,
        )
        self._tiktok_analytics = TikTokAnalyticsApi(self)
        self._tiktok = TikTokChatSource(
            self._coordinator,
            on_status=self._on_user_status,
            on_gift=self._on_tiktok_gift,
            get_locale=self._get_locale,
            on_room_viewers_current=self._on_tiktok_room_viewers_current,
            on_room_viewers_total=self._tiktok_analytics.on_room_viewers_total,
            on_follow=self._on_tiktok_follow_any,
            on_join=self._on_tiktok_join_any,
            on_paid_sub=self._on_tiktok_paid_sub_any,
            on_gift_analytics=self._on_tiktok_gift_analytics_any,
            on_like=self._on_tiktok_like_any,
            on_share=self._on_tiktok_share_any,
            on_stream_start=self._on_tiktok_stream_start,
        )
        self._kick_analytics = KickAnalyticsApi(self)
        self._kick = KickSource(
            self._coordinator,
            on_status=self._on_user_status,
            get_locale=self._get_locale,
            on_follow=self._on_kick_follow_any,
            on_sub=self._on_kick_sub_any,
            on_gift_sub=self._on_kick_gift_sub_any,
            on_kick_gift=self._on_kick_gift_any,
        )
        self._like_share_agg = LikeShareAggregator(window_sec=7.0)
        self._tiktok_top_likers = TikTokSessionTopLikers()
        self._top_likers_publish_handle: asyncio.TimerHandle | None = None
        self._tiktok_top_gifters = TikTokSessionTopGifters()
        self._top_gifters_publish_handle: asyncio.TimerHandle | None = None
        # Points economy: per-stream earn tracker + watch-time sampling.
        self._earn_tracker = StreamEarnTracker(load_points_config_from_settings(self._settings))
        self._points_watch_active: dict[str, tuple[str, str]] = {}
        self._points_watch_timer = QTimer(self)
        self._points_watch_timer.timeout.connect(self._on_points_watch_tick)
        self._restart_points_watch_timer()
        self._points_notify_pending: dict[int, _PointsNotifyPending] = {}
        self._points_notify_timer = QTimer(self)
        self._points_notify_timer.setSingleShot(True)
        self._points_notify_timer.setInterval(2500)
        self._points_notify_timer.timeout.connect(self._flush_points_earn_notifications)
        self._king_overlay_publish_handle: asyncio.TimerHandle | None = None
        self._king_presence_seq: int = 0
        self._king_chat_highlight_seq: int = 0
        self._king_overlay_cached_king_key: str = ""
        self._king_overlay_cached_king_display: str = ""
        self._battle_controller = BattleRoyaleController()
        self._battle_controller._on_battle_ended.append(self._on_battle_royale_ended)
        self._battle_auto_arm_hint_count: int = 0
        self._battle_overlay_publish_handle: asyncio.TimerHandle | None = None
        self._battle_tick_timer = QTimer(self)
        self._battle_tick_timer.setInterval(1000)
        self._battle_tick_timer.timeout.connect(self._on_battle_tick)
        self._stream_pet = StreamPetController(
            pubsub=self._overlay_server.pubsub(),
            get_locale=lambda: self._locale,
            instance="main",
            parent=self,
        )
        self._stream_goal = StreamGoalController(
            pubsub=self._overlay_server.pubsub(),
            get_locale=lambda: self._locale,
            instance="main",
            parent=self,
        )
        self._live_leaderboard = LiveLeaderboardController(
            pubsub=self._overlay_server.pubsub(),
            get_locale=lambda: self._locale,
            instance="main",
            parent=self,
        )
        self._social_rotator = SocialRotatorController(
            pubsub=self._overlay_server.pubsub(),
            get_locale=lambda: self._locale,
            instance="main",
            parent=self,
        )
        self._community_world = CommunityWorldController(
            pubsub=self._overlay_server.pubsub(),
            get_locale=lambda: self._locale,
            instance="main",
            parent=self,
        )
        self._webcam_frame = WebcamFrameController(
            pubsub=self._overlay_server.pubsub(),
            get_locale=lambda: self._locale,
            instance="main",
            parent=self,
        )
        self._signal_system = SignalSystemController(
            pubsub=self._overlay_server.pubsub(),
            get_locale=lambda: self._locale,
            instance="main",
            parent=self,
        )
        self._activity_engine = ActivityEngine(
            pubsub=self._overlay_server.pubsub(),
            enabled=True,
            decay_speed=1.5,
            event_weights={
                "like": 2.0,
                "comment": 4.0,
                "follow": 6.0,
                "share": 8.0,
                "gift": 12.0,
            },
            on_score_change=lambda score: (
                self._signal_system.on_activity_surge(score) if score >= 85.0 else None
            ),
        )
        self._qml_pages_loaded: set[int] = set()
        self._active_qml_stack_index: int | None = None
        self._tiktok_username = QLineEdit()
        self._kick_channel = QLineEdit()
        self._obs_ws_host = QLineEdit()
        self._obs_ws_port = QLineEdit()
        self._obs_ws_password = QLineEdit()
        self._obs_ws_password.setEchoMode(QLineEdit.EchoMode.Password)
        self._obs_ws_enabled = QCheckBox()
        self._tg_enabled = QCheckBox()
        self._tg_token = QLineEdit()
        self._tg_token.setEchoMode(QLineEdit.EchoMode.Password)
        self._tg_admin_id = QLineEdit()
        self._tg_song_requests_enabled = QCheckBox()
        self._tg_tiktok_lyrics_filter = QCheckBox()
        self._tg_genius_token = QLineEdit()
        self._tg_genius_token.setEchoMode(QLineEdit.EchoMode.Password)
        self._tg_groq_api_key = QLineEdit()
        self._tg_groq_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._lbl_tg_tiktok_filter_hint = QLabel()
        self._openai_api_key = QLineEdit()
        self._openai_api_key.setEchoMode(QLineEdit.EchoMode.Password)

        self._music_use_mpv = QCheckBox()
        self._lbl_music_backend_hint = QLabel()
        self._btn_mpv_check = QPushButton()
        self._lbl_mpv_check_result = QLabel()
        self._lbl_music_max_duration = MainWindow._obs_settings_label("")
        self._music_max_duration_min = QSpinBox()
        self._lbl_music_max_duration_hint = QLabel()
        self._points_enabled_cb = QCheckBox()
        self._btn_points_configure = QPushButton()
        self._lbl_points_hint = QLabel()
        self._actions_qml_api = ActionsQmlApi(self)
        self._qml_actions: QQuickWidget | None = None
        self._widgets_qml_api: WidgetsQmlApi | None = None
        self._docks_qml_api: DocksQmlApi | None = None
        self._overlay_tunnel_qml_api: OverlayTunnelQmlApi | None = None
        self._qml_widgets_win: QQuickView | None = None
        self._qml_widgets: QQuickWidget | None = None
        self._qml_docks: QQuickWidget | None = None
        self._actions_engines: dict[tuple[str, str], PlatformActionsEngine] = {}
        self._chat_ic_tw: str | None = None
        self._chat_ic_yt: str | None = None
        self._chat_ic_tk: str | None = None
        self._chat_ic_kk: str | None = None
        # Hard cap: no unbounded growth; eviction matches QTextDocument line trim below.
        self._chat_message_history: deque[ChatMessage] = deque(
            maxlen=_MAX_CHAT_DOCUMENT_BLOCKS,
        )
        self._chat_popout: ChatPopoutWindow | None = None
        self._big_picture_active = False
        self._bp_return_index = self._IX_CONN
        self._bp_saved_geometry: QByteArray | None = None
        self._bp_was_maximized = False
        self._bp_was_fullscreen = False

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

    def nativeEvent(self, eventType, message):  # type: ignore[override]
        # Delegate to PySideSix-Frameless-Window native handler on Windows.
        return super().nativeEvent(eventType, message)

    def showEvent(self, e) -> None:  # type: ignore[override]
        super().showEvent(e)
        if self._win_anim_applied:
            return
        self._win_anim_applied = True
        # Apply window-animation styles after the HWND exists and Qt finished
        # applying its own flags; otherwise Qt may overwrite the style.
        QTimer.singleShot(0, self._apply_windows_animation_if_possible)

    def _apply_windows_animation_if_possible(self) -> None:
        if sys.platform != "win32" or win32con is None or win32gui is None:
            return
        h = int(self.winId())
        if h == 0:
            return

        # qframelesswindow already has windowEffect; re-apply to ensure styles are set.
        try:
            self.windowEffect.addWindowAnimation(h)  # type: ignore[attr-defined]
        except AttributeError:
            return

        win32gui.SetWindowPos(
            h,
            None,
            0,
            0,
            0,
            0,
            win32con.SWP_NOMOVE
            | win32con.SWP_NOSIZE
            | win32con.SWP_NOZORDER
            | win32con.SWP_FRAMECHANGED,
        )

    def _get_locale(self) -> str:
        return self._locale

    def _tr(self, key: str, **kwargs: object) -> str:
        return l10n.tr(self._locale, key, **kwargs)

    def _tts_whitelist_text(self) -> str:
        edit = getattr(self, "_edit_tts_whitelist", None)
        if edit is not None:
            return edit.toPlainText().strip()
        return str(self._settings.value(_SETTINGS_TTS_WHITELIST, "", str) or "").strip()

    def _should_tts_for_message(self, msg: ChatMessage) -> bool:
        if not self._chat_tts_enabled(msg.platform):
            return False
        return message_allowed_by_tts_whitelist(msg, self._tts_whitelist_text())

    def _chat_tts_enabled(self, platform: ChatPlatform) -> bool:
        return bool(self._tts_chat_platform_enabled.get(platform, True))

    def _set_chat_tts_enabled(self, platform: ChatPlatform, enabled: bool) -> None:
        self._tts_chat_platform_enabled[platform] = bool(enabled)
        key = {
            ChatPlatform.TWITCH: _SETTINGS_TTS_CHAT_TWITCH,
            ChatPlatform.YOUTUBE: _SETTINGS_TTS_CHAT_YOUTUBE,
            ChatPlatform.TIKTOK: _SETTINGS_TTS_CHAT_TIKTOK,
            ChatPlatform.KICK: _SETTINGS_TTS_CHAT_KICK,
        }.get(platform)
        if key is not None:
            self._settings.setValue(key, bool(enabled))

    async def _pre_tts_chat(self, text: str, author: str) -> str:
        out, replaced = await self._apply_openai_moderation_to_tts_text(text, author)
        out = self._maybe_strip_non_letters_for_tts(out, moderation_replaced=replaced)
        out = (out or "").strip()
        if not out:
            return ""
        return self._maybe_prefix_tts_author(author, out, moderation_replaced=replaced)

    async def _apply_openai_moderation_to_tts_text(
        self,
        text: str,
        author: str,
    ) -> tuple[str, bool]:
        """
        Returns (text_for_tts, moderation_replaced).
        ``moderation_replaced`` is True when the original was swapped for a policy message.
        """
        cb = getattr(self, "_cb_tts_openai_moderate", None)
        if cb is None or not cb.isChecked():
            return text, False
        key = (keyring_store.get_password(constants.KEY_OPENAI_API_KEY) or "").strip()
        if not key:
            self._on_user_status(self._tr("openai.moderation_no_api_key"))
            return text, False
        try:
            flagged = await openai_moderation_flagged(key, text)
        except (httpx.HTTPError, ValueError, OSError) as e:
            logger.warning("OpenAI moderation failed: %s", e)
            self._on_user_status(self._tr("openai.moderation_error", err=str(e)))
            return text, False
        if not flagged:
            return text, False
        return l10n.moderation_blocked_for_tts(self._current_tts_language(), author), True

    def _maybe_prefix_tts_author(
        self,
        author: str,
        text: str,
        *,
        moderation_replaced: bool,
    ) -> str:
        if moderation_replaced:
            return text
        sw = getattr(self, "_cb_tts_speak_author", None)
        if sw is None or not sw.isChecked():
            return text
        return l10n.tts_chat_author_lead(self._current_tts_language(), author) + text

    def _maybe_strip_non_letters_for_tts(self, text: str, *, moderation_replaced: bool) -> str:
        if moderation_replaced:
            return text
        cb = getattr(self, "_cb_tts_strip_non_alpha", None)
        if cb is None or not cb.isChecked():
            return text
        return strip_non_alphabetic_for_tts(text)

    def _tts_language_from_settings(self) -> str:
        v = str(self._settings.value(_SETTINGS_TTS_LANG, "uk-UA", str)).strip()
        return v if v else "uk-UA"

    def _current_tts_language(self) -> str:
        if hasattr(self, "_combo_tts_lang"):
            d = self._combo_tts_lang.currentData()
            if isinstance(d, str) and d.strip():
                return d.strip()
        return self._tts_language_from_settings()

    def _tts_rate_percent_from_settings(self) -> int:
        raw = self._settings.value(_SETTINGS_TTS_RATE_PERCENT, _TTS_RATE_DEFAULT)
        try:
            v = int(raw)
        except (TypeError, ValueError):
            v = _TTS_RATE_DEFAULT
        return max(_TTS_RATE_MIN, min(_TTS_RATE_MAX, v))

    def _min_interval_sec_from_settings(self) -> float:
        raw = self._settings.value(_SETTINGS_TTS_MIN_INTERVAL_SEC, 0.4)
        try:
            v = float(raw)
        except (TypeError, ValueError):
            v = 0.4
        return v

    @staticmethod
    def _edge_rate_string(rate_percent: int) -> str | None:
        """Map absolute speed percent (100 = normal) to Edge's relative rate, e.g. ``+25%``."""
        delta = int(rate_percent) - 100
        if delta == 0:
            return None
        return f"{delta:+d}%"

    def _construct_initial_tts(self) -> TextToSpeech:
        """Lightweight TTS for startup; other engines load in :meth:`run_startup` if selected."""
        lang = self._tts_language_from_settings()
        return GoogleTranslateTts(
            language=lang,
            rate_percent=self._tts_rate_percent_from_settings(),
        )

    def _build_ui(self) -> None:
        self._connections_root = self._build_connections_tab()
        self._connections_root.setParent(self)
        self._connections_root.hide()

        self._qml_api = StreamCheremshaQmlApi(self)
        self._qml_conn = QQuickWidget(self)
        self._qml_conn.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        self._qml_conn.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._qml_conn.setClearColor(QColor(10, 11, 14))
        _setup_qml_import_path(self._qml_conn)
        qml_p = _qml_path("ConnectionsView.qml")
        if not qml_p.is_file():
            logger.error("QML not found: %s", qml_p)
        self._bind_qml_context_properties(self._IX_CONN)
        self._qml_conn.setSource(QUrl.fromLocalFile(str(qml_p)))
        self._qml_pages_loaded.add(self._IX_CONN)
        self._active_qml_stack_index = self._IX_CONN

        self._donations_qml_api = DonationsQmlApi(self)
        self._qml_donations = QQuickWidget(self)
        self._qml_donations.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        self._qml_donations.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._qml_donations.setClearColor(QColor(10, 11, 14))
        self._widgets_qml_api = WidgetsQmlApi(pubsub=self._overlay_server.pubsub())
        self._widgets_qml_api.set_stream_goal_controller(self._stream_goal)
        self._widgets_qml_api.set_live_leaderboard_controller(self._live_leaderboard)
        self._widgets_qml_api.set_social_rotator_controller(self._social_rotator)
        self._widgets_qml_api.set_webcam_frame_controller(self._webcam_frame)
        self._widgets_qml_api.set_signal_system_controller(self._signal_system)
        self._donations_qml_api.set_donation_listener(self._on_external_donation)
        self._overlay_tunnel_qml_api = OverlayTunnelQmlApi(self)
        self._qml_widgets = QQuickWidget(self)
        self._qml_widgets.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        self._qml_widgets.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._qml_widgets.setClearColor(QColor(10, 11, 14))
        self._docks_qml_api = DocksQmlApi()
        self._qml_docks = QQuickWidget(self)
        self._qml_docks.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        self._qml_docks.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._qml_docks.setClearColor(QColor(10, 11, 14))
        self._qml_actions = QQuickWidget(self)
        self._qml_actions.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        self._qml_actions.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._qml_actions.setClearColor(QColor(10, 11, 14))
        root = QVBoxLayout(self)
        root.setSpacing(0)
        # qframelesswindow title bar is drawn on top of the client area
        # (not managed by layouts), so we reserve vertical space for it.
        root.setContentsMargins(0, int(self.titleBar.height()), 0, 0)

        body = QHBoxLayout()
        body.setSpacing(0)
        body.setContentsMargins(0, 0, 0, 0)
        root.addLayout(body, stretch=1)

        self._sidebar_frame = QFrame()
        self._sidebar_frame.setObjectName("appSidebar")
        # Design artboard sidebar content width is 212px (plus 1px divider).
        self._sidebar_frame.setFixedWidth(212)
        side_lay = QVBoxLayout(self._sidebar_frame)
        # Measured from design: left 12 / top 19 / right 13 / bottom 16; item gap 25.
        side_lay.setContentsMargins(12, 19, 13, 16)
        side_lay.setSpacing(25)

        brand = QWidget()
        brand.setObjectName("sidebarBrand")
        brand_lay = QHBoxLayout(brand)
        # Logo sits at x=20 in the design → +8px inside the 12px sidebar inset.
        brand_lay.setContentsMargins(8, 0, 0, 0)
        brand_lay.setSpacing(10)
        logo = QLabel()
        logo.setObjectName("sidebarLogo")
        logo.setFixedSize(34, 34)
        logo_path = _asset_path("icon.png")
        if logo_path.is_file():
            pm = QPixmap(str(logo_path))
            logo.setPixmap(
                pm.scaled(
                    34,
                    34,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                ),
            )
        brand_text = QWidget()
        brand_text_lay = QVBoxLayout(brand_text)
        brand_text_lay.setContentsMargins(0, 0, 0, 0)
        brand_text_lay.setSpacing(1)
        self._lbl_brand_name = QLabel()
        self._lbl_brand_name.setObjectName("sidebarBrandName")
        self._lbl_brand_tagline = QLabel()
        self._lbl_brand_tagline.setObjectName("sidebarBrandTagline")
        brand_text_lay.addWidget(self._lbl_brand_name)
        brand_text_lay.addWidget(self._lbl_brand_tagline)
        brand_lay.addWidget(logo, 0, Qt.AlignmentFlag.AlignVCenter)
        brand_lay.addWidget(brand_text, 1, Qt.AlignmentFlag.AlignVCenter)
        side_lay.addWidget(brand)

        def _nav_icon(asset_name: str, fallback: QStyle.StandardPixmap) -> QIcon:
            p = _asset_path(asset_name)
            if p.is_file():
                return QIcon(str(p))
            return self.style().standardIcon(fallback)

        def _make_nav_btn(
            *,
            nav_id: str,
            asset_name: str,
            fallback: QStyle.StandardPixmap,
            on_click,
        ) -> QToolButton:
            b = QToolButton()
            b.setObjectName("sideNav")
            b.setProperty("navId", nav_id)
            b.setIcon(_nav_icon(asset_name, fallback))
            b.setIconSize(QSize(22, 22))
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            b.clicked.connect(on_click)
            return b

        self._btn_footer_home = _make_nav_btn(
            nav_id="navHome",
            asset_name="home.png",
            fallback=QStyle.StandardPixmap.SP_DirHomeIcon,
            on_click=lambda: self._set_main_page(self._IX_CONN),
        )
        self._btn_footer_donations = _make_nav_btn(
            nav_id="navDonations",
            asset_name="donate.png",
            fallback=QStyle.StandardPixmap.SP_DialogApplyButton,
            on_click=lambda: self._set_main_page(self._IX_DONATIONS),
        )
        self._btn_footer_actions = _make_nav_btn(
            nav_id="navActions",
            asset_name="actions.png",
            fallback=QStyle.StandardPixmap.SP_FileDialogContentsView,
            on_click=self.open_actions,
        )
        self._btn_footer_widgets = _make_nav_btn(
            nav_id="navWidgets",
            asset_name="widgets.png",
            fallback=QStyle.StandardPixmap.SP_DesktopIcon,
            on_click=lambda: self._set_main_page(self._IX_WIDGETS),
        )
        self._btn_footer_docks = _make_nav_btn(
            nav_id="navDocks",
            asset_name="docks.png",
            fallback=QStyle.StandardPixmap.SP_TitleBarUnshadeButton,
            on_click=lambda: self._set_main_page(self._IX_DOCKS),
        )
        self._btn_footer_music = _make_nav_btn(
            nav_id="navMusic",
            asset_name="music.png",
            fallback=QStyle.StandardPixmap.SP_MediaPlay,
            on_click=lambda: self._set_main_page(self._IX_MUSIC),
        )
        self._btn_footer_logs = _make_nav_btn(
            nav_id="navLogs",
            asset_name="logs.png",
            fallback=QStyle.StandardPixmap.SP_FileDialogDetailedView,
            on_click=lambda: self._set_main_page(self._IX_LOGS),
        )
        self._btn_footer_chat = _make_nav_btn(
            nav_id="navChat",
            asset_name="chat.png",
            fallback=QStyle.StandardPixmap.SP_MessageBoxInformation,
            on_click=lambda: self._set_main_page(self._IX_CHAT),
        )
        self._btn_footer_tts = _make_nav_btn(
            nav_id="navTts",
            asset_name="tts.png",
            fallback=QStyle.StandardPixmap.SP_MediaVolume,
            on_click=lambda: self._set_main_page(self._IX_AUDIO),
        )

        for btn in (
            self._btn_footer_home,
            self._btn_footer_donations,
            self._btn_footer_actions,
            self._btn_footer_widgets,
            self._btn_footer_docks,
            self._btn_footer_music,
            self._btn_footer_logs,
            self._btn_footer_chat,
            self._btn_footer_tts,
        ):
            side_lay.addWidget(btn)
        side_lay.addStretch(1)
        body.addWidget(self._sidebar_frame, 0)

        right = QVBoxLayout()
        right.setSpacing(0)
        right.setContentsMargins(0, 0, 0, 0)
        body.addLayout(right, stretch=1)

        self._stack = QStackedWidget()
        self._apply_dark_chrome()
        right.addWidget(self._stack, stretch=1)

        self._stack.addWidget(self._qml_conn)
        self._stack.addWidget(self._build_settings_tab())
        self._stack.addWidget(self._build_chat_tab())
        self._stack.addWidget(self._build_audio_tab())
        self._stack.addWidget(self._build_logs_tab())
        self._stack.addWidget(self._qml_donations)
        self._stack.addWidget(self._qml_widgets)
        self._stack.addWidget(self._qml_docks)
        self._stack.addWidget(self._qml_actions)
        self._stack.addWidget(self._build_music_tab())
        self._stack.addWidget(self._build_big_picture_tab())

        self._bp_esc_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self._bp_esc_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        self._bp_esc_shortcut.activated.connect(self._on_big_picture_esc)

        self._footer_frame = QFrame()
        self._footer_frame.setObjectName("appFooter")
        _foot = QHBoxLayout(self._footer_frame)
        _foot.setContentsMargins(14, 8, 14, 8)
        _foot.setSpacing(8)
        self._status_label = QLabel()
        self._status_label.setWordWrap(True)
        self._status_label.setTextFormat(Qt.TextFormat.RichText)
        self._status_label.setObjectName("footerStatus")
        _foot.addWidget(self._status_label, stretch=1, alignment=Qt.AlignmentFlag.AlignTop)
        right.addWidget(self._footer_frame, 0)

        self._qml_api.refresh()
        self._refresh_footer()
        self._apply_in_app_chrome_texts()
        self._stack.currentChanged.connect(self._sync_footer_nav)
        self._sync_footer_nav()

    def _bind_big_picture_qml_context(self, ctx) -> None:
        ctx.setContextProperty("api", self._qml_api)
        ctx.setContextProperty("tiktokAnalytics", self._tiktok_analytics)
        ctx.setContextProperty("twitchAnalytics", self._twitch_analytics)
        ctx.setContextProperty("youtubeAnalytics", self._youtube_analytics)
        ctx.setContextProperty("kickAnalytics", self._kick_analytics)

    def _create_bp_qml_widget(self, qml_name: str) -> QQuickWidget:
        widget = QQuickWidget(self)
        widget.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        widget.setClearColor(QColor(10, 11, 14))
        _setup_qml_import_path(widget)
        self._bind_big_picture_qml_context(widget.rootContext())
        qml_p = _qml_path(qml_name)
        if not qml_p.is_file():
            logger.error("QML not found: %s", qml_p)
        widget.setSource(QUrl.fromLocalFile(str(qml_p)))
        return widget

    def _build_big_picture_tab(self) -> QWidget:
        w = QWidget()
        w.setObjectName("bigPictureRoot")
        w.setStyleSheet("QWidget#bigPictureRoot { background: #080a0f; }")
        lay = QHBoxLayout(w)
        lay.setSpacing(0)
        lay.setContentsMargins(0, 0, 0, 0)

        self._qml_bp_platforms = self._create_bp_qml_widget("BigPicturePlatformsPanel.qml")
        self._qml_bp_platforms.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        chat_col = QWidget()
        chat_col.setObjectName("bigPictureChatHost")
        chat_col.setStyleSheet(
            """
            QWidget#bigPictureChatHost {
                background: #0c0f16;
                border-left: 1px solid #2a3142;
                border-right: 1px solid #2a3142;
            }
            QWidget#bigPictureChatHeaderBar {
                background: #151b27;
                border-bottom: 1px solid #2a3142;
            }
            QLabel#bigPictureChatHeader {
                color: #e8eaed;
                font-size: 13px;
                font-weight: 600;
                padding: 10px 14px;
                background: transparent;
            }
            QWidget#chatToolbar[bpMode="true"] {
                background: #0c0f16;
                border-bottom: 1px solid #1e2430;
            }
            QWidget#chatToolbar[bpMode="true"] QLabel {
                font-size: 11px;
            }
            QWidget#chatToolbar[bpMode="true"] QPushButton {
                font-size: 11px;
                padding: 4px 8px;
            }
            QWidget#chatToolbar[bpMode="true"] QComboBox,
            QWidget#chatToolbar[bpMode="true"] QSpinBox {
                font-size: 11px;
                max-height: 26px;
            }
            QTextEdit#chatMessageView {
                background: #0a0b0e;
                border: none;
                padding: 8px 12px;
            }
            """,
        )
        self._bp_chat_host_layout = QVBoxLayout(chat_col)
        self._bp_chat_host_layout.setSpacing(0)
        self._bp_chat_host_layout.setContentsMargins(10, 10, 10, 10)

        chat_hdr_bar = QWidget()
        chat_hdr_bar.setObjectName("bigPictureChatHeaderBar")
        chat_hdr_lay = QHBoxLayout(chat_hdr_bar)
        chat_hdr_lay.setContentsMargins(0, 0, 0, 0)
        chat_hdr = QLabel()
        chat_hdr.setObjectName("bigPictureChatHeader")
        self._lbl_bp_chat_header = chat_hdr
        chat_hdr_lay.addWidget(chat_hdr)
        self._bp_chat_host_layout.addWidget(chat_hdr_bar)

        chat_body = QWidget()
        chat_body.setObjectName("bigPictureChatBody")
        chat_body.setStyleSheet(
            "QWidget#bigPictureChatBody { background: #0c0f16; "
            "border: 1px solid #2a3142; border-radius: 12px; }",
        )
        self._bp_chat_body_layout = QVBoxLayout(chat_body)
        self._bp_chat_body_layout.setSpacing(0)
        self._bp_chat_body_layout.setContentsMargins(0, 0, 0, 0)
        self._bp_chat_host_layout.addWidget(chat_body, stretch=1)

        self._qml_bp_analytics = self._create_bp_qml_widget("BigPictureAnalyticsPanel.qml")
        self._qml_bp_analytics.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        lay.addWidget(self._qml_bp_platforms, 24)
        lay.addWidget(chat_col, 46)
        lay.addWidget(self._qml_bp_analytics, 30)
        return w

    def _toggle_big_picture(self) -> None:
        if self._big_picture_active:
            self._exit_big_picture()
        else:
            self._enter_big_picture()

    def _on_big_picture_esc(self) -> None:
        if self._big_picture_active:
            self._exit_big_picture()

    def _enter_big_picture(self) -> None:
        if self._big_picture_active:
            return
        self._bp_return_index = self._stack.currentIndex()
        self._bp_saved_geometry = self.saveGeometry()
        self._bp_was_maximized = self.isMaximized()
        self._bp_was_fullscreen = self.isFullScreen()
        self._reparent_chat_to_big_picture()
        self._sidebar_frame.hide()
        self._footer_frame.hide()
        self._set_main_page(self._IX_BIG_PICTURE)
        self._big_picture_active = True
        if hasattr(self, "titleBar") and hasattr(self.titleBar, "bigPictureBtn"):
            try:
                self.titleBar.bigPictureBtn.setChecked(True)
            except RuntimeError:
                pass
        self._qml_api.notify_big_picture_active_changed()
        self._apply_in_app_chrome_texts()
        self.showFullScreen()

    def _exit_big_picture(self) -> None:
        if not self._big_picture_active:
            return
        self._big_picture_active = False
        self._reparent_chat_to_chat_tab()
        self._sidebar_frame.show()
        self._footer_frame.show()
        return_index = self._bp_return_index
        if not (0 <= return_index < self._stack.count()):
            return_index = self._IX_CONN
        self._set_main_page(return_index)
        if self._bp_was_fullscreen:
            self.showFullScreen()
        elif self._bp_was_maximized:
            self.showMaximized()
        else:
            self.showNormal()
            saved = self._bp_saved_geometry
            if saved is not None and not saved.isEmpty():
                self.restoreGeometry(saved)
        if hasattr(self, "titleBar") and hasattr(self.titleBar, "bigPictureBtn"):
            try:
                self.titleBar.bigPictureBtn.setChecked(False)
            except RuntimeError:
                pass
        self._qml_api.notify_big_picture_active_changed()
        self._apply_in_app_chrome_texts()

    def _reparent_chat_to_big_picture(self) -> None:
        if not hasattr(self, "_chat_toolbar") or not hasattr(self, "_bp_chat_body_layout"):
            return
        self._chat_toolbar.setProperty("bpMode", "true")
        self._chat_toolbar.setParent(None)
        self._chat_view.setParent(None)
        self._bp_chat_body_layout.addWidget(self._chat_toolbar)
        self._bp_chat_body_layout.addWidget(self._chat_view, stretch=1)

    def _reparent_chat_to_chat_tab(self) -> None:
        if not hasattr(self, "_chat_page_layout") or not hasattr(self, "_chat_toolbar"):
            return
        self._chat_toolbar.setProperty("bpMode", "false")
        self._chat_toolbar.setParent(None)
        self._chat_view.setParent(None)
        self._chat_page_layout.addWidget(self._chat_toolbar)
        self._chat_page_layout.addWidget(self._chat_view, stretch=1)

    def _toggle_maximized(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _qml_widget_for_stack_index(self, index: int) -> QQuickWidget | None:
        attr = {
            self._IX_CONN: "_qml_conn",
            self._IX_DONATIONS: "_qml_donations",
            self._IX_WIDGETS: "_qml_widgets",
            self._IX_DOCKS: "_qml_docks",
            self._IX_ACTIONS: "_qml_actions",
        }.get(index)
        if attr is None:
            return None
        return getattr(self, attr, None)

    def _bind_qml_context_properties(self, index: int) -> None:
        """Each QQuickWidget must have its own context properties (never share QQmlEngine)."""
        widget = self._qml_widget_for_stack_index(index)
        if widget is None:
            return
        ctx = widget.rootContext()
        if index == self._IX_CONN:
            ctx.setContextProperty("api", self._qml_api)
            ctx.setContextProperty("tiktokAnalytics", self._tiktok_analytics)
            ctx.setContextProperty("twitchAnalytics", self._twitch_analytics)
            ctx.setContextProperty("youtubeAnalytics", self._youtube_analytics)
            ctx.setContextProperty("kickAnalytics", self._kick_analytics)
        elif index == self._IX_DONATIONS:
            ctx.setContextProperty("donApi", self._donations_qml_api)
        elif index == self._IX_WIDGETS:
            ctx.setContextProperty("api", self._widgets_qml_api)
            ctx.setContextProperty("tunnelApi", self._overlay_tunnel_qml_api)
            ctx.setContextProperty("navApi", self._qml_api)
        elif index == self._IX_DOCKS:
            ctx.setContextProperty("dockApi", self._docks_qml_api)
            ctx.setContextProperty("tunnelApi", self._overlay_tunnel_qml_api)
            ctx.setContextProperty("navApi", self._qml_api)
        elif index == self._IX_ACTIONS:
            ctx.setContextProperty("api", self._qml_api)
            ctx.setContextProperty("actApi", self._actions_qml_api)
            ctx.setContextProperty("navApi", self._qml_api)

    def _load_qml_page(self, index: int) -> None:
        """Instantiate one QML tab (each QQuickWidget has its own QQmlEngine/context)."""
        if index in self._qml_pages_loaded:
            return
        widget = self._qml_widget_for_stack_index(index)
        if widget is None:
            return
        if index == self._IX_CONN:
            qml_path = _qml_path("ConnectionsView.qml")
        elif index == self._IX_DONATIONS:
            qml_path = _qml_path("DonationsView.qml")
        elif index == self._IX_WIDGETS:
            qml_path = _qml_path("WidgetsView.qml")
        elif index == self._IX_DOCKS:
            qml_path = _qml_path("DocksView.qml")
        elif index == self._IX_ACTIONS:
            qml_path = _qml_path("ActionsView.qml")
        else:
            return
        if not qml_path.is_file():
            logger.error("QML not found: %s", qml_path)
            return
        self._bind_qml_context_properties(index)
        widget.setSource(QUrl.fromLocalFile(str(qml_path)))
        if index == self._IX_ACTIONS:
            ro_actions = widget.rootObject()
            if ro_actions is not None:
                ro_actions.setProperty("platform", "tiktok")
                ro_actions.setProperty("accountKey", constants.TIKTOK_ACTIONS_ACCOUNT_KEY)
        elif index == self._IX_WIDGETS:
            try:
                local_url = self._overlay_server.base_url() or ""
            except RuntimeError:
                local_url = ""
            self._apply_overlay_urls_to_qml(local_url=local_url)
        self._qml_pages_loaded.add(index)

    def _unload_qml_page(self, index: int) -> None:
        """Drop the QML scene for a tab; Python APIs keep working while the tab is away."""
        if index not in self._qml_pages_loaded:
            return
        widget = self._qml_widget_for_stack_index(index)
        if widget is None:
            return
        widget.setSource(QUrl())
        self._qml_pages_loaded.discard(index)

    def _sync_qml_stack_visibility(self, stack_index: int) -> None:
        """Keep a single QQuickWidget scene alive — hidden tabs must not run in parallel."""
        qml_index = stack_index if stack_index in self._QML_STACK_INDICES else None
        prev = self._active_qml_stack_index
        if prev == qml_index:
            if qml_index is not None:
                self._load_qml_page(qml_index)
            return
        if prev is not None:
            self._unload_qml_page(prev)
        self._active_qml_stack_index = qml_index
        if qml_index is not None:
            self._load_qml_page(qml_index)

    async def _warm_qml_page_cache(self) -> None:
        """Compile every QML tab once after startup, then leave only the visible scene loaded."""
        for index in (
            self._IX_DONATIONS,
            self._IX_WIDGETS,
            self._IX_DOCKS,
            self._IX_ACTIONS,
        ):
            if self._closing:
                return
            self._load_qml_page(index)
            await asyncio.sleep(0)
        current = self._stack.currentIndex()
        for index in list(self._qml_pages_loaded):
            if index != current:
                self._unload_qml_page(index)
        self._active_qml_stack_index = current if current in self._QML_STACK_INDICES else None
        if self._active_qml_stack_index is not None:
            self._load_qml_page(self._active_qml_stack_index)

    def _set_main_page(self, index: int) -> None:
        if not hasattr(self, "_stack") or not (0 <= index < self._stack.count()):
            return
        self._sync_qml_stack_visibility(index)
        self._stack.setCurrentIndex(index)

    def _sync_footer_nav(self, _index: int = 0) -> None:
        """Subtle active state for side nav buttons when the stacked page matches."""
        if not hasattr(self, "_stack") or not hasattr(self, "_btn_footer_chat"):
            return
        on_conn = self._stack.currentIndex() == self._IX_CONN
        on_chat = self._stack.currentIndex() == self._IX_CHAT
        on_tts = self._stack.currentIndex() == self._IX_AUDIO
        on_logs = self._stack.currentIndex() == self._IX_LOGS
        on_don = self._stack.currentIndex() == self._IX_DONATIONS
        on_actions = self._stack.currentIndex() == self._IX_ACTIONS
        on_widgets = self._stack.currentIndex() == self._IX_WIDGETS
        on_docks = self._stack.currentIndex() == self._IX_DOCKS
        on_music = self._stack.currentIndex() == self._IX_MUSIC
        for b, active in (
            (getattr(self, "_btn_footer_home", None), on_conn),
            (getattr(self, "_btn_footer_donations", None), on_don),
            (getattr(self, "_btn_footer_actions", None), on_actions),
            (getattr(self, "_btn_footer_widgets", None), on_widgets),
            (getattr(self, "_btn_footer_docks", None), on_docks),
            (getattr(self, "_btn_footer_music", None), on_music),
            (getattr(self, "_btn_footer_logs", None), on_logs),
            (self._btn_footer_chat, on_chat),
            (self._btn_footer_tts, on_tts),
        ):
            if b is not None:
                b.setProperty("activeNav", "on" if active else "off")
                b.style().unpolish(b)
                b.style().polish(b)
                b.update()
        music_timer = getattr(self, "_music_refresh_timer", None)
        if music_timer is not None:
            if on_music:
                if not music_timer.isActive():
                    music_timer.start()
                self._refresh_music_tab()
            else:
                music_timer.stop()

    def _apply_in_app_chrome_texts(self) -> None:
        if hasattr(self, "titleBar"):
            tb = self.titleBar
            if hasattr(tb, "bigPictureBtn"):
                try:
                    tip = (
                        self._tr("ui.big_picture_exit_tooltip")
                        if self._big_picture_active
                        else self._tr("ui.big_picture_tooltip")
                    )
                    tb.bigPictureBtn.setToolTip(tip)
                except RuntimeError:
                    pass
            if hasattr(tb, "settingsBtn"):
                try:
                    tb.settingsBtn.setToolTip(self._tr("ui.settings_tooltip"))
                except RuntimeError:
                    pass
        if hasattr(self, "_lbl_bp_chat_header"):
            self._lbl_bp_chat_header.setText(self._tr("ui.big_picture_chat"))
        if hasattr(self, "_lbl_brand_name"):
            self._lbl_brand_name.setText(self._tr("ui.brand_name"))
        if hasattr(self, "_lbl_brand_tagline"):
            self._lbl_brand_tagline.setText(self._tr("ui.brand_tagline"))
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
        if hasattr(self, "_btn_footer_actions"):
            ta = self._tr("ui.nav_actions")
            self._btn_footer_actions.setText(ta)
            self._btn_footer_actions.setToolTip(self._tr("ui.nav_actions_hint"))
            self._btn_footer_actions.setAccessibleName(ta)
        if hasattr(self, "_btn_footer_widgets"):
            tw = self._tr("ui.nav_widgets")
            self._btn_footer_widgets.setText(tw)
            self._btn_footer_widgets.setToolTip(self._tr("ui.nav_widgets_hint"))
            self._btn_footer_widgets.setAccessibleName(tw)
        if hasattr(self, "_btn_footer_docks"):
            td = self._tr("ui.nav_docks")
            self._btn_footer_docks.setText(td)
            self._btn_footer_docks.setToolTip(self._tr("ui.nav_docks_hint"))
            self._btn_footer_docks.setAccessibleName(td)
        if hasattr(self, "_btn_footer_music"):
            self._btn_footer_music.setText(self._tr("ui.nav_music"))
            self._btn_footer_music.setToolTip(self._tr("ui.nav_music_hint"))
            self._btn_footer_music.setAccessibleName(self._tr("ui.nav_music"))

    def _apply_dark_chrome(self) -> None:
        self.setStyleSheet(
            # Keep most widgets transparent; paint page roots explicitly for a cohesive backdrop.
            "MainWindow { background-color: #0d0f14; }"
            "QWidget { background-color: transparent; color: #e6e6e6; }"
            "QWidget#connectionsPageRoot { "
            "background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            "stop:0 #0f172a, stop:0.55 #0b1220, stop:1 #070910); }"
            "QWidget#settingsPageRoot { "
            "background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            "stop:0 #0f172a, stop:0.55 #0b1220, stop:1 #070910); }"
            "QWidget#chatPageRoot { "
            "background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            "stop:0 #0f172a, stop:0.55 #0b1220, stop:1 #070910); }"
            "QWidget#musicPageRoot { "
            "background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            "stop:0 #0f172a, stop:0.55 #0b1220, stop:1 #070910); }"
            "QWidget#logsPageRoot { "
            "background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            "stop:0 #0f172a, stop:0.55 #0b1220, stop:1 #070910); }"
            "QWidget#settingsScrollBody { background-color: transparent; }"
            "QFrame#appSidebar { background-color: #080a0e; border: none; "
            "border-right: 1px solid #1a2030; }"
            "QLabel#sidebarBrandName { color: #f3f4f6; font-size: 15px; font-weight: 800; "
            "letter-spacing: 1.2px; }"
            "QLabel#sidebarBrandTagline { color: #8b95a5; font-size: 10px; font-weight: 600; "
            "letter-spacing: 1.6px; }"
            "QToolButton#sideNav { background: transparent; color: #d7deea; "
            "border: none; border-radius: 14px; font-weight: 500; font-size: 15px; "
            "text-align: left; padding: 9px 14px; min-height: 40px; }"
            "QToolButton#sideNav:hover { background: #1a2233; color: #eef2f6; }"
            'QToolButton#sideNav[activeNav="on"] { '
            "background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, "
            "stop:0 #5b3cc8, stop:0.45 #3f3a9a, stop:1 #2f55c8); "
            "color: #ffffff; font-weight: 700; border-radius: 16px; "
            "padding: 18px 14px; min-height: 56px; }"
            "QFrame#appFooter { background-color: #080a0e; border: none; "
            "border-top: 1px solid #1e2430; }"
            "QLabel#footerStatus { color: #b8c0ce; font-size: 11px; }"
            "QGroupBox { border: 1px solid #2a3142; border-radius: 12px; margin-top: 16px; "
            "padding-top: 10px; padding-bottom: 12px; padding-left: 14px; padding-right: 14px; "
            "font-weight: 600; background-color: rgba(18, 22, 32, 210); }"
            "QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; "
            "left: 12px; padding: 1px 8px; color: #e8eaed; font-size: 12px; "
            "background: rgba(8, 10, 14, 170); border-radius: 8px; }"
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
            "border-radius: 10px; padding: 7px 10px; min-height: 36px; }"
            "QComboBox::drop-down { border: none; width: 26px; }"
            "QComboBox::down-arrow { image: none; }"
            "QLabel { color: #d7deea; }"
            "QPushButton { min-height: 36px; }"
            "QCheckBox { min-height: 28px; }"
            "QTextEdit#chatMessageView { background-color: rgba(7, 9, 16, 210); color: #e2e8f0; "
            "border: none; border-radius: 0; padding: 6px 8px; "
            "selection-background-color: #1e3a5f; selection-color: #f8fafc; }"
            "QWidget#chatToolbar { background-color: rgba(10, 11, 14, 200); "
            "border-bottom: 1px solid #1e2430; padding: 6px 10px; }"
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
        page = QWidget()
        page.setObjectName("settingsPageRoot")
        page_lay = QVBoxLayout(page)
        page_lay.setContentsMargins(0, 0, 0, 0)

        center_row = QHBoxLayout()
        center_row.setContentsMargins(12, 12, 12, 12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        body = QWidget()
        body.setObjectName("settingsScrollBody")
        body.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        lay = QVBoxLayout(body)
        lay.setSpacing(14)
        lay.setContentsMargins(0, 0, 0, 0)

        self._gb_settings_general = QGroupBox()
        gen_outer = QVBoxLayout(self._gb_settings_general)
        gen_outer.setContentsMargins(6, 10, 6, 8)
        gen_outer.setSpacing(10)

        lang_row = QHBoxLayout()
        self._lbl_locale = QLabel()
        self._combo_locale = QComboBox()
        self._combo_locale.addItem(self._tr("settings.lang.uk"), "uk")
        self._combo_locale.addItem(self._tr("settings.lang.en"), "en")
        self._combo_locale.currentIndexChanged.connect(self._on_locale_changed)
        lang_row.addWidget(self._lbl_locale)
        lang_row.addWidget(self._combo_locale, stretch=1)
        gen_outer.addLayout(lang_row)

        self._settings_intro = QLabel()
        self._settings_intro.setWordWrap(True)
        gen_outer.addWidget(self._settings_intro)

        self._cb_autostart_twitch = QCheckBox()
        self._cb_autostart_twitch.stateChanged.connect(self._persist_autostart_twitch)
        gen_outer.addWidget(self._cb_autostart_twitch)

        self._cb_autostart_youtube = QCheckBox()
        self._cb_autostart_youtube.stateChanged.connect(self._persist_autostart_youtube)
        gen_outer.addWidget(self._cb_autostart_youtube)

        self._cb_autostart_tiktok = QCheckBox()
        self._cb_autostart_tiktok.stateChanged.connect(self._persist_autostart_tiktok)
        gen_outer.addWidget(self._cb_autostart_tiktok)

        self._cb_autostart_kick = QCheckBox()
        self._cb_autostart_kick.stateChanged.connect(self._persist_autostart_kick)
        gen_outer.addWidget(self._cb_autostart_kick)

        lay.addWidget(self._gb_settings_general)

        self._gb_obs = QGroupBox()
        obs_outer = QVBoxLayout(self._gb_obs)
        obs_outer.setContentsMargins(6, 10, 6, 8)
        obs_outer.setSpacing(10)

        self._lbl_obs_help = self._external_link_label("")
        self._lbl_obs_help.setWordWrap(True)
        self._lbl_obs_help.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )

        obs_grid = QGridLayout()
        obs_grid.setContentsMargins(0, 0, 0, 0)
        obs_grid.setHorizontalSpacing(12)
        obs_grid.setVerticalSpacing(8)
        obs_grid.setColumnStretch(1, 1)
        obs_grid.setColumnMinimumWidth(0, 124)

        row = 0
        obs_grid.addWidget(self._lbl_obs_help, row, 0, 1, 2)
        row += 1

        self._obs_ws_enabled.stateChanged.connect(self._persist_obs_ws_enabled)
        obs_grid.addWidget(self._obs_ws_enabled, row, 0, 1, 2)
        row += 1

        self._lbl_obs_host = MainWindow._obs_settings_label("")
        self._lbl_obs_host.setBuddy(self._obs_ws_host)
        obs_grid.addWidget(self._lbl_obs_host, row, 0)
        obs_grid.addWidget(self._stretch_field(self._obs_ws_host), row, 1)
        row += 1

        self._lbl_obs_port = MainWindow._obs_settings_label("")
        self._lbl_obs_port.setBuddy(self._obs_ws_port)
        self._obs_ws_port.setMaximumWidth(120)
        port_cell = QWidget()
        port_cell_lay = QHBoxLayout(port_cell)
        port_cell_lay.setContentsMargins(0, 0, 0, 0)
        port_cell_lay.setSpacing(0)
        port_cell_lay.addWidget(self._obs_ws_port, stretch=0)
        port_cell_lay.addStretch(1)
        obs_grid.addWidget(self._lbl_obs_port, row, 0)
        obs_grid.addWidget(port_cell, row, 1)
        row += 1

        self._lbl_obs_password = MainWindow._obs_settings_label("")
        self._lbl_obs_password.setBuddy(self._obs_ws_password)
        obs_grid.addWidget(self._lbl_obs_password, row, 0)
        obs_grid.addWidget(self._stretch_field(self._obs_ws_password), row, 1)
        row += 1

        self._btn_obs_ws_test = QPushButton()
        self._btn_obs_ws_test.setMinimumHeight(36)
        self._btn_obs_ws_test.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self._btn_obs_ws_test.clicked.connect(
            lambda: asyncio.ensure_future(self._obs_test_connection_async()),
        )
        obs_grid.addWidget(self._btn_obs_ws_test, row, 0, 1, 2, Qt.AlignmentFlag.AlignLeft)
        row += 1

        self._lbl_obs_test_hint = QLabel()
        self._lbl_obs_test_hint.setWordWrap(True)
        self._lbl_obs_test_hint.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )
        self._lbl_obs_test_hint.setStyleSheet("color: #8b95a5; font-size: 11px;")
        obs_grid.addWidget(self._lbl_obs_test_hint, row, 0, 1, 2)
        row += 1

        self._lbl_obs_test_result = QLabel()
        self._lbl_obs_test_result.setWordWrap(True)
        self._lbl_obs_test_result.setMinimumHeight(1)
        self._lbl_obs_test_result.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )
        self._lbl_obs_test_result.setContentsMargins(0, 2, 0, 4)
        obs_grid.addWidget(self._lbl_obs_test_result, row, 0, 1, 2)

        obs_outer.addLayout(obs_grid)

        lay.addWidget(self._gb_obs)

        self._obs_ws_host.editingFinished.connect(self._persist_obs_ws_host)
        self._obs_ws_port.editingFinished.connect(self._persist_obs_ws_port)
        self._obs_ws_password.editingFinished.connect(self._persist_obs_ws_password)

        self._gb_telegram = QGroupBox()
        tg_outer = QVBoxLayout(self._gb_telegram)
        tg_outer.setContentsMargins(6, 10, 6, 8)
        tg_outer.setSpacing(10)

        tg_grid = QGridLayout()
        tg_grid.setContentsMargins(0, 0, 0, 0)
        tg_grid.setHorizontalSpacing(12)
        tg_grid.setVerticalSpacing(8)
        tg_grid.setColumnStretch(1, 1)
        tg_grid.setColumnMinimumWidth(0, 124)

        tg_row = 0
        tg_grid.addWidget(self._tg_enabled, tg_row, 0, 1, 2)
        tg_row += 1

        self._lbl_tg_token = MainWindow._obs_settings_label("")
        self._lbl_tg_token.setBuddy(self._tg_token)
        tg_grid.addWidget(self._lbl_tg_token, tg_row, 0)
        tg_grid.addWidget(self._stretch_field(self._tg_token), tg_row, 1)
        tg_row += 1

        self._lbl_tg_admin_id = MainWindow._obs_settings_label("")
        self._lbl_tg_admin_id.setBuddy(self._tg_admin_id)
        self._tg_admin_id.setMaximumWidth(220)
        tg_grid.addWidget(self._lbl_tg_admin_id, tg_row, 0)
        tg_grid.addWidget(self._stretch_field(self._tg_admin_id), tg_row, 1)
        tg_row += 1

        tg_grid.addWidget(self._tg_song_requests_enabled, tg_row, 0, 1, 2)
        tg_row += 1

        tg_outer.addLayout(tg_grid)
        lay.addWidget(self._gb_telegram)

        self._gb_ai_shield = QGroupBox()
        self._gb_ai_shield.setTitle(self._tr("settings.ai_shield_group"))
        ai_outer = QVBoxLayout(self._gb_ai_shield)
        ai_outer.setContentsMargins(6, 10, 6, 8)
        ai_outer.setSpacing(10)

        ai_head = QHBoxLayout()
        ai_head.setContentsMargins(0, 0, 0, 0)
        ai_head.setSpacing(10)
        self._lbl_ai_shield_icon = QLabel()
        self._lbl_ai_shield_icon.setFixedSize(40, 40)
        self._lbl_ai_shield_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _ai_pm = QPixmap(str(_asset_path("ai.png")))
        if not _ai_pm.isNull():
            self._lbl_ai_shield_icon.setPixmap(
                _ai_pm.scaled(
                    36,
                    36,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                ),
            )
        ai_head.addWidget(self._lbl_ai_shield_icon, alignment=Qt.AlignmentFlag.AlignTop)
        ai_head.addStretch(1)
        ai_outer.addLayout(ai_head)

        ai_grid = QGridLayout()
        ai_grid.setContentsMargins(0, 0, 0, 0)
        ai_grid.setHorizontalSpacing(12)
        ai_grid.setVerticalSpacing(8)
        ai_grid.setColumnStretch(1, 1)
        ai_grid.setColumnMinimumWidth(0, 124)
        o_row = 0

        self._lbl_ai_shield_tts_caption = QLabel()
        self._lbl_ai_shield_tts_caption.setStyleSheet("color: #8b95a5; font-size: 11px;")
        ai_grid.addWidget(self._lbl_ai_shield_tts_caption, o_row, 0, 1, 2)
        o_row += 1

        self._cb_tts_openai_moderate = QCheckBox()
        self._cb_tts_openai_moderate.stateChanged.connect(self._persist_tts_openai_moderate)
        ai_grid.addWidget(self._cb_tts_openai_moderate, o_row, 0, 1, 2)
        o_row += 1

        self._lbl_openai_api_key = MainWindow._obs_settings_label("")
        self._lbl_openai_api_key.setBuddy(self._openai_api_key)
        ai_grid.addWidget(self._lbl_openai_api_key, o_row, 0)
        ai_grid.addWidget(self._stretch_field(self._openai_api_key), o_row, 1)
        o_row += 1
        self._lbl_openai_api_hint = QLabel()
        self._lbl_openai_api_hint.setWordWrap(True)
        self._lbl_openai_api_hint.setStyleSheet("color: #8b95a5; font-size: 11px;")
        ai_grid.addWidget(self._lbl_openai_api_hint, o_row, 0, 1, 2)
        o_row += 1

        self._lbl_ai_shield_songs_caption = QLabel()
        self._lbl_ai_shield_songs_caption.setStyleSheet("color: #8b95a5; font-size: 11px;")
        ai_grid.addWidget(self._lbl_ai_shield_songs_caption, o_row, 0, 1, 2)
        o_row += 1

        ai_grid.addWidget(self._tg_tiktok_lyrics_filter, o_row, 0, 1, 2)
        o_row += 1

        self._lbl_tg_genius_token = MainWindow._obs_settings_label("")
        self._lbl_tg_genius_token.setBuddy(self._tg_genius_token)
        ai_grid.addWidget(self._lbl_tg_genius_token, o_row, 0)
        ai_grid.addWidget(self._stretch_field(self._tg_genius_token), o_row, 1)
        o_row += 1

        self._lbl_tg_groq_api_key = MainWindow._obs_settings_label("")
        self._lbl_tg_groq_api_key.setBuddy(self._tg_groq_api_key)
        ai_grid.addWidget(self._lbl_tg_groq_api_key, o_row, 0)
        ai_grid.addWidget(self._stretch_field(self._tg_groq_api_key), o_row, 1)
        o_row += 1

        self._lbl_tg_tiktok_filter_hint.setWordWrap(True)
        self._lbl_tg_tiktok_filter_hint.setStyleSheet("color: #8b95a5; font-size: 11px;")
        ai_grid.addWidget(self._lbl_tg_tiktok_filter_hint, o_row, 0, 1, 2)
        o_row += 1

        ai_outer.addLayout(ai_grid)
        lay.addWidget(self._gb_ai_shield)

        self._openai_api_key.editingFinished.connect(self._persist_openai_api_key)

        self._tg_enabled.stateChanged.connect(self._persist_telegram_enabled)
        self._tg_token.editingFinished.connect(self._persist_telegram_token)
        self._tg_admin_id.editingFinished.connect(self._persist_telegram_admin_id)
        self._tg_song_requests_enabled.stateChanged.connect(
            self._persist_telegram_song_requests_enabled
        )
        self._tg_tiktok_lyrics_filter.stateChanged.connect(
            self._persist_telegram_tiktok_lyrics_filter,
        )
        self._tg_genius_token.editingFinished.connect(self._persist_telegram_genius_token)
        self._tg_groq_api_key.editingFinished.connect(self._persist_telegram_groq_api_key)

        self._gb_music = QGroupBox()
        music_outer = QVBoxLayout(self._gb_music)
        music_outer.setContentsMargins(6, 10, 6, 8)
        music_outer.setSpacing(10)

        music_grid = QGridLayout()
        music_grid.setContentsMargins(0, 0, 0, 0)
        music_grid.setHorizontalSpacing(14)
        music_grid.setVerticalSpacing(8)
        music_grid.setColumnStretch(1, 1)
        music_grid.setColumnMinimumWidth(0, 124)

        mr = 0
        music_grid.addWidget(self._music_use_mpv, mr, 0, 1, 2)
        mr += 1
        self._lbl_music_backend_hint.setWordWrap(True)
        self._lbl_music_backend_hint.setStyleSheet("color: #8b95a5; font-size: 11px;")
        music_grid.addWidget(self._lbl_music_backend_hint, mr, 0, 1, 2)
        mr += 1

        self._btn_mpv_check.setMinimumHeight(34)
        self._btn_mpv_check.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        music_grid.addWidget(self._btn_mpv_check, mr, 0, 1, 2, Qt.AlignmentFlag.AlignLeft)
        mr += 1

        self._lbl_mpv_check_result.setWordWrap(True)
        self._lbl_mpv_check_result.setStyleSheet("color: #8b95a5; font-size: 11px;")
        music_grid.addWidget(self._lbl_mpv_check_result, mr, 0, 1, 2)
        mr += 1

        self._lbl_music_max_duration.setBuddy(self._music_max_duration_min)
        music_grid.addWidget(self._lbl_music_max_duration, mr, 0)
        self._music_max_duration_min.setMinimum(0)
        self._music_max_duration_min.setMaximum(240)
        self._music_max_duration_min.setSingleStep(1)
        self._music_max_duration_min.setMinimumHeight(30)
        music_grid.addWidget(self._stretch_field(self._music_max_duration_min), mr, 1)
        mr += 1
        self._lbl_music_max_duration_hint.setWordWrap(True)
        self._lbl_music_max_duration_hint.setStyleSheet("color: #8b95a5; font-size: 11px;")
        music_grid.addWidget(self._lbl_music_max_duration_hint, mr, 0, 1, 2)
        mr += 1

        self._points_enabled_cb.setText(self._tr("settings.points_enabled"))
        music_grid.addWidget(self._points_enabled_cb, mr, 0, 1, 2)
        mr += 1
        self._btn_points_configure.setMinimumHeight(34)
        self._btn_points_configure.setSizePolicy(
            QSizePolicy.Policy.Maximum,
            QSizePolicy.Policy.Fixed,
        )
        music_grid.addWidget(self._btn_points_configure, mr, 0, 1, 2, Qt.AlignmentFlag.AlignLeft)
        mr += 1
        self._lbl_points_hint.setWordWrap(True)
        self._lbl_points_hint.setStyleSheet("color: #8b95a5; font-size: 11px;")
        music_grid.addWidget(self._lbl_points_hint, mr, 0, 1, 2)
        mr += 1

        music_outer.addLayout(music_grid)
        lay.addWidget(self._gb_music)

        self._music_use_mpv.stateChanged.connect(self._persist_music_backend)
        self._btn_mpv_check.clicked.connect(self._check_mpv_installed)
        self._music_max_duration_min.valueChanged.connect(self._persist_music_max_duration_min)
        self._points_enabled_cb.stateChanged.connect(self._persist_points_enabled)
        self._btn_points_configure.clicked.connect(self._open_points_settings_dialog)

        # Updates (Windows: download+launch installer; Linux: redirect to releases).
        self._gb_updates = QGroupBox()
        upd_outer = QVBoxLayout(self._gb_updates)
        upd_outer.setContentsMargins(6, 10, 6, 8)
        upd_outer.setSpacing(10)

        upd_grid = QGridLayout()
        upd_grid.setContentsMargins(0, 0, 0, 0)
        upd_grid.setHorizontalSpacing(14)
        upd_grid.setVerticalSpacing(8)
        upd_grid.setColumnStretch(1, 1)
        upd_grid.setColumnMinimumWidth(0, 124)

        self._cb_updates_check_on_startup = QCheckBox()
        self._cb_updates_check_on_startup.setChecked(
            bool(self._settings.value(_SETTINGS_UPDATES_CHECK_ON_STARTUP, True, bool)),
        )
        self._cb_updates_check_on_startup.stateChanged.connect(
            self._persist_updates_check_on_startup
        )
        upd_grid.addWidget(self._cb_updates_check_on_startup, 0, 0, 1, 2)

        self._btn_updates_check_now = QPushButton()
        self._btn_updates_check_now.setMinimumHeight(34)
        self._btn_updates_check_now.setSizePolicy(
            QSizePolicy.Policy.Maximum,
            QSizePolicy.Policy.Fixed,
        )
        self._btn_updates_check_now.clicked.connect(self._updates_check_now_clicked)
        upd_grid.addWidget(self._btn_updates_check_now, 1, 0, 1, 2, Qt.AlignmentFlag.AlignLeft)

        self._lbl_updates_status = QLabel()
        self._lbl_updates_status.setWordWrap(True)
        self._lbl_updates_status.setStyleSheet("color: #8b95a5; font-size: 11px;")
        upd_grid.addWidget(self._lbl_updates_status, 2, 0, 1, 2)

        upd_outer.addLayout(upd_grid)
        lay.addWidget(self._gb_updates)

        scroll.setWidget(body)
        center_row.addWidget(scroll)
        page_lay.addLayout(center_row, stretch=1)

        self._apply_settings_tab_texts()
        return page

    def _persist_obs_ws_host(self) -> None:
        vv = (self._obs_ws_host.text() or "").strip() or "127.0.0.1"
        self._obs_ws_host.setText(vv)
        self._settings.setValue(constants.SETTINGS_OBS_WS_HOST, vv)

    def _persist_obs_ws_port(self) -> None:
        raw = (self._obs_ws_port.text() or "").strip() or "4455"
        try:
            p = int(raw)
        except ValueError:
            p = 4455
        p = max(1, min(65535, p))
        self._obs_ws_port.setText(str(p))
        self._settings.setValue(constants.SETTINGS_OBS_WS_PORT, p)

    def _persist_obs_ws_password(self) -> None:
        vv = self._obs_ws_password.text() or ""
        if vv.strip():
            keyring_store.set_password(constants.KEY_OBS_WEBSOCKET_PASSWORD, vv)
        else:
            keyring_store.delete_password(constants.KEY_OBS_WEBSOCKET_PASSWORD)

    @Slot(int)
    def _persist_obs_ws_enabled(self, _state: int) -> None:
        self._settings.setValue(
            constants.SETTINGS_OBS_WS_ENABLED,
            bool(self._obs_ws_enabled.isChecked()),
        )

    @Slot(int)
    def _persist_telegram_enabled(self, _state: int) -> None:
        enabled = bool(self._tg_enabled.isChecked())
        self._settings.setValue(_SETTINGS_TELEGRAM_ENABLED, enabled)
        asyncio.ensure_future(self._apply_telegram_from_settings())

    @Slot(int)
    def _persist_tts_openai_moderate(self, _state: int) -> None:
        self._settings.setValue(
            _SETTINGS_TTS_OPENAI_MODERATE,
            self._cb_tts_openai_moderate.isChecked(),
        )

    @Slot(int)
    def _persist_tts_speak_author(self, _state: int) -> None:
        self._settings.setValue(_SETTINGS_TTS_SPEAK_AUTHOR, self._cb_tts_speak_author.isChecked())

    @Slot(int)
    def _persist_tts_strip_non_alpha(self, _state: int) -> None:
        self._settings.setValue(
            _SETTINGS_TTS_STRIP_NON_ALPHA,
            self._cb_tts_strip_non_alpha.isChecked(),
        )

    def _schedule_persist_tts_whitelist(self) -> None:
        if not hasattr(self, "_whitelist_save_timer"):
            self._whitelist_save_timer = QTimer(self)
            self._whitelist_save_timer.setSingleShot(True)
            self._whitelist_save_timer.setInterval(500)
            self._whitelist_save_timer.timeout.connect(self._persist_tts_whitelist)
        self._whitelist_save_timer.start()

    def _persist_tts_whitelist(self) -> None:
        vv = self._edit_tts_whitelist.toPlainText().strip()
        self._settings.setValue(_SETTINGS_TTS_WHITELIST, vv)

    def _persist_openai_api_key(self) -> None:
        vv = self._openai_api_key.text() or ""
        if vv.strip():
            keyring_store.set_password(constants.KEY_OPENAI_API_KEY, vv)
        else:
            keyring_store.delete_password(constants.KEY_OPENAI_API_KEY)

    @Slot(int)
    def _persist_updates_check_on_startup(self, _state: int) -> None:
        self._settings.setValue(
            _SETTINGS_UPDATES_CHECK_ON_STARTUP,
            bool(self._cb_updates_check_on_startup.isChecked()),
        )

    @Slot()
    def _updates_check_now_clicked(self) -> None:
        asyncio.ensure_future(self._check_for_updates(interactive=True))

    async def _check_for_updates(self, interactive: bool) -> None:
        """
        Windows: prompt and download installer.
        Linux: redirect to releases page (manual update).
        """
        from stream_cheremsha.updates.client import fetch_latest_manifest, is_newer_version

        current = self._app_version()
        title = self._tr("dlg.update")
        try:
            manifest = await asyncio.to_thread(fetch_latest_manifest)
        except (OSError, ValueError, httpx.HTTPError, RuntimeError, TypeError) as e:
            if interactive:
                QMessageBox.warning(self, title, str(e))
            return

        latest = manifest.version
        ignored = str(
            self._settings.value(_SETTINGS_UPDATES_IGNORED_VERSION, "", str) or "",
        ).strip()
        self._settings.setValue(
            _SETTINGS_UPDATES_LAST_CHECKED_AT,
            datetime.now(tz=UTC).isoformat(),
        )

        try:
            newer = is_newer_version(latest, current)
        except ValueError:
            newer = False

        if not newer:
            if interactive:
                QMessageBox.information(
                    self,
                    title,
                    self._tr("updates.up_to_date", version=current),
                )
            return
        if ignored and ignored == latest and not interactive:
            return

        if sys.platform.startswith("win"):
            await self._prompt_and_update_windows(manifest, current=current, latest=latest)
        else:
            rel = (
                manifest.platforms.linux.releases_url
                if manifest.platforms.linux is not None
                else ""
            )
            if interactive and rel:
                QDesktopServices.openUrl(QUrl(rel))
            elif interactive:
                QMessageBox.information(self, title, self._tr("updates.redirect_releases"))

    def _app_version(self) -> str:
        try:
            import importlib.metadata

            return str(importlib.metadata.version("stream-cheremsha"))
        except (ImportError, ModuleNotFoundError, RuntimeError):
            return "0.0.0"

    async def _prompt_and_update_windows(self, manifest, current: str, latest: str) -> None:
        from stream_cheremsha.updates.downloader import download_file, sha256_file

        title = self._tr("dlg.update")
        msg = self._tr(
            "updates.available",
            current=current,
            latest=latest,
            url=manifest.changelog_url,
        )

        dlg = QMessageBox(self)
        dlg.setIcon(QMessageBox.Icon.Information)
        dlg.setWindowTitle(title)
        dlg.setText(msg)
        dlg.setTextFormat(Qt.TextFormat.RichText)
        btn_update = dlg.addButton(
            self._tr("updates.btn_update"),
            QMessageBox.ButtonRole.AcceptRole,
        )
        dlg.addButton(self._tr("updates.btn_not_now"), QMessageBox.ButtonRole.RejectRole)
        dlg.setDefaultButton(btn_update)

        # Parent the checkbox to the dialog at construction: PySide6 setCheckBox() does not
        # transfer ownership, so a parentless checkbox is deleted with its Python wrapper
        # while the (C++-owned) dialog lingers — the next theme/style change then rebuilds
        # the dialog layout with a dangling pointer and crashes natively (access violation).
        cb_ignore = QCheckBox(self._tr("updates.ignore_this_version"), dlg)
        dlg.setCheckBox(cb_ignore)

        try:
            await async_dialog_code(dlg)
            clicked = dlg.clickedButton()
            if clicked != btn_update:
                if cb_ignore.isChecked():
                    self._settings.setValue(_SETTINGS_UPDATES_IGNORED_VERSION, latest)
                return
        finally:
            # Destroy the dialog instead of leaving a hidden child of MainWindow that keeps
            # receiving change events for the rest of the session.
            dlg.deleteLater()

        win = manifest.platforms.windows
        if win is None:
            QMessageBox.warning(self, title, self._tr("updates.no_windows_asset"))
            return

        local_app_data = (os.getenv("LOCALAPPDATA") or "").strip()
        base = Path(local_app_data) if local_app_data else Path.home()
        updates_dir = base / "stream-cheremsha" / "updates"
        installer_path = updates_dir / f"Cheremsha-Setup-{manifest.tag}.exe"

        try:
            self._btn_updates_check_now.setEnabled(False)
            self._lbl_updates_status.setText(self._tr("updates.downloading"))
            await asyncio.to_thread(download_file, win.installer.url, installer_path)
            got = await asyncio.to_thread(sha256_file, installer_path)
            if got.lower() != win.installer.sha256.lower():
                try:
                    installer_path.unlink(missing_ok=True)
                except OSError:
                    pass
                QMessageBox.critical(self, title, self._tr("updates.sha_mismatch"))
                return

            if _UPDATES_REQUIRE_SIGNATURE and not self._verify_windows_installer_signature(
                str(installer_path),
            ):
                try:
                    installer_path.unlink(missing_ok=True)
                except OSError:
                    pass
                QMessageBox.critical(self, title, self._tr("updates.signature_invalid"))
                return

            self._lbl_updates_status.setText(self._tr("updates.ready_to_install"))
        finally:
            self._btn_updates_check_now.setEnabled(True)

        # Silent in-place update: the installer reuses the recorded install dir,
        # waits for this process to exit, then relaunches the new version.
        subprocess.Popen([str(installer_path), "/S"], close_fds=True)
        self.close()

    def _verify_windows_installer_signature(self, exe_path: str) -> bool:
        if not sys.platform.startswith("win"):
            return True
        escaped = exe_path.replace("'", "''")
        ps = (
            "$sig = Get-AuthenticodeSignature -FilePath "
            + f"'{escaped}'"
            + ";"
            + "$ok = ($sig.Status -eq 'Valid');"
            + "$sub = '';"
            + "if ($sig.SignerCertificate -ne $null) { $sub = $sig.SignerCertificate.Subject }"
            + ";"
            + f"$pubOk = ($sub -like '*{_UPDATES_EXPECTED_PUBLISHER_SUBJECT_CONTAINS}*');"
            + "if ($ok -and $pubOk) { exit 0 } else { exit 1 }"
        )
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
        except (OSError, subprocess.SubprocessError, ValueError):
            return False
        return r.returncode == 0

    def _persist_telegram_token(self) -> None:
        vv = self._tg_token.text() or ""
        if vv.strip():
            keyring_store.set_password(constants.KEY_TELEGRAM_BOT_TOKEN, vv)
        else:
            keyring_store.delete_password(constants.KEY_TELEGRAM_BOT_TOKEN)
        asyncio.ensure_future(self._apply_telegram_from_settings())

    def _persist_telegram_admin_id(self) -> None:
        raw = (self._tg_admin_id.text() or "").strip()
        if raw and not raw.isdigit():
            raw = "".join([c for c in raw if c.isdigit()])
        self._tg_admin_id.setText(raw)
        self._settings.setValue(_SETTINGS_TELEGRAM_ADMIN_ID, raw)
        asyncio.ensure_future(self._apply_telegram_from_settings())

    @Slot(int)
    def _persist_telegram_song_requests_enabled(self, _state: int) -> None:
        enabled = bool(self._tg_song_requests_enabled.isChecked())
        self._settings.setValue(_SETTINGS_TELEGRAM_SONG_REQUESTS_ENABLED, enabled)
        asyncio.ensure_future(self._apply_telegram_from_settings())

    def _persist_telegram_tiktok_lyrics_filter(self, _state: int) -> None:
        self._settings.setValue(
            _SETTINGS_TELEGRAM_TIKTOK_LYRICS_FILTER,
            bool(self._tg_tiktok_lyrics_filter.isChecked()),
        )

    def _persist_telegram_genius_token(self) -> None:
        vv = self._tg_genius_token.text() or ""
        if vv.strip():
            keyring_store.set_password(constants.KEY_GENIUS_CLIENT_ACCESS_TOKEN, vv)
        else:
            keyring_store.delete_password(constants.KEY_GENIUS_CLIENT_ACCESS_TOKEN)

    def _persist_telegram_groq_api_key(self) -> None:
        vv = self._tg_groq_api_key.text() or ""
        if vv.strip():
            keyring_store.set_password(constants.KEY_GROQ_API_KEY, vv)
            keyring_store.delete_password(constants.KEY_LEGACY_GEMINI_API_KEY)
        else:
            keyring_store.delete_password(constants.KEY_GROQ_API_KEY)
            keyring_store.delete_password(constants.KEY_LEGACY_GEMINI_API_KEY)

    @Slot(int)
    def _persist_music_backend(self, _state: int) -> None:
        backend = "mpv" if bool(self._music_use_mpv.isChecked()) else "app"
        self._settings.setValue(_SETTINGS_MUSIC_BACKEND, backend)
        self._refresh_mpv_check_label()
        asyncio.ensure_future(self._apply_music_backend_from_settings())

    @Slot(int)
    def _persist_music_volume(self, value: int) -> None:
        v = max(0, min(100, int(value)))
        self._settings.setValue("music/volume_percent", v)
        mp = self._music_player
        if mp is not None:
            mp.set_volume_percent(v)

    async def _music_toggle_pause(self) -> None:
        mp = self._music_player
        if mp is None:
            return
        await mp.toggle_pause()

    async def _music_next(self) -> None:
        mp = self._music_player
        if mp is None:
            await self._music_queue.skip()
            return
        await mp.skip_now()

    def _refresh_music_tab(self) -> None:
        # IMPORTANT: do not read queue state synchronously (races with asyncio tasks).
        # Always fetch via the async API to get a consistent view.
        if not hasattr(self, "_music_queue_list") or self._closing:
            return
        if getattr(self, "_music_refresh_inflight", False):
            return
        loop = self._asyncio_loop
        if loop is None:
            return
        self._music_refresh_inflight = True

        def _start() -> None:
            asyncio.ensure_future(self._refresh_music_tab_async())

        loop.call_soon(_start)

    async def _refresh_music_tab_async(self) -> None:
        try:
            cur, q = await self._music_queue.list_queue(limit=50)
            now_line = "Now: —"
            if cur is not None:
                title = (cur.title or "").strip()
                vid = (cur.video_id or "").strip()
                rb = (cur.requested_by or "").strip()
                show = title or vid or "—"
                now_line = f"Now: {show}" + (f" (by {rb})" if rb else "")
            if hasattr(self, "_music_now"):
                self._music_now.setText(now_line)

            if hasattr(self, "_music_queue_list"):
                self._music_queue_list.clear()
                for i, t in enumerate(q[:50], start=1):
                    title = (t.title or "").strip()
                    vid = (t.video_id or "").strip()
                    rb = (t.requested_by or "").strip()
                    text = f"{i}. {title or vid}"
                    if rb:
                        text += f" — {rb}"
                    self._music_queue_list.addItem(text)
        finally:
            self._music_refresh_inflight = False

    @Slot()
    def _check_mpv_installed(self) -> None:
        self._refresh_mpv_check_label(force=True)

    def _refresh_mpv_check_label(self, *, force: bool = False) -> None:
        if not hasattr(self, "_lbl_mpv_check_result"):
            return
        want_mpv = bool(getattr(self, "_music_use_mpv", None) and self._music_use_mpv.isChecked())
        mpv_path = shutil.which("mpv")
        if mpv_path:
            self._lbl_mpv_check_result.setText(f"mpv: OK ({mpv_path})")
            return
        if want_mpv or force:
            self._lbl_mpv_check_result.setText(
                "mpv: НЕ знайдено. Встанови mpv і додай його в PATH."
            )
        else:
            self._lbl_mpv_check_result.setText("")

    async def _fetch_music_title_for_track(self, track_id: str, video_id: str) -> None:
        vid = (video_id or "").strip()
        if not vid:
            return
        cached = self._music_title_cache.get(vid)
        if cached:
            await self._music_queue.set_track_title(track_id, cached)
            return
        try:
            title = await asyncio.to_thread(fetch_youtube_title, vid)
        except (OSError, ValueError, RuntimeError) as e:
            logger.debug("Music title fetch failed: %s", e)
            return
        title = (title or "").strip()
        if not title:
            return
        self._music_title_cache[vid] = title
        await self._music_queue.set_track_title(track_id, title)

    def _build_connections_tab(self) -> QWidget:
        w = QWidget()
        w.setObjectName("connectionsPageRoot")
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
        self._gb_settings_general.setTitle(self._tr("settings.general_group"))
        self._cb_autostart_twitch.setText(self._tr("settings.autostart_twitch"))
        self._cb_autostart_youtube.setText(self._tr("settings.autostart_youtube"))
        self._cb_autostart_tiktok.setText(self._tr("settings.autostart_tiktok"))
        self._cb_autostart_kick.setText(self._tr("settings.autostart_kick"))
        self._gb_obs.setTitle(self._tr("settings.obs_group"))
        self._lbl_obs_help.setText(self._tr("settings.obs_help_html"))
        self._obs_ws_enabled.setText(self._tr("settings.obs_enabled"))
        self._lbl_obs_host.setText(self._tr("settings.obs_host"))
        self._lbl_obs_port.setText(self._tr("settings.obs_port"))
        self._lbl_obs_password.setText(self._tr("settings.obs_password"))
        self._btn_obs_ws_test.setText(self._tr("settings.obs_test"))
        self._lbl_obs_test_hint.setText(self._tr("settings.obs_test_hint"))

        self._gb_telegram.setTitle(self._tr("settings.telegram_group"))
        self._tg_enabled.setText(self._tr("settings.telegram_enabled"))
        self._lbl_tg_token.setText(self._tr("settings.telegram_token"))
        self._lbl_tg_admin_id.setText(self._tr("settings.telegram_admin_id"))
        self._tg_song_requests_enabled.setText(self._tr("settings.telegram_song_requests"))
        self._gb_ai_shield.setTitle(self._tr("settings.ai_shield_group"))
        self._lbl_ai_shield_tts_caption.setText(self._tr("settings.ai_shield_section_tts"))
        self._cb_tts_openai_moderate.setText(self._tr("audio.openai_moderate"))
        self._cb_tts_openai_moderate.setToolTip(self._tr("audio.openai_moderate_hint"))
        self._lbl_openai_api_key.setText(self._tr("settings.openai_api_key"))
        self._lbl_openai_api_hint.setText(self._tr("settings.openai_api_key_hint"))
        self._lbl_ai_shield_songs_caption.setText(self._tr("settings.ai_shield_section_songs"))
        self._tg_tiktok_lyrics_filter.setText(self._tr("settings.telegram_tiktok_lyrics_filter"))
        self._lbl_tg_genius_token.setText(self._tr("settings.telegram_genius_token"))
        self._lbl_tg_groq_api_key.setText(self._tr("settings.telegram_groq_api_key"))
        self._lbl_tg_tiktok_filter_hint.setText(self._tr("settings.telegram_tiktok_filter_hint"))

        self._gb_music.setTitle(self._tr("settings.music_group"))
        self._music_use_mpv.setText(self._tr("settings.music_open_in_mpv"))
        self._lbl_music_backend_hint.setText(self._tr("settings.music_backend_hint"))
        self._lbl_music_max_duration.setText(self._tr("settings.music_max_duration"))
        self._lbl_music_max_duration_hint.setText(self._tr("settings.music_max_duration_hint"))
        self._btn_mpv_check.setText(self._tr("settings.music_check_mpv"))
        self._points_enabled_cb.setText(self._tr("settings.points_enabled"))
        self._btn_points_configure.setText(self._tr("settings.points_configure"))
        self._lbl_points_hint.setText(self._tr("settings.points_hint"))

        self._gb_updates.setTitle(self._tr("settings.updates_group"))
        self._cb_updates_check_on_startup.setText(self._tr("settings.updates_check_on_startup"))
        self._btn_updates_check_now.setText(self._tr("settings.updates_check_now"))
        self._lbl_updates_status.setText("")

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
        self._schedule_king_overlay_publish()
        self._schedule_battle_overlay_publish()
        if hasattr(self, "_live_leaderboard") and self._live_leaderboard is not None:
            self._live_leaderboard.schedule_publish()
        if hasattr(self, "_webcam_frame") and self._webcam_frame is not None:
            self._webcam_frame.schedule_publish()

    def _retranslate_ui(self) -> None:
        self.setWindowTitle(self._tr("app.window_title"))
        self._apply_settings_tab_texts()
        self._apply_connections_tab_texts()
        self._apply_audio_tab_texts()
        self._apply_logs_tab_texts()
        self._apply_chat_tab_texts()
        self._apply_music_tab_texts()
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
        await self._stop_twitch_analytics()
        twitch_credentials.clear_twitch_session()
        self._twitch_token.clear()
        self._on_user_status(self._tr("status.logout_twitch"))
        self._refresh_connection_panels()

    @Slot()
    def _logout_youtube(self) -> None:
        asyncio.ensure_future(self._async_logout_youtube())

    async def _async_logout_youtube(self) -> None:
        await self._youtube.stop()
        self._youtube_analytics.resetSession()
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
        w.setObjectName("chatPageRoot")
        self._chat_page_root = w
        lay = QVBoxLayout(w)
        self._chat_page_layout = lay
        lay.setSpacing(0)
        lay.setContentsMargins(0, 0, 0, 0)

        bar = QWidget()
        bar.setObjectName("chatToolbar")
        self._chat_toolbar = bar
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
        w.setObjectName("logsPageRoot")
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

    def _build_music_tab(self) -> QWidget:
        w = QWidget()
        w.setObjectName("musicPageRoot")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(12)

        self._music_title_label = QLabel(self._tr("music.title"))
        self._music_title_label.setStyleSheet("color: #e8eaed; font-size: 18px; font-weight: 600;")
        lay.addWidget(self._music_title_label)

        self._music_now = QLabel("Now: —")
        self._music_now.setWordWrap(True)
        lay.addWidget(self._music_now)

        self._music_queue_list = QListWidget()
        self._music_queue_list.setMinimumHeight(220)
        lay.addWidget(self._music_queue_list, stretch=1)

        controls = QHBoxLayout()
        self._btn_music_play_pause = QPushButton(self._tr("music.play_pause"))
        self._btn_music_next = QPushButton(self._tr("music.next"))
        self._btn_music_play_pause.clicked.connect(
            lambda: asyncio.ensure_future(self._music_toggle_pause())
        )
        self._btn_music_next.clicked.connect(lambda: asyncio.ensure_future(self._music_next()))
        controls.addWidget(self._btn_music_play_pause)
        controls.addWidget(self._btn_music_next)
        controls.addStretch(1)

        self._music_vol = QSlider(Qt.Orientation.Horizontal)
        self._music_vol.setMinimum(0)
        self._music_vol.setMaximum(100)
        self._music_vol.setValue(int(self._settings.value("music/volume_percent", 100)))
        self._music_vol.valueChanged.connect(self._persist_music_volume)
        controls.addWidget(QLabel(self._tr("music.volume")))
        controls.addWidget(self._music_vol, stretch=1)
        lay.addLayout(controls)

        self._music_refresh_timer = QTimer(self)
        self._music_refresh_timer.setInterval(2000)
        self._music_refresh_timer.timeout.connect(self._refresh_music_tab)
        self._apply_music_tab_texts()
        return w

    def _apply_music_tab_texts(self) -> None:
        if not hasattr(self, "_btn_music_play_pause"):
            return
        if hasattr(self, "_music_title_label"):
            self._music_title_label.setText(self._tr("music.title"))
        if hasattr(self, "_btn_music_play_pause"):
            self._btn_music_play_pause.setText(self._tr("music.play_pause"))
        if hasattr(self, "_btn_music_next"):
            self._btn_music_next.setText(self._tr("music.next"))

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
        tw, yt, tk, kk = load_platform_icon_data_uris(_STREAM_ROOT / "assets")
        self._chat_ic_tw = tw
        self._chat_ic_yt = yt
        self._chat_ic_tk = tk
        self._chat_ic_kk = kk

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
            kick_icon_uri=self._chat_ic_kk,
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
        pop = self._chat_popout
        if pop is not None and shiboken6.isValid(pop):
            pop.clear_view()

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

        # --- TTS language & engine ---
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
        self._combo_tts_engine.addItem("", _TTS_ENGINE_EDGE)
        self._combo_tts_engine.addItem("", _TTS_ENGINE_RESPEECHER)
        self._combo_tts_engine.currentIndexChanged.connect(self._on_tts_engine_changed)
        self._engine_row = QWidget()
        er = QHBoxLayout(self._engine_row)
        er.setContentsMargins(0, 0, 0, 0)
        er.addWidget(self._combo_tts_engine, stretch=1)
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
            lambda: asyncio.ensure_future(self._flush_tts_queues()),
        )
        tts_body.addWidget(self._btn_audio_flush_queues)
        self._cb_tts_speak_author = QCheckBox()
        self._cb_tts_speak_author.stateChanged.connect(self._persist_tts_speak_author)
        tts_body.addWidget(self._cb_tts_speak_author)
        self._cb_tts_strip_non_alpha = QCheckBox()
        self._cb_tts_strip_non_alpha.stateChanged.connect(self._persist_tts_strip_non_alpha)
        tts_body.addWidget(self._cb_tts_strip_non_alpha)

        self._lbl_tts_whitelist = QLabel()
        self._edit_tts_whitelist = QTextEdit()
        self._edit_tts_whitelist.setPlaceholderText(self._tr("audio.tts_whitelist_ph"))
        self._edit_tts_whitelist.setMaximumHeight(80)
        self._edit_tts_whitelist.textChanged.connect(self._schedule_persist_tts_whitelist)
        whitelist_form = QFormLayout()
        whitelist_form.setContentsMargins(0, 0, 0, 0)
        whitelist_form.setHorizontalSpacing(10)
        whitelist_form.setVerticalSpacing(8)
        whitelist_form.addRow(self._lbl_tts_whitelist, self._edit_tts_whitelist)
        tts_body.addLayout(whitelist_form)

        self._lbl_tts_rate = QLabel()
        self._tts_rate_spin = QSpinBox()
        self._tts_rate_spin.setRange(_TTS_RATE_MIN, _TTS_RATE_MAX)
        self._tts_rate_spin.setSingleStep(5)
        self._tts_rate_spin.setSuffix(" %")
        self._tts_rate_spin.setValue(self._tts_rate_percent_from_settings())
        self._tts_rate_spin.valueChanged.connect(self._on_tts_rate_changed)
        rate_form = QFormLayout()
        rate_form.setContentsMargins(0, 0, 0, 0)
        rate_form.setHorizontalSpacing(10)
        rate_form.setVerticalSpacing(8)
        rate_form.addRow(self._lbl_tts_rate, self._tts_rate_spin)
        tts_body.addLayout(rate_form)
        main_lay.addWidget(self._frm_audio_tts)

        # --- Edge card (voice selection per language) ---
        self._frm_edge_voice, edge_body, self._lbl_audio_edge_card_h = self._make_audio_card(
            "#22c55e",
        )
        self._lbl_edge_voice = QLabel()
        self._combo_edge_voice = QComboBox()
        self._combo_edge_voice.currentIndexChanged.connect(self._on_edge_voice_changed)
        self._cb_edge_randomize = QCheckBox()
        self._cb_edge_randomize.toggled.connect(self._on_edge_randomize_changed)
        edge_form = QFormLayout()
        edge_form.setContentsMargins(0, 0, 0, 0)
        edge_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        edge_form.setHorizontalSpacing(10)
        edge_form.setVerticalSpacing(8)
        edge_form.addRow(self._lbl_edge_voice, self._combo_edge_voice)
        edge_form.addRow(self._tr("audio.tts_randomize_voice"), self._cb_edge_randomize)
        edge_body.addLayout(edge_form)
        main_lay.addWidget(self._frm_edge_voice)

        # --- ReSpeecher card (voice selection per language) ---
        self._frm_respeecher_voice, respeecher_body, self._lbl_audio_respeecher_card_h = (
            self._make_audio_card(
                "#a855f7",
            )
        )
        self._lbl_respeecher_voice = QLabel()
        self._combo_respeecher_voice = QComboBox()
        # Populate with the 13 Ukrainian voices
        for voice_id, voice_label in REPEECHER_VOICES.items():
            self._combo_respeecher_voice.addItem(voice_label, voice_id)
        self._combo_respeecher_voice.currentIndexChanged.connect(self._on_respeecher_voice_changed)
        self._cb_respeecher_randomize = QCheckBox()
        self._cb_respeecher_randomize.toggled.connect(self._on_respeecher_randomize_changed)
        respeecher_form = QFormLayout()
        respeecher_form.setContentsMargins(0, 0, 0, 0)
        respeecher_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        respeecher_form.setHorizontalSpacing(10)
        respeecher_form.setVerticalSpacing(8)
        respeecher_form.addRow(self._lbl_respeecher_voice, self._combo_respeecher_voice)
        respeecher_form.addRow(self._tr("audio.tts_randomize_voice"), self._cb_respeecher_randomize)
        respeecher_body.addLayout(respeecher_form)
        main_lay.addWidget(self._frm_respeecher_voice)

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
        self._combo_tts_engine.setItemText(1, self._tr("audio.tts_engine_edge"))
        self._combo_tts_engine.setItemText(2, self._tr("audio.tts_engine_respeecher"))
        self._btn_audio_flush_queues.setText(self._tr("audio.flush_queues"))
        self._btn_audio_flush_queues.setToolTip(self._tr("audio.flush_queues_hint"))
        self._lbl_audio_tts_card_h.setText(self._tr("audio.card_tts_title"))
        self._cb_tts_speak_author.setText(self._tr("audio.speak_author_name"))
        self._cb_tts_speak_author.setToolTip(self._tr("audio.speak_author_name_hint"))
        self._cb_tts_strip_non_alpha.setText(self._tr("audio.strip_non_alpha"))
        self._cb_tts_strip_non_alpha.setToolTip(self._tr("audio.strip_non_alpha_hint"))
        self._lbl_tts_whitelist.setText(self._tr("audio.tts_whitelist"))
        self._lbl_tts_whitelist.setToolTip(self._tr("audio.tts_whitelist_hint"))
        self._edit_tts_whitelist.setToolTip(self._tr("audio.tts_whitelist_hint"))
        self._edit_tts_whitelist.setPlaceholderText(self._tr("audio.tts_whitelist_ph"))
        self._lbl_tts_rate.setText(self._tr("audio.tts_rate"))
        _rate_tip = self._tr("audio.tts_rate_tip")
        self._tts_rate_spin.setToolTip(_rate_tip)
        self._lbl_tts_rate.setToolTip(_rate_tip)
        self._lbl_audio_edge_card_h.setText(self._tr("audio.edge_voice_group"))
        self._lbl_edge_voice.setText(self._tr("audio.edge_voice_label"))
        self._cb_edge_randomize.setText(self._tr("audio.tts_randomize_voice"))
        self._cb_edge_randomize.setToolTip(self._tr("audio.tts_randomize_voice_hint"))
        self._lbl_audio_respeecher_card_h.setText(self._tr("audio.respeecher_voice_group"))
        self._lbl_respeecher_voice.setText(self._tr("audio.respeecher_voice_label"))
        self._cb_respeecher_randomize.setText(self._tr("audio.tts_randomize_voice"))
        self._cb_respeecher_randomize.setToolTip(self._tr("audio.tts_randomize_voice_hint"))
        self._update_tts_engine_related_visibility()
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

    def _update_tts_engine_related_visibility(self) -> None:
        eng = self._combo_tts_engine.currentData()
        use_edge = eng == _TTS_ENGINE_EDGE
        use_respeecher = eng == _TTS_ENGINE_RESPEECHER
        self._frm_edge_voice.setVisible(use_edge)
        self._frm_respeecher_voice.setVisible(use_respeecher)

    def _sync_tts_engine_combo_to_backend(self) -> None:
        """Combo reflects saved engine (not live ``self._tts``)."""
        raw_eng = str(self._settings.value(_SETTINGS_TTS_ENGINE, _TTS_ENGINE_GOOGLE, str))
        gid = raw_eng.strip().lower()
        self._combo_tts_engine.blockSignals(True)
        if gid == _TTS_ENGINE_EDGE:
            idx = 1
        elif gid == _TTS_ENGINE_RESPEECHER:
            idx = 2
        else:
            idx = 0
        self._combo_tts_engine.setCurrentIndex(idx)
        self._combo_tts_engine.blockSignals(False)
        self._update_tts_engine_related_visibility()

    @Slot(int)
    def _on_tts_engine_changed(self, _index: int) -> None:
        eng = self._combo_tts_engine.currentData()
        self._settings.setValue(_SETTINGS_TTS_ENGINE, eng)
        self._update_tts_engine_related_visibility()
        if eng == _TTS_ENGINE_EDGE:
            asyncio.ensure_future(self._refresh_edge_voices_for_current_language())
        elif eng == _TTS_ENGINE_RESPEECHER:
            # No voice refresh needed for ReSpeecher at this time
            pass
        asyncio.ensure_future(self._swap_tts_backend())

    @Slot(int)
    def _on_tts_language_changed(self, _index: int) -> None:
        tag = self._combo_tts_lang.currentData()
        if isinstance(tag, str) and tag.strip():
            self._settings.setValue(_SETTINGS_TTS_LANG, tag.strip())
        eng = self._combo_tts_engine.currentData()
        if eng == _TTS_ENGINE_EDGE:
            asyncio.ensure_future(self._refresh_edge_voices_for_current_language())
            asyncio.ensure_future(self._swap_tts_backend())
            return
        if eng == _TTS_ENGINE_RESPEECHER:
            asyncio.ensure_future(self._swap_tts_backend())
            return
        if eng == _TTS_ENGINE_GOOGLE:
            asyncio.ensure_future(self._swap_tts_backend())

    def _load_edge_voice_map(self) -> dict[str, str]:
        raw = str(self._settings.value(_SETTINGS_EDGE_VOICE_BY_LANG, "{}", str) or "").strip()
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            return {}
        if not isinstance(data, dict):
            return {}
        out: dict[str, str] = {}
        for k, v in data.items():
            if isinstance(k, str) and isinstance(v, str) and k.strip() and v.strip():
                out[k.strip()] = v.strip()
        return out

    def _save_edge_voice_map(self, m: dict[str, str]) -> None:
        cleaned: dict[str, str] = {}
        for k, v in m.items():
            if isinstance(k, str) and isinstance(v, str) and k.strip() and v.strip():
                cleaned[k.strip()] = v.strip()
        payload = json.dumps(cleaned, ensure_ascii=False)
        self._settings.setValue(_SETTINGS_EDGE_VOICE_BY_LANG, payload)

    async def _refresh_edge_voices_for_current_language(self) -> None:
        if not hasattr(self, "_combo_edge_voice"):
            return
        async with self._edge_voices_refresh_lock:
            lang = self._current_tts_language()
            self._combo_edge_voice.setEnabled(False)
            self._combo_edge_voice.blockSignals(True)
            self._combo_edge_voice.clear()
            self._combo_edge_voice.blockSignals(False)
            prev_pipeline = self._status_app
            self._on_user_status(self._tr("status.edge_voices_loading"))
            try:
                all_voices = await list_edge_voices_cached()
                voices = filter_edge_voices_for_locale(all_voices, lang)
            except (ImportError, OSError, RuntimeError, ValueError) as e:
                logger.warning(
                    "Edge voices UI refresh failed (locale=%r): %s: %s",
                    lang,
                    type(e).__name__,
                    e,
                    exc_info=True,
                )
                self._on_user_status(self._tr("status.edge_voices_failed"))
                self._combo_edge_voice.setEnabled(False)
                return

            logger.info(
                "Edge voices for locale %r: %d in combo (of %d total from API)",
                lang,
                len(voices),
                len(all_voices),
            )
            if not voices and all_voices:
                logger.warning(
                    "Edge TTS: no voices match locale %r; check TTS language vs Edge locale tag",
                    lang,
                )

            self._combo_edge_voice.blockSignals(True)
            try:
                for v in voices:
                    self._combo_edge_voice.addItem(v.label, v.short_name)
            finally:
                self._combo_edge_voice.blockSignals(False)

            m = self._load_edge_voice_map()
            want = m.get(lang, "")
            idx = 0
            if want:
                for i in range(self._combo_edge_voice.count()):
                    if self._combo_edge_voice.itemData(i) == want:
                        idx = i
                        break
            self._combo_edge_voice.setCurrentIndex(idx if self._combo_edge_voice.count() else -1)
            chosen = self._combo_edge_voice.currentData()
            if isinstance(chosen, str) and chosen.strip():
                m[lang] = chosen.strip()
                self._save_edge_voice_map(m)
            self._combo_edge_voice.setEnabled(self._combo_edge_voice.count() > 0)
            self._on_user_status(prev_pipeline)

    @Slot(int)
    def _on_edge_voice_changed(self, _index: int) -> None:
        if not hasattr(self, "_combo_edge_voice"):
            return
        voice = self._combo_edge_voice.currentData()
        if not isinstance(voice, str) or not voice.strip():
            return
        lang = self._current_tts_language()
        m = self._load_edge_voice_map()
        m[lang] = voice.strip()
        self._save_edge_voice_map(m)
        if self._combo_tts_engine.currentData() == _TTS_ENGINE_EDGE:
            asyncio.ensure_future(self._swap_tts_backend())

    def _on_respeecher_voice_changed(self, _index: int) -> None:
        # When voice changes, swap the backend to use the new voice
        if self._combo_tts_engine.currentData() == _TTS_ENGINE_RESPEECHER:
            asyncio.ensure_future(self._swap_tts_backend())

    @Slot(bool)
    def _on_edge_randomize_changed(self, checked: bool) -> None:
        self._settings.setValue(_SETTINGS_TTS_RANDOMIZE_EDGE, checked)
        if self._combo_tts_engine.currentData() == _TTS_ENGINE_EDGE:
            asyncio.ensure_future(self._swap_tts_backend())

    @Slot(bool)
    def _on_respeecher_randomize_changed(self, checked: bool) -> None:
        self._settings.setValue(_SETTINGS_TTS_RANDOMIZE_RESPEECHER, checked)
        if self._combo_tts_engine.currentData() == _TTS_ENGINE_RESPEECHER:
            asyncio.ensure_future(self._swap_tts_backend())

    def eventFilter(self, watched: QObject, event: QEvent | None) -> bool:  # noqa: N802
        return super().eventFilter(watched, event)

    async def _swap_tts_backend(self) -> None:
        from stream_cheremsha.tts.edge_tts import RandomizedEdgeTts
        from stream_cheremsha.tts.google_translate_tts import GoogleTranslateTts
        from stream_cheremsha.tts.respeecher_tts import (
            REPEECHER_VOICES,
            RandomizedReSpeecherTts,
        )

        eng = self._combo_tts_engine.currentData()
        new_tts: TextToSpeech

        def _revert_to_google_combo() -> None:
            self._combo_tts_engine.blockSignals(True)
            self._combo_tts_engine.setCurrentIndex(0)
            self._combo_tts_engine.blockSignals(False)
            self._settings.setValue(_SETTINGS_TTS_ENGINE, _TTS_ENGINE_GOOGLE)
            self._update_tts_engine_related_visibility()

        lang = self._current_tts_language()
        rate_percent = self._tts_rate_percent_from_settings()
        randomize_edge = hasattr(self, "_cb_edge_randomize") and self._cb_edge_randomize.isChecked()
        randomize_respeecher = (
            hasattr(self, "_cb_respeecher_randomize") and self._cb_respeecher_randomize.isChecked()
        )

        if eng == _TTS_ENGINE_EDGE:
            if randomize_edge:
                try:
                    new_tts = RandomizedEdgeTts(
                        locale=lang, rate=self._edge_rate_string(rate_percent)
                    )
                except ValueError:
                    self._on_user_status(self._tr("status.edge_voices_failed"))
                    new_tts = GoogleTranslateTts(language=lang, rate_percent=rate_percent)
            else:
                voice = None
                if hasattr(self, "_combo_edge_voice"):
                    cd = self._combo_edge_voice.currentData()
                    if isinstance(cd, str) and cd.strip():
                        voice = cd.strip()
                if not voice:
                    m = self._load_edge_voice_map()
                    voice = (m.get(lang, "") or "").strip() or None
                if not voice:
                    self._on_user_status(self._tr("status.edge_voices_failed"))
                    new_tts = GoogleTranslateTts(language=lang, rate_percent=rate_percent)
                else:
                    try:
                        new_tts = EdgeTts(voice, rate=self._edge_rate_string(rate_percent))
                    except (ImportError, ValueError, OSError) as e:
                        QMessageBox.warning(self, self._tr("dlg.tts"), str(e))
                        _revert_to_google_combo()
                        new_tts = GoogleTranslateTts(language=lang, rate_percent=rate_percent)
        elif eng == _TTS_ENGINE_RESPEECHER:
            if randomize_respeecher:
                new_tts = RandomizedReSpeecherTts(
                    rate_percent=rate_percent,
                    fallback_tts=EdgeTts(voice="olesia-conversation"),
                    min_interval_sec=self._min_interval_sec_from_settings(),
                )
            else:
                # Get voice ID from the UI combo (if available) or default
                voice = _TTS_DEFAULT_VOICE_ID
                if hasattr(self, "_combo_respeecher_voice"):
                    cd = self._combo_respeecher_voice.currentData()
                    if isinstance(cd, str) and cd.strip():
                        voice = cd.strip()
                # Validate voice is in our supported list
                if voice not in REPEECHER_VOICES:
                    voice = _TTS_DEFAULT_VOICE_ID
                # Instantiate ReSpeecherTts with Edge TTS as fallback
                fallback = EdgeTts(voice=_TTS_DEFAULT_VOICE_ID)
                new_tts = ReSpeecherTts(
                    voice=voice,
                    rate_percent=rate_percent,
                    fallback_tts=fallback,
                    min_interval_sec=self._min_interval_sec_from_settings(),
                )
        else:
            new_tts = GoogleTranslateTts(language=lang, rate_percent=rate_percent)

        old = self._tts
        oid = getattr(old, "ENGINE_ID", "")
        nid = getattr(new_tts, "ENGINE_ID", "")
        if oid == nid == _TTS_ENGINE_GOOGLE:
            old_lang = getattr(old, "language", None)
            new_lang = getattr(new_tts, "language", None)
            old_rate = getattr(old, "rate_percent", None)
            new_rate = getattr(new_tts, "rate_percent", None)
            if old_lang == new_lang and old_rate == new_rate:
                return
        if oid == nid == _TTS_ENGINE_EDGE:
            same_voice = getattr(old, "voice", None) == getattr(new_tts, "voice", None)
            same_rate = getattr(old, "rate", None) == getattr(new_tts, "rate", None)
            if same_voice and same_rate:
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
        self._cb_autostart_tiktok.blockSignals(True)
        self._cb_autostart_tiktok.setChecked(
            bool(self._settings.value(_SETTINGS_AUTOSTART_TIKTOK, False, bool)),
        )
        self._cb_autostart_tiktok.blockSignals(False)

        self._cb_autostart_kick.blockSignals(True)
        self._cb_autostart_kick.setChecked(
            bool(self._settings.value(_SETTINGS_AUTOSTART_KICK, False, bool)),
        )
        self._cb_autostart_kick.blockSignals(False)

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

        if hasattr(self, "_combo_tts_engine"):
            self._sync_tts_engine_combo_to_backend()
            if self._combo_tts_engine.currentData() == _TTS_ENGINE_EDGE:
                asyncio.ensure_future(self._refresh_edge_voices_for_current_language())

        if hasattr(self, "_tts_gain_spin"):
            gv = int(self._settings.value(_SETTINGS_TTS_GAIN_DB, 14))
            self._tts_gain_spin.blockSignals(True)
            self._tts_gain_spin.setValue(max(0, min(36, gv)))
            self._tts_gain_spin.blockSignals(False)
            self._sink.set_tts_gain_db(self._tts_gain_spin.value())

        if hasattr(self, "_tts_rate_spin"):
            self._tts_rate_spin.blockSignals(True)
            self._tts_rate_spin.setValue(self._tts_rate_percent_from_settings())
            self._tts_rate_spin.blockSignals(False)
        self._load_chat_font_from_settings()

        obs_ws_on = bool(self._settings.value(constants.SETTINGS_OBS_WS_ENABLED, True, bool))
        self._obs_ws_enabled.blockSignals(True)
        self._obs_ws_enabled.setChecked(obs_ws_on)
        self._obs_ws_enabled.blockSignals(False)

        obs_host = str(
            self._settings.value(constants.SETTINGS_OBS_WS_HOST, "127.0.0.1", str) or "",
        ).strip()
        self._obs_ws_host.setText(obs_host or "127.0.0.1")
        obs_port_raw = self._settings.value(constants.SETTINGS_OBS_WS_PORT, 4455)
        try:
            obs_port_i = int(obs_port_raw)
        except (TypeError, ValueError):
            obs_port_i = 4455
        obs_port_i = max(1, min(65535, obs_port_i))
        self._obs_ws_port.setText(str(obs_port_i))
        obs_pw = keyring_store.get_password(constants.KEY_OBS_WEBSOCKET_PASSWORD) or ""
        self._obs_ws_password.setText(obs_pw)

        tg_enabled = bool(self._settings.value(_SETTINGS_TELEGRAM_ENABLED, False, bool))
        self._tg_enabled.blockSignals(True)
        self._tg_enabled.setChecked(tg_enabled)
        self._tg_enabled.blockSignals(False)

        tg_admin_raw = self._settings.value(_SETTINGS_TELEGRAM_ADMIN_ID, "")
        self._tg_admin_id.setText(str(tg_admin_raw or "").strip())

        tg_tok = keyring_store.get_password(constants.KEY_TELEGRAM_BOT_TOKEN) or ""
        self._tg_token.setText(tg_tok)

        tg_songs = bool(self._settings.value(_SETTINGS_TELEGRAM_SONG_REQUESTS_ENABLED, True, bool))
        self._tg_song_requests_enabled.blockSignals(True)
        self._tg_song_requests_enabled.setChecked(tg_songs)
        self._tg_song_requests_enabled.blockSignals(False)

        tg_tiktok = bool(
            self._settings.value(_SETTINGS_TELEGRAM_TIKTOK_LYRICS_FILTER, False, bool),
        )
        self._tg_tiktok_lyrics_filter.blockSignals(True)
        self._tg_tiktok_lyrics_filter.setChecked(tg_tiktok)
        self._tg_tiktok_lyrics_filter.blockSignals(False)

        self._tg_genius_token.setText(
            keyring_store.get_password(constants.KEY_GENIUS_CLIENT_ACCESS_TOKEN) or "",
        )
        gq = (keyring_store.get_password(constants.KEY_GROQ_API_KEY) or "").strip()
        if not gq:
            gq = (keyring_store.get_password(constants.KEY_LEGACY_GEMINI_API_KEY) or "").strip()
        self._tg_groq_api_key.setText(gq)

        oai = keyring_store.get_password(constants.KEY_OPENAI_API_KEY) or ""
        self._openai_api_key.setText(oai)

        if hasattr(self, "_cb_tts_openai_moderate"):
            self._cb_tts_openai_moderate.blockSignals(True)
            self._cb_tts_openai_moderate.setChecked(
                bool(self._settings.value(_SETTINGS_TTS_OPENAI_MODERATE, False, bool)),
            )
            self._cb_tts_openai_moderate.blockSignals(False)

        if hasattr(self, "_cb_tts_speak_author"):
            self._cb_tts_speak_author.blockSignals(True)
            self._cb_tts_speak_author.setChecked(
                bool(self._settings.value(_SETTINGS_TTS_SPEAK_AUTHOR, False, bool)),
            )
            self._cb_tts_speak_author.blockSignals(False)

        if hasattr(self, "_cb_tts_strip_non_alpha"):
            self._cb_tts_strip_non_alpha.blockSignals(True)
            self._cb_tts_strip_non_alpha.setChecked(
                bool(self._settings.value(_SETTINGS_TTS_STRIP_NON_ALPHA, False, bool)),
            )
            self._cb_tts_strip_non_alpha.blockSignals(False)

        if hasattr(self, "_cb_edge_randomize"):
            self._cb_edge_randomize.blockSignals(True)
            self._cb_edge_randomize.setChecked(
                bool(self._settings.value(_SETTINGS_TTS_RANDOMIZE_EDGE, False, bool)),
            )
            self._cb_edge_randomize.blockSignals(False)

        if hasattr(self, "_cb_respeecher_randomize"):
            self._cb_respeecher_randomize.blockSignals(True)
            self._cb_respeecher_randomize.setChecked(
                bool(self._settings.value(_SETTINGS_TTS_RANDOMIZE_RESPEECHER, False, bool)),
            )
            self._cb_respeecher_randomize.blockSignals(False)

        if hasattr(self, "_edit_tts_whitelist"):
            whitelist = str(self._settings.value(_SETTINGS_TTS_WHITELIST, "", str) or "").strip()
            self._edit_tts_whitelist.blockSignals(True)
            self._edit_tts_whitelist.setPlainText(whitelist)
            self._edit_tts_whitelist.blockSignals(False)

        backend = str(self._settings.value(_SETTINGS_MUSIC_BACKEND, "app", str) or "").strip()
        use_mpv = backend == "mpv"
        self._music_use_mpv.blockSignals(True)
        self._music_use_mpv.setChecked(use_mpv)
        self._music_use_mpv.blockSignals(False)
        self._refresh_mpv_check_label()

        if hasattr(self, "_music_max_duration_min"):
            raw = self._settings.value(_SETTINGS_MUSIC_MAX_DURATION_MIN, 5)
            try:
                mm = int(raw)
            except (TypeError, ValueError):
                mm = 5
            mm = max(0, min(240, mm))
            self._music_max_duration_min.blockSignals(True)
            self._music_max_duration_min.setValue(mm)
            self._music_max_duration_min.blockSignals(False)

        if hasattr(self, "_points_enabled_cb"):
            self._points_enabled_cb.blockSignals(True)
            self._points_enabled_cb.setChecked(self._points_enabled())
            self._points_enabled_cb.blockSignals(False)

    @Slot(int)
    def _persist_music_max_duration_min(self, _value: int) -> None:
        mm = int(self._music_max_duration_min.value())
        mm = max(0, min(240, mm))
        self._settings.setValue(_SETTINGS_MUSIC_MAX_DURATION_MIN, mm)

    @Slot(int)
    def _persist_points_enabled(self, _state: int) -> None:
        on = bool(self._points_enabled_cb.isChecked())
        self._settings.setValue(SETTINGS_POINTS_ENABLED, on)
        self._refresh_points_config()
        asyncio.ensure_future(self._apply_telegram_from_settings())

    def _open_points_settings_dialog(self) -> None:
        dlg = PointsSettingsDialog(
            parent=self,
            settings=self._settings,
            tr=self._tr,
            on_saved=self._on_points_settings_saved,
        )
        dlg.exec()

    def _on_points_settings_saved(self) -> None:
        self._refresh_points_config()
        asyncio.ensure_future(self._apply_telegram_from_settings())

    @Slot(int)
    def _on_tts_gain_changed(self, value: int) -> None:
        self._settings.setValue(_SETTINGS_TTS_GAIN_DB, value)
        self._sink.set_tts_gain_db(value)

    @Slot(int)
    def _on_tts_rate_changed(self, value: int) -> None:
        v = max(_TTS_RATE_MIN, min(_TTS_RATE_MAX, int(value)))
        self._settings.setValue(_SETTINGS_TTS_RATE_PERCENT, v)
        asyncio.ensure_future(self._swap_tts_backend())

    @Slot(int)
    def _persist_autostart_twitch(self, _state: int) -> None:
        self._settings.setValue(_SETTINGS_AUTOSTART_TWITCH, self._cb_autostart_twitch.isChecked())

    @Slot(int)
    def _persist_autostart_youtube(self, _state: int) -> None:
        self._settings.setValue(
            _SETTINGS_AUTOSTART_YOUTUBE,
            self._cb_autostart_youtube.isChecked(),
        )

    @Slot(int)
    def _persist_autostart_tiktok(self, _state: int) -> None:
        self._settings.setValue(
            _SETTINGS_AUTOSTART_TIKTOK,
            self._cb_autostart_tiktok.isChecked(),
        )

    @Slot(int)
    def _persist_autostart_kick(self, _state: int) -> None:
        self._settings.setValue(
            _SETTINGS_AUTOSTART_KICK,
            self._cb_autostart_kick.isChecked(),
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
        if getattr(self, "_qml_actions", None) is not None and self._qml_actions.isVisible():
            self._qml_api.refresh()

    def _apply_status_routes(self, msg: str) -> None:
        """Keep separate footer lines so Twitch and YouTube statuses are not overwritten."""
        if msg.startswith(("Twitch:", "Twitch error")):
            rest = (
                msg.removeprefix("Twitch:").removeprefix("Twitch error").strip().lstrip(":").strip()
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
                    self._status_youtube = msg[len(prefix) :].strip(" :") or msg
                    return
            self._status_youtube = msg.removeprefix("YouTube:").strip() or msg
            return
        if msg.startswith(("TikTok:", "TikTok error")):
            rest = (
                msg.removeprefix("TikTok:").removeprefix("TikTok error").strip().lstrip(":").strip()
            )
            self._status_tiktok = rest if rest else msg
            return
        if msg.startswith(("Kick:", "Kick error", "Kick HTTP", "Kick API")):
            for prefix in ("Kick API", "Kick HTTP", "Kick error", "Kick:"):
                if msg.startswith(prefix):
                    self._status_kick = msg[len(prefix) :].strip(" :") or msg
                    return
            self._status_kick = msg.removeprefix("Kick:").strip() or msg
            return
        if msg in l10n.all_locale_strings_many("status.logout_twitch", "status.twitch_keys_saved"):
            self._status_twitch = msg
            return
        if msg in l10n.all_locale_strings_many("status.logout_youtube"):
            self._status_youtube = msg
            return
        if msg in l10n.all_locale_strings_many("status.logout_kick"):
            self._status_kick = msg
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
        e = html.escape
        tw_on = self._tr("footer.on") if self._twitch.running else self._tr("footer.off")
        yt_on = self._tr("footer.on") if self._youtube.running else self._tr("footer.off")
        tk_on = self._tr("footer.on") if self._tiktok.running else self._tr("footer.off")
        kk_on = self._tr("footer.on") if self._kick.running else self._tr("footer.off")
        tw_c = "#34d399" if self._twitch.running else "#fb923c"
        yt_c = "#34d399" if self._youtube.running else "#fb923c"
        tk_c = "#34d399" if self._tiktok.running else "#fb923c"
        kk_c = "#34d399" if self._kick.running else "#fb923c"
        pl = e(self._tr("footer.pipeline"))
        ftw = e(self._tr("footer.twitch"))
        fyt = e(self._tr("footer.youtube"))
        ftk = e(self._tr("footer.tiktok"))
        fkk = e(self._tr("footer.kick"))
        fq = e(self._tr("footer.queues"))
        fchat = e(self._tr("footer.chat"))
        ftts = e(self._tr("footer.tts"))
        h1 = (
            f'<span style="color:#4ade80">●</span> <span style="color:#cbd5e1;">{pl}:'
            f'</span> <span style="color:#f1f5f9;">{e(self._status_app)}</span>'
        )
        tw_ico = _footer_richtext_img("twitch.svg", 15)
        yt_ico = _footer_richtext_img("youtube.svg", 15)
        tk_ico = _footer_richtext_img("tiktok.svg", 15)
        kk_ico = _footer_richtext_img("kick.svg", 15)
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
            f'{kk_ico}<span style="color:{kk_c}">●</span> <span style="color:#cbd5e1;">{fkk}'
            f'</span> <span style="color:#94a3b8;">({e(kk_on)}):</span> '
            f'<span style="color:#e2e8f0;">{e(self._status_kick)}</span>'
        )
        h6 = f'<span style="color:#94a3b8;">{fq}: {fchat}={cq} &nbsp; {ftts}={tq}</span>'
        self._status_label.setText(f"{h1}<br/>{h2}<br/>{h3}<br/>{h4}<br/>{h5}<br/>{h6}")
        tw_btn = "tw.transport_stop" if self._twitch.running else "tw.transport_start"
        yt_btn = "yt.transport_stop" if self._youtube.running else "yt.transport_start"
        self._btn_twitch_transport.setText(self._tr(tw_btn))
        self._btn_youtube_transport.setText(self._tr(yt_btn))

    @Slot()
    def _on_tiktok_transport_clicked(self) -> None:
        self._qml_refresh_if_visible()
        asyncio.ensure_future(self._async_set_tiktok_enabled(not self._tiktok_enabled))

    @Slot()
    def _on_kick_transport_clicked(self) -> None:
        self._qml_refresh_if_visible()
        asyncio.ensure_future(self._async_set_kick_enabled(not self._kick_enabled))

    def _request_kick_enabled(self, enabled: bool) -> None:
        self._qml_refresh_if_visible()
        asyncio.ensure_future(self._async_set_kick_enabled(bool(enabled)))

    async def _async_set_kick_enabled(self, enabled: bool) -> None:
        if self._kick_toggle_busy:
            return
        if bool(enabled) == bool(self._kick_enabled):
            return
        self._kick_toggle_busy = True
        try:
            self._kick_enabled = bool(enabled)
            if self._kick_enabled:
                await self._start_kick()
            else:
                await self._kick.stop()
                self._kick_analytics.resetSession()
        finally:
            self._kick_toggle_busy = False
            self._refresh_footer()
            self._qml_refresh_if_visible()

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
                self._social_rotator.on_stream_live(True)
                self._schedule_king_overlay_publish()
                if self._widgets_qml_api is not None:
                    self._widgets_qml_api.kingOfLiveOverlayUrlChanged.emit()
            else:
                await self._tiktok.stop()
                self._tiktok_analytics.resetSession()
                self._social_rotator.on_stream_live(False)
                self._social_rotator.on_viewers("tiktok", 0)
                self._schedule_king_overlay_publish()
                if self._widgets_qml_api is not None:
                    self._widgets_qml_api.kingOfLiveOverlayUrlChanged.emit()
        finally:
            self._tiktok_toggle_busy = False
            self._qml_refresh_if_visible()

    @Slot()
    def _on_twitch_transport_clicked(self) -> None:
        self._qml_refresh_if_visible()
        if self._twitch.running:
            asyncio.ensure_future(self._async_stop_twitch_all())
        else:
            asyncio.ensure_future(self._start_twitch())

    async def _async_stop_twitch_all(self) -> None:
        await self._twitch.stop()
        await self._stop_twitch_analytics()

    @Slot()
    def _on_youtube_transport_clicked(self) -> None:
        self._qml_refresh_if_visible()
        if self._youtube.running:
            asyncio.ensure_future(self._async_stop_youtube_all())
        else:
            asyncio.ensure_future(self._start_youtube())

    async def _async_stop_youtube_all(self) -> None:
        await self._youtube.stop()
        self._youtube_analytics.resetSession()
        self._refresh_footer()
        self._qml_refresh_if_visible()

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
        if message.platform == ChatPlatform.KICK:
            self._kick_analytics.enqueue_messages(1)
        self._chat_message_history.append(message)
        fragment = self._format_chat_message_fragment(message)
        self._bridge.append_chat.emit(fragment)
        pop = self._chat_popout
        if pop is not None and shiboken6.isValid(pop):
            pop.append_message(message)
        if not self._closing:
            chat_patch = chat_message_to_patch(message)
            if message.platform == ChatPlatform.TIKTOK:
                key = (message.tiktok_stable_key or "").strip()
                if not key:
                    key = (message.author or "").strip().casefold()
                if self._battle_controller.is_vip_user(key):
                    append = chat_patch.get("append")
                    if isinstance(append, dict):
                        append["vip_gold"] = True
            t = asyncio.create_task(
                self._overlay_server.pubsub().publish(
                    "overlay:chat:main",
                    chat_patch,
                ),
            )
            # Ensure exceptions are retrieved to avoid "Task exception was never retrieved".
            t.add_done_callback(lambda _t: _t.exception())
        self._dispatch_actions_for_chat(message)
        self._maybe_bump_king_chat_highlight(message)
        self._try_tiktok_link_from_comment(message)
        self._stream_pet.on_chat(author=message.author, text=message.text)
        self._stream_goal.on_comment(user=message.author, text=message.text)
        self._live_leaderboard.on_comment(
            user=message.author,
            stable_key=message.tiktok_stable_key,
            unique_id=message.tiktok_unique_id,
        )
        self._community_world.on_chat(user=message.author, text=message.text)
        self._signal_system.on_comment(
            user=message.author,
            text=message.text,
            stable_key=message.tiktok_stable_key,
            unique_id=message.tiktok_unique_id,
        )

    def _try_tiktok_link_from_comment(self, message: ChatMessage) -> None:
        if self._closing or not self._points_enabled():
            return
        if message.platform != ChatPlatform.TIKTOK:
            return
        code = extract_link_code_from_comment(message.text)
        if not code:
            return
        sk = (message.tiktok_stable_key or "").strip()
        if not sk:
            return
        try:
            result = try_complete_telegram_link_challenge(
                code=code,
                stable_key=sk,
                unique_id=message.tiktok_unique_id,
            )
        except (OSError, sqlite3.Error) as exc:
            logger.warning("points: tiktok link challenge failed: %s", exc)
            return
        if not result.ok:
            return
        tg = self._telegram
        if tg is None:
            return
        msg = self._tr(
            "telegram.link.verified",
            handle=result.unique_id,
        )
        tg.send_html_message_to_chat(int(result.telegram_id), msg)

    def _on_youtube_analytics_event(self, kind: str, user: str, detail: str, count: int) -> None:
        self._youtube_analytics.enqueue_event(kind, user, detail, count)
        k = (kind or "").strip().lower()
        if k not in ("superchat", "supersticker", "member", "membership"):
            return
        it = ActivityItem(
            platform="youtube",
            kind=("member" if k == "membership" else k),  # type: ignore[arg-type]
            user=(user or "").strip() or "?",
            detail=(detail or "").strip(),
            count=max(1, int(count) if isinstance(count, int) else 1),
            icon_url="",
            time_hms=now_hms(),
        )
        self._publish_activity_item(it)

    def _on_youtube_action_event(self, signal: YouTubeActionSignal) -> None:
        """Dispatch a structured YouTube live-chat event to the Actions engine."""
        if self._closing:
            return
        eng = self._get_app_actions_engine()
        user = (signal.user or "").strip()
        pic = (signal.profile_image_url or "").strip()
        now = datetime.now(UTC)
        kind = (signal.kind or "").strip().lower()
        if kind == "superchat":
            asyncio.ensure_future(
                eng.on_youtube_superchat(
                    user,
                    int(signal.amount_micros),
                    signal.currency,
                    signal.amount_display,
                    signal.message,
                    now,
                    profile_picture_url=pic,
                )
            )
        elif kind == "supersticker":
            asyncio.ensure_future(
                eng.on_youtube_supersticker(
                    user,
                    int(signal.amount_micros),
                    signal.currency,
                    signal.amount_display,
                    now,
                    profile_picture_url=pic,
                )
            )
        elif kind == "member":
            asyncio.ensure_future(
                eng.on_youtube_member(
                    user,
                    int(signal.months),
                    signal.level,
                    now,
                    profile_picture_url=pic,
                )
            )
        if kind in ("superchat", "supersticker"):
            gift_label = (signal.amount_display or kind).strip()
            self._stream_pet.on_gift(
                platform=ChatPlatform.YOUTUBE.value,
                user=user,
                gift_name=gift_label,
                youtube_amount_micros=int(signal.amount_micros),
            )
        elif kind == "member":
            self._stream_pet.on_member(user=user)

    def _publish_activity_item(self, item: ActivityItem) -> None:
        if self._closing:
            return
        try:
            ps = self._overlay_server.pubsub()
        except RuntimeError:
            return
        t = asyncio.create_task(
            ps.publish(
                "overlay:activity:main",
                activity_append_patch(item),
            ),
        )
        t.add_done_callback(lambda _t: _t.exception())
        if item.kind == "like":
            self._stream_pet.on_like_burst(user=item.user)

    def _publish_activity_join_ticker(self, item: ActivityItem) -> None:
        if self._closing:
            return
        try:
            ps = self._overlay_server.pubsub()
        except RuntimeError:
            return
        t = asyncio.create_task(
            ps.publish(
                "overlay:activity:main",
                activity_join_ticker_patch(item),
            ),
        )
        t.add_done_callback(lambda _t: _t.exception())

    def _on_tiktok_follow_any(self, user: str, stable_key: str = "", unique_id: str = "") -> None:
        if self._closing:
            return
        eng = self._get_actions_engine(
            ChatPlatform.TIKTOK.value,
            constants.TIKTOK_ACTIONS_ACCOUNT_KEY,
        )
        asyncio.ensure_future(eng.on_tiktok_followed((user or "").strip(), datetime.now(UTC)))
        self._tiktok_analytics.on_follow(user)
        if self._points_enabled():
            self._register_watch_activity(
                stable_key=stable_key,
                unique_id=unique_id,
                display_name=user,
            )
            sk = (stable_key or "").strip()
            cfg = self._load_points_config()
            if sk and self._engagement_award_allowed(sk, "follow", cfg.follow_cooldown_sec):
                delta = self._earn_tracker.on_follow(sk)
                if delta > 0:
                    self._award_points(
                        stable_key=stable_key,
                        unique_id=unique_id,
                        display_name=user,
                        delta=delta,
                        reason="follow",
                    )
        it = ActivityItem(
            platform="tiktok",
            kind="follow",
            user=(user or "").strip() or "?",
            detail="",
            count=1,
            icon_url="",
            time_hms=now_hms(),
        )
        self._publish_activity_item(it)
        self._stream_pet.on_follow(user=user)
        self._stream_goal.on_follow(user=user, stable_key=stable_key)
        self._social_rotator.on_follow(user=user, stable_key=stable_key)
        self._community_world.on_follow(user=user, user_key=stable_key)
        self._signal_system.on_follow(user=user, stable_key=stable_key, unique_id=unique_id)

    def _on_tiktok_room_viewers_current(self, n: int) -> None:
        self._tiktok_analytics.enqueue_viewers_current(int(n))
        self._social_rotator.on_viewers("tiktok", int(n))

    def _on_youtube_viewers_current(self, n: int) -> None:
        self._youtube_analytics.enqueue_viewers(int(n))
        self._social_rotator.on_viewers("youtube", int(n))

    def _on_external_donation(self, name: str, amount: float, source: str) -> None:
        if self._closing:
            return
        self._social_rotator.on_donation(name=name, amount=amount, source=source)

    def _on_tiktok_join_any(self, user: str, stable_key: str = "") -> None:
        if self._closing:
            return
        eng = self._get_actions_engine(
            ChatPlatform.TIKTOK.value,
            constants.TIKTOK_ACTIONS_ACCOUNT_KEY,
        )
        asyncio.ensure_future(eng.on_tiktok_joined((user or "").strip(), datetime.now(UTC)))
        self._tiktok_analytics.on_join(user)
        if self._points_enabled():
            self._register_watch_activity(
                stable_key=stable_key,
                unique_id="",
                display_name=user,
            )
        self._maybe_bump_king_presence(
            display_name=(user or "").strip(),
            stable_key=(stable_key or "").strip(),
        )
        it = ActivityItem(
            platform="tiktok",
            kind="join",
            user=(user or "").strip() or "?",
            detail="",
            count=1,
            icon_url="",
            time_hms=now_hms(),
        )
        self._publish_activity_join_ticker(it)
        self._stream_pet.on_join(user=user)
        self._community_world.on_join(user=user, user_key=stable_key)

    def _on_tiktok_gift_analytics_any(
        self,
        sender: str,
        gift_id: str,
        gift_name: str,
        count: int,
        diamonds: int,
        icon_url: str,
    ) -> None:
        self._tiktok_analytics.on_gift_analytics(
            sender,
            gift_id,
            gift_name,
            count,
            diamonds,
            icon_url,
        )
        gid = (gift_id or "").strip()
        gname = (gift_name or "").strip()
        icon = (icon_url or "").strip()
        if not icon:
            icon = tiktok_catalog_gift_image_url(gift_id=gid, gift_name=gname)
        it = ActivityItem(
            platform="tiktok",
            kind="gift",
            user=(sender or "").strip() or "?",
            detail=gname or gid,
            count=max(1, int(count) if isinstance(count, int) else 1),
            icon_url=icon,
            time_hms=now_hms(),
        )
        self._publish_activity_item(it)

    def _on_tiktok_like_any(
        self,
        user: str,
        n: int,
        profile_picture_url: str = "",
        user_key: str = "",
        unique_id: str = "",
    ) -> None:
        # Activity dock aggregates likes; actions engine evaluates tiktok_likes_received rules.
        if self._closing:
            return
        try:
            n_i = max(1, int(n))
        except (TypeError, ValueError):
            n_i = 1
        eng = self._get_actions_engine(
            ChatPlatform.TIKTOK.value,
            constants.TIKTOK_ACTIONS_ACCOUNT_KEY,
        )
        asyncio.ensure_future(
            eng.on_tiktok_likes_received(
                (user or "").strip(),
                n_i,
                datetime.now(UTC),
                profile_picture_url=(profile_picture_url or "").strip(),
            ),
        )
        self._like_share_agg.ingest(
            kind="like",
            user=(user or "").strip(),
            n=n_i,
            now_mono=time.monotonic(),
        )
        for it in self._like_share_agg.flush_ready(now_mono=time.monotonic()):
            self._publish_activity_item(it)
        self._tiktok_top_likers.add_likes(
            user_key=(user_key or "").strip(),
            display_name=(user or "").strip(),
            n=n_i,
            avatar_url=(profile_picture_url or "").strip(),
        )
        self._schedule_top_likers_overlay_publish()
        if self._points_enabled():
            self._register_watch_activity(
                stable_key=user_key,
                unique_id=unique_id,
                display_name=user,
            )
            delta = self._earn_tracker.on_like((user_key or "").strip(), n_i)
            self._award_points(
                stable_key=user_key,
                unique_id=unique_id,
                display_name=user,
                delta=delta,
                reason="like",
            )
        self._stream_goal.on_like(
            user=user,
            count=n_i,
            profile_picture_url=profile_picture_url,
            user_key=user_key,
            unique_id=unique_id,
        )
        self._live_leaderboard.on_like(
            user=user,
            count=n_i,
            profile_picture_url=profile_picture_url,
            user_key=user_key,
            unique_id=unique_id,
        )
        self._community_world.on_like(
            user=user,
            n=n_i,
            user_key=user_key,
            avatar_url=profile_picture_url,
        )
        self._signal_system.on_like(
            user=user,
            count=n_i,
            profile_picture_url=profile_picture_url,
        )

    def _schedule_top_likers_overlay_publish(self) -> None:
        if self._closing:
            return
        loop = self._asyncio_loop
        if loop is None:
            return
        prev = self._top_likers_publish_handle
        if prev is not None:
            prev.cancel()
        self._top_likers_publish_handle = loop.call_later(
            0.12,
            self._on_top_likers_debounced_fire,
        )

    def _on_top_likers_debounced_fire(self) -> None:
        self._top_likers_publish_handle = None
        if self._closing:
            return
        loop = self._asyncio_loop
        if loop is None:
            return
        loop.create_task(self._publish_top_likers_leaders_patch())

    async def _publish_top_likers_leaders_patch(self) -> None:
        cfg = load_top_likers_overlay_config()
        leaders = self._tiktok_top_likers.leaders(
            limit=int(cfg.top_count),
            sort=str(cfg.leader_sort),
        )
        await self._overlay_server.pubsub().publish(
            "overlay:top_likers:main",
            {"leaders": leaders},
        )

    def _schedule_top_gifters_overlay_publish(self) -> None:
        if self._closing:
            return
        loop = self._asyncio_loop
        if loop is None:
            return
        prev = self._top_gifters_publish_handle
        if prev is not None:
            prev.cancel()
        self._top_gifters_publish_handle = loop.call_later(
            0.12,
            self._on_top_gifters_debounced_fire,
        )

    def _on_top_gifters_debounced_fire(self) -> None:
        self._top_gifters_publish_handle = None
        if self._closing:
            return
        loop = self._asyncio_loop
        if loop is None:
            return
        loop.create_task(self._publish_top_gifters_leaders_patch())

    async def _publish_top_gifters_leaders_patch(self) -> None:
        cfg = load_top_gifters_overlay_config()
        leaders = self._tiktok_top_gifters.leaders(
            limit=int(cfg.top_count),
            sort=str(cfg.leader_sort),
        )
        await self._overlay_server.pubsub().publish(
            "overlay:top_gifters:main",
            {"leaders": leaders},
        )

    def _schedule_king_overlay_publish(self) -> None:
        if self._closing:
            return
        loop = self._asyncio_loop
        if loop is None:
            return
        prev = self._king_overlay_publish_handle
        if prev is not None:
            prev.cancel()
        self._king_overlay_publish_handle = loop.call_later(
            0.35,
            self._on_king_overlay_debounced_fire,
        )

    def _on_king_overlay_debounced_fire(self) -> None:
        self._king_overlay_publish_handle = None
        if self._closing:
            return
        loop = self._asyncio_loop
        if loop is None:
            return
        loop.create_task(self._publish_king_overlay_patch())

    def current_tiktok_anchor_username(self) -> str:
        """Normalized TikTok live host for the active or configured stream."""
        streamer = (self._tiktok.connected_stream_unique_id or "").strip()
        if not streamer:
            streamer = (self._tiktok_username.text() or "").strip().lstrip("@").strip()
        return streamer

    async def _publish_king_overlay_patch(self) -> None:
        cfg = load_king_of_live_overlay_config()
        anchor = self.current_tiktok_anchor_username()
        tops = fetch_all_time_gifter_totals(
            limit=5,
            anchor_username=anchor if anchor else "",
        )
        king = tops[0] if tops else None
        runner = tops[1] if len(tops) > 1 else None
        gap = 0
        runner_name = ""
        if king and runner and str(king.get("key") or "") != str(runner.get("key") or ""):
            gap = max(0, int(king.get("diamonds") or 0) - int(runner.get("diamonds") or 0))
            runner_name = str(runner.get("user") or "")
        king_d = int(king.get("diamonds") or 0) if king else 0
        king_key = str(king.get("key") or "").strip() if king else ""

        leaders = self._tiktok_top_gifters.leaders(limit=12, sort="likes_desc")
        challenger: dict[str, Any] | None = None
        best_ratio = 0.0
        if king_key and king_d > 0:
            for row in leaders:
                rk = str(row.get("key") or "").strip()
                if not rk or rk == king_key:
                    continue
                coins = int(row.get("coins") or 0)
                ratio = coins / float(king_d) if king_d else 0.0
                if ratio > best_ratio:
                    best_ratio = ratio
                    challenger = {
                        "key": rk,
                        "user": str(row.get("user") or "?"),
                        "coins": coins,
                        "ratio": round(ratio, 4),
                    }

        thr_pct = max(50, min(99, int(cfg.danger_threshold_pct)))
        throne_danger = bool(challenger and best_ratio * 100.0 >= float(thr_pct))

        cfg_payload = json.loads(king_of_live_overlay_config_to_json_text(cfg))
        cfg_payload["ui_locale"] = self._locale
        patch: dict[str, Any] = {
            "config": cfg_payload,
            "king": king,
            "gap_diamonds": gap,
            "runner_up_user": runner_name,
            "session_challenger": challenger,
            "throne_danger": throne_danger,
            "king_revision": 0,
            "king_presence_seq": int(self._king_presence_seq),
            "chat_highlight_seq": int(self._king_chat_highlight_seq),
            "hall_of_fame": fetch_hall_of_fame(limit=5),
        }
        if king:
            self._king_overlay_cached_king_key = king_key
            self._king_overlay_cached_king_display = str(king.get("user") or "").strip()
        else:
            self._king_overlay_cached_king_key = ""
            self._king_overlay_cached_king_display = ""
        await self._overlay_server.pubsub().publish("overlay:king_of_live:main", patch)

    def _maybe_bump_king_presence(self, *, display_name: str, stable_key: str) -> None:
        if self._closing:
            return
        k_key = (stable_key or "").strip()
        k_disp = (display_name or "").strip().casefold()
        king_key = self._king_overlay_cached_king_key
        king_disp = self._king_overlay_cached_king_display.strip().casefold()
        hit = bool(k_key and king_key and k_key == king_key)
        if not hit and k_disp and king_disp:
            hit = k_disp == king_disp
        if not hit:
            return
        self._king_presence_seq += 1
        try:
            ps = self._overlay_server.pubsub()
        except RuntimeError:
            return
        t = asyncio.create_task(
            ps.publish(
                "overlay:king_of_live:main",
                {
                    "king_presence_seq": int(self._king_presence_seq),
                },
            ),
        )
        t.add_done_callback(lambda _t: _t.exception())

    def _maybe_bump_king_chat_highlight(self, message: ChatMessage) -> None:
        if self._closing or message.platform != ChatPlatform.TIKTOK:
            return
        k_key = (message.tiktok_stable_key or "").strip()
        author_cf = (message.author or "").strip().casefold()
        king_key = self._king_overlay_cached_king_key
        king_disp = self._king_overlay_cached_king_display.strip().casefold()
        hit = bool(k_key and king_key and k_key == king_key)
        if not hit and author_cf and king_disp:
            hit = author_cf == king_disp
        if not hit:
            return
        self._king_chat_highlight_seq += 1
        try:
            ps = self._overlay_server.pubsub()
        except RuntimeError:
            return
        t = asyncio.create_task(
            ps.publish(
                "overlay:king_of_live:main",
                {
                    "chat_highlight_seq": int(self._king_chat_highlight_seq),
                },
            ),
        )
        t.add_done_callback(lambda _t: _t.exception())

    def _on_battle_tick(self) -> None:
        if self._closing:
            return
        if self._battle_controller.tick():
            self._schedule_battle_overlay_publish()

    def _schedule_battle_overlay_publish(self) -> None:
        if self._closing:
            return
        loop = self._asyncio_loop
        if loop is None:
            return
        prev = self._battle_overlay_publish_handle
        if prev is not None:
            prev.cancel()
        self._battle_overlay_publish_handle = loop.call_later(
            0.35,
            self._on_battle_overlay_debounced_fire,
        )

    def _on_battle_overlay_debounced_fire(self) -> None:
        self._battle_overlay_publish_handle = None
        if self._closing:
            return
        loop = self._asyncio_loop
        if loop is None:
            return
        loop.create_task(self._publish_battle_overlay_patch())

    def _build_battle_overlay_patch(self) -> dict[str, Any]:
        cfg = load_battle_royale_overlay_config()
        patch = self._battle_controller.overlay_patch()
        cfg_payload = json.loads(battle_royale_overlay_config_to_json_text(cfg))
        cfg_payload["ui_locale"] = self._locale
        patch["config"] = cfg_payload
        return patch

    def _publish_battle_overlay_patch_sync(self) -> None:
        if self._closing:
            return
        try:
            ps = self._overlay_server.pubsub()
        except RuntimeError:
            return
        ps.publish_sync("overlay:battle_royale:main", self._build_battle_overlay_patch())

    async def _publish_battle_overlay_patch(self) -> None:
        try:
            ps = self._overlay_server.pubsub()
        except RuntimeError:
            return
        ps.publish_sync("overlay:battle_royale:main", self._build_battle_overlay_patch())

    def _sync_battle_ui_after_gift(self, *, prev_phase: BattlePhase) -> None:
        st = self._battle_controller.state()
        if st.phase in (
            BattlePhase.COUNTDOWN,
            BattlePhase.ACTIVE,
            BattlePhase.VICTORY,
        ):
            self._battle_tick_timer.start()
            self._publish_battle_overlay_patch_sync()
            self._schedule_battle_overlay_publish()
            if prev_phase == BattlePhase.IDLE and st.phase == BattlePhase.COUNTDOWN:
                names = ", ".join(f.display_name for f in st.fighters[:4])
                self._on_user_status(
                    self._tr("battle.auto_started", fighters=names),
                )

    def _on_battle_royale_ended(self, winner: BattleFighter | None) -> None:
        if winner is not None:
            record_battle_win(
                user_key=winner.user_key,
                display_name=winner.display_name,
                avatar_url=winner.avatar_url,
            )
            self._on_user_status(
                self._tr("battle.winner_music_toast", user=winner.display_name),
            )
            self._schedule_king_overlay_publish()
            self._community_world.on_battle_win(
                user=winner.display_name,
                user_key=winner.user_key,
                avatar_url=winner.avatar_url,
            )
        self._schedule_battle_overlay_publish()
        phase = self._battle_controller.state().phase
        if phase in (BattlePhase.COUNTDOWN, BattlePhase.ACTIVE, BattlePhase.VICTORY):
            self._battle_tick_timer.start()
        else:
            self._battle_tick_timer.stop()

    def battle_royale_start_from_leaders(self) -> bool:
        leaders = self._tiktok_top_gifters.leaders(limit=4, sort="likes_desc")
        fighters = [
            {
                "user_key": str(r.get("key") or ""),
                "user": str(r.get("user") or "?"),
                "avatar_url": str(r.get("avatar_url") or ""),
            }
            for r in leaders[:2]
        ]
        return self.battle_royale_start_fighters(fighters)

    def battle_royale_start_fighters(self, fighters: list[dict[str, str]]) -> bool:
        cfg = load_battle_royale_overlay_config()
        ok = self._battle_controller.start_manual(fighters, cfg=cfg)
        if ok:
            self._battle_tick_timer.start()
            self._publish_battle_overlay_patch_sync()
            self._schedule_battle_overlay_publish()
            names = ", ".join(str(f.get("user") or "?") for f in fighters[:4])
            self._on_user_status(self._tr("battle.manual_started", fighters=names))
        else:
            self._on_user_status(self._tr("battle.start_failed"))
        return ok

    def battle_royale_stop(self) -> None:
        self._battle_controller.stop()
        self._battle_auto_arm_hint_count = 0
        self._battle_tick_timer.stop()
        self._publish_battle_overlay_patch_sync()
        self._schedule_battle_overlay_publish()

    def _load_points_config(self) -> PointsConfig:
        return load_points_config_from_settings(self._settings)

    def _points_enabled(self) -> bool:
        return bool(self._settings.value(SETTINGS_POINTS_ENABLED, False, bool))

    def _points_insufficient_message(self, balance: int, cost: int) -> str:
        return self._tr(
            "telegram.song.points_insufficient",
            balance=str(balance),
            cost=str(cost),
            **earn_rate_template_vars(self._load_points_config()),
        )

    def _restart_points_watch_timer(self) -> None:
        cfg = self._earn_tracker.config
        self._points_watch_timer.stop()
        self._points_watch_timer.setInterval(max(1, cfg.watch_interval_minutes) * 60_000)
        if self._points_enabled():
            self._points_watch_timer.start()

    def _refresh_points_config(self) -> None:
        self._earn_tracker.set_config(self._load_points_config())
        self._restart_points_watch_timer()

    def _engagement_award_allowed(
        self,
        stable_key: str,
        reason: str,
        cooldown_sec: int,
    ) -> bool:
        try:
            rem = engagement_cooldown_remaining_sec(
                stable_key=stable_key,
                reason=reason,
                cooldown_sec=int(cooldown_sec),
            )
        except (OSError, sqlite3.Error) as exc:
            logger.warning("points: cooldown check failed (%s): %s", reason, exc)
            return False
        return rem <= 0

    def _award_points(
        self,
        *,
        stable_key: str,
        unique_id: str,
        display_name: str,
        delta: int,
        reason: str,
    ) -> None:
        if delta <= 0:
            return
        sk = (stable_key or "").strip()
        if not sk:
            return
        try:
            balance = add_points(
                stable_key=sk,
                unique_id=unique_id,
                display_name=display_name,
                delta=int(delta),
                reason=reason,
            )
        except (OSError, sqlite3.Error) as exc:
            logger.warning("points: award failed (%s): %s", reason, exc)
            return
        if not self._points_enabled():
            return
        uid = normalize_tiktok_username(unique_id)
        if not uid:
            wallet = get_wallet_for_stable_key(sk)
            uid = normalize_tiktok_username(wallet.unique_id) if wallet is not None else ""
        if not uid:
            return
        telegram_id = get_telegram_id_for_unique_id(uid)
        if telegram_id is None:
            return
        self._schedule_points_earn_notify(
            telegram_id=telegram_id,
            delta=int(delta),
            reason=(reason or "").strip(),
            balance=balance,
        )

    def _schedule_points_earn_notify(
        self,
        *,
        telegram_id: int,
        delta: int,
        reason: str,
        balance: int,
    ) -> None:
        if telegram_id <= 0 or delta <= 0:
            return
        reason_key = (reason or "").strip() or "other"
        prev = self._points_notify_pending.get(telegram_id)
        if prev is None:
            reasons = frozenset({reason_key})
            pending = _PointsNotifyPending(delta, reasons, balance)
        else:
            reasons = prev.reasons | {reason_key}
            pending = _PointsNotifyPending(prev.delta + delta, reasons, balance)
        self._points_notify_pending[telegram_id] = pending
        self._points_notify_timer.start()

    def _format_points_earn_reasons(self, reasons: frozenset[str]) -> str:
        labels: list[str] = []
        for key in _POINTS_EARN_REASON_ORDER:
            if key in reasons:
                labels.append(self._tr(f"telegram.points.reason.{key}"))
        for key in sorted(reasons):
            if key not in _POINTS_EARN_REASON_ORDER:
                labels.append(key)
        return ", ".join(labels) if labels else self._tr("telegram.points.reason.other")

    def _flush_points_earn_notifications(self) -> None:
        if self._closing:
            self._points_notify_pending.clear()
            return
        tg = self._telegram
        pending_map = self._points_notify_pending
        self._points_notify_pending = {}
        if tg is None:
            return
        for telegram_id, batch in pending_map.items():
            if batch.delta <= 0:
                continue
            msg = self._tr(
                "telegram.points.earned",
                delta=str(batch.delta),
                reasons=self._format_points_earn_reasons(batch.reasons),
                balance=str(batch.balance),
            )
            tg.send_html_message_to_chat(telegram_id, msg)

    def _register_watch_activity(
        self,
        *,
        stable_key: str,
        unique_id: str,
        display_name: str,
    ) -> None:
        sk = (stable_key or "").strip()
        if not sk:
            return
        prev = self._points_watch_active.get(sk)
        uid = normalize_tiktok_username(unique_id) or (prev[0] if prev else "")
        name = (display_name or "").strip() or (prev[1] if prev else "")
        self._points_watch_active[sk] = (uid, name)

    def _on_points_watch_tick(self) -> None:
        if self._closing or not self._points_enabled():
            return
        active = self._points_watch_active
        self._points_watch_active = {}
        for sk, (uid, name) in active.items():
            delta = self._earn_tracker.on_watch_tick(sk)
            if delta > 0:
                self._award_points(
                    stable_key=sk,
                    unique_id=uid,
                    display_name=name,
                    delta=delta,
                    reason="watch",
                )

    def _on_tiktok_stream_start(self) -> None:
        """Reset per-stream counters when TikTokLive indicates a new stream has started."""
        if self._closing:
            return
        self._earn_tracker.set_config(self._load_points_config())
        self._earn_tracker.reset()
        self._points_watch_active.clear()
        self._restart_points_watch_timer()
        eng = self._get_actions_engine(
            ChatPlatform.TIKTOK.value,
            constants.TIKTOK_ACTIONS_ACCOUNT_KEY,
        )
        eng.reset_tiktok_like_totals()
        self._tiktok_top_likers.reset()
        self._tiktok_top_gifters.reset()
        h = self._top_likers_publish_handle
        if h is not None:
            h.cancel()
            self._top_likers_publish_handle = None
        hg = self._top_gifters_publish_handle
        if hg is not None:
            hg.cancel()
            self._top_gifters_publish_handle = None
        hk = self._king_overlay_publish_handle
        if hk is not None:
            hk.cancel()
            self._king_overlay_publish_handle = None
        self.battle_royale_stop()
        hb = self._battle_overlay_publish_handle
        if hb is not None:
            hb.cancel()
            self._battle_overlay_publish_handle = None
        self._stream_pet.reset_for_new_stream()
        self._stream_goal.reset_for_new_stream()
        self._live_leaderboard.reset_for_new_stream()
        self._social_rotator.reset_for_new_stream()
        self._community_world.reset_session()
        loop = self._asyncio_loop
        if loop is not None:
            loop.create_task(
                self._overlay_server.pubsub().publish(
                    "overlay:top_likers:main",
                    {"leaders": []},
                ),
            )
            loop.create_task(
                self._overlay_server.pubsub().publish(
                    "overlay:top_gifters:main",
                    {"leaders": []},
                ),
            )
            self._schedule_king_overlay_publish()

    def _on_tiktok_share_any(
        self,
        user: str,
        n: int,
        stable_key: str = "",
        unique_id: str = "",
    ) -> None:
        if self._closing:
            return
        eng = self._get_actions_engine(
            ChatPlatform.TIKTOK.value,
            constants.TIKTOK_ACTIONS_ACCOUNT_KEY,
        )
        asyncio.ensure_future(
            eng.on_tiktok_shared((user or "").strip(), int(n), datetime.now(UTC)),
        )
        self._like_share_agg.ingest(
            kind="share",
            user=(user or "").strip(),
            n=int(n),
            now_mono=time.monotonic(),
        )
        for it in self._like_share_agg.flush_ready(now_mono=time.monotonic()):
            self._publish_activity_item(it)
        if self._points_enabled():
            self._register_watch_activity(
                stable_key=stable_key,
                unique_id=unique_id,
                display_name=user,
            )
            sk = (stable_key or "").strip()
            cfg = self._load_points_config()
            if sk and self._engagement_award_allowed(sk, "share", cfg.share_cooldown_sec):
                delta = self._earn_tracker.on_share(sk, int(n))
                if delta > 0:
                    self._award_points(
                        stable_key=stable_key,
                        unique_id=unique_id,
                        display_name=user,
                        delta=delta,
                        reason="share",
                    )
        self._stream_goal.on_share(
            user=user, count=int(n), stable_key=stable_key, unique_id=unique_id
        )
        self._live_leaderboard.on_share(
            user=user,
            count=int(n),
            stable_key=stable_key,
            unique_id=unique_id,
        )
        self._community_world.on_share(user=user, n=int(n), user_key=stable_key)
        self._signal_system.on_share(user=user, count=int(n))

    def _on_tiktok_paid_sub_any(self, user: str) -> None:
        if self._closing:
            return
        eng = self._get_actions_engine(
            ChatPlatform.TIKTOK.value,
            constants.TIKTOK_ACTIONS_ACCOUNT_KEY,
        )
        asyncio.ensure_future(
            eng.on_tiktok_paid_subscribed((user or "").strip(), datetime.now(UTC))
        )
        it = ActivityItem(
            platform="tiktok",
            kind="paid_sub",
            user=(user or "").strip() or "?",
            detail="",
            count=1,
            icon_url="",
            time_hms=now_hms(),
        )
        self._publish_activity_item(it)

    def _actions_scope_key(self, platform: str, account_key: str) -> tuple[str, str]:
        return (platform.strip().lower(), account_key.strip())

    def _get_app_actions_engine(self) -> PlatformActionsEngine:
        """Rules edited in Actions (stored under tiktok/app for all platforms)."""
        return self._get_actions_engine(
            ChatPlatform.TIKTOK.value,
            constants.TIKTOK_ACTIONS_ACCOUNT_KEY,
        )

    def _actions_account_key_for_platform(self, platform: ChatPlatform) -> str | None:
        # Actions UI persists one ruleset at tiktok/app; live dispatch uses the same scope.
        _ = platform
        return constants.TIKTOK_ACTIONS_ACCOUNT_KEY

    def _maybe_migrate_tiktok_actions(self) -> None:
        """If the app-wide TikTok rules key is unset, copy from legacy .../tiktok/<nick>/.

        Older builds stored TikTok actions under the streamer username. Current builds use a
        single app-wide key (`account_key="app"`). If we cannot resolve the username (or the
        username has changed), fall back to scanning any legacy keys under `actions/tiktok/*`.
        """
        if actions_rules_key_is_set("tiktok", constants.TIKTOK_ACTIONS_ACCOUNT_KEY):
            return
        user = (self._tiktok_username.text() or "").strip().lstrip("@").strip()
        if not user:
            t = keyring_store.get_password(constants.KEY_TIKTOK_USERNAME)
            user = (t or "").strip().lstrip("@").strip() if t else ""
        legacy_candidates: list[str] = []
        if user and user != constants.TIKTOK_ACTIONS_ACCOUNT_KEY:
            legacy_candidates.append(user)

        # Fallback: enumerate all legacy account keys under actions/tiktok/*.
        try:
            s = QSettings("stream-cheremsha", "cheremsha")
            s.beginGroup("actions/tiktok")
            for g in s.childGroups():
                gg = (g or "").strip()
                if not gg or gg == constants.TIKTOK_ACTIONS_ACCOUNT_KEY:
                    continue
                legacy_candidates.append(gg)
        finally:
            try:
                s.endGroup()
            except Exception:
                # Defensive: endGroup can raise if beginGroup never happened.
                pass

        # De-dup (preserve order), then pick the first non-empty legacy ruleset.
        seen: set[str] = set()
        for ak in legacy_candidates:
            if ak in seen:
                continue
            seen.add(ak)
            try:
                old = load_rules("tiktok", ak)
            except ValueError:
                continue
            if not old:
                continue
            save_rules("tiktok", constants.TIKTOK_ACTIONS_ACCOUNT_KEY, old)
            self._actions_reload_scope("tiktok", constants.TIKTOK_ACTIONS_ACCOUNT_KEY)
            return

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
                pubsub=self._overlay_server.pubsub(),
                obs_execute=self._obs_execute_for_actions,
                activity_engine=self._activity_engine,
            )
            self._actions_engines[k] = eng
        return eng

    async def _obs_execute_for_actions(self, payload: dict[str, Any]) -> None:
        from stream_cheremsha.obs_ws.control import ObsControlError, run_obs_scene_action

        if not self._obs_ws_enabled.isChecked():
            return

        host = (self._obs_ws_host.text() or "").strip() or "127.0.0.1"
        port_s = (self._obs_ws_port.text() or "").strip() or "4455"
        try:
            port = int(port_s)
        except ValueError:
            port = 4455
        port = max(1, min(65535, port))
        pw = (self._obs_ws_password.text() or "").strip()
        if not pw:
            pw = keyring_store.get_password(constants.KEY_OBS_WEBSOCKET_PASSWORD) or ""
        try:
            await asyncio.to_thread(
                run_obs_scene_action,
                host,
                port,
                pw,
                mode=str(payload.get("mode") or "program_scene"),
                scene_name=str(payload.get("scene_name") or ""),
                source_name=str(payload.get("source_name") or ""),
                visible=bool(payload.get("visible", True)),
                canvas_uuid=str(payload.get("canvas_uuid") or ""),
            )
        except ObsControlError as e:
            self._on_user_status(f"OBS: {e}")
        except (ImportError, OSError, RuntimeError, TypeError, ValueError) as e:
            logger.exception("OBS action execution failed")
            self._on_user_status(f"OBS: failed ({e})")

    async def _obs_test_connection_async(self) -> None:
        from stream_cheremsha.obs_ws.control import ObsControlError, obs_test_connection

        btn = self._btn_obs_ws_test
        old_btn_text = btn.text()
        res = self._lbl_obs_test_result
        title = self._tr("settings.obs_group")

        if not self._obs_ws_enabled.isChecked():
            msg = self._tr("settings.obs_test_when_disabled")
            res.setText(msg)
            res.setStyleSheet("color: #8b95a5;")
            self._on_user_status(msg)
            QMessageBox.information(self, title, msg)
            return

        btn.setEnabled(False)
        btn.setText(self._tr("settings.obs_test_busy"))
        res.clear()
        res.setStyleSheet("")

        host = (self._obs_ws_host.text() or "").strip() or "127.0.0.1"
        port_s = (self._obs_ws_port.text() or "").strip() or "4455"
        try:
            port = int(port_s)
        except ValueError:
            port = 4455
        port = max(1, min(65535, port))
        pw = (self._obs_ws_password.text() or "").strip()
        if not pw:
            pw = keyring_store.get_password(constants.KEY_OBS_WEBSOCKET_PASSWORD) or ""

        try:
            ver = await asyncio.to_thread(obs_test_connection, host, port, pw)
        except ObsControlError as e:
            msg = self._tr("obs.test_fail", detail=str(e))
            res.setText(msg)
            res.setStyleSheet("color: #fca5a5;")
            self._on_user_status(msg)
            QMessageBox.warning(self, title, msg)
        except (OSError, ValueError, TypeError) as e:
            logger.exception("OBS WebSocket test failed")
            msg = self._tr("obs.test_fail", detail=str(e))
            res.setText(msg)
            res.setStyleSheet("color: #fca5a5;")
            self._on_user_status(msg)
            QMessageBox.warning(self, title, msg)
        else:
            msg = self._tr("obs.test_ok", version=ver)
            res.setText(msg)
            res.setStyleSheet("color: #86efac;")
            self._on_user_status(msg)
            QMessageBox.information(self, title, msg)
        finally:
            btn.setEnabled(True)
            btn.setText(old_btn_text)

    def _actions_reload_scope(self, platform: str, account_key: str) -> None:
        k = self._actions_scope_key(platform, account_key)
        eng = self._actions_engines.get(k)
        if eng is not None:
            eng.set_rules(load_rules(k[0], k[1]))

    def _dispatch_actions_for_chat(self, message: ChatMessage) -> None:
        eng = self._get_app_actions_engine()
        ev = ChatMessageEvent(
            platform=message.platform,
            author=message.author,
            text=message.text,
            received_at=message.received_at,
            profile_picture_url=(message.author_avatar_url or "").strip(),
        )
        asyncio.ensure_future(eng.on_chat_message(ev))

    def _on_tiktok_gift(
        self,
        sender: str,
        gift_id: str,
        gift_name: str,
        count: int,
        icon_url: str = "",
        sender_avatar_url: str = "",
        tiktok_coin_each: int = 0,
        sender_user_key: str = "",
        gift_raw_json: str = "",
        tiktok_user_bundle_json: str = "",
        stream_host_unique_id: str = "",
    ) -> None:
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
        now = datetime.now(UTC)
        ev = GiftReceivedEvent(
            platform=ChatPlatform.TIKTOK,
            sender=sender,
            gift_id=gift_id,
            gift_name=gift_name,
            count=count,
            gift_icon_url=str(icon_url or ""),
            received_at=now,
            sender_avatar_url=str(sender_avatar_url or "").strip(),
            tiktok_coin_each=int(tiktok_coin_each or 0),
        )
        asyncio.ensure_future(eng.on_gift_received(ev))
        try:
            c = max(1, int(count))
        except (TypeError, ValueError):
            c = 1
        try:
            each = max(0, int(tiktok_coin_each or 0))
        except (TypeError, ValueError):
            each = 0
        total_coins = each * c
        if not self._closing:
            try:
                streamer = (stream_host_unique_id or "").strip()
                if not streamer:
                    streamer = (self._tiktok.connected_stream_unique_id or "").strip()
                if not streamer:
                    streamer = (self._tiktok_username.text() or "").strip()
                append_tiktok_gift_event(
                    anchor_username=streamer,
                    received_at=now,
                    sender_display=sender,
                    sender_user_key=(sender_user_key or "").strip(),
                    gift_id=gift_id,
                    gift_name=gift_name,
                    gift_count=c,
                    diamond_each=each,
                    diamonds_total=total_coins,
                    gift_icon_url=str(icon_url or ""),
                    sender_avatar_url=str(sender_avatar_url or "").strip(),
                    raw_json=gift_raw_json or "",
                    tiktok_user_bundle_json=tiktok_user_bundle_json or "",
                )
            except (OSError, sqlite3.Error) as exc:
                logger.warning("tiktok gifts sqlite: persist failed: %s", exc)
        if total_coins > 0 and self._points_enabled():
            gifter_unique = unique_id_from_user_bundle(tiktok_user_bundle_json or "")
            self._register_watch_activity(
                stable_key=sender_user_key,
                unique_id=gifter_unique,
                display_name=sender,
            )
            self._award_points(
                stable_key=sender_user_key,
                unique_id=gifter_unique,
                display_name=sender,
                delta=self._earn_tracker.config.coins_to_points(total_coins),
                reason="gift",
            )
        if total_coins > 0:
            prev_battle_phase = self._battle_controller.state().phase
            battle_hit = self._battle_controller.on_gift(
                sender_user_key=(sender_user_key or "").strip(),
                sender_display=(sender or "").strip(),
                sender_avatar_url=(sender_avatar_url or "").strip(),
                diamonds=total_coins,
                gift_id=(gift_id or "").strip(),
                gift_name=(gift_name or "").strip(),
            )
            self._sync_battle_ui_after_gift(prev_phase=prev_battle_phase)
            if (
                prev_battle_phase == BattlePhase.IDLE
                and self._battle_controller.state().phase == BattlePhase.IDLE
            ):
                br_cfg = load_battle_royale_overlay_config()
                if br_cfg.auto_arm_enabled:
                    n = self._battle_controller.count_auto_arm_candidates(cfg=br_cfg)
                    if n != self._battle_auto_arm_hint_count:
                        self._battle_auto_arm_hint_count = n
                        if n == 1:
                            self._on_user_status(
                                self._tr(
                                    "battle.need_second_viewer",
                                    threshold=br_cfg.auto_threshold_each,
                                    count=n,
                                ),
                            )
                        self._publish_battle_overlay_patch_sync()
            if battle_hit is not None:
                self._publish_battle_overlay_patch_sync()
                self._schedule_battle_overlay_publish()
            self._tiktok_top_gifters.add_coins(
                user_key=(sender_user_key or "").strip(),
                display_name=(sender or "").strip(),
                n=total_coins,
                avatar_url=(sender_avatar_url or "").strip(),
            )
            self._schedule_top_gifters_overlay_publish()
            self._schedule_king_overlay_publish()
            self._stream_pet.on_gift(
                platform=ChatPlatform.TIKTOK.value,
                user=sender,
                gift_name=gift_name,
                tiktok_coins=total_coins,
            )
            self._stream_goal.on_gift(
                sender=sender,
                gift_id=gift_id,
                gift_name=gift_name,
                count=count,
                icon_url=str(icon_url or ""),
                sender_avatar_url=str(sender_avatar_url or ""),
                tiktok_coin_each=tiktok_coin_each,
                sender_user_key=sender_user_key,
            )
            self._live_leaderboard.on_gift(
                sender=sender,
                count=count,
                tiktok_coin_each=tiktok_coin_each,
                sender_avatar_url=str(sender_avatar_url or ""),
                sender_user_key=sender_user_key,
            )
            self._social_rotator.on_tiktok_gift(
                sender=sender,
                count=count,
                tiktok_coin_each=tiktok_coin_each,
                sender_avatar_url=str(sender_avatar_url or ""),
                sender_user_key=sender_user_key,
            )
            self._community_world.on_gift(
                user=sender,
                user_key=sender_user_key,
                gift_name=gift_name,
                coins=total_coins,
                icon_url=str(icon_url or ""),
                avatar_url=str(sender_avatar_url or ""),
            )
            self._signal_system.on_gift(
                sender=sender,
                gift_name=gift_name,
                count=count,
                tiktok_coin_each=tiktok_coin_each,
                extra={
                    "gift_id": gift_id,
                    "icon_url": str(icon_url or ""),
                    "sender_avatar_url": str(sender_avatar_url or ""),
                    "sender_user_key": sender_user_key,
                },
            )

    def _ensure_widgets_window(self) -> QQuickView:
        if self._qml_widgets_win is not None:
            try:
                self._qml_widgets_win.close()
            except RuntimeError:
                pass
            self._qml_widgets_win = None
            self._widgets_qml_api = None
            self._widgets_window_qml_api = None

        view = QQuickView()
        view.setFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        try:
            if self.windowHandle() is not None:
                view.setTransientParent(self.windowHandle())
        except RuntimeError:
            pass
        view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        view.setMinimumSize(QSize(560, 420))
        view.resize(QSize(760, 560))

        try:
            base_url = self._overlay_public_base_url()
        except RuntimeError:
            base_url = ""
        self._widgets_qml_api = WidgetsQmlApi(
            overlay_base_url=base_url,
            pubsub=self._overlay_server.pubsub(),
        )
        self._widgets_qml_api.set_battle_host(self)
        self._widgets_qml_api.set_signal_system_controller(self._signal_system)
        self._widgets_window_qml_api = WidgetsWindowQmlApi(view=view)
        ctx = view.engine().rootContext()
        ctx.setContextProperty("api", self._widgets_qml_api)
        ctx.setContextProperty("tunnelApi", self._overlay_tunnel_qml_api)
        ctx.setContextProperty("winApi", self._widgets_window_qml_api)
        ctx.setContextProperty("widgetsWindow", view)
        qml_p = _qml_path("WidgetsView.qml")
        view.setSource(QUrl.fromLocalFile(str(qml_p)))

        self._qml_widgets_win = view
        return view

    def open_widgets(self) -> None:
        self._set_main_page(self._IX_WIDGETS)

    def open_actions(self) -> None:
        self._set_main_page(self._IX_ACTIONS)
        self._qml_api.refresh()

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
        await self._start_twitch_analytics(
            token=token,
            client_id=client_id,
            channel_login=channel,
        )

    async def _resolve_twitch_profile_picture(
        self,
        *,
        user_id: str = "",
        login: str = "",
        display_name: str = "",
    ) -> str:
        helix = self._twitch_helix
        if helix is None:
            return ""
        try:
            return await helix.resolve_profile_image_url(
                user_id=user_id,
                login=login or display_name,
            )
        except httpx.HTTPError as exc:
            logger.debug("Twitch profile image lookup failed: %s", exc)
            return ""

    async def _start_twitch_analytics(
        self,
        *,
        token: str,
        client_id: str,
        channel_login: str,
    ) -> None:
        await self._stop_twitch_analytics()
        tok = (token or "").strip()
        cid = (client_id or "").strip()
        login = (channel_login or "").strip().lstrip("#").lower()
        if not (tok and cid and login):
            return

        helix = TwitchHelixClient(client_id=cid, access_token=tok)
        self._twitch_helix = helix
        try:
            uid = await helix.get_user_id(login)
        except (httpx.HTTPError, ValueError, RuntimeError) as exc:
            self._on_user_status(f"Twitch Helix: {exc}")
            await helix.aclose()
            self._twitch_helix = None
            return
        if not uid:
            self._on_user_status("Twitch Helix: cannot resolve broadcaster id")
            await helix.aclose()
            self._twitch_helix = None
            return

        self._twitch_viewers_task = asyncio.create_task(
            self._twitch_poll_viewers(helix=helix, broadcaster_id=uid),
            name="twitch-viewers",
        )

        async def _dispatch_twitch_follow_actions(tu: TwitchNotifiedUser) -> None:
            if self._closing:
                return
            pic = await self._resolve_twitch_profile_picture(
                user_id=tu.user_id,
                login=tu.login,
                display_name=tu.display_name,
            )
            eng = self._get_app_actions_engine()
            await eng.on_twitch_follow(
                tu.display_name,
                datetime.now(UTC),
                profile_picture_url=pic,
            )

        async def _dispatch_twitch_sub_actions(
            tu: TwitchNotifiedUser,
            st: str,
            months: int,
            message: str,
        ) -> None:
            if self._closing:
                return
            pic = await self._resolve_twitch_profile_picture(
                user_id=tu.user_id,
                login=tu.login,
                display_name=tu.display_name,
            )
            eng = self._get_app_actions_engine()
            u_sub = tu.display_name
            mom = max(0, int(months))
            msg_sub = (message or "").strip()
            now_sub = datetime.now(UTC)
            if st == "sub":
                await eng.on_twitch_subscribe(u_sub, mom, now_sub, profile_picture_url=pic)
            elif st == "resub":
                await eng.on_twitch_resub(u_sub, mom, msg_sub, now_sub, profile_picture_url=pic)
            elif st == "gift":
                await eng.on_twitch_sub_gift(u_sub, mom, now_sub, profile_picture_url=pic)

        async def _dispatch_twitch_cheer_actions(tu: TwitchNotifiedUser, bits: int) -> None:
            if self._closing:
                return
            pic = await self._resolve_twitch_profile_picture(
                user_id=tu.user_id,
                login=tu.login,
                display_name=tu.display_name,
            )
            eng = self._get_app_actions_engine()
            await eng.on_twitch_cheer(
                tu.display_name,
                int(bits),
                datetime.now(UTC),
                profile_picture_url=pic,
            )

        async def _dispatch_twitch_raid_actions(tu: TwitchNotifiedUser, viewers: int) -> None:
            if self._closing:
                return
            pic = await self._resolve_twitch_profile_picture(
                user_id=tu.user_id,
                login=tu.login,
                display_name=tu.display_name,
            )
            eng = self._get_app_actions_engine()
            await eng.on_twitch_raid(
                tu.display_name,
                int(viewers),
                datetime.now(UTC),
                profile_picture_url=pic,
            )

        def _on_follow(tu: TwitchNotifiedUser) -> None:
            self._twitch_analytics.on_follow(tu.display_name)
            it = ActivityItem(
                platform="twitch",
                kind="follow",
                user=tu.display_name or "?",
                detail="",
                count=1,
                icon_url="",
                time_hms=now_hms(),
            )
            self._publish_activity_item(it)
            asyncio.ensure_future(_dispatch_twitch_follow_actions(tu))
            self._stream_pet.on_follow(user=tu.display_name)

        def _on_sub(tu: TwitchNotifiedUser, sub_type: str, months: int, message: str = "") -> None:
            self._twitch_analytics.on_sub(tu.display_name, sub_type, months, message)
            st = (sub_type or "").strip()
            if st not in ("sub", "resub", "gift"):
                return
            detail = ""
            if st == "resub":
                m = max(0, int(months))
                detail = f"{m}m" if m else ""
            it = ActivityItem(
                platform="twitch",
                kind=st,  # type: ignore[arg-type]
                user=tu.display_name or "?",
                detail=detail,
                count=1,
                icon_url="",
                time_hms=now_hms(),
            )
            self._publish_activity_item(it)
            asyncio.ensure_future(_dispatch_twitch_sub_actions(tu, st, months, message))

        def _on_cheer(tu: TwitchNotifiedUser, bits: int) -> None:
            self._twitch_analytics.on_cheer(tu.display_name, bits)
            asyncio.ensure_future(_dispatch_twitch_cheer_actions(tu, bits))
            self._stream_pet.on_gift(
                platform=ChatPlatform.TWITCH.value,
                user=tu.display_name,
                gift_name=f"{int(bits)} bits",
                twitch_bits=int(bits),
            )

        def _on_raid(tu: TwitchNotifiedUser, viewers: int) -> None:
            self._twitch_analytics.on_raid(tu.display_name, viewers)
            asyncio.ensure_future(_dispatch_twitch_raid_actions(tu, viewers))

        cbs = TwitchEventSubCallbacks(
            on_follow=_on_follow,
            on_sub=_on_sub,
            on_cheer=_on_cheer,
            on_raid=_on_raid,
            on_status=self._on_user_status,
        )
        es = TwitchEventSubClient(helix=helix, broadcaster_id=uid, callbacks=cbs)
        self._twitch_eventsub = es
        await es.start()

    async def _stop_twitch_analytics(self) -> None:
        t, self._twitch_viewers_task = self._twitch_viewers_task, None
        if t is not None:
            t.cancel()
            await asyncio.gather(t, return_exceptions=True)

        es, self._twitch_eventsub = self._twitch_eventsub, None
        if es is not None:
            await es.stop()

        helix, self._twitch_helix = self._twitch_helix, None
        if helix is not None:
            await helix.aclose()

        self._twitch_analytics.resetSession()

    async def _twitch_poll_viewers(self, *, helix: TwitchHelixClient, broadcaster_id: str) -> None:
        backoff = 5.0
        while True:
            try:
                v = await helix.get_stream_viewers(broadcaster_id)
                if v is not None:
                    self._twitch_analytics.enqueue_viewers(v)
                    self._social_rotator.on_viewers("twitch", int(v))
                backoff = 10.0
            except asyncio.CancelledError:
                raise
            except (httpx.HTTPError, RuntimeError, ValueError) as exc:
                logger.debug("Twitch viewers poll error: %s", exc)
                backoff = min(backoff * 1.6, 60.0)
            await asyncio.sleep(backoff)

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
        self._youtube_analytics.resetSession()
        await self._youtube.start(url if url else None)
        self._refresh_footer()
        self._qml_refresh_if_visible()

    async def _start_tiktok(self) -> None:
        user = self._tiktok_username.text().strip()
        if not user:
            QMessageBox.warning(self, self._tr("dlg.tiktok"), self._tr("dlg.tiktok_need_username"))
            self._tiktok_enabled = False
            return
        await self._tiktok.start(user)

    # -------- Kick --------
    def _schedule_kick_browser_login(self) -> None:
        asyncio.ensure_future(self._kick_browser_login())

    async def _kick_browser_login(self) -> None:
        cfg = KickOAuthConfig.from_env()
        if cfg is None:
            QTimer.singleShot(
                0,
                lambda: QMessageBox.warning(
                    self,
                    self._tr("dlg.kick"),
                    self._tr("dlg.kick_need_client_config"),
                ),
            )
            return
        try:
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices

            def _open(url: str) -> None:
                QDesktopServices.openUrl(QUrl(url))

            from stream_cheremsha.chat.kick_oauth import run_kick_oauth

            self._on_user_status(self._tr("status.kick_oauth_prompt"))
            code, _state, pkce = await run_kick_oauth(cfg, _open)
        except (OSError, RuntimeError, TimeoutError, ValueError) as e:
            QTimer.singleShot(
                0,
                lambda e=e: QMessageBox.warning(self, self._tr("dlg.kick_oauth"), str(e)),
            )
            return
        try:
            payload = await exchange_code(cfg, pkce, code)
        except (ValueError, httpx.HTTPError, OSError, RuntimeError) as e:
            QTimer.singleShot(
                0,
                lambda e=e: QMessageBox.warning(self, self._tr("dlg.kick_oauth"), str(e)),
            )
            return
        kick_credentials.save_oauth_bundle(payload)
        token = str(payload.get("access_token") or "")
        api = None
        if token:
            try:
                api = KickApiClient(token)
                me = await api.get_me()
                name = str(me.get("name") or "").strip()
                if name:
                    kick_credentials.set_authorized_channel(name)
                    self._kick_channel.setText(name)
            except (ValueError, httpx.HTTPError, OSError, RuntimeError) as e:
                logger.debug("Kick channel resolve failed: %s", e)
            finally:
                if api is not None:
                    await api.aclose()
        self._on_user_status(self._tr("status.kick_browser_ok"))
        self._refresh_connection_panels()

    async def _start_kick(self) -> None:
        channel = (self._kick_channel.text() or "").strip().lstrip("@").strip()
        if not channel:
            channel = kick_credentials.authorized_channel()
        if not channel:
            QMessageBox.warning(self, self._tr("dlg.kick"), self._tr("dlg.kick_need_channel"))
            self._kick_enabled = False
            return
        self._kick_analytics.resetSession()
        cid = kick_credentials.chatroom_id()
        await self._kick.start(channel, chatroom_id=cid or None)
        self._schedule_kick_viewer_poll(channel)
        self._refresh_footer()
        self._qml_refresh_if_visible()

    def _schedule_kick_viewer_poll(self, channel: str) -> None:
        asyncio.ensure_future(self._kick_poll_viewers(channel))

    async def _kick_poll_viewers(self, channel: str) -> None:
        backoff = 5.0
        while self._kick_enabled and not self._closing:
            try:
                cfg = KickOAuthConfig.from_env()
                token = await kick_credentials.ensure_valid_access_token()
                if cfg is not None and token:
                    api = KickApiClient(token)
                    try:
                        info = await api.fetch_live_channel(channel)
                        self._kick_analytics.enqueue_viewers(info.viewer_count)
                        self._social_rotator.on_viewers("kick", int(info.viewer_count))
                    finally:
                        await api.aclose()
                backoff = 30.0
            except (ValueError, httpx.HTTPError, OSError, RuntimeError) as exc:
                logger.debug("Kick viewers poll error: %s", exc)
                backoff = min(backoff * 1.5, 60.0)
            try:
                await asyncio.sleep(backoff)
            except asyncio.CancelledError:
                raise

    def _logout_kick(self) -> None:
        asyncio.ensure_future(self._kick_logout())

    async def _kick_logout(self) -> None:
        await self._kick.stop()
        kick_credentials.clear_oauth_bundle()
        kick_credentials.clear_channel()
        kick_credentials.set_chatroom_id(0)
        self._kick_analytics.resetSession()
        self._on_user_status(self._tr("status.logout_kick"))
        self._refresh_connection_panels()

    def _on_kick_follow_any(self, user: str, _stable_key: str = "") -> None:
        if self._closing:
            return
        eng = self._get_app_actions_engine()
        asyncio.ensure_future(eng.on_kick_follow((user or "").strip(), datetime.now(UTC)))
        self._kick_analytics.enqueue_follow(user)
        it = ActivityItem(
            platform="kick",
            kind="follow",
            user=(user or "").strip() or "?",
            detail="",
            count=1,
            icon_url="",
            time_hms=now_hms(),
        )
        self._publish_activity_item(it)

    def _on_kick_sub_any(self, user: str, months: int) -> None:
        if self._closing:
            return
        eng = self._get_app_actions_engine()
        asyncio.ensure_future(
            eng.on_kick_subscription((user or "").strip(), int(months), datetime.now(UTC))
        )
        self._kick_analytics.enqueue_sub(user, months)
        it = ActivityItem(
            platform="kick",
            kind="subscription",
            user=(user or "").strip() or "?",
            detail=f"{int(months)}m" if months else "",
            count=1,
            icon_url="",
            time_hms=now_hms(),
        )
        self._publish_activity_item(it)

    def _on_kick_gift_sub_any(self, user: str, count: int) -> None:
        if self._closing:
            return
        eng = self._get_app_actions_engine()
        asyncio.ensure_future(
            eng.on_kick_gift_subscription((user or "").strip(), int(count), datetime.now(UTC))
        )
        self._kick_analytics.enqueue_gift_sub(user, count)
        it = ActivityItem(
            platform="kick",
            kind="gift",
            user=(user or "").strip() or "?",
            detail="gift sub",
            count=max(1, int(count)),
            icon_url="",
            time_hms=now_hms(),
        )
        self._publish_activity_item(it)

    def _on_kick_gift_any(self, user: str, amount: int) -> None:
        if self._closing:
            return
        eng = self._get_app_actions_engine()
        asyncio.ensure_future(
            eng.on_kick_gift((user or "").strip(), int(amount), datetime.now(UTC))
        )
        self._kick_analytics.enqueue_kick_gift(user, amount)
        it = ActivityItem(
            platform="kick",
            kind="kick_gift",
            user=(user or "").strip() or "?",
            detail="",
            count=max(1, int(amount)),
            icon_url="",
            time_hms=now_hms(),
        )
        self._publish_activity_item(it)

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

    async def announce_donation_tts(self, line: str, donor_name: str | None = None) -> None:
        """Speak one donation line (used by Donations live TTS). Errors are logged, not modal."""
        text = (line or "").strip()
        if not text:
            return
        author = (donor_name or "").strip() or "?"
        text, replaced = await self._apply_openai_moderation_to_tts_text(text, author)
        text = self._maybe_strip_non_letters_for_tts(text, moderation_replaced=replaced)
        text = (text or "").strip()
        if not text:
            return
        self._apply_audio_device_selection()
        try:
            audio = await self._tts.synthesize(text)
            await self._sink.play_mp3(audio)
        except (OSError, ValueError) as e:
            logger.warning("Donation TTS: %s", e)

    async def speak_action_tts(self, text: str, author: str | None = None) -> None:
        """Speak text from platform Actions; errors propagate to the actions engine."""
        line = (text or "").strip()
        if not line:
            return
        who = (author or "").strip() or "?"
        line, replaced = await self._apply_openai_moderation_to_tts_text(line, who)
        line = self._maybe_strip_non_letters_for_tts(line, moderation_replaced=replaced)
        line = (line or "").strip()
        if not line:
            return
        self._apply_audio_device_selection()
        audio = await self._tts.synthesize(line)
        await self._sink.play_mp3(audio)

    async def _test_tts(self) -> None:
        text = self._test_phrase.text().strip()
        if not text:
            return
        author_label = self._tr("chat.test_author")
        text, replaced = await self._apply_openai_moderation_to_tts_text(text, author_label)
        text = self._maybe_strip_non_letters_for_tts(text, moderation_replaced=replaced)
        text = self._maybe_prefix_tts_author(author_label, text, moderation_replaced=replaced)
        text = (text or "").strip()
        if not text:
            return
        self._apply_audio_device_selection()
        try:
            audio = await self._tts.synthesize(text)
            await self._sink.play_mp3(audio)
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, self._tr("dlg.tts"), str(e))

    async def _flush_tts_queues(self) -> None:
        """Force-stop pending TTS work and current playback."""
        # Stop playback ASAP (even if synth is still running).
        try:
            self._sink.shutdown()
        except RuntimeError:
            # Qt objects may already be shutting down; ignore.
            pass
        # Cancel in-flight TTS processing + drop queued work.
        await self._coordinator.flush_tts()
        self._on_user_status(self._tr("audio.flush_queues"))

    def _overlay_public_base_url(self) -> str:
        local_url = self._overlay_server.base_url()
        if not bool(self._settings.value(constants.SETTINGS_OVERLAY_TUNNEL_ENABLED, False, bool)):
            return local_url
        return f"https://{embedded.OVERLAY_PUBLIC_HOSTNAME}:17171"

    def _apply_overlay_urls_to_qml(self, *, local_url: str) -> None:
        base = self._overlay_public_base_url() if local_url else ""
        if self._widgets_qml_api is not None:
            self._widgets_qml_api.set_overlay_base_url(base)
        if self._docks_qml_api is not None:
            self._docks_qml_api.set_base_url(base)
        if self._overlay_tunnel_qml_api is not None:
            self._overlay_tunnel_qml_api.refresh_from_tunnel(local_base_url=local_url)

    async def _ensure_tunnel_cli_installed(
        self, provider_str: str, *, prompt_install: bool
    ) -> bool:
        if not provider_needs_cli(provider_str):
            return True
        if is_tunnel_cli_installed(provider_str):
            return True

        uk = self._locale != "en"
        auto_install = provider_auto_installs_cli(provider_str)
        if not auto_install and not prompt_install:
            return False

        if not is_winget_available():
            title = tunnel_cli_title(provider_str)
            if uk:
                body = (
                    f"{title} не знайдено, а winget недоступний. "
                    "Встановіть вручну або через Microsoft Store."
                )
            else:
                body = (
                    f"{title} was not found and winget is unavailable. "
                    "Install manually or from Microsoft Store."
                )
            QMessageBox.warning(self, title, body)
            return False

        if not auto_install:
            dlg_title, dlg_text = install_prompt_labels(provider_str, locale=self._locale)
            answer = QMessageBox.question(
                self,
                dlg_title,
                dlg_text,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return False
            dlg_title_for_error = dlg_title
        else:
            dlg_title_for_error = tunnel_cli_title(provider_str)

        if self._overlay_tunnel_qml_api is not None:
            self._overlay_tunnel_qml_api.set_tunnel_status_message(
                install_status_message(provider_str, locale=self._locale),
            )

        ok, err = await install_tunnel_tool_via_winget(provider_str)
        if not ok:
            detail = err or ("Не вдалося встановити" if uk else "Installation failed")
            QMessageBox.warning(self, dlg_title_for_error, detail)
            return False
        return True

    async def apply_overlay_tunnel(self, *, prompt_install: bool = False) -> None:
        if self._closing:
            return
        try:
            local_url = self._overlay_server.base_url()
        except RuntimeError:
            return

        enabled = bool(self._settings.value(constants.SETTINGS_OVERLAY_TUNNEL_ENABLED, False, bool))
        if enabled:
            await self._overlay_tunnel.stop()
            if self._overlay_tunnel_qml_api is not None:
                self._overlay_tunnel_qml_api.set_tunnel_status_message(
                    f"https://{embedded.OVERLAY_PUBLIC_HOSTNAME}:17171"
                )
        else:
            await self._overlay_tunnel.stop()

        self._apply_overlay_urls_to_qml(local_url=local_url)

    async def run_startup(self) -> None:
        try:
            if self._closing:
                return
            self._on_user_status(self._tr("startup.workers"))
            self._asyncio_loop = asyncio.get_running_loop()
            self._music_queue.set_loop(self._asyncio_loop)
            cert_paths = ensure_valid_ssl()
            if cert_paths is not None:
                self._overlay_server.set_tls_files(*cert_paths)
            await self._overlay_server.start()
            if self._closing:
                await self._overlay_server.stop()
                return
            logger.info("Overlay server: %s", self._overlay_server.base_url())
            self._stream_pet.set_pubsub(self._overlay_server.pubsub())
            self._stream_pet.set_event_loop(self._asyncio_loop)
            self._stream_pet.start()
            self._stream_goal.set_pubsub(self._overlay_server.pubsub())
            self._stream_goal.set_event_loop(self._asyncio_loop)
            self._stream_goal.start()
            self._live_leaderboard.set_pubsub(self._overlay_server.pubsub())
            self._live_leaderboard.set_event_loop(self._asyncio_loop)
            self._live_leaderboard.start()
            self._social_rotator.set_pubsub(self._overlay_server.pubsub())
            self._social_rotator.set_event_loop(self._asyncio_loop)
            self._social_rotator.start()
            self._community_world.set_pubsub(self._overlay_server.pubsub())
            self._community_world.set_event_loop(self._asyncio_loop)
            self._community_world.start()
            self._webcam_frame.set_pubsub(self._overlay_server.pubsub())
            self._webcam_frame.set_event_loop(self._asyncio_loop)
            self._webcam_frame.start()
            self._signal_system.set_pubsub(self._overlay_server.pubsub())
            self._signal_system.set_event_loop(self._asyncio_loop)
            self._signal_system.start()
            await self.apply_overlay_tunnel()
            self._schedule_king_overlay_publish()
            self._publish_battle_overlay_patch_sync()
            self._music_player = MusicPlayer(
                queue=self._music_queue,
                sink=self._sink,
                on_status=self._on_user_status,
                backend=str(
                    self._settings.value(_SETTINGS_MUSIC_BACKEND, "app", str) or ""
                ).strip(),
            )
            self._music_player.set_volume_percent(
                int(self._settings.value("music/volume_percent", 100)),
            )
            await self._music_player.start()
            if self._online_publish_task is None:
                self._online_publish_task = asyncio.create_task(
                    self._publish_online_loop(),
                    name="online-publish",
                )
            await self._swap_tts_backend()
            await self._coordinator.start_workers()
            vol = int(self._settings.value("audio/volume", 100))
            self._sink.set_volume(vol / 100.0)
            self._apply_audio_device_selection()
            self._on_user_status(self._tr("startup.ready"))
            await self._apply_music_backend_from_settings()
            await self._apply_telegram_from_settings()
            await self._maybe_auto_start_platforms()
            if bool(self._settings.value(_SETTINGS_UPDATES_CHECK_ON_STARTUP, True, bool)):
                asyncio.create_task(
                    self._check_for_updates(interactive=False),
                    name="updates-startup-check",
                )
            await self._warm_qml_page_cache()
        finally:
            self.startup_finished.emit()

    async def _apply_telegram_from_settings(self) -> None:
        if self._closing:
            return
        enabled = bool(self._settings.value(_SETTINGS_TELEGRAM_ENABLED, False, bool))
        songs_enabled = bool(
            self._settings.value(_SETTINGS_TELEGRAM_SONG_REQUESTS_ENABLED, True, bool),
        )
        tok = (keyring_store.get_password(constants.KEY_TELEGRAM_BOT_TOKEN) or "").strip()
        admin_raw = str(self._settings.value(_SETTINGS_TELEGRAM_ADMIN_ID, "", str) or "").strip()
        try:
            admin_id = int(admin_raw) if admin_raw else 0
        except ValueError:
            admin_id = 0

        if not enabled:
            if self._telegram is not None:
                self._telegram.stop()
                self._telegram = None
            return

        if not tok or admin_id <= 0:
            # Settings incomplete; keep disabled without crashing startup.
            if self._telegram is not None:
                self._telegram.stop()
                self._telegram = None
            return

        # Restart if config changed.
        if self._telegram is not None:
            self._telegram.stop()
            self._telegram = None

        loop = self._asyncio_loop
        if loop is None:
            return

        def call_on_main_loop(fn) -> None:
            asyncio.run_coroutine_threadsafe(fn(), loop)

        async def enqueue_song(
            video_id: str,
            requested_by: str,
            requester_chat_id: int,
            requester_user_id: int = 0,
        ) -> str | tuple[str, Literal["info"]] | None:
            loc = self._get_locale()
            vid = (video_id or "").strip()
            if not vid:
                return self._tr("telegram.song.empty_link")

            # Points economy: resolve wallet and fail fast before any network calls.
            points_on = self._points_enabled()
            cost = self._load_points_config().song_cost if points_on else 0
            charged_unique = ""
            if points_on and cost > 0:
                charged_unique = get_telegram_link(int(requester_user_id)) or ""
                if not charged_unique:
                    return self._tr("telegram.song.points_link_required")
                balance = get_balance_for_unique_id(charged_unique)
                if balance < cost:
                    return self._points_insufficient_message(balance, cost)

            def _reserve_points() -> bool:
                if not (points_on and cost > 0):
                    return True
                return try_spend_for_unique_id(
                    unique_id=charged_unique,
                    amount=cost,
                    reason="song_order",
                    ref=vid,
                )

            def _refund_points() -> None:
                if points_on and cost > 0 and charged_unique:
                    refund_for_unique_id(
                        unique_id=charged_unique,
                        amount=cost,
                        reason="song_refund",
                        ref=vid,
                    )

            def _insufficient_now() -> str:
                bal = get_balance_for_unique_id(charged_unique)
                return self._points_insufficient_message(bal, cost)

            max_min_raw = self._settings.value(_SETTINGS_MUSIC_MAX_DURATION_MIN, 5)
            try:
                max_min = int(max_min_raw)
            except (TypeError, ValueError):
                max_min = 5
            max_min = max(0, max_min)

            title = ""
            if max_min > 0:
                try:
                    meta = await asyncio.to_thread(fetch_youtube_meta, vid)
                except (OSError, ValueError, RuntimeError) as e:
                    logger.debug("Music duration fetch failed: %s", e)
                    return self._tr("telegram.song.duration_unknown")
                dur = meta.duration_seconds
                title = (meta.title or "").strip()
                if dur is None:
                    return self._tr("telegram.song.duration_unknown")
                if dur > int(max_min) * 60:
                    mins = max(1, (dur + 59) // 60)
                    return self._tr(
                        "telegram.song.too_long",
                        mins=str(mins),
                        limit=str(int(max_min)),
                    )

            tiktok_filter = bool(
                self._settings.value(_SETTINGS_TELEGRAM_TIKTOK_LYRICS_FILTER, False, bool),
            )
            if tiktok_filter:
                genius_tok = (
                    keyring_store.get_password(constants.KEY_GENIUS_CLIENT_ACCESS_TOKEN) or ""
                ).strip()
                groq_key = (keyring_store.get_password(constants.KEY_GROQ_API_KEY) or "").strip()
                if not groq_key:
                    groq_key = (
                        keyring_store.get_password(constants.KEY_LEGACY_GEMINI_API_KEY) or ""
                    ).strip()
                if not genius_tok or not groq_key:
                    return self._tr("telegram.song.tiktok_need_keys")
                if not title:
                    try:
                        meta_title = await asyncio.to_thread(fetch_youtube_meta, vid)
                    except (OSError, ValueError, RuntimeError) as e:
                        logger.debug("YouTube meta for TikTok filter failed: %s", e)
                        return self._tr("telegram.song.title_unknown")
                    title = (meta_title.title or "").strip()
                if not title:
                    return self._tr("telegram.song.title_unknown")
                try:
                    if await youtube_title_indicates_russian_artist_area(title):
                        return self._tr("telegram.song.musicbrainz_russian_origin")
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.warning("MusicBrainz artist-area check failed: %s", e)
                try:
                    lyrics = await asyncio.to_thread(
                        fetch_lyrics_for_youtube_title,
                        genius_tok,
                        title,
                    )
                except Exception as e:
                    logger.warning("Genius lyrics fetch failed: %s", e)
                    return self._tr("telegram.song.genius_unavailable")
                lyrics_stripped = (lyrics or "").strip()
                if not lyrics_stripped:
                    logger.debug(
                        "TikTok lyrics filter: no Genius lyrics for %r — Groq title-only check.",
                        title,
                    )
                try:
                    verdict = await analyze_lyrics_with_groq(
                        groq_key,
                        lyrics_stripped,
                        loc,
                        youtube_title=title,
                    )
                except TikTokLyricsCheckError as e:
                    return str(e)
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.warning("Groq TikTok check failed: %s", e)
                    return self._tr("telegram.song.check_unavailable")
                if verdict.status == "Banned":
                    return format_tiktok_reject_reason(verdict, ui_locale=loc)
                if verdict.status == "Risky":
                    if not _reserve_points():
                        return _insufficient_now()
                    pending_id = secrets.token_hex(8)
                    vline = ", ".join(verdict.violations[:6]) if verdict.violations else "—"
                    rs = verdict.risk_score
                    rs_s = "—" if rs is None else str(rs)
                    admin_html = self._tr(
                        "telegram.admin.risky_track",
                        title=html.escape(title),
                        video_id=html.escape(vid),
                        requested_by=html.escape(requested_by),
                        risk_score=html.escape(rs_s),
                        violations=html.escape(vline),
                    )
                    self._telegram_risky_pending[pending_id] = _RiskyPendingTrack(
                        video_id=vid,
                        requested_by=requested_by,
                        title=title,
                        requester_chat_id=int(requester_chat_id),
                        charged_unique_id=charged_unique if (points_on and cost > 0) else "",
                        charged_amount=cost if (points_on and cost > 0) else 0,
                    )
                    tg = self._telegram
                    if tg is not None:
                        tg.schedule_risky_review(
                            pending_id=pending_id,
                            admin_message_html=admin_html,
                        )
                    return (self._tr("telegram.song.risky_sent_to_admin"), "info")

            if not _reserve_points():
                return _insufficient_now()
            try:
                new_track = await self._music_queue.enqueue(video_id=vid, requested_by=requested_by)
            except Exception:
                _refund_points()
                raise
            if title:
                asyncio.create_task(self._music_queue.set_track_title(new_track.id, title))
            else:
                asyncio.create_task(
                    self._fetch_music_title_for_track(new_track.id, new_track.video_id),
                )
            return None

        async def skip_song() -> None:
            mp = self._music_player
            if mp is not None:
                await mp.skip_now()
                return
            await self._music_queue.skip()

        async def remove_song_by_id(tid: str) -> bool:
            tr = await self._music_queue.remove_by_id(tid)
            return tr is not None

        async def list_queue(limit: int) -> tuple[dict[str, str] | None, list[dict[str, str]]]:
            cur, q = await self._music_queue.list_queue(limit=limit)
            cur_map = None
            if cur is not None:
                cur_map = {"id": cur.id, "video_id": cur.video_id, "requested_by": cur.requested_by}
            q_maps = [
                {"id": t.id, "video_id": t.video_id, "requested_by": t.requested_by} for t in q
            ]
            return (cur_map, q_maps)

        async def on_risky_admin_decision(pending_id: str, approved: bool) -> RiskyDecisionResult:
            pending = self._telegram_risky_pending.pop(pending_id, None)
            if pending is None:
                return RiskyDecisionResult(
                    handled=False,
                    answer_hint=self._tr("telegram.admin.risky_already_done"),
                )
            tg = self._telegram
            if approved:
                try:
                    new_track = await self._music_queue.enqueue(
                        video_id=pending.video_id,
                        requested_by=pending.requested_by,
                    )
                except Exception as e:
                    logger.warning("Risky approve enqueue failed: %s", e)
                    self._telegram_risky_pending[pending_id] = pending
                    return RiskyDecisionResult(
                        handled=False,
                        answer_hint=self._tr("telegram.admin.risky_enqueue_failed"),
                    )
                if pending.title:
                    asyncio.create_task(
                        self._music_queue.set_track_title(new_track.id, pending.title),
                    )
                else:
                    asyncio.create_task(
                        self._fetch_music_title_for_track(new_track.id, new_track.video_id),
                    )
                if tg is not None and pending.requester_chat_id > 0:
                    msg = self._tr(
                        "telegram.song.risky_approved",
                        video_id=html.escape(pending.video_id),
                    )
                    tg.send_html_message_to_chat(pending.requester_chat_id, msg)
                return RiskyDecisionResult(
                    handled=True,
                    answer_hint=self._tr("telegram.admin.risky_approved_answer"),
                )
            if pending.charged_amount > 0 and pending.charged_unique_id:
                refund_for_unique_id(
                    unique_id=pending.charged_unique_id,
                    amount=pending.charged_amount,
                    reason="song_refund_denied",
                    ref=pending.video_id,
                )
            if tg is not None and pending.requester_chat_id > 0:
                tg.send_html_message_to_chat(
                    pending.requester_chat_id,
                    self._tr("telegram.song.risky_rejected"),
                )
            return RiskyDecisionResult(
                handled=True,
                answer_hint=self._tr("telegram.admin.risky_rejected_answer"),
            )

        async def start_tiktok_link_challenge(telegram_id: int) -> str | None:
            try:
                return create_telegram_link_challenge(telegram_id=int(telegram_id))
            except (OSError, sqlite3.Error, RuntimeError) as exc:
                logger.warning("points: create link challenge failed: %s", exc)
                return None

        async def cancel_tiktok_link_challenge_cb(telegram_id: int) -> None:
            try:
                cancel_telegram_link_challenge(telegram_id=int(telegram_id))
            except (OSError, sqlite3.Error) as exc:
                logger.warning("points: cancel link challenge failed: %s", exc)

        async def points_status(telegram_id: int) -> tuple[str | None, int, int]:
            cost = self._load_points_config().song_cost if self._points_enabled() else 0
            try:
                handle = get_telegram_link(int(telegram_id))
                if not handle:
                    return (None, 0, cost)
                bal = get_balance_for_unique_id(handle)
            except (OSError, sqlite3.Error) as exc:
                logger.warning("points: status failed: %s", exc)
                return (None, 0, cost)
            return (handle, bal, cost)

        self._telegram = TelegramBotService(
            token=tok,
            admin_id=admin_id,
            song_requests_enabled=songs_enabled,
            call_on_main_loop=call_on_main_loop,
            enqueue_song=enqueue_song,
            skip_song=skip_song,
            remove_song_by_id=remove_song_by_id,
            list_queue=list_queue,
            on_risky_admin_decision=on_risky_admin_decision,
            tiktok_lyrics_filter_enabled=bool(
                self._settings.value(_SETTINGS_TELEGRAM_TIKTOK_LYRICS_FILTER, False, bool),
            ),
            moderation_notice_text=lambda: self._tr("telegram.song.moderating_line"),
            points_enabled=self._points_enabled(),
            start_tiktok_link_challenge=start_tiktok_link_challenge,
            cancel_tiktok_link_challenge=cancel_tiktok_link_challenge_cb,
            points_status=points_status,
        )
        self._telegram.start()

    async def _apply_music_backend_from_settings(self) -> None:
        if self._closing:
            return
        mp = self._music_player
        if mp is None:
            return
        backend = str(self._settings.value(_SETTINGS_MUSIC_BACKEND, "app", str) or "").strip()
        mp.set_backend("mpv" if backend == "mpv" else "app")
        mp.set_volume_percent(int(self._settings.value("music/volume_percent", 100)))

    async def _publish_online_loop(self) -> None:
        while True:
            try:
                if not self._closing:
                    ps = self._overlay_server.pubsub()
                    state = {
                        "twitch": {
                            "current": int(self._twitch_analytics.viewersCurrent),
                            "peak": int(self._twitch_analytics.viewersPeak),
                        },
                        "tiktok": {
                            "current": int(self._tiktok_analytics.onlineViewersCurrent),
                            "total": int(self._tiktok_analytics.onlineViewersTotal),
                            "gifts": int(self._tiktok_analytics.giftUnitsTotal),
                            "diamonds": int(self._tiktok_analytics.diamondsTotal),
                        },
                        "youtube": {
                            "current": int(self._youtube_analytics.viewersCurrent),
                            "peak": int(self._youtube_analytics.viewersPeak),
                            "messages": int(self._youtube_analytics.messagesSession),
                            "unique": int(self._youtube_analytics.uniqueChattersSession),
                            "superchats": int(self._youtube_analytics.superChatsSession),
                            "memberships": int(self._youtube_analytics.membershipsSession),
                        },
                        "kick": {
                            "current": int(self._kick_analytics.viewersCurrent),
                            "peak": int(self._kick_analytics.viewersPeak),
                            "messages": int(self._kick_analytics.messagesSession),
                            "follows": int(self._kick_analytics.followsSession),
                            "subscriptions": int(self._kick_analytics.subscriptionsSession),
                            "gift_subs": int(self._kick_analytics.giftSubsSession),
                            "kicks": int(self._kick_analytics.kicksSession),
                        },
                        "updated_at": online_now_hms(),
                    }
                    await ps.publish("overlay:online:main", online_state_patch(state))  # type: ignore[arg-type]
            except asyncio.CancelledError:
                raise
            except RuntimeError:
                # Overlay server may not be ready or may be shutting down.
                pass
            await asyncio.sleep(5.0)

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
        if (
            bool(self._settings.value(_SETTINGS_AUTOSTART_TIKTOK, False, bool))
            and not self._tiktok.running
        ):
            user = (self._tiktok_username.text() or "").strip().lstrip("@").strip()
            if user:
                self._tiktok_enabled = True
                await self._start_tiktok()
        if (
            bool(self._settings.value(_SETTINGS_AUTOSTART_KICK, False, bool))
            and not self._kick.running
        ):
            channel = (self._kick_channel.text() or "").strip().lstrip("@").strip()
            if channel:
                self._kick_enabled = True
                await self._start_kick()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._closing:
            event.accept()
            return
        pop = self._chat_popout
        if pop is not None and shiboken6.isValid(pop):
            pop.close()
            self._chat_popout = None
        save_window_geometry(KEY_MAIN_WINDOW, self)
        try:
            self._settings.sync()
        except (RuntimeError, OSError):
            pass
        self._closing = True
        h = self._top_likers_publish_handle
        if h is not None:
            h.cancel()
            self._top_likers_publish_handle = None
        hg = self._top_gifters_publish_handle
        if hg is not None:
            hg.cancel()
            self._top_gifters_publish_handle = None
        hk = self._king_overlay_publish_handle
        if hk is not None:
            hk.cancel()
            self._king_overlay_publish_handle = None
        # We run an async shutdown sequence; hide immediately so the user doesn't
        # need to click close twice while teardown runs in the background.
        try:
            self.setEnabled(False)
            self.hide()
        except RuntimeError:
            # Window may already be in teardown; keep going.
            pass
        event.ignore()
        asyncio.ensure_future(self._async_shutdown())

    async def _async_shutdown(self) -> None:
        """Tear down chat, workers, TTS, audio, GPU; always quit Qt even on errors."""
        app = QApplication.instance()
        watchdog = threading.Timer(6.0, os._exit, args=(0,))
        watchdog.daemon = True
        watchdog.start()
        try:
            # Release the listening port before any potentially slow service cleanup.
            # Otherwise the watchdog can terminate the process while 17171 is still bound.
            try:
                await self._overlay_tunnel.stop()
            except (OSError, RuntimeError, ValueError, TypeError) as e:
                logger.exception("Shutdown step failed (overlay_tunnel.stop): %s", e)
            try:
                await self._overlay_server.stop()
            except (OSError, RuntimeError, ValueError, TypeError) as e:
                logger.exception("Shutdown step failed (overlay_server.stop): %s", e)

            t, self._online_publish_task = self._online_publish_task, None
            if t is not None:
                t.cancel()
                await asyncio.gather(t, return_exceptions=True)

            try:
                self._stream_goal.stop()
            except (OSError, RuntimeError, ValueError, TypeError) as e:
                logger.exception("Shutdown step failed (stream_goal.stop): %s", e)

            try:
                self._live_leaderboard.stop()
            except (OSError, RuntimeError, ValueError, TypeError) as e:
                logger.exception("Shutdown step failed (live_leaderboard.stop): %s", e)

            try:
                self._community_world.stop()
            except (OSError, RuntimeError, ValueError, TypeError) as e:
                logger.exception("Shutdown step failed (community_world.stop): %s", e)

            try:
                self._webcam_frame.stop()
            except (OSError, RuntimeError, ValueError, TypeError) as e:
                logger.exception("Shutdown step failed (webcam_frame.stop): %s", e)

            try:
                self._signal_system.stop()
            except (OSError, RuntimeError, ValueError, TypeError) as e:
                logger.exception("Shutdown step failed (signal_system.stop): %s", e)

            try:
                self._queue_timer.stop()
            except RuntimeError:
                logger.debug("Shutdown: queue timer already stopped")

            try:
                self._uninstall_log_handler()
            except RuntimeError:
                logger.debug("Shutdown: log handler already uninstalled")

            if self._telegram is not None:
                try:
                    self._telegram.stop()
                except (OSError, RuntimeError, ValueError, TypeError) as e:
                    logger.exception("Shutdown step failed (telegram.stop): %s", e)
                self._telegram = None

            mp = self._music_player
            self._music_player = None
            if mp is not None:
                try:
                    await mp.stop()
                except (OSError, RuntimeError, ValueError, TypeError) as e:
                    logger.exception("Shutdown step failed (music_player.stop): %s", e)

            for name, coro in (
                ("twitch.stop", self._twitch.stop()),
                ("youtube.stop", self._youtube.stop()),
                ("tiktok.stop", self._tiktok.stop()),
                ("coordinator.stop_workers", self._coordinator.stop_workers()),
                ("tts.aclose", self._tts.aclose()),
            ):
                try:
                    await coro
                except (OSError, RuntimeError, ValueError, TypeError) as e:
                    logger.exception("Shutdown step failed (%s): %s", name, e)
                except asyncio.CancelledError:
                    raise

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
