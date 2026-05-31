from __future__ import annotations

from stream_cheremsha.pipeline.tts_sanitize import strip_non_alphabetic_for_tts


def test_strip_removes_emoji_punctuation() -> None:
    assert strip_non_alphabetic_for_tts("hi 😀 there") == "hi there"
    assert strip_non_alphabetic_for_tts("hello!!!") == "hello"


def test_strip_keeps_digits() -> None:
    assert strip_non_alphabetic_for_tts("a1b2c") == "a1b2c"
    assert strip_non_alphabetic_for_tts("123 @@@") == "123"
    assert strip_non_alphabetic_for_tts("level 42") == "level 42"


def test_strip_removes_bracket_emote_shortcodes() -> None:
    assert strip_non_alphabetic_for_tts("[hi] hello [heart]") == "hello"
    assert strip_non_alphabetic_for_tts("[Kappa]") == ""


def test_strip_keeps_letters_across_scripts() -> None:
    assert "Привіт" in strip_non_alphabetic_for_tts("Привіт 🎉 світ")
    assert "café" == strip_non_alphabetic_for_tts("café")  # é is a letter


def test_strip_empty() -> None:
    assert strip_non_alphabetic_for_tts("") == ""
    assert strip_non_alphabetic_for_tts("@@@") == ""
