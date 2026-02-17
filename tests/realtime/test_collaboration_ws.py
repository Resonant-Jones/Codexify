"""Tests for WebSocket collaboration manager.

Tests cover:
- Multiple WebSocket connections per document
- Presence join/leave broadcasts
- Update propagation across clients
- Event emission
- Connection/disconnection handling
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guardian.realtime.collaboration import CollaborationManager


@pytest.fixture
def collab_manager():
    """Create a collaboration manager for testing."""
    return CollaborationManager()


@pytest.fixture
def mock_ws():
    """Create a mock WebSocket connection."""
    ws = AsyncMock()
    # Make sure these are proper AsyncMocks that return None
    ws.accept = AsyncMock(return_value=None)
    ws.send_json = AsyncMock(return_value=None)
    ws.receive_json = AsyncMock(return_value=None)
    return ws


class TestCollaborationManager:
    """Tests for CollaborationManager class."""

    @pytest.mark.asyncio
    async def test_connect_single_client(self, collab_manager, mock_ws):
        """Test connecting a single client to a document."""
        await collab_manager.connect("doc1", mock_ws, "user1")

        # Verify connection was accepted
        mock_ws.accept.assert_called_once()

        # Verify presence was broadcast
        mock_ws.send_json.assert_called()
        call_args = mock_ws.send_json.call_args
        assert call_args is not None
        message = call_args[0][0]
        assert message["type"] == "presence.join"
        assert message["user_id"] == "user1"
        assert "user1" in message["active_users"]

    @pytest.mark.asyncio
    async def test_connect_multiple_clients_same_doc(
        self, collab_manager, mock_ws
    ):
        """Test connecting multiple clients to the same document."""
        ws1 = AsyncMock()
        ws2 = AsyncMock()

        await collab_manager.connect("doc1", ws1, "user1")
        await collab_manager.connect("doc1", ws2, "user2")

        # Both WebSockets should have received presence updates
        assert ws1.send_json.call_count >= 1
        assert ws2.send_json.call_count >= 1

        # Verify active users count
        assert collab_manager.get_session_user_count("doc1") == 2

    @pytest.mark.asyncio
    async def test_disconnect_removes_client(self, collab_manager):
        """Test disconnecting a client removes it from active set."""
        ws = AsyncMock()
        await collab_manager.connect("doc1", ws, "user1")

        # Verify connected
        assert collab_manager.get_session_user_count("doc1") == 1

        # Disconnect
        await collab_manager.disconnect("doc1", ws, "user1")

        # Verify disconnected
        assert collab_manager.get_session_user_count("doc1") == 0
        assert "doc1" not in collab_manager.active

    @pytest.mark.asyncio
    async def test_disconnect_broadcasts_leave(self, collab_manager):
        """Test that disconnect broadcasts presence.leave to remaining clients."""
        ws1 = AsyncMock()
        ws2 = AsyncMock()

        await collab_manager.connect("doc1", ws1, "user1")
        await collab_manager.connect("doc1", ws2, "user2")

        # Clear previous calls
        ws1.send_json.reset_mock()
        ws2.send_json.reset_mock()

        # Disconnect user1
        await collab_manager.disconnect("doc1", ws1, "user1")

        # Verify leave was broadcast to remaining clients
        assert ws2.send_json.call_count >= 1
        call_args = ws2.send_json.call_args
        assert call_args is not None
        message = call_args[0][0]
        assert message["type"] == "presence.leave"
        assert "user1" not in message["active_users"]

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all_clients(self, collab_manager):
        """Test broadcast sends message to all connected clients."""
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws3 = AsyncMock()

        await collab_manager.connect("doc1", ws1, "user1")
        await collab_manager.connect("doc1", ws2, "user2")
        await collab_manager.connect("doc1", ws3, "user3")

        # Reset mocks to count only broadcast calls
        ws1.send_json.reset_mock()
        ws2.send_json.reset_mock()
        ws3.send_json.reset_mock()

        # Broadcast a message
        test_message = {"type": "update", "payload": {"content": "Hello"}}
        await collab_manager.broadcast("doc1", test_message)

        # Verify all clients received the message
        ws1.send_json.assert_called_with(test_message)
        ws2.send_json.assert_called_with(test_message)
        ws3.send_json.assert_called_with(test_message)

    @pytest.mark.asyncio
    async def test_broadcast_handles_disconnected_clients(self, collab_manager):
        """Test broadcast gracefully handles failed sends."""
        ws1 = AsyncMock()
        ws2 = AsyncMock()

        await collab_manager.connect("doc1", ws1, "user1")
        await collab_manager.connect("doc1", ws2, "user2")

        # Reset mocks
        ws1.send_json.reset_mock()
        ws2.send_json.reset_mock()

        # Make ws2 fail
        ws2.send_json.side_effect = Exception("Connection lost")

        # Get initial active connection count
        initial_active_connections = len(collab_manager.active.get("doc1", []))

        # Broadcast should still succeed
        test_message = {"type": "update", "payload": {"content": "Test"}}
        await collab_manager.broadcast("doc1", test_message)

        # ws1 should have been called at least once
        assert ws1.send_json.call_count >= 1

        # ws2 connection should be removed from active connections
        final_active_connections = len(collab_manager.active.get("doc1", []))
        assert final_active_connections < initial_active_connections

    @pytest.mark.asyncio
    async def test_get_active_sessions(self, collab_manager):
        """Test counting active sessions."""
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws3 = AsyncMock()

        await collab_manager.connect("doc1", ws1, "user1")
        await collab_manager.connect("doc2", ws2, "user2")
        await collab_manager.connect("doc3", ws3, "user3")

        assert collab_manager.get_active_sessions() == 3

    @pytest.mark.asyncio
    async def test_get_session_user_count(self, collab_manager):
        """Test counting active users in a session."""
        ws1 = AsyncMock()
        ws2 = AsyncMock()

        await collab_manager.connect("doc1", ws1, "user1")
        await collab_manager.connect("doc1", ws2, "user2")

        assert collab_manager.get_session_user_count("doc1") == 2
        assert collab_manager.get_session_user_count("doc_nonexistent") == 0

    @pytest.mark.asyncio
    async def test_multiple_connections_same_user(self, collab_manager):
        """Test that same user connecting multiple times is tracked correctly."""
        ws1 = AsyncMock()
        ws2 = AsyncMock()

        # Same user, different connections (e.g., multiple tabs)
        await collab_manager.connect("doc1", ws1, "user1")
        await collab_manager.connect("doc1", ws2, "user1")

        # Should only count as 1 active user (both connections count as single user)
        assert collab_manager.get_session_user_count("doc1") == 1

        # Disconnect one connection - the user is removed when any connection disconnects
        # In a production system, you might track per-connection, but this is the current behavior
        await collab_manager.disconnect("doc1", ws1, "user1")

        # User is no longer active after disconnect (current simple behavior)
        assert collab_manager.get_session_user_count("doc1") == 0

    @pytest.mark.asyncio
    async def test_isolated_documents(self, collab_manager):
        """Test that messages for one document don't go to other documents."""
        ws1 = AsyncMock()
        ws2 = AsyncMock()

        await collab_manager.connect("doc1", ws1, "user1")
        await collab_manager.connect("doc2", ws2, "user2")

        # Reset mocks
        ws1.send_json.reset_mock()
        ws2.send_json.reset_mock()

        # Broadcast to doc1
        test_message = {"type": "update", "payload": {"content": "Test"}}
        await collab_manager.broadcast("doc1", test_message)

        # Only ws1 should receive it
        ws1.send_json.assert_called_with(test_message)
        ws2.send_json.assert_not_called()


class TestCollaborationWebSocket:
    """Tests for WebSocket endpoint integration."""

    @pytest.mark.asyncio
    @patch("guardian.realtime.collaboration.manager")
    @patch("guardian.realtime.collaboration.event_bus")
    async def test_ws_endpoint_flow(self, mock_event_bus, mock_manager):
        """Test the WebSocket endpoint connection flow."""
        from guardian.realtime.collaboration import ws_collab

        mock_ws = AsyncMock()
        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_db.SessionLocal.return_value = mock_session
        mock_manager.permissions = {}
        mock_manager.connect = AsyncMock()
        mock_manager.disconnect = AsyncMock()
        mock_manager.broadcast = AsyncMock()
        mock_manager.verify_access = MagicMock(
            return_value=(True, {"can_edit": True, "can_comment": True})
        )

        # Handshake, one update, then disconnect.
        mock_ws.receive_json = AsyncMock(
            side_effect=[
                {"user_id": "user1", "token": "token-1"},
                {"type": "update", "content": "Hello"},
                Exception("WebSocketDisconnect"),
            ]
        )

        with patch("guardian.realtime.collaboration._db", mock_db):
            # Call the endpoint
            try:
                await ws_collab(mock_ws, "doc1")
            except Exception:
                pass  # Expected to raise due to disconnect

        # Verify connect was called
        mock_manager.connect.assert_called_once_with("doc1", mock_ws, "user1")

        # Verify broadcast was called for the message
        assert mock_manager.broadcast.call_count >= 1

        # Verify disconnect was called
        mock_manager.disconnect.assert_called()

    @pytest.mark.asyncio
    @patch("guardian.realtime.collaboration.manager")
    @patch("guardian.realtime.collaboration.event_bus")
    async def test_ws_endpoint_emits_events(self, mock_event_bus, mock_manager):
        """Test that WebSocket endpoint emits collab.update events."""
        from guardian.realtime.collaboration import ws_collab

        mock_ws = AsyncMock()
        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_db.SessionLocal.return_value = mock_session
        mock_manager.permissions = {}
        mock_manager.connect = AsyncMock()
        mock_manager.disconnect = AsyncMock()
        mock_manager.broadcast = AsyncMock()
        mock_manager.get_active_sessions = MagicMock(return_value=2)
        mock_manager.verify_access = MagicMock(
            return_value=(True, {"can_edit": True, "can_comment": True})
        )

        # Handshake, one update, then disconnect.
        mock_ws.receive_json = AsyncMock(
            side_effect=[
                {"user_id": "user1", "token": "token-1"},
                {"type": "update", "content": "Hello"},
                Exception("WebSocketDisconnect"),
            ]
        )

        with patch("guardian.realtime.collaboration._db", mock_db):
            # Call the endpoint
            try:
                await ws_collab(mock_ws, "doc1")
            except Exception:
                pass  # Expected to raise

        # Verify event was emitted
        assert mock_event_bus.emit_event.call_count >= 1
        call_args = mock_event_bus.emit_event.call_args
        assert call_args is not None
        assert call_args[1]["topic"] == "collab.update"
        assert call_args[1]["payload"]["document_id"] == "doc1"


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    import asyncio

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
