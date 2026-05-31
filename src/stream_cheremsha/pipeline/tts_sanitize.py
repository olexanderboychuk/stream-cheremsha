"""Normalize text for TTS (Qt-free)."""

from __future__ import annotations

import re
import unicodedata

# TikTok/Twitch-style emote names in chat, e.g. [hi], [heart], [Kappa].
_EMOTE_SHORTCODE_RE = re.compile(r"\[[^\[\]]+\]")


def _is_tts_kept_char(ch: str) -> bool:
    cat = unicodedata.category(ch)
    return cat.startswith("L") or cat == "Nd"


def strip_non_alphabetic_for_tts(text: str) -> str:
    """
    Remove characters that are not Unicode letters (category L*) or decimal digits (Nd).
    Bracketed emote shortcodes (e.g. ``[heart]``) are removed first.
    Other characters (punctuation, symbols, emoji, etc.) become word breaks;
    runs of whitespace collapse to a single space.
    """
    if not text:
        return ""
    text = _EMOTE_SHORTCODE_RE.sub(" ", text)
    out: list[str] = []
    for ch in text:
        if _is_tts_kept_char(ch):
            out.append(ch)
        else:
            out.append(" ")
    return " ".join("".join(out).split())
