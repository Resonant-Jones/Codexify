"""Route tests for personal facts endpoints."""

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

SERVER_USER_ID = "local_user"


@pytest.fixture
def mock_facts_db(mock_db):
    mock_db.list_facts.return_value = [
        {
            "id": 1,
            "user_id": SERVER_USER_ID,
            "key": "location",
            "value": "NYC",
            "status": "candidate",
            "confidence": 0.5,
            "is_active": True,
        }
    ]
    mock_db.create_fact.return_value = 1
    mock_db.get_fact.return_value = {
        "id": 1,
        "user_id": SERVER_USER_ID,
        "key": "location",
        "value": "NYC",
        "status": "candidate",
        "confidence": 0.5,
        "is_active": True,
    }
    mock_db.update_fact.return_value = {
        "id": 1,
        "user_id": SERVER_USER_ID,
        "key": "location",
        "value": "NYC",
        "status": "verified",
        "confidence": 0.9,
        "is_active": True,
    }
    mock_db.list_fact_evidence.return_value = []
    mock_db.add_fact_evidence.return_value = 10
    mock_db.get_fact_revisions.return_value = []
    mock_db.count_facts.return_value = 1
    mock_db.list_fact_evidence_for_facts.return_value = {}
    return mock_db


@pytest.fixture
def auth_headers():
    return {"X-API-Key": "test-api-key", "X-User-Id": "spoofed_user"}


@pytest.fixture
def facts_test_client(mock_facts_db, mock_auth, monkeypatch, tmp_path):
    monkeypatch.setenv("STORAGE_BASE_PATH", str(tmp_path / "media"))
    monkeypatch.setenv("CODEXIFY_SINGLE_USER_ID", SERVER_USER_ID)
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("LOCAL_DEV", "false")

    with patch("guardian.vector.store.VectorStore"):
        with patch("logging.info"):
            from guardian.routes import personal_facts

            app = FastAPI()
            app.dependency_overrides[
                personal_facts.require_api_key
            ] = lambda: mock_auth
            app.dependency_overrides[
                personal_facts.get_current_user
            ] = lambda: SERVER_USER_ID
            monkeypatch.setattr(
                personal_facts, "chatlog_db", mock_facts_db
            )
            app.include_router(personal_facts.router)

            client = TestClient(app)
            yield client


def test_list_personal_facts(facts_test_client, auth_headers, mock_facts_db):
    response = facts_test_client.get("/personal-facts", headers=auth_headers)
    assert response.status_code == 200
    mock_facts_db.list_facts.assert_called_once()
    call_args = mock_facts_db.list_facts.call_args
    assert call_args.args[0] == SERVER_USER_ID
    assert call_args.kwargs["active_only"] is True


def test_create_personal_fact(facts_test_client, auth_headers, mock_facts_db):
    response = facts_test_client.post(
        "/personal-facts",
        headers=auth_headers,
        json={"key": "location", "value": "NYC"},
    )
    assert response.status_code == 200
    mock_facts_db.create_fact.assert_called_once()
    call_args = mock_facts_db.create_fact.call_args.args
    assert call_args[0] == SERVER_USER_ID


def test_get_personal_fact(facts_test_client, auth_headers, mock_facts_db):
    response = facts_test_client.get(
        "/personal-facts/1",
        headers=auth_headers,
    )
    assert response.status_code == 200
    mock_facts_db.list_fact_evidence.assert_called_once_with(1)


def test_update_personal_fact(facts_test_client, auth_headers, mock_facts_db):
    response = facts_test_client.patch(
        "/personal-facts/1",
        headers=auth_headers,
        json={"value": "Brooklyn", "reason": "clarified"},
    )
    assert response.status_code == 200
    mock_facts_db.update_fact.assert_called_once()


def test_confirm_personal_fact(facts_test_client, auth_headers, mock_facts_db):
    response = facts_test_client.post(
        "/personal-facts/1/confirm",
        headers=auth_headers,
        json={},
    )
    assert response.status_code == 200
    _, call_kwargs = mock_facts_db.update_fact.call_args
    assert call_kwargs["status"] == "verified"


def test_dispute_personal_fact(facts_test_client, auth_headers, mock_facts_db):
    response = facts_test_client.post(
        "/personal-facts/1/dispute",
        headers=auth_headers,
        json={},
    )
    assert response.status_code == 200
    _, call_kwargs = mock_facts_db.update_fact.call_args
    assert call_kwargs["status"] == "disputed"


def test_add_fact_evidence(facts_test_client, auth_headers, mock_facts_db):
    response = facts_test_client.post(
        "/personal-facts/1/evidence",
        headers=auth_headers,
        json={"excerpt": "I live in NYC", "source_type": "user_stated"},
    )
    assert response.status_code == 200
    mock_facts_db.add_fact_evidence.assert_called_once()


def test_list_fact_revisions(facts_test_client, auth_headers, mock_facts_db):
    response = facts_test_client.get(
        "/personal-facts/1/revisions",
        headers=auth_headers,
    )
    assert response.status_code == 200
    mock_facts_db.get_fact_revisions.assert_called_once_with(1)


# ── Candidate listing ───────────────────────────────────────────────────────
#
# The literal "/candidates" route must be dispatched ahead of "/{fact_id}".
# Starlette matches routes in registration order, so a "/candidates"
# declaration placed after "/{fact_id}" is captured by the parameterised
# route and rejected as a non-integer path parameter.


def test_list_fact_candidates_is_dispatched(facts_test_client, auth_headers):
    response = facts_test_client.get(
        "/personal-facts/candidates", headers=auth_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["limit"] == 50
    assert body["offset"] == 0
    assert body["total"] == 1
    assert len(body["facts"]) == 1


def test_list_fact_candidates_passes_paging_to_the_database(
    facts_test_client, auth_headers, mock_facts_db
):
    response = facts_test_client.get(
        "/personal-facts/candidates?offset=200&limit=25", headers=auth_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["offset"] == 200
    assert body["limit"] == 25
    _, call_kwargs = mock_facts_db.list_facts.call_args
    assert call_kwargs["offset"] == 200
    assert call_kwargs["limit"] == 25
    assert call_kwargs["active_only"] is True


def test_list_fact_candidates_total_comes_from_a_count(
    facts_test_client, auth_headers, mock_facts_db
):
    mock_facts_db.count_facts.return_value = 253
    response = facts_test_client.get(
        "/personal-facts/candidates?limit=10", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["total"] == 253
    assert mock_facts_db.count_facts.called


def test_list_fact_candidates_rejects_a_negative_offset(
    facts_test_client, auth_headers
):
    response = facts_test_client.get(
        "/personal-facts/candidates?offset=-1", headers=auth_headers
    )
    assert response.status_code == 422
    assert "offset" in response.text


def test_list_fact_candidates_caps_the_page_size(
    facts_test_client, auth_headers
):
    response = facts_test_client.get(
        "/personal-facts/candidates?limit=5000", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["limit"] == 200


def test_list_fact_candidates_passes_the_thread_filter(
    facts_test_client, auth_headers, mock_facts_db
):
    response = facts_test_client.get(
        "/personal-facts/candidates?thread_id=42", headers=auth_headers
    )
    assert response.status_code == 200
    _, call_kwargs = mock_facts_db.list_facts.call_args
    assert call_kwargs["thread_id"] == 42
    _, count_kwargs = mock_facts_db.count_facts.call_args
    assert count_kwargs["thread_id"] == 42
