from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, List
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.services.document_chunking import (
    DEFAULT_CHUNK_SIZE,
    chunk_document_text,
)


@dataclass
class _StoredItem:
    text: str
    meta: dict[str, Any]


class _FakeVectorStore:
    def __init__(self) -> None:
        self.items: list[_StoredItem] = []

    def add_texts(self, items: list[dict[str, Any]]) -> int:
        for item in items:
            self.items.append(
                _StoredItem(
                    text=item.get("text", ""),
                    meta=item.get("meta", {}),
                )
            )
        return len(items)

    def search(
        self,
        query: str,
        k: int = 5,
        namespace: str | None = None,
    ) -> list[dict[str, Any]]:
        _ = namespace
        lowered = query.lower()
        matches = []
        for item in self.items:
            if lowered in item.text.lower():
                matches.append(
                    {"text": item.text, "meta": item.meta, "score": 1.0}
                )
        return matches[:k]


class _FakeEmbedder:
    def __init__(self, store: _FakeVectorStore) -> None:
        self.store = store
        self.calls: list[dict[str, Any]] = []

    def embed_and_index(
        self,
        docs: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        ids_prefix: str = "doc",
    ) -> dict[str, Any]:
        normalized_metas = metadatas or [{} for _ in docs]
        items = [
            {"text": doc, "meta": meta}
            for doc, meta in zip(docs, normalized_metas)
        ]
        self.store.add_texts(items)
        self.calls.append({"docs": docs, "metas": normalized_metas})
        return {"count": len(docs), "ids_prefix": ids_prefix}


def _simple_pdf_bytes(text: str) -> bytes:
    content = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET"
    header = b"%PDF-1.4\n1 0 obj\n<< /Length "
    footer = b" >>\nstream\n"
    return (
        header
        + str(len(content)).encode("ascii")
        + footer
        + content.encode("ascii")
        + b"\nendstream\nendobj\n%%EOF"
    )


def _make_mock_db() -> MagicMock:
    mock_db = MagicMock()
    mock_session = MagicMock()
    query_mock = MagicMock()
    query_mock.filter.return_value = query_mock
    query_mock.filter_by.return_value = query_mock
    query_mock.order_by.return_value = query_mock
    query_mock.limit.return_value = query_mock
    query_mock.all.return_value = []
    query_mock.first.return_value = None
    mock_session.query.return_value = query_mock
    mock_db.get_session.return_value.__enter__.return_value = mock_session
    mock_db.get_session.return_value.__exit__.return_value = False
    return mock_db


def test_document_upload_retrieval_flow():
    needle = "needle"
    padding = "lorem " * 260
    long_text = f"{padding}{needle} {padding}"
    assert len(long_text) > DEFAULT_CHUNK_SIZE

    pdf_bytes = _simple_pdf_bytes(long_text)
    fake_store = _FakeVectorStore()
    mock_db = _make_mock_db()

    with patch("guardian.vector.store.VectorStore", return_value=fake_store):
        import importlib

        import guardian.routes.codexify_router as codexify_router

        codexify_router = importlib.reload(codexify_router)

    from guardian.routes import media as media_routes

    app = FastAPI()
    app.include_router(media_routes.router, prefix="/api/media")
    app.include_router(codexify_router.router)

    with patch("guardian.routes.media.storage") as mock_storage, patch(
        "guardian.routes.media._get_db", return_value=mock_db
    ), patch("guardian.routes.media.enqueue_document_embed") as mock_enqueue:
        mock_storage.upload_file.return_value = "/media/documents/test.pdf"

        client = TestClient(app)
        response = client.post(
            "/api/media/upload/document",
            files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
            data={"project_id": 1, "thread_id": 1, "user_id": "default"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert needle in (payload.get("parsed_text") or "")
        assert mock_enqueue.call_count == 1

        expected_chunks = chunk_document_text(payload.get("parsed_text"))
        expected_texts = [chunk.text for chunk in expected_chunks]

        assert len(expected_texts) > 1
        assert [
            chunk.text
            for chunk in chunk_document_text(payload.get("parsed_text"))
        ] == expected_texts

        api_key = os.getenv("GUARDIAN_API_KEY", "test-key")
        headers = {"X-API-Key": api_key}
        for index, text in enumerate(expected_texts):
            embed_response = client.post(
                "/embed",
                json={
                    "text": text,
                    "metadata": {
                        "chunk_index": index,
                        "chunk_count": len(expected_texts),
                    },
                },
                headers=headers,
            )
            assert embed_response.status_code == 200

        assert [item.text for item in fake_store.items] == expected_texts

        chunk_indices = [
            item.meta.get("chunk_index") for item in fake_store.items
        ]
        assert chunk_indices == list(range(len(expected_texts)))
        assert all(
            item.meta.get("chunk_count") == len(expected_texts)
            for item in fake_store.items
        )

        search_response = client.post(
            "/search",
            json={"query": needle},
            headers=headers,
        )
        assert search_response.status_code == 200
        results = search_response.json().get("results", [])
        assert any(needle in result.get("text", "") for result in results)
