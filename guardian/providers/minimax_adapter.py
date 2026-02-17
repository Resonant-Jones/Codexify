"""
MiniMax chat adapter using an OpenAI-compatible API surface.
"""

# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import os
from typing import Any, Iterator, Optional

import requests

from guardian.core.egress import EgressDeniedError, assert_egress_allowed

from .base import ChatProvider

try:
    from openai import OpenAI  # type: ignore
except Exception:
    OpenAI = None  # type: ignore


def _get_value(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _coerce_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
                    continue
                item_content = item.get("content")
                if isinstance(item_content, str):
                    parts.append(item_content)
        return "".join(parts)
    return str(content)


def _normalize_messages(
    prompt: str, kw: dict[str, Any]
) -> list[dict[str, str]]:
    raw_messages = kw.pop("messages", None)
    if isinstance(raw_messages, list):
        normalized: list[dict[str, str]] = []
        for raw in raw_messages:
            if not isinstance(raw, dict):
                continue
            role = str(raw.get("role") or "user").strip() or "user"
            text = _coerce_text(raw.get("content")).strip()
            if not text:
                continue
            normalized.append({"role": role, "content": text})
        if normalized:
            return normalized
    return [{"role": "user", "content": prompt}]


def _extract_text_from_payload(payload: Any) -> str:
    choices = _get_value(payload, "choices")
    if not isinstance(choices, list) or not choices:
        return ""
    choice = choices[0]

    delta = _get_value(choice, "delta")
    text = _coerce_text(_get_value(delta, "content"))
    if text:
        return text

    message = _get_value(choice, "message")
    text = _coerce_text(_get_value(message, "content"))
    if text:
        return text

    return _coerce_text(_get_value(choice, "text"))


class MiniMaxProviderError(RuntimeError):
    def __init__(self, message: str, *, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


class MiniMaxAdapter(ChatProvider):
    name = "minimax"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str | None = None,
        timeout: float = 60.0,
    ):
        try:
            assert_egress_allowed("minimax")
        except EgressDeniedError as exc:
            raise RuntimeError(str(exc)) from exc

        self.api_key = (api_key or os.getenv("MINIMAX_API_KEY") or "").strip()
        self.base_url = (
            (base_url or os.getenv("MINIMAX_API_BASE") or "")
            .strip()
            .rstrip("/")
        )
        self.default_model = (
            default_model or os.getenv("MINIMAX_MODEL") or ""
        ).strip()
        self.timeout = float(os.getenv("MINIMAX_TIMEOUT_SECONDS", timeout))

        missing: list[str] = []
        if not self.api_key:
            missing.append("MINIMAX_API_KEY")
        if not self.base_url:
            missing.append("MINIMAX_API_BASE")
        if missing:
            raise RuntimeError(
                "MiniMax is not configured. Missing environment variable(s): "
                + ", ".join(missing)
                + "."
            )

        self.client = (
            OpenAI(api_key=self.api_key, base_url=self.base_url)
            if OpenAI is not None
            else None
        )

    def _safe_error(self, detail: str, *, status_code: int = 502) -> Exception:
        message = (detail or "").replace(self.api_key, "<redacted>").strip()
        if not message:
            message = "request failed"
        return MiniMaxProviderError(
            f"MiniMax request failed ({status_code}): {message}",
            status_code=status_code,
        )

    def _resolve_model(self, model: str | None) -> str:
        resolved = (model or self.default_model).strip()
        if not resolved:
            raise self._safe_error(
                "MINIMAX_MODEL is not configured and no model was provided.",
                status_code=500,
            )
        return resolved

    def _http_url(self) -> str:
        return f"{self.base_url}/chat/completions"

    def _http_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def generate(self, prompt: str, model: str | None = None, **kw) -> str:
        resolved_model = self._resolve_model(model)
        messages = _normalize_messages(prompt, kw)
        if self.client is not None:
            try:
                response = self.client.chat.completions.create(
                    model=resolved_model,
                    messages=messages,
                    timeout=self.timeout,
                    **kw,
                )
                return _extract_text_from_payload(response)
            except Exception as exc:
                raise self._safe_error(str(exc)) from exc

        request_timeout = float(kw.pop("timeout", self.timeout))
        payload: dict[str, Any] = {
            "model": resolved_model,
            "messages": messages,
        }
        payload.update(kw)

        try:
            response = requests.post(
                self._http_url(),
                json=payload,
                headers=self._http_headers(),
                timeout=request_timeout,
            )
            if not (200 <= response.status_code < 300):
                detail = response.text
                try:
                    body = response.json()
                    detail = (
                        _coerce_text(
                            _get_value(_get_value(body, "error"), "message")
                        )
                        or _coerce_text(_get_value(body, "message"))
                        or detail
                    )
                except Exception:
                    pass
                raise self._safe_error(detail, status_code=response.status_code)
            return _extract_text_from_payload(response.json())
        except MiniMaxProviderError:
            raise
        except Exception as exc:
            raise self._safe_error(str(exc)) from exc

    def stream(
        self, prompt: str, model: str | None = None, **kw
    ) -> Iterator[str]:
        resolved_model = self._resolve_model(model)
        messages = _normalize_messages(prompt, kw)
        if self.client is not None:
            try:
                stream = self.client.chat.completions.create(
                    model=resolved_model,
                    messages=messages,
                    stream=True,
                    timeout=self.timeout,
                    **kw,
                )
                for chunk in stream:
                    text = _extract_text_from_payload(chunk)
                    if text:
                        yield text
                return
            except Exception as exc:
                raise self._safe_error(str(exc)) from exc

        request_timeout = float(kw.pop("timeout", self.timeout))
        payload: dict[str, Any] = {
            "model": resolved_model,
            "messages": messages,
            "stream": True,
        }
        payload.update(kw)

        try:
            with requests.post(
                self._http_url(),
                json=payload,
                headers=self._http_headers(),
                stream=True,
                timeout=request_timeout,
            ) as response:
                if not (200 <= response.status_code < 300):
                    raise self._safe_error(
                        response.text, status_code=response.status_code
                    )
                for raw_line in response.iter_lines(decode_unicode=True):
                    if not raw_line:
                        continue
                    line = raw_line.strip()
                    if line.startswith("data:"):
                        line = line[5:].strip()
                    if not line or line == "[DONE]":
                        continue
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    text = _extract_text_from_payload(payload)
                    if text:
                        yield text
        except MiniMaxProviderError:
            raise
        except Exception as exc:
            raise self._safe_error(str(exc)) from exc
