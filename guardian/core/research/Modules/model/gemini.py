import os

import google.generativeai as genai
from dotenv import load_dotenv

try:
    from crawl4ai import LLMConfig
except ImportError:  # pragma: no cover - fallback for older crawl4ai versions
    from dataclasses import dataclass

    @dataclass
    class LLMConfig:
        provider: str
        api_token: str | None = None


from .model import Model


class Gemini(Model):
    def __init__(self, model):
        load_dotenv()
        self.api_key = os.getenv("GEMINI_API")
        self.model = model
        # Configure Gemini SDK
        genai.configure(api_key=self.api_key)
        # Create a chat session (for multi-turn)
        self.session = genai.ChatSession(model=model)

    def clear_message(self):
        """Clears the chat session."""
        self.session = genai.ChatSession(model=self.model)

    def set_api(self, api):
        self.api = api

    def completion(self, query: str):
        """Send a message and return the response text."""
        response = self.session.send_message(query)
        # If response is a list of candidates, return the first one's text
        if hasattr(response, "text"):
            return response.text
        elif (
            isinstance(response, list)
            and len(response) > 0
            and hasattr(response[0], "text")
        ):
            return response[0].text
        else:
            return str(response)

    def reset(self):
        """Reset chat session."""
        self.session = genai.ChatSession(model=self.model)

    def add_system_instruction(self, instruction: str):
        # System instructions in Gemini SDK may require config object
        # See https://ai.google.dev/docs/system-instructions for updates
        pass  # Placeholder (implement as needed)

    def get_llm_config(self) -> LLMConfig:
        return LLMConfig(provider="gemini/" + self.model, api_token=self.api_key)

    def get_model(self):
        return self.model
