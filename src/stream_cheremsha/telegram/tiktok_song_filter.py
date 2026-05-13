"""TikTok Live song screening: Genius lyrics + Groq chat API (JSON verdict)."""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any

import httpx
import lyricsgenius as lg

from stream_cheremsha import l10n

logger = logging.getLogger(__name__)

# Groq OpenAI-compatible API (https://console.groq.com/docs/openai).
_GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"
# Fast default; override with STREAM_CHEREMSHA_GROQ_MODEL (see Groq docs for IDs).
_GROQ_MODEL_DEFAULT = "llama-3.1-8b-instant"
_GROQ_MODEL_ENV = "STREAM_CHEREMSHA_GROQ_MODEL"


def _groq_model_id() -> str:
    raw = (os.environ.get(_GROQ_MODEL_ENV) or "").strip()
    return raw if raw else _GROQ_MODEL_DEFAULT


def _redact_api_key(text: str, key: str) -> str:
    k = (key or "").strip()
    if len(k) < 12:
        return text
    return text.replace(k, "***REDACTED***")


def _groq_api_error_user_message(body_text: str) -> str | None:
    """Parse Groq / OpenAI-style error JSON for a short user-facing line."""
    raw = (body_text or "").strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    err = data.get("error")
    if isinstance(err, str) and err.strip():
        one_line = " ".join(err.split())
        return one_line[:400] + ("…" if len(one_line) > 400 else "")
    if not isinstance(err, dict):
        return None
    msg = err.get("message")
    if not isinstance(msg, str) or not msg.strip():
        return None
    one_line = " ".join(msg.split())
    if len(one_line) > 400:
        return one_line[:397] + "…"
    return one_line


_MAX_LYRICS_CHARS = 18_000

_TIKTOK_SYSTEM_PROMPT = (
    "You are a moderator for a live streamer's song-request queue. Your task is to tell "
    "**artistic song lyrics** apart from content that truly warrants blocking the request.\n\n"
    "**Artistic context (always apply first):**\n"
    "- The text is **song lyrics** for entertainment, not a user chat message or a manifesto.\n"
    "- **Normally Safe:** metaphors; sadness, heartbreak, emotional pain, anger, or angst "
    "expressed in a lyrical or poetic way; storytelling; social or personal themes in song form; "
    "mild or occasional strong language typical of mainstream music.\n"
    "- Do **not** treat figurative or literary lines as literal threats, hate, or drug use.\n\n"
    '**"Banned"** — use **only** for clear-cut cases (when in doubt, do **not** choose Banned):\n'
    "- Direct slurs or extreme profanity used **as insults or attacks** (not mild emphasis or "
    "chorus expletives in an otherwise ordinary track).\n"
    "- Explicit **calls** to real-world violence or illegal harm against people.\n"
    "- **Weapon propaganda** or realistic instructions that enable harm.\n"
    "- **Named illegal drugs** used to **promote** use, sale, or procurement (specific substance "
    "or unambiguous street names). Vague references, metaphor, or mood alone do **not** count.\n\n"
    '**"Risky"** — use **sparingly**: borderline for a very family-friendly livestream but **not** '
    "strong enough for Banned (e.g. gratuitous crude sexual bragging as the main point, without "
    "literary framing). Do **not** use Risky for normal sad, intense, or metaphorical lyrics.\n\n"
    '**"Safe"** — the **default** for most music, including melancholic or "dark" lyrics that '
    "stay within normal artistic expression.\n\n"
    "Spirit (follow this): sad songs and metaphors about pain or a broken heart are Safe; only "
    "direct severe profanity as attacks, weapon propaganda, calls to real violence, or clear "
    "drug-promotion with specific names belong in Banned.\n\n"
    "Lyrics may be in any language — judge **meaning and intent in full context**, not isolated "
    "words.\n\n"
    "Response format (JSON only — no markdown, no text outside the JSON object):\n"
    "{\n"
    '"status": "Safe" | "Risky" | "Banned",\n'
    '"risk_score": 0-100,\n'
    '"violations": ["list of violations"],\n'
    '"dangerous_segments": ["verbatim phrases from the lyrics"]\n'
    "}"
)


def _strip_youtube_title_noise(title: str) -> str:
    t = (title or "").strip()
    if not t:
        return ""
    t = re.sub(r"\s*[\[(]\s*(official\s*)?(music\s*)?video.*$", "", t, flags=re.I)
    t = re.sub(r"\s*[\[(]\s*lyrics.*$", "", t, flags=re.I)
    t = re.sub(r"\s*[\[(]\s*audio.*$", "", t, flags=re.I)
    return t.strip()


def fetch_lyrics_for_youtube_title(genius_access_token: str, youtube_title: str) -> str | None:
    """
    Blocking: resolve lyrics via Genius from a YouTube video title (sync for asyncio.to_thread).

    Returns ``None`` if no match or empty lyrics.
    """
    token = (genius_access_token or "").strip()
    raw_title = (youtube_title or "").strip()
    if not token or not raw_title:
        return None

    title = _strip_youtube_title_noise(raw_title)
    if not title:
        return None

    genius = lg.Genius(
        token,
        remove_section_headers=True,
        skip_non_songs=True,
        timeout=25,
    )

    song = None
    if " - " in title:
        left, right = title.split(" - ", 1)
        left, right = left.strip(), right.strip()
        if left and right:
            song = genius.search_song(title=right, artist=left)
    if song is None:
        song = genius.search_song(title=title)
    if song is None:
        return None
    lyrics = (getattr(song, "lyrics", None) or "").strip()
    return lyrics if lyrics else None


def _extract_json_object(text: str) -> dict[str, Any] | None:
    s = (text or "").strip()
    if not s:
        return None
    try:
        data = json.loads(s)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", s, flags=re.I)
    if fence:
        inner = fence.group(1).strip()
        try:
            data = json.loads(inner)
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None
    m = re.search(r"\{[\s\S]*\}\s*$", s)
    if m:
        try:
            data = json.loads(m.group(0))
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def _coerce_str_list(v: Any) -> list[str]:
    if not isinstance(v, list):
        return []
    out: list[str] = []
    for it in v:
        if isinstance(it, str) and it.strip():
            out.append(it.strip())
    return out


def _normalize_status(raw: Any) -> str:
    s = str(raw or "").strip().lower()
    if s == "safe":
        return "Safe"
    if s == "risky":
        return "Risky"
    if s == "banned":
        return "Banned"
    return ""


def _coerce_risk_score(raw: Any) -> int | None:
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return max(0, min(100, raw))
    if isinstance(raw, float):
        return max(0, min(100, int(round(raw))))
    if isinstance(raw, str) and raw.strip():
        try:
            return max(0, min(100, int(float(raw.strip()))))
        except ValueError:
            return None
    return None


@dataclass(slots=True)
class TikTokLyricsVerdict:
    status: str
    risk_score: int | None
    violations: list[str]
    dangerous_segments: list[str]

    def allows_enqueue(self) -> bool:
        return self.status == "Safe"


class TikTokLyricsCheckError(Exception):
    """Raised when Genius/Groq screening cannot complete (message is viewer-localized)."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def format_tiktok_reject_reason(verdict: TikTokLyricsVerdict, *, ui_locale: str) -> str:
    """Human-friendly Telegram line; language follows app UI locale."""
    lc = l10n.normalize_locale(ui_locale)
    if verdict.status == "Banned":
        return l10n.tr(lc, "telegram.song.tiktok_hard_no")
    if verdict.status == "Risky":
        return l10n.tr(lc, "telegram.song.tiktok_soft_no")
    return l10n.tr(lc, "telegram.song.tiktok_soft_no")


def _groq_chat_response_content(data: dict[str, Any]) -> str:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    c0 = choices[0]
    if not isinstance(c0, dict):
        return ""
    msg = c0.get("message")
    if not isinstance(msg, dict):
        return ""
    return str(msg.get("content") or "").strip()


async def analyze_lyrics_with_groq(
    api_key: str,
    lyrics: str,
    ui_locale: str,
    *,
    youtube_title: str = "",
    timeout_s: float = 75.0,
) -> TikTokLyricsVerdict:
    """
    Ask Groq (chat completions) to classify lyrics for stream song-queue risk.

    Only ``Safe`` enqueues. Uses JSON object mode when the model supports it.
    Prompts favour **artistic context** (lyrics are not literal speech) and a **narrow** Banned bar.
    """
    lc = l10n.normalize_locale(ui_locale)
    key = (api_key or "").strip()
    if not key:
        raise TikTokLyricsCheckError(l10n.tr(lc, "telegram.song.check_unavailable"))

    body_lyrics = (lyrics or "").strip()
    if len(body_lyrics) > _MAX_LYRICS_CHARS:
        body_lyrics = body_lyrics[:_MAX_LYRICS_CHARS]

    user_lines = [
        "Task: Classify the following text using the artistic-context rules in your system "
        "message. Prefer **Safe** when lyrics are ordinary music (including sad or metaphorical). "
        "Use **Banned** only when the strict Banned criteria clearly apply. Use **Risky** rarely.",
        "",
        "Lyrics to analyze:",
        f'"{body_lyrics}"',
    ]
    meta = (youtube_title or "").strip()
    if meta:
        user_lines.insert(0, f"YouTube title (context): {meta}")
        user_lines.insert(1, "")

    user_text = "\n".join(user_lines)
    model_id = _groq_model_id()

    payload: dict[str, Any] = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": _TIKTOK_SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            response = await client.post(
                _GROQ_CHAT_COMPLETIONS_URL,
                json=payload,
                headers=headers,
            )
        response.raise_for_status()
    except httpx.HTTPStatusError:
        detail = ""
        try:
            detail = response.text[:1200]
        except OSError:
            detail = ""
        detail = _redact_api_key(detail, key)
        status = int(response.status_code)
        api_err = _groq_api_error_user_message(detail)
        logger.warning(
            "Groq HTTP error model=%s status=%s detail=%s",
            model_id,
            status,
            detail,
        )
        if status == 429:
            if api_err:
                logger.warning("Groq 429 detail: %s", api_err)
            raise TikTokLyricsCheckError(l10n.tr(lc, "telegram.song.groq_busy")) from None
        if api_err:
            logger.warning("Groq HTTP %s detail: %s", status, api_err)
        raise TikTokLyricsCheckError(
            l10n.tr(lc, "telegram.song.groq_service"),
        ) from None
    except httpx.RequestError as e:
        logger.warning(
            "Groq network error model=%s err=%s",
            model_id,
            _redact_api_key(str(e), key),
        )
        raise TikTokLyricsCheckError(l10n.tr(lc, "telegram.song.check_unavailable")) from None

    try:
        data = response.json()
    except json.JSONDecodeError as e:
        logger.warning("Groq response JSON parse failed: %s", e)
        raise TikTokLyricsCheckError(l10n.tr(lc, "telegram.song.check_unavailable")) from e

    text_out = _groq_chat_response_content(data)
    if not text_out:
        choices = data.get("choices")
        reason = ""
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            reason = str(choices[0].get("finish_reason") or "").strip()
        if reason:
            logger.warning("Groq empty assistant content (finish_reason=%s)", reason)
        raise TikTokLyricsCheckError(l10n.tr(lc, "telegram.song.check_unavailable"))

    parsed = _extract_json_object(text_out)
    if not parsed:
        logger.warning("Groq output JSON parse failed; snippet=%r", text_out[:240])
        raise TikTokLyricsCheckError(l10n.tr(lc, "telegram.song.check_unavailable"))

    verdict_status = _normalize_status(parsed.get("status"))
    if not verdict_status:
        verdict_status = "Risky"
    risk = _coerce_risk_score(parsed.get("risk_score"))
    violations = _coerce_str_list(parsed.get("violations"))
    dangerous = _coerce_str_list(parsed.get("dangerous_segments"))

    return TikTokLyricsVerdict(
        status=verdict_status,
        risk_score=risk,
        violations=violations,
        dangerous_segments=dangerous,
    )
