import json
import unittest
from unittest.mock import MagicMock, patch

import tempfile
from pathlib import Path
from click.testing import CliRunner

from guardian.cli import cli


class TestCli(unittest.TestCase):
    @patch("guardian.cli.ImprintZero")
    def test_dump_imprint_zero_prompt_text(self, mock_imprint_zero):
        """
        Verify the CLI dump command outputs the correct text format.
        """
        # Configure the mock ImprintZero instance
        mock_instance = MagicMock()
        mock_instance.system_prompt = "Test System Prompt"
        mock_instance.question_scaffold = "Test Question Scaffold"
        mock_imprint_zero.return_value = mock_instance

        runner = CliRunner()
        result = runner.invoke(cli, ["dump-imprint-zero-prompt"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("--- System Prompt ---", result.output)
        self.assertIn("Test System Prompt", result.output)
        self.assertIn("--- Question Scaffold ---", result.output)
        self.assertIn("Test Question Scaffold", result.output)

    @patch("guardian.cli.ImprintZero")
    def test_dump_imprint_zero_prompt_json(self, mock_imprint_zero):
        """
        Verify the CLI dump command outputs the correct JSON format.
        """
        # Configure the mock ImprintZero instance
        mock_instance = MagicMock()
        mock_instance.system_prompt = "Test System Prompt"
        mock_instance.question_scaffold = "Test Question Scaffold"
        mock_imprint_zero.return_value = mock_instance

        runner = CliRunner()
        result = runner.invoke(cli, ["dump-imprint-zero-prompt", "--json-output"])

        self.assertEqual(result.exit_code, 0)

        # Parse the JSON output and verify its contents
        output_data = json.loads(result.output)
        self.assertEqual(output_data["system_prompt"], "Test System Prompt")
        self.assertEqual(output_data["question_scaffold"], "Test Question Scaffold")

    @patch("guardian.imprint_zero.settings")
    @patch("guardian.imprint_zero.UserManager")
    def test_cli_dump_end_to_end(self, mock_user_manager, mock_settings):
        """
        Verify the CLI dump command works end-to-end with a real ImprintZero instance
        reading from a temporary file system.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            prompt_dir = Path(tmpdir)

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
            result = runner.invoke(cli, ["dump-imprint-zero-prompt"])

            self.assertEqual(result.exit_code, 0)
            self.assertIn(system_prompt_content, result.output)
            self.assertIn(scaffold_content, result.output)

    @patch("guardian.cli.ImprintZero")
    def test_cli_dump_graceful_failure(self, mock_imprint_zero):
        """
        Verify the CLI handles exceptions during ImprintZero initialization gracefully.
        """
        mock_imprint_zero.side_effect = Exception("Simulated broken config")
        runner = CliRunner()
        result = runner.invoke(cli, ["dump-imprint-zero-prompt"])

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Error: Failed to load ImprintZero.", result.output)
        self.assertIn("Simulated broken config", result.output)