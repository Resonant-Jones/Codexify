from dotenv import load_dotenv
from openai import OpenAI

from .model import Model

try:
    from crawl4ai import LLMConfig
except ImportError:  # pragma: no cover - fallback for older crawl4ai versions
    from dataclasses import dataclass

    @dataclass
    class LLMConfig:
        provider: str
        api_token: str | None = None


import os


class OpenAI(Model):
    def __init__(self, model: str = "", api_key: str = ""):
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = model
        self.client = OpenAI(
            api_key=self.api_key,
        )
        self.messages = []

    def set_api(self, api_key: str):
        self.api_key = api_key

    def completion(self, query):
        self._add_message(query)
        response = self.client.chat.completions.create(
            model=self.model, messages=self.messages, stream=False
        )
        return response.choices[0].message.content

    def add_system_instructuion(self, instruction: str):
        pass

    def get_llm_config(self):
        return LLMConfig(provider="openai/" + self.model, api_token=self.api_key)

    def get_client(self):
        return self.client

    def get_model(self):
        return self.model

    def clear_message(self):
        self.messages = []

    def _add_message(self, message, role="use"):
        self.messages.append({"role": "user", "content": message})
