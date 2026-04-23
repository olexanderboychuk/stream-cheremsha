from __future__ import annotations

from stream_cheremsha.config.constants import TTS_CHUNK_CHARS, TTS_MIN_MERGE_CHUNK_CHARS


def chunk_text(text: str, max_chars: int = TTS_CHUNK_CHARS) -> list[str]:
    """Split text into chunks suitable for the Google TTS endpoint."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    rest = text
    while rest:
        if len(rest) <= max_chars:
            chunks.append(rest)
            break
        window = rest[:max_chars]
        cut = window.rfind(" ")
        if cut <= max_chars // 4:
            cut = max_chars
        piece = rest[:cut].strip()
        if piece:
            chunks.append(piece)
        rest = rest[cut:].strip()
    return chunks


def merge_short_subchunks(
    chunks: list[str],
    *,
    min_chars: int = TTS_MIN_MERGE_CHUNK_CHARS,
    max_chars: int = TTS_CHUNK_CHARS,
) -> list[str]:
    """Merge small neighbors into one chunk (up to *max_chars*) to save TTS/RVC work."""
    if not chunks:
        return []
    first = chunks[0].strip()
    if not first:
        rest = [c for c in chunks[1:] if c.strip()]
        if not rest:
            return []
        return merge_short_subchunks(rest, min_chars=min_chars, max_chars=max_chars)
    out: list[str] = []
    buf = first
    for nxt in chunks[1:]:
        n = nxt.strip()
        if not n:
            continue
        if (
            len(buf) + 1 + len(n) <= max_chars
            and (len(buf) < min_chars or len(n) < min_chars)
        ):
            buf = f"{buf} {n}"
        else:
            out.append(buf)
            buf = n
    out.append(buf)
    if len(out) >= 2 and len(out[-1]) < min_chars:
        a, b = out[-2], out[-1]
        if len(a) + 1 + len(b) <= max_chars:
            out[-2] = f"{a} {b}"
            out.pop()
    return out
