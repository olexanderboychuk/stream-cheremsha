from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QTimer

from stream_cheremsha.overlays.pubsub import OverlayPubSub
from stream_cheremsha.overlays.social_rotator_overlay_config import (
    load_social_rotator_overlay_config,
    parse_platforms,
    social_rotator_overlay_config_to_public_dict,
)
from stream_cheremsha.overlays.social_rotator_rotation import (
    SocialRotatorRotationEngine,
    enabled_rotation_entries,
)
from stream_cheremsha.overlays.social_rotator_stats import SocialRotatorStatsSession

_LOG = logging.getLogger(__name__)
_PUBLISH_DEBOUNCE_MS = 200
_ROTATION_TICK_MS = 250


class SocialRotatorController(QObject):
    def __init__(
        self,
        *,
        pubsub: OverlayPubSub | None,
        get_locale: Callable[[], str],
        instance: str = "main",
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._pubsub = pubsub
        self._get_locale = get_locale
        self._instance = str(instance or "main").strip() or "main"
        self._publish_handle: asyncio.TimerHandle | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stats = SocialRotatorStatsSession()

        cfg = load_social_rotator_overlay_config()
        entries = enabled_rotation_entries(parse_platforms(cfg))
        self._rotation = SocialRotatorRotationEngine.from_entries(
            entries,
            interval_ms=cfg.rotation_interval_ms,
        )

        self._rotation_timer = QTimer(self)
        self._rotation_timer.setInterval(_ROTATION_TICK_MS)
        self._rotation_timer.timeout.connect(self._on_rotation_tick)

    def set_pubsub(self, pubsub: OverlayPubSub | None) -> None:
        self._pubsub = pubsub

    def set_event_loop(self, loop: asyncio.AbstractEventLoop | None) -> None:
        self._loop = loop

    def start(self) -> None:
        self._reload_config(reset_rotation=False)
        self._rotation_timer.start()
        self.schedule_publish()

    def stop(self) -> None:
        self._rotation_timer.stop()
        if self._publish_handle is not None:
            self._publish_handle.cancel()
            self._publish_handle = None

    def reset_for_new_stream(self) -> None:
        self._stats.reset()
        # TikTok stream-start resets session stats; restart the elapsed timer here.
        # (on_stream_live(True) alone is not enough — connect often fires after it and
        # would clear the timestamp via this reset.)
        self._stats.set_stream_started_at_ms(int(time.time() * 1000))
        self._rotation.started_at_ms = int(time.time() * 1000)
        self.schedule_publish()

    def reload_config(self) -> None:
        self._reload_config(reset_rotation=False)
        self.schedule_publish()

    def initial_state(self) -> dict[str, Any]:
        return self._build_state()

    def on_follow(
        self,
        user: str,
        stable_key: str = "",
        unique_id: str = "",
    ) -> None:
        _ = stable_key, unique_id
        cfg = load_social_rotator_overlay_config()
        if not cfg.enabled:
            return
        self._stats.on_follow(user)
        self.schedule_publish()

    def on_tiktok_gift(
        self,
        sender: str,
        count: int,
        tiktok_coin_each: int = 0,
        sender_avatar_url: str = "",
        sender_user_key: str = "",
    ) -> None:
        _ = sender_avatar_url, sender_user_key
        cfg = load_social_rotator_overlay_config()
        if not cfg.enabled:
            return
        try:
            c = max(1, int(count))
        except (TypeError, ValueError):
            c = 1
        try:
            each = max(0, int(tiktok_coin_each or 0))
        except (TypeError, ValueError):
            each = 0
        coins = float(c * each if each > 0 else c)
        self._stats.on_donation(
            name=sender,
            amount=coins,
            source="tiktok_gift",
            coin_rate=float(cfg.tiktok_coin_to_value_rate),
        )
        self.schedule_publish()

    def on_donation(self, name: str, amount: float, source: str) -> None:
        cfg = load_social_rotator_overlay_config()
        if not cfg.enabled:
            return
        self._stats.on_donation(
            name=name,
            amount=amount,
            source=source,
            coin_rate=float(cfg.tiktok_coin_to_value_rate),
        )
        self.schedule_publish()

    def on_viewers(self, platform: str, count: int) -> None:
        cfg = load_social_rotator_overlay_config()
        if not cfg.enabled:
            return
        self._stats.set_viewers(platform, count)
        self.schedule_publish()

    def on_stream_live(self, started: bool) -> None:
        cfg = load_social_rotator_overlay_config()
        if not cfg.enabled:
            return
        if started:
            self._stats.set_stream_started_at_ms(int(time.time() * 1000))
        else:
            self._stats.set_stream_started_at_ms(None)
        self.schedule_publish()

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

    async def _publish_patch(self) -> None:
        pubsub = self._pubsub
        if pubsub is None:
            return
        patch = self._build_state()
        topic = f"overlay:social_rotator:{self._instance}"
        await pubsub.publish(topic, patch)

    def _on_rotation_tick(self) -> None:
        cfg = load_social_rotator_overlay_config()
        if not cfg.enabled:
            return
        advanced = self._rotation.tick(now_ms=int(time.time() * 1000))
        if advanced:
            self.schedule_publish()

    def _build_state(self) -> dict[str, Any]:
        cfg = load_social_rotator_overlay_config()
        now_ms = int(time.time() * 1000)
        platforms = parse_platforms(cfg)
        enabled = enabled_rotation_entries(platforms)
        return {
            "config": social_rotator_overlay_config_to_public_dict(cfg),
            "rotation": self._rotation.presentation_dict(server_now_ms=now_ms),
            "platforms_enabled": [
                {
                    "id": e.entry_id,
                    "platform": e.platform,
                    "username": e.username,
                    "url": e.url,
                    "order": i,
                }
                for i, e in enumerate(enabled)
            ],
            "stats": self._stats.to_public_dict(),
            "locale": str(self._get_locale() or "uk"),
        }

    def _reload_config(self, *, reset_rotation: bool) -> None:
        cfg = load_social_rotator_overlay_config()
        entries = enabled_rotation_entries(parse_platforms(cfg))
        self._rotation.replace_entries(
            entries,
            interval_ms=cfg.rotation_interval_ms,
            preserve_position=not reset_rotation,
        )
        _LOG.debug(
            "social_rotator config reloaded entries=%d reset=%s",
            len(entries),
            reset_rotation,
        )
