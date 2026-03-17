from __future__ import annotations

from types import SimpleNamespace

import pytest

from guardian.core import config as core_config


def _legacy_settings(**overrides):
    baseline = {
        "GUARDIAN_API_KEY": None,
        "GUARDIAN_API_KEYS": None,
        "GUARDIAN_DATABASE_URL": None,
        "OPENAI_API_KEY": None,
        "GROQ_API_KEY": None,
        "AI_BACKEND": "groq",
        "CLOUD_ONLY": False,
    }
    baseline.update(overrides)
    return SimpleNamespace(**baseline)


@pytest.fixture(autouse=True)
def _reset_coherence_logging_state(monkeypatch):
    core_config._LOGGED_COHERENCE_SOURCES.clear()
    monkeypatch.delenv("CODEXIFY_CONFIG_SOURCE", raising=False)


def test_config_coherence_passes_when_values_match(monkeypatch):
    core = core_config.Settings(
        GUARDIAN_API_KEY="k-primary",
        GUARDIAN_API_KEYS="k1,k2",
        GUARDIAN_DATABASE_URL="postgresql://db:5432/guardian",
        OPENAI_API_KEY="openai-key",
        GROQ_API_KEY="groq-key",
    )
    legacy = _legacy_settings(
        GUARDIAN_API_KEY="k-primary",
        GUARDIAN_API_KEYS="k1,k2",
        GUARDIAN_DATABASE_URL="postgresql://db:5432/guardian",
        OPENAI_API_KEY="openai-key",
        GROQ_API_KEY="groq-key",
    )
    monkeypatch.setattr(
        core_config,
        "_load_legacy_settings_for_coherence",
        lambda: legacy,
    )
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("AI_BACKEND", raising=False)
    monkeypatch.delenv("CLOUD_ONLY", raising=False)

    core_config.assert_config_coherence(core)


def test_config_coherence_rejects_api_key_mismatch(monkeypatch):
    core = core_config.Settings(GUARDIAN_API_KEY="core-key")
    legacy = _legacy_settings(GUARDIAN_API_KEY="legacy-key")
    monkeypatch.setattr(
        core_config,
        "_load_legacy_settings_for_coherence",
        lambda: legacy,
    )

    with pytest.raises(
        core_config.ConfigCoherenceError, match="GUARDIAN_API_KEY"
    ):
        core_config.assert_config_coherence(core)


def test_config_coherence_rejects_provider_mismatch_when_explicit(monkeypatch):
    core = core_config.Settings(
        LLM_PROVIDER="openai",
        ALLOW_CLOUD_PROVIDERS=True,
    )
    legacy = _legacy_settings(AI_BACKEND="ollama")
    monkeypatch.setattr(
        core_config,
        "_load_legacy_settings_for_coherence",
        lambda: legacy,
    )
    monkeypatch.setenv("LLM_PROVIDER", "openai")

    with pytest.raises(
        core_config.ConfigCoherenceError, match="LLM_PROVIDER/AI_BACKEND"
    ):
        core_config.assert_config_coherence(core)


def test_config_coherence_strict_mode_error_lists_env_sources(monkeypatch):
    core = core_config.Settings(
        LLM_PROVIDER="openai",
        ALLOW_CLOUD_PROVIDERS=True,
        CODEXIFY_CONFIG_SOURCE="strict",
    )
    legacy = _legacy_settings(AI_BACKEND="ollama")
    monkeypatch.setattr(
        core_config,
        "_load_legacy_settings_for_coherence",
        lambda: legacy,
    )
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("AI_BACKEND", "ollama")

    with pytest.raises(core_config.ConfigCoherenceError) as excinfo:
        core_config.assert_config_coherence(core)

    msg = str(excinfo.value)
    assert "Core source: LLM_PROVIDER=openai" in msg
    assert "Legacy source: AI_BACKEND=ollama" in msg
    assert "CODEXIFY_CONFIG_SOURCE=core|legacy" in msg


def test_config_coherence_core_mode_allows_mismatch_and_logs_source(
    monkeypatch, caplog
):
    core = core_config.Settings(
        LLM_PROVIDER="local",
        CODEXIFY_CONFIG_SOURCE="core",
    )
    legacy = _legacy_settings(AI_BACKEND="groq")
    monkeypatch.setattr(
        core_config,
        "_load_legacy_settings_for_coherence",
        lambda: legacy,
    )
    monkeypatch.setenv("LLM_PROVIDER", "local")
    monkeypatch.setenv("AI_BACKEND", "groq")

    with caplog.at_level("INFO", logger="guardian.core.config"):
        core_config.assert_config_coherence(core)

    assert "CODEXIFY_CONFIG_SOURCE=core" in caplog.text


def test_config_coherence_legacy_mode_allows_mismatch_and_logs_source(
    monkeypatch, caplog
):
    core = core_config.Settings(
        LLM_PROVIDER="local",
        CODEXIFY_CONFIG_SOURCE="legacy",
    )
    legacy = _legacy_settings(
        AI_BACKEND="groq",
        GROQ_API_KEY="legacy-groq-key",
    )
    monkeypatch.setattr(
        core_config,
        "_load_legacy_settings_for_coherence",
        lambda: legacy,
    )
    monkeypatch.setenv("LLM_PROVIDER", "local")
    monkeypatch.setenv("AI_BACKEND", "groq")

    with caplog.at_level("INFO", logger="guardian.core.config"):
        core_config.assert_config_coherence(core)

    assert "CODEXIFY_CONFIG_SOURCE=legacy" in caplog.text


def test_config_coherence_rejects_cloud_only_without_cloud_allow(monkeypatch):
    core = core_config.Settings(ALLOW_CLOUD_PROVIDERS=False)
    legacy = _legacy_settings(CLOUD_ONLY=True)
    monkeypatch.setattr(
        core_config,
        "_load_legacy_settings_for_coherence",
        lambda: legacy,
    )
    monkeypatch.setenv("CLOUD_ONLY", "1")

    with pytest.raises(core_config.ConfigCoherenceError, match="CLOUD_ONLY"):
        core_config.assert_config_coherence(core)


def test_config_coherence_skips_when_legacy_unavailable(monkeypatch):
    core = core_config.Settings()
    monkeypatch.setattr(
        core_config,
        "_load_legacy_settings_for_coherence",
        lambda: None,
    )

    core_config.assert_config_coherence(core)


def test_validate_llm_config_rejects_alibaba_without_api_key():
    settings = core_config.Settings(
        LLM_PROVIDER="alibaba",
        ALLOW_CLOUD_PROVIDERS=True,
        ALIBABA_API_KEY="",
    )

    with pytest.raises(core_config.LLMConfigError, match="ALIBABA_API_KEY"):
        core_config.validate_llm_config(settings)


def test_validate_llm_config_rejects_alibaba_with_blank_base():
    settings = core_config.Settings(
        LLM_PROVIDER="alibaba",
        ALLOW_CLOUD_PROVIDERS=True,
        ALIBABA_API_KEY="test-alibaba-key",
        ALIBABA_API_BASE="",
    )

    with pytest.raises(core_config.LLMConfigError, match="ALIBABA_API_BASE"):
        core_config.validate_llm_config(settings)


def test_validate_llm_config_accepts_alibaba_with_default_base():
    settings = core_config.Settings(
        LLM_PROVIDER="alibaba",
        ALLOW_CLOUD_PROVIDERS=True,
        ALIBABA_API_KEY="test-alibaba-key",
    )

    core_config.validate_llm_config(settings)
