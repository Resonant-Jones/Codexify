from __future__ import annotations

from guardian.user_profile_tokens import (
    DEFAULT_USER_ACCENT_COLOR,
    USER_ACCENT_COLORS,
    is_valid_user_accent_color,
    normalize_user_accent_color,
)


def test_canonical_accent_token_set():
    assert USER_ACCENT_COLORS == frozenset(
        [
            "default",
            "blue",
            "cyan",
            "emerald",
            "amber",
            "rose",
            "violet",
            "slate",
        ]
    )


def test_default_token_is_a_valid_member():
    assert DEFAULT_USER_ACCENT_COLOR == "default"
    assert DEFAULT_USER_ACCENT_COLOR in USER_ACCENT_COLORS


def test_no_duplicate_tokens():
    assert len(USER_ACCENT_COLORS) == len(set(USER_ACCENT_COLORS))


def test_storage_length_limit():
    max_length_col = 16
    for token in USER_ACCENT_COLORS:
        assert (
            len(token) <= max_length_col
        ), f"token {token!r} exceeds column length {max_length_col}"


def test_all_valid_tokens_pass_validation():
    for token in USER_ACCENT_COLORS:
        assert is_valid_user_accent_color(token) is True


def test_invalid_css_like_values_are_rejected():
    invalid = [
        "#ff00ff",
        "var(--accent)",
        "url(https://example.com)",
        "linear-gradient(red, blue)",
        "rgb(255,0,0)",
        "rgba(0,0,0,0.5)",
        "hsl(240, 100%, 50%)",
        "none",
        "",
        "DEFAULT",
        "Blue",
        "EMERALD",
        "cyan ",
        " amber",
        "anything-else",
    ]
    for value in invalid:
        assert not is_valid_user_accent_color(
            value
        ), f"value {value!r} should not be accepted"


def test_normalize_returns_default_for_none():
    assert normalize_user_accent_color(None) == "default"


def test_normalize_returns_default_for_unknown():
    assert normalize_user_accent_color("#ff00ff") == "default"
    assert normalize_user_accent_color("invalid") == "default"
    assert normalize_user_accent_color("") == "default"


def test_normalize_passes_through_valid_tokens():
    for token in USER_ACCENT_COLORS:
        assert normalize_user_accent_color(token) == token
