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
