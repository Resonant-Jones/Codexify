"""MiniMax chat adapter supporting OpenAI- and Anthropic-compatible surfaces."""

# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import os
from typing import Any, Iterator

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


def _normalize_anthropic_messages(
    prompt: str, kw: dict[str, Any]
) -> tuple[list[dict[str, Any]], str | None]:
    raw_messages = kw.pop("messages", None)
    system_parts: list[str] = []
    normalized: list[dict[str, Any]] = []

    if isinstance(raw_messages, list):
        for raw in raw_messages:
            if not isinstance(raw, dict):
                continue
            role = str(raw.get("role") or "user").strip().lower() or "user"
            text = _coerce_text(raw.get("content")).strip()
            if not text:
                continue
            if role == "system":
                system_parts.append(text)
                continue
            if role not in {"user", "assistant"}:
                role = "user"
            normalized.append(
                {
                    "role": role,
                    "content": [{"type": "text", "text": text}],
                }
            )

    if not normalized:
        normalized = [
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}],
            }
        ]

    system_text = "\n\n".join(part for part in system_parts if part).strip()
    return normalized, (system_text or None)


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


def _extract_text_from_anthropic_payload(payload: Any) -> str:
    content = _get_value(payload, "content")
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if str(block.get("type") or "").strip() != "text":
            continue
        text = _coerce_text(block.get("text")).strip()
        if text:
            parts.append(text)
    return "".join(parts)


def _extract_text_from_anthropic_stream_event(payload: Any) -> str:
    event_type = str(_get_value(payload, "type") or "").strip()
    if event_type == "content_block_delta":
        delta = _get_value(payload, "delta")
        text = _coerce_text(_get_value(delta, "text"))
        if text:
            return text
    if event_type == "content_block_start":
        block = _get_value(payload, "content_block")
        text = _coerce_text(_get_value(block, "text"))
        if text:
            return text
    return _extract_text_from_anthropic_payload(payload)


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
        api_flavor: str | None = None,
        anthropic_version: str | None = None,
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
        self.api_flavor = (
            (api_flavor or os.getenv("MINIMAX_API_FLAVOR") or "openai")
            .strip()
            .lower()
        )
        self.anthropic_version = (
            anthropic_version
            or os.getenv("MINIMAX_ANTHROPIC_VERSION")
            or "2023-06-01"
        ).strip()
        self.anthropic_max_tokens = int(
            os.getenv("MINIMAX_ANTHROPIC_MAX_TOKENS", "1024")
        )

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

        if self.api_flavor not in {"openai", "anthropic"}:
            raise RuntimeError(
                "MINIMAX_API_FLAVOR must be either 'openai' or 'anthropic'."
            )

        self.client = None
        if self.api_flavor == "openai" and OpenAI is not None:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def _safe_error(self, detail: str, *, status_code: int = 502) -> Exception:
        message = (detail or "").replace(self.api_key, "<redacted>").strip()
        if not message:
            message = "request failed"
        return MiniMaxProviderError(
            f"MiniMax request failed ({status_code}): {message}",
            status_code=status_code,
        )

    def _extract_error_detail(self, response: requests.Response) -> str:
        detail = response.text
        try:
            body = response.json()
            detail = (
                _coerce_text(_get_value(_get_value(body, "error"), "message"))
                or _coerce_text(_get_value(body, "message"))
                or detail
            )
        except Exception:
            pass
        return detail

    def _resolve_model(self, model: str | None) -> str:
        resolved = (model or self.default_model).strip()
        if not resolved:
            raise self._safe_error(
                "MINIMAX_MODEL is not configured and no model was provided.",
                status_code=500,
            )
        return resolved

    def _openai_http_url(self) -> str:
        return f"{self.base_url}/chat/completions"

    def _anthropic_http_url(self) -> str:
        if self.base_url.endswith("/v1"):
            return f"{self.base_url}/messages"
        return f"{self.base_url}/v1/messages"

    def _openai_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _anthropic_headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": self.anthropic_version,
            "Content-Type": "application/json",
        }

    def generate(self, prompt: str, model: str | None = None, **kw) -> str:
        if self.api_flavor == "anthropic":
            return self._generate_anthropic(prompt, model=model, **kw)

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
                self._openai_http_url(),
                json=payload,
                headers=self._openai_headers(),
                timeout=request_timeout,
            )
            if not (200 <= response.status_code < 300):
                raise self._safe_error(
                    self._extract_error_detail(response),
                    status_code=response.status_code,
                )
            return _extract_text_from_payload(response.json())
        except MiniMaxProviderError:
            raise
        except Exception as exc:
            raise self._safe_error(str(exc)) from exc

    def _generate_anthropic(
        self, prompt: str, model: str | None = None, **kw
    ) -> str:
        resolved_model = self._resolve_model(model)
        messages, system_prompt = _normalize_anthropic_messages(prompt, kw)
        request_timeout = float(kw.pop("timeout", self.timeout))
        max_tokens = int(kw.pop("max_tokens", self.anthropic_max_tokens))

        payload: dict[str, Any] = {
            "model": resolved_model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if system_prompt:
            payload["system"] = system_prompt
        payload.update(kw)

        try:
            response = requests.post(
                self._anthropic_http_url(),
                json=payload,
                headers=self._anthropic_headers(),
                timeout=request_timeout,
            )
            if not (200 <= response.status_code < 300):
                raise self._safe_error(
                    self._extract_error_detail(response),
                    status_code=response.status_code,
                )
            return _extract_text_from_anthropic_payload(response.json())
        except MiniMaxProviderError:
            raise
        except Exception as exc:
            raise self._safe_error(str(exc)) from exc

    def stream(
        self, prompt: str, model: str | None = None, **kw
    ) -> Iterator[str]:
        if self.api_flavor == "anthropic":
            yield from self._stream_anthropic(prompt, model=model, **kw)
            return

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
                self._openai_http_url(),
                json=payload,
                headers=self._openai_headers(),
                stream=True,
                timeout=request_timeout,
            ) as response:
                if not (200 <= response.status_code < 300):
                    raise self._safe_error(
                        self._extract_error_detail(response),
                        status_code=response.status_code,
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

    def _stream_anthropic(
        self, prompt: str, model: str | None = None, **kw
    ) -> Iterator[str]:
        resolved_model = self._resolve_model(model)
        messages, system_prompt = _normalize_anthropic_messages(prompt, kw)
        request_timeout = float(kw.pop("timeout", self.timeout))
        max_tokens = int(kw.pop("max_tokens", self.anthropic_max_tokens))

        payload: dict[str, Any] = {
            "model": resolved_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if system_prompt:
            payload["system"] = system_prompt
        payload.update(kw)

        try:
            with requests.post(
                self._anthropic_http_url(),
                json=payload,
                headers=self._anthropic_headers(),
                stream=True,
                timeout=request_timeout,
            ) as response:
                if not (200 <= response.status_code < 300):
                    raise self._safe_error(
                        self._extract_error_detail(response),
                        status_code=response.status_code,
                    )

                for raw_line in response.iter_lines(decode_unicode=True):
                    if not raw_line:
                        continue
                    line = raw_line.strip()
                    if line.startswith("event:"):
                        continue
                    if line.startswith("data:"):
                        line = line[5:].strip()
                    if not line or line == "[DONE]":
                        continue

                    try:
                        event_payload = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    text = _extract_text_from_anthropic_stream_event(
                        event_payload
                    )
                    if text:
                        yield text
        except MiniMaxProviderError:
            raise
        except Exception as exc:
            raise self._safe_error(str(exc)) from exc
