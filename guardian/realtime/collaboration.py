"""WebSocket-based collaborative editing manager.

Handles real-time document synchronization, presence indicators,
and broadcast of updates to multiple connected clients.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from guardian.core import event_bus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/collab")


class CollaborationManager:
    """Manages WebSocket connections for collaborative document editing.

    Maintains active connections per document and broadcasts updates
    to all connected clients. Tracks presence (join/leave) events.
    """

    def __init__(self):
        """Initialize the collaboration manager."""
        # Map of document_id -> set of active WebSocket connections
        self.active: Dict[str, Set[WebSocket]] = {}
        # Map of document_id -> set of active user IDs (for presence)
        self.presence: Dict[str, Set[str]] = {}

    async def connect(self, doc_id: str, ws: WebSocket, user_id: Optional[str] = None) -> None:
        """Register a new WebSocket connection for a document.

        Args:
            doc_id: Document ID for this collaboration session
            ws: The WebSocket connection
            user_id: Optional user ID for presence tracking
        """
        await ws.accept()

        # Initialize document if first connection
        if doc_id not in self.active:
            self.active[doc_id] = set()
            self.presence[doc_id] = set()

        self.active[doc_id].add(ws)
        if user_id:
            self.presence[doc_id].add(user_id)

        logger.info(f"Client connected to document {doc_id}. Active users: {len(self.presence[doc_id])}")

        # Broadcast presence update
        await self.broadcast(
            doc_id,
            {
                "type": "presence.join",
                "user_id": user_id,
                "active_users": list(self.presence[doc_id]),
            },
        )

    async def disconnect(self, doc_id: str, ws: WebSocket, user_id: Optional[str] = None) -> None:
        """Unregister a WebSocket connection from a document.

        Args:
            doc_id: Document ID
            ws: The WebSocket connection to remove
            user_id: Optional user ID for presence tracking
        """
        if doc_id in self.active:
            self.active[doc_id].discard(ws)

            # Remove user from presence if no more connections
            if user_id and doc_id in self.presence:
                self.presence[doc_id].discard(user_id)

            logger.info(f"Client disconnected from document {doc_id}. Active users: {len(self.presence.get(doc_id, []))}")

            # Broadcast presence update
            await self.broadcast(
                doc_id,
                {
                    "type": "presence.leave",
                    "user_id": user_id,
                    "active_users": list(self.presence.get(doc_id, [])),
                },
            )

            # Clean up empty document
            if not self.active[doc_id]:
                del self.active[doc_id]
                if doc_id in self.presence:
                    del self.presence[doc_id]

    async def broadcast(self, doc_id: str, message: Dict[str, Any]) -> None:
        """Broadcast a message to all connected clients for a document.

        Args:
            doc_id: Document ID
            message: Message dict to broadcast
        """
        if doc_id not in self.active:
            return

        # Make a copy of the set to avoid modification during iteration
        connections = list(self.active[doc_id])
        disconnected = []

        for ws in connections:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send message to client: {e}")
                disconnected.append(ws)

        # Clean up disconnected clients
        for ws in disconnected:
            await self.disconnect(doc_id, ws)

    def get_active_sessions(self) -> int:
        """Get the count of active collaboration sessions.

        Returns:
            Number of documents with active connections
        """
        return len(self.active)

    def get_session_user_count(self, doc_id: str) -> int:
        """Get the number of active users in a session.

        Args:
            doc_id: Document ID

        Returns:
            Number of active users
        """
        return len(self.presence.get(doc_id, []))


# Global collaboration manager instance
manager = CollaborationManager()


@router.websocket("/ws/{document_id}")
async def ws_collab(ws: WebSocket, document_id: str) -> None:
    """WebSocket endpoint for collaborative document editing.

    Accepts connections, broadcasts updates, and tracks presence.

    Args:
        ws: The WebSocket connection
        document_id: The document being edited
    """
    user_id: Optional[str] = None

    try:
        await manager.connect(document_id, ws, user_id)

        while True:
            # Receive update from client
            data = await ws.receive_json()

            # Extract user_id if provided in the message
            if "user_id" in data and not user_id:
                user_id = data["user_id"]
                # Update presence with actual user_id
                if document_id in manager.presence:
                    manager.presence[document_id].add(user_id)

            # Broadcast the update to all connected clients
            await manager.broadcast(
                document_id,
                {
                    "type": "update",
                    "payload": data,
                    "user_id": user_id,
                },
            )

            # Emit event for telemetry and session metrics
            try:
                event_bus.emit_event(
                    topic="collab.update",
                    payload={
                        "document_id": document_id,
                        "user_id": user_id,
                        "active_sessions": manager.get_active_sessions(),
                    },
                )
            except Exception as e:
                logger.error(f"Failed to emit collab.update event: {e}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for document {document_id}")
        await manager.disconnect(document_id, ws, user_id)
    except Exception as e:
        logger.error(f"WebSocket error for document {document_id}: {e}", exc_info=True)
        await manager.disconnect(document_id, ws, user_id)
