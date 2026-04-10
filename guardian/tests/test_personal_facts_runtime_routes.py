"""Runtime checks for the mounted personal-facts routes."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url

import guardian.guardian_api as guardian_api
import guardian.routes.personal_facts as personal_facts
from guardian.core import dependencies
from guardian.core.chatlog_postgres import PostgresChatLogDB


def _resolve_api_key() -> str:
    api_key = (
        getattr(dependencies, "API_KEY", "")
        or os.getenv("GUARDIAN_API_KEY")
        or ""
    ).strip()
    if not api_key:
        pytest.skip(
            "GUARDIAN_API_KEY is not configured for runtime route tests"
        )
    return api_key


def _resolve_runtime_db_url() -> str:
    for env_name in (
        "TEST_DATABASE_URL",
        "GUARDIAN_DATABASE_URL",
        "DATABASE_URL",
    ):
        db_url = (os.getenv(env_name) or "").strip()
        if db_url:
            return db_url

    runtime_db = getattr(guardian_api, "chatlog_db", None) or getattr(
        dependencies, "chatlog_db", None
    )
    db_url = (
        getattr(runtime_db, "dsn", None)
        or getattr(runtime_db, "db_url", None)
        or ""
    ).strip()
    if not db_url:
        pytest.skip("No Postgres runtime DSN is available for route tests")

    try:
        parsed = make_url(db_url)
        if parsed.host == "db":
            parsed = parsed.set(host="127.0.0.1", port=5433)
        return parsed.render_as_string(hide_password=False)
    except Exception:
        return db_url


@pytest.fixture
def runtime_personal_facts_client(monkeypatch):
    api_key = _resolve_api_key()
    db_url = _resolve_runtime_db_url()
    runtime_db = PostgresChatLogDB(db_url)
    user_id = f"runtime-personal-facts-{uuid4().hex}"

    monkeypatch.setenv("GUARDIAN_API_KEY", api_key)
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "local")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("CODEXIFY_SINGLE_USER_ID", user_id)
    monkeypatch.setattr(dependencies, "chatlog_db", runtime_db, raising=False)
    monkeypatch.setattr(dependencies, "init_database", lambda: runtime_db)
    monkeypatch.setattr(guardian_api, "chatlog_db", runtime_db, raising=False)
    monkeypatch.setattr(personal_facts, "chatlog_db", runtime_db, raising=False)

    client = TestClient(
        guardian_api.app,
        raise_server_exceptions=False,
    )
    headers = {"X-API-Key": api_key}
    try:
        yield client, headers, user_id
    finally:
        client.close()


def _create_runtime_fact(
    client: TestClient, headers: dict[str, str]
) -> dict[str, object]:
    suffix = uuid4().hex
    payload = {
        "key": f"runtime-fact-{suffix}",
        "value": f"runtime-value-{suffix}",
        "status": "candidate",
        "confidence": 0.5,
    }
    response = client.post("/personal-facts", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["ok"] is True
    assert isinstance(data["id"], int)
    return {"id": data["id"], "payload": payload}


def test_runtime_personal_facts_list_create_and_get(
    runtime_personal_facts_client,
):
    client, headers, user_id = runtime_personal_facts_client
    created = _create_runtime_fact(client, headers)
    fact_id = int(created["id"])
    payload = created["payload"]

    list_response = client.get("/personal-facts", headers=headers)
    assert list_response.status_code == 200, list_response.text
    list_data = list_response.json()
    assert list_data["ok"] is True
    assert any(fact["id"] == fact_id for fact in list_data["facts"])

    detail_response = client.get(f"/personal-facts/{fact_id}", headers=headers)
    assert detail_response.status_code == 200, detail_response.text
    detail_data = detail_response.json()
    assert detail_data["ok"] is True
    assert detail_data["fact"]["id"] == fact_id
    assert detail_data["fact"]["user_id"] == user_id
    assert detail_data["fact"]["key"] == payload["key"]
    assert detail_data["fact"]["value"] == payload["value"]


def test_runtime_personal_fact_confirm_dispute_evidence_and_revisions(
    runtime_personal_facts_client,
):
    client, headers, _user_id = runtime_personal_facts_client
    created = _create_runtime_fact(client, headers)
    fact_id = int(created["id"])

    confirm_response = client.post(
        f"/personal-facts/{fact_id}/confirm",
        headers=headers,
        json={"reason": "runtime seam verification"},
    )
    assert confirm_response.status_code == 200, confirm_response.text
    confirm_data = confirm_response.json()
    assert confirm_data["ok"] is True
    assert confirm_data["fact"]["status"] == "verified"

    dispute_response = client.post(
        f"/personal-facts/{fact_id}/dispute",
        headers=headers,
        json={"reason": "runtime seam verification"},
    )
    assert dispute_response.status_code == 200, dispute_response.text
    dispute_data = dispute_response.json()
    assert dispute_data["ok"] is True
    assert dispute_data["fact"]["status"] == "disputed"

    evidence_response = client.post(
        f"/personal-facts/{fact_id}/evidence",
        headers=headers,
        json={
            "excerpt": "runtime evidence",
            "source_type": "user_stated",
        },
    )
    assert evidence_response.status_code == 200, evidence_response.text
    evidence_data = evidence_response.json()
    assert evidence_data["ok"] is True
    assert isinstance(evidence_data["id"], int)

    list_evidence_response = client.get(
        f"/personal-facts/{fact_id}/evidence",
        headers=headers,
    )
    assert (
        list_evidence_response.status_code == 200
    ), list_evidence_response.text
    list_evidence_data = list_evidence_response.json()
    assert list_evidence_data["ok"] is True
    assert any(
        evidence["id"] == evidence_data["id"]
        for evidence in list_evidence_data["evidence"]
    )

    revisions_response = client.get(
        f"/personal-facts/{fact_id}/revisions",
        headers=headers,
    )
    assert revisions_response.status_code == 200, revisions_response.text
    revisions_data = revisions_response.json()
    assert revisions_data["ok"] is True
    assert len(revisions_data["revisions"]) >= 2
