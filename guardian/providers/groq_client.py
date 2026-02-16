# guardian/providers/groq_client.py

import json
import os
from typing import Iterator

import requests

from guardian.config import settings
from guardian.core.egress import EgressDeniedError, assert_egress_allowed

# Streaming-capable Groq Chat client
# Read from settings if present, otherwise use sensible defaults.
# Groq uses an OpenAI-compatible base path: https://api.groq.com/openai/v1
GROQ_API_URL = getattr(
    settings,
    "GROQ_API_URL",
    "https://api.groq.com/openai/v1/chat/completions",
)
# Do NOT require this at import-time; it may be populated by dotenv later.
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


class GroqChatClient:
    def __init__(
        self, api_url: str = GROQ_API_URL, api_key: str = GROQ_API_KEY
    ):
        self.api_url = api_url
        self.api_key = api_key

    def __call__(
        self, prompt: str, model: str = "llama-3.1-70b-versatile"
    ) -> str:
        """Synchronous call to Groq chat completions."""
        try:
            assert_egress_allowed("groq")
        except EgressDeniedError as exc:
            raise RuntimeError(str(exc)) from exc
        model_name = model.split(":", 1)[-1]
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        resp = requests.post(
            self.api_url, headers=headers, json=body, timeout=60
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def stream(
        self, prompt: str, model: str = "llama-3.1-70b-versatile"
    ) -> Iterator[str]:
        """Stream tokens from Groq chat completions via SSE."""
        try:
            assert_egress_allowed("groq")
        except EgressDeniedError as exc:
            raise RuntimeError(str(exc)) from exc
        model_name = model.split(":", 1)[-1]
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            "temperature": 0.2,
        }
        with requests.post(
            self.api_url, headers=headers, json=body, timeout=60, stream=True
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                decoded = line.decode("utf-8")
                # lines are prefixed with 'data: '
                if not decoded.startswith("data: "):
                    continue
                content = decoded[len("data: ") :]
                if content == "[DONE]":
                    break
                try:
                    chunk = json.loads(content)
                    delta = chunk["choices"][0].get("delta", {})
                    token = delta.get("content")
                    if token:
                        yield token
                except json.JSONDecodeError:
                    continue


def get_groq_chat() -> GroqChatClient | None:
    """Create a Groq client lazily using the latest env/settings.
    Returns None if no API key is configured.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    try:
        assert_egress_allowed("groq")
    except EgressDeniedError:
        return None
    api_url = getattr(settings, "GROQ_API_URL", GROQ_API_URL)
    return GroqChatClient(api_url=api_url, api_key=api_key)


__all__ = ["GroqChatClient", "get_groq_chat"]
