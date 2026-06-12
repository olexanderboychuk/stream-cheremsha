from __future__ import annotations

from PySide6.QtCore import QSettings

from stream_cheremsha import l10n


def load_ui_locale(settings: QSettings | None = None) -> l10n.AppLocale:
    """App UI locale as picked in Settings — used to localize overlay texts."""
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    raw = s.value(l10n.SETTINGS_UI_LOCALE, l10n.DEFAULT_LOCALE, str)
    return l10n.normalize_locale(str(raw or ""))
