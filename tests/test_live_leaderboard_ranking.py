from __future__ import annotations

from stream_cheremsha.overlays.live_leaderboard_ranking import (
    SOURCE_COMMENTERS,
    SOURCE_CONTRIBUTORS,
    SOURCE_GIFTERS,
    SOURCE_LIKERS,
    SOURCE_SHARERS,
    ContributorWeights,
    LiveLeaderboardRankingEngine,
)


def test_likes_ranking_and_top_n() -> None:
    eng = LiveLeaderboardRankingEngine()
    eng.add_likes(user_key="a", display_name="ALPHA", n=100, immediate=True)
    eng.add_likes(user_key="b", display_name="BETA", n=50, immediate=True)
    eng.add_likes(user_key="c", display_name="GAMMA", n=75, immediate=True)
    leaders = eng.leaders(source=SOURCE_LIKERS, limit=2)
    assert len(leaders) == 2
    assert leaders[0]["user"] == "ALPHA"
    assert leaders[0]["value"] == 100
    assert leaders[0]["rank"] == 1
    assert leaders[1]["user"] == "GAMMA"


def test_gifts_shares_comments() -> None:
    eng = LiveLeaderboardRankingEngine()
    eng.add_gift_coins(user_key="g1", display_name="GIVER", coins=420)
    eng.add_shares(user_key="s1", display_name="SHARER", n=12)
    eng.add_comment(user_key="c1", display_name="TALKER")
    eng.add_comment(user_key="c1", display_name="TALKER")
    assert eng.leaders(source=SOURCE_GIFTERS, limit=5)[0]["value"] == 420
    assert eng.leaders(source=SOURCE_SHARERS, limit=5)[0]["value"] == 12
    assert eng.leaders(source=SOURCE_COMMENTERS, limit=5)[0]["value"] == 2


def test_contributor_weighted_score() -> None:
    eng = LiveLeaderboardRankingEngine(
        weights=ContributorWeights(like=1, gift_coin=10, share=50, comment=5)
    )
    eng.add_likes(user_key="u", display_name="VOID", n=10, immediate=True)
    eng.add_gift_coins(user_key="u", display_name="VOID", coins=3)
    eng.add_shares(user_key="u", display_name="VOID", n=1)
    eng.add_comment(user_key="u", display_name="VOID")
    # 10*1 + 3*10 + 1*50 + 1*5 = 95
    leaders = eng.leaders(source=SOURCE_CONTRIBUTORS, limit=5)
    assert leaders[0]["value"] == 95


def test_ties_stable_by_name() -> None:
    eng = LiveLeaderboardRankingEngine()
    eng.add_likes(user_key="2", display_name="ZED", n=50, immediate=True)
    eng.add_likes(user_key="1", display_name="ANN", n=50, immediate=True)
    leaders = eng.leaders(source=SOURCE_LIKERS, limit=5)
    assert [x["user"] for x in leaders] == ["ANN", "ZED"]


def test_like_batching_flush() -> None:
    eng = LiveLeaderboardRankingEngine()
    eng.add_likes(user_key="a", display_name="A", n=1)
    eng.add_likes(user_key="a", display_name="A", n=2)
    eng.add_likes(user_key="a", display_name="A", n=4)
    assert eng.leaders(source=SOURCE_LIKERS, limit=5) == []
    flushed = eng.flush_likes()
    assert flushed == 7
    assert eng.leaders(source=SOURCE_LIKERS, limit=5)[0]["value"] == 7


def test_high_frequency_likes_aggregate() -> None:
    eng = LiveLeaderboardRankingEngine()
    for _ in range(500):
        eng.add_likes(user_key="x", display_name="X", n=1)
    eng.flush_likes()
    assert eng.leaders(source=SOURCE_LIKERS, limit=1)[0]["value"] == 500


def test_zero_scores_excluded() -> None:
    eng = LiveLeaderboardRankingEngine()
    eng.add_likes(user_key="a", display_name="A", n=5, immediate=True)
    # shares empty → empty list for sharers
    assert eng.leaders(source=SOURCE_SHARERS, limit=5) == []


def test_all_rankings_keys() -> None:
    eng = LiveLeaderboardRankingEngine()
    eng.add_likes(user_key="a", display_name="A", n=1, immediate=True)
    rankings = eng.all_rankings(limit=5)
    assert set(rankings.keys()) == {
        SOURCE_LIKERS,
        SOURCE_GIFTERS,
        SOURCE_SHARERS,
        SOURCE_COMMENTERS,
        SOURCE_CONTRIBUTORS,
    }


def test_reset_clears() -> None:
    eng = LiveLeaderboardRankingEngine()
    eng.add_likes(user_key="a", display_name="A", n=9, immediate=True)
    eng.reset()
    assert eng.leaders(source=SOURCE_LIKERS, limit=5) == []
