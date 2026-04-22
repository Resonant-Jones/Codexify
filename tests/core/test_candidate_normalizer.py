from guardian.core.candidate_normalizer import normalize_candidate_trace


def test_normalizes_documents_list():
    candidate_trace = {
        "documents": [
            {
                "content": "Document body",
                "confidence": 0.9,
                "id": "doc-1",
            }
        ]
    }

    normalized = normalize_candidate_trace(candidate_trace)

    assert len(normalized.entities) == 1
    entity = normalized.entities[0]
    assert entity.type == "document"
    assert entity.source == "retrieval"
    assert entity.content == "Document body"
    assert entity.confidence == 0.9
    assert entity.metadata["field"] == "documents"
    assert entity.metadata["fragment"]["id"] == "doc-1"
    assert normalized.warnings == []


def test_handles_missing_fields_gracefully():
    candidate_trace = {"request_id": "req-1"}

    normalized = normalize_candidate_trace(candidate_trace)

    assert normalized.entities == []
    assert normalized.warnings == ["empty_candidate_trace"]


def test_empty_trace_returns_warning():
    normalized = normalize_candidate_trace({})

    assert normalized.entities == []
    assert normalized.warnings == ["empty_candidate_trace"]


def test_malformed_entries_are_skipped():
    candidate_trace = {
        "messages": [
            {},
            {
                "content": "Recovered message",
                "confidence": 0.7,
                "role": "assistant",
            },
        ]
    }

    normalized = normalize_candidate_trace(candidate_trace)

    assert len(normalized.entities) == 1
    entity = normalized.entities[0]
    assert entity.type == "message"
    assert entity.source == "thread"
    assert entity.content == "Recovered message"
    assert entity.confidence == 0.7
    assert "malformed_candidate_entry" in normalized.warnings


def test_confidence_defaults_to_midpoint():
    candidate_trace = {
        "memory": [
            {
                "content": "Persistent fact",
            }
        ]
    }

    normalized = normalize_candidate_trace(candidate_trace)

    assert len(normalized.entities) == 1
    entity = normalized.entities[0]
    assert entity.type == "fact"
    assert entity.source == "memory"
    assert entity.confidence == 0.5
    assert normalized.warnings == []
