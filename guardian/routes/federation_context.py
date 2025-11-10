"""Federated semantic search and context retrieval API.

Enables Guardian to query the awareness graph and vector store locally,
and to request context from trusted peer nodes across the federation.
"""

import logging
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from guardian.core import event_bus
from guardian.core.auth import require_user
from guardian.federation.graph_model import GraphNode, GraphEdge
from guardian.federation.graph_store import get_graph_store
from guardian.federation.manager import manager
from guardian.federation.trust_registry import (
    get_trust_registry,
    calculate_result_score,
    calculate_recency_factor,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/federation/context", tags=["federation-context"])


class SearchRequest(BaseModel):
    """Request body for semantic context search."""

    query: str = Field(..., description="Search query/question")
    limit: int = Field(default=5, ge=1, le=50, description="Max results to return")
    include_peers: bool = Field(
        default=False,
        description="Whether to include results from peer nodes",
    )
    include_graph: bool = Field(
        default=True,
        description="Whether to include relationship data from awareness graph",
    )
    depth: str = Field(
        default="normal",
        description="Search depth: 'shallow', 'normal', 'deep'",
    )


class SearchResult(BaseModel):
    """Individual search result from local or peer node."""

    source: str = Field(..., description="'local' or peer node ID")
    node_id: str = Field(..., description="ID of the found node")
    node_type: str = Field(..., description="Type of node (document, thread, etc)")
    label: str = Field(..., description="Human-readable label")
    score: float = Field(..., ge=0.0, le=1.0, description="Ranked relevance score")
    summary: Optional[str] = Field(None, description="Brief description or content excerpt")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional node metadata",
    )
    relationship: Optional[str] = Field(
        None,
        description="Edge relation that led to this result",
    )
    peer: Optional[str] = Field(None, description="Peer node ID if from remote")


class SearchResponse(BaseModel):
    """Response containing ranked search results."""

    results: List[SearchResult] = Field(..., description="Ranked results")
    total: int = Field(..., description="Total results found")
    query: str = Field(..., description="The query that was executed")
    sources: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of results per source",
    )


class PeerInfo(BaseModel):
    """Information about a reachable peer node."""

    node_id: str = Field(..., description="Peer node identifier")
    relay_endpoint: str = Field(..., description="WebSocket endpoint for relay")
    capabilities: List[str] = Field(
        default_factory=list,
        description="Capabilities supported by this peer",
    )
    trust_level: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Trust level for this peer (0.0-1.0)",
    )
    active_relays: int = Field(
        default=0,
        description="Number of active relay sessions with this peer",
    )


class PeersResponse(BaseModel):
    """Response listing reachable peer nodes."""

    peers: List[PeerInfo] = Field(..., description="List of reachable peers")
    total: int = Field(..., description="Total peer count")
    local_node_id: str = Field(..., description="This node's ID")


async def _search_local(
    query: str,
    limit: int,
    include_graph: bool,
) -> List[SearchResult]:
    """Search locally using awareness graph and vector store.

    Args:
        query: Search query
        limit: Maximum results to return
        include_graph: Whether to include graph-based results

    Returns:
        List of SearchResult objects
    """
    results = []
    store = get_graph_store()

    # Search by node labels and metadata if include_graph is true
    if include_graph:
        try:
            # Search all nodes
            all_nodes = list(store.graph["nodes"].values())

            # Score nodes based on query match in label and metadata
            scored_nodes = []
            for node in all_nodes:
                # Simple text matching scoring
                label_match = (
                    query.lower() in node.label.lower()
                    if isinstance(node.label, str)
                    else 0
                )
                metadata_match = any(
                    query.lower() in str(v).lower()
                    for v in (node.metadata.values() if node.metadata else [])
                )

                if label_match or metadata_match:
                    # Calculate recency
                    if hasattr(node, "updated_at") and node.updated_at:
                        minutes_ago = (
                            datetime.now(timezone.utc) - node.updated_at
                        ).total_seconds() / 60
                        recency = calculate_recency_factor(int(minutes_ago))
                    else:
                        recency = 0.5

                    score = (label_match * 0.5 + metadata_match * 0.3 + recency * 0.2)
                    scored_nodes.append((score, node))

            # Sort by score and take top results
            scored_nodes.sort(key=lambda x: x[0], reverse=True)
            for score, node in scored_nodes[:limit]:
                results.append(
                    SearchResult(
                        source="local",
                        node_id=f"{node.type}:{node.id}",
                        node_type=node.type,
                        label=node.label,
                        score=min(score, 1.0),
                        summary=node.metadata.get("description") if node.metadata else None,
                        metadata=node.metadata or {},
                    )
                )

            logger.debug(f"Local graph search found {len(results)} results")

        except Exception as e:
            logger.error(f"Error searching local graph: {e}")

    return results


async def _search_peers(
    query: str,
    limit: int,
    relays: Optional[Dict[str, Any]] = None,
) -> List[SearchResult]:
    """Query peer nodes for context via federation relays.

    Args:
        query: Search query
        limit: Maximum results per peer
        relays: Optional relay sessions to use (all active if not provided)

    Returns:
        List of SearchResult objects from peers
    """
    results = []
    trust_registry = get_trust_registry()

    # Get relay sessions to query
    if relays is None:
        relays = manager.active_relays

    if not relays:
        logger.debug("No active relay sessions for peer search")
        return results

    # Query each peer via relay
    for relay in list(relays.values()):
        if relay.is_expired():
            continue

        try:
            # Get peer manifest to check capabilities and trust
            target_node_id = relay.target_node_id
            target_manifest = manager.get_peer_manifest(target_node_id)

            if not target_manifest or "search" not in target_manifest.capabilities:
                logger.debug(f"Peer {target_node_id} does not support search capability")
                continue

            trust_level = trust_registry.get_trust_level(target_node_id)

            # Prepare search request for peer
            search_payload = {
                "query": query,
                "limit": limit,
                "include_peers": False,  # Avoid recursive peer queries
                "include_graph": True,
            }

            # Send to peer via relay
            message = {
                "type": "context_search",
                "payload": search_payload,
            }

            # Forward via both WebSocket connections if available
            for ws in [relay.source_ws, relay.target_ws]:
                if ws and hasattr(ws, "send_json"):
                    try:
                        await ws.send_json(message)
                        logger.debug(f"Sent search query to peer {target_node_id}")
                    except Exception as e:
                        logger.warning(f"Failed to send search to peer: {e}")

            # In a real implementation, we'd wait for responses from peers
            # For now, this demonstrates the mechanism

        except Exception as e:
            logger.error(f"Error querying peer {relay.target_node_id}: {e}")

    return results


@router.post("/search", response_model=SearchResponse)
async def search_context(
    body: SearchRequest,
    user=Depends(require_user),
) -> Dict[str, Any]:
    """Search for context across local and peer nodes.

    Performs semantic search on the awareness graph and optionally
    queries trusted peer nodes. Results are ranked by relevance,
    peer trust, and recency.

    Args:
        body: SearchRequest with query and options
        user: Authenticated user

    Returns:
        SearchResponse with ranked results
    """
    try:
        # Validate user has search capability
        # In a real implementation, check user roles/permissions
        logger.info(f"Context search from user {user.id}: {body.query}")

        # Search locally
        local_results = await _search_local(
            body.query,
            body.limit,
            body.include_graph,
        )

        all_results = local_results.copy()

        # Search peers if requested
        if body.include_peers:
            try:
                peer_results = await _search_peers(body.query, body.limit)
                all_results.extend(peer_results)
            except Exception as e:
                logger.warning(f"Error searching peers: {e}")

        # Apply trust-weighted ranking
        trust_registry = get_trust_registry()
        for result in all_results:
            if result.peer:
                trust_level = trust_registry.get_trust_level(result.peer)
            else:
                trust_level = 1.0  # Local results have full trust

            # Recalculate score with trust weight
            result.score = calculate_result_score(
                result.score,
                trust_level=trust_level,
            )

        # Sort by score
        all_results.sort(key=lambda r: r.score, reverse=True)

        # Limit results
        ranked_results = all_results[: body.limit]

        # Count by source
        source_counts = {}
        for result in ranked_results:
            source = result.source
            source_counts[source] = source_counts.get(source, 0) + 1

        # Emit event
        event_bus.emit_event(
            topic="federation.context.search",
            payload={
                "query": body.query,
                "result_count": len(ranked_results),
                "sources": source_counts,
                "user_id": user.id,
            },
        )

        return {
            "results": ranked_results,
            "total": len(all_results),
            "query": body.query,
            "sources": source_counts,
        }

    except Exception as e:
        logger.error(f"Error performing context search: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/peers", response_model=PeersResponse)
async def get_peers(
    user=Depends(require_user),
) -> Dict[str, Any]:
    """Get list of reachable peer nodes and their capabilities.

    Returns information about trusted peers including their
    relay endpoints, supported capabilities, and trust levels.

    Args:
        user: Authenticated user

    Returns:
        PeersResponse with peer information
    """
    try:
        trust_registry = get_trust_registry()
        peers = []

        # Get active relays to find reachable peers
        for relay in list(manager.active_relays.values()):
            if relay.is_expired():
                continue

            target_node_id = relay.target_node_id
            target_manifest = manager.get_peer_manifest(target_node_id)

            if not target_manifest:
                continue

            trust_level = trust_registry.get_trust_level(target_node_id)

            peers.append(
                PeerInfo(
                    node_id=target_node_id,
                    relay_endpoint=target_manifest.relay_endpoint,
                    capabilities=target_manifest.capabilities,
                    trust_level=trust_level,
                    active_relays=1,  # Each relay counted once
                )
            )

        # Also include cached peer manifests even without active relays
        for node_id, manifest in manager.peer_manifests.items():
            if not any(p.node_id == node_id for p in peers):
                trust_level = trust_registry.get_trust_level(node_id)
                peers.append(
                    PeerInfo(
                        node_id=node_id,
                        relay_endpoint=manifest.relay_endpoint,
                        capabilities=manifest.capabilities,
                        trust_level=trust_level,
                        active_relays=0,
                    )
                )

        # Get this node's ID from federation config
        try:
            from guardian.routes.federation import _node_id
            local_node_id = _node_id or "unknown"
        except Exception:
            local_node_id = "unknown"

        logger.info(f"Returning info for {len(peers)} peers to user {user.id}")

        return {
            "peers": peers,
            "total": len(peers),
            "local_node_id": local_node_id,
        }

    except Exception as e:
        logger.error(f"Error getting peer list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/peers/{peer_id}/trust")
async def set_peer_trust(
    peer_id: str,
    trust_level: float = Query(
        ...,
        ge=0.0,
        le=1.0,
        description="Trust level from 0.0 to 1.0",
    ),
    user=Depends(require_user),
) -> Dict[str, Any]:
    """Set trust level for a peer node.

    Allows admins to adjust how much weight peer search results
    receive in ranking.

    Args:
        peer_id: Peer node identifier
        trust_level: Trust level from 0.0 to 1.0
        user: Authenticated user

    Returns:
        Confirmation with updated trust level
    """
    try:
        # In a real implementation, check if user is admin
        trust_registry = get_trust_registry()
        trust_registry.set_trust_level(peer_id, trust_level)

        logger.info(f"User {user.id} set trust level for {peer_id}: {trust_level}")

        event_bus.emit_event(
            topic="federation.trust.updated",
            payload={
                "peer_id": peer_id,
                "trust_level": trust_level,
                "updated_by": user.id,
            },
        )

        return {
            "status": "updated",
            "peer_id": peer_id,
            "trust_level": trust_level,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error setting peer trust: {e}")
        raise HTTPException(status_code=500, detail=str(e))
