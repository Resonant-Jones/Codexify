from __future__ import annotations

from guardian.routes.chat import _build_scoped_doc_override


def test_build_scoped_doc_override_includes_delimiters_and_provenance() -> None:
    bundle = {
        "project": [
            {
                "id": "proj-123",
                "title": "Project Spec",
                "scope": "project",
                "source": "uploaded",
                "document_type": "uploaded",
                "thread_id": None,
                "project_id": 44,
                "excerpt": "project excerpt",
                "provenance": {"relation": "project_library"},
            }
        ],
        "thread": [
            {
                "id": "thr-456",
                "title": "Thread Draft",
                "scope": "thread",
                "source": "generated",
                "document_type": "generated",
                "thread_id": 8,
                "project_id": 44,
                "excerpt": "thread excerpt",
                "provenance": {"relation": "attached"},
            }
        ],
    }

    text = _build_scoped_doc_override(bundle, max_chars=5000)

    assert text is not None
    assert "=== PROJECT DOCUMENTS ===" in text
    assert "=== THREAD DOCUMENTS ===" in text
    assert "id: proj-123" in text
    assert "id: thr-456" in text
    assert "relation: project_library" in text
    assert "relation: attached" in text


def test_build_scoped_doc_override_respects_char_budget() -> None:
    bundle = {
        "project": [
            {
                "id": "doc-a",
                "title": "Doc A",
                "scope": "project",
                "source": "uploaded",
                "document_type": "uploaded",
                "thread_id": None,
                "project_id": 1,
                "excerpt": "A" * 150,
                "provenance": {"relation": "project_library"},
            },
            {
                "id": "doc-b",
                "title": "Doc B",
                "scope": "project",
                "source": "uploaded",
                "document_type": "uploaded",
                "thread_id": None,
                "project_id": 1,
                "excerpt": "B" * 150,
                "provenance": {"relation": "project_library"},
            },
        ],
        "thread": [],
    }

    text = _build_scoped_doc_override(bundle, max_chars=330)

    assert text is not None
    assert "id: doc-a" in text
    assert "id: doc-b" not in text
