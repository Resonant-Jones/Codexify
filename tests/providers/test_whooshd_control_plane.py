"""Focused Codexify tests for the versioned Whoosh'd control plane."""

from __future__ import annotations

import json

import pytest
from fastapi import HTTPException

import guardian.core.ai_router as ai_router
from guardian.core.config import Settings
import guardian.core.supported_profile as supported_profile
from guardian.providers.whooshd_control_plane import (
    WHOOSHD_CONTROL_PLANE_VERSION,
    WHOOSHD_CONTROL_VERSION_HEADER,
    parse_whooshd_error,
    provider_failure_kind,
)


class _Response:
    def __init__(self, body: dict, *, version: str | None = WHOOSHD_CONTROL_PLANE_VERSION):
        self.status_code = int(body.get("http_status", 503))
        self.headers = {}
        if version is not None:
            self.headers[WHOOSHD_CONTROL_VERSION_HEADER] = version
        self.content = json.dumps(body).encode("utf-8")
        self._body = body

    def json(self):
        return self._body


def test_v1_header_and_body_are_parsed_without_content_fields():
    response = _Response(
        {
            "contract_version": WHOOSHD_CONTROL_PLANE_VERSION,
            "code": "model_warming",
            "http_status": 425,
            "retryable": True,
            "retry_after_seconds": 2,
            "request_id": "req-42",
            "category": "model_runtime",
            "message": "prompt-secret-generated-secret",
            "details": {"body": "upstream-response-secret"},
            "optional_future_field": "ignored",
        }
    )

    diagnostic = parse_whooshd_error(response)

    assert diagnostic is not None
    assert diagnostic.contract_version == WHOOSHD_CONTROL_PLANE_VERSION
    assert diagnostic.code == "model_warming"
    assert diagnostic.http_status == 425
    assert diagnostic.retryable is True
    assert diagnostic.retry_after_seconds == 2.0
    assert diagnostic.request_id == "req-42"
    assert diagnostic.category == "model_runtime"
    serialized = json.dumps(diagnostic.as_dict())
    assert "prompt-secret-generated-secret" not in serialized
    assert "upstream-response-secret" not in serialized
    assert "optional_future_field" not in serialized


@pytest.mark.parametrize(
    "version",
    [None, "whooshd.control.v0", "whooshd.control.v2"],
)
def test_missing_mismatched_and_unsupported_versions_remain_legacy(version):
    response = _Response(
        {
            "code": "runtime_unavailable",
            "http_status": 503,
            "retryable": True,
        },
        version=version,
    )

    assert parse_whooshd_error(response) is None


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("timeout", "provider_timeout"),
        ("upstream_timeout", "provider_timeout"),
        ("runtime_unavailable", "transport_error"),
        ("model_unavailable", "transport_error"),
        ("model_not_found", "local_model_unavailable"),
        ("unsupported_field", "request_error"),
        ("unsupported_capability", "request_error"),
    ],
)
def test_codexify_classifies_from_machine_readable_code_only(code, expected):
    assert provider_failure_kind(code) == expected


def test_legacy_unversioned_response_is_not_assumed_to_be_v1():
    response = _Response(
        {
            "code": "runtime_unavailable",
            "message": "legacy response body may be provider-defined",
        },
        version=None,
    )

    assert parse_whooshd_error(response) is None


def test_call_local_sends_v1_header_and_uses_code_not_body(monkeypatch):
    captured: dict[str, object] = {}

    def _post(url, *, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return _Response(
            {
                "contract_version": WHOOSHD_CONTROL_PLANE_VERSION,
                "code": "runtime_unavailable",
                "http_status": 503,
                "retryable": True,
                "request_id": "turn-9",
                "message": "prompt-body-sentinel",
                "details": {"response": "provider-body-sentinel"},
            }
        )

    monkeypatch.setattr(ai_router.requests, "post", _post)
    monkeypatch.setattr(
        supported_profile,
        "get_active_supported_profile",
        lambda: None,
    )
    settings = Settings(
        LLM_PROVIDER="local",
        CODEXIFY_LOCAL_ONLY_MODE=True,
        ALLOW_CLOUD_PROVIDERS=False,
        CODEXIFY_EGRESS_ALLOWLIST="",
        LOCAL_BASE_URL="http://host.docker.internal:8000/v1",
        LOCAL_LLM_MODEL="gemma-3-4b-it",
        LOCAL_CHAT_MODEL="gemma-3-4b-it",
        DEFAULT_LOCAL_MODEL="gemma-3-4b-it",
        LLM_MODEL="gemma-3-4b-it",
    )

    with pytest.raises(HTTPException) as exc:
        ai_router.call_local(
            [{"role": "user", "content": "prompt-input-sentinel"}],
            "gemma-3-4b-it",
            settings=settings,
        )

    assert captured["headers"][WHOOSHD_CONTROL_VERSION_HEADER] == WHOOSHD_CONTROL_PLANE_VERSION
    detail = exc.value.detail
    assert detail["failure_kind"] == "transport_error"
    assert detail["provider_error"] == "runtime_unavailable"
    assert detail["whooshd_error"]["request_id"] == "turn-9"
    serialized = json.dumps(detail)
    assert "prompt-body-sentinel" not in serialized
    assert "provider-body-sentinel" not in serialized
    assert "prompt-input-sentinel" not in serialized
