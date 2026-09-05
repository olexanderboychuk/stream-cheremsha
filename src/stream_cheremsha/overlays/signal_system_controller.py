from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any
from urllib.parse import urlparse

from PySide6.QtCore import QObject, QSettings, QTimer

from stream_cheremsha import l10n
from stream_cheremsha.overlays.pubsub import OverlayPubSub
from stream_cheremsha.overlays.signal_system_overlay_config import (
    SignalSystemOverlayConfig,
    load_signal_system_overlay_config,
    signal_system_overlay_config_to_public_dict,
)

_LOG = logging.getLogger(__name__)
_PUBLISH_DEBOUNCE_MS = 150
_DISPATCH_TICK_MS = 250


# Explicit presentation states consumed by the renderer state machine.
# IDLE -> DETECTING -> ACQUIRING -> DECODING -> ACTIVE -> PEAK -> DISCHARGE
#   -> LOST -> RETURN_TO_IDLE. Renderer derives phase from elapsed time,
# but the backend guarantees single-active-event + priority + cooldowns.
EVENT_PHASES: tuple[str, ...] = (
    "idle",
    "detecting",
    "acquiring",
    "decoding",
    "active",
    "peak",
    "discharge",
    "lost",
    "return_to_idle",
)

# Hosts the renderer is allowed to load gift icons from. Defensive:
# never let a raw payload force the OBS widget to fetch arbitrary URLs.
_ALLOWED_GIFT_ICON_HOSTS: tuple[str, ...] = (
    "tiktokcdn.com",
    "tiktokcdn-us.com",
    "tiktokcdn-eu.com",
    "ibytedtos.com",
)


def _is_allowed_gift_icon_url(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except (ValueError, AttributeError):
        return False
    if not host:
        return False
    return any(host == h or host.endswith("." + h) for h in _ALLOWED_GIFT_ICON_HOSTS)


def _safe_str(v: Any, *, limit: int = 64) -> str:
    try:
        s = str(v or "").strip()
    except (ValueError, TypeError):
        return ""
    if len(s) > limit:
        s = s[:limit]
    # Never leak raw null-ish tokens into the overlay.
    if s.lower() in ("none", "null", "nan", "undefined"):
        return ""
    return s


@dataclass
class SignalGiftData:
    """Normalized presentation model for a TikTok gift transmission.

    The renderer consumes this (flattened into SignalEvent) rather than
    depending on raw TikTok payload quirks.
    """

    gift_id: str = ""
    gift_name: str = ""
    gift_icon_url: str = ""
    gift_icon_source: str = "none"  # "live" | "catalog" | "none"
    quantity: int = 1
    coins: int = 0
    sender: str = ""


@dataclass
class SignalEvent:
    id: str
    # big_gift | mega_gift | milestone | activity_surge | ai_observation
    # | unknown_signal
    type: str
    # Priority: milestone=100, mega=90, big_gift=80, ai=60, surge=40,
    # unknown=20
    priority: int
    title: str
    subtitle: str
    username: str
    value: str
    intensity: float  # 0.0 to 1.0
    duration_ms: int
    created_at: float
    # Normalized gift presentation model (flattened for wire compat)
    gift_id: str = ""
    gift_name: str = ""
    gift_icon_url: str = ""
    gift_icon_source: str = "none"
    gift_quantity: int = 1
    coin_value: int = 0
    sender_avatar_url: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # Keep wire payload JSON-safe.
        meta = d.get("metadata")
        if not isinstance(meta, dict):
            d["metadata"] = {}
        return d


class SignalSystemController(QObject):
    def __init__(
        self,
        *,
        pubsub: OverlayPubSub | None,
        get_locale: Callable[[], str] | None = None,
        instance: str = "main",
        settings: QSettings | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._pubsub = pubsub
        self._settings = settings
        self._get_locale = get_locale or (lambda: "uk")
        self._instance = str(instance or "main").strip() or "main"
        self._publish_handle: asyncio.TimerHandle | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

        self._start_time = time.time()
        self._event_seq = 0
        self._current_event: SignalEvent | None = None
        self._current_event_end_time = 0.0
        self._last_event_finish_time = 0.0

        self._pending_events: list[SignalEvent] = []
        self._activity_timestamps: deque[float] = deque(maxlen=200)

        # Cooldown trackers (timestamps)
        self._last_ai_time = 0.0
        self._last_unknown_time = 0.0
        self._last_surge_time = 0.0
        self._ai_observation_timestamps: deque[float] = deque(maxlen=12)
        # Rolling high-frequency coalescing window (likes/follows/shares)
        self._burst_window: deque[float] = deque(maxlen=400)
        self._last_burst_surge_time = 0.0

        self._dispatch_timer = QTimer(self)
        self._dispatch_timer.setInterval(_DISPATCH_TICK_MS)
        self._dispatch_timer.timeout.connect(self._on_dispatch_tick)

    def set_pubsub(self, pubsub: OverlayPubSub | None) -> None:
        self._pubsub = pubsub

    def set_event_loop(self, loop: asyncio.AbstractEventLoop | None) -> None:
        self._loop = loop

    def start(self) -> None:
        self._dispatch_timer.start()
        self.schedule_publish()

    def stop(self) -> None:
        self._dispatch_timer.stop()
        if self._publish_handle is not None:
            self._publish_handle.cancel()
            self._publish_handle = None

    def reload_config(self) -> None:
        self.schedule_publish()

    def _get_config(self) -> SignalSystemOverlayConfig:
        return load_signal_system_overlay_config(self._settings)

    def _tr(self, key: str, **kwargs: object) -> str:
        return l10n.tr(str(self._get_locale() or "uk"), key, **kwargs)

    def _coins_label(self, n: int) -> str:
        return self._tr("signal_system.goal.coins_fmt", n=f"{int(n):,}")

    def _per_min_label(self, n: int) -> str:
        return self._tr("signal_system.goal.per_min_fmt", n=int(n))

    def _get_activity_rate(self) -> int:
        now = time.time()
        cutoff = now - 30.0
        while self._activity_timestamps and self._activity_timestamps[0] < cutoff:
            self._activity_timestamps.popleft()
        # Returns estimated events per minute based on 30s window
        return len(self._activity_timestamps) * 2

    def initial_state(self) -> dict[str, Any]:
        cfg = self._get_config()
        return {
            "config": signal_system_overlay_config_to_public_dict(cfg),
            "locale": self._get_locale(),
            "current_event": self._current_event.to_dict() if self._current_event else None,
            "event_seq": self._event_seq,
            "idle_metrics": {
                "activity_rate": self._get_activity_rate(),
                "system_status": "ONLINE",
                "uptime_s": int(time.time() - self._start_time),
            },
        }

    def _queue_event(self, event: SignalEvent, *, force_immediate: bool = False) -> None:
        cfg = self._get_config()
        if not getattr(cfg, "enabled", True) and not force_immediate:
            return
        if force_immediate:
            # For testing: interrupt current event if any or place at front
            self._event_seq += 1
            self._current_event = event
            self._current_event_end_time = time.time() + (event.duration_ms / 1000.0)
            self._pending_events.clear()
            self.schedule_publish()
            # Qt UI triggers run off the asyncio thread; flush immediately so
            # browser sources see the event without waiting on loop scheduling.
            self._flush_publish()
            return

        # Check queue length (keep max 3 pending)
        self._pending_events.append(event)
        self._pending_events.sort(key=lambda e: (-e.priority, e.created_at))
        if len(self._pending_events) > 3:
            self._pending_events = self._pending_events[:3]

        self._on_dispatch_tick()

    def _global_cooldown_sec(self, cfg: SignalSystemOverlayConfig) -> float:
        try:
            g = float(getattr(cfg, "global_cooldown_ms", 8000)) / 1000.0
        except (TypeError, ValueError):
            g = 8.0
        try:
            legacy = float(cfg.cooldown_ms) / 1000.0
        except (TypeError, ValueError):
            legacy = 3.0
        return max(1.0, min(30.0, g), max(0.5, min(15.0, legacy)))

    def _on_dispatch_tick(self) -> None:
        now = time.time()

        # Check if current event has completed
        if self._current_event is not None:
            if now >= self._current_event_end_time:
                self._current_event = None
                self._last_event_finish_time = now
                self.schedule_publish()
            else:
                # Active cinematic signal must NOT be randomly interrupted.
                # Only CRITICAL/MEGA (priority >= 90) may supersede, and only
                # if strictly higher priority than the running event.
                if self._pending_events:
                    top = self._pending_events[0]
                    if top.priority >= 90 and top.priority > self._current_event.priority:
                        self._current_event = self._pending_events.pop(0)
                        self._event_seq += 1
                        dur_s = self._current_event.duration_ms / 1000.0
                        self._current_event_end_time = now + dur_s
                        self.schedule_publish()
            return
        if not self._pending_events:
            return
        cfg = self._get_config()
        cooldown_sec = self._global_cooldown_sec(cfg)
        if (now - self._last_event_finish_time) < cooldown_sec:
            return
        # Cooldown expired, dispatch next event
        next_event = self._pending_events.pop(0)
        self._event_seq += 1
        self._current_event = next_event
        self._current_event_end_time = now + (next_event.duration_ms / 1000.0)
        self.schedule_publish()

    # --- Ingestion Methods ---

    def _normalize_gift(
        self,
        *,
        gift_name: str,
        count: int,
        tiktok_coin_each: int | None,
        extra: dict[str, Any] | None,
        sender: str,
    ) -> SignalGiftData:
        try:
            c = max(1, int(count))
        except (TypeError, ValueError):
            c = 1
        c = min(c, 9999)
        try:
            each = max(0, int(tiktok_coin_each or 0))
        except (TypeError, ValueError):
            each = 0
        total_coins = c * each

        ex: dict[str, Any] = extra if isinstance(extra, dict) else {}
        raw_gift_id = _safe_str(ex.get("gift_id"), limit=64)
        raw_icon = _safe_str(ex.get("icon_url") or ex.get("gift_icon_url"), limit=512)
        avatar = _safe_str(ex.get("sender_avatar_url") or ex.get("avatar_url"), limit=512)
        if avatar and not (avatar.startswith("http://") or avatar.startswith("https://")):
            avatar = ""
        name = _safe_str(gift_name, limit=48)

        icon_url = ""
        icon_source = "none"
        if raw_icon and (raw_icon.startswith("http://") or raw_icon.startswith("https://")):
            if _is_allowed_gift_icon_url(raw_icon):
                icon_url = raw_icon
                icon_source = "live"
        if not icon_url and (raw_gift_id or name):
            try:
                from stream_cheremsha.actions.tiktok_gifts import (
                    tiktok_catalog_gift_image_url as _catalog_url,
                )

                resolved = _catalog_url(gift_id=raw_gift_id, gift_name=name)
            except (ImportError, AttributeError, TypeError, ValueError):
                resolved = ""
            if resolved and (resolved.startswith("http://") or resolved.startswith("https://")):
                if _is_allowed_gift_icon_url(resolved):
                    icon_url = resolved
                    icon_source = "catalog"
        return SignalGiftData(
            gift_id=raw_gift_id,
            gift_name=name,
            gift_icon_url=icon_url,
            gift_icon_source=icon_source,
            quantity=c,
            coins=total_coins,
            sender=_safe_str(sender, limit=48),
        )

    def on_gift(
        self,
        sender: str,
        gift_name: str,
        count: int,
        tiktok_coin_each: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        cfg = self._get_config()
        if not getattr(cfg, "enabled", True):
            return
        now = time.time()
        self._activity_timestamps.append(now)
        self._burst_window.append(now)

        gift = self._normalize_gift(
            gift_name=gift_name,
            count=count,
            tiktok_coin_each=tiktok_coin_each,
            extra=extra,
            sender=sender,
        )
        total_coins = gift.coins
        if total_coins < cfg.min_gift_coins_for_event:
            self._maybe_trigger_burst_surge(now)
            return

        is_mega = total_coins >= 10000
        if is_mega:
            intensity = min(1.0, 0.75 + (total_coins / 45000.0) * 0.25)
            duration_ms = int(6000 + min(3000, total_coins * 0.05))
            ev_type = "mega_gift"
            priority = 90
            title = self._tr("signal_system.goal.mega")
        else:
            intensity = min(1.0, 0.4 + (total_coins / 5000.0) * 0.6)
            duration_ms = int(4000 + min(4000, total_coins * 1.5))
            ev_type = "big_gift"
            priority = 80
            title = self._tr("signal_system.goal.detected")
        username = gift.sender or self._tr("signal_system.goal.anonymous")
        gift_label = (gift.gift_name or self._tr("signal_system.goal.gift")).upper()
        ex_avatar = ""
        if isinstance(extra, dict):
            ex_avatar = _safe_str(
                extra.get("sender_avatar_url") or extra.get("avatar_url"), limit=512
            )
            if ex_avatar and not (
                ex_avatar.startswith("http://") or ex_avatar.startswith("https://")
            ):
                ex_avatar = ""

        event = SignalEvent(
            id=str(uuid.uuid4())[:8],
            type=ev_type,
            priority=priority,
            title=title,
            subtitle=f"{gift_label} x{gift.quantity}",
            username=username,
            value=self._coins_label(total_coins),
            intensity=round(intensity, 2),
            duration_ms=duration_ms,
            created_at=now,
            gift_id=gift.gift_id,
            gift_name=gift.gift_name,
            gift_icon_url=gift.gift_icon_url,
            gift_icon_source=gift.gift_icon_source,
            gift_quantity=gift.quantity,
            coin_value=total_coins,
            sender_avatar_url=ex_avatar,
            metadata={"gift_id": gift.gift_id, "icon_source": gift.gift_icon_source},
        )
        self._queue_event(event)

    def _maybe_trigger_burst_surge(self, now: float) -> None:
        """Aggregate high-frequency low-value activity into a surge event."""
        cutoff = now - 15.0
        while self._burst_window and self._burst_window[0] < cutoff:
            self._burst_window.popleft()
        if len(self._burst_window) < 25:
            return
        if (now - self._last_burst_surge_time) < 30.0:
            return
        cfg = self._get_config()
        if not cfg.activity_surge_enabled:
            return
        self._last_burst_surge_time = now
        self._last_surge_time = now
        rate = self._get_activity_rate()
        event = SignalEvent(
            id=str(uuid.uuid4())[:8],
            type="activity_surge",
            priority=40,
            title=self._tr("signal_system.goal.overdrive"),
            subtitle=self._tr("signal_system.goal.surge_sub"),
            username="",
            value=self._per_min_label(rate),
            intensity=0.8,
            duration_ms=4500,
            created_at=now,
            metadata={"burst_count": len(self._burst_window)},
        )
        self._queue_event(event)

    def on_milestone(
        self,
        title: str = "",
        subtitle: str = "",
        milestone_type: str | None = None,
        username: str = "",
        value: str = "",
        count: int | None = None,
        target: int | None = None,
    ) -> None:
        cfg = self._get_config()
        if not cfg.milestones_enabled:
            return
        now = time.time()
        if title:
            t = title.upper()
        else:
            t = self._tr("signal_system.goal.milestone_default")
        if subtitle:
            s = subtitle.upper()
        else:
            s = self._tr("signal_system.goal.milestone_sub")
        event = SignalEvent(
            id=str(uuid.uuid4())[:8],
            type="milestone",
            priority=100,
            title=t,
            subtitle=s,
            username=str(username or "").strip(),
            value=str(value or "").strip(),
            intensity=1.0,
            duration_ms=6000,
            created_at=now,
        )
        self._queue_event(event)

    def on_activity_surge(self, score: float = 0.0, state: str = "surge", **kwargs: Any) -> None:
        level = kwargs.pop("level", None)
        count = kwargs.pop("count", None)
        top_chatter = kwargs.pop("top_chatter", None)
        if level is not None:
            try:
                score = float(level)
            except (TypeError, ValueError):
                score = 0.0
        cfg = self._get_config()
        if not cfg.activity_surge_enabled:
            return
        now = time.time()
        if (now - self._last_surge_time) < 20.0:
            return
        self._last_surge_time = now

        rate = self._get_activity_rate()
        intensity = max(0.55, min(0.95, 0.6 + float(score or 0.0) * 0.3))
        chatter = _safe_str(top_chatter, limit=32)
        event = SignalEvent(
            id=str(uuid.uuid4())[:8],
            type="activity_surge",
            priority=40,
            title=self._tr("signal_system.goal.overdrive"),
            subtitle=self._tr("signal_system.goal.surge_sub"),
            username=chatter,
            value=self._per_min_label(rate),
            intensity=round(intensity, 2),
            duration_ms=4500,
            created_at=now,
            metadata={"score": float(score or 0.0), "count": count},
        )
        self._queue_event(event)

    def on_ai_observation(self, text: str, confidence: float = 0.95) -> None:
        cfg = self._get_config()
        if not cfg.ai_observations_enabled:
            return
        now = time.time()
        try:
            ai_cd = float(getattr(cfg, "ai_observation_cooldown_ms", 300000)) / 1000.0
        except (TypeError, ValueError):
            ai_cd = 300.0
        ai_cd = max(30.0, min(3600.0, ai_cd))
        if (now - self._last_ai_time) < ai_cd:
            return
        # Max N per hour sliding window.
        try:
            max_per_hour = int(getattr(cfg, "ai_observation_max_per_hour", 3))
        except (TypeError, ValueError):
            max_per_hour = 3
        max_per_hour = max(1, min(12, max_per_hour))
        hour_ago = now - 3600.0
        while self._ai_observation_timestamps and self._ai_observation_timestamps[0] < hour_ago:
            self._ai_observation_timestamps.popleft()
        if len(self._ai_observation_timestamps) >= max_per_hour:
            return
        self._last_ai_time = now
        self._ai_observation_timestamps.append(now)

        clean = _safe_str(text, limit=90) or self._tr("signal_system.goal.ai_default_sub")
        try:
            conf = max(0.0, min(1.0, float(confidence)))
        except (TypeError, ValueError):
            conf = 0.95
        event = SignalEvent(
            id=str(uuid.uuid4())[:8],
            type="ai_observation",
            priority=60,
            title=self._tr("signal_system.goal.ai_title"),
            subtitle=clean.upper()[:45],
            username="",
            value=f"{self._tr('signal_system.overlay.conf')}: {int(conf * 100)}%",
            intensity=0.75,
            duration_ms=5000,
            created_at=now,
            metadata={"full_text": clean, "confidence": conf},
        )
        self._queue_event(event)

    def on_unknown_signal(self, code: str = "", reason: str = "") -> None:
        cfg = self._get_config()
        if not cfg.unknown_signals_enabled:
            return
        now = time.time()
        try:
            unk_cd = float(getattr(cfg, "unknown_signal_cooldown_ms", 900000)) / 1000.0
        except (TypeError, ValueError):
            unk_cd = 900.0
        unk_cd = max(60.0, min(3600.0, unk_cd))
        if (now - self._last_unknown_time) < unk_cd:
            return
        self._last_unknown_time = now

        event = SignalEvent(
            id=str(uuid.uuid4())[:8],
            type="unknown_signal",
            priority=20,
            title=self._tr("signal_system.goal.anomaly_title"),
            subtitle=(
                _safe_str(reason, limit=45) or self._tr("signal_system.goal.anomaly_sub")
            ).upper(),
            username="",
            value=_safe_str(code, limit=48) or "0x7F9A::DEEP_SCAN",
            intensity=0.9,
            duration_ms=4500,
            created_at=now,
        )
        self._queue_event(event)

    def _track_burst(self, *, weight: int = 1) -> None:
        now = time.time()
        for _ in range(max(1, min(10, int(weight)))):
            self._activity_timestamps.append(now)
            self._burst_window.append(now)
        self._maybe_trigger_burst_surge(now)

    def on_follow(self, user: str = "", stable_key: str = "", unique_id: str = "") -> None:
        self._track_burst(weight=1)

    def on_like(self, user: str = "", count: int = 1, profile_picture_url: str = "") -> None:
        try:
            w = max(1, int(count))
        except (TypeError, ValueError):
            w = 1
        self._track_burst(weight=min(w, 10))

    def on_share(self, user: str = "", count: int = 1) -> None:
        self._track_burst(weight=2)

    def on_comment(
        self, user: str = "", text: str = "", stable_key: str = "", unique_id: str = ""
    ) -> None:
        self._track_burst(weight=1)

    def trigger_test_event(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        now = time.time()
        et = str(event_type or "").strip().lower()
        pl: dict[str, Any] = dict(payload) if isinstance(payload, dict) else {}

        def _pl_str(key: str, default: str = "") -> str:
            v = pl.get(key, default)
            return _safe_str(v, limit=64) or default

        def _pl_int(key: str, default: int) -> int:
            try:
                return int(pl.get(key, default))
            except (TypeError, ValueError):
                return default

        # Resolve a sample gift icon through the real catalog pipeline so
        # testing exercises the production resolution path.
        sample_icon = ""
        sample_source = "none"
        # Default to a real catalog gift so dev/test triggers exercise the
        # full icon acquisition path (explicit payloads may override it).
        sample_name = _pl_str("gift_name", "Galaxy")
        try:
            from stream_cheremsha.actions.tiktok_gifts import (
                tiktok_catalog_gift_image_url as _catalog_url,
            )

            resolved = _catalog_url(gift_id=_pl_str("gift_id", ""), gift_name=sample_name)
            if resolved and _is_allowed_gift_icon_url(resolved):
                sample_icon = resolved
                sample_source = "catalog"
        except (ImportError, AttributeError, TypeError, ValueError):
            sample_icon = ""
        live_icon = _safe_str(pl.get("gift_icon_url"), limit=512)
        if live_icon and _is_allowed_gift_icon_url(live_icon):
            sample_icon = live_icon
            sample_source = "live"

        if et == "big_gift":
            qty = max(1, _pl_int("gift_quantity", 3))
            coins = max(1, _pl_int("coins", 2500))
            event = SignalEvent(
                id=str(uuid.uuid4())[:8],
                type="big_gift",
                priority=80,
                title=self._tr("signal_system.goal.detected"),
                subtitle=f"{sample_name.upper()} x{qty}",
                username=_pl_str("username", "KODI THE CAT"),
                value=self._coins_label(coins),
                intensity=0.85,
                duration_ms=5000,
                created_at=now,
                gift_id=_pl_str("gift_id", ""),
                gift_name=sample_name,
                gift_icon_url=sample_icon,
                gift_icon_source=sample_source,
                gift_quantity=qty,
                coin_value=coins,
                metadata={"icon_source": sample_source},
            )
        elif et == "mega_gift":
            qty = max(1, _pl_int("gift_quantity", 10))
            coins = max(10000, _pl_int("coins", 25000))
            event = SignalEvent(
                id=str(uuid.uuid4())[:8],
                type="mega_gift",
                priority=90,
                title=self._tr("signal_system.goal.mega"),
                subtitle=f"{sample_name.upper()} x{qty}",
                username=_pl_str("username", "KODI THE CAT"),
                value=self._coins_label(coins),
                intensity=1.0,
                duration_ms=7000,
                created_at=now,
                gift_id=_pl_str("gift_id", ""),
                gift_name=sample_name,
                gift_icon_url=sample_icon,
                gift_icon_source=sample_source,
                gift_quantity=qty,
                coin_value=coins,
                metadata={"icon_source": sample_source},
            )
        elif et == "milestone":
            event = SignalEvent(
                id=str(uuid.uuid4())[:8],
                type="milestone",
                priority=100,
                title=self._tr("signal_system.goal.milestone_reached"),
                subtitle=self._tr("signal_system.goal.milestone_test_sub"),
                username=self._tr("signal_system.goal.community"),
                value=self._tr("signal_system.goal.milestone_test_value"),
                intensity=1.0,
                duration_ms=6000,
                created_at=now,
            )
        elif et == "activity_surge":
            event = SignalEvent(
                id=str(uuid.uuid4())[:8],
                type="activity_surge",
                priority=40,
                title=self._tr("signal_system.goal.overdrive"),
                subtitle=self._tr("signal_system.goal.surge_sub"),
                username="",
                value=self._per_min_label(480),
                intensity=0.8,
                duration_ms=4500,
                created_at=now,
            )
        elif et == "ai_observation":
            event = SignalEvent(
                id=str(uuid.uuid4())[:8],
                type="ai_observation",
                priority=60,
                title=self._tr("signal_system.goal.ai_title"),
                subtitle=self._tr("signal_system.goal.ai_test_sub"),
                username="",
                value=f"{self._tr('signal_system.overlay.conf')}: 98%",
                intensity=0.75,
                duration_ms=5000,
                created_at=now,
            )
        elif et == "unknown_signal":
            event = SignalEvent(
                id=str(uuid.uuid4())[:8],
                type="unknown_signal",
                priority=20,
                title=self._tr("signal_system.goal.anomaly_title"),
                subtitle=self._tr("signal_system.goal.anomaly_test_sub"),
                username="",
                value="0xDEAD_BEEF::RADAR",
                intensity=0.9,
                duration_ms=4500,
                created_at=now,
            )
        else:
            # Default test event
            event = SignalEvent(
                id=str(uuid.uuid4())[:8],
                type="big_gift",
                priority=80,
                title=self._tr("signal_system.goal.system"),
                subtitle=self._tr("signal_system.goal.test_sub"),
                username=self._tr("signal_system.goal.test_pilot"),
                value=self._coins_label(1000),
                intensity=0.7,
                duration_ms=4500,
                created_at=now,
            )
        self._queue_event(event, force_immediate=True)

    # --- Publish Mechanism ---

    def schedule_publish(self) -> None:
        loop = self._loop
        pubsub = self._pubsub
        if loop is None or pubsub is None:
            return
        if self._publish_handle is not None:
            self._publish_handle.cancel()
        delay = _PUBLISH_DEBOUNCE_MS / 1000.0

        def _fire() -> None:
            self._publish_handle = None
            asyncio.ensure_future(self._publish_patch())

        self._publish_handle = loop.call_later(delay, _fire)

    def _flush_publish(self) -> None:
        pubsub = self._pubsub
        if pubsub is None:
            return
        if self._publish_handle is not None:
            self._publish_handle.cancel()
            self._publish_handle = None
        cfg = self._get_config()
        patch = {
            "config": signal_system_overlay_config_to_public_dict(cfg),
            "current_event": self._current_event.to_dict() if self._current_event else None,
            "event_seq": self._event_seq,
            "idle_metrics": {
                "activity_rate": self._get_activity_rate(),
                "system_status": "ONLINE",
                "uptime_s": int(time.time() - self._start_time),
            },
        }
        topic = f"overlay:signal_system:{self._instance}"
        if hasattr(pubsub, "publish_sync"):
            pubsub.publish_sync(topic, patch)
        else:
            pubsub.publish(topic, patch)

    async def _publish_patch(self) -> None:
        pubsub = self._pubsub
        if pubsub is None:
            return
        cfg = self._get_config()
        patch = {
            "config": signal_system_overlay_config_to_public_dict(cfg),
            "locale": self._get_locale(),
            "current_event": self._current_event.to_dict() if self._current_event else None,
            "event_seq": self._event_seq,
            "idle_metrics": {
                "activity_rate": self._get_activity_rate(),
                "system_status": "ONLINE",
                "uptime_s": int(time.time() - self._start_time),
            },
        }
        topic = f"overlay:signal_system:{self._instance}"
        await pubsub.publish(topic, patch)
