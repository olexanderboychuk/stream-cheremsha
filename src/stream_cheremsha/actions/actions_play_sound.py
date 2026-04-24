from __future__ import annotations

from pathlib import Path

from stream_cheremsha.domain.protocols import AudioSink


async def play_sound_from_file(path: str, *, sink: AudioSink) -> None:
    p = Path((path or "").strip())
    if not p:
        raise ValueError("file_path is required")
    if p.suffix.lower() != ".mp3":
        raise ValueError("Only .mp3 is supported for now")
    if not p.is_file():
        raise FileNotFoundError(str(p))
    data = p.read_bytes()
    await sink.play_mp3(data)

