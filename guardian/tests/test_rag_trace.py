from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from guardian.context.broker import ContextBroker
from guardian.routes.chat import _rag_traces, get_latest_rag_trace


@pytest.mark.asyncio
async def test_context_broker_returns_trace():
    """Verify ContextBroker returns a trace with expected structure."""
    mock_vector = MagicMock()
    mock_vector.search.return_value = [
        {
            "id": "doc1",
            "text": "snippet1",
            "score": 0.9,
            "metadata": {"filename": "test.txt"},
        }
    ]

    mock_settings = MagicMock()
    mock_settings.GUARDIAN_ENABLE_GRAPH_CONTEXT = True

    broker = ContextBroker(MagicMock(), mock_vector, settings=mock_settings)

    # Mock graph context
    with patch.object(
        broker, "_get_graph_context", new_callable=AsyncMock
    ) as mock_graph:
        mock_graph.return_value = [
            {"message_id": "msg1", "kind": "UserNode", "text": "graph snippet"}
        ]

        context, trace = await broker.assemble(1, "query", depth="normal")

        assert "documents" in trace
        assert "graph" in trace
        assert len(trace["documents"]) == 1
        assert trace["documents"][0]["id"] == "doc1"
        assert trace["documents"][0]["title"] == "test.txt"
        assert trace["documents"][0]["score"] == 0.9
        assert len(trace["graph"]) == 1
        assert trace["graph"][0]["node_id"] == "msg1"


def test_debug_endpoint_returns_trace():
    """Verify debug endpoint returns stored trace."""
    _rag_traces.clear()
    _rag_traces[123] = {"documents": [], "graph": []}

    result = get_latest_rag_trace(123)
    assert result.get("documents") == []
    assert result.get("graph") == []


def test_debug_endpoint_empty_when_missing():
    """Verify debug endpoint returns empty structure for missing trace."""
    _rag_traces.clear()
    result = get_latest_rag_trace(999)
    assert result.get("documents") == []
    assert result.get("graph") == []
