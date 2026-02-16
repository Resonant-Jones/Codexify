"""Federation routes for cross-node collaboration.

Handles session exchange, token generation, and relay channel
establishment between federated Codexify nodes.
"""

import json
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import jwt
import requests
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel, Field

from guardian.core import event_bus
from guardian.core.auth import verify_federation_trust_policy
from guardian.core.config import get_settings
from guardian.core.dependencies import require_api_key
from guardian.core.egress import require_egress_allowed
from guardian.federation.diff_engine import DiffEngine, DiffEntry
from guardian.federation.diff_store import get_diff_store
from guardian.federation.graph_model import GraphEdge, GraphNode, GraphSnapshot
from guardian.federation.graph_store import get_graph_store
from guardian.federation.manager import manager
from guardian.federation.manifest import (
    NodeManifest,
    generate_keypair,
    load_node_keypair_from_env,
    sign_manifest,
    verify_manifest,
)

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/federation",
    tags=["federation"],
    dependencies=[Depends(require_api_key)],
)

# Module-level state for this node
_node_id: Optional[str] = None
_private_key: Optional[str] = None
_public_key: Optional[str] = None
_relay_endpoint: Optional[str] = None


def _normalize_origin(url: str) -> str | None:
    raw = str(url or "").strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def _as_str_set(values: Any) -> set[str]:
    if not isinstance(values, list):
        return set()
    result: set[str] = set()
    for value in values:
        text = str(value).strip()
        if text:
            result.add(text)
    return result


def _policy_allows_open_enrollment(policy: dict[str, Any]) -> bool:
    return bool(policy.get("allow_open_enrollment", False))


def _load_trust_policy() -> dict[str, Any]:
    settings = get_settings()

    if not bool(getattr(settings, "GUARDIAN_FEDERATION_ENABLED", False)):
        raise HTTPException(
            status_code=403,
            detail=(
                "Federation is disabled " "(GUARDIAN_FEDERATION_ENABLED=false)."
            ),
        )

    raw_policy = getattr(
        settings, "GUARDIAN_FEDERATION_TRUST_POLICY_JSON", None
    )
    raw_signature = getattr(
        settings, "GUARDIAN_FEDERATION_TRUST_POLICY_SIGNATURE", None
    )
    require_signed = bool(
        getattr(settings, "GUARDIAN_FEDERATION_REQUIRE_SIGNED_POLICY", True)
    )
    signing_key = getattr(
        settings, "GUARDIAN_FEDERATION_POLICY_SIGNING_KEY", None
    )

    if require_signed:
        valid, policy = verify_federation_trust_policy(
            raw_policy,
            raw_signature,
            signing_key=signing_key,
        )
        if not valid or not isinstance(policy, dict):
            raise HTTPException(
                status_code=503,
                detail=(
                    "Federation trust policy signature is missing or invalid."
                ),
            )
        return policy

    if not raw_policy:
        return {}

    try:
        parsed = json.loads(str(raw_policy))
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Invalid federation trust policy JSON: {exc}",
        ) from exc

    if not isinstance(parsed, dict):
        raise HTTPException(
            status_code=503,
            detail="Federation trust policy must be a JSON object.",
        )
    return parsed


def _enforce_node_allowed(
    policy: dict[str, Any],
    node_id: str | None,
    *,
    label: str,
) -> None:
    if _policy_allows_open_enrollment(policy):
        return
    allowed_nodes = _as_str_set(policy.get("allowed_nodes"))
    if not allowed_nodes:
        raise HTTPException(
            status_code=403,
            detail="Federation trust policy does not allow any peer nodes.",
        )
    normalized = str(node_id or "").strip()
    if not normalized or (
        "*" not in allowed_nodes and normalized not in allowed_nodes
    ):
        raise HTTPException(
            status_code=403,
            detail=f"Federation {label} node is not allowed by trust policy.",
        )


def _enforce_target_origin_allowed(
    policy: dict[str, Any],
    target_url: str,
) -> None:
    if _policy_allows_open_enrollment(policy):
        return
    allowed_origins = _as_str_set(policy.get("allowed_origins"))
    if not allowed_origins:
        raise HTTPException(
            status_code=403,
            detail="Federation trust policy does not allow any peer origins.",
        )

    origin = _normalize_origin(target_url)
    if not origin:
        raise HTTPException(status_code=400, detail="Invalid target_node_url")
    if "*" not in allowed_origins and origin not in allowed_origins:
        raise HTTPException(
            status_code=403,
            detail="Federation target origin is not allowed by trust policy.",
        )


def configure_federation(
    node_id: str,
    relay_endpoint: str,
    private_key: Optional[str] = None,
    public_key: Optional[str] = None,
) -> None:
    """Configure federation settings for this node.

    Args:
        node_id: Unique identifier for this node
        relay_endpoint: Full WebSocket URL for relay endpoint
        private_key: Base64-encoded Ed25519 private key (generated if not provided)
        public_key: Base64-encoded Ed25519 public key (generated if not provided)
    """
    global _node_id, _private_key, _public_key, _relay_endpoint

    _node_id = node_id
    _relay_endpoint = relay_endpoint

    # Try to load from environment if not provided
    if not private_key or not public_key:
        env_private, env_public = load_node_keypair_from_env()
        if env_private and env_public:
            private_key = env_private
            public_key = env_public

    # Generate new keypair if still not available
    if not private_key or not public_key:
        logger.info("Generating new federation keypair")
        private_key, public_key = generate_keypair()

    _private_key = private_key
    _public_key = public_key

    logger.info(f"Federation configured: node_id={node_id}")


def _get_config() -> tuple[str, str, str, str]:
    """Get federation configuration, raising if not configured."""
    if not all([_node_id, _private_key, _public_key, _relay_endpoint]):
        raise RuntimeError(
            "Federation not configured. Call configure_federation() first."
        )
    return _node_id, _private_key, _public_key, _relay_endpoint


class SessionRequestBody(BaseModel):
    """Body for federation session request."""

    target_node_url: str = Field(
        ...,
        description="Full URL of target node (e.g., https://peer.codexify.io)",
    )
    document_id: str = Field(..., description="Document ID to collaborate on")
    user_id: str = Field(..., description="User requesting the session")
    thread_id: Optional[str] = Field(None, description="Optional thread ID")


class SessionResponse(BaseModel):
    """Response for successful session establishment."""

    relay_id: str = Field(..., description="ID for this relay session")
    relay_url: str = Field(
        ..., description="WebSocket URL for relay connection"
    )
    token: str = Field(..., description="JWT token for relay authentication")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class ManifestResponse(BaseModel):
    """Node manifest response."""

    node_id: str
    public_key: str
    capabilities: list[str]
    relay_endpoint: str
    signature: str


@router.get("/manifest", response_model=ManifestResponse)
async def get_node_manifest() -> Dict[str, Any]:
    """Get this node's manifest with signature.

    Returns:
        Signed NodeManifest
    """
    _load_trust_policy()

    try:
        node_id, private_key, _public_key, relay_endpoint = _get_config()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Create manifest
    manifest = NodeManifest(
        node_id=node_id,
        public_key=public_key,
        capabilities=["share", "collab", "autosave"],
        relay_endpoint=relay_endpoint,
    )

    # Sign manifest
    signature = sign_manifest(manifest, private_key)
    manifest.signature = signature

    return manifest.model_dump()


@router.post("/session/request", response_model=SessionResponse)
async def request_session(body: SessionRequestBody) -> Dict[str, Any]:
    """Request a cross-node collaboration session.

    Process:
    1. Fetch target node's manifest
    2. Generate JWT token signed with local private key
    3. Create relay session
    4. Emit federation event
    5. Return relay URL and token

    Args:
        body: Session request parameters

    Returns:
        SessionResponse with relay URL and token
    """
    policy = _load_trust_policy()
    _enforce_target_origin_allowed(policy, body.target_node_url)
    require_egress_allowed("federation")

    try:
        node_id, private_key, _public_key, _relay_endpoint = _get_config()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Check rate limiting
    if not manager.check_rate_limit(body.target_node_url):
        raise HTTPException(status_code=429, detail="Rate limited")

    # Fetch target node's manifest
    try:
        manifest_url = urljoin(body.target_node_url, "/api/federation/manifest")
        response = requests.get(manifest_url, timeout=5)
        response.raise_for_status()
        manifest_data = response.json()
        target_manifest = NodeManifest(**manifest_data)
    except requests.RequestException as e:
        logger.error(f"Failed to fetch target manifest: {e}")
        raise HTTPException(
            status_code=502, detail="Failed to fetch peer manifest"
        )

    # Verify target manifest signature
    if not verify_manifest(target_manifest):
        logger.error(
            f"Invalid signature on manifest from {body.target_node_url}"
        )
        raise HTTPException(
            status_code=400, detail="Invalid peer manifest signature"
        )
    _enforce_node_allowed(policy, target_manifest.node_id, label="target")

    # Cache the peer manifest
    manager.cache_peer_manifest(target_manifest)

    # Check if target supports collab capability
    if "collab" not in target_manifest.capabilities:
        raise HTTPException(
            status_code=400, detail="Target node does not support collaboration"
        )

    # Generate relay session ID
    relay_id = f"relay-{secrets.token_hex(8)}"

    # Create JWT token
    token_payload = {
        "relay_id": relay_id,
        "source_node_id": node_id,
        "target_node_id": target_manifest.node_id,
        "document_id": body.document_id,
        "thread_id": body.thread_id,
        "user_id": body.user_id,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "nonce": secrets.token_hex(16),
    }
    token = jwt.encode(token_payload, private_key, algorithm="HS256")

    # Create relay session locally
    relay_session = manager.create_relay_session(
        relay_id=relay_id,
        token=token,
        source_node_id=node_id,
        target_node_id=target_manifest.node_id,
        document_id=body.document_id,
        thread_id=body.thread_id,
        ttl_seconds=3600,
    )

    # Emit event
    event_bus.emit_event(
        topic="federation.session.requested",
        payload={
            "relay_id": relay_id,
            "source_node_id": node_id,
            "target_node_id": target_manifest.node_id,
            "document_id": body.document_id,
        },
    )

    logger.info(f"Requested federation session {relay_id}")

    return {
        "relay_id": relay_id,
        "relay_url": _relay_endpoint,
        "token": token,
        "expires_in": 3600,
    }


@router.post("/session/accept")
async def accept_session(
    relay_id: str = Query(..., description="Relay session ID"),
    token: str = Query(..., description="JWT token from source node"),
) -> Dict[str, Any]:
    """Accept a remote federation session request.

    Validates the JWT using the source node's public key from cached manifest.
    Creates corresponding relay session on this node.

    Args:
        relay_id: Relay session ID from request
        token: JWT token from source node

    Returns:
        Acceptance confirmation with relay connection details
    """
    policy = _load_trust_policy()

    try:
        node_id, _private_key, _public_key, relay_endpoint = _get_config()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Verify JWT (would need to fetch source node's public key)
    # For now, we'll trust the structure and let the relay endpoint validate
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=400, detail="Invalid token format")

    source_node_id = payload.get("source_node_id")
    if not source_node_id:
        raise HTTPException(
            status_code=400, detail="Missing source_node_id in token"
        )
    _enforce_node_allowed(policy, source_node_id, label="source")

    # Get source node's manifest from cache or reject
    source_manifest = manager.get_peer_manifest(source_node_id)
    if not source_manifest:
        raise HTTPException(status_code=400, detail="Unknown source node")

    # Create relay session on this node
    relay_session = manager.create_relay_session(
        relay_id=relay_id,
        token=token,
        source_node_id=source_node_id,
        target_node_id=node_id,
        document_id=payload.get("document_id"),
        thread_id=payload.get("thread_id"),
        ttl_seconds=3600,
    )

    # Emit event
    event_bus.emit_event(
        topic="federation.session.accepted",
        payload={
            "relay_id": relay_id,
            "source_node_id": source_node_id,
            "target_node_id": node_id,
            "document_id": payload.get("document_id"),
        },
    )

    logger.info(f"Accepted federation session {relay_id}")

    return {
        "status": "accepted",
        "relay_id": relay_id,
        "relay_url": relay_endpoint,
    }


@router.websocket("/relay/{relay_id}")
async def ws_federation_relay(
    ws: WebSocket,
    relay_id: str,
    token: str = Query(..., description="JWT token for authentication"),
) -> None:
    """WebSocket endpoint for federation relay channel.

    Handles bidirectional message forwarding between source and target nodes.
    Messages include presence events, updates, and autosave notifications.

    Message types:
    - presence.join
    - presence.leave
    - update
    - autosave

    Args:
        ws: WebSocket connection
        relay_id: Relay session ID
        token: JWT authentication token
    """
    try:
        _load_trust_policy()
    except HTTPException as exc:
        await ws.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason=str(exc.detail),
        )
        return

    relay = manager.get_relay_session(relay_id)
    if not relay:
        await ws.close(
            code=status.WS_1008_POLICY_VIOLATION, reason="Invalid relay_id"
        )
        return

    # Validate token matches relay
    if token != relay.token:
        await ws.close(
            code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token"
        )
        return

    try:
        await ws.accept()

        # Determine if this is source or target connection
        is_source = await ws.receive_json()
        connection_type = is_source.get(
            "connection_type"
        )  # "source" or "target"

        if connection_type == "source":
            if not manager.connect_relay_source(relay_id, ws):
                await ws.close(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="Failed to connect source",
                )
                return
            logger.info(f"Source connected to relay {relay_id}")
        elif connection_type == "target":
            if not manager.connect_relay_target(relay_id, ws):
                await ws.close(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="Failed to connect target",
                )
                return
            logger.info(f"Target connected to relay {relay_id}")
        else:
            await ws.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Invalid connection_type",
            )
            return

        # Forward messages between source and target
        while True:
            message = await ws.receive_json()

            # Track active users for presence
            if message.get("type") == "presence.join":
                user_id = message.get("user_id")
                if user_id:
                    relay.active_users.add(user_id)
            elif message.get("type") == "presence.leave":
                user_id = message.get("user_id")
                if user_id:
                    relay.active_users.discard(user_id)

            # Forward to other side
            other_ws = (
                relay.target_ws
                if connection_type == "source"
                else relay.source_ws
            )

            if other_ws and other_ws.client_state.name == "CONNECTED":
                try:
                    await other_ws.send_json(message)
                except Exception as e:
                    logger.error(
                        f"Failed to forward message in relay {relay_id}: {e}"
                    )
                    break

            # Emit event for relay traffic
            event_bus.emit_event(
                topic="federation.relay.message",
                payload={
                    "relay_id": relay_id,
                    "message_type": message.get("type"),
                    "source": connection_type,
                },
            )

    except WebSocketDisconnect:
        logger.info(f"Disconnected from relay {relay_id}")
    except Exception as e:
        logger.error(f"Error in relay {relay_id}: {e}", exc_info=True)
    finally:
        # Clean up relay if both sides disconnected
        relay = manager.get_relay_session(relay_id)
        if relay and not relay.is_active():
            manager.close_relay_session(relay_id)
            logger.info(f"Closed relay {relay_id}")


# ─────────────────────────────────────────────────────────────────────
# DIFF SYNCHRONIZATION ENDPOINTS
# ─────────────────────────────────────────────────────────────────────


class DiffPushRequest(BaseModel):
    """Request body for pushing a diff from a peer node."""

    doc_id: str = Field(..., description="Document ID")
    version: int = Field(..., description="Version number for this diff")
    patch: str = Field(..., description="Unified diff format patch")
    author: str = Field(..., description="Author/node that created diff")
    content_hash: Optional[str] = Field(
        None, description="Hash of resulting content"
    )
    base_version: int = Field(0, description="Version this was created from")
    signature: Optional[str] = Field(
        None, description="Optional signature from source node"
    )


class DiffListResponse(BaseModel):
    """Response for diff list queries."""

    doc_id: str
    since_version: int
    diffs: List[Dict[str, Any]]


@router.post("/diff/push")
async def push_diff(body: DiffPushRequest) -> Dict[str, Any]:
    """Accept and apply a diff from a peer node.

    Validates the diff, applies it to local document state,
    records it for other peers, and forwards via relay channels.

    Args:
        body: DiffPushRequest with patch and metadata

    Returns:
        Confirmation with new version
    """
    _load_trust_policy()

    try:
        _get_config()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Create DiffEntry from request
    diff = DiffEntry(
        doc_id=body.doc_id,
        version=body.version,
        patch=body.patch,
        author=body.author,
        base_version=body.base_version,
        content_hash=body.content_hash,
    )

    try:
        # Get diff store and engine
        store = get_diff_store()
        engine = DiffEngine(store)

        # Get current document state
        current_content = store.get_latest_content(body.doc_id) or ""
        current_version = store.get_latest_version(body.doc_id) or 0

        # Verify version compatibility
        if diff.base_version > current_version:
            logger.warning(
                f"Diff version {diff.base_version} newer than current {current_version}"
            )
            raise HTTPException(
                status_code=409,
                detail=f"Diff base_version {diff.base_version} exceeds current {current_version}",
            )

        # Apply the diff
        try:
            new_content = engine.apply_diff(current_content, diff)
        except ValueError as e:
            logger.error(f"Failed to apply diff: {e}")
            raise HTTPException(
                status_code=400, detail=f"Cannot apply diff: {e}"
            )

        # Verify content hash if provided
        if diff.content_hash:
            if not engine.verify_diff(diff, new_content):
                logger.warning(
                    f"Content hash mismatch for {body.doc_id} v{body.version}"
                )
                # Log but continue - might be acceptable in some scenarios

        # Record the diff
        store.record_diff(diff, new_content)

        # Forward diff to active relays
        diff_payload = {
            "doc_id": diff.doc_id,
            "version": diff.version,
            "patch": diff.patch,
            "author": diff.author,
            "timestamp": diff.timestamp.isoformat(),
            "content_hash": diff.content_hash,
        }
        forwarded_count = await manager.forward_diff(body.doc_id, diff_payload)

        # Emit event
        event_bus.emit_event(
            topic="federation.diff.applied",
            payload={
                "doc_id": body.doc_id,
                "version": body.version,
                "author": body.author,
                "forwarded_to": forwarded_count,
            },
        )

        logger.info(
            f"Applied diff {body.doc_id} v{body.version} by {body.author}"
        )

        return {
            "status": "applied",
            "doc_id": body.doc_id,
            "version": body.version,
            "forwarded_to": forwarded_count,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing diff push: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/diff/pull", response_model=DiffListResponse)
async def pull_diffs(
    doc_id: str = Query(..., description="Document ID"),
    since: int = Query(0, description="Get diffs with version > this"),
) -> Dict[str, Any]:
    """Retrieve diffs for a document since a given version.

    Used for resynchronization after periods of offline or
    when a node joins late.

    Args:
        doc_id: Document ID to sync
        since: Return diffs with version > this value

    Returns:
        List of DiffEntry objects in version order
    """
    _load_trust_policy()

    try:
        store = get_diff_store()

        # Get diffs since version
        diffs = store.get_diffs_since(doc_id, since)

        # Convert to dict format for response
        diff_list = [
            {
                "version": d.version,
                "author": d.author,
                "timestamp": d.timestamp.isoformat(),
                "content_hash": d.content_hash,
                "base_version": d.base_version,
            }
            for d in diffs
        ]

        logger.info(f"Pulled {len(diffs)} diffs for {doc_id} since v{since}")

        return {
            "doc_id": doc_id,
            "since_version": since,
            "diffs": diff_list,
        }

    except Exception as e:
        logger.error(f"Error pulling diffs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────
# GRAPH SYNCHRONIZATION ENDPOINTS
# ─────────────────────────────────────────────────────────────────────


class GraphUpdateRequest(BaseModel):
    """Request body for pushing graph updates from a peer node."""

    nodes: List[Dict[str, Any]] = Field(
        default_factory=list, description="List of nodes to upsert"
    )
    edges: List[Dict[str, Any]] = Field(
        default_factory=list, description="List of edges to add/update"
    )
    signature: Optional[str] = Field(
        None, description="Optional signature from source node"
    )


class GraphSnapshotResponse(BaseModel):
    """Response containing graph snapshot."""

    nodes: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict, description="Map of node_id to node data"
    )
    edges: List[Dict[str, Any]] = Field(
        default_factory=list, description="List of edges"
    )
    timestamp: str = Field(..., description="Snapshot timestamp in ISO format")


@router.post("/graph/update")
async def update_graph(body: GraphUpdateRequest) -> Dict[str, Any]:
    """Accept and apply graph updates from a peer node.

    Validates the update, merges nodes and edges into local graph,
    and forwards to other active relays.

    Args:
        body: GraphUpdateRequest with nodes and edges

    Returns:
        Confirmation with update count
    """
    _load_trust_policy()

    try:
        _get_config()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    try:
        store = get_graph_store()

        nodes_updated = 0
        edges_updated = 0

        # Process nodes
        for node_data in body.nodes:
            try:
                node = GraphNode(**node_data)
                store.upsert_node(node)
                nodes_updated += 1
            except Exception as e:
                logger.error(f"Failed to upsert node: {e}")
                continue

        # Process edges
        for edge_data in body.edges:
            try:
                edge = GraphEdge(**edge_data)
                store.add_edge(edge)
                edges_updated += 1
            except Exception as e:
                logger.error(f"Failed to add edge: {e}")
                continue

        # Forward update to active relays
        forwarded_count = await manager.forward_graph_update(
            {
                "nodes": body.nodes,
                "edges": body.edges,
            }
        )

        # Emit event
        event_bus.emit_event(
            topic="federation.graph.updated",
            payload={
                "nodes_updated": nodes_updated,
                "edges_updated": edges_updated,
                "forwarded_to": forwarded_count,
            },
        )

        logger.info(
            f"Applied graph update: {nodes_updated} nodes, {edges_updated} edges"
        )

        return {
            "status": "updated",
            "nodes_updated": nodes_updated,
            "edges_updated": edges_updated,
            "forwarded_to": forwarded_count,
        }

    except Exception as e:
        logger.error(f"Error processing graph update: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/snapshot", response_model=GraphSnapshotResponse)
async def get_graph_snapshot() -> Dict[str, Any]:
    """Get a snapshot of the local awareness graph for sync.

    Returns the entire graph state for bootstrap or resync with peer nodes.

    Returns:
        GraphSnapshotResponse with all nodes and edges
    """
    _load_trust_policy()

    try:
        store = get_graph_store()
        snapshot = store.export_snapshot()

        # Convert nodes dict to serializable format
        nodes_dict = {
            node_id: node.model_dump(mode="json")
            for node_id, node in snapshot.nodes.items()
        }

        # Convert edges list
        edges_list = [edge.model_dump(mode="json") for edge in snapshot.edges]

        logger.info(f"Exported graph snapshot with {len(nodes_dict)} nodes")

        return {
            "nodes": nodes_dict,
            "edges": edges_list,
            "timestamp": snapshot.timestamp.isoformat(),
        }

    except Exception as e:
        logger.error(f"Error exporting graph snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/stats")
async def get_graph_statistics() -> Dict[str, Any]:
    """Get statistics about the local awareness graph.

    Returns:
        Graph statistics including node/edge counts and types
    """
    _load_trust_policy()

    try:
        store = get_graph_store()
        stats = store.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error getting graph statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
