"""Kick REST API client + OAuth 2.1 (Authorization Code + PKCE).

Official Kick API. Auth host is ``id.kick.com``; API host is ``api.kick.com``.
We request only the scopes the desktop app needs (``user:read``,
``channel:read``, ``chat:write``). Kick rotates refresh tokens on use, so the
new refresh token must always be persisted after a refresh.
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx

from stream_cheremsha.config import embedded

AUTH_HOST = "https://id.kick.com"
API_HOST = "https://api.kick.com"

OAUTH_AUTHORIZE_URL = f"{AUTH_HOST}/oauth/authorize"
OAUTH_TOKEN_URL = f"{AUTH_HOST}/oauth/token"
OAUTH_REVOKE_URL = f"{AUTH_HOST}/oauth/revoke"
OAUTH_INTROSPECT_URL = f"{AUTH_HOST}/oauth/token/introspect"

# Environment overrides (mirrors STREAM_CHEREMSHA_TWITCH_CLIENT_ID pattern).
ENV_KICK_CLIENT_ID = "STREAM_CHEREMSHA_KICK_CLIENT_ID"
ENV_KICK_CLIENT_SECRET = "STREAM_CHEREMSHA_KICK_CLIENT_SECRET"
ENV_KICK_REDIRECT_URI = "STREAM_CHEREMSHA_KICK_REDIRECT_URI"
DEFAULT_REDIRECT_URI = "http://localhost:8080/callback"

KICK_SCOPES = "user:read channel:read chat:write"


@dataclass(frozen=True, slots=True)
class KickPkce:
    verifier: str
    challenge: str


def generate_pkce() -> KickPkce:
    """Generate a PKCE verifier + S256 challenge pair (RFC 7636)."""
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode("ascii")
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return KickPkce(verifier=verifier, challenge=challenge)


@dataclass(frozen=True, slots=True)
class KickOAuthConfig:
    client_id: str
    redirect_uri: str
    scopes: str = KICK_SCOPES
    client_secret: str = ""

    @classmethod
    def from_env(cls) -> KickOAuthConfig | None:
        cid = (os.environ.get(ENV_KICK_CLIENT_ID) or "").strip()
        if not cid:
            cid = (embedded.KICK_CLIENT_ID or "").strip()
        if not cid:
            return None
        sec = (os.environ.get(ENV_KICK_CLIENT_SECRET) or "").strip()
        if not sec:
            sec = (embedded.KICK_CLIENT_SECRET or "").strip()
        redir = os.environ.get(ENV_KICK_REDIRECT_URI, "").strip() or DEFAULT_REDIRECT_URI
        return cls(client_id=cid, client_secret=sec, redirect_uri=redir)


def build_authorize_url(cfg: KickOAuthConfig, pkce: KickPkce, state: str) -> str:
    params = {
        "response_type": "code",
        "client_id": cfg.client_id,
        "redirect_uri": cfg.redirect_uri,
        "scope": cfg.scopes,
        "state": state,
        "code_challenge": pkce.challenge,
        "code_challenge_method": "S256",
    }
    return f"{OAUTH_AUTHORIZE_URL}?{urlencode(params)}"


async def exchange_code(
    cfg: KickOAuthConfig,
    pkce: KickPkce,
    code: str,
    *,
    client: httpx.AsyncClient | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Exchange an authorization code for tokens via the token endpoint."""
    owns = client is None
    c = client or httpx.AsyncClient(timeout=timeout)
    try:
        data: dict[str, str] = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": cfg.client_id,
            "redirect_uri": cfg.redirect_uri,
            "code_verifier": pkce.verifier,
        }
        if cfg.client_secret:
            data["client_secret"] = cfg.client_secret
        resp = await c.post(OAUTH_TOKEN_URL, data=data)
    finally:
        if owns:
            await c.aclose()
    if resp.status_code != 200:
        raise ValueError(f"Kick OAuth exchange failed ({resp.status_code}): {resp.text}")
    payload = resp.json()
    if not isinstance(payload, dict) or not payload.get("access_token"):
        raise ValueError("Kick OAuth exchange returned no access token")
    return payload


async def refresh_access_token(
    cfg: KickOAuthConfig,
    refresh_token: str,
    *,
    client: httpx.AsyncClient | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Refresh access+refresh tokens. Kick rotates the refresh token, so callers
    must persist the new ``refresh_token`` returned here."""
    owns = client is None
    c = client or httpx.AsyncClient(timeout=timeout)
    try:
        data: dict[str, str] = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": cfg.client_id,
        }
        if cfg.client_secret:
            data["client_secret"] = cfg.client_secret
        resp = await c.post(OAUTH_TOKEN_URL, data=data)
    finally:
        if owns:
            await c.aclose()
    if resp.status_code != 200:
        raise ValueError(f"Kick OAuth refresh failed ({resp.status_code}): {resp.text}")
    payload = resp.json()
    if not isinstance(payload, dict) or not payload.get("access_token"):
        raise ValueError("Kick OAuth refresh returned no access token")
    return payload


async def introspect_token(
    access_token: str,
    *,
    client: httpx.AsyncClient | None = None,
    timeout: float = 20.0,
) -> dict[str, Any]:
    """Check whether a Kick access token is still valid."""
    owns = client is None
    c = client or httpx.AsyncClient(timeout=timeout)
    try:
        resp = await c.post(
            OAUTH_INTROSPECT_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
    finally:
        if owns:
            await c.aclose()
    if resp.status_code != 200:
        raise ValueError(f"Kick token introspection failed ({resp.status_code})")
    payload = resp.json()
    if not isinstance(payload, dict):
        return {}
    data = payload.get("data")
    return data if isinstance(data, dict) else {}


@dataclass(slots=True)
class KickChannelInfo:
    broadcaster_user_id: int = 0
    slug: str = ""
    is_live: bool = False
    viewer_count: int = 0
    title: str = ""

    def to_online_dict(self) -> dict[str, int]:
        return {"current": max(0, self.viewer_count)}


class KickApiClient:
    """Minimal official REST client for the data the app needs."""

    def __init__(
        self,
        access_token: str,
        *,
        client: httpx.AsyncClient | None = None,
        timeout: float = 20.0,
    ) -> None:
        self._token = (access_token or "").strip()
        self._client = client or httpx.AsyncClient(timeout=timeout)
        self._owns_client = client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        resp = await self._client.get(
            f"{API_HOST}{path}",
            params=params,
            headers={"Authorization": f"Bearer {self._token}"},
        )
        if resp.status_code != 200:
            raise ValueError(f"Kick API GET {path} failed ({resp.status_code}): {resp.text}")
        data = resp.json()
        if not isinstance(data, dict):
            return None
        return data.get("data")

    async def get_me(self) -> dict[str, Any]:
        out = await self._get_json("/public/v1/users")
        if isinstance(out, list) and out:
            item = out[0]
            return item if isinstance(item, dict) else {}
        return {}

    async def get_channel_by_slug(self, slug: str) -> dict[str, Any]:
        out = await self._get_json("/public/v1/channels", {"slug": (slug or "").strip()})
        if isinstance(out, list) and out:
            item = out[0]
            return item if isinstance(item, dict) else {}
        return {}

    async def get_my_channel(self) -> dict[str, Any]:
        out = await self._get_json("/public/v1/channels")
        if isinstance(out, list) and out:
            item = out[0]
            return item if isinstance(item, dict) else {}
        return {}

    @staticmethod
    def parse_channel_info(payload: dict[str, Any]) -> KickChannelInfo:
        info = KickChannelInfo()
        info.broadcaster_user_id = int(payload.get("broadcaster_user_id") or 0)
        info.slug = str(payload.get("slug") or "").strip()
        info.title = str(payload.get("stream_title") or "").strip()
        stream = payload.get("stream")
        if isinstance(stream, dict):
            info.is_live = bool(stream.get("is_live"))
            try:
                info.viewer_count = max(0, int(stream.get("viewer_count") or 0))
            except (TypeError, ValueError):
                info.viewer_count = 0
        return info

    async def fetch_live_channel(self, slug: str) -> KickChannelInfo:
        payload = await self.get_channel_by_slug(slug)
        return self.parse_channel_info(payload)

    async def send_message(
        self,
        content: str,
        *,
        broadcaster_user_id: int | None = None,
        reply_to_message_id: str | None = None,
    ) -> str:
        body: dict[str, Any] = {
            "content": (content or "").strip()[:500],
            "type": "user",
        }
        if broadcaster_user_id:
            body["broadcaster_user_id"] = int(broadcaster_user_id)
        if reply_to_message_id:
            body["reply_to_message_id"] = str(reply_to_message_id)
        resp = await self._client.post(
            f"{API_HOST}/public/v1/chat",
            json=body,
            headers={"Authorization": f"Bearer {self._token}"},
        )
        if resp.status_code != 200:
            raise ValueError(f"Kick send message failed ({resp.status_code}): {resp.text}")
        data = resp.json()
        if not isinstance(data, dict):
            return ""
        inner = data.get("data")
        if isinstance(inner, dict):
            return str(inner.get("message_id") or "")
        return ""
