from __future__ import annotations

import json
from typing import Any

import pytest

from scripts.ops.private_preview_provider_proof import (
    PrivatePreviewProviderProof,
    ProofError,
    _safe_json_value,
)


LOCAL_MODEL = "qwen3.8-27b-4bit"
DEEPSEEK_MODEL = "deepseek-v4-flash"


class FakeTransport:
    def __init__(self) -> None:
        self.next_thread_id = 100
        self.threads: dict[int, tuple[str, str]] = {}
        self.tasks: dict[str, tuple[int, str, str]] = {}
        self.overrides: dict[str, dict[str, Any]] = {}
        self.no_terminal: set[str] = set()
        self.assistant_count: dict[str, int] = {}
        self.persisted_execution_mismatch: set[str] = set()
        self.deepseek_authorized = True
        self.unrelated_authorized: str | None = None
        self.deepseek_catalog_model = DEEPSEEK_MODEL
        self.secret_value = "super-secret-response-token"

    def _catalog_entry(
        self,
        provider: str,
        *,
        authorized: bool,
        enabled: bool,
        model: str,
    ) -> dict[str, Any]:
        return {
            "id": provider,
            "authorized": authorized,
            "available": enabled,
            "enabled": enabled,
            "models": [{"id": model}],
            "debug_api_key": self.secret_value,
        }

    def request_json(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if path == "/health":
            return {
                "status": "ok",
                "details": {
                    "supported_profile": {
                        "name": "v1-whooshd-deepseek-web",
                        "valid": True,
                    },
                    "session_token": self.secret_value,
                },
            }
        if path == "/health/chat":
            return {
                "status": "healthy",
                "redis": "ok",
                "worker": {"status": "alive"},
            }
        if path == "/api/health/llm":
            return {
                "status": "ok",
                "details": {
                    "provider": "local",
                    "provider_runtime": {"enabled": True},
                    "authorization": self.secret_value,
                },
            }
        if path == "/api/llm/catalog?include=all":
            providers = [
                self._catalog_entry(
                    "local",
                    authorized=True,
                    enabled=True,
                    model=LOCAL_MODEL,
                ),
                self._catalog_entry(
                    "deepseek",
                    authorized=self.deepseek_authorized,
                    enabled=self.deepseek_authorized,
                    model=self.deepseek_catalog_model,
                ),
            ]
            for provider in (
                "openai",
                "groq",
                "minimax",
                "alibaba",
                "anthropic",
                "gemini",
            ):
                authorized = provider == self.unrelated_authorized
                providers.append(
                    self._catalog_entry(
                        provider,
                        authorized=authorized,
                        enabled=authorized,
                        model=f"{provider}-model",
                    )
                )
            return {"providers": providers}
        if method == "POST" and path == "/api/chat/threads":
            assert payload is not None
            thread_id = self.next_thread_id
            self.next_thread_id += 1
            self.threads[thread_id] = (
                str(payload["providerId"]),
                str(payload["modelId"]),
            )
            return {"ok": True, "id": thread_id}
        if method == "POST" and path.endswith("/messages"):
            return {"ok": True, "message": {"id": 1, "role": "user"}}
        if method == "POST" and path.endswith("/complete"):
            assert payload is not None
            thread_id = int(path.split("/")[3])
            provider = str(payload["provider"])
            model = str(payload["model"])
            task_id = f"task-{provider}"
            self.tasks[task_id] = (thread_id, provider, model)
            return {"ok": True, "task_id": task_id}
        if method == "GET" and "/messages?" in path:
            thread_id = int(path.split("/")[3])
            provider, model = self.threads[thread_id]
            count = self.assistant_count.get(provider, 1)
            messages: list[dict[str, Any]] = [
                {"id": 1, "role": "user", "content": "proof"}
            ]
            for index in range(count):
                execution_provider = (
                    "local"
                    if provider in self.persisted_execution_mismatch
                    else provider
                )
                messages.append(
                    {
                        "id": thread_id * 10 + index,
                        "role": "assistant",
                        "content": "proof",
                        "execution": {
                            "attempted_provider": execution_provider,
                            "attempted_model": model,
                            "final_provider": execution_provider,
                            "final_model": model,
                        },
                    }
                )
            return {"ok": True, "messages": messages}
        raise AssertionError(f"unexpected request: {method} {path}")

    def stream_task_events(
        self, task_id: str, *, timeout_seconds: float
    ) -> list[dict[str, Any]]:
        _, provider, model = self.tasks[task_id]
        if provider in self.no_terminal:
            return [{"type": "task.progress", "data": {}}]
        override = self.overrides.get(provider, {})
        final_provider = str(override.get("final_provider") or provider)
        final_model = str(override.get("final_model") or model)
        attempted_provider = str(
            override.get("attempted_provider") or provider
        )
        attempted_model = str(override.get("attempted_model") or model)
        return [
            {
                "type": str(override.get("event_type") or "task.completed"),
                "data": {
                    "message_id": self.tasks[task_id][0] * 10,
                    "attempted_provider": attempted_provider,
                    "attempted_model": attempted_model,
                    "final_provider": final_provider,
                    "final_model": final_model,
                    "provider": final_provider,
                    "model": final_model,
                    "completion_truth": {
                        "fallback_attempted": bool(
                            override.get("fallback_attempted")
                        )
                    },
                },
            }
        ]


def _proof(transport: FakeTransport) -> PrivatePreviewProviderProof:
    return PrivatePreviewProviderProof(
        transport,
        local_model=LOCAL_MODEL,
        deepseek_model=DEEPSEEK_MODEL,
        sentinel="proof-sentinel",
        task_timeout_seconds=0.01,
    )


def test_valid_two_provider_proof_passes_and_sanitizes_summary() -> None:
    transport = FakeTransport()

    summary = _proof(transport).run()

    assert summary["ok"] is True
    assert summary["turns"]["local"]["final_provider"] == "local"
    assert summary["turns"]["deepseek"]["final_model"] == DEEPSEEK_MODEL
    assert transport.secret_value not in json.dumps(summary)


def test_local_fallback_during_deepseek_proof_fails() -> None:
    transport = FakeTransport()
    transport.overrides["deepseek"] = {
        "final_provider": "local",
        "final_model": LOCAL_MODEL,
        "fallback_attempted": True,
    }

    with pytest.raises(ProofError, match="fallback") as error:
        _proof(transport).run()
    assert error.value.classification == "provider_fallback_occurred"


def test_deepseek_execution_during_local_proof_fails() -> None:
    transport = FakeTransport()
    transport.overrides["local"] = {
        "final_provider": "deepseek",
        "final_model": DEEPSEEK_MODEL,
    }

    with pytest.raises(ProofError) as error:
        _proof(transport).run()
    assert error.value.classification == "provider_fallback_occurred"


def test_accepted_without_terminal_completion_fails() -> None:
    transport = FakeTransport()
    transport.no_terminal.add("local")

    with pytest.raises(ProofError) as error:
        _proof(transport).run()
    assert error.value.classification == "accepted_but_not_completed"


def test_duplicate_assistant_persistence_fails() -> None:
    transport = FakeTransport()
    transport.assistant_count["local"] = 2

    with pytest.raises(ProofError) as error:
        _proof(transport).run()
    assert error.value.classification == "transcript_duplication"


def test_mismatched_terminal_and_persisted_metadata_fails() -> None:
    transport = FakeTransport()
    transport.persisted_execution_mismatch.add("deepseek")

    with pytest.raises(ProofError) as error:
        _proof(transport).run()
    assert error.value.classification == "persistence_mismatch"


def test_unauthorized_deepseek_fails() -> None:
    transport = FakeTransport()
    transport.deepseek_authorized = False

    with pytest.raises(ProofError) as error:
        _proof(transport).run()
    assert error.value.classification == "provider_unauthorized"


def test_unrelated_authorized_cloud_provider_fails() -> None:
    transport = FakeTransport()
    transport.unrelated_authorized = "openai"

    with pytest.raises(ProofError) as error:
        _proof(transport).run()
    assert error.value.classification == "provider_unauthorized"


def test_secret_bearing_fields_are_redacted() -> None:
    sanitized = _safe_json_value(
        {
            "authorization": "Bearer secret",
            "nested": {
                "DEEPSEEK_API_KEY": "secret",
                "status": "available",
            },
        }
    )

    assert sanitized == {
        "authorization": "<redacted>",
        "nested": {
            "DEEPSEEK_API_KEY": "<redacted>",
            "status": "available",
        },
    }


def test_provider_model_matching_is_exact_not_substring_based() -> None:
    transport = FakeTransport()
    transport.deepseek_catalog_model = f"prefix-{DEEPSEEK_MODEL}-suffix"

    with pytest.raises(ProofError, match="absent") as error:
        _proof(transport).run()
    assert error.value.classification == "provider_unavailable"
