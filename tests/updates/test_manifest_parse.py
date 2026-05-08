import json

import pytest

from stream_cheremsha.updates.models import LatestManifest


def test_latest_manifest_parses_valid_schema_1() -> None:
    raw = json.dumps(
        {
            "schema": 1,
            "version": "0.1.9",
            "tag": "v0.1.9",
            "published_at": "2026-05-07T12:34:56Z",
            "platforms": {
                "windows": {
                    "installer": {"url": "https://example.com/setup.exe", "sha256": "a" * 64},
                    "portable_zip": {"url": "https://example.com/app.zip", "sha256": "b" * 64},
                },
                "linux": {"releases_url": "https://example.com/releases/tag/v0.1.9"},
            },
            "changelog_url": "https://example.com/CHANGELOG.md",
        }
    )

    m = LatestManifest.from_json(raw)
    assert m.schema == 1
    assert m.version == "0.1.9"
    assert m.tag == "v0.1.9"
    assert m.platforms.windows is not None
    assert m.platforms.windows.installer.url == "https://example.com/setup.exe"
    assert m.platforms.windows.installer.sha256 == "a" * 64
    assert m.platforms.windows.portable_zip is not None
    assert m.platforms.linux is not None


def test_latest_manifest_rejects_schema_mismatch() -> None:
    raw = json.dumps(
        {
            "schema": 2,
            "version": "0.1.9",
            "tag": "v0.1.9",
            "published_at": "2026-05-07T12:34:56Z",
            "platforms": {"linux": {"releases_url": "https://example.com/releases/tag/v0.1.9"}},
            "changelog_url": "https://example.com/CHANGELOG.md",
        }
    )
    with pytest.raises(ValueError, match="schema"):
        LatestManifest.from_json(raw)
