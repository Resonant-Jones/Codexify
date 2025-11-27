"""
Groq chat adapter.
"""

# SPDX-License-Identifier: MIT
import os
from typing import Iterator, Optional

from .base import ChatProvider

try:
    from groq import Groq  # type: ignore
except Exception:
    Groq = None  # type: ignore


_DEFAULT = os.getenv("GROQ_CHAT_MODEL", "llama3-70b-8192")


class GroqChat(ChatProvider):
    name = "groq"

    def __init__(self, api_key: Optional[str] = None, timeout: float = 60.0):
        if Groq is None:
            raise RuntimeError("groq package not installed")
        self.client = Groq(api_key=api_key or os.getenv("GROQ_API_KEY"))
        self.timeout = float(os.getenv("GROQ_TIMEOUT", timeout))

    def generate(self, prompt: str, model: Optional[str] = None, **kw) -> str:
        model = model or _DEFAULT
        r = self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            timeout=self.timeout,
            **kw,
        )
        return r.choices[0].message.content or ""

    def stream(
        self, prompt: str, model: Optional[str] = None, **kw
    ) -> Iterator[str]:
        model = model or _DEFAULT
        s = self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            **kw,
        )
        for chunk in s:
            try:
                # SDK stream chunks may mirror OpenAI semantics
                delta = getattr(chunk.choices[0], "delta", None)
                if isinstance(delta, dict):
                    text = delta.get("content")
                    if text:
                        yield text
                else:
                    text = getattr(delta, "content", None)
                    if text:
                        yield text
            except Exception:
                continue
