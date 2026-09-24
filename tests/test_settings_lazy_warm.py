"""Settings tab lazy load + splash warm regression (no QApplication).

Static source-structure + l10n checks, in the style of
test_production_qsettings_guard.py: no MainWindow / QApplication is
ever constructed and no production QSettings scope is touched.
"""

from __future__ import annotations

import ast
import pathlib

from stream_cheremsha import l10n

MW = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "stream_cheremsha"
    / "ui"
    / "main_window.py"
)


def _src() -> str:
    return MW.read_text(encoding="utf-8")


def _method_src(name: str) -> str:
    tree = ast.parse(_src())
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return ast.get_source_segment(_src(), node) or ""
    return ""


def test_splash_settings_l10n_both_locales() -> None:
    uk = l10n.tr("uk", "splash.settings")
    en = l10n.tr("en", "splash.settings")
    assert uk.strip()
    assert en.strip()
    assert "налаштувань" in uk.lower()
    assert "settings" in en.lower()


def test_settings_not_built_eagerly_in_build_ui() -> None:
    build_ui = _method_src("_build_ui")
    assert "self._build_settings_tab()" not in build_ui
    assert "self._settings_placeholder" in build_ui
    assert "self._stack.addWidget(self._settings_placeholder)" in build_ui


def test_ensure_settings_builds_once_and_loads_fields() -> None:
    ensure = _method_src("_ensure_settings_widgets")
    assert "if self._settings_page is not None:" in ensure
    assert "return self._settings_page" in ensure
    assert "self._build_settings_tab()" in ensure
    assert "self._settings_fields_loaded" in ensure
    assert "self._load_settings_fields()" in ensure
    assert "self._stack.removeWidget(placeholder)" in ensure
    assert "self._stack.insertWidget(self._IX_SETTINGS, page)" in ensure
    assert "placeholder.deleteLater()" in ensure
    assert "self._stack.setCurrentWidget(current_widget)" in ensure
    assert "self._settings_placeholder = None" in ensure


def test_warm_secondary_pages_includes_settings_last() -> None:
    warm = _method_src("warm_secondary_pages")
    assert '(self._IX_SETTINGS, "splash.settings")' in warm
    assert warm.index('"splash.docks"') < warm.index('"splash.settings"')
    branch_start = warm.index("if qml_index == self._IX_SETTINGS:")
    branch_end = warm.index("self._load_qml_page(qml_index)", branch_start)
    branch = warm[branch_start:branch_end]
    assert "self._ensure_settings_widgets()" in branch
    assert "self._load_qml_page" not in branch


def test_set_main_page_ensures_settings_synchronously() -> None:
    set_page = _method_src("_set_main_page")
    start = set_page.index("if index == self._IX_SETTINGS:")
    end = set_page.index("if index == self._IX_AUDIO", start)
    branch = set_page[start:end]
    assert "self._ensure_settings_widgets()" in branch
    assert "singleShot" not in branch
    assert "veil" not in branch


def test_settings_texts_and_fields_guarded_prebuild() -> None:
    guard = 'if getattr(self, "_settings_page", None) is None:'
    texts = _method_src("_apply_settings_tab_texts")
    fields = _method_src("_load_settings_fields")
    assert guard in texts
    assert texts.index(guard) < texts.index("self._lbl_locale.setText")
    assert guard in fields
    assert fields.index(guard) < fields.index("env_cid")


def test_settings_excluded_from_qml_indices() -> None:
    src = _src()
    start = src.index("_QML_STACK_INDICES =")
    qml_set = src[start:src.index(")", start)]
    assert "_IX_SETTINGS" not in qml_set
    assert "self._qml_pages_loaded.add(self._IX_SETTINGS)" not in src
    assert "self._qml_pages_loaded.add(_IX_SETTINGS)" not in src
