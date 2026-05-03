from __future__ import annotations

from fastapi.testclient import TestClient

from guardian.guardian_api import app


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


def test_llm_model_override_routes_upsert_and_delete(monkeypatch):
    fake_db = _FakeModelOverrideDB()
    monkeypatch.setattr(
        "guardian.routes.llm_overrides.chatlog_db", fake_db, raising=False
    )

    client = TestClient(app)

    response = client.put(
        "/api/llm/model-overrides/local/llama3.1:8b",
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

    response = client.delete("/api/llm/model-overrides/local/llama3.1:8b")
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert fake_db.deletes == [("local", "llama3.1:8b")]
