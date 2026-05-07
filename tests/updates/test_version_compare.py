import pytest

from stream_cheremsha.updates.client import is_newer_version


def test_is_newer_version_compares_semver() -> None:
    assert is_newer_version("0.1.9", "0.1.8") is True
    assert is_newer_version("0.1.8", "0.1.8") is False
    assert is_newer_version("0.1.7", "0.1.8") is False


def test_is_newer_version_handles_multi_digit_patch() -> None:
    assert is_newer_version("0.1.10", "0.1.9") is True


def test_is_newer_version_rejects_invalid_versions() -> None:
    with pytest.raises(ValueError):
        is_newer_version("0.1", "0.1.8")

