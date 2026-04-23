from stream_cheremsha import l10n


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
