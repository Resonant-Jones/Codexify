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


def test_gpt_image_uses_modern_parameters_without_paid_retries(client):
    image = ImageGenRouter.generate(
        "a moon", provider="openai", model="gpt-image-2.5-sunburst"
    )
    assert image == b"png"
    client.assert_called_once_with(timeout=180, max_retries=0)
    client.return_value.images.generate.assert_called_once_with(
        prompt="a moon",
        model="gpt-image-2.5-sunburst",
        size="1024x1024",
        n=1,
        output_format="png",
        quality="medium",
    )


def test_explicit_provider_wins_over_environment(client, monkeypatch):
    monkeypatch.setenv("IMAGE_GEN_PROVIDER", "local")
    assert (
        ImageGenRouter.generate(
            "moon", provider="openai", model="gpt-image-1-mini"
        )
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


def test_legacy_api_shape_remains_compatible(client):
    ImageGenRouter.generate("moon", provider="openai", model="dall-e-3")
    assert (
        client.return_value.images.generate.call_args.kwargs["response_format"]
        == "b64_json"
    )


def test_local_only_blocks_cloud_before_client_construction(
    client, monkeypatch
):
    monkeypatch.setenv("CODEXIFY_LOCAL_ONLY_MODE", "true")
    with pytest.raises(HTTPException) as failure:
        ImageGenRouter.generate(
            "moon", provider="openai", model="gpt-image-1-mini"
        )
    assert failure.value.status_code == 403
    client.assert_not_called()


def test_catalog_exposes_configured_state_without_a_paid_probe(client):
    catalog = ImageGenRouter.catalog()
    provider = catalog["providers"][0]
    assert provider["id"] == "openai"
    assert provider["available"]
    assert provider["model_aliases"]["sunburst"] in provider["models"]
    assert all(
        not item["available"]
        for item in catalog["providers"]
        if item["id"] != "openai"
    )
    assert "synthetic-test-key" not in str(catalog)
    client.assert_not_called()


@pytest.mark.parametrize("payload", ["%%%", ""])
def test_malformed_provider_response_is_failure(client, payload):
    client.return_value.images.generate.return_value.data[0].b64_json = payload
    with pytest.raises(HTTPException) as failure:
        ImageGenRouter.generate(
            "moon", provider="openai", model="gpt-image-1-mini"
        )
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
        ImageGenRouter.generate(
            "moon", provider="openai", model="gpt-image-1-mini"
        )
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
        ImageGenRouter.generate("moon", provider=FutureAdapter.name)
        == b"future-image"
    )


def test_bounded_spend_denial_prevents_image_dispatch(client, monkeypatch):
    def deny():
        raise HTTPException(status_code=403, detail="Synthetic spend denial")
    monkeypatch.setattr(adapter, "deny_unqualified_spend", deny)
    with pytest.raises(HTTPException, match="Synthetic spend denial"):
        ImageGenRouter.generate("moon", provider="openai", model="gpt-image-1-mini")
    client.return_value.images.generate.assert_not_called()
