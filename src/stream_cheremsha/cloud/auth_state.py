"""Single application-level Cheremsha account/auth state (desktop side).

Owns the whole login/session lifecycle and is the ONLY source of account
truth for the UI (title-bar pill, popover, QML ``cheremshaAuth`` property).
No other component keeps its own copy of the Cheremsha session.

Only Cheremsha credentials are ever handled here (access/refresh tokens stay
in memory + OS keyring, never exposed to QML, never logged). Provider OAuth
tokens/secrets never exist on this side by design.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from stream_cheremsha.chat.kick_api import generate_pkce
from stream_cheremsha.cloud import constants
from stream_cheremsha.cloud.callback import DesktopCallbackServer
from stream_cheremsha.cloud.client import (
    CheremshaCloudClient,
    CloudApiError,
    CloudAutoConnectOutcome,
    CloudPlatformStatus,
    CloudUser,
)
from stream_cheremsha.cloud.session_store import (
    CheremshaSession,
    clear_session,
    load_session,
    save_session,
)

logger = logging.getLogger(__name__)

STATUS_LOGGED_OUT = "logged-out"
STATUS_RESTORING = "restoring"
STATUS_STARTING = "starting"
STATUS_AWAITING_CALLBACK = "awaiting-callback"
STATUS_AUTHENTICATED = "authenticated"

_CONNECT_LOGIN_MAP = {
    "twitch": "twitch",
    "tiktok": "tiktok",
    "kick": "kick",
    "youtube": "google",
}


class CheremshaAuthState(QObject):
    """QObject holding Cheremsha account state. All network work is async."""

    statusChanged = Signal(str)
    userChanged = Signal()
    platformsChanged = Signal()
    avatarChanged = Signal()
    identitiesChanged = Signal()
    # Non-modal failure notice: short reason code, never any secret.
    # Reasons: "unreachable" | "callback-busy" | "exchange-failed".
    # Cancel/timeout stay silent (user simply walked away).
    notice = Signal(str)

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        base_url: str | None = None,
        client: CheremshaCloudClient | None = None,
        open_url: Callable[[str], None] | None = None,
        on_auto_connected: Callable[[CloudAutoConnectOutcome], None] | None = None,
        on_auto_reauth_required: Callable[[CloudAutoConnectOutcome], None] | None = None,
    ) -> None:
        super().__init__(parent)
        # Resolve env > embedded > default when no explicit base_url is
        # given (MainWindow passes the QSettings-resolved value explicitly).
        self._base_url = (base_url or constants.api_base_url()).rstrip("/")
        self._client = client
        self._owns_client = client is None
        self._open_url = open_url or (lambda url: None)
        self._on_auto_connected = on_auto_connected or (lambda _o: None)
        self._on_auto_reauth_required = on_auto_reauth_required or (lambda _o: None)
        self._status = STATUS_LOGGED_OUT
        self._user: CloudUser | None = None
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._platforms: dict[str, CloudPlatformStatus] = {}
        self._avatar_bytes: bytes | None = None
        self._task: asyncio.Task[None] | None = None
        self._last_auto_connect: CloudAutoConnectOutcome | None = None
        self._auto_connected_platform: str | None = None
        self._identities: list[dict[str, Any]] = []
        self._pending_platform: str | None = None

    # -- Qt properties (user-visible state only; tokens are never exposed) --
    def _get_status(self) -> str:
        return self._status

    status = Property(str, _get_status, notify=statusChanged)

    def _get_authenticated(self) -> bool:
        return self._status == STATUS_AUTHENTICATED and self._user is not None

    isAuthenticated = Property(bool, _get_authenticated, notify=statusChanged)

    def _get_user_id(self) -> str:
        return self._user.id if self._user else ""

    userId = Property(str, _get_user_id, notify=userChanged)

    def _get_display_name(self) -> str:
        return self._user.display_name if self._user else ""

    displayName = Property(str, _get_display_name, notify=userChanged)

    def _get_email(self) -> str:
        return self._user.email if self._user else ""

    email = Property(str, _get_email, notify=userChanged)

    def _get_avatar_url(self) -> str:
        return self._user.avatar_url or "" if self._user else ""

    avatarUrl = Property(str, _get_avatar_url, notify=userChanged)

    def _get_platform_count(self) -> int:
        return sum(1 for p in self._platforms.values() if p.connected)

    connectedPlatformCount = Property(int, _get_platform_count, notify=platformsChanged)

    def _get_has_avatar(self) -> bool:
        return self._avatar_bytes is not None

    hasAvatar = Property(bool, _get_has_avatar, notify=avatarChanged)

    # -- internal helpers --------------------------------------------------
    def _set_status(self, status: str) -> None:
        if self._status != status:
            self._status = status
            self.statusChanged.emit(status)

    def _client_or_create(self) -> CheremshaCloudClient:
        if self._client is None:
            self._client = CheremshaCloudClient(self._base_url)
            self._owns_client = True
        return self._client

    def _busy(self) -> bool:
        return self._task is not None and not self._task.done()

    def _launch(self, coro_factory: Callable[[], Any], *, name: str) -> bool:
        """Start a lifecycle task unless one is already running (dup guard).

        Takes a factory (not a coroutine) so rejected duplicates never create
        un-awaited coroutine objects.
        """
        if self._busy():
            logger.debug("cheremsha auth busy, ignoring duplicate request")
            return False
        self._task = asyncio.create_task(coro_factory(), name=name)
        return True

    def _store_session(self, access: str, refresh: str, user: CloudUser) -> None:
        self._access_token = access
        self._refresh_token = refresh
        self._user = user
        self.userChanged.emit()
        save_session(
            CheremshaSession(
                access_token=access,
                refresh_token=refresh,
                user_id=user.id,
                email=user.email,
                display_name=user.display_name,
                avatar_url=user.avatar_url,
            )
        )

    def _clear_local(self) -> None:
        self._access_token = None
        self._refresh_token = None
        self._user = None
        self._platforms = {}
        self._avatar_bytes = None
        clear_session()
        self.userChanged.emit()
        self.platformsChanged.emit()
        self.avatarChanged.emit()

    # -- public slots ------------------------------------------------------
    @Slot(str)
    def login(self, provider: str) -> None:
        """Begin login with a provider (google/twitch/tiktok/kick). Non-blocking."""
        provider = (provider or "").strip().lower()
        if provider not in constants.LOGIN_PROVIDERS:
            return
        if self._status == STATUS_AUTHENTICATED:
            return
        self._launch(lambda: self._login_flow(provider), name="cheremsha-login")

    @Slot()
    def logout(self) -> None:
        """Best-effort cloud logout + local wipe. Non-blocking."""
        if self._task is not None and not self._task.done():
            # Abandon an in-flight login/restore first; the flows are idempotent
            # and converge on logged-out, as does the logout flow below.
            self._task.cancel()
            self._task = None
        self._launch(self._logout_flow, name="cheremsha-logout")

    @Slot()
    def cancelLogin(self) -> None:
        self._pending_platform = None
        if self._task is not None and not self._task.done():
            self._task.cancel()

    @Slot()
    def refreshPlatforms(self) -> None:
        if self._status != STATUS_AUTHENTICATED or not self._access_token:
            return
        self._launch(self._platforms_flow, name="cheremsha-platforms")

    @Slot()
    def openDashboard(self) -> None:
        self._open_url(constants.dashboard_url())

    @Slot(str)
    def linkProvider(self, provider: str) -> None:
        """Begin linking another login provider (authenticated only)."""
        provider = (provider or "").strip().lower()
        if provider not in constants.LOGIN_PROVIDERS:
            return
        if self._status != STATUS_AUTHENTICATED or not self._access_token:
            return
        self._launch(lambda: self._link_flow(provider), name="cheremsha-link")

    @Slot(str)
    def connectPlatform(self, platform: str) -> None:
        """Cloud-first platform connect. Logged out → login with the mapped
        provider (auto-connect finishes the job); logged in → explicit
        platform-connect round-trip."""
        platform = (platform or "").strip().lower()
        if platform not in ("twitch", "tiktok", "kick", "youtube"):
            return
        if self._status != STATUS_AUTHENTICATED or not self._access_token:
            self._pending_platform = platform
            self.login(_CONNECT_LOGIN_MAP[platform])
            return
        self._launch(
            lambda: self._platform_connect_flow(platform), name="cheremsha-connect"
        )

    @Slot(str)
    def unlinkIdentity(self, identity_id: str) -> None:
        """Unlink a login identity (backend refuses the last one)."""
        identity_id = (identity_id or "").strip()
        if not identity_id:
            return
        if self._status != STATUS_AUTHENTICATED or not self._access_token:
            return
        self._launch(lambda: self._unlink_flow(identity_id), name="cheremsha-unlink")

    @Slot(str, result="QVariantMap")
    def platformStatus(self, platform: str) -> dict[str, Any]:
        info = self._platforms.get((platform or "").strip().lower())
        if info is None:
            return {"platform": platform, "connected": False}
        return {
            "platform": info.platform,
            "connected": info.connected,
            "username": info.username or "",
            "display_name": info.display_name or "",
            "avatar_url": info.avatar_url or "",
            "status": info.status or "",
        }

    def avatar_bytes(self) -> bytes | None:
        return self._avatar_bytes

    def linked_identities(self) -> list[dict[str, Any]]:
        """User-visible linked login identities (provider + email only)."""
        return [dict(i) for i in self._identities]

    # -- flows (async, never block the GUI thread) -------------------------
    async def restore_session(self) -> None:
        """Validate a persisted session at startup. Silent on failure."""
        if self._status != STATUS_LOGGED_OUT or self._busy():
            return
        self._set_status(STATUS_RESTORING)
        try:
            saved = await asyncio.to_thread(load_session)
        except Exception:
            saved = None
        if saved is None:
            self._set_status(STATUS_LOGGED_OUT)
            return
        client = self._client_or_create()
        try:
            user = await client.get_me(saved.access_token)
        except CloudApiError as exc:
            if exc.status != 401 or not saved.refresh_token:
                self._clear_local()
                self._set_status(STATUS_LOGGED_OUT)
                return
            try:
                tokens, _ = await client.refresh_session(saved.refresh_token)
            except CloudApiError:
                self._clear_local()
                self._set_status(STATUS_LOGGED_OUT)
                return
            try:
                user = await client.get_me(tokens.access_token)
            except CloudApiError:
                self._clear_local()
                self._set_status(STATUS_LOGGED_OUT)
                return
            self._store_session(tokens.access_token, tokens.refresh_token, user)
        else:
            self._store_session(saved.access_token, saved.refresh_token, user)
        self._set_status(STATUS_AUTHENTICATED)
        await self._sync_platforms_and_avatar(client)
        await self._refresh_identities(client)

    async def _login_flow(self, provider: str) -> None:
        self._set_status(STATUS_STARTING)
        pkce = generate_pkce()
        desktop_state = secrets.token_urlsafe(24)
        server = DesktopCallbackServer(expected_state=desktop_state)
        try:
            try:
                await server.start()
            except OSError:
                logger.warning("cheremsha login aborted: loopback callback port busy")
                self._set_status(STATUS_LOGGED_OUT)
                self.notice.emit("callback-busy")
                return
            client = self._client_or_create()
            try:
                start = await client.login_start(
                    provider, code_challenge=pkce.challenge, desktop_state=desktop_state
                )
            except CloudApiError as exc:
                logger.warning("cheremsha login start failed: %s", exc)
                self._set_status(STATUS_LOGGED_OUT)
                self.notice.emit("unreachable")
                return
            auth_url = str(start.get("authorization_url") or "")
            if not (auth_url.startswith("https://") or auth_url.startswith("http://")):
                self._set_status(STATUS_LOGGED_OUT)
                return
            self._set_status(STATUS_AWAITING_CALLBACK)
            self._open_url(auth_url)
            try:
                grant, _ = await server.wait_for_callback()
            except (TimeoutError, asyncio.CancelledError):
                # User closed the browser / cancelled: back to logged-out, no popup.
                self._set_status(STATUS_LOGGED_OUT)
                return
            try:
                tokens, user, auto_connect = await client.exchange_desktop_code(
                    code=grant, verifier=pkce.verifier
                )
            except CloudApiError as exc:
                logger.warning("cheremsha code exchange failed: %s", exc)
                self._set_status(STATUS_LOGGED_OUT)
                self.notice.emit("exchange-failed")
                return
            self._store_session(tokens.access_token, tokens.refresh_token, user)
            self._set_status(STATUS_AUTHENTICATED)
            # Surface the OAuth auto-connect result. The reconcile loop
            # reads this on the next tick to enable the corresponding
            # platform for this installation (and to suppress redundant
            # connect-time OAuth round-trips in the QML).
            if auto_connect is not None:
                self._last_auto_connect = auto_connect
                if auto_connect.connected and auto_connect.platform:
                    self._auto_connected_platform = auto_connect.platform
                    self._on_auto_connected(auto_connect)
                if auto_connect.reauth_required and auto_connect.platform:
                    self._on_auto_reauth_required(auto_connect)
            # A logged-out platform-connect request lands here: twitch/tiktok/
            # kick arrive connected via auto-connect + reconcile; youtube needs
            # an explicit connect round-trip (google login is login-only).
            pending, self._pending_platform = self._pending_platform, None
            if pending == "youtube":
                await self._platform_connect_flow("youtube")
            await self._sync_platforms_and_avatar(client)
            await self._refresh_identities(client)
        except asyncio.CancelledError:
            # cancelLogin() or logout() abandoned this flow: converge on logged-out.
            self._set_status(STATUS_LOGGED_OUT)
            raise
        finally:
            await server.stop()

    async def _link_flow(self, provider: str) -> None:
        server = DesktopCallbackServer(expected_state="")
        try:
            try:
                await server.start()
            except OSError:
                self.notice.emit("callback-busy")
                return
            client = self._client_or_create()
            try:
                start = await client.link_start(provider, self._access_token or "")
            except CloudApiError:
                self.notice.emit("unreachable")
                return
            auth_url = str(start.get("authorization_url") or "")
            if not (auth_url.startswith("https://") or auth_url.startswith("http://")):
                return
            self._open_url(auth_url)
            try:
                outcome = await server.wait_for_link()
            except (TimeoutError, asyncio.CancelledError):
                return
            if outcome.get("status") == "conflict":
                self.notice.emit("link-conflict")
            await self._refresh_identities(client)
        except asyncio.CancelledError:
            raise
        finally:
            await server.stop()

    async def _refresh_identities(self, client: CheremshaCloudClient) -> None:
        if not self._access_token:
            return
        try:
            self._identities = await client.get_identities(self._access_token)
        except CloudApiError:
            return
        self.identitiesChanged.emit()

    async def _unlink_flow(self, identity_id: str) -> None:
        client = self._client_or_create()
        try:
            await client.unlink_identity(identity_id, self._access_token or "")
        except CloudApiError as exc:
            self.notice.emit("unlink-last" if exc.status == 400 else "unreachable")
            return
        await self._refresh_identities(client)

    async def _platform_connect_flow(self, platform: str) -> None:
        server = DesktopCallbackServer(expected_state="")
        try:
            try:
                await server.start()
            except OSError:
                self.notice.emit("callback-busy")
                return
            client = self._client_or_create()
            try:
                start = await client.platform_connect_start(
                    platform, self._access_token or ""
                )
            except CloudApiError:
                self.notice.emit("unreachable")
                return
            auth_url = str(start.get("authorization_url") or "")
            if not (auth_url.startswith("https://") or auth_url.startswith("http://")):
                return
            self._open_url(auth_url)
            try:
                await server.wait_for_platform(platform=platform)
            except (TimeoutError, asyncio.CancelledError):
                return
            await self._sync_platforms_and_avatar(client)
        except asyncio.CancelledError:
            raise
        finally:
            await server.stop()

    async def _logout_flow(self) -> None:
        self._pending_platform = None
        if self._access_token:
            try:
                await self._client_or_create().logout(self._access_token)
            except Exception:
                pass
        self._clear_local()
        self._set_status(STATUS_LOGGED_OUT)

    def replace_auto_connect_callbacks(
        self,
        *,
        on_auto_connected: Callable[[CloudAutoConnectOutcome], None] | None,
        on_auto_reauth_required: Callable[[CloudAutoConnectOutcome], None] | None,
    ) -> None:
        """Replace the auto-connect callbacks after the QObject has been
        constructed (used by MainWindow so closure-based callbacks can
        reference helpers defined later in __init__)."""
        if on_auto_connected is not None:
            self._on_auto_connected = on_auto_connected
        if on_auto_reauth_required is not None:
            self._on_auto_reauth_required = on_auto_reauth_required

    async def _platforms_flow(self) -> None:
        if not self._access_token:
            return
        await self._sync_platforms_and_avatar(self._client_or_create())

    async def _sync_platforms_and_avatar(self, client: CheremshaCloudClient) -> None:
        if not self._access_token:
            return
        try:
            platforms = await client.get_platforms(self._access_token)
        except CloudApiError as exc:
            if exc.status == 401 and self._refresh_token:
                try:
                    tokens, _ = await client.refresh_session(self._refresh_token)
                except CloudApiError:
                    self._clear_local()
                    self._set_status(STATUS_LOGGED_OUT)
                    return
                if self._user is not None:
                    self._store_session(tokens.access_token, tokens.refresh_token, self._user)
                try:
                    platforms = await client.get_platforms(tokens.access_token)
                except CloudApiError:
                    return
            else:
                return
        self._platforms = {p.platform: p for p in platforms}
        self.platformsChanged.emit()
        if self._user and self._user.avatar_url and self._avatar_bytes is None:
            avatar = await client.fetch_avatar(self._user.avatar_url)
            if avatar:
                self._avatar_bytes = avatar
                self.avatarChanged.emit()
