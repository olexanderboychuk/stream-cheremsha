"""Regression: Actions QML bridge must not wipe rules on empty or invalid saves."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QApplication, QWidget

from stream_cheremsha.actions.models import RuleV1


@pytest.fixture()
def qapplication() -> QApplication:
    app = QApplication.instance()
    if app is None:
        return QApplication([])
    return app


@pytest.fixture()
def spy_platform_and_monkeypatch(monkeypatch: pytest.MonkeyPatch):
    import stream_cheremsha.ui.actions_qml_api as mod

    calls: list[tuple[str, str]] = []

    def _spy(p: str, ak: str, *args: object, **kwargs: object) -> None:
        calls.append((p, ak))

    monkeypatch.setattr(mod, "save_rules", _spy)
    monkeypatch.setattr(mod, "save_rules_bundle", _spy)
    return calls, mod


@pytest.mark.usefixtures("qapplication")
def test_save_rules_json_empty_payload_does_not_clear(
    spy_platform_and_monkeypatch,
) -> None:
    calls, mod = spy_platform_and_monkeypatch
    api = mod.ActionsQmlApi(QObject())
    api.saveRulesJson("twitch", "mychannel", "")
    api.saveRulesJson("twitch", "mychannel", "  \n\t")
    assert calls == []


@pytest.mark.usefixtures("qapplication")
def test_save_rules_json_whitespace_only_does_not_clear(
    spy_platform_and_monkeypatch,
) -> None:
    calls, mod = spy_platform_and_monkeypatch
    api = mod.ActionsQmlApi(QObject())
    api.saveRulesJson("  twitch ", " x ", " ")
    assert calls == []


@pytest.mark.usefixtures("qapplication")
def test_save_rules_ui_layout_skipped_when_rules_corrupt(
    monkeypatch: pytest.MonkeyPatch,
    spy_platform_and_monkeypatch,
) -> None:
    calls, mod = spy_platform_and_monkeypatch

    def _boom(_p: str, _ak: str, **kwargs: object) -> list[RuleV1]:
        raise ValueError("corrupt")

    monkeypatch.setattr(mod, "load_rules", _boom)
    api = mod.ActionsQmlApi(QObject())
    api.saveRulesUiLayoutJson("twitch", "ch", "{}")
    assert calls == []


class _ReloadStub(QWidget):
    """Minimal QObject parent with MainWindow-compatible reload hook."""

    def __init__(self) -> None:
        super().__init__()
        self.reload_calls: list[tuple[str, str]] = []

    def _actions_reload_scope(self, p: str, ak: str) -> None:  # noqa: SLF001
        self.reload_calls.append((p, ak))


@pytest.mark.usefixtures("qapplication")
def test_save_rules_json_explicit_empty_list_calls_bundle_with_empty_rules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import stream_cheremsha.ui.actions_qml_api as mod

    bundles: list[list[RuleV1]] = []

    def _spy_bundle(
        p: str,
        ak: str,
        rules: list[RuleV1],
        layout_in: object,
        **kwargs: object,
    ) -> None:
        bundles.append(list(rules))

    monkeypatch.setattr(mod, "save_rules_bundle", _spy_bundle)

    stub = _ReloadStub()
    api = mod.ActionsQmlApi(stub)
    api.saveRulesJson("twitch", "ch", '{"schema_version":1,"rules":[]}')
    assert bundles == [[]]
    assert stub.reload_calls == [("twitch", "ch")]
