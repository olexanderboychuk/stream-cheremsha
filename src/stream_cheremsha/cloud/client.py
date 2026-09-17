"""Async Cheremsha Cloud API client (desktop side).

Speaks only to Cheremsha Cloud — never to Google/Twitch/TikTok/Kick OAuth
endpoints. The desktop therefore holds no provider client secrets and never
receives provider tokens; it only ever handles its own Cheremsha credentials.

Pattern follows ``chat/kick_api.py``: injectable ``httpx.AsyncClient`` with an
``owns`` flag, module-level timeout constants, typed errors. No secret is ever
logged (see ``_safe_params`` — only non-sensitive metadata is logged).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

from stream_cheremsha.cloud import constants

logger = logging.getLogger(__name__)


class CloudApiError(Exception):
    """Cloud API request failed (network, HTTP error, or bad payload)."""

    def __init__(self, message: str, *, status: int = 0, code: str = "") -> None:
        super().__init__(message)
        self.status = status
        self.code = code


@dataclass(frozen=True, slots=True)
class CloudUser:
    id: str
    email: str
    display_name: str
    avatar_url: str | None = None


@dataclass(frozen=True, slots=True)
class CloudSessionTokens:
    access_token: str
    refresh_token: str
    expires_in: int


@dataclass(frozen=True, slots=True)
class CloudPlatformStatus:
    platform: str
    connected: bool
    username: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None
    status: str | None = None


@dataclass(frozen=True, slots=True)
class CloudAutoConnectOutcome:
    """Outcome of a same-transaction OAuth auto-connect during login.

    ``connected=True`` means the platform is fully authorized and ready
    for runtime use. ``missing`` lists scopes that were not granted
    (the user must re-authorize). ``error`` carries a reason code when
    the auto-connect raised an exception (e.g. server misconfiguration);
    the platform stays disconnected in that case.
    """

    platform: str | None = None
    connected: bool = False
    missing: tuple[str, ...] = ()
    reauth_required: bool = False
    error: str | None = None


class CheremshaCloudClient:
    """Thin async wrapper over the Cheremsha Cloud REST API."""

    def __init__(
        self,
        base_url: str,
        client: httpx.AsyncClient | None = None,
        *,
        timeout: float = constants.HTTP_TIMEOUT_S,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._client = client
        self._owns = client is None
        self._timeout = timeout

    async def aclose(self) -> None:
        if self._owns and self._client is not None:
            await self._client.aclose()
            self._client = None

    def _c(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
            self._owns = True
        return self._client

    async def _get(self, path: str, token: str | None, params: dict[str, str] | None = None) -> Any:
        return await self._request("GET", path, token=token, params=params)

    async def _post(
        self, path: str, token: str | None, payload: dict[str, Any] | None = None
    ) -> Any:
        return await self._request("POST", path, token=token, json_body=payload)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        token: str | None,
        params: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        # Only method + path are logged: never tokens, codes, verifiers,
        # request bodies, or response payloads (they may contain secrets).
        logger.debug("cloud %s %s", method, path)
        headers = {"Accept": "application/json", "User-Agent": "stream-cheremsha-desktop/1"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            resp = await self._c().request(
                method, self._base + path, params=params, json=json_body, headers=headers
            )
        except httpx.HTTPError as exc:
            raise CloudApiError(f"cloud request failed: {type(exc).__name__}") from exc
        if resp.status_code >= 400:
            code = ""
            try:
                code = str(resp.json().get("code", ""))
            except Exception:
                code = ""
            raise CloudApiError(
                f"cloud error {resp.status_code}", status=resp.status_code, code=code
            )
        try:
            return resp.json()
        except ValueError as exc:
            raise CloudApiError("cloud returned non-JSON response") from exc

    # -- login -----------------------------------------------------------
    async def login_start(
        self, provider: str, *, code_challenge: str, desktop_state: str
    ) -> dict[str, Any]:
        body = await self._get(
            f"/api/v1/auth/{provider}/start",
            token=None,
            params={
                "mode": "desktop",
                "code_challenge": code_challenge,
                "desktop_state": desktop_state,
            },
        )
        if not isinstance(body, dict) or not body.get("authorization_url"):
            raise CloudApiError("cloud login start has no authorization URL")
        return body

    async def exchange_desktop_code(
        self, *, code: str, verifier: str
    ) -> tuple[CloudSessionTokens, CloudUser, CloudAutoConnectOutcome | None]:
        body = await self._post(
            "/api/v1/auth/desktop/exchange",
            token=None,
            payload={"code": code, "code_verifier": verifier},
        )
        tokens, user, auto_connect = _parse_session(body)
        return tokens, user, auto_connect

    # -- session ---------------------------------------------------------
    async def get_me(self, access_token: str) -> CloudUser:
        return _parse_user(await self._get("/api/v1/auth/me", token=access_token))

    async def refresh_session(self, refresh_token: str) -> tuple[CloudSessionTokens, None]:
        body = await self._post(
            "/api/v1/auth/refresh", token=None, payload={"refresh_token": refresh_token}
        )
        tokens = _parse_tokens(body)
        return tokens, None

    async def logout(self, access_token: str) -> None:
        try:
            await self._post("/api/v1/auth/logout", token=access_token)
        except CloudApiError:
            # Logout is best-effort: local state is cleared regardless.
            logger.debug("cloud logout request failed (best-effort)")

    # -- platforms -------------------------------------------------------
    async def get_platforms(self, access_token: str) -> list[CloudPlatformStatus]:
        body = await self._get("/api/v1/platforms", token=access_token)
        out: list[CloudPlatformStatus] = []
        for item in body.get("platforms", []) if isinstance(body, dict) else []:
            if not isinstance(item, dict) or "platform" not in item:
                continue
            out.append(
                CloudPlatformStatus(
                    platform=str(item.get("platform")),
                    connected=bool(item.get("connected")),
                    username=item.get("username"),
                    display_name=item.get("display_name"),
                    avatar_url=item.get("avatar_url"),
                    status=item.get("status"),
                )
            )
        return out

    # -- sync -------------------------------------------------------------
    async def sync_push(self, access_token: str, body: dict) -> dict:  # type: ignore[no-untyped-def]
        return await self._post("/api/v1/sync", token=access_token, payload=body)

    async def sync_state(self, access_token: str) -> dict:  # type: ignore[no-untyped-def]
        return await self._get("/api/v1/sync/state", token=access_token)

    async def fetch_runtime_token(
        self, platform: str, access_token: str  # type: ignore[no-untyped-def]
    ) -> dict:
        """Short-lived brokered credential for one platform.

        Returns a dict with at minimum ``access_token`` + identity fields
        (``platform_user_id``, ``username``, ``display_name``, ``avatar_url``,
        ``scope``). ``refresh_token`` is **never** returned by the backend.

        ``access_token`` MUST be a valid Cheremsha session token; the
        runtime-token endpoint is authenticated and the manager's
        reconcile loop awaits this method before starting any local
        PlatformSource for the platform.
        """
        return await self._post(
            f"/api/v1/platforms/{platform}/runtime-token",
            token=access_token,
            payload={},
        )

    async def fetch_avatar(self, url: str) -> bytes | None:
        try:
            resp = await self._c().get(url, timeout=constants.AVATAR_TIMEOUT_S)
        except httpx.HTTPError:
            return None
        if resp.status_code != 200 or not resp.content:
            return None
        if len(resp.content) > 2 * 1024 * 1024:
            return None
        return resp.content


def _parse_user(body: Any) -> CloudUser:
    if not isinstance(body, dict) or not body.get("id") or not body.get("email"):
        raise CloudApiError("cloud returned malformed user")
    return CloudUser(
        id=str(body["id"]),
        email=str(body["email"]),
        display_name=str(body.get("display_name") or ""),
        avatar_url=str(body["avatar_url"]) if body.get("avatar_url") else None,
    )


def _parse_tokens(body: Any) -> CloudSessionTokens:
    if not isinstance(body, dict) or not body.get("access_token") or not body.get("refresh_token"):
        raise CloudApiError("cloud returned malformed session")
    try:
        expires = int(body.get("expires_in", 900))
    except (TypeError, ValueError):
        expires = 900
    return CloudSessionTokens(
        access_token=str(body["access_token"]),
        refresh_token=str(body["refresh_token"]),
        expires_in=expires,
    )


def _parse_session(
    body: Any,
) -> tuple[CloudSessionTokens, CloudUser, CloudAutoConnectOutcome | None]:
    tokens = _parse_tokens(body)
    user = _parse_user(body.get("user") if isinstance(body, dict) else None)
    auto_connect = _parse_auto_connect(
        body.get("auto_connect") if isinstance(body, dict) else None
    )
    return tokens, user, auto_connect


def _parse_auto_connect(payload: Any) -> CloudAutoConnectOutcome | None:
    if payload is None:
        return None
    if not isinstance(payload, dict):
        return None
    missing = payload.get("missing") or []
    if not isinstance(missing, list):
        missing = []
    return CloudAutoConnectOutcome(
        platform=str(payload["platform"]) if payload.get("platform") else None,
        connected=bool(payload.get("connected") or False),
        missing=tuple(str(m) for m in missing),
        reauth_required=bool(payload.get("reauth_required") or False),
        error=str(payload["error"]) if payload.get("error") else None,
    )
