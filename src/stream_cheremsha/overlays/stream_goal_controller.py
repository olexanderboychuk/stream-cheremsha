from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from PySide6.QtCore import QObject, QTimer

from stream_cheremsha import l10n
from stream_cheremsha.overlays.pubsub import OverlayPubSub
from stream_cheremsha.overlays.stream_goal_overlay_config import (
    load_stream_goal_overlay_config,
    stream_goal_overlay_config_to_public_dict,
)
from stream_cheremsha.overlays.stream_goal_session import StreamGoalSession

_LOG = logging.getLogger(__name__)
_PUBLISH_DEBOUNCE_MS = 200
_LIKE_FLUSH_MS = 500


class StreamGoalController(QObject):
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
        cfg = load_stream_goal_overlay_config()
        self._session = StreamGoalSession.from_config(cfg)
        self._publish_handle: asyncio.TimerHandle | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

        self._decay_timer = QTimer(self)
        self._decay_timer.setInterval(1000)
        self._decay_timer.timeout.connect(self._on_tick)

        self._like_flush_timer = QTimer(self)
        self._like_flush_timer.setInterval(_LIKE_FLUSH_MS)
        self._like_flush_timer.timeout.connect(self._on_like_flush)
        self._like_flush_timer.start()

    def set_pubsub(self, pubsub: OverlayPubSub | None) -> None:
        self._pubsub = pubsub

    def set_event_loop(self, loop: asyncio.AbstractEventLoop | None) -> None:
        self._loop = loop

    def start(self) -> None:
        self._reload_config()
        self._decay_timer.start()
        self.schedule_publish()

    def stop(self) -> None:
        self._decay_timer.stop()
        self._like_flush_timer.stop()
        if self._publish_handle is not None:
            self._publish_handle.cancel()
            self._publish_handle = None

    def reset_session(self) -> None:
        cfg = load_stream_goal_overlay_config()
        self._session = StreamGoalSession.from_config(cfg)
        self.schedule_publish()

    def reset_for_new_stream(self) -> None:
        self._session.reset_for_new_stream()
        self.schedule_publish()

    def reload_config(self) -> None:
        self._reload_config()
        self.schedule_publish()

    def initial_state(self) -> dict[str, Any]:
        cfg = load_stream_goal_overlay_config()
        state = self._session.to_overlay_dict()
        state["config"] = stream_goal_overlay_config_to_public_dict(cfg)
        return state

    def on_follow(self, user: str, stable_key: str = "", unique_id: str = "") -> None:
        cfg = load_stream_goal_overlay_config()
        if not cfg.enabled:
            return
        self._session.add_follow(user, {"stable_key": stable_key, "unique_id": unique_id})
        self.schedule_publish()

    def on_like(self, user: str, count: int, profile_picture_url: str = "", user_key: str = "", unique_id: str = "") -> None:
        cfg = load_stream_goal_overlay_config()
        if not cfg.enabled:
            return
        try:
            n = max(1, int(count))
        except (TypeError, ValueError):
            n = 1
        self._session.add_like(n, {
            "user": user,
            "profile_picture_url": profile_picture_url,
            "user_key": user_key,
            "unique_id": unique_id,
        })
        # Don't schedule publish here - will be flushed by timer

    def _on_like_flush(self) -> None:
        self._session.flush_likes()
        self.schedule_publish()

    def on_share(self, user: str, count: int, stable_key: str = "", unique_id: str = "") -> None:
        cfg = load_stream_goal_overlay_config()
        if not cfg.enabled:
            return
        try:
            n = max(1, int(count))
        except (TypeError, ValueError):
            n = 1
        self._session.add_share(n, {"stable_key": stable_key, "unique_id": unique_id, "user": user})
        self.schedule_publish()

    def on_gift(
        self,
        sender: str,
        gift_id: str,
        gift_name: str,
        count: int,
        icon_url: str = "",
        sender_avatar_url: str = "",
        tiktok_coin_each: int = 0,
        sender_user_key: str = "",
        gift_raw_json: str = "",
        tiktok_user_bundle_json: str = "",
        stream_host_unique_id: str = "",
    ) -> None:
        cfg = load_stream_goal_overlay_config()
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
        self._session.add_gift(sender, gift_name, c, each, {
            "gift_id": gift_id,
            "icon_url": icon_url,
            "sender_avatar_url": sender_avatar_url,
            "sender_user_key": sender_user_key,
        })
        self.schedule_publish()

    def on_comment(self, user: str, text: str, stable_key: str = "", unique_id: str = "") -> None:
        cfg = load_stream_goal_overlay_config()
        if not cfg.enabled:
            return
        self._session.add_comment(user, text, {"stable_key": stable_key, "unique_id": unique_id})
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
        cfg = load_stream_goal_overlay_config()
        patch = self._session.to_overlay_dict()
        patch["config"] = stream_goal_overlay_config_to_public_dict(cfg)
        topic = f"overlay:stream_goal:{self._instance}"
        await pubsub.publish(topic, patch)

    def _on_tick(self) -> None:
        cfg = load_stream_goal_overlay_config()
        if not cfg.enabled:
            return
        now = time.time()
        self._session.tick(now)
        self.schedule_publish()

    def _reload_config(self) -> None:
        cfg = load_stream_goal_overlay_config()
        self._session = StreamGoalSession.from_config(cfg)

    def _tr(self, key: str, **kwargs: object) -> str:
        return l10n.tr(self._get_locale(), key, **kwargs)