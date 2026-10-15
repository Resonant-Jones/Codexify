from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.core.dependencies import RequestUserScope, get_request_user_scope
from guardian.db.models import TTSVoiceProfile
from guardian.routes import tts


class _RouteTestDB:
    def __init__(self):
        engine = create_engine(
            "sqlite:///:memory:",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        TTSVoiceProfile.__table__.create(engine)
        self.Session = sessionmaker(bind=engine, future=True)

    @contextmanager
    def get_session(self):
        with self.Session() as session:
            yield session


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(tts.router)
    app.dependency_overrides[get_request_user_scope] = lambda: RequestUserScope(
        user_id="local"
    )
    tts.configure_db(_RouteTestDB())
    return TestClient(app)


def test_tts_profile_routes_create_roundtrip_update_default_delete(client):
    created = client.post(
        "/api/tts/profiles",
        json={
            "name": "Narrator",
            "backend_id": "qwen3_tts",
            "is_default": True,
            "backend_params": {"non_streaming_mode": True},
        },
    )
    assert created.status_code == 201
    profile = created.json()
    assert profile["is_default"] is True
    assert profile["backend_params"] == {"non_streaming_mode": True}

    listed = client.get("/api/tts/profiles")
    assert listed.status_code == 200
    assert listed.json()["default_profile_id"] == profile["id"]

    patched = client.patch(
        f"/api/tts/profiles/{profile['id']}",
        json={"style_instructions": "Quiet confidence.", "speed": 1.2},
    )
    assert patched.status_code == 200
    assert patched.json()["style_instructions"] == "Quiet confidence."
    assert patched.json()["speed"] == 1.2

    second = client.post(
        "/api/tts/profiles",
        json={"name": "Backup", "backend_id": "qwen3_tts"},
    ).json()
    defaulted = client.post(f"/api/tts/profiles/{second['id']}/set-default")
    assert defaulted.status_code == 200
    assert defaulted.json()["is_default"] is True

    first_after = client.get(f"/api/tts/profiles/{profile['id']}")
    assert first_after.json()["is_default"] is False

    deleted = client.delete(f"/api/tts/profiles/{profile['id']}")
    assert deleted.status_code == 200
    assert deleted.json() == {"ok": True}


def test_tts_backends_route_exposes_qwen_controls(client, monkeypatch):
    monkeypatch.setattr(
        tts.Qwen3TTSBackend,
        "health",
        lambda self: SimpleNamespace(
            to_dict=lambda: {
                "backend_id": "qwen3_tts",
                "status": "backend_unavailable",
                "healthy": False,
            }
        ),
    )

    response = client.get("/api/tts/backends")

    assert response.status_code == 200
    qwen = response.json()["items"][0]
    controls = {control["id"]: control for control in qwen["controls"]}
    assert controls["temperature"]["backend_native"] is True
    assert controls["speed"]["delivery_control"] is True
    assert controls["speed"]["backend_native"] is False


def test_tts_profile_preview_uses_existing_renderer_without_runtime_side_effects(
    client, monkeypatch, tmp_path
):
    profile = client.post(
        "/api/tts/profiles",
        json={
            "name": "Preview",
            "backend_id": "qwen3_tts",
            "speaker": "Ryan",
            "voice_prompt": "Close mic.",
            "style_instructions": "Patient.",
        },
    ).json()
    calls: list[dict] = []

    def fake_render_voiceover(**kwargs):
        calls.append(kwargs)
        output_path = Path(kwargs["output_path"])
        return SimpleNamespace(
            render_succeeded=True,
            output_path=output_path,
            bytes_written=128,
            failure_reason=None,
            setup_hint=None,
            plan=SimpleNamespace(to_dict=lambda: {"chunks": []}),
            to_dict=lambda: {
                "render_succeeded": True,
                "output_path": str(output_path),
                "dry_run": False,
            },
        )

    monkeypatch.setattr(tts, "render_voiceover", fake_render_voiceover)
    monkeypatch.setattr(
        tts,
        "get_local_tts_config",
        lambda: SimpleNamespace(
            backend_id="qwen3_tts",
            local_only=True,
            output_dir=tmp_path,
            default_voice="default",
            qwen3_model_path=None,
            qwen3_python="python",
            qwen3_render_script=None,
            chunk_max_chars=900,
            short_pause_ms=350,
            long_pause_ms=900,
        ),
    )

    response = client.post(
        f"/api/tts/profiles/{profile['id']}/preview",
        json={"text": "Preview this voice.", "format": "wav"},
    )

    assert response.status_code == 200
    assert len(calls) == 1
    assert calls[0]["profile_id"] == profile["id"]
    assert calls[0]["backend_id"] == "qwen3_tts"
    assert calls[0]["voice_id"] == "Ryan"
    assert calls[0]["voice_prompt"] == "Close mic."
    assert calls[0]["style_instructions"] == "Patient."
    assert response.json()["artifact"]["media_url"].startswith("/api/tts/previews/")
