from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from guardian.agents.execution_credentials import (
    CredentialAuthorityError,
    authorize_binding_credential,
    authorize_credential_selection,
    issue_api_key_lease,
    revoke_account_credential,
    store_api_key,
)
from guardian.db.models import (
    Base,
    CodingExecutionCredential,
    CodingExecutionCredentialLease,
)


class _CredentialDB:
    def __init__(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(
            self.engine,
            tables=[
                CodingExecutionCredential.__table__,
                CodingExecutionCredentialLease.__table__,
            ],
        )
        self._sessions = sessionmaker(bind=self.engine, expire_on_commit=False)

    @contextmanager
    def get_session(self) -> Iterator[Session]:
        session = self._sessions()
        try:
            yield session
        finally:
            session.close()


def _store_account_credential(db: _CredentialDB) -> dict[str, object]:
    return store_api_key(
        db,
        owner_scope="account",
        owner_id="account-a",
        provider_id="provider-a",
        api_key="SECRET-SENTINEL-account-a",
        funding_route="user_byok",
    )


def _binding(credential: dict[str, object], **overrides: object) -> dict[str, object]:
    return {
        "binding_id": "xeb-binding-a",
        "credential_ref": credential["credential_ref"],
        "credential_owner_scope": credential["owner_scope"],
        "credential_owner_id": credential["owner_id"],
        "provider_id": credential["provider_id"],
        "model_id": "model-a",
        "funding_route": credential["funding_route"],
        "usage_policy_ref": credential.get("usage_policy_ref"),
        "user_id": "account-a",
        "harness_id": "pi",
        "harness_selection_mode": "default",
        "attempt_id": "attempt-a",
        "max_attempts": 2,
        **overrides,
    }


def test_account_secret_is_encrypted_and_leased_once_per_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "test-execution-credential-key")
    db = _CredentialDB()
    credential = _store_account_credential(db)

    assert "SECRET-SENTINEL-account-a" not in str(credential)
    with db.get_session() as session:
        stored = session.query(CodingExecutionCredential).one()
        assert stored.encrypted_secret != "SECRET-SENTINEL-account-a"
        assert stored.encrypted_secret

    secret, lease = issue_api_key_lease(
        db,
        binding=_binding(credential),
        account_id="account-a",
        attempt_id="attempt-a",
        attempt_index=1,
    )
    assert secret == "SECRET-SENTINEL-account-a"
    assert lease["credential_owner_scope"] == "account"
    assert lease["account_id"] == "account-a"
    assert "SECRET-SENTINEL-account-a" not in str(lease)
    with db.get_session() as session:
        durable_lease = session.query(CodingExecutionCredentialLease).one()
        assert "SECRET-SENTINEL-account-a" not in repr(durable_lease)

    with pytest.raises(CredentialAuthorityError, match="already_leased"):
        issue_api_key_lease(
            db,
            binding=_binding(credential),
            account_id="account-a",
            attempt_id="attempt-a",
            attempt_index=1,
        )


def test_account_credentials_reject_cross_account_provider_and_operator_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "test-execution-credential-key")
    db = _CredentialDB()
    account_credential = _store_account_credential(db)

    with pytest.raises(CredentialAuthorityError, match="account_credential_owner_mismatch"):
        authorize_credential_selection(
            db,
            credential_ref=str(account_credential["credential_ref"]),
            account_id="account-b",
            provider_id="provider-a",
            model_id="model-a",
        )
    with pytest.raises(CredentialAuthorityError, match="provider_mismatch"):
        authorize_credential_selection(
            db,
            credential_ref=str(account_credential["credential_ref"]),
            account_id="account-a",
            provider_id="provider-b",
            model_id="model-a",
        )

    operator_credential = store_api_key(
        db,
        owner_scope="operator",
        owner_id="operator-local",
        provider_id="provider-a",
        api_key="SECRET-SENTINEL-operator",
        funding_route="local_self_hosted",
    )
    with pytest.raises(
        CredentialAuthorityError,
        match="operator_credential_not_authorized_for_account",
    ):
        authorize_credential_selection(
            db,
            credential_ref=str(operator_credential["credential_ref"]),
            account_id="account-a",
            provider_id="provider-a",
            model_id="model-a",
        )

    with pytest.raises(CredentialAuthorityError, match="credential_reference_missing"):
        authorize_credential_selection(
            db,
            credential_ref="credential-does-not-exist",
            account_id="account-a",
            provider_id="provider-a",
            model_id="model-a",
        )


def test_service_credential_remains_service_owned_and_policy_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "test-execution-credential-key")
    db = _CredentialDB()
    credential = store_api_key(
        db,
        owner_scope="service",
        owner_id="deployment-service-a",
        provider_id="provider-a",
        api_key="SECRET-SENTINEL-service",
        funding_route="codexify_included",
        allowed_account_ids=["account-a"],
        allowed_model_ids=["model-a"],
        usage_policy_ref="usage-policy-a",
    )

    selected = authorize_credential_selection(
        db,
        credential_ref=str(credential["credential_ref"]),
        account_id="account-a",
        provider_id="provider-a",
        model_id="model-a",
    )
    assert selected["owner_scope"] == "service"
    assert selected["owner_id"] == "deployment-service-a"
    assert selected["usage_policy_ref"] == "usage-policy-a"

    binding = _binding(credential, credential_owner_scope="service")
    assert authorize_binding_credential(
        db, binding=binding, account_id="account-a"
    )["owner_scope"] == "service"

    with pytest.raises(CredentialAuthorityError, match="service_account_policy_denied"):
        authorize_credential_selection(
            db,
            credential_ref=str(credential["credential_ref"]),
            account_id="account-b",
            provider_id="provider-a",
            model_id="model-a",
        )
    with pytest.raises(CredentialAuthorityError, match="service_model_policy_denied"):
        authorize_credential_selection(
            db,
            credential_ref=str(credential["credential_ref"]),
            account_id="account-a",
            provider_id="provider-a",
            model_id="model-b",
        )
    with pytest.raises(CredentialAuthorityError, match="usage_policy_mismatch"):
        authorize_binding_credential(
            db,
            binding={**binding, "usage_policy_ref": "other-policy"},
            account_id="account-a",
        )

    secret, lease = issue_api_key_lease(
        db,
        binding=binding,
        account_id="account-a",
        attempt_id="attempt-a",
        attempt_index=1,
    )
    assert secret == "SECRET-SENTINEL-service"
    assert lease["owner_scope"] == "service"
    assert lease["owner_id"] == "deployment-service-a"
    assert lease["account_id"] == "account-a"


def test_revocation_expiry_and_attempt_mismatch_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "test-execution-credential-key")
    db = _CredentialDB()
    credential = _store_account_credential(db)

    with pytest.raises(CredentialAuthorityError, match="attempt_binding_mismatch"):
        issue_api_key_lease(
            db,
            binding=_binding(credential),
            account_id="account-a",
            attempt_id="attempt-other",
            attempt_index=1,
        )

    with db.get_session() as session:
        stored = session.query(CodingExecutionCredential).one()
        stored.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        session.commit()
    with pytest.raises(CredentialAuthorityError, match="expired"):
        authorize_binding_credential(
            db, binding=_binding(credential), account_id="account-a"
        )

    with db.get_session() as session:
        stored = session.query(CodingExecutionCredential).one()
        stored.expires_at = None
        session.commit()
    assert revoke_account_credential(
        db,
        account_id="account-a",
        credential_ref=str(credential["credential_ref"]),
    )
    with pytest.raises(CredentialAuthorityError, match="revoked_or_missing"):
        authorize_credential_selection(
            db,
            credential_ref=str(credential["credential_ref"]),
            account_id="account-a",
            provider_id="provider-a",
            model_id="model-a",
        )
