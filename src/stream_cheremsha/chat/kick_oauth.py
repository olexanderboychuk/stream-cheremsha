"""Kick OAuth 2.1 (PKCE) flow with a local callback server.

Kick requires an exact-match ``redirect_uri`` (``http://localhost:8080/callback``).
We spin up a short-lived aiohttp server on localhost that captures the OAuth
``code`` + ``state`` returned by the browser redirect, then tear it down.

No public URL or tunnel is required — the browser redirect is outbound to the
user's local machine.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from aiohttp import web

from stream_cheremsha.chat.kick_api import (
    KickOAuthConfig,
    KickPkce,
    build_authorize_url,
    generate_pkce,
)

logger = logging.getLogger(__name__)

CALLBACK_HOST = "127.0.0.1"
CALLBACK_PORT = 8080


class KickOAuthFlow:
    """Runs the local callback server and returns (url, future) for the code."""

    def __init__(self, cfg: KickOAuthConfig) -> None:
        self._cfg = cfg
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None
        self._pending: dict[str, asyncio.Future[tuple[str, str]]] = {}
        self._auth_url = ""
        self._state = ""
        self._pkce = generate_pkce()

    @property
    def auth_url(self) -> str:
        return self._auth_url

    async def start(self) -> None:
        app = web.Application()

        async def _callback(req: web.Request) -> web.Response:
            code = str(req.query.get("code") or "")
            state = str(req.query.get("state") or "")
            fut = self._pending.get(state)
            if fut is not None and not fut.done():
                fut.set_result((code, state))
            return web.Response(text="<h1>OK</h1>You can close this tab.", content_type="text/html")

        app.router.add_get("/callback", _callback)
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, CALLBACK_HOST, CALLBACK_PORT)
        await self._site.start()

        self._state = _random_state()
        self._pending[self._state] = asyncio.get_running_loop().create_future()
        self._auth_url = build_authorize_url(self._cfg, self._pkce, self._state)

    def wait_for_code(self, *, timeout: float = 180.0) -> Awaitable[tuple[str, str]]:
        fut = self._pending.get(self._state)
        if fut is None:
            raise RuntimeError("OAuth flow not started")
        return asyncio.wait_for(fut, timeout=timeout)

    @property
    def pkce(self):
        return self._pkce

    async def stop(self) -> None:
        self._pending.clear()
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None
        self._site = None


def _random_state() -> str:
    import secrets

    return secrets.token_hex(16)


async def run_kick_oauth(
    cfg: KickOAuthConfig, open_url: Callable[[str], None]
) -> tuple[str, str, KickPkce]:
    """Open the browser, wait for the code, return (code, state, pkce).

    The returned PKCE pair is the exact one used to build the auth URL, so the
    caller can exchange the code with the matching verifier.
    """
    flow = KickOAuthFlow(cfg)
    try:
        await flow.start()
        open_url(flow.auth_url)
        code, state = await flow.wait_for_code()
        return code, state, flow.pkce
    finally:
        await flow.stop()
