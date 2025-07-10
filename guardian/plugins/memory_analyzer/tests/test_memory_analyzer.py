"""
Memory Analyzer Plugin Tests
--------------------------
Test suite for memory analysis functionality.
"""

import json
import logging
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from guardian.codex_awareness import CodexAwareness
from guardian.metacognition import MetacognitionEngine
from guardian.plugins.memory_analyzer.main import MemoryAnalyzer


# Helper function to load config
def load_config():
    plugin_dir = Path(__file__).parent.parent
    with open(plugin_dir / "plugin.json", "r") as f:
        return json.load(f)["config"]


@pytest.mark.asyncio
async def test_initialization():
    config = load_config()
    codex = MagicMock(spec=CodexAwareness)
    metacognition = MagicMock(spec=MetacognitionEngine)
    analyzer = MemoryAnalyzer(config)
    analyzer.codex = codex
    analyzer.metacognition = metacognition
    assert analyzer is not None
    assert analyzer.config == config


@pytest.mark.asyncio
async def test_memory_analysis():
    config = load_config()
    codex = MagicMock(spec=CodexAwareness)
    metacognition = MagicMock(spec=MetacognitionEngine)
    analyzer = MemoryAnalyzer(config)
    analyzer.codex = codex
    analyzer.metacognition = metacognition
    test_memories = [
        {
            "id": "mem1",
            "content": "test memory 1",
            "timestamp": "2024-01-01T00:00:00Z",
            "tags": ["test"],
        },
        {
            "id": "mem2",
            "content": "test memory 2",
            "timestamp": "2024-01-02T00:00:00Z",
            "tags": ["test"],
        },
    ]
    codex.query_memory.return_value = test_memories
    result = await analyzer.analyze_memories()
    assert result is not None
    assert "patterns" in result
    assert "statistics" in result


@pytest.mark.asyncio
async def test_pattern_detection():
    config = load_config()
    codex = MagicMock(spec=CodexAwareness)
    metacognition = MagicMock(spec=MetacognitionEngine)
    analyzer = MemoryAnalyzer(config)
    analyzer.codex = codex
    analyzer.metacognition = metacognition
    test_memories = [
        {
            "id": "mem1",
            "content": "recurring pattern A",
            "timestamp": "2024-01-01T00:00:00Z",
        },
        {
            "id": "mem2",
            "content": "recurring pattern A",
            "timestamp": "2024-01-02T00:00:00Z",
        },
        {
            "id": "mem3",
            "content": "unique content",
            "timestamp": "2024-01-03T00:00:00Z",
        },
    ]
    codex.query_memory.return_value = test_memories
    patterns = await analyzer.detect_patterns(test_memories)
    assert len(patterns) > 0
    assert "recurring pattern A" in str(patterns[0])


def test_memory_statistics():
    config = load_config()
    codex = MagicMock(spec=CodexAwareness)
    metacognition = MagicMock(spec=MetacognitionEngine)
    analyzer = MemoryAnalyzer(config)
    analyzer.codex = codex
    analyzer.metacognition = metacognition
    test_memories = [
        {
            "id": "mem1",
            "content": "test content",
            "timestamp": "2024-01-01T00:00:00Z",
            "confidence": 0.8,
        },
        {
            "id": "mem2",
            "content": "test content",
            "timestamp": "2024-01-02T00:00:00Z",
            "confidence": 0.9,
        },
    ]
    stats = analyzer.calculate_statistics(test_memories)
    assert "total_memories" in stats
    assert "average_confidence" in stats
    assert stats["total_memories"] == 2
    assert abs(stats["average_confidence"] - 0.85) < 1e-6


@pytest.mark.asyncio
async def test_error_handling():
    config = load_config()
    codex = MagicMock(spec=CodexAwareness)
    metacognition = MagicMock(spec=MetacognitionEngine)
    analyzer = MemoryAnalyzer(config)
    analyzer.codex = codex
    analyzer.metacognition = metacognition
    codex.query_memory.side_effect = Exception("Test error")
    import pytest

    with pytest.raises(Exception):
        await analyzer.analyze_memories()
    metacognition.handle_error.assert_called_once()


def test_memory_filtering():
    config = load_config()
    codex = MagicMock(spec=CodexAwareness)
    metacognition = MagicMock(spec=MetacognitionEngine)
    analyzer = MemoryAnalyzer(config)
    analyzer.codex = codex
    analyzer.metacognition = metacognition
    test_memories = [
        {"id": "mem1", "content": "important memory", "tags": ["important"]},
        {"id": "mem2", "content": "regular memory", "tags": ["regular"]},
    ]
    filtered = analyzer.filter_memories(test_memories, tags=["important"])
    assert len(filtered) == 1
    assert filtered[0]["id"] == "mem1"


def test_plugin_metadata():
    config = load_config()
    codex = MagicMock(spec=CodexAwareness)
    metacognition = MagicMock(spec=MetacognitionEngine)
    analyzer = MemoryAnalyzer(config)
    analyzer.codex = codex
    analyzer.metacognition = metacognition
    metadata = analyzer.get_metadata()
    assert "name" in metadata
    assert "version" in metadata
    assert "description" in metadata
    assert "capabilities" in metadata


def test_health_check():
    config = load_config()
    codex = MagicMock(spec=CodexAwareness)
    metacognition = MagicMock(spec=MetacognitionEngine)
    analyzer = MemoryAnalyzer(config)
    analyzer.codex = codex
    analyzer.metacognition = metacognition
    health = analyzer.health_check()
    assert "status" in health
    assert "timestamp" in health
    assert health["status"] == "healthy"
