from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
import requests
from fastapi import HTTPException

import guardian.core.ai_router as ai_router
import guardian.core.provider_registry as provider_registry
import guardian.core.supported_profile as supported_profile
from guardian.core.ai_router import (
    LOCAL_MODEL_MISSING_FAILURE_KIND,
    LOCAL_MODEL_RESOLUTION_ERROR,
    call_alibaba,
    call_local,
    call_minimax,
    chat_with_ai,
    resolve_local_execution_model,
    stream_local,
)
from guardian.core.config import Settings
from guardian.protocol_tokens import (
    CompletionTerminalStatus,
    GuardianProviderFailureKind,
    GuardianProviderTransportClassification,
)
from guardian.providers.whooshd_tool_adapter import WhooshdStructuredResponse

SUPPORTED_LOCAL_BASE_URL = "http://host.docker.internal:8000/v1"


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


class _MockStreamingResponse:
    def __init__(self, lines: list[bytes], status_code: int = 200) -> None:
        self._lines = lines
        self.status_code = status_code
        self.closed = False

    def iter_lines(self, decode_unicode: bool = False):
        _ = decode_unicode
        yield from self._lines

    def close(self) -> None:
        self.closed = True


def _drain_stream_with_terminal(stream):
    tokens: list[str] = []
    iterator = iter(stream)
    while True:
        try:
            tokens.append(next(iterator))
        except StopIteration as stop:
            return tokens, stop.value


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


def _disable_supported_profile(monkeypatch) -> None:
    monkeypatch.setattr(
        supported_profile,
        "get_active_supported_profile",
        lambda: None,
    )


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

    monkeypatch.setattr(ai_router.requests, "post", _mock_post)
    monkeypatch.setattr(
        ai_router,
        "assert_egress_allowed",
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
    _disable_supported_profile(monkeypatch)
    captured: dict[str, object] = {}

    def _mock_call_alibaba(messages, model: str, *, settings=None):
        captured["messages"] = messages
        captured["model"] = model
        captured["settings"] = settings
        return "Alibaba routed"

    monkeypatch.setattr(ai_router, "call_alibaba", _mock_call_alibaba)
    monkeypatch.setattr(
        provider_registry.requests,
        "get",
        _mock_alibaba_model_index,
    )

    settings = Settings(
        LLM_PROVIDER="alibaba",
        ALLOW_CLOUD_PROVIDERS=True,
        CODEXIFY_LOCAL_ONLY_MODE=False,
        CODEXIFY_EGRESS_ALLOWLIST="alibaba",
        ALIBABA_API_KEY="test-alibaba-key",
        ALIBABA_API_BASE="https://dashscope-us.aliyuncs.com/compatible-mode/v1",
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


def test_strict_explicit_provider_model_preserves_exact_model_and_token_bound(
    monkeypatch,
):
    _disable_supported_profile(monkeypatch)
    captured: dict[str, object] = {}

    def _mock_call_openai(
        messages,
        model: str,
        *,
        temperature=None,
        max_tokens=None,
        settings=None,
    ):
        captured["messages"] = messages
        captured["model"] = model
        captured["temperature"] = temperature
        captured["max_tokens"] = max_tokens
        captured["settings"] = settings
        return "strict result"

    monkeypatch.setattr(ai_router, "call_openai", _mock_call_openai)
    settings = Settings(LLM_PROVIDER="openai", OPENAI_API_KEY="test-key")

    result = chat_with_ai(
        [{"role": "user", "content": "Review this."}],
        provider="openai",
        model="gpt-4.1",
        temperature=0,
        max_tokens=4096,
        strict_provider_model=True,
        strict_single_request=True,
        settings=settings,
    )

    assert result == "strict result"
    assert captured["model"] == "gpt-4.1"
    assert captured["temperature"] == 0
    assert captured["max_tokens"] == 4096
    assert captured["settings"] is settings


def test_chat_with_ai_dispatches_to_deepseek_provider(monkeypatch):
    _disable_supported_profile(monkeypatch)
    captured: dict[str, object] = {}

    def _mock_post(url: str, *, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return _MockResponse(
            {"choices": [{"message": {"content": "DeepSeek routed"}}]}
        )

    monkeypatch.setattr(ai_router.requests, "post", _mock_post)

    settings = Settings(
        LLM_PROVIDER="deepseek",
        ALLOW_CLOUD_PROVIDERS=True,
        CODEXIFY_LOCAL_ONLY_MODE=False,
        CODEXIFY_EGRESS_ALLOWLIST="deepseek",
        DEEPSEEK_API_KEY="test-deepseek-key",
        DEEPSEEK_BASE_URL="https://api.deepseek.com",
        DEEPSEEK_CHAT_MODEL="deepseek-v4-flash",
    )
    messages = [{"role": "user", "content": "Ping"}]

    result = chat_with_ai(
        messages,
        provider="deepseek",
        settings=settings,
    )

    assert result == "DeepSeek routed"
    assert captured["url"] == "https://api.deepseek.com/v1/chat/completions"
    assert captured["json"] == {
        "model": "deepseek-v4-flash",
        "messages": messages,
        "thinking": {"type": "disabled"},
        "temperature": 0.7,
    }
    assert captured["headers"] == {
        "Authorization": "Bearer test-deepseek-key",
        "Content-Type": "application/json",
    }


def test_deepseek_health_capability_uses_an_opaque_native_alias_without_tool_choice(
    monkeypatch,
):
    _disable_supported_profile(monkeypatch)
    captured: dict[str, object] = {}

    def _mock_post(url: str, *, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        _ = (headers, timeout)
        return _MockResponse(
            {"choices": [{"message": {"content": "Plain answer."}}]}
        )

    monkeypatch.setattr(ai_router.requests, "post", _mock_post)
    settings = Settings(
        LLM_PROVIDER="deepseek",
        ALLOW_CLOUD_PROVIDERS=True,
        CODEXIFY_LOCAL_ONLY_MODE=False,
        CODEXIFY_EGRESS_ALLOWLIST="deepseek",
        DEEPSEEK_API_KEY="test-deepseek-key",
        DEEPSEEK_BASE_URL="https://api.deepseek.com",
        DEEPSEEK_CHAT_MODEL="deepseek-v4-flash",
    )
    health_tool = {
        "command_id": "op::health_health_get",
        "description": "Read the current Guardian health status (GET /health).",
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "maxProperties": 0,
        },
    }

    result = chat_with_ai(
        [{"role": "user", "content": "Ping"}],
        provider="deepseek",
        settings=settings,
        tools=[health_tool],
    )

    assert result == "Plain answer."
    payload = captured["json"]
    assert isinstance(payload, dict)
    assert payload["tools"] == [
        {
            "type": "function",
            "function": {
                "name": "codexify_tool_0",
                "description": health_tool["description"],
                "parameters": health_tool["input_schema"],
            },
        }
    ]
    assert "op::health_health_get" not in repr(payload["tools"])
    assert "tool_choice" not in payload


def test_chat_with_ai_local_falls_back_to_host_bridge_on_loopback_failure(
    monkeypatch,
):
    _disable_supported_profile(monkeypatch)
    calls: list[str] = []

    def _mock_post(url: str, *, json, headers, timeout):
        _ = (json, headers, timeout)
        calls.append(url)
        if "127.0.0.1:11434" in url:
            raise requests.exceptions.ConnectionError("connection refused")
        return _MockRawResponse(
            {"message": {"content": "Local fallback reply"}}
        )

    monkeypatch.setattr(ai_router.requests, "post", _mock_post)

    settings = Settings(
        LLM_PROVIDER="local",
        LOCAL_BASE_URL="http://127.0.0.1:11434",
        LOCAL_DOCKER_FALLBACK_BASE_URL="http://host.docker.internal:11434",
        CODEXIFY_LOCAL_DOCKER_FALLBACK_ENABLED=True,
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


def test_stream_local_strict_mode_pins_configured_model_over_registered_whooshd_profile(
    monkeypatch,
):
    _disable_supported_profile(monkeypatch)
    captured: dict[str, object] = {}

    def _mock_post(url: str, *, json, headers, stream, timeout):
        captured["url"] = url
        captured["json"] = json
        _ = (headers, stream, timeout)
        return _MockStreamingResponse(
            [
                b'data: {"choices":[{"delta":{"content":"Whoosh"}}]}',
                b'data: {"choices":[{"delta":{"content":"d"}}]}',
                b"data: [DONE]",
            ]
        )

    monkeypatch.setattr(ai_router.requests, "post", _mock_post)

    settings = Settings(
        LLM_PROVIDER="local",
        CODEXIFY_LOCAL_ONLY_MODE=True,
        LOCAL_BASE_URL="http://host.docker.internal:8000/v1",
        LOCAL_LLM_MODEL="library2/ministral-3:8b",
        LOCAL_CHAT_MODEL="library2/ministral-3:8b",
    )

    tokens = list(
        stream_local(
            [{"role": "user", "content": "hello"}],
            "gemma-4-12b-it-optiq-4bit",
            settings=settings,
        )
    )

    assert tokens == ["Whoosh", "d"]
    assert captured["json"]["model"] == "library2/ministral-3:8b"
    assert captured["url"] == (
        "http://host.docker.internal:8000/v1/chat/completions"
    )


def test_stream_local_preserves_done_terminal_evidence(monkeypatch):
    _disable_supported_profile(monkeypatch)

    monkeypatch.setattr(
        ai_router.requests,
        "post",
        lambda *_args, **_kwargs: _MockStreamingResponse(
            [
                b'data: {"choices":[{"delta":{"content":"answer"},"finish_reason":"stop"}]}',
                b"data: [DONE]",
            ]
        ),
    )
    settings = Settings(
        LLM_PROVIDER="local",
        CODEXIFY_LOCAL_ONLY_MODE=True,
        LOCAL_BASE_URL=SUPPORTED_LOCAL_BASE_URL,
        LOCAL_CHAT_MODEL="test-model",
        LOCAL_LLM_MODEL="test-model",
    )

    tokens, terminal = _drain_stream_with_terminal(
        stream_local(
            [{"role": "user", "content": "hello"}],
            "test-model",
            settings=settings,
        )
    )

    assert tokens == ["answer"]
    assert terminal.status is CompletionTerminalStatus.SUCCESS
    assert terminal.explicit_provider_terminal_observed is True
    assert terminal.finish_reason == "stop"


def test_stream_local_classifies_eof_without_done_as_incomplete(monkeypatch):
    _disable_supported_profile(monkeypatch)

    monkeypatch.setattr(
        ai_router.requests,
        "post",
        lambda *_args, **_kwargs: _MockStreamingResponse(
            [b'data: {"choices":[{"delta":{"content":"partial"}}]}']
        ),
    )
    settings = Settings(
        LLM_PROVIDER="local",
        CODEXIFY_LOCAL_ONLY_MODE=True,
        LOCAL_BASE_URL=SUPPORTED_LOCAL_BASE_URL,
        LOCAL_CHAT_MODEL="test-model",
        LOCAL_LLM_MODEL="test-model",
    )

    tokens, terminal = _drain_stream_with_terminal(
        stream_local(
            [{"role": "user", "content": "hello"}],
            "test-model",
            settings=settings,
        )
    )

    assert tokens == ["partial"]
    assert terminal.status is CompletionTerminalStatus.STREAM_INCOMPLETE
    assert terminal.retry_permitted is False


def test_stream_local_strict_mode_pins_configured_model_over_registered_whooshd_qat_profile(
    monkeypatch,
):
    _disable_supported_profile(monkeypatch)
    captured: dict[str, object] = {}

    def _mock_post(url: str, *, json, headers, stream, timeout):
        captured["url"] = url
        captured["json"] = json
        _ = (headers, stream, timeout)
        return _MockStreamingResponse(
            [
                b'data: {"choices":[{"delta":{"content":"QAT"}}]}',
                b"data: [DONE]",
            ]
        )

    monkeypatch.setattr(ai_router.requests, "post", _mock_post)

    settings = Settings(
        LLM_PROVIDER="local",
        CODEXIFY_LOCAL_ONLY_MODE=True,
        LOCAL_BASE_URL="http://host.docker.internal:8000/v1",
        LOCAL_LLM_MODEL="library2/ministral-3:8b",
        LOCAL_CHAT_MODEL="library2/ministral-3:8b",
    )

    tokens = list(
        stream_local(
            [{"role": "user", "content": "hello"}],
            "gemma-4-12b-it-qat-4bit",
            settings=settings,
        )
    )

    assert tokens == ["QAT"]
    assert captured["json"]["model"] == "library2/ministral-3:8b"
    assert captured["url"] == (
        "http://host.docker.internal:8000/v1/chat/completions"
    )


def test_chat_with_ai_local_failure_surfaces_attempt_diagnostics(monkeypatch):
    _disable_supported_profile(monkeypatch)

    def _mock_post(url: str, *, json, headers, timeout):
        _ = (url, json, headers, timeout)
        raise requests.exceptions.ConnectionError("connection refused")

    monkeypatch.setattr(ai_router.requests, "post", _mock_post)

    settings = Settings(
        LLM_PROVIDER="local",
        LOCAL_BASE_URL="http://127.0.0.1:11434",
        LOCAL_DOCKER_FALLBACK_BASE_URL="http://host.docker.internal:11434",
        CODEXIFY_LOCAL_DOCKER_FALLBACK_ENABLED=True,
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

    monkeypatch.setattr(ai_router.requests, "post", _mock_post)

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


def test_chat_with_ai_non_strict_local_mode_ignores_stale_local_chat_model(
    monkeypatch,
):
    _disable_supported_profile(monkeypatch)
    captured: dict[str, object] = {}

    def _mock_post(url: str, *, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        _ = (headers, timeout)
        return _MockRawResponse({"message": {"content": "Non-strict reply"}})

    monkeypatch.setattr(ai_router.requests, "post", _mock_post)

    settings = Settings(
        LLM_PROVIDER="local",
        CODEXIFY_LOCAL_ONLY_MODE=False,
        ALLOW_CLOUD_PROVIDERS=False,
        CODEXIFY_EGRESS_ALLOWLIST="",
        LOCAL_BASE_URL=SUPPORTED_LOCAL_BASE_URL,
        LOCAL_LLM_MODEL="llama3.2:3b",
        LOCAL_CHAT_MODEL="qwen3.5:0.8b",
        DEFAULT_LOCAL_MODEL="llama3.2:3b",
        LLM_MODEL="llama3.2:3b",
    )

    result = chat_with_ai(
        [{"role": "user", "content": "hello"}],
        provider="local",
        settings=settings,
    )

    assert result == "Non-strict reply"
    assert captured["json"]["model"] == "llama3.2:3b"


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
        ai_router.requests,
        "get",
        _mock_local_inventory_request(["qwen3.5:0.8b"]),
    )
    monkeypatch.setattr(ai_router.requests, "post", _mock_post)

    settings = Settings(
        LLM_PROVIDER="local",
        CODEXIFY_LOCAL_ONLY_MODE=True,
        ALLOW_CLOUD_PROVIDERS=False,
        CODEXIFY_EGRESS_ALLOWLIST="",
        LOCAL_BASE_URL=SUPPORTED_LOCAL_BASE_URL,
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
        LOCAL_BASE_URL=SUPPORTED_LOCAL_BASE_URL,
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


def test_dual_provider_profile_keeps_local_chat_model_authoritative(
    monkeypatch,
):
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-whooshd-deepseek-web")
    settings = Settings(
        LLM_PROVIDER="local",
        CODEXIFY_LOCAL_ONLY_MODE=False,
        ALLOW_CLOUD_PROVIDERS=True,
        CODEXIFY_EGRESS_ALLOWLIST="deepseek",
        LOCAL_BASE_URL=SUPPORTED_LOCAL_BASE_URL,
        LOCAL_PROVIDER_VENDOR="whooshd",
        LOCAL_CHAT_MODEL="gemma-4-12b-it-qat-4bit",
        LOCAL_LLM_MODEL="gemma-4-12b-it-qat-4bit",
    )

    result = resolve_local_execution_model(
        settings=settings,
        requested_model="model-retained-from-another-profile",
    )

    assert result.ok
    assert result.strict is True
    assert result.model == "gemma-4-12b-it-qat-4bit"
    assert result.source == "LOCAL_CHAT_MODEL"


def test_chat_with_ai_local_only_invalid_local_chat_model_fails_clearly(
    monkeypatch,
):
    _disable_supported_profile(monkeypatch)
    monkeypatch.setattr(
        ai_router.requests,
        "get",
        _mock_local_inventory_request(["qwen2.5:7b"]),
    )

    settings = Settings(
        LLM_PROVIDER="local",
        CODEXIFY_LOCAL_ONLY_MODE=True,
        ALLOW_CLOUD_PROVIDERS=False,
        CODEXIFY_EGRESS_ALLOWLIST="",
        LOCAL_BASE_URL=SUPPORTED_LOCAL_BASE_URL,
        LOCAL_PROVIDER_VENDOR="whooshd",
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
    assert exc.value.detail["failure_kind"] == (
        ai_router.WHOOSHD_CONFIGURED_MODEL_NOT_ADVERTISED_REASON
    )
    assert exc.value.detail["model"] == "qwen3.5:0.8b"


def test_call_local_local_only_uses_resolved_model_for_execution(monkeypatch):
    captured: dict[str, object] = {}

    def _mock_post(url: str, *, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        _ = (headers, timeout)
        return _MockRawResponse({"message": {"content": "Local call reply"}})

    monkeypatch.setattr(ai_router.requests, "post", _mock_post)

    settings = Settings(
        LLM_PROVIDER="local",
        CODEXIFY_LOCAL_ONLY_MODE=True,
        ALLOW_CLOUD_PROVIDERS=False,
        CODEXIFY_EGRESS_ALLOWLIST="",
        LOCAL_BASE_URL=SUPPORTED_LOCAL_BASE_URL,
        LOCAL_LLM_MODEL="library2/ministral-3:8b",
        LOCAL_CHAT_MODEL="qwen3.5:0.8b",
        DEFAULT_LOCAL_MODEL="library2/ministral-3:8b",
        LLM_MODEL="library2/ministral-3:8b",
    )

    result = call_local(
        [{"role": "user", "content": "hello"}],
        "library2/ministral-3:8b",
        settings=settings,
    )

    assert result == "Local call reply"
    assert captured["json"]["model"] == "qwen3.5:0.8b"


def test_call_local_uses_local_max_tokens_when_not_explicitly_provided(
    monkeypatch,
):
    captured: dict[str, object] = {}

    def _mock_post(url: str, *, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        _ = (headers, timeout)
        return _MockRawResponse({"message": {"content": "Local call reply"}})

    monkeypatch.setattr(ai_router.requests, "post", _mock_post)

    settings = SimpleNamespace(
        LLM_PROVIDER="local",
        CODEXIFY_LOCAL_ONLY_MODE=True,
        ALLOW_CLOUD_PROVIDERS=False,
        CODEXIFY_EGRESS_ALLOWLIST="",
        LOCAL_BASE_URL=SUPPORTED_LOCAL_BASE_URL,
        LOCAL_LLM_MODEL="library2/ministral-3:8b",
        LOCAL_CHAT_MODEL="qwen3.5:0.8b",
        DEFAULT_LOCAL_MODEL="library2/ministral-3:8b",
        LLM_MODEL="library2/ministral-3:8b",
        LOCAL_API_KEY="local",
        LOCAL_MAX_TOKENS=321,
    )

    result = call_local(
        [{"role": "user", "content": "hello"}],
        "library2/ministral-3:8b",
        settings=settings,
    )

    assert result == "Local call reply"
    assert captured["json"]["model"] == "qwen3.5:0.8b"
    assert captured["json"]["max_tokens"] == 321


def test_stream_local_local_only_uses_resolved_model_for_execution(
    monkeypatch,
):
    captured: dict[str, object] = {}

    def _mock_post(url: str, *, json, headers, stream, timeout):
        captured["url"] = url
        captured["json"] = json
        _ = (headers, stream, timeout)
        return _MockStreamingResponse(
            [
                b'data: {"choices":[{"delta":{"content":"Local "}}]}',
                b'data: {"choices":[{"delta":{"content":"stream"}}]}',
                b"data: [DONE]",
            ]
        )

    monkeypatch.setattr(ai_router.requests, "post", _mock_post)

    settings = Settings(
        LLM_PROVIDER="local",
        CODEXIFY_LOCAL_ONLY_MODE=True,
        ALLOW_CLOUD_PROVIDERS=False,
        CODEXIFY_EGRESS_ALLOWLIST="",
        LOCAL_BASE_URL=SUPPORTED_LOCAL_BASE_URL,
        LOCAL_LLM_MODEL="library2/ministral-3:8b",
        LOCAL_CHAT_MODEL="qwen3.5:0.8b",
        DEFAULT_LOCAL_MODEL="library2/ministral-3:8b",
        LLM_MODEL="library2/ministral-3:8b",
    )

    result = list(
        stream_local(
            [{"role": "user", "content": "hello"}],
            "library2/ministral-3:8b",
            settings=settings,
        )
    )

    assert result == ["Local ", "stream"]
    assert captured["json"]["model"] == "qwen3.5:0.8b"


def _whooshd_stage_2e_settings() -> Settings:
    return Settings(
        LLM_PROVIDER="local",
        CODEXIFY_LOCAL_ONLY_MODE=True,
        ALLOW_CLOUD_PROVIDERS=False,
        CODEXIFY_EGRESS_ALLOWLIST="",
        LOCAL_BASE_URL=SUPPORTED_LOCAL_BASE_URL,
        LOCAL_PROVIDER_VENDOR="whooshd",
        LOCAL_CHAT_MODEL="gemma-4-12b-it-qat-4bit",
        LOCAL_LLM_MODEL="gemma-4-12b-it-qat-4bit",
        DEFAULT_LOCAL_MODEL="gemma-4-12b-it-qat-4bit",
        LLM_MODEL="gemma-4-12b-it-qat-4bit",
    )


def _whooshd_stage_2e_provenance() -> dict:
    return {
        "schema_version": "whooshd.runtime.v1",
        "request_id": "req-stage2e",
        "requested_model_id": "gemma-4-12b-it-qat-4bit",
        "advertised_model_id": "gemma-4-12b-it-qat-4bit",
        "resolved_model_id": "gemma-4-12b-it-qat-4bit",
        "backend_reported_model_id": "gemma-4-12b-it-qat-4bit",
        "runtime_kind": "mlx_vlm",
        "adapter_name": "mlx-vlm",
        "resolution_source": "authoritative_registry",
        "execution_mode": "managed_sidecar",
        "streaming": False,
        "queued": False,
        "batched": False,
        "model_lifecycle": "ready",
        "whooshd_version": "0.1.0rc1",
    }


def test_call_local_uses_strict_structured_payload_only_for_exact_stage_2e_target(
    monkeypatch,
):
    _disable_supported_profile(monkeypatch)
    captured: dict[str, object] = {}

    def _mock_post(url: str, *, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return _MockRawResponse(
            {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": '{"kind":"assistant","text":"Hello","command_id":null,"arguments":{}}'
                        },
                    }
                ],
                "runtime_provenance": _whooshd_stage_2e_provenance(),
            }
        )

    monkeypatch.setattr(ai_router.requests, "post", _mock_post)
    result = call_local(
        [{"role": "user", "content": "hello"}],
        "gemma-4-12b-it-qat-4bit",
        settings=_whooshd_stage_2e_settings(),
        tools=[
            {
                "command_id": "op::lookup_widget",
                "description": "Return a synthetic widget status.",
                "input_schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["widget_id"],
                    "properties": {
                        "widget_id": {"type": "string", "enum": ["alpha"]}
                    },
                },
            }
        ],
    )

    assert isinstance(result, WhooshdStructuredResponse)
    payload = captured["json"]
    assert payload["model"] == "gemma-4-12b-it-qat-4bit"
    assert payload["stream"] is False
    assert payload["temperature"] == 0
    assert payload["seed"] == 20260809
    assert payload["response_format"]["type"] == "json_schema"
    assert "tools" not in payload
    assert "tool_choice" not in payload
    assert "function_call" not in payload
    assert (
        payload["response_format"]["json_schema"]["schema"]["oneOf"][1]["properties"]["command_id"]
        == {"const": "op::lookup_widget"}
    )
    assert payload["messages"][0]["role"] == "system"
    assert "op::lookup_widget" in payload["messages"][0]["content"]
    normalized = ai_router.normalize_completion_output(result)
    assert normalized.kind == "assistant"
    assert normalized.text == "Hello"
    assert normalized.provider == "whooshd"


def test_call_local_keeps_no_tools_whooshd_chat_unstructured(monkeypatch):
    _disable_supported_profile(monkeypatch)
    captured: dict[str, object] = {}

    def _mock_post(url: str, *, json, headers, timeout):
        _ = (url, headers, timeout)
        captured["json"] = json
        return _MockRawResponse(
            {"choices": [{"message": {"content": "ordinary response"}}]}
        )

    monkeypatch.setattr(ai_router.requests, "post", _mock_post)
    result = call_local(
        [{"role": "user", "content": "hello"}],
        "gemma-4-12b-it-qat-4bit",
        settings=_whooshd_stage_2e_settings(),
        tools=None,
    )

    assert result == "ordinary response"
    payload = captured["json"]
    assert "response_format" not in payload
    assert "seed" not in payload
    assert payload["messages"] == [{"role": "user", "content": "hello"}]


def test_call_local_rejects_multiple_stage_2e_tools_before_post(monkeypatch):
    _disable_supported_profile(monkeypatch)
    monkeypatch.setattr(
        ai_router.requests,
        "post",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("provider inference should not run")
        ),
    )
    tools = [
        {"command_id": "op::one", "description": "one"},
        {"command_id": "op::two", "description": "two"},
    ]

    with pytest.raises(HTTPException) as exc:
        call_local(
            [{"role": "user", "content": "hello"}],
            "gemma-4-12b-it-qat-4bit",
            settings=_whooshd_stage_2e_settings(),
            tools=tools,
        )

    assert exc.value.status_code == 400
    assert "exactly one" in exc.value.detail


def test_call_local_timeout_surfaces_provider_timeout(monkeypatch):
    def _mock_post(url: str, *, json, headers, timeout):
        _ = (url, json, headers, timeout)
        raise requests.exceptions.ReadTimeout("read timed out")

    monkeypatch.setattr(ai_router.requests, "post", _mock_post)

    settings = Settings(
        LLM_PROVIDER="local",
        CODEXIFY_LOCAL_ONLY_MODE=True,
        ALLOW_CLOUD_PROVIDERS=False,
        CODEXIFY_EGRESS_ALLOWLIST="",
        LOCAL_BASE_URL=SUPPORTED_LOCAL_BASE_URL,
        LOCAL_CHAT_MODEL="library2/ministral-3:8b",
        LOCAL_LLM_MODEL="library2/ministral-3:8b",
        DEFAULT_LOCAL_MODEL="library2/ministral-3:8b",
        LLM_MODEL="library2/ministral-3:8b",
        LLM_REQUEST_TIMEOUT_SECONDS=60,
    )

    with pytest.raises(HTTPException) as exc:
        call_local(
            [{"role": "user", "content": "hello"}],
            "library2/ministral-3:8b",
            settings=settings,
        )

    assert exc.value.status_code == 502
    detail = exc.value.detail
    assert detail["provider"] == "local"
    assert (
        detail["failure_kind"]
        == GuardianProviderFailureKind.PROVIDER_TIMEOUT.value
    )
    assert (
        detail["transport_classification"]
        == GuardianProviderTransportClassification.TIMEOUT.value
    )
    assert detail["local_runtime"]["profile"] == "default"
    assert detail["local_runtime"]["read_timeout_seconds"] == 60.0


def test_stream_local_timeout_surfaces_provider_timeout(monkeypatch):
    def _mock_post(url: str, *, json, headers, stream, timeout):
        _ = (url, json, headers, stream, timeout)
        raise requests.exceptions.ReadTimeout("read timed out")

    monkeypatch.setattr(ai_router.requests, "post", _mock_post)

    settings = Settings(
        LLM_PROVIDER="local",
        CODEXIFY_LOCAL_ONLY_MODE=True,
        ALLOW_CLOUD_PROVIDERS=False,
        CODEXIFY_EGRESS_ALLOWLIST="",
        LOCAL_BASE_URL=SUPPORTED_LOCAL_BASE_URL,
        LOCAL_CHAT_MODEL="library2/ministral-3:8b",
        LOCAL_LLM_MODEL="library2/ministral-3:8b",
        DEFAULT_LOCAL_MODEL="library2/ministral-3:8b",
        LLM_MODEL="library2/ministral-3:8b",
        LLM_REQUEST_TIMEOUT_SECONDS=60,
    )

    with pytest.raises(HTTPException) as exc:
        list(
            stream_local(
                [{"role": "user", "content": "hello"}],
                "library2/ministral-3:8b",
                settings=settings,
            )
        )

    assert exc.value.status_code == 502
    detail = exc.value.detail
    assert detail["provider"] == "local"
    assert (
        detail["failure_kind"]
        == GuardianProviderFailureKind.PROVIDER_TIMEOUT.value
    )
    assert (
        detail["transport_classification"]
        == GuardianProviderTransportClassification.TIMEOUT.value
    )
    assert detail["local_runtime"]["profile"] == "default"
    assert detail["local_runtime"]["read_timeout_seconds"] == 60.0


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

    monkeypatch.setattr(ai_router.requests, "post", _mock_post)
    monkeypatch.setattr(
        ai_router,
        "assert_egress_allowed",
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
    assert (
        detail["failure_kind"]
        == GuardianProviderFailureKind.PROVIDER_TIMEOUT.value
    )
    assert (
        detail["transport_classification"]
        == GuardianProviderTransportClassification.TIMEOUT.value
    )


def test_call_minimax_transport_failure_surfaces_transport_error(monkeypatch):
    def _mock_post(url: str, *, json, headers, timeout):
        _ = (url, json, headers, timeout)
        raise requests.exceptions.ConnectionError("connection refused")

    monkeypatch.setattr(ai_router.requests, "post", _mock_post)
    monkeypatch.setattr(
        ai_router,
        "assert_egress_allowed",
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
    assert (
        detail["failure_kind"]
        == GuardianProviderFailureKind.TRANSPORT_ERROR.value
    )
    assert (
        detail["transport_classification"]
        == GuardianProviderTransportClassification.CONNECTION_REFUSED.value
    )


def test_call_minimax_http_error_surfaces_provider_error_payload(monkeypatch):
    def _mock_post(url: str, *, json, headers, timeout):
        _ = (url, json, headers, timeout)
        return _MockResponse(
            {"error": {"message": "quota exceeded"}},
            status_code=429,
        )

    monkeypatch.setattr(ai_router.requests, "post", _mock_post)
    monkeypatch.setattr(
        ai_router,
        "assert_egress_allowed",
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
