import os

# Provide dummy env so importing CLI doesn't trigger Settings validation during test collection
os.environ.setdefault("GENAI_API_KEY", "test")
os.environ.setdefault("NOTION_API_KEY", "test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test")


# Lazy import to avoid import-time settings validation during test collection
def _load_cli():
    from guardian.cli.imprint_zero_cli import app as cli

    return cli


import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

logger = logging.getLogger(__name__)


@patch("guardian.cli.imprint_zero_cli.ImprintZeroCore")
def test_dump_imprint_zero_prompt_text(mock_imprint_zero: MagicMock):
    """
    Verify the CLI dump command outputs the correct text format.
    """
    # Configure the mock ImprintZero instance
    mock_instance = MagicMock()
    mock_instance.system_prompt = "Test System Prompt"
    mock_instance.question_scaffold = "Test Question Scaffold"
    mock_imprint_zero.return_value = mock_instance

    runner = CliRunner()
    result = runner.invoke(
        _load_cli(), ["imprint-zero", "dump-imprint-zero-prompt"]
    )

    assert result.exit_code == 0
    mock_imprint_zero.assert_called_once()
    assert "--- System Prompt ---" in result.output
    assert "Test System Prompt" in result.output
    assert "--- Question Scaffold ---" in result.output
    assert "Test Question Scaffold" in result.output


@patch("guardian.cli.imprint_zero_cli.ImprintZeroCore")
def test_dump_imprint_zero_prompt_json(mock_imprint_zero: MagicMock):
    """
    Verify the CLI dump command outputs the correct JSON format.
    """
    # Configure the mock ImprintZero instance
    mock_instance = MagicMock()
    mock_instance.system_prompt = "Test System Prompt"
    mock_instance.question_scaffold = "Test Question Scaffold"
    mock_imprint_zero.return_value = mock_instance

    runner = CliRunner()
    result = runner.invoke(
        _load_cli(),
        ["imprint-zero", "dump-imprint-zero-prompt", "--json-output"],
    )

    assert result.exit_code == 0
    mock_imprint_zero.assert_called_once()

    # Parse the JSON output and verify its contents
    output_data = json.loads(result.output)
    assert output_data["system_prompt"] == "Test System Prompt"
    assert output_data["question_scaffold"] == "Test Question Scaffold"


@patch("guardian.imprint_zero.settings")
@patch("guardian.imprint_zero.UserManager")
def test_cli_dump_end_to_end(
    mock_user_manager: MagicMock, mock_settings: MagicMock, tmp_path: Path
):
    """
    Verify the CLI dump command works end-to-end with a real ImprintZero instance
    reading from a temporary file system.
    """
    prompt_dir = tmp_path

    # Create dummy prompt files
    system_prompt_content = "CLI E2E System Prompt"
    scaffold_content = "CLI E2E Question Scaffold"
    (prompt_dir / "imprint_zero_system_prompt.md").write_text(
        system_prompt_content
    )
    (prompt_dir / "imprint_zero_question_scaffold.md").write_text(
        scaffold_content
    )

    # Point settings to our temporary directory
    mock_settings.PROMPT_DIR_PATH = str(prompt_dir)

    runner = CliRunner()
    result = runner.invoke(
        _load_cli(), ["imprint-zero", "dump-imprint-zero-prompt"]
    )

    assert result.exit_code == 0
    assert system_prompt_content in result.output
    assert scaffold_content in result.output


@patch("guardian.cli.imprint_zero_cli.ImprintZeroCore")
def test_cli_dump_graceful_failure(mock_imprint_zero: MagicMock):
    """
    Verify the CLI handles exceptions during ImprintZero initialization gracefully.
    """
    mock_imprint_zero.side_effect = Exception("Simulated broken config")
    runner = CliRunner()
    with pytest.raises(Exception, match="Simulated broken config"):
        runner.invoke(
            _load_cli(),
            ["imprint-zero", "dump-imprint-zero-prompt"],
            catch_exceptions=False,
        )
