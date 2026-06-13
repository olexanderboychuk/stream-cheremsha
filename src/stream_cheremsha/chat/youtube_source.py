from __future__ import annotations

import asyncio
import json
import logging
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from stream_cheremsha import l10n
from stream_cheremsha.chat.video_id import extract_youtube_video_id
from stream_cheremsha.chat.youtube_chat_downloader import (
    ChatDownloaderMessage,
    iter_youtube_live_chat,
    normalize_chat_downloader_item,
)
from stream_cheremsha.chat.youtube_rss import extract_video_ids_from_rss_xml
from stream_cheremsha.config import keyring_store
from stream_cheremsha.config.constants import KEY_YOUTUBE_OAUTH, YOUTUBE_READONLY_SCOPE
from stream_cheremsha.domain.models import ChatMessage, ChatPlatform
from stream_cheremsha.pipeline.coordinator import StreamCoordinator

logger = logging.getLogger(__name__)

# How long to wait between checks when no live chat is available yet (manual URL or auto).
YOUTUBE_POLL_FOR_LIVE_SEC = 45.0

# Never poll live chat faster than this (ms); API may suggest less — quota is per call.
YOUTUBE_MIN_POLL_INTERVAL_MS = 5000

# After quotaExceeded, avoid hammering the API until the daily bucket resets (Pacific midnight).
YOUTUBE_QUOTA_BACKOFF_SEC = 3600.0


@dataclass(frozen=True, slots=True)
class YouTubeActionSignal:
    """Structured YouTube live-chat event for the Actions engine (separate from analytics feed).

    `kind` is one of ``superchat`` / ``supersticker`` / ``member``. Tip amounts carry
    ``amount_micros`` (currency micros) so rules can filter by a minimum threshold.
    """

    kind: str
    user: str
    amount_micros: int = 0
    currency: str = ""
    amount_display: str = ""
    message: str = ""
    months: int = 0
    level: str = ""
    profile_image_url: str = ""


def _int_or_zero(raw: object) -> int:
    """Parse YouTube numeric fields (often strings, e.g. amountMicros) into a non-negative int."""
    if isinstance(raw, bool):
        return 0
    if isinstance(raw, int):
        return max(0, raw)
    if isinstance(raw, float):
        return max(0, int(raw))
    if isinstance(raw, str):
        s = raw.strip()
        if s.isdigit():
            return int(s)
    return 0


def _http_error_is_quota_exceeded(err: HttpError) -> bool:
    if getattr(err, "resp", None) is None or err.resp.status != 403:
        return False
    raw = getattr(err, "content", b"") or b""
    if isinstance(raw, bytes):
        text = raw.decode("utf-8", errors="replace")
    else:
        text = str(raw)
    return "quotaExceeded" in text


def _http_error_is_fallback_worthy(err: HttpError) -> bool:
    """Return True when the Data API is effectively unusable for polling.

    This is intentionally broader than quotaExceeded: in real user setups the API can be
    disabled/misconfigured (403 accessNotConfigured), temporarily rate-limited (429), or
    intermittently unavailable (5xx). For manual video URLs we can still read chat via
    the non-API fallback reader.
    """
    resp = getattr(err, "resp", None)
    status = getattr(resp, "status", None)
    if status in (429, 500, 502, 503, 504):
        return True
    if status != 403:
        return False
    raw = getattr(err, "content", b"") or b""
    if isinstance(raw, bytes):
        text = raw.decode("utf-8", errors="replace")
    else:
        text = str(raw)
    # Common 403 reasons that mean "API not usable right now".
    return any(
        reason in text
        for reason in (
            "quotaExceeded",
            "dailyLimitExceeded",
            "rateLimitExceeded",
            "accessNotConfigured",
            "forbidden",
        )
    )


def _dedupe_strs(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _dedupe_pairs(
    items: list[tuple[str, str | None]],
) -> list[tuple[str, str | None]]:
    """Deduplicate by chat_id while preserving order and the first paired video_id."""
    seen: set[str] = set()
    out: list[tuple[str, str | None]] = []
    for cid, vid in items:
        if cid in seen:
            continue
        seen.add(cid)
        out.append((cid, vid))
    return out


# Concurrent-viewers polling cadence: cheap enough not to blow daily quota.
YOUTUBE_VIEWERS_POLL_INTERVAL_SEC = 30.0


# YouTube API rejects ``mine=true`` together with ``broadcastStatus``; filter client-side.
_LIVE_BROADCAST_LIFE_CYCLES = frozenset({"live", "testing"})


def _live_broadcast_row_is_on_air(item: Mapping[str, Any]) -> bool:
    st = item.get("status") or {}
    return st.get("lifeCycleStatus") in _LIVE_BROADCAST_LIFE_CYCLES


def _oauth_channel_id(service: object) -> str | None:
    resp = service.channels().list(part="id", mine=True, maxResults=1).execute()
    items = resp.get("items") or []
    if not items:
        return None
    cid = items[0].get("id")
    return cid if isinstance(cid, str) and cid else None


_YOUTUBE_WATCH_URL_TMPL = "https://www.youtube.com/watch?v={video_id}"


def youtube_watch_url(video_id: str) -> str:
    return _YOUTUBE_WATCH_URL_TMPL.format(video_id=video_id.strip())


def resolve_youtube_fallback_watch_url(
    service: object,
    *,
    manual_video_id: str | None = None,
    discovered_video_ids: list[str] | None = None,
) -> str | None:
    """Pick a watch URL for the non-API chat reader.

    Prefer a concrete ``watch?v=`` link (manual or from API discovery) over
    ``channel/…/live``, which makes chat-downloader scrape the channel streams tab.
    """
    if manual_video_id:
        return youtube_watch_url(manual_video_id)
    if discovered_video_ids:
        for vid in discovered_video_ids:
            if isinstance(vid, str) and vid.strip():
                return youtube_watch_url(vid)
    return _channel_live_fallback_url(service)


def _channel_live_fallback_url(service: object) -> str | None:
    cid = _oauth_channel_id(service)
    return f"https://www.youtube.com/channel/{cid}/live" if cid else None


_YOUTUBE_CHANNEL_VIDEO_RSS_TMPL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"


def fetch_channel_video_ids_from_rss(channel_id: str) -> list[str]:
    url = _YOUTUBE_CHANNEL_VIDEO_RSS_TMPL.format(channel_id=channel_id)
    resp = httpx.get(url, timeout=httpx.Timeout(15.0))
    resp.raise_for_status()
    return _dedupe_strs(extract_video_ids_from_rss_xml(resp.text))


def discover_my_live_streams(service: object) -> list[tuple[str, str | None]]:
    """Resolve ``(live_chat_id, video_id)`` pairs for the OAuth user's current streams.

    Prefer ``liveBroadcasts.list`` with ``mine=true`` (no ``broadcastStatus`` — it is
    incompatible with ``mine``) and ``part=snippet,status``, keeping rows whose
    ``status.lifeCycleStatus`` is ``live`` or ``testing``. The broadcast ``id`` is the
    video ID used for concurrent-viewer queries.

    If none, fall back to ``channels.list(mine=true)``, the channel's public video RSS
    feed, then ``videos.list`` ``liveStreamingDetails.activeLiveChatId``.
    """
    pairs: list[tuple[str, str | None]] = []
    page_token: str | None = None
    while True:
        resp = (
            service.liveBroadcasts()
            .list(
                part="snippet,status",
                mine=True,
                maxResults=50,
                pageToken=page_token,
            )
            .execute()
        )
        for item in resp.get("items", []):
            if not _live_broadcast_row_is_on_air(item):
                continue
            sn = item.get("snippet") or {}
            lcid = sn.get("liveChatId")
            vid = item.get("id")
            if isinstance(lcid, str) and lcid:
                pairs.append((lcid, vid if isinstance(vid, str) and vid else None))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    if pairs:
        return _dedupe_pairs(pairs)

    channel_id = _oauth_channel_id(service)
    if not channel_id:
        return []

    video_ids = fetch_channel_video_ids_from_rss(channel_id)
    if not video_ids:
        return []

    out: list[tuple[str, str | None]] = []
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i : i + 50]
        vresp = service.videos().list(part="liveStreamingDetails", id=",".join(chunk)).execute()
        for item in vresp.get("items", []):
            lsd = item.get("liveStreamingDetails") or {}
            lcid = lsd.get("activeLiveChatId")
            vid = item.get("id")
            if isinstance(lcid, str) and lcid:
                out.append((lcid, vid if isinstance(vid, str) and vid else None))
    return _dedupe_pairs(out)


def discover_my_live_chat_ids(service: object) -> list[str]:
    """Backwards-compatible wrapper returning only chat IDs."""
    return _dedupe_strs([cid for cid, _ in discover_my_live_streams(service)])


def fetch_concurrent_viewers_total(service: object, video_ids: list[str]) -> int | None:
    """Sum ``concurrentViewers`` across the given video IDs.

    Returns ``None`` when the API yields no parsable counters (stream may have
    ended or the field is hidden); callers should treat that as "no update".
    """
    if not video_ids:
        return None
    total = 0
    seen_any = False
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i : i + 50]
        resp = service.videos().list(part="liveStreamingDetails", id=",".join(chunk)).execute()
        for item in resp.get("items", []):
            lsd = item.get("liveStreamingDetails") or {}
            raw = lsd.get("concurrentViewers")
            if raw is None:
                continue
            try:
                total += int(raw)
            except (TypeError, ValueError):
                continue
            seen_any = True
    return total if seen_any else None


def is_google_account_linked() -> bool:
    raw = keyring_store.get_password(KEY_YOUTUBE_OAUTH)
    return bool(raw and raw.strip())


def clear_youtube_user_session() -> None:
    keyring_store.delete_password(KEY_YOUTUBE_OAUTH)


_SCOPES = [YOUTUBE_READONLY_SCOPE]


def parse_google_desktop_client_json(raw: str) -> dict[str, Any]:
    """Validate Google OAuth client JSON (Desktop app → top-level ``installed``)."""
    data = json.loads(raw)
    if not isinstance(data, Mapping):
        raise ValueError("OAuth client JSON must be a JSON object")
    if "installed" not in data:
        raise ValueError(
            'Google OAuth JSON must contain an "installed" block — create an OAuth '
            'client of type "Desktop" in Google Cloud Console and download the JSON.'
        )
    return dict(data)


def _load_credentials() -> Credentials | None:
    raw = keyring_store.get_password(KEY_YOUTUBE_OAUTH)
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Stored YouTube OAuth JSON is invalid")
        return None
    return Credentials.from_authorized_user_info(data, _SCOPES)


def run_oauth_browser_with_client_config(client_config: dict[str, Any]) -> Credentials:
    flow = InstalledAppFlow.from_client_config(client_config, _SCOPES)
    return flow.run_local_server(port=0, open_browser=True)


class YouTubeChatSource:
    """Poll YouTube live chat via Data API v3."""

    def __init__(
        self,
        coordinator: StreamCoordinator,
        on_status: Callable[[str], None],
        on_analytics_event: Callable[[str, str, str, int], None] | None = None,
        get_locale: Callable[[], str] | None = None,
        on_viewers_current: Callable[[int], None] | None = None,
        on_action_event: Callable[[YouTubeActionSignal], None] | None = None,
    ) -> None:
        self._coordinator = coordinator
        self._on_status = on_status
        self._on_analytics_event = on_analytics_event
        self._on_viewers_current = on_viewers_current
        self._on_action_event = on_action_event
        self._get_locale = get_locale or (lambda: l10n.DEFAULT_LOCALE)
        self._task: asyncio.Task[None] | None = None
        self._running = False

    async def _refresh_oauth_credentials(self, creds: Credentials) -> bool:
        """Refresh access token and persist to keyring.

        Returns False when the refresh token is revoked or unusable; stored
        session is cleared and the user must sign in again (no automatic fix).
        """

        def do_refresh() -> None:
            creds.refresh(Request())

        try:
            await asyncio.to_thread(do_refresh)
        except RefreshError as err:
            logger.warning("YouTube OAuth refresh failed: %s", err)
            clear_youtube_user_session()
            self._on_status(l10n.tr(self._get_locale(), "yt.oauth_refresh_failed"))
            return False
        keyring_store.set_password(KEY_YOUTUBE_OAUTH, creds.to_json())
        return True

    @property
    def running(self) -> bool:
        return self._running and self._task is not None and not self._task.done()

    async def browser_login(self, client_config: dict[str, Any]) -> None:
        """Run Google OAuth in the system browser; persist refresh/user token to keyring."""
        self._on_status(l10n.tr(self._get_locale(), "yt.oauth_browser"))

        def sync_flow() -> Credentials:
            return run_oauth_browser_with_client_config(client_config)

        creds = await asyncio.to_thread(sync_flow)
        keyring_store.set_password(KEY_YOUTUBE_OAUTH, creds.to_json())
        self._on_status(l10n.tr(self._get_locale(), "yt.oauth_saved"))

    async def start(self, video_url_or_id: str | None = None) -> None:
        # Cancel any prior run without emitting the "stopped" status: doing so here
        # would log "youtube stopped" the instant the user turns the toggle on and
        # trigger a UI refresh while ``_running`` is still False, snapping the switch
        # back off.
        await self._cancel_task()

        creds = _load_credentials()
        if creds is None:
            self._on_status(l10n.tr(self._get_locale(), "yt.run_oauth_first"))
            return
        if creds.expired:
            if not creds.refresh_token:
                self._on_status(l10n.tr(self._get_locale(), "yt.token_expired"))
                return
            if not await self._refresh_oauth_credentials(creds):
                return

        self._running = True
        self._task = asyncio.create_task(
            self._supervisor(video_url_or_id),
            name="youtube-chat",
        )

    async def _cancel_task(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None

    async def stop(self) -> None:
        await self._cancel_task()
        self._on_status(l10n.tr(self._get_locale(), "yt.stopped"))

    async def _supervisor(self, video_url_or_id: str | None) -> None:
        manual = (video_url_or_id or "").strip()
        video_id: str | None = None
        if manual:
            video_id = extract_youtube_video_id(manual)
            if not video_id:
                self._on_status(l10n.tr(self._get_locale(), "yt.bad_url"))
                self._running = False
                return

        wait = YOUTUBE_POLL_FOR_LIVE_SEC
        while self._running:
            loaded = _load_credentials()
            if loaded is None:
                self._on_status(l10n.tr(self._get_locale(), "yt.token_missing"))
                self._running = False
                return
            creds = loaded
            if creds.expired:
                if not creds.refresh_token:
                    self._on_status(l10n.tr(self._get_locale(), "yt.token_expired"))
                    self._running = False
                    return
                if not await self._refresh_oauth_credentials(creds):
                    self._running = False
                    return

            try:
                service = await asyncio.to_thread(
                    lambda: build("youtube", "v3", credentials=creds, cache_discovery=False),
                )
            except (HttpError, OSError) as e:
                if video_id and isinstance(e, HttpError) and _http_error_is_fallback_worthy(e):
                    if video_id:
                        self._on_status(
                            l10n.tr(self._get_locale(), "yt.fallback_switching"),
                        )
                        await self._run_fallback_for_video(video_id)
                    else:
                        # Unreachable: guarded by video_id above. Kept symmetrical with
                        # the auto-discovery path below.
                        self._on_status(
                            l10n.tr(
                                self._get_locale(),
                                "yt.quota_backoff",
                                min=YOUTUBE_QUOTA_BACKOFF_SEC / 60.0,
                            ),
                        )
                        await asyncio.sleep(YOUTUBE_QUOTA_BACKOFF_SEC)
                elif video_id and isinstance(e, OSError):
                    # Data API init may fail due to networking/system errors; manual URL can
                    # still proceed via fallback.
                    self._on_status(l10n.tr(self._get_locale(), "yt.fallback_switching"))
                    await self._run_fallback_for_video(video_id)
                elif isinstance(e, HttpError) and _http_error_is_quota_exceeded(e):
                    if video_id:
                        self._on_status(
                            l10n.tr(self._get_locale(), "yt.fallback_switching"),
                        )
                        await self._run_fallback_for_video(video_id)
                    else:
                        self._on_status(
                            l10n.tr(
                                self._get_locale(),
                                "yt.quota_backoff",
                                min=YOUTUBE_QUOTA_BACKOFF_SEC / 60.0,
                            ),
                        )
                        await asyncio.sleep(YOUTUBE_QUOTA_BACKOFF_SEC)
                else:
                    self._on_status(
                        l10n.tr(self._get_locale(), "yt.api_init_retry", err=str(e), sec=wait),
                    )
                    await asyncio.sleep(wait)
                continue

            try:
                if video_id is not None:
                    live_chat_ids = await asyncio.to_thread(
                        self._resolve_live_chat_ids_for_videos,
                        service,
                        [video_id],
                    )
                    live_video_ids: list[str] = [video_id]
                else:
                    pairs = await asyncio.to_thread(discover_my_live_streams, service)
                    live_chat_ids = [cid for cid, _ in pairs]
                    live_video_ids = [vid for _, vid in pairs if isinstance(vid, str) and vid]
            except HttpError as e:
                if video_id and _http_error_is_fallback_worthy(e):
                    if video_id:
                        self._on_status(
                            l10n.tr(self._get_locale(), "yt.fallback_switching"),
                        )
                        await self._run_fallback_for_video(video_id)
                    else:
                        self._on_status(
                            l10n.tr(
                                self._get_locale(),
                                "yt.quota_backoff",
                                min=YOUTUBE_QUOTA_BACKOFF_SEC / 60.0,
                            ),
                        )
                        await asyncio.sleep(YOUTUBE_QUOTA_BACKOFF_SEC)
                elif _http_error_is_quota_exceeded(e):
                    if video_id:
                        self._on_status(
                            l10n.tr(self._get_locale(), "yt.fallback_switching"),
                        )
                        await self._run_fallback_for_video(video_id)
                    else:
                        self._on_status(
                            l10n.tr(
                                self._get_locale(),
                                "yt.quota_backoff",
                                min=YOUTUBE_QUOTA_BACKOFF_SEC / 60.0,
                            ),
                        )
                        await asyncio.sleep(YOUTUBE_QUOTA_BACKOFF_SEC)
                else:
                    self._on_status(l10n.tr(self._get_locale(), "yt.retry", err=str(e), sec=wait))
                    await asyncio.sleep(wait)
                continue
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                self._on_status(l10n.tr(self._get_locale(), "yt.retry", err=str(e), sec=wait))
                await asyncio.sleep(wait)
                continue
            except ValueError as e:
                self._on_status(l10n.tr(self._get_locale(), "yt.wait_live", err=str(e), sec=wait))
                await asyncio.sleep(wait)
                continue

            if not live_chat_ids:
                if video_id is None:
                    self._on_status(l10n.tr(self._get_locale(), "yt.no_live_retry", sec=wait))
                else:
                    self._on_status(l10n.tr(self._get_locale(), "yt.no_chat_retry", sec=wait))
                await asyncio.sleep(wait)
                continue

            live_chat_ids = _dedupe_strs(live_chat_ids)
            n = len(live_chat_ids)
            if n == 1:
                self._on_status(l10n.tr(self._get_locale(), "yt.polling"))
            else:
                self._on_status(l10n.tr(self._get_locale(), "yt.multi_streams", n=n))

            fb_url = await asyncio.to_thread(
                resolve_youtube_fallback_watch_url,
                service,
                manual_video_id=video_id,
                discovered_video_ids=live_video_ids,
            )

            await self._poll_chats_round_robin(creds, live_chat_ids, fb_url, live_video_ids)
            break

    async def _run_fallback_for_watch_url(self, watch_url: str) -> None:
        self._on_status(l10n.tr(self._get_locale(), "yt.fallback_polling"))
        loop = asyncio.get_running_loop()
        q: asyncio.Queue[ChatDownloaderMessage | None] = asyncio.Queue()
        stop = threading.Event()

        def producer() -> None:
            try:
                for raw in iter_youtube_live_chat(watch_url):
                    if not self._running or stop.is_set():
                        break
                    msg = normalize_chat_downloader_item(raw)
                    if msg is None:
                        continue
                    loop.call_soon_threadsafe(q.put_nowait, msg)
            except Exception as err:
                logger.warning("YouTube fallback reader error: %s", err)

                def emit(err_s: str = str(err)) -> None:
                    self._on_status(
                        l10n.tr(self._get_locale(), "yt.fallback_error", err=err_s),
                    )

                loop.call_soon_threadsafe(emit)
            finally:
                loop.call_soon_threadsafe(q.put_nowait, None)

        worker = asyncio.create_task(asyncio.to_thread(producer))
        try:
            while True:
                if not self._running:
                    break
                dm = await q.get()
                if dm is None:
                    break
                cb = self._on_analytics_event
                if cb is not None:
                    cb("chat", dm.author, dm.text, 1)
                chat_msg = ChatMessage(
                    author=dm.author,
                    text=dm.text,
                    platform=ChatPlatform.YOUTUBE,
                    received_at=dm.received_at,
                )
                await self._coordinator.enqueue_chat(chat_msg)
        except asyncio.CancelledError:
            raise
        finally:
            stop.set()
            if not worker.done():
                worker.cancel()
            await asyncio.gather(worker, return_exceptions=True)

    async def _run_fallback_for_video(self, video_id: str) -> None:
        await self._run_fallback_for_watch_url(youtube_watch_url(video_id))

    async def _poll_chats_round_robin(
        self,
        creds: Credentials,
        live_chat_ids: list[str],
        fallback_watch_url: str | None,
        video_ids: list[str] | None = None,
    ) -> None:
        """One ``liveChatMessages.list`` at a time, rotating chats.

        Parallel loops per stream multiply quota (~N×); round-robin keeps total call rate ~1×.
        Concurrent viewers (when ``video_ids`` is provided) are polled in a side task at a
        slow cadence so the chat loop never blocks on the viewers call.
        """
        if not live_chat_ids:
            return
        try:
            service = await asyncio.to_thread(
                lambda: build("youtube", "v3", credentials=creds, cache_discovery=False),
            )
        except HttpError as e:
            if _http_error_is_quota_exceeded(e):
                self._on_status(l10n.tr(self._get_locale(), "yt.fallback_switching"))
                if fallback_watch_url:
                    await self._run_fallback_for_watch_url(fallback_watch_url)
                    return
                self._on_status(
                    l10n.tr(
                        self._get_locale(),
                        "yt.quota_backoff",
                        min=YOUTUBE_QUOTA_BACKOFF_SEC / 60.0,
                    ),
                )
                await asyncio.sleep(YOUTUBE_QUOTA_BACKOFF_SEC)
                return
            self._on_status(l10n.tr(self._get_locale(), "yt.api_init", err=str(e)))
            return
        except OSError as e:
            self._on_status(l10n.tr(self._get_locale(), "yt.api_init", err=str(e)))
            return

        viewers_task: asyncio.Task[None] | None = None
        if video_ids and self._on_viewers_current is not None:
            viewers_task = asyncio.create_task(
                self._poll_concurrent_viewers(service, list(video_ids)),
                name="youtube-viewers",
            )

        page_tokens: dict[str, str | None] = {lcid: None for lcid in live_chat_ids}
        order = list(live_chat_ids)
        rr = 0

        try:
            await self._chat_round_robin_loop(service, order, page_tokens, rr, fallback_watch_url)
        finally:
            if viewers_task is not None and not viewers_task.done():
                viewers_task.cancel()
                await asyncio.gather(viewers_task, return_exceptions=True)

    async def _chat_round_robin_loop(
        self,
        service: object,
        order: list[str],
        page_tokens: dict[str, str | None],
        rr: int,
        fallback_watch_url: str | None,
    ) -> None:
        while self._running:
            lcid = order[rr % len(order)]
            rr += 1
            try:
                body = await asyncio.to_thread(
                    self._list_messages,
                    service,
                    lcid,
                    page_tokens[lcid],
                )
            except asyncio.CancelledError:
                raise
            except HttpError as e:
                logger.warning("YouTube poll HTTP error: %s", e)
                if _http_error_is_fallback_worthy(e):
                    self._on_status(l10n.tr(self._get_locale(), "yt.fallback_switching"))
                    if fallback_watch_url:
                        await self._run_fallback_for_watch_url(fallback_watch_url)
                    else:
                        self._on_status(
                            l10n.tr(
                                self._get_locale(),
                                "yt.quota_backoff",
                                min=YOUTUBE_QUOTA_BACKOFF_SEC / 60.0,
                            ),
                        )
                        await asyncio.sleep(YOUTUBE_QUOTA_BACKOFF_SEC)
                    return
                self._on_status(l10n.tr(self._get_locale(), "yt.http_error", err=str(e)))
                await asyncio.sleep(5.0)
                continue
            except OSError as e:
                logger.warning("YouTube poll error: %s", e)
                self._on_status(l10n.tr(self._get_locale(), "yt.error", err=str(e)))
                await asyncio.sleep(5.0)
                continue

            interval_ms = int(body.get("pollingIntervalMillis", 5000))
            page_tokens[lcid] = body.get("nextPageToken")

            for item in body.get("items", []):
                snippet = item.get("snippet") or {}
                author_details = item.get("authorDetails") or {}
                author = author_details.get("displayName") or "unknown"
                profile_image_url = str(author_details.get("profileImageUrl") or "")
                text = snippet.get("displayMessage") or ""
                self._ingest_analytics_item(
                    author=author,
                    snippet=snippet,
                    text=text,
                    profile_image_url=profile_image_url,
                )
                msg = ChatMessage(
                    author=author,
                    text=text,
                    platform=ChatPlatform.YOUTUBE,
                    received_at=datetime.now(UTC),
                )
                await self._coordinator.enqueue_chat(msg)

            await asyncio.sleep(
                max(interval_ms, YOUTUBE_MIN_POLL_INTERVAL_MS) / 1000.0,
            )

    async def _poll_concurrent_viewers(self, service: object, video_ids: list[str]) -> None:
        """Periodically pull ``concurrentViewers`` for the active broadcast(s).

        Failures (HTTP, transport, parse) are logged and the loop continues so a transient
        viewers-API hiccup never tears down the chat polling.
        """
        cb = self._on_viewers_current
        if cb is None or not video_ids:
            return
        while self._running:
            try:
                total = await asyncio.to_thread(
                    fetch_concurrent_viewers_total,
                    service,
                    video_ids,
                )
            except asyncio.CancelledError:
                raise
            except HttpError as exc:
                logger.debug("YouTube concurrentViewers HTTP error: %s", exc)
            except OSError as exc:
                logger.debug("YouTube concurrentViewers network error: %s", exc)
            else:
                if total is not None:
                    cb(int(total))
            await asyncio.sleep(YOUTUBE_VIEWERS_POLL_INTERVAL_SEC)

    @staticmethod
    def _resolve_live_chat_ids_for_videos(service: object, video_ids: list[str]) -> list[str]:
        if not video_ids:
            return []
        out: list[str] = []
        for i in range(0, len(video_ids), 50):
            chunk = video_ids[i : i + 50]
            resp = service.videos().list(part="liveStreamingDetails", id=",".join(chunk)).execute()
            items = resp.get("items", [])
            if len(chunk) == 1 and not items:
                raise ValueError("video not found or not accessible")
            for item in items:
                lsd = item.get("liveStreamingDetails") or {}
                lcid = lsd.get("activeLiveChatId")
                if isinstance(lcid, str) and lcid:
                    out.append(lcid)
        if len(video_ids) == 1 and not out:
            raise ValueError("no active live chat for this video (is the stream live?)")
        return _dedupe_strs(out)

    @staticmethod
    def _list_messages(
        service: object, live_chat_id: str, page_token: str | None
    ) -> dict[str, Any]:
        req = service.liveChatMessages().list(
            liveChatId=live_chat_id,
            part="snippet,authorDetails",
            pageToken=page_token,
            maxResults=2000,
        )
        return req.execute()

    def _emit_action_event(self, signal: YouTubeActionSignal) -> None:
        cb = self._on_action_event
        if cb is None:
            return
        cb(signal)

    def _ingest_analytics_item(
        self,
        *,
        author: str,
        snippet: Mapping[str, Any],
        text: str,
        profile_image_url: str = "",
    ) -> None:
        cb = self._on_analytics_event
        kind = snippet.get("type") or "textMessageEvent"
        kind_s = kind if isinstance(kind, str) else "textMessageEvent"
        author_s = str(author or "")
        pic = str(profile_image_url or "")

        if kind_s == "superChatEvent":
            details = snippet.get("superChatDetails") or {}
            amount = str(details.get("amountDisplayString") or "").strip()
            msg = str(text or "").strip()
            self._emit_action_event(
                YouTubeActionSignal(
                    kind="superchat",
                    user=author_s,
                    amount_micros=_int_or_zero(details.get("amountMicros")),
                    currency=str(details.get("currency") or "").strip(),
                    amount_display=amount,
                    message=msg,
                    profile_image_url=pic,
                )
            )
            if cb is not None:
                det = f"{amount} · {msg}" if (amount and msg) else (amount or msg)
                cb("superchat", author_s, det, 1)
            return
        if kind_s == "superStickerEvent":
            details = snippet.get("superStickerDetails") or {}
            amount = str(details.get("amountDisplayString") or "").strip()
            msg = str(text or "").strip()
            self._emit_action_event(
                YouTubeActionSignal(
                    kind="supersticker",
                    user=author_s,
                    amount_micros=_int_or_zero(details.get("amountMicros")),
                    currency=str(details.get("currency") or "").strip(),
                    amount_display=amount,
                    profile_image_url=pic,
                )
            )
            if cb is not None:
                det = f"{amount} · {msg}" if (amount and msg) else (amount or msg)
                cb("supersticker", author_s, det, 1)
            return
        if kind_s in ("newSponsorEvent", "memberMilestoneChatEvent"):
            if kind_s == "newSponsorEvent":
                details = snippet.get("newSponsorDetails") or {}
                months = 0
            else:
                details = snippet.get("memberMilestoneChatDetails") or {}
                months = _int_or_zero(details.get("memberMonth"))
            self._emit_action_event(
                YouTubeActionSignal(
                    kind="member",
                    user=author_s,
                    months=months,
                    level=str(details.get("memberLevelName") or "").strip(),
                    profile_image_url=pic,
                )
            )
            if cb is not None:
                cb("member", author_s, "", 1)
            return

        # Default: count as chat message and keep the full message text as detail.
        if cb is not None:
            cb("chat", author_s, str(text or ""), 1)
