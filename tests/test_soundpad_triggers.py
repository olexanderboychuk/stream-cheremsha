from __future__ import annotations

from stream_cheremsha.soundpad.models import TriggerConfig, TriggerKind
from stream_cheremsha.soundpad.triggers import (
    matches_chat_command,
    matches_donation,
    matches_gift,
    trigger_allowed,
)


def test_chat_command_exact_case_insensitive():
    assert matches_chat_command("!airhorn", "!airhorn") is True
    assert matches_chat_command("!Airhorn ", "airhorn") is True
    assert matches_chat_command("!airhorn please", "!airhorn") is False
    assert matches_chat_command("hello", "!airhorn") is False


def test_gift_match():
    assert matches_gift("Rose", "rose") is True
    assert matches_gift("Rose", "Money Gun") is False


def test_donation_threshold():
    assert matches_donation(15.0, "USD", ">10") is True
    assert matches_donation(5.0, "USD", ">10") is False
    assert matches_donation(10.0, "USD", "applause") is False


def test_cooldown_and_permission():
    t = TriggerConfig(
        kind=TriggerKind.CHAT_COMMAND, value="!a", permission="moderator", cooldown_sec=10.0
    )
    ok, _ = trigger_allowed(t, 100.0, 95.0, "viewer")
    assert ok is False
    ok2, wait = trigger_allowed(t, 100.0, 95.0, "moderator")
    assert ok2 is False and wait > 0
    ok3, _ = trigger_allowed(t, 200.0, 95.0, "moderator")
    assert ok3 is True
