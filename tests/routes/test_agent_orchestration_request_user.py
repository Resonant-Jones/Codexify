"""Regression coverage for account-scoped agent-run readback identity.

`f83fe5da3` ("Bind coding execution identity per invocation", ADR-094) changed
`_resolved_request_user(current_user, fallback)` into
`_resolved_request_user(current_user, requested_user)`. The second argument
stopped being a fallback value and became a caller-supplied identity that must
match the authenticated principal exactly.

Five routes supply no caller-supplied identity, but kept passing the obsolete
fallback sentinel `""`. Under the new semantics an explicitly supplied empty
string is a *conflicting* identity, so every one of those routes raised
`403 account_identity_mismatch` before reaching its account-scoped store
operation:

    POST /api/agents/runs/{run_id}/cancel
    GET  /api/agents/runs/{run_id}/coding
    GET  /api/agents/runs/{run_id}
    GET  /api/chat/{thread_id}/agent-runs   (and the /api/agents/chat alias)
    GET  /api/chat/{thread_id}/coding-runs

Authenticated readback and cancellation became unreachable, and the routes'
`404` masking for a missing or unauthorized resource became dead code.

The correction distinguishes an *absent* requested identity (`None`) from an
*explicitly supplied* one. Absent means the route relies exclusively on the
authenticated principal, which is the account authority. Explicit means the
supplied identity must match that principal exactly, including when the
supplied value is empty.

These tests are import- and HTTP-level only. They use an isolated FastAPI
application and deterministic store doubles: no live database, Redis, provider,
or execution adapter is contacted.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.routes import agent_orchestration


ACCOUNT_OWNER = "owner@example.invalid"
ACCOUNT_OTHER = "other@example.invalid"
API_KEY = "test-api-key"
RUN_ID = "run-1"
THREAD_ID = 7

CODING_ROUTE = "/api/agents/coding/execute"


# ---------------------------------------------------------------------------
# Deterministic doubles
# ---------------------------------------------------------------------------


class _ScopedStore:
    """AgentStore double that records scoped lookups.

    Every read is scoped to the recorded account id exactly as the real
    `AgentStore` scopes its account reads: a lookup for an account that does
    not own the resource resolves to `None`, which the routes translate into
    the `404` that masks both "missing" and "not yours".
    """

    def __init__(
        self,
        *,
        owner_account: str = ACCOUNT_OWNER,
        existing_runs: frozenset[str] = frozenset({RUN_ID}),
    ) -> None:
        self.owner_account = owner_account
        self.existing_runs = set(existing_runs)
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.mutations: list[tuple[str, dict[str, Any]]] = []
        self.db: Any = None

    # -- internals ----------------------------------------------------

    def _record(self, name: str, kwargs: dict[str, Any]) -> None:
        self.calls.append((name, dict(kwargs)))

    def _owned(self, user_id: Any) -> bool:
        return str(user_id or "").strip() == self.owner_account

    def _exists(self, run_id: str) -> bool:
        return str(run_id) in self.existing_runs

    @property
    def call_names(self) -> list[str]:
        return [name for name, _ in self.calls]

    # -- store surface used by the routes ----------------------------

    def get_run(
        self, run_id: str, *, user_id: str | None = None
    ) -> dict[str, Any] | None:
        self._record("get_run", {"run_id": run_id, "user_id": user_id})
        if not self._exists(run_id) or not self._owned(user_id):
            return None
        return {
            "run_id": run_id,
            "deployment_id": "dep-1",
            "thread_id": THREAD_ID,
            "status": "running",
        }

    def get_account_run(self, run_id: str, *, user_id: str) -> dict[str, Any] | None:
        self._record("get_account_run", {"run_id": run_id, "user_id": user_id})
        if not self._exists(run_id) or not self._owned(user_id):
            return None
        return {
            "run_id": run_id,
            "deployment_id": "dep-1",
            "thread_id": THREAD_ID,
            "status": "running",
        }

    def get_coding_run_snapshot(
        self,
        run_id: str,
        *,
        user_id: str | None = None,
    ) -> dict[str, Any] | None:
        self._record("get_coding_run_snapshot", {"run_id": run_id, "user_id": user_id})
        if not self._exists(run_id) or not self._owned(user_id):
            return None
        return {
            "run_id": run_id,
            "coding_task_id": "coding-task-1",
            "status": "running",
        }

    def list_account_runs_for_thread(
        self,
        thread_id: int,
        *,
        user_id: str,
    ) -> list[dict[str, Any]] | None:
        self._record(
            "list_account_runs_for_thread",
            {"thread_id": thread_id, "user_id": user_id},
        )
        if not self._owned(user_id):
            return None
        return [{"run_id": RUN_ID, "status": "running"}]

    def list_coding_runs_for_thread(
        self,
        thread_id: int,
        *,
        user_id: str,
    ) -> list[dict[str, Any]] | None:
        self._record(
            "list_coding_runs_for_thread",
            {"thread_id": thread_id, "user_id": user_id},
        )
        if not self._owned(user_id):
            return None
        return [{"run_id": RUN_ID, "coding_task_id": "coding-task-1"}]

    def update_run_status(self, *, run_id: str, status: str) -> bool:
        self.mutations.append(
            ("update_run_status", {"run_id": run_id, "status": status})
        )
        return True

    def create_deployment(self, **kwargs: Any) -> dict[str, Any]:
        self._record("create_deployment", kwargs)
        return {"deployment_id": "dep-1"}


class _RecordingPublisher:
    """AgentEventPublisher double that records emitted events."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def emit(self, **kwargs: Any) -> None:
        self.events.append(dict(kwargs))


class _FakeSession:
    """Session double that never resolves a row."""

    def query(self, *args: Any, **kwargs: Any) -> _FakeSession:
        return self

    def filter_by(self, **kwargs: Any) -> _FakeSession:
        return self

    def one_or_none(self) -> None:
        return None


class _FakeSessionContext:
    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    def __enter__(self) -> _FakeSession:
        return self._session

    def __exit__(self, *exc_info: Any) -> bool:
        return False


class _FakeDB:
    """DB double whose sessions resolve no credential rows."""

    def get_session(self) -> _FakeSessionContext:
        return _FakeSessionContext(_FakeSession())


# ---------------------------------------------------------------------------
# Fixtures and builders
# ---------------------------------------------------------------------------


@pytest.fixture
def store() -> _ScopedStore:
    return _ScopedStore()


@pytest.fixture
def wired(monkeypatch: pytest.MonkeyPatch, store: _ScopedStore) -> SimpleNamespace:
    """Install the deterministic store and publisher into the route module."""
    publisher = _RecordingPublisher()
    monkeypatch.setattr(agent_orchestration, "_store", store)
    monkeypatch.setattr(agent_orchestration, "_event_publisher", publisher)
    monkeypatch.setenv("GUARDIAN_API_KEY", API_KEY)
    return SimpleNamespace(store=store, publisher=publisher)


def _client(
    *,
    account: str | None = ACCOUNT_OWNER,
    bypass_account_session: bool = False,
) -> TestClient:
    """Isolated app exposing the agent routes with a resolved account.

    ``account=None`` leaves the authentication dependency untouched, so the
    production identity resolution is exercised instead of being overridden.

    ``bypass_account_session=True`` replaces the account-session gate. It is
    only used by the test that forces the private-preview store branch, where
    the real gate would demand a signed preview session and mask the store
    decision under test. Authentication itself is covered separately by
    :func:`test_authenticated_principal_is_resolved_without_dependency_override`.
    """
    app = FastAPI()
    app.include_router(agent_orchestration.router)
    app.include_router(agent_orchestration.chat_router)
    if account is not None:
        app.dependency_overrides[agent_orchestration.get_current_user] = lambda: account
    if bypass_account_session:
        app.dependency_overrides[agent_orchestration.require_api_key] = (
            lambda: "operator-key"
        )
    return TestClient(app)


def _headers() -> dict[str, str]:
    return {"X-API-Key": API_KEY}


def _coding_body(**overrides: Any) -> dict[str, Any]:
    """A structurally conforming coding-execution request body."""
    body: dict[str, Any] = {
        "coding_task_id": "coding-task-1",
        "thread_id": str(THREAD_ID),
        "source_message_id": "11",
        "attempt_id": "attempt-1",
        "user_id": ACCOUNT_OWNER,
        "project_id": None,
        "adapter_kind": "pi_codex_runner",
        "instructions": "echo proof",
        "repo_root": "/tmp",
        "context_summary": None,
        "permission_policy": {
            "allow_shell": True,
            "allow_network": False,
            "allow_write": False,
            "allowed_paths": [],
            "max_runtime_seconds": 30,
        },
        "provider_id": "provider-a",
        "model_id": "model-a",
        "credential_ref": "credential-a",
    }
    body.update(overrides)
    return body


def _assert_scoped_to(store: _ScopedStore, account: str) -> None:
    """Every store call must carry the authenticated account id, never None."""
    assert store.calls, "expected the route to reach the store"
    for name, kwargs in store.calls:
        assert (
            kwargs.get("user_id") == account
        ), f"{name} was not scoped to the authenticated account: {kwargs}"


# ---------------------------------------------------------------------------
# The identity helper
# ---------------------------------------------------------------------------


def test_absent_requested_identity_resolves_to_authenticated_principal() -> None:
    """No caller-supplied identity: the authenticated principal is authority."""
    resolved = agent_orchestration._resolved_request_user(ACCOUNT_OWNER)
    assert resolved == ACCOUNT_OWNER


def test_matching_requested_identity_is_accepted() -> None:
    resolved = agent_orchestration._resolved_request_user(ACCOUNT_OWNER, ACCOUNT_OWNER)
    assert resolved == ACCOUNT_OWNER


def test_conflicting_requested_identity_is_rejected() -> None:
    with pytest.raises(Exception) as excinfo:
        agent_orchestration._resolved_request_user(ACCOUNT_OWNER, ACCOUNT_OTHER)
    assert getattr(excinfo.value, "status_code", None) == 403
    assert getattr(excinfo.value, "detail", None) == "account_identity_mismatch"


def test_explicit_empty_requested_identity_is_rejected() -> None:
    """An explicitly supplied empty identity conflicts; it is not 'absent'.

    This is the control that fails if the helper resolves an empty requested
    identity to the authenticated principal.
    """
    with pytest.raises(Exception) as excinfo:
        agent_orchestration._resolved_request_user(ACCOUNT_OWNER, "")
    assert getattr(excinfo.value, "status_code", None) == 403
    assert getattr(excinfo.value, "detail", None) == "account_identity_mismatch"


def test_missing_authenticated_identity_is_rejected() -> None:
    for missing in ("", None, "   "):
        with pytest.raises(Exception) as excinfo:
            agent_orchestration._resolved_request_user(missing)
        assert getattr(excinfo.value, "status_code", None) == 401
        assert getattr(excinfo.value, "detail", None) == "account_identity_missing"


def test_unresolved_dependency_placeholder_is_rejected() -> None:
    placeholder = "Depends(get_current_user)"
    with pytest.raises(Exception) as excinfo:
        agent_orchestration._resolved_request_user(placeholder)
    assert getattr(excinfo.value, "status_code", None) == 401
    assert getattr(excinfo.value, "detail", None) == "account_identity_missing"


# ---------------------------------------------------------------------------
# The five corrected call sites
# ---------------------------------------------------------------------------


def test_get_run_scopes_lookup_to_authenticated_account(wired: SimpleNamespace) -> None:
    store = wired.store
    with _client() as client:
        response = client.get(f"/api/agents/runs/{RUN_ID}", headers=_headers())

    assert response.status_code == 200, response.text
    assert response.json()["run"]["run_id"] == RUN_ID
    _assert_scoped_to(store, ACCOUNT_OWNER)


def test_get_run_in_account_mode_uses_account_scoped_lookup(
    wired: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The remote/private-preview branch must scope by durable account origin."""
    monkeypatch.setattr(
        agent_orchestration.dependencies, "is_private_preview", lambda: True
    )
    store = wired.store
    with _client(bypass_account_session=True) as client:
        response = client.get(f"/api/agents/runs/{RUN_ID}", headers=_headers())

    assert response.status_code == 200, response.text
    assert store.call_names == ["get_account_run"]
    _assert_scoped_to(store, ACCOUNT_OWNER)


def test_get_coding_run_scopes_snapshot_to_authenticated_account(
    wired: SimpleNamespace,
) -> None:
    store = wired.store
    with _client() as client:
        response = client.get(f"/api/agents/runs/{RUN_ID}/coding", headers=_headers())

    assert response.status_code == 200, response.text
    assert store.call_names == ["get_coding_run_snapshot"]
    _assert_scoped_to(store, ACCOUNT_OWNER)


def test_cancel_run_scopes_lookup_to_authenticated_account(
    wired: SimpleNamespace,
) -> None:
    store = wired.store
    with _client() as client:
        response = client.post(f"/api/agents/runs/{RUN_ID}/cancel", headers=_headers())

    assert response.status_code == 200, response.text
    assert store.call_names == ["get_run"]
    _assert_scoped_to(store, ACCOUNT_OWNER)
    assert store.mutations == [
        ("update_run_status", {"run_id": RUN_ID, "status": "canceled"})
    ]


def test_cancel_run_cannot_mutate_unauthorized_run(wired: SimpleNamespace) -> None:
    """Cancellation requires a successful scoped lookup before any mutation."""
    store = wired.store
    with _client(account=ACCOUNT_OTHER) as client:
        response = client.post(f"/api/agents/runs/{RUN_ID}/cancel", headers=_headers())

    assert response.status_code == 404, response.text
    assert store.mutations == []
    _assert_scoped_to(store, ACCOUNT_OTHER)


def test_list_thread_runs_scopes_thread_lookup_to_authenticated_account(
    wired: SimpleNamespace,
) -> None:
    store = wired.store
    with _client() as client:
        response = client.get(
            f"/api/agents/chat/{THREAD_ID}/agent-runs", headers=_headers()
        )

    assert response.status_code == 200, response.text
    assert store.call_names == ["list_account_runs_for_thread"]
    _assert_scoped_to(store, ACCOUNT_OWNER)


def test_list_coding_runs_scopes_thread_lookup_to_authenticated_account(
    wired: SimpleNamespace,
) -> None:
    store = wired.store
    with _client() as client:
        response = client.get(f"/api/chat/{THREAD_ID}/coding-runs", headers=_headers())

    assert response.status_code == 200, response.text
    assert store.call_names == ["list_coding_runs_for_thread"]
    _assert_scoped_to(store, ACCOUNT_OWNER)


def test_chat_agent_runs_alias_matches_canonical_route(
    wired: SimpleNamespace,
) -> None:
    """The /api/chat alias must behave exactly like the canonical route."""
    store = wired.store
    with _client() as client:
        canonical = client.get(
            f"/api/agents/chat/{THREAD_ID}/agent-runs", headers=_headers()
        )
        alias = client.get(f"/api/chat/{THREAD_ID}/agent-runs", headers=_headers())

    assert canonical.status_code == 200, canonical.text
    assert alias.status_code == 200, alias.text
    assert canonical.json() == alias.json()
    assert store.call_names == [
        "list_account_runs_for_thread",
        "list_account_runs_for_thread",
    ]
    _assert_scoped_to(store, ACCOUNT_OWNER)


# ---------------------------------------------------------------------------
# 404 masking and account isolation
# ---------------------------------------------------------------------------


def test_cancel_run_cannot_mutate_unseen_run(wired: SimpleNamespace) -> None:
    """A run that does not exist cannot be mutated either."""
    store = wired.store
    with _client() as client:
        response = client.post(
            "/api/agents/runs/run-does-not-exist/cancel", headers=_headers()
        )

    assert response.status_code == 404, response.text
    assert store.mutations == []
    _assert_scoped_to(store, ACCOUNT_OWNER)


def test_missing_run_returns_404(wired: SimpleNamespace) -> None:
    """A run that does not exist is masked as 404, never as 403."""
    store = wired.store
    with _client() as client:
        response = client.get("/api/agents/runs/run-does-not-exist", headers=_headers())

    assert response.status_code == 404, response.text
    _assert_scoped_to(store, ACCOUNT_OWNER)


def test_cross_account_run_is_not_visible(wired: SimpleNamespace) -> None:
    """A run owned by another account is masked as 404, never as 403."""
    store = wired.store
    with _client(account=ACCOUNT_OTHER) as client:
        response = client.get(f"/api/agents/runs/{RUN_ID}", headers=_headers())

    assert response.status_code == 404, response.text
    _assert_scoped_to(store, ACCOUNT_OTHER)


def test_cross_account_thread_is_not_visible(wired: SimpleNamespace) -> None:
    store = wired.store
    with _client(account=ACCOUNT_OTHER) as client:
        response = client.get(f"/api/chat/{THREAD_ID}/coding-runs", headers=_headers())

    assert response.status_code == 404, response.text
    _assert_scoped_to(store, ACCOUNT_OTHER)


def test_no_store_lookup_when_authentication_fails(wired: SimpleNamespace) -> None:
    """An unauthenticated caller must not reach any store operation."""
    store = wired.store
    with _client() as client:
        response = client.get(
            f"/api/agents/runs/{RUN_ID}", headers={"X-API-Key": "wrong-key"}
        )

    assert response.status_code in {401, 403}
    assert store.calls == []


def test_no_store_lookup_when_identity_is_missing(wired: SimpleNamespace) -> None:
    """An unresolved identity must fail closed before any scoped lookup."""
    store = wired.store
    with _client(account="") as client:
        response = client.get(f"/api/agents/runs/{RUN_ID}", headers=_headers())

    assert response.status_code == 401, response.text
    assert store.calls == []


def test_authenticated_principal_is_resolved_without_dependency_override(
    wired: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Genuine authentication: the production identity resolution is exercised.

    Overriding a dependency would only prove the override works. This test
    leaves `get_current_user` untouched and drives the real local principal
    resolution, so it also proves the production gate still supplies an
    account identity.
    """
    monkeypatch.setenv("CODEXIFY_SINGLE_USER_ID", ACCOUNT_OWNER)
    store = wired.store
    with _client(account=None) as client:
        response = client.get(f"/api/agents/runs/{RUN_ID}", headers=_headers())

    assert response.status_code == 200, response.text
    _assert_scoped_to(store, ACCOUNT_OWNER)


# ---------------------------------------------------------------------------
# Coding execution keeps strict explicit-identity enforcement
# ---------------------------------------------------------------------------


def test_coding_execution_rejects_conflicting_user_id(
    wired: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A body user_id that differs from the caller is still rejected."""
    credential_calls: list[dict[str, Any]] = []

    def _spy(*args: Any, **kwargs: Any) -> dict[str, Any]:
        credential_calls.append(dict(kwargs))
        raise AssertionError("credential authority must not be reached")

    monkeypatch.setattr(agent_orchestration, "authorize_credential_selection", _spy)

    with _client() as client:
        response = client.post(
            CODING_ROUTE,
            headers=_headers(),
            json=_coding_body(user_id=ACCOUNT_OTHER),
        )

    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "account_identity_mismatch"
    assert credential_calls == []


def test_coding_execution_rejects_explicit_empty_user_id(
    wired: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An explicitly empty body user_id is a conflict, not an absent identity."""
    credential_calls: list[dict[str, Any]] = []

    def _spy(*args: Any, **kwargs: Any) -> dict[str, Any]:
        credential_calls.append(dict(kwargs))
        raise AssertionError("credential authority must not be reached")

    monkeypatch.setattr(agent_orchestration, "authorize_credential_selection", _spy)

    with _client() as client:
        response = client.post(
            CODING_ROUTE,
            headers=_headers(),
            json=_coding_body(user_id=""),
        )

    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "account_identity_mismatch"
    assert credential_calls == []


def test_coding_execution_still_requires_credential_authority(
    wired: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A matching identity still reaches the real credential-authority gate.

    The lineage lookup is stubbed because it is a database-backed seam that
    would otherwise mask the credential decision. The credential authority
    itself is NOT stubbed: it runs and denies, proving the identity
    correction did not weaken it.
    """
    monkeypatch.setattr(
        agent_orchestration,
        "_validate_coding_lineage",
        lambda **kwargs: None,
    )
    wired.store.db = _FakeDB()

    with _client() as client:
        response = client.post(
            CODING_ROUTE,
            headers=_headers(),
            json=_coding_body(),
        )

    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "credential_reference_missing"
