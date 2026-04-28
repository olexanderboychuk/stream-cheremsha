from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from stream_cheremsha import l10n
from stream_cheremsha.chat.video_id import extract_youtube_video_id
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


def _http_error_is_quota_exceeded(err: HttpError) -> bool:
    if getattr(err, "resp", None) is None or err.resp.status != 403:
        return False
    raw = getattr(err, "content", b"") or b""
    if isinstance(raw, bytes):
        text = raw.decode("utf-8", errors="replace")
    else:
        text = str(raw)
    return "quotaExceeded" in text


def _dedupe_strs(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


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


def discover_my_live_chat_ids(service: object) -> list[str]:
    """Resolve live chat IDs for the OAuth user's current streams.

    Prefer ``liveBroadcasts.list`` with ``mine=true`` (no ``broadcastStatus`` — it is
    incompatible with ``mine``) and ``part=snippet,status``, keeping rows whose
    ``status.lifeCycleStatus`` is ``live`` or ``testing``.

    If none, fall back to ``channels.list(mine=true)`` then ``search.list`` with
    ``channelId`` + ``eventType=live`` (``forMine`` + ``eventType`` returns 400) and
    ``videos.list`` ``activeLiveChatId``.
    """
    chat_ids: list[str] = []
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
            if isinstance(lcid, str) and lcid:
                chat_ids.append(lcid)
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    if chat_ids:
        return _dedupe_strs(chat_ids)

    channel_id = _oauth_channel_id(service)
    if not channel_id:
        return []

    video_ids: list[str] = []
    page_token = None
    while True:
        resp = (
            service.search()
            .list(
                part="id",
                channelId=channel_id,
                type="video",
                eventType="live",
                maxResults=50,
                pageToken=page_token,
            )
            .execute()
        )
        for item in resp.get("items", []):
            vid = (item.get("id") or {}).get("videoId")
            if isinstance(vid, str) and vid:
                video_ids.append(vid)
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    video_ids = _dedupe_strs(video_ids)
    if not video_ids:
        return []

    out: list[str] = []
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i : i + 50]
        vresp = (
            service.videos()
            .list(part="liveStreamingDetails", id=",".join(chunk))
            .execute()
        )
        for item in vresp.get("items", []):
            lsd = item.get("liveStreamingDetails") or {}
            lcid = lsd.get("activeLiveChatId")
            if isinstance(lcid, str) and lcid:
                out.append(lcid)
    return _dedupe_strs(out)


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
        get_locale: Callable[[], str] | None = None,
    ) -> None:
        self._coordinator = coordinator
        self._on_status = on_status
        self._get_locale = get_locale or (lambda: l10n.DEFAULT_LOCALE)
        self._task: asyncio.Task[None] | None = None
        self._running = False

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
        await self.stop()

        creds = _load_credentials()
        if creds is None:
            self._on_status(l10n.tr(self._get_locale(), "yt.run_oauth_first"))
            return
        if creds.expired:
            if not creds.refresh_token:
                self._on_status(l10n.tr(self._get_locale(), "yt.token_expired"))
                return

            def refresh() -> None:
                creds.refresh(Request())

            await asyncio.to_thread(refresh)
            keyring_store.set_password(KEY_YOUTUBE_OAUTH, creds.to_json())

        self._running = True
        self._task = asyncio.create_task(
            self._supervisor(video_url_or_id),
            name="youtube-chat",
        )

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
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

                def refresh() -> None:
                    creds.refresh(Request())

                await asyncio.to_thread(refresh)
                keyring_store.set_password(KEY_YOUTUBE_OAUTH, creds.to_json())

            try:
                service = await asyncio.to_thread(
                    lambda: build("youtube", "v3", credentials=creds, cache_discovery=False),
                )
            except (HttpError, OSError) as e:
                if isinstance(e, HttpError) and _http_error_is_quota_exceeded(e):
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
                else:
                    live_chat_ids = await asyncio.to_thread(discover_my_live_chat_ids, service)
            except HttpError as e:
                if _http_error_is_quota_exceeded(e):
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

            await self._poll_chats_round_robin(creds, live_chat_ids)
            break

    async def _poll_chats_round_robin(self, creds: Credentials, live_chat_ids: list[str]) -> None:
        """One ``liveChatMessages.list`` at a time, rotating chats.

        Parallel loops per stream multiply quota (~N×); round-robin keeps total call rate ~1×.
        """
        if not live_chat_ids:
            return
        try:
            service = await asyncio.to_thread(
                lambda: build("youtube", "v3", credentials=creds, cache_discovery=False),
            )
        except (HttpError, OSError) as e:
            self._on_status(l10n.tr(self._get_locale(), "yt.api_init", err=str(e)))
            return

        page_tokens: dict[str, str | None] = {lcid: None for lcid in live_chat_ids}
        order = list(live_chat_ids)
        rr = 0

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
                self._on_status(l10n.tr(self._get_locale(), "yt.http_error", err=str(e)))
                if _http_error_is_quota_exceeded(e):
                    self._on_status(
                        l10n.tr(
                            self._get_locale(),
                            "yt.quota_backoff",
                            min=YOUTUBE_QUOTA_BACKOFF_SEC / 60.0,
                        ),
                    )
                    await asyncio.sleep(YOUTUBE_QUOTA_BACKOFF_SEC)
                else:
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
                author = (item.get("authorDetails") or {}).get("displayName") or "unknown"
                text = snippet.get("displayMessage") or ""
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

    @staticmethod
    def _resolve_live_chat_ids_for_videos(service: object, video_ids: list[str]) -> list[str]:
        if not video_ids:
            return []
        out: list[str] = []
        for i in range(0, len(video_ids), 50):
            chunk = video_ids[i : i + 50]
            resp = (
                service.videos()
                .list(part="liveStreamingDetails", id=",".join(chunk))
                .execute()
            )
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
    def _list_messages(service: object, live_chat_id: str, page_token: str | None) -> dict:
        req = (
            service.liveChatMessages()
            .list(
                liveChatId=live_chat_id,
                part="snippet,authorDetails",
                pageToken=page_token,
                maxResults=2000,
            )
        )
        return req.execute()
