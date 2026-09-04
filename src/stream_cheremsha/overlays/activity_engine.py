from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from typing import Any


class ActivityEngine:
    """Manages a normalized activity score (0-100) that reflects recent stream activity.

    The score uses time-based smooth decay toward idle, so it naturally returns
    to lower values when no events arrive. Event types contribute configurable
    weights, and high-frequency events are aggregated rather than animating
    individually.

    Designed to be lightweight and run for many hours without memory growth.
    """

    #: Default event weights — higher = stronger immediate activity response.
    #: These are expressive defaults; callers may override per their config.
    DEFAULT_EVENT_WEIGHTS: dict[str, float] = {
        "like": 2.0,
        "comment": 4.0,
        "follow": 6.0,
        "share": 8.0,
        "gift": 12.0,
    }

    #: Decay speed in activity points per second.
    #: Lower = slower fade; higher = quicker return to idle.
    DEFAULT_DECAY_SPEED = 1.5

    #: Hysteresis buffer points — prevents jittery state flapping.
    STATE_HYSTERESIS = 3.0

    #: State boundaries (inclusive lower, exclusive upper), in activity-score units.
    STATE_IDLE_UPPER = 20.0
    STATE_ACTIVE_UPPER = 45.0
    STATE_HYPED_UPPER = 70.0
    STATE_OVERDRIVE_UPPER = 90.0
    STATE_SURGE_CAP = 100.0

    def __init__(
        self,
        *,
        pubsub: Any | None = None,
        enabled: bool = True,
        decay_speed: float | None = None,
        event_weights: dict[str, float] | None = None,
        on_score_change: Callable[[float], Any] | None = None,
    ) -> None:
        self._pubsub = pubsub
        self._enabled = bool(enabled)
        self._decay_speed = (
            float(decay_speed) if decay_speed is not None else self.DEFAULT_DECAY_SPEED
        )
        self._event_weights: dict[str, float] = (
            dict(event_weights) if event_weights else dict(self.DEFAULT_EVENT_WEIGHTS)
        )
        self._on_score_change = on_score_change
        self._score: float = 0.0
        self._last_update: float = time.monotonic()
        self._running: bool = False
        self._task: asyncio.Task[Any] | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background decay task."""
        if self._running:
            return
        self._running = True
        try:
            loop = asyncio.get_running_loop()
            self._task = loop.create_task(self._decay_loop())
        except RuntimeError:
            self._task = None

    def stop(self) -> None:
        """Stop the background decay task."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            self._task = None

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    async def handle_event(self, event_type: str, event_data: dict[str, Any] | None = None) -> None:
        """Process a single stream event and update the activity score.

        This method aggregates the event's weight into the score and
        schedules a score-publish.  The actual decay is handled by the
        background loop; calling this method does not immediately publish.
        """
        if not self._enabled:
            return

        # Apply decay first so the score catches up from the previous tick.
        now = time.monotonic()
        elapsed = now - self._last_update
        if elapsed > 0:
            self._apply_decay(elapsed)
            self._last_update = now

        weight = self._event_weights.get(event_type, 0.0)
        if weight <= 0:
            return

        self._score = min(100.0, self._score + weight)
        # Clamp after addition; the decay loop will bring it down.
        self._last_update = time.monotonic()
        await self._publish_score()

    # ------------------------------------------------------------------
    # Score query / state
    # ------------------------------------------------------------------

    def get_score(self) -> float:
        """Return the current activity score (0-100)."""
        # Apply inline decay so the returned value is always fresh.
        now = time.monotonic()
        elapsed = now - self._last_update
        if elapsed > 0:
            self._apply_decay(elapsed)
            self._last_update = now
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._publish_score())
            except RuntimeError:
                pass
        return round(self._score, 1)

    def get_state(self) -> str:
        """Return the current conceptual state name based on the score."""
        s = self._score
        if s <= self.STATE_IDLE_UPPER:
            return "idle"
        if s <= self.STATE_ACTIVE_UPPER:
            return "active"
        if s <= self.STATE_HYPED_UPPER:
            return "hyped"
        if s <= self.STATE_OVERDRIVE_UPPER:
            return "overdrive"
        return "surge"

    # ------------------------------------------------------------------
    # Internal decay / publish
    # ------------------------------------------------------------------

    def _apply_decay(self, elapsed: float) -> None:
        """Subtract decay-speed * elapsed from the score (toward 0)."""
        if not self._enabled:
            return
        decay = self._decay_speed * elapsed
        self._score = max(0.0, self._score - decay)

    async def _publish_score(self) -> None:
        """Invoke the score-change callback, if any."""
        if self._on_score_change is not None:
            try:
                await self._on_score_change(self._score)
            except Exception:  # pragma: no cover
                pass

    async def _decay_loop(self) -> None:
        """Run forever (until stop()), periodically applying decay and publishing."""
        while self._running:
            await asyncio.sleep(0.4)
            now = time.monotonic()
            elapsed = now - self._last_update
            if elapsed > 0:
                self._apply_decay(elapsed)
                self._last_update = now
                await self._publish_score()
