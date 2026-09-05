"""Regression tests for the production-QSettings guard.

These tests prove that any attempt by test code to mutate the real user
settings scope fails loudly instead of wiping user data. See
tests/conftest.py for the guard itself.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QSettings

from tests.conftest import is_production_scope


def _production_settings() -> QSettings:
    # Built dynamically so the static tripwire below does not flag this file.
    return QSettings("stream-" + "cheremsha", "cher" + "emsha")


def test_guard_blocks_production_clear() -> None:
    with pytest.raises(AssertionError):
        _production_settings().clear()


def test_guard_blocks_production_remove() -> None:
    with pytest.raises(AssertionError):
        _production_settings().remove("overlays/layouts/config_json")


def test_guard_blocks_production_set_value() -> None:
    with pytest.raises(AssertionError):
        _production_settings().setValue("guard/selftest", "1")


def test_guard_allows_production_reads() -> None:
    s = _production_settings()
    # Reads must keep working (production code under test reads defaults).
    _ = s.value("overlays/layouts/config_json", "", str)


def test_guard_allows_isolated_scope_mutation(tmp_path) -> None:
    ini = tmp_path / "iso.ini"
    s = QSettings(str(ini), QSettings.Format.IniFormat)
    assert not is_production_scope(s)
    s.setValue("k", "v")
    s.sync()
    assert s.value("k", "", str) == "v"
    s.remove("k")
    s.clear()


def test_no_test_file_references_production_scope() -> None:
    """Static tripwire: no test may construct the production scope."""
    import pathlib

    tests_dir = pathlib.Path(__file__).resolve().parent
    offenders: list[str] = []
    needle_dq = '"' + "stream-cheremsha" + '", "' + "cheremsha" + '"'
    needle_sq = "'" + "stream-cheremsha" + "', '" + "cheremsha" + "'"
    for path in sorted(tests_dir.rglob("test_*.py")):
        if path.name == pathlib.Path(__file__).name:
            continue  # this file builds the scope dynamically (see above)
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if needle_dq in line or needle_sq in line:
                offenders.append(f"{path.name}:{lineno}: {stripped}")
    assert not offenders, "tests must not reference the production QSettings scope:\n" + "\n".join(
        offenders
    )
