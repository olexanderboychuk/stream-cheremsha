from stream_cheremsha.overlays.community_world_config import (
    community_world_overlay_config_defaults,
)
from stream_cheremsha.overlays.community_world_session import (
    CommunityWorldSession,
    cumulative_xp,
    level_from_xp,
)


def _session() -> CommunityWorldSession:
    return CommunityWorldSession.fresh(community_world_overlay_config_defaults())


def test_level_curve() -> None:
    assert level_from_xp(0) == 1
    assert level_from_xp(119) == 1
    assert level_from_xp(120) == 2
    assert level_from_xp(120 + 200 - 1) == 2
    assert level_from_xp(120 + 200) == 3
    assert cumulative_xp(3) == 320


def test_events_accumulate() -> None:
    s = _session()
    s.on_chat(user="a", text="hi")
    s.on_follow(user="b", user_key="k-b")
    s.on_like(user="c", n=25, user_key="k-c")
    s.on_share(user="d", n=3, user_key="k-d")
    s.on_gift(user="e", user_key="k-e", gift_name="Rose", coins=120)
    s.on_join(user="f", user_key="k-f")
    s.on_battle_win(user="b", user_key="k-b")
    assert s.chat_messages == 1
    assert s.follows == 1
    assert s.likes == 25
    assert s.shares == 3
    assert s.gift_coins == 120
    assert s.joins == 1
    assert s.unique_viewers == 6


def test_xp_and_level_grow() -> None:
    s = _session()
    for _ in range(4):
        s.on_follow(user="u", user_key="k")
    # 4 follows * 40 XP = 160 XP => level 2 (needs 120).
    assert s.xp == 160
    assert s.level == 2
    state = s.to_overlay_dict()
    assert state["level"] == 2
    assert state["progress"] > 0.0


def test_quests_complete_and_badge() -> None:
    s = _session()
    cfg = community_world_overlay_config_defaults().replace(
        quest_follows_target=3,
        quest2_type="follows",
        quest3_type="none",
    )
    s = CommunityWorldSession.fresh(cfg)
    s.on_follow(user="a", user_key="k-a")
    s.on_follow(user="b", user_key="k-b")
    s.on_follow(user="c", user_key="k-c")
    quests = s.quests()
    follows_q = next(q for q in quests if q["type"] == "follows")
    assert follows_q["completed"] is True
    assert s.quest_complete_seq >= 1
    badges = s.passports()
    finishers = [p for p in badges if "quest_finisher" in p["badges"]]
    assert finishers


def test_buildings_unlock() -> None:
    s = _session()
    ids = {b["id"] for b in s.buildings() if b["unlocked"]}
    assert ids == {"house"}
    # Likes unlock the well at 500.
    for _ in range(50):
        s.on_like(user="u", n=10, user_key="k")
    ids2 = {b["id"] for b in s.buildings() if b["unlocked"]}
    assert "well" in ids2
    # Shares unlock bridge at 25.
    for _ in range(5):
        s.on_share(user="u", n=5, user_key="k")
    ids3 = {b["id"] for b in s.buildings() if b["unlocked"]}
    assert "bridge" in ids3


def test_pending_buildings_consumed() -> None:
    s = _session()
    s.on_like(user="u", n=500, user_key="k")
    state = s.to_overlay_dict()
    well = next(b for b in state["buildings"] if b["id"] == "well")
    assert well["new"] is True
    s.consume_pending_buildings()
    state2 = s.to_overlay_dict()
    well2 = next(b for b in state2["buildings"] if b["id"] == "well")
    assert well2["new"] is False


def test_founder_and_badges() -> None:
    s = _session()
    s.on_follow(user="first", user_key="k-1")
    s.on_follow(user="second", user_key="k-2")
    assert s.founder == "first"
    passports = s.passports()
    first = next(p for p in passports if p["user"] == "first")
    assert "founder" in first["badges"]
    s.on_gift(user="gifter", user_key="k-g", gift_name="Rose", coins=200)
    gifter = next(p for p in s.passports() if p["user"] == "gifter")
    assert "gifter" in gifter["badges"]
    assert "supporter" in gifter["badges"]


def test_recognition_feed_capped() -> None:
    s = _session()
    for i in range(30):
        s.on_join(user=f"u{i}", user_key=f"k{i}")
    assert len(s.recent) <= 12
    assert s.recent[-1]["kind"] == "join"


def test_reset() -> None:
    s = _session()
    s.on_follow(user="a", user_key="k")
    s.reset()
    assert s.follows == 0
    assert s.xp == 0
    assert s.level == 1
    assert s.founder == ""