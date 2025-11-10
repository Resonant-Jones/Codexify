"""Real-time collaboration module for Guardian.

Provides WebSocket-based multi-user editing, presence indicators,
and synchronization across connected clients.
"""

from guardian.realtime.collaboration import CollaborationManager, router

__all__ = ["CollaborationManager", "router"]
