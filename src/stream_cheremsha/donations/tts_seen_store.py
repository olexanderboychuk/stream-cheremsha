"""Persist donation ids already covered by TTS (survives app restarts)."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from PySide6.QtCore import QStandardPaths

logger = logging.getLogger(__name__)

KEY_DONATIK = "donatik"
KEY_DONATELLO = "donatello"
_MAX_IDS = 4000
_FILENAME = "donation_tts_seen.json"


def _base_dir() -> Path:
    loc = QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)
    d = Path(loc) / "stream-cheremsha"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _path() -> Path:
    return _base_dir() / _FILENAME


def load_ids(provider_key: str) -> set[str]:
    path = _path()
    if not path.is_file():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError) as e:
        logger.warning("donation_tts_seen: load failed: %s", e)
        return set()
    if not isinstance(data, dict):
        return set()
    raw = data.get(provider_key)
    if not isinstance(raw, list):
        return set()
    out: set[str] = set()
    for x in raw:
        if isinstance(x, str):
            s = x.strip()
            if s:
                out.add(s)
    return out


def _trim_list(ids: set[str]) -> list[str]:
    lst = sorted(ids)
    if len(lst) > _MAX_IDS:
        return lst[-_MAX_IDS:]
    return lst


def save_ids(provider_key: str, ids: set[str]) -> None:
    path = _path()
    all_data: dict[str, Any] = {}
    if path.is_file():
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(parsed, dict):
                all_data = parsed
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError):
            all_data = {}
    all_data[provider_key] = _trim_list(ids)
    tmp = path.with_suffix(".tmp")
    try:
        txt = json.dumps(all_data, ensure_ascii=False, separators=(",", ":")) + "\n"
        tmp.write_text(txt, encoding="utf-8")
        os.replace(tmp, path)
    except OSError as e:
        logger.warning("donation_tts_seen: save failed: %s", e)
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def clear_provider(provider_key: str) -> None:
    path = _path()
    if not path.is_file():
        return
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        return
    if not isinstance(parsed, dict):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        return
    parsed.pop(provider_key, None)
    if not parsed:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        return
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(
            json.dumps(parsed, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        os.replace(tmp, path)
    except OSError as e:
        logger.warning("donation_tts_seen: clear_provider save failed: %s", e)
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
