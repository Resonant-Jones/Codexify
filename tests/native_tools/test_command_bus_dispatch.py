"""Bus-level dispatch tests for the native read-file command.

The native command must execute **in process**. This file proves that the
command-bus invoke path reaches the native handler, that the loopback HTTP
transport is never used for it, and that the phase-1 write gate does not
block a read-effect internal command.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from guardian.command_bus import invoke as invoke_module
from guardian.core.repository_authority import (
    SOURCE_CLASS_EXTERNAL_LINKED,
    ResolvedRepositoryBinding,
)
from guardian.native_tools.command_specs import NATIVE_READ_FILE_COMMAND_ID
from guardian.routes import command_bus as command_bus_routes

ACCOUNT_ID = "account-1"
PROJECT_ID = 7


class _FakeChatLogDB:
    @contextmanager
    def get_session(self) -> Iterator[Any]:
        yield object()


def _build_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    monkeypatch.setenv("DEBUG", "1")
    command_bus_routes.configure_db(None)

    app = FastAPI()

    @app.get("/health", operation_id="health_check")
    def health() -> dict[str, bool]:
        return {"ok": True}

    def _current_user(request: Request) -> str:
        return request.headers.get("X-User-Id", ACCOUNT_ID)

    app.dependency_overrides[command_bus_routes.get_current_user] = _current_user
    app.include_router(command_bus_routes.router)
    return TestClient(app)


def _invoke_native(
    client: TestClient,
    *,
    body: dict[str, Any],
) -> dict[str, Any]:
    response = client.post(
        "/api/guardian/commands/invoke",
        headers={"X-API-Key": "test-key", "X-User-Id": ACCOUNT_ID},
        json={
            "invoke_version": "1.0",
            "command_id": NATIVE_READ_FILE_COMMAND_ID,
            "actor": {"kind": "human", "id": ACCOUNT_ID},
            "arguments": {"body": body},
        },
    )
    assert response.status_code == 200
    return response.json()


@pytest.fixture()
def repo_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir(parents=True)
    (root / "app.py").write_text("alpha\nbeta\n", encoding="utf-8")
    return root


@pytest.fixture()
def bound_project(
    monkeypatch: pytest.MonkeyPatch,
    repo_root: Path,
) -> None:
    monkeypatch.setattr(
        "guardian.core.dependencies.chatlog_db",
        _FakeChatLogDB(),
        raising=False,
    )
    monkeypatch.setattr(
        "guardian.core.repository_authority.resolve_project_repository_binding",
        lambda *_args, **_kwargs: ResolvedRepositoryBinding(
            binding_id="binding-1",
            project_id=PROJECT_ID,
            source_class=SOURCE_CLASS_EXTERNAL_LINKED,
            canonical_root=repo_root,
        ),
    )


def test_native_command_executes_in_process_without_the_loopback_transport(
    monkeypatch: pytest.MonkeyPatch,
    bound_project: None,
) -> None:
    client = _build_client(monkeypatch)

    async def unexpected_loopback(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError(
            "loopback HTTP must not run for a native in-process command"
        )

    monkeypatch.setattr(
        invoke_module, "execute_loopback_request", unexpected_loopback
    )

    payload = _invoke_native(
        client,
        body={"path": "app.py", "scope": {"project_id": PROJECT_ID}},
    )

    assert payload["status"] == "completed"
    assert payload["inline_result"]["content"] == "1\talpha\n2\tbeta\n"
    assert payload["inline_result"]["path"] == "app.py"

    events = command_bus_routes._store.list_events_after(
        run_id=payload["run_id"],
        after_seq=0,
    )
    assert any(event.get("event_type") == "run.completed" for event in events)


def test_native_command_is_not_blocked_by_the_phase1_write_gate(
    monkeypatch: pytest.MonkeyPatch,
    bound_project: None,
) -> None:
    client = _build_client(monkeypatch)

    payload = _invoke_native(
        client,
        body={"path": "app.py", "scope": {"project_id": PROJECT_ID}},
    )

    # A read-effect internal command must not trip ``phase1_write_blocked``.
    assert payload["status"] == "completed"


def test_native_command_refuses_a_scope_the_account_does_not_own(
    monkeypatch: pytest.MonkeyPatch,
    bound_project: None,
) -> None:
    client = _build_client(monkeypatch)

    def _refuse(*_args: Any, **_kwargs: Any) -> ResolvedRepositoryBinding:
        raise RuntimeError("binding mismatch")

    monkeypatch.setattr(
        "guardian.core.repository_authority.resolve_project_repository_binding",
        _refuse,
    )

    payload = _invoke_native(
        client,
        body={"path": "app.py", "scope": {"project_id": 999}},
    )

    assert payload["status"] == "failed"
    assert payload["error"]


def test_native_command_refuses_a_path_outside_the_project_root(
    monkeypatch: pytest.MonkeyPatch,
    bound_project: None,
) -> None:
    client = _build_client(monkeypatch)

    payload = _invoke_native(
        client,
        body={"path": "../../etc/passwd", "scope": {"project_id": PROJECT_ID}},
    )

    assert payload["status"] == "failed"
    # The failure message never leaks the resolved root or a filesystem path.
    assert "passwd" not in str(payload.get("error", ""))
