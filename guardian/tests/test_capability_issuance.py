from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.routes import admin, codexify_router


def _api_headers() -> dict[str, str]:
    return {"X-API-Key": os.getenv("GUARDIAN_API_KEY", "test")}


def test_capability_issue_requires_auth():
    app = FastAPI()
    app.include_router(admin.router)

    client = TestClient(app)
    response = client.post(
        "/api/capabilities/issue",
        json={"actions": ["vector:read"]},
    )

    assert response.status_code == 401


def test_capability_issue_and_use_for_vector_endpoints():
    app = FastAPI()
    app.include_router(admin.router)
    app.include_router(codexify_router.router)

    codexify_router.clear_capability_grants()
    client = TestClient(app)

    issue = client.post(
        "/api/capabilities/issue",
        json={
            "actions": ["vector:write", "vector:read"],
            "namespace": "user:local",
            "ttl_seconds": 120,
            "max_calls": 2,
        },
        headers=_api_headers(),
    )
    assert issue.status_code == 200
    payload = issue.json()

    grants = {item["action"]: item["token"] for item in payload["grants"]}
    write_token = grants["vector:write"]
    read_token = grants["vector:read"]

    embed = client.post(
        "/embed",
        json={"text": "needle capability", "namespace": "user:local"},
        headers={
            **_api_headers(),
            codexify_router.CAPABILITY_HEADER: write_token,
        },
    )
    assert embed.status_code == 200

    search = client.post(
        "/search",
        json={"query": "needle", "namespace": "user:local"},
        headers={
            **_api_headers(),
            codexify_router.CAPABILITY_HEADER: read_token,
        },
    )
    assert search.status_code == 200
