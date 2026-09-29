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
