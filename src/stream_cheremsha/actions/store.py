from __future__ import annotations

from typing import Final

from PySide6.QtCore import QSettings

from stream_cheremsha.actions.models import (
    RuleV1,
    UiRulesLayoutV1,
    normalize_ui_rules_layout_v1,
    ruleset_bundle_from_json_text,
    ruleset_to_json_text,
)

DEFAULT_SETTINGS_ORG: Final[str] = 'stream-cheremsha'
DEFAULT_SETTINGS_APP: Final[str] = 'cheremsha'


def _validate_key_part(name: str, value: str) -> str:
    v = (value or '').strip()
    if not v:
        raise ValueError(f'{name} must be non-empty')
    if '/' in v or '\\' in v:
        raise ValueError(f'{name} must not contain path separators')
    return v


def _rules_key(platform: str, account_key: str) -> str:
    p2 = _validate_key_part('platform', platform)
    a2 = _validate_key_part('account_key', account_key)
    return f'actions/{p2}/{a2}/rules_json'


def actions_rules_key_is_set(
    platform: str,
    account_key: str,
    *,
    settings: QSettings | None = None,
    org: str = DEFAULT_SETTINGS_ORG,
    app: str = DEFAULT_SETTINGS_APP,
) -> bool:
    """True if a non-empty rules JSON is stored (including an intentionally empty rules list)."""
    key = _rules_key(platform, account_key)
    s = _get_settings(settings, org=org, app=app)
    text = s.value(key, None, str)
    if text is None:
        return False
    return (text or '').strip() != ''


def _get_settings(settings: QSettings | None, *, org: str, app: str) -> QSettings:
    if settings is not None:
        return settings
    return QSettings(org, app)


def load_rules(
    platform: str,
    account_key: str,
    *,
    settings: QSettings | None = None,
    org: str = DEFAULT_SETTINGS_ORG,
    app: str = DEFAULT_SETTINGS_APP,
) -> list[RuleV1]:
    key = _rules_key(platform, account_key)
    s = _get_settings(settings, org=org, app=app)
    text = s.value(key, None, str)
    if text is None:
        return []
    text = (text or '').strip()
    if not text:
        return []
    rules, _layout = ruleset_bundle_from_json_text(text)
    return rules


def load_rules_bundle(
    platform: str,
    account_key: str,
    *,
    settings: QSettings | None = None,
    org: str = DEFAULT_SETTINGS_ORG,
    app: str = DEFAULT_SETTINGS_APP,
) -> tuple[list[RuleV1], UiRulesLayoutV1 | None]:
    key = _rules_key(platform, account_key)
    s = _get_settings(settings, org=org, app=app)
    text = s.value(key, None, str)
    if text is None:
        return [], None
    text = (text or "").strip()
    if not text:
        return [], None
    rules, layout = ruleset_bundle_from_json_text(text)
    return rules, layout


def save_rules(
    platform: str,
    account_key: str,
    rules: list[RuleV1],
    *,
    settings: QSettings | None = None,
    org: str = DEFAULT_SETTINGS_ORG,
    app: str = DEFAULT_SETTINGS_APP,
) -> None:
    key = _rules_key(platform, account_key)
    s = _get_settings(settings, org=org, app=app)
    s.setValue(key, ruleset_to_json_text(rules))
    s.sync()


def save_rules_bundle(
    platform: str,
    account_key: str,
    rules: list[RuleV1],
    ui_layout: UiRulesLayoutV1 | None,
    *,
    settings: QSettings | None = None,
    org: str = DEFAULT_SETTINGS_ORG,
    app: str = DEFAULT_SETTINGS_APP,
) -> None:
    key = _rules_key(platform, account_key)
    s = _get_settings(settings, org=org, app=app)
    layout2 = normalize_ui_rules_layout_v1(ui_layout, rules)
    s.setValue(key, ruleset_to_json_text(rules, ui_layout=layout2))
    s.sync()
