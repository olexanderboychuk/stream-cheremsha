"""QML context object: exposes MainWindow state and actions to Qt Quick (connections UI)."""

from __future__ import annotations

import typing
import weakref

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from stream_cheremsha.config import constants
from stream_cheremsha.config import keyring_store

if typing.TYPE_CHECKING:
    from stream_cheremsha.ui.main_window import MainWindow


class StreamCheremshaQmlApi(QObject):
    """Bridges the QML «Connections» view to :class:`MainWindow` (hidden QWidgets + slots)."""

    refreshCounterChanged = Signal()

    def __init__(self, main: MainWindow) -> None:
        super().__init__(parent=main)
        self._m: weakref.ref[MainWindow] = weakref.ref(main)
        self._rc: int = 0

    def _win(self) -> MainWindow | None:
        return self._m()

    @Property(int, notify=refreshCounterChanged)
    def refreshCounter(self) -> int:  # noqa: ANN201 - PySide pattern
        return self._rc

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
