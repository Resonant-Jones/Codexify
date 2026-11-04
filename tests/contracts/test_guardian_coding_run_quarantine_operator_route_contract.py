"""Guardian coding run — operator quarantine route contract.

The quarantine persistence operation is proven; this contract proves that an
**authenticated operator** can reach it through the existing, feature-gated
Guardian delegation route family -- and that nothing else can.

What this contract pins down:

- the route is absent under the existing default posture and present only
  when the existing feature gate is explicitly enabled,
- operator authentication is the established one, and account or guest
  credentials never reach the disposition,
- the request cannot grant authority: it carries the operator's optimistic
  concurrency values and a reason, nothing else,
- the route delegates to the existing service and performs no persistence of
  its own,
- the durable outcome is the one the atomic operation already produces.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import threading
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.core.auth import (
    ACCOUNT_SESSION_PURPOSE,
    OPERATOR_SESSION_PURPOSE,
    issue_session_token,
)
from guardian.core.hosted_room_session import issue_guest_session_token
from guardian.db.models import AgentEscalation, AgentRun
from guardian.routes import guardian_delegations

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CONTRACTS_DIR = Path(__file__).resolve().parent

_spec = importlib.util.spec_from_file_location(
    "_guardian_quarantine_contract",
    _CONTRACTS_DIR / "test_guardian_coding_run_uncertain_quarantine_contract.py",
)
assert _spec is not None and _spec.loader is not None
quarantine = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(quarantine)
acceptance = quarantine.acceptance

_QUARANTINE_PATH = "/api/guardian/delegations/runs/{run_id}/quarantine"
_OPERATOR_KEY = "operator-route-contract-key"
_SESSION_SECRET = "operator-route-contract-session-secret"


# ---------------------------------------------------------------------------
# Fixtures and helpers.
# ---------------------------------------------------------------------------


@pytest.fixture
def db() -> Iterator[Any]:
    with acceptance._disposable_postgres_engine() as engine:
        acceptance.Base.metadata.create_all(bind=engine)
        yield acceptance._TestDB(engine)


@pytest.fixture(autouse=True)
def _operator_key(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """The established Guardian operator authority: the configured API key."""
    monkeypatch.setenv("GUARDIAN_API_KEY", _OPERATOR_KEY)
    # Signed session credentials need a signing secret. The contract mints
    # operator, account, and guest tokens and the route verifies them with this
    # same secret, so it is stated explicitly rather than inherited from dev
    # mode.
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", _SESSION_SECRET)
    yield


@pytest.fixture
def operator_client(db: Any) -> TestClient:
    """A client for the explicitly enabled posture."""
    guardian_delegations.configure_db(db)
    app = FastAPI()
    app.include_router(guardian_delegations.router)
    return TestClient(app)


@pytest.fixture
def credential_client(db: Any) -> TestClient:
    """A client that presents only the credential the test chooses.

    The repository's root ``conftest.py`` gives every ``TestClient`` a default
    ``X-API-Key`` header so that ordinary tests stay terse. That default would
    silently turn an anonymous request into an authorized one, and would turn a
    single-principal request into a mixed one, so it is removed here: the
    principal-separation cases must present exactly one credential shape -- or
    none at all.
    """
    guardian_delegations.configure_db(db)
    app = FastAPI()
    app.include_router(guardian_delegations.router)
    client = TestClient(app)
    client.headers.pop("X-API-Key", None)
    return client


@pytest.fixture
def gated_off_client(db: Any) -> TestClient:
    """A client for the default posture: the router is not registered."""
    guardian_delegations.configure_db(db)
    return TestClient(FastAPI())


def _accepted_run(db: Any) -> Any:
    """A run accepted by a known worker instance and claim."""
    return quarantine._accepted_run(
        db,
        worker_instance_id=quarantine._INSTANCE_A,
        claim_id=quarantine._CLAIM_A,
    )


def _stale(db: Any, run_id: str) -> None:
    quarantine._stale_heartbeat(db, run_id, seconds=600)


def _body(
    *,
    worker_instance_id: str | None = quarantine._INSTANCE_A,
    claim_id: str | None = quarantine._CLAIM_A,
    reason: str | None = "operator reviewed the unresolved execution",
) -> dict[str, Any]:
    body: dict[str, Any] = {}
    if worker_instance_id is not None:
        body["expected_worker_instance_id"] = worker_instance_id
    if claim_id is not None:
        body["expected_worker_claim_id"] = claim_id
    if reason is not None:
        body["reason"] = reason
    return body


def _post(
    client: TestClient,
    run_id: str,
    *,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> Any:
    return client.post(
        _QUARANTINE_PATH.format(run_id=run_id),
        json=body if body is not None else _body(),
        headers=headers if headers is not None else {"X-API-Key": _OPERATOR_KEY},
    )


def _run_state(db: Any, run_id: str) -> dict[str, Any]:
    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=run_id).one()
        return {
            "status": row.status,
            "instance_id": row.coding_worker_instance_id,
            "claim_id": row.coding_worker_claim_id,
            "ended_at": row.ended_at,
        }


def _escalations(db: Any, run_id: str) -> list[Any]:
    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=run_id).one()
        return (
            session.query(AgentEscalation)
            .filter_by(run_id=row.id)
            .order_by(AgentEscalation.id.asc())
            .all()
        )


def _operator_token() -> str:
    token, _expires = issue_session_token(
        "operator-contract",
        3600,
        purpose=OPERATOR_SESSION_PURPOSE,
    )
    return token


def _account_token() -> str:
    token, _expires = issue_session_token(
        "account-contract",
        3600,
        purpose=ACCOUNT_SESSION_PURPOSE,
    )
    return token


# ---------------------------------------------------------------------------
# 1-2: the existing feature gate decides whether the route exists.
# ---------------------------------------------------------------------------


def _gate_probe(flag: str, *, supported_profile: str | None = None) -> list[str]:
    """Import the real app and report the registered Guardian delegation paths.

    The probe controls the *feature gate* only, so every other switch that can
    affect router registration is neutralized explicitly: the Guardian
    delegation family is quarantined in every supported profile, so an ambient
    ``CODEXIFY_SUPPORTED_PROFILE`` would hide the route regardless of the
    gate and would make this probe depend on unrelated ambient state.
    """
    env = dict(os.environ)
    env["GUARDIAN_API_KEY"] = _OPERATOR_KEY
    env["PYTEST_CURRENT_TEST"] = "gate-probe"
    env["CODEXIFY_BETA_CORE_ONLY"] = "0"
    if supported_profile:
        env["CODEXIFY_SUPPORTED_PROFILE"] = supported_profile
    else:
        env.pop("CODEXIFY_SUPPORTED_PROFILE", None)
    if flag:
        env["CODEXIFY_ENABLE_GUARDIAN_DELEGATIONS_ROUTES"] = flag
    else:
        env.pop("CODEXIFY_ENABLE_GUARDIAN_DELEGATIONS_ROUTES", None)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import guardian.guardian_api as api;"
                "print('\\n'.join(sorted({r.path for r in api.app.routes "
                "if 'guardian/delegations' in getattr(r, 'path', '')})))"
            ),
        ],
        cwd=str(_REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    return [line for line in result.stdout.splitlines() if line.strip()]


def test_the_route_is_absent_when_the_feature_flag_is_disabled() -> None:
    """The default supported posture exposes no Guardian delegation route."""
    paths = _gate_probe("")

    assert paths == []


def test_the_route_is_present_when_the_feature_flag_is_explicitly_enabled() -> None:
    """The route joins the existing family when the gate is explicitly enabled."""
    paths = _gate_probe("1")

    assert "/api/guardian/delegations" in paths
    assert "/api/guardian/delegations/runs/{run_id}/quarantine" in paths


def test_the_route_stays_quarantined_under_a_supported_profile() -> None:
    """Enabling the gate does not add a public surface to a supported profile.

    The Guardian delegation family is quarantined by every supported profile,
    so the new invocation path inherits that quarantine: it cannot appear in
    the supported release surface even when the feature gate is on.
    """
    paths = _gate_probe("1", supported_profile="v1-local-core-web-mcp")

    assert paths == []


# ---------------------------------------------------------------------------
# 3-8: principal separation.
# ---------------------------------------------------------------------------


def test_an_anonymous_request_is_rejected(
    credential_client: TestClient, db: Any
) -> None:
    """No credential is no authority."""
    task = _accepted_run(db)
    _stale(db, str(task.run_id))

    response = _post(credential_client, str(task.run_id), headers={})

    assert response.status_code == 401
    assert _run_state(db, str(task.run_id))["status"] == "running"
    assert _escalations(db, str(task.run_id)) == []


def test_an_account_purpose_token_is_rejected(
    credential_client: TestClient, db: Any
) -> None:
    """An account session is not an operator credential."""
    task = _accepted_run(db)
    _stale(db, str(task.run_id))

    response = _post(
        credential_client,
        str(task.run_id),
        headers={"Authorization": f"Bearer {_account_token()}"},
    )

    assert response.status_code == 401
    assert _run_state(db, str(task.run_id))["status"] == "running"
    assert _escalations(db, str(task.run_id)) == []


def test_a_guest_credential_is_rejected(
    credential_client: TestClient, db: Any
) -> None:
    """A guest credential is not an operator credential."""
    task = _accepted_run(db)
    _stale(db, str(task.run_id))

    guest_token, _expires = issue_guest_session_token(
        room_id="room-contract",
        room_slug="contract-room",
        participant_id="participant-contract",
        invitation_id="invitation-contract",
    )

    client = credential_client
    # The canonical guest lane: the guest cookie itself.
    client.cookies.set("codexify_hosted_room_session", guest_token)
    try:
        in_guest_lane = _post(credential_client, str(task.run_id), headers={})
    finally:
        client.cookies.clear()

    # The session-cookie lane: the same signed guest token presented where an
    # operator session would be presented.
    client.cookies.set("gc_session", guest_token)
    try:
        in_session_lane = _post(credential_client, str(task.run_id), headers={})
    finally:
        client.cookies.clear()

    assert in_guest_lane.status_code == 401
    assert in_session_lane.status_code == 401
    assert _run_state(db, str(task.run_id))["status"] == "running"
    assert _escalations(db, str(task.run_id)) == []


def test_an_expired_operator_token_is_rejected(
    credential_client: TestClient, db: Any
) -> None:
    """An expired operator token authorizes nothing."""
    task = _accepted_run(db)
    _stale(db, str(task.run_id))
    token, _expires = issue_session_token(
        "operator-contract",
        -60,
        purpose=OPERATOR_SESSION_PURPOSE,
    )

    response = _post(
        credential_client,
        str(task.run_id),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert _run_state(db, str(task.run_id))["status"] == "running"
    assert _escalations(db, str(task.run_id)) == []


def test_an_invalid_operator_key_is_rejected(
    operator_client: TestClient, db: Any
) -> None:
    """A wrong configured key authorizes nothing."""
    task = _accepted_run(db)
    _stale(db, str(task.run_id))

    response = _post(
        operator_client,
        str(task.run_id),
        headers={"X-API-Key": "not-the-operator-key"},
    )

    assert response.status_code == 401
    assert _run_state(db, str(task.run_id))["status"] == "running"
    assert _escalations(db, str(task.run_id)) == []


def test_a_mixed_principal_request_is_rejected(
    operator_client: TestClient, db: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An account token may not fall back to an operator key."""
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
    task = _accepted_run(db)
    _stale(db, str(task.run_id))

    response = _post(
        operator_client,
        str(task.run_id),
        headers={
            "X-API-Key": _OPERATOR_KEY,
            "Authorization": f"Bearer {_account_token()}",
        },
    )

    assert response.status_code in {400, 401}
    assert _run_state(db, str(task.run_id))["status"] == "running"
    assert _escalations(db, str(task.run_id)) == []


# ---------------------------------------------------------------------------
# 9-10: the accepted operator credentials.
# ---------------------------------------------------------------------------


def test_a_valid_operator_api_key_is_accepted(
    operator_client: TestClient, db: Any
) -> None:
    """The configured Guardian API key is operator authority."""
    task = _accepted_run(db)
    _stale(db, str(task.run_id))

    response = _post(operator_client, str(task.run_id))

    assert response.status_code == 201
    payload = response.json()
    assert payload["disposition"] == "escalated"
    assert payload["already_quarantined"] is False
    assert _run_state(db, str(task.run_id))["status"] == "escalated"


def test_a_valid_operator_session_is_accepted(
    credential_client: TestClient, db: Any
) -> None:
    """An operator-purpose signed token is operator authority."""
    task = _accepted_run(db)
    _stale(db, str(task.run_id))

    response = _post(
        credential_client,
        str(task.run_id),
        headers={"Authorization": f"Bearer {_operator_token()}"},
    )

    assert response.status_code == 201
    assert response.json()["disposition"] == "escalated"
    assert _run_state(db, str(task.run_id))["status"] == "escalated"


# ---------------------------------------------------------------------------
# 11-16: the request contract.
# ---------------------------------------------------------------------------


def test_a_caller_supplied_authorization_boolean_is_rejected(
    operator_client: TestClient, db: Any
) -> None:
    """A request field cannot grant authority."""
    task = _accepted_run(db)
    _stale(db, str(task.run_id))

    body = _body()
    body["operator_authorized"] = True
    response = _post(operator_client, str(task.run_id), body=body)

    assert response.status_code == 422
    assert _run_state(db, str(task.run_id))["status"] == "running"
    assert _escalations(db, str(task.run_id)) == []


def test_a_missing_operator_reason_is_rejected(
    operator_client: TestClient, db: Any
) -> None:
    """Quarantine requires an intentional, reasoned decision."""
    task = _accepted_run(db)
    _stale(db, str(task.run_id))

    response = _post(operator_client, str(task.run_id), body=_body(reason=None))

    assert response.status_code == 422
    assert _run_state(db, str(task.run_id))["status"] == "running"


def test_an_oversized_operator_reason_is_rejected(
    operator_client: TestClient, db: Any
) -> None:
    """The operator reason is bounded."""
    task = _accepted_run(db)
    _stale(db, str(task.run_id))

    response = _post(
        operator_client,
        str(task.run_id),
        body=_body(reason="x" * 5000),
    )

    assert response.status_code == 422
    assert _run_state(db, str(task.run_id))["status"] == "running"


def test_a_missing_worker_identity_is_rejected(
    operator_client: TestClient, db: Any
) -> None:
    """The expected owner is required."""
    task = _accepted_run(db)
    _stale(db, str(task.run_id))

    response = _post(
        operator_client,
        str(task.run_id),
        body=_body(worker_instance_id=None),
    )

    assert response.status_code == 422
    assert _run_state(db, str(task.run_id))["status"] == "running"


def test_a_missing_claim_identity_is_rejected(
    operator_client: TestClient, db: Any
) -> None:
    """The expected claim is required."""
    task = _accepted_run(db)
    _stale(db, str(task.run_id))

    response = _post(
        operator_client,
        str(task.run_id),
        body=_body(claim_id=None),
    )

    assert response.status_code == 422
    assert _run_state(db, str(task.run_id))["status"] == "running"


def test_unknown_request_fields_are_rejected(
    operator_client: TestClient, db: Any
) -> None:
    """The request model forbids unknown fields."""
    task = _accepted_run(db)
    _stale(db, str(task.run_id))

    body = _body()
    body["target_status"] = "failed"
    response = _post(operator_client, str(task.run_id), body=body)

    assert response.status_code == 422
    assert _run_state(db, str(task.run_id))["status"] == "running"


# ---------------------------------------------------------------------------
# 17-18: the route delegates; the service revalidates.
# ---------------------------------------------------------------------------


def test_the_route_delegates_to_the_existing_service(
    operator_client: TestClient, db: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The route performs no persistence of its own."""
    task = _accepted_run(db)
    _stale(db, str(task.run_id))
    calls: list[dict[str, Any]] = []
    original = guardian_delegations._service.quarantine_uncertain_coding_run

    def _recording(**kwargs: Any) -> dict[str, Any]:
        calls.append(dict(kwargs))
        return original(**kwargs)

    monkeypatch.setattr(
        guardian_delegations._service,
        "quarantine_uncertain_coding_run",
        _recording,
    )

    response = _post(operator_client, str(task.run_id))

    assert response.status_code == 201
    assert len(calls) == 1
    call = calls[0]
    assert call["run_id"] == str(task.run_id)
    assert call["expected_worker_instance_id"] == quarantine._INSTANCE_A
    assert call["expected_claim_id"] == quarantine._CLAIM_A
    assert call["reason"]
    # The credential material travels server-side, never from the body.
    assert call.get("operator_api_key") == _OPERATOR_KEY


def test_the_service_revalidates_canonical_ownership(
    operator_client: TestClient, db: Any
) -> None:
    """A stale claim in the request cannot disposition the run."""
    task = _accepted_run(db)
    _stale(db, str(task.run_id))

    response = _post(
        operator_client,
        str(task.run_id),
        body=_body(claim_id=quarantine._CLAIM_B),
    )

    assert response.status_code == 409
    assert _run_state(db, str(task.run_id))["status"] == "running"
    assert _escalations(db, str(task.run_id)) == []


def test_an_active_peer_run_is_unaffected(
    operator_client: TestClient, db: Any
) -> None:
    """Disposing one run through the route never touches the peer's run.

    Worker A owns the target run; Worker B owns a second, independently
    accepted run. The operator invocation must move only the run it names.
    """
    target = _accepted_run(db)
    peer = quarantine._second_run(db)
    _stale(db, str(target.run_id))

    peer_before = _run_state(db, str(peer.run_id))
    assert peer_before["status"] == "running"
    assert peer_before["instance_id"] == quarantine._INSTANCE_B
    assert peer_before["claim_id"] == quarantine._CLAIM_B

    response = _post(operator_client, str(target.run_id))

    assert response.status_code == 201
    peer_after = _run_state(db, str(peer.run_id))
    assert peer_after["status"] == "running"
    assert peer_after["instance_id"] == quarantine._INSTANCE_B
    assert peer_after["claim_id"] == quarantine._CLAIM_B
    assert _escalations(db, str(peer.run_id)) == []


def test_the_request_cannot_name_an_account(
    operator_client: TestClient, db: Any
) -> None:
    """No client-supplied account can aim a disposition at another account.

    The account is canonical and is read from the run row inside the
    transaction; it is never client-supplied, so the request model refuses the
    field outright and the run is left untouched.
    """
    task = _accepted_run(db)
    _stale(db, str(task.run_id))

    response = _post(
        operator_client,
        str(task.run_id),
        body={**_body(), "account_user_id": "some-other-account"},
    )

    assert response.status_code == 422
    assert _run_state(db, str(task.run_id))["status"] == "running"
    assert _escalations(db, str(task.run_id)) == []


def test_a_fresh_heartbeat_prevents_quarantine(
    operator_client: TestClient, db: Any
) -> None:
    """An actively reporting run is not a recovery candidate."""
    task = _accepted_run(db)

    response = _post(operator_client, str(task.run_id))

    assert response.status_code == 409
    assert _run_state(db, str(task.run_id))["status"] == "running"
    assert _escalations(db, str(task.run_id)) == []


def test_a_changed_worker_claim_prevents_quarantine(
    operator_client: TestClient, db: Any
) -> None:
    """The claim must still be the one the worker holds."""
    task = _accepted_run(db)
    _stale(db, str(task.run_id))
    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=str(task.run_id)).one()
        row.coding_worker_claim_id = quarantine._CLAIM_B
        session.commit()

    response = _post(operator_client, str(task.run_id))

    assert response.status_code == 409
    assert _run_state(db, str(task.run_id))["status"] == "running"
    assert _escalations(db, str(task.run_id)) == []


def test_an_already_terminal_run_remains_unchanged(
    operator_client: TestClient, db: Any
) -> None:
    """A completed run is not dispositioned."""
    task = _accepted_run(db)
    _stale(db, str(task.run_id))
    acceptance._store_coding_result_placeholder = None
    AgentStore = quarantine.AgentStore
    AgentStore(db=db).update_run_status(
        run_id=str(task.run_id),
        status="succeeded",
    )

    response = _post(operator_client, str(task.run_id))

    assert response.status_code == 409
    assert _run_state(db, str(task.run_id))["status"] == "succeeded"
    assert _escalations(db, str(task.run_id)) == []


def test_an_existing_identical_quarantine_is_idempotent(
    operator_client: TestClient, db: Any
) -> None:
    """A repeated request observes the committed disposition read-only."""
    task = _accepted_run(db)
    _stale(db, str(task.run_id))

    first = _post(operator_client, str(task.run_id))
    second = _post(operator_client, str(task.run_id))

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["already_quarantined"] is True
    assert second.json()["escalation_id"] == first.json()["escalation_id"]
    assert len(_escalations(db, str(task.run_id))) == 1


def test_a_conflicting_quarantine_is_rejected(
    operator_client: TestClient, db: Any
) -> None:
    """A disposition by another authority is never rewritten."""
    task = _accepted_run(db)
    _stale(db, str(task.run_id))
    AgentStore = quarantine.AgentStore
    AgentStore(db=db).add_escalation(
        run_id=str(task.run_id),
        step_index=None,
        severity="hard",
        reason_code="some_other_reason",
        reason="A different disposition.",
        preserved_worktree=False,
        payload={"operator_actor": "someone-else"},
    )
    AgentStore(db=db).update_run_status(
        run_id=str(task.run_id),
        status="escalated",
    )

    response = _post(operator_client, str(task.run_id))

    assert response.status_code == 409
    escalations = _escalations(db, str(task.run_id))
    assert len(escalations) == 1
    assert escalations[0].reason_code == "some_other_reason"


def test_concurrent_terminalization_remains_safe(
    operator_client: TestClient, db: Any
) -> None:
    """A terminal decision and a quarantine cannot both win."""
    task = _accepted_run(db)
    _stale(db, str(task.run_id))
    barrier = threading.Barrier(2)

    def _terminalize() -> str:
        barrier.wait(timeout=30)
        quarantine.AgentStore(db=db).update_run_status(
            run_id=str(task.run_id),
            status="succeeded",
        )
        return "terminal"

    def _quarantine_request() -> str:
        barrier.wait(timeout=30)
        response = _post(operator_client, str(task.run_id))
        return str(response.status_code)

    with ThreadPoolExecutor(max_workers=2) as pool:
        terminal_future = pool.submit(_terminalize)
        request_future = pool.submit(_quarantine_request)
        terminal_future.result(timeout=60)
        status = request_future.result(timeout=60)

    state = _run_state(db, str(task.run_id))
    escalations = _escalations(db, str(task.run_id))
    if status == "201":
        # The quarantine won: the run is escalated with exactly one record.
        assert state["status"] == "escalated"
        assert len(escalations) == 1
    else:
        # The terminal decision won: the run keeps its terminal status and
        # no quarantine escalation was created.
        assert state["status"] == "succeeded"
        assert escalations == []


# ---------------------------------------------------------------------------
# 25-27: the receipt.
# ---------------------------------------------------------------------------


def test_the_operator_response_contains_bounded_evidence(
    operator_client: TestClient, db: Any
) -> None:
    """The receipt reports the committed disposition and nothing more."""
    task = _accepted_run(db)
    _stale(db, str(task.run_id))

    response = _post(operator_client, str(task.run_id))

    payload = response.json()
    assert set(payload) == {
        "run_id",
        "disposition",
        "escalation_id",
        "reason_code",
        "original_worker_instance_id",
        "original_worker_claim_id",
        "operator_actor",
        "already_quarantined",
        "recorded_at",
    }
    assert payload["run_id"] == str(task.run_id)
    assert payload["disposition"] == "escalated"
    assert payload["original_worker_instance_id"] == quarantine._INSTANCE_A
    assert payload["original_worker_claim_id"] == quarantine._CLAIM_A
    assert payload["operator_actor"]
    assert payload["recorded_at"]


def test_no_credential_material_appears_in_the_response(
    operator_client: TestClient, db: Any
) -> None:
    """The receipt never echoes the operator credential."""
    task = _accepted_run(db)
    _stale(db, str(task.run_id))

    response = _post(operator_client, str(task.run_id))

    text = json.dumps(response.json())
    assert _OPERATOR_KEY not in text
    assert "sk-" not in text


def test_no_secret_material_enters_escalation_evidence(
    operator_client: TestClient, db: Any
) -> None:
    """The durable escalation evidence carries no credential material."""
    task = _accepted_run(db)
    _stale(db, str(task.run_id))

    _post(operator_client, str(task.run_id))

    escalations = _escalations(db, str(task.run_id))
    assert len(escalations) == 1
    text = json.dumps(escalations[0].payload_json).lower()
    assert _OPERATOR_KEY.lower() not in text
    for marker in ("api_key", "bearer ", "authorization", "prompt"):
        assert marker not in text


# ---------------------------------------------------------------------------
# 28-33: nothing else happens.
# ---------------------------------------------------------------------------


def test_no_duplicate_escalation_row_is_created(
    operator_client: TestClient, db: Any
) -> None:
    """A repeated request does not duplicate the escalation."""
    task = _accepted_run(db)
    _stale(db, str(task.run_id))

    _post(operator_client, str(task.run_id))
    _post(operator_client, str(task.run_id))
    _post(operator_client, str(task.run_id))

    assert len(_escalations(db, str(task.run_id))) == 1


def test_no_coding_result_artifact_is_fabricated(
    operator_client: TestClient, db: Any
) -> None:
    """A quarantine creates no coding-result artifact."""
    task = _accepted_run(db)
    _stale(db, str(task.run_id))

    _post(operator_client, str(task.run_id))

    assert acceptance._artifact_count(db, str(task.run_id)) == 0


def test_no_source_thread_result_is_fabricated(
    operator_client: TestClient, db: Any
) -> None:
    """A quarantine delivers no result to the source thread."""
    task = _accepted_run(db)
    _stale(db, str(task.run_id))

    _post(operator_client, str(task.run_id))

    assert acceptance._coding_result_message_count(db, task.thread_id) == 0


def test_no_queue_task_is_inserted(
    operator_client: TestClient, db: Any
) -> None:
    """A quarantine enqueues nothing."""
    from guardian.queue.redis_queue import dequeue_coding_execution

    task = _accepted_run(db)
    _stale(db, str(task.run_id))

    _post(operator_client, str(task.run_id))

    assert dequeue_coding_execution(block=False) is None


def test_no_credential_lease_is_issued(
    operator_client: TestClient, db: Any
) -> None:
    """A quarantine issues no credential lease."""
    from guardian.db.models import CodingWorktreeLease

    task = _accepted_run(db)
    _stale(db, str(task.run_id))

    _post(operator_client, str(task.run_id))

    with db.get_session() as session:
        assert session.query(CodingWorktreeLease).count() == 0


def test_no_new_worker_attempt_is_authorized(
    operator_client: TestClient, db: Any
) -> None:
    """A quarantine creates no execution attempt."""
    from guardian.db.models import AgentRunAttempt

    task = _accepted_run(db)
    _stale(db, str(task.run_id))
    with db.get_session() as session:
        before = session.query(AgentRunAttempt).count()

    _post(operator_client, str(task.run_id))

    with db.get_session() as session:
        assert session.query(AgentRunAttempt).count() == before


def test_database_unavailability_fails_closed(
    operator_client: TestClient, db: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unreachable persistence never becomes a success."""
    task = _accepted_run(db)
    _stale(db, str(task.run_id))
    monkeypatch.setattr(
        guardian_delegations._service.agent_store,
        "_has_db",
        lambda: False,
    )

    response = _post(operator_client, str(task.run_id))

    assert response.status_code == 503
    assert _run_state(db, str(task.run_id))["status"] == "running"
    assert _escalations(db, str(task.run_id)) == []


def test_existing_delegation_routes_retain_their_behavior(
    operator_client: TestClient, db: Any
) -> None:
    """The existing intent routes are untouched by the new one."""
    seeded = acceptance._seed_account(db)
    response = operator_client.get(
        "/api/guardian/delegations",
        params={"thread_id": seeded["thread_id"]},
        headers={"X-API-Key": _OPERATOR_KEY},
    )

    assert response.status_code == 200
    assert isinstance(response.json(), dict)


def test_the_route_is_absent_under_the_default_posture(
    gated_off_client: TestClient, db: Any
) -> None:
    """No route means no public operator surface."""
    task = _accepted_run(db)
    _stale(db, str(task.run_id))

    response = _post(gated_off_client, str(task.run_id))

    assert response.status_code == 404
    assert _run_state(db, str(task.run_id))["status"] == "running"
    assert _escalations(db, str(task.run_id)) == []
