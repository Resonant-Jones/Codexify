import asyncio
import json
import logging
from typing import AsyncGenerator
from pathlib import Path

# These imports create a dependency on other parts of the application.
# A more advanced pattern would inject these dependencies at the server level.
from guardian.core.client_factory import get_memoryos_instance
from guardian.core.config import settings

logger = logging.getLogger(__name__)

# Define the default path to the prompts directory relative to this file
DEFAULT_PROMPTS_DIR = Path(__file__).parent / "prompts"


class ImprintZero:
    """
    Handles the initial user onboarding process, including registration
    and the initial "pulse read" to establish a baseline for the user relationship.
    """

    def __init__(self):
        # In the current architecture, we instantiate dependencies directly.
        self.user_manager = UserManager()

        # Determine the prompts directory to use, defaulting if not configured.
        prompts_dir = (
            Path(settings.PROMPT_DIR_PATH)
            if settings.PROMPT_DIR_PATH
            else DEFAULT_PROMPTS_DIR
        )
        logger.info(f"Loading ImprintZero prompts from: {prompts_dir}")

        try:
            with open(prompts_dir / "imprint_zero_system_prompt.md", "r") as f:
                self.system_prompt = f.read()
            with open(prompts_dir / "imprint_zero_question_scaffold.md", "r") as f:
                self.question_scaffold = f.read()
        except FileNotFoundError as e:
            logger.error(f"Could not load ImprintZero prompts from {prompts_dir}: {e}. Using fallback defaults.")
            self.system_prompt = "You are a friendly onboarding assistant."
            self.question_scaffold = "Please tell me a little about yourself."
        self.status = "initialized"
        logger.info("ImprintZero initialized.")

    def create_initial_profile(
        self,
        username: str,
        password: str,
        narrative_style: str,
        communication_preferences: dict,
        accessibility_needs: dict,
    ) -> dict:
        """
        Handles user registration and saves the initial "imprint" to memory.
        """
        logger.info(f"Creating initial profile for user: {username}")

        # 1. Use UserManager to create the user in the database.
        # This assumes user_manager.create_user exists and returns a dict.
        user_creation_result = self.user_manager.create_user(username, password)
        if user_creation_result.get("status") != "success":
            return user_creation_result  # Return the error from UserManager

        user_id = user_creation_result["user_id"]

        # 2. Save the initial profile data using the user_manager.
        profile_data = {
            "narrative_style": narrative_style,
            "communication_preferences": communication_preferences,
            "accessibility_needs": accessibility_needs,
        }
        self.user_manager.update_user_profile(user_id, {"profile_data": profile_data})

        # 3. Save a corresponding entry in MemoryOS to mark the "imprint".
        try:
            memory = get_memoryos_instance()
            imprint_content = f"Initial imprint for user {username}. Narrative Style: {narrative_style}."
            memory.save(
                title="User Imprint Zero",
                content=imprint_content,
                tags=["imprint_zero", "onboarding", "profile"],
            )
            logger.info(f"Saved Imprint Zero to memory for user: {username}")
        except Exception as e:
            logger.error(f"Failed to save Imprint Zero to memory for {username}: {e}")

        return user_creation_result

    async def process_onboarding_message(
        self, user_id: int, message: str
    ) -> AsyncGenerator[str, None]:
        """
        Handles the conversational part of the onboarding, the "pulse read".
        This is a streaming async generator that yields JSON strings.
        """
        logger.info(f"Processing onboarding message for user_id {user_id}: '{message}'")
        try:
            # Get the memoryos instance to access its configured LLM client
            memory = get_memoryos_instance()

            # Construct a specialized prompt for the "pulse read"
            user_prompt = f"{self.question_scaffold}\n\nUser's Response: {message}"

            # Use the underlying client for a direct, controlled LLM call
            response_content = memory.client.chat_completion(
                model=memory.llm_model,  # Use the model configured in memoryos
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=1000,
            )

            yield json.dumps({"type": "text", "content": response_content})
        except Exception as e:
            logger.error(f"Error during onboarding message processing: {e}")
            error_message = "I'm having a little trouble connecting right now. Let's try that again in a moment."
            yield json.dumps({"type": "error", "content": error_message})