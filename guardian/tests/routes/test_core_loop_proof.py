from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.core import core_loop_proof as proof_service
from guardian.routes import core_loop_proof as proof_route

_API_KEY = "test-key"
_RAW_MESSAGE = "Summarize the current project state."
_RAW_DOC_SNIPPET = "document secret text"
_RAW_MEMORY_SNIPPET = "memory secret text"


class _FakeChatLogDB:
    def __init__(self) -> None:
        self.threads: dict[int, dict[str, Any]] = {}
        self.messages: list[dict[str, Any]] = []
        self.metadata_updates: list[tuple[int, dict[str, Any]]] = []
        self._next_thread_id = 1
        self._next_message_id = 100

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def create_chat_thread(
        self,
        user_id: str,
        title: str,
        summary: str = "",
        project_id: int | None = None,
        parent_id: int | None = None,
    ) -> dict[str, Any]:
        thread_id = self._next_thread_id
        self._next_thread_id += 1
        thread = {
            "id": thread_id,
            "user_id": user_id,
            "title": title,
            "summary": summary,
            "project_id": project_id,
            "parent_id": parent_id,
            "thread_config": {},
            "metadata": {},
            "created_at": self._now(),
            "updated_at": self._now(),
        }
        self.threads[thread_id] = thread
        return dict(thread)

    def ensure_chat_thread(
        self,
        thread_id: int,
        user_id: str,
        title: str,
        summary: str = "",
        project_id: int | None = None,
        parent_id: int | None = None,
    ) -> dict[str, Any]:
        existing = self.threads.get(thread_id)
        if existing is not None:
            return dict(existing)
        thread = {
            "id": thread_id,
            "user_id": user_id,
            "title": title,
            "summary": summary,
            "project_id": project_id,
            "parent_id": parent_id,
            "thread_config": {},
            "metadata": {},
            "created_at": self._now(),
            "updated_at": self._now(),
        }
        self.threads[thread_id] = thread
        return dict(thread)

    def get_chat_thread(self, thread_id: int) -> dict[str, Any] | None:
        thread = self.threads.get(thread_id)
        return dict(thread) if thread is not None else None

    def count_messages(self, thread_id: int) -> int:
        return sum(1 for item in self.messages if item["thread_id"] == thread_id)

    def create_message(
        self,
        thread_id: int,
        role: str,
        content: str,
        created_at: str | None = None,
        user_id: str | None = None,
    ) -> int:
        message_id = self._next_message_id
        self._next_message_id += 1
        self.messages.append(
            {
                "id": message_id,
                "thread_id": thread_id,
                "role": role,
                "content": content,
                "created_at": created_at or self._now(),
                "user_id": user_id,
            }
        )
        if thread_id in self.threads:
            self.threads[thread_id]["updated_at"] = self._now()
        return message_id

    def update_thread_metadata(self, thread_id: int, metadata: dict[str, Any]) -> bool:
        self.metadata_updates.append((thread_id, copy.deepcopy(metadata)))
        thread = self.threads.get(thread_id)
        if thread is None:
            return False
        thread["metadata"] = copy.deepcopy(metadata)
        thread["updated_at"] = self._now()
        return True


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(proof_route.router)
    return app


def _headers() -> dict[str, str]:
    return {"X-API-Key": _API_KEY}


def _install_proof_lane(
    monkeypatch: pytest.MonkeyPatch,
    broker_payload: dict[str, Any],
    *,
    provider_raises: bool = False,
) -> tuple[_FakeChatLogDB, list[dict[str, Any]], list[dict[str, Any]]]:
    monkeypatch.setenv("GUARDIAN_API_KEY", _API_KEY)
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "local")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("CODEXIFY_SINGLE_USER_ID", "local")
    monkeypatch.setenv("CODEXIFY_ENABLE_CORE_LOOP_PROOF", "true")

    db = _FakeChatLogDB()
    emitted_events: list[dict[str, Any]] = []
    broker_calls: list[dict[str, Any]] = []

    monkeypatch.setattr(proof_service.dependencies, "chatlog_db", db, raising=False)
    monkeypatch.setattr(
        proof_service.dependencies,
        "get_vector_store",
        lambda: object(),
        raising=False,
    )
    monkeypatch.setattr(proof_service, "get_settings", lambda: SimpleNamespace())
    monkeypatch.setattr(
        proof_service, "first_enabled_provider", lambda *, settings=None: "local"
    )

    if provider_raises:

        def _raise_provider_settings(*_args: Any, **_kwargs: Any) -> Any:
            raise RuntimeError("provider unavailable")

        monkeypatch.setattr(
            proof_service,
            "resolve_thread_completion_settings",
            _raise_provider_settings,
        )
    else:
        monkeypatch.setattr(
            proof_service,
            "resolve_thread_completion_settings",
            lambda *args, **kwargs: SimpleNamespace(
                provider="local",
                model="local-proof-model",
                source_mode="project",
                reasoning_mode=None,
                has_thread_config=False,
            ),
        )

    monkeypatch.setattr(
        proof_service,
        "resolve_provider_capability",
        lambda provider, settings: {
            "available": True,
            "enabled": True,
            "authorized": True,
        },
    )
    monkeypatch.setattr(
        proof_service,
        "build_provider_truth",
        lambda provider, settings, **kwargs: {
            "provider": provider,
            "available": kwargs.get("capability", {}).get("available", True),
            "enabled": kwargs.get("capability", {}).get("enabled", True),
            "authorized": kwargs.get("capability", {}).get("authorized", True),
            "attempted": kwargs.get("attempted", False),
            "executed": kwargs.get("executed", False),
            "completed": kwargs.get("completed", False),
        },
    )

    class _FakeContextBroker:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            broker_calls.append(
                {
                    "kind": "init",
                    "args": args,
                    "kwargs": kwargs,
                }
            )

        async def assemble(
            self,
            thread_id: int,
            query: str,
            depth_mode: str,
            project_id: int | None,
            user_id: str,
            source_mode: str,
        ) -> tuple[dict[str, Any], dict[str, Any]]:
            broker_calls.append(
                {
                    "kind": "assemble",
                    "thread_id": thread_id,
                    "query": query,
                    "depth_mode": depth_mode,
                    "project_id": project_id,
                    "user_id": user_id,
                    "source_mode": source_mode,
                }
            )
            return (
                copy.deepcopy(broker_payload["context"]),
                copy.deepcopy(broker_payload["rag_trace"]),
            )

    monkeypatch.setattr(proof_service, "ContextBroker", _FakeContextBroker)

    def _emit_event(
        topic: str,
        payload: dict[str, Any],
        *,
        tenant_id: str = "default",
    ) -> None:
        emitted_events.append(
            {
                "topic": topic,
                "payload": copy.deepcopy(payload),
                "tenant_id": tenant_id,
            }
        )

    monkeypatch.setattr(proof_service.event_bus, "emit_event", _emit_event)
    return db, emitted_events, broker_calls


def test_core_loop_proof_disabled_when_flag_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GUARDIAN_API_KEY", _API_KEY)
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "local")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.delenv("CODEXIFY_ENABLE_CORE_LOOP_PROOF", raising=False)

    app = _build_app()
    with TestClient(app) as client:
        response = client.post(
            "/api/core-loop/proof",
            headers=_headers(),
            json={"message": _RAW_MESSAGE},
        )

    assert response.status_code == 404
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "CORE_LOOP_PROOF_DISABLED"


@pytest.mark.parametrize(
    "payload",
    [
        {"message": "   "},
        {"message": "x" * 12_001},
        {"thread_id": 0, "message": _RAW_MESSAGE},
    ],
)
def test_core_loop_proof_validates_request_shape(
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, Any],
) -> None:
    monkeypatch.setenv("GUARDIAN_API_KEY", _API_KEY)
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "local")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("CODEXIFY_ENABLE_CORE_LOOP_PROOF", "true")

    app = _build_app()
    with TestClient(app) as client:
        response = client.post(
            "/api/core-loop/proof",
            headers=_headers(),
            json=payload,
        )

    assert response.status_code == 422


def test_core_loop_proof_creates_updates_and_emits_safe_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broker_payload = {
        "context": {
            "messages": [],
            "semantic": [
                {
                    "id": "sem-1",
                    "title": "Thread note",
                    "text": "semantic secret text",
                    "namespace": "thread:1",
                }
            ],
            "docs": {
                "project": [
                    {
                        "document_id": "doc-1",
                        "title": "Project brief",
                        "content": _RAW_DOC_SNIPPET,
                    }
                ],
                "thread": [],
                "global": [],
            },
            "memory": [
                {
                    "memory_id": "mem-1",
                    "text": _RAW_MEMORY_SNIPPET,
                }
            ],
            "graph": [
                {
                    "node_id": "node-1",
                    "kind": "graph_node",
                    "text": "graph secret text",
                }
            ],
        },
        "rag_trace": {
            "retrieval_provenance": {
                "retrieval_status": "workspace_local_success",
                "source_hit_counts": {
                    "semantic_total": 1,
                    "thread_semantic": 1,
                    "obsidian_semantic": 0,
                    "other_semantic": 0,
                    "project_documents": 1,
                    "thread_documents": 0,
                    "global_documents": 0,
                    "other_documents": 0,
                    "memory": 1,
                    "graph": 1,
                },
            },
            "retrieval_executed": True,
            "retrieval_absence_reason": None,
            "source_mode": "project",
            "widen_reason": None,
        },
    }
    db, emitted_events, broker_calls = _install_proof_lane(
        monkeypatch,
        broker_payload,
    )

    app = _build_app()
    with TestClient(app) as client:
        first_response = client.post(
            "/api/core-loop/proof",
            headers=_headers(),
            json={
                "message": _RAW_MESSAGE,
                "provider_hint": "local",
                "retrieval": {
                    "enabled": True,
                    "query": "current project state",
                },
            },
        )
        second_response = client.post(
            "/api/core-loop/proof",
            headers=_headers(),
            json={
                "thread_id": first_response.json()["thread_id"],
                "message": "Follow up on the same thread.",
                "provider_hint": "local",
                "retrieval": {
                    "enabled": True,
                    "query": "follow up state",
                },
            },
        )

    assert first_response.status_code == 200
    first_body = first_response.json()
    assert first_body["ok"] is True
    assert first_body["status"] == "completed"
    assert first_body["provider"]["selected"] == "local"
    assert first_body["provider"]["reason"] == "request_hint"
    assert first_body["thread_state"]["message_count"] == 2
    assert first_body["proof_record"]["created_new"] is True
    assert (
        first_body["retrieval_proof"]["retrieval_status"] == "workspace_local_success"
    )
    assert first_body["retrieval_proof"]["result_count"] == 4
    assert set(first_body["retrieval_proof"]["source_ids"]) == {
        "sem-1",
        "doc-1",
        "mem-1",
        "node-1",
    }
    assert first_body["message"]["role"] == "assistant"
    assert _RAW_MESSAGE not in json.dumps(first_body)
    assert _RAW_DOC_SNIPPET not in json.dumps(first_body)
    assert _RAW_MEMORY_SNIPPET not in json.dumps(first_body)

    first_event_types = [item["event_type"] for item in first_body["events"]]
    assert first_event_types == [
        "request_received",
        "thread_loaded_or_created",
        "provider_selected",
        "retrieval_started",
        "retrieval_completed",
        "response_started",
        "response_completed",
    ]
    assert all(
        _RAW_MESSAGE not in json.dumps(event)
        and _RAW_DOC_SNIPPET not in json.dumps(event)
        and _RAW_MEMORY_SNIPPET not in json.dumps(event)
        for event in first_body["events"]
    )

    assert second_response.status_code == 200
    second_body = second_response.json()
    assert second_body["proof_record"]["created_new"] is False
    assert second_body["thread_id"] == first_body["thread_id"]
    assert second_body["thread_state"]["message_count"] == 4
    assert second_body["retrieval_proof"]["result_count"] == 4
    assert len(db.threads) == 1
    assert len(db.messages) == 4
    assert broker_calls and broker_calls[0]["kind"] == "init"
    assert broker_calls and broker_calls[1]["kind"] == "assemble"
    assert emitted_events


def test_core_loop_proof_retrieval_disabled_reports_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broker_payload = {
        "context": {
            "messages": [],
            "semantic": [],
            "docs": {"project": [], "thread": [], "global": []},
            "memory": [],
            "graph": [],
        },
        "rag_trace": {
            "retrieval_provenance": {
                "retrieval_status": "not_configured",
                "source_hit_counts": {
                    "semantic_total": 0,
                    "thread_semantic": 0,
                    "obsidian_semantic": 0,
                    "other_semantic": 0,
                    "project_documents": 0,
                    "thread_documents": 0,
                    "global_documents": 0,
                    "other_documents": 0,
                    "memory": 0,
                    "graph": 0,
                },
            },
            "retrieval_executed": False,
            "retrieval_absence_reason": "not_configured",
            "source_mode": "project",
            "widen_reason": None,
        },
    }
    _db, _emitted_events, broker_calls = _install_proof_lane(
        monkeypatch,
        broker_payload,
    )

    app = _build_app()
    with TestClient(app) as client:
        response = client.post(
            "/api/core-loop/proof",
            headers=_headers(),
            json={
                "message": _RAW_MESSAGE,
                "retrieval": {"enabled": False},
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["retrieval_proof"]["retrieval_status"] == "disabled"
    assert body["retrieval_proof"]["result_count"] == 0
    assert body["retrieval_proof"]["retrieval_enabled"] is False
    assert body["retrieval_proof"]["executed"] is False
    assert body["retrieval_proof"]["source_ids"] == []
    assert all(
        item["event_type"] not in {"retrieval_started", "retrieval_completed"}
        for item in body["events"]
    )
    assert broker_calls == []


def test_core_loop_proof_retrieval_unavailable_reports_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broker_payload = {
        "context": {
            "messages": [],
            "semantic": [],
            "docs": {"project": [], "thread": [], "global": []},
            "memory": [],
            "graph": [],
        },
        "rag_trace": {
            "retrieval_provenance": {
                "retrieval_status": "not_configured",
                "source_hit_counts": {
                    "semantic_total": 0,
                    "thread_semantic": 0,
                    "obsidian_semantic": 0,
                    "other_semantic": 0,
                    "project_documents": 0,
                    "thread_documents": 0,
                    "global_documents": 0,
                    "other_documents": 0,
                    "memory": 0,
                    "graph": 0,
                },
            },
            "retrieval_executed": False,
            "retrieval_absence_reason": "not_configured",
            "source_mode": "project",
            "widen_reason": None,
        },
    }
    _db, _emitted_events, _broker_calls = _install_proof_lane(
        monkeypatch,
        broker_payload,
    )

    app = _build_app()
    with TestClient(app) as client:
        response = client.post(
            "/api/core-loop/proof",
            headers=_headers(),
            json={
                "message": _RAW_MESSAGE,
                "retrieval": {
                    "enabled": True,
                    "query": "missing retrieval backend",
                },
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["retrieval_proof"]["retrieval_status"] == "not_configured"
    assert body["retrieval_proof"]["result_count"] == 0
    assert body["retrieval_proof"]["retrieval_enabled"] is True
    assert body["retrieval_proof"]["executed"] is False
    assert body["retrieval_proof"]["source_ids"] == []


def test_core_loop_proof_provider_failure_returns_safe_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broker_payload = {
        "context": {
            "messages": [],
            "semantic": [],
            "docs": {"project": [], "thread": [], "global": []},
            "memory": [],
            "graph": [],
        },
        "rag_trace": {
            "retrieval_provenance": {
                "retrieval_status": "not_configured",
                "source_hit_counts": {
                    "semantic_total": 0,
                    "thread_semantic": 0,
                    "obsidian_semantic": 0,
                    "other_semantic": 0,
                    "project_documents": 0,
                    "thread_documents": 0,
                    "global_documents": 0,
                    "other_documents": 0,
                    "memory": 0,
                    "graph": 0,
                },
            },
            "retrieval_executed": False,
            "retrieval_absence_reason": "not_configured",
            "source_mode": "project",
            "widen_reason": None,
        },
    }
    _install_proof_lane(
        monkeypatch,
        broker_payload,
        provider_raises=True,
    )

    app = _build_app()
    with TestClient(app) as client:
        response = client.post(
            "/api/core-loop/proof",
            headers=_headers(),
            json={
                "message": _RAW_MESSAGE,
                "provider_hint": "local",
            },
        )

    assert response.status_code == 500
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "core_loop_proof_failed"
    assert "provider unavailable" not in json.dumps(body)
    assert any(event["event_type"] == "request_failed" for event in body["events"])
