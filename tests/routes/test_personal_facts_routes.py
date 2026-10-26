"""Route tests for personal facts endpoints."""

import logging
import traceback
from unittest.mock import patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

SERVER_USER_ID = "local_user"

#: Synthetic sensitive content used to prove that a backend failure never
#: reaches the HTTP response, the application logs, or the raised error's
#: traceback. Every value here is fabricated.
SENSITIVE_MARKERS = (
    "postgresql://dbuser@db.internal:5432/guardian",  # connection detail
    "hunter2",  # password
    "tok_abcdef123456",  # token
    "SENSITIVE-CANDIDATE-CONTENT",  # private record content
)
SENSITIVE_EXCEPTION_MESSAGE = (
    "psycopg.OperationalError: could not connect to "
    "postgresql://dbuser@db.internal:5432/guardian "
    "password=hunter2 token=tok_abcdef123456 "
    "row=SENSITIVE-CANDIDATE-CONTENT"
)


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
    # Thread-filtered reads attach the matching source evidence. The candidate
    # endpoint is fail-closed, so the loader must return usable evidence for
    # every fact it selects.
    mock_db.list_fact_evidence_for_facts.return_value = {
        1: [
            {
                "id": 10,
                "fact_id": 1,
                "source_type": "user_stated",
                "evidence_meta": {"thread_id": 42, "source": "chat"},
            }
        ]
    }
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


# ── Fail-closed evidence reads ──────────────────────────────────────────────
#
# The Guardrails Contract requires that evidence is never silently dropped.
# A thread-filtered candidate page promises its source evidence, so a storage
# failure or an unusable loader must fail the request rather than return an
# incomplete page as a success.


def test_thread_filtered_read_attaches_matching_evidence(
    facts_test_client, auth_headers
):
    response = facts_test_client.get(
        "/personal-facts/candidates?thread_id=42", headers=auth_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["total"] == 1
    evidence = body["facts"][0]["_evidence"]
    assert evidence["evidence_meta"]["thread_id"] == 42


def test_thread_filtered_read_fails_closed_when_the_loader_raises(
    facts_test_client, auth_headers, mock_facts_db
):
    mock_facts_db.list_fact_evidence_for_facts.side_effect = RuntimeError(
        "evidence store unavailable: host=db.internal token=secret-value"
    )
    response = facts_test_client.get(
        "/personal-facts/candidates?thread_id=42", headers=auth_headers
    )
    assert response.status_code == 500
    assert response.json() != {"ok": True}


def test_thread_filtered_read_fails_closed_when_the_loader_is_absent(
    facts_test_client, auth_headers, mock_facts_db
):
    mock_facts_db.list_fact_evidence_for_facts = None
    response = facts_test_client.get(
        "/personal-facts/candidates?thread_id=42", headers=auth_headers
    )
    assert response.status_code == 500


def test_thread_filtered_read_fails_closed_on_a_malformed_result(
    facts_test_client, auth_headers, mock_facts_db
):
    mock_facts_db.list_fact_evidence_for_facts.return_value = ["not-a-mapping"]
    response = facts_test_client.get(
        "/personal-facts/candidates?thread_id=42", headers=auth_headers
    )
    assert response.status_code == 500


def test_thread_filtered_read_fails_closed_on_malformed_evidence_rows(
    facts_test_client, auth_headers, mock_facts_db
):
    mock_facts_db.list_fact_evidence_for_facts.return_value = {1: "not-a-list"}
    response = facts_test_client.get(
        "/personal-facts/candidates?thread_id=42", headers=auth_headers
    )
    assert response.status_code == 500


def test_thread_filtered_read_fails_closed_when_matching_evidence_is_absent(
    facts_test_client, auth_headers, mock_facts_db
):
    mock_facts_db.list_fact_evidence_for_facts.return_value = {
        1: [{"id": 10, "fact_id": 1, "evidence_meta": {"thread_id": 7}}]
    }
    response = facts_test_client.get(
        "/personal-facts/candidates?thread_id=42", headers=auth_headers
    )
    assert response.status_code == 500


def test_evidence_failure_response_leaks_no_internal_detail(
    facts_test_client, auth_headers, mock_facts_db
):
    mock_facts_db.list_fact_evidence_for_facts.side_effect = RuntimeError(
        "psycopg connection to db.internal failed for user chris: token=secret"
    )
    response = facts_test_client.get(
        "/personal-facts/candidates?thread_id=42", headers=auth_headers
    )
    assert response.status_code == 500
    body = response.text
    assert "psycopg" not in body
    assert "db.internal" not in body
    assert "secret" not in body
    assert "chris" not in body
    assert "Traceback" not in body


def test_evidence_failure_does_not_leak_fact_content(
    facts_test_client, auth_headers, mock_facts_db
):
    mock_facts_db.list_fact_evidence_for_facts.side_effect = RuntimeError(
        "failed"
    )
    response = facts_test_client.get(
        "/personal-facts/candidates?thread_id=42", headers=auth_headers
    )
    assert response.status_code == 500
    assert "NYC" not in response.text
    assert "location" not in response.text


def test_read_without_thread_id_does_not_load_evidence(
    facts_test_client, auth_headers, mock_facts_db
):
    """Without thread_id the current read path is unchanged."""
    mock_facts_db.list_fact_evidence_for_facts.side_effect = RuntimeError(
        "must not be called"
    )
    response = facts_test_client.get(
        "/personal-facts/candidates", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert "_evidence" not in response.json()["facts"][0]
    assert not mock_facts_db.list_fact_evidence_for_facts.called


# ── Archived status visibility ──────────────────────────────────────────────
#
# Archival sets status="archived" and is_active=False, so an active-only
# listing hid the very status the route advertises. An explicitly requested
# archived read must drop the active-only predicate, and the page and the
# count must use the same effective value.


def test_archived_status_disables_the_active_only_predicate(
    facts_test_client, auth_headers, mock_facts_db
):
    response = facts_test_client.get(
        "/personal-facts/candidates?status=archived", headers=auth_headers
    )
    assert response.status_code == 200
    assert mock_facts_db.list_facts.call_args.kwargs["active_only"] is False
    assert mock_facts_db.count_facts.call_args.kwargs["active_only"] is False


def test_archived_status_keeps_page_and_count_filters_identical(
    facts_test_client, auth_headers, mock_facts_db
):
    facts_test_client.get(
        "/personal-facts/candidates?status=archived", headers=auth_headers
    )
    list_kwargs = mock_facts_db.list_facts.call_args.kwargs
    count_kwargs = mock_facts_db.count_facts.call_args.kwargs
    assert list_kwargs["active_only"] == count_kwargs["active_only"]
    assert list_kwargs["status"] == count_kwargs["status"] == "archived"


@pytest.mark.parametrize("status", ["candidate", "verified", "disputed"])
def test_other_statuses_keep_the_active_only_predicate(
    facts_test_client, auth_headers, mock_facts_db, status
):
    response = facts_test_client.get(
        f"/personal-facts/candidates?status={status}", headers=auth_headers
    )
    assert response.status_code == 200
    assert mock_facts_db.list_facts.call_args.kwargs["active_only"] is True
    assert mock_facts_db.count_facts.call_args.kwargs["active_only"] is True


def test_default_read_keeps_the_active_only_predicate(
    facts_test_client, auth_headers, mock_facts_db
):
    response = facts_test_client.get(
        "/personal-facts/candidates", headers=auth_headers
    )
    assert response.status_code == 200
    assert mock_facts_db.list_facts.call_args.kwargs["active_only"] is True
    assert mock_facts_db.count_facts.call_args.kwargs["active_only"] is True


def test_archived_thread_read_uses_the_same_effective_filter(
    facts_test_client, auth_headers, mock_facts_db
):
    response = facts_test_client.get(
        "/personal-facts/candidates?status=archived&thread_id=42",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert mock_facts_db.list_facts.call_args.kwargs["active_only"] is False
    assert mock_facts_db.count_facts.call_args.kwargs["active_only"] is False


# ── Failure diagnostics must not disclose backend exception content ──────────
#
# A storage exception can carry connection strings, credentials, tokens or
# private record detail. The endpoint must fail closed without letting any of
# that reach the HTTP response, the application logs, or the raised error's
# traceback.


def test_secret_bearing_exception_produces_a_sanitized_500(
    facts_test_client, auth_headers, mock_facts_db
):
    mock_facts_db.list_fact_evidence_for_facts.side_effect = RuntimeError(
        SENSITIVE_EXCEPTION_MESSAGE
    )
    response = facts_test_client.get(
        "/personal-facts/candidates?thread_id=42", headers=auth_headers
    )
    assert response.status_code == 500
    assert response.json()["detail"] == "Candidate evidence could not be loaded"
    for marker in SENSITIVE_MARKERS:
        assert marker not in response.text


def test_captured_logs_contain_no_sensitive_markers(
    facts_test_client, auth_headers, mock_facts_db, caplog
):
    mock_facts_db.list_fact_evidence_for_facts.side_effect = RuntimeError(
        SENSITIVE_EXCEPTION_MESSAGE
    )
    with caplog.at_level(logging.ERROR, logger="guardian.routes.personal_facts"):
        response = facts_test_client.get(
            "/personal-facts/candidates?thread_id=42", headers=auth_headers
        )
    assert response.status_code == 500

    records = [
        record
        for record in caplog.records
        if record.name == "guardian.routes.personal_facts"
    ]
    assert records, "the failure must stay observable in the logs"
    for record in records:
        # No traceback, no exception arguments, no sensitive rendered text.
        assert record.exc_info is None
        assert getattr(record, "exc_text", None) is None
        for marker in SENSITIVE_MARKERS:
            assert marker not in record.getMessage()
            assert marker not in repr(record.args)
            assert marker not in repr(record.exc_info)


def test_failure_log_message_stays_stable_and_sanitized(
    facts_test_client, auth_headers, mock_facts_db, caplog
):
    """The failure must stay observable, in the repository's safe event form.

    Codexify's log-safety boundary preserves a static snake_case event token
    and redacts free-form prose to ``log_event=<redacted>``. A free-form
    sentence would therefore be unobservable to an operator, so the failure is
    reported as a stable event token with no arguments.
    """
    mock_facts_db.list_fact_evidence_for_facts.side_effect = RuntimeError(
        SENSITIVE_EXCEPTION_MESSAGE
    )
    with caplog.at_level(logging.ERROR, logger="guardian.routes.personal_facts"):
        facts_test_client.get(
            "/personal-facts/candidates?thread_id=42", headers=auth_headers
        )
    messages = [
        record.getMessage()
        for record in caplog.records
        if record.name == "guardian.routes.personal_facts"
    ]
    assert messages == ["personal_fact_candidate_evidence_load_failed"]
    for message in messages:
        assert "log_event=<redacted>" not in message


def test_raised_error_does_not_chain_the_storage_exception(
    facts_test_client, auth_headers, mock_facts_db
):
    """The handled HTTP error must not expose the original exception."""
    from guardian.routes import personal_facts

    mock_facts_db.list_fact_evidence_for_facts.side_effect = RuntimeError(
        SENSITIVE_EXCEPTION_MESSAGE
    )
    with pytest.raises(HTTPException) as excinfo:
        personal_facts.list_fact_candidates(
            status="candidate",
            thread_id=42,
            limit=50,
            offset=0,
            current_user=SERVER_USER_ID,
        )
    error = excinfo.value
    assert error.status_code == 500
    assert error.detail == "Candidate evidence could not be loaded"
    # No explicit cause, and the implicit context is suppressed so the
    # storage exception is absent from the rendered traceback.
    assert error.__cause__ is None
    assert error.__suppress_context__ is True
    rendered = "".join(
        traceback.format_exception(type(error), error, error.__traceback__)
    )
    for marker in SENSITIVE_MARKERS:
        assert marker not in rendered
    assert "RuntimeError" not in rendered
