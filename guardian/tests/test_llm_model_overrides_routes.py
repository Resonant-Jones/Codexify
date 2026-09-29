from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend import llm_overrides as legacy_llm_overrides
from guardian.core.auth import (
    ACCOUNT_SESSION_PURPOSE,
    OPERATOR_SESSION_PURPOSE,
    issue_session_token,
)
from guardian.core.supported_profile import load_supported_profile
from guardian import guardian_api
from guardian.routes import llm_overrides


PROFILE_NAMES = (
    "test-continuity",
    "v1-friends-family-web",
    "v1-local-core-web-mcp",
    "v1-user-profile-accent-proof",
    "v1-whooshd-deepseek-web",
)


class _FakeModelOverrideDB:
    def __init__(self) -> None:
        self.upserts: list[tuple[str, str, dict[str, object]]] = []
        self.deletes: list[tuple[str, str]] = []

    def list_inference_model_overrides(self):
        return []

    def get_inference_model_override(self, provider_id: str, model_id: str):
        return None

    def upsert_inference_model_override(
        self, provider_id: str, model_id: str, overrides: dict[str, object]
    ):
        self.upserts.append((provider_id, model_id, dict(overrides)))
        return {
            "provider_id": provider_id,
            "model_id": model_id,
            "display_label": overrides.get("display_label"),
            "picker_label": overrides.get("picker_label"),
            "supports_vision": overrides.get("supports_vision"),
        }

    def delete_inference_model_override(
        self, provider_id: str, model_id: str
    ) -> bool:
        self.deletes.append((provider_id, model_id))
        return True


def test_supported_profiles_quarantine_canonical_model_override_router(
    monkeypatch,
):
    assert legacy_llm_overrides.router is llm_overrides.router
    assert guardian_api.llm_overrides.router is llm_overrides.router
    path = "/api/llm/model-overrides/local/llama3.1:8b"
    for profile_name in PROFILE_NAMES:
        profile = load_supported_profile(profile_name)
        assert profile.route_status("llm_overrides") == "quarantined"
        profile_app = FastAPI()
        monkeypatch.setattr(guardian_api, "app", profile_app)
        monkeypatch.setattr(guardian_api, "_SUPPORTED_PROFILE_MANIFEST", profile)
        guardian_api._include_router(
            label="llm_overrides",
            flag_name="CODEXIFY_ENABLE_CHAT_ROUTES",
            include_fn=lambda: profile_app.include_router(llm_overrides.router),
            core_surface=True,
        )
        assert not any(
            getattr(route, "path", None) == path for route in profile_app.routes
        )
        response = TestClient(profile_app).put(
            path,
            headers={"X-API-Key": "test-api-key"},
            json={"display_label": "Office Llama"},
        )
        assert response.status_code == 404


def test_canonical_model_override_router_preserves_contract_and_operator_auth(
    monkeypatch,
):
    monkeypatch.setenv("GUARDIAN_API_KEY", "model-override-test-key")
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "model-override-test-secret")
    monkeypatch.setenv("CODEXIFY_DISABLE_DOTENV", "1")
    fake_db = _FakeModelOverrideDB()
    monkeypatch.setattr(llm_overrides, "chatlog_db", fake_db)

    route_app = FastAPI()
    route_app.include_router(llm_overrides.router)
    client = TestClient(route_app)
    path = "/api/llm/model-overrides/local/llama3.1:8b"
    assert client.put(
        path,
        headers={"X-API-Key": ""},
        json={"display_label": "Office Llama"},
    ).status_code == 401
    account_token, _ = issue_session_token(
        subject="account-a", purpose=ACCOUNT_SESSION_PURPOSE
    )
    assert client.put(
        path,
        headers={"Authorization": f"Bearer {account_token}", "X-API-Key": ""},
        json={"display_label": "Office Llama"},
    ).status_code == 401
    operator_token, _ = issue_session_token(
        subject="operator", purpose=OPERATOR_SESSION_PURPOSE
    )
    assert client.get(
        "/api/llm/model-overrides",
        headers={"Authorization": f"Bearer {operator_token}"},
    ).status_code == 200

    response = client.put(
        path,
        headers={"X-API-Key": "model-override-test-key"},
        json={
            "display_label": "Office Llama",
            "picker_label": "Office Llama (Vision)",
            "supports_vision": True,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert fake_db.upserts == [
        (
            "local",
            "llama3.1:8b",
            {
                "display_label": "Office Llama",
                "picker_label": "Office Llama (Vision)",
                "supports_vision": True,
            },
        )
    ]

    response = client.delete(
        path, headers={"X-API-Key": "model-override-test-key"}
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert fake_db.deletes == [("local", "llama3.1:8b")]
