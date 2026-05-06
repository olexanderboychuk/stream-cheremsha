from __future__ import annotations

import os
from pathlib import Path

from stream_cheremsha.domain.protocols import AudioSink


def sound_file_dedupe_key(raw_path: str) -> str:
    """Stable key for the same on-disk .mp3 (shared across all action engines on one sink)."""
    s = (raw_path or "").strip()
    if not s:
        return ""
    p = Path(s).expanduser()
    try:
        return os.path.normcase(str(p.resolve(strict=False)))
    except OSError:
        return os.path.normcase(str(p))


async def play_sound_from_file(
    path: str,
    *,
    sink: AudioSink,
    volume_percent: int = 100,
    skip_queue_if_same: bool = False,
) -> None:
    p = Path((path or "").strip())
    if not p:
        raise ValueError("file_path is required")
    if p.suffix.lower() != ".mp3":
        raise ValueError("Only .mp3 is supported for now")
    if not p.is_file():
        raise FileNotFoundError(str(p))
    data = p.read_bytes()
    vp = int(volume_percent)
    if vp < 0:
        vp = 0
    if vp > 100:
        vp = 100
    linear = vp / 100.0

    dedupe_key = sound_file_dedupe_key(str(p)) if skip_queue_if_same else ""
    play_deduped = getattr(sink, "play_mp3_with_volume_deduped", None)
    if dedupe_key and callable(play_deduped):
        ok = await play_deduped(data, linear, dedupe_key=dedupe_key)
        if not ok:
            return
        return

    # Optional sink volume control (QtAudioSink supports it).
    #
    # IMPORTANT: set_volume alone is racy when multiple playbacks are scheduled concurrently,
    # because sinks typically serialize audio with an internal lock. Another action can change
    # sink volume while the first action is waiting to acquire that lock, causing the first
    # clip to play at the wrong volume. Prefer an atomic method if the sink provides one.
    play_with_volume = getattr(sink, "play_mp3_with_volume", None)
    if callable(play_with_volume):
        await play_with_volume(data, linear)
        return

    get_vol = getattr(sink, "get_volume", None)
    set_vol = getattr(sink, "set_volume", None)
    prev: float | None = None
    if callable(set_vol):
        if callable(get_vol):
            try:
                prev = float(get_vol())
            except (TypeError, ValueError):
                prev = None
        set_vol(linear)
    try:
        await sink.play_mp3(data)
    finally:
        if callable(set_vol):
            set_vol(prev if prev is not None else 1.0)
