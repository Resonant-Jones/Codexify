from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from guardian.core.config import Settings, get_settings
from guardian.guardian_api import app
from guardian.providers.minimax_adapter import MiniMaxAdapter


def _require_smoke_opt_in(settings: Settings | None = None) -> Settings:
    if not os.getenv("MINIMAX_SMOKE_TEST"):
        pytest.skip("MiniMax smoke test disabled; set MINIMAX_SMOKE_TEST=1")

    resolved = settings or get_settings()
    missing = []
    if not (resolved.MINIMAX_API_KEY or "").strip():
        missing.append("MINIMAX_API_KEY")
    if not (resolved.MINIMAX_API_BASE or "").strip():
        missing.append("MINIMAX_API_BASE")
    if not bool(resolved.ALLOW_CLOUD_PROVIDERS):
        missing.append("ALLOW_CLOUD_PROVIDERS=true")
    allowlist = str(resolved.CODEXIFY_EGRESS_ALLOWLIST or "").lower()
    if "minimax" not in {
        part.strip() for part in allowlist.split(",") if part.strip()
    }:
        missing.append("CODEXIFY_EGRESS_ALLOWLIST includes minimax")
    if bool(resolved.CODEXIFY_LOCAL_ONLY_MODE):
        missing.append("CODEXIFY_LOCAL_ONLY_MODE=false")
    if missing:
        pytest.skip("MiniMax smoke test requires: " + ", ".join(missing))
    return resolved


def test_minimax_catalog_smoke():
    settings = _require_smoke_opt_in()
    client = TestClient(app)

    response = client.get("/api/llm/catalog?include=all")
    assert response.status_code == 200

    payload = response.json()
    provider = next(
        item for item in payload["providers"] if item.get("id") == "minimax"
    )

    assert provider["enabled"] is True
    assert provider["authorized"] is True
    assert provider["available"] is True
    assert provider["models"]
    assert any(model.get("supports_chat") for model in provider["models"])

    model_index = provider.get("model_index") or {}
    assert model_index.get("state") in {"available", "degraded"}
    if model_index.get("state") == "degraded":
        assert str(model_index.get("reason") or "").strip()

    assert settings.MINIMAX_API_KEY
    assert settings.MINIMAX_API_BASE


def test_minimax_chat_smoke():
    settings = _require_smoke_opt_in()
    adapter = MiniMaxAdapter(
        api_key=settings.MINIMAX_API_KEY,
        base_url=settings.MINIMAX_API_BASE,
        default_model=settings.MINIMAX_MODEL,
        timeout=float(os.getenv("MINIMAX_SMOKE_TIMEOUT_SECONDS", "30")),
        api_flavor=settings.MINIMAX_API_FLAVOR,
    )

    reply = adapter.generate(
        "Reply with the single word ok.",
        messages=[
            {"role": "system", "content": "Be concise."},
            {"role": "user", "content": "Smoke test."},
        ],
    )

    assert isinstance(reply, str)
    assert reply.strip()
