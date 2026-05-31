from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from stream_cheremsha.battle_royale.gifts import assign_support_gifts, fighter_index_for_gift
from stream_cheremsha.battle_royale.models import BattleFighter, BattleHit, BattlePhase, BattleState
from stream_cheremsha.overlays.battle_royale_overlay_config import (
    BattleRoyaleOverlayConfig,
    load_battle_royale_overlay_config,
)
from stream_cheremsha.persistence.battle_royale_wins_sqlite import fetch_battle_stats_for_users


def _fighter_side(index: int, total: int) -> str:
    if total == 2:
        return "left" if index == 0 else "right"
    return f"slot{index}"


@dataclass(slots=True)
class _AutoGiftEntry:
    user_key: str
    display_name: str
    avatar_url: str
    diamonds: int
    ts: float


@dataclass(slots=True)
class VipReward:
    user_key: str
    display_name: str
    until: datetime


class BattleRoyaleController:
    """In-memory battle session state machine."""

    def __init__(self) -> None:
        self._state = BattleState()
        self._auto_buffer: list[_AutoGiftEntry] = []
        self._vip: VipReward | None = None
        self._on_battle_ended: list[Any] = []
        self._session_cfg: BattleRoyaleOverlayConfig | None = None

    def reset(self) -> None:
        self._state = BattleState()
        self._auto_buffer.clear()
        self._session_cfg = None

    def _effective_config(self) -> BattleRoyaleOverlayConfig:
        return self._session_cfg or self.config()

    def is_active_or_arming(self) -> bool:
        return self._state.phase in (
            BattlePhase.COUNTDOWN,
            BattlePhase.ACTIVE,
            BattlePhase.VICTORY,
        )

    def is_active(self) -> bool:
        return self._state.phase == BattlePhase.ACTIVE

    def state(self) -> BattleState:
        return self._state

    def config(self) -> BattleRoyaleOverlayConfig:
        return load_battle_royale_overlay_config()

    def vip_reward(self) -> VipReward | None:
        if self._vip is None:
            return None
        if datetime.now(UTC) >= self._vip.until:
            self._vip = None
            return None
        return self._vip

    def is_vip_user(self, user_key: str) -> bool:
        vip = self.vip_reward()
        if vip is None:
            return False
        return (user_key or "").strip() == vip.user_key

    def start_manual(
        self,
        fighters: list[dict[str, str]],
        *,
        cfg: BattleRoyaleOverlayConfig | None = None,
    ) -> bool:
        c = cfg or self.config()
        if self._state.phase not in (BattlePhase.IDLE, BattlePhase.VICTORY):
            return False
        built = self._build_fighters(fighters, max_hp=c.max_hp, max_fighters=c.max_fighters)
        if len(built) < 2:
            return False
        self._begin_countdown(built, cfg=c)
        return True

    def stop(self) -> None:
        self._state = BattleState()
        self._auto_buffer.clear()
        self._session_cfg = None

    def tick(self, *, now: float | None = None) -> bool:
        """Advance countdown/timer. Returns True if overlay should refresh."""
        t = now if now is not None else time.monotonic()
        st = self._state
        cfg = self._effective_config()
        if st.phase == BattlePhase.COUNTDOWN:
            if st.countdown_deadline is not None and t >= st.countdown_deadline:
                self._activate_round(cfg)
                return True
            remaining = max(0, int(st.countdown_deadline - t)) if st.countdown_deadline else 0
            if remaining != st.countdown_remaining_s:
                st.countdown_remaining_s = remaining
                return True
            return False
        if st.phase == BattlePhase.ACTIVE:
            if st.round_deadline is not None and t >= st.round_deadline:
                self._resolve_by_hp(cfg)
                return True
            remaining = max(0, int(st.round_deadline - t)) if st.round_deadline else 0
            if remaining != st.timer_remaining_s:
                st.timer_remaining_s = remaining
                return True
            return False
        if st.phase == BattlePhase.VICTORY:
            if st.victory_deadline is not None and t >= st.victory_deadline:
                self._state = BattleState()
                self._session_cfg = None
                return True
        return False

    def set_session_config(self, cfg: BattleRoyaleOverlayConfig) -> None:
        """For tests or explicit session config before auto-arm."""
        self._session_cfg = cfg

    def on_gift(
        self,
        *,
        sender_user_key: str,
        sender_display: str,
        sender_avatar_url: str,
        diamonds: int,
        gift_id: str = "",
        gift_name: str = "",
        now: float | None = None,
    ) -> BattleHit | None:
        if diamonds <= 0:
            return None
        t = now if now is not None else time.monotonic()
        cfg = self._effective_config()
        key = (sender_user_key or "").strip() or (sender_display or "").strip().casefold()
        name = (sender_display or "").strip() or "?"
        av = (sender_avatar_url or "").strip()

        st = self._state
        if st.phase == BattlePhase.IDLE and cfg.auto_arm_enabled:
            self._record_auto_gift(key, name, av, diamonds, t)
            pair = self._try_auto_arm(cfg, t)
            if pair is not None:
                self._begin_countdown(pair, cfg=cfg)
            return None

        if st.phase != BattlePhase.ACTIVE:
            return None

        supporter_idx = fighter_index_for_gift(
            st.fighters,
            gift_id=gift_id,
            gift_name=gift_name,
        )
        if supporter_idx is not None:
            return self._apply_fighter_gift(supporter_idx, diamonds, cfg)
        return None

    def overlay_patch(self) -> dict[str, Any]:
        st = self._state
        cfg = self._effective_config()
        fighters = [f.to_dict() for f in st.fighters]
        winner = None
        if st.winner_key:
            winner = {
                "user_key": st.winner_key,
                "user": st.winner_display,
                "avatar_url": st.winner_avatar_url,
            }
        last_hit = st.last_hit.to_dict() if st.last_hit else None
        last_attack = self._last_attack_payload(st, last_hit)
        keys = [f.user_key for f in st.fighters]
        stats = fetch_battle_stats_for_users(keys)
        for f in fighters:
            row = stats.get(str(f.get("user_key") or ""), {})
            f["wins"] = int(row.get("wins") or 0)
            f["rank"] = int(row.get("rank") or 0)
        vip = self.vip_reward()
        vip_patch = None
        if vip is not None:
            vip_patch = {
                "user_key": vip.user_key,
                "user": vip.display_name,
                "until_iso": vip.until.isoformat(),
            }
        auto_candidates = 0
        if st.phase == BattlePhase.IDLE and cfg.auto_arm_enabled:
            auto_candidates = self.count_auto_arm_candidates(cfg=cfg)
        return {
            "phase": st.phase.value,
            "session_id": st.session_id,
            "fighters": fighters,
            "timer_remaining_s": int(st.timer_remaining_s),
            "countdown_remaining_s": int(st.countdown_remaining_s),
            "last_hit": last_hit,
            "last_attack": last_attack,
            "fx_seq": int(st.fx_seq),
            "winner": winner,
            "vip_reward": vip_patch,
            "auto_arm_candidates": int(auto_candidates),
        }

    def _build_fighters(
        self,
        raw: list[dict[str, str]],
        *,
        max_hp: int,
        max_fighters: int,
    ) -> list[BattleFighter]:
        out: list[BattleFighter] = []
        seen: set[str] = set()
        for row in raw[: max(2, max_fighters)]:
            key = str(row.get("user_key") or row.get("key") or "").strip()
            if not key:
                key = str(row.get("user") or row.get("display_name") or "").strip().casefold()
            if not key or key in seen:
                continue
            seen.add(key)
            name = str(row.get("user") or row.get("display_name") or "?").strip() or "?"
            av = str(row.get("avatar_url") or "").strip()
            out.append(
                BattleFighter(
                    user_key=key,
                    display_name=name,
                    avatar_url=av,
                    hp=max_hp,
                    max_hp=max_hp,
                    side=_fighter_side(len(out), min(len(raw), max_fighters)),
                )
            )
        return out

    def _begin_countdown(
        self, fighters: list[BattleFighter], *, cfg: BattleRoyaleOverlayConfig
    ) -> None:
        self._session_cfg = cfg
        assign_support_gifts(fighters, per_fighter=cfg.gifts_per_fighter)
        t = time.monotonic()
        self._state = BattleState(
            phase=BattlePhase.COUNTDOWN,
            session_id=uuid.uuid4().hex[:12],
            fighters=fighters,
            countdown_remaining_s=cfg.countdown_s,
            fx_seq=1,
        )
        self._state.countdown_deadline = t + float(cfg.countdown_s)

    def _activate_round(self, cfg: BattleRoyaleOverlayConfig) -> None:
        t = time.monotonic()
        st = self._state
        st.phase = BattlePhase.ACTIVE
        st.timer_remaining_s = cfg.round_duration_s
        st.round_deadline = t + float(cfg.round_duration_s)
        st.countdown_deadline = None
        st.fx_seq += 1

    def _resolve_by_hp(self, cfg: BattleRoyaleOverlayConfig) -> None:
        alive = [f for f in self._state.fighters if f.hp > 0]
        if not alive:
            self._end_battle(None, cfg)
            return
        if len(alive) == 1:
            self._end_battle(alive[0], cfg)
            return
        best = max(self._state.fighters, key=lambda f: f.hp)
        self._end_battle(best, cfg)

    def _end_battle(self, winner: BattleFighter | None, cfg: BattleRoyaleOverlayConfig) -> None:
        st = self._state
        st.phase = BattlePhase.VICTORY
        st.round_deadline = None
        st.fx_seq += 1
        t = time.monotonic()
        st.victory_deadline = t + 8.0
        if winner is not None:
            st.winner_key = winner.user_key
            st.winner_display = winner.display_name
            st.winner_avatar_url = winner.avatar_url
            hours = max(1, min(24, int(cfg.vip_chat_hours)))
            self._vip = VipReward(
                user_key=winner.user_key,
                display_name=winner.display_name,
                until=datetime.now(UTC) + timedelta(hours=hours),
            )
        for cb in self._on_battle_ended:
            cb(winner)

    def _last_attack_payload(
        self,
        st: BattleState,
        last_hit: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not last_hit or not st.fighters:
            return None
        to_i = int(last_hit.get("to", -1))
        from_i = int(last_hit.get("from", -1))
        dmg = int(last_hit.get("damage") or 0)
        if dmg <= 0:
            return None
        attacker = "?"
        target = "?"
        amount = dmg
        if from_i >= 0 and from_i < len(st.fighters):
            attacker = st.fighters[from_i].display_name
            amount = max(dmg, int(last_hit.get("heal") or 0))
        elif from_i == -1 and to_i >= 0 and to_i < len(st.fighters):
            attacker = "Chat"
        if to_i >= 0 and to_i < len(st.fighters):
            target = st.fighters[to_i].display_name
        return {
            "attacker": attacker,
            "target": target,
            "damage": dmg,
            "amount": amount,
            "crit": bool(last_hit.get("crit")),
        }

    def _add_session_donation(self, fighter_idx: int, diamonds: int) -> None:
        if fighter_idx < 0 or fighter_idx >= len(self._state.fighters):
            return
        self._state.fighters[fighter_idx].session_donated += max(0, int(diamonds))

    def _apply_spectator_damage(
        self,
        sender_key: str,
        diamonds: int,
        cfg: BattleRoyaleOverlayConfig,
    ) -> BattleHit:
        st = self._state
        target_idx = self._pick_damage_target()
        dmg = diamonds
        st.fighters[target_idx].hp = max(0, st.fighters[target_idx].hp - dmg)
        # Attribute spectator support to the strongest living opponent of the target.
        if len(st.fighters) == 2:
            supporter_idx = 1 - target_idx
            self._add_session_donation(supporter_idx, diamonds)
        hit = BattleHit(from_index=-1, to_index=target_idx, damage=dmg, heal=0, crit=False)
        st.last_hit = hit
        st.fx_seq += 1
        self._after_hit(target_idx, cfg)
        return hit

    def _apply_fighter_gift(
        self, fighter_idx: int, diamonds: int, cfg: BattleRoyaleOverlayConfig
    ) -> BattleHit:
        st = self._state
        f = st.fighters[fighter_idx]
        self._add_session_donation(fighter_idx, diamonds)
        heal = diamonds
        f.hp = min(f.max_hp, f.hp + heal)
        crit = diamonds >= cfg.crit_threshold_diamonds
        extra_dmg = 0
        target_idx = self._pick_opponent_index(fighter_idx)
        if crit and target_idx is not None:
            excess = diamonds - cfg.crit_threshold_diamonds
            bonus = int(excess * cfg.crit_multiplier)
            extra_dmg = cfg.crit_threshold_diamonds + bonus
            st.fighters[target_idx].hp = max(0, st.fighters[target_idx].hp - extra_dmg)
        hit = BattleHit(
            from_index=fighter_idx,
            to_index=target_idx if target_idx is not None else fighter_idx,
            damage=extra_dmg,
            heal=heal,
            crit=crit,
        )
        st.last_hit = hit
        st.fx_seq += 1
        if target_idx is not None and extra_dmg > 0:
            self._after_hit(target_idx, cfg)
        elif f.hp <= 0:
            self._resolve_by_hp(cfg)
        return hit

    def _pick_opponent_index(self, fighter_idx: int) -> int | None:
        st = self._state
        if len(st.fighters) < 2:
            return None
        if len(st.fighters) == 2:
            return 1 - fighter_idx
        others = [i for i in range(len(st.fighters)) if i != fighter_idx]
        if not others:
            return None
        return min(others, key=lambda i: st.fighters[i].hp)

    def _pick_damage_target(self) -> int:
        st = self._state
        if len(st.fighters) <= 1:
            return 0
        return min(range(len(st.fighters)), key=lambda i: st.fighters[i].hp)

    def _after_hit(self, target_idx: int, cfg: BattleRoyaleOverlayConfig) -> None:
        st = self._state
        if st.fighters[target_idx].hp <= 0:
            alive = [i for i, f in enumerate(st.fighters) if f.hp > 0]
            if len(alive) <= 1:
                winner = st.fighters[alive[0]] if alive else None
                self._end_battle(winner, cfg)
                return
        st.target_rr_index = (st.target_rr_index + 1) % max(1, len(st.fighters))

    def _record_auto_gift(
        self,
        user_key: str,
        display_name: str,
        avatar_url: str,
        diamonds: int,
        ts: float,
    ) -> None:
        self._auto_buffer.append(
            _AutoGiftEntry(
                user_key=user_key,
                display_name=display_name,
                avatar_url=avatar_url,
                diamonds=diamonds,
                ts=ts,
            )
        )
        window = float(self._effective_config().auto_window_s)
        cutoff = ts - window
        self._auto_buffer = [e for e in self._auto_buffer if e.ts >= cutoff]

    def count_auto_arm_candidates(self, *, cfg: BattleRoyaleOverlayConfig | None = None) -> int:
        """How many distinct viewers have a qualifying gift in the auto-arm window."""
        c = cfg or self._effective_config()
        now = time.monotonic()
        window = float(c.auto_window_s)
        cutoff = now - window
        qualified: set[str] = set()
        for e in self._auto_buffer:
            if e.ts < cutoff:
                continue
            if e.diamonds < c.auto_threshold_each:
                continue
            qualified.add(e.user_key)
        return len(qualified)

    def _try_auto_arm(
        self,
        cfg: BattleRoyaleOverlayConfig,
        now: float,
    ) -> list[BattleFighter] | None:
        window = float(cfg.auto_window_s)
        cutoff = now - window
        qualified: dict[str, _AutoGiftEntry] = {}
        for e in self._auto_buffer:
            if e.ts < cutoff:
                continue
            if e.diamonds < cfg.auto_threshold_each:
                continue
            prev = qualified.get(e.user_key)
            if prev is None or e.diamonds > prev.diamonds:
                qualified[e.user_key] = e
        if len(qualified) < 2:
            return None
        ranked = sorted(qualified.values(), key=lambda x: -x.diamonds)[: cfg.max_fighters]
        raw = [
            {
                "user_key": e.user_key,
                "user": e.display_name,
                "avatar_url": e.avatar_url,
            }
            for e in ranked
        ]
        built = self._build_fighters(raw, max_hp=cfg.max_hp, max_fighters=cfg.max_fighters)
        if len(built) < 2:
            return None
        self._auto_buffer.clear()
        return built
