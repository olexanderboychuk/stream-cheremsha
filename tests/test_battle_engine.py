"""Tests for ``stream_cheremsha.battle.engine`` (the pure Python 1v1 BattleEngine).

The engine is deterministic and time-injected: every time-dependent call
(``start_manual`` / ``on_gift`` / ``on_like`` / ``on_follow`` / ``tick``)
accepts an explicit ``now`` float, so no real sleeping is ever involved.
"""

from __future__ import annotations

from stream_cheremsha.battle.engine import BattleEngine
from stream_cheremsha.overlays.battle_overlay_config import (
    BattleOverlayConfig,
    battle_overlay_config_defaults,
)


def _cfg(**kwargs: object) -> BattleOverlayConfig:
    return battle_overlay_config_defaults().replace(**kwargs)


def _eng(**kwargs: object) -> BattleEngine:
    return BattleEngine(lambda: _cfg(**kwargs))


def _start_active(eng: BattleEngine, now: float) -> float:
    """Start a 2-player battle (A left / B right) and drive it into ACTIVE.

    Returns the monotonic ``t`` at which the round became ACTIVE, so callers
    can gift within the round window ``[t, round_deadline)``.
    """
    assert eng.start_manual(
        [{"user_key": "a", "user": "A"}, {"user_key": "b", "user": "B"}], now=now
    )
    # Drive well past the countdown (countdown_s is clamped to <= 10). tick()
    # returns the emitted events (here [round_started]), so we only check the
    # resulting status.
    t_active = now + 1000.0
    eng.tick(now=t_active)  # -> ACTIVE (round_started)
    assert eng.snapshot()["status"] == "active"
    return t_active


def _resolve(eng: BattleEngine) -> list[dict]:
    """Advance past the round deadline so the current round resolves."""
    return eng.tick(now=eng._state.round_deadline + 0.1)


def _score(eng: BattleEngine, team: str) -> int:
    return next(t["score"] for t in eng.snapshot()["teams"] if t["id"] == team)


def test_idle_snapshot_shape() -> None:
    eng = _eng()
    s = eng.snapshot()
    assert s["status"] == "idle"
    assert s["battle_id"] == ""
    assert s["round"] == 1
    assert s["best_of"] == 3
    assert s["round_wins"] == {"left": 0, "right": 0}
    assert s["duration_s"] == 60
    assert s["remaining_seconds"] == 0
    assert s["countdown_remaining_s"] == 0
    assert s["participants"] == []
    assert s["combo"] == {"team_id": None, "count": 0, "multiplier": 1.0}
    assert s["flags"] == {
        "is_close": False,
        "is_comeback": False,
        "final_push": False,
    }
    assert s["winner"] is None


def test_auto_arm_arms_battle_higher_gift_left() -> None:
    eng = _eng(auto_start=True, auto_threshold_each=100, auto_window_s=30, combo_enabled=False)
    t0 = 1000.0
    # A's gift qualifies (200 >= 100) but only one user qualifies yet -> no arm.
    assert eng.on_gift(user_key="a", display="A", avatar_url="", diamonds=200, now=t0) == []
    # B's gift qualifies (150 >= 100); two distinct qualified users -> arm the battle.
    ev = eng.on_gift(user_key="b", display="B", avatar_url="", diamonds=150, now=t0 + 1)
    assert [e["type"] for e in ev] == ["battle_started", "round_started"]
    s = eng.snapshot()
    assert s["status"] == "countdown"
    # Higher gift (A=200) is locked into the LEFT slot.
    assert [(p["name"], p["team_id"]) for p in s["participants"]] == [
        ("A", "left"),
        ("B", "right"),
    ]
    assert s["participants"][0]["score"] == 0
    assert s["participants"][1]["score"] == 0


def test_auto_arm_stays_idle_below_threshold_or_one_qualifier() -> None:
    # Below-threshold gifts never arm the battle.
    eng = _eng(auto_start=True, auto_threshold_each=100, auto_window_s=30, combo_enabled=False)
    t0 = 1000.0
    eng.on_gift(user_key="a", display="A", avatar_url="", diamonds=120, now=t0)
    ev = eng.on_gift(user_key="b", display="B", avatar_url="", diamonds=90, now=t0 + 1)  # 90 < 100
    assert ev == []
    assert eng.snapshot()["status"] == "idle"

    # Only one qualified user is not enough even if the other gift is huge.
    eng = _eng(auto_start=True, auto_threshold_each=100, auto_window_s=30, combo_enabled=False)
    t0 = 1000.0
    eng.on_gift(user_key="a", display="A", avatar_url="", diamonds=500, now=t0)
    ev = eng.on_gift(user_key="b", display="B", avatar_url="", diamonds=1, now=t0 + 1)
    assert ev == []
    assert eng.snapshot()["status"] == "idle"


def test_auto_arm_respects_window_and_auto_start_off() -> None:
    # Gifts outside the auto window must be dropped from qualification.
    eng = _eng(auto_start=True, auto_threshold_each=100, auto_window_s=5, combo_enabled=False)
    t0 = 1000.0
    eng.on_gift(user_key="a", display="A", avatar_url="", diamonds=200, now=t0)
    # B gifts 20s later -> A is now outside the 5s window, only B qualifies.
    ev = eng.on_gift(user_key="b", display="B", avatar_url="", diamonds=200, now=t0 + 20)
    assert ev == []
    assert eng.snapshot()["status"] == "idle"

    # auto_start=False disables arming entirely.
    eng = _eng(auto_start=False, auto_threshold_each=100, combo_enabled=False)
    t0 = 1000.0
    eng.on_gift(user_key="a", display="A", avatar_url="", diamonds=200, now=t0)
    ev = eng.on_gift(user_key="b", display="B", avatar_url="", diamonds=150, now=t0 + 1)
    assert ev == []
    assert eng.snapshot()["status"] == "idle"


def test_manual_start_requires_two_distinct() -> None:
    eng = _eng()
    t0 = 1000.0
    assert eng.start_manual([], now=t0) is False  # zero users
    assert eng.start_manual([{"user_key": "a", "user": "A"}], now=t0) is False  # one user
    assert (
        eng.start_manual([{"user_key": "a", "user": "A"}, {"user_key": "a", "user": "A"}], now=t0)
        is False  # same user twice
    )
    assert eng.snapshot()["status"] == "idle"
    assert (
        eng.start_manual([{"user_key": "a", "user": "A"}, {"user_key": "b", "user": "B"}], now=t0)
        is True
    )
    assert eng.snapshot()["status"] == "countdown"
    # Starting again while not IDLE/FINISHED is rejected.
    assert (
        eng.start_manual([{"user_key": "a", "user": "A"}, {"user_key": "b", "user": "B"}], now=t0)
        is False
    )


def test_countdown_transitions_to_active() -> None:
    eng = _eng(countdown_s=5, round_duration_s=60)
    t0 = 1000.0
    _start_active(eng, t0)
    s = eng.snapshot()
    assert s["status"] == "active"
    assert s["round"] == 1
    assert s["remaining_seconds"] == 60  # round_duration_s
    assert s["participants"] and s["teams"]


def test_points_from_multiplier() -> None:
    eng = _eng(gift_multiplier=2.0, combo_enabled=False, countdown_s=5, round_duration_s=600)
    t0 = 1000.0
    t_active = _start_active(eng, t0)
    eng.on_gift(user_key="a", display="A", avatar_url="", diamonds=200, now=t_active + 1)
    s = eng.snapshot()
    # 200 diamonds * 2.0 multiplier * 1.0 combo = 400 points.
    assert _score(eng, "left") == 400
    assert _score(eng, "right") == 0
    gr = next(e for e in s["events"] if e["type"] == "gift_received")
    assert gr["payload"]["points"] == 400
    assert gr["payload"]["diamonds"] == 200
    assert gr["payload"]["user"] == "A"
    assert gr["payload"]["multiplier"] == 1.0
    # A gift of >= 500 diamonds emits a big_gift event; 200 does not.
    assert not any(e["type"] == "big_gift" for e in s["events"])
    eng.on_gift(user_key="a", display="A", avatar_url="", diamonds=500, now=t_active + 2)
    assert any(
        e["type"] == "big_gift" and e["payload"]["diamonds"] == 500
        for e in eng.snapshot()["events"]
    )


def test_combo_ladder_x2_then_x3() -> None:
    eng = _eng(
        combo_enabled=True,
        combo_threshold=3,
        combo_window_s=60,
        combo_max_multiplier=3.0,
        countdown_s=5,
        round_duration_s=600,
    )
    t0 = 1000.0
    t_active = _start_active(eng, t0)
    # First two gifts: below threshold -> no combo yet.
    eng.on_gift(user_key="a", display="A", avatar_url="", diamonds=10, now=t_active + 1)
    eng.on_gift(user_key="a", display="A", avatar_url="", diamonds=10, now=t_active + 2)
    s = eng.snapshot()
    assert s["combo"]["multiplier"] == 1.0
    assert s["combo"]["team_id"] is None
    # Third gift reaches the threshold -> combo x2.
    eng.on_gift(user_key="a", display="A", avatar_url="", diamonds=10, now=t_active + 3)
    s = eng.snapshot()
    assert s["combo"]["team_id"] == "left"
    assert s["combo"]["count"] == 3
    assert s["combo"]["multiplier"] == 2.0
    assert any(e["type"] == "combo_started" for e in s["events"])
    # Points now use the x2 multiplier.
    assert _score(eng, "left") == 10 + 10 + 10 * 2  # 10 + 10 + 20 = 40
    # Sixth gift reaches 2x the threshold -> combo x3.
    eng.on_gift(user_key="a", display="A", avatar_url="", diamonds=10, now=t_active + 4)
    eng.on_gift(user_key="a", display="A", avatar_url="", diamonds=10, now=t_active + 5)
    eng.on_gift(user_key="a", display="A", avatar_url="", diamonds=10, now=t_active + 6)
    s = eng.snapshot()
    assert s["combo"]["multiplier"] == 3.0
    assert s["combo"]["count"] == 6
    assert any(e["type"] == "combo_updated" for e in s["events"])


def test_combo_capped_by_max_multiplier() -> None:
    eng = _eng(
        combo_enabled=True,
        combo_threshold=3,
        combo_window_s=60,
        combo_max_multiplier=2.0,  # cap at x2; 2x-threshold would be x3.
        countdown_s=5,
        round_duration_s=600,
    )
    t0 = 1000.0
    t_active = _start_active(eng, t0)
    for i in range(6):  # 6 gifts = 2x threshold -> would be x3, capped at x2.
        eng.on_gift(user_key="a", display="A", avatar_url="", diamonds=10, now=t_active + 1 + i)
    s = eng.snapshot()
    assert s["combo"]["multiplier"] == 2.0
    assert s["combo"]["count"] == 6


def test_comeback_fires_once_on_overtake() -> None:
    eng = _eng(combo_enabled=False, countdown_s=5, round_duration_s=600)
    t0 = 1000.0
    t_active = _start_active(eng, t0)
    # Leader (A/left) pulls ahead: 60 >= 50 with a wide gap -> comeback arms.
    eng.on_gift(user_key="a", display="A", avatar_url="", diamonds=60, now=t_active + 1)
    assert eng.snapshot()["flags"]["is_comeback"] is False
    # B overtakes (70 > 60) -> comeback fires exactly once.
    eng.on_gift(user_key="b", display="B", avatar_url="", diamonds=70, now=t_active + 2)
    s = eng.snapshot()
    assert s["flags"]["is_comeback"] is True
    assert any(e["type"] == "comeback" and e["team_id"] == "right" for e in s["events"])
    assert sum(1 for e in s["events"] if e["type"] == "comeback") == 1
    # Further gifts must not re-fire the comeback (armed state was reset).
    eng.on_gift(user_key="b", display="B", avatar_url="", diamonds=50, now=t_active + 3)
    assert sum(1 for e in eng.snapshot()["events"] if e["type"] == "comeback") == 1


def test_comeback_arms_only_above_noise_floor() -> None:
    # No comeback can be armed while the leader is below the 50-point noise floor.
    eng = _eng(combo_enabled=False, countdown_s=5, round_duration_s=600)
    t0 = 1000.0
    t_active = _start_active(eng, t0)
    eng.on_gift(user_key="a", display="A", avatar_url="", diamonds=30, now=t_active + 1)  # 30 < 50
    eng.on_gift(user_key="b", display="B", avatar_url="", diamonds=10, now=t_active + 2)
    assert eng.snapshot()["flags"]["is_comeback"] is False
    # B then overtakes; the comeback was never armed, so nothing fires.
    assert sum(1 for e in eng.snapshot()["events"] if e["type"] == "comeback") == 0


def test_close_battle_fires_and_resets() -> None:
    eng = _eng(combo_enabled=False, countdown_s=5, round_duration_s=600, close_threshold_pct=10)
    t0 = 1000.0
    t_active = _start_active(eng, t0)
    # A=50, B=45 -> top=50 >= 20, gap=5/50=10% <= 10% -> close fires.
    eng.on_gift(user_key="a", display="A", avatar_url="", diamonds=50, now=t_active + 1)
    eng.on_gift(user_key="b", display="B", avatar_url="", diamonds=45, now=t_active + 2)
    s = eng.snapshot()
    assert s["flags"]["is_close"] is True
    assert any(e["type"] == "close_battle" for e in s["events"])
    # A then extends the lead -> gap 45/90=50% > 15% -> close resets.
    eng.on_gift(user_key="a", display="A", avatar_url="", diamonds=40, now=t_active + 3)
    assert eng.snapshot()["flags"]["is_close"] is False


def test_final_push_fires_once() -> None:
    eng = _eng(
        combo_enabled=False,
        round_duration_s=60,
        final_push_seconds=10,
        comeback_enabled=True,
        close_threshold_pct=10,
        countdown_s=5,
    )
    t0 = 1000.0
    t_active = _start_active(eng, t0)
    rd = eng._state.round_deadline  # t_active + 60
    # A=50, B=45 -> both >= 20, gap=10% <= close threshold.
    eng.on_gift(user_key="a", display="A", avatar_url="", diamonds=50, now=t_active + 1)
    eng.on_gift(user_key="b", display="B", avatar_url="", diamonds=45, now=t_active + 2)
    # Advance into the final-push window (remaining <= 10).
    for t in (rd - 6.0, rd - 5.0):
        eng.tick(now=t)
    s = eng.snapshot()
    assert s["flags"]["final_push"] is True
    assert sum(1 for e in s["events"] if e["type"] == "final_push") == 1


def test_round_zero_zero_is_draw_replay() -> None:
    eng = _eng(combo_enabled=False, countdown_s=5, round_duration_s=60)
    t0 = 1000.0
    _start_active(eng, t0)
    _resolve(eng)
    s = eng.snapshot()
    assert s["status"] == "countdown"  # replayed, not finished
    assert s["round"] == 1  # same round replayed
    assert s["round_wins"] == {"left": 0, "right": 0}
    assert _score(eng, "left") == 0 and _score(eng, "right") == 0
    assert any(e["type"] == "round_finished" and e["payload"]["draw"] is True for e in s["events"])


def test_exact_tie_positive_goes_left() -> None:
    eng = _eng(combo_enabled=False, countdown_s=5, round_duration_s=60)
    t0 = 1000.0
    t_active = _start_active(eng, t0)
    eng.on_gift(user_key="a", display="A", avatar_url="", diamonds=50, now=t_active + 1)
    eng.on_gift(user_key="b", display="B", avatar_url="", diamonds=50, now=t_active + 2)
    _resolve(eng)
    s = eng.snapshot()
    # Exact tie above zero is deterministic -> left.
    assert s["round_wins"]["left"] == 1
    assert s["round_wins"]["right"] == 0
    assert any(
        e["type"] == "round_finished" and e["payload"]["winner"] == "left" for e in s["events"]
    )


def _play_round(eng: BattleEngine, left_diamonds: int, right_diamonds: int) -> None:
    """Advance the engine one round: ensure ACTIVE, gift both sides, resolve."""
    st = eng._state
    if st.status.value == "countdown" and st.countdown_deadline is not None:
        eng.tick(now=st.countdown_deadline + 0.5)  # -> ACTIVE
    rd = eng._state.round_deadline
    assert rd is not None
    if left_diamonds:
        eng.on_gift(user_key="a", display="A", avatar_url="", diamonds=left_diamonds, now=rd - 10)
    if right_diamonds:
        eng.on_gift(user_key="b", display="B", avatar_url="", diamonds=right_diamonds, now=rd - 10)
    _resolve(eng)


def test_majority_best_of_3_finishes() -> None:
    eng = _eng(combo_enabled=False, countdown_s=1, round_duration_s=60, best_of=3)
    t0 = 1000.0
    # Round 1: A wins (50 > 10).
    _start_active(eng, t0)
    _play_round(eng, 50, 10)
    assert eng.snapshot()["round_wins"] == {"left": 1, "right": 0}
    assert eng.snapshot()["status"] == "countdown"
    # Round 2: B wins (10 < 50).
    _play_round(eng, 10, 50)
    assert eng.snapshot()["round_wins"] == {"left": 1, "right": 1}
    assert eng.snapshot()["status"] == "countdown"
    # Round 3: B wins -> 2/3 majority -> FINISHED.
    _play_round(eng, 10, 50)
    s = eng.snapshot()
    assert s["round_wins"] == {"left": 1, "right": 2}
    assert s["status"] == "finished"
    assert s["winner"] == {"team_id": "right", "name": "B"}
    assert any(
        e["type"] == "battle_finished" and e["payload"]["winner"] == "right" for e in s["events"]
    )


def test_best_of_1_finishes_on_first_round() -> None:
    eng = _eng(combo_enabled=False, countdown_s=1, round_duration_s=60, best_of=1)
    t0 = 1000.0
    _start_active(eng, t0)
    rd = eng._state.round_deadline
    eng.on_gift(user_key="a", display="A", avatar_url="", diamonds=10, now=rd - 10)
    eng.on_gift(user_key="b", display="B", avatar_url="", diamonds=20, now=rd - 10)
    _resolve(eng)
    s = eng.snapshot()
    assert s["status"] == "finished"
    assert s["winner"] == {"team_id": "right", "name": "B"}


def test_auto_reset_after_victory() -> None:
    eng = _eng(
        combo_enabled=False,
        countdown_s=1,
        round_duration_s=60,
        best_of=1,
        auto_reset=True,
    )
    t0 = 1000.0
    _start_active(eng, t0)
    rd = eng._state.round_deadline
    eng.on_gift(user_key="a", display="A", avatar_url="", diamonds=20, now=rd - 10)
    eng.on_gift(user_key="b", display="B", avatar_url="", diamonds=10, now=rd - 10)
    _resolve(eng)
    assert eng.snapshot()["status"] == "finished"
    vdl = eng._state.victory_deadline
    # Ticking past the victory deadline resets the engine to IDLE.
    eng.tick(now=vdl + 0.1)
    s = eng.snapshot()
    assert s["status"] == "idle"
    assert s["participants"] == []


def test_no_auto_reset_stays_finished() -> None:
    eng = _eng(
        combo_enabled=False,
        countdown_s=1,
        round_duration_s=60,
        best_of=1,
        auto_reset=False,
    )
    t0 = 1000.0
    _start_active(eng, t0)
    rd = eng._state.round_deadline
    eng.on_gift(user_key="a", display="A", avatar_url="", diamonds=20, now=rd - 10)
    eng.on_gift(user_key="b", display="B", avatar_url="", diamonds=10, now=rd - 10)
    _resolve(eng)
    vdl = eng._state.victory_deadline
    eng.tick(now=vdl + 10.0)  # well past the victory display
    assert eng.snapshot()["status"] == "finished"
    assert eng.snapshot()["winner"] is not None


def test_invalid_gifts_and_noops() -> None:
    eng = _eng(auto_start=True, auto_threshold_each=1, countdown_s=5)
    # Empty key / blank display is rejected.
    assert eng.on_gift(user_key="", display="", avatar_url="", diamonds=10) == []
    # Zero or negative diamonds rejected.
    assert eng.on_gift(user_key="a", display="A", avatar_url="", diamonds=0) == []
    assert eng.on_gift(user_key="a", display="A", avatar_url="", diamonds=-5) == []
    # Non-integer diamonds rejected.
    assert eng.on_gift(user_key="a", display="A", avatar_url="", diamonds="oops") == []
    # Likes and follows are no-ops in v1.
    assert eng.on_like(user_key="a", count=5) == []
    assert eng.on_follow(user_key="a") == []


def test_spectator_gift_not_participant_is_noop() -> None:
    # auto_start=False so gifts do not auto-arm; we arm A and B manually so they
    # are the two locked participants.
    eng = _eng(
        combo_enabled=False,
        countdown_s=5,
        round_duration_s=600,
        auto_start=False,
    )
    t0 = 1000.0
    t_active = _start_active(eng, t0)
    # A and B are participants; their gifts add points.
    eng.on_gift(user_key="a", display="A", avatar_url="", diamonds=10, now=t_active + 1)
    eng.on_gift(user_key="b", display="B", avatar_url="", diamonds=10, now=t_active + 2)
    a_before, b_before = _score(eng, "left"), _score(eng, "right")
    # A spectator (not a participant) must be ignored: scores unchanged.
    eng.on_gift(user_key="spectator", display="Spec", avatar_url="", diamonds=10, now=t_active + 3)
    assert _score(eng, "left") == a_before
    assert _score(eng, "right") == b_before
    assert (a_before, b_before) == (10, 10)
