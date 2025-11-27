"""Federation manager for cross-node relay sessions.

Manages lifecycle of relay channels between federated nodes,
including verification, connection establishment, and message routing.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Set

import jwt
from fastapi import WebSocket

from .manifest import NodeManifest, verify_manifest

logger = logging.getLogger(__name__)


@dataclass
class RelaySession:
    """Represents an active relay channel between nodes.

    Relays realtime collaboration messages (presence, updates, autosave)
    between two federated nodes.
    """

    relay_id: str
    token: str
    source_node_id: str
    target_node_id: str
    document_id: str
    thread_id: Optional[str] = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    expires_at: Optional[datetime] = None
    source_ws: Optional[WebSocket] = None
    target_ws: Optional[WebSocket] = None
    active_users: Set[str] = field(default_factory=set)

    def is_expired(self) -> bool:
        """Check if relay session has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    def is_active(self) -> bool:
        """Check if relay has active WebSocket connections."""
        return self.source_ws is not None and self.target_ws is not None


class FederationManager:
    """Manages federation relay sessions and cross-node coordination.

    Lifecycle:
    1. Peer A requests session exchange (POST /api/federation/session/request)
    2. Peer B receives and accepts (POST /api/federation/session/accept)
    3. Both open WebSocket connections to relay endpoint
    4. Messages are forwarded bidirectionally (presence, updates, autosave)
    5. When done, relay session is cleaned up
    """

    def __init__(self):
        """Initialize the federation manager."""
        # Map of relay_id -> RelaySession
        self.active_relays: Dict[str, RelaySession] = {}
        # Map of node_id -> cached NodeManifest
        self.peer_manifests: Dict[str, NodeManifest] = {}
        # Rate limiting: node_id -> list of request timestamps
        self.request_history: Dict[str, list[datetime]] = {}

    def create_relay_session(
        self,
        relay_id: str,
        token: str,
        source_node_id: str,
        target_node_id: str,
        document_id: str,
        thread_id: Optional[str] = None,
        ttl_seconds: int = 3600,
    ) -> RelaySession:
        """Create a new relay session.

        Args:
            relay_id: Unique identifier for this relay
            token: JWT token for verification
            source_node_id: Originating node ID
            target_node_id: Target node ID
            document_id: Document being collaborated on
            thread_id: Optional thread ID
            ttl_seconds: Time-to-live for this session (default 1 hour)

        Returns:
            New RelaySession instance
        """
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        relay = RelaySession(
            relay_id=relay_id,
            token=token,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            document_id=document_id,
            thread_id=thread_id,
            expires_at=expires_at,
        )
        self.active_relays[relay_id] = relay
        logger.info(
            f"Created relay session {relay_id}: {source_node_id} -> {target_node_id}"
        )
        return relay

    def get_relay_session(self, relay_id: str) -> Optional[RelaySession]:
        """Get a relay session by ID.

        Args:
            relay_id: The relay session ID

        Returns:
            RelaySession if found and not expired, None otherwise
        """
        relay = self.active_relays.get(relay_id)
        if relay and not relay.is_expired():
            return relay
        if relay:
            # Clean up expired relay
            del self.active_relays[relay_id]
        return None

    def connect_relay_source(self, relay_id: str, ws: WebSocket) -> bool:
        """Connect source WebSocket to relay.

        Args:
            relay_id: The relay session ID
            ws: The WebSocket connection

        Returns:
            True if connection successful, False otherwise
        """
        relay = self.get_relay_session(relay_id)
        if not relay:
            return False
        relay.source_ws = ws
        logger.info(f"Connected source WebSocket to relay {relay_id}")
        return True

    def connect_relay_target(self, relay_id: str, ws: WebSocket) -> bool:
        """Connect target WebSocket to relay.

        Args:
            relay_id: The relay session ID
            ws: The WebSocket connection

        Returns:
            True if connection successful, False otherwise
        """
        relay = self.get_relay_session(relay_id)
        if not relay:
            return False
        relay.target_ws = ws
        logger.info(f"Connected target WebSocket to relay {relay_id}")
        return True

    def close_relay_session(self, relay_id: str) -> None:
        """Close and clean up a relay session.

        Args:
            relay_id: The relay session ID
        """
        if relay_id in self.active_relays:
            relay = self.active_relays[relay_id]
            logger.info(f"Closing relay session {relay_id}")
            del self.active_relays[relay_id]

    def verify_relay_token(
        self, token: str, secret: str
    ) -> Optional[Dict[str, Any]]:
        """Verify a relay token and return its payload.

        Args:
            token: JWT token
            secret: Secret key for verification

        Returns:
            Token payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(token, secret, algorithms=["HS256"])
            return payload
        except jwt.InvalidTokenError:
            return None

    def cache_peer_manifest(self, manifest: NodeManifest) -> None:
        """Cache a peer node's manifest.

        Args:
            manifest: The NodeManifest to cache
        """
        self.peer_manifests[manifest.node_id] = manifest
        logger.info(f"Cached manifest for node {manifest.node_id}")

    def get_peer_manifest(self, node_id: str) -> Optional[NodeManifest]:
        """Get cached peer manifest.

        Args:
            node_id: The node ID

        Returns:
            Cached NodeManifest if available, None otherwise
        """
        return self.peer_manifests.get(node_id)

    def check_rate_limit(
        self, node_id: str, limit: int = 10, window_seconds: int = 60
    ) -> bool:
        """Check if node has exceeded rate limit for requests.

        Args:
            node_id: The node ID
            limit: Max requests per window
            window_seconds: Time window in seconds

        Returns:
            True if within limit, False if exceeded
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=window_seconds)

        # Get request history for this node
        if node_id not in self.request_history:
            self.request_history[node_id] = []

        # Prune old requests
        self.request_history[node_id] = [
            ts for ts in self.request_history[node_id] if ts > cutoff
        ]

        # Check limit
        if len(self.request_history[node_id]) >= limit:
            logger.warning(f"Rate limit exceeded for node {node_id}")
            return False

        # Record this request
        self.request_history[node_id].append(now)
        return True

    def get_active_relay_count(self) -> int:
        """Get count of active relay sessions.

        Returns:
            Number of active, non-expired relay sessions
        """
        return sum(
            1 for relay in self.active_relays.values() if not relay.is_expired()
        )

    async def forward_diff(
        self, doc_id: str, diff_payload: Dict[str, Any]
    ) -> int:
        """Forward a diff to all active relays for a document.

        Used to broadcast document diffs across federated nodes via
        active relay channels.

        Args:
            doc_id: Document ID
            diff_payload: Diff payload to forward (should include version, patch, etc.)

        Returns:
            Number of relays the diff was forwarded to
        """
        forwarded_count = 0

        for relay in list(self.active_relays.values()):
            if relay.is_expired():
                continue

            # Only forward to relays for this document
            if relay.document_id != doc_id:
                continue

            # Forward to both source and target
            message = {"type": "diff", "payload": diff_payload}

            for ws, side in [
                (relay.source_ws, "source"),
                (relay.target_ws, "target"),
            ]:
                if ws and hasattr(ws, "send_json"):
                    try:
                        await ws.send_json(message)
                        forwarded_count += 1
                        logger.debug(
                            f"Forwarded diff to {side} of relay {relay.relay_id}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to forward diff to {side} of relay {relay.relay_id}: {e}"
                        )

        return forwarded_count

    async def forward_graph_update(self, update_payload: Dict[str, Any]) -> int:
        """Forward a graph update to all active relays.

        Used to broadcast awareness graph updates across federated nodes via
        active relay channels.

        Args:
            update_payload: Graph update payload (should include nodes and edges)

        Returns:
            Number of relays the update was forwarded to
        """
        forwarded_count = 0

        for relay in list(self.active_relays.values()):
            if relay.is_expired():
                continue

            # Forward graph updates to all active relays (not document-specific)
            message = {"type": "graph_update", "payload": update_payload}

            for ws, side in [
                (relay.source_ws, "source"),
                (relay.target_ws, "target"),
            ]:
                if ws and hasattr(ws, "send_json"):
                    try:
                        await ws.send_json(message)
                        forwarded_count += 1
                        logger.debug(
                            f"Forwarded graph update to {side} of relay {relay.relay_id}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to forward graph update to {side} of relay {relay.relay_id}: {e}"
                        )

        return forwarded_count


# Global federation manager instance
manager = FederationManager()
