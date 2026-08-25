from stream_cheremsha.persistence.community_world_sqlite import (
    award_community_badge,
    fetch_community_badges_for_user,
    fetch_village_elders,
)


def test_badge_award_idempotent(tmp_path) -> None:  # noqa: ANN001
    db = tmp_path / "cw.sqlite"
    award_community_badge(
        user_key="k-1",
        display_name="Alpha",
        badge="founder",
        db_path=db,
    )
    award_community_badge(
        user_key="k-1",
        display_name="Alpha",
        badge="founder",
        db_path=db,
    )
    award_community_badge(
        user_key="k-1",
        display_name="Alpha",
        badge="gifter",
        db_path=db,
    )
    badges = fetch_community_badges_for_user("k-1", db_path=db)
    assert len(badges) == 2
    assert {b["badge"] for b in badges} == {"founder", "gifter"}


def test_elders_ranked_by_badge_count(tmp_path) -> None:  # noqa: ANN001
    db = tmp_path / "cw.sqlite"
    award_community_badge(user_key="k-a", display_name="A", badge="founder", db_path=db)
    award_community_badge(user_key="k-a", display_name="A", badge="gifter", db_path=db)
    award_community_badge(user_key="k-b", display_name="B", badge="founder", db_path=db)
    elders = fetch_village_elders(limit=8, db_path=db)
    assert elders[0]["user"] == "A"
    assert elders[0]["badge_count"] == 2
    assert elders[1]["user"] == "B"


def test_empty_db(tmp_path) -> None:  # noqa: ANN001
    db = tmp_path / "missing.sqlite"
    assert fetch_village_elders(limit=8, db_path=db) == []
    assert fetch_community_badges_for_user("k", db_path=db) == []