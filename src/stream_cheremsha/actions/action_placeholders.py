from __future__ import annotations

import re
from typing import Any

from stream_cheremsha.actions.events import (
    ChatMessageEvent,
    DonateReceivedEvent,
    GiftReceivedEvent,
    KickFollowEvent,
    KickGiftEvent,
    KickGiftSubscriptionEvent,
    KickSubscriptionEvent,
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
    YouTubeMemberEvent,
    YouTubeSuperChatEvent,
    YouTubeSuperStickerEvent,
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
    if isinstance(ev, (YouTubeSuperChatEvent, YouTubeSuperStickerEvent)):
        u = ev.user or ""
        disp = ev.amount_display or ""
        value = f"{ev.amount_micros / 1_000_000.0:g}" if ev.amount_micros else "0"
        cur = ev.currency or ""
        msg = getattr(ev, "message", "") or ""
        return {
            "sender": u,
            "user": u,
            "username": u,
            "nickname": u,
            "amount": disp,
            "amount_value": value,
            "currency": cur,
            "message": msg,
            "text": msg,
            "platform": _platform_str(ev.platform),
        }
    if isinstance(ev, YouTubeMemberEvent):
        u = ev.user or ""
        mo = str(int(ev.months))
        lvl = ev.level or ""
        return {
            "sender": u,
            "user": u,
            "username": u,
            "nickname": u,
            "months": mo,
            "submonth": mo,
            "level": lvl,
            "platform": _platform_str(ev.platform),
        }
    if isinstance(ev, DonateReceivedEvent):
        u = ev.user or ""
        try:
            amt = float(ev.amount)
        except (TypeError, ValueError):
            amt = 0.0
        disp = f"{amt:g}"
        cur = ev.currency or ""
        msg = ev.message or ""
        return {
            "sender": u,
            "user": u,
            "username": u,
            "nickname": u,
            "donor": u,
            "amount": disp,
            "amount_value": disp,
            "currency": cur,
            "message": msg,
            "text": msg,
            "platform": _platform_str(ev.platform),
        }
    if isinstance(ev, KickFollowEvent):
        u = ev.user or ""
        return {
            "sender": u,
            "user": u,
            "username": u,
            "nickname": u,
            "platform": _platform_str(ev.platform),
        }
    if isinstance(ev, KickSubscriptionEvent):
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
    if isinstance(ev, KickGiftSubscriptionEvent):
        u = ev.user or ""
        c = str(int(ev.count))
        return {
            "sender": u,
            "user": u,
            "username": u,
            "nickname": u,
            "count": c,
            "giftcount": c,
            "platform": _platform_str(ev.platform),
        }
    if isinstance(ev, KickGiftEvent):
        u = ev.user or ""
        a = str(int(ev.amount))
        return {
            "sender": u,
            "user": u,
            "username": u,
            "nickname": u,
            "amount": a,
            "amount_value": a,
            "count": a,
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


def _ref_var(names: list[str], uk: str, en: str) -> dict[str, object]:
    return {"names": list(names), "uk": uk, "en": en}


def _ref_cat(title_uk: str, title_en: str, triggers: str, rows: list[dict[str, object]]) -> dict[str, object]:
    return {"title_uk": title_uk, "title_en": title_en, "triggers": triggers, "vars": rows}


def placeholder_reference(locale: str = "uk") -> list[dict[str, object]]:
    """Categorized `{variable}` reference for the Actions editor (single source of truth).

    Each category mirrors one ``build_placeholder_context`` branch. ``names`` lists all
    aliases with identical values; the first name is the canonical one.
    """
    _ = locale
    user_names = ["sender", "user", "username", "nickname"]
    user_row = _ref_var(
        user_names,
        "нік користувача (усі варіанти — синоніми)",
        "user nickname (all variants are synonyms)",
    )
    platform_row = _ref_var(
        ["platform"],
        "платформа події: tiktok, twitch, youtube, kick, donatik, donatello",
        "event platform: tiktok, twitch, youtube, kick, donatik, donatello",
    )
    return [
        _ref_cat(
            "Чат (ключове слово)",
            "Chat (keyword)",
            "chat_keyword",
            [
                _ref_var(["author"], "автор повідомлення", "message author"),
                _ref_var(["text", "comment"], "текст повідомлення", "message text"),
                _ref_var(["username", "nickname"], "автор (синоніми)", "author (synonyms)"),
                platform_row,
            ],
        ),
        _ref_cat(
            "Подарунок TikTok",
            "TikTok gift",
            "gift_received, tiktok_any_gift_received",
            [
                _ref_var(
                    ["giftcount", "gift_count", "count", "repeatcount"],
                    "кількість подарунків",
                    "gift count",
                ),
                _ref_var(["giftname", "gift_name"], "назва подарунка", "gift name"),
                _ref_var(["giftid", "gift_id"], "id подарунка", "gift id"),
                user_row,
                platform_row,
            ],
        ),
        _ref_cat(
            "Лайки TikTok",
            "TikTok likes",
            "tiktok_likes_received",
            [
                _ref_var(
                    ["likebatch", "likes_batch", "likecount", "count"],
                    "лайків у цій пачці",
                    "likes in this batch",
                ),
                _ref_var(
                    ["liketotal", "likes_total", "totallikecount"],
                    "сумарні лайки (за обраним охопленням)",
                    "total likes (for the chosen scope)",
                ),
                user_row,
                platform_row,
            ],
        ),
        _ref_cat(
            "Вступ / фолов / саб без лічильника",
            "Join / follow / sub (no counter)",
            "tiktok_joined, tiktok_followed, tiktok_paid_subscribed, twitch_follow, twitch_subscribe, "
            "twitch_sub_gift, kick_follow",
            [user_row, platform_row],
        ),
        _ref_cat(
            "Підписки з місяцями",
            "Subscriptions with months",
            "twitch_subscribe, twitch_resub, twitch_sub_gift, youtube_member, kick_subscription",
            [
                user_row,
                _ref_var(["months", "submonth"], "місяців підписки", "subscription months"),
                _ref_var(
                    ["level"],
                    "рівень (тільки YouTube member)",
                    "tier level (YouTube member only)",
                ),
                _ref_var(
                    ["message", "text"],
                    "повідомлення (тільки Twitch resub)",
                    "message (Twitch resub only)",
                ),
                platform_row,
            ],
        ),
        _ref_cat(
            "Шер TikTok",
            "TikTok share",
            "tiktok_shared",
            [
                user_row,
                _ref_var(["count"], "кількість шерів", "share count"),
                platform_row,
            ],
        ),
        _ref_cat(
            "Перша активність TikTok",
            "TikTok first activity",
            "tiktok_first_activity",
            [
                user_row,
                _ref_var(["count"], "кількість", "count"),
                _ref_var(
                    ["kind"],
                    "тип активності: join, comment, gift, like, follow, share, paid_sub",
                    "activity kind: join, comment, gift, like, follow, share, paid_sub",
                ),
                platform_row,
            ],
        ),
        _ref_cat(
            "Cheer / біти Twitch",
            "Twitch cheer / bits",
            "twitch_cheer",
            [
                user_row,
                _ref_var(["bits", "count"], "кількість бітів", "bits count"),
                platform_row,
            ],
        ),
        _ref_cat(
            "Рейд Twitch",
            "Twitch raid",
            "twitch_raid",
            [
                _ref_var(["raider"], "канал рейдера", "raider channel"),
                _ref_var(["viewers", "count"], "глядачів у рейді", "raid viewers"),
                user_row,
                platform_row,
            ],
        ),
        _ref_cat(
            "Super Chat / Super Sticker YouTube",
            "YouTube Super Chat / Super Sticker",
            "youtube_superchat, youtube_supersticker",
            [
                user_row,
                _ref_var(
                    ["amount"],
                    "сума як на екрані (з валютою, напр. $5)",
                    "amount as displayed (with currency, e.g. $5)",
                ),
                _ref_var(
                    ["amount_value"],
                    "числове значення суми (без валюти)",
                    "numeric amount value (no currency)",
                ),
                _ref_var(["currency"], "валюта (USD, UAH…)", "currency (USD, UAH…)"),
                _ref_var(
                    ["message", "text"],
                    "повідомлення (тільки Super Chat)",
                    "message (Super Chat only)",
                ),
                platform_row,
            ],
        ),
        _ref_cat(
            "Донат Donatik / Donatello",
            "Donatik / Donatello donation",
            "donate",
            [
                _ref_var(
                    ["donor", "sender", "user", "username", "nickname"],
                    "нік донатера",
                    "donor nickname",
                ),
                _ref_var(
                    ["amount", "amount_value"],
                    "сума донату числом",
                    "donation amount as a number",
                ),
                _ref_var(["currency"], "валюта", "currency"),
                _ref_var(["message", "text"], "повідомлення донатера", "donor message"),
                platform_row,
            ],
        ),
        _ref_cat(
            "Подарункові саби / KICKs (Kick)",
            "Kick gift subs / KICKs",
            "kick_gift_sub, kick_gift",
            [
                user_row,
                _ref_var(
                    ["count", "giftcount"],
                    "кількість гіфт-сабів (kick_gift_sub)",
                    "gift sub count (kick_gift_sub)",
                ),
                _ref_var(
                    ["amount", "amount_value", "count"],
                    "кількість KICKs (kick_gift)",
                    "KICKs amount (kick_gift)",
                ),
                platform_row,
            ],
        ),
        _ref_cat(
            "Математика в дужках",
            "Math inside braces",
            "будь-який тригер з числовою змінною",
            [
                _ref_var(
                    ["{giftcount-1}", "{liketotal+5}", "{count*2}"],
                    "цілочисельні вирази: + - * / % і дужки",
                    "integer expressions: + - * / % and parentheses",
                ),
            ],
        ),
    ]
