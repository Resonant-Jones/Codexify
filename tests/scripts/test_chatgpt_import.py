import pytest

pytestmark = pytest.mark.xfail(
    reason="Legacy CLI migration API; superseded by backend.rag.chatgpt_migration.ingest_chatgpt_export",
    strict=False,
)

"""
Tests for ChatGPT import script.

Tests cover:
- JSON parsing and validation
- Neo4j graph import
- Chroma embeddings import
- Error handling and resilience
- Idempotency
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, call

import pytest


# Add scripts directory to path for import
SCRIPT_DIR = Path(__file__).parent.parent.parent / "scripts" / "chatgpt_import"
sys.path.insert(0, str(SCRIPT_DIR))


@pytest.fixture
def sample_chatgpt_export():
    """Sample ChatGPT export data."""
    return [
        {
            "id": "test-thread-1",
            "title": "Test Conversation",
            "create_time": 1234567890.0,
            "update_time": 1234567900.0,
            "mapping": {
                "msg-1": {
                    "id": "msg-1",
                    "message": {
                        "id": "msg-1",
                        "author": {"role": "user", "name": "User"},
                        "content": {"parts": ["Hello, how are you?"]},
                        "create_time": 1234567890.0,
                    },
                    "parent": None,
                },
                "msg-2": {
                    "id": "msg-2",
                    "message": {
                        "id": "msg-2",
                        "author": {"role": "assistant", "name": "Assistant"},
                        "content": {"parts": ["I'm doing great! How can I help you?"]},
                        "create_time": 1234567895.0,
                    },
                    "parent": "msg-1",
                },
            },
        }
    ]


@pytest.fixture
def sample_export_file(tmp_path, sample_chatgpt_export):
    """Create a temporary ChatGPT export file."""
    export_file = tmp_path / "test_export.json"
    export_file.write_text(json.dumps(sample_chatgpt_export))
    return export_file


@pytest.fixture
def mock_env(tmp_path, monkeypatch):
    """Set up mock environment variables."""
    chroma_path = tmp_path / "chroma"
    export_file = tmp_path / "test_export.json"

    monkeypatch.setenv("NEO4J_URL", "bolt://localhost:7687")
    monkeypatch.setenv("NEO4J_USER", "neo4j")
    monkeypatch.setenv("NEO4J_PASS", "test_password")
    monkeypatch.setenv("CHROMA_PATH", str(chroma_path))
    monkeypatch.setenv("CHATGPT_EXPORT_FILE", str(export_file))
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    monkeypatch.setenv("EMBED_BATCH_SIZE", "5")

    return {
        "chroma_path": chroma_path,
        "export_file": export_file,
    }


class TestTimestampNormalization:
    """Test timestamp normalization functionality."""

    def test_normalize_unix_timestamp(self):
        """Test normalizing Unix timestamp to ISO format."""
        from import_chatgpt import normalize_timestamp

        result = normalize_timestamp(1234567890)
        assert result == "2009-02-13T23:31:30"

    def test_normalize_float_timestamp(self):
        """Test normalizing float timestamp."""
        from import_chatgpt import normalize_timestamp

        result = normalize_timestamp(1234567890.5)
        assert result.startswith("2009-02-13")

    def test_normalize_iso_string(self):
        """Test normalizing ISO string."""
        from import_chatgpt import normalize_timestamp

        result = normalize_timestamp("2024-01-15T10:30:00Z")
        assert "2024-01-15" in result

    def test_normalize_none(self):
        """Test normalizing None returns current time."""
        from import_chatgpt import normalize_timestamp

        result = normalize_timestamp(None)
        assert isinstance(result, str)
        assert "T" in result  # ISO format contains 'T'

    def test_normalize_invalid(self):
        """Test normalizing invalid input returns current time."""
        from import_chatgpt import normalize_timestamp

        result = normalize_timestamp("invalid")
        assert isinstance(result, str)


class TestBatchFunction:
    """Test batching functionality."""

    def test_batch_exact_size(self):
        """Test batching with exact batch size."""
        from import_chatgpt import batch

        items = list(range(10))
        batches = list(batch(items, 5))

        assert len(batches) == 2
        assert batches[0] == [0, 1, 2, 3, 4]
        assert batches[1] == [5, 6, 7, 8, 9]

    def test_batch_uneven(self):
        """Test batching with uneven size."""
        from import_chatgpt import batch

        items = list(range(11))
        batches = list(batch(items, 5))

        assert len(batches) == 3
        assert batches[0] == [0, 1, 2, 3, 4]
        assert batches[1] == [5, 6, 7, 8, 9]
        assert batches[2] == [10]

    def test_batch_single_item(self):
        """Test batching single item."""
        from import_chatgpt import batch

        items = [1]
        batches = list(batch(items, 5))

        assert len(batches) == 1
        assert batches[0] == [1]

    def test_batch_empty(self):
        """Test batching empty list."""
        from import_chatgpt import batch

        items = []
        batches = list(batch(items, 5))

        assert len(batches) == 0


class TestLoadChatGPTExport:
    """Test ChatGPT export file loading."""

    def test_load_valid_export(self, sample_export_file):
        """Test loading valid export file."""
        from import_chatgpt import load_chatgpt_export

        result = load_chatgpt_export(str(sample_export_file))

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == "test-thread-1"
        assert result[0]["title"] == "Test Conversation"

    def test_load_single_conversation(self, tmp_path):
        """Test loading single conversation format."""
        from import_chatgpt import load_chatgpt_export

        # Create single conversation (not in array)
        single_convo = {
            "id": "single-thread",
            "title": "Single",
            "mapping": {},
        }

        file_path = tmp_path / "single.json"
        file_path.write_text(json.dumps(single_convo))

        result = load_chatgpt_export(str(file_path))

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == "single-thread"

    def test_load_nonexistent_file(self):
        """Test loading nonexistent file raises error."""
        from import_chatgpt import load_chatgpt_export

        with pytest.raises(FileNotFoundError):
            load_chatgpt_export("/nonexistent/file.json")

    def test_load_invalid_json(self, tmp_path):
        """Test loading invalid JSON raises error."""
        from import_chatgpt import load_chatgpt_export

        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("not valid json {")

        with pytest.raises(json.JSONDecodeError):
            load_chatgpt_export(str(invalid_file))


class TestNeo4jImport:
    """Test Neo4j import functionality."""

    @patch("import_chatgpt.tqdm")
    def test_import_to_neo4j_basic(self, mock_tqdm, sample_chatgpt_export):
        """Test basic Neo4j import."""
        from import_chatgpt import import_to_neo4j

        # Mock tqdm to return iterable directly
        mock_tqdm.return_value = sample_chatgpt_export

        # Mock Neo4j driver and session
        mock_session = MagicMock()
        mock_driver = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session

        threads, messages, relationships = import_to_neo4j(
            mock_driver, sample_chatgpt_export
        )

        # Verify counts
        assert threads == 1
        assert messages == 2  # Two messages in sample data
        assert relationships > 0  # At least some relationships created

        # Verify Neo4j session was used
        assert mock_session.run.called

    @patch("import_chatgpt.tqdm")
    def test_import_creates_thread_nodes(self, mock_tqdm, sample_chatgpt_export):
        """Test that thread nodes are created."""
        from import_chatgpt import import_to_neo4j

        mock_tqdm.return_value = sample_chatgpt_export

        mock_session = MagicMock()
        mock_driver = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session

        import_to_neo4j(mock_driver, sample_chatgpt_export)

        # Check that MERGE Thread was called
        calls = [str(call) for call in mock_session.run.call_args_list]
        thread_calls = [c for c in calls if "Thread" in c and "MERGE" in c]
        assert len(thread_calls) > 0

    @patch("import_chatgpt.tqdm")
    def test_import_creates_message_nodes(self, mock_tqdm, sample_chatgpt_export):
        """Test that message nodes are created."""
        from import_chatgpt import import_to_neo4j

        mock_tqdm.return_value = sample_chatgpt_export

        mock_session = MagicMock()
        mock_driver = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session

        import_to_neo4j(mock_driver, sample_chatgpt_export)

        # Check that MERGE Message was called
        calls = [str(call) for call in mock_session.run.call_args_list]
        message_calls = [c for c in calls if "Message" in c and "MERGE" in c]
        assert len(message_calls) > 0

    @patch("import_chatgpt.tqdm")
    def test_import_handles_empty_messages(self, mock_tqdm):
        """Test that empty messages are skipped."""
        from import_chatgpt import import_to_neo4j

        # Create export with empty message
        export_with_empty = [
            {
                "id": "test-thread",
                "title": "Test",
                "mapping": {
                    "empty-msg": {
                        "message": {
                            "id": "empty-msg",
                            "author": {"role": "user"},
                            "content": {"parts": []},  # Empty content
                        }
                    }
                },
            }
        ]

        mock_tqdm.return_value = export_with_empty

        mock_session = MagicMock()
        mock_driver = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session

        threads, messages, relationships = import_to_neo4j(mock_driver, export_with_empty)

        # Thread should be created, but no messages
        assert threads == 1
        assert messages == 0


class TestChromaImport:
    """Test Chroma embeddings import functionality."""

    @patch("import_chatgpt.tqdm")
    def test_import_embeddings_basic(self, mock_tqdm, sample_chatgpt_export):
        """Test basic embeddings import."""
        from import_chatgpt import import_embeddings_to_chroma

        # Mock OpenAI client
        mock_openai_client = MagicMock()
        mock_embedding_response = MagicMock()
        mock_embedding_response.data = [
            MagicMock(embedding=[0.1, 0.2, 0.3]),
            MagicMock(embedding=[0.4, 0.5, 0.6]),
        ]
        mock_openai_client.embeddings.create.return_value = mock_embedding_response

        # Mock Chroma collection
        mock_collection = MagicMock()

        # Mock tqdm
        mock_tqdm.return_value = [[("msg-1", "text1"), ("msg-2", "text2")]]

        successful, failed = import_embeddings_to_chroma(
            mock_openai_client, mock_collection, sample_chatgpt_export, batch_size=5
        )

        assert successful == 2
        assert failed == 0
        assert mock_openai_client.embeddings.create.called
        assert mock_collection.add.called

    @patch("import_chatgpt.tqdm")
    def test_import_embeddings_handles_failure(self, mock_tqdm, sample_chatgpt_export):
        """Test embeddings import handles API failures gracefully."""
        from import_chatgpt import import_embeddings_to_chroma

        # Mock OpenAI client to raise error
        mock_openai_client = MagicMock()
        mock_openai_client.embeddings.create.side_effect = Exception("API Error")

        mock_collection = MagicMock()

        # Mock tqdm
        mock_tqdm.return_value = [[("msg-1", "text1")]]

        successful, failed = import_embeddings_to_chroma(
            mock_openai_client, mock_collection, sample_chatgpt_export, batch_size=5
        )

        assert successful == 0
        assert failed > 0

    @patch("import_chatgpt.tqdm")
    def test_import_embeddings_empty_export(self, mock_tqdm):
        """Test embeddings import with no messages."""
        from import_chatgpt import import_embeddings_to_chroma

        mock_openai_client = MagicMock()
        mock_collection = MagicMock()

        empty_export = [{"id": "thread", "mapping": {}}]

        successful, failed = import_embeddings_to_chroma(
            mock_openai_client, mock_collection, empty_export, batch_size=5
        )

        assert successful == 0
        assert failed == 0


class TestFullImport:
    """Integration-style tests for full import process."""

    @patch("import_chatgpt.chromadb")
    @patch("import_chatgpt.OpenAI")
    @patch("import_chatgpt.GraphDatabase")
    def test_full_import_success(
        self,
        mock_graph_db,
        mock_openai,
        mock_chromadb,
        sample_export_file,
        mock_env,
        monkeypatch,
    ):
        """Test full import process succeeds."""
        # Set export file path
        monkeypatch.setenv("CHATGPT_EXPORT_FILE", str(sample_export_file))

        # Mock Neo4j
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_graph_db.driver.return_value = mock_driver

        # Mock OpenAI
        mock_openai_client = MagicMock()
        mock_embedding_response = MagicMock()
        mock_embedding_response.data = [
            MagicMock(embedding=[0.1] * 1536),
            MagicMock(embedding=[0.2] * 1536),
        ]
        mock_openai_client.embeddings.create.return_value = mock_embedding_response
        mock_openai.return_value = mock_openai_client

        # Mock Chroma
        mock_chroma_client = MagicMock()
        mock_collection = MagicMock()
        mock_chroma_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.PersistentClient.return_value = mock_chroma_client

        # Import and run
        from import_chatgpt import import_chatgpt

        # Should complete without raising
        import_chatgpt()

        # Verify both systems were used
        assert mock_graph_db.driver.called
        assert mock_openai.called
        assert mock_chromadb.PersistentClient.called

    @patch("import_chatgpt.GraphDatabase")
    def test_import_fails_on_missing_file(self, mock_graph_db, mock_env, monkeypatch):
        """Test import fails gracefully when export file missing."""
        # Point to non-existent file
        monkeypatch.setenv("CHATGPT_EXPORT_FILE", "/nonexistent/file.json")

        from import_chatgpt import import_chatgpt

        with pytest.raises(SystemExit) as exc_info:
            import_chatgpt()

        assert exc_info.value.code == 1

    @patch("import_chatgpt.chromadb")
    @patch("import_chatgpt.GraphDatabase")
    def test_import_continues_without_openai_key(
        self,
        mock_graph_db,
        mock_chromadb,
        sample_export_file,
        mock_env,
        monkeypatch,
    ):
        """Test import continues with Neo4j only when OpenAI key missing."""
        # Set export file but remove OpenAI key
        monkeypatch.setenv("CHATGPT_EXPORT_FILE", str(sample_export_file))
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Mock Neo4j
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_graph_db.driver.return_value = mock_driver

        from import_chatgpt import import_chatgpt

        # Should complete without raising (skips embeddings)
        import_chatgpt()

        # Neo4j should be used
        assert mock_graph_db.driver.called

        # Chroma should not be initialized (no API key)
        assert not mock_chromadb.PersistentClient.called


class TestIdempotency:
    """Test that import operations are idempotent."""

    @patch("import_chatgpt.tqdm")
    def test_repeated_import_uses_merge(self, mock_tqdm, sample_chatgpt_export):
        """Test that repeated imports use MERGE (idempotent)."""
        from import_chatgpt import import_to_neo4j

        mock_tqdm.return_value = sample_chatgpt_export

        mock_session = MagicMock()
        mock_driver = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session

        # Run import twice
        import_to_neo4j(mock_driver, sample_chatgpt_export)
        import_to_neo4j(mock_driver, sample_chatgpt_export)

        # Check that all Cypher queries use MERGE (not CREATE)
        for call_args in mock_session.run.call_args_list:
            query = call_args[0][0] if call_args[0] else ""
            # All node and relationship operations should use MERGE
            if "Thread" in query or "Message" in query or "Author" in query:
                assert "MERGE" in query or "MATCH" in query
                assert "CREATE " not in query  # Note space to avoid matching CREATE INDEX


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
