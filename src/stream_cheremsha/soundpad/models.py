from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

ALLOWED_AUDIO_SUFFIXES = frozenset({".mp3", ".wav", ".ogg"})


class PlaybackMode(StrEnum):
    RESTART = "restart"
    OVERLAP = "overlap"
    REPLACE = "replace"
    QUEUE = "queue"


class TriggerKind(StrEnum):
    HOTKEY = "hotkey"
    CHAT_COMMAND = "chat_command"
    GIFT = "gift"
    DONATION = "donation"
    CUSTOM = "custom"


@dataclass(slots=True)
class TriggerConfig:
    kind: TriggerKind = TriggerKind.HOTKEY
    value: str = ""
    permission: str = "anyone"
    cooldown_sec: float = 0.0


@dataclass(slots=True)
class SoundEntry:
    id: str
    name: str
    file_path: str
    category: str = "Custom"
    hotkey: str = ""
    volume: float = 1.0
    playback_mode: PlaybackMode = PlaybackMode.RESTART
    cooldown_sec: float = 0.0
    triggers: tuple[TriggerConfig, ...] = ()
    waveform_peaks: tuple[float, ...] = ()
    duration_sec: float = 0.0
    play_count: int = 0
    last_played_at: str = ""
    order: int = 0
    enabled: bool = True
    monitor: bool = True
    stream_out: bool = True


def normalize_hotkey(raw: str) -> str:
    parts = [p.strip() for p in str(raw or "").replace(" ", "+").split("+") if p.strip()]
    fixed: list[str] = []
    for p in parts:
        u = p.upper()
        if u in ("CTRL", "CONTROL"):
            fixed.append("Ctrl")
        elif u == "ALT":
            fixed.append("Alt")
        elif u == "SHIFT":
            fixed.append("Shift")
        elif u.startswith("F") and u[1:].isdigit():
            fixed.append(u)
        elif len(u) == 1:
            fixed.append(u)
        else:
            fixed.append(p.strip().capitalize())
    # Canonical order: Ctrl, Alt, Shift, then main key.
    rank = {"Ctrl": 0, "Alt": 1, "Shift": 2}
    mods = sorted([x for x in fixed if x in rank], key=lambda x: rank[x])
    mains = [x for x in fixed if x not in rank]
    return "+".join(mods + mains)


def validate_sound_entry(entry: SoundEntry) -> list[str]:
    errs: list[str] = []
    if not entry.id.strip():
        errs.append("id is required")
    if not entry.name.strip():
        errs.append("name is required")
    if not str(entry.file_path or "").strip():
        errs.append("file_path is required")
    try:
        v = float(entry.volume)
    except (TypeError, ValueError):
        errs.append("volume must be a number 0.0-1.0")
    else:
        if not 0.0 <= v <= 1.0:
            errs.append("volume must be 0.0-1.0")
    try:
        cd = float(entry.cooldown_sec)
    except (TypeError, ValueError):
        errs.append("cooldown_sec must be >= 0")
    else:
        if cd < 0:
            errs.append("cooldown_sec must be >= 0")
    if float(entry.duration_sec or 0.0) < 0:
        errs.append("duration_sec must be >= 0")
    if int(entry.play_count or 0) < 0:
        errs.append("play_count must be >= 0")
    return errs
