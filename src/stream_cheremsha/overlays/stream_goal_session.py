from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal


GoalType = Literal["followers", "likes", "gifts", "shares", "comments"]
SkinType = Literal["digital_core", "boss", "reactor", "rocket", "vault", "tower", "creature"]
AnimationIntensity = Literal["low", "medium", "high"]
ResetBehavior = Literal["manual", "after_completion", "new_stream", "daily"]


@dataclass(slots=True)
class Milestone:
    percent: int
    label: str
    effect: str
    triggered: bool = False


@dataclass(slots=True)
class VisualEvent:
    type: str
    payload: dict[str, Any]
    timestamp: float = field(default_factory=time.time)


@dataclass(slots=True)
class StreamGoalSession:
    # Core configuration
    goal_type: GoalType = "followers"
    target_value: int = 10000
    current_value: int = 0
    title: str = "FOLLOW GOAL"
    subtitle: str = ""
    skin: SkinType = "digital_core"
    accent_color: str = "#00ffff"
    scale_percent: int = 100
    animation_intensity: AnimationIntensity = "medium"
    enable_event_animations: bool = True
    enable_combo: bool = True
    enable_milestones: bool = True
    enable_completion_animation: bool = True
    enable_glitch: bool = True
    enable_particles: bool = True
    enable_sound: bool = False
    milestones: list[Milestone] = field(default_factory=list)
    gift_coin_per_progress: int = 10
    combo_window_sec: float = 3.0
    reset_behavior: ResetBehavior = "after_completion"
    next_target_value: int = 25000

    # Runtime state
    combo_count: int = 0
    combo_expires_at: float = 0.0
    core_level: int = 1
    completed_goals: int = 0
    last_event_time: float = 0.0
    is_completing: bool = False
    completion_anim_seq: int = 0

    # Like batching
    _pending_likes: int = 0
    _like_batch_timer: float = 0.0
    _like_batch_window: float = 0.5

    # Visual event queue
    _visual_events: list[VisualEvent] = field(default_factory=list)

    @classmethod
    def from_config(cls, cfg: Any) -> StreamGoalSession:
        milestones = []
        try:
            parsed = json.loads(cfg.milestones_json)
            for m in parsed:
                milestones.append(Milestone(
                    percent=int(m.get("percent", 0)),
                    label=str(m.get("label", "")),
                    effect=str(m.get("effect", "pulse")),
                    triggered=False,
                ))
        except (json.JSONDecodeError, TypeError, ValueError):
            milestones = [
                Milestone(25, "CORE ONLINE", "pulse"),
                Milestone(50, "ENERGY STABLE", "rings"),
                Milestone(75, "CRITICAL ENERGY", "arcs"),
                Milestone(90, "CONTAINMENT FAILURE", "glitch"),
                Milestone(100, "CORE BREACH", "explosion"),
            ]

        return cls(
            goal_type=cfg.goal_type,
            target_value=cfg.target_value,
            current_value=cfg.current_value,
            title=cfg.title,
            subtitle=cfg.subtitle,
            skin=cfg.skin,
            accent_color=cfg.accent_color,
            scale_percent=max(40, min(250, int(getattr(cfg, "scale_percent", 100) or 100))),
            animation_intensity=cfg.animation_intensity,
            enable_event_animations=cfg.enable_event_animations,
            enable_combo=cfg.enable_combo,
            enable_milestones=cfg.enable_milestones,
            enable_completion_animation=cfg.enable_completion_animation,
            enable_glitch=cfg.enable_glitch,
            enable_particles=cfg.enable_particles,
            enable_sound=cfg.enable_sound,
            milestones=milestones,
            gift_coin_per_progress=cfg.gift_coin_per_progress,
            combo_window_sec=cfg.combo_window_sec,
            reset_behavior=cfg.reset_behavior,
            next_target_value=cfg.next_target_value,
        )

    def to_config_dict(self) -> dict[str, Any]:
        return {
            "goal_type": self.goal_type,
            "target_value": self.target_value,
            "current_value": self.current_value,
            "title": self.title,
            "subtitle": self.subtitle,
            "skin": self.skin,
            "accent_color": self.accent_color,
            "scale_percent": int(self.scale_percent),
            "animation_intensity": self.animation_intensity,
            "enable_event_animations": self.enable_event_animations,
            "enable_combo": self.enable_combo,
            "enable_milestones": self.enable_milestones,
            "enable_completion_animation": self.enable_completion_animation,
            "enable_glitch": self.enable_glitch,
            "enable_particles": self.enable_particles,
            "enable_sound": self.enable_sound,
            "milestones_json": json.dumps([
                {"percent": m.percent, "label": m.label, "effect": m.effect}
                for m in self.milestones
            ], ensure_ascii=False),
            "gift_coin_per_progress": self.gift_coin_per_progress,
            "combo_window_sec": self.combo_window_sec,
            "reset_behavior": self.reset_behavior,
            "next_target_value": self.next_target_value,
        }

    @property
    def progress(self) -> float:
        if self.target_value <= 0:
            return 0.0
        return min(1.0, max(0.0, self.current_value / self.target_value))

    @property
    def progress_percent(self) -> int:
        return int(self.progress * 100)

    @property
    def is_complete(self) -> bool:
        return self.current_value >= self.target_value

    @property
    def remaining(self) -> int:
        return max(0, self.target_value - self.current_value)

    def _emit(self, event_type: str, payload: dict[str, Any]) -> None:
        self._visual_events.append(VisualEvent(type=event_type, payload=payload))

    def pop_visual_events(self) -> list[VisualEvent]:
        events = self._visual_events
        self._visual_events = []
        return events

    def _check_combo_expiration(self, now: float) -> None:
        if not self.enable_combo:
            return
        if self.combo_count > 0 and now > self.combo_expires_at:
            self._emit("combo_reset", {"previous_combo": self.combo_count})
            self.combo_count = 0

    def _update_combo(self, now: float) -> None:
        if not self.enable_combo:
            return
        self._check_combo_expiration(now)
        self.combo_count += 1
        self.combo_expires_at = now + self.combo_window_sec
        self._emit("combo_update", {"combo": self.combo_count, "expires_at": self.combo_expires_at})

    def _check_milestones(self) -> None:
        if not self.enable_milestones:
            return
        pct = self.progress_percent
        for m in self.milestones:
            if not m.triggered and pct >= m.percent:
                m.triggered = True
                self._emit("milestone_reached", {
                    "percent": m.percent,
                    "label": m.label,
                    "effect": m.effect,
                })

    def _check_critical_state(self) -> None:
        pct = self.progress_percent
        if pct >= 95:
            self._emit("critical_state", {"level": "extreme", "percent": pct})
        elif pct >= 80:
            self._emit("critical_state", {"level": "high", "percent": pct})
        elif pct >= 60:
            self._emit("critical_state", {"level": "medium", "percent": pct})
        elif pct >= 40:
            self._emit("critical_state", {"level": "low", "percent": pct})

    def _maybe_complete(self) -> bool:
        if self.is_complete and not self.is_completing:
            self.is_completing = True
            self.completion_anim_seq += 1
            self._emit("goal_complete", {
                "anim_seq": self.completion_anim_seq,
                "next_target": self.next_target_value,
            })
            return True
        return False

    def _complete_goal(self) -> None:
        self.completed_goals += 1
        if self.core_level < 5:
            self.core_level += 1
            self._emit("core_evolved", {"level": self.core_level})

        if self.reset_behavior == "after_completion":
            self.current_value = 0
            self.target_value = self.next_target_value
            self.next_target_value = int(self.next_target_value * 1.5)
            for m in self.milestones:
                m.triggered = False
            self.is_completing = False
            self._emit("goal_reset", {
                "new_target": self.target_value,
                "next_target": self.next_target_value,
                "core_level": self.core_level,
            })
        elif self.reset_behavior == "manual":
            self.is_completing = True
        elif self.reset_behavior == "new_stream":
            self.is_completing = True

    def tick(self, now: float | None = None) -> None:
        if now is None:
            now = time.time()
        self._check_combo_expiration(now)
        self._check_critical_state()

    def add_progress(self, amount: int, event_type: str, metadata: dict[str, Any] | None = None) -> None:
        if amount <= 0:
            return
        now = time.time()
        self.last_event_time = now

        old_progress = self.progress
        self.current_value = min(self.target_value, self.current_value + amount)

        self._update_combo(now)
        self._check_milestones()

        if self.enable_event_animations:
            meta = metadata or {}
            payload: dict[str, Any] = {
                "type": event_type,
                "amount": amount,
                "progress": self.progress,
                "progress_percent": self.progress_percent,
                "combo": self.combo_count,
                "metadata": meta,
            }
            if event_type == "gift":
                payload["gift_name"] = str(meta.get("gift_name") or "Gift")
                payload["total_coins"] = int(meta.get("total_coins") or 0)
            if event_type == "like":
                payload["batched"] = bool(meta.get("batched")) or amount > 1
            self._emit("event_absorbed", payload)

        if self._maybe_complete():
            self._complete_goal()

    def add_follow(self, user: str, metadata: dict[str, Any] | None = None) -> None:
        if self.goal_type != "followers":
            return
        self.add_progress(1, "follow", metadata)

    def add_like(self, count: int, metadata: dict[str, Any] | None = None) -> None:
        if self.goal_type != "likes":
            return
        self._pending_likes += count
        self._like_batch_timer = time.time() + self._like_batch_window

    def flush_likes(self) -> None:
        if self._pending_likes > 0:
            count = self._pending_likes
            self._pending_likes = 0
            self.add_progress(count, "like", {"batched": True, "count": count})

    def add_share(self, count: int, metadata: dict[str, Any] | None = None) -> None:
        if self.goal_type != "shares":
            return
        self.add_progress(count, "share", metadata)

    def add_gift(self, sender: str, gift_name: str, count: int, coins_each: int, metadata: dict[str, Any] | None = None) -> None:
        if self.goal_type != "gifts":
            return
        total_coins = coins_each * count
        progress = max(1, total_coins // self.gift_coin_per_progress)
        meta = {"sender": sender, "gift_name": gift_name, "count": count, "coins_each": coins_each, "total_coins": total_coins}
        if metadata:
            meta.update(metadata)
        self.add_progress(progress, "gift", meta)

    def add_comment(self, user: str, text: str, metadata: dict[str, Any] | None = None) -> None:
        if self.goal_type != "comments":
            return
        self.add_progress(1, "comment", {"user": user, "text": text, **(metadata or {})})

    def reset_for_new_stream(self) -> None:
        self.current_value = 0
        self.target_value = self.next_target_value
        self.next_target_value = int(self.next_target_value * 1.5)
        for m in self.milestones:
            m.triggered = False
        self.combo_count = 0
        self.combo_expires_at = 0.0
        self.is_completing = False
        self._emit("goal_reset", {
            "new_target": self.target_value,
            "next_target": self.next_target_value,
            "core_level": self.core_level,
        })

    def reset_manual(self) -> None:
        self.current_value = 0
        for m in self.milestones:
            m.triggered = False
        self.is_completing = False
        self._emit("goal_reset", {
            "new_target": self.target_value,
            "next_target": self.next_target_value,
            "core_level": self.core_level,
        })

    def to_overlay_dict(self) -> dict[str, Any]:
        return {
            "goal_type": self.goal_type,
            "title": self.title,
            "subtitle": self.subtitle,
            "current_value": self.current_value,
            "target_value": self.target_value,
            "progress": self.progress,
            "progress_percent": self.progress_percent,
            "remaining": self.remaining,
            "skin": self.skin,
            "accent_color": self.accent_color,
            "scale_percent": int(self.scale_percent),
            "animation_intensity": self.animation_intensity,
            "enable_particles": self.enable_particles,
            "enable_glitch": self.enable_glitch,
            "combo_count": self.combo_count,
            "combo_expires_at": self.combo_expires_at,
            "core_level": self.core_level,
            "completed_goals": self.completed_goals,
            "is_completing": self.is_completing,
            "completion_anim_seq": self.completion_anim_seq,
            "milestones": [
                {"percent": m.percent, "label": m.label, "effect": m.effect, "triggered": m.triggered}
                for m in self.milestones
            ],
            "visual_events": [
                {"type": e.type, "payload": e.payload, "timestamp": e.timestamp}
                for e in self.pop_visual_events()
            ],
        }