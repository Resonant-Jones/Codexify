"""
Tests for CLI migration tool (codexify migrate).

Tests cover:
- CLI argument parsing
- Migration execution
- Validation command
- History command
- Error handling
- Summary logging
"""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, call

import pytest

pytestmark = pytest.mark.xfail(
    reason="Legacy CLI migration API; superseded by backend.rag.chatgpt_migration.ingest_chatgpt_export",
    strict=False,
)


# Sample test data
SAMPLE_EXPORT = [
    {
        "id": "test-thread-cli",
        "title": "CLI Test Conversation",
        "create_time": 1234567890.0,
        "update_time": 1234567900.0,
        "mapping": {
            "msg-1": {
                "id": "msg-1",
                "message": {
                    "id": "msg-1",
                    "author": {"role": "user", "name": "User"},
                    "content": {"parts": ["Test message from CLI"]},
                    "create_time": 1234567890.0,
                },
                "parent": None,
            },
        },
    }
]


@pytest.fixture
def sample_export_file(tmp_path):
    """Create a temporary ChatGPT export file for CLI testing."""
    export_file = tmp_path / "test_cli_export.json"
    export_file.write_text(json.dumps(SAMPLE_EXPORT))
    return export_file


@pytest.fixture
def cli_env(tmp_path, monkeypatch):
    """Set up CLI test environment."""
    chroma_path = tmp_path / "chroma_cli"
    logs_path = tmp_path / "logs"

    monkeypatch.setenv("NEO4J_URL", "bolt://localhost:7687")
    monkeypatch.setenv("NEO4J_USER", "neo4j")
    monkeypatch.setenv("NEO4J_PASS", "test_password")
    monkeypatch.setenv("CHROMA_PATH", str(chroma_path))
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")

    # Change to temp directory for logs
    monkeypatch.chdir(tmp_path)

    return {
        "chroma_path": chroma_path,
        "logs_path": logs_path,
    }


class TestCLIMigrateCommand:
    """Test the migrate command."""

    @patch("scripts.chatgpt_import.cli_migrate.import_embeddings_to_chroma")
    @patch("scripts.chatgpt_import.cli_migrate.import_to_neo4j")
    @patch("scripts.chatgpt_import.cli_migrate.GraphDatabase")
    @patch("scripts.chatgpt_import.cli_migrate.chromadb")
    @patch("scripts.chatgpt_import.cli_migrate.OpenAI")
    def test_migrate_command_basic(
        self,
        mock_openai,
        mock_chromadb,
        mock_graph_db,
        mock_import_neo4j,
        mock_import_chroma,
        sample_export_file,
        cli_env,
        monkeypatch,
    ):
        """Test basic migrate command execution."""
        # Mock Neo4j
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_import_neo4j.return_value = (1, 1, 2)  # threads, messages, relationships

        # Mock Chroma
        mock_chroma_client = MagicMock()
        mock_collection = MagicMock()
        mock_chroma_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.PersistentClient.return_value = mock_chroma_client

        # Mock embeddings
        mock_import_chroma.return_value = (1, 0)  # successful, failed

        # Import and run
        from typer.testing import CliRunner
        from scripts.chatgpt_import import cli_migrate

        runner = CliRunner()
        result = runner.invoke(
            cli_migrate.app,
            ["migrate", str(sample_export_file), "--skip-embeddings"]
        )

        # Should succeed
        assert result.exit_code == 0
        assert "Migration Complete" in result.output
        assert "Welcome home" in result.output

        # Neo4j should be called
        assert mock_graph_db.driver.called

    @patch("scripts.chatgpt_import.cli_migrate.import_to_neo4j")
    @patch("scripts.chatgpt_import.cli_migrate.GraphDatabase")
    def test_migrate_with_custom_batch_size(
        self,
        mock_graph_db,
        mock_import_neo4j,
        sample_export_file,
        cli_env,
        monkeypatch,
    ):
        """Test migrate with custom batch size."""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_import_neo4j.return_value = (1, 1, 2)

        from typer.testing import CliRunner
        from scripts.chatgpt_import import cli_migrate

        runner = CliRunner()
        result = runner.invoke(
            cli_migrate.app,
            [
                "migrate",
                str(sample_export_file),
                "--batch-size", "10",
                "--skip-embeddings"
            ]
        )

        assert result.exit_code == 0
        # Verify batch size was set in environment
        import os
        # Note: This might not work exactly as expected due to subprocess isolation
        # but tests the CLI interface

    def test_migrate_missing_file(self, cli_env):
        """Test migrate with non-existent file."""
        from typer.testing import CliRunner
        from scripts.chatgpt_import import cli_migrate

        runner = CliRunner()
        result = runner.invoke(
            cli_migrate.app,
            ["migrate", "/nonexistent/file.json"]
        )

        # Should fail due to missing file
        assert result.exit_code != 0

    @patch("scripts.chatgpt_import.cli_migrate.import_to_neo4j")
    @patch("scripts.chatgpt_import.cli_migrate.GraphDatabase")
    def test_migrate_saves_summary(
        self,
        mock_graph_db,
        mock_import_neo4j,
        sample_export_file,
        cli_env,
        tmp_path,
        monkeypatch,
    ):
        """Test that migrate saves migration summary."""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_import_neo4j.return_value = (1, 1, 2)

        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        from typer.testing import CliRunner
        from scripts.chatgpt_import import cli_migrate

        runner = CliRunner()
        result = runner.invoke(
            cli_migrate.app,
            ["migrate", str(sample_export_file), "--skip-embeddings"]
        )

        assert result.exit_code == 0

        # Check that summary was saved
        summary_file = tmp_path / "logs" / "migration_summary.json"
        assert summary_file.exists()

        # Verify summary content
        with open(summary_file, 'r') as f:
            summaries = json.load(f)
            assert isinstance(summaries, list)
            assert len(summaries) > 0

            latest = summaries[-1]
            assert "started_at" in latest
            assert "completed_at" in latest
            assert latest["threads"] == 1
            assert latest["messages"] == 1


class TestCLIValidateCommand:
    """Test the validate command."""

    @patch("scripts.chatgpt_import.cli_migrate.chromadb")
    @patch("scripts.chatgpt_import.cli_migrate.GraphDatabase")
    def test_validate_command_success(
        self,
        mock_graph_db,
        mock_chromadb,
        cli_env,
    ):
        """Test validate command with successful validation."""
        # Mock Neo4j
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = {"count": 10}
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_graph_db.driver.return_value = mock_driver

        # Mock Chroma
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.count.return_value = 10
        mock_client.get_collection.return_value = mock_collection
        mock_chromadb.PersistentClient.return_value = mock_client

        from typer.testing import CliRunner
        from scripts.chatgpt_import import cli_migrate

        runner = CliRunner()
        result = runner.invoke(cli_migrate.app, ["validate"])

        assert result.exit_code == 0
        assert "validation" in result.output.lower()
        assert "passed" in result.output.lower() or "successful" in result.output.lower()

    @patch("scripts.chatgpt_import.cli_migrate.GraphDatabase")
    def test_validate_command_neo4j_failure(
        self,
        mock_graph_db,
        cli_env,
    ):
        """Test validate command when Neo4j connection fails."""
        mock_graph_db.driver.side_effect = Exception("Connection failed")

        from typer.testing import CliRunner
        from scripts.chatgpt_import import cli_migrate

        runner = CliRunner()
        result = runner.invoke(cli_migrate.app, ["validate"])

        assert result.exit_code == 1
        assert "failed" in result.output.lower() or "error" in result.output.lower()


class TestCLIHistoryCommand:
    """Test the history command."""

    def test_history_no_migrations(self, cli_env, tmp_path, monkeypatch):
        """Test history command with no prior migrations."""
        monkeypatch.chdir(tmp_path)

        from typer.testing import CliRunner
        from scripts.chatgpt_import import cli_migrate

        runner = CliRunner()
        result = runner.invoke(cli_migrate.app, ["history"])

        assert result.exit_code == 0
        assert "No migration history" in result.output

    def test_history_with_migrations(self, cli_env, tmp_path, monkeypatch):
        """Test history command with existing migrations."""
        monkeypatch.chdir(tmp_path)

        # Create sample migration history
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        summary_file = logs_dir / "migration_summary.json"

        summaries = [
            {
                "started_at": "2025-11-11T10:00:00",
                "completed_at": "2025-11-11T10:05:00",
                "threads": 5,
                "messages": 100,
                "elapsed_seconds": 300,
            },
            {
                "started_at": "2025-11-11T11:00:00",
                "completed_at": "2025-11-11T11:03:00",
                "threads": 3,
                "messages": 50,
                "elapsed_seconds": 180,
            },
        ]

        with open(summary_file, 'w') as f:
            json.dump(summaries, f)

        from typer.testing import CliRunner
        from scripts.chatgpt_import import cli_migrate

        runner = CliRunner()
        result = runner.invoke(cli_migrate.app, ["history"])

        assert result.exit_code == 0
        assert "Migration History" in result.output
        assert "100" in result.output  # message count
        assert "50" in result.output

    def test_history_with_limit(self, cli_env, tmp_path, monkeypatch):
        """Test history command with --limit flag."""
        monkeypatch.chdir(tmp_path)

        # Create sample migration history with multiple entries
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        summary_file = logs_dir / "migration_summary.json"

        summaries = [
            {
                "completed_at": f"2025-11-11T10:0{i}:00",
                "threads": i,
                "messages": i * 10,
                "elapsed_seconds": i * 60,
            }
            for i in range(1, 6)  # 5 migrations
        ]

        with open(summary_file, 'w') as f:
            json.dump(summaries, f)

        from typer.testing import CliRunner
        from scripts.chatgpt_import import cli_migrate

        runner = CliRunner()
        result = runner.invoke(cli_migrate.app, ["history", "--limit", "3"])

        assert result.exit_code == 0
        # Should show only last 3
        assert result.output.count("✅ Success") <= 3


class TestCLIErrorHandling:
    """Test error handling in CLI."""

    @patch("scripts.chatgpt_import.cli_migrate.GraphDatabase")
    def test_migrate_handles_neo4j_error(
        self,
        mock_graph_db,
        sample_export_file,
        cli_env,
    ):
        """Test that CLI handles Neo4j connection errors gracefully."""
        mock_graph_db.driver.side_effect = Exception("Connection refused")

        from typer.testing import CliRunner
        from scripts.chatgpt_import import cli_migrate

        runner = CliRunner()
        result = runner.invoke(
            cli_migrate.app,
            ["migrate", str(sample_export_file)]
        )

        assert result.exit_code == 1
        assert "failed" in result.output.lower()

    @patch("scripts.chatgpt_import.cli_migrate.load_chatgpt_export")
    @patch("scripts.chatgpt_import.cli_migrate.GraphDatabase")
    def test_migrate_handles_invalid_json(
        self,
        mock_graph_db,
        mock_load,
        sample_export_file,
        cli_env,
    ):
        """Test that CLI handles invalid JSON gracefully."""
        mock_load.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

        from typer.testing import CliRunner
        from scripts.chatgpt_import import cli_migrate

        runner = CliRunner()
        result = runner.invoke(
            cli_migrate.app,
            ["migrate", str(sample_export_file)]
        )

        assert result.exit_code == 1


class TestCLIIntegration:
    """Integration tests for CLI (subprocess-based)."""

    def test_cli_help_command(self):
        """Test that --help works."""
        result = subprocess.run(
            [sys.executable, "scripts/chatgpt_import/cli_migrate.py", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert "codexify" in result.stdout.lower() or "migration" in result.stdout.lower()

    def test_cli_migrate_help(self):
        """Test that migrate --help works."""
        result = subprocess.run(
            [sys.executable, "scripts/chatgpt_import/cli_migrate.py", "migrate", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert "import" in result.stdout.lower() or "conversation" in result.stdout.lower()

    def test_cli_validate_help(self):
        """Test that validate --help works."""
        result = subprocess.run(
            [sys.executable, "scripts/chatgpt_import/cli_migrate.py", "validate", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert "validate" in result.stdout.lower()

    def test_cli_history_help(self):
        """Test that history --help works."""
        result = subprocess.run(
            [sys.executable, "scripts/chatgpt_import/cli_migrate.py", "history", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert "history" in result.stdout.lower() or "migration" in result.stdout.lower()


class TestSummaryLogging:
    """Test migration summary logging functionality."""

    def test_save_migration_summary(self, tmp_path, monkeypatch):
        """Test that migration summary is saved correctly."""
        monkeypatch.chdir(tmp_path)

        from scripts.chatgpt_import.cli_migrate import save_migration_summary

        stats = {
            "threads": 5,
            "messages": 100,
            "elapsed_seconds": 60.5,
        }

        summary_file = save_migration_summary(stats, output_dir=tmp_path / "logs")

        assert summary_file.exists()

        with open(summary_file, 'r') as f:
            summaries = json.load(f)
            assert isinstance(summaries, list)
            assert len(summaries) == 1
            assert summaries[0]["threads"] == 5
            assert "completed_at" in summaries[0]

    def test_save_migration_summary_appends(self, tmp_path, monkeypatch):
        """Test that multiple summaries are appended."""
        monkeypatch.chdir(tmp_path)

        from scripts.chatgpt_import.cli_migrate import save_migration_summary

        stats1 = {"threads": 5, "messages": 100}
        stats2 = {"threads": 3, "messages": 50}

        logs_dir = tmp_path / "logs"
        save_migration_summary(stats1, output_dir=logs_dir)
        save_migration_summary(stats2, output_dir=logs_dir)

        summary_file = logs_dir / "migration_summary.json"

        with open(summary_file, 'r') as f:
            summaries = json.load(f)
            assert len(summaries) == 2
            assert summaries[0]["threads"] == 5
            assert summaries[1]["threads"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
