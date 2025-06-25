"""Lightweight model package initializer.

This module exposes the core ``Model`` class and attempts to import optional
model backends. Many of these backends require third‑party dependencies which
may not be installed in all environments (for example during unit tests). To
avoid ``ImportError`` at import time we try/except each optional import and
expose ``None`` when the dependency is missing.
"""

from .model import Model

try:
    from .deepseek import Deepseek
except Exception:  # pragma: no cover - missing package
    Deepseek = None

try:
    from .gemini import Gemini
except Exception:  # pragma: no cover
    Gemini = None

try:
    from .ollama import Ollama
except Exception:  # pragma: no cover
    Ollama = None

try:
    from .openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None

try:
    from .gork import Gork
except Exception:  # pragma: no cover
    Gork = None
