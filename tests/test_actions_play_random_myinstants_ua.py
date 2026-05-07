from __future__ import annotations

import os
from pathlib import Path

from stream_cheremsha.actions.actions_play_random_myinstants_ua import (
    _enforce_cache_max_files,
    extract_instant_page_paths_from_ua_index_html,
    extract_mp3_url_from_instant_page_html,
)


def _read_fixture(name: str) -> str:
    fixtures_dir = Path(__file__).parent / "fixtures"
    return (fixtures_dir / name).read_text(encoding="utf-8")


def test_extract_instant_page_paths_from_ua_index_html() -> None:
    html = _read_fixture("myinstants_ua_index.html")
    paths = extract_instant_page_paths_from_ua_index_html(html)
    assert len(paths) >= 5
    assert all(p.startswith("/en/instant/") for p in paths)


def test_extract_mp3_url_from_instant_page_html() -> None:
    html = _read_fixture("myinstants_instant_page.html")
    url = extract_mp3_url_from_instant_page_html(html)
    assert url.startswith("https://")
    assert url.endswith(".mp3")
    assert "myinstants" in url


def test_enforce_cache_max_files(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    files: list[Path] = []
    for i in range(5):
        p = cache_dir / f"{i}.mp3"
        p.write_bytes(b"fake-mp3")
        files.append(p)

    # Ensure deterministic mtimes: newest should be "4.mp3".
    now = 1_700_000_000
    for i, p in enumerate(files):
        t = now + i
        os.utime(p, (t, t))

    _enforce_cache_max_files(cache_dir, max_files=2)

    remaining = sorted(p.name for p in cache_dir.glob("*.mp3") if p.is_file())
    assert len(remaining) == 2
