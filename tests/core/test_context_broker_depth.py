"""Tests validating ContextBroker depth modes and diagnostic retrieval."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guardian.context.broker import ContextBroker


@pytest.fixture
def mock_chatlog_db():
    """Mock database providing chat history."""
    mock = AsyncMock()
    mock.last_messages = MagicMock(return_value=["msg1", "msg2"])
    return mock


@pytest.fixture
def mock_vector_store():
    """Mock vector store for semantic search."""
    mock = AsyncMock()
    mock.search = MagicMock(return_value=[{"text": "semantic"}])
    return mock


@pytest.fixture
def mock_memory_store():
    """Mock memory store for related memory search."""
    mock = AsyncMock()
    mock.search_related = MagicMock(return_value=[{"memory": "stored"}])
    return mock


@pytest.fixture
def mock_sensors():
    """Mock sensors provider for system diagnostics."""
    mock = AsyncMock()
    mock.snapshot = MagicMock(return_value={"cpu": 5, "memory": 42})
    return mock


@pytest.fixture
def context_broker(
    mock_chatlog_db, mock_vector_store, mock_memory_store, mock_sensors
):
    """Create a ContextBroker instance with mocked dependencies."""
    return ContextBroker(
        chatlog_db=mock_chatlog_db,
        vector_store=mock_vector_store,
        memory_store=mock_memory_store,
        sensors=mock_sensors,
    )


class TestContextBrokerShallowDepth:
    """Test ContextBroker in 'shallow' depth mode."""

    @pytest.mark.asyncio
    async def test_shallow_depth_returns_only_messages(
        self, context_broker, mock_chatlog_db
    ):
        """Verify shallow mode returns only messages key."""
        context, _ = await context_broker.assemble(
            thread_id=1, query="test query", depth_mode="shallow"
        )

        # Verify structure
        assert isinstance(context, dict)
        assert "messages" in context
        assert "semantic" in context
        assert "memory" not in context
        assert "sensors" not in context

    @pytest.mark.asyncio
    async def test_shallow_depth_fetches_messages(
        self, context_broker, mock_chatlog_db
    ):
        """Verify shallow mode fetches recent messages."""
        await context_broker.assemble(
            thread_id=1, query="test query", depth_mode="shallow", n_messages=6
        )

        # Verify messages were fetched
        mock_chatlog_db.last_messages.assert_called_once_with(1, n=6)

    @pytest.mark.asyncio
    async def test_shallow_depth_empty_semantic(
        self, context_broker, mock_vector_store
    ):
        """Verify shallow mode has empty semantic results."""
        context, _ = await context_broker.assemble(
            thread_id=1, query="test query", depth_mode="shallow"
        )

        # Semantic should be present but empty for shallow
        assert context["semantic"] == []
        # Vector store should not be called for shallow depth
        mock_vector_store.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_shallow_depth_message_count(self, context_broker):
        """Verify shallow mode respects n_messages parameter."""
        await context_broker.assemble(
            thread_id=1, query="test query", depth_mode="shallow", n_messages=10
        )

        # Should have called with n=10
        context_broker.chatlog.last_messages.assert_called_once_with(1, n=10)


class TestContextBrokerNormalDepth:
    """Test ContextBroker in 'normal' depth mode."""

    @pytest.mark.asyncio
    async def test_normal_depth_includes_messages_and_semantic(
        self, context_broker
    ):
        """Verify normal mode returns messages and semantic."""
        context, _ = await context_broker.assemble(
            thread_id=1, query="test query", depth_mode="normal"
        )

        # Verify structure
        assert "messages" in context
        assert "semantic" in context
        assert "memory" not in context
        assert "sensors" not in context

    @pytest.mark.asyncio
    async def test_normal_depth_fetches_messages(
        self, context_broker, mock_chatlog_db
    ):
        """Verify normal mode fetches recent messages."""
        await context_broker.assemble(
            thread_id=1, query="test query", depth_mode="normal"
        )

        # Verify messages were fetched
        mock_chatlog_db.last_messages.assert_called_once()

    @pytest.mark.asyncio
    async def test_normal_depth_performs_semantic_search(
        self, context_broker, mock_vector_store
    ):
        """Verify normal mode performs semantic search."""
        await context_broker.assemble(
            thread_id=1, query="test query", depth_mode="normal", k_semantic=4
        )

        # Verify semantic search was performed
        mock_vector_store.search.assert_called_once_with(
            "test query", k=4, namespace="thread:1"
        )

    @pytest.mark.asyncio
    async def test_normal_depth_default_mode(
        self, context_broker, mock_vector_store
    ):
        """Verify normal is the default depth when not specified."""
        context, _ = await context_broker.assemble(
            thread_id=1, query="test query"
        )

        # Should perform semantic search (normal mode behavior)
        mock_vector_store.search.assert_called_once()
        assert "semantic" in context

    @pytest.mark.asyncio
    async def test_normal_depth_no_memory(
        self, context_broker, mock_memory_store
    ):
        """Verify normal mode does not fetch memory."""
        await context_broker.assemble(
            thread_id=1, query="test query", depth_mode="normal"
        )

        # Memory should not be called for normal depth
        mock_memory_store.search_related.assert_not_called()

    @pytest.mark.asyncio
    async def test_normal_depth_semantic_results(self, context_broker):
        """Verify normal mode returns semantic search results."""
        context, _ = await context_broker.assemble(
            thread_id=1, query="test query", depth_mode="normal"
        )

        # Should have semantic results (mocked as [{"text": "semantic"}])
        assert context["semantic"] == [{"text": "semantic"}]


class TestContextBrokerDeepDepth:
    """Test ContextBroker in 'deep' depth mode."""

    @pytest.mark.asyncio
    async def test_deep_depth_includes_messages_semantic_memory(
        self, context_broker
    ):
        """Verify deep mode returns messages, semantic, and memory."""
        context, _ = await context_broker.assemble(
            thread_id=1, query="test query", depth_mode="deep"
        )

        # Verify structure
        assert "messages" in context
        assert "semantic" in context
        assert "memory" in context
        assert "sensors" not in context

    @pytest.mark.asyncio
    async def test_deep_depth_fetches_messages(
        self, context_broker, mock_chatlog_db
    ):
        """Verify deep mode fetches recent messages."""
        await context_broker.assemble(
            thread_id=1, query="test query", depth_mode="deep"
        )

        # Verify messages were fetched
        mock_chatlog_db.last_messages.assert_called_once()

    @pytest.mark.asyncio
    async def test_deep_depth_performs_semantic_search(
        self, context_broker, mock_vector_store
    ):
        """Verify deep mode performs semantic search."""
        await context_broker.assemble(
            thread_id=1, query="test query", depth_mode="deep"
        )

        # Verify semantic search was performed
        # Note: In deep mode, vector store is called twice (semantic + memory via MemoryOSRetriever)
        assert mock_vector_store.search.call_count >= 1
        # First call should be for semantic search
        mock_vector_store.search.assert_any_call(
            "test query", k=4, namespace="thread:1"
        )

    @pytest.mark.asyncio
    async def test_deep_depth_searches_memory(
        self, context_broker, mock_vector_store
    ):
        """Verify deep mode searches memory via MemoryOSRetriever."""
        await context_broker.assemble(
            thread_id=1, query="test query", depth_mode="deep", k_memory=5
        )

        # Verify memory search was performed via MemoryOSRetriever (uses vector_store)
        # Vector store should be called twice: once for semantic (k=4), once
        # for memory candidate pool k=max(5*3, 5+5)=15.
        assert mock_vector_store.search.call_count == 2
        mock_vector_store.search.assert_any_call(
            "test query", k=15, namespace="thread:1"
        )

    @pytest.mark.asyncio
    async def test_deep_depth_memory_results(self, context_broker):
        """Verify deep mode returns memory search results via MemoryOSRetriever."""
        context, _ = await context_broker.assemble(
            thread_id=1, query="test query", depth_mode="deep"
        )

        # Should have memory results with MemoryOSRetriever schema: {text, metadata, score}
        # Vector store returns [{"text": "semantic"}], MemoryOSRetriever normalizes it
        assert "memory" in context
        assert len(context["memory"]) > 0
        # Verify normalized schema
        assert "text" in context["memory"][0]
        assert "metadata" in context["memory"][0]
        assert "score" in context["memory"][0]

    @pytest.mark.asyncio
    async def test_deep_depth_no_sensors(self, context_broker, mock_sensors):
        """Verify deep mode does not include sensors."""
        await context_broker.assemble(
            thread_id=1, query="test query", depth_mode="deep"
        )

        # Sensors should not be called for deep depth
        mock_sensors.snapshot.assert_not_called()

    @pytest.mark.asyncio
    async def test_deep_depth_all_results_present(self, context_broker):
        """Verify deep mode returns all required context components."""
        context, _ = await context_broker.assemble(
            thread_id=1, query="test query", depth_mode="deep"
        )

        # All three components should be present
        assert "messages" in context
        assert len(context["messages"]) > 0
        assert "semantic" in context
        assert len(context["semantic"]) > 0
        assert "memory" in context
        assert len(context["memory"]) > 0


class TestContextBrokerDiagnosticDepth:
    """Test ContextBroker in 'diagnostic' depth mode."""

    @pytest.mark.asyncio
    async def test_diagnostic_depth_includes_all_components(
        self, context_broker
    ):
        """Verify diagnostic mode returns all context components including sensors."""
        context, _ = await context_broker.assemble(
            thread_id=1, query="test query", depth_mode="diagnostic"
        )

        # Verify structure - should have all keys
        assert "messages" in context
        assert "semantic" in context
        assert "memory" in context
        assert "sensors" in context

    @pytest.mark.asyncio
    async def test_diagnostic_depth_fetches_messages(
        self, context_broker, mock_chatlog_db
    ):
        """Verify diagnostic mode fetches recent messages."""
        await context_broker.assemble(
            thread_id=1, query="test query", depth_mode="diagnostic"
        )

        # Verify messages were fetched
        mock_chatlog_db.last_messages.assert_called_once()

    @pytest.mark.asyncio
    async def test_diagnostic_depth_performs_semantic_search(
        self, context_broker, mock_vector_store
    ):
        """Verify diagnostic mode performs semantic search."""
        await context_broker.assemble(
            thread_id=1, query="test query", depth_mode="diagnostic"
        )

        # Verify semantic search was performed
        # Note: In diagnostic mode, vector store is called twice (semantic + memory via MemoryOSRetriever)
        assert mock_vector_store.search.call_count >= 1
        mock_vector_store.search.assert_any_call(
            "test query", k=4, namespace="thread:1"
        )

    @pytest.mark.asyncio
    async def test_diagnostic_depth_searches_memory(
        self, context_broker, mock_vector_store
    ):
        """Verify diagnostic mode searches memory via MemoryOSRetriever."""
        await context_broker.assemble(
            thread_id=1, query="test query", depth_mode="diagnostic"
        )

        # Verify memory search was performed via MemoryOSRetriever (uses vector_store)
        # Vector store called twice: semantic + memory
        assert mock_vector_store.search.call_count >= 1

    @pytest.mark.asyncio
    async def test_diagnostic_depth_snapshots_sensors(
        self, context_broker, mock_sensors
    ):
        """Verify diagnostic mode snapshots sensors."""
        await context_broker.assemble(
            thread_id=1, query="test query", depth_mode="diagnostic"
        )

        # Verify sensors were snapshot
        mock_sensors.snapshot.assert_called_once()

    @pytest.mark.asyncio
    async def test_diagnostic_depth_sensor_results(self, context_broker):
        """Verify diagnostic mode returns sensor snapshot results."""
        context, _ = await context_broker.assemble(
            thread_id=1, query="test query", depth_mode="diagnostic"
        )

        # Should have sensor results (mocked as {"cpu": 5, "memory": 42})
        assert context["sensors"] == {"cpu": 5, "memory": 42}
        assert context["sensors"]["cpu"] == 5
        assert context["sensors"]["memory"] == 42

    @pytest.mark.asyncio
    async def test_diagnostic_depth_all_results_present(self, context_broker):
        """Verify diagnostic mode returns all context components."""
        context, _ = await context_broker.assemble(
            thread_id=1, query="test query", depth_mode="diagnostic"
        )

        # All components should be present and populated
        assert "messages" in context and len(context["messages"]) > 0
        assert "semantic" in context and len(context["semantic"]) > 0
        assert "memory" in context and len(context["memory"]) > 0
        assert "sensors" in context and len(context["sensors"]) > 0


class TestContextBrokerParameterization:
    """Test ContextBroker parameter handling."""

    @pytest.mark.asyncio
    async def test_custom_n_messages(self, context_broker, mock_chatlog_db):
        """Verify custom n_messages parameter is respected."""
        await context_broker.assemble(
            thread_id=1, query="test query", depth_mode="normal", n_messages=15
        )

        # Verify the parameter was passed
        mock_chatlog_db.last_messages.assert_called_once_with(1, n=15)

    @pytest.mark.asyncio
    async def test_custom_k_semantic(self, context_broker, mock_vector_store):
        """Verify custom k_semantic parameter is respected."""
        await context_broker.assemble(
            thread_id=1, query="test query", depth_mode="normal", k_semantic=10
        )

        # Verify the parameter was passed
        mock_vector_store.search.assert_called_once_with(
            "test query", k=10, namespace="thread:1"
        )

    @pytest.mark.asyncio
    async def test_custom_k_memory(self, context_broker, mock_vector_store):
        """Verify custom k_memory parameter is respected."""
        await context_broker.assemble(
            thread_id=1, query="test query", depth_mode="deep", k_memory=8
        )

        # Verify the parameter was passed to MemoryOSRetriever (via vector_store.search)
        # Should use candidate pool k=max(8*3, 8+5)=24 for memory search
        mock_vector_store.search.assert_any_call(
            "test query", k=24, namespace="thread:1"
        )

    @pytest.mark.asyncio
    async def test_depth_case_insensitive(
        self, context_broker, mock_vector_store
    ):
        """Verify depth parameter is case-insensitive."""
        await context_broker.assemble(
            thread_id=1, query="test query", depth_mode="NORMAL"
        )

        # Should still perform semantic search (normal mode)
        mock_vector_store.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_depth_whitespace_trimmed(
        self, context_broker, mock_vector_store
    ):
        """Verify depth parameter whitespace is trimmed."""
        await context_broker.assemble(
            thread_id=1, query="test query", depth_mode="  normal  "
        )

        # Should still perform semantic search (normal mode)
        mock_vector_store.search.assert_called_once()


class TestContextBrokerErrorHandling:
    """Test ContextBroker error handling and resilience."""

    @pytest.mark.asyncio
    async def test_message_fetch_error_graceful(
        self, context_broker, mock_chatlog_db
    ):
        """Verify message fetch errors are handled gracefully."""
        mock_chatlog_db.last_messages.side_effect = Exception("DB error")

        context, _ = await context_broker.assemble(
            thread_id=1, query="test query", depth_mode="normal"
        )

        # Should still return a result with empty messages
        assert "messages" in context
        assert context["messages"] == []

    @pytest.mark.asyncio
    async def test_semantic_search_error_graceful(
        self, context_broker, mock_vector_store
    ):
        """Verify semantic search errors are handled gracefully."""
        mock_vector_store.search.side_effect = Exception("Vector store error")

        context, _ = await context_broker.assemble(
            thread_id=1, query="test query", depth_mode="normal"
        )

        # Should still return a result with empty semantic
        assert "semantic" in context
        assert context["semantic"] == []

    @pytest.mark.asyncio
    async def test_memory_search_error_graceful(
        self, mock_chatlog_db, mock_sensors
    ):
        """Verify memory search errors are handled gracefully."""
        # Create a vector_store that fails for memory search (second call)
        from unittest.mock import MagicMock

        error_vector_store = MagicMock()
        call_count = [0]

        def search_side_effect(query, k, namespace=None):
            call_count[0] += 1
            if call_count[0] == 1:  # First call (semantic) succeeds
                return [{"text": "semantic"}]
            else:  # Second call (memory) fails
                raise Exception("Memory retriever error")

        error_vector_store.search = MagicMock(side_effect=search_side_effect)

        broker = ContextBroker(
            chatlog_db=mock_chatlog_db,
            vector_store=error_vector_store,
            memory_store=None,
            sensors=mock_sensors,
        )

        context, _ = await broker.assemble(
            thread_id=1, query="test query", depth_mode="deep"
        )

        # Should still return a result with empty memory (MemoryOSRetriever failed, no fallback)
        assert "memory" in context
        assert context["memory"] == []

    @pytest.mark.asyncio
    async def test_sensor_snapshot_error_graceful(
        self, context_broker, mock_sensors
    ):
        """Verify sensor snapshot errors are handled gracefully."""
        mock_sensors.snapshot.side_effect = Exception("Sensor error")

        context, _ = await context_broker.assemble(
            thread_id=1, query="test query", depth_mode="diagnostic"
        )

        # Should still return a result with empty sensors
        assert "sensors" in context
        assert context["sensors"] == {}

    @pytest.mark.asyncio
    async def test_multiple_errors_graceful(
        self, context_broker, mock_chatlog_db, mock_vector_store
    ):
        """Verify multiple errors are handled gracefully."""
        mock_chatlog_db.last_messages.side_effect = Exception("DB error")
        mock_vector_store.search.side_effect = Exception("Vector error")

        context, _ = await context_broker.assemble(
            thread_id=1, query="test query", depth_mode="normal"
        )

        # Should still return a result with both empty
        assert "messages" in context and context["messages"] == []
        assert "semantic" in context and context["semantic"] == []


class TestContextBrokerOptionalDependencies:
    """Test ContextBroker with optional dependencies missing."""

    @pytest.mark.asyncio
    async def test_without_memory_store(
        self, mock_chatlog_db, mock_vector_store, mock_sensors
    ):
        """Verify deep mode works without memory store."""
        broker = ContextBroker(
            chatlog_db=mock_chatlog_db,
            vector_store=mock_vector_store,
            memory_store=None,
            sensors=mock_sensors,
        )

        context, _ = await broker.assemble(
            thread_id=1, query="test query", depth_mode="deep"
        )

        # Should have empty memory
        assert context["memory"] == []

    @pytest.mark.asyncio
    async def test_without_sensors(
        self, mock_chatlog_db, mock_vector_store, mock_memory_store
    ):
        """Verify diagnostic mode works without sensors."""
        broker = ContextBroker(
            chatlog_db=mock_chatlog_db,
            vector_store=mock_vector_store,
            memory_store=mock_memory_store,
            sensors=None,
        )

        context, _ = await broker.assemble(
            thread_id=1, query="test query", depth_mode="diagnostic"
        )

        # Should have empty sensors
        assert context["sensors"] == {}

    @pytest.mark.asyncio
    async def test_without_optional_dependencies(
        self, mock_chatlog_db, mock_vector_store
    ):
        """Verify all modes work without optional dependencies."""
        broker = ContextBroker(
            chatlog_db=mock_chatlog_db,
            vector_store=mock_vector_store,
            memory_store=None,
            sensors=None,
        )

        # Test all depths
        for depth in ["shallow", "normal", "deep", "diagnostic"]:
            context, _ = await broker.assemble(
                thread_id=1, query="test query", depth_mode=depth
            )

            # Should always return a dict
            assert isinstance(context, dict)
            assert "messages" in context


class TestContextBrokerIntegration:
    """Integration tests for ContextBroker."""

    @pytest.mark.asyncio
    async def test_full_diagnostic_workflow(self, context_broker):
        """Test a complete diagnostic workflow."""
        thread_id = 1
        query = "What is the status?"

        context, _ = await context_broker.assemble(
            thread_id=thread_id,
            query=query,
            depth_mode="diagnostic",
            n_messages=10,
            k_semantic=5,
            k_memory=3,
        )

        # Verify all components are present
        assert context["messages"] == ["msg1", "msg2"]
        assert context["semantic"] == [{"text": "semantic"}]
        # Memory now uses MemoryOSRetriever with normalized schema
        assert len(context["memory"]) > 0
        assert "text" in context["memory"][0]
        assert "metadata" in context["memory"][0]
        assert "score" in context["memory"][0]
        assert context["sensors"] == {"cpu": 5, "memory": 42}

    @pytest.mark.asyncio
    async def test_progressive_depth_expansion(self, context_broker):
        """Test that each depth level includes previous depth components."""
        thread_id = 1
        query = "test"

        # Test shallow
        shallow, _ = await context_broker.assemble(
            thread_id=thread_id, query=query, depth_mode="shallow"
        )
        assert "messages" in shallow

        # Test normal - should have everything from shallow plus semantic
        normal, _ = await context_broker.assemble(
            thread_id=thread_id, query=query, depth_mode="normal"
        )
        assert "messages" in normal
        assert "semantic" in normal

        # Test deep - should have everything from normal plus memory
        deep, _ = await context_broker.assemble(
            thread_id=thread_id, query=query, depth_mode="deep"
        )
        assert "messages" in deep
        assert "semantic" in deep
        assert "memory" in deep

        # Test diagnostic - should have everything plus sensors
        diagnostic, _ = await context_broker.assemble(
            thread_id=thread_id, query=query, depth_mode="diagnostic"
        )
        assert "messages" in diagnostic
        assert "semantic" in diagnostic
        assert "memory" in diagnostic
        assert "sensors" in diagnostic
