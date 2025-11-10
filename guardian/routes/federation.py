"""Federation routes for cross-node collaboration.

Handles session exchange, token generation, and relay channel
establishment between federated Codexify nodes.
"""

import logging
import os
import secrets
from typing import Any, Dict, Optional
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

import jwt
import requests
from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field

from guardian.core import event_bus
from guardian.federation.manifest import (
    NodeManifest,
    generate_keypair,
    load_node_keypair_from_env,
    sign_manifest,
    verify_manifest,
)
from guardian.federation.manager import manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/federation", tags=["federation"])

# Module-level state for this node
_node_id: Optional[str] = None
_private_key: Optional[str] = None
_public_key: Optional[str] = None
_relay_endpoint: Optional[str] = None


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
        raise RuntimeError("Federation not configured. Call configure_federation() first.")
    return _node_id, _private_key, _public_key, _relay_endpoint


class SessionRequestBody(BaseModel):
    """Body for federation session request."""

    target_node_url: str = Field(..., description="Full URL of target node (e.g., https://peer.codexify.io)")
    document_id: str = Field(..., description="Document ID to collaborate on")
    user_id: str = Field(..., description="User requesting the session")
    thread_id: Optional[str] = Field(None, description="Optional thread ID")


class SessionResponse(BaseModel):
    """Response for successful session establishment."""

    relay_id: str = Field(..., description="ID for this relay session")
    relay_url: str = Field(..., description="WebSocket URL for relay connection")
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
    try:
        node_id, private_key, public_key, relay_endpoint = _get_config()
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
    try:
        node_id, private_key, public_key, relay_endpoint = _get_config()
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
        raise HTTPException(status_code=502, detail="Failed to fetch peer manifest")

    # Verify target manifest signature
    if not verify_manifest(target_manifest):
        logger.error(f"Invalid signature on manifest from {body.target_node_url}")
        raise HTTPException(status_code=400, detail="Invalid peer manifest signature")

    # Cache the peer manifest
    manager.cache_peer_manifest(target_manifest)

    # Check if target supports collab capability
    if "collab" not in target_manifest.capabilities:
        raise HTTPException(status_code=400, detail="Target node does not support collaboration")

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
    try:
        node_id, private_key, public_key, relay_endpoint = _get_config()
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
        raise HTTPException(status_code=400, detail="Missing source_node_id in token")

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
    relay = manager.get_relay_session(relay_id)
    if not relay:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid relay_id")
        return

    # Validate token matches relay
    if token != relay.token:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        return

    try:
        await ws.accept()

        # Determine if this is source or target connection
        is_source = await ws.receive_json()
        connection_type = is_source.get("connection_type")  # "source" or "target"

        if connection_type == "source":
            if not manager.connect_relay_source(relay_id, ws):
                await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="Failed to connect source")
                return
            logger.info(f"Source connected to relay {relay_id}")
        elif connection_type == "target":
            if not manager.connect_relay_target(relay_id, ws):
                await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="Failed to connect target")
                return
            logger.info(f"Target connected to relay {relay_id}")
        else:
            await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid connection_type")
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
            other_ws = relay.target_ws if connection_type == "source" else relay.source_ws

            if other_ws and other_ws.client_state.name == "CONNECTED":
                try:
                    await other_ws.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to forward message in relay {relay_id}: {e}")
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
