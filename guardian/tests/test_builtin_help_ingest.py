from __future__ import annotations

import hashlib
from pathlib import Path

from guardian.db.models import ProjectDocumentLink, UploadedDocument
from guardian.protocol_tokens import EmbeddingLifecycleStatus
from guardian.services import builtin_help_ingest as help_ingest


class _State:
    def __init__(self) -> None:
        self.uploaded_documents: dict[str, UploadedDocument] = {}
        self.project_links: dict[tuple[int, str, str], ProjectDocumentLink] = {}


class _Query:
    def __init__(self, state: _State, model) -> None:
        self._state = state
        self._model = model
        self._filters: dict[str, object] = {}

    def filter_by(self, **kwargs):
        self._filters.update(kwargs)
        return self

    def first(self):
        if self._model is UploadedDocument:
            doc_id = str(self._filters.get("id") or "")
            return self._state.uploaded_documents.get(doc_id)
        if self._model is ProjectDocumentLink:
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
        self.added: list[object] = []

    def query(self, model):
        return _Query(self._state, model)

    def add(self, obj):
        self.added.append(obj)
        if isinstance(obj, UploadedDocument):
            self._state.uploaded_documents[obj.id] = obj
            return
        if isinstance(obj, ProjectDocumentLink):
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
    def __init__(self, project_id: int = 7) -> None:
        self.project_id = project_id
        self.state = _State()
        self.ensure_default_project_calls = 0
        self.sessions: list[_Session] = []

    def ensure_default_project(self) -> int:
        self.ensure_default_project_calls += 1
        return self.project_id

    def get_session(self):
        session = _Session(self.state)
        self.sessions.append(session)
        return _SessionContext(session)


class _RecordingVectorStore:
    def __init__(self) -> None:
        self.calls: list[list[dict[str, object]]] = []

    def add_texts(self, items):
        snapshot = [
            {
                "id": item.get("id"),
                "text": item.get("text"),
                "meta": dict(item.get("meta") or {}),
            }
            for item in items
        ]
        self.calls.append(snapshot)
        return len(items)


def _source_path() -> Path:
    return (
        Path(__file__).resolve().parents[2] / help_ingest.BUILTIN_HELP_REL_PATH
    )


def _read_source_text() -> str:
    return _source_path().read_text(encoding="utf-8")


def _expected_hash() -> str:
    return hashlib.sha256(_read_source_text().encode("utf-8")).hexdigest()


def test_builtin_help_ingest_creates_document_in_default_scope():
    db = _FakeGuardianDB(project_id=17)
    vector_store = _RecordingVectorStore()

    result = help_ingest.ingest_builtin_help_document(
        db,
        vector_store=vector_store,
        repo_root=Path(__file__).resolve().parents[2],
    )

    assert result["status"] == "created"
    assert result["vector_written"] is True
    assert result["project_id"] == 17
    assert db.ensure_default_project_calls == 1

    docs = db.state.uploaded_documents
    assert len(docs) == 1
    document = next(iter(docs.values()))
    assert document.id == help_ingest.BUILTIN_HELP_DOCUMENT_ID
    assert document.project_id == 17
    assert document.source_tag == help_ingest.BUILTIN_HELP_SOURCE_TAG
    assert document.src_url == help_ingest.BUILTIN_HELP_REL_PATH.as_posix()
    assert document.parsed_text == _read_source_text()
    assert document.embedding_status == EmbeddingLifecycleStatus.READY.value
    assert document.embedding_error is None
    assert document.embedding_completed_at is not None

    links = db.state.project_links
    assert len(links) == 1
    link = next(iter(links.values()))
    assert link.project_id == 17
    assert link.document_id == help_ingest.BUILTIN_HELP_DOCUMENT_ID
    assert link.document_type == "uploaded"
    assert link.is_enabled is True
    assert link.attached_by == help_ingest.BUILTIN_HELP_SOURCE_TAG


def test_builtin_help_ingest_is_idempotent_on_second_run():
    db = _FakeGuardianDB(project_id=17)
    vector_store = _RecordingVectorStore()

    first = help_ingest.ingest_builtin_help_document(
        db,
        vector_store=vector_store,
        repo_root=Path(__file__).resolve().parents[2],
    )
    second = help_ingest.ingest_builtin_help_document(
        db,
        vector_store=vector_store,
        repo_root=Path(__file__).resolve().parents[2],
    )

    assert first["status"] == "created"
    assert second["status"] == "already_present"
    assert second["vector_written"] is False
    assert len(db.state.uploaded_documents) == 1
    assert len(db.state.project_links) == 1
    assert len(vector_store.calls) == 1


def test_builtin_help_ingest_indexes_through_existing_vector_store_abstraction():
    db = _FakeGuardianDB(project_id=23)
    vector_store = _RecordingVectorStore()

    result = help_ingest.ingest_builtin_help_document(
        db,
        vector_store=vector_store,
        repo_root=Path(__file__).resolve().parents[2],
    )

    assert result["vector_written"] is True
    assert len(vector_store.calls) == 1
    call = vector_store.calls[0]
    assert len(call) == 1
    item = call[0]
    assert item["id"] == help_ingest.BUILTIN_HELP_DOCUMENT_ID
    assert item["text"] == _read_source_text()
    assert item["meta"]["source_tag"] == help_ingest.BUILTIN_HELP_SOURCE_TAG
    assert (
        item["meta"]["source_path"]
        == help_ingest.BUILTIN_HELP_REL_PATH.as_posix()
    )
    assert item["meta"]["content_hash"] == _expected_hash()
    assert item["meta"]["project_id"] == 23


def test_builtin_help_ingest_uses_stable_machine_checkable_metadata():
    db = _FakeGuardianDB(project_id=31)
    vector_store = _RecordingVectorStore()

    help_ingest.ingest_builtin_help_document(
        db,
        vector_store=vector_store,
        repo_root=Path(__file__).resolve().parents[2],
    )

    metadata = vector_store.calls[0][0]["meta"]
    assert metadata == {
        "content_hash": _expected_hash(),
        "document_id": help_ingest.BUILTIN_HELP_DOCUMENT_ID,
        "filename": help_ingest.BUILTIN_HELP_FILENAME,
        "namespace": "project:31",
        "project_id": 31,
        "project_name": "General",
        "scope": "General",
        "source_path": help_ingest.BUILTIN_HELP_REL_PATH.as_posix(),
        "source_tag": help_ingest.BUILTIN_HELP_SOURCE_TAG,
        "title": help_ingest.BUILTIN_HELP_TITLE,
    }
