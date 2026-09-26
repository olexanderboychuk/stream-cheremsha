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
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject

from stream_cheremsha.domain.protocols import AudioSink
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

# SFX flight times match the page's tierCounts() (flightMs).
_SFX_FLIGHT_MS = {"LOW": 520, "MEDIUM": 650, "HIGH": 750, "EPIC": 900}
_SFX_IMPACT = {
    "LOW": "sfx_impact_low",
    "MEDIUM": "sfx_impact_mid",
    "HIGH": "sfx_impact_mid",
    "EPIC": "sfx_impact_epic",
}


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

        # Global gift-streak timestamps (D6: global combo, not per-gifter).
        self._gift_timestamps: list[float] = []

        # Bounded event list, oldest first. Each item is
        # {"type": "gift", "at": float, "payload": {...}}.
        self._events: list[dict[str, Any]] = []
        self._sfx_cache: dict[str, bytes] = {}
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

        # A new projected burst is visible, so fire its sounds (app-side).
        self._play_gift_sfx(cfg, intensity, payload, combo)

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

    # -- sfx (app-side, via the app's AudioSink) ------------------------------

    def _sfx_bytes(self, name: str) -> bytes:
        """Cached MP3 bytes for a named sound (empty bytes if absent)."""
        if name not in self._sfx_cache:
            p = Path(__file__).resolve().parents[1] / "assets" / "sounds" / f"{name}.mp3"
            try:
                self._sfx_cache[name] = p.read_bytes() if p.is_file() else b""
            except OSError:
                self._sfx_cache[name] = b""
        return self._sfx_cache[name]

    def _play_gift_sfx(
        self, cfg: GiftRushOverlayConfig, intensity: str, payload: dict[str, Any], combo: int
    ) -> None:
        """Play the gift's sounds from the app process (no autoplay policy;
        works in OBS and a plain browser alike). Silent when sound is off,
        the sink is missing, or the event loop is gone.

        The launch whoosh fires immediately; the impact/coins/ding/tick/combo
        sequence is delayed by the intensity flight time so the audio lands
        with the visual burst."""
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
        flight_ms = int(_SFX_FLIGHT_MS.get(intensity, 650) * (0.7 if reduced else 1.0))

        def _clip(name: str, gain: float) -> None:
            data = self._sfx_bytes(name)
            if not data:
                return
            g = max(0.0, min(1.0, gain * scale))

            async def _run() -> None:
                try:
                    await play(data, g)
                except Exception as exc:  # noqa: BLE001 - never break the gift flow
                    _LOG.debug("gift_rush sfx %s failed: %s", name, exc)

            loop.create_task(_run())

        def _burst() -> None:
            seq: list[tuple[str, float]] = [(_SFX_IMPACT.get(intensity, "sfx_impact_low"), 1.0)]
            if bool(getattr(cfg, "effects_coins", True)):
                seq.append(("sfx_coins", 0.7))
            if bool(getattr(cfg, "show_value", True)):
                seq.append(("sfx_score_ding", 0.6))
            if bool(getattr(cfg, "effects_sparks", True)):
                seq.append(("sfx_spark_tink", 0.4))
            if (
                combo > 1
                and bool(getattr(cfg, "show_combo", True))
                and bool(getattr(cfg, "combo_enabled", True))
            ):
                seq.append(("sfx_combo_tick", 0.5))

            # Fire every burst clip as its own concurrent task so they overlap
            # on the sink's player pool (like the old Web Audio engine). Default
            # args capture the loop variables (late-binding bug otherwise).
            for name, gain in seq:
                data = self._sfx_bytes(name)
                if not data:
                    continue
                g = max(0.0, min(1.0, gain * scale))

                async def _one(_n=name, _d=data, _g=g) -> None:
                    try:
                        await play(_d, _g)
                    except Exception as exc:  # noqa: BLE001
                        _LOG.debug("gift_rush sfx %s failed: %s", _n, exc)

                loop.create_task(_one())

        _clip("sfx_gift_launch", 0.8)
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
