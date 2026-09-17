"""Cheremsha Cloud account auth: client shapes, session store, state machine.

No real Cloud API or provider is ever touched: HTTP goes through
``httpx.MockTransport`` and the loopback callback is driven directly.
"""

from __future__ import annotations

import asyncio
import json
import logging

import httpx
import pytest

from stream_cheremsha.cloud import constants as cloud_constants
from stream_cheremsha.cloud.auth_state import (
    STATUS_AUTHENTICATED,
    STATUS_AWAITING_CALLBACK,
    STATUS_LOGGED_OUT,
    CheremshaAuthState,
)
from stream_cheremsha.cloud.client import (
    CheremshaCloudClient,
    CloudApiError,
    CloudAutoConnectOutcome,
    CloudPlatformStatus,
    CloudSessionTokens,
    CloudUser,
)
from stream_cheremsha.cloud.session_store import (
    CheremshaSession,
    clear_session,
    load_session,
    save_session,
)


# ---------------------------------------------------------------- helpers
class FakeCloudClient(CheremshaCloudClient):
    """Scriptable backend double. Never touches the network."""

    def __init__(self) -> None:
        super().__init__("http://cloud.test")
        self.start_calls: list[dict] = []
        self.exchange_calls: list[dict] = []
        self.me_result: CloudUser | CloudApiError = CloudUser(
            id="u-1", email="kodi@example.com", display_name="kodi_the_cat"
        )
        self.refresh_result: tuple | CloudApiError = (
            CloudSessionTokens("tok-a2", "tok-r2", 900),
            None,
        )
        self.platforms: list[CloudPlatformStatus] = []
        self.avatar: bytes | None = None
        self.logged_out = 0

    async def login_start(self, provider, *, code_challenge, desktop_state):  # type: ignore[override]
        self.start_calls.append(
            {"provider": provider, "challenge": code_challenge, "state": desktop_state}
        )
        return {"authorization_url": "https://accounts.example/auth", "state": "srv-state"}

    async def exchange_desktop_code(self, *, code, verifier):  # type: ignore[override]
        self.exchange_calls.append({"code": code, "verifier": verifier})
        return (
            CloudSessionTokens("tok-access-SECRET", "tok-refresh-SECRET", 900),
            CloudUser("u-1", "kodi@example.com", "kodi_the_cat"),
            None,
        )

    async def get_me(self, access_token):  # type: ignore[override]
        if isinstance(self.me_result, CloudApiError):
            raise self.me_result
        assert access_token
        return self.me_result

    async def refresh_session(self, refresh_token):  # type: ignore[override]
        if isinstance(self.refresh_result, CloudApiError):
            raise self.refresh_result
        return self.refresh_result

    async def logout(self, access_token):  # type: ignore[override]
        self.logged_out += 1

    async def get_platforms(self, access_token):  # type: ignore[override]
        assert access_token
        return self.platforms

    async def fetch_avatar(self, url):  # type: ignore[override]
        return self.avatar


@pytest.fixture()
def keyring_fake(monkeypatch):
    store: dict[str, str] = {}
    import stream_cheremsha.config.keyring_store as ks

    monkeypatch.setattr(ks, "get_password", store.get)
    monkeypatch.setattr(ks, "set_password", lambda k, v: store.__setitem__(k, v))
    monkeypatch.setattr(ks, "delete_password", lambda k: store.pop(k, None))
    return store


@pytest.fixture()
def qapplication():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def _auth(client=None, opened=None):
    return CheremshaAuthState(
        base_url="http://cloud.test",
        client=client or FakeCloudClient(),
        open_url=(opened.append if opened is not None else (lambda url: None)),
    )


async def _drive_callback(client: FakeCloudClient, grant: str = "grant-SECRET") -> None:
    """Simulate the system browser hitting the loopback callback server."""
    state = client.start_calls[-1]["state"]
    async with httpx.AsyncClient() as http:
        resp = await http.get(
            f"http://127.0.0.1:{cloud_constants.CALLBACK_PORT}{cloud_constants.CALLBACK_PATH}",
            params={"code": grant, "state": state},
        )
    assert resp.status_code == 200


# ---------------------------------------------------------------- client
def _transport(handler):
    return httpx.MockTransport(handler)


async def _test_client_shape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/auth/google/start"):
            return httpx.Response(200, json={"authorization_url": "https://x/auth", "state": "s"})
        if path.endswith("/desktop/exchange"):
            return httpx.Response(
                200,
                json={
                    "access_token": "a",
                    "refresh_token": "r",
                    "user": {"id": "u", "email": "e@x.io", "display_name": "n"},
                },
            )
        if path.endswith("/auth/me"):
            assert request.headers["authorization"].startswith("Bearer ")
            return httpx.Response(200, json={"id": "u", "email": "e@x.io", "display_name": "n"})
        if path.endswith("/platforms"):
            return httpx.Response(
                200,
                json={
                    "platforms": [
                        {"platform": "twitch", "connected": True, "username": "kodithecat"}
                    ]
                },
            )
        raise AssertionError(path)

    client = CheremshaCloudClient(
        "http://cloud.test", httpx.AsyncClient(transport=_transport(handler))
    )
    start = await client.login_start("google", code_challenge="c", desktop_state="s")
    assert start["authorization_url"] == "https://x/auth"
    tokens, user, _auto = await client.exchange_desktop_code(code="g", verifier="v")
    assert (tokens.access_token, user.email) == ("a", "e@x.io")
    assert (await client.get_me("a")).id == "u"
    platforms = await client.get_platforms("a")
    assert platforms[0].platform == "twitch" and platforms[0].connected is True
    await client.aclose()


@pytest.mark.asyncio()
async def test_cloud_client_shapes() -> None:
    await _test_client_shape()


@pytest.mark.asyncio()
async def test_cloud_client_http_error_maps() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "session revoked", "code": "unauthorized"})

    client = CheremshaCloudClient(
        "http://cloud.test", httpx.AsyncClient(transport=_transport(handler))
    )
    with pytest.raises(CloudApiError) as exc:
        await client.get_me("bad")
    assert exc.value.status == 401
    await client.aclose()


# ---------------------------------------------------------------- session store
def test_session_store_roundtrip(keyring_fake) -> None:
    assert load_session() is None
    save_session(
        CheremshaSession("a", "r", "u-1", "kodi@example.com", "kodi_the_cat", "http://x/a.png")
    )
    loaded = load_session()
    assert loaded is not None and loaded.access_token == "a" and loaded.email == "kodi@example.com"
    clear_session()
    assert load_session() is None


def test_session_store_rejects_malformed(keyring_fake) -> None:
    keyring_fake[cloud_constants.KEY_CHEREMSHA_SESSION] = "not-json{{{"
    assert load_session() is None
    keyring_fake[cloud_constants.KEY_CHEREMSHA_SESSION] = json.dumps({"nope": True})
    assert load_session() is None


# ---------------------------------------------------------------- state machine
@pytest.mark.asyncio()
async def test_login_success_flow(keyring_fake) -> None:
    opened: list[str] = []
    client = FakeCloudClient()
    client.platforms = [
        CloudPlatformStatus("twitch", True, username="kodithecat"),
        CloudPlatformStatus("kick", False),
    ]
    auth = _auth(client, opened)
    auth.login("twitch")
    await asyncio.sleep(0.2)
    assert auth.status == STATUS_AWAITING_CALLBACK
    assert opened == ["https://accounts.example/auth"]
    await _drive_callback(client)
    await asyncio.wait_for(auth._task, timeout=10)
    assert auth.status == STATUS_AUTHENTICATED
    assert auth.isAuthenticated is True
    assert auth.displayName == "kodi_the_cat" and auth.email == "kodi@example.com"
    assert auth.connectedPlatformCount == 1
    assert auth.platformStatus("twitch")["username"] == "kodithecat"
    # Session persisted without provider secrets anywhere near it.
    saved = load_session()
    assert saved is not None and saved.access_token == "tok-access-SECRET"


@pytest.mark.asyncio()
async def test_duplicate_login_ignored(keyring_fake) -> None:
    client = FakeCloudClient()
    auth = _auth(client)
    auth.login("google")
    auth.login("google")
    auth.login("twitch")
    await asyncio.sleep(0.2)
    assert len(client.start_calls) == 1
    auth.cancelLogin()
    await asyncio.sleep(0.2)
    assert auth.status == STATUS_LOGGED_OUT


@pytest.mark.asyncio()
async def test_callback_wrong_state_ignored(keyring_fake) -> None:
    client = FakeCloudClient()
    auth = _auth(client)
    auth.login("google")
    await asyncio.sleep(0.2)
    async with httpx.AsyncClient() as http:
        resp = await http.get(
            f"http://127.0.0.1:{cloud_constants.CALLBACK_PORT}{cloud_constants.CALLBACK_PATH}",
            params={"code": "evil-grant", "state": "attacker-state"},
        )
    assert resp.status_code == 200
    await asyncio.sleep(0.2)
    assert client.exchange_calls == []
    assert auth.status == STATUS_AWAITING_CALLBACK
    auth.cancelLogin()
    await asyncio.sleep(0.2)
    assert auth.status == STATUS_LOGGED_OUT


@pytest.mark.asyncio()
async def test_restore_valid_session(keyring_fake) -> None:
    save_session(CheremshaSession("tok-a", "tok-r", "u-1", "kodi@example.com", "kodi_the_cat"))
    auth = _auth(FakeCloudClient())
    await auth.restore_session()
    assert auth.status == STATUS_AUTHENTICATED
    assert auth.displayName == "kodi_the_cat"


@pytest.mark.asyncio()
async def test_restore_expired_clears_silently(keyring_fake) -> None:
    save_session(CheremshaSession("tok-old", "tok-old-r", "u-1", "kodi@example.com", "kodi"))
    client = FakeCloudClient()
    client.me_result = CloudApiError("gone", status=401)
    client.refresh_result = CloudApiError("bad", status=400)
    auth = _auth(client)
    await auth.restore_session()
    assert auth.status == STATUS_LOGGED_OUT
    assert auth.isAuthenticated is False
    assert load_session() is None


@pytest.mark.asyncio()
async def test_restore_refreshes_once(keyring_fake) -> None:
    save_session(CheremshaSession("tok-old", "tok-r", "u-1", "kodi@example.com", "kodi"))
    client = FakeCloudClient()
    calls = {"me": 0}

    async def flaky_me(token):  # type: ignore[no-untyped-def]
        calls["me"] += 1
        if calls["me"] == 1:
            raise CloudApiError("expired", status=401)
        return CloudUser("u-1", "kodi@example.com", "kodi_the_cat")

    client.get_me = flaky_me  # type: ignore[method-assign]
    auth = _auth(client)
    await auth.restore_session()
    assert auth.status == STATUS_AUTHENTICATED
    assert load_session() is not None and load_session().access_token == "tok-a2"


@pytest.mark.asyncio()
async def test_logout_clears_everything(keyring_fake) -> None:
    save_session(CheremshaSession("tok-a", "tok-r", "u-1", "kodi@example.com", "kodi"))
    client = FakeCloudClient()
    auth = _auth(client)
    await auth.restore_session()
    assert auth.status == STATUS_AUTHENTICATED
    auth.logout()
    await asyncio.wait_for(auth._task, timeout=10)
    assert auth.status == STATUS_LOGGED_OUT
    assert client.logged_out == 1
    assert load_session() is None


@pytest.mark.asyncio()
async def test_no_secrets_in_logs(keyring_fake, caplog) -> None:
    opened: list[str] = []
    client = FakeCloudClient()
    auth = _auth(client, opened)
    with caplog.at_level(logging.DEBUG, logger="stream_cheremsha"):
        auth.login("google")
        await asyncio.sleep(0.2)
        await _drive_callback(client, grant="grant-VERY-SECRET")
        await asyncio.wait_for(auth._task, timeout=10)
        await auth.restore_session()
    text = "\n".join(r.getMessage() for r in caplog.records)
    for secret in ("tok-access-SECRET", "tok-refresh-SECRET", "grant-VERY-SECRET"):
        assert secret not in text
    assert auth.status == STATUS_AUTHENTICATED


def test_pill_state_switching(qapplication, keyring_fake) -> None:
    from stream_cheremsha.ui.account_pill import AccountPill

    client = FakeCloudClient()
    auth = _auth(client)
    pill = AccountPill(auth, lambda key: key, lambda: None, lambda: None)
    assert "cloud.login" in pill._name.text()
    auth._store_session(
        "a",
        "r",
        CloudUser("u-1", "kodi@example.com", "kodi_the_cat"),
    )
    auth._set_status(STATUS_AUTHENTICATED)
    assert pill._name.text() == "kodi_the_cat"
    assert "cloud.account" in pill._sub.text()
    auth._set_status(STATUS_LOGGED_OUT)
    assert "cloud.login" in pill._name.text()


@pytest.mark.asyncio()
async def test_login_twitch_auto_connect_persists_platform_enabled(
    qapplication, keyring_fake
) -> None:
    """When the same-transaction OAuth fully satisfied the platform
    scopes, the auto-connect callback must flip the platform_enabled
    QSettings key to True + record an init sentinel so the Platform
    Connection Manager's reconcile loop will start TwitchSource via
    the runtime broker on the next tick."""
    client = FakeCloudClient()

    # Switch exchange into "auto-connect succeeded for twitch"
    async def exchange_connected(*, code, verifier):  # type: ignore[no-untyped-def]
        client.exchange_calls.append({"code": code, "verifier": verifier})
        return (
            CloudSessionTokens("tok-access", "tok-refresh", 900),
            CloudUser("u-1", "kodi@example.com", "kodi_the_cat"),
            CloudAutoConnectOutcome(
                platform="twitch",
                connected=True,
                missing=(),
                reauth_required=False,
            ),
        )

    client.exchange_desktop_code = exchange_connected  # type: ignore[assignment]

    # Compose per-platform enabled store that mirrors what
    # ``_write_platform_local_enabled`` does on disk.
    enabled: dict[str, bool] = {}
    init: dict[str, bool] = {}

    def on_auto_connected(outcome: CloudAutoConnectOutcome) -> None:
        plat = outcome.platform
        if plat and outcome.connected:
            enabled[plat] = True
            init[plat] = True

    def on_auto_reauth_required(_: CloudAutoConnectOutcome) -> None:
        return None

    auth = CheremshaAuthState(
        base_url="http://cloud.test",
        client=client,
        open_url=lambda _u: None,
        on_auto_connected=on_auto_connected,
        on_auto_reauth_required=on_auto_reauth_required,
    )
    # Drive login → exchange → status push to the auto_connected
    # callback.
    import stream_cheremsha.cloud.auth_state as astate

    real_class = astate.DesktopCallbackServer

    class _FakeServer:
        def __init__(self, *a, **kw) -> None:
            pass

        async def start(self) -> None:
            return None

        async def wait_for_callback(self, **kw) -> tuple[str, str]:
            return ("grant-1", "desktop-state-1")

        async def stop(self) -> None:
            return None

    astate.DesktopCallbackServer = _FakeServer  # type: ignore[assignment]
    try:
        auth.open_url = lambda url: None  # type: ignore[assignment]
        await auth._login_flow("twitch")  # noqa: SLF001
        assert enabled.get("twitch") is True
        assert init.get("twitch") is True
    finally:
        astate.DesktopCallbackServer = real_class


@pytest.mark.asyncio()
async def test_login_twitch_partial_scopes_emits_reauth_without_persisting(
    qapplication, keyring_fake
) -> None:
    """When granted scopes are missing some platform scope, the
    on_auto_connected flap does NOT fire (no fake enabled=True). The
    on_auto_reauth_required hook fires."""
    client = FakeCloudClient()

    async def exchange_partial(*, code, verifier):  # type: ignore[no-untyped-def]
        client.exchange_calls.append({"code": code, "verifier": verifier})
        return (
            CloudSessionTokens("tok-access", "tok-refresh", 900),
            CloudUser("u-1", "kodi@example.com", "kodi_the_cat"),
            CloudAutoConnectOutcome(
                platform="twitch",
                connected=False,
                missing=("channel:read:subscriptions",),
                reauth_required=True,
            ),
        )

    client.exchange_desktop_code = exchange_partial  # type: ignore[assignment]

    enabled: dict[str, bool] = {}
    reauth: list[str] = []

    def on_connected(_: CloudAutoConnectOutcome) -> None:
        enabled["twitch"] = True  # MUST NOT fire

    def on_reauth(outcome: CloudAutoConnectOutcome) -> None:
        reauth.append(outcome.platform or "")

    auth = CheremshaAuthState(
        base_url="http://cloud.test",
        client=client,
        open_url=lambda _u: None,
        on_auto_connected=on_connected,
        on_auto_reauth_required=on_reauth,
    )

    import stream_cheremsha.cloud.auth_state as astate

    real_class = astate.DesktopCallbackServer

    class _FakeServer:
        def __init__(self, *a, **kw) -> None:
            pass

        async def start(self) -> None:
            return None

        async def wait_for_callback(self, **kw) -> tuple[str, str]:
            return ("grant-1", "desktop-state-1")

        async def stop(self) -> None:
            return None

    astate.DesktopCallbackServer = _FakeServer  # type: ignore[assignment]
    try:
        await auth._login_flow("twitch")  # noqa: SLF001
        assert "twitch" not in enabled or enabled["twitch"] is False
        assert "twitch" in reauth
    finally:
        astate.DesktopCallbackServer = real_class

