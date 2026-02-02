"""
OpenAI chat and embeddings adapters (SDK >= 1.x)
"""

# SPDX-License-Identifier: MIT
import os
from typing import Iterator, List, Optional

from .base import ChatProvider, EmbeddingsProvider

try:
    from openai import OpenAI  # type: ignore
except Exception:
    OpenAI = None  # type: ignore


_DEFAULT_CHAT = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
_DEFAULT_EMB = os.getenv("OPENAI_EMBED_MODEL") or os.getenv(
    "OPENAI_EMBEDDING_MODEL"
)


class OpenAIChat(ChatProvider):
    name = "openai"

    def __init__(self, api_key: Optional[str] = None, timeout: float = 60.0):
        if OpenAI is None:
            raise RuntimeError("openai package not installed")
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.timeout = float(os.getenv("OPENAI_TIMEOUT", timeout))

    def generate(self, prompt: str, model: Optional[str] = None, **kw) -> str:
        model = model or _DEFAULT_CHAT
        r = self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            timeout=self.timeout,
            **kw,
        )
        # OpenAI 1.x returns choices[0].message.content
        return r.choices[0].message.content or ""

    def stream(
        self, prompt: str, model: Optional[str] = None, **kw
    ) -> Iterator[str]:
        model = model or _DEFAULT_CHAT
        s = self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            **kw,
        )
        for chunk in s:
            # chunk.choices[0].delta.content in streaming
            try:
                delta = getattr(chunk.choices[0], "delta", None)
                if delta and getattr(delta, "content", None):
                    yield delta.content  # type: ignore[attr-defined]
            except Exception:
                # Soft-fail chunk parsing
                continue


class OpenAIEmbeddings(EmbeddingsProvider):
    name = "openai"

    def __init__(self, api_key: Optional[str] = None, timeout: float = 60.0):
        if OpenAI is None:
            raise RuntimeError("openai package not installed")
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.timeout = float(os.getenv("OPENAI_TIMEOUT", timeout))

    def embed(
        self, texts: List[str], model: Optional[str] = None, **kw
    ) -> List[List[float]]:
        model = model or _DEFAULT_EMB
        if not model:
            raise ValueError(
                "OPENAI_EMBED_MODEL or OPENAI_EMBEDDING_MODEL is required for OpenAI embeddings."
            )
        r = self.client.embeddings.create(
            model=model, input=texts, timeout=self.timeout, **kw
        )
        return [d.embedding for d in r.data]
