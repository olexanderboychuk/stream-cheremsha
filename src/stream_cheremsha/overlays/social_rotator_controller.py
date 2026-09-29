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
    entry_public_dict,
)

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
        # Restart the rotation elapsed timer for a fresh stream.
        self._rotation.started_at_ms = int(time.time() * 1000)
        self.schedule_publish()

    def reload_config(self) -> None:
        self._reload_config(reset_rotation=False)
        self.schedule_publish()

    def initial_state(self) -> dict[str, Any]:
        return self._build_state()

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
            self._publish_patch_sync()

        self._publish_handle = loop.call_later(delay, _fire)

    def _publish_patch_sync(self) -> None:
        pubsub = self._pubsub
        if pubsub is None:
            return
        patch = self._build_state()
        # State-only broadcast: every instance keeps its own config (render /
        # initial_state); the singleton config must not leak into instances.
        patch.pop("config", None)
        topic = "overlay:social_rotator:*"
        pubsub.publish_sync(topic, patch)

    async def _publish_patch(self) -> None:
        self._publish_patch_sync()

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
                entry_public_dict(e, order=i) for i, e in enumerate(enabled)
            ],
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
