"""Authenticated HTTP and disposable PostgreSQL proof for the preflight."""

from copy import deepcopy
from types import SimpleNamespace

import psycopg
import pytest

from guardian.routes import migration
from tests.services.test_imported_history_evidence import A, B, snapshot

pytest_plugins = ["tests.routes.test_imported_history_inspection"]

PATH = "/api/imports/history/chronicle/authorization-check"
BODY = {
    "project_id": 1,
    "thread_ids": [10, 11],
    "origins": ["openai", "anthropic"],
    "max_messages": 100,
    "max_inspected_messages": 1000,
    "max_excerpt_bytes": 8192,
    "max_response_bytes": 262144,
    "offset": 0,
    "purpose": "migration_chronicle_preview",
    "interpretation_consent": True,
    "import_treatment": "recallable_archive",
}


def post(http, body=None, headers=None):
    return http.client.post(
        PATH,
        json=BODY if body is None else body,
        headers=(
            {"Authorization": "Bearer " + http.token_a} if headers is None else headers
        ),
    )


def denied(response, status=403):
    assert response.status_code == status, response.text
    assert response.headers["Cache-Control"] == "no-store"
    assert "excerpts" not in response.text
    assert "grant" not in response.text.lower()
    assert "secret" not in response.text.lower()


def test_authenticated_scope_is_exact_ephemeral_and_read_only(http):
    before = snapshot(http.url)
    response = post(http)
    assert response.status_code == 200, response.text
    assert response.headers["Cache-Control"] == "no-store"
    result = response.json()
    assert result["authorized"] is True
    assert result["scope"] == {
        "project_id": 1,
        "thread_ids": [10, 11],
        "origins": ["openai", "anthropic"],
        "max_messages": 100,
        "max_inspected_messages": 1000,
        "max_excerpt_bytes": 8192,
        "max_response_bytes": 262144,
        "offset": 0,
        "purpose": "migration_chronicle_preview",
        "import_treatment": "recallable_archive",
    }
    assert "grant" not in result and "excerpts" not in result
    assert http.redis.writes == 0
    assert not http.client.app.dependency_overrides
    assert snapshot(http.url) == before


@pytest.mark.parametrize("credential", ["missing", "operator", "guest", "unmapped"])
def test_account_authentication_is_required(http, credential):
    headers = {}
    if credential in {"operator", "guest"}:
        headers["Authorization"] = "Bearer " + getattr(http, credential)
    elif credential == "unmapped":
        from guardian.core.auth import issue_session_token

        headers["Authorization"] = (
            "Bearer "
            + issue_session_token("unknown-subject", purpose="account_session")[0]
        )
    denied(post(http, headers=headers), 401)


def test_client_identity_and_single_user_mode_cannot_widen_account_scope(http):
    body = deepcopy(BODY)
    body.update(project_id=1, thread_ids=[10], origins=["openai"])
    denied(
        post(
            http,
            body,
            headers={
                "Authorization": "Bearer " + http.token_b,
                "X-User-Id": A,
            },
        )
    )
    http.settings.CODEXIFY_MULTI_USER_ENABLED = False
    denied(
        post(
            http,
            body,
            headers={"Authorization": "Bearer " + http.token_b},
        ),
        401,
    )
    http.settings.CODEXIFY_MULTI_USER_ENABLED = True


def test_mixed_account_and_guest_credentials_are_rejected(http):
    http.client.cookies.set("codexify_hosted_room_session", http.guest)
    denied(
        post(
            http,
            headers={"Authorization": "Bearer " + http.token_a},
        ),
        400,
    )
    http.client.cookies.delete("codexify_hosted_room_session")


@pytest.mark.parametrize(
    "mutate",
    [
        lambda b: b.pop("interpretation_consent"),
        lambda b: b.update(interpretation_consent=False),
        lambda b: b.pop("import_treatment"),
        lambda b: b.update(import_treatment="archive_only"),
        lambda b: b.update(import_treatment="continuity_scaffold"),
        lambda b: b.update(import_treatment="unknown"),
        lambda b: b.update(purpose="account_wide_history"),
        lambda b: b.update(account_id=B),
        lambda b: b.update(grant="old-token"),
        lambda b: b.update(project_id=3),
        lambda b: b.update(thread_ids=[10, 10]),
        lambda b: b.update(thread_ids=[12]),
        lambda b: b.update(thread_ids=[10]),
        lambda b: b.update(origins=["codexify"]),
        lambda b: b.update(thread_ids=list(range(1, 22))),
    ],
)
def test_invalid_policy_or_scope_fails_closed(http, mutate):
    body = deepcopy(BODY)
    mutate(body)
    response = post(http, body)
    assert response.headers["Cache-Control"] == "no-store"
    assert response.status_code in (403, 422, 404)
    assert "excerpts" not in response.text
    assert "grant" not in response.text.lower()


@pytest.mark.parametrize("thread_id", [15, 16])
def test_diary_and_modeling_exclusions_deny_without_changing_inspection(
    http, thread_id
):
    body = deepcopy(BODY)
    body.update(thread_ids=[thread_id], origins=["openai"])
    before = snapshot(http.url)
    denied(post(http, body))
    assert snapshot(http.url) == before


def test_project_ownership_conflict_and_foreign_thread_deny(http):
    body = deepcopy(BODY)
    body.update(project_id=5, thread_ids=[21], origins=["openai"])
    denied(post(http, body))
    body.update(project_id=1, thread_ids=[14], origins=["openai"])
    denied(post(http, body))


def test_response_cannot_be_reused_as_authority(http):
    first = post(http)
    assert first.status_code == 200
    second_body = deepcopy(BODY)
    second_body["authorization"] = first.json()
    denied(post(http, second_body), 422)
    assert http.redis.writes == 0


def test_unavailable_canonical_authorization_store_fails_closed(http, monkeypatch):
    monkeypatch.setattr(
        migration,
        "chatlog_db",
        SimpleNamespace(
            _connect=lambda: (_ for _ in ()).throw(
                psycopg.OperationalError("fixture unavailable")
            )
        ),
    )
    response = post(http)
    denied(response, 503)
