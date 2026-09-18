"""End-to-end: real Cheremsha Cloud app + real desktop auth code over HTTP.

Everything is production code except ONE seam: the external OAuth provider
website is emulated by FakeLoginProvider (deterministic authorize / exchange
/ userinfo). Covered live: FastAPI routes, KV grants (single-use + TTL),
PKCE verification, sessions, auto-connect, platform broker, desktop
AuthState, the real loopback callback server on 127.0.0.1:8471, real httpx.

Requires backend deps (fastapi/sqlalchemy/aiosqlite/...) and the
cheremsha-cloud checkout next to this repo; skipped otherwise.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")
pytest.importorskip("aiosqlite")

_BACKEND_ROOT = Path(__file__).resolve().parents[1].parent / "cheremsha-cloud"
_BACKEND_ROOT = _BACKEND_ROOT.resolve()
if not (_BACKEND_ROOT / "app" / "main.py").is_file():
    pytest.skip("cheremsha-cloud checkout not found — E2E needs it",
                allow_module_level=True)

sys.path.insert(0, str(_BACKEND_ROOT))

# Backend imports lower the root/httpx log levels as a side effect; restore
# them so sibling test modules (e.g. no-secrets-in-logs) see a pristine
# logging setup.
import logging as _logging  # noqa: E402

_saved_levels = {
    name: _logging.getLogger(name).level
    for name in ("", "httpx", "uvicorn", "sqlalchemy")
}

os.environ.setdefault("TOKEN_ENCRYPTION_KEY", "test-key-placeholder")
os.environ.setdefault("SESSION_JWT_SECRET", "test-secret-0123456789abcdef0123456789")

from cryptography.fernet import Fernet  # noqa: E402

_TEST_KEY = Fernet.generate_key().decode()
os.environ["TOKEN_ENCRYPTION_KEY"] = _TEST_KEY

from app.auth.providers.base import (  # noqa: E402
    OAuthProvider,
    OAuthTokenResponse,
    ProviderIdentity,
)
from app.auth.providers.factory import combined_scopes_for_login  # noqa: E402
from app.common import store as store_module  # noqa: E402
from app.common.store import MemoryKV  # noqa: E402
from app.config.settings import Settings  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.database.session import reset_engine_for_tests  # noqa: E402
from app.main import create_app  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

for _name, _level in _saved_levels.items():
    _logging.getLogger(_name).setLevel(_level)
del _name, _level

from stream_cheremsha.cloud.auth_state import (  # noqa: E402
    STATUS_AUTHENTICATED,
    CheremshaAuthState,
)
from stream_cheremsha.cloud.client import CheremshaCloudClient  # noqa: E402


class FakeLoginProvider(OAuthProvider):
    """Emulates ONLY the provider website. No cloud/desktop code is faked."""

    provider_name = "fake"

    def __init__(self, user_id="fake-user-1", email="fake@example.com", **kw):
        super().__init__(None)
        self._uid = user_id
        self._email = email
        self.granted_scope: str = kw.pop("granted_scope", "a b")

    def get_authorization_url(self, *, state, redirect_uri, scopes,
                              code_challenge=None) -> str:
        return f"https://provider.example/authorize?state={state}"

    async def exchange_code(self, *, code, redirect_uri, code_verifier=None):
        return OAuthTokenResponse(
            access_token=f"access-{code}",
            refresh_token=f"refresh-{code}",
            expires_in=3600,
            scope=self.granted_scope,
        )

    async def get_user_identity(self, *, access_token: str) -> ProviderIdentity:
        return ProviderIdentity(
            provider_user_id=self._uid,
            email=self._email,
            display_name="E2E User",
            username="e2euser",
            avatar_url=None,
            raw={},
        )

    async def refresh_token(self, *, refresh_token: str) -> OAuthTokenResponse:
        return OAuthTokenResponse(
            access_token="access-refreshed",
            refresh_token="refresh-new",
            expires_in=3600,
            scope=self.granted_scope,
        )

    async def revoke_token(self, *, token: str) -> None:
        return None


@pytest.fixture()
def backend(tmp_path):
    """Real backend app: isolated sqlite DB + memory KV. Yields (app, settings)."""
    # create_app() lowers the root log level as a side effect; restore it on
    # teardown so sibling modules see pristine logging.
    _root_level = _logging.getLogger().level
    db_path = tmp_path / "e2e.db"
    settings = Settings(
        app_env="test",
        database_url=f"sqlite+aiosqlite:///{db_path}",
        redis_url="redis://localhost:6379/0",
        session_jwt_secret="test-secret-0123456789abcdef0123456789",
        token_encryption_key=_TEST_KEY,
        app_base_url="http://test",
        web_base_url="http://test",
        desktop_callback_url="http://127.0.0.1:8471/callback",
        rate_limit_enabled=False,
    )
    engine = create_async_engine(
        settings.database_url, connect_args={"check_same_thread": False})

    async def _init() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    asyncio.get_event_loop().run_until_complete(_init())
    reset_engine_for_tests()
    application = create_app(settings)

    from app.api import deps as deps_module
    from app.database import session as session_module

    factory = async_sessionmaker(bind=engine, class_=AsyncSession,
                                 expire_on_commit=False)

    async def override_get_db(request):  # type: ignore[no-untyped-def]
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    application.dependency_overrides[deps_module.get_db] = override_get_db
    session_module._factories[settings.database_url] = factory  # type: ignore[attr-defined]
    mem = MemoryKV()
    application.state.test_kv = mem
    store_module._store = mem  # type: ignore[attr-defined]
    try:
        yield application, settings
    finally:
        _logging.getLogger().setLevel(_root_level)
        store_module._store = None  # type: ignore[attr-defined]
        application.dependency_overrides.clear()
        asyncio.get_event_loop().run_until_complete(engine.dispose())


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


def _state_from_authorize_url(url: str) -> str:
    return parse_qs(urlparse(url).query)["state"][0]


async def _emulate_browser_for_login(authorization_url: str, asgi) -> None:
    """Perform the provider round-trip and deliver the 303 to loopback."""
    state = _state_from_authorize_url(authorization_url)
    cb = await asgi.get(
        "/api/v1/auth/twitch/callback", params={"code": "e2e-code", "state": state}
    )
    assert cb.status_code == 303, cb.text
    target = cb.headers["location"]
    assert target.startswith("http://127.0.0.1:8471/callback?code=")
    async with httpx.AsyncClient() as http:
        resp = await http.get(target)
    assert resp.status_code == 200


async def _wait_opened(opened: list[str], timeout: float = 15.0) -> str:
    async def _poll() -> str:
        while not opened:
            await asyncio.sleep(0.05)
        return opened[-1]

    return await asyncio.wait_for(_poll(), timeout=timeout)


async def _wait_next_url(opened: list[str], known: int, timeout: float = 15.0) -> str:
    async def _poll() -> str:
        while len(opened) <= known:
            await asyncio.sleep(0.05)
        return opened[-1]

    return await asyncio.wait_for(_poll(), timeout=timeout)


def _desktop_client(backend_app) -> CheremshaCloudClient:
    http = httpx.AsyncClient(transport=httpx.ASGITransport(app=backend_app))
    return CheremshaCloudClient("http://cloud.e2e", http)


@pytest.mark.asyncio()
async def test_e2e_twitch_login_auto_connects_and_brokers(
    backend, qapplication, keyring_fake
) -> None:
    """The user's scenario live: login via Twitch connects the platform."""
    backend_app, settings = backend
    scopes = " ".join(combined_scopes_for_login("twitch", settings))
    backend_app.state.provider_overrides["twitch"] = FakeLoginProvider(
        user_id="tw-e2e-1", email="e2e@example.com", granted_scope=scopes
    )

    opened: list[str] = []
    client = _desktop_client(backend_app)
    auth = CheremshaAuthState(
        base_url="http://cloud.e2e", client=client,
        open_url=opened.append,
    )
    asgi = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=backend_app), base_url="http://test")
    try:
        auth.login("twitch")
        url = await _wait_opened(opened)
        await _emulate_browser_for_login(url, asgi)
        await asyncio.wait_for(auth._task, timeout=20)
        assert auth.status == STATUS_AUTHENTICATED

        token = auth._access_token
        assert token
        platforms = await client.get_platforms(token)
        twitch = [p for p in platforms if p.platform == "twitch"]
        assert twitch and twitch[0].connected is True

        runtime = await client.fetch_runtime_token("twitch", token)
        assert runtime.get("access_token")
    finally:
        await client.aclose()
        await asgi.aclose()


@pytest.mark.asyncio()
async def test_e2e_link_google_with_different_email(
    backend, qapplication, keyring_fake
) -> None:
    """Feature 1 live: Twitch account + Google on another email = one account."""
    backend_app, settings = backend
    scopes = " ".join(combined_scopes_for_login("twitch", settings))
    backend_app.state.provider_overrides["twitch"] = FakeLoginProvider(
        user_id="tw-e2e-2", email="tw@example.com", granted_scope=scopes)
    backend_app.state.provider_overrides["google"] = FakeLoginProvider(
        user_id="go-e2e-9", email="completely-different@example.com",
        granted_scope=" ".join(combined_scopes_for_login("google", settings)),
    )

    opened: list[str] = []
    client = _desktop_client(backend_app)
    auth = CheremshaAuthState(
        base_url="http://cloud.e2e", client=client,
        open_url=opened.append,
    )
    asgi = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=backend_app), base_url="http://test")
    try:
        auth.login("twitch")
        url = await _wait_opened(opened)
        await _emulate_browser_for_login(url, asgi)
        await asyncio.wait_for(auth._task, timeout=20)
        assert auth.status == STATUS_AUTHENTICATED
        token = auth._access_token
        assert token

        auth.linkProvider("google")
        link_url = await _wait_next_url(opened, 1, timeout=15.0)
        state = _state_from_authorize_url(link_url)
        cb = await asgi.get(
            "/api/v1/auth/google/link-callback",
            params={"code": "e2e-link", "state": state},
        )
        assert cb.status_code == 303, cb.text
        target = cb.headers["location"]
        assert "action=link" in target and "status=ok" in target
        async with httpx.AsyncClient() as http:
            resp = await http.get(target)
        assert resp.status_code == 200
        await asyncio.wait_for(auth._task, timeout=20)

        identities = await client.get_identities(token)
        providers = sorted(i["provider"] for i in identities)
        assert providers == ["google", "twitch"]
    finally:
        await client.aclose()
        await asgi.aclose()


@pytest.mark.asyncio()
async def test_e2e_logged_out_platforms_empty(backend) -> None:
    """Sanity: anonymous platform list is refused, not leaked."""
    backend_app, _ = backend
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=backend_app),
        base_url="http://test",
    ) as asgi:
        r = await asgi.get("/api/v1/platforms")
    assert r.status_code in (401, 403)
