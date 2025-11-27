import pytest
from memoryos import utils


def test_build_llm_client_requires_api_key():
    with pytest.raises(ValueError, match="LLM_PROVIDER 'openai'"):
        utils.build_llm_client("openai", api_key=None)


def test_build_llm_client_openai(monkeypatch):
    captured = {}

    class DummyOpenAI:
        def __init__(self, *, api_key, base_url=None):
            captured["api_key"] = api_key
            captured["base_url"] = base_url

    monkeypatch.setattr(utils, "OpenAIClient", DummyOpenAI)

    client = utils.build_llm_client(
        "openai", api_key="abc", base_url="https://example"
    )

    assert isinstance(client, DummyOpenAI)
    assert captured == {"api_key": "abc", "base_url": "https://example"}


def test_build_llm_client_groq(monkeypatch):
    captured = {}

    class DummyGroq:
        def __init__(self, api_key, base_url=None, timeout=60):
            captured["api_key"] = api_key
            captured["base_url"] = base_url
            captured["timeout"] = timeout

    monkeypatch.setattr(utils, "GroqClient", DummyGroq)

    client = utils.build_llm_client("groq", api_key="token", base_url=None)

    assert isinstance(client, DummyGroq)
    assert captured["api_key"] == "token"
    # Builder should fall back to the default Groq endpoint when none provided
    assert captured["base_url"] == utils.DEFAULT_GROQ_BASE_URL
