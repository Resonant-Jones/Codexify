from __future__ import annotations

import json

import pytest
import requests
from fastapi import HTTPException

from guardian.core.ai_router import (
    LOCAL_MODEL_MISSING_FAILURE_KIND,
    LOCAL_MODEL_RESOLUTION_ERROR,
    LOCAL_MODEL_UNAVAILABLE_FAILURE_KIND,
    call_alibaba,
    call_minimax,
    chat_with_ai,
)
from guardian.core.config import Settings


class _MockResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict:
        return self._payload


class _MockRawResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self.status_code = status_code
        self.content = json.dumps(payload).encode("utf-8")

    def json(self) -> dict:
        return json.loads(self.content.decode("utf-8"))


def _mock_local_inventory_request(
    available_models: list[str],
):
    def _handler(url: str, *args, **kwargs) -> _MockResponse:
        _ = (args, kwargs)
        if url.endswith("/api/tags"):
            return _MockResponse(
                {"models": [{"name": name} for name in available_models]}
            )
        return _MockResponse({"data": []}, status_code=404)

    return _handler


def _mock_alibaba_model_index(url, headers, timeout):
    assert url == "https://dashscope-us.aliyuncs.com/compatible-mode/v1/models"
    assert timeout == 3.0
    assert headers["Authorization"] == "Bearer test-alibaba-key"
    return _MockResponse({"data": [{"id": "qwen-plus"}]})


def test_call_alibaba_uses_default_dashscope_base_and_timeout(monkeypatch):
    captured: dict[str, object] = {}

    def _mock_post(url: str, *, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return _MockResponse(
            {"choices": [{"message": {"content": "Alibaba reply"}}]}
        )

    monkeypatch.setattr("guardian.core.ai_router.requests.post", _mock_post)
    monkeypatch.setattr(
        "guardian.core.ai_router.assert_egress_allowed",
        lambda *args, **kwargs: None,
    )

    settings = Settings(
        ALLOW_CLOUD_PROVIDERS=True,
        CODEXIFY_LOCAL_ONLY_MODE=False,
        CODEXIFY_EGRESS_ALLOWLIST="alibaba",
        ALIBABA_API_KEY="test-alibaba-key",
        ALIBABA_MODEL="qwen-plus",
        ALIBABA_TIMEOUT_SECONDS=17.5,
    )

    result = call_alibaba(
        [{"role": "user", "content": "Hello"}],
        "qwen-plus",
        settings=settings,
    )

    assert result == "Alibaba reply"
    assert (
        captured["url"]
        == "https://dashscope-us.aliyuncs.com/compatible-mode/v1/chat/completions"
    )
    assert captured["timeout"] == 17.5
    assert captured["json"] == {
        "model": "qwen-plus",
        "messages": [{"role": "user", "content": "Hello"}],
        "temperature": 0.7,
    }
    assert captured["headers"] == {
        "Authorization": "Bearer test-alibaba-key",
        "Content-Type": "application/json",
    }


def test_chat_with_ai_dispatches_to_alibaba_provider(monkeypatch):
    captured: dict[str, object] = {}

    def _mock_call_alibaba(messages, model: str, *, settings=None):
        captured["messages"] = messages
        captured["model"] = model
        captured["settings"] = settings
        return "Alibaba routed"

    monkeypatch.setattr(
        "guardian.core.ai_router.call_alibaba", _mock_call_alibaba
    )
    monkeypatch.setattr(
        "guardian.core.provider_registry.requests.get",
        _mock_alibaba_model_index,
    )

    settings = Settings(
        LLM_PROVIDER="alibaba",
        ALLOW_CLOUD_PROVIDERS=True,
        CODEXIFY_LOCAL_ONLY_MODE=False,
        CODEXIFY_EGRESS_ALLOWLIST="alibaba",
        ALIBABA_API_KEY="test-alibaba-key",
        ALIBABA_MODEL="qwen-plus",
    )
    messages = [{"role": "user", "content": "Ping"}]

    result = chat_with_ai(
        messages,
        model="qwen-plus",
        provider="alibaba",
        settings=settings,
    )

    assert result == "Alibaba routed"
    assert captured["messages"] == messages
    assert captured["model"] == "qwen-plus"
    assert captured["settings"] is settings


def test_chat_with_ai_local_falls_back_to_host_bridge_on_loopback_failure(
    monkeypatch,
):
    calls: list[str] = []

    def _mock_post(url: str, *, json, headers, timeout):
        _ = (json, headers, timeout)
        calls.append(url)
        if "127.0.0.1:11434" in url:
            raise requests.exceptions.ConnectionError("connection refused")
        return _MockRawResponse(
            {"message": {"content": "Local fallback reply"}}
        )

    monkeypatch.setattr("guardian.core.ai_router.requests.post", _mock_post)

    settings = Settings(
        LLM_PROVIDER="local",
        LOCAL_BASE_URL="http://127.0.0.1:11434",
        LOCAL_DOCKER_FALLBACK_BASE_URL="http://host.docker.internal:11434",
        LOCAL_LLM_MODEL="library2/ministral-3:8b",
        LOCAL_CHAT_MODEL="library2/ministral-3:8b",
    )

    result = chat_with_ai(
        [{"role": "user", "content": "hello"}],
        provider="local",
        model="library2/ministral-3:8b",
        settings=settings,
    )

    assert result == "Local fallback reply"
    assert calls[0].startswith("http://127.0.0.1:11434")
    assert any(
        "host.docker.internal:11434" in attempted_url for attempted_url in calls
    )


def test_chat_with_ai_local_failure_surfaces_attempt_diagnostics(monkeypatch):
    def _mock_post(url: str, *, json, headers, timeout):
        _ = (url, json, headers, timeout)
        raise requests.exceptions.ConnectionError("connection refused")

    monkeypatch.setattr("guardian.core.ai_router.requests.post", _mock_post)

    settings = Settings(
        LLM_PROVIDER="local",
        LOCAL_BASE_URL="http://127.0.0.1:11434",
        LOCAL_DOCKER_FALLBACK_BASE_URL="http://host.docker.internal:11434",
        LOCAL_LLM_MODEL="library2/ministral-3:8b",
        LOCAL_CHAT_MODEL="library2/ministral-3:8b",
    )

    with pytest.raises(HTTPException) as exc:
        chat_with_ai(
            [{"role": "user", "content": "hello"}],
            provider="local",
            model="library2/ministral-3:8b",
            settings=settings,
        )

    detail = str(exc.value.detail)
    assert exc.value.status_code == 502
    assert "Attempted endpoints" in detail
    assert "127.0.0.1:11434" in detail
    assert "host.docker.internal:11434" in detail


def test_chat_with_ai_local_uses_configured_endpoint_chain_order(monkeypatch):
    calls: list[str] = []

    def _mock_post(url: str, *, json, headers, timeout):
        _ = (json, headers, timeout)
        calls.append(url)
        if "primary.local:11434" in url:
            raise requests.exceptions.ConnectionError("connection refused")
        return _MockRawResponse({"message": {"content": "Local chain reply"}})

    monkeypatch.setattr("guardian.core.ai_router.requests.post", _mock_post)

    settings = Settings(
        LLM_PROVIDER="local",
        LOCAL_BASE_URL="http://host.docker.internal:11434/v1",
        CODEXIFY_LOCAL_ENDPOINT_CHAIN=(
            "http://primary.local:11434,http://secondary.local:11434"
        ),
        LOCAL_LLM_MODEL="library2/ministral-3:8b",
        LOCAL_CHAT_MODEL="library2/ministral-3:8b",
    )

    result = chat_with_ai(
        [{"role": "user", "content": "hello"}],
        provider="local",
        model="library2/ministral-3:8b",
        settings=settings,
    )

    assert result == "Local chain reply"
    assert calls[0].startswith("http://primary.local:11434")
    assert any(
        "secondary.local:11434" in attempted_url for attempted_url in calls
    )


def test_chat_with_ai_local_only_uses_local_chat_model_for_execution(
    monkeypatch,
):
    captured: dict[str, object] = {}

    def _mock_post(url: str, *, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        _ = (headers, timeout)
        return _MockRawResponse({"message": {"content": "Local chat reply"}})

    monkeypatch.setattr(
        "guardian.core.ai_router.requests.get",
        _mock_local_inventory_request(["qwen3.5:0.8b"]),
    )
    monkeypatch.setattr("guardian.core.ai_router.requests.post", _mock_post)

    settings = Settings(
        LLM_PROVIDER="local",
        CODEXIFY_LOCAL_ONLY_MODE=True,
        ALLOW_CLOUD_PROVIDERS=False,
        CODEXIFY_EGRESS_ALLOWLIST="",
        LOCAL_BASE_URL="http://127.0.0.1:11434",
        LOCAL_LLM_MODEL="library2/ministral-3:8b",
        LOCAL_CHAT_MODEL="qwen3.5:0.8b",
        DEFAULT_LOCAL_MODEL="library2/ministral-3:8b",
        LLM_MODEL="library2/ministral-3:8b",
    )

    result = chat_with_ai(
        [{"role": "user", "content": "hello"}],
        provider="local",
        model="library2/ministral-3:8b",
        settings=settings,
    )

    assert result == "Local chat reply"
    assert captured["json"]["model"] == "qwen3.5:0.8b"


def test_chat_with_ai_local_only_blank_local_chat_model_fails_clearly():
    settings = Settings(
        LLM_PROVIDER="local",
        CODEXIFY_LOCAL_ONLY_MODE=True,
        ALLOW_CLOUD_PROVIDERS=False,
        CODEXIFY_EGRESS_ALLOWLIST="",
        LOCAL_BASE_URL="http://127.0.0.1:11434",
        LOCAL_LLM_MODEL="library2/ministral-3:8b",
        LOCAL_CHAT_MODEL="",
        DEFAULT_LOCAL_MODEL="library2/ministral-3:8b",
        LLM_MODEL="library2/ministral-3:8b",
    )

    with pytest.raises(HTTPException) as exc:
        chat_with_ai(
            [{"role": "user", "content": "hello"}],
            provider="local",
            model="library2/ministral-3:8b",
            settings=settings,
        )

    assert exc.value.status_code == 400
    assert exc.value.detail["error"] == LOCAL_MODEL_RESOLUTION_ERROR
    assert exc.value.detail["failure_kind"] == LOCAL_MODEL_MISSING_FAILURE_KIND
    assert exc.value.detail["configured_source"] == "LOCAL_CHAT_MODEL"


def test_chat_with_ai_local_only_invalid_local_chat_model_fails_clearly(
    monkeypatch,
):
    monkeypatch.setattr(
        "guardian.core.ai_router.requests.get",
        _mock_local_inventory_request(["qwen2.5:7b"]),
    )

    settings = Settings(
        LLM_PROVIDER="local",
        CODEXIFY_LOCAL_ONLY_MODE=True,
        ALLOW_CLOUD_PROVIDERS=False,
        CODEXIFY_EGRESS_ALLOWLIST="",
        LOCAL_BASE_URL="http://127.0.0.1:11434",
        LOCAL_LLM_MODEL="library2/ministral-3:8b",
        LOCAL_CHAT_MODEL="qwen3.5:0.8b",
        DEFAULT_LOCAL_MODEL="library2/ministral-3:8b",
        LLM_MODEL="library2/ministral-3:8b",
    )

    with pytest.raises(HTTPException) as exc:
        chat_with_ai(
            [{"role": "user", "content": "hello"}],
            provider="local",
            model="library2/ministral-3:8b",
            settings=settings,
        )

    assert exc.value.status_code == 400
    assert exc.value.detail["error"] == LOCAL_MODEL_RESOLUTION_ERROR
    assert (
        exc.value.detail["failure_kind"] == LOCAL_MODEL_UNAVAILABLE_FAILURE_KIND
    )
    assert exc.value.detail["model"] == "qwen3.5:0.8b"


def test_call_alibaba_missing_key_surfaces_auth_config_failure():
    settings = Settings(
        ALLOW_CLOUD_PROVIDERS=True,
        CODEXIFY_LOCAL_ONLY_MODE=False,
        CODEXIFY_EGRESS_ALLOWLIST="alibaba",
        ALIBABA_API_KEY="",
        ALIBABA_API_BASE="https://dashscope-us.aliyuncs.com/compatible-mode/v1",
        ALIBABA_MODEL="qwen-plus",
    )

    with pytest.raises(HTTPException) as exc:
        call_alibaba(
            [{"role": "user", "content": "Hello"}],
            "qwen-plus",
            settings=settings,
        )

    assert exc.value.status_code == 400
    assert exc.value.detail["provider"] == "alibaba"
    assert exc.value.detail["failure_kind"] == "auth_config_error"
    assert (
        exc.value.detail["provider_error"]
        == "ALIBABA_API_KEY is not configured"
    )


def test_call_alibaba_timeout_surfaces_provider_timeout(monkeypatch):
    def _mock_post(url: str, *, json, headers, timeout):
        _ = (url, json, headers, timeout)
        raise requests.exceptions.Timeout("request timed out")

    monkeypatch.setattr("guardian.core.ai_router.requests.post", _mock_post)
    monkeypatch.setattr(
        "guardian.core.ai_router.assert_egress_allowed",
        lambda *args, **kwargs: None,
    )

    settings = Settings(
        ALLOW_CLOUD_PROVIDERS=True,
        CODEXIFY_LOCAL_ONLY_MODE=False,
        CODEXIFY_EGRESS_ALLOWLIST="alibaba",
        ALIBABA_API_KEY="test-alibaba-key",
        ALIBABA_API_BASE="https://dashscope-us.aliyuncs.com/compatible-mode/v1",
        ALIBABA_MODEL="qwen-plus",
        ALIBABA_TIMEOUT_SECONDS=5.0,
    )

    with pytest.raises(HTTPException) as exc:
        call_alibaba(
            [{"role": "user", "content": "Hello"}],
            "qwen-plus",
            settings=settings,
        )

    assert exc.value.status_code == 502
    detail = exc.value.detail
    assert detail["provider"] == "alibaba"
    assert detail["failure_kind"] == "provider_timeout"
    assert detail["transport_classification"] == "timeout"


def test_call_minimax_transport_failure_surfaces_transport_error(monkeypatch):
    def _mock_post(url: str, *, json, headers, timeout):
        _ = (url, json, headers, timeout)
        raise requests.exceptions.ConnectionError("connection refused")

    monkeypatch.setattr("guardian.core.ai_router.requests.post", _mock_post)
    monkeypatch.setattr(
        "guardian.core.ai_router.assert_egress_allowed",
        lambda *args, **kwargs: None,
    )

    settings = Settings(
        ALLOW_CLOUD_PROVIDERS=True,
        CODEXIFY_LOCAL_ONLY_MODE=False,
        CODEXIFY_EGRESS_ALLOWLIST="minimax",
        MINIMAX_API_KEY="test-minimax-key",
        MINIMAX_API_BASE="https://api.minimax.chat/v1",
        MINIMAX_API_FLAVOR="openai",
        MINIMAX_MODEL="abab6.5s-chat",
        MINIMAX_TIMEOUT_SECONDS=5.0,
    )

    with pytest.raises(HTTPException) as exc:
        call_minimax(
            [{"role": "user", "content": "Hi"}],
            "abab6.5s-chat",
            settings=settings,
        )

    assert exc.value.status_code == 502
    detail = exc.value.detail
    assert detail["provider"] == "minimax"
    assert detail["failure_kind"] == "transport_error"
    assert detail["transport_classification"] == "connection_refused"


def test_call_minimax_http_error_surfaces_provider_error_payload(monkeypatch):
    def _mock_post(url: str, *, json, headers, timeout):
        _ = (url, json, headers, timeout)
        return _MockResponse(
            {"error": {"message": "quota exceeded"}},
            status_code=429,
        )

    monkeypatch.setattr("guardian.core.ai_router.requests.post", _mock_post)
    monkeypatch.setattr(
        "guardian.core.ai_router.assert_egress_allowed",
        lambda *args, **kwargs: None,
    )

    settings = Settings(
        ALLOW_CLOUD_PROVIDERS=True,
        CODEXIFY_LOCAL_ONLY_MODE=False,
        CODEXIFY_EGRESS_ALLOWLIST="minimax",
        MINIMAX_API_KEY="test-minimax-key",
        MINIMAX_API_BASE="https://api.minimax.chat/v1",
        MINIMAX_API_FLAVOR="openai",
        MINIMAX_MODEL="abab6.5s-chat",
    )

    with pytest.raises(HTTPException) as exc:
        call_minimax(
            [{"role": "user", "content": "Hi"}],
            "abab6.5s-chat",
            settings=settings,
        )

    assert exc.value.status_code == 502
    detail = exc.value.detail
    assert detail["provider"] == "minimax"
    assert detail["failure_kind"] == "provider_http_error"
    assert detail["upstream_status"] == 429
    assert detail["provider_error"] == "quota exceeded"
