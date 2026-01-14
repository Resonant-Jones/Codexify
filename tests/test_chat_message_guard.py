import pytest

from guardian.core.message_guard import (
    EMPTY_ASSISTANT_FALLBACK,
    guard_assistant_message_content,
)


def test_guard_rejects_blank_assistant_in_dev(monkeypatch):
    monkeypatch.setenv("GUARDIAN_ENV", "development")
    with pytest.raises(ValueError, match="empty assistant message"):
        guard_assistant_message_content("assistant", "   ")


def test_guard_allows_non_blank_assistant(monkeypatch):
    monkeypatch.setenv("GUARDIAN_ENV", "development")
    content = guard_assistant_message_content("assistant", "Hello!")
    assert content == "Hello!"


def test_guard_falls_back_in_production(monkeypatch):
    monkeypatch.setenv("GUARDIAN_ENV", "production")
    content = guard_assistant_message_content("assistant", "")
    assert content == EMPTY_ASSISTANT_FALLBACK


def test_guard_ignores_non_assistant_roles(monkeypatch):
    monkeypatch.setenv("GUARDIAN_ENV", "development")
    content = guard_assistant_message_content("user", "")
    assert content == ""
