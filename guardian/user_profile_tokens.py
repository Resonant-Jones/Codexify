"""Bounded canonical accent-preference token registry for User Profile metadata.

These tokens are presentation-preference identifiers, not runtime protocol
tokens.  They belong here rather than in ``guardian/protocol_tokens.py``
because they describe account-scoped UI-metadata values, not queue, event,
error, or execution state.

Canonical accent tokens
------------------------

``default``
    Current neutral user-message styling.
``blue``
``cyan``
``emerald``
``amber``
``rose``
``violet``
``slate``
    Codexify-compatible restrained accent palettes.  The exact rendered
    colour may evolve while the stable token name remains the same.
"""

from __future__ import annotations

USER_ACCENT_COLORS: frozenset[str] = frozenset(
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

DEFAULT_USER_ACCENT_COLOR: str = "default"

_MAX_TOKEN_LENGTH: int = max(len(t) for t in USER_ACCENT_COLORS)


def is_valid_user_accent_color(value: str) -> bool:
    """Return True when *value* is one of the canonical accent tokens."""
    return value in USER_ACCENT_COLORS


def normalize_user_accent_color(value: str | None) -> str:
    """Return the canonical accent token for *value* or ``"default"``.

    Unknown / missing values always resolve to ``"default"``.
    """
    if value is not None and is_valid_user_accent_color(value):
        return value
    return DEFAULT_USER_ACCENT_COLOR


__all__ = [
    "DEFAULT_USER_ACCENT_COLOR",
    "USER_ACCENT_COLORS",
    "is_valid_user_accent_color",
    "normalize_user_accent_color",
]
