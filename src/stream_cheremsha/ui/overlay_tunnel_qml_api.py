"""QML bridge for overlay public URL tunnel settings (ngrok / Cloudflare)."""

from __future__ import annotations

import asyncio
import logging
import typing
import weakref

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox

from stream_cheremsha.config import constants, embedded, keyring_store
from stream_cheremsha.config.tunnel_secrets import (
    cloudflare_tunnel_token_configured,
)
from stream_cheremsha.overlays.tunnel_types import TunnelProvider

if typing.TYPE_CHECKING:
    from stream_cheremsha.ui.main_window import MainWindow

logger = logging.getLogger(__name__)


class OverlayTunnelQmlApi(QObject):
    tunnelEnabledChanged = Signal()
    tunnelStatusTextChanged = Signal()
    tunnelProviderChanged = Signal()
    tunnelCustomUrlChanged = Signal()
    ngrokTokenChanged = Signal()
    ngrokTokenConfiguredChanged = Signal()
    ngrokDomainChanged = Signal()
    cloudflareHostnameChanged = Signal()
    cloudflareTokenChanged = Signal()
    cloudflareTokenConfiguredChanged = Signal()
    localBaseUrlChanged = Signal()

    def __init__(self, main: MainWindow) -> None:
        super().__init__(parent=main)
        self._m: weakref.ref[MainWindow] = weakref.ref(main)
        self._tunnel_enabled = False
        self._tunnel_status_text = ""
        self._tunnel_provider = TunnelProvider.NGROK.value
        self._tunnel_custom_url = ""
        self._ngrok_token = ""
        self._ngrok_domain = ""
        self._cloudflare_hostname = ""
        self._cloudflare_token = ""
        self._local_base_url = ""
        self._load_from_settings()

    def _main(self) -> MainWindow | None:
        return self._m()

    def _locale(self) -> str:
        w = self._main()
        if w is None:
            return "uk"
        return w._get_locale()  # noqa: SLF001

    def _load_from_settings(self) -> None:
        w = self._main()
        if w is None:
            return
        s = w._settings  # noqa: SLF001
        self._tunnel_enabled = bool(s.value(constants.SETTINGS_OVERLAY_TUNNEL_ENABLED, False, bool))
        self._tunnel_provider = TunnelProvider.CLOUDFLARE.value
        self._tunnel_custom_url = str(
            s.value(constants.SETTINGS_OVERLAY_TUNNEL_CUSTOM_URL, "", str) or ""
        )
        self._ngrok_domain = str(s.value(constants.SETTINGS_OVERLAY_NGROK_DOMAIN, "", str) or "")
        self._cloudflare_hostname = str(
            s.value(constants.SETTINGS_OVERLAY_CLOUDFLARE_HOSTNAME, "", str) or ""
        )
        self._ngrok_token = ""
        self._cloudflare_token = ""
        self._refresh_status_text()

    def refresh_from_tunnel(self, *, local_base_url: str = "") -> None:
        if local_base_url:
            if local_base_url != self._local_base_url:
                self._local_base_url = local_base_url.rstrip("/")
                self.localBaseUrlChanged.emit()
        self._refresh_status_text()

    def _refresh_status_text(self) -> None:
        w = self._main()
        if w is None:
            return
        st = w._overlay_tunnel.state()  # noqa: SLF001
        uk = self._locale() != "en"
        if not self._tunnel_enabled:
            text = "Локальний URL (localhost)" if uk else "Local URL (localhost)"
        elif self._tunnel_enabled:
            text = f"https://{embedded.OVERLAY_PUBLIC_HOSTNAME}:17171"
        elif st.status == "error":
            text = st.message or ("Помилка тунелю" if uk else "Tunnel error")
        else:
            text = "Локальний URL (localhost)" if uk else "Local URL (localhost)"
        if text != self._tunnel_status_text:
            self._tunnel_status_text = text
            self.tunnelStatusTextChanged.emit()

    @Property(bool, notify=tunnelEnabledChanged)
    def tunnelEnabled(self) -> bool:  # noqa: ANN201 - PySide pattern
        return self._tunnel_enabled

    @Property(str, notify=tunnelStatusTextChanged)
    def tunnelStatusText(self) -> str:  # noqa: ANN201 - PySide pattern
        return self._tunnel_status_text

    @Property(str, notify=tunnelProviderChanged)
    def tunnelProvider(self) -> str:  # noqa: ANN201 - PySide pattern
        return self._tunnel_provider

    @Property(str, notify=localBaseUrlChanged)
    def localBaseUrl(self) -> str:  # noqa: ANN201 - PySide pattern
        return self._local_base_url

    @Property(str, notify=tunnelCustomUrlChanged)
    def tunnelCustomUrl(self) -> str:  # noqa: ANN201 - PySide pattern
        return self._tunnel_custom_url

    @Property(str, notify=ngrokDomainChanged)
    def ngrokDomain(self) -> str:  # noqa: ANN201 - PySide pattern
        return self._ngrok_domain

    @Property(str, notify=cloudflareHostnameChanged)
    def cloudflareHostname(self) -> str:  # noqa: ANN201 - PySide pattern
        return self._cloudflare_hostname

    @Property(str, notify=ngrokTokenConfiguredChanged)
    def ngrokTokenPlaceholder(self) -> str:  # noqa: ANN201 - PySide pattern
        uk = self._locale() != "en"
        if self.ngrokTokenConfigured:
            return (
                "authtoken збережено — введіть новий для заміни"
                if uk
                else "authtoken saved — enter a new one to replace"
            )
        return "ngrok authtoken"

    @Property(str, notify=ngrokTokenChanged)
    def ngrokToken(self) -> str:  # noqa: ANN201 - PySide pattern
        return ""

    @Property(bool, notify=ngrokTokenConfiguredChanged)
    def ngrokTokenConfigured(self) -> bool:  # noqa: ANN201 - PySide pattern
        return bool((keyring_store.get_password(constants.KEY_NGROK_AUTHTOKEN) or "").strip())

    @Property(str, notify=cloudflareTokenConfiguredChanged)
    def cloudflareTokenPlaceholder(self) -> str:  # noqa: ANN201 - PySide pattern
        uk = self._locale() != "en"
        if self.cloudflareTokenConfigured:
            return (
                "tunnel token збережено — введіть новий для заміни"
                if uk
                else "tunnel token saved — enter a new one to replace"
            )
        return "Cloudflare tunnel token"

    @Property(str, notify=cloudflareTokenChanged)
    def cloudflareToken(self) -> str:  # noqa: ANN201 - PySide pattern
        return ""

    @Property(bool, notify=cloudflareTokenConfiguredChanged)
    def cloudflareTokenConfigured(self) -> bool:  # noqa: ANN201 - PySide pattern
        return cloudflare_tunnel_token_configured()

    @Property(str, constant=True)
    def tunnelEnabledLabel(self) -> str:  # noqa: ANN201 - PySide pattern
        uk = self._locale() != "en"
        return "Публічний URL" if uk else "Public URL"

    @Property(str, notify=tunnelProviderChanged)
    def tunnelHelpText(self) -> str:  # noqa: ANN201 - PySide pattern
        uk = self._locale() != "en"
        if uk:
            return f"Віджети будуть доступні через https://{embedded.OVERLAY_PUBLIC_HOSTNAME}:17171/…"
        return f"Widgets will be available at https://{embedded.OVERLAY_PUBLIC_HOSTNAME}:17171/…"

    @Property(str, constant=True)
    def ngrokDomainPlaceholder(self) -> str:  # noqa: ANN201 - PySide pattern
        return "abc123.ngrok-free.dev (dashboard.ngrok.com/domains)"

    @Property(str, constant=True)
    def cloudflareHostnamePlaceholder(self) -> str:  # noqa: ANN201 - PySide pattern
        return "widgets.example.com"

    @Slot(bool)
    def setTunnelEnabled(self, enabled: bool) -> None:
        if enabled == self._tunnel_enabled:
            return
        self._tunnel_enabled = bool(enabled)
        w = self._main()
        if w is not None:
            w._settings.setValue(constants.SETTINGS_OVERLAY_TUNNEL_ENABLED, self._tunnel_enabled)  # noqa: SLF001
        self.tunnelEnabledChanged.emit()
        self._schedule_apply(prompt_install=True)

    @Slot(str)
    def setTunnelProvider(self, provider: str) -> None:
        value = str(provider or "").strip()
        if value not in {
            TunnelProvider.NGROK.value,
            TunnelProvider.CLOUDFLARE.value,
            TunnelProvider.CUSTOM.value,
        }:
            value = TunnelProvider.NGROK.value
        if value == self._tunnel_provider:
            return
        self._tunnel_provider = value
        w = self._main()
        if w is not None:
            w._settings.setValue(constants.SETTINGS_OVERLAY_TUNNEL_PROVIDER, value)  # noqa: SLF001
        self.tunnelProviderChanged.emit()
        if self._tunnel_enabled:
            self._schedule_apply(prompt_install=True)

    @Slot(str)
    def setTunnelCustomUrl(self, url: str) -> None:
        value = str(url or "").strip()
        if value == self._tunnel_custom_url:
            return
        self._tunnel_custom_url = value
        w = self._main()
        if w is not None:
            w._settings.setValue(constants.SETTINGS_OVERLAY_TUNNEL_CUSTOM_URL, value)  # noqa: SLF001
        self.tunnelCustomUrlChanged.emit()
        if self._tunnel_enabled:
            self._schedule_apply()

    def sync_ngrok_domain(self, domain: str) -> None:
        value = str(domain or "").strip()
        if value == self._ngrok_domain:
            return
        self._ngrok_domain = value
        self.ngrokDomainChanged.emit()

    @Slot(str)
    def setNgrokDomain(self, domain: str) -> None:
        value = str(domain or "").strip()
        if value == self._ngrok_domain:
            return
        self._ngrok_domain = value
        w = self._main()
        if w is not None:
            w._settings.setValue(constants.SETTINGS_OVERLAY_NGROK_DOMAIN, value)  # noqa: SLF001
        self.ngrokDomainChanged.emit()
        if self._tunnel_enabled and self._tunnel_provider == TunnelProvider.NGROK.value:
            self._schedule_apply()

    @Slot(str)
    def setNgrokToken(self, token: str) -> None:
        value = str(token or "")
        if value == self._ngrok_token:
            return
        self._ngrok_token = value
        self.ngrokTokenChanged.emit()

    @Slot()
    def saveNgrokToken(self) -> None:
        token = self._ngrok_token.strip()
        if not token:
            return
        try:
            keyring_store.set_password(constants.KEY_NGROK_AUTHTOKEN, token)
        except RuntimeError as e:
            w = self._main()
            if w is not None:
                QMessageBox.warning(w, w._tr("dlg.keyring"), str(e))  # noqa: SLF001
            return
        self._ngrok_token = ""
        self.ngrokTokenChanged.emit()
        self.ngrokTokenConfiguredChanged.emit()
        if self._tunnel_enabled and self._tunnel_provider == TunnelProvider.NGROK.value:
            self._schedule_apply(prompt_install=True)

    @Slot(str)
    def setCloudflareHostname(self, hostname: str) -> None:
        value = str(hostname or "").strip()
        if value == self._cloudflare_hostname:
            return
        self._cloudflare_hostname = value
        w = self._main()
        if w is not None:
            w._settings.setValue(constants.SETTINGS_OVERLAY_CLOUDFLARE_HOSTNAME, value)  # noqa: SLF001
        self.cloudflareHostnameChanged.emit()
        if self._tunnel_enabled and self._tunnel_provider == TunnelProvider.CLOUDFLARE.value:
            self._schedule_apply()

    @Slot(str)
    def setCloudflareToken(self, token: str) -> None:
        value = str(token or "")
        if value == self._cloudflare_token:
            return
        self._cloudflare_token = value
        self.cloudflareTokenChanged.emit()

    @Slot()
    def saveCloudflareToken(self) -> None:
        token = self._cloudflare_token.strip()
        if not token:
            return
        try:
            keyring_store.set_password(constants.KEY_CLOUDFLARE_TUNNEL_TOKEN, token)
        except RuntimeError as e:
            w = self._main()
            if w is not None:
                QMessageBox.warning(w, w._tr("dlg.keyring"), str(e))  # noqa: SLF001
            return
        self._cloudflare_token = ""
        self.cloudflareTokenChanged.emit()
        self.cloudflareTokenConfiguredChanged.emit()
        if self._tunnel_enabled and self._tunnel_provider == TunnelProvider.CLOUDFLARE.value:
            self._schedule_apply(prompt_install=True)

    @Slot()
    def openNgrokDomainsPage(self) -> None:
        QDesktopServices.openUrl("https://dashboard.ngrok.com/domains")

    @Slot()
    def openCloudflareTunnelsPage(self) -> None:
        QDesktopServices.openUrl("https://one.dash.cloudflare.com/?to=/:account/networks/tunnels")

    @Slot()
    def applyTunnelSettings(self) -> None:
        self._schedule_apply(prompt_install=True)

    def set_tunnel_status_message(self, message: str) -> None:
        text = str(message or "")
        if text == self._tunnel_status_text:
            return
        self._tunnel_status_text = text
        self.tunnelStatusTextChanged.emit()

    def _schedule_apply(self, *, prompt_install: bool = False) -> None:
        w = self._main()
        if w is None:
            return
        loop = w._asyncio_loop  # noqa: SLF001
        if loop is None:
            return
        asyncio.run_coroutine_threadsafe(
            w.apply_overlay_tunnel(prompt_install=prompt_install),
            loop,
        )

    def resolved_tunnel_provider(self) -> str:
        return self._tunnel_provider
