from __future__ import annotations

import random
import re
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from stream_cheremsha.overlays.stream_pet_overlay_config import StreamPetOverlayConfig
from stream_cheremsha.overlays.stream_pet_phrases import (
    HUNGRY_DONOR_PHRASE_KEY,
    MOOD_PHRASE_KEYS,
    SLEEP_PHRASE_KEYS,
    idle_phrase_keys,
)

_REACTION_TTL_MS = 5000
_CHAT_ENERGY_CAP_PER_MIN = 3.0
_CHAT_ENERGY_PER_MSG = 0.3
_FOLLOW_ENERGY = 8.0
_LIKE_ENERGY = 0.5
_GIFT_ENERGY = {"small": 5.0, "medium": 15.0, "large": 30.0}
_CHAT_BURST_ENERGY = 10.0
_CHAT_BURST_WINDOW_SEC = 30.0
_CHAT_BURST_MIN_MSGS = 8
_CHAT_BURST_MIN_AUTHORS = 3
_HUNGRY_CHAT_SILENCE_SEC = 180.0
_HUNGRY_GIFT_SILENCE_SEC = 300.0

_EMOJI_RE = re.compile(
    r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F600-\U0001F64F]+",
    flags=re.UNICODE,
)


class StreamPetMood(StrEnum):
    HUNGRY = "hungry"
    CHILL = "chill"
    HYPER = "hyper"
    SLEEP = "sleep"


class StreamPetSpeechKind(StrEnum):
    IDLE = "idle"
    REACTION = "reaction"
    STATE_CHANGE = "state_change"


class GiftTier(StrEnum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class StreamPetEventKind(StrEnum):
    CHAT = "chat"
    LIKE = "like"
    FOLLOW = "follow"
    JOIN = "join"
    GIFT = "gift"
    GIFT_LARGE = "gift_large"
    MEMBER = "member"
    SPAM = "spam"
    CHAT_BURST = "chat_burst"


_EVENT_ANIM: dict[StreamPetEventKind, str] = {
    StreamPetEventKind.CHAT: "walk",
    StreamPetEventKind.LIKE: "jump",
    StreamPetEventKind.FOLLOW: "jump",
    StreamPetEventKind.JOIN: "jump",
    StreamPetEventKind.GIFT: "chew",
    StreamPetEventKind.GIFT_LARGE: "backflip",
    StreamPetEventKind.MEMBER: "jump",
    StreamPetEventKind.SPAM: "scared",
    StreamPetEventKind.CHAT_BURST: "dance",
}


def event_anim(kind: StreamPetEventKind) -> str:
    return _EVENT_ANIM.get(kind, "walk")


@dataclass(slots=True)
class SpeechBubble:
    text: str
    kind: StreamPetSpeechKind
    ttl_ms: int
    anim: str = ""
    user: str = ""

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "text": self.text,
            "kind": str(self.kind),
            "ttl_ms": int(self.ttl_ms),
        }
        if self.anim:
            out["anim"] = self.anim
        if self.user:
            out["user"] = self.user
        return out


@dataclass(slots=True)
class RecentChatMsg:
    author_key: str
    text: str
    at: datetime


_MAX_LEVEL = 3
_ENERGY_CAP = 100.0


def truncate_stream_pet_phrase(text: str, max_chars: int) -> str:
    limit = max(20, int(max_chars))
    body = (text or "").strip()
    if len(body) <= limit:
        return body
    return body[: max(0, limit - 1)].rstrip() + "…"


@dataclass(slots=True)
class StreamPetSession:
    cfg: StreamPetOverlayConfig
    energy: float = 70.0
    level: int = 1
    evolution_count: int = 0
    sleeping: bool = False
    last_chat_at: datetime | None = None
    last_gift_at: datetime | None = None
    last_activity_at: datetime | None = None
    last_donor_name: str = ""
    last_bubble_at: datetime | None = None
    anim_seq: int = 0
    speech: SpeechBubble | None = None
    disco_until: datetime | None = None
    vip_bonus_due: bool = False
    _mood: StreamPetMood = StreamPetMood.CHILL
    _next_idle_bubble_at: datetime | None = None
    _recent_chat: deque[RecentChatMsg] = field(default_factory=lambda: deque(maxlen=64))
    _recent_viewers: deque[str] = field(default_factory=lambda: deque(maxlen=48))
    _chat_energy_this_minute: float = 0.0
    _chat_energy_minute_started: datetime | None = None
    _suppress_mood_bubble: bool = False

    @classmethod
    def fresh(cls, cfg: StreamPetOverlayConfig) -> StreamPetSession:
        now = datetime.now(UTC)
        energy = max(0.0, min(100.0, float(cfg.initial_energy)))
        s = cls(cfg=cfg, energy=energy, last_activity_at=now, last_chat_at=now)
        s._mood = mood_from_energy(energy)
        s._schedule_next_idle_bubble(now)
        return s

    @property
    def mood(self) -> StreamPetMood:
        if self.sleeping:
            return StreamPetMood.SLEEP
        return self._mood

    def to_overlay_dict(self, *, now: datetime | None = None) -> dict[str, Any]:
        at = now or datetime.now(UTC)
        disco_active = self.disco_until is not None and at < self.disco_until
        return {
            "energy": round(self.energy, 1),
            "mood": str(self.mood),
            "level": int(self.level),
            "evolution_count": int(self.evolution_count),
            "disco_active": bool(disco_active),
            "sleeping": bool(self.sleeping),
            "speech": self.speech.to_dict() if self.speech else None,
            "anim_seq": int(self.anim_seq),
            "last_donor": self.last_donor_name,
        }

    def reset_for_new_stream(self) -> None:
        now = datetime.now(UTC)
        self.level = 1
        self.evolution_count = 0
        self.energy = max(0.0, min(_ENERGY_CAP, float(self.cfg.initial_energy)))
        self.sleeping = False
        self.disco_until = None
        self.vip_bonus_due = False
        self.speech = None
        self.last_donor_name = ""
        self._recent_chat.clear()
        self._recent_viewers.clear()
        self._chat_energy_this_minute = 0.0
        self._chat_energy_minute_started = None
        self._suppress_mood_bubble = False
        self.last_activity_at = now
        self.last_chat_at = now
        self.last_gift_at = None
        self._mood = mood_from_energy(self.energy)
        self._schedule_next_idle_bubble(now)

    def pick_vip_viewer(self) -> str:
        if not self._recent_viewers:
            return ""
        return random.choice(list(self._recent_viewers))

    def bump_anim(self) -> None:
        self.anim_seq += 1

    def tick_decay(self, now: datetime) -> bool:
        if self.sleeping or self.energy <= 0.0:
            return False
        per_min = float(self.cfg.decay_per_2min) / 2.0
        self.energy = max(0.0, self.energy - per_min)
        return self._sync_mood(now)

    def check_auto_sleep(self, now: datetime) -> bool:
        if self.sleeping:
            return False
        if self.last_activity_at is None:
            return False
        idle_sec = (now - self.last_activity_at).total_seconds()
        if idle_sec < float(self.cfg.sleep_idle_sec):
            return False
        return self._enter_sleep(now)

    def check_idle_bubble(self, now: datetime) -> bool:
        if self.sleeping:
            return False
        if self.speech is not None and self.speech.kind == StreamPetSpeechKind.REACTION:
            return False
        if self._next_idle_bubble_at is not None and now < self._next_idle_bubble_at:
            return False
        if not self._idle_bubble_conditions_met(now):
            self._schedule_next_idle_bubble(now)
            return False
        return self._show_idle_bubble(now)

    def on_chat(
        self,
        *,
        author: str,
        text: str,
        now: datetime,
        phrase: str | None = None,
    ) -> tuple[bool, StreamPetEventKind | None]:
        author_key = (author or "").strip().casefold() or "?"
        body = (text or "").strip()
        changed = False

        if is_wake_command(body):
            if self.sleeping:
                self.sleeping = False
                self._sync_mood(now)
                self.bump_anim()
                changed = True
            self._touch_activity(now, chat=True)
            return changed, None

        if is_sleep_command(body):
            if not self.sleeping:
                changed = self._enter_sleep(now, phrase=phrase)
            return changed, None

        woke = self._wake_if_sleeping(now)
        changed = woke

        self._recent_chat.append(RecentChatMsg(author_key=author_key, text=body, at=now))
        self._track_viewer(author)
        self._touch_activity(now, chat=True)

        spam = is_chat_spam(body, self._recent_chat, author_key=author_key, now=now)
        if spam:
            return changed, StreamPetEventKind.SPAM

        chat_delta = self._apply_chat_energy(now)
        if chat_delta > 0:
            changed = True

        if self._chat_burst_detected(now):
            if self._add_energy(_CHAT_BURST_ENERGY, now):
                changed = True
            if self._sync_mood(now):
                changed = True
            return changed, StreamPetEventKind.CHAT_BURST

        return changed, StreamPetEventKind.CHAT

    def on_follow(
        self,
        *,
        user: str,
        now: datetime,
        phrase: str | None = None,
    ) -> bool:
        self._wake_if_sleeping(now)
        self._touch_activity(now)
        self._track_viewer(user)
        changed = self._add_energy(_FOLLOW_ENERGY, now)
        mood_changed = self._sync_mood(now)
        reaction = False
        if phrase:
            reaction = self.emit_reaction(
                now,
                author=user,
                phrase=phrase,
                anim=event_anim(StreamPetEventKind.FOLLOW),
            )
        return changed or mood_changed or reaction

    def on_join(
        self,
        *,
        user: str,
        now: datetime,
        phrase: str | None = None,
    ) -> bool:
        self._wake_if_sleeping(now)
        self._touch_activity(now, chat=True)
        self._track_viewer(user)
        reaction = False
        if phrase:
            reaction = self.emit_reaction(
                now,
                author=user,
                phrase=phrase,
                anim=event_anim(StreamPetEventKind.JOIN),
            )
        return reaction

    def on_like(self, *, user: str, now: datetime, phrase: str | None = None) -> bool:
        self._wake_if_sleeping(now)
        self._touch_activity(now)
        self._track_viewer(user)
        changed = self._add_energy(_LIKE_ENERGY, now)
        mood_changed = self._sync_mood(now)
        reaction = False
        if phrase:
            reaction = self.emit_reaction(
                now,
                author=user,
                phrase=phrase,
                anim=event_anim(StreamPetEventKind.LIKE),
            )
        return changed or mood_changed or reaction

    def on_member(
        self,
        *,
        user: str,
        now: datetime,
        phrase: str | None = None,
    ) -> bool:
        self._wake_if_sleeping(now)
        self._touch_activity(now)
        self._track_viewer(user)
        changed = self._add_energy(_FOLLOW_ENERGY, now)
        mood_changed = self._sync_mood(now)
        reaction = False
        if phrase:
            reaction = self.emit_reaction(
                now,
                author=user,
                phrase=phrase,
                anim=event_anim(StreamPetEventKind.MEMBER),
            )
        return changed or mood_changed or reaction

    def on_gift(
        self,
        *,
        user: str,
        tier: GiftTier,
        gift_name: str,
        now: datetime,
        phrase: str | None = None,
        anim: str = "",
    ) -> bool:
        self._wake_if_sleeping(now)
        self._touch_activity(now, gift=True)
        donor = (user or "").strip()
        if donor:
            self.last_donor_name = donor
            self._track_viewer(donor)
        delta = _GIFT_ENERGY.get(str(tier), _GIFT_ENERGY["small"])
        changed = self._add_energy(delta, now)
        mood_changed = self._sync_mood(now)

        if anim == "":
            kind = (
                StreamPetEventKind.GIFT_LARGE if tier == GiftTier.LARGE else StreamPetEventKind.GIFT
            )
            anim = event_anim(kind)

        reaction = False
        if phrase:
            reaction = self.emit_reaction(now, author=user, phrase=phrase, anim=anim)
        return changed or mood_changed or reaction

    def emit_reaction(
        self,
        now: datetime,
        *,
        author: str,
        phrase: str,
        anim: str,
    ) -> bool:
        self.speech = SpeechBubble(
            text=phrase,
            kind=StreamPetSpeechKind.REACTION,
            ttl_ms=_REACTION_TTL_MS,
            anim=anim,
            user=(author or "").strip(),
        )
        self.bump_anim()
        self.last_bubble_at = now
        return True

    def emit_vip_bonus(self, now: datetime, *, phrase_key: str, user: str) -> bool:
        viewer = (user or "").strip()
        if not viewer:
            return False
        self.speech = SpeechBubble(
            text=phrase_key,
            kind=StreamPetSpeechKind.REACTION,
            ttl_ms=_REACTION_TTL_MS,
            anim="dance",
            user=viewer,
        )
        self.bump_anim()
        self.last_bubble_at = now
        return True

    def force_sleep(self, now: datetime, *, phrase: str | None = None) -> bool:
        if self.sleeping:
            return False
        return self._enter_sleep(now, phrase=phrase)

    def _wake_if_sleeping(self, now: datetime) -> bool:
        if not self.sleeping:
            return False
        self.sleeping = False
        self._sync_mood(now)
        self.bump_anim()
        self._touch_activity(now)
        return True

    def _enter_sleep(self, now: datetime, *, phrase: str | None = None) -> bool:
        self.sleeping = True
        self._mood = StreamPetMood.SLEEP
        self.bump_anim()
        key = random.choice(SLEEP_PHRASE_KEYS)
        self.speech = SpeechBubble(
            text=phrase or key,
            kind=StreamPetSpeechKind.IDLE,
            ttl_ms=0,
            anim="sleep",
        )
        self.last_bubble_at = now
        self._schedule_next_idle_bubble(now)
        return True

    def _track_viewer(self, user: str) -> None:
        name = (user or "").strip()
        if not name:
            return
        if name in self._recent_viewers:
            self._recent_viewers.remove(name)
        self._recent_viewers.append(name)

    def _add_energy(self, delta: float, now: datetime) -> bool:
        if delta <= 0.0:
            return False
        self.energy += float(delta)
        evolved = False
        if self.cfg.evolution_enabled:
            while self.energy >= _ENERGY_CAP and self.level < _MAX_LEVEL:
                self.energy -= _ENERGY_CAP
                self.level += 1
                self.evolution_count += 1
                self._on_level_up(now, self.level)
                evolved = True
        self.energy = min(_ENERGY_CAP, self.energy)
        return evolved

    def _on_level_up(self, now: datetime, level: int) -> None:
        floor = max(31.0, float(self.cfg.post_evolution_energy))
        if self.energy < floor:
            self.energy = floor
        self._mood = mood_from_energy(self.energy)
        self._suppress_mood_bubble = True
        self.bump_anim()
        self.speech = SpeechBubble(
            text=f"stream_pet.evolve.{level}",
            kind=StreamPetSpeechKind.STATE_CHANGE,
            ttl_ms=6000,
            anim="jump" if level == 2 else "dance",
        )
        self.last_bubble_at = now
        if level >= _MAX_LEVEL:
            disco_ms = max(1000, int(self.cfg.disco_duration_ms))
            self.disco_until = now + timedelta(milliseconds=disco_ms)
            self.vip_bonus_due = True

    def _touch_activity(self, now: datetime, *, chat: bool = False, gift: bool = False) -> None:
        self.last_activity_at = now
        if chat:
            self.last_chat_at = now
        if gift:
            self.last_gift_at = now

    def _apply_chat_energy(self, now: datetime) -> float:
        if self._chat_energy_minute_started is None:
            self._chat_energy_minute_started = now
            self._chat_energy_this_minute = 0.0
        elif (now - self._chat_energy_minute_started).total_seconds() >= 60.0:
            self._chat_energy_minute_started = now
            self._chat_energy_this_minute = 0.0
        room = _CHAT_ENERGY_CAP_PER_MIN - self._chat_energy_this_minute
        if room <= 0.0:
            return 0.0
        delta = min(_CHAT_ENERGY_PER_MSG, room)
        self._chat_energy_this_minute += delta
        self._add_energy(delta, now)
        return delta

    def _sync_mood(self, now: datetime) -> bool:
        if self.sleeping:
            return False
        if self._suppress_mood_bubble:
            self._suppress_mood_bubble = False
            self._mood = mood_from_energy(self.energy)
            return False
        new_mood = mood_from_energy(self.energy)
        if new_mood == self._mood:
            return False
        self._mood = new_mood
        self.bump_anim()
        self._show_state_change_bubble(now, new_mood)
        return True

    def _show_state_change_bubble(self, now: datetime, mood: StreamPetMood) -> None:
        keys = MOOD_PHRASE_KEYS.get(str(mood), ())
        if not keys:
            return
        key = random.choice(keys)
        self.speech = SpeechBubble(
            text=key,
            kind=StreamPetSpeechKind.STATE_CHANGE,
            ttl_ms=5000,
            anim=_MOOD_ANIM.get(mood, ""),
        )
        self.last_bubble_at = now
        self._schedule_next_idle_bubble(now)

    def _show_idle_bubble(self, now: datetime) -> bool:
        mood = self.mood
        keys = idle_phrase_keys(self.level, str(mood))
        if not keys:
            self._schedule_next_idle_bubble(now)
            return False
        pool = list(keys)
        if mood == StreamPetMood.HUNGRY and self.last_donor_name:
            pool.append(HUNGRY_DONOR_PHRASE_KEY)
        key = random.choice(pool)
        self.speech = SpeechBubble(
            text=key,
            kind=StreamPetSpeechKind.IDLE,
            ttl_ms=5000,
            anim=_MOOD_ANIM.get(mood, ""),
        )
        self.last_bubble_at = now
        self.bump_anim()
        self._schedule_next_idle_bubble(now)
        return True

    def _idle_bubble_conditions_met(self, now: datetime) -> bool:
        mood = self.mood
        if mood == StreamPetMood.HUNGRY:
            chat_silent = (
                self.last_chat_at is None
                or (now - self.last_chat_at).total_seconds() >= _HUNGRY_CHAT_SILENCE_SEC
            )
            gift_silent = (
                self.last_gift_at is None
                or (now - self.last_gift_at).total_seconds() >= _HUNGRY_GIFT_SILENCE_SEC
            )
            return chat_silent or gift_silent
        return True

    def _schedule_next_idle_bubble(self, now: datetime) -> None:
        lo = max(30, int(self.cfg.idle_bubble_min_sec))
        hi = max(lo, int(self.cfg.idle_bubble_max_sec))
        delay = random.randint(lo, hi)
        self._next_idle_bubble_at = now + timedelta(seconds=delay)

    def _chat_burst_detected(self, now: datetime) -> bool:
        cutoff = now - timedelta(seconds=_CHAT_BURST_WINDOW_SEC)
        recent = [m for m in self._recent_chat if m.at >= cutoff]
        if len(recent) < _CHAT_BURST_MIN_MSGS:
            return False
        authors = {m.author_key for m in recent}
        return len(authors) >= _CHAT_BURST_MIN_AUTHORS


_MOOD_ANIM: dict[StreamPetMood, str] = {
    StreamPetMood.HUNGRY: "sad",
    StreamPetMood.CHILL: "walk",
    StreamPetMood.HYPER: "dance",
    StreamPetMood.SLEEP: "sleep",
}


def mood_from_energy(energy: float) -> StreamPetMood:
    e = max(0.0, min(100.0, float(energy)))
    if e <= 30.0:
        return StreamPetMood.HUNGRY
    if e >= 81.0:
        return StreamPetMood.HYPER
    return StreamPetMood.CHILL


def is_sleep_command(text: str) -> bool:
    t = (text or "").strip().casefold()
    return t == "!sleep" or t.startswith("!sleep ")


def is_wake_command(text: str) -> bool:
    t = (text or "").strip().casefold()
    return t in ("!wake", "!прокинься") or t.startswith("!wake ")


def is_chat_spam(
    text: str,
    recent: deque[RecentChatMsg],
    *,
    author_key: str,
    now: datetime,
) -> bool:
    body = (text or "").strip()
    if not body:
        return False

    letters = [c for c in body if c.isalpha()]
    if len(letters) > 5:
        upper = sum(1 for c in letters if c.isupper())
        if upper / len(letters) >= 0.7:
            return True

    emojis = _EMOJI_RE.findall(body)
    if emojis:
        joined = "".join(emojis)
        if len(joined) >= 4 and len(set(joined)) <= 2:
            return True

    cutoff = now - timedelta(seconds=10.0)
    same_author = sum(1 for m in recent if m.author_key == author_key and m.at >= cutoff)
    if same_author >= 3:
        return True
    return False


def classify_gift_tier(
    *,
    platform: str,
    cfg: StreamPetOverlayConfig,
    tiktok_coins: int = 0,
    twitch_bits: int = 0,
    youtube_amount_micros: int = 0,
) -> GiftTier:
    plat = (platform or "").strip().lower()
    if plat == "twitch":
        bits = max(0, int(twitch_bits))
        if bits >= int(cfg.large_gift_threshold_bits):
            return GiftTier.LARGE
        if bits >= int(cfg.small_gift_threshold_bits):
            return GiftTier.MEDIUM
        return GiftTier.SMALL
    if plat == "youtube":
        micros = max(0, int(youtube_amount_micros))
        if micros >= int(cfg.youtube_large_amount_micros):
            return GiftTier.LARGE
        if micros >= int(cfg.youtube_small_amount_micros):
            return GiftTier.MEDIUM
        return GiftTier.SMALL
    coins = max(0, int(tiktok_coins))
    if coins >= int(cfg.large_gift_threshold_coins):
        return GiftTier.LARGE
    if coins >= int(cfg.small_gift_threshold_coins):
        return GiftTier.MEDIUM
    return GiftTier.SMALL
