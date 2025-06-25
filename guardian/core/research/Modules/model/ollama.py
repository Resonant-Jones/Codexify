from ollama import chat
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


class Ollama(Model):
    def __init__(self, model: str):
        self.model = model
        self.messages = []

    def set_api(self, api):
        """
        no need to do anything
        """
        return

    def completion(self, message: str, stream: str = False):
        self._append_message(message=message, role="user")
        msg_cache = ""
        if stream == False:
            res = chat(model=self.model, messages=self.messages, stream=False)
            # Handle both string and dict responses for compatibility
            if isinstance(res, dict):
                # Most likely new Ollama API returns {"message": {"content": ...}}
                content = res.get("message", {}).get("content", "")
            elif isinstance(res, str):
                # Fallback: just use the string
                content = res
            else:
                # Unknown type: cast to string
                content = str(res)
            self._append_message(role="assistant", message=content)
            # Wrap in OpenAI-style format
            return {"choices": [{"message": {"content": content}}]}
        else:
            res = chat(model=self.model, messages=self.messages, stream=True)
            for chunk in res:
                part = (
                    chunk.get("message", {}).get("content", "")
                    if isinstance(chunk, dict)
                    else str(chunk)
                )
                msg_cache += part
                print(part, end="", flush=True)
            # Wrap stream result in OpenAI-style format
            return {"choices": [{"message": {"content": msg_cache}}]}

    def get_client(self):
        client = OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama",  # required, but unused
        )
        return client

    def get_model(self):
        return self.model

    def get_llm_config(self) -> LLMConfig:
        return LLMConfig(provider="ollama/" + self.model, api_token=None)

    def clear_message(self):
        self.messages = []

    def _append_message(self, role: str, message: str):
        self.messages.append({"role": role, "content": message})
