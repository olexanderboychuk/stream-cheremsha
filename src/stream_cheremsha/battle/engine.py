from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any

from stream_cheremsha.battle.models import (
    BattleEvent,
    BattleState,
    BattleStatus,
    ComboState,
    Participant,
    Team,
)


@dataclass(slots=True)
class _AutoEntry:
    key: str
    name: str
    avatar: str
    diamonds: int
    ts: float


def _coerce_float(v: Any, default: float) -> float:
    try:
        f = float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    if f != f:  # NaN guard
        return default
    return f


class BattleEngine:
    def __init__(self, cfg_provider) -> None:  # noqa: ANN001 - duck-typed config
        self._cfg = cfg_provider
        self._state = BattleState(teams=[Team(id="left"), Team(id="right")])
        self._auto: list[_AutoEntry] = []
        self._combo_hits: dict[str, list[float]] = {"left": [], "right": []}
        self._comeback_armed: bool = False
        self._close_fired: bool = False
        self._final_push_fired: bool = False
        self._trailer: str | None = None

    # -- lifecycle ---------------------------------------------------------
    def reset(self) -> None:
        best = 3
        try:
            best = int(getattr(self._cfg(), "best_of", 3))
        except (TypeError, ValueError):
            best = 3
        if best not in (1, 3, 5):
            best = 3
        self._state = BattleState(best_of=best, teams=[Team(id="left"), Team(id="right")])
        self._auto.clear()
        self._combo_hits = {"left": [], "right": []}
        self._comeback_armed = False
        self._close_fired = False
        self._final_push_fired = False
        self._trailer = None

    # -- public API --------------------------------------------------------
    def snapshot(self) -> dict[str, Any]:
        st = self._state
        try:
            cfg = self._cfg()
            duration_s = int(getattr(cfg, "round_duration_s", 60))
        except (TypeError, ValueError):
            duration_s = 60
        round_wins = {t.id: int(t.round_wins) for t in st.teams}
        for tid in ("left", "right"):
            round_wins.setdefault(tid, 0)
        winner = None
        if st.winner_team_id is not None:
            name = st.winner_team_id
            for p in st.participants:
                if p.team_id == st.winner_team_id:
                    name = p.name
                    break
            winner = {"team_id": st.winner_team_id, "name": name}
        return {
            "battle_id": st.battle_id,
            "status": st.status.value,
            "round": int(st.round),
            "best_of": int(st.best_of),
            "round_wins": round_wins,
            "duration_s": duration_s,
            "remaining_seconds": int(st.remaining_seconds),
            "countdown_remaining_s": int(st.countdown_remaining_s),
            "participants": [p.to_dict() for p in st.participants],
            "teams": [t.to_dict() for t in st.teams],
            "combo": st.combo.to_dict(),
            "flags": {
                "is_close": bool(st.is_close),
                "is_comeback": bool(st.is_comeback),
                "final_push": bool(st.final_push),
            },
            "events": [e.to_dict() for e in st.events],
            "winner": winner,
        }

    def start_manual(self, rows: list[dict[str, str]], *, now: float | None = None) -> bool:
        t = time.monotonic() if now is None else float(now)
        st = self._state
        if st.status not in (BattleStatus.IDLE, BattleStatus.FINISHED):
            return False
        seen: dict[str, dict[str, str]] = {}
        for r in rows or []:
            key = (
                str(r.get("user_key") or r.get("id") or "").strip()
                or str(r.get("user") or r.get("name") or r.get("display") or "").casefold().strip()
            )
            if not key or key in seen:
                continue
            seen[key] = {
                "key": key,
                "name": str(r.get("user") or r.get("name") or r.get("display") or "?"),
                "avatar": str(r.get("avatar_url") or r.get("avatar") or ""),
            }
        if len(seen) < 2:
            return False
        first_two = list(seen.values())[:2]
        self._lock_slots(first_two[0], first_two[1], now=t)
        return True

    def on_gift(
        self,
        *,
        user_key: str,
        display: str,
        avatar_url: str,
        diamonds: int,
        now: float | None = None,
    ) -> list[dict[str, Any]]:
        t = time.monotonic() if now is None else float(now)
        try:
            dia = int(diamonds)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return []
        if dia <= 0:
            return []
        key = str(user_key or "").strip() or str(display or "").casefold().strip()
        if not key:
            return []
        name = str(display or "").strip() or "?"
        avatar = str(avatar_url or "")
        st = self._state
        cfg = self._cfg()

        if st.status == BattleStatus.IDLE:
            if not bool(getattr(cfg, "auto_start", True)):
                return []
            try:
                window_s = int(getattr(cfg, "auto_window_s", 30))
                threshold = int(getattr(cfg, "auto_threshold_each", 100))
            except (TypeError, ValueError):
                return []
            self._auto.append(_AutoEntry(key=key, name=name, avatar=avatar, diamonds=dia, ts=t))
            cutoff = t - max(1, window_s)
            self._auto = [e for e in self._auto if e.ts >= cutoff]
            # Per-user max single gift within window must meet threshold.
            best_by_user: dict[str, _AutoEntry] = {}
            for e in self._auto:
                prev = best_by_user.get(e.key)
                if prev is None or e.diamonds > prev.diamonds:
                    best_by_user[e.key] = e
            qualified = [e for e in best_by_user.values() if e.diamonds >= threshold]
            if len(qualified) >= 2:
                qualified.sort(key=lambda e: e.diamonds, reverse=True)
                q0, q1 = qualified[0], qualified[1]
                self._lock_slots(
                    {"key": q0.key, "name": q0.name, "avatar": q0.avatar},
                    {"key": q1.key, "name": q1.name, "avatar": q1.avatar},
                    now=t,
                )
                out = [e.to_dict() for e in st.events[-2:]]
                return out
            return []

        if st.status in (BattleStatus.COUNTDOWN, BattleStatus.FINISHED):
            return []

        if st.status != BattleStatus.ACTIVE:
            return []

        participant = st.participant(key)
        if participant is None:
            return []
        if not bool(getattr(cfg, "gifts_enabled", True)):
            return []
        team_id = participant.team_id

        # Combo update.
        try:
            combo_window_s = max(1, int(getattr(cfg, "combo_window_s", 5)))
            combo_threshold = max(2, int(getattr(cfg, "combo_threshold", 5)))
            combo_enabled = bool(getattr(cfg, "combo_enabled", True))
            max_mult = _coerce_float(getattr(cfg, "combo_max_multiplier", 3.0), 3.0)
        except (TypeError, ValueError):
            combo_window_s, combo_threshold, combo_enabled, max_mult = 5, 5, True, 3.0
        hits = self._combo_hits.setdefault(team_id, [])
        hits = [h for h in hits if h >= t - combo_window_s]
        hits.append(t)
        self._combo_hits[team_id] = hits
        count = len(hits)
        mult = 1.0
        combo_event: BattleEvent | None = None
        if combo_enabled and count >= combo_threshold:
            target = 2.0 if count < 2 * combo_threshold else 3.0
            mult = min(max(1.0, max_mult), target)
            first = st.combo.count < combo_threshold or st.combo.team_id != team_id
            st.combo = ComboState(
                team_id=team_id, count=count, multiplier=mult, window_start=hits[0]
            )
            combo_event = BattleEvent(
                type="combo_started" if first else "combo_updated",
                team_id=team_id,
                payload={"count": count, "multiplier": mult},
                at=t,
            )
            st.push_event(combo_event)
        else:
            if st.combo.team_id != team_id:
                st.combo = ComboState(team_id=None, count=0, multiplier=1.0, window_start=0.0)

        try:
            gift_mult = _coerce_float(getattr(cfg, "gift_multiplier", 1.0), 1.0)
        except (TypeError, ValueError):
            gift_mult = 1.0
        points = int(dia * gift_mult * mult)
        if points <= 0:
            return []

        participant.score += points
        team = st.team(team_id)
        if team is not None:
            team.score += points

        emitted: list[BattleEvent] = []
        emitted.append(
            BattleEvent(
                type="gift_received",
                team_id=team_id,
                payload={"user": name, "points": points, "diamonds": dia, "multiplier": mult},
                at=t,
            )
        )
        left = st.team("left")
        right = st.team("right")
        emitted.append(
            BattleEvent(
                type="score_changed",
                team_id=team_id,
                payload={
                    "left": int(left.score if left else 0),
                    "right": int(right.score if right else 0),
                },
                at=t,
            )
        )
        if dia >= 500:
            emitted.append(
                BattleEvent(
                    type="big_gift", team_id=team_id, payload={"user": name, "diamonds": dia}, at=t
                )
            )
        for ev in emitted:
            st.push_event(ev)
        out_events = ([combo_event] if combo_event is not None else []) + emitted
        out_events += self._evaluate_comeback_close(t)
        return [e.to_dict() for e in out_events]

    def on_like(
        self, *, user_key: str, count: int, now: float | None = None
    ) -> list[dict[str, Any]]:
        return []  # v1 disabled-path interface (config likes_enabled respected when wired later)

    def on_follow(self, *, user_key: str, now: float | None = None) -> list[dict[str, Any]]:
        return []

    def tick(self, now: float | None = None) -> list[dict[str, Any]]:
        t = time.monotonic() if now is None else float(now)
        st = self._state
        cfg = self._cfg()
        out: list[BattleEvent] = []

        if st.status == BattleStatus.COUNTDOWN:
            try:
                cd = st.countdown_deadline
            except AttributeError:
                cd = None
            if cd is None:
                return []
            remaining = int(max(0, round(cd - t)))
            st.countdown_remaining_s = remaining
            if t >= cd:
                try:
                    duration = max(30, int(getattr(cfg, "round_duration_s", 60)))
                except (TypeError, ValueError):
                    duration = 60
                st.status = BattleStatus.ACTIVE
                st.round_deadline = t + duration
                st.remaining_seconds = duration
                ev = BattleEvent(
                    type="round_started",
                    payload={"round": int(st.round), "best_of": int(st.best_of)},
                    at=t,
                )
                st.push_event(ev)
                out.append(ev)
            return [e.to_dict() for e in out]

        if st.status == BattleStatus.ACTIVE:
            try:
                duration = max(30, int(getattr(cfg, "round_duration_s", 60)))
            except (TypeError, ValueError):
                duration = 60
            rd = st.round_deadline
            if rd is not None:
                st.remaining_seconds = int(max(0, round(rd - t)))
            # Combo expiry.
            try:
                combo_window_s = max(1, int(getattr(cfg, "combo_window_s", 5)))
            except (TypeError, ValueError):
                combo_window_s = 5
            expired = True
            for _tid, hits in self._combo_hits.items():
                kept = [h for h in hits if h >= t - combo_window_s]
                self._combo_hits[_tid] = kept
                if kept:
                    expired = False
            if expired and st.combo.count > 0:
                st.combo = ComboState(team_id=None, count=0, multiplier=1.0, window_start=0.0)
                ev = BattleEvent(type="combo_broken", payload={}, at=t)
                st.push_event(ev)
                out.append(ev)
            # Final push.
            try:
                fp_seconds = max(3, int(getattr(cfg, "final_push_seconds", 10)))
                comeback_on = bool(getattr(cfg, "comeback_enabled", True))
                close_pct = int(getattr(cfg, "close_threshold_pct", 10))
            except (TypeError, ValueError):
                fp_seconds, comeback_on, close_pct = 10, True, 10
            left = st.team("left")
            right = st.team("right")
            a = int(left.score) if left else 0
            b = int(right.score) if right else 0
            gap = abs(a - b) / max(1, max(a, b)) if max(a, b) > 0 else 1.0
            if (
                comeback_on
                and not self._final_push_fired
                and st.remaining_seconds <= fp_seconds
                and gap <= close_pct / 100.0
                and a >= 20
                and b >= 20
            ):
                self._final_push_fired = True
                st.final_push = True
                ev = BattleEvent(
                    type="final_push",
                    payload={"remaining": int(st.remaining_seconds)},
                    at=t,
                )
                st.push_event(ev)
                out.append(ev)
            if rd is not None and t >= rd:
                out += self._resolve_round(t)
            return [e.to_dict() for e in out]

        if st.status == BattleStatus.FINISHED:
            vd = st.victory_deadline
            if vd is not None and t >= vd:
                try:
                    auto_reset = bool(getattr(cfg, "auto_reset", True))
                except (TypeError, ValueError):
                    auto_reset = True
                if auto_reset:
                    self.reset()
            return []

        return []

    # -- internals ---------------------------------------------------------
    def _lock_slots(self, first: dict[str, str], second: dict[str, str], *, now: float) -> None:
        st = self._state
        cfg = self._cfg()
        try:
            best_of = int(getattr(cfg, "best_of", 3))
        except (TypeError, ValueError):
            best_of = 3
        if best_of not in (1, 3, 5):
            best_of = 3
        try:
            countdown_s = max(1, min(10, int(getattr(cfg, "countdown_s", 5))))
            duration = max(30, min(300, int(getattr(cfg, "round_duration_s", 60))))
        except (TypeError, ValueError):
            countdown_s, duration = 5, 60
        st.battle_id = uuid.uuid4().hex[:12]
        st.best_of = best_of
        st.round = 1
        st.participants = [
            Participant(
                id=first["key"],
                name=first["name"],
                avatar_url=first.get("avatar", ""),
                team_id="left",
                score=0,
            ),
            Participant(
                id=second["key"],
                name=second["name"],
                avatar_url=second.get("avatar", ""),
                team_id="right",
                score=0,
            ),
        ]
        st.teams = [Team(id="left", score=0, round_wins=0), Team(id="right", score=0, round_wins=0)]
        st.combo = ComboState()
        st.events = []
        st.winner_team_id = None
        st.is_close = False
        st.is_comeback = False
        st.final_push = False
        st.status = BattleStatus.COUNTDOWN
        st.countdown_deadline = now + countdown_s
        st.countdown_remaining_s = countdown_s
        st.remaining_seconds = duration
        st.round_deadline = None
        st.victory_deadline = None
        self._auto.clear()
        self._combo_hits = {"left": [], "right": []}
        self._comeback_armed = False
        self._close_fired = False
        self._final_push_fired = False
        self._trailer = None
        st.push_event(
            BattleEvent(type="battle_started", payload={"battle_id": st.battle_id}, at=now)
        )
        st.push_event(
            BattleEvent(type="round_started", payload={"round": 1, "best_of": best_of}, at=now)
        )

    def _evaluate_comeback_close(self, t: float) -> list[BattleEvent]:
        st = self._state
        cfg = self._cfg()
        try:
            comeback_on = bool(getattr(cfg, "comeback_enabled", True))
            comeback_pct = int(getattr(cfg, "comeback_threshold_pct", 20))
            close_pct = int(getattr(cfg, "close_threshold_pct", 10))
        except (TypeError, ValueError):
            return []
        if not comeback_on:
            return []
        left = st.team("left")
        right = st.team("right")
        if left is None or right is None:
            return []
        a, b = int(left.score), int(right.score)
        top = max(a, b)
        out: list[BattleEvent] = []
        if top <= 0:
            return []
        gap = abs(a - b) / max(1, top)
        trailer = "right" if a >= b else "left"
        # Arm comeback when trailing by threshold with noise floor.
        if not self._comeback_armed and top >= 50 and gap >= comeback_pct / 100.0:
            self._comeback_armed = True
            self._trailer = trailer
        # Overtake → comeback once. The stored trailer was trailing at arm time;
        # it has completed an overtake as soon as it now leads the opposing team.
        if self._comeback_armed and self._trailer is not None:
            tr_team = st.team(self._trailer)
            opp_team = st.team("right" if self._trailer == "left" else "left")
            tr_score = int(tr_team.score) if tr_team is not None else 0
            opp_score = int(opp_team.score) if opp_team is not None else 0
            if tr_team is not None and opp_team is not None and tr_score > opp_score:
                ev = BattleEvent(
                    type="comeback",
                    team_id=self._trailer,
                    payload={"winner": self._trailer},
                    at=t,
                )
                st.push_event(ev)
                out.append(ev)
                st.is_comeback = True
                self._comeback_armed = False
                self._trailer = None
        # Close battle once per approach.
        if gap <= close_pct / 100.0 and top >= 20 and not self._close_fired:
            self._close_fired = True
            st.is_close = True
            ev = BattleEvent(type="close_battle", payload={"left": a, "right": b}, at=t)
            st.push_event(ev)
            out.append(ev)
        elif gap > (close_pct / 100.0) * 1.5:
            st.is_close = False
            self._close_fired = False
        return out

    def _resolve_round(self, t: float) -> list[BattleEvent]:
        st = self._state
        cfg = self._cfg()
        try:
            best_of = int(getattr(cfg, "best_of", 3))
            duration = max(30, min(300, int(getattr(cfg, "round_duration_s", 60))))
            countdown_s = max(1, min(10, int(getattr(cfg, "countdown_s", 5))))
            victory_s = max(3, min(15, int(getattr(cfg, "victory_display_s", 8))))
        except (TypeError, ValueError):
            best_of, duration, countdown_s, victory_s = 3, 60, 5, 8
        if best_of not in (1, 3, 5):
            best_of = 3
        left = st.team("left")
        right = st.team("right")
        a = int(left.score) if left else 0
        b = int(right.score) if right else 0
        out: list[BattleEvent] = []
        majority = best_of // 2 + 1
        if a == 0 and b == 0:
            ev = BattleEvent(
                type="round_finished",
                payload={"round": int(st.round), "draw": True, "left": a, "right": b},
                at=t,
            )
            st.push_event(ev)
            out.append(ev)
            # A drawn round consumes itself: replaying the same round would
            # freeze the live widget (spectator gifts score nothing, so rounds
            # end 0-0) in an endless round-1 countdown/active loop.
            st.round += 1
            st.round_deadline = None
            st.status = BattleStatus.COUNTDOWN
            st.countdown_deadline = t + countdown_s
            st.countdown_remaining_s = countdown_s
            if left is not None:
                left.score = 0
            if right is not None:
                right.score = 0
            for p in st.participants:
                p.score = 0
            st.combo = ComboState()
            self._combo_hits = {"left": [], "right": []}
            self._comeback_armed = False
            self._close_fired = False
            self._final_push_fired = False
            self._trailer = None
            st.is_close = False
            st.final_push = False
            st.remaining_seconds = duration
            return out
        winner = "left" if a >= b else "right"  # exact tie >0 → left (deterministic)
        wteam = st.team(winner)
        if wteam is not None:
            wteam.round_wins += 1
            wins = int(wteam.round_wins)
        else:
            wins = 0
        ev = BattleEvent(
            type="round_finished",
            team_id=winner,
            payload={"round": int(st.round), "winner": winner, "left": a, "right": b},
            at=t,
        )
        st.push_event(ev)
        out.append(ev)
        if wins >= majority:
            st.status = BattleStatus.FINISHED
            st.winner_team_id = winner
            st.victory_deadline = t + victory_s
            st.remaining_seconds = 0
            fin = BattleEvent(
                type="battle_finished",
                team_id=winner,
                payload={
                    "winner": winner,
                    "left": a,
                    "right": b,
                    "round_wins": {t2.id: int(t2.round_wins) for t2 in st.teams},
                },
                at=t,
            )
            st.push_event(fin)
            out.append(fin)
            return out
        # Next round.
        st.round += 1
        st.status = BattleStatus.COUNTDOWN
        st.countdown_deadline = t + countdown_s
        st.countdown_remaining_s = countdown_s
        st.remaining_seconds = duration
        st.round_deadline = None
        if left is not None:
            left.score = 0
        if right is not None:
            right.score = 0
        for p in st.participants:
            p.score = 0
        st.combo = ComboState()
        self._combo_hits = {"left": [], "right": []}
        self._comeback_armed = False
        self._close_fired = False
        self._final_push_fired = False
        self._trailer = None
        st.is_close = False
        st.is_comeback = False
        st.final_push = False
        return out
