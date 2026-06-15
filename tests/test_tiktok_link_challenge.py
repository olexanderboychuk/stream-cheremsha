from __future__ import annotations

from stream_cheremsha.domain.tiktok_link_challenge import (
    LINK_CODE_WORDS,
    comment_matches_link_code,
    extract_link_code_from_comment,
    generate_link_code,
    normalize_link_code,
)


def test_generate_link_code_is_vocab_word() -> None:
    code = generate_link_code()
    assert code in LINK_CODE_WORDS
    assert normalize_link_code(code) == code


def test_extract_link_code_from_comment() -> None:
    assert extract_link_code_from_comment("Cat") == "Cat"
    assert extract_link_code_from_comment("  kitty  ") == "Kitty"
    assert extract_link_code_from_comment("привіт Dog дякую") == "Dog"
    assert extract_link_code_from_comment("CH-ABC123") is None
    assert extract_link_code_from_comment("") is None


def test_comment_matches_link_code() -> None:
    assert comment_matches_link_code("my Puppy", "puppy")
    assert not comment_matches_link_code("Tiger", "Lion")
