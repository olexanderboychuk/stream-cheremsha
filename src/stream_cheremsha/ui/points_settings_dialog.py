"""Dialog for fine-grained points economy settings."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from stream_cheremsha.domain.points import PointsConfig
from stream_cheremsha.ui.app_styles import settings_panel_stylesheet

# QSettings keys (shared with MainWindow).
SETTINGS_POINTS_ENABLED = "points/enabled"
SETTINGS_POINTS_SONG_COST = "points/song_cost"
SETTINGS_POINTS_PER_COIN = "points/per_coin"
SETTINGS_POINTS_LIKES_PER_POINT = "points/likes_per_point"
SETTINGS_POINTS_PER_SHARE = "points/per_share"
SETTINGS_POINTS_PER_FOLLOW = "points/per_follow"
SETTINGS_POINTS_WATCH_PER_INTERVAL = "points/watch_points_per_interval"
SETTINGS_POINTS_WATCH_INTERVAL_MIN = "points/watch_interval_minutes"

TrFn = Callable[[str, object], str]


@dataclass(slots=True)
class _SpinField:
    key: str
    spin: QSpinBox
    default: int
    minimum: int
    maximum: int


def load_points_config_from_settings(settings) -> PointsConfig:
    """Build a :class:`PointsConfig` from ``QSettings`` (missing keys use defaults)."""
    defaults = PointsConfig()

    def _int(key: str, default: int) -> int:
        try:
            return int(settings.value(key, default))
        except (TypeError, ValueError):
            return default

    return PointsConfig(
        song_cost=_int(SETTINGS_POINTS_SONG_COST, defaults.song_cost),
        points_per_coin=_int(SETTINGS_POINTS_PER_COIN, defaults.points_per_coin),
        likes_per_point=_int(SETTINGS_POINTS_LIKES_PER_POINT, defaults.likes_per_point),
        points_per_share=_int(SETTINGS_POINTS_PER_SHARE, defaults.points_per_share),
        points_per_follow=_int(SETTINGS_POINTS_PER_FOLLOW, defaults.points_per_follow),
        watch_points_per_interval=_int(
            SETTINGS_POINTS_WATCH_PER_INTERVAL, defaults.watch_points_per_interval
        ),
        watch_interval_minutes=_int(
            SETTINGS_POINTS_WATCH_INTERVAL_MIN, defaults.watch_interval_minutes
        ),
    ).sanitized()


def save_points_config_to_settings(settings, cfg: PointsConfig) -> None:
    """Persist a sanitized :class:`PointsConfig` to ``QSettings``."""
    s = cfg.sanitized()
    settings.setValue(SETTINGS_POINTS_SONG_COST, s.song_cost)
    settings.setValue(SETTINGS_POINTS_PER_COIN, s.points_per_coin)
    settings.setValue(SETTINGS_POINTS_LIKES_PER_POINT, s.likes_per_point)
    settings.setValue(SETTINGS_POINTS_PER_SHARE, s.points_per_share)
    settings.setValue(SETTINGS_POINTS_PER_FOLLOW, s.points_per_follow)
    settings.setValue(SETTINGS_POINTS_WATCH_PER_INTERVAL, s.watch_points_per_interval)
    settings.setValue(SETTINGS_POINTS_WATCH_INTERVAL_MIN, s.watch_interval_minutes)


def _field_label(text: str) -> QLabel:
    lab = QLabel(text)
    lab.setObjectName("formFieldLabel")
    lab.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    lab.setWordWrap(True)
    lab.setMinimumWidth(118)
    lab.setContentsMargins(0, 0, 6, 0)
    return lab


def _stretch_spin(spin: QSpinBox) -> QWidget:
    wrap = QWidget()
    lay = QHBoxLayout(wrap)
    lay.setContentsMargins(0, 0, 0, 0)
    spin.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    lay.addWidget(spin)
    return wrap


class PointsSettingsDialog(QDialog):
    """Fine-grained editor for the song-request points economy."""

    def __init__(
        self,
        *,
        parent: QWidget | None,
        settings,
        tr: TrFn,
        on_saved: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self._tr = tr
        self._on_saved = on_saved
        self._fields: list[_SpinField] = []

        self.setObjectName("pointsSettingsDialog")
        self.setStyleSheet(settings_panel_stylesheet())
        self.setWindowTitle(self._tr("settings.points_dialog_title"))
        self.setModal(True)
        self.setMinimumSize(500, 520)
        self.resize(520, 560)
        if parent is not None:
            win_icon = parent.windowIcon()
            if not win_icon.isNull():
                self.setWindowIcon(win_icon)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 14)
        root.setSpacing(12)

        intro = QLabel(self._tr("settings.points_dialog_intro"))
        intro.setObjectName("mutedHint")
        intro.setWordWrap(True)
        root.addWidget(intro)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        body.setObjectName("pointsSettingsScrollBody")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 8, 0)
        body_lay.setSpacing(14)

        defaults = PointsConfig()
        body_lay.addWidget(
            self._build_group(
                "settings.points_group_general",
                [
                    (
                        "settings.points_song_cost",
                        SETTINGS_POINTS_SONG_COST,
                        defaults.song_cost,
                        0,
                        100_000,
                    ),
                    (
                        "settings.points_per_coin",
                        SETTINGS_POINTS_PER_COIN,
                        defaults.points_per_coin,
                        0,
                        1_000,
                    ),
                ],
            ),
        )
        body_lay.addWidget(
            self._build_group(
                "settings.points_group_likes",
                [
                    (
                        "settings.points_likes_per_point",
                        SETTINGS_POINTS_LIKES_PER_POINT,
                        defaults.likes_per_point,
                        1,
                        10_000,
                    ),
                ],
            ),
        )
        body_lay.addWidget(
            self._build_group(
                "settings.points_group_shares",
                [
                    (
                        "settings.points_per_share",
                        SETTINGS_POINTS_PER_SHARE,
                        defaults.points_per_share,
                        0,
                        10_000,
                    ),
                ],
            ),
        )
        body_lay.addWidget(
            self._build_group(
                "settings.points_group_follow",
                [
                    (
                        "settings.points_per_follow",
                        SETTINGS_POINTS_PER_FOLLOW,
                        defaults.points_per_follow,
                        0,
                        10_000,
                    ),
                ],
            ),
        )
        body_lay.addWidget(
            self._build_group(
                "settings.points_group_watch",
                [
                    (
                        "settings.points_watch_per_interval",
                        SETTINGS_POINTS_WATCH_PER_INTERVAL,
                        defaults.watch_points_per_interval,
                        0,
                        10_000,
                    ),
                    (
                        "settings.points_watch_interval_min",
                        SETTINGS_POINTS_WATCH_INTERVAL_MIN,
                        defaults.watch_interval_minutes,
                        1,
                        240,
                    ),
                ],
            ),
        )
        body_lay.addStretch(1)
        scroll.setWidget(body)
        root.addWidget(scroll, stretch=1)

        hint = QLabel(self._tr("settings.points_dialog_hint"))
        hint.setObjectName("mutedHint")
        hint.setWordWrap(True)
        root.addWidget(hint)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        cancel_btn = QPushButton(self._tr("settings.points_dialog_cancel"))
        cancel_btn.clicked.connect(self.reject)
        ok_btn = QPushButton(self._tr("settings.points_dialog_ok"))
        ok_btn.setObjectName("primaryButton")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._on_accept)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)
        root.addLayout(btn_row)

        self._load_from_settings()

    def _build_group(
        self,
        title_key: str,
        rows: list[tuple[str, str, int, int, int]],
    ) -> QGroupBox:
        box = QGroupBox(self._tr(title_key))
        grid = QGridLayout(box)
        grid.setContentsMargins(6, 10, 6, 8)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(1, 1)
        grid.setColumnMinimumWidth(0, 124)
        for row_i, (label_key, settings_key, default, minimum, maximum) in enumerate(rows):
            spin = QSpinBox()
            spin.setMinimum(minimum)
            spin.setMaximum(maximum)
            spin.setMinimumHeight(30)
            lbl = _field_label(self._tr(label_key))
            lbl.setBuddy(spin)
            grid.addWidget(lbl, row_i, 0)
            grid.addWidget(_stretch_spin(spin), row_i, 1)
            self._fields.append(
                _SpinField(
                    key=settings_key,
                    spin=spin,
                    default=default,
                    minimum=minimum,
                    maximum=maximum,
                ),
            )
        return box

    def _load_from_settings(self) -> None:
        cfg = load_points_config_from_settings(self._settings)
        values = {
            SETTINGS_POINTS_SONG_COST: cfg.song_cost,
            SETTINGS_POINTS_PER_COIN: cfg.points_per_coin,
            SETTINGS_POINTS_LIKES_PER_POINT: cfg.likes_per_point,
            SETTINGS_POINTS_PER_SHARE: cfg.points_per_share,
            SETTINGS_POINTS_PER_FOLLOW: cfg.points_per_follow,
            SETTINGS_POINTS_WATCH_PER_INTERVAL: cfg.watch_points_per_interval,
            SETTINGS_POINTS_WATCH_INTERVAL_MIN: cfg.watch_interval_minutes,
        }
        for field in self._fields:
            field.spin.setValue(values.get(field.key, field.default))

    def _on_accept(self) -> None:
        cfg = PointsConfig(
            song_cost=self._spin_value(SETTINGS_POINTS_SONG_COST),
            points_per_coin=self._spin_value(SETTINGS_POINTS_PER_COIN),
            likes_per_point=self._spin_value(SETTINGS_POINTS_LIKES_PER_POINT),
            points_per_share=self._spin_value(SETTINGS_POINTS_PER_SHARE),
            points_per_follow=self._spin_value(SETTINGS_POINTS_PER_FOLLOW),
            watch_points_per_interval=self._spin_value(SETTINGS_POINTS_WATCH_PER_INTERVAL),
            watch_interval_minutes=self._spin_value(SETTINGS_POINTS_WATCH_INTERVAL_MIN),
        ).sanitized()
        save_points_config_to_settings(self._settings, cfg)
        if self._on_saved is not None:
            self._on_saved()
        self.accept()

    def _spin_value(self, key: str) -> int:
        for field in self._fields:
            if field.key == key:
                return int(field.spin.value())
        return 0
