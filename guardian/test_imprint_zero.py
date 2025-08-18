import asyncio
import json
import unittest
from unittest.mock import MagicMock, mock_open, patch
import tempfile
from pathlib import Path

from guardian.imprint_zero_onboarding import ImprintZero


class TestImprintZero(unittest.TestCase):
    @patch("guardian.imprint_zero.settings")
    @patch("guardian.imprint_zero.UserManager")
    def test_prompt_loading_fallback(self, mock_user_manager, mock_settings):
        """
        Verify ImprintZero uses fallback prompts when prompt files are not found.
        """
        # Ensure the configurable path is not set for this test
        mock_settings.PROMPT_DIR_PATH = None

        # Patch 'open' to raise FileNotFoundError
        with patch("builtins.open", mock_open()) as mock_file:
            mock_file.side_effect = FileNotFoundError

            imprint = ImprintZero()

            # Assert that the fallback prompts are used
            self.assertEqual(
                imprint.system_prompt, "You are a friendly onboarding assistant."
            )
            self.assertEqual(
                imprint.question_scaffold, "Please tell me a little about yourself."
            )

    @patch("guardian.imprint_zero.settings")
    @patch("guardian.imprint_zero.UserManager")
    def test_prompt_loading_success(self, mock_user_manager, mock_settings):
        """
        Verify ImprintZero loads prompts correctly from files.
        """
        # Ensure the configurable path is not set for this test
        mock_settings.PROMPT_DIR_PATH = None

        mock_prompts = {
            "prompts/imprint_zero_system_prompt.md": "Test System Prompt",
            "prompts/imprint_zero_question_scaffold.md": "Test Question Scaffold",
        }

        # Patch 'open' to return different content based on the file path
        def mock_file_open(file, mode="r"):
            # Find which mock file is being opened
            for key, content in mock_prompts.items():
                if key in str(file):
                    return mock_open(read_data=content)()
            raise FileNotFoundError(f"File not found: {file}")

        with patch("builtins.open", mock_file_open):
            imprint = ImprintZero()
            self.assertEqual(imprint.system_prompt, "Test System Prompt")
            self.assertEqual(imprint.question_scaffold, "Test Question Scaffold")

    @patch("guardian.imprint_zero.settings")
    @patch("guardian.imprint_zero.get_memoryos_instance")
    @patch("guardian.imprint_zero.UserManager")
    def test_process_onboarding_message(
        self, mock_user_manager, mock_get_memoryos, mock_settings
    ):
        """
        Verify the onboarding message calls the LLM with the correct prompts and yields valid JSON.
        """
        mock_settings.PROMPT_DIR_PATH = None

        # Setup mock MemoryOS client
        mock_llm_client = MagicMock()
        mock_llm_client.chat_completion.return_value = "This is the AI response."
        mock_memoryos = MagicMock()
        mock_memoryos.client = mock_llm_client
        mock_get_memoryos.return_value = mock_memoryos

        imprint = ImprintZero()
        imprint.system_prompt = "SysPrompt"
        imprint.question_scaffold = "QuestionScaffold"

        user_message = "Here is my story."

        # Run the async generator
        async def run_test():
            response_generator = imprint.process_onboarding_message(1, user_message)
            response_json = await anext(response_generator)
            return json.loads(response_json)

        result = asyncio.run(run_test())

        # Assertions
        self.assertEqual(result["type"], "text")
        self.assertEqual(result["content"], "This is the AI response.")
        mock_llm_client.chat_completion.assert_called_once()
        call_args = mock_llm_client.chat_completion.call_args
        messages = call_args.kwargs["messages"]
        self.assertEqual(messages[0]["content"], "SysPrompt")
        self.assertIn("QuestionScaffold", messages[1]["content"])
        self.assertIn(user_message, messages[1]["content"])

    @patch("guardian.imprint_zero.settings")
    @patch("guardian.imprint_zero.UserManager")
    def test_end_to_end_prompt_loading(self, mock_user_manager, mock_settings):
        """
        Verify ImprintZero loads prompts from a real directory structure
        without mocking the core file I/O logic.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            prompt_dir = Path(tmpdir)

            # Create dummy prompt files in the temporary directory
            system_prompt_content = "E2E Test System Prompt"
            scaffold_content = "E2E Test Question Scaffold"
            (prompt_dir / "imprint_zero_system_prompt.md").write_text(
                system_prompt_content
            )
            (prompt_dir / "imprint_zero_question_scaffold.md").write_text(
                scaffold_content
            )

            # Point settings to our temporary directory
            mock_settings.PROMPT_DIR_PATH = str(prompt_dir)

            # Instantiate the real ImprintZero class
            imprint = ImprintZero()

            # Assert that the prompts were loaded correctly and are non-empty
            self.assertEqual(imprint.system_prompt, system_prompt_content)
            self.assertEqual(imprint.question_scaffold, scaffold_content)
            self.assertTrue(len(imprint.system_prompt) > 0)
