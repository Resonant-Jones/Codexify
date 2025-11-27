"""
Gemini chat adapter (google-generativeai)
"""

# SPDX-License-Identifier: MIT
import os
from typing import Iterator, Optional

from .base import ChatProvider

try:
    import google.generativeai as genai  # type: ignore
except Exception:
    genai = None  # type: ignore


_DEFAULT = os.getenv("GEMINI_CHAT_MODEL", "gemini-1.5-flash")


class GeminiChat(ChatProvider):
    name = "gemini"

    def __init__(self, api_key: Optional[str] = None):
        if genai is None:
            raise RuntimeError("google-generativeai package not installed")
        genai.configure(api_key=api_key or os.getenv("GEMINI_API_KEY"))

    def generate(self, prompt: str, model: Optional[str] = None, **kw) -> str:
        model = model or _DEFAULT
        g = genai.GenerativeModel(model)
        r = g.generate_content(prompt, **kw)
        return getattr(r, "text", "") or ""

    def stream(
        self, prompt: str, model: Optional[str] = None, **kw
    ) -> Iterator[str]:
        model = model or _DEFAULT
        g = genai.GenerativeModel(model)
        for ev in g.generate_content(prompt, stream=True, **kw):
            t = getattr(ev, "text", None)
            if t:
                yield t
