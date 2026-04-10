from __future__ import annotations

import importlib

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.services import builtin_help_ingest as help_ingest


class _State:
    def __init__(self) -> None:
        self.uploaded_documents = {}
        self.project_links = {}


class _Query:
    def __init__(self, state: _State, model) -> None:
        self._state = state
        self._model = model
        self._filters: dict[str, object] = {}
        self._limit: int | None = None

    def filter(self, *args, **kwargs):
        _ = args, kwargs
        return self

    def filter_by(self, **kwargs):
        self._filters.update(kwargs)
        return self

    def order_by(self, *args, **kwargs):
        _ = args, kwargs
        return self

    def limit(self, value):
        try:
            self._limit = int(value)
        except (TypeError, ValueError):
            self._limit = None
        return self

    def all(self):
        if self._model.__name__ != "UploadedDocument":
            return []
        rows = [
            doc
            for doc in self._state.uploaded_documents.values()
            if getattr(doc, "deleted_at", None) is None
        ]
        if "project_id" in self._filters:
            rows = [
                doc
                for doc in rows
                if getattr(doc, "project_id", None)
                == self._filters["project_id"]
            ]
        if "thread_id" in self._filters:
            rows = [
                doc
                for doc in rows
                if getattr(doc, "thread_id", None) == self._filters["thread_id"]
            ]
        if "source_tag" in self._filters:
            rows = [
                doc
                for doc in rows
                if getattr(doc, "source_tag", None)
                == self._filters["source_tag"]
            ]
        if self._limit is not None:
            rows = rows[: self._limit]
        return rows

    def first(self):
        if self._model.__name__ == "UploadedDocument":
            doc_id = str(self._filters.get("id") or "")
            return self._state.uploaded_documents.get(doc_id)
        if self._model.__name__ == "ProjectDocumentLink":
            key = (
                int(self._filters.get("project_id") or 0),
                str(self._filters.get("document_id") or ""),
                str(self._filters.get("document_type") or ""),
            )
            return self._state.project_links.get(key)
        raise AssertionError(f"Unexpected query model: {self._model!r}")


class _Session:
    def __init__(self, state: _State) -> None:
        self._state = state
        self.commits = 0

    def query(self, model):
        return _Query(self._state, model)

    def add(self, obj):
        if obj.__class__.__name__ == "UploadedDocument":
            self._state.uploaded_documents[obj.id] = obj
            return
        if obj.__class__.__name__ == "ProjectDocumentLink":
            key = (obj.project_id, obj.document_id, obj.document_type)
            self._state.project_links[key] = obj
            return
        raise AssertionError(f"Unexpected add object: {type(obj)!r}")

    def commit(self):
        self.commits += 1


class _SessionContext:
    def __init__(self, session: _Session) -> None:
        self._session = session

    def __enter__(self):
        return self._session

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeGuardianDB:
    def __init__(self, project_id: int = 9) -> None:
        self.project_id = project_id
        self.state = _State()

    def ensure_default_project(self) -> int:
        return self.project_id

    def get_session(self):
        return _SessionContext(_Session(self.state))


class _FakeChatlogDB:
    def list_connector_configs(self):
        return []

    def ensure_event_outbox(self):
        return None

    def ensure_sync_job_support(self):
        return None

    def sync_inference_provider_rows_from_catalog(self):
        return {}


def test_startup_seeds_builtin_help_and_retrieval_can_find_it(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    monkeypatch.setenv("CODEXIFY_BETA_CORE_ONLY", "0")
    monkeypatch.setenv("ENABLE_CONNECTOR_WORKER", "0")
    monkeypatch.setenv("ENABLE_OUTBOX", "0")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-local-core-web-mcp")
    monkeypatch.setenv("CODEXIFY_EMBEDDINGS_BACKEND", "mock")
    monkeypatch.setenv("CODEXIFY_VECTOR_STORE", "chroma")
    monkeypatch.setenv("CODEXIFY_CHROMA_PATH", str(tmp_path / "chroma"))
    monkeypatch.setenv("CODEXIFY_COLLECTION", "builtin_help_startup_test")
    monkeypatch.delenv("GUARDIAN_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    fake_guardian_db = _FakeGuardianDB(project_id=9)
    fake_chatlog_db = _FakeChatlogDB()

    real_ingest = help_ingest.ingest_builtin_help_document
    ingest_calls = {"count": 0}

    def _wrapped_ingest(*args, **kwargs):
        ingest_calls["count"] += 1
        return real_ingest(*args, **kwargs)

    monkeypatch.setattr(
        help_ingest,
        "ingest_builtin_help_document",
        _wrapped_ingest,
    )

    import guardian.guardian_api as guardian_api

    guardian_api = importlib.reload(guardian_api)
    monkeypatch.setattr(
        guardian_api,
        "assert_config_coherence",
        lambda _settings: None,
    )
    monkeypatch.setattr(
        guardian_api.dependencies,
        "init_database",
        lambda: fake_chatlog_db,
    )
    monkeypatch.setattr(
        guardian_api,
        "load_guardian_db_from_env",
        lambda: fake_guardian_db,
    )
    monkeypatch.setattr(guardian_api, "ensure_default_project", lambda: True)
    monkeypatch.setattr(
        guardian_api,
        "_schedule_chatgpt_import_startup_sweep",
        lambda _app: None,
    )
    monkeypatch.setattr(guardian_api, "ENABLE_OUTBOX", False)
    monkeypatch.setattr(guardian_api, "ENABLE_CONNECTOR_WORKER", False)
    import guardian.routes.media as media_routes

    monkeypatch.setattr(
        media_routes,
        "load_guardian_db_from_env",
        lambda: fake_guardian_db,
    )

    with TestClient(guardian_api.app) as client:
        response = client.get(
            "/api/media/documents",
            headers={"X-API-Key": "test-api-key"},
            params={"tag": "builtin_help"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] == 1
        document = payload["documents"][0]
        assert document["id"] == help_ingest.BUILTIN_HELP_DOCUMENT_ID
        assert document["source_tag"] == help_ingest.BUILTIN_HELP_SOURCE_TAG
        assert document["project_id"] == 9
        assert document["src_url"].endswith(
            help_ingest.BUILTIN_HELP_REL_PATH.as_posix()
        )
        assert ingest_calls["count"] == 1

    import guardian.retrieve.api as retrieve_api

    retrieve_api = importlib.reload(retrieve_api)
    monkeypatch.setattr(
        "guardian.core.config.assert_config_coherence",
        lambda _settings: None,
    )

    retrieve_app = FastAPI()
    retrieve_app.include_router(retrieve_api.router)

    with TestClient(retrieve_app) as client:
        response = client.post(
            "/api/retrieve",
            json={
                "q": "codexify-builtin-help-sentinel amber lantern 4k2",
                "k": 1,
            },
        )
        assert response.status_code == 200
        matches = response.json()["matches"]
        assert matches
        assert (
            "codexify-builtin-help-sentinel amber lantern 4k2"
            in matches[0]["text"]
        )
        assert matches[0]["meta"]["source_tag"] == "builtin_help"
