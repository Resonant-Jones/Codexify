"""Contract tests for the Groq Search-as-RAG adapter (Remote Recall)."""

from __future__ import annotations

from typing import Any

from guardian.core.config import Settings
from guardian.protocol_tokens import RemoteRecallFailureReason
from guardian.web.contracts import SearchProviderRequest
from guardian.web.groq_search_adapter import (
    DEFAULT_GROQ_WEB_SEARCH_MODEL,
    SUPPORTED_GROQ_WEB_SEARCH_MODELS,
    GroqSearchAdapter,
)


def _enabled_settings(
    *,
    local_only: bool = False,
    allow_cloud: bool = True,
    allowlist: str = "groq",
    api_key: str = "test-key",
    model: str = DEFAULT_GROQ_WEB_SEARCH_MODEL,
) -> Settings:
    return Settings(
        CODEXIFY_LOCAL_ONLY_MODE=local_only,
        ALLOW_CLOUD_PROVIDERS=allow_cloud,
        CODEXIFY_EGRESS_ALLOWLIST=allowlist,
        GROQ_API_KEY=api_key,
        GROQ_WEB_SEARCH_ENABLED=True,
        REMOTE_RECALL_ENABLED=True,
        GROQ_WEB_SEARCH_MODEL=model,
    )


def _request() -> SearchProviderRequest:
    return SearchProviderRequest(
        request_id="req-1",
        query="latest codexify release notes",
        provider="groq",
        source_kind="groq_web_search",
        max_results=5,
    )


def _fake_transport(payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    """Records the payload so tests can assert request shape."""

    _fake_transport.last_payload = payload  # type: ignore[attr-defined]
    return {
        "choices": [
            {
                "message": {
                    "content": "Synthesized answer (not used as the answer).",
                    "reasoning": "<tool>search(query)</tool>",
                    "executed_tools": [
                        {
                            "search_results": {
                                "results": [
                                    {
                                        "title": "Codexify release notes",
                                        "url": "https://example.com/notes",
                                        "content": "Beta hardening continues.",
                                        "score": 0.82,
                                    },
                                    {
                                        "title": "Codexify changelog",
                                        "url": "https://example.com/changelog",
                                        "content": "Local-first posture preserved.",
                                        "score": 0.71,
                                    },
                                ]
                            }
                        }
                    ],
                }
            }
        ]
    }


def test_supported_models_match_official_groq_docs() -> None:
    assert SUPPORTED_GROQ_WEB_SEARCH_MODELS == ("groq/compound", "groq/compound-mini")


def test_request_payload_uses_compound_model_and_query() -> None:
    adapter = GroqSearchAdapter(
        _enabled_settings(), transport=_fake_transport
    )
    result = adapter.invoke(_request())

    payload = _fake_transport.last_payload  # type: ignore[attr-defined]
    assert payload["model"] == DEFAULT_GROQ_WEB_SEARCH_MODEL
    assert payload["messages"] == [
        {"role": "user", "content": "latest codexify release notes"}
    ]


def test_fake_response_with_citations_normalizes_correctly() -> None:
    adapter = GroqSearchAdapter(
        _enabled_settings(), transport=_fake_transport
    )
    result = adapter.invoke(_request())

    assert result.status == "ok"
    assert result.provider == "groq"
    assert result.source_kind == "groq_web_search"
    assert result.result_count == 2
    assert result.blocked_reason is None
    assert [item.url for item in result.results] == [
        "https://example.com/notes",
        "https://example.com/changelog",
    ]
    assert result.results[0].title == "Codexify release notes"
    assert result.results[0].snippet == "Beta hardening continues."
    assert result.results[0].score == 0.82
    assert result.results[0].rank == 0
    assert result.results[1].rank == 1
    assert result.results[0].citation["url"] == "https://example.com/notes"


def test_response_without_citations_returns_safe_empty_result() -> None:
    def transport(payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        return {"choices": [{"message": {"content": "no tools used"}}]}

    adapter = GroqSearchAdapter(_enabled_settings(), transport=transport)
    result = adapter.invoke(_request())

    assert result.status == "empty"
    assert result.result_count == 0
    assert result.results == []
    assert (
        result.blocked_reason == RemoteRecallFailureReason.EMPTY_RESULT_SET.value
    )


def test_partial_rows_with_missing_fields_handled_defensively() -> None:
    def transport(payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        return {
            "choices": [
                {
                    "message": {
                        "executed_tools": [
                            {
                                "search_results": [
                                    {"title": "Only title, no url/content"},
                                    {"url": "https://example.com/only-url"},
                                    {"score": 0.5},  # nothing usable
                                ]
                            }
                        ]
                    }
                }
            ]
        }

    adapter = GroqSearchAdapter(_enabled_settings(), transport=transport)
    result = adapter.invoke(_request())

    # Rows with at least one usable field (title or url) are kept; the
    # score-only row is dropped as unusable.
    assert result.status == "ok"
    assert result.result_count == 2
    assert {item.url for item in result.results} == {
        "",
        "https://example.com/only-url",
    }


def test_disabled_flag_fails_closed() -> None:
    settings = Settings(GROQ_WEB_SEARCH_ENABLED=False)
    adapter = GroqSearchAdapter(settings, transport=_fake_transport)
    result = adapter.invoke(_request())

    assert result.status == "error"
    assert result.results == []
    assert (
        result.blocked_reason
        == RemoteRecallFailureReason.PROVIDER_NOT_CONFIGURED.value
    )


def test_missing_credentials_fails_closed() -> None:
    settings = Settings(
        GROQ_WEB_SEARCH_ENABLED=True,
        GROQ_API_KEY=None,
        ALLOW_CLOUD_PROVIDERS=True,
        CODEXIFY_LOCAL_ONLY_MODE=False,
        CODEXIFY_EGRESS_ALLOWLIST="groq",
    )
    adapter = GroqSearchAdapter(settings, transport=_fake_transport)
    result = adapter.invoke(_request())

    assert result.status == "error"
    assert (
        result.blocked_reason
        == RemoteRecallFailureReason.PROVIDER_NOT_CONFIGURED.value
    )


def test_local_only_mode_fails_closed() -> None:
    settings = _enabled_settings(local_only=True)
    adapter = GroqSearchAdapter(settings, transport=_fake_transport)
    result = adapter.invoke(_request())

    assert result.status == "error"
    assert adapter.is_enabled() is False


def test_groq_not_in_allowlist_fails_closed() -> None:
    settings = _enabled_settings(allowlist="openai")
    adapter = GroqSearchAdapter(settings, transport=_fake_transport)
    assert adapter.is_enabled() is False
    result = adapter.invoke(_request())
    assert result.status == "error"


def test_cloud_providers_disabled_fails_closed() -> None:
    settings = _enabled_settings(allow_cloud=False)
    adapter = GroqSearchAdapter(settings, transport=_fake_transport)
    assert adapter.is_enabled() is False


def test_no_raw_provider_object_leaks_out() -> None:
    adapter = GroqSearchAdapter(
        _enabled_settings(), transport=_fake_transport
    )
    result = adapter.invoke(_request())

    # All public result fields are provider-neutral dataclasses or primitives.
    assert result.__class__.__name__ == "SearchProviderResult"
    for item in result.results:
        assert item.__class__.__name__ == "SearchResultItem"
        # No raw Groq response object is carried on the result.
        assert not any(
            isinstance(getattr(item, attr, None), dict)
            and "executed_tools" in getattr(item, attr)
            for attr in ("provider_metadata", "citation")
        )


def test_transport_failure_fails_closed() -> None:
    def transport(payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        raise RuntimeError("connection refused")

    adapter = GroqSearchAdapter(_enabled_settings(), transport=transport)
    result = adapter.invoke(_request())

    assert result.status == "error"
    assert (
        result.blocked_reason
        == RemoteRecallFailureReason.PROVIDER_UNAVAILABLE.value
    )


def test_max_results_truncates_provider_rows() -> None:
    adapter = GroqSearchAdapter(
        _enabled_settings(), transport=_fake_transport
    )
    request = SearchProviderRequest(
        request_id="req-1",
        query="q",
        provider="groq",
        source_kind="groq_web_search",
        max_results=1,
    )
    result = adapter.invoke(request)
    assert result.result_count == 1


def test_search_settings_passed_through_from_extra() -> None:
    seen: dict[str, Any] = {}

    def transport(payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        seen.update(payload)
        return {"choices": [{"message": {}}]}

    adapter = GroqSearchAdapter(_enabled_settings(), transport=transport)
    request = SearchProviderRequest(
        request_id="req-1",
        query="q",
        provider="groq",
        source_kind="groq_web_search",
        extra={"include_domains": ["arxiv.org"], "country": "united states"},
    )
    adapter.invoke(request)
    assert seen["search_settings"] == {
        "include_domains": ["arxiv.org"],
        "country": "united states",
    }


def test_unsupported_model_falls_back_to_supported_default() -> None:
    settings = _enabled_settings(model="groq/does-not-exist")
    adapter = GroqSearchAdapter(settings, transport=_fake_transport)
    adapter.invoke(_request())
    payload = _fake_transport.last_payload  # type: ignore[attr-defined]
    assert payload["model"] == DEFAULT_GROQ_WEB_SEARCH_MODEL
