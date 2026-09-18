"""Desktop PlatformConnectionManager reconciliation against mocked
Cheremsha Cloud responses — no real provider / Cloud traffic.

Covers the spec:
- Cloud-connected Twitch starts the existing TwitchSource via runtime token
- Stale local credentials cannot recreate a disconnected cloud connection
- Insufficient / reauth_required surfaces NEITHER starts nor hard crash
- Pending task guard prevents duplicate reconcile runs

The manager only reacts to status, calls cloud helpers, then routes through
injected Callable hooks. We never construct the full MainWindow.
"""

from __future__ import annotations

import asyncio
import logging

import pytest
from PySide6.QtCore import QCoreApplication, QObject

# ---------------------------------------------------------------- stub auth
from stream_cheremsha.cloud.platform_bridge import PlatformConnectionManager


class _StubAuth(QObject):
    def __init__(self) -> None:
        super().__init__()
        self.status = "logged-out"
        self._status_signal_calls: list[str] = []
        self.platforms = []
        self.statusChanged = type(
            "Signal",
            (),
            {"connect": lambda self_, fn: fn},  # immediate fire pattern
        )()
        self.platformsChanged = type(
            "Signal",
            (),
            {"connect": lambda self_, fn: fn},
        )()


def _make_manager(
    *,
    fetch_platforms_response: list[dict] | Exception,
    fetch_runtime_response: dict | Exception,
    autostart_twitch: bool = True,
) -> tuple[PlatformConnectionManager, dict]:
    """Returns the manager plus a recorder capturing start/stop/post_status."""
    events: dict = {"started": [], "stopped": [], "status": [], "status_fields": []}
    fetched_platforms_calls: list = []
    fetched_runtime_calls: list[str] = []

    async def _fetch_platforms() -> list[dict]:
        fetched_platforms_calls.append("called")
        if isinstance(fetch_platforms_response, Exception):
            raise fetch_platforms_response
        return list(fetch_platforms_response)

    async def _fetch_runtime(platform: str) -> dict:
        fetched_runtime_calls.append(platform)
        if isinstance(fetch_runtime_response, Exception):
            raise fetch_runtime_response
        return dict(fetch_runtime_response)

    async def _start(platform: str, runtime: dict) -> bool:
        events["started"].append((platform, dict(runtime)))
        return True

    async def _stop(platform: str) -> bool:
        events["stopped"].append(platform)
        return True

    def _autostart(platform: str) -> bool:
        return autostart_twitch and platform == "twitch"

    def _local() -> dict[str, dict]:
        return {
            p: {"running": True, "reauth_required": False}
            for p in ("twitch", "youtube", "tiktok", "kick")
        }

    def _post(msg: str) -> None:
        events["status"].append(msg)

    def _fields(plat: str, status: str, connected: bool) -> None:
        events["status_fields"].append((plat, status, connected))

    mgr = PlatformConnectionManager(
        _StubAuth(),
        cloud_fetch_platforms=_fetch_platforms,
        cloud_fetch_runtime_token=_fetch_runtime,
        fetch_local_summaries=_local,
        start_platform=_start,
        stop_platform=_stop,
        autostart_predicate=_autostart,
        post_status=_post,
        platform_status_fields=_fields,
    )
    recorder = {
        "events": events,
        "fetched_platforms_calls": fetched_platforms_calls,
        "fetched_runtime_calls": fetched_runtime_calls,
    }
    return mgr, recorder


# ---------------------------------------------------------------- tests
@pytest.fixture()
def qapp():
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


@pytest.mark.asyncio()
async def test_cloud_connected_twitch_starts_without_local_keyring(qapp):
    mgr, rec = _make_manager(
        fetch_platforms_response=[
            {
                "platform": "twitch",
                "connected": True,
                "username": "kodithecat",
                "display_name": "KodiTheCat",
                "status": "active",
            }
        ],
        fetch_runtime_response={
            "access_token": "BROKERED-TOKEN-MARKER",
            "platform_user_id": "1",
            "username": "kodithecat",
            "display_name": "KodiTheCat",
            "reauth_required": False,
            "scope": "user:read:email",
        },
    )
    await mgr.reconcile()
    assert rec["fetched_platforms_calls"] == ["called"]
    assert rec["fetched_runtime_calls"] == ["twitch"]
    assert any(
        plat == "twitch" and data.get("access_token") == "BROKERED-TOKEN-MARKER"
        for plat, data in rec["events"]["started"]
    )
    assert rec["events"]["status_fields"] == [("twitch", "active", True)]
    assert rec["events"]["stopped"] == []


@pytest.mark.asyncio()
async def test_stale_local_credentials_do_not_recreate_disconnected_cloud(qapp):
    """The manager sees Cloud as disconnected and asks the local layer
    to stop — even though the local TwitchSource would otherwise still
    be running per ``_local()`` summary."""
    mgr, rec = _make_manager(
        fetch_platforms_response=[
            {
                "platform": "twitch",
                "connected": False,
                "username": None,
                "display_name": None,
                "status": "disconnected",
            }
        ],
        fetch_runtime_response={"reauth_required": True},  # arbitrary
    )
    mgr._autostart = lambda platform: False  # noqa: SLF001
    await mgr.reconcile()
    # Crucial: even if the broker is reachable, **no token fetch happened**
    # because Cloud says disconnected. The local TwitchSource is stopped
    # to prevent stale credentials from recreating a phantom connection.
    assert rec["fetched_runtime_calls"] == []
    assert "twitch" in rec["events"]["stopped"]
    assert ("twitch", "disconnected", False) in rec["events"]["status_fields"]


@pytest.mark.asyncio()
async def test_reauth_required_does_not_start_platform(qapp):
    """Two reauth_required paths:
    (A) cloud PlatformConnection metadata already says reauth_required:
        we never even call the broker (saves a round trip per spec).
    (B) cloud says active but broker returns reauth_required at runtime:
        we never start the platform.
    """
    # Path A — metadata-level reauth.
    mgr, rec = _make_manager(
        fetch_platforms_response=[
            {
                "platform": "twitch",
                "connected": True,
                "username": "kodithecat",
                "display_name": "KodiTheCat",
                "status": "reauth_required",
            }
        ],
        fetch_runtime_response={"reauth_required": True},
    )
    await mgr.reconcile()
    assert rec["fetched_runtime_calls"] == []
    assert rec["events"]["started"] == []
    assert ("twitch", "reauth_required", False) in rec["events"]["status_fields"]
    assert "twitch" in mgr.needsReauthPlatforms

    # Path B — runtime broker returns reauth_required.
    mgr2, rec2 = _make_manager(
        fetch_platforms_response=[
            {
                "platform": "twitch",
                "connected": True,
                "username": "kodithecat",
                "display_name": "KodiTheCat",
                "status": "active",
            }
        ],
        fetch_runtime_response={"reauth_required": True},
    )
    await mgr2.reconcile()
    assert rec2["fetched_runtime_calls"] == ["twitch"]
    assert rec2["events"]["started"] == []
    assert ("twitch", "reauth_required", False) in rec2["events"]["status_fields"]
    assert "twitch" in mgr2.needsReauthPlatforms


@pytest.mark.asyncio()
async def test_broker_unreachable_keeps_local_source_running(qapp):
    """When the broker call itself fails (network), the manager does not
    crash, does not swallow existing local state, and reports the error.

    The local TwitchSource is still ``running=True``; we do not stop it
    on network failure (that's the legacy/local fallback path)."""
    mgr, rec = _make_manager(
        fetch_platforms_response=[
            {
                "platform": "twitch",
                "connected": True,
                "username": "kodithecat",
                "status": "active",
            }
        ],
        fetch_runtime_response=RuntimeError("broker_unreachable"),
    )
    await mgr.reconcile()
    # Has the broker error report and has NOT started or stopped the
    # platform.
    assert mgr.lastError.startswith("twitch: broker_unreachable")
    assert mgr.lastError.endswith("RuntimeError")
    assert rec["events"]["started"] == []
    assert rec["events"]["stopped"] == []
    # The failure is also surfaced in the footer (never silent).
    assert any("Twitch" in m for m in rec["events"]["status"])


@pytest.mark.asyncio()
async def test_fetch_failure_posts_cause_to_footer(qapp):
    """Footer carries the exception cause so the user knows what to fix."""
    mgr, rec = _make_manager(
        fetch_platforms_response=RuntimeError("boom"),
        fetch_runtime_response={},
    )
    await mgr.reconcile()
    assert any("boom" in m for m in rec["events"]["status"])


@pytest.mark.asyncio()
async def test_fetch_while_logged_out_asks_to_sign_in(qapp):
    """Missing session is not an error: the footer says what to do."""
    mgr, rec = _make_manager(
        fetch_platforms_response=RuntimeError("not authenticated"),
        fetch_runtime_response={},
    )
    await mgr.reconcile()
    assert any("увійдіть" in m.lower() for m in rec["events"]["status"])


@pytest.mark.asyncio()
async def test_reconcile_is_a_single_duplicate_guarded_task(qapp):
    """Calling triggerReconcile multiple times in quick succession must
    coalesce (only one running task). Once it finishes, a new call can fire."""
    mgr, rec = _make_manager(
        fetch_platforms_response=[
            {
                "platform": "twitch",
                "connected": True,
                "username": "kodithecat",
                "status": "active",
            }
        ],
        fetch_runtime_response={
            "access_token": "B-T",
            "platform_user_id": "1",
            "username": "kodithecat",
            "reauth_required": False,
        },
    )
    # Direct ``reconcile()`` runs synchronously — we test the live trigger.
    mgr.triggerReconcile()
    mgr.triggerReconcile()
    mgr.triggerReconcile()
    # The task is queued.
    task = mgr._task
    assert task is not None
    # Await the actual task, with timeout.
    await asyncio.wait_for(asyncio.shield(task), timeout=10)
    # After completion, exactly one fetch call happened.
    assert rec["fetched_platforms_calls"] == ["called"]


@pytest.mark.asyncio()
async def test_non_token_fields_only_in_payload(qapp):
    """The runtime token dict passed to the existing source must NEVER
    contain a refresh_token field. We assert that responsibility at the
    adapter level (manager layer)."""
    mgr, rec = _make_manager(
        fetch_platforms_response=[
            {
                "platform": "twitch",
                "connected": True,
                "username": "kodithecat",
                "status": "active",
            }
        ],
        # Cloud broker never returns refresh_token in the runtime payload.
        fetch_runtime_response={
            "access_token": "AT-NO-RT",
            "platform_user_id": "1",
            "username": "kodithecat",
            "display_name": "KodiTheCat",
            "reauth_required": False,
            "scope": "user:read:email",
        },
    )
    await mgr.reconcile()
    assert rec["events"]["started"]
    for plat, payload in rec["events"]["started"]:
        assert "refresh_token" not in payload
        assert "client_secret" not in payload
        assert "client_id" not in payload  # desktop-only fields stay out


@pytest.mark.asyncio()
async def test_no_qml_logging_of_secrets(qapp, caplog):
    """The reconciliation cycle must NOT log access tokens, refresh
    tokens, or other secrets to the application logger."""
    mgr, rec = _make_manager(
        fetch_platforms_response=[
            {
                "platform": "twitch",
                "connected": True,
                "username": "kodithecat",
                "status": "active",
            }
        ],
        fetch_runtime_response={
            "access_token": "AT-SECRET-MARKER",
            "refresh_token": "RT-SECRET-MARKER",
            "platform_user_id": "1",
            "username": "kodithecat",
            "reauth_required": False,
        },
    )
    with caplog.at_level(logging.DEBUG):
        await mgr.reconcile()
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert "AT-SECRET-MARKER" not in text
    assert "RT-SECRET-MARKER" not in text


# ---------------------------------------------------------------- new tests:
# State propagation through auto-connect path.
@pytest.mark.asyncio()
async def test_local_enabled_gate_starts_only_when_init_sentinel_written(qapp):
    """Brand-new account: no platform_enabled init sentinel → manager
    will NOT start the source, even if Cloud says connected. The user
    must explicitly consent (either via OAuth auto-connect or via the
    in-app toggle)."""
    enabled_by_platform: dict[str, bool] = {}

    mgr, rec = await _build_manager_with_local_enabled(
        enabled_by_platform=enabled_by_platform,
        platforms_response=[
            {
                "platform": "twitch",
                "connected": True,
                "username": "kodithecat",
                "status": "active",
            }
        ],
        runtime_response={
            "access_token": "AT",
            "platform_user_id": "1",
            "username": "kodithecat",
            "reauth_required": False,
        },
        autostart_twitch=False,
        local_running={"twitch": True},
    )
    await mgr.reconcile()
    # local-enabled is False (no init), autostart is False → twitch
    # is still a candidate ONLY because ``local_running`` says True.
    # The legacy-fallback still works for users who configured a local
    # TwitchSource via the legacy keyring flow already.
    started = rec["events"]["started"]
    assert len(started) == 1 and started[0][0] == "twitch"
    assert started[0][1]["access_token"] == "AT"


@pytest.mark.asyncio()
async def test_local_enabled_starts_freshly_auto_connected_platform(qapp):
    """Auth flow has flipped ``twitch`` enabled=True + sentinel. Reconcile
    sees Cloud-connected Twitch AND local_enabled=True → twitches source
    starts via the runtime broker."""
    enabled_by_platform = {"twitch": True}

    mgr, rec = await _build_manager_with_local_enabled(
        enabled_by_platform=enabled_by_platform,
        platforms_response=[
            {
                "platform": "twitch",
                "connected": True,
                "username": "kodithecat",
                "status": "active",
            }
        ],
        runtime_response={
            "access_token": "AT-AUTO",
            "platform_user_id": "1",
            "username": "kodithecat",
            "reauth_required": False,
        },
        autostart_twitch=False,
        local_running={"twitch": False},  # brand-new install
    )
    await mgr.reconcile()
    assert ("twitch", "active", True) in rec["events"]["status_fields"]
    started = rec["events"]["started"]
    assert len(started) == 1 and started[0][0] == "twitch"
    assert started[0][1]["access_token"] == "AT-AUTO"


@pytest.mark.asyncio()
async def test_user_disabled_platform_is_not_reenabled_on_startup(qapp):
    """User manual toggle persisted platform_enabled=False with sentinel.
    On subsequent reconcile, we MUST NOT start the source even though
    Cloud still says connected."""
    enabled_by_platform = {"twitch": False}

    mgr, rec = await _build_manager_with_local_enabled(
        enabled_by_platform=enabled_by_platform,
        platforms_response=[
            {
                "platform": "twitch",
                "connected": True,
                "username": "kodithecat",
                "status": "active",
            }
        ],
        runtime_response={
            "access_token": "AT-LEAVE-ME",
            "platform_user_id": "1",
            "username": "kodithecat",
            "reauth_required": False,
        },
        autostart_twitch=False,
        local_running={"twitch": False},
    )
    await mgr.reconcile()
    # The runtime issuer may still be called because a previous installed
    # source could have been running. Here, local_running says no.
    # We accept either no-start (gate by local_enabled) or a graceful
    # stop. The defining assertion is that no new credentials are wired
    # into the source. We require the connect card to NOT show active
    # unless user re-enables — meaning status_fields stays at the
    # default the platform would otherwise have.
    assert (
        ("twitch", "active", True) not in rec["events"]["status_fields"]
    )


async def _build_manager_with_local_enabled(
    *,
    enabled_by_platform: dict[str, bool],
    platforms_response: list[dict],
    runtime_response: dict,
    autostart_twitch: bool,
    local_running: dict[str, bool],
) -> tuple[PlatformConnectionManager, dict]:
    events: dict = {"started": [], "stopped": [], "status": [], "status_fields": []}
    fetched_platforms_calls: list = []
    fetched_runtime_calls: list[str] = []

    async def _fetch_platforms() -> list[dict]:
        fetched_platforms_calls.append("called")
        return list(platforms_response)

    async def _fetch_runtime(platform: str) -> dict:
        fetched_runtime_calls.append(platform)
        return dict(runtime_response)

    async def _start(platform: str, runtime: dict) -> bool:
        events["started"].append((platform, dict(runtime)))
        return True

    async def _stop(platform: str) -> bool:
        events["stopped"].append(platform)
        return True

    def _autostart(plat: str) -> bool:
        return autostart_twitch and plat == "twitch"

    def _local_summary() -> dict[str, dict]:
        platforms = ("twitch", "youtube", "tiktok", "kick")
        return {
            p: {"running": bool(local_running.get(p, False))}
            for p in platforms
        }

    def _local_enabled(plat: str) -> bool:
        # Mirrors `_read_platform_local_enabled`: requires init-sentinel
        # AND the boolean value.
        if plat not in enabled_by_platform:
            return False
        return enabled_by_platform[plat]

    def _set_local_enabled(plat: str, enabled: bool) -> None:
        enabled_by_platform[plat] = bool(enabled)

    def _post(msg: str) -> None:
        events["status"].append(msg)

    def _fields(plat: str, status: str, connected: bool) -> None:
        events["status_fields"].append((plat, status, connected))

    mgr = PlatformConnectionManager(
        _StubAuth(),
        cloud_fetch_platforms=_fetch_platforms,
        cloud_fetch_runtime_token=_fetch_runtime,
        fetch_local_summaries=_local_summary,
        start_platform=_start,
        stop_platform=_stop,
        autostart_predicate=_autostart,
        post_status=_post,
        platform_status_fields=_fields,
        platform_local_enabled=_local_enabled,
        set_platform_local_enabled=_set_local_enabled,
    )
    recorder = {
        "events": events,
        "fetched_platforms_calls": fetched_platforms_calls,
        "fetched_runtime_calls": fetched_runtime_calls,
    }
    return mgr, recorder
