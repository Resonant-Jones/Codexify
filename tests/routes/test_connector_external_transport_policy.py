from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.routes import connectors as connectors_module


def _connector_record(
    *,
    name: str = "github-main",
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": "cfg-1",
        "name": name,
        "type": "github",
        "settings": settings or {"owner": "octocat", "repo": "hello-world"},
    }


def _create_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": "github-main",
        "type": "github",
        "settings": {"owner": "octocat", "repo": "hello-world"},
    }
    payload.update(overrides)
    return payload


def _update_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "settings": {"owner": "octocat", "repo": "hello-world"},
    }
    payload.update(overrides)
    return payload


def _allow_rule(**overrides: Any) -> dict[str, Any]:
    rule: dict[str, Any] = {
        "effect": "allow",
        "connector_name": "github-main",
        "transport": "https",
        "reason": "allow rule",
    }
    rule.update(overrides)
    return rule


def _deny_rule(**overrides: Any) -> dict[str, Any]:
    rule: dict[str, Any] = {
        "effect": "deny",
        "connector_name": "github-main",
        "transport": "https",
        "reason": "deny rule",
    }
    rule.update(overrides)
    return rule


@contextmanager
def _client_with_db(mock_db: MagicMock) -> Iterator[TestClient]:
    with patch.object(connectors_module, "chatlog_db", mock_db):
        app = FastAPI()
        app.dependency_overrides[connectors_module.require_api_key] = (
            lambda: "test-key"
        )
        app.dependency_overrides[connectors_module.get_current_user] = (
            lambda: "subject-1"
        )
        app.include_router(connectors_module.router)
        with TestClient(app) as client:
            yield client


def _mock_db_for_create() -> MagicMock:
    mock_db = MagicMock()
    mock_db.get_connector_config.return_value = None
    mock_db.create_connector_config.return_value = _connector_record()
    return mock_db


def _mock_db_for_update() -> MagicMock:
    mock_db = MagicMock()
    mock_db.get_connector_config.return_value = _connector_record()
    mock_db.update_connector_config.return_value = _connector_record()
    mock_db.get_last_connector_run.return_value = None
    return mock_db


def test_legacy_create_without_policy_metadata_preserves_existing_behavior() -> None:
    mock_db = _mock_db_for_create()
    with _client_with_db(mock_db) as client:
        response = client.post("/api/connectors", json=_create_payload())

    assert response.status_code == 200
    assert mock_db.create_connector_config.call_count == 1


def test_legacy_update_without_policy_metadata_preserves_existing_behavior() -> None:
    mock_db = _mock_db_for_update()
    with _client_with_db(mock_db) as client:
        response = client.patch(
            "/api/connectors/github-main",
            json=_update_payload(),
        )

    assert response.status_code == 200
    assert mock_db.update_connector_config.call_count == 1


def test_create_with_matching_allow_policy_continues_and_persists() -> None:
    mock_db = _mock_db_for_create()
    with _client_with_db(mock_db) as client:
        response = client.post(
            "/api/connectors",
            json=_create_payload(
                transport="https",
                policy_rules=[_allow_rule()],
            ),
        )

    assert response.status_code == 200
    assert mock_db.create_connector_config.call_count == 1


def test_update_with_matching_allow_policy_continues_and_persists() -> None:
    mock_db = _mock_db_for_update()
    with _client_with_db(mock_db) as client:
        response = client.patch(
            "/api/connectors/github-main",
            json=_update_payload(
                transport="https",
                policy_rules=[_allow_rule()],
            ),
        )

    assert response.status_code == 200
    assert mock_db.update_connector_config.call_count == 1


def test_create_with_no_allow_rule_denies_before_persistence() -> None:
    mock_db = _mock_db_for_create()
    with _client_with_db(mock_db) as client:
        response = client.post(
            "/api/connectors",
            json=_create_payload(transport="https", policy_rules=[]),
        )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "no_allow_rule"
    assert mock_db.create_connector_config.call_count == 0


def test_update_with_no_allow_rule_denies_before_persistence() -> None:
    mock_db = _mock_db_for_update()
    with _client_with_db(mock_db) as client:
        response = client.patch(
            "/api/connectors/github-main",
            json=_update_payload(transport="https", policy_rules=[]),
        )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "no_allow_rule"
    assert mock_db.update_connector_config.call_count == 0


def test_deny_rule_overrides_allow_before_persistence() -> None:
    mock_db = _mock_db_for_create()
    with _client_with_db(mock_db) as client:
        response = client.post(
            "/api/connectors",
            json=_create_payload(
                transport="https",
                policy_rules=[
                    _allow_rule(reason="allow-first"),
                    _deny_rule(reason="explicit-deny"),
                ],
            ),
        )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "denied_by_rule"
    assert response.json()["detail"]["reason"] == "explicit-deny"
    assert mock_db.create_connector_config.call_count == 0


def test_unknown_transport_denies_before_persistence() -> None:
    mock_db = _mock_db_for_create()
    with _client_with_db(mock_db) as client:
        response = client.post(
            "/api/connectors",
            json=_create_payload(
                transport="ftp",
                policy_rules=[_allow_rule(transport="ftp")],
            ),
        )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "unsupported_transport"
    assert mock_db.create_connector_config.call_count == 0


def test_malformed_target_url_denies_before_persistence() -> None:
    mock_db = _mock_db_for_create()
    with _client_with_db(mock_db) as client:
        response = client.post(
            "/api/connectors",
            json=_create_payload(
                transport="https",
                target_url="http://[::1",
                policy_rules=[_allow_rule(url_host_pattern="api.example.com")],
            ),
        )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "malformed_url"
    assert mock_db.create_connector_config.call_count == 0


def test_connector_name_mismatch_denies_before_persistence() -> None:
    mock_db = _mock_db_for_create()
    with _client_with_db(mock_db) as client:
        response = client.post(
            "/api/connectors",
            json=_create_payload(
                transport="https",
                policy_rules=[_allow_rule(connector_name="other-connector")],
            ),
        )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "no_allow_rule"
    assert mock_db.create_connector_config.call_count == 0


def test_exact_url_host_match_allows_before_persistence() -> None:
    mock_db = _mock_db_for_create()
    with _client_with_db(mock_db) as client:
        response = client.post(
            "/api/connectors",
            json=_create_payload(
                transport="https",
                target_url="https://api.example.com/v1/repos",
                policy_rules=[
                    _allow_rule(
                        url_host_pattern="api.example.com",
                        url_scheme="https",
                    )
                ],
            ),
        )

    assert response.status_code == 200
    assert mock_db.create_connector_config.call_count == 1


def test_wildcard_url_host_match_allows_valid_subdomain() -> None:
    mock_db = _mock_db_for_create()
    with _client_with_db(mock_db) as client:
        response = client.post(
            "/api/connectors",
            json=_create_payload(
                transport="https",
                target_url="https://api.example.com/resource",
                policy_rules=[_allow_rule(url_host_pattern="*.example.com")],
            ),
        )

    assert response.status_code == 200
    assert mock_db.create_connector_config.call_count == 1


def test_wildcard_host_rejects_boundary_unsafe_domain() -> None:
    mock_db = _mock_db_for_create()
    with _client_with_db(mock_db) as client:
        response = client.post(
            "/api/connectors",
            json=_create_payload(
                transport="https",
                target_url="https://badexample.com/resource",
                policy_rules=[_allow_rule(url_host_pattern="*.example.com")],
            ),
        )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "no_allow_rule"
    assert mock_db.create_connector_config.call_count == 0


def test_command_tuple_mismatch_denies_before_persistence() -> None:
    mock_db = _mock_db_for_create()
    with _client_with_db(mock_db) as client:
        response = client.post(
            "/api/connectors",
            json=_create_payload(
                transport="https",
                command_namespace="repos",
                command_name="write",
                policy_rules=[
                    _allow_rule(
                        command_namespace="repos",
                        command_name="read",
                    )
                ],
            ),
        )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "no_allow_rule"
    assert mock_db.create_connector_config.call_count == 0


def test_project_scope_mismatch_denies_before_persistence() -> None:
    mock_db = _mock_db_for_create()
    with _client_with_db(mock_db) as client:
        response = client.post(
            "/api/connectors",
            json=_create_payload(
                transport="https",
                request_project_id="project-b",
                policy_rules=[_allow_rule(project_id="project-a")],
            ),
        )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "no_allow_rule"
    assert mock_db.create_connector_config.call_count == 0


def test_thread_scope_mismatch_denies_before_persistence() -> None:
    mock_db = _mock_db_for_create()
    with _client_with_db(mock_db) as client:
        response = client.post(
            "/api/connectors",
            json=_create_payload(
                transport="https",
                request_thread_id="thread-b",
                policy_rules=[_allow_rule(thread_id="thread-a")],
            ),
        )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "no_allow_rule"
    assert mock_db.create_connector_config.call_count == 0


def test_denial_response_includes_code_reason_and_blocked_marker() -> None:
    mock_db = _mock_db_for_create()
    with _client_with_db(mock_db) as client:
        response = client.post(
            "/api/connectors",
            json=_create_payload(
                transport="https",
                policy_rules=[
                    _deny_rule(reason="blocked-by-policy"),
                ],
            ),
        )

    assert response.status_code == 403
    detail = response.json()["detail"]
    assert detail["code"] == "denied_by_rule"
    assert detail["reason"] == "blocked-by-policy"
    assert detail["blocked_before_persistence"] is True
    assert mock_db.create_connector_config.call_count == 0


def test_denial_response_includes_evaluator_code() -> None:
    mock_db = _mock_db_for_create()
    with _client_with_db(mock_db) as client:
        response = client.post(
            "/api/connectors",
            json=_create_payload(
                transport="https",
                policy_rules=[_deny_rule(reason="deny-with-code")],
            ),
        )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "denied_by_rule"


def test_denial_response_includes_evaluator_reason() -> None:
    mock_db = _mock_db_for_create()
    with _client_with_db(mock_db) as client:
        response = client.post(
            "/api/connectors",
            json=_create_payload(
                transport="https",
                policy_rules=[_deny_rule(reason="deny-with-reason")],
            ),
        )

    assert response.status_code == 403
    assert response.json()["detail"]["reason"] == "deny-with-reason"


def test_denial_response_includes_blocked_before_persistence_true() -> None:
    mock_db = _mock_db_for_create()
    with _client_with_db(mock_db) as client:
        response = client.post(
            "/api/connectors",
            json=_create_payload(
                transport="https",
                policy_rules=[_deny_rule(reason="deny-with-marker")],
            ),
        )

    assert response.status_code == 403
    assert response.json()["detail"]["blocked_before_persistence"] is True


def test_blocked_create_path_does_not_call_create_persistence() -> None:
    mock_db = _mock_db_for_create()
    with _client_with_db(mock_db) as client:
        response = client.post(
            "/api/connectors",
            json=_create_payload(
                transport="https",
                policy_rules=[_deny_rule(reason="blocked-create")],
            ),
        )

    assert response.status_code == 403
    assert mock_db.create_connector_config.call_count == 0


def test_blocked_update_path_does_not_call_update_persistence() -> None:
    mock_db = _mock_db_for_update()
    with _client_with_db(mock_db) as client:
        response = client.patch(
            "/api/connectors/github-main",
            json=_update_payload(
                transport="https",
                policy_rules=[_deny_rule(reason="nope")],
            ),
        )

    assert response.status_code == 403
    assert mock_db.update_connector_config.call_count == 0


def test_allowed_update_path_calls_update_persistence() -> None:
    mock_db = _mock_db_for_update()
    with _client_with_db(mock_db) as client:
        response = client.patch(
            "/api/connectors/github-main",
            json=_update_payload(
                transport="https",
                policy_rules=[_allow_rule()],
            ),
        )

    assert response.status_code == 200
    assert mock_db.update_connector_config.call_count == 1
