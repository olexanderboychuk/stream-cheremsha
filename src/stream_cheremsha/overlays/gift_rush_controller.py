"""Per-instance controller for the ``gift_rush`` overlay.

Mirrors :class:`BattleController`: normalizes each gift event, tracks a
global combo window, assigns an intensity tier, aggregates rapid low-value
identical gifts, keeps a bounded event list, and publishes the debounced
state patch to ``overlay:gift_rush:{instance}``.

The controller is **platform-agnostic** (``platform`` field carried in each
payload). v1 only wires the existing TikTok fan-out, but the payload shape
works for any platform.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject

from stream_cheremsha.overlays.gift_rush_config import (
    GiftRushOverlayConfig,
    gift_rush_overlay_config_defaults,
    gift_rush_overlay_config_to_public_dict,
    load_gift_rush_overlay_config,
)
from stream_cheremsha.overlays.pubsub import OverlayPubSub

_LOG = logging.getLogger(__name__)
_PUBLISH_DEBOUNCE_MS = 200

# How long a pending LOW gift batch is considered "pending" for aggregation.
_AGGREGATION_WINDOW_S = 2.0

# Hard cap on stored events (JS dedupes on `at`, so this is a memory guard).
_MAX_EVENTS = 32


class GiftRushController(QObject):
    OVERLAY_TYPE = "gift_rush"

    def __init__(
        self,
        *,
        pubsub: OverlayPubSub | None,
        get_locale: Callable[[], str],
        instance: str = "main",
        parent: QObject | None = None,
        config_loader: Callable[[], Any] | None = None,
    ) -> None:
        super().__init__(parent)
        self._pubsub = pubsub
        self._get_locale = get_locale
        self._instance = str(instance or "main").strip() or "main"
        self._config_loader = config_loader
        self._publish_handle: asyncio.TimerHandle | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

        # Global gift-streak timestamps (D6: global combo, not per-gifter).
        self._gift_timestamps: list[float] = []

        # Bounded event list, oldest first. Each item is
        # {"type": "gift", "at": float, "payload": {...}}.
        self._events: list[dict[str, Any]] = []
        self._load_cfg()  # prime state so initial_state works before start()

    def _load_cfg(self) -> GiftRushOverlayConfig:
        if self._config_loader is not None:
            return self._config_loader()
        return load_gift_rush_overlay_config()

    # -- wiring (set by InstanceControllerGroup / MainWindow) ----------------

    def set_pubsub(self, pubsub: OverlayPubSub | None) -> None:
        self._pubsub = pubsub

    def set_event_loop(self, loop: asyncio.AbstractEventLoop | None) -> None:
        self._loop = loop

    def start(self) -> None:
        self.reload_config()
        self.schedule_publish()

    def stop(self) -> None:
        if self._publish_handle is not None:
            try:
                self._publish_handle.cancel()
            except Exception:  # noqa: BLE001 - best effort teardown
                pass
            self._publish_handle = None

    def reload_config(self) -> None:
        """Re-read config and publish. Config changes are live from next publish."""
        try:
            self._load_cfg()
        except Exception as exc:  # noqa: BLE001 - keep live on bad config
            _LOG.warning("gift_rush reload_config failed: %s", exc)
        self.schedule_publish()
        self._publish_patch_sync()

    # -- event entrypoint ---------------------------------------------------

    def on_gift(
        self,
        sender: str = "",
        gift_name: str = "",
        gift_id: str = "",
        count: int = 1,
        tiktok_coin_each: int = 0,
        icon_url: str = "",
        sender_avatar_url: str = "",
        sender_user_key: str = "",
        platform: str = "tiktok",
    ) -> None:
        """Normalize one gift event and append it to the (bounded) event list."""
        try:
            c = max(1, int(count))
        except (TypeError, ValueError):
            c = 1
        try:
            each = max(0, int(tiktok_coin_each or 0))
        except (TypeError, ValueError):
            each = 0
        value = each * c if each else c

        sender = str(sender or "").strip()
        gift_name = str(gift_name or "").strip()
        gift_id = str(gift_id or "").strip()
        icon_url = str(icon_url or "").strip()
        sender_avatar_url = str(sender_avatar_url or "").strip()
        sender_user_key = str(sender_user_key or "").strip()
        platform = str(platform or "tiktok").strip().lower()

        # A visual-only reaction still fires for a name-bearing gift with no
        # coin value (value 0 -> LOW, no score float).
        if not sender and not sender_user_key and not gift_name:
            return

        # Gate: animations off -> idle, emit nothing.
        try:
            cfg = self._load_cfg()
        except Exception:  # noqa: BLE001
            cfg = gift_rush_overlay_config_defaults()
        if not bool(getattr(cfg, "event_animations", True)):
            return

        now = time.time()

        # Global combo window (D6): trim, extend, count.
        window = max(1, int(getattr(cfg, "combo_window_s", 10)))
        self._gift_timestamps = [t for t in self._gift_timestamps if t > now - window]
        self._gift_timestamps.append(now)
        combo = len(self._gift_timestamps)

        intensity = self._intensity(value, combo)

        payload = {
            "sender": sender or ("?" if not sender_user_key else ""),
            "gift_name": gift_name,
            "gift_id": gift_id,
            "count": c,
            "aggregated_count": 1,
            "value": int(value),
            "icon_url": icon_url,
            "sender_avatar_url": sender_avatar_url,
            "sender_user_key": sender_user_key,
            "platform": platform,
            "combo": combo,
            "intensity": intensity,
            "target": str(getattr(cfg, "target_mode", "center")),
        }

        # Aggregation (D5): rapid, identical, LOW gifts merge into one visual.
        # Identity is gift_id + sender_user_key (key must be present); the
        # pending batch must be LOW and younger than the aggregation window.
        if intensity == "LOW":
            last = self._events[-1] if self._events else None
            if last is not None:
                p_last = last.get("payload") or {}
                if (
                    sender_user_key
                    and self._same_sender_key(gift_id, sender_user_key, p_last)
                    and (now - float(last.get("at", 0))) < _AGGREGATION_WINDOW_S
                ):
                    p_last["aggregated_count"] = int(p_last.get("aggregated_count", 0)) + 1
                    p_last["value"] = int(p_last.get("value", 0)) + int(value)
                    self._publish_patch_sync()
                    return

        event = {"type": "gift", "at": now, "payload": payload}
        self._events.append(event)
        if len(self._events) > _MAX_EVENTS:
            self._events.pop(0)
        self.schedule_publish()

    def _same_sender_key(
        self,
        gift_id: str,
        sender_user_key: str,
        p: dict[str, Any],
    ) -> bool:
        return (
            str(p.get("gift_id", "")) == gift_id
            and str(p.get("sender_user_key", "")) == sender_user_key
        )

    def _intensity(self, value: int, combo: int) -> str:
        """Tier from value + combo; take whichever is higher (D9)."""
        if value >= 200 or combo >= 10:
            return "EPIC"
        if 50 <= value < 200 or combo >= 5:
            return "HIGH"
        if 10 <= value < 50 or combo >= 3:
            return "MEDIUM"
        return "LOW"

    # -- state / publish ----------------------------------------------------

    def initial_state(self) -> dict[str, Any]:
        """Fresh state (empty events) used to boot the overlay."""
        try:
            cfg = self._load_cfg()
            public = gift_rush_overlay_config_to_public_dict(cfg)
        except Exception:  # noqa: BLE001
            public = gift_rush_overlay_config_to_public_dict(gift_rush_overlay_config_defaults())
        try:
            locale = str(self._get_locale() or "uk")
        except Exception:  # noqa: BLE001
            locale = "uk"
        return {"config": public, "locale": locale, "events": list(self._events)}

    def schedule_publish(self) -> None:
        loop = self._loop
        pubsub = self._pubsub
        if loop is None or pubsub is None:
            return
        if self._publish_handle is not None:
            try:
                self._publish_handle.cancel()
            except Exception:  # noqa: BLE001
                pass
        delay = _PUBLISH_DEBOUNCE_MS / 1000.0

        def _fire() -> None:
            self._publish_handle = None
            self._publish_patch_sync()

        try:
            self._publish_handle = loop.call_later(delay, _fire)
        except Exception:  # noqa: BLE001 - loop closed in tests
            self._publish_handle = None

    def _publish_patch_sync(self) -> None:
        pubsub = self._pubsub
        if pubsub is None:
            return
        patch = self._build_state()
        topic = f"overlay:{type(self).OVERLAY_TYPE}:{self._instance}"
        try:
            pubsub.publish_sync(topic, patch)
        except Exception as exc:  # noqa: BLE001 - never break callers
            _LOG.warning("gift_rush publish failed: %s", exc)

    def _build_state(self) -> dict[str, Any]:
        try:
            cfg = self._load_cfg()
            public = gift_rush_overlay_config_to_public_dict(cfg)
        except Exception:  # noqa: BLE001
            public = gift_rush_overlay_config_to_public_dict(gift_rush_overlay_config_defaults())
        try:
            locale = str(self._get_locale() or "uk")
        except Exception:  # noqa: BLE001
            locale = "uk"
        return {"config": public, "locale": locale, "events": list(self._events)}

    def reset_for_new_stream(self) -> None:
        """Clear all in-stream state and publish an idle state."""
        self._events.clear()
        self._gift_timestamps.clear()
        self.schedule_publish()
        self._publish_patch_sync()

    # -- no-op fan-out (group may call any of these) ------------------------

    def on_like(self, *args: Any, **kwargs: Any) -> None:
        return

    def on_share(self, *args: Any, **kwargs: Any) -> None:
        return

    def on_comment(self, *args: Any, **kwargs: Any) -> None:
        return

    def on_follow(self, *args: Any, **kwargs: Any) -> None:
        return
