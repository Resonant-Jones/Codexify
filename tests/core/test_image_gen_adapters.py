import base64
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from guardian.image_gen.providers import openai as adapter
from guardian.image_gen.router import ImageGenRouter


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("CODEXIFY_LOCAL_ONLY_MODE", "false")
    monkeypatch.setenv("ALLOW_CLOUD_PROVIDERS", "true")
    monkeypatch.setenv("CODEXIFY_EGRESS_ALLOWLIST", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key")
    factory = MagicMock()
    factory.return_value.images.generate.return_value = SimpleNamespace(
        data=[SimpleNamespace(b64_json=base64.b64encode(b"png").decode())]
    )
    monkeypatch.setattr(adapter, "OpenAI", factory)
    return factory


@pytest.mark.parametrize("model", ["gpt-image-2.6-sunburst", "gpt-image-2.6-flare"])
def test_gpt_image_uses_modern_parameters_without_paid_retries(client, model):
    image = ImageGenRouter.generate("a moon", provider="openai", model=model)
    assert image == b"png"
    client.assert_called_once_with(timeout=180, max_retries=0)
    client.return_value.images.generate.assert_called_once_with(
        prompt="a moon",
        model=model,
        size="1024x1024",
        n=1,
        output_format="png",
        quality="medium",
    )


def test_explicit_provider_wins_over_environment(client, monkeypatch):
    monkeypatch.setenv("IMAGE_GEN_PROVIDER", "local")
    assert (
        ImageGenRouter.generate("moon", provider="openai", model="gpt-image-2.6-flare")
        == b"png"
    )


@pytest.mark.parametrize(
    "base",
    [
        "https://api.openai.com",
        "https://api.openai.com/",
        "https://api.openai.com/v1",
    ],
)
def test_preview_origin_is_normalized_for_sdk(client, monkeypatch, base):
    monkeypatch.setenv("OPENAI_BASE_URL", base)
    adapter.OpenAIImageGen()
    client.assert_called_once_with(
        api_key=None,
        base_url="https://api.openai.com/v1",
        timeout=180,
        max_retries=0,
    )


@pytest.mark.parametrize(
    "model",
    [
        "gpt-image-1",
        "gpt-image-1-mini",
        "gpt-image-1.5",
        "gpt-image-1.5-2025-12-16",
        "chatgpt-image-latest",
        "dall-e-2",
        "dall-e-3",
    ],
)
def test_retired_explicit_models_are_denied_before_client_construction(client, model):
    with pytest.raises(HTTPException, match="Choose GPT Image 2.6") as failure:
        ImageGenRouter.generate("moon", provider="openai", model=model)
    assert failure.value.status_code == 400
    assert model not in ImageGenRouter.catalog()["providers"][0]["models"]
    client.assert_not_called()


def test_stale_environment_default_does_not_dispatch(client, monkeypatch):
    monkeypatch.setenv("IMAGE_GEN_PROVIDER", "openai")
    monkeypatch.setenv("IMAGE_GEN_MODEL", "gpt-image-1-mini")
    assert ImageGenRouter.catalog()["default_model"] == "gpt-image-2.6-sunburst"
    with pytest.raises(HTTPException, match="retired"):
        ImageGenRouter.generate("moon")
    client.assert_not_called()
    assert ImageGenRouter.generate("moon", model="gpt-image-2.6-flare") == b"png"


def test_openai_default_dispatches_current_sunburst(client, monkeypatch):
    monkeypatch.delenv("IMAGE_GEN_MODEL", raising=False)
    assert ImageGenRouter.generate("moon", provider="openai") == b"png"
    assert (
        client.return_value.images.generate.call_args.kwargs["model"]
        == "gpt-image-2.6-sunburst"
    )


def test_supported_environment_override_is_preserved(client, monkeypatch):
    monkeypatch.setenv("IMAGE_GEN_PROVIDER", "openai")
    monkeypatch.setenv("IMAGE_GEN_MODEL", "gpt-image-2.5-flare")
    assert ImageGenRouter.catalog()["default_model"] == "gpt-image-2.5-flare"
    assert ImageGenRouter.generate("moon") == b"png"
    assert (
        client.return_value.images.generate.call_args.kwargs["model"]
        == "gpt-image-2.5-flare"
    )


def test_still_supported_explicit_25_choice_is_not_rewritten(client):
    assert (
        ImageGenRouter.generate("moon", provider="openai", model="gpt-image-2.5-flare")
        == b"png"
    )
    assert (
        client.return_value.images.generate.call_args.kwargs["model"]
        == "gpt-image-2.5-flare"
    )


def test_local_only_blocks_cloud_before_client_construction(client, monkeypatch):
    monkeypatch.setenv("CODEXIFY_LOCAL_ONLY_MODE", "true")
    with pytest.raises(HTTPException) as failure:
        ImageGenRouter.generate("moon", provider="openai", model="gpt-image-2.6-flare")
    assert failure.value.status_code == 403
    client.assert_not_called()


def test_catalog_exposes_configured_state_without_a_paid_probe(client):
    catalog = ImageGenRouter.catalog()
    provider = catalog["providers"][0]
    assert provider["id"] == "openai"
    assert provider["available"]
    assert provider["default_model"] == "gpt-image-2.6-sunburst"
    assert provider["model_aliases"] == {
        "sunburst": "gpt-image-2.6-sunburst",
        "flare": "gpt-image-2.6-flare",
    }
    assert set(provider["model_aliases"].values()) <= set(provider["models"])
    assert all(
        not item["available"] for item in catalog["providers"] if item["id"] != "openai"
    )
    assert "synthetic-test-key" not in str(catalog)
    client.assert_not_called()


@pytest.mark.parametrize("payload", ["%%%", ""])
def test_malformed_provider_response_is_failure(client, payload):
    client.return_value.images.generate.return_value.data[0].b64_json = payload
    with pytest.raises(HTTPException) as failure:
        ImageGenRouter.generate("moon", provider="openai", model="gpt-image-2.6-flare")
    assert failure.value.status_code == 502


def test_unknown_model_does_not_make_paid_call(client):
    with pytest.raises(HTTPException) as failure:
        ImageGenRouter.generate("moon", provider="openai", model="chat-model")
    assert failure.value.status_code == 400
    client.return_value.images.generate.assert_not_called()


@pytest.mark.parametrize(
    "status, expected",
    [(400, 400), (401, 400), (403, 400), (429, 429), (500, 502)],
)
def test_provider_failures_are_bounded_and_redacted(client, status, expected):
    failure = RuntimeError("private prompt and secret upstream error")
    failure.status_code = status
    client.return_value.images.generate.side_effect = failure
    with pytest.raises(HTTPException) as result:
        ImageGenRouter.generate("moon", provider="openai", model="gpt-image-2.6-flare")
    assert result.value.status_code == expected
    assert "private prompt" not in result.value.detail
    assert client.return_value.images.generate.call_count == 1


def test_adapter_owns_default_without_vendor_specific_callers(monkeypatch):
    from guardian.image_gen import router
    from guardian.image_gen.base import ImageGenProvider

    class FutureAdapter(ImageGenProvider):
        name = "future-test"
        default_model = "future-model"
        supported_models = {default_model}

        def generate(self, prompt, model=None, **kwargs):
            assert model == self.default_model
            return b"future-image"

    monkeypatch.delenv("IMAGE_GEN_MODEL", raising=False)
    monkeypatch.setitem(router._PROVIDERS, FutureAdapter.name, FutureAdapter)
    assert (
        ImageGenRouter.generate("moon", provider=FutureAdapter.name) == b"future-image"
    )


def test_bounded_spend_denial_prevents_image_dispatch(client, monkeypatch):
    def deny():
        raise HTTPException(status_code=403, detail="Synthetic spend denial")

    monkeypatch.setattr(adapter, "deny_unqualified_spend", deny)
    with pytest.raises(HTTPException, match="Synthetic spend denial"):
        ImageGenRouter.generate("moon", provider="openai", model="gpt-image-2.6-flare")
    client.return_value.images.generate.assert_not_called()
