from __future__ import annotations

import asyncio
import logging
import re
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
TIKTOK_COMMENT_BACKLOG_WINDOW_SEC = 2.0
# HTTP room/info snapshot occasionally exposes viewer counts when websocket fields stay zero.
TIKTOK_VIEWERS_POLL_SEC = 25.0
# RoomUserSeq: fused / multi-live rooms often expose concurrent viewers only via fields
# that exceed cumulative total_user.
_MULTI_LIVE_POPULARITY_TO_TOTAL_USER_RATIO_CAP = 96

_ROOM_INFO_VIEWER_KEYS = frozenset(
    {
        "user_count",
        "viewer_count",
        "live_viewer_count",
        "watching_count",
        "watch_count",
        "display_viewer_count",
        "live_room_viewer_count",
        "live_watch_cnt",
        "watch_cnt",
        "fusion_room_viewer_cnt",
        "multi_live_viewer_cnt",
        "cross_room_viewer_cnt",
        "combined_viewer_cnt",
    },
)

# Skip nested ints that look like gifts/likes/ranks — not concurrent viewers.
_ROOM_INFO_KEY_EXCLUDE_HINTS = (
    "gift",
    "like_count",
    "fan_club",
    "follower_count",
    "follow_count",
    "score",
    "rank_list",
    "diamond",
)


def _room_info_key_might_be_live_viewers(key_norm: str) -> bool:
    if any(ex in key_norm for ex in _ROOM_INFO_KEY_EXCLUDE_HINTS):
        return False
    if key_norm in _ROOM_INFO_VIEWER_KEYS:
        return True
    if key_norm.endswith("_viewer_count") or key_norm.endswith("_user_count"):
        return True
    if "watching" in key_norm:
        return True
    if key_norm.endswith("_watch_cnt") or key_norm.endswith("watch_cnt"):
        return True
    if "live_user" in key_norm:
        return True
    if "multi_live" in key_norm and (
        "viewer" in key_norm or "watch" in key_norm or "user" in key_norm
    ):
        return True
    return False


def _extract_live_viewers_from_room_payload(obj: object, *, _depth: int = 0) -> int | None:
    """Best-effort concurrent viewers from TikTok `/room/info`-style JSON (shape varies)."""
    if _depth > 14:
        return None
    best = 0

    if isinstance(obj, dict):
        for key, val in obj.items():
            kn = str(key).replace("-", "_").lower()
            if _room_info_key_might_be_live_viewers(kn) and not isinstance(val, (dict, list)):
                n = _parse_int_best_effort(val, default=0)
                if 0 < n < 99_000_000:
                    best = max(best, n)

        for val in obj.values():
            if isinstance(val, (dict, list)):
                got = _extract_live_viewers_from_room_payload(val, _depth=_depth + 1)
                if got is not None:
                    best = max(best, got)

    elif isinstance(obj, list):
        for item in obj[:150]:
            got = _extract_live_viewers_from_room_payload(item, _depth=_depth + 1)
            if got is not None:
                best = max(best, got)

    return best if best > 0 else None


def _join_event_live_viewer_count_hint(event: object) -> int:
    """Concurrent viewers sometimes appear only on member/join payloads (not RoomUserSeq)."""
    c = _parse_int_best_effort(getattr(event, "count", None), default=0)
    ps = getattr(event, "pop_str", None)
    p = _parse_int_best_effort(ps, default=0) if isinstance(ps, str) else 0
    return max(c, p)


def _room_viewers_total(event: object) -> int:
    """Best-effort cumulative viewers count (TikTokLive versions differ)."""
    try:
        total_user = int(getattr(event, "total_user", 0) or 0)
    except (TypeError, ValueError):
        total_user = 0
    return total_user


def _room_viewers_current(event: object) -> int:
    """Best-effort current online viewers count (TikTokLive versions differ)."""
    total_user = _room_viewers_total(event)
    try:
        m_total = int(getattr(event, "m_total", 0) or 0)
    except (TypeError, ValueError):
        m_total = 0
    # Strong signal when TikTok fills it (usually single-anchor concurrent viewers).
    if m_total > 0:
        return m_total

    try:
        popularity = int(getattr(event, "m_popularity", 0) or 0)
    except (TypeError, ValueError):
        popularity = 0

    def _weak_metric_ok(v: int) -> bool:
        if v <= 0 or v >= 50_000_000:
            return False
        if total_user <= 0:
            return True
        if v <= total_user:
            return True
        # Shared / multi-live: cumulative total_user may stay smaller than fused-room concurrent.
        return v <= total_user * _MULTI_LIVE_POPULARITY_TO_TOTAL_USER_RATIO_CAP

    best = 0
    if _weak_metric_ok(popularity):
        best = max(best, popularity)

    ps = getattr(event, "pop_str", None)
    if isinstance(ps, str):
        parsed = _parse_int_best_effort(ps, default=0)
        if _weak_metric_ok(parsed):
            best = max(best, parsed)

    try:
        anon = int(getattr(event, "anonymous", 0) or 0)
    except (TypeError, ValueError):
        anon = 0
    if _weak_metric_ok(anon):
        best = max(best, anon)

    return best


def _room_viewers_current_metric(event: object) -> tuple[int, str]:
    """Return (viewers_current, metric_name) for RoomUserSeq-like events."""
    try:
        m_total = int(getattr(event, "m_total", 0) or 0)
    except (TypeError, ValueError):
        m_total = 0
    if m_total > 0:
        return m_total, "m_total"

    total_user = _room_viewers_total(event)

    try:
        popularity = int(getattr(event, "m_popularity", 0) or 0)
    except (TypeError, ValueError):
        popularity = 0

    def _weak_metric_ok(v: int) -> bool:
        if v <= 0 or v >= 50_000_000:
            return False
        if total_user <= 0:
            return True
        if v <= total_user:
            return True
        return v <= total_user * _MULTI_LIVE_POPULARITY_TO_TOTAL_USER_RATIO_CAP

    best = 0
    metric = ""
    if _weak_metric_ok(popularity):
        best = popularity
        metric = "popularity"

    ps = getattr(event, "pop_str", None)
    if isinstance(ps, str):
        parsed = _parse_int_best_effort(ps, default=0)
        if _weak_metric_ok(parsed) and parsed > best:
            best = parsed
            metric = "pop_str"

    try:
        anon = int(getattr(event, "anonymous", 0) or 0)
    except (TypeError, ValueError):
        anon = 0
    if _weak_metric_ok(anon) and anon > best:
        best = anon
        metric = "anonymous"

    return best, metric


_TIKTOKLIVE_LOG_ID_PATCHED = False


def _patch_tiktoklive_negative_log_id() -> None:
    """
    TikTokLive currently constructs `WebcastPushFrame(log_id=-1, ...)` inside its
    signed-websocket route, but `log_id` is validated as `>= 0` by Pydantic.
    Patch the route module's reference to clamp negative values to 0.
    """
    global _TIKTOKLIVE_LOG_ID_PATCHED
    if _TIKTOKLIVE_LOG_ID_PATCHED:
        return

    try:
        import TikTokLive.client.web.routes.fetch_signed_websocket as fetch_signed_websocket  # type: ignore
        from TikTokLive.proto import WebcastPushFrame as _WebcastPushFrame  # type: ignore
    except ImportError:
        return

    def _safe_webcast_push_frame(*args: object, **kwargs: object) -> object:
        log_id = kwargs.get("log_id")
        if isinstance(log_id, int) and log_id < 0:
            kwargs["log_id"] = 0
        return _WebcastPushFrame(*args, **kwargs)

    fetch_signed_websocket.WebcastPushFrame = _safe_webcast_push_frame  # type: ignore[attr-defined]
    _TIKTOKLIVE_LOG_ID_PATCHED = True


# TikTokLiveProto forward refs such as ``bytes.HashtagNamespace`` are evaluated under pydantic
# rebuild with ``bytes`` resolving to the builtin, not the proto package → parse raises.
_TIKTOKLIVE_PARSE_IGNORE_HASHTAG_NAMESPACE = "HashtagNamespace"


def _configure_tiktoklive_client(client: object) -> None:
    """Apply TikTokLiveClient knobs that upstream recommends extending at runtime."""
    ignore = getattr(client, "parse_error_ignorelist", None)
    if ignore is None:
        return
    if _TIKTOKLIVE_PARSE_IGNORE_HASHTAG_NAMESPACE not in ignore:
        ignore.append(_TIKTOKLIVE_PARSE_IGNORE_HASHTAG_NAMESPACE)


def _optional_event(name: str):  # noqa: ANN001
    """Import one TikTokLive event type; never fail other imports if one symbol is missing."""
    try:
        from TikTokLive import events as _tk_events  # type: ignore

        ev = getattr(_tk_events, name, None)
        if ev is not None:
            return ev

        # Back-compat: some TikTokLive versions removed/renamed certain event classes.
        # Our code and tests still treat ColdStartEvent as a supported hook.
        if name == "ColdStartEvent":

            class _ColdStartEventFallback:
                @staticmethod
                def get_type() -> str:
                    return "cold_start"

            return _ColdStartEventFallback

        return None
    except ImportError:
        return None


# Import individually so e.g. missing SubNotifyEvent never clears JoinEvent/RoomUserSeqEvent.
ColdStartEvent = _optional_event("ColdStartEvent")
FollowEvent = _optional_event("FollowEvent")
GiftEvent = _optional_event("GiftEvent")
JoinEvent = _optional_event("JoinEvent")
LikeEvent = _optional_event("LikeEvent")
RoomUserSeqEvent = _optional_event("RoomUserSeqEvent")
ShareEvent = _optional_event("ShareEvent")
SubscribeEvent = _optional_event("SubscribeEvent") or _optional_event("SubNotifyEvent")


def _normalize_unique_id(v: str) -> str:
    # TikTokLive accepts "@username" or "username"; keep stored value without "@".
    return (v or "").strip().lstrip("@").strip()


def _gift_icon_url(gift: object | None) -> str:
    if gift is None:
        return ""
    icon = getattr(gift, "icon", None)
    if icon is None:
        return ""
    urls = getattr(icon, "m_urls", None) or []
    for u in urls:
        s = str(u).strip()
        if s.startswith("http://") or s.startswith("https://"):
            return s
    return ""


def _image_like_first_url(img: object | None) -> str:
    """Best-effort URL from TikTok proto Image-like objects (url_list / m_urls)."""
    if img is None:
        return ""
    urls = getattr(img, "url_list", None) or getattr(img, "m_urls", None) or []
    if isinstance(urls, (list, tuple)):
        for u in urls:
            s = str(u).strip()
            if s.startswith("http://") or s.startswith("https://"):
                return s
    return ""


def tiktok_user_avatar_url(user: object | None) -> str:
    """Resolve viewer avatar HTTPS URL from TikTokLive user / user_info objects.

    Library/version-dependent.
    """
    if user is None:
        return ""
    for attr in ("profile_picture_url", "avatar_url", "avatar_uri"):
        v = getattr(user, attr, None)
        if isinstance(v, str) and v.startswith(("http://", "https://")):
            return v.strip()
    for attr in ("avatar_thumb", "avatar_medium", "avatar_large", "avatar"):
        u = _image_like_first_url(getattr(user, attr, None))
        if u:
            return u
    nested = getattr(user, "user_info", None)
    if nested is not None and nested is not user:
        inner = tiktok_user_avatar_url(nested)
        if inner:
            return inner
    return ""


def _display_name_from_user(user: object | None) -> str:
    if user is None:
        return "?"
    nick = getattr(user, "nickname", None)
    if nick:
        return str(nick).strip() or "?"
    raw = getattr(user, "nick_name", None) or getattr(user, "username", None)
    return str(raw or "?").strip() or "?"


_INT_RE = re.compile(r"[-+]?\d+")


def _parse_int_best_effort(v: object, *, default: int) -> int:
    if isinstance(v, bool) or v is None:
        return default
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        if v != v:  # NaN
            return default
        return int(v)
    if isinstance(v, str):
        s = v.strip().replace(",", "").replace("_", "")
        if not s:
            return default
        if s.isdigit() or (s[0] in "+-" and s[1:].isdigit()):
            try:
                return int(s)
            except (TypeError, ValueError):
                return default
        m = _INT_RE.search(s)
        if not m:
            return default
        try:
            return int(m.group(0))
        except (TypeError, ValueError):
            return default
    return default


class TikTokChatSource:
    """TikTokLive client wrapper: forwards TikTok comments into the coordinator."""

    def __init__(
        self,
        coordinator: StreamCoordinator,
        on_status: Callable[[str], None],
        on_gift: Callable[[str, str, str, int, str, str, int], None] | None = None,
        get_locale: Callable[[], str] | None = None,
        client_factory: Callable[[str], TikTokLiveClient] | None = None,
        on_room_viewers: Callable[[int], None] | None = None,
        on_room_viewers_current: Callable[[int], None] | None = None,
        on_room_viewers_total: Callable[[int], None] | None = None,
        on_follow: Callable[[str], None] | None = None,
        on_join: Callable[[str], None] | None = None,
        on_gift_analytics: Callable[[str, str, str, int, int, str], None] | None = None,
        on_like: Callable[[str, int, str], None] | None = None,
        on_share: Callable[[str, int], None] | None = None,
        on_stream_start: Callable[[], None] | None = None,
        on_paid_sub: Callable[[str], None] | None = None,
    ) -> None:
        self._coordinator = coordinator
        self._on_status = on_status
        self._on_gift = on_gift
        # Back-compat: on_room_viewers is treated as current online viewers.
        self._on_room_viewers = on_room_viewers
        self._on_room_viewers_current = on_room_viewers_current
        self._on_room_viewers_total = on_room_viewers_total
        self._on_follow = on_follow
        self._on_join = on_join
        self._on_gift_analytics = on_gift_analytics
        self._on_like = on_like
        self._on_share = on_share
        self._on_stream_start = on_stream_start
        self._on_paid_sub = on_paid_sub
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
        # If a CommentEvent doesn't expose any usable timestamp, TikTokLive may still emit
        # a small "history burst" right after connect. Suppress that short window.
        self._comment_backlog_window_sec: float = TIKTOK_COMMENT_BACKLOG_WINDOW_SEC
        # Only treat the next ConnectEvent as "new stream start" after LiveEndEvent.
        self._stream_ended = True
        # Some TikTokLive builds expose like totals (stream-level) rather than per-event batches.
        self._last_like_total: int | None = None
        self._logged_room_info_keys = False
        self._last_viewers_current: int = 0
        self._last_viewers_current_non_join_mono: float | None = None
        # Connect-time cutoffs for suppressing backlog comments.
        self._connect_cutoff_epoch: float | None = None
        self._connect_cutoff_mono: float | None = None
        # Current reconnect backoff used for status messages (read by event handlers).
        self._connect_backoff_sec: float = TIKTOK_RECONNECT_SEC

    @staticmethod
    def _room_info_viewer_candidates(payload: object) -> dict[str, int]:
        if not isinstance(payload, dict):
            return {}
        out: dict[str, int] = {}
        for k, v in payload.items():
            kn = str(k).replace("-", "_").lower()
            if not _room_info_key_might_be_live_viewers(kn):
                continue
            if isinstance(v, (dict, list)):
                continue
            n = _parse_int_best_effort(v, default=0)
            if 0 < n < 99_000_000:
                out[kn] = max(out.get(kn, 0), n)
        return out

    @property
    def running(self) -> bool:
        return self._running and self._task is not None and not self._task.done()

    def _push_room_viewers_current(self, n: int, *, reliable: bool, source: str) -> None:
        cb_cur = self._on_room_viewers_current or self._on_room_viewers
        if cb_cur is None:
            return

        v = max(0, int(n))
        if v <= 0:
            return

        if reliable:
            self._last_viewers_current = v
            self._last_viewers_current_non_join_mono = time.monotonic()
            logger.info("TikTok viewers_current=%s source=%s", v, source)
            cb_cur(v)
            return

        # Join/member payloads are inconsistent between TikTokLive versions and may represent
        # "joined since last packet" rather than concurrent viewers. Only use as a fallback
        # when it increases the best known current viewers and we haven't seen reliable updates.
        if v <= self._last_viewers_current:
            logger.info(
                "TikTok viewers_current drop ignored candidate=%s source=%s last=%s",
                v,
                source,
                self._last_viewers_current,
            )
            return

        mono0 = self._last_viewers_current_non_join_mono
        if mono0 is not None and (time.monotonic() - mono0) <= 60.0:
            logger.info(
                "TikTok viewers_current join ignored candidate=%s last=%s (reliable seen recently)",
                v,
                self._last_viewers_current,
            )
            return

        self._last_viewers_current = v
        logger.info("TikTok viewers_current=%s source=%s (unreliable)", v, source)
        cb_cur(v)

    def _enqueue_live_viewers_from_room_payload(self, payload: object) -> None:
        v = _extract_live_viewers_from_room_payload(payload)
        if v is not None and v > 0:
            cand = self._room_info_viewer_candidates(payload)
            if cand:
                logger.info("TikTok room/info viewer candidates=%s chosen=%s", cand, v)
            self._push_room_viewers_current(v, reliable=True, source="room_info")
            return
        if isinstance(payload, dict) and not self._logged_room_info_keys:
            self._logged_room_info_keys = True
            keys = sorted(str(k) for k in payload.keys())
            logger.debug("TikTok room/info: viewer fields not matched; keys(sample)=%s", keys[:70])

    async def _poll_live_viewers_http(self, client: TikTokLiveClient) -> None:
        """Fill gaps when websocket `m_total` stays 0 (TikTok payload differences)."""
        cb_cur = self._on_room_viewers_current or self._on_room_viewers
        if cb_cur is None:
            return

        async def _pull_once() -> None:
            try:
                payload = await client.web.fetch_room_info()
            except asyncio.CancelledError:
                raise
            except (
                AgeRestrictedError,
                TikTokLiveError,
                OSError,
                RuntimeError,
                ValueError,
                KeyError,
            ) as exc:
                logger.debug("TikTok viewer poll: %s", exc)
                return
            except Exception as exc:
                logger.warning("TikTok viewer poll failed: %s", exc)
                return
            self._enqueue_live_viewers_from_room_payload(payload)

        try:
            await _pull_once()
            while self._running and self._client is client:
                await asyncio.sleep(TIKTOK_VIEWERS_POLL_SEC)
                if not self._running or self._client is not client:
                    break
                await _pull_once()
        except asyncio.CancelledError:
            raise

    async def start(self, unique_id: str) -> None:
        logger.info("TikTokChatSource.start called")
        await self.stop()
        uid = _normalize_unique_id(unique_id)
        if not uid:
            self._on_status(l10n.tr(self._get_locale(), "tk.bad_username"))
            return
        self._unique_id = uid
        self._running = True
        logger.debug("TikTok supervisor start @%s", uid)
        self._task = asyncio.create_task(self._supervisor(), name="tiktok-live")

    async def stop(self) -> None:
        if self._running or self._task is not None:
            stack = "".join(traceback.format_stack(limit=12))
            logger.info("TikTokChatSource.stop called\n%s", stack)
            if self._unique_id:
                logger.debug("TikTok supervisor stop @%s", self._unique_id)
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
            # `disconnect(close_client=True)` already closes the underlying HTTP client.
            # Only attempt a direct close as a best-effort fallback if disconnect failed.
            try:
                await client.close()
            except (OSError, RuntimeError, TikTokLiveError) as exc2:
                logger.debug("TikTok close ignored: %s", exc2)

    async def _supervisor(self) -> None:
        assert self._unique_id is not None
        backoff = TIKTOK_RECONNECT_SEC
        attempt = 0
        while self._running:
            self._connect_cutoff_epoch = None
            self._connect_cutoff_mono = None
            self._connect_backoff_sec = backoff
            attempt += 1
            uid = self._unique_id
            self._logged_room_info_keys = False
            logger.info("TikTok supervisor attempt=%s uid=@%s", attempt, uid)
            logger.debug("TikTok supervisor attempt %s @%s", attempt, uid)
            client = self._client_factory(uid)
            self._client = client
            _patch_tiktoklive_negative_log_id()
            _configure_tiktoklive_client(client)

            # Handlers may be registered multiple times if the caller supplies a client_factory
            # that reuses the same client instance. Guard against duplicates.
            if not bool(getattr(client, "_cheremsha_handlers_installed", False)):
                setattr(client, "_cheremsha_handlers_installed", True)

                @client.on(ConnectEvent)
                async def _on_connect(event: ConnectEvent) -> None:  # noqa: ANN001
                    # TikTokLive may emit a small backlog of chat messages when attaching to an
                    # already-running live. Record "connected" time and suppress comments that
                    # are older than this moment (when the event provides timestamps).
                    self._connect_cutoff_epoch = time.time()
                    self._connect_cutoff_mono = time.monotonic()
                    if self._stream_ended:
                        cb = self._on_stream_start
                        if cb is not None:
                            cb()
                        self._stream_ended = False
                        self._last_like_total = None
                    self._on_status(
                        l10n.tr(self._get_locale(), "tk.connected", user=event.unique_id)
                    )

                @client.on(DisconnectEvent)
                async def _on_disconnect(_event: DisconnectEvent) -> None:  # noqa: ANN001
                    if self._running:
                        msg = l10n.tr(
                            self._get_locale(),
                            "tk.disconnected_retry",
                            sec=self._connect_backoff_sec,
                        )
                        self._on_status(msg)

                @client.on(LiveEndEvent)
                async def _on_live_end(_event: LiveEndEvent) -> None:  # noqa: ANN001
                    if self._running:
                        self._stream_ended = True
                        self._on_status(
                            l10n.tr(
                                self._get_locale(),
                                "tk.live_ended_retry",
                                sec=self._connect_backoff_sec,
                            )
                        )

                @client.on(CommentEvent)
                async def _on_comment(event: CommentEvent) -> None:  # noqa: ANN001
                    cutoff = self._connect_cutoff_epoch
                    if cutoff is not None:
                        # Best-effort event time extraction (TikTokLive differs between versions).
                        # Common fields observed: create_time (epoch sec), timestamp (epoch ms/sec).
                        base_msg = getattr(event, "base_message", None)
                        raw_ts = (
                            getattr(event, "create_time", None)
                            or getattr(event, "timestamp", None)
                            or getattr(event, "time", None)
                            or getattr(event, "event_time", None)
                            or getattr(base_msg, "create_time", None)
                            or getattr(base_msg, "timestamp", None)
                            or getattr(base_msg, "server_time", None)
                        )
                        event_epoch: float | None = None
                        if isinstance(raw_ts, datetime):
                            event_epoch = raw_ts.replace(tzinfo=UTC).timestamp()
                        elif isinstance(raw_ts, (int, float)):
                            # Heuristic: treat very large numbers as ms.
                            v = float(raw_ts)
                            event_epoch = (v / 1000.0) if v > 3_000_000_000 else v
                        elif isinstance(raw_ts, str):
                            s = raw_ts.strip()
                            if s.isdigit():
                                v = float(s)
                                event_epoch = (v / 1000.0) if v > 3_000_000_000 else v
                        if event_epoch is not None:
                            if event_epoch < cutoff:
                                return
                        else:
                            # Fallback: if the library doesn't expose timestamps for comments,
                            # suppress a short backlog window right after connect.
                            mono0 = self._connect_cutoff_mono
                            if (
                                mono0 is not None
                                and (time.monotonic() - mono0)
                                <= self._comment_backlog_window_sec
                            ):
                                return

                    user_blob = getattr(event, "user_info", None) or getattr(event, "user", None)
                    author = getattr(user_blob, "nickname", None) or "unknown"
                    text = (
                        getattr(event, "comment", None)
                        or getattr(event, "content", None)
                        or ""
                    )
                    msg = ChatMessage(
                        author=str(author),
                        text=str(text),
                        platform=ChatPlatform.TIKTOK,
                        received_at=datetime.now(UTC),
                        author_avatar_url=tiktok_user_avatar_url(user_blob),
                    )
                    await self._coordinator.enqueue_chat(msg)

            if ColdStartEvent is not None:

                @client.on(ColdStartEvent)  # type: ignore[misc]
                async def _on_cold_start(event: object) -> None:  # noqa: ANN001
                    vc = _parse_int_best_effort(getattr(event, "viewer_count", None), default=0)
                    tc = _parse_int_best_effort(getattr(event, "total_count", None), default=0)
                    if vc > 0:
                        logger.info(
                            "TikTok ColdStart viewer_count=%s total_count=%s",
                            vc,
                            tc,
                        )
                        self._push_room_viewers_current(vc, reliable=True, source="cold_start")
                    cb_tot = self._on_room_viewers_total
                    if cb_tot is not None and tc > 0:
                        cb_tot(tc)

            if RoomUserSeqEvent is not None:

                @client.on(RoomUserSeqEvent)  # type: ignore[misc]
                async def _on_room_users(event: object) -> None:  # noqa: ANN001
                    cur, metric = _room_viewers_current_metric(event)
                    tot = _room_viewers_total(event)
                    # TikTok often includes total_user while m_total stays 0; pushing 0
                    # would constantly reset the dashboard "online" counter.
                    if cur > 0:
                        logger.info(
                            "TikTok RoomUserSeq cur=%s m_total=%s total_user=%s "
                            "pop=%s pop_str=%s anon=%s",
                            cur,
                            getattr(event, "m_total", None),
                            getattr(event, "total_user", None),
                            getattr(event, "m_popularity", None),
                            getattr(event, "pop_str", None),
                            getattr(event, "anonymous", None),
                        )
                        # `anonymous` is commonly a small value unrelated to concurrent viewers.
                        # Allow decreases only when TikTok provides m_total.
                        if metric == "m_total":
                            reliable = True
                        elif metric == "anonymous":
                            reliable = False
                        else:
                            reliable = cur >= self._last_viewers_current
                        self._push_room_viewers_current(
                            cur,
                            reliable=reliable,
                            source=f"room_user_seq:{metric or 'unknown'}",
                        )
                    cb_tot = self._on_room_viewers_total
                    # Avoid pushing total_user=0 (common while TikTok omits totals on some WS
                    # packets).
                    if cb_tot is not None and tot > 0:
                        cb_tot(tot)

            if FollowEvent is not None:

                @client.on(FollowEvent)  # type: ignore[misc]
                async def _on_follow(event: object) -> None:  # noqa: ANN001
                    cb = self._on_follow
                    if cb is None:
                        return
                    user = getattr(event, "user", None)
                    cb(_display_name_from_user(user))

            if JoinEvent is not None:

                @client.on(JoinEvent)  # type: ignore[misc]
                async def _on_join(event: object) -> None:  # noqa: ANN001
                    cb = self._on_join
                    if cb is not None:
                        user = getattr(event, "user", None)
                        cb(_display_name_from_user(user))
                    n = _join_event_live_viewer_count_hint(event)
                    if n > 0:
                        logger.info(
                            "TikTok Join viewer_hint=%s raw_count=%s pop_str=%s",
                            n,
                            getattr(event, "count", None),
                            getattr(event, "pop_str", None),
                        )
                        self._push_room_viewers_current(n, reliable=False, source="join_hint")

            if LikeEvent is not None:

                @client.on(LikeEvent)  # type: ignore[misc]
                async def _on_like(event: object) -> None:  # noqa: ANN001
                    cb = self._on_like
                    if cb is None:
                        return
                    user = getattr(event, "user", None) or getattr(event, "user_info", None)
                    avatar_u = tiktok_user_avatar_url(user)
                    # Best-effort: TikTokLive differs between versions:
                    # - some expose per-event batch count
                    # - some expose a stream-level running total (often likeCount)
                    raw_like_total = getattr(event, "likeCount", None) or getattr(
                        event, "likes", None
                    )
                    total_i = _parse_int_best_effort(raw_like_total, default=-1)
                    if total_i >= 0:
                        prev_total = self._last_like_total
                        self._last_like_total = total_i
                        if prev_total is None:
                            n_i = max(1, total_i)
                        else:
                            n_i = total_i - prev_total
                            if n_i <= 0:
                                n_i = 1
                        cb(_display_name_from_user(user), n_i, avatar_u)
                        return

                    raw_batch = (
                        getattr(event, "like_count", None) or getattr(event, "count", None) or 1
                    )
                    n_i = _parse_int_best_effort(raw_batch, default=1)
                    cb(_display_name_from_user(user), max(1, n_i), avatar_u)

            if ShareEvent is not None:

                @client.on(ShareEvent)  # type: ignore[misc]
                async def _on_share(event: object) -> None:  # noqa: ANN001
                    cb = self._on_share
                    if cb is None:
                        return
                    user = getattr(event, "user", None) or getattr(event, "user_info", None)
                    raw_n = (
                        getattr(event, "count", None) or getattr(event, "share_count", None) or 1
                    )
                    try:
                        n = int(raw_n)
                    except (TypeError, ValueError):
                        n = 1
                    cb(_display_name_from_user(user), max(1, n))

            if SubscribeEvent is not None:

                @client.on(SubscribeEvent)  # type: ignore[misc]
                async def _on_paid_sub(event: object) -> None:  # noqa: ANN001
                    cb = self._on_paid_sub
                    if cb is None:
                        return
                    user = getattr(event, "user", None) or getattr(event, "user_info", None)
                    cb(_display_name_from_user(user))

            # Gifts support (optional in library builds).
            self._gift_event_supported = GiftEvent is not None
            if GiftEvent is None:
                logger.info("TikTok gifts disabled: TikTokLive.events.GiftEvent not available")
            else:
                logger.info("TikTok gifts enabled: GiftEvent handler registered")

            if GiftEvent is not None:

                @client.on(GiftEvent)  # type: ignore[misc]
                async def _on_gift(event: object) -> None:  # noqa: ANN001
                    cb = self._on_gift
                    if cb is None and self._on_gift_analytics is None:
                        logger.debug("TikTok gift received but no gift callbacks are configured")
                        return
                    # Best-effort extraction (TikTokLive differs between versions).
                    user_obj = getattr(event, "user", None)
                    sender_avatar = tiktok_user_avatar_url(user_obj)
                    user = getattr(user_obj, "nickname", None) or getattr(
                        user_obj, "unique_id", None
                    )
                    gift = getattr(event, "gift", None)
                    gift_id = getattr(gift, "id", None) or getattr(gift, "gift_id", None) or ""
                    gift_name = (
                        getattr(gift, "name", None) or getattr(gift, "gift_name", None) or ""
                    )
                    count = (
                        getattr(event, "repeat_count", None) or getattr(event, "count", None) or 1
                    )
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
                                (
                                    "TikTok gift suppressed (repeat_end=False): "
                                    "sender=%s gift_id=%s gift_name=%s count=%s"
                                ),
                                sender_s,
                                gift_id_s,
                                gift_name_s,
                                count_i,
                            )
                            return
                    elif isinstance(streaking, bool) and streaking:
                        logger.info(
                            (
                                "TikTok gift suppressed (streaking=True): "
                                "sender=%s gift_id=%s gift_name=%s count=%s"
                            ),
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
                            (
                                "TikTok gift suppressed (dedupe %.1fs): "
                                "sender=%s gift_id=%s gift_name=%s count=%s"
                            ),
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
                        self._gift_dedupe = {
                            kk: ts for kk, ts in self._gift_dedupe.items() if ts >= cutoff
                        }
                    logger.info(
                        "TikTok gift: sender=%s gift_id=%s gift_name=%s count=%s",
                        sender_s,
                        gift_id_s,
                        gift_name_s,
                        count_i,
                    )
                    icon_url = _gift_icon_url(gift)
                    diamond_each = 0
                    if gift is not None:
                        try:
                            diamond_each = int(getattr(gift, "diamond_count", 0) or 0)
                        except (TypeError, ValueError):
                            diamond_each = 0
                    diamonds_total = diamond_each * max(1, count_i)
                    ga = self._on_gift_analytics
                    if ga is not None:
                        ga(sender_s, gift_id_s, gift_name_s, count_i, diamonds_total, icon_url)
                    if cb is not None:
                        cb(
                            sender_s,
                            gift_id_s,
                            gift_name_s,
                            count_i,
                            icon_url,
                            sender_avatar,
                            diamond_each,
                        )

            try:
                # TikTokLive docs: using connect/start just to check "is live" is inefficient.
                # We poll via is_live() and only connect once the creator is live.
                self._on_status(l10n.tr(self._get_locale(), "tk.connecting", user=uid))
                try:
                    live = await client.is_live()
                except UserNotFoundError:
                    msg = l10n.tr(self._get_locale(), "tk.user_not_found", user=uid, sec=backoff)
                    self._on_status(msg)
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
                    msg = l10n.tr(self._get_locale(), "tk.user_offline", user=uid, sec=backoff)
                    self._on_status(msg)
                else:
                    # Keep WS connect independent of `/room/info` (HTTP may fail while WS works).
                    t = await client.start(fetch_room_info=False, fetch_gift_info=True)
                    poll_task = asyncio.create_task(
                        self._poll_live_viewers_http(client),
                        name="tiktok-room-viewers",
                    )
                    try:
                        await t
                    finally:
                        poll_task.cancel()
                        await asyncio.gather(poll_task, return_exceptions=True)
            except asyncio.CancelledError:
                raise
            except UserOfflineError:
                # Normal case when the creator is not live.
                msg = l10n.tr(self._get_locale(), "tk.user_offline", user=uid, sec=backoff)
                self._on_status(msg)
            except UserNotFoundError:
                msg = l10n.tr(self._get_locale(), "tk.user_not_found", user=uid, sec=backoff)
                self._on_status(msg)
            except AgeRestrictedError:
                msg = l10n.tr(self._get_locale(), "tk.age_restricted", user=uid, sec=backoff)
                self._on_status(msg)
            except SignatureRateLimitError as exc:
                # Wait what the library tells us (retry_after), but cap at a sane min.
                wait = max(float(getattr(exc, "retry_after", backoff)), backoff)
                self._on_status(l10n.tr(self._get_locale(), "tk.rate_limited", sec=wait))
                await asyncio.sleep(wait)
            except (TikTokLiveError, OSError, RuntimeError) as exc:
                logger.warning("TikTokLive error: %s", exc)
                msg = l10n.tr(self._get_locale(), "tk.error_retry", err=str(exc), sec=backoff)
                self._on_status(msg)
            except Exception as exc:
                # TikTokLive occasionally raises unexpected wrapper errors; do not let the
                # supervisor task die, keep retrying instead.
                logger.exception("TikTokLive unexpected error: %s", exc)
                msg = l10n.tr(self._get_locale(), "tk.error_retry", err=str(exc), sec=backoff)
                self._on_status(msg)
            finally:
                await self._close_client()

            if not self._running:
                logger.info("TikTok supervisor stopping (running flag false)")
                logger.debug("TikTok supervisor stopping")
                break
            try:
                logger.info("TikTok supervisor sleep %.1fs then retry", backoff)
                logger.debug("TikTok supervisor sleep %.1fs then retry", backoff)
                await asyncio.sleep(backoff)
            except asyncio.CancelledError:
                raise
        logger.info(
            "TikTok supervisor exited (running=%s task_done=%s)",
            self._running,
            self._task.done() if self._task else None,
        )
        logger.debug("TikTok supervisor exited")
