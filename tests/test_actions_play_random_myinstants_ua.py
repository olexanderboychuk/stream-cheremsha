from __future__ import annotations

import os
import random
from pathlib import Path

from stream_cheremsha.actions.actions_play_random_myinstants_ua import (
    _enforce_cache_max_files,
    extract_instant_entries_from_ua_index_html,
    extract_instant_page_paths_from_ua_index_html,
    extract_mp3_url_from_instant_page_html,
    pick_random_instant_path,
)


def _read_fixture(name: str) -> str:
    fixtures_dir = Path(__file__).parent / "fixtures"
    return (fixtures_dir / name).read_text(encoding="utf-8")


def test_extract_instant_page_paths_from_ua_index_html() -> None:
    html = _read_fixture("myinstants_ua_index.html")
    entries = extract_instant_entries_from_ua_index_html(html)
    assert len(entries) >= 5
    paths = extract_instant_page_paths_from_ua_index_html(html)
    assert len(paths) >= 5
    assert all(p.startswith("/en/instant/") for p in paths)
    assert extract_instant_page_paths_from_ua_index_html(None) == []
    assert extract_instant_page_paths_from_ua_index_html("") == []
    one = '<a href = "/en/instant/abc/">X</a>'
    assert extract_instant_page_paths_from_ua_index_html(one) == ["/en/instant/abc/"]


def test_extract_mp3_url_from_instant_page_html() -> None:
    html = _read_fixture("myinstants_instant_page.html")
    url = extract_mp3_url_from_instant_page_html(html)
    assert url.startswith("https://")
    assert ".mp3" in url
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
    assert remaining == ["3.mp3", "4.mp3"]


def test_pick_random_instant_path_is_deterministic() -> None:
    paths = [
        "/en/instant/a/",
        "/en/instant/b/",
        "/en/instant/c/",
        "/en/instant/d/",
    ]
    rng = random.Random(123)
    assert pick_random_instant_path(paths, rng=rng) == "/en/instant/a/"
