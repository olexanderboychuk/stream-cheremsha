# Link endpoints (backend) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add authenticated provider-linking endpoints to cheremsha-cloud so a logged-in user can attach a second login provider to the same account.

**Architecture:** Two thin routes in `app/api/v1/auth.py` reusing the login KV-state + provider-override patterns; attach logic reuses `find_or_create_user_from_identity` semantics via direct `AuthIdentity` handling (email ignored on attach).

**Tech Stack:** FastAPI, SQLAlchemy async, MemoryKV in tests, pytest + pytest-asyncio, httpx ASGI transport.

**Spec:** `docs/superpowers/specs/2026-09-17-cloud-account-linking-design.md` (sections 2, 4.1). Note: the spec file lives in the stream-cheremsha repo; all paths below are in cheremsha-cloud.

**Prerequisite:** Run every command from the cheremsha-cloud repo root.

## Global Constraints

- No new DB migrations; `AuthIdentity` + KV state only.
- No `login-and-connect` endpoint.
- Link state is single-use with `oauth_state_ttl_seconds` TTL (replay → 400).
- Foreign identity → 409, never attach to another user.
- No secret logging (log provider + mode only).

---

### Task 1: `GET /auth/{provider}/link-start`

**Files:**
- Modify: `app/api/v1/auth.py` (append link section after desktop exchange, ~line 444)
- Test: `tests/test_account_link.py` (new file)

**Interfaces:**
- Consumes: `CurrentUser` (deps), `oauth_state_key`, `generate_state`, `get_login_provider`, `combined_scopes_for_login`, `AuthStartOut`.
- Produces: `GET /auth/{provider}/link-start → AuthStartOut` (used by Task 2 and the desktop plan).

- [ ] **Step 1: Write the failing test**

```python
"""Linking a second login provider (authenticated)."""

from __future__ import annotations

from tests.conftest import FakeLoginProvider, login_headers


async def test_link_start_requires_session(client, app):
    r = await client.get("/api/v1/auth/google/link-start")
    assert r.status_code == 401


async def test_link_start_unknown_provider_404(client, app):
    headers = await login_headers(client, app, "google", FakeLoginProvider(email="a@example.com"))
    r = await client.get("/api/v1/auth/nope/link-start", headers=headers)
    assert r.status_code == 404


async def test_link_start_returns_url_and_state(client, app):
    headers = await login_headers(client, app, "google", FakeLoginProvider(email="a@example.com"))
    app.state.provider_overrides["twitch"] = FakeLoginProvider(email="b@example.com")
    r = await client.get("/api/v1/auth/twitch/link-start", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["authorization_url"].startswith("https://provider.example/authorize")
    assert body["state"] and body["expires_in"] == 600
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_account_link.py -v`
Expected: FAIL (404, no route).

- [ ] **Step 3: Write minimal implementation** (append to `app/api/v1/auth.py`)

```python
@router.get(
    "/{provider}/link-start",
    response_model=AuthStartOut,
    summary="Begin linking an OAuth provider (authenticated)",
)
async def link_start(
    request: Request,
    provider: str,
    mode: Literal["web", "desktop"] = Query(default="web"),
    current: CurrentUser = Depends(get_current_user),  # noqa: B008
) -> AuthStartOut:
    await _rate_limit(request, "auth:start")
    if provider not in LOGIN_PROVIDERS:
        raise HTTPException(status_code=404, detail=f"unsupported provider: {provider}")
    s = _settings(request)
    state = generate_state()
    store = await get_kv(request)
    await store.set(
        oauth_state_key(state),
        {"kind": "link", "provider": provider, "mode": mode,
         "user_id": str(current.user.id)},
        ttl_seconds=s.oauth_state_ttl_seconds,
    )
    redirect_uri = _redirect_uri(request, provider)
    scopes = combined_scopes_for_login(provider, s)
    url = _provider(request, provider).get_authorization_url(
        state=state, redirect_uri=redirect_uri, scopes=scopes
    )
    clog.audit("link.started", provider=provider, mode=mode,
               user_id=str(current.user.id))
    return AuthStartOut(authorization_url=url, state=state,
                        expires_in=s.oauth_state_ttl_seconds)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_account_link.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add app/api/v1/auth.py tests/test_account_link.py
git commit -m "feat: link-start endpoint for attaching login providers"
```

---

### Task 2: `GET /auth/{provider}/link-callback` (attach + idempotent)

**Files:**
- Modify: `app/api/v1/auth.py` (after `link_start`)
- Test: `tests/test_account_link.py` (append)

**Interfaces:**
- Consumes: Task 1 route (state with `kind=link`), `AuthIdentity`, `find_or_create` NOT used (direct row handling).
- Produces: link-callback behavior (used by Task 3 for conflict/replay cases).

- [ ] **Step 1: Write the failing tests**

```python
async def test_link_callback_route_missing_before_implementation(client, app):
    from tests.conftest import FakeLoginProvider

    from tests.test_account_link import *  # noqa
```

No — keep it simple and deterministic without cross-test imports:

```python
async def test_link_callback_absent_before_implementation(client, app):
    from tests.conftest import FakeLoginProvider

    headers = await login_headers(client, app, "google", FakeLoginProvider(email="a@example.com"))
    r = await client.get(
        "/api/v1/auth/twitch/link-callback",
        params={"code": "c1", "state": "nope"},
        headers={"Accept": "application/json"},
    )
    assert r.status_code == 404


async def test_login_callback_rejects_link_kind_state(client, app):
    from tests.conftest import FakeLoginProvider

    headers = await login_headers(client, app, "google", FakeLoginProvider(email="a@example.com"))
    app.state.provider_overrides["twitch"] = FakeLoginProvider(user_id="tw-1", email="b@example.com")
    start = await client.get("/api/v1/auth/twitch/link-start", headers=headers)
    assert start.status_code == 200
    # The LOGIN callback must not accept a link-kind state (single-use consume → 400).
    cb = await client.get(
        "/api/v1/auth/twitch/callback",
        params={"code": "c1", "state": start.json()["state"]},
        headers={"Accept": "application/json"},
    )
    assert cb.status_code == 400
```

- [ ] **Step 2: Run to verify they fail**

Run: `pytest tests/test_account_link.py -v`
Expected: FAIL (no link-callback route yet).

- [ ] **Step 3: Write minimal implementation**

```python
@router.get("/{provider}/link-callback", summary="OAuth provider callback (link)")
async def link_callback(
    request: Request, provider: str, code: str = "", state: str = ""
) -> Response:
    await _rate_limit(request, "auth:callback")
    if provider not in LOGIN_PROVIDERS:
        raise HTTPException(status_code=404, detail=f"unsupported provider: {provider}")
    if not code or not state:
        raise HTTPException(status_code=400, detail="missing code or state")
    store = await get_kv(request)
    saved = await store.consume_json(oauth_state_key(state))
    if saved is None or saved.get("kind") != "link" or saved.get("provider") != provider:
        raise HTTPException(status_code=400, detail="invalid or expired state")
    try:
        bound_user_id = uuid.UUID(saved["user_id"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="invalid link state") from exc
    adapter = _provider(request, provider)
    redirect_uri = _redirect_uri(request, provider)
    try:
        token = await adapter.exchange_code(code=code, redirect_uri=redirect_uri)
        identity = await adapter.get_user_identity(access_token=token.access_token)
    except OAuthError as exc:
        raise HTTPException(
            status_code=502, detail=f"provider authentication failed: {exc}"
        ) from exc
    async with get_db(request) as db:
        id_res = await db.execute(
            select(AuthIdentity).where(
                AuthIdentity.provider == provider,
                AuthIdentity.provider_user_id == identity.provider_user_id,
            )
        )
        row = id_res.scalar_one_or_none()
        if row is not None and row.user_id != bound_user_id:
            raise HTTPException(
                status_code=409, detail="identity belongs to another account")
        status = "already" if row is not None else "ok"
        if row is None:
            user = await db.get(User, bound_user_id)
            if user is None or not user.is_active:
                raise HTTPException(status_code=400, detail="invalid link state")
            db.add(AuthIdentity(
                user_id=user.id, provider=provider,
                provider_user_id=identity.provider_user_id,
                provider_email=identity.email))
            clog.audit("identity.linked", provider=provider, user_id=str(user.id))
        if _wants_json(request):
            return JSONResponse({"provider": provider, "status": status})
        if saved.get("mode", "web") == "desktop":
            s = _settings(request)
            from urllib.parse import urlencode

            target = f"{s.desktop_callback_url}?" + urlencode(
                {"action": "link", "provider": provider, "status": status})
            return RedirectResponse(target, status_code=303)
        return RedirectResponse(f"{s.web_base_url}/account?linked={provider}",
                                status_code=303)
    raise AssertionError("unreachable")  # pragma: no cover
```

Required imports (add if missing): `uuid`, `select`, `AuthIdentity`, `JSONResponse` (already), `urlencode` (local import like login_callback).

- [ ] **Step 4: Extend tests to assert attach + idempotency, run green**

Append:

```python
async def test_link_attaches_and_lists_two_identities(client, app):
    from tests.conftest import FakeLoginProvider

    headers = await login_headers(client, app, "google", FakeLoginProvider(email="a@example.com"))
    app.state.provider_overrides["twitch"] = FakeLoginProvider(user_id="tw-1", email="b@example.com")
    start = await client.get("/api/v1/auth/twitch/link-start", headers=headers)
    cb = await client.get(
        "/api/v1/auth/twitch/link-callback",
        params={"code": "c1", "state": start.json()["state"]},
        headers={"Accept": "application/json"},
    )
    assert cb.status_code == 200, cb.text
    assert cb.json() == {"provider": "twitch", "status": "ok"}
    ids = await client.get("/api/v1/account/identities", headers=headers)
    assert sorted(i["provider"] for i in ids.json()) == ["google", "twitch"]
    # Idempotent repeat with a fresh state.
    start2 = await client.get("/api/v1/auth/twitch/link-start", headers=headers)
    cb2 = await client.get(
        "/api/v1/auth/twitch/link-callback",
        params={"code": "c1", "state": start2.json()["state"]},
        headers={"Accept": "application/json"},
    )
    assert cb2.json() == {"provider": "twitch", "status": "already"}
```

Run: `pytest tests/test_account_link.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/api/v1/auth.py tests/test_account_link.py
git commit -m "feat: link-callback attaches provider, idempotent re-link"
```

---

### Task 3: Conflict (409), replay (400), desktop redirect query

**Files:**
- Modify: none expected (behavior from Task 2); only tests unless gaps found.
- Test: `tests/test_account_link.py` (append)

**Interfaces:**
- Consumes: Task 2 route.
- Produces: verified normative query `?action=link&provider=&status=` for the desktop plan.

- [ ] **Step 1: Write the failing tests**

```python
async def test_link_foreign_identity_conflicts(client, app):
    from tests.conftest import FakeLoginProvider

    headers_a = await login_headers(client, app, "google", FakeLoginProvider(email="a@example.com"))
    app.state.provider_overrides["twitch"] = FakeLoginProvider(user_id="tw-X", email="x@example.com")
    s1 = await client.get("/api/v1/auth/twitch/link-start", headers=headers_a)
    cb1 = await client.get(
        "/api/v1/auth/twitch/link-callback",
        params={"code": "c1", "state": s1.json()["state"]},
        headers={"Accept": "application/json"},
    )
    assert cb1.status_code == 200
    # Second user tries to link the SAME twitch identity.
    headers_b = await login_headers(client, app, "kick", FakeLoginProvider(email="bb@example.com"))
    s2 = await client.get("/api/v1/auth/twitch/link-start", headers=headers_b)
    cb2 = await client.get(
        "/api/v1/auth/twitch/link-callback",
        params={"code": "c1", "state": s2.json()["state"]},
        headers={"Accept": "application/json"},
    )
    assert cb2.status_code == 409


async def test_link_state_replay_fails(client, app):
    from tests.conftest import FakeLoginProvider

    headers = await login_headers(client, app, "google", FakeLoginProvider(email="a@example.com"))
    app.state.provider_overrides["twitch"] = FakeLoginProvider(user_id="tw-1", email="b@example.com")
    s = await client.get("/api/v1/auth/twitch/link-start", headers=headers)
    state = s.json()["state"]
    first = await client.get(
        "/api/v1/auth/twitch/link-callback", params={"code": "c1", "state": state},
        headers={"Accept": "application/json"})
    assert first.status_code == 200
    replay = await client.get(
        "/api/v1/auth/twitch/link-callback", params={"code": "c1", "state": state},
        headers={"Accept": "application/json"})
    assert replay.status_code == 400


async def test_link_desktop_redirect_query(client, app):
    from tests.conftest import FakeLoginProvider

    headers = await login_headers(client, app, "google", FakeLoginProvider(email="a@example.com"))
    app.state.provider_overrides["twitch"] = FakeLoginProvider(user_id="tw-9", email="z@example.com")
    s = await client.get("/api/v1/auth/twitch/link-start", headers=headers,
                         params={"mode": "desktop"})
    cb = await client.get(
        "/api/v1/auth/twitch/link-callback",
        params={"code": "c9", "state": s.json()["state"]})
    assert cb.status_code == 303, cb.text
    assert "action=link" in cb.headers["location"]
    assert "provider=twitch" in cb.headers["location"]
    assert "status=ok" in cb.headers["location"]
```

- [ ] **Step 2: Run to verify**

Run: `pytest tests/test_account_link.py -v`
Expected: PASS if Task 2 implementation is complete; otherwise fix `auth.py` minimally (no new behavior beyond spec §4.1) and re-run.

- [ ] **Step 3: Commit**

```bash
git add tests/test_account_link.py app/api/v1/auth.py
git commit -m "test: link conflict, replay, desktop redirect coverage"
```

---

### Task 4: Full backend verification

- [ ] **Step 1: Run the whole suite**

Run: `pytest -q`
Expected: all green.

- [ ] **Step 2: Run lint**

Run: `ruff check app tests` (or per `pyproject.toml` config)
Expected: clean; fix only issues in touched files.

- [ ] **Step 3: Commit any lint fixes**

```bash
git add -A
git commit -m "chore: lint after link endpoints"
```
