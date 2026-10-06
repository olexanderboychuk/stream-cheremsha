"""Per-instance controller for the ``balloon_hunter`` overlay.

Mirrors :class:`GiftRushController`: normalizes each gift event, tracks a
global combo window, assigns a balloon tier (NORMAL / GOLD / EPIC) from coin
value + combo, keeps a bounded event list, and publishes the debounced state
patch to ``overlay:balloon_hunter:{instance}``.

The controller is **platform-agnostic** (``platform`` field carried in each
payload). v1 only wires the existing TikTok fan-out.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject

from stream_cheremsha.domain.protocols import AudioSink
from stream_cheremsha.overlays.balloon_hunter_config import (
    BalloonHunterOverlayConfig,
    balloon_hunter_overlay_config_defaults,
    balloon_hunter_overlay_config_to_public_dict,
    load_balloon_hunter_overlay_config,
)
from stream_cheremsha.overlays.pubsub import OverlayPubSub

_LOG = logging.getLogger(__name__)
_PUBLISH_DEBOUNCE_MS = 200

# Hard cap on stored pop events (JS dedupes on `at`, so this is a memory guard).
_MAX_EVENTS = 32

# Projectile flight times match the overlay's PROJECTILE_FLIGHT_MS.
_SFX_FLIGHT_MS = {"NORMAL": 550, "GOLD": 650, "EPIC": 800}

# Dedicated balloon pop sounds (AI-generated, see assets/sounds/). The
# fallback keeps shared gift_rush impacts until the dedicated files land.
_POP_SFX = {
    "NORMAL": "sfx_balloon_pop",
    "GOLD": "sfx_balloon_pop_gold",
    "EPIC": "sfx_balloon_pop_epic",
}
_POP_SFX_FALLBACK = {
    "NORMAL": "sfx_impact_low",
    "GOLD": "sfx_impact_low",
    "EPIC": "sfx_impact_epic",
}


def pop_sfx_names(intensity: str) -> tuple[str, str]:
    """(primary, fallback) sound names for a pop intensity tier."""
    key = str(intensity or "NORMAL").upper()
    return (
        _POP_SFX.get(key, _POP_SFX["NORMAL"]),
        _POP_SFX_FALLBACK.get(key, _POP_SFX_FALLBACK["NORMAL"]),
    )


class BalloonHunterController(QObject):
    OVERLAY_TYPE = "balloon_hunter"

    def __init__(
        self,
        *,
        pubsub: OverlayPubSub | None,
        get_locale: Callable[[], str],
        instance: str = "main",
        parent: QObject | None = None,
        config_loader: Callable[[], Any] | None = None,
        audio_sink: AudioSink | None = None,
    ) -> None:
        super().__init__(parent)
        self._pubsub = pubsub
        self._get_locale = get_locale
        self._instance = str(instance or "main").strip() or "main"
        self._config_loader = config_loader
        self._audio_sink: AudioSink | None = audio_sink
        self._publish_handle: asyncio.TimerHandle | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

        # Global gift-streak timestamps (global combo, not per-gifter).
        self._gift_timestamps: list[float] = []

        # Bounded event list, oldest first. Each item is
        # {"type": "pop", "at": float, "payload": {...}}.
        self._events: list[dict[str, Any]] = []
        self._sfx_cache: dict[str, bytes] = {}
        self._load_cfg()  # prime state so initial_state works before start()

    def _load_cfg(self) -> BalloonHunterOverlayConfig:
        if self._config_loader is not None:
            return self._config_loader()
        return load_balloon_hunter_overlay_config()

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
            _LOG.warning("balloon_hunter reload_config failed: %s", exc)
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
        """Normalize one gift event and append a pop command to the event list."""
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

        if not sender and not sender_user_key and not gift_name:
            return

        try:
            cfg = self._load_cfg()
        except Exception:  # noqa: BLE001
            cfg = balloon_hunter_overlay_config_defaults()
        if not bool(getattr(cfg, "event_animations", True)):
            return

        now = time.time()

        window = max(1, int(getattr(cfg, "combo_window_s", 10)))
        self._gift_timestamps = [t for t in self._gift_timestamps if t > now - window]
        self._gift_timestamps.append(now)
        combo = len(self._gift_timestamps)

        intensity = self._intensity(value, combo, cfg)

        payload = {
            "sender": sender or ("?" if not sender_user_key else ""),
            "gift_name": gift_name,
            "gift_id": gift_id,
            "count": c,
            "value": int(value),
            "icon_url": icon_url,
            "sender_avatar_url": sender_avatar_url,
            "sender_user_key": sender_user_key,
            "platform": platform,
            "combo": combo,
            "intensity": intensity,
            # Client matches a live balloon of this kind first, then falls back.
            "target_balloon_kind": intensity,
        }

        self._play_pop_sfx(cfg, intensity)

        event = {"type": "pop", "at": now, "payload": payload}
        self._events.append(event)
        if len(self._events) > _MAX_EVENTS:
            self._events.pop(0)
        self.schedule_publish()

    def _intensity(self, value: int, combo: int, cfg: BalloonHunterOverlayConfig) -> str:
        """Tier from value + combo; whichever is higher wins."""
        try:
            epic_min = int(getattr(cfg, "epic_min_coins", 200))
        except (TypeError, ValueError):
            epic_min = 200
        try:
            gold_min = int(getattr(cfg, "gold_min_coins", 50))
        except (TypeError, ValueError):
            gold_min = 50
        combo_on = bool(getattr(cfg, "combo_enabled", True))
        if value >= epic_min or (combo_on and combo >= 10):
            return "EPIC"
        if value >= gold_min or (combo_on and combo >= 5):
            return "GOLD"
        return "NORMAL"

    # -- state / publish ----------------------------------------------------

    def initial_state(self) -> dict[str, Any]:
        """Fresh state (empty events) used to boot the overlay."""
        try:
            cfg = self._load_cfg()
            public = balloon_hunter_overlay_config_to_public_dict(cfg)
        except Exception:  # noqa: BLE001
            public = balloon_hunter_overlay_config_to_public_dict(
                balloon_hunter_overlay_config_defaults()
            )
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
            _LOG.warning("balloon_hunter publish failed: %s", exc)

    def _build_state(self) -> dict[str, Any]:
        try:
            cfg = self._load_cfg()
            public = balloon_hunter_overlay_config_to_public_dict(cfg)
        except Exception:  # noqa: BLE001
            public = balloon_hunter_overlay_config_to_public_dict(
                balloon_hunter_overlay_config_defaults()
            )
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

    # -- sfx (app-side, via the app's AudioSink) ------------------------------

    def _sfx_bytes(self, name: str) -> bytes:
        """Cached MP3 bytes for a named sound (empty bytes if absent)."""
        if name not in self._sfx_cache:
            p = Path(__file__).resolve().parents[1] / "assets" / "sounds" / f"{name}.mp3"
            try:
                data = p.read_bytes() if p.is_file() else b""
            except OSError:
                data = b""
            if not data:
                _LOG.warning("balloon_hunter sfx %s missing at %s — gift will be silent", name, p)
            self._sfx_cache[name] = data
        return self._sfx_cache[name]

    def _play_pop_sfx(self, cfg: BalloonHunterOverlayConfig, intensity: str) -> None:
        """Play the pop sound from the app process. Silent when off/missing."""
        if not bool(getattr(cfg, "sound_enabled", False)):
            return
        sink = self._audio_sink
        loop = self._loop
        if sink is None or loop is None:
            return
        play = getattr(sink, "play_mp3_parallel_with_volume", None)
        if not callable(play):
            return
        reduced = bool(getattr(cfg, "reduced_effects", False))
        scale = 0.5 if reduced else 1.0
        flight_ms = int(_SFX_FLIGHT_MS.get(intensity, 150) * (0.7 if reduced else 1.0))
        name, fallback = pop_sfx_names(intensity)

        def _burst() -> None:
            data = self._sfx_bytes(name) or self._sfx_bytes(fallback)
            if not data:
                return

            async def _one() -> None:
                try:
                    await play(data, max(0.0, min(1.0, 0.8 * scale)))
                except Exception as exc:  # noqa: BLE001
                    _LOG.debug("balloon_hunter sfx %s failed: %s", name, exc)

            loop.create_task(_one())

        if flight_ms <= 0:
            _burst()
        else:
            try:
                loop.call_later(flight_ms / 1000.0, _burst)
            except Exception:  # noqa: BLE001 - loop closed mid-stream
                _burst()

    # -- no-op fan-out (group may call any of these) ------------------------

    def on_like(self, *args: Any, **kwargs: Any) -> None:
        return

    def on_share(self, *args: Any, **kwargs: Any) -> None:
        return

    def on_comment(self, *args: Any, **kwargs: Any) -> None:
        return

    def on_follow(self, *args: Any, **kwargs: Any) -> None:
        return
