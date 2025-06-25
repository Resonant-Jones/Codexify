import os

import pytest
from pydantic import ValidationError

from guardian.config import Settings, get_settings


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("GENAI_API_KEY", "fake-gemini-key")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-openai-key")
    monkeypatch.setenv("NOTION_API_KEY", "fake-notion-key")
    s = get_settings()
    assert isinstance(s, Settings)
    assert s.GENAI_API_KEY == "fake-gemini-key"
    assert s.OPENAI_API_KEY == "fake-openai-key"


def test_missing_required_env(monkeypatch):
    monkeypatch.delenv("GENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValidationError):
        s = get_settings()
        # Pydantic v2: model_dump() triggers validation; v1: instantiation should fail
        # This works for both versions
        if hasattr(s, "model_dump"):
            s.model_dump()
        else:
            # For older Pydantic (v1), just access a required field to force validation
            _ = s.GENAI_API_KEY


from guardian.config import (get_active_model, get_backend_capabilities,
                             get_model_and_host, is_backend_capable,
                             is_cloud_backend)


def test_get_active_model_returns_string():
    s = get_settings()
    model = get_active_model(s)
    assert isinstance(model, str)
    assert len(model) > 0


def test_model_and_host_are_valid():
    s = get_settings()
    model, host = get_model_and_host(s)
    assert isinstance(model, str)
    assert isinstance(host, str)
    assert model and host


def test_is_cloud_backend_returns_bool():
    s = get_settings()
    assert isinstance(is_cloud_backend(s), bool)


def test_backend_capabilities_structure():
    s = get_settings()
    caps = get_backend_capabilities(s)
    assert isinstance(caps, dict)
    for key, value in caps.items():
        assert isinstance(value, bool)


def test_is_backend_capable_consistency():
    s = get_settings()
    caps = get_backend_capabilities(s)
    for key in caps:
        assert is_backend_capable(s, key) == caps[key]
