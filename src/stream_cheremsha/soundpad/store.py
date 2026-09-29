from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import asdict
from pathlib import Path

from PySide6.QtCore import QSettings

from stream_cheremsha.soundpad.models import (
    PlaybackMode,
    SoundEntry,
    TriggerConfig,
    TriggerKind,
    normalize_hotkey,
    validate_sound_entry,
)

_GROUP = "soundpad/"
_K_ENTRIES = _GROUP + "entries_json"
_K_VOL = _GROUP + "global_volume"
_K_MON = _GROUP + "monitor"
_K_STREAM = _GROUP + "stream_out"
_K_DEV = _GROUP + "output_device"


def _entry_to_dict(e: SoundEntry) -> dict:
    d = asdict(e)
    d["playback_mode"] = str(
        e.playback_mode.value if isinstance(e.playback_mode, PlaybackMode) else e.playback_mode
    )
    d["triggers"] = [
        {
            "kind": str(t.kind.value if isinstance(t.kind, TriggerKind) else t.kind),
            "value": t.value,
            "permission": t.permission,
            "cooldown_sec": float(t.cooldown_sec),
        }
        for t in (e.triggers or ())
    ]
    d["waveform_peaks"] = [float(x) for x in (e.waveform_peaks or ())]
    return d


def _entry_from_dict(d: dict) -> SoundEntry:
    trigs: list[TriggerConfig] = []
    for t in d.get("triggers") or []:
        try:
            kind = TriggerKind(str(t.get("kind", "hotkey")))
        except ValueError:
            kind = TriggerKind.CUSTOM
        trigs.append(
            TriggerConfig(
                kind=kind,
                value=str(t.get("value", "")),
                permission=str(t.get("permission", "anyone")),
                cooldown_sec=float(t.get("cooldown_sec", 0.0) or 0.0),
            )
        )
    try:
        mode = PlaybackMode(str(d.get("playback_mode", "restart")))
    except ValueError:
        mode = PlaybackMode.RESTART
    return SoundEntry(
        id=str(d.get("id", "")),
        name=str(d.get("name", "")),
        file_path=str(d.get("file_path", "")),
        category=str(d.get("category", "Custom") or "Custom"),
        hotkey=normalize_hotkey(str(d.get("hotkey", "") or "")),
        volume=float(d.get("volume", 1.0)),
        playback_mode=mode,
        cooldown_sec=float(d.get("cooldown_sec", 0.0) or 0.0),
        triggers=tuple(trigs),
        waveform_peaks=tuple(float(x) for x in (d.get("waveform_peaks") or ())),
        duration_sec=float(d.get("duration_sec", 0.0) or 0.0),
        play_count=int(d.get("play_count", 0) or 0),
        last_played_at=str(d.get("last_played_at", "") or ""),
        order=int(d.get("order", 0) or 0),
        enabled=bool(d.get("enabled", True)),
        monitor=bool(d.get("monitor", True)),
        stream_out=bool(d.get("stream_out", True)),
    )


class SoundpadStore:
    def __init__(
        self, settings: QSettings | None = None, root_dir: Path | str | None = None
    ) -> None:
        self._settings = settings or QSettings("stream-cheremsha", "cheremsha")
        if root_dir is None:
            from PySide6.QtCore import QStandardPaths

            base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
            self._root = Path(base or ".") / "soundpad"
        else:
            rd = Path(root_dir)
            self._root = rd if rd.name == "soundpad" else rd / "soundpad"
        self._entries: dict[str, SoundEntry] = {}
        self._load()

    @property
    def library_dir(self) -> Path:
        p = self._root / "sounds"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _load(self) -> None:
        raw = self._settings.value(_K_ENTRIES, "[]", str)
        try:
            items = json.loads(raw or "[]")
        except (ValueError, TypeError):
            items = []
        self._entries = {}
        for d in items if isinstance(items, list) else []:
            try:
                e = _entry_from_dict(d)
            except (ValueError, TypeError, KeyError):
                continue
            if e.id:
                self._entries[e.id] = e

    def _save(self) -> None:
        payload = json.dumps(
            [_entry_to_dict(e) for e in self._entries.values()], ensure_ascii=False
        )
        self._settings.setValue(_K_ENTRIES, payload)
        self._settings.sync()

    def list_all(self) -> list[SoundEntry]:
        return sorted(self._entries.values(), key=lambda e: (int(e.order), e.name.lower()))

    def get(self, sound_id: str) -> SoundEntry | None:
        return self._entries.get(sound_id)

    def next_order(self) -> int:
        return max((int(e.order) for e in self._entries.values()), default=-1) + 1

    def upsert(self, entry: SoundEntry) -> list[str]:
        entry.hotkey = normalize_hotkey(entry.hotkey or "")
        errs = validate_sound_entry(entry)
        if errs:
            return errs
        self._entries[entry.id] = entry
        self._save()
        return []

    def remove(self, sound_id: str) -> bool:
        if sound_id not in self._entries:
            return False
        del self._entries[sound_id]
        self._save()
        return True

    def duplicate(self, sound_id: str) -> SoundEntry | None:
        src = self.get(sound_id)
        if src is None:
            return None
        import copy

        dup = copy.deepcopy(src)
        dup.id = f"{src.id}-copy-{uuid.uuid4().hex[:6]}"
        dup.name = f"{src.name} (копія)"
        dup.hotkey = ""
        dup.play_count = 0
        dup.last_played_at = ""
        dup.order = self.next_order()
        self._entries[dup.id] = dup
        self._save()
        return dup

    def move(self, sound_id: str, new_category: str) -> bool:
        e = self.get(sound_id)
        if e is None or not str(new_category or "").strip():
            return False
        e.category = str(new_category).strip()
        self._save()
        return True

    def reorder(self, ordered_ids: list[str]) -> None:
        for i, sid in enumerate(ordered_ids):
            if sid in self._entries:
                self._entries[sid].order = i
        self._save()

    def search(self, query: str) -> list[SoundEntry]:
        q = str(query or "").strip().lower()
        if not q:
            return self.list_all()
        out: list[SoundEntry] = []
        for e in self.list_all():
            if (
                q in e.name.lower()
                or q in e.category.lower()
                or q in normalize_hotkey(e.hotkey).lower()
            ):
                out.append(e)
        return out

    def by_category(self, category: str) -> list[SoundEntry]:
        if not category or category == "Усі":
            return self.list_all()
        return [e for e in self.list_all() if e.category == category]

    def categories(self) -> list[str]:
        cats = sorted({e.category for e in self._entries.values() if e.category})
        return ["Усі", *cats]

    def resolve_library_path(self, src_path: str | Path, sound_id: str) -> Path:
        src = Path(str(src_path))
        safe = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in str(sound_id))[:48]
        safe = safe or "sound"
        dest = self.library_dir / f"{safe}{src.suffix.lower()}"
        need_copy = True
        if dest.exists():
            try:
                need_copy = src.resolve() != dest.resolve()
            except OSError:
                need_copy = True
        if need_copy:
            try:
                shutil.copy2(src, dest)
            except OSError:
                return src
        return dest

    def global_volume(self) -> float:
        try:
            return max(0.0, min(1.0, float(self._settings.value(_K_VOL, 0.78, float))))
        except (TypeError, ValueError):
            return 0.78

    def set_global_volume(self, v: float) -> None:
        self._settings.setValue(_K_VOL, max(0.0, min(1.0, float(v))))
        self._settings.sync()

    def monitor(self) -> bool:
        try:
            return bool(self._settings.value(_K_MON, True))
        except (TypeError, ValueError):
            return True

    def set_monitor(self, b: bool) -> None:
        self._settings.setValue(_K_MON, bool(b))
        self._settings.sync()

    def stream_out(self) -> bool:
        try:
            return bool(self._settings.value(_K_STREAM, True))
        except (TypeError, ValueError):
            return True

    def set_stream_out(self, b: bool) -> None:
        self._settings.setValue(_K_STREAM, bool(b))
        self._settings.sync()
