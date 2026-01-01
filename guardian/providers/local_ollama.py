# guardian/providers/local_ollama.py

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Generator, Iterable, List, Optional

import requests

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_BASE = "http://localhost:11434"


def _ollama_url(base_url: str) -> str:
    return base_url.rstrip("/") + "/api/chat"


def _build_payload(
    model: str,
    messages: list[dict[str, str]],
    temperature: float | None = None,
    stream: bool = True,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": stream,
    }
    if temperature is not None:
        payload["options"] = {"temperature": temperature}
    return payload


def ollama_chat(
    *,
    model: str,
    messages: list[dict[str, str]],
    base_url: str = DEFAULT_OLLAMA_BASE,
    temperature: float | None = None,
    timeout: int = 60,
) -> str:
    """
    Non-streaming Ollama chat (used rarely, mostly for probes).
    """
    url = _ollama_url(base_url)
    payload = _build_payload(model, messages, temperature, stream=False)

    resp = requests.post(url, json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

    return data.get("message", {}).get("content", "")


def ollama_stream(
    *,
    model: str,
    messages: list[dict[str, str]],
    base_url: str = DEFAULT_OLLAMA_BASE,
    temperature: float | None = None,
    timeout: int = 60,
) -> Generator[str, None, None]:
    """
    Streaming Ollama chat.
    Yields decoded text deltas only.
    """
    url = _ollama_url(base_url)
    payload = _build_payload(model, messages, temperature, stream=True)

    with requests.post(url, json=payload, stream=True, timeout=timeout) as resp:
        resp.raise_for_status()

        for raw_line in resp.iter_lines(decode_unicode=True):
            if not raw_line:
                continue

            try:
                chunk = json.loads(raw_line)
            except json.JSONDecodeError:
                logger.debug("Skipping non-JSON Ollama line: %r", raw_line)
                continue

            if chunk.get("done"):
                return

            message = chunk.get("message") or {}
            content = message.get("content")
            if content:
                yield content
