import pytest

from stream_cheremsha.actions.registry import match_chat_keyword


@pytest.mark.parametrize(
    ("text", "keyword", "case_sensitive", "expected"),
    [
        ("hello world", "world", True, True),
        ("hello world", "WORLD", True, False),
        ("hello world", "WORLD", False, True),
        ("Привіт Світ", "світ", False, True),
    ],
)
def test_match_chat_keyword_contains(
    text: str, keyword: str, case_sensitive: bool, expected: bool
) -> None:
    assert (
        match_chat_keyword(text, keyword, mode="contains", case_sensitive=case_sensitive)
        is expected
    )


@pytest.mark.parametrize(
    ("text", "keyword", "case_sensitive", "expected"),
    [
        ("ping", "ping", True, True),
        ("ping", "PING", True, False),
        ("ping", "PING", False, True),
    ],
)
def test_match_chat_keyword_equals(
    text: str, keyword: str, case_sensitive: bool, expected: bool
) -> None:
    assert (
        match_chat_keyword(text, keyword, mode="equals", case_sensitive=case_sensitive) is expected
    )


def test_match_chat_keyword_regex_happy_path() -> None:
    assert match_chat_keyword("hello 123", r"\d+", mode="regex", case_sensitive=True) is True


def test_match_chat_keyword_regex_invalid_pattern_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Invalid regex pattern"):
        match_chat_keyword("hello", r"(", mode="regex")
