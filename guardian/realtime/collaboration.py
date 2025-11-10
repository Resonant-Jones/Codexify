"""WebSocket-based collaborative editing manager.

Handles real-time document synchronization, presence indicators,
and broadcast of updates to multiple connected clients.
Includes permission enforcement and audit logging.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status, Query
from sqlalchemy import select, and_
from sqlalchemy.orm import Session
from guardian.core import event_bus
from guardian.core.db import GuardianDB
from guardian.db.models import CollaborationPermission, CollaborationAuditLog, SharedLink

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/collab")

# Module-level database instance (will be set by guardian_api.py)
_db: GuardianDB | None = None


def configure_db(db: GuardianDB) -> None:
    """Configure the database instance for this router."""
    global _db
    _db = db


def _get_db() -> GuardianDB:
    """Get the configured database instance."""
    if _db is None:
        raise RuntimeError("Database not configured for collaboration router")
    return _db


class CollaborationManager:
    """Manages WebSocket connections for collaborative document editing.

    Maintains active connections per document and broadcasts updates
    to all connected clients. Tracks presence (join/leave) events.
    Enforces per-document permissions and logs all collaboration events.
    """

    def __init__(self):
        """Initialize the collaboration manager."""
        # Map of document_id -> set of active WebSocket connections
        self.active: Dict[str, Set[WebSocket]] = {}
        # Map of document_id -> set of active user IDs (for presence)
        self.presence: Dict[str, Set[str]] = {}
        # Map of document_id -> map of user_id -> permissions dict
        self.permissions: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def verify_access(
        self,
        doc_id: str,
        user_id: str,
        token: Optional[str],
        session: Session,
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """Verify user has access to document via token or permission.

        Args:
            doc_id: Document ID
            user_id: User ID
            token: Optional access token
            session: Database session

        Returns:
            Tuple of (is_authorized, permissions_dict)
        """
        # Check if token is a valid SharedLink
        if token:
            shared_link = session.query(SharedLink).filter(
                SharedLink.token == token,
                SharedLink.target_type == "document",
                SharedLink.target_id == doc_id,
            ).first()
            if shared_link and (shared_link.expires_at is None or shared_link.expires_at > datetime.now(timezone.utc)):
                # SharedLink allows read-only access
                return True, {"can_edit": False, "can_comment": True}

        # Check CollaborationPermission
        perm = session.query(CollaborationPermission).filter(
            CollaborationPermission.document_id == doc_id,
            CollaborationPermission.user_id == user_id,
        ).first()
        if perm:
            return True, {"can_edit": perm.can_edit, "can_comment": perm.can_comment}

        return False, None

    def log_audit_event(
        self,
        doc_id: str,
        user_id: Optional[str],
        action: str,
        payload: Optional[Dict[str, Any]],
        session: Session,
    ) -> None:
        """Log collaboration audit event to database.

        Args:
            doc_id: Document ID
            user_id: User ID (may be None for unauthenticated events)
            action: Action type (presence.join, presence.leave, update, etc.)
            payload: Action-specific data
            session: Database session
        """
        try:
            audit_log = CollaborationAuditLog(
                document_id=doc_id,
                user_id=user_id,
                action=action,
                payload=payload,
            )
            session.add(audit_log)
            session.commit()
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")

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


@router.get("/{document_id}/audit")
async def get_audit_trail(
    document_id: str,
    limit: int = Query(100, ge=1, le=1000),
) -> Dict[str, Any]:
    """Get audit trail for a collaboration session.

    Args:
        document_id: The document ID
        limit: Maximum number of entries to return (default 100, max 1000)

    Returns:
        List of audit log entries
    """
    db = _get_db()
    session = db.SessionLocal()
    try:
        logs = session.query(CollaborationAuditLog).filter(
            CollaborationAuditLog.document_id == document_id
        ).order_by(
            CollaborationAuditLog.timestamp.desc()
        ).limit(limit).all()

        return {
            "document_id": document_id,
            "total": len(logs),
            "entries": [
                {
                    "id": log.id,
                    "user_id": log.user_id,
                    "action": log.action,
                    "payload": log.payload,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                }
                for log in logs
            ],
        }
    finally:
        session.close()


@router.websocket("/ws/{document_id}")
async def ws_collab(ws: WebSocket, document_id: str, token: Optional[str] = Query(None)) -> None:
    """WebSocket endpoint for collaborative document editing.

    Requires authentication via token query parameter or authenticated user.
    Enforces per-document permissions and broadcasts updates.

    Args:
        ws: The WebSocket connection
        document_id: The document being edited
        token: Optional access token (SharedLink or session token)
    """
    user_id: Optional[str] = None
    permissions: Optional[Dict[str, Any]] = None

    try:
        # Get database instance
        db = _get_db()
        session = db.SessionLocal()

        try:
            # Receive initial handshake from client with user_id and auth token
            initial_data = await ws.receive_json()
            user_id = initial_data.get("user_id")
            client_token = initial_data.get("token") or token

            if not user_id:
                await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="user_id required")
                return

            # Verify access
            is_authorized, permissions = manager.verify_access(
                document_id, user_id, client_token, session
            )

            if not is_authorized:
                # Log access denied event
                audit_session = db.SessionLocal()
                try:
                    manager.log_audit_event(
                        document_id,
                        user_id,
                        "access_denied",
                        {"reason": "unauthorized"},
                        audit_session,
                    )
                finally:
                    audit_session.close()

                # Emit event for monitoring
                event_bus.emit_event(
                    topic="collab.access_denied",
                    payload={"document_id": document_id, "user_id": user_id},
                )
                await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="access_denied")
                return

            # Store permissions in manager
            if document_id not in manager.permissions:
                manager.permissions[document_id] = {}
            manager.permissions[document_id][user_id] = permissions

            # Connection accepted
            await ws.accept()
            await manager.connect(document_id, ws, user_id)

            # Log presence.join event
            audit_session = db.SessionLocal()
            try:
                manager.log_audit_event(
                    document_id,
                    user_id,
                    "presence.join",
                    {"can_edit": permissions.get("can_edit"), "can_comment": permissions.get("can_comment")},
                    audit_session,
                )
            finally:
                audit_session.close()

            while True:
                # Receive update from client
                data = await ws.receive_json()

                # Enforce edit permissions
                if data.get("type") == "update" and not permissions.get("can_edit"):
                    # Log permission violation and skip broadcast
                    audit_session = db.SessionLocal()
                    try:
                        manager.log_audit_event(
                            document_id,
                            user_id,
                            "update_denied",
                            {"reason": "insufficient_permissions"},
                            audit_session,
                        )
                    finally:
                        audit_session.close()
                    continue

                # Log update (hash content for audit, not full text)
                content_hash = None
                if "content" in data:
                    content_hash = hashlib.sha256(str(data["content"]).encode()).hexdigest()[:16]

                audit_session = db.SessionLocal()
                try:
                    manager.log_audit_event(
                        document_id,
                        user_id,
                        "update",
                        {"content_hash": content_hash},
                        audit_session,
                    )
                finally:
                    audit_session.close()

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

        finally:
            session.close()

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for document {document_id}")
        if user_id:
            # Log presence.leave event
            try:
                db = _get_db()
                audit_session = db.SessionLocal()
                try:
                    manager.log_audit_event(
                        document_id,
                        user_id,
                        "presence.leave",
                        {},
                        audit_session,
                    )
                finally:
                    audit_session.close()
            except Exception as e:
                logger.error(f"Failed to log presence.leave event: {e}")
        await manager.disconnect(document_id, ws, user_id)
    except Exception as e:
        logger.error(f"WebSocket error for document {document_id}: {e}", exc_info=True)
        await manager.disconnect(document_id, ws, user_id)
