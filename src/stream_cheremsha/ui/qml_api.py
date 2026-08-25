"""QML context object: exposes MainWindow state and actions to Qt Quick (connections UI)."""

from __future__ import annotations

import typing
import weakref

from PySide6.QtCore import Property, QEvent, QObject, QPoint, QRect, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from stream_cheremsha.config import constants, keyring_store
from stream_cheremsha.domain.models import ChatPlatform

if typing.TYPE_CHECKING:
    from stream_cheremsha.ui.main_window import MainWindow


class StreamCheremshaQmlApi(QObject):
    """Bridges the QML «Connections» view to :class:`MainWindow` (hidden QWidgets + slots)."""

    refreshCounterChanged = Signal()
    bigPictureActiveChanged = Signal()

    def __init__(self, main: MainWindow) -> None:
        super().__init__(parent=main)
        self._m: weakref.ref[MainWindow] = weakref.ref(main)
        self._rc: int = 0
        self._footer_obj: QObject | None = None
        self._qml_conn_obj: QObject | None = None
        self._win_obj: QObject | None = main

        try:
            foot = main._footer_frame  # noqa: SLF001
        except AttributeError:
            foot = None
        if foot is not None:
            self._footer_obj = foot
            foot.installEventFilter(self)

        try:
            qml = main._qml_conn  # noqa: SLF001
        except AttributeError:
            qml = None
        if qml is not None:
            self._qml_conn_obj = qml
            qml.installEventFilter(self)

        main.installEventFilter(self)

    def _win(self) -> MainWindow | None:
        return self._m()

    @Property(int, notify=refreshCounterChanged)
    def refreshCounter(self) -> int:  # noqa: ANN201 - PySide pattern
        return self._rc

    @Property(int, notify=refreshCounterChanged)
    def bottomInsetPx(self) -> int:  # noqa: ANN201 - PySide pattern
        """Bottom inset for QML ScrollViews to avoid overlapping the QWidget footer."""
        w = self._win()
        if w is None:
            return 0
        try:
            foot = w._footer_frame  # noqa: SLF001
        except AttributeError:
            return 0
        try:
            h = int(foot.height())
        except RuntimeError:
            return 0
        return max(0, h)

    @Property(int, notify=refreshCounterChanged)
    def footerOverlapPx(self) -> int:  # noqa: ANN201 - PySide pattern
        """Pixels by which the QWidget footer overlaps the QML connections view.

        If layouts are correct, this is 0. If the footer is drawn on top of QML,
        this reports the real overlap in screen coordinates.
        """
        w = self._win()
        if w is None:
            return 0
        try:
            qml = w._qml_conn  # noqa: SLF001
            foot = w._footer_frame  # noqa: SLF001
        except AttributeError:
            return 0
        try:
            if not qml.isVisible() or not foot.isVisible():
                return 0
            qml_tl = qml.mapToGlobal(QPoint(0, 0))
            qml_br = qml.mapToGlobal(QPoint(qml.width(), qml.height()))
            foot_tl = foot.mapToGlobal(QPoint(0, 0))
            foot_br = foot.mapToGlobal(QPoint(foot.width(), foot.height()))
        except RuntimeError:
            return 0
        qml_r = QRect(qml_tl, qml_br)
        foot_r = QRect(foot_tl, foot_br)
        inter = qml_r.intersected(foot_r)
        if inter.isNull() or inter.height() <= 0:
            return 0
        return int(inter.height())

    @Property(int, notify=refreshCounterChanged)
    def footerHeightPx(self) -> int:  # noqa: ANN201 - PySide pattern
        w = self._win()
        if w is None:
            return 0
        if getattr(w, "_big_picture_active", False):
            return 0
        try:
            foot = w._footer_frame  # noqa: SLF001
        except AttributeError:
            return 0
        try:
            return int(foot.height())
        except RuntimeError:
            return 0

    @Property(bool, notify=bigPictureActiveChanged)
    def bigPictureActive(self) -> bool:  # noqa: ANN201 - PySide pattern
        w = self._win()
        if w is None:
            return False
        return bool(getattr(w, "_big_picture_active", False))

    @Slot()
    def exitBigPicture(self) -> None:
        w = self._win()
        if w is None:
            return
        w._exit_big_picture()  # noqa: SLF001

    def notify_big_picture_active_changed(self) -> None:
        self.bigPictureActiveChanged.emit()
        self.refresh()

    @Property(int, notify=refreshCounterChanged)
    def qmlConnHeightPx(self) -> int:  # noqa: ANN201 - PySide pattern
        w = self._win()
        if w is None:
            return 0
        try:
            qml = w._qml_conn  # noqa: SLF001
        except AttributeError:
            return 0
        try:
            return int(qml.height())
        except RuntimeError:
            return 0

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802 - Qt naming
        et = event.type()
        if watched in (self._footer_obj, self._qml_conn_obj, self._win_obj):
            if et in (
                QEvent.Type.Resize,
                QEvent.Type.Move,
                QEvent.Type.Show,
                QEvent.Type.Hide,
                QEvent.Type.LayoutRequest,
            ):
                self.refresh()
        return super().eventFilter(watched, event)

    @Slot()
    def refresh(self) -> None:
        self._rc += 1
        self.refreshCounterChanged.emit()

    @Slot(str, result=str)
    def loc(self, key: str) -> str:
        w = self._win()
        if w is None:
            return key
        return w._tr(key)  # noqa: SLF001

    @Slot(result=str)
    def twitchAppsHelpHtml(self) -> str:
        w = self._win()
        if w is None:
            return ""
        u = "https://dev.twitch.tv/console/apps"
        return w._tr("tw.apps_help", url=u)  # noqa: SLF001

    @Slot(result=str)
    def youtubeOauthHelpHtml(self) -> str:
        w = self._win()
        if w is None:
            return ""
        return w._tr(  # noqa: SLF001
            "yt.oauth_help",
            creds_url="https://console.cloud.google.com/apis/credentials",
            api_url="https://console.cloud.google.com/apis/library/youtube.googleapis.com",
        )

    @Slot(result=str)
    def youtubeStudioLinkHtml(self) -> str:
        w = self._win()
        if w is None:
            return ""
        return w._tr("yt.studio_link")  # noqa: SLF001

    @Slot(result=str)
    def twitchUrlApps(self) -> str:
        return "https://dev.twitch.tv/console/apps"

    @Slot(result=str)
    def googleCredsUrl(self) -> str:
        return "https://console.cloud.google.com/apis/credentials"

    @Slot(result=str)
    def youtubeApiUrl(self) -> str:
        return "https://console.cloud.google.com/apis/library/youtube.googleapis.com"

    @Slot(result=str)
    def youtubeStudioUrl(self) -> str:
        return "https://studio.youtube.com"

    @Slot(str)
    def openUrl(self, url: str) -> None:
        u = (url or "").strip()
        if u.startswith("http://") or u.startswith("https://"):
            QDesktopServices.openUrl(QUrl(u))

    @Slot()
    def twitchBrowserLogin(self) -> None:
        w = self._win()
        if w is not None:
            w._schedule_twitch_browser_login()  # noqa: SLF001

    @Slot()
    def twitchSaveAppKeys(self) -> None:
        w = self._win()
        if w is not None:
            w._save_twitch_keys()  # noqa: SLF001

    @Slot()
    def twitchTransport(self) -> None:
        w = self._win()
        if w is not None:
            w._on_twitch_transport_clicked()  # noqa: SLF001

    @Slot()
    def twitchLogout(self) -> None:
        w = self._win()
        if w is not None:
            w._logout_twitch()  # noqa: SLF001

    @Slot()
    def youtubeOauth(self) -> None:
        w = self._win()
        if w is not None:
            w._yt_oauth_from_qml()  # noqa: SLF001

    @Slot()
    def youtubeForgetClient(self) -> None:
        w = self._win()
        if w is not None:
            w._forget_youtube_client_config()  # noqa: SLF001

    @Slot()
    def youtubeTransport(self) -> None:
        w = self._win()
        if w is not None:
            w._on_youtube_transport_clicked()  # noqa: SLF001

    @Slot()
    def youtubeLogout(self) -> None:
        w = self._win()
        if w is not None:
            w._logout_youtube()  # noqa: SLF001

    @Slot(result=bool)
    def twitchKeyringSession(self) -> bool:
        from stream_cheremsha.chat import twitch_credentials

        return bool(twitch_credentials.twitch_keyring_has_session())

    @Slot(result=bool)
    def googleLinked(self) -> bool:
        from stream_cheremsha.chat.youtube_source import is_google_account_linked

        return bool(is_google_account_linked())

    @Slot(result=str)
    def twitchClientIdEnvName(self) -> str:
        return constants.ENV_TWITCH_CLIENT_ID

    @Slot(result=bool)
    def twitchClientConfigured(self) -> bool:
        """True if Twitch Client ID is available (ENV/keyring/UI resolved)."""
        w = self._win()
        if w is None:
            return False
        return bool(w._twitch_client_id_resolved().strip())  # noqa: SLF001

    @Slot(result=bool)
    def twitchRunning(self) -> bool:
        w = self._win()
        return w._twitch.running if w is not None else False  # noqa: SLF001

    @Slot(result=bool)
    def youtubeRunning(self) -> bool:
        w = self._win()
        return w._youtube.running if w is not None else False  # noqa: SLF001

    @Slot(result=bool)
    def twitchChatTtsEnabled(self) -> bool:
        w = self._win()
        return bool(w._chat_tts_enabled(ChatPlatform.TWITCH)) if w is not None else True  # noqa: SLF001

    @Slot(bool)
    def twitchSetChatTtsEnabled(self, enabled: bool) -> None:
        w = self._win()
        if w is not None:
            w._set_chat_tts_enabled(ChatPlatform.TWITCH, bool(enabled))  # noqa: SLF001
        self.refresh()

    @Slot(result=bool)
    def youtubeChatTtsEnabled(self) -> bool:
        w = self._win()
        return bool(w._chat_tts_enabled(ChatPlatform.YOUTUBE)) if w is not None else True  # noqa: SLF001

    @Slot(bool)
    def youtubeSetChatTtsEnabled(self, enabled: bool) -> None:
        w = self._win()
        if w is not None:
            w._set_chat_tts_enabled(ChatPlatform.YOUTUBE, bool(enabled))  # noqa: SLF001
        self.refresh()

    @Slot(result=bool)
    def tiktokChatTtsEnabled(self) -> bool:
        w = self._win()
        return bool(w._chat_tts_enabled(ChatPlatform.TIKTOK)) if w is not None else True  # noqa: SLF001

    @Slot(bool)
    def tiktokSetChatTtsEnabled(self, enabled: bool) -> None:
        w = self._win()
        if w is not None:
            w._set_chat_tts_enabled(ChatPlatform.TIKTOK, bool(enabled))  # noqa: SLF001
        self.refresh()

    @Slot(result=bool)
    def tiktokRunning(self) -> bool:
        w = self._win()
        return bool(w._tiktok_enabled) if w is not None else False  # noqa: SLF001

    @Slot(result=bool)
    def tiktokEnabled(self) -> bool:
        w = self._win()
        return bool(w._tiktok_enabled) if w is not None else False  # noqa: SLF001

    @Slot(result=str)
    def twitchChannelGet(self) -> str:
        w = self._win()
        if w is None:
            return ""
        return w._twitch_channel.text()  # noqa: SLF001

    @Slot(result=str)
    def twitchClientIdGet(self) -> str:
        w = self._win()
        if w is None:
            return ""
        return w._twitch_client_id_resolved()  # noqa: SLF001

    @Slot(result=str)
    def twitchSecretGet(self) -> str:
        w = self._win()
        if w is None:
            return ""
        return w._twitch_client_secret.text()  # noqa: SLF001

    @Slot(result=str)
    def twitchTokenGet(self) -> str:
        w = self._win()
        if w is None:
            return ""
        return w._twitch_token.text()  # noqa: SLF001

    @Slot(result=str)
    def youtubeVideoGet(self) -> str:
        w = self._win()
        if w is None:
            return ""
        return w._yt_video.text()  # noqa: SLF001

    @Slot(result=str)
    def tiktokUsernameGet(self) -> str:
        w = self._win()
        if w is None:
            return ""
        return w._tiktok_username.text()  # noqa: SLF001

    @Slot(result=str)
    def twitchConnectedTextGet(self) -> str:
        w = self._win()
        if w is None:
            return ""
        return w._twitch_logged_in_label.text()  # noqa: SLF001

    @Slot(result=str)
    def youtubeConnectedTextGet(self) -> str:
        w = self._win()
        if w is None:
            return ""
        return w._yt_logged_in_label.text()  # noqa: SLF001

    @Slot(result=str)
    def tiktokConnectedTextGet(self) -> str:
        w = self._win()
        if w is None:
            return ""
        return w._status_tiktok  # noqa: SLF001

    @Slot(result=str)
    def twitchTransportLabelGet(self) -> str:
        w = self._win()
        if w is None:
            return ""
        tw_btn = "tw.transport_stop" if w._twitch.running else "tw.transport_start"  # noqa: SLF001
        return w._tr(tw_btn)  # noqa: SLF001

    @Slot(result=str)
    def youtubeTransportLabelGet(self) -> str:
        w = self._win()
        if w is None:
            return ""
        yt_btn = "yt.transport_stop" if w._youtube.running else "yt.transport_start"  # noqa: SLF001
        return w._tr(yt_btn)  # noqa: SLF001

    @Slot()
    def tiktokTransport(self) -> None:
        w = self._win()
        if w is not None:
            w._on_tiktok_transport_clicked()  # noqa: SLF001

    @Slot(bool)
    def tiktokSetEnabled(self, enabled: bool) -> None:
        w = self._win()
        if w is not None:
            w._request_tiktok_enabled(bool(enabled))  # noqa: SLF001

    @Slot(str)
    def setTwitchChannelText(self, v: str) -> None:
        w = self._win()
        if w is not None:
            w._twitch_channel.setText(v)  # noqa: SLF001

    @Slot(str)
    def twitchChannelCommit(self, v: str) -> None:
        """Persist channel to keyring (called on editing finished)."""
        w = self._win()
        if w is None:
            return
        vv = (v or "").strip()
        w._twitch_channel.setText(vv)  # noqa: SLF001
        if vv:
            keyring_store.set_password(constants.KEY_TWITCH_CHANNEL, vv)
        else:
            keyring_store.delete_password(constants.KEY_TWITCH_CHANNEL)

    @Slot(str)
    def setTwitchClientIdText(self, v: str) -> None:
        w = self._win()
        if w is not None:
            w._twitch_client_id.setText(v)  # noqa: SLF001

    @Slot(str)
    def setTwitchSecretText(self, v: str) -> None:
        w = self._win()
        if w is not None:
            w._twitch_client_secret.setText(v)  # noqa: SLF001

    @Slot(str)
    def setTwitchTokenText(self, v: str) -> None:
        w = self._win()
        if w is not None:
            w._twitch_token.setText(v)  # noqa: SLF001

    @Slot(str)
    def setYoutubeVideoText(self, v: str) -> None:
        w = self._win()
        if w is not None:
            w._yt_video.setText(v)  # noqa: SLF001

    @Slot(str)
    def setTiktokUsernameText(self, v: str) -> None:
        w = self._win()
        if w is not None:
            w._tiktok_username.setText(v)  # noqa: SLF001

    @Slot(str)
    def tiktokUsernameCommit(self, v: str) -> None:
        w = self._win()
        if w is None:
            return
        vv = (v or "").strip()
        w._tiktok_username.setText(vv)  # noqa: SLF001
        if vv:
            keyring_store.set_password(constants.KEY_TIKTOK_USERNAME, vv)
        else:
            keyring_store.delete_password(constants.KEY_TIKTOK_USERNAME)

    @Slot()
    def openTikTokActions(self) -> None:
        w = self._win()
        if w is not None:
            w.open_actions()  # noqa: SLF001

    # -------- Kick --------
    @Slot()
    def kickBrowserLogin(self) -> None:
        w = self._win()
        if w is not None:
            w._schedule_kick_browser_login()  # noqa: SLF001

    @Slot()
    def kickLogout(self) -> None:
        w = self._win()
        if w is not None:
            w._logout_kick()  # noqa: SLF001

    @Slot()
    def kickTransport(self) -> None:
        w = self._win()
        if w is not None:
            w._on_kick_transport_clicked()  # noqa: SLF001

    @Slot(bool)
    def kickSetEnabled(self, enabled: bool) -> None:
        w = self._win()
        if w is not None:
            w._request_kick_enabled(bool(enabled))  # noqa: SLF001

    @Slot(result=bool)
    def kickKeyringSession(self) -> bool:
        from stream_cheremsha.chat import kick_credentials

        return bool(kick_credentials.has_session())

    @Slot(result=bool)
    def kickClientConfigured(self) -> bool:
        from stream_cheremsha.chat.kick_api import KickOAuthConfig

        return KickOAuthConfig.from_env() is not None

    @Slot(result=str)
    def kickClientIdEnvName(self) -> str:
        from stream_cheremsha.chat.kick_api import ENV_KICK_CLIENT_ID

        return ENV_KICK_CLIENT_ID

    @Slot(result=str)
    def kickRedirectUri(self) -> str:
        from stream_cheremsha.chat.kick_api import KickOAuthConfig

        cfg = KickOAuthConfig.from_env()
        return cfg.redirect_uri if cfg is not None else ""

    @Slot(result=bool)
    def kickRunning(self) -> bool:
        w = self._win()
        return w._kick.running if w is not None else False  # noqa: SLF001

    @Slot(result=bool)
    def kickEnabled(self) -> bool:
        w = self._win()
        return bool(getattr(w, "_kick_enabled", False)) if w is not None else False  # noqa: SLF001

    @Slot(result=bool)
    def kickChatTtsEnabled(self) -> bool:
        w = self._win()
        return bool(w._chat_tts_enabled(ChatPlatform.KICK)) if w is not None else True  # noqa: SLF001

    @Slot(bool)
    def kickSetChatTtsEnabled(self, enabled: bool) -> None:
        w = self._win()
        if w is not None:
            w._set_chat_tts_enabled(ChatPlatform.KICK, bool(enabled))  # noqa: SLF001
        self.refresh()

    @Slot(result=str)
    def kickChannelGet(self) -> str:
        w = self._win()
        if w is None:
            return ""
        return w._kick_channel.text()  # noqa: SLF001

    @Slot(str)
    def setKickChannelText(self, v: str) -> None:
        w = self._win()
        if w is not None:
            w._kick_channel.setText(v)  # noqa: SLF001

    @Slot(str)
    def kickChannelCommit(self, v: str) -> None:
        w = self._win()
        if w is None:
            return
        from stream_cheremsha.chat import kick_credentials

        vv = (v or "").strip().lstrip("@").strip()
        w._kick_channel.setText(vv)  # noqa: SLF001
        kick_credentials.set_authorized_channel(vv)

    @Slot(result=str)
    def kickConnectedTextGet(self) -> str:
        w = self._win()
        if w is None:
            return ""
        return w._status_kick  # noqa: SLF001

    @Slot(result=str)
    def kickTransportLabelGet(self) -> str:
        w = self._win()
        if w is None:
            return ""
        btn = "kick.transport_stop" if w._kick.running else "kick.transport_start"  # noqa: SLF001
        return w._tr(btn)  # noqa: SLF001

    @Slot()
    def openKickActions(self) -> None:
        w = self._win()
        if w is not None:
            w.open_actions()  # noqa: SLF001

    @Slot()
    def openWidgets(self) -> None:
        w = self._win()
        if w is not None:
            w.open_widgets()

    @Slot()
    def goHome(self) -> None:
        w = self._win()
        if w is not None:
            w._set_main_page(w._IX_CONN)  # noqa: SLF001
