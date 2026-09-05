from stream_cheremsha import l10n
from stream_cheremsha.overlays.signal_system_overlay import _I18N_KEYS, _overlay_i18n_bundle


def test_normalize_locale() -> None:
    assert l10n.normalize_locale("EN") == "en"
    assert l10n.normalize_locale("uk") == "uk"
    assert l10n.normalize_locale("") == "uk"


def test_tr_both_locales() -> None:
    assert "Settings" in l10n.tr("en", "tab.settings")
    assert "Налаштування" in l10n.tr("uk", "tab.settings")


def test_all_locale_strings_many() -> None:
    s = l10n.all_locale_strings_many("status.logout_twitch")
    assert l10n.tr("uk", "status.logout_twitch") in s
    assert l10n.tr("en", "status.logout_twitch") in s


def test_signal_system_keys_cover_app_locales() -> None:
    """Signal System UI/overlay strings must exist for every AppLocale (uk, en)."""
    keys = [
        "widgets.signal_system.title",
        "widgets.signal_system.settings_title",
        "widgets.signal_system.settings_blurb",
        "widgets.signal_system.card_title",
        "widgets.signal_system.edit_header",
        "signal_system.ui.scale",
        "signal_system.ui.scale_hint",
        "signal_system.ui.core_vertical",
        "signal_system.ui.core_vertical_hint",
        "signal_system.ui.theme",
        "signal_system.ui.title",
        "signal_system.ui.perimeter",
        "signal_system.ui.particles",
        "signal_system.ui.glitch",
        "signal_system.ui.sound",
        "signal_system.ui.opacity_idle",
        "signal_system.ui.opacity_active",
        "signal_system.ui.cooldown",
        "signal_system.ui.min_gift_coins",
        "signal_system.goal.detected",
        "signal_system.goal.milestone",
        "signal_system.goal.surge",
        "signal_system.goal.ai",
        "signal_system.goal.anomaly",
        "signal_system.goal.test",
        "signal_system.goal.system",
        "signal_system.goal.unknown",
        "signal_system.goal.gifts",
        "signal_system.goal.coins",
        "signal_system.theme.neon_cyber",
        "signal_system.theme.toxic_system",
        "signal_system.theme.ice_protocol",
        "signal_system.theme.amber_core",
        "signal_system.theme.critical",
    ]
    for key in keys:
        uk = l10n.tr("uk", key)
        en = l10n.tr("en", key)
        assert uk.strip(), f"empty uk for {key}"
        assert en.strip(), f"empty en for {key}"
        # Bad legacy translations that should stay fixed
        assert "КОНИ" not in uk
        assert "КОГНІТІВНА" not in uk
        assert "МАЙЛСТОУН" not in uk
        assert "ПЕРЕЗАГРУЗКА" not in uk
        assert "НЕВІДОМА ЧАСТИНА" not in uk


def test_signal_system_overlay_i18n_bundle_matches_l10n() -> None:
    bundle = _overlay_i18n_bundle()
    assert set(bundle.keys()) == {"uk", "en"}
    for short in _I18N_KEYS:
        full = f"signal_system.{short}"
        assert bundle["uk"][short] == l10n.tr("uk", full)
        assert bundle["en"][short] == l10n.tr("en", full)
