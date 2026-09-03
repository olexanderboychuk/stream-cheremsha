from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QTimer

from stream_cheremsha.overlays.live_leaderboard_overlay_config import (
    enabled_scenes_from_config,
    enabled_sources_from_config,
    live_leaderboard_overlay_config_to_public_dict,
    load_live_leaderboard_overlay_config,
    parse_sequence_steps,
)
from stream_cheremsha.overlays.live_leaderboard_ranking import (
    ContributorWeights,
    LiveLeaderboardRankingEngine,
)
from stream_cheremsha.overlays.live_leaderboard_rotation import (
    LiveLeaderboardRotationEngine,
    filter_sequence_for_config,
)
from stream_cheremsha.overlays.pubsub import OverlayPubSub

_LOG = logging.getLogger(__name__)
_PUBLISH_DEBOUNCE_MS = 200
_LIKE_FLUSH_MS = 500
_ROTATION_TICK_MS = 250


class LiveLeaderboardController(QObject):
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

        cfg = load_live_leaderboard_overlay_config()
        self._ranking = LiveLeaderboardRankingEngine(
            weights=ContributorWeights(
                like=cfg.weight_like,
                gift_coin=cfg.weight_gift_coin,
                share=cfg.weight_share,
                comment=cfg.weight_comment,
            )
        )
        steps = filter_sequence_for_config(
            parse_sequence_steps(cfg),
            enabled_sources=enabled_sources_from_config(cfg),
            enabled_scenes=enabled_scenes_from_config(cfg),
        )
        self._rotation = LiveLeaderboardRotationEngine.from_steps(steps)

        self._like_flush_timer = QTimer(self)
        self._like_flush_timer.setInterval(_LIKE_FLUSH_MS)
        self._like_flush_timer.timeout.connect(self._on_like_flush)

        self._rotation_timer = QTimer(self)
        self._rotation_timer.setInterval(_ROTATION_TICK_MS)
        self._rotation_timer.timeout.connect(self._on_rotation_tick)

    def set_pubsub(self, pubsub: OverlayPubSub | None) -> None:
        self._pubsub = pubsub

    def set_event_loop(self, loop: asyncio.AbstractEventLoop | None) -> None:
        self._loop = loop

    def start(self) -> None:
        self._reload_config(reset_rotation=False)
        self._like_flush_timer.start()
        self._rotation_timer.start()
        self.schedule_publish()

    def stop(self) -> None:
        self._like_flush_timer.stop()
        self._rotation_timer.stop()
        if self._publish_handle is not None:
            self._publish_handle.cancel()
            self._publish_handle = None

    def reset_for_new_stream(self) -> None:
        self._ranking.reset()
        # Keep sequence; restart current scene clock without inventing a new show.
        self._rotation.scene_started_at_ms = int(time.time() * 1000)
        self.schedule_publish()

    def reload_config(self) -> None:
        self._reload_config(reset_rotation=True)
        self.schedule_publish()

    def initial_state(self) -> dict[str, Any]:
        return self._build_state()

    def on_like(
        self,
        user: str,
        count: int,
        profile_picture_url: str = "",
        user_key: str = "",
        unique_id: str = "",
    ) -> None:
        cfg = load_live_leaderboard_overlay_config()
        if not cfg.enabled:
            return
        self._ranking.add_likes(
            user_key=(user_key or unique_id or "").strip(),
            display_name=user,
            n=count,
            avatar_url=profile_picture_url,
        )
        # Flush timer publishes; do not touch rotation.

    def _on_like_flush(self) -> None:
        flushed = self._ranking.flush_likes()
        if flushed > 0:
            self.schedule_publish()

    def on_share(
        self,
        user: str,
        count: int,
        stable_key: str = "",
        unique_id: str = "",
        avatar_url: str = "",
    ) -> None:
        cfg = load_live_leaderboard_overlay_config()
        if not cfg.enabled:
            return
        self._ranking.add_shares(
            user_key=(stable_key or unique_id or "").strip(),
            display_name=user,
            n=count,
            avatar_url=avatar_url,
        )
        self.schedule_publish()

    def on_gift(
        self,
        sender: str,
        count: int,
        tiktok_coin_each: int = 0,
        sender_avatar_url: str = "",
        sender_user_key: str = "",
    ) -> None:
        cfg = load_live_leaderboard_overlay_config()
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
        coins = c * each if each > 0 else c
        self._ranking.add_gift_coins(
            user_key=(sender_user_key or "").strip(),
            display_name=sender,
            coins=coins,
            avatar_url=sender_avatar_url,
        )
        self.schedule_publish()

    def on_comment(
        self,
        user: str,
        stable_key: str = "",
        unique_id: str = "",
        avatar_url: str = "",
    ) -> None:
        cfg = load_live_leaderboard_overlay_config()
        if not cfg.enabled:
            return
        self._ranking.add_comment(
            user_key=(stable_key or unique_id or "").strip(),
            display_name=user,
            avatar_url=avatar_url,
        )
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
        topic = f"overlay:live_leaderboard:{self._instance}"
        await pubsub.publish(topic, patch)

    def _on_rotation_tick(self) -> None:
        cfg = load_live_leaderboard_overlay_config()
        if not cfg.enabled:
            return
        advanced = self._rotation.tick(now_ms=int(time.time() * 1000))
        if advanced:
            self.schedule_publish()

    def _build_state(self) -> dict[str, Any]:
        cfg = load_live_leaderboard_overlay_config()
        now_ms = int(time.time() * 1000)
        return {
            "config": live_leaderboard_overlay_config_to_public_dict(cfg),
            "rankings": self._ranking.all_rankings(limit=cfg.top_n),
            "presentation": self._rotation.presentation_dict(server_now_ms=now_ms),
            "locale": str(self._get_locale() or "uk"),
        }

    def _reload_config(self, *, reset_rotation: bool) -> None:
        cfg = load_live_leaderboard_overlay_config()
        self._ranking.weights = ContributorWeights(
            like=cfg.weight_like,
            gift_coin=cfg.weight_gift_coin,
            share=cfg.weight_share,
            comment=cfg.weight_comment,
        )
        steps = filter_sequence_for_config(
            parse_sequence_steps(cfg),
            enabled_sources=enabled_sources_from_config(cfg),
            enabled_scenes=enabled_scenes_from_config(cfg),
        )
        if reset_rotation:
            self._rotation.replace_sequence(steps, preserve_position=False)
        else:
            # Keep token unless sequence identity forced a fallback change.
            self._rotation.replace_sequence(steps, preserve_position=True)
