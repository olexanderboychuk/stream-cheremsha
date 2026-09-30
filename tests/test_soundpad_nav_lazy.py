from __future__ import annotations

import ast
import pathlib

MW = pathlib.Path("src/stream_cheremsha/ui/main_window.py").read_text()


def test_index_and_qml_set():
    assert "_IX_SOUNDPAD = 11" in MW
    assert "_IX_SOUNDPAD" in MW and "_QML_STACK_INDICES" in MW


def test_lazy_no_eager_source():
    tree = ast.parse(MW)
    src = ast.get_source_segment(
        MW,
        next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_build_ui"),
    )
    assert src is not None and "SoundpadView.qml" not in src


def test_load_branch_exists():
    assert "SoundpadView.qml" in MW
    assert '"_qml_soundpad"' in MW or "'_qml_soundpad'" in MW or "_qml_soundpad" in MW


def test_icon_exists():
    assert pathlib.Path("src/stream_cheremsha/assets/nav/soundpad.svg").is_file()


def test_qml_files_exist():
    assert pathlib.Path("src/stream_cheremsha/qml/SoundpadView.qml").is_file()
    assert pathlib.Path("src/stream_cheremsha/qml/components/CheremshaSoundCard.qml").is_file()
    assert pathlib.Path("src/stream_cheremsha/qml/components/CheremshaKeycap.qml").is_file()


def test_soundpad_api_locale_wiring():
    i_lazy = MW.find("def _soundpad_api_lazy")
    i_retr = MW.find("def _retranslate_ui")
    assert i_lazy != -1 and i_retr > i_lazy, "both methods must exist"
    lazy_src = MW[i_lazy:i_retr]
    retr_src = MW[i_retr:]
    # Lazy creation applies the current locale...
    assert "set_locale(self._locale)" in lazy_src
    # ...and a settings language switch re-applies it to the cached api.
    assert "_soundpad_api" in retr_src and "set_locale(self._locale)" in retr_src
