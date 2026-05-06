from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_HELIX = "https://api.twitch.tv/helix"


@dataclass(frozen=True, slots=True)
class TwitchUser:
    id: str
    login: str
    display_name: str | None = None


class TwitchHelixClient:
    """Minimal Helix client for analytics (users + streams viewer counts)."""

    def __init__(
        self,
        *,
        client_id: str,
        access_token: str,
        http: httpx.AsyncClient | None = None,
    ) -> None:
        self._client_id = client_id.strip()
        self._access_token = access_token.strip()
        self._http = http or httpx.AsyncClient(timeout=httpx.Timeout(15.0))
        self._owns_http = http is None
        self._user_cache: dict[str, TwitchUser] = {}

    async def aclose(self) -> None:
        if self._owns_http:
            await self._http.aclose()

    def _headers(self) -> dict[str, str]:
        return {
            "Client-Id": self._client_id,
            "Authorization": f"Bearer {self._access_token}",
        }

    async def get_users_by_login(self, logins: Iterable[str]) -> list[TwitchUser]:
        xs = [x.strip().lower() for x in logins if x and x.strip()]
        out: list[TwitchUser] = []
        need: list[str] = []
        for login in xs:
            cached = self._user_cache.get(login)
            if cached is not None:
                out.append(cached)
            else:
                need.append(login)
        if not need:
            return out

        params = [("login", x) for x in need]
        r = await self._http.get(f"{_HELIX}/users", headers=self._headers(), params=params)
        r.raise_for_status()
        users = _parse_users(r.json())
        for u in users:
            self._user_cache[u.login] = u
        out.extend(users)
        return out

    async def get_user_id(self, login: str) -> str | None:
        login_n = (login or "").strip().lower()
        if not login_n:
            return None
        cached = self._user_cache.get(login_n)
        if cached is not None:
            return cached.id
        users = await self.get_users_by_login([login_n])
        if not users:
            return None
        return users[0].id

    async def get_stream_viewers(self, user_id: str) -> int | None:
        uid = (user_id or "").strip()
        if not uid:
            return None
        r = await self._http.get(
            f"{_HELIX}/streams",
            headers=self._headers(),
            params={"user_id": uid},
        )
        r.raise_for_status()
        return _parse_stream_viewer_count(r.json())

    async def create_eventsub_subscription(
        self,
        *,
        type_name: str,
        version: str,
        condition: dict[str, Any],
        session_id: str,
    ) -> dict[str, Any]:
        payload = {
            "type": type_name,
            "version": version,
            "condition": condition,
            "transport": {"method": "websocket", "session_id": session_id},
        }
        r = await self._http.post(
            f"{_HELIX}/eventsub/subscriptions",
            headers={**self._headers(), "Content-Type": "application/json"},
            json=payload,
        )
        r.raise_for_status()
        return r.json()


def _parse_users(payload: dict[str, Any]) -> list[TwitchUser]:
    data = payload.get("data")
    if not isinstance(data, list):
        return []
    out: list[TwitchUser] = []
    for row in data:
        if not isinstance(row, dict):
            continue
        uid = row.get("id")
        login = row.get("login")
        if not isinstance(uid, str) or not isinstance(login, str):
            continue
        dn = row.get("display_name")
        out.append(
            TwitchUser(
                id=uid,
                login=login.strip().lower(),
                display_name=dn if isinstance(dn, str) else None,
            ),
        )
    return out


def _parse_stream_viewer_count(payload: dict[str, Any]) -> int | None:
    data = payload.get("data")
    if not isinstance(data, list) or not data:
        return 0
    row = data[0]
    if not isinstance(row, dict):
        return 0
    vc = row.get("viewer_count")
    if isinstance(vc, int):
        return max(0, vc)
    if isinstance(vc, float):
        return max(0, int(vc))
    return 0
