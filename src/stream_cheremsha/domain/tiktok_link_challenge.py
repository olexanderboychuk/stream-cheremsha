"""TikTok ↔ Telegram link verification via a one-time code in live chat."""

from __future__ import annotations

import re
import secrets

# Simple English words — easy to type in TikTok live chat.
LINK_CODE_WORDS: tuple[str, ...] = (
    "Cat",
    "Dog",
    "Kitty",
    "Puppy",
    "Bear",
    "Fox",
    "Wolf",
    "Lion",
    "Tiger",
    "Panda",
    "Koala",
    "Bunny",
    "Rabbit",
    "Horse",
    "Pony",
    "Deer",
    "Owl",
    "Eagle",
    "Duck",
    "Swan",
    "Fish",
    "Shark",
    "Whale",
    "Frog",
    "Turtle",
    "Snake",
    "Mouse",
    "Hamster",
    "Parrot",
    "Bee",
    "Crab",
    "Seal",
    "Otter",
    "Lamb",
    "Pig",
    "Cow",
    "Goat",
    "Hen",
    "Crow",
    "Bat",
    "Moth",
    "Snail",
    "Star",
    "Moon",
    "Sun",
    "Cloud",
    "Rose",
    "Lily",
    "Maple",
    "Cedar",
    "Olive",
)

_CANONICAL_BY_LOWER = {word.lower(): word for word in LINK_CODE_WORDS}
_WORDS_LONGEST_FIRST = sorted(LINK_CODE_WORDS, key=len, reverse=True)
_LINK_CODE_RE = re.compile(
    r"\b(" + "|".join(re.escape(word) for word in _WORDS_LONGEST_FIRST) + r")\b",
    re.IGNORECASE,
)

DEFAULT_LINK_CHALLENGE_TTL_SEC = 600


def generate_link_code() -> str:
    """Return a fresh one-time word code for the viewer to post in TikTok live chat."""
    return secrets.choice(LINK_CODE_WORDS)


def normalize_link_code(raw: str) -> str:
    """Normalize a code for DB lookup (canonical Title Case word)."""
    key = (raw or "").strip().lower()
    return _CANONICAL_BY_LOWER.get(key, "")


def extract_link_code_from_comment(text: str) -> str | None:
    """Extract a link verification code from a chat comment, if present."""
    m = _LINK_CODE_RE.search((text or "").strip())
    if m is None:
        return None
    return normalize_link_code(m.group(1))


def comment_matches_link_code(text: str, expected_code: str) -> bool:
    """Return whether ``text`` contains the expected verification code."""
    found = extract_link_code_from_comment(text)
    if not found:
        return False
    return found == normalize_link_code(expected_code)
