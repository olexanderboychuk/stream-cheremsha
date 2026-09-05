"""Pytest fixtures for the whole tests/ tree.

Safety policy: no test may ever mutate the production QSettings scope
(organization "stream-cheremsha", application "cheremsha") — that scope
holds the user's real app settings on disk/registry. A past incident wiped
user settings because a test called .clear() on the production scope.

The autouse fixture below turns any such attempt into a loud test failure
instead of silent data loss. Tests must use isolated scopes instead, e.g.
QSettings("stream-cheremsha-test", "<test-name>") or an IniFormat temp file.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QSettings

_PROD_ORG = "stream-cheremsha"
_PROD_APP = "cheremsha"


def is_production_scope(settings: QSettings) -> bool:
    try:
        return settings.organizationName() == _PROD_ORG and settings.applicationName() == _PROD_APP
    except Exception:
        return False


def _blocked(op: str):
    raise AssertionError(
        f"tests must never call QSettings.{op}() on the production scope "
        f"({_PROD_ORG!r}/{_PROD_APP!r}): use an isolated test scope instead"
    )


@pytest.fixture(autouse=True)
def _guard_production_qsettings(monkeypatch):
    orig_clear = QSettings.clear
    orig_remove = QSettings.remove
    orig_set_value = QSettings.setValue

    def clear(self):
        if is_production_scope(self):
            _blocked("clear")
        return orig_clear(self)

    def remove(self, key):
        if is_production_scope(self):
            _blocked("remove")
        return orig_remove(self, key)

    def setValue(self, key, value):
        if is_production_scope(self):
            _blocked("setValue")
        return orig_set_value(self, key, value)

    monkeypatch.setattr(QSettings, "clear", clear)
    monkeypatch.setattr(QSettings, "remove", remove)
    monkeypatch.setattr(QSettings, "setValue", setValue)
