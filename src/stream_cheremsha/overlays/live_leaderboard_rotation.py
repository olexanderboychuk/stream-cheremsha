from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

SCENE_HALL_OF_FAME = "hall_of_fame"
SCENE_ARENA = "arena"
SCENE_ENERGY_NETWORK = "energy_network"

ALL_SCENES = (SCENE_HALL_OF_FAME, SCENE_ARENA, SCENE_ENERGY_NETWORK)

SOURCE_LIKERS = "likers"
SOURCE_GIFTERS = "gifters"
SOURCE_SHARERS = "sharers"
SOURCE_COMMENTERS = "commenters"
SOURCE_CONTRIBUTORS = "contributors"

ALL_SOURCES = (
    SOURCE_LIKERS,
    SOURCE_GIFTERS,
    SOURCE_SHARERS,
    SOURCE_COMMENTERS,
    SOURCE_CONTRIBUTORS,
)


@dataclass(frozen=True, slots=True)
class RotationStep:
    source_id: str
    scene_id: str
    duration_sec: float


@dataclass(slots=True)
class LiveLeaderboardRotationEngine:
    """Owns presentation timeline only. Never reads TikTok events."""

    sequence: list[RotationStep]
    sequence_index: int = 0
    transition_token: int = 1
    scene_started_at_ms: int = 0
    _active: bool = False

    def __post_init__(self) -> None:
        if not self.sequence:
            self.sequence = [
                RotationStep(SOURCE_LIKERS, SCENE_HALL_OF_FAME, 8.0),
            ]
        self.sequence_index = max(0, int(self.sequence_index)) % len(self.sequence)
        if self.scene_started_at_ms <= 0:
            self.scene_started_at_ms = int(time.time() * 1000)
        self._active = True

    @classmethod
    def from_steps(
        cls,
        steps: list[RotationStep] | list[dict[str, Any]],
        *,
        now_ms: int | None = None,
    ) -> LiveLeaderboardRotationEngine:
        parsed: list[RotationStep] = []
        for raw in steps:
            if isinstance(raw, RotationStep):
                parsed.append(raw)
                continue
            if not isinstance(raw, dict):
                continue
            src = str(raw.get("source_id") or raw.get("source") or "").strip().lower()
            scene = str(raw.get("scene_id") or raw.get("scene") or "").strip().lower()
            try:
                dur = float(raw.get("duration_sec", raw.get("duration", 8)))
            except (TypeError, ValueError):
                dur = 8.0
            if src not in ALL_SOURCES or scene not in ALL_SCENES:
                continue
            parsed.append(RotationStep(src, scene, max(1.0, min(120.0, dur))))
        if not parsed:
            parsed = [RotationStep(SOURCE_LIKERS, SCENE_HALL_OF_FAME, 8.0)]
        started = int(now_ms if now_ms is not None else time.time() * 1000)
        return cls(
            sequence=parsed, sequence_index=0, transition_token=1, scene_started_at_ms=started
        )

    @property
    def current_step(self) -> RotationStep:
        return self.sequence[self.sequence_index % len(self.sequence)]

    def replace_sequence(
        self,
        steps: list[RotationStep],
        *,
        now_ms: int | None = None,
        preserve_position: bool = False,
    ) -> None:
        if not steps:
            steps = [RotationStep(SOURCE_LIKERS, SCENE_HALL_OF_FAME, 8.0)]
        old = self.current_step
        self.sequence = list(steps)
        if preserve_position:
            for i, step in enumerate(self.sequence):
                if step.source_id == old.source_id and step.scene_id == old.scene_id:
                    self.sequence_index = i
                    break
            else:
                self.sequence_index = 0
                self.transition_token += 1
                self.scene_started_at_ms = int(now_ms if now_ms is not None else time.time() * 1000)
        else:
            self.sequence_index = 0
            self.transition_token += 1
            self.scene_started_at_ms = int(now_ms if now_ms is not None else time.time() * 1000)

    def advance(self, *, now_ms: int | None = None) -> RotationStep:
        """Advance to the next scene. Increments transition_token."""
        n = len(self.sequence)
        self.sequence_index = (self.sequence_index + 1) % n
        self.transition_token += 1
        self.scene_started_at_ms = int(now_ms if now_ms is not None else time.time() * 1000)
        return self.current_step

    def tick(self, *, now_ms: int | None = None) -> bool:
        """Return True if the scene advanced due to elapsed duration."""
        now = int(now_ms if now_ms is not None else time.time() * 1000)
        step = self.current_step
        elapsed = now - int(self.scene_started_at_ms)
        need = int(max(1.0, float(step.duration_sec)) * 1000)
        if elapsed < need:
            return False
        self.advance(now_ms=now)
        return True

    def presentation_dict(self, *, server_now_ms: int | None = None) -> dict[str, Any]:
        now = int(server_now_ms if server_now_ms is not None else time.time() * 1000)
        step = self.current_step
        return {
            "source_id": step.source_id,
            "scene_id": step.scene_id,
            "sequence_index": int(self.sequence_index),
            "scene_started_at_ms": int(self.scene_started_at_ms),
            "scene_duration_ms": int(max(1.0, float(step.duration_sec)) * 1000),
            "transition_token": int(self.transition_token),
            "server_now_ms": now,
        }


def filter_sequence_for_config(
    steps: list[RotationStep],
    *,
    enabled_sources: set[str],
    enabled_scenes: set[str],
) -> list[RotationStep]:
    out = [s for s in steps if s.source_id in enabled_sources and s.scene_id in enabled_scenes]
    if out:
        return out
    # Fallback: first enabled source × first enabled scene
    src = next((s for s in ALL_SOURCES if s in enabled_sources), SOURCE_LIKERS)
    scene = next((s for s in ALL_SCENES if s in enabled_scenes), SCENE_HALL_OF_FAME)
    return [RotationStep(src, scene, 8.0)]
