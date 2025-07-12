# Guardian Prompt Engineering

This directory contains the core prompt assets that define the Guardian's persona and interaction rituals. These files are the "soul" of the AI.

## Files

- **`imprint_zero_system_prompt.md`**: This is the master system prompt for the initial onboarding conversation. It sets the tone, purpose, and empathetic stance of the Guardian during its first-ever interaction with the user.

- **`imprint_zero_question_scaffold.md`**: This contains the initial message and question the Guardian uses to begin the "pulse read." It's the conversational entry point for the Imprint Zero ritual.

## How to Edit and Version Prompts

1.  **Branch First**: Never edit directly on `main`. Create a new branch for prompt changes (e.g., `feature/refine-onboarding-tone`).
2.  **Make Your Changes**: Edit the markdown files as needed.
3.  **Verify with Tests**: The most critical step. The CI pipeline runs `pytest`, which executes end-to-end tests in `guardian/test_imprint_zero.py` and `guardian/test_cli.py`. These tests use a real temporary file system (`tempfile`) to load your prompt files and verify the `ImprintZero` class behaves as expected. **If you change the prompt file names or the core loading logic, you MUST update these tests.**
4.  **Verify with CLI**: Use the command `python -m guardian.cli dump-imprint-zero-prompt` to manually inspect that your changes are loaded correctly by the live application code.
5.  **Commit with Clarity**: Your commit message should explain the *why* behind the prompt change (e.g., "refine: make Imprint Zero prompt more curious").
6.  **Merge and Tag**: Once the CI tests pass and your changes are approved, merge them. For significant persona shifts, consider creating a new version tag.

---

**Testing Philosophy**: We treat prompt files as critical configuration. Therefore, we prefer end-to-end tests that validate the real file loading and parsing behavior over extensive mocking. This ensures that the contract between the code and its prompt assets is always honored.