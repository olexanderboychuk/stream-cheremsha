from __future__ import annotations

from stream_cheremsha.activity.aggregator import LikeShareAggregator
from stream_cheremsha.activity.models import ActivityItem, activity_append_patch


def test_activity_item_to_dict_shape() -> None:
    it = ActivityItem(
        platform="twitch",
        kind="follow",
        user="alice",
        detail="",
        count=1,
        icon_url="",
        time_hms="12:34:56",
    )
    d = it.to_dict()
    assert d["platform"] == "twitch"
    assert d["kind"] == "follow"
    assert d["user"] == "alice"
    p = activity_append_patch(it)
    assert set(p.keys()) == {"append"}
    assert p["append"]["time"] == "12:34:56"


def test_aggregator_coalesces_counts_in_window() -> None:
    ag = LikeShareAggregator(window_sec=5.0)
    ag.ingest(kind="like", user="bob", n=1, now_mono=100.0)
    ag.ingest(kind="like", user="bob", n=2, now_mono=101.0)
    out = ag.flush_ready(now_mono=104.0)
    assert out == []
    out2 = ag.flush_ready(now_mono=105.1)
    assert len(out2) == 1
    assert out2[0].kind == "like"
    assert out2[0].user == "bob"
    assert out2[0].count == 3


def test_aggregator_splits_after_window() -> None:
    ag = LikeShareAggregator(window_sec=5.0)
    ag.ingest(kind="share", user="", n=1, now_mono=10.0)
    out = ag.flush_ready(now_mono=20.1)
    assert len(out) == 1
    ag.ingest(kind="share", user="", n=4, now_mono=21.0)
    out2 = ag.flush_ready(now_mono=26.2)
    assert len(out2) == 1
    assert out2[0].count == 4

