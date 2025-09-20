import pytest

pytestmark = pytest.mark.settings

from guardian.config.core import (
    get_model_and_host,
    get_settings_no_env,
    is_cloud_backend,
    warn_if_missing_keys,
)


def unset_env(monkeypatch, *keys):
    for k in keys:
        monkeypatch.delenv(k, raising=False)


def test_dev_defaults_instantiates(monkeypatch):
    s = get_settings_no_env(ENV="development")
    assert s.ENV == "development"


def test_dev_gemini_without_keys_warns(monkeypatch, capsys):
    s = get_settings_no_env(
        ENV="development", AI_BACKEND="gemini", GENAI_API_KEY=None, GOOGLE_API_KEY=None
    )
    warn_if_missing_keys(s)
    out = capsys.readouterr().out
    assert "missing gemini api key" in out.lower()


def test_prod_groq_missing_key_raises(monkeypatch):
    with pytest.raises(ValueError):
        get_settings_no_env(ENV="production", AI_BACKEND="groq", GROQ_API_KEY=None)


@pytest.mark.parametrize(
    "genai, google",
    [
        ("test-genai", None),
        (None, "test-google"),
    ],
)
def test_prod_gemini_accepts_either_key(monkeypatch, genai, google):
    args = {
        "ENV": "production",
        "AI_BACKEND": "gemini",
        "GENAI_API_KEY": None,
        "GOOGLE_API_KEY": None,
    }
    if genai is not None:
        args["GENAI_API_KEY"] = genai
    if google is not None:
        args["GOOGLE_API_KEY"] = google
    s = get_settings_no_env(**args)
    assert s.AI_BACKEND.lower() == "gemini"


def test_dev_openai_missing_key_warns(monkeypatch, capsys):
    s = get_settings_no_env(ENV="development", AI_BACKEND="openai", OPENAI_API_KEY=None)
    warn_if_missing_keys(s)
    out = capsys.readouterr().out
    assert "missing openai api key" in out.lower()


def test_get_model_and_host_openai_uses_settings(monkeypatch):
    # Ensure env cannot interfere with overrides
    monkeypatch.setenv("OPENAI_MODEL", "env-model")
    s = get_settings_no_env(
        AI_BACKEND="openai",
        OPENAI_MODEL="gpt-4o-mini",
        OPENAI_API_ENDPOINT="https://api.openai.com/v1",
    )
    model, host = get_model_and_host(s)
    assert model == "gpt-4o-mini"
    assert host == "https://api.openai.com/v1"


def test_is_cloud_backend_includes_anthropic():
    s = get_settings_no_env(AI_BACKEND="anthropic")
    assert is_cloud_backend(s) is True


def test_get_model_and_host_gemini_uses_cloud_values():
    s = get_settings_no_env(
        AI_BACKEND="gemini",
        CLOUD_MODEL_NAME="gemini-1.5-pro",
        CLOUD_API_HOST="https://generativelanguage.googleapis.com/v1/models",
    )
    model, host = get_model_and_host(s)
    assert model == "gemini-1.5-pro"
    assert host == "https://generativelanguage.googleapis.com/v1/models"


def test_get_settings_no_env_respects_overrides_over_env(monkeypatch):
    # Simulate conflicting env and ensure explicit overrides win
    monkeypatch.setenv("OPENAI_MODEL", "env-model")
    s = get_settings_no_env(
        AI_BACKEND="openai",
        OPENAI_MODEL="override-model",
        OPENAI_API_ENDPOINT="https://api.openai.com/v1",
    )
    model, _ = get_model_and_host(s)
    assert model == "override-model"
