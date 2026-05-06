"""Normalize text for TTS (Qt-free)."""

from __future__ import annotations

import unicodedata


def strip_non_alphabetic_for_tts(text: str) -> str:
    """
    Remove characters that are not Unicode letters (category L*).
    Other characters (digits, punctuation, symbols, emoji, etc.) become word breaks;
    runs of whitespace collapse to a single space.
    """
    if not text:
        return ""
    out: list[str] = []
    for ch in text:
        if unicodedata.category(ch).startswith("L"):
            out.append(ch)
        else:
            out.append(" ")
    return " ".join("".join(out).split())
