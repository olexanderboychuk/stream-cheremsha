from __future__ import annotations

import asyncio
import logging
import time
import traceback
from collections.abc import Callable
from datetime import UTC, datetime
from TikTokLive import TikTokLiveClient
from TikTokLive.client.errors import (
    AgeRestrictedError,
    SignatureRateLimitError,
    TikTokLiveError,
    UserNotFoundError,
    UserOfflineError,
)
from TikTokLive.events import CommentEvent, ConnectEvent, DisconnectEvent, LiveEndEvent

from stream_cheremsha import l10n
from stream_cheremsha.domain.models import ChatMessage, ChatPlatform
from stream_cheremsha.pipeline.coordinator import StreamCoordinator

logger = logging.getLogger(__name__)

# Delay before reconnecting after an ended/failed connection.
TIKTOK_RECONNECT_SEC = 15.0


def _normalize_unique_id(v: str) -> str:
    # TikTokLive accepts "@username" or "username"; keep stored value without "@".
    return (v or "").strip().lstrip("@").strip()


class TikTokChatSource:
    """TikTokLive client wrapper: forwards TikTok comments into the coordinator."""

    def __init__(
        self,
        coordinator: StreamCoordinator,
        on_status: Callable[[str], None],
        on_gift: Callable[[str, str, str, int], None] | None = None,
        get_locale: Callable[[], str] | None = None,
        client_factory: Callable[[str], TikTokLiveClient] | None = None,
    ) -> None:
        self._coordinator = coordinator
        self._on_status = on_status
        self._on_gift = on_gift
        self._get_locale = get_locale or (lambda: l10n.DEFAULT_LOCALE)
        self._client_factory = client_factory or (lambda uid: TikTokLiveClient(unique_id=uid))
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._unique_id: str | None = None
        self._client: TikTokLiveClient | None = None
        self._gift_event_supported: bool | None = None
        # TikTokLive may emit multiple GiftEvent updates for a single gift
        # (e.g. streak updates + final). Keep a tiny in-memory dedupe window.
        self._gift_dedupe: dict[tuple[str, str, str, int], float] = {}
        self._gift_dedupe_window_sec: float = 6.0

    @property
    def running(self) -> bool:
        return self._running and self._task is not None and not self._task.done()

    async def start(self, unique_id: str) -> None:
        logger.info("TikTokChatSource.start called")
        await self.stop()
        uid = _normalize_unique_id(unique_id)
        if not uid:
            self._on_status(l10n.tr(self._get_locale(), "tk.bad_username"))
            return
        self._unique_id = uid
        self._running = True
        # Ensure we can see lifecycle in the app's status log (terminal often only shows httpx).
        self._on_status(f"TikTok: debug: start @{uid}")
        self._task = asyncio.create_task(self._supervisor(), name="tiktok-live")

    async def stop(self) -> None:
        if self._running or self._task is not None:
            logger.info("TikTokChatSource.stop called\n%s", "".join(traceback.format_stack(limit=12)))
            if self._unique_id:
                self._on_status(f"TikTok: debug: stop @{self._unique_id}")
        self._running = False
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
        await self._close_client()
        self._on_status(l10n.tr(self._get_locale(), "tk.stopped"))

    async def _close_client(self) -> None:
        client, self._client = self._client, None
        if client is None:
            return
        try:
            await client.disconnect(close_client=True)
        except (OSError, RuntimeError, TikTokLiveError) as exc:
            logger.debug("TikTok disconnect ignored: %s", exc)
        try:
            await client.close()
        except (OSError, RuntimeError, TikTokLiveError) as exc:
            logger.debug("TikTok close ignored: %s", exc)

    async def _supervisor(self) -> None:
        assert self._unique_id is not None
        backoff = TIKTOK_RECONNECT_SEC
        attempt = 0
        while self._running:
            attempt += 1
            uid = self._unique_id
            logger.info("TikTok supervisor attempt=%s uid=@%s", attempt, uid)
            self._on_status(f"TikTok: debug: attempt {attempt} @{uid}")
            client = self._client_factory(uid)
            self._client = client

            @client.on(ConnectEvent)
            async def _on_connect(event: ConnectEvent) -> None:  # noqa: ANN001
                self._on_status(l10n.tr(self._get_locale(), "tk.connected", user=event.unique_id))

            @client.on(DisconnectEvent)
            async def _on_disconnect(_event: DisconnectEvent) -> None:  # noqa: ANN001
                if self._running:
                    self._on_status(l10n.tr(self._get_locale(), "tk.disconnected_retry", sec=backoff))

            @client.on(LiveEndEvent)
            async def _on_live_end(_event: LiveEndEvent) -> None:  # noqa: ANN001
                if self._running:
                    self._on_status(l10n.tr(self._get_locale(), "tk.live_ended_retry", sec=backoff))

            @client.on(CommentEvent)
            async def _on_comment(event: CommentEvent) -> None:  # noqa: ANN001
                author = getattr(getattr(event, "user_info", None), "nickname", None) or "unknown"
                text = getattr(event, "comment", None) or getattr(event, "content", None) or ""
                msg = ChatMessage(
                    author=str(author),
                    text=str(text),
                    platform=ChatPlatform.TIKTOK,
                    received_at=datetime.now(UTC),
                )
                await self._coordinator.enqueue_chat(msg)

            # Gifts support (optional in library builds).
            gift_event = None
            try:
                from TikTokLive.events import GiftEvent as _GiftEvent  # type: ignore

                gift_event = _GiftEvent
            except ImportError:
                gift_event = None
            self._gift_event_supported = gift_event is not None
            if gift_event is None:
                logger.info("TikTok gifts disabled: TikTokLive.events.GiftEvent not available")
            else:
                logger.info("TikTok gifts enabled: GiftEvent handler registered")

            if gift_event is not None:

                @client.on(gift_event)  # type: ignore[misc]
                async def _on_gift(event: object) -> None:  # noqa: ANN001
                    cb = self._on_gift
                    if cb is None:
                        logger.debug("TikTok gift received but no callback is configured")
                        return
                    # Best-effort extraction (TikTokLive differs between versions).
                    user = getattr(getattr(event, "user", None), "nickname", None) or getattr(
                        getattr(event, "user", None),
                        "unique_id",
                        None,
                    )
                    gift = getattr(event, "gift", None)
                    gift_id = getattr(gift, "id", None) or getattr(gift, "gift_id", None) or ""
                    gift_name = getattr(gift, "name", None) or getattr(gift, "gift_name", None) or ""
                    count = getattr(event, "repeat_count", None) or getattr(event, "count", None) or 1
                    try:
                        count_i = int(count)
                    except (TypeError, ValueError):
                        count_i = 1

                    sender_s = str(user or "unknown")
                    gift_id_s = str(gift_id or "")
                    gift_name_s = str(gift_name or "")

                    # Prefer emitting only once per "streak": TikTokLive often sends incremental
                    # updates while a gift streak is in progress. Many versions expose flags like:
                    # - repeat_end: bool (True when streak ended)
                    # - streaking: bool
                    repeat_end = getattr(event, "repeat_end", None)
                    streaking = getattr(event, "streaking", None)
                    if isinstance(repeat_end, bool):
                        if not repeat_end:
                            logger.info(
                                "TikTok gift suppressed (repeat_end=False): sender=%s gift_id=%s gift_name=%s count=%s",
                                sender_s,
                                gift_id_s,
                                gift_name_s,
                                count_i,
                            )
                            return
                    elif isinstance(streaking, bool) and streaking:
                        logger.info(
                            "TikTok gift suppressed (streaking=True): sender=%s gift_id=%s gift_name=%s count=%s",
                            sender_s,
                            gift_id_s,
                            gift_name_s,
                            count_i,
                        )
                        return

                    # Extra safety: suppress identical gifts repeated within a short time window.
                    now = time.monotonic()
                    k = (sender_s, gift_id_s, gift_name_s, count_i)
                    last = self._gift_dedupe.get(k)
                    if last is not None and (now - last) <= self._gift_dedupe_window_sec:
                        logger.info(
                            "TikTok gift suppressed (dedupe %.1fs): sender=%s gift_id=%s gift_name=%s count=%s",
                            self._gift_dedupe_window_sec,
                            sender_s,
                            gift_id_s,
                            gift_name_s,
                            count_i,
                        )
                        return
                    self._gift_dedupe[k] = now
                    # Garbage-collect old keys occasionally (small map, O(n) is fine).
                    cutoff = now - self._gift_dedupe_window_sec
                    if len(self._gift_dedupe) > 64:
                        self._gift_dedupe = {kk: ts for kk, ts in self._gift_dedupe.items() if ts >= cutoff}
                    logger.info(
                        "TikTok gift: sender=%s gift_id=%s gift_name=%s count=%s",
                        sender_s,
                        gift_id_s,
                        gift_name_s,
                        count_i,
                    )
                    cb(sender_s, gift_id_s, gift_name_s, count_i)

            try:
                # TikTokLive docs: using connect/start just to check "is live" is inefficient.
                # We poll via is_live() and only connect once the creator is live.
                self._on_status(l10n.tr(self._get_locale(), "tk.connecting", user=uid))
                try:
                    live = await client.is_live()
                except UserNotFoundError:
                    self._on_status(l10n.tr(self._get_locale(), "tk.user_not_found", user=uid, sec=backoff))
                    live = False
                except AgeRestrictedError:
                    self._on_status(l10n.tr(self._get_locale(), "tk.age_restricted", user=uid))
                    live = False
                except SignatureRateLimitError as exc:
                    wait = max(float(getattr(exc, "retry_after", backoff)), backoff)
                    self._on_status(l10n.tr(self._get_locale(), "tk.rate_limited", sec=wait))
                    await asyncio.sleep(wait)
                    live = False

                if not live:
                    self._on_status(l10n.tr(self._get_locale(), "tk.user_offline", user=uid, sec=backoff))
                else:
                    # Non-blocking: returns a task which completes when disconnected.
                    t = await client.start(fetch_room_info=False, fetch_gift_info=True)
                    await t
            except asyncio.CancelledError:
                raise
            except UserOfflineError:
                # Normal case when the creator is not live.
                self._on_status(l10n.tr(self._get_locale(), "tk.user_offline", user=uid, sec=backoff))
            except UserNotFoundError:
                self._on_status(l10n.tr(self._get_locale(), "tk.user_not_found", user=uid, sec=backoff))
            except AgeRestrictedError:
                self._on_status(l10n.tr(self._get_locale(), "tk.age_restricted", user=uid, sec=backoff))
            except SignatureRateLimitError as exc:
                # Wait what the library tells us (retry_after), but cap at a sane min.
                wait = max(float(getattr(exc, "retry_after", backoff)), backoff)
                self._on_status(l10n.tr(self._get_locale(), "tk.rate_limited", sec=wait))
                await asyncio.sleep(wait)
            except (TikTokLiveError, OSError, RuntimeError) as exc:
                logger.warning("TikTokLive error: %s", exc)
                self._on_status(l10n.tr(self._get_locale(), "tk.error_retry", err=str(exc), sec=backoff))
            except Exception as exc:
                # TikTokLive occasionally raises unexpected wrapper errors; do not let the
                # supervisor task die, keep retrying instead.
                logger.exception("TikTokLive unexpected error: %s", exc)
                self._on_status(l10n.tr(self._get_locale(), "tk.error_retry", err=str(exc), sec=backoff))
            finally:
                await self._close_client()

            if not self._running:
                logger.info("TikTok supervisor stopping (running flag false)")
                self._on_status("TikTok: debug: supervisor stopping")
                break
            try:
                logger.info("TikTok supervisor sleep %.1fs then retry", backoff)
                self._on_status(f"TikTok: debug: sleep {backoff:.0f}s then retry")
                await asyncio.sleep(backoff)
            except asyncio.CancelledError:
                raise
        logger.info(
            "TikTok supervisor exited (running=%s task_done=%s)",
            self._running,
            self._task.done() if self._task else None,
        )
        self._on_status("TikTok: debug: supervisor exited")
