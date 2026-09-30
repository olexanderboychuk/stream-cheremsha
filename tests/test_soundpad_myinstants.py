from __future__ import annotations

import pathlib

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
