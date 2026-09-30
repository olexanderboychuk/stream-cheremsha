from __future__ import annotations

import os
import pathlib
import time as _time

import pytest


def _fixture(name: str) -> str:
    return (pathlib.Path(__file__).parent / "fixtures" / name).read_text(encoding="utf-8")


def test_candidate_langs_mapping():
    from stream_cheremsha.soundpad.myinstants import candidate_langs

    assert candidate_langs("uk") == ["ua", "en"]
    assert candidate_langs("UA ") == ["ua", "en"]
    assert candidate_langs("en") == ["en"]
    assert candidate_langs("") == ["en"]
    assert candidate_langs("xx") == ["en"]


def test_extract_instant_entries_from_fixture():
    from stream_cheremsha.soundpad.myinstants import LibrarySound, extract_instant_entries

    entries = extract_instant_entries(_fixture("myinstants_ua_index.html"))
    assert len(entries) >= 5
    assert all(isinstance(e, LibrarySound) for e in entries)
    assert all(e.path.startswith("/en/instant/") for e in entries)
    assert entries[0].title == "Slava Ukraini"


def test_extract_instant_entries_edge_cases():
    from stream_cheremsha.soundpad.myinstants import extract_instant_entries

    assert extract_instant_entries(None) == []
    assert extract_instant_entries("") == []
    one = '<a href="/en/instant/abc-1/">X</a>'
    out = extract_instant_entries(one)
    assert [e.path for e in out] == ["/en/instant/abc-1/"]
    # duplicates collapse; non-instant links are ignored
    dup = one + " " + one + ' <a href="/en/categories/funny/">F</a>'
    assert len(extract_instant_entries(dup)) == 1


def test_extract_mp3_url_from_fixture():
    from stream_cheremsha.soundpad.myinstants import extract_mp3_url

    url = extract_mp3_url(_fixture("myinstants_instant_page.html"))
    assert url.startswith("https://") and ".mp3" in url and "myinstants" in url


def test_extract_mp3_url_rejects_foreign_hosts_and_empty():
    from stream_cheremsha.soundpad.myinstants import extract_mp3_url

    with pytest.raises(ValueError):
        extract_mp3_url("")
    with pytest.raises(ValueError):
        extract_mp3_url('<a href="https://evil.example.com/x.mp3">x</a>')


class FakeResponse:
    def __init__(self, text="", content=b"", status=200):
        self.text = text
        self.content = content
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    """Canned responses per URL substring; records requested URLs."""

    def __init__(self, routes: dict[str, FakeResponse]):
        self.routes = routes
        self.requests: list[tuple[str, dict | None]] = []

    def get(self, url, headers=None):
        self.requests.append((url, headers))
        for key, resp in self.routes.items():
            if key in url:
                return resp
        raise AssertionError(f"no fake route for {url}")

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _client(tmp_path, routes, **kw):
    from stream_cheremsha.soundpad.myinstants import MyInstantsClient

    fake = FakeSession(routes)
    c = MyInstantsClient(session_factory=lambda: fake, cache_dir=tmp_path / "cache", **kw)
    return c, fake


def test_fetch_index_page_urls(tmp_path):
    index_html = _fixture("myinstants_ua_index.html")
    c, fake = _client(tmp_path, {"/en/index/ua/": FakeResponse(text=index_html)})
    assert len(c.fetch_index_entries("ua", 1)) >= 5
    assert fake.requests[0][0] == "https://www.myinstants.com/en/index/ua/"

    c2, fake2 = _client(tmp_path, {"/en/index/ua/?page=3": FakeResponse(text=index_html)})
    c2.fetch_index_entries("ua", 3)
    assert fake2.requests[0][0] == "https://www.myinstants.com/en/index/ua/?page=3"


def test_rate_limit_sleeps_between_requests(monkeypatch, tmp_path):
    import stream_cheremsha.soundpad.myinstants as mi

    sleeps: list[float] = []
    real_mono = _time.monotonic

    class _FakeTime:
        @staticmethod
        def monotonic():
            return real_mono()

        @staticmethod
        def sleep(s):
            sleeps.append(float(s))

    monkeypatch.setattr(mi, "time", _FakeTime)
    index_html = _fixture("myinstants_ua_index.html")
    c, fake = _client(
        tmp_path, {"/en/index/ua/": FakeResponse(text=index_html)}, min_interval_sec=0.3
    )
    # page 1 and page 2 are different cache keys -> two network calls back-to-back
    c.fetch_index_entries("ua", 1)
    c._index_cache.clear()
    c.fetch_index_entries("ua", 2)
    assert len(fake.requests) == 2
    assert sleeps, "expected a rate-limit sleep between requests"
    assert sleeps[0] >= 0.25


def test_resolve_mp3_url_uses_referer(tmp_path):
    page_html = _fixture("myinstants_instant_page.html")
    c, fake = _client(tmp_path, {"/en/instant/": FakeResponse(text=page_html)})
    url = c.resolve_mp3_url("/en/instant/some-sound-1/")
    assert ".mp3" in url
    assert fake.requests[0][1] is not None and "Referer" in fake.requests[0][1]


def test_resolve_mp3_url_rejects_bad_path(tmp_path):
    c, _ = _client(tmp_path, {})

    with pytest.raises(ValueError):
        c.resolve_mp3_url("https://evil.example.com/x")


def test_ensure_cached_mp3_downloads_once(tmp_path):
    mp3_url = "https://www.myinstantscdn.com/audio/abc.mp3"
    c, fake = _client(tmp_path, {mp3_url: FakeResponse(content=b"ID3fake-mp3-bytes")})
    p1 = c.ensure_cached_mp3(mp3_url)
    assert p1.is_file() and p1.read_bytes() == b"ID3fake-mp3-bytes"
    p2 = c.ensure_cached_mp3(mp3_url)  # cache hit: no second network call
    assert p2 == p1
    assert len(fake.requests) == 1


def test_ensure_cached_mp3_rejects_non_mp3(tmp_path):
    from stream_cheremsha.soundpad.myinstants import MyInstantsClient

    c = MyInstantsClient(session_factory=lambda: FakeSession({}), cache_dir=tmp_path / "c")

    with pytest.raises(ValueError):
        c.ensure_cached_mp3("https://www.myinstants.com/x.wav")


def test_enforce_cache_bounds_count(tmp_path):
    from stream_cheremsha.soundpad.myinstants import enforce_cache_bounds

    d = tmp_path / "cache"
    d.mkdir()
    now = 1_700_000_000
    for i, name in enumerate(["a.mp3", "b.mp3", "c.mp3", "d.mp3"]):
        p = d / name
        p.write_bytes(b"x" * (10 + i * 10))
        os.utime(p, (now + i, now + i))

    enforce_cache_bounds(d, max_files=2)
    assert sorted(p.name for p in d.glob("*.mp3")) == ["c.mp3", "d.mp3"]


def test_enforce_cache_bounds_bytes(tmp_path):
    from stream_cheremsha.soundpad.myinstants import enforce_cache_bounds

    d = tmp_path / "cache"
    d.mkdir()
    now = 1_700_000_000
    for i, name in enumerate(["a.mp3", "b.mp3", "c.mp3", "d.mp3"]):
        p = d / name
        p.write_bytes(b"x" * (10 + i * 10))  # sizes: 10, 20, 30, 40
        os.utime(p, (now + i, now + i))

    enforce_cache_bounds(d, max_files=10, max_bytes=50)
    assert [p.name for p in d.glob("*.mp3")] == ["d.mp3"]


def test_index_cache_hit_avoids_network(tmp_path):
    index_html = _fixture("myinstants_ua_index.html")
    c, fake = _client(tmp_path, {"/en/index/ua/": FakeResponse(text=index_html)})
    c.fetch_index_entries("ua", 1)
    c.fetch_index_entries("ua", 1)
    assert len(fake.requests) == 1


def test_index_cache_ttl_expiry(tmp_path):
    index_html = _fixture("myinstants_ua_index.html")
    c, fake = _client(
        tmp_path, {"/en/index/ua/": FakeResponse(text=index_html)}, index_ttl_sec=0.0
    )
    c.fetch_index_entries("ua", 1)
    c.fetch_index_entries("ua", 1)
    assert len(fake.requests) == 2


def test_index_cache_bounded_pages(tmp_path):
    index_html = _fixture("myinstants_ua_index.html")
    c, fake = _client(
        tmp_path, {"/en/index/ua/": FakeResponse(text=index_html)}, max_cached_pages=2
    )
    for page in (1, 2, 3):
        c.fetch_index_entries("ua", page)
    assert set(c._index_cache) == {("ua", 2), ("ua", 3)}
