from __future__ import annotations

import os
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.routes import codexify_router


def _headers(token: str | None = None) -> dict[str, str]:
    headers = {"X-API-Key": os.getenv("GUARDIAN_API_KEY", "test")}
    if token:
        headers[codexify_router.CAPABILITY_HEADER] = token
    return headers


def test_embed_without_capability_returns_403():
    app = FastAPI()
    app.include_router(codexify_router.router)

    codexify_router.clear_capability_grants()
    client = TestClient(app)
    response = client.post(
        "/embed",
        json={"text": "hello", "namespace": "user:local"},
        headers=_headers(),
    )

    assert response.status_code == 403


def test_embed_and_search_with_valid_capability_succeeds():
    app = FastAPI()
    app.include_router(codexify_router.router)

    codexify_router.clear_capability_grants()
    embed_token = "cap-write-1"
    search_token = "cap-read-1"
    codexify_router.register_capability_grant(
        embed_token,
        action="vector:write",
        resource="ns:user:local",
        ttl_seconds=300,
        max_calls=2,
    )
    codexify_router.register_capability_grant(
        search_token,
        action="vector:read",
        resource="ns:user:local",
        ttl_seconds=300,
        max_calls=2,
    )

    client = TestClient(app)
    embed = client.post(
        "/embed",
        json={"text": "needle vector", "namespace": "user:local"},
        headers=_headers(embed_token),
    )
    assert embed.status_code == 200

    search = client.post(
        "/search",
        json={"query": "needle", "namespace": "user:local"},
        headers=_headers(search_token),
    )
    assert search.status_code == 200


def test_expired_capability_returns_403():
    app = FastAPI()
    app.include_router(codexify_router.router)

    codexify_router.clear_capability_grants()
    token = "expired-cap"
    codexify_router.register_capability_grant(
        token,
        action="vector:read",
        resource="ns:user:local",
        ttl_seconds=5,
        max_calls=1,
    )
    codexify_router.CAPABILITY_GRANTS[token]["expires_at"] = time.time() - 1

    client = TestClient(app)
    response = client.post(
        "/search",
        json={"query": "hello", "namespace": "user:local"},
        headers=_headers(token),
    )

    assert response.status_code == 403
