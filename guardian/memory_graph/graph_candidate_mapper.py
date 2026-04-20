"""Pure graph-candidate mapping helpers for normalized candidate entities."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List

from guardian.core.candidate_normalizer import NormalizedEntitySet

_NODE_TYPE_MAP = {
    "document": "Document",
    "message": "Message",
    "fact": "MemoryFact",
}


@dataclass
class GraphNodeCandidate:
    node_key: str
    node_type: str
    source_type: str
    source_id: str | None
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdgeCandidate:
    edge_type: str
    from_node_key: str
    to_node_key: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphWriteCandidateSet:
    nodes: list[GraphNodeCandidate]
    edges: list[GraphEdgeCandidate]
    warnings: list[str]


def _entity_metadata(entity: Any) -> dict[str, Any]:
    metadata = getattr(entity, "metadata", {}) or {}
    return dict(metadata) if isinstance(metadata, dict) else {}


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _source_id_from_metadata(metadata: dict[str, Any]) -> str | None:
    for key in (
        "source_id",
        "message_id",
        "document_id",
        "fact_id",
        "chunk_id",
        "id",
    ):
        value = metadata.get(key)
        if value not in (None, ""):
            text = str(value).strip()
            if text:
                return text

    fragment = metadata.get("fragment")
    if isinstance(fragment, dict):
        for key in (
            "source_id",
            "message_id",
            "document_id",
            "fact_id",
            "chunk_id",
            "id",
        ):
            value = fragment.get(key)
            if value not in (None, ""):
                text = str(value).strip()
                if text:
                    return text

    return None


def _scope_value(metadata: dict[str, Any], key: str) -> str | None:
    value = metadata.get(key)
    if value in (None, ""):
        return None
    text = str(value).strip()
    return text or None


def _stable_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
        ensure_ascii=False,
    )


def _node_key_for_entity(
    *,
    entity_type: str,
    content: str,
    source_type: str,
    source_id: str | None,
    metadata: dict[str, Any],
) -> str:
    material = {
        "entity_type": entity_type,
        "content": content,
        "source_type": source_type,
        "source_id": source_id,
        "thread_id": _scope_value(metadata, "thread_id"),
        "project_id": _scope_value(metadata, "project_id"),
        "source_message_id": _scope_value(metadata, "source_message_id"),
    }
    digest = hashlib.sha256(_stable_json(material).encode("utf-8")).hexdigest()
    return f"graph:{entity_type}:{digest[:24]}"


def _build_node_metadata(
    *,
    entity: Any,
    entity_type: str,
    source_type: str,
    source_id: str | None,
    normalized_metadata: dict[str, Any],
) -> dict[str, Any]:
    metadata = {
        "normalized_metadata": copy.deepcopy(normalized_metadata),
        "normalized_confidence": getattr(entity, "confidence", 0.5),
        "normalized_type": getattr(entity, "type", ""),
        "normalized_source": source_type,
    }
    if source_id is not None:
        metadata["source_id"] = source_id
    for key in ("thread_id", "project_id", "source_message_id"):
        value = normalized_metadata.get(key)
        if value not in (None, ""):
            metadata[key] = value
    metadata["graph_node_type"] = entity_type
    return metadata


def _map_node_type(entity_type: str, warnings: list[str]) -> str:
    node_type = _NODE_TYPE_MAP.get(entity_type)
    if node_type is None:
        warnings.append("unknown_entity_type")
        return "Unknown"
    return node_type


def map_to_graph_write_candidates(
    normalized_entity_set: NormalizedEntitySet,
) -> GraphWriteCandidateSet:
    entities = list(getattr(normalized_entity_set, "entities", []) or [])
    warnings = list(getattr(normalized_entity_set, "warnings", []) or [])
    if not entities:
        warnings.append("empty_normalized_entity_set")
        return GraphWriteCandidateSet(nodes=[], edges=[], warnings=warnings)

    unique_nodes_by_key: dict[str, GraphNodeCandidate] = {}
    ordered_nodes: list[GraphNodeCandidate] = []

    for entity in entities:
        content = _coerce_text(getattr(entity, "content", "")).strip()
        if not content:
            warnings.append("skipped_entity_missing_content")
            continue

        raw_type = _coerce_text(getattr(entity, "type", "")).strip().lower()
        node_type = _map_node_type(raw_type, warnings)
        normalized_metadata = _entity_metadata(entity)
        source_type = (
            _coerce_text(getattr(entity, "source", "")).strip() or "unknown"
        )
        source_id = _source_id_from_metadata(normalized_metadata)
        node_key = _node_key_for_entity(
            entity_type=raw_type or "unknown",
            content=content,
            source_type=source_type,
            source_id=source_id,
            metadata=normalized_metadata,
        )

        if node_key in unique_nodes_by_key:
            warnings.append("duplicate_node_key_deduped")
            continue

        node = GraphNodeCandidate(
            node_key=node_key,
            node_type=node_type,
            source_type=source_type,
            source_id=source_id,
            content=content,
            metadata=_build_node_metadata(
                entity=entity,
                entity_type=node_type,
                source_type=source_type,
                source_id=source_id,
                normalized_metadata=normalized_metadata,
            ),
        )
        unique_nodes_by_key[node_key] = node
        ordered_nodes.append(node)

    nodes = sorted(ordered_nodes, key=lambda item: item.node_key)
    edges: list[GraphEdgeCandidate] = []

    def _group_by_scope(scope_key: str) -> dict[str, list[GraphNodeCandidate]]:
        groups: dict[str, list[GraphNodeCandidate]] = {}
        for node in nodes:
            scope_value = _scope_value(
                node.metadata.get("normalized_metadata", {}),
                scope_key,
            )
            if scope_value is None:
                continue
            groups.setdefault(scope_value, []).append(node)
        return groups

    for thread_id, scoped_nodes in sorted(_group_by_scope("thread_id").items()):
        if len(scoped_nodes) < 2:
            continue
        anchor = sorted(scoped_nodes, key=lambda item: item.node_key)[0]
        for node in sorted(scoped_nodes, key=lambda item: item.node_key)[1:]:
            edges.append(
                GraphEdgeCandidate(
                    edge_type="PART_OF_THREAD",
                    from_node_key=node.node_key,
                    to_node_key=anchor.node_key,
                    metadata={
                        "thread_id": thread_id,
                        "anchor_node_key": anchor.node_key,
                        "relation_basis": "explicit_thread_id",
                    },
                )
            )

    for project_id, scoped_nodes in sorted(
        _group_by_scope("project_id").items()
    ):
        if len(scoped_nodes) < 2:
            continue
        anchor = sorted(scoped_nodes, key=lambda item: item.node_key)[0]
        for node in sorted(scoped_nodes, key=lambda item: item.node_key)[1:]:
            edges.append(
                GraphEdgeCandidate(
                    edge_type="PART_OF_PROJECT",
                    from_node_key=node.node_key,
                    to_node_key=anchor.node_key,
                    metadata={
                        "project_id": project_id,
                        "anchor_node_key": anchor.node_key,
                        "relation_basis": "explicit_project_id",
                    },
                )
            )

    for node in nodes:
        normalized_metadata = node.metadata.get("normalized_metadata", {})
        source_message_id = _scope_value(
            normalized_metadata, "source_message_id"
        )
        if source_message_id is None:
            continue
        matches = [
            candidate
            for candidate in nodes
            if candidate.source_id == source_message_id
        ]
        if len(matches) != 1:
            warnings.append("ambiguous_relationship")
            continue
        target = matches[0]
        if target.node_key == node.node_key:
            warnings.append("ambiguous_relationship")
            continue
        edges.append(
            GraphEdgeCandidate(
                edge_type="DERIVED_FROM",
                from_node_key=node.node_key,
                to_node_key=target.node_key,
                metadata={
                    "source_message_id": source_message_id,
                    "source_node_key": target.node_key,
                    "derived_node_key": node.node_key,
                },
            )
        )

    return GraphWriteCandidateSet(nodes=nodes, edges=edges, warnings=warnings)
