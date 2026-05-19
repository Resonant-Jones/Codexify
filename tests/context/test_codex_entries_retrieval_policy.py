"""Focused tests for Codex Entry retrieval exclusion policy."""

from __future__ import annotations

from guardian.context.broker import ContextBroker


def test_codex_entries_with_retrieval_disabled_are_excluded():
    items = [
        {
            "id": "codex-disabled",
            "source_type": "codex_entry",
            "retrieval_enabled": False,
            "text": "Drafted Codex Entry",
        },
        {
            "id": "codex-missing-flag",
            "source_type": "codex_entry",
            "metadata": {},
            "text": "Legacy Codex Entry",
        },
        {
            "id": "project-doc",
            "source_type": "document",
            "text": "Project Knowledge Base document",
        },
    ]

    filtered = ContextBroker._filter_codex_entries(items)

    assert [item["id"] for item in filtered] == ["project-doc"]


def test_codex_entries_with_retrieval_enabled_are_not_excluded():
    items = [
        {
            "id": "codex-enabled",
            "source_type": "codex_entry",
            "metadata": {"retrieval_enabled": True},
            "text": "Opted-in Codex Entry",
        },
        {
            "id": "ordinary-doc",
            "type": "document",
            "text": "Ordinary document",
        },
    ]

    filtered = ContextBroker._filter_codex_entries(items)

    assert [item["id"] for item in filtered] == [
        "codex-enabled",
        "ordinary-doc",
    ]


def test_non_codex_documents_are_not_filtered_by_codex_exclusion_rule():
    items = [
        {
            "id": "pkb-doc",
            "source_type": "document",
            "metadata": {"document_scope": "project"},
            "text": "Project Knowledge Base material",
        },
        {
            "id": "thread-doc",
            "type": "uploaded_document",
            "text": "Thread-linked document",
        },
        {
            "id": "semantic-hit",
            "source_type": "semantic",
            "text": "Non-Codex semantic hit",
        },
    ]

    filtered = ContextBroker._filter_codex_entries(items)

    assert filtered == items


def test_doc_bucket_filter_preserves_non_codex_project_knowledge_boundary():
    docs = {
        "project": [
            {
                "id": "project-doc",
                "source_type": "document",
                "metadata": {"document_scope": "project"},
            },
            {
                "id": "disabled-codex",
                "source_type": "codex_entry",
                "retrieval_enabled": False,
            },
        ],
        "thread": [
            {
                "id": "thread-doc",
                "type": "uploaded_document",
            },
            {
                "id": "enabled-codex",
                "type": "codex_entry",
                "retrieval_enabled": True,
            },
        ],
    }

    filtered = ContextBroker._filter_codex_from_doc_buckets(docs)

    assert [item["id"] for item in filtered["project"]] == ["project-doc"]
    assert [item["id"] for item in filtered["thread"]] == [
        "thread-doc",
        "enabled-codex",
    ]
