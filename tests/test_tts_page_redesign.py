"""Regression tests for the TTS page visual redesign.

Covers only the new, isolated pieces:
- ``CheremshaSwitch`` keeps the QCheckBox two-state contract used by the
  TTS persistence wiring (setChecked/isChecked/toggled/stateChanged).
- The new TTS-page l10n keys exist in both locales.
- The TTS icon family (new + reused local SVGs) follows one visual system
  and renders through the same Qt SVG engine used by QWidget and QML.

Backend behavior, settings keys, and page wiring are unchanged and remain
covered by the existing TTS test modules.
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

from stream_cheremsha import l10n
from stream_cheremsha.ui.cheremsha_switch import CheremshaSwitch

_NEW_TTS_KEYS = (
    "audio.page_subtitle",
    "audio.status_ready",
    "audio.speak_test_primary",
    "audio.speak_stop",
    "audio.card_output_title",
    "audio.card_audio_levels",
    "audio.card_filter_title",
    "audio.tts_whitelist_caption",
    "audio.card_test_sub",
    "audio.card_lang_sub",
    "audio.card_filter_sub",
    "audio.card_voice_sub",
    "audio.card_output_sub",
    "audio.speak_author_inline_hint",
    "audio.strip_non_alpha_inline_hint",
    "audio.randomize_inline_hint",
    "audio.tts_whitelist_example",
    "audio.levels_section",
)


def test_new_tts_strings_exist_in_both_locales() -> None:
    for key in _NEW_TTS_KEYS:
        uk = l10n.tr("uk", key)
        en = l10n.tr("en", key)
        assert uk.strip(), f"empty uk for {key}"
        assert en.strip(), f"empty en for {key}"
        assert uk != key, f"missing uk for {key}"
        assert en != key, f"missing en for {key}"


@pytest.fixture(scope="module")
def _qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


def test_switch_starts_unchecked(_qt_app) -> None:
    sw = CheremshaSwitch()
    assert sw.isCheckable()
    assert not sw.isChecked()
    assert sw.sizeHint().width() == 38
    assert sw.sizeHint().height() == 21


def test_switch_set_checked_emits_checkbox_contract(_qt_app) -> None:
    sw = CheremshaSwitch()
    states: list[int] = []
    toggled: list[bool] = []
    sw.stateChanged.connect(states.append)
    sw.toggled.connect(toggled.append)
    sw.setChecked(True)
    assert sw.isChecked()
    assert states == [Qt.CheckState.Checked.value]
    assert toggled == [True]
    sw.setChecked(False)
    assert states == [Qt.CheckState.Checked.value, Qt.CheckState.Unchecked.value]
    assert toggled == [True, False]


def test_switch_click_toggles(_qt_app) -> None:
    sw = CheremshaSwitch()
    sw.click()
    assert sw.isChecked()
    sw.click()
    assert not sw.isChecked()


def test_switch_user_toggle_starts_short_slide_animation(_qt_app) -> None:
    sw = CheremshaSwitch()
    sw.setChecked(True)
    assert sw._anim.endValue() == 1.0
    assert sw._anim.duration() <= 120
    sw.setChecked(False)
    assert sw._anim.endValue() == 0.0


def test_switch_programmatic_set_snaps_without_signal(_qt_app) -> None:
    sw = CheremshaSwitch()
    sw.resize(sw.sizeHint())
    sw.blockSignals(True)
    sw.setChecked(True)
    sw.blockSignals(False)
    assert sw.isChecked()
    _ = sw.grab()
    assert sw._slide == 1.0


def test_switch_slide_animation_reaches_end_state(_qt_app) -> None:
    sw = CheremshaSwitch()
    sw.resize(sw.sizeHint())
    sw.setChecked(True)
    sw._anim.setCurrentTime(sw._anim.duration())
    assert sw._slide == pytest.approx(1.0)
    sw.setChecked(False)
    sw._anim.setCurrentTime(sw._anim.duration())
    assert sw._slide == pytest.approx(0.0)


_ICONS_DIR = (
    Path(__file__).resolve().parent.parent / "src" / "stream_cheremsha" / "assets" / "icons"
)

_NEW_TTS_ICONS = (
    "play.svg",
    "stop.svg",
    "filter.svg",
    "mic.svg",
    "sliders.svg",
    "shuffle.svg",
    "gear.svg",
    "chevron-down.svg",
    "x.svg",
)
_REUSED_TTS_ICONS = ("globe.svg", "web_volume.svg", "web_refresh.svg")

# Plain SVG subset that Qt's QWidget and QML renderers both support.
_QML_SAFE_TAGS = {"path", "line", "polyline", "polygon", "rect", "circle", "ellipse", "g"}


def _parse_icon(name: str) -> ET.Element:
    path = _ICONS_DIR / name
    assert path.is_file(), f"missing icon asset: {name}"
    return ET.fromstring(path.read_text(encoding="utf-8"))


def test_tts_icon_family_shares_one_visual_system() -> None:
    for name in (*_NEW_TTS_ICONS, *_REUSED_TTS_ICONS):
        root = _parse_icon(name)
        assert root.tag == "{http://www.w3.org/2000/svg}svg", name
        assert root.attrib.get("viewBox") == "0 0 24 24", name
        assert root.attrib.get("fill") == "none", name
        assert root.attrib.get("stroke-width") == "1.8", name
        assert root.attrib.get("stroke-linecap") == "round", name
        assert root.attrib.get("stroke-linejoin") == "round", name
        assert root.attrib.get("stroke", "").strip(), f"{name} must define a stroke color"
        assert "transparent" not in root.attrib.get("stroke", ""), name


def test_tts_icons_use_qml_safe_subset_only() -> None:
    forbidden = ("linearGradient", "radialGradient", "filter", "image", "text", "style")
    for name in _NEW_TTS_ICONS:
        text = (_ICONS_DIR / name).read_text(encoding="utf-8")
        for tag in forbidden:
            assert f"<{tag}" not in text, f"{name} uses QML-unsafe <{tag}>"
        root = ET.fromstring(text)
        for el in root.iter():
            tag = el.tag.replace("{http://www.w3.org/2000/svg}", "")
            assert tag in _QML_SAFE_TAGS or tag == "svg", f"{name}: unexpected <{tag}>"


def test_tts_icons_render_pixels(_qt_app) -> None:
    for name in (*_NEW_TTS_ICONS, *_REUSED_TTS_ICONS):
        renderer = QSvgRenderer(str(_ICONS_DIR / name))
        assert renderer.isValid(), name
        img = QImage(QSize(48, 48), QImage.Format.Format_ARGB32)
        img.fill(0)
        painter = QPainter(img)
        renderer.render(painter)
        painter.end()
        painted = 0
        for y in range(48):
            for x in range(48):
                if (img.pixel(x, y) >> 24) > 16:
                    painted += 1
        assert painted > 100, f"{name} renders almost nothing ({painted}px)"


def test_make_audio_card_returns_title_and_subtitle(_qt_app) -> None:
    from types import SimpleNamespace

    from stream_cheremsha.ui import main_window as mw

    fake = SimpleNamespace(_audio_icon_label=mw.MainWindow._audio_icon_label)
    card, body, title, sub = mw.MainWindow._make_audio_card(
        fake, "#38bdf8", "icons/globe.svg", "audio.card_lang_sub"
    )
    assert card is not None
    assert body.count() >= 0
    assert title.objectName() == "audioCardTitle"
    assert sub is not None
    assert sub.objectName() == "audioCardSub"
    _card2, _body2, _title2, sub2 = mw.MainWindow._make_audio_card(fake, "#38bdf8")
    assert sub2 is None


def test_switch_block_signals_suppresses_emissions(_qt_app) -> None:
    sw = CheremshaSwitch()
    states: list[int] = []
    sw.stateChanged.connect(states.append)
    sw.blockSignals(True)
    sw.setChecked(True)
    sw.blockSignals(False)
    assert sw.isChecked()
    assert states == []


def test_switch_paints_without_crash(_qt_app) -> None:
    sw = CheremshaSwitch()
    sw.resize(sw.sizeHint())
    sw.setChecked(True)
    _ = sw.grab()
    sw.setChecked(False)
    sw.setEnabled(False)
    _ = sw.grab()


def test_tts_rate_setting_contract_unchanged() -> None:
    from stream_cheremsha.ui import main_window as mw

    assert (mw._TTS_RATE_MIN, mw._TTS_RATE_MAX, mw._TTS_RATE_DEFAULT) == (50, 200, 100)
    assert mw._SETTINGS_TTS_RATE_PERCENT == "tts/rate_percent"
