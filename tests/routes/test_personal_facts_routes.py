"""Route tests for personal facts endpoints."""

from unittest.mock import patch

import pytest
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
            with patch("guardian.guardian_api.chatlog_db", mock_facts_db):
                with patch(
                    "guardian.core.dependencies.chatlog_db", mock_facts_db
                ):
                    with patch(
                        "guardian.routes.personal_facts.chatlog_db",
                        mock_facts_db,
                    ):
                        with patch(
                            "guardian.guardian_api.event_bus"
                        ) as mock_event_bus:
                            mock_event_bus.emit_event.return_value = None

                            from guardian.guardian_api import (
                                app,
                                require_api_key,
                            )

                            def mock_require_api_key_override():
                                return mock_auth

                            app.dependency_overrides[
                                require_api_key
                            ] = mock_require_api_key_override

                            client = TestClient(app)
                            yield client

                            app.dependency_overrides.clear()


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
