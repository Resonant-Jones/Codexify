from fastapi import HTTPException
from guardian.routes import migration as routes
from tests.routes.test_migration_routes import test_client, SERVER_USER_ID


def identity():
    return {
        "relative_path": "export/original.dat",
        "file_size": 10,
        "file_sha256": "a" * 64,
        "source_export_fingerprint": "b" * 64,
    }


def test_repair_uses_authenticated_owner_and_json_identity(test_client, monkeypatch):
    seen = []
    monkeypatch.setattr(routes, "_get_account_import_service", lambda: object())

    def perform(service, **kwargs):
        seen.append(kwargs)
        return {"job": {"job_id": "job"}, "events": [], "busy": False}

    monkeypatch.setattr(routes, "repair_retained_pdf", perform)
    response = test_client.post(
        "/api/imports/openai-account/job/pdf-repair", json=identity()
    )
    assert (
        response.status_code == 200 and response.headers["cache-control"] == "no-store"
    )
    assert seen == [{"job_id": "job", "user_id": SERVER_USER_ID, **identity()}]


def test_auth_denial_is_private_and_never_enters_repair(test_client, monkeypatch):
    called = []

    def deny():
        raise HTTPException(
            401,
            "Account authentication required",
            headers={"X-Guardian-Auth-Failure": "ACCOUNT_SESSION_INVALID"},
        )

    test_client.app.dependency_overrides[routes.require_api_key] = deny
    monkeypatch.setattr(
        routes, "repair_retained_pdf", lambda *a, **k: called.append(True)
    )
    for method in ("get", "post"):
        response = getattr(test_client, method)(
            "/api/imports/openai-account/job/pdf-repair",
            **({"json": identity()} if method == "post" else {}),
        )
        assert (
            response.status_code == 401
            and response.headers["cache-control"] == "no-store"
        )
        assert response.headers["X-Guardian-Auth-Failure"] == "ACCOUNT_SESSION_INVALID"
    assert not called


def test_repair_rejects_caller_scope_and_sanitizes_invalid_body(test_client):
    response = test_client.post(
        "/api/imports/openai-account/job/pdf-repair",
        json={**identity(), "user_id": "secret-account", "data": "private-content"},
    )
    assert (
        response.status_code == 422
        and "private-content" not in response.text
        and "secret-account" not in response.text
    )
    assert response.headers["cache-control"] == "no-store"


def test_unexpected_error_never_returns_sql_or_document_text(test_client, monkeypatch):
    monkeypatch.setattr(routes, "_get_account_import_service", lambda: object())

    def fail(*a, **k):
        raise RuntimeError("private document SQL parameters")

    monkeypatch.setattr(routes, "repair_retained_pdf", fail)
    response = test_client.post(
        "/api/imports/openai-account/job/pdf-repair", json=identity()
    )
    assert (
        response.status_code == 503 and response.headers["cache-control"] == "no-store"
    )
    assert "SQL" not in response.text and "parameters" not in response.text
