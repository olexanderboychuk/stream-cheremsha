from stream_cheremsha.audio.qt_sink import (
    _SETTINGS_AUDIO_BACKEND,
    _SETTINGS_AUDIO_BACKEND_LEGACY,
    AUDIO_BACKEND_FFPLAY,
    AUDIO_BACKEND_QT,
    normalize_audio_backend,
    read_audio_backend_setting,
)


def test_normalize_audio_backend_defaults_to_qt() -> None:
    assert normalize_audio_backend("") == AUDIO_BACKEND_QT
    assert normalize_audio_backend(None) == AUDIO_BACKEND_QT
    assert normalize_audio_backend("unknown") == AUDIO_BACKEND_QT


def test_normalize_audio_backend_accepts_ffplay() -> None:
    assert normalize_audio_backend("ffplay") == AUDIO_BACKEND_FFPLAY


def test_normalize_audio_backend_accepts_qt_aliases() -> None:
    assert normalize_audio_backend("qt") == AUDIO_BACKEND_QT
    assert normalize_audio_backend("QMediaPlayer") == AUDIO_BACKEND_QT


def test_read_audio_backend_setting_prefers_new_key() -> None:
    store = {
        _SETTINGS_AUDIO_BACKEND: "qt",
        _SETTINGS_AUDIO_BACKEND_LEGACY: "ffplay",
    }

    def get_value(key: str, default: object, _type: type) -> object:
        return store.get(key, default)

    assert read_audio_backend_setting(get_value) == AUDIO_BACKEND_QT


def test_read_audio_backend_setting_migrates_legacy_key() -> None:
    store = {_SETTINGS_AUDIO_BACKEND_LEGACY: "qt"}

    def get_value(key: str, default: object, _type: type) -> object:
        return store.get(key, default)

    assert read_audio_backend_setting(get_value) == AUDIO_BACKEND_QT
