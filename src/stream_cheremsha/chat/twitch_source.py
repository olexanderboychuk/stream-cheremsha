from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime

from twitchio import Message
from twitchio.ext import commands

from stream_cheremsha import l10n
from stream_cheremsha.domain.models import ChatMessage, ChatPlatform
from stream_cheremsha.pipeline.coordinator import StreamCoordinator

logger = logging.getLogger(__name__)

# Delay before reconnecting IRC after a failed or ended connection.
TWITCH_RECONNECT_SEC = 15.0


class CheremshaTwitchBot(commands.Bot):
    """twitchio 2 IRC bot: forwards chat into the coordinator."""

    def __init__(
        self,
        coordinator: StreamCoordinator,
        token: str,
        channel: str,
        loop: asyncio.AbstractEventLoop,
        on_status: Callable[[str], None],
        get_locale: Callable[[], str],
    ) -> None:
        ch = channel.lstrip("#").lower()
        self._channel_login = ch
        self._on_status = on_status
        self._get_locale = get_locale
        super().__init__(
            token=token,
            prefix="!",
            initial_channels=[ch],
            loop=loop,
        )
        self._coordinator = coordinator

    async def event_ready(self) -> None:
        """IRC logged in; ``start()`` still blocks until disconnect — refresh UI status."""
        nick = self.nick or "?"
        self._on_status(
            l10n.tr(
                self._get_locale(),
                "twitch.irc_ready",
                nick=nick,
                channel=self._channel_login,
            ),
        )

    async def event_message(self, message: Message) -> None:
        if message.echo:
            return
        await self.handle_commands(message)
        author = getattr(message.author, "name", None) or "unknown"
        text = message.content or ""
        msg = ChatMessage(
            author=author,
            text=text,
            platform=ChatPlatform.TWITCH,
            received_at=datetime.now(UTC),
        )
        await self._coordinator.enqueue_chat(msg)


class TwitchSource:
    """Lifecycle wrapper around :class:`CheremshaTwitchBot`."""

    def __init__(
        self,
        coordinator: StreamCoordinator,
        on_status: Callable[[str], None],
        get_locale: Callable[[], str] | None = None,
    ) -> None:
        self._coordinator = coordinator
        self._on_status = on_status
        self._get_locale = get_locale or (lambda: l10n.DEFAULT_LOCALE)
        self._bot: CheremshaTwitchBot | None = None
        self._task: asyncio.Task[None] | None = None
        self._running = False

    async def _close_bot_safely(self) -> None:
        """Close IRC client; tolerate twitchio bug when ``_keeper`` was never set."""
        bot, self._bot = self._bot, None
        if bot is None:
            return
        try:
            await bot.close()
        except AttributeError as exc:
            # twitchio websocket.WSConnection._close does self._keeper.cancel() unconditionally
            if getattr(exc, "name", None) != "cancel" or getattr(exc, "obj", None) is not None:
                raise
            logger.debug("Twitch bot close skipped (twitchio partial state): %s", exc)

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self, token: str, channel: str) -> None:
        await self.stop()
        self._running = True
        self._task = asyncio.create_task(
            self._run_irc_until_stopped(token, channel),
            name="twitch-bot",
        )

    async def _run_irc_until_stopped(self, token: str, channel: str) -> None:
        loop = asyncio.get_running_loop()
        backoff = TWITCH_RECONNECT_SEC
        while self._running:
            self._bot = CheremshaTwitchBot(
                self._coordinator,
                token=token,
                channel=channel,
                loop=loop,
                on_status=self._on_status,
                get_locale=self._get_locale,
            )
            try:
                self._on_status(l10n.tr(self._get_locale(), "twitch.connecting"))
                await self._bot.start()
            except asyncio.CancelledError:
                raise
            except OSError as e:
                logger.warning("Twitch connection failed: %s", e)
                self._on_status(
                    l10n.tr(self._get_locale(), "twitch.error_retry", err=str(e), sec=backoff),
                )
            except RuntimeError as e:
                logger.warning("Twitch runtime error: %s", e)
                self._on_status(
                    l10n.tr(self._get_locale(), "twitch.error_retry", err=str(e), sec=backoff),
                )
            else:
                if self._running:
                    self._on_status(
                        l10n.tr(self._get_locale(), "twitch.closed_retry", sec=backoff),
                    )
            finally:
                await self._close_bot_safely()

            if not self._running:
                break
            try:
                await asyncio.sleep(backoff)
            except asyncio.CancelledError:
                raise

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
        await self._close_bot_safely()
        self._on_status(l10n.tr(self._get_locale(), "twitch.stopped"))
