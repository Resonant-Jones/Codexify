from __future__ import annotations

from guardian.core.candidate_normalizer import (
    NormalizedEntity,
    NormalizedEntitySet,
)
from guardian.memory_graph.graph_candidate_mapper import (
    map_to_graph_write_candidates,
)


def _entity(
    *,
    entity_type: str,
    content: str,
    source: str,
    confidence: float = 0.5,
    metadata: dict[str, object] | None = None,
) -> NormalizedEntity:
    return NormalizedEntity(
        type=entity_type,
        content=content,
        source=source,
        confidence=confidence,
        metadata=dict(metadata or {}),
    )


def test_maps_document_entity_to_graph_node_candidate():
    normalized = NormalizedEntitySet(
        entities=[
            _entity(
                entity_type="document",
                content="Project brief",
                source="retrieval",
                confidence=0.9,
                metadata={
                    "id": "doc-1",
                    "thread_id": "thread-1",
                    "project_id": "project-1",
                },
            )
        ],
        warnings=[],
    )

    candidate_set = map_to_graph_write_candidates(normalized)

    assert len(candidate_set.nodes) == 1
    node = candidate_set.nodes[0]
    assert node.node_type == "Document"
    assert node.source_type == "retrieval"
    assert node.source_id == "doc-1"
    assert node.content == "Project brief"
    assert node.metadata["normalized_confidence"] == 0.9
    assert node.metadata["normalized_type"] == "document"
    assert node.metadata["normalized_source"] == "retrieval"
    assert node.metadata["normalized_metadata"]["thread_id"] == "thread-1"
    assert candidate_set.edges == []
    assert candidate_set.warnings == []


def test_maps_message_entity_to_graph_node_candidate():
    normalized = NormalizedEntitySet(
        entities=[
            _entity(
                entity_type="message",
                content="Hello world",
                source="thread",
                metadata={
                    "message_id": "msg-1",
                    "thread_id": "thread-1",
                },
            )
        ],
        warnings=[],
    )

    candidate_set = map_to_graph_write_candidates(normalized)

    assert len(candidate_set.nodes) == 1
    node = candidate_set.nodes[0]
    assert node.node_type == "Message"
    assert node.source_type == "thread"
    assert node.source_id == "msg-1"
    assert node.content == "Hello world"
    assert candidate_set.edges == []
    assert candidate_set.warnings == []


def test_unknown_entity_type_emits_warning_and_unknown_node_type():
    normalized = NormalizedEntitySet(
        entities=[
            _entity(
                entity_type="alien",
                content="Unknown record",
                source="model",
                metadata={"id": "alien-1"},
            )
        ],
        warnings=[],
    )

    candidate_set = map_to_graph_write_candidates(normalized)

    assert len(candidate_set.nodes) == 1
    assert candidate_set.nodes[0].node_type == "Unknown"
    assert "unknown_entity_type" in candidate_set.warnings


def test_shared_thread_id_creates_part_of_thread_edge():
    normalized = NormalizedEntitySet(
        entities=[
            _entity(
                entity_type="document",
                content="Doc A",
                source="retrieval",
                metadata={
                    "id": "doc-a",
                    "thread_id": "thread-1",
                },
            ),
            _entity(
                entity_type="fact",
                content="Fact B",
                source="memory",
                metadata={
                    "id": "fact-b",
                    "thread_id": "thread-1",
                },
            ),
        ],
        warnings=[],
    )

    candidate_set = map_to_graph_write_candidates(normalized)

    assert len(candidate_set.edges) == 1
    edge = candidate_set.edges[0]
    assert edge.edge_type == "PART_OF_THREAD"
    assert edge.metadata["thread_id"] == "thread-1"
    assert edge.from_node_key != edge.to_node_key


def test_shared_project_id_creates_part_of_project_edge():
    normalized = NormalizedEntitySet(
        entities=[
            _entity(
                entity_type="document",
                content="Doc A",
                source="retrieval",
                metadata={
                    "id": "doc-a",
                    "project_id": "project-1",
                },
            ),
            _entity(
                entity_type="message",
                content="Message B",
                source="thread",
                metadata={
                    "id": "msg-b",
                    "project_id": "project-1",
                },
            ),
        ],
        warnings=[],
    )

    candidate_set = map_to_graph_write_candidates(normalized)

    assert len(candidate_set.edges) == 1
    edge = candidate_set.edges[0]
    assert edge.edge_type == "PART_OF_PROJECT"
    assert edge.metadata["project_id"] == "project-1"
    assert edge.from_node_key != edge.to_node_key


def test_explicit_source_message_id_creates_derived_from_edge():
    normalized = NormalizedEntitySet(
        entities=[
            _entity(
                entity_type="message",
                content="Source message",
                source="thread",
                metadata={
                    "id": "msg-1",
                    "thread_id": "thread-1",
                },
            ),
            _entity(
                entity_type="document",
                content="Derived document",
                source="retrieval",
                metadata={
                    "id": "doc-1",
                    "source_message_id": "msg-1",
                    "thread_id": "thread-1",
                },
            ),
        ],
        warnings=[],
    )

    candidate_set = map_to_graph_write_candidates(normalized)

    derived_edge = next(
        edge for edge in candidate_set.edges if edge.edge_type == "DERIVED_FROM"
    )
    assert derived_edge.metadata["source_message_id"] == "msg-1"
    assert derived_edge.from_node_key != derived_edge.to_node_key


def test_empty_entity_set_returns_warning():
    candidate_set = map_to_graph_write_candidates(
        NormalizedEntitySet(entities=[], warnings=[])
    )

    assert candidate_set.nodes == []
    assert candidate_set.edges == []
    assert candidate_set.warnings == ["empty_normalized_entity_set"]


def test_missing_content_skips_entity_with_warning():
    normalized = NormalizedEntitySet(
        entities=[
            _entity(
                entity_type="document",
                content="   ",
                source="retrieval",
                metadata={"id": "doc-1"},
            )
        ],
        warnings=[],
    )

    candidate_set = map_to_graph_write_candidates(normalized)

    assert candidate_set.nodes == []
    assert candidate_set.edges == []
    assert "skipped_entity_missing_content" in candidate_set.warnings


def test_duplicate_node_key_is_deduped_with_warning():
    normalized = NormalizedEntitySet(
        entities=[
            _entity(
                entity_type="document",
                content="Duplicate document",
                source="retrieval",
                metadata={"id": "doc-1", "thread_id": "thread-1"},
            ),
            _entity(
                entity_type="document",
                content="Duplicate document",
                source="retrieval",
                metadata={"id": "doc-1", "thread_id": "thread-1"},
            ),
        ],
        warnings=[],
    )

    candidate_set = map_to_graph_write_candidates(normalized)

    assert len(candidate_set.nodes) == 1
    assert "duplicate_node_key_deduped" in candidate_set.warnings
