from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from stream_cheremsha.overlays.community_world_config import (
    CommunityWorldOverlayConfig,
)

# Badge ids used by the overlay and persisted all-time in SQLite.
BADGE_FOUNDER = "founder"
BADGE_GIFTER = "gifter"
BADGE_SUPPORTER = "supporter"
BADGE_TOP_LIKER = "top_liker"
BADGE_SHARER = "sharer"
BADGE_REGULAR = "regular"
BADGE_QUEST_FINISHER = "quest_finisher"
BADGE_BATTLE_CHAMPION = "battle_champion"

_ALL_BADGES: tuple[str, ...] = (
    BADGE_FOUNDER,
    BADGE_GIFTER,
    BADGE_SUPPORTER,
    BADGE_TOP_LIKER,
    BADGE_SHARER,
    BADGE_REGULAR,
    BADGE_QUEST_FINISHER,
    BADGE_BATTLE_CHAMPION,
)

# Static building unlock rules (id, display-name key, predicate). Buildings are
# unlocked as the community grows during the live session.
_BUILDING_RULES: tuple[tuple[str, str, Any], ...] = (
    ("house", "house", lambda s: s.level >= 1),
    ("tree", "tree", lambda s: s.level >= 2),
    ("house2", "house2", lambda s: s.follows >= 5),
    ("well", "well", lambda s: s.likes >= 500),
    ("bridge", "bridge", lambda s: s.shares >= 25),
    ("church", "church", lambda s: s.level >= 4),
    ("market", "market", lambda s: s.shares >= 60),
    ("monument", "monument", lambda s: s.gift_coins >= 500),
    ("tower", "tower", lambda s: s.gift_coins >= 1500),
    ("castle", "castle", lambda s: s.level >= 6),
)

# Quest slot -> counter accessor.
_QUEST_ACCESSOR = {
    "likes": lambda s: s.likes,
    "shares": lambda s: s.shares,
    "gifts": lambda s: s.gift_coins,
    "follows": lambda s: s.follows,
}


def xp_for_level_advance(level: int) -> int:
    """XP required to advance *from* ``level`` to ``level + 1``."""
    return 120 + (level - 1) * 80


def level_from_xp(xp: int) -> int:
    level = 1
    remaining = max(0, int(xp))
    while remaining >= xp_for_level_advance(level) and level < 99:
        remaining -= xp_for_level_advance(level)
        level += 1
    return level


def cumulative_xp(level: int) -> int:
    total = 0
    for lv in range(1, level):
        total += xp_for_level_advance(lv)
    return total


@dataclass(slots=True)
class CommunityViewer:
    key: str
    display_name: str
    avatar_url: str = ""
    points: int = 0
    likes: int = 0
    shares: int = 0
    gift_coins: int = 0
    chat: int = 0
    badges: set[str] = field(default_factory=set)


@dataclass(slots=True)
class CommunityQuest:
    type: str
    current: int
    target: int
    completed: bool = False


@dataclass(slots=True)
class CommunityWorldSession:
    cfg: CommunityWorldOverlayConfig

    xp: int = 0
    follows: int = 0
    likes: int = 0
    shares: int = 0
    gift_coins: int = 0
    joins: int = 0
    chat_messages: int = 0

    _viewers: dict[str, CommunityViewer] = field(default_factory=dict)
    _unique_users: set[str] = field(default_factory=set)
    _founder_key: str = ""
    _gifter_key: str = ""
    _feed: list[dict[str, Any]] = field(default_factory=list)
    _feed_seq: int = 0
    _anim_seq: int = 0
    _quest_complete_seq: int = 0
    _completed_quests: set[str] = field(default_factory=set)
    _pending_buildings: list[str] = field(default_factory=list)
    _announced_buildings: set[str] = field(default_factory=set)
    _last_activity_key: str = ""

    @classmethod
    def fresh(cls, cfg: CommunityWorldOverlayConfig) -> CommunityWorldSession:
        return cls(cfg=cfg)

    def reset(self) -> None:
        self.xp = 0
        self.follows = 0
        self.likes = 0
        self.shares = 0
        self.gift_coins = 0
        self.joins = 0
        self.chat_messages = 0
        self._viewers.clear()
        self._unique_users.clear()
        self._founder_key = ""
        self._gifter_key = ""
        self._feed.clear()
        self._feed_seq = 0
        self._anim_seq = 0
        self._quest_complete_seq = 0
        self._completed_quests.clear()
        self._pending_buildings.clear()
        self._announced_buildings.clear()
        self._last_activity_key = ""

    # -- helpers --------------------------------------------------------------

    @property
    def level(self) -> int:
        return level_from_xp(self.xp)

    @property
    def unique_viewers(self) -> int:
        return len(self._unique_users)

    @property
    def recent(self) -> list[dict[str, Any]]:
        return list(self._feed)

    @property
    def quest_complete_seq(self) -> int:
        return int(self._quest_complete_seq)

    def _viewer_key(self, user: str, user_key: str = "") -> str:
        k = (user_key or "").strip()
        if k:
            return k
        name = (user or "").strip().casefold()
        return name or "?"

    def _get_viewer(self, key: str, display_name: str, avatar_url: str) -> CommunityViewer:
        v = self._viewers.get(key)
        if v is None:
            v = CommunityViewer(
                key=key,
                display_name=(display_name or "").strip() or "?",
                avatar_url=(avatar_url or "").strip(),
            )
            self._viewers[key] = v
        else:
            if (display_name or "").strip():
                v.display_name = (display_name or "").strip()
            if (avatar_url or "").strip():
                v.avatar_url = (avatar_url or "").strip()
        return v

    def _grant_badge(self, viewer: CommunityViewer, badge: str) -> bool:
        if badge in viewer.badges:
            return False
        viewer.badges.add(badge)
        self._anim_seq += 1
        return True

    def _push_feed(self, *, kind: str, user: str, detail: str = "", icon: str = "") -> None:
        self._feed_seq += 1
        item = {
            "kind": kind,
            "user": (user or "").strip() or "?",
            "detail": (detail or "").strip(),
            "icon": (icon or "").strip(),
            "seq": self._feed_seq,
        }
        self._feed.append(item)
        limit = max(1, min(50, int(self.cfg.feed_max_items)))
        if len(self._feed) > limit:
            self._feed = self._feed[-limit:]

    def _add_xp(self, amount: int) -> None:
        self.xp += max(0, int(amount))

    def _track_unique(self, key: str) -> None:
        self._unique_users.add(key)

    def _check_quests(self) -> None:
        completed_any = False
        for quest in self._quests():
            if quest.type in self._completed_quests or quest.current < quest.target:
                continue
            self._completed_quests.add(quest.type)
            completed_any = True
        if completed_any:
            self._quest_complete_seq += 1
            self._anim_seq += 1
            finisher_key = self._last_activity_key
            if finisher_key:
                viewer = self._viewers.get(finisher_key)
                if viewer is not None:
                    self._grant_badge(viewer, BADGE_QUEST_FINISHER)

    def _quests(self) -> list[CommunityQuest]:
        slots = (
            self.cfg.quest1_type,
            self.cfg.quest2_type,
            self.cfg.quest3_type,
            self.cfg.quest4_type,
        )
        out: list[CommunityQuest] = []
        for stype in slots:
            stype = (stype or "none").strip().lower()
            if stype == "none":
                continue
            accessor = _QUEST_ACCESSOR.get(stype)
            if accessor is None:
                continue
            target = {
                "likes": self.cfg.quest_likes_target,
                "shares": self.cfg.quest_shares_target,
                "gifts": self.cfg.quest_gifts_target,
                "follows": self.cfg.quest_follows_target,
            }[stype]
            out.append(
                CommunityQuest(
                    type=stype,
                    current=accessor(self),
                    target=target,
                    completed=stype in self._completed_quests,
                )
            )
        return out

    # -- events ---------------------------------------------------------------

    def on_chat(self, *, user: str, text: str) -> None:
        self.chat_messages += 1
        key = self._viewer_key(user)
        viewer = self._get_viewer(key, user, "")
        viewer.chat += 1
        viewer.points += int(self.cfg.xp_chat)
        if viewer.chat >= 10:
            self._grant_badge(viewer, BADGE_REGULAR)
        self._add_xp(self.cfg.xp_chat)
        self._track_unique(key)
        self._last_activity_key = key
        if self.chat_messages == 1 or self.chat_messages % 25 == 0:
            self._push_feed(kind="chat", user=user, detail=str(self.chat_messages))

    def on_follow(self, *, user: str, user_key: str = "", avatar_url: str = "") -> None:
        self.follows += 1
        key = self._viewer_key(user, user_key)
        viewer = self._get_viewer(key, user, avatar_url)
        viewer.points += int(self.cfg.xp_follow)
        if not self._founder_key:
            self._founder_key = key
            self._grant_badge(viewer, BADGE_FOUNDER)
        self._add_xp(self.cfg.xp_follow)
        self._track_unique(key)
        self._last_activity_key = key
        self._push_feed(kind="follow", user=user)
        self._check_quests()

    def on_join(self, *, user: str, user_key: str = "") -> None:
        self.joins += 1
        key = self._viewer_key(user, user_key)
        viewer = self._get_viewer(key, user, "")
        viewer.points += int(self.cfg.xp_join)
        self._add_xp(self.cfg.xp_join)
        self._track_unique(key)
        self._last_activity_key = key
        self._push_feed(kind="join", user=user)
        self._check_quests()

    def on_like(
        self,
        *,
        user: str,
        n: int,
        user_key: str = "",
        avatar_url: str = "",
    ) -> None:
        n = max(1, int(n))
        self.likes += n
        key = self._viewer_key(user, user_key)
        viewer = self._get_viewer(key, user, avatar_url)
        viewer.likes += n
        per10 = max(1, n // 10)
        viewer.points += per10 * int(self.cfg.xp_like_per_10)
        if viewer.likes >= 100:
            self._grant_badge(viewer, BADGE_TOP_LIKER)
        self._add_xp(per10 * int(self.cfg.xp_like_per_10))
        self._track_unique(key)
        self._last_activity_key = key
        self._push_feed(kind="like", user=user, detail=str(n))
        self._check_quests()

    def on_share(self, *, user: str, n: int, user_key: str = "") -> None:
        n = max(1, int(n))
        self.shares += n
        key = self._viewer_key(user, user_key)
        viewer = self._get_viewer(key, user, "")
        viewer.shares += n
        viewer.points += n * int(self.cfg.xp_share)
        if viewer.shares >= 5:
            self._grant_badge(viewer, BADGE_SHARER)
        self._add_xp(n * int(self.cfg.xp_share))
        self._track_unique(key)
        self._last_activity_key = key
        self._push_feed(kind="share", user=user, detail=str(n))
        self._check_quests()

    def on_gift(
        self,
        *,
        user: str,
        user_key: str = "",
        gift_name: str = "",
        coins: int = 0,
        icon_url: str = "",
        avatar_url: str = "",
    ) -> None:
        coins = max(1, int(coins))
        self.gift_coins += coins
        key = self._viewer_key(user, user_key)
        viewer = self._get_viewer(key, user, avatar_url)
        viewer.gift_coins += coins
        per10 = max(1, coins // 10)
        viewer.points += per10 * int(self.cfg.xp_gift_coin_per_10)
        if not self._gifter_key:
            self._gifter_key = key
            self._grant_badge(viewer, BADGE_GIFTER)
        if viewer.gift_coins >= 100:
            self._grant_badge(viewer, BADGE_SUPPORTER)
        self._add_xp(per10 * int(self.cfg.xp_gift_coin_per_10))
        self._track_unique(key)
        self._last_activity_key = key
        self._push_feed(
            kind="gift",
            user=user,
            detail=(gift_name or "").strip(),
            icon=(icon_url or "").strip(),
        )
        self._check_quests()

    def on_battle_win(self, *, user: str, user_key: str = "", avatar_url: str = "") -> None:
        key = self._viewer_key(user, user_key)
        viewer = self._get_viewer(key, user, avatar_url)
        viewer.points += int(self.cfg.xp_battle_win)
        self._grant_badge(viewer, BADGE_BATTLE_CHAMPION)
        self._add_xp(self.cfg.xp_battle_win)
        self._track_unique(key)
        self._last_activity_key = key
        self._push_feed(kind="battle", user=user)

    # -- output ---------------------------------------------------------------

    def buildings(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for bid, _name_key, pred in _BUILDING_RULES:
            unlocked = bool(pred(self))
            out.append(
                {
                    "id": bid,
                    "unlocked": unlocked,
                    "new": unlocked and bid in self._pending_buildings,
                }
            )
        return out

    def consume_pending_buildings(self) -> None:
        self._announced_buildings.update(self._pending_buildings)
        self._pending_buildings.clear()

    def _collect_new_buildings(self) -> None:
        for bid, _name_key, pred in _BUILDING_RULES:
            if (
                bool(pred(self))
                and bid not in self._announced_buildings
                and bid not in self._pending_buildings
            ):
                self._pending_buildings.append(bid)

    def quests(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for q in self._quests():
            out.append(
                {
                    "type": q.type,
                    "current": int(q.current),
                    "target": int(q.target),
                    "completed": bool(q.completed),
                }
            )
        return out

    def passports(self, *, limit: int = 6) -> list[dict[str, Any]]:
        lim = max(1, min(20, int(limit)))
        ranked = sorted(
            self._viewers.values(),
            key=lambda v: (-v.points, v.display_name.casefold()),
        )[:lim]
        out: list[dict[str, Any]] = []
        for v in ranked:
            out.append(
                {
                    "key": v.key,
                    "user": v.display_name,
                    "avatar_url": v.avatar_url,
                    "points": int(v.points),
                    "badges": sorted(v.badges),
                }
            )
        return out

    @property
    def founder(self) -> str:
        v = self._viewers.get(self._founder_key)
        if v is None:
            return ""
        return v.display_name

    def to_overlay_dict(self) -> dict[str, Any]:
        self._collect_new_buildings()
        level = self.level
        xp = max(0, int(self.xp))
        need = xp_for_level_advance(level)
        cum = cumulative_xp(level)
        xp_in_level = max(0, xp - cum)
        progress = min(1.0, (xp_in_level / float(need)) if need > 0 else 0.0)
        return {
            "level": level,
            "xp": xp,
            "xp_to_next": max(0, need - xp_in_level),
            "progress": round(progress, 4),
            "follows": int(self.follows),
            "likes": int(self.likes),
            "shares": int(self.shares),
            "gift_coins": int(self.gift_coins),
            "joins": int(self.joins),
            "chat_messages": int(self.chat_messages),
            "unique_viewers": self.unique_viewers,
            "buildings": self.buildings(),
            "quests": self.quests(),
            "recent": list(self._feed),
            "passports": self.passports(),
            "founder": self.founder,
            "anim_seq": int(self._anim_seq),
            "quest_complete_seq": int(self._quest_complete_seq),
        }
