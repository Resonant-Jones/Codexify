"""Coding-worker client for Guardian's sealed, invocation-bound API-key lease."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from guardian.agents.credential_transport import (
    generate_lease_keypair,
    open_lease_payload,
)


class CredentialLeaseClientError(RuntimeError):
    """Safe failure that never includes response bodies or credential data."""


def request_coding_credential_lease(
    *,
    binding: dict[str, Any],
    run_id: str,
    deployment_id: str,
    coding_task_id: str,
    attempt_id: str,
    attempt_index: int,
) -> tuple[str, dict[str, Any]]:
    if (
        str(binding.get("attempt_id") or "") != attempt_id
        or str(binding.get("coding_task_id") or "") != coding_task_id
    ):
        raise CredentialLeaseClientError("guardian_credential_lease_binding_mismatch")
    service_key = (os.getenv("GUARDIAN_API_KEY") or "").strip()
    if not service_key:
        raise CredentialLeaseClientError("guardian_service_authority_unavailable")
    base_url = (
        os.getenv("GUARDIAN_INTERNAL_URL") or "http://backend:8888"
    ).strip().rstrip("/")
    private_pem, public_pem = generate_lease_keypair()
    payload = {
        "run_id": run_id,
        "deployment_id": deployment_id,
        "coding_task_id": coding_task_id,
        "attempt_id": attempt_id,
        "attempt_index": attempt_index,
        "worker_public_key": public_pem.decode("ascii"),
    }
    request = Request(
        f"{base_url}/api/agents/coding/credential-lease",
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-API-Key": service_key,
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            response_payload = json.loads(response.read(32_768))
    except HTTPError as exc:
        raise CredentialLeaseClientError(
            f"guardian_credential_lease_rejected_{exc.code}"
        ) from None
    except (URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
        raise CredentialLeaseClientError("guardian_credential_lease_unavailable") from None

    sealed = response_payload.get("sealed_lease") if isinstance(response_payload, dict) else None
    if not isinstance(sealed, dict):
        raise CredentialLeaseClientError("guardian_credential_lease_invalid")
    try:
        opened = open_lease_payload(private_pem, sealed)
    except Exception:
        raise CredentialLeaseClientError("guardian_credential_lease_unwrap_failed") from None
    finally:
        del private_pem

    secret = opened.get("api_key")
    lease = opened.get("lease")
    if (
        not isinstance(secret, str)
        or not secret
        or len(secret) > 8192
        or not isinstance(lease, dict)
    ):
        raise CredentialLeaseClientError("guardian_credential_lease_invalid")
    expected = {
        **binding,
        "account_id": binding.get("user_id"),
        "owner_scope": binding.get("credential_owner_scope"),
        "owner_id": binding.get("credential_owner_id"),
        "source_class": binding.get("credential_source_class"),
        "attempt_id": attempt_id,
        "attempt_index": attempt_index,
        "coding_task_id": coding_task_id,
    }
    if any(lease.get(key) != value for key, value in expected.items()):
        raise CredentialLeaseClientError("guardian_credential_lease_binding_mismatch")
    if not str(lease.get("lease_id") or "").strip():
        raise CredentialLeaseClientError("guardian_credential_lease_invalid")
    try:
        lease_expiry = datetime.fromisoformat(str(lease.get("expires_at")))
        if lease_expiry.tzinfo is None:
            raise ValueError("expired")
        now = datetime.now(timezone.utc)
        if lease_expiry <= now or lease_expiry > now + timedelta(minutes=3):
            raise ValueError("expired_or_unbounded")
    except (TypeError, ValueError):
        raise CredentialLeaseClientError("guardian_credential_lease_expired") from None
    return secret, lease
