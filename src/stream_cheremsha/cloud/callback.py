"""Loopback callback server for the Cheremsha desktop login flow.

After the user authenticates in the system browser, Cloud API redirects to
``http://127.0.0.1:8471/callback?code=<grant>&state=<desktop_state>`` (see
``DESKTOP_CALLBACK_URL``). This short-lived server captures that redirect.

Pattern follows ``chat/kick_oauth.py`` (single-use future keyed by our own
``desktop_state`` for CSRF protection, immediate teardown). ``aiohttp`` is
imported lazily so this module costs nothing at startup.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable

from stream_cheremsha.cloud import constants

logger = logging.getLogger(__name__)


class DesktopCallbackServer:
    """Serve one callback on 127.0.0.1:8471 and resolve the grant code."""

    def __init__(self, *, expected_state: str) -> None:
        self._expected_state = expected_state
        self._runner: object | None = None
        self._site: object | None = None
        self._future: asyncio.Future[tuple[str, str]] | None = None
        self._platform_future: asyncio.Future[dict[str, str]] | None = None
        self._platform_name = ""
        self._link_future: asyncio.Future[dict[str, str]] | None = None

    async def start(self) -> None:
        from aiohttp import web

        app = web.Application()

        async def _callback(req: web.Request) -> web.Response:
            code = str(req.query.get("code") or "")
            state = str(req.query.get("state") or "")
            fut = self._future
            # Accept only the state we generated (CSRF / login-injection guard);
            # ignore anything else (e.g. stray platform-connect redirects).
            if fut is not None and not fut.done() and state == self._expected_state and code:
                fut.set_result((code, state))
                return web.Response(
                    text=(
                        "<h1>Успішно!</h1>"
                        "<p>Авторизацію завершено. Поверніться до застосунку Cheremsha.</p>"
                    ),
                    content_type="text/html",
                )
            # Platform-connect / link redirects carry no secrets: they only
            # trigger a refresh. Each is accepted solely while its waiter is
            # armed (exact platform / any link outcome, respectively).
            query_platform = str(req.query.get("platform") or "")
            query_status = str(req.query.get("status") or "")
            pfut = self._platform_future
            if (
                pfut is not None
                and not pfut.done()
                and query_platform
                and query_platform == self._platform_name
                and query_status
            ):
                pfut.set_result({"platform": query_platform, "status": query_status})
                return web.Response(
                    text="<h1>Cheremsha</h1><p>Це вікно можна закрити.</p>",
                    content_type="text/html",
                )
            if (
                req.query.get("action") == "link"
                and self._link_future is not None
                and not self._link_future.done()
                and str(req.query.get("provider") or "")
            ):
                outcome: dict[str, str] = {
                    "provider": str(req.query.get("provider")),
                    "status": str(req.query.get("status") or ""),
                }
                if "auto_connected" in req.query:
                    outcome["auto_connected"] = str(req.query.get("auto_connected"))
                if req.query.get("auto_error"):
                    outcome["auto_error"] = str(req.query.get("auto_error"))
                self._link_future.set_result(outcome)
                return web.Response(
                    text="<h1>Cheremsha</h1><p>Це вікно можна закрити.</p>",
                    content_type="text/html",
                )
            return web.Response(
                text="<h1>Cheremsha</h1><p>Це вікно можна закрити.</p>",
                content_type="text/html",
            )

        app.router.add_get(constants.CALLBACK_PATH, _callback)
        # access_log=None: the default access log would record the full
        # request line including ?code= / ?state= query values. The grant
        # code is single-use but must still never hit the logs.
        runner = web.AppRunner(app, access_log=None)
        await runner.setup()
        site = web.TCPSite(runner, constants.CALLBACK_HOST, constants.CALLBACK_PORT)
        await site.start()
        self._runner = runner
        self._site = site
        self._future = asyncio.get_running_loop().create_future()
        self._platform_future = asyncio.get_running_loop().create_future()
        self._link_future = asyncio.get_running_loop().create_future()

    def wait_for_callback(
        self, *, timeout: float = constants.LOGIN_WAIT_TIMEOUT_S
    ) -> Awaitable[tuple[str, str]]:
        if self._future is None:
            raise RuntimeError("callback server not started")
        return asyncio.wait_for(self._future, timeout=timeout)

    def wait_for_platform(
        self, *, platform: str, timeout: float = constants.LOGIN_WAIT_TIMEOUT_S
    ) -> Awaitable[dict[str, str]]:
        self._platform_name = (platform or "").strip().lower()
        if self._platform_future is None:
            raise RuntimeError("callback server not started")
        return asyncio.wait_for(self._platform_future, timeout=timeout)

    def wait_for_link(
        self, *, timeout: float = constants.LOGIN_WAIT_TIMEOUT_S
    ) -> Awaitable[dict[str, str]]:
        if self._link_future is None:
            raise RuntimeError("callback server not started")
        return asyncio.wait_for(self._link_future, timeout=timeout)

    def cancel(self) -> None:
        if self._future is not None and not self._future.done():
            self._future.cancel()
        if self._platform_future is not None and not self._platform_future.done():
            self._platform_future.cancel()
        if self._link_future is not None and not self._link_future.done():
            self._link_future.cancel()

    async def stop(self) -> None:
        self._future = None
        self._platform_future = None
        self._platform_name = ""
        self._link_future = None
        runner, self._runner = self._runner, None
        self._site = None
        if runner is not None:
            try:
                await runner.cleanup()  # type: ignore[union-attr]
            except Exception:
                logger.debug("callback server cleanup failed", exc_info=False)
