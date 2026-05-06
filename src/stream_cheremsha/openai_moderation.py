"""OpenAI Moderation API (https://platform.openai.com/docs/api-reference/moderations)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_OPENAI_MODERATIONS_URL = "https://api.openai.com/v1/moderations"

# --- Decision thresholds (scores are 0..1). Tuned to reduce false positives for
# stream/game chat while still catching clear hate / harassment on text. ---

_STRONG_TEXT_KEYS = (
    "hate",
    "hate/threatening",
    "harassment",
    "harassment/threatening",
)
_STRONG_SCORE = 0.48
_MINORS_AND_ILLICIT = ("sexual/minors", "illicit", "illicit/violent")
_MINORS_SCORE = 0.22
_ILLICIT_SCORE = 0.42

_SELF_HARM_KEYS = ("self-harm", "self-harm/intent", "self-harm/instructions")
_SELF_HARM_SCORE = 0.38

_SEXUAL_KEY = "sexual"
_SEXUAL_SCORE = 0.82

# Violence alone often misfires on game commentary; require very high text-linked scores.
_VIOLENCE_KEYS = ("violence", "violence/graphic")
_VIOLENCE_SCORE = 0.93
_VIOLENCE_GRAPHIC_SCORE = 0.86


def moderation_response_should_suppress_tts(first: dict[str, Any]) -> bool:
    """
    Decide whether to replace chat TTS from the first element of ``results``.

    Does not rely on ``flagged`` alone: uses per-category booleans, scores, and
    ``category_applied_input_types`` so flags that apply only to ``image`` (or other
    non-text modalities) do not mute text TTS. Violence requires a very high score
    when tied to text, to avoid blocking harmless in-game talk.
    """
    cats = first.get("categories")
    scores = first.get("category_scores")
    applied_map = first.get("category_applied_input_types")

    if not isinstance(cats, dict):
        cats = {}
    if not isinstance(scores, dict):
        scores = {}
    if not isinstance(applied_map, dict):
        applied_map = {}

    def score(key: str) -> float:
        v = scores.get(key)
        if isinstance(v, bool):
            return 1.0 if v else 0.0
        if isinstance(v, int | float):
            return float(v)
        return 0.0

    def flagged_cat(key: str) -> bool:
        return cats.get(key) is True

    def applies_to_text(key: str) -> bool:
        """
        If OpenAI lists only non-text modalities for this category, ignore it for TTS text.
        Missing key, non-list, or empty list → treat as relevant to text (legacy / omni).
        """
        v = applied_map.get(key)
        if v is None:
            return True
        if not isinstance(v, list):
            return True
        if len(v) == 0:
            return True
        return "text" in v

    for key in _STRONG_TEXT_KEYS:
        if not applies_to_text(key):
            continue
        if flagged_cat(key) or score(key) >= _STRONG_SCORE:
            return True

    for key in _MINORS_AND_ILLICIT:
        if not applies_to_text(key):
            continue
        thr = _MINORS_SCORE if key == "sexual/minors" else _ILLICIT_SCORE
        if flagged_cat(key) or score(key) >= thr:
            return True

    for key in _SELF_HARM_KEYS:
        if not applies_to_text(key):
            continue
        if flagged_cat(key) or score(key) >= _SELF_HARM_SCORE:
            return True

    if applies_to_text(_SEXUAL_KEY) and (
        flagged_cat(_SEXUAL_KEY) or score(_SEXUAL_KEY) >= _SEXUAL_SCORE
    ):
        return True

    v_score = score("violence")
    vg_score = score("violence/graphic")
    if applies_to_text("violence") and v_score >= _VIOLENCE_SCORE:
        return True
    if applies_to_text("violence/graphic") and vg_score >= _VIOLENCE_GRAPHIC_SCORE:
        return True

    # Legacy responses without granular fields: fall back to top-level flagged.
    if not cats and not scores and first.get("flagged") is True:
        return True

    return False


async def openai_moderation_flagged(api_key: str, text: str, *, timeout_s: float = 30.0) -> bool:
    """
    Return True if TTS should use the moderation replacement line for ``text``.

    Uses per-category scores and ``category_applied_input_types``, not ``flagged`` alone.
    """
    key = (api_key or "").strip()
    if not key:
        raise ValueError("OpenAI API key is empty")
    payload: dict[str, Any] = {"input": text}
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        response = await client.post(_OPENAI_MODERATIONS_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
    results = data.get("results")
    if not isinstance(results, list) or not results:
        logger.warning("OpenAI moderation: missing results in response")
        return False
    first = results[0]
    if not isinstance(first, dict):
        return False
    return moderation_response_should_suppress_tts(first)
