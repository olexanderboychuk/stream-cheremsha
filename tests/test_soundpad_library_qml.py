from __future__ import annotations

from pathlib import Path

QML = Path(__file__).resolve().parents[1] / "src" / "stream_cheremsha" / "qml"


def _read(rel: str) -> str:
    return (QML / rel).read_text(encoding="utf-8")


def test_modal_has_preferred_width():
    src = _read("components/CheremshaModal.qml")
    assert "property real preferredWidth" in src
    assert "modal.preferredWidth" in src
