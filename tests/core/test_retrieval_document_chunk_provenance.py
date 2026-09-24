from __future__ import annotations

from guardian.core.chat_completion_service import (
    _build_retrieval_provenance,
    _cohere_contributing_retrieval_truth,
)


def _prompt_meta(*, semantic_injected: bool, docs_injected: bool) -> dict:
    return {
        "context": {
            "semantic": {
                "count": 1 if semantic_injected else 0,
                "injected": semantic_injected,
            }
        },
        "docs": {
            "count": 1 if docs_injected else 0,
            "injected": docs_injected,
        },
    }


def test_retained_document_chunk_projects_bounded_contributing_provenance() -> None:
    bundle = {
        "semantic": [
            {
                "id": "vector-item-7",
                "text": "CODEXIFY_PROVENANCE_TEST has value COBALT-3187.",
                "score": 0.94,
                "source_type": "document",
                "role": "document",
                "project_id": 17,
                "thread_id": 23,
                "retrieval_lane": "project_semantic",
                "metadata": {
                    "doc_id": "doc-stable-123",
                    "chunk_index": 2,
                    "chunk_count": 5,
                    "filename": "provenance-fixture.txt",
                    "namespace": "project:17",
                    "user_id": "local",
                },
            }
        ],
        "docs": {"project": [], "thread": [], "global": []},
        "_prompt_meta": _prompt_meta(
            semantic_injected=True,
            docs_injected=False,
        ),
        "retrieval_suppression": {
            "items": [
                {
                    "id": "foreign-vector-item",
                    "metadata": {
                        "doc_id": "foreign-doc",
                        "chunk_index": 0,
                        "project_id": 999,
                        "user_id": "other-user",
                    },
                    "suppressed": True,
                }
            ]
        },
    }

    provenance = _build_retrieval_provenance(
        requested_source_mode="workspace",
        normalized_source_mode="workspace",
        bundle=bundle,
    )

    assert provenance["source_hit_counts"]["semantic_total"] == 1
    assert provenance["retrieval_status"] == "workspace_local_success"
    assert provenance["contributing_items"] == [
        {
            "source_type": "document",
            "role": "document",
            "document_id": "doc-stable-123",
            "chunk_id": "vector-item-7",
            "chunk_index": 2,
            "chunk_count": 5,
            "project_id": 17,
            "thread_id": 23,
            "retrieval_lane": "project_semantic",
            "namespace": "project:17",
            "filename": "provenance-fixture.txt",
            "score": 0.94,
        }
    ]
    serialized = repr(provenance["contributing_items"])
    assert "CODEXIFY_PROVENANCE_TEST" not in serialized
    assert "foreign-doc" not in serialized

    retrieval_executed, absence_reason = _cohere_contributing_retrieval_truth(
        retrieval_provenance=provenance,
        retrieval_executed=False,
        retrieval_absence_reason="retrieval_no_candidates",
    )
    assert retrieval_executed is True
    assert absence_reason is None


def test_injected_document_record_preserves_document_and_chunk_index() -> None:
    bundle = {
        "semantic": [],
        "docs": {
            "project": [
                {
                    "id": "doc-project-44",
                    "title": "project-fact.txt",
                    "excerpt": "A bounded excerpt used by the provider.",
                    "source_type": "uploaded",
                    "role": "document",
                    "project_id": 17,
                    "chunk_index": 0,
                    "retrieval_lane": "project_docs",
                }
            ],
            "thread": [],
            "global": [],
        },
        "_prompt_meta": _prompt_meta(
            semantic_injected=False,
            docs_injected=True,
        ),
    }

    provenance = _build_retrieval_provenance(
        requested_source_mode="project",
        normalized_source_mode="project",
        bundle=bundle,
    )

    assert provenance["source_hit_counts"]["project_documents"] == 1
    assert provenance["contributing_items"] == [
        {
            "source_type": "uploaded",
            "role": "document",
            "document_id": "doc-project-44",
            "chunk_index": 0,
            "project_id": 17,
            "retrieval_lane": "project_docs",
            "filename": "project-fact.txt",
        }
    ]
    assert "chunk_id" not in provenance["contributing_items"][0]
    assert "excerpt" not in provenance["contributing_items"][0]


def test_non_injected_candidates_do_not_fabricate_contributing_items() -> None:
    bundle = {
        "semantic": [
            {
                "id": "candidate-only",
                "text": "Candidate text that was not injected.",
                "metadata": {
                    "doc_id": "doc-candidate-only",
                    "chunk_index": 0,
                },
            }
        ],
        "docs": {"project": [], "thread": [], "global": []},
        "_prompt_meta": _prompt_meta(
            semantic_injected=False,
            docs_injected=False,
        ),
    }

    provenance = _build_retrieval_provenance(
        requested_source_mode="workspace",
        normalized_source_mode="workspace",
        bundle=bundle,
    )

    assert provenance["source_hit_counts"]["semantic_total"] == 1
    assert provenance["contributing_items"] == []
    retrieval_executed, absence_reason = _cohere_contributing_retrieval_truth(
        retrieval_provenance=provenance,
        retrieval_executed=True,
        retrieval_absence_reason="retrieval_no_candidates",
    )
    assert retrieval_executed is True
    assert absence_reason == "retrieval_no_candidates"
