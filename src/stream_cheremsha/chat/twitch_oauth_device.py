from __future__ import annotations

import asyncio
import json
import logging
import time
import webbrowser
from collections.abc import Callable
from typing import Any, Final

import httpx

from stream_cheremsha import l10n

logger = logging.getLogger(__name__)

_TWITCH_DEVICE: Final[str] = "https://id.twitch.tv/oauth2/device"
_TWITCH_TOKEN: Final[str] = "https://id.twitch.tv/oauth2/token"
_TWITCH_VALIDATE: Final[str] = "https://id.twitch.tv/oauth2/validate"

# IRC + Helix/EventSub scopes for the account that authorizes the app.
# Note: changing scopes requires the user to re-run OAuth once.
_DEFAULT_SCOPES: Final[str] = " ".join(
    [
        "chat:read",
        # EventSub: channel.follow requires moderator privileges; broadcaster can act as moderator.
        "moderator:read:followers",
        "channel:read:subscriptions",
        "bits:read",
    ],
)


def _lower_message(payload: dict[str, Any] | None, text: str) -> str:
    parts: list[str] = []
    if payload:
        for key in ("message", "error_description", "error"):
            v = payload.get(key)
            if isinstance(v, str):
                parts.append(v)
    parts.append(text)
    return " ".join(parts).lower()


async def run_device_code_flow(
    client_id: str,
    *,
    scopes: str = _DEFAULT_SCOPES,
    status: Callable[[str], None] = lambda _m: None,
    locale: str | None = None,
) -> dict[str, Any]:
    """Run Twitch device-code OAuth; opens the system browser for user approval.

    Returns the token JSON from Twitch (access_token, refresh_token, expires_in, ...).
    """
    lc = l10n.normalize_locale(locale or l10n.DEFAULT_LOCALE)
    client_id = client_id.strip()
    if not client_id:
        raise ValueError("Twitch Client ID is required")

    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as http:
        dr = await http.post(
            _TWITCH_DEVICE,
            data={"client_id": client_id, "scopes": scopes},
        )
        dr.raise_for_status()
        device_payload = dr.json()

    device_code = device_payload["device_code"]
    user_code = device_payload["user_code"]
    verification_uri = device_payload["verification_uri"]
    verification_uri_complete = device_payload.get("verification_uri_complete")
    interval = float(device_payload.get("interval", 5))
    expires_in = float(device_payload.get("expires_in", 1800))

    open_url = verification_uri_complete or verification_uri
    await asyncio.to_thread(webbrowser.open, open_url)
    status(
        l10n.tr(
            lc,
            "twitch.oauth_prompt",
            code=user_code,
            sec=int(expires_in),
        ),
    )

    deadline = time.monotonic() + expires_in
    sleep_for = interval

    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as http:
        while time.monotonic() < deadline:
            await asyncio.sleep(sleep_for)
            tr = await http.post(
                _TWITCH_TOKEN,
                data={
                    "client_id": client_id,
                    "device_code": device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
            )
            if tr.status_code == 200:
                data = tr.json()
                status(l10n.tr(lc, "twitch.oauth_signed_in"))
                return data

            payload: dict[str, Any] | None = None
            try:
                payload = tr.json()
            except json.JSONDecodeError:
                logger.debug("Non-JSON Twitch token response: %s", tr.text)

            msg = _lower_message(payload, tr.text)
            if "authorization_pending" in msg:
                continue
            if "slow_down" in msg:
                sleep_for = min(sleep_for + 5.0, 30.0)
                continue
            if "expired_token" in msg or "invalid_grant" in msg:
                raise ValueError(l10n.tr(lc, "twitch.oauth_denied"))
            raise ValueError(l10n.tr(lc, "twitch.oauth_token_err", detail=str(payload or tr.text)))

    raise TimeoutError(l10n.tr(lc, "twitch.oauth_timeout"))


async def validate_token(access_token: str) -> dict[str, Any]:
    """Return Twitch /validate JSON (includes ``login``)."""
    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as http:
        r = await http.get(
            _TWITCH_VALIDATE,
            headers={"Authorization": f"OAuth {access_token}"},
        )
        r.raise_for_status()
        return r.json()


async def refresh_access_token(
    client_id: str,
    refresh_token: str,
    client_secret: str | None,
) -> dict[str, Any]:
    data: dict[str, str] = {
        "client_id": client_id,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    if client_secret:
        data["client_secret"] = client_secret
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as http:
        r = await http.post(_TWITCH_TOKEN, data=data)
        r.raise_for_status()
        return r.json()
