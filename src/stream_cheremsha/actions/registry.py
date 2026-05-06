from __future__ import annotations

import re
from typing import Literal

MatchMode = Literal["contains", "equals", "regex"]


def match_chat_keyword(
    text: str,
    keyword: str,
    *,
    mode: MatchMode = "contains",
    case_sensitive: bool = False,
) -> bool:
    """Return True if `text` matches `keyword` per `mode`.

    Modes:
    - contains: keyword is a substring of text
    - equals: keyword equals text
    - regex: keyword is a regular expression; uses re.search

    If case_sensitive is False, comparisons use str.casefold().

    Invalid regex patterns raise ValueError.
    """

    if mode not in ("contains", "equals", "regex"):
        raise ValueError(f"Unsupported match mode: {mode}")

    t = text
    k = keyword
    if not case_sensitive:
        t = t.casefold()
        k = k.casefold()

    if mode == "contains":
        return k in t
    if mode == "equals":
        return k == t

    try:
        return re.search(k, t) is not None
    except re.error as e:
        # re.error messages are reasonably clear; keep it user-facing.
        raise ValueError(f"Invalid regex pattern: {e}") from e
