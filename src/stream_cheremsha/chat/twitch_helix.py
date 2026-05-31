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
    profile_image_url: str = ""


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
        self._user_cache_by_id: dict[str, TwitchUser] = {}

    async def aclose(self) -> None:
        if self._owns_http:
            await self._http.aclose()

    def _headers(self) -> dict[str, str]:
        return {
            "Client-Id": self._client_id,
            "Authorization": f"Bearer {self._access_token}",
        }

    def _cache_user(self, user: TwitchUser) -> None:
        self._user_cache[user.login] = user
        self._user_cache_by_id[user.id] = user

    async def get_users(
        self,
        *,
        logins: Iterable[str] = (),
        user_ids: Iterable[str] = (),
    ) -> list[TwitchUser]:
        xs_login = [x.strip().lower() for x in logins if x and x.strip()]
        xs_id = [x.strip() for x in user_ids if x and x.strip()]
        out: list[TwitchUser] = []
        need_login: list[str] = []
        need_id: list[str] = []
        for login in xs_login:
            cached = self._user_cache.get(login)
            if cached is not None:
                out.append(cached)
            else:
                need_login.append(login)
        for uid in xs_id:
            cached = self._user_cache_by_id.get(uid)
            if cached is not None:
                if cached not in out:
                    out.append(cached)
            else:
                need_id.append(uid)
        if not need_login and not need_id:
            return out

        params: list[tuple[str, str]] = [("login", x) for x in need_login]
        params.extend(("id", x) for x in need_id)
        r = await self._http.get(f"{_HELIX}/users", headers=self._headers(), params=params)
        r.raise_for_status()
        users = _parse_users(r.json())
        for u in users:
            self._cache_user(u)
            if u not in out:
                out.append(u)
        return out

    async def get_users_by_login(self, logins: Iterable[str]) -> list[TwitchUser]:
        return await self.get_users(logins=logins)

    async def resolve_profile_image_url(
        self,
        *,
        user_id: str = "",
        login: str = "",
    ) -> str:
        """Helix GET /users → profile_image_url (cached per id/login)."""
        uid = (user_id or "").strip()
        log = (login or "").strip().lower()
        if uid:
            cached = self._user_cache_by_id.get(uid)
            if cached is not None and cached.profile_image_url:
                return cached.profile_image_url
        if log:
            cached = self._user_cache.get(log)
            if cached is not None and cached.profile_image_url:
                return cached.profile_image_url
        if not uid and not log:
            return ""
        users = await self.get_users(user_ids=[uid] if uid else [], logins=[log] if log else [])
        if not users:
            return ""
        return (users[0].profile_image_url or "").strip()

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
        pic = row.get("profile_image_url")
        out.append(
            TwitchUser(
                id=uid,
                login=login.strip().lower(),
                display_name=dn if isinstance(dn, str) else None,
                profile_image_url=pic.strip() if isinstance(pic, str) else "",
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
