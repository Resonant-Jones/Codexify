from __future__ import annotations

import pytest
from memoryos.embedders import factory

from guardian.core.config import (
    LLMConfigError,
    Settings,
    validate_embedding_provider_config,
)


class DummyProvider:
    name = "dummy"

    def embed(self, texts, model=None, **kw):
        return [[0.1, 0.2, 0.3] for _ in texts]


class DummyRegistry:
    def __init__(self) -> None:
        self.provider = DummyProvider()

    def get_embeddings(self, provider):
        assert provider == "dummy"
        return self.provider


class DummyOpenAIEmbedder:
    name = "openai"

    def __init__(self, api_key=None, model=None):
        self.api_key = api_key
        self.model_name = model

    def embed(self, text: str):
        return [0.1, 0.2, 0.3]

    def embed_batch(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


def _settings(**overrides) -> Settings:
    base = dict(
        EMBEDDER_PROVIDER="local",
        ALLOW_CLOUD_PROVIDERS=True,
        CODEXIFY_LOCAL_ONLY_MODE=False,
        CODEXIFY_EGRESS_ALLOWLIST="openai,dummy",
        OPENAI_API_KEY="openai-key",
        EMBEDDING_MODEL="embed-model",
    )
    base.update(overrides)
    return Settings(**base)


def test_build_embedder_local_alias(monkeypatch):
    monkeypatch.setattr(
        factory,
        "get_settings",
        lambda: _settings(EMBEDDER_PROVIDER="local_api"),
    )
    embedder = factory.build_memoryos_embedder("local_api")
    assert getattr(embedder, "name", "") == "local"


def test_build_embedder_openai(monkeypatch):
    monkeypatch.setattr(factory, "OpenAIEmbedder", DummyOpenAIEmbedder)
    monkeypatch.setattr(
        factory, "get_settings", lambda: _settings(EMBEDDER_PROVIDER="openai")
    )
    monkeypatch.setenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

    embedder = factory.build_memoryos_embedder("openai")
    assert isinstance(embedder, DummyOpenAIEmbedder)
    assert embedder.api_key == "openai-key"
    assert embedder.model_name == "text-embedding-3-small"


def test_build_embedder_registry_adapter(monkeypatch):
    monkeypatch.setattr(factory, "ProviderRegistry", DummyRegistry)
    monkeypatch.setattr(
        factory, "get_settings", lambda: _settings(EMBEDDER_PROVIDER="dummy")
    )

    embedder = factory.build_memoryos_embedder("dummy")
    assert embedder.name == "dummy"
    assert embedder.embed("hello") == [0.1, 0.2, 0.3]


def test_validate_embedding_provider_policy_blocked_cloud():
    settings = _settings(
        EMBEDDER_PROVIDER="openai",
        ALLOW_CLOUD_PROVIDERS=False,
        CODEXIFY_LOCAL_ONLY_MODE=False,
        CODEXIFY_EGRESS_ALLOWLIST="openai",
    )

    with pytest.raises(LLMConfigError):
        validate_embedding_provider_config(settings)


def test_build_embedder_unsupported_provider(monkeypatch):
    monkeypatch.setattr(factory, "ProviderRegistry", DummyRegistry)
    monkeypatch.setattr(
        factory, "get_settings", lambda: _settings(EMBEDDER_PROVIDER="unknown")
    )

    with pytest.raises(Exception):
        factory.build_memoryos_embedder("unknown")
