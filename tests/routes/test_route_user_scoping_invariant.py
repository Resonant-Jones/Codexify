from __future__ import annotations

from guardian.core.dependencies import RequestUserScope
from guardian.routes import projects as projects_routes
from tests.utils import get_test_auth_headers, get_test_user_id


def test_routes_return_only_owned_entities(test_client, mock_db):
    expected_user_id = get_test_user_id()
    test_client.app.dependency_overrides[
        projects_routes.get_request_user_scope
    ] = lambda: RequestUserScope(
        user_id=expected_user_id,
        account_id=expected_user_id,
        multi_user_enabled=False,
    )
    headers = get_test_auth_headers(user_id=expected_user_id)

    response_a = test_client.post(
        "/projects", json={"name": "p1"}, headers=headers
    )
    response_b = test_client.post(
        "/projects", json={"name": "p2"}, headers=headers
    )
    assert response_a.status_code == 200
    assert response_b.status_code == 200

    resp = test_client.get("/projects", headers=headers)
    data = resp.json()

    assert len(data) >= 2
    assert all(p["user_id"] == expected_user_id for p in data)
    assert mock_db.create_project.call_count == 2
