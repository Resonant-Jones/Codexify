from __future__ import annotations

from guardian.core.ai_router import call_alibaba, chat_with_ai
from guardian.core.config import Settings


class _MockResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict:
        return self._payload


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
