# Link + two-way connect (desktop) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire provider linking and two-way platform auto-connect into the desktop app per the spec.

**Architecture:** Four thin client methods, two extra armed futures on the loopback server, two new `AuthState` slots with a pending-platform field, pill + connections-tab UI on top; reconcile loop untouched.

**Tech Stack:** PySide6, qasync/asyncio, httpx, pytest + pytest-asyncio, ruff.

**Spec:** `docs/superpowers/specs/2026-09-17-cloud-account-linking-design.md` (sections 2, 5, 6, 7).

**Prerequisite:** The oauth stash is applied in this working tree (uncommitted `cloud/`, `sync/`, `account_pill.py`); run every command from the stream-cheremsha repo root with `.venv/bin/python -m`.

## Global Constraints

- Loopback callback never carries secrets and decides nothing: trigger only; authoritative state always comes from `GET /platforms`, `GET /account/identities`, `GET /auth/me`.
- `LOGIN_WAIT_TIMEOUT_S` (600s) for all waits; `access_log=None` stays.
- No secret ever reaches logs/QML (existing `client._request` + `caplog` test convention).
- Local panels stay as cloud-unreachable fallback.

---

### Task 1: Client methods (`link_start`, `platform_connect_start`, identities)

**Files:**
- Modify: `src/stream_cheremsha/cloud/client.py` (append after `logout`, ~line 191)
- Test: `tests/test_cloud_auth.py` (append; reuse `_transport` + `keyring_fake`/`qapplication` fixtures)

**Interfaces:**
- Consumes: `_get`, `_post`, new `_delete` helper wrapping `_request("DELETE", …)`.
- Produces: `link_start(provider, token) → dict`, `platform_connect_start(platform, token) → dict`, `get_identities(token) → list[dict]`, `unlink_identity(identity_id, token) → None` (used by Tasks 3–5).

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.asyncio()
async def test_cloud_client_link_and_platform_connect_shapes() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/auth/twitch/link-start"):
            assert request.headers["authorization"].startswith("Bearer ")
            return httpx.Response(200, json={"authorization_url": "https://x/link", "state": "s"})
        if path.endswith("/platforms/youtube/connect"):
            assert request.url.params.get("mode") == "desktop"
            return httpx.Response(200, json={"authorization_url": "https://x/connect", "state": "s"})
        if path.endswith("/account/identities"):
            return httpx.Response(200, json=[
                {"id": "i-1", "provider": "google", "provider_email": "a@example.com"}])
        raise AssertionError(path)

    client = CheremshaCloudClient(
        "http://cloud.test", httpx.AsyncClient(transport=_transport(handler)))
    start = await client.link_start("twitch", "tok")
    assert start["authorization_url"] == "https://x/link"
    conn = await client.platform_connect_start("youtube", "tok")
    assert conn["authorization_url"] == "https://x/connect"
    ids = await client.get_identities("tok")
    assert ids[0]["provider"] == "google"
    await client.aclose()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_cloud_auth.py::test_cloud_client_link_and_platform_connect_shapes -v`
Expected: FAIL with AttributeError.

- [ ] **Step 3: Write minimal implementation**

```python
async def _delete(self, path: str, token: str | None) -> Any:
    return await self._request("DELETE", path, token=token)

async def link_start(self, provider: str, access_token: str) -> dict[str, Any]:
    body = await self._get(f"/api/v1/auth/{provider}/link-start", token=access_token)
    if not isinstance(body, dict) or not body.get("authorization_url"):
        raise CloudApiError("cloud link start has no authorization URL")
    return body

async def platform_connect_start(self, platform: str, access_token: str) -> dict[str, Any]:
    body = await self._post(
        f"/api/v1/platforms/{platform}/connect?mode=desktop",
        token=access_token, payload={})
    if not isinstance(body, dict) or not body.get("authorization_url"):
        raise CloudApiError("cloud connect start has no authorization URL")
    return body

async def get_identities(self, access_token: str) -> list[dict[str, Any]]:
    body = await self._get("/api/v1/account/identities", token=access_token)
    return [i for i in body] if isinstance(body, list) else []

async def unlink_identity(self, identity_id: str, access_token: str) -> None:
    await self._delete(f"/api/v1/account/identities/{identity_id}", token=access_token)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_cloud_auth.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/stream_cheremsha/cloud/client.py tests/test_cloud_auth.py
git commit -m "feat: cloud client link/connect/identities methods"
```

---

### Task 2: Loopback contract (platform + link futures)

**Files:**
- Modify: `src/stream_cheremsha/cloud/callback.py`
- Test: `tests/test_cloud_auth.py` (append)

**Interfaces:**
- Consumes: `constants.CALLBACK_PATH/PORT/HOST`, `LOGIN_WAIT_TIMEOUT_S`.
- Produces: `wait_for_platform(platform, timeout) → {platform, status}`, `wait_for_link(timeout) → {provider, status}` (used by Tasks 3–4).

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.asyncio()
async def test_callback_server_platform_and_link_triggers() -> None:
    from stream_cheremsha.cloud.callback import DesktopCallbackServer

    server = DesktopCallbackServer(expected_state="ds-1")
    await server.start()
    try:
        async with httpx.AsyncClient() as http:
            # Unarmed hits are ignored, never resolve anything.
            r = await http.get(
                f"http://127.0.0.1:{cloud_constants.CALLBACK_PORT}{cloud_constants.CALLBACK_PATH}",
                params={"platform": "twitch", "status": "connected"})
            assert r.status_code == 200
            waiter = server.wait_for_platform(platform="twitch", timeout=5)
            r = await http.get(
                f"http://127.0.0.1:{cloud_constants.CALLBACK_PORT}{cloud_constants.CALLBACK_PATH}",
                params={"platform": "twitch", "status": "connected"})
            assert r.status_code == 200
            assert await waiter == {"platform": "twitch", "status": "connected"}
            link_waiter = server.wait_for_link(timeout=5)
            r = await http.get(
                f"http://127.0.0.1:{cloud_constants.CALLBACK_PORT}{cloud_constants.CALLBACK_PATH}",
                params={"action": "link", "provider": "google", "status": "conflict"})
            assert r.status_code == 200
            assert await link_waiter == {"provider": "google", "status": "conflict"}
    finally:
        await server.stop()
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_cloud_auth.py::test_callback_server_platform_and_link_triggers -v`
Expected: FAIL (no such methods).

- [ ] **Step 3: Write minimal implementation**

Add to `DesktopCallbackServer.__init__`: `self._platform_future = None`,
`self._platform_name = ""`, `self._link_future = None`. In `start()`, create
both futures alongside `self._future`. Extend `_callback`:

```python
query_platform = str(req.query.get("platform") or "")
query_status = str(req.query.get("status") or "")
pfut = self._platform_future
if (pfut is not None and not pfut.done() and query_platform
        and query_platform == self._platform_name and query_status):
    pfut.set_result({"platform": query_platform, "status": query_status})
    return web.Response(text="<h1>Cheremsha</h1><p>Це вікно можна закрити.</p>",
                        content_type="text/html")
if (req.query.get("action") == "link" and self._link_future is not None
        and not self._link_future.done()
        and str(req.query.get("provider") or "")):
    self._link_future.set_result({
        "provider": str(req.query.get("provider")),
        "status": str(req.query.get("status") or "")})
    return web.Response(text="<h1>Cheremsha</h1><p>Це вікно можна закрити.</p>",
                        content_type="text/html")
```

Add methods (mirror `wait_for_callback`/`cancel`/`stop` for the new futures):

```python
def wait_for_platform(self, *, platform: str, timeout: float = constants.LOGIN_WAIT_TIMEOUT_S):
    self._platform_name = (platform or "").strip().lower()
    if self._platform_future is None:
        raise RuntimeError("callback server not started")
    return asyncio.wait_for(self._platform_future, timeout=timeout)

def wait_for_link(self, *, timeout: float = constants.LOGIN_WAIT_TIMEOUT_S):
    if self._link_future is None:
        raise RuntimeError("callback server not started")
    return asyncio.wait_for(self._link_future, timeout=timeout)
```

Extend `cancel()` (cancel all three futures) and `stop()` (clear all three).

- [ ] **Step 4: Run to verify**

Run: `.venv/bin/python -m pytest tests/test_cloud_auth.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/stream_cheremsha/cloud/callback.py tests/test_cloud_auth.py
git commit -m "feat: loopback platform/link trigger futures"
```

---

### Task 3: `linkProvider` slot + identities cache

**Files:**
- Modify: `src/stream_cheremsha/cloud/auth_state.py`
- Test: `tests/test_cloud_auth.py` (append; extend `FakeCloudClient` with `link_start`/`get_identities`/`unlink_identity` scriptable doubles)

**Interfaces:**
- Consumes: Task 1 client methods, Task 2 `wait_for_link`.
- Produces: `linkProvider(provider)` slot, `identitiesChanged` signal, `identities` cache (used by Task 5 pill UI).

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.asyncio()
async def test_link_provider_conflict_emits_notice(qapplication, keyring_fake) -> None:
    import stream_cheremsha.cloud.auth_state as astate

    client = FakeCloudClient()
    opened: list[str] = []
    notices: list[str] = []

    async def fake_link_start(provider, access_token):
        return {"authorization_url": "https://x/link"}

    async def fake_identities(access_token):
        return [{"provider": "google", "provider_email": "a@example.com"}]

    client.link_start = fake_link_start  # type: ignore[assignment]
    client.get_identities = fake_identities  # type: ignore[assignment]
    auth = _auth(client, opened)
    auth.notice.connect(notices.append)
    auth._store_session("a", "r", CloudUser("u-1", "a@example.com", "u"))
    auth._set_status(STATUS_AUTHENTICATED)

    real_class = astate.DesktopCallbackServer

    class _FakeLinkServer:
        def __init__(self, *a, **kw) -> None:
            pass

        async def start(self) -> None:
            return None

        async def wait_for_link(self, **kw) -> dict:
            return {"provider": "twitch", "status": "conflict"}

        async def stop(self) -> None:
            return None

    astate.DesktopCallbackServer = _FakeLinkServer  # type: ignore[assignment]
    try:
        auth.linkProvider("twitch")
        await asyncio.wait_for(auth._task, timeout=10)
        assert notices == ["link-conflict"]
    finally:
        astate.DesktopCallbackServer = real_class
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_cloud_auth.py::test_link_provider_conflict_emits_notice -v`
Expected: FAIL (no `linkProvider` slot).

- [ ] **Step 3: Write minimal implementation**

```python
identitiesChanged = Signal()

# in __init__:
self._identities: list[dict[str, Any]] = []

@Slot(str)
def linkProvider(self, provider: str) -> None:
    provider = (provider or "").strip().lower()
    if provider not in constants.LOGIN_PROVIDERS:
        return
    if self._status != STATUS_AUTHENTICATED or not self._access_token:
        return
    self._launch(lambda: self._link_flow(provider), name="cheremsha-link")

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
```

Call `_refresh_identities` after `_sync_platforms_and_avatar` in `restore_session` and `_login_flow` (two one-line additions).

- [ ] **Step 4: Run to verify**

Run: `.venv/bin/python -m pytest tests/test_cloud_auth.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/stream_cheremsha/cloud/auth_state.py tests/test_cloud_auth.py
git commit -m "feat: linkProvider flow with conflict notice"
```

---

### Task 4: `connectPlatform` slot (two-way connect)

**Files:**
- Modify: `src/stream_cheremsha/cloud/auth_state.py`
- Test: `tests/test_cloud_auth.py` (append)

**Interfaces:**
- Consumes: Task 1 `platform_connect_start`, Task 2 `wait_for_platform`, existing `login()` + auto-connect callbacks.
- Produces: `connectPlatform(platform)` slot + `_pending_platform` (used by Task 5 connections tab).

Mapping (exact): `{"twitch": "twitch", "tiktok": "tiktok", "kick": "kick", "youtube": "google"}`.

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.asyncio()
async def test_connect_platform_logged_out_triggers_login(qapplication, keyring_fake) -> None:
    client = FakeCloudClient()
    opened: list[str] = []
    auth = _auth(client, opened)
    auth.connectPlatform("twitch")
    await asyncio.sleep(0.2)
    assert client.start_calls and client.start_calls[-1]["provider"] == "twitch"
    assert auth._pending_platform == "twitch"  # noqa: SLF001
    auth.cancelLogin()


@pytest.mark.asyncio()
async def test_connect_platform_logged_in_unreachable_emits_notice(
    qapplication, keyring_fake
) -> None:
    client = FakeCloudClient()
    opened: list[str] = []
    notices: list[str] = []

    async def boom(platform, access_token):
        raise CloudApiError("down")

    client.platform_connect_start = boom  # type: ignore[assignment]
    auth = _auth(client, opened)
    auth.notice.connect(notices.append)
    auth._store_session("a", "r", CloudUser("u-1", "a@example.com", "u"))
    auth._set_status(STATUS_AUTHENTICATED)
    auth.connectPlatform("kick")
    await asyncio.wait_for(auth._task, timeout=10)
    assert notices == ["unreachable"]
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_cloud_auth.py -k "connect_platform" -v`
Expected: FAIL (no `connectPlatform`, no `_pending_platform`).

- [ ] **Step 3: Write minimal implementation**

```python
_CONNECT_LOGIN_MAP = {"twitch": "twitch", "tiktok": "tiktok",
                      "kick": "kick", "youtube": "google"}

# in __init__:
self._pending_platform: str | None = None

@Slot(str)
def connectPlatform(self, platform: str) -> None:
    platform = (platform or "").strip().lower()
    if platform not in ("twitch", "tiktok", "kick", "youtube"):
        return
    if self._status != STATUS_AUTHENTICATED or not self._access_token:
        self._pending_platform = platform
        self.login(_CONNECT_LOGIN_MAP[platform])
        return
    self._launch(lambda: self._platform_connect_flow(platform),
                 name="cheremsha-connect")

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
                platform, self._access_token or "")
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
```

In `_login_flow`, after `_set_status(STATUS_AUTHENTICATED)`: if
`self._pending_platform == "youtube"` → clear it and `await
self._platform_connect_flow("youtube")`; else clear `_pending_platform`
(twitch/tiktok/kick arrive via auto-connect + reconcile). In `logout()` and
`cancelLogin()` paths the pending value is cleared (`_logout_flow` start +
`cancelLogin` body, one line each).

- [ ] **Step 4: Add logout-during-pending test, run all green**

```python
@pytest.mark.asyncio()
async def test_logout_during_link_converges_logged_out(qapplication, keyring_fake) -> None:
    import stream_cheremsha.cloud.auth_state as astate

    client = FakeCloudClient()
    opened: list[str] = []
    auth = _auth(client, opened)
    auth._store_session("a", "r", CloudUser("u-1", "a@example.com", "u"))
    auth._set_status(STATUS_AUTHENTICATED)

    real_class = astate.DesktopCallbackServer

    class _HangingServer:
        def __init__(self, *a, **kw) -> None:
            pass

        async def start(self) -> None:
            return None

        async def wait_for_link(self, **kw) -> dict:
            await asyncio.sleep(60)
            return {}

        async def stop(self) -> None:
            return None

    astate.DesktopCallbackServer = _HangingServer  # type: ignore[assignment]
    try:
        auth.linkProvider("twitch")
        await asyncio.sleep(0.2)
        assert auth._task is not None and not auth._task.done()
        auth.logout()
        await asyncio.wait_for(auth._task, timeout=10)
        assert auth.status == STATUS_LOGGED_OUT
        assert load_session() is None
    finally:
        astate.DesktopCallbackServer = real_class
```

Run: `.venv/bin/python -m pytest tests/test_cloud_auth.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/stream_cheremsha/cloud/auth_state.py tests/test_cloud_auth.py
git commit -m "feat: connectPlatform two-way flow with pending youtube"
```

---

### Task 5: Pill identities UI + connections routing + l10n

**Files:**
- Modify: `src/stream_cheremsha/ui/account_pill.py`, `src/stream_cheremsha/ui/main_window.py` (connections buttons → `connectPlatform`; `unreachable` → reveal local panel), `src/stream_cheremsha/l10n.py`
- Test: `tests/test_cloud_auth.py` (pill identities render test, QApplication pattern)

**Interfaces:**
- Consumes: Task 3 `identitiesChanged`/`_identities`, Task 4 `connectPlatform`.
- Produces: visible UI (verified by Task 6 QA matrix).

- [ ] **Step 1: Write the failing test**

```python
def test_pill_shows_identities_and_link_actions(qapplication, keyring_fake) -> None:
    from stream_cheremsha.ui.account_pill import AccountPill

    client = FakeCloudClient()
    auth = _auth(client)
    pill = AccountPill(auth, lambda key: key, lambda: None, lambda: None)
    auth._store_session("a", "r", CloudUser("u-1", "a@example.com", "u"))
    auth._identities = [{"provider": "google", "provider_email": "a@example.com"}]  # noqa: SLF001
    auth._set_status(STATUS_AUTHENTICATED)
    menu_actions = [a.text() for a in pill._account_menu_actions()]
    assert any("google" in t for t in menu_actions)
    assert any("twitch" in t.lower() for t in menu_actions)
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_cloud_auth.py::test_pill_shows_identities_and_link_actions -v`
Expected: FAIL (no `_account_menu_actions`).

- [ ] **Step 3: Write minimal implementation**

`account_pill.py`: connect `auth.identitiesChanged` to `_refresh`; split
`_show_account_menu` so identities rows are built by `_account_menu_actions()`
returning `list[QAction]`-describing texts: one disabled row per linked
identity (`f"{provider} · {email}"`) with an `«unlink»` action calling
`client.unlink_identity` via auth (add `unlinkIdentity(identity_id)` slot on
auth reusing `_launch` + `_refresh_identities`), plus one action per missing
`LOGIN_PROVIDERS` entry calling `auth.linkProvider(p)`.
`l10n.py`: add `cloud.link_provider` (`Увійти щоб під'єднати {provider}` /
`Sign in to link {provider}`), `cloud.unlink`, `cloud.link_conflict`
(`Цей акаунт вже прив'язано до іншого Cheremsha-акаунта` /
`This account is already linked to another Cheremsha account`),
`cloud.signed_in_as` (`Увійшли як {name}, {platform} під'єднано` /
`Signed in as {name}, {platform} connected`).
`main_window.py`: route each platform transport/connect button handler to
`self._cloud_auth.connectPlatform("<p>")` first; extend `_on_cloud_notice`
with `"link-conflict"` and keep `"unreachable"` revealing the local panel.

- [ ] **Step 4: Run to verify**

Run: `.venv/bin/python -m pytest tests/test_cloud_auth.py tests/test_platform_manager.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/stream_cheremsha/ui/account_pill.py src/stream_cheremsha/ui/main_window.py src/stream_cheremsha/l10n.py tests/test_cloud_auth.py
git commit -m "feat: identities UI and cloud-first connections routing"
```

---

### Task 6: Full verification + QA matrix

- [ ] **Step 1: Run desktop suites**

Run: `.venv/bin/python -m pytest tests/test_cloud_auth.py tests/test_cloud_sync.py tests/test_platform_manager.py tests/test_build_nuitka_embedded.py tests/test_widget_instances.py -q`
Expected: all green.

- [ ] **Step 2: Run lint**

Run: `.venv/bin/python -m ruff check src/stream_cheremsha/cloud src/stream_cheremsha/sync src/stream_cheremsha/ui/account_pill.py src/stream_cheremsha/config/embedded.py src/stream_cheremsha/build_nuitka.py`
Expected: clean.

- [ ] **Step 3: Manual QA** (spec §8): providers {google, twitch, tiktok, kick} × {logged out, logged in} for link; platforms {twitch, youtube, tiktok, kick} × {logged out, logged in, cloud-down} for connect; unlink down to one identity; email-mismatch link; replay of a used link URL against a dev backend.
