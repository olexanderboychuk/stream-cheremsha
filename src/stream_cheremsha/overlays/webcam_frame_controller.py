from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject

from stream_cheremsha.overlays.activity_engine import ActivityEngine
from stream_cheremsha.overlays.pubsub import OverlayPubSub
from stream_cheremsha.overlays.webcam_frame_overlay_config import (
    load_webcam_frame_overlay_config,
    webcam_frame_overlay_config_to_public_dict,
)

_PUBLISH_DEBOUNCE_MS = 150


class WebcamFrameController(QObject):
    """Config-driven controller for the decorative Live Webcam Frame widget.

    There is no live gameplay/session state to track - the widget is purely a
    themeable animated frame. This controller only exists to push settings
    changes to any already-open browser sources instantly, matching the
    pattern used by the other overlay controllers.

    Additionally, the controller owns an :class:`ActivityEngine` that tracks
    recent stream activity and publishes an ``activity_score`` (0-100) patch
    to any open webcam-frame browser sources.  The overlay JavaScript maps
    the score to visual states (idle / active / hyped / overdrive / surge).
    """

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
        self._activity_engine = ActivityEngine(
            pubsub=pubsub,
            enabled=True,
            decay_speed=1.5,
            event_weights={
                "like": 2.0,
                "comment": 4.0,
                "follow": 6.0,
                "share": 8.0,
                "gift": 12.0,
            },
            on_score_change=self._on_activity_score_changed,
        )

    def set_pubsub(self, pubsub: OverlayPubSub | None) -> None:
        self._pubsub = pubsub
        self._activity_engine._pubsub = pubsub

    def set_event_loop(self, loop: asyncio.AbstractEventLoop | None) -> None:
        self._loop = loop
        self._activity_engine._loop = loop

    def start(self) -> None:
        self._activity_engine.start()
        self.schedule_publish()

    def stop(self) -> None:
        self._activity_engine.stop()
        if self._publish_handle is not None:
            self._publish_handle.cancel()
            self._publish_handle = None

    def reload_config(self) -> None:
        self.schedule_publish()

    def initial_state(self) -> dict[str, Any]:
        cfg = load_webcam_frame_overlay_config()
        base = {
            "config": webcam_frame_overlay_config_to_public_dict(cfg),
            "locale": str(self._get_locale() or "uk"),
        }
        # Include the current activity score so the overlay renders the
        # correct visual state immediately on startup.
        base["activity_score"] = self._activity_engine.get_score()
        return base

    # -----------------------------------------------------------------
    # Debounced publish
    # -----------------------------------------------------------------

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
        topic = f"overlay:webcam_frame:{self._instance}"
        # Publish config + activity score as a single patch.
        await pubsub.publish(topic, self.initial_state())

    # -----------------------------------------------------------------
    # Activity score change handler
    # -----------------------------------------------------------------

    def _on_activity_score_changed(self, score: float) -> None:
        """Called by the ActivityEngine when the score updates.

        We debounce the publish by re-scheduling the normal config publish;
        the initial_state() call inside that path will include the fresh
        score, so the overlay always has the latest value.
        """
        # Reschedule the debounced publish so the overlay gets the new score.
        self.schedule_publish()
