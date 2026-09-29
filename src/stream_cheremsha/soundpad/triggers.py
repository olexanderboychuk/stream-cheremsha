from __future__ import annotations

import re

from stream_cheremsha.soundpad.models import TriggerConfig

_ROLE_RANK = {"anyone": 0, "follower": 1, "subscriber": 2, "moderator": 3, "broadcaster": 4}


def _norm_cmd(v: str) -> str:
    s = str(v or "").strip().lower()
    return s if s.startswith("!") else f"!{s}" if s else ""


def matches_chat_command(text: str, trigger_value: str) -> bool:
    want = _norm_cmd(trigger_value)
    if not want:
        return False
    got = str(text or "").strip().lower()
    return got == want


def matches_gift(gift_name: str, trigger_value: str) -> bool:
    want = str(trigger_value or "").strip().lower()
    return bool(want) and str(gift_name or "").strip().lower() == want


def matches_donation(amount: float, currency: str, trigger_value: str) -> bool:
    spec = str(trigger_value or "").strip()
    if not spec:
        return False
    m = re.match(r"^\s*(>=|>|<=|<|==)?\s*(\d+(?:\.\d+)?)\s*([A-Za-z]{0,4})\s*$", spec)
    if m:
        op, num, _cur = m.groups()
        try:
            threshold = float(num)
        except ValueError:
            return False
        amt = float(amount or 0.0)
        op = op or ">="
        return {
            ">": amt > threshold,
            ">=": amt >= threshold,
            "<": amt < threshold,
            "<=": amt <= threshold,
            "==": amt == threshold,
        }[op]
    return False


def trigger_allowed(
    trigger: TriggerConfig, now: float, last_fired: float, user_role: str
) -> tuple[bool, float]:
    need = _ROLE_RANK.get(str(trigger.permission or "anyone").lower(), 0)
    have = _ROLE_RANK.get(str(user_role or "anyone").lower(), 0)
    if have < need:
        return False, 0.0
    cd = max(0.0, float(trigger.cooldown_sec or 0.0))
    wait = (float(last_fired or 0.0) + cd) - float(now)
    if wait > 0:
        return False, round(wait, 2)
    return True, 0.0
