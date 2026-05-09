"""Neo4j graph backend adapter for derived graph-write persistence."""

from __future__ import annotations

import copy
import json
import logging
from typing import Any

from neo4j import GraphDatabase

from guardian.memory_graph.graph_backend import (
    GRAPH_BACKEND_KIND_NEO4J,
    GRAPH_BACKEND_RESULT_STATUS_FAILED,
    GRAPH_BACKEND_RESULT_STATUS_SKIPPED,
    GRAPH_BACKEND_RESULT_STATUS_WRITTEN,
    GraphBackendWriteResult,
)

logger = logging.getLogger(__name__)


class Neo4jGraphBackend:
    backend_kind = GRAPH_BACKEND_KIND_NEO4J

    def __init__(
        self,
        *,
        uri: str,
        username: str,
        password: str,
        database: str | None = None,
        driver: Any | None = None,
    ) -> None:
        self._uri = uri
        self._username = username
        self._password = password
        self._database = database
        self._driver = driver

    def _get_driver(self):
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                self._uri,
                auth=(self._username, self._password),
            )
        return self._driver

    def _execute_node_merge(self, tx, node: dict[str, Any]) -> None:
        metadata_json = json.dumps(
            dict(node.get("metadata") or {}),
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        tx.run(
            """
            MERGE (n:GraphEntity {node_key: $node_key})
            SET
              n.node_type = $node_type,
              n.source_type = $source_type,
              n.source_id = $source_id,
              n.content = $content,
              n.metadata = $metadata_json
            """,
            node_key=str(node.get("node_key") or ""),
            node_type=str(node.get("node_type") or ""),
            source_type=str(node.get("source_type") or ""),
            source_id=str(node.get("source_id") or ""),
            content=str(node.get("content") or ""),
            metadata_json=metadata_json,
        )

    def _execute_edge_merge(
        self, tx, edge: dict[str, Any], graph_write_id: str
    ) -> None:
        metadata_json = json.dumps(
            dict(edge.get("metadata") or {}),
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        tx.run(
            """
            MATCH (src:GraphEntity {node_key: $from_node_key})
            MATCH (dst:GraphEntity {node_key: $to_node_key})
            MERGE (src)-[r:GRAPH_EDGE {
                edge_type: $edge_type,
                from_node_key: $from_node_key,
                to_node_key: $to_node_key
            }]->(dst)
            SET r.metadata = $metadata_json,
                r.graph_write_id = $graph_write_id
            """,
            edge_type=str(edge.get("edge_type") or ""),
            from_node_key=str(edge.get("from_node_key") or ""),
            to_node_key=str(edge.get("to_node_key") or ""),
            metadata_json=metadata_json,
            graph_write_id=graph_write_id,
        )

    def write_graph_candidates(
        self, graph_write_task: dict[str, Any]
    ) -> GraphBackendWriteResult:
        task = copy.deepcopy(graph_write_task)
        graph_write_id = str(task.get("graph_write_id") or "").strip()
        nodes = task.get("nodes") if isinstance(task.get("nodes"), list) else []
        edges = task.get("edges") if isinstance(task.get("edges"), list) else []

        if not graph_write_id:
            return GraphBackendWriteResult(
                status=GRAPH_BACKEND_RESULT_STATUS_FAILED,
                backend_kind=self.backend_kind,
                graph_write_id="",
                metadata={"reason": "missing_graph_write_id"},
            )

        filtered_nodes = [
            dict(node)
            for node in nodes
            if isinstance(node, dict)
            and str(node.get("node_key") or "").strip()
        ]
        filtered_edges = [
            dict(edge)
            for edge in edges
            if isinstance(edge, dict)
            and str(edge.get("edge_type") or "").strip()
            and str(edge.get("from_node_key") or "").strip()
            and str(edge.get("to_node_key") or "").strip()
        ]

        if not filtered_nodes and not filtered_edges:
            return GraphBackendWriteResult(
                status=GRAPH_BACKEND_RESULT_STATUS_SKIPPED,
                backend_kind=self.backend_kind,
                graph_write_id=graph_write_id,
                metadata={"reason": "empty_candidates"},
            )

        try:
            driver = self._get_driver()
            with driver.session(database=self._database) as session:

                def _tx(tx):
                    for node in filtered_nodes:
                        self._execute_node_merge(tx, node)
                    for edge in filtered_edges:
                        self._execute_edge_merge(tx, edge, graph_write_id)

                session.execute_write(_tx)
        except Exception as exc:
            logger.exception("[graph-write] neo4j backend write failed")
            return GraphBackendWriteResult(
                status=GRAPH_BACKEND_RESULT_STATUS_FAILED,
                backend_kind=self.backend_kind,
                graph_write_id=graph_write_id,
                node_count=len(filtered_nodes),
                edge_count=len(filtered_edges),
                metadata={"reason": "neo4j_write_failed", "error": str(exc)},
            )

        return GraphBackendWriteResult(
            status=GRAPH_BACKEND_RESULT_STATUS_WRITTEN,
            backend_kind=self.backend_kind,
            graph_write_id=graph_write_id,
            node_count=len(filtered_nodes),
            edge_count=len(filtered_edges),
            metadata={"persisted": True},
        )


__all__ = ["Neo4jGraphBackend"]
