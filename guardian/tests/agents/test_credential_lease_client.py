from __future__ import annotations

import io
import json
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from guardian.agents.credential_lease_client import (
    CredentialLeaseClientError,
    request_coding_credential_lease,
)
from guardian.agents.credential_transport import seal_lease_payload

_SECRET = "SYNTHETIC-LEASE-CLIENT-SECRET"


def _binding() -> dict[str, Any]:
    return {
        "binding_id": "xeb-account-a-attempt-a",
        "schema_version": 1,
        "harness_id": "pi",
        "harness_selection_mode": "default",
        "provider_id": "provider-a",
        "model_id": "model-a",
        "funding_route": "user_byok",
        "placement": "container",
        "credential_ref": "credential-account-a",
        "credential_owner_scope": "account",
        "credential_owner_id": "account-a",
        "credential_type": "api_key",
        "credential_source_class": "account_api_key",
        "usage_policy_ref": None,
        "user_id": "account-a",
        "project_id": "project-a",
        "thread_id": "thread-a",
        "source_message_id": "message-a",
        "coding_task_id": "coding-task-a",
        "attempt_id": "attempt-a",
        "max_attempts": 2,
        "authorization_evidence_ref": "evidence-a",
    }


def _run_client(
    monkeypatch: pytest.MonkeyPatch,
    *,
    overrides: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    binding = _binding()
    lease = {
        **binding,
        "lease_id": "cl-one-use-a",
        "owner_scope": "account",
        "owner_id": "account-a",
        "account_id": "account-a",
        "source_class": "account_api_key",
        "attempt_index": 1,
        "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat(),
        **(overrides or {}),
    }

    def _urlopen(request, *, timeout: int):
        assert timeout == 15
        request_payload = json.loads(request.data)
        sealed = seal_lease_payload(
            request_payload["worker_public_key"],
            {"api_key": _SECRET, "lease": lease},
        )
        return io.BytesIO(json.dumps({"sealed_lease": sealed}).encode("utf-8"))

    monkeypatch.setenv("GUARDIAN_API_KEY", "synthetic-worker-service-key")
    monkeypatch.setattr(
        "guardian.agents.credential_lease_client.urlopen",
        _urlopen,
    )
    return request_coding_credential_lease(
        binding=binding,
        run_id="run-a",
        deployment_id="deployment-a",
        coding_task_id="coding-task-a",
        attempt_id="attempt-a",
        attempt_index=1,
    )


def test_lease_client_unwraps_only_a_complete_matching_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret, lease = _run_client(monkeypatch)

    assert secret == _SECRET
    assert lease["provider_id"] == "provider-a"
    assert lease["credential_ref"] == "credential-account-a"
    assert lease["account_id"] == "account-a"
    assert _SECRET not in str(lease)


@pytest.mark.parametrize(
    ("field", "wrong_value"),
    [("placement", "host"), ("project_id", "project-b"), ("credential_source_class", "operator_api_key")],
)
def test_lease_client_rejects_any_binding_field_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    wrong_value: Any,
) -> None:
    with pytest.raises(CredentialLeaseClientError, match="binding_mismatch") as error:
        _run_client(monkeypatch, overrides={field: wrong_value})

    assert _SECRET not in str(error.value)


def test_lease_client_rejects_missing_receipt_or_unbounded_expiry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(CredentialLeaseClientError, match="lease_invalid"):
        _run_client(monkeypatch, overrides={"lease_id": ""})

    with pytest.raises(CredentialLeaseClientError, match="lease_expired"):
        _run_client(
            monkeypatch,
            overrides={
                "expires_at": (
                    datetime.now(timezone.utc) + timedelta(minutes=10)
                ).isoformat()
            },
        )
