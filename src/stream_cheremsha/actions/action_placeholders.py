from __future__ import annotations

import re
from typing import Any

from stream_cheremsha.actions.events import (
    ChatMessageEvent,
    GiftReceivedEvent,
    TikTokFirstActivityEvent,
    TikTokFollowedEvent,
    TikTokJoinedEvent,
    TikTokLikesReceivedEvent,
    TikTokPaidSubscribedEvent,
    TikTokSharedEvent,
    TwitchCheerEvent,
    TwitchFollowEvent,
    TwitchRaidEvent,
    TwitchResubscribeEvent,
    TwitchSubscribeEvent,
    TwitchSubscriptionGiftEvent,
)

_PLACEHOLDER_RE = re.compile(r"\{([^{}]+)\}")
_SIMPLE_TOKEN_RE = re.compile(r"^[a-zA-Z0-9_]+$")
_INT_RE = re.compile(r"^[+-]?\d+$")


class _ExprError(Exception):
    pass


def _tokenize_int_expr(expr: str) -> list[tuple[str, str]]:
    """Tokenize a small integer expression language.

    Tokens:
    - INT: 123
    - ID: giftcount
    - OP: + - * / %
    - PAREN: ( )
    """
    out: list[tuple[str, str]] = []
    i = 0
    s = expr
    n = len(s)
    while i < n:
        ch = s[i]
        if ch.isspace():
            i += 1
            continue
        if ch in "()+-*/%":
            if ch in "()":
                out.append(("PAREN", ch))
            else:
                out.append(("OP", ch))
            i += 1
            continue
        if ch.isdigit():
            j = i + 1
            while j < n and s[j].isdigit():
                j += 1
            out.append(("INT", s[i:j]))
            i = j
            continue
        if ch.isalpha() or ch == "_":
            j = i + 1
            while j < n and (s[j].isalnum() or s[j] == "_"):
                j += 1
            out.append(("ID", s[i:j]))
            i = j
            continue
        raise _ExprError(f"Unexpected character: {ch!r}")
    return out


def _eval_int_expr(expr: str, vars_int: dict[str, int]) -> int:
    """Evaluate integer expression without using eval().

    Grammar (precedence):
      expr  := term (('+'|'-') term)*
      term  := factor (('*'|'/'|'%') factor)*
      factor:= ('+'|'-') factor | primary
      primary:= INT | ID | '(' expr ')'
    """
    toks = _tokenize_int_expr(expr)
    pos = 0

    def peek() -> tuple[str, str] | None:
        nonlocal pos
        if pos >= len(toks):
            return None
        return toks[pos]

    def take(expected_kind: str | None = None, expected_val: str | None = None) -> tuple[str, str]:
        nonlocal pos
        t = peek()
        if t is None:
            raise _ExprError("Unexpected end of expression")
        kind, val = t
        if expected_kind is not None and kind != expected_kind:
            raise _ExprError(f"Expected {expected_kind}, got {kind}")
        if expected_val is not None and val != expected_val:
            raise _ExprError(f"Expected {expected_val!r}, got {val!r}")
        pos += 1
        return kind, val

    def parse_primary() -> int:
        t = peek()
        if t is None:
            raise _ExprError("Unexpected end of expression")
        kind, val = t
        if kind == "INT":
            take("INT")
            return int(val)
        if kind == "ID":
            take("ID")
            k = val.lower()
            if k not in vars_int:
                raise _ExprError(f"Unknown variable: {val}")
            return int(vars_int[k])
        if kind == "PAREN" and val == "(":
            take("PAREN", "(")
            v = parse_expr()
            take("PAREN", ")")
            return v
        raise _ExprError(f"Unexpected token: {kind} {val!r}")

    def parse_factor() -> int:
        t = peek()
        if t is not None and t[0] == "OP" and t[1] in "+-":
            op = take("OP")[1]
            v = parse_factor()
            return v if op == "+" else -v
        return parse_primary()

    def parse_term() -> int:
        v = parse_factor()
        while True:
            t = peek()
            if t is None or t[0] != "OP" or t[1] not in "*/%":
                break
            op = take("OP")[1]
            rhs = parse_factor()
            if op == "*":
                v = v * rhs
            elif op == "%":
                if rhs == 0:
                    raise _ExprError("Modulo by zero")
                v = v % rhs
            else:
                if rhs == 0:
                    raise _ExprError("Division by zero")
                # Truncate towards zero (so 7/2 -> 3, -7/2 -> -3)
                v = int(v / rhs)
        return v

    def parse_expr() -> int:
        v = parse_term()
        while True:
            t = peek()
            if t is None or t[0] != "OP" or t[1] not in "+-":
                break
            op = take("OP")[1]
            rhs = parse_term()
            v = v + rhs if op == "+" else v - rhs
        return v

    out = parse_expr()
    if pos != len(toks):
        raise _ExprError("Unexpected trailing tokens")
    return out


def _platform_str(platform: Any) -> str:
    return str(getattr(platform, "value", platform))


def build_placeholder_context(ev: object) -> dict[str, str]:
    """Lowercase keys for `{name}` lookup (name is matched case-insensitively)."""
    if isinstance(ev, GiftReceivedEvent):
        c = str(int(ev.count))
        gn = ev.gift_name or ""
        gid = ev.gift_id or ""
        snd = ev.sender or ""
        plat = _platform_str(ev.platform)
        return {
            "giftcount": c,
            "gift_count": c,
            "count": c,
            "repeatcount": c,
            "giftname": gn,
            "gift_name": gn,
            "giftid": gid,
            "gift_id": gid,
            "sender": snd,
            "username": snd,
            "nickname": snd,
            "platform": plat,
        }
    if isinstance(ev, ChatMessageEvent):
        au = ev.author or ""
        tx = ev.text or ""
        return {
            "author": au,
            "text": tx,
            "comment": tx,
            "username": au,
            "nickname": au,
            "platform": _platform_str(ev.platform),
        }
    if isinstance(ev, TikTokLikesReceivedEvent):
        batch = str(int(ev.likes_in_batch))
        tot = str(int(ev.likes_total_for_scope))
        u = ev.user or ""
        return {
            "sender": u,
            "user": u,
            "username": u,
            "nickname": u,
            "likebatch": batch,
            "likes_batch": batch,
            "likecount": batch,
            "liketotal": tot,
            "likes_total": tot,
            "totallikecount": tot,
            "count": batch,
            "platform": _platform_str(ev.platform),
        }
    if isinstance(
        ev,
        (
            TikTokJoinedEvent,
            TikTokFollowedEvent,
            TikTokPaidSubscribedEvent,
        ),
    ):
        u = ev.user or ""
        return {
            "sender": u,
            "user": u,
            "username": u,
            "nickname": u,
            "platform": _platform_str(ev.platform),
        }
    if isinstance(ev, TikTokSharedEvent):
        u = ev.user or ""
        c = str(int(ev.count))
        return {
            "sender": u,
            "user": u,
            "username": u,
            "nickname": u,
            "count": c,
            "platform": _platform_str(ev.platform),
        }
    if isinstance(ev, TikTokFirstActivityEvent):
        u = ev.user or ""
        c = str(int(ev.count))
        return {
            "sender": u,
            "user": u,
            "username": u,
            "nickname": u,
            "count": c,
            "kind": ev.kind or "",
            "platform": _platform_str(ev.platform),
        }
    if isinstance(ev, TwitchFollowEvent):
        u = ev.user or ""
        return {
            "sender": u,
            "user": u,
            "username": u,
            "nickname": u,
            "platform": _platform_str(ev.platform),
        }
    if isinstance(ev, (TwitchSubscribeEvent, TwitchSubscriptionGiftEvent)):
        u = ev.user or ""
        mo = str(int(ev.months))
        return {
            "sender": u,
            "user": u,
            "username": u,
            "nickname": u,
            "months": mo,
            "submonth": mo,
            "platform": _platform_str(ev.platform),
        }
    if isinstance(ev, TwitchResubscribeEvent):
        u = ev.user or ""
        mo = str(int(ev.months))
        msg = ev.message or ""
        return {
            "sender": u,
            "user": u,
            "username": u,
            "nickname": u,
            "months": mo,
            "submonth": mo,
            "message": msg,
            "text": msg,
            "platform": _platform_str(ev.platform),
        }
    if isinstance(ev, TwitchCheerEvent):
        u = ev.user or ""
        b = str(int(ev.bits))
        return {
            "sender": u,
            "user": u,
            "username": u,
            "nickname": u,
            "bits": b,
            "count": b,
            "platform": _platform_str(ev.platform),
        }
    if isinstance(ev, TwitchRaidEvent):
        r = ev.raider or ""
        v = str(int(ev.viewers))
        return {
            "sender": r,
            "user": r,
            "username": r,
            "nickname": r,
            "raider": r,
            "viewers": v,
            "count": v,
            "platform": _platform_str(ev.platform),
        }
    return {}


def apply_action_placeholders(template: str, ev: object) -> str:
    """Replace `{token}` substrings using event context; unknown tokens stay unchanged."""
    ctx = build_placeholder_context(ev)
    if not ctx:
        return template

    def repl(m: re.Match[str]) -> str:
        raw = (m.group(1) or "").strip()
        if not raw:
            return m.group(0)

        # Fast path: simple `{token}`.
        if _SIMPLE_TOKEN_RE.match(raw):
            key = raw.lower()
            if key in ctx:
                return ctx[key]
            return m.group(0)

        # Expression path: `{giftcount-1}` etc (integer-only).
        vars_int: dict[str, int] = {}
        for k, v in ctx.items():
            if _INT_RE.match(v.strip()):
                vars_int[k.lower()] = int(v)
        try:
            val = _eval_int_expr(raw, vars_int)
        except _ExprError:
            return m.group(0)
        return str(val)

    return _PLACEHOLDER_RE.sub(repl, template)


def strip_unresolved_placeholders(text: str) -> str:
    """Remove any leftover `{...}` tokens after placeholder substitution.

    This is intended for user-facing speech (TTS) where unresolved placeholders should not
    be read aloud.
    """
    if not text or "{" not in text:
        return text
    # Replace any `{...}` chunk with empty string.
    return _PLACEHOLDER_RE.sub("", text)
