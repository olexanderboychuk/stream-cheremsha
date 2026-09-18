"""PlatformConnectionManager — desktop-side reconciliation between the
Cheremsha Cloud PlatformConnection table and the existing platform sources.

Responsibilities:
- After Cheremsha login (or session restore), read ``GET /platforms``.
- For each platform the desktop wants to run (autostart or already-
  running), request a short-lived runtime token from the Cloud broker.
- Inject the credential into the existing Twitch / TikTok / Kick / YouTube
  PlatformSource ``start()`` methods.

Hard rules (per spec):
- Never touch ``SyncManager``.
- Never duplicate provider OAuth code; reuse existing
  ``PlatformTokenService`` on the Cloud side.
- Never delete local credentials when a cloud PlatformConnection exists.
- Never silently recreate a disconnected platform from stale keys.
- All network work is async; no GUI-thread blocking.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from stream_cheremsha.cloud.auth_state import STATUS_AUTHENTICATED

logger = logging.getLogger(__name__)

REAUTH_REQUIRED_PLATFORMS: tuple[str, ...] = ("twitch", "tiktok", "kick", "youtube")


class PlatformConnectionManager(QObject):
    """Reconciles cloud PlatformConnection rows against local platform state.

    The desktop has existing ``TwitchSource``/``TikTokChatSource``/``KickSource``/
    ``YouTubeChatSource`` instances that the application already constructs.
    This class only orchestrates start/stop; it never reads or writes provider
    tokens directly. Credentials come through injected
    ``CloudCredentialAdapter`` (Cloud broker) or fall back to the existing
    local keyring via the existing ``_start_*`` helpers.
    """

    statusChanged = Signal()  # emit when reauth-not-required grid changes.
    lastErrorChanged = Signal()
    needsReauthChanged = Signal()

    def __init__(
        self,
        auth: QObject,
        *,
        cloud_fetch_platforms: Callable[[], Awaitable[list[dict[str, Any]]]],
        cloud_fetch_runtime_token: Callable[[str], Awaitable[dict[str, Any]]],
        fetch_local_summaries: Callable[[], dict[str, dict[str, Any]]],
        start_platform: Callable[[str, dict[str, Any]], Awaitable[bool]],
        stop_platform: Callable[[str], Awaitable[bool]],
        autostart_predicate: Callable[[str], bool],
        post_status: Callable[[str], None],
        platform_status_fields: Callable[[str, str, bool], None],
        platform_local_enabled: Callable[[str], bool] | None = None,
        set_platform_local_enabled: Callable[[str, bool], None] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._auth = auth
        self._fetch_platforms = cloud_fetch_platforms
        self._fetch_runtime = cloud_fetch_runtime_token
        self._local_summaries = fetch_local_summaries
        self._start = start_platform
        self._stop = stop_platform
        self._autostart = autostart_predicate
        self._local_enabled = platform_local_enabled or (lambda _p: False)
        self._set_local_enabled = set_platform_local_enabled or (lambda _p, _e: None)
        self._post_status = post_status
        self._platform_status_fields = platform_status_fields
        self._last_error: str = ""
        self._needs_reauth: dict[str, bool] = {}
        self._task: asyncio.Task | None = None
        try:
            auth.statusChanged.connect(self._on_auth_status)  # type: ignore[union-attr]
        except Exception:
            pass
        try:
            auth.platformsChanged.connect(self._on_platforms_changed)  # type: ignore[union-attr]
        except Exception:
            pass

    # ---- properties ------------------------------------------------------
    def _get_last_error(self) -> str:
        return self._last_error

    lastError = Property(str, _get_last_error, notify=lastErrorChanged)

    def _get_needs_reauth(self) -> str:
        return ",".join(p for p, v in self._needs_reauth.items() if v)

    needsReauthPlatforms = Property(str, _get_needs_reauth, notify=needsReauthChanged)

    # ---- lifecycle -------------------------------------------------------
    def _on_auth_status(self, status: str) -> None:
        if status == STATUS_AUTHENTICATED or status == "auth-restored":
            self._launch(reason="auth-status")

    def _on_platforms_changed(self) -> None:
        # Fired by AuthState after ``/platforms`` polling; re-sync.
        self._launch(reason="platforms-changed")

    @Slot()
    def triggerReconcile(self) -> None:
        """QML-facing manual refresh (e.g. settings-page refresh button)."""
        self._launch(reason="manual")

    def _launch(self, *, reason: str) -> None:
        if self._task is not None and not self._task.done():
            return  # duplicate guard
        logger.debug("cloud platform reconcile trigger: %s", reason)
        try:
            self._task = asyncio.create_task(
                self._reconcile_loop(), name="cheremsha-platform-reconcile"
            )
        except RuntimeError:
            pass

    async def _reconcile_loop(self) -> None:
        try:
            await self.reconcile()
        finally:
            self._task = None

    async def reconcile(self) -> None:
        """Pull cloud state and drive local PlatformSource start/stop.

        Strategy:
        1. Fetch cloud ``PlatformConnection`` metadata (safe fields only).
        2. For each cloud-connected platform with reauth not required:
            attempt to short-start the local PlatformSource via the existing
            ``start()`` API, but routing the credential request through the
            broker instead of the local keyring.
        3. For each platform the desktop wants to run according to the user
            autostart preference but the cloud does not list: keep the
            existing local-credential path intact (legacy / fallback).
        4. For any cloud-disconnected platform that the desktop still has
            running locally, stop the local source. Never silently recreate.
        """
        try:
            cloud_platforms = await self._fetch_platforms()
        except Exception as exc:
            self._last_error = f"fetch_failed: {type(exc).__name__}"
            self.lastErrorChanged.emit()
            self._post_status("Cheremsha Cloud: не вдалося отримати платформи")
            return
        self._last_error = ""
        self.lastErrorChanged.emit()

        cloud_by_name: dict[str, dict[str, Any]] = {
            p["platform"]: p for p in cloud_platforms if "platform" in p
        }

        # Resolve platforms we care about right now. The reconcile
        # gate is now `_platform_local_enabled`: a boolean that flips
        # to True automatically after a successful OAuth auto-connect
        # and stays at the user's manually chosen value across
        # restarts. The legacy `_autostart` setting ("start on app
        # launch") is still allowed to bring up a platform that has
        # no record in the local-enabled store but is still connected
        # via Cloud.
        candidate_names: set[str] = set()
        for plat in REAUTH_REQUIRED_PLATFORMS:
            if self._local_enabled(plat):
                candidate_names.add(plat)
        # Allow the legacy autostart-on-launch flag to bring up a
        # previously-configured platform even when no local-enabled
        # sentinel has been written yet (covers users who already had
        # local credentials before this cloud flow landed).
        for plat in REAUTH_REQUIRED_PLATFORMS:
            if plat not in candidate_names and self._autostart(plat):
                candidate_names.add(plat)
        local = self._local_summaries()
        for plat in REAUTH_REQUIRED_PLATFORMS:
            if local.get(plat, {}).get("running"):
                candidate_names.add(plat)

        # Also: stop the local source for any platform whose Cloud row
        # explicitly says "disconnected / deleted / revoked". An *absent*
        # cloud row is not equivalent — it means "Cloud has no row for this
        # platform under this account". We must NEVER silently recreate a
        # connection from stale local state, but we also must NEVER halt a
        # legitimate legacy/local source if Cloud simply hasn't synced yet.
        for plat in REAUTH_REQUIRED_PLATFORMS:
            info = cloud_by_name.get(plat)
            local_running = bool(local.get(plat, {}).get("running"))
            if (
                local_running
                and info is not None
                and info.get("status")
                in {
                    "disconnected",
                    "deleted",
                    "revoked",
                }
            ):
                await self._stop(plat)
                self._post_status(f"{plat.capitalize()}: зупинено — Cloud вимкнув з'єднання")
                self._platform_status_fields(plat, "disconnected", False)
                continue

        # Start / repair candidate platforms that are cloud-connected.
        for plat in sorted(candidate_names):
            info = cloud_by_name.get(plat)
            if info is None:
                # Local-only fallback: try the existing keyring path.
                # Nothing to do here — the existing autostart helpers in
                # MainWindow would have already started the source. Leave
                # status alone.
                continue
            status = info.get("status") or ""
            # Anything that says "disconnected / deleted / revoked" was
            # already handled above (we called ``continue`` so we never
            # call the broker for these). Defensive re-check here covers
            # the case where ``info`` only appears AFTER we entered the
            # start loop with stale local state.
            if status in {"disconnected", "deleted", "revoked"}:
                self._needs_reauth[plat] = True
                self.needsReauthChanged.emit()
                self._platform_status_fields(plat, "disconnected", False)
                continue
            if status in {"reauth_required", "expired"}:
                self._needs_reauth[plat] = True
                self.needsReauthChanged.emit()
                self._platform_status_fields(plat, "reauth_required", False)
                self._post_status(f"{plat.capitalize()}: потрібна повторна авторизація")
                continue
            # Cloud says connected. Try to acquire a runtime credential and
            # feed it to the existing source.
            try:
                runtime = await self._fetch_runtime(plat)
            except Exception as exc:
                self._last_error = f"{plat}: broker_unreachable: {type(exc).__name__}"
                self.lastErrorChanged.emit()
                self._post_status(f"{plat.capitalize()}: Cloud недоступний")
                continue
            if runtime.get("reauth_required"):
                self._needs_reauth[plat] = True
                self.needsReauthChanged.emit()
                self._platform_status_fields(plat, "reauth_required", False)
                continue
            runtime["platform"] = plat
            ok = await self._start(plat, runtime)
            if ok:
                self._needs_reauth[plat] = False
                self.needsReauthChanged.emit()
                self._platform_status_fields(plat, "active", True)
                name = runtime.get("username") or runtime.get("display_name") or plat
                self._post_status(f"{plat.capitalize()}: Підключено (@{name})")

    # ---- helpers --------------------------------------------------------
    @staticmethod
    def needs_reauth_for(platform: str, last_status: str | None) -> bool:
        """Static helper: does the cloud metadata indicate reauth needed?"""
        return last_status in {"reauth_required", "revoked", "expired"}
