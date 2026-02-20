"""
External MLX inference service (OpenAI-compatible subset).

This service intentionally sits behind the existing `local` provider contract:
- POST /v1/chat/completions
- GET  /v1/models
- GET  /healthz

It supports per-request mode hints (`chat` / `coding`) and applies
mode-specific concurrency caps.
"""

from __future__ import annotations

import inspect
import json
import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Iterable, Iterator, Protocol

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


def _env_int(name: str, default: int) -> int:
    raw = str(os.getenv(name, str(default))).strip()
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _env_csv(name: str) -> list[str]:
    raw = str(os.getenv(name, "")).strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _normalize_mode(raw_mode: str | None) -> str:
    value = str(raw_mode or "").strip().lower()
    if value in {"chat", "coding"}:
        return value
    return ""


def _coding_keywords() -> tuple[str, ...]:
    values = _env_csv("MLX_SERVER_CODING_MODEL_HINTS")
    if not values:
        values = ["code", "coder", "coding", "programmer"]
    return tuple(v.lower() for v in values if v)


def _infer_mode(model_id: str, raw_mode: str | None) -> str:
    explicit = _normalize_mode(raw_mode)
    if explicit:
        return explicit

    model = str(model_id or "").strip()
    lowered = model.lower()
    coding_models = {
        candidate.lower() for candidate in _env_csv("MLX_SERVER_CODING_MODELS")
    }
    chat_models = {
        candidate.lower() for candidate in _env_csv("MLX_SERVER_CHAT_MODELS")
    }

    if lowered and lowered in coding_models:
        return "coding"
    if lowered and lowered in chat_models:
        return "chat"
    if any(keyword in lowered for keyword in _coding_keywords()):
        return "coding"

    default_mode = _normalize_mode(os.getenv("MLX_SERVER_DEFAULT_MODE"))
    return default_mode or "chat"


def _resolve_default_chat_model() -> str:
    candidates = (
        os.getenv("MLX_SERVER_DEFAULT_CHAT_MODEL"),
        os.getenv("LOCAL_CHAT_MODEL"),
        os.getenv("LOCAL_LLM_MODEL"),
        os.getenv("DEFAULT_LOCAL_MODEL"),
        os.getenv("LLM_MODEL"),
        "mlx-community/Llama-3B-Instruct-4bit",
    )
    for candidate in candidates:
        value = str(candidate or "").strip()
        if value:
            return value
    return "mlx-community/Llama-3B-Instruct-4bit"


def _resolve_default_coding_model() -> str:
    candidates = (
        os.getenv("MLX_SERVER_DEFAULT_CODING_MODEL"),
        os.getenv("LOCAL_CODE_MODEL"),
        os.getenv("LOCAL_CHAT_MODEL"),
        os.getenv("LOCAL_LLM_MODEL"),
        _resolve_default_chat_model(),
    )
    for candidate in candidates:
        value = str(candidate or "").strip()
        if value:
            return value
    return _resolve_default_chat_model()


def _resolve_model(model_id: str | None, mode: str) -> str:
    requested = str(model_id or "").strip()
    if requested:
        return requested
    if mode == "coding":
        return _resolve_default_coding_model()
    return _resolve_default_chat_model()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str | None = None
    messages: list[ChatMessage] = Field(default_factory=list)
    temperature: float | None = 0.7
    max_tokens: int | None = None
    stream: bool = False
    mode: str | None = None

    model_config = ConfigDict(extra="ignore")


class TextBackend(Protocol):
    def backend_name(self) -> str:
        ...

    def list_models(self) -> list[str]:
        ...

    def generate(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int | None,
    ) -> str:
        ...

    def stream_generate(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int | None,
    ) -> Iterator[str]:
        ...

    def health(self) -> dict[str, Any]:
        ...


class EchoBackend:
    """Deterministic fallback backend for environments without MLX runtime."""

    def backend_name(self) -> str:
        return "echo"

    def list_models(self) -> list[str]:
        return sorted(
            {_resolve_default_chat_model(), _resolve_default_coding_model()}
        )

    def generate(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int | None,
    ) -> str:
        _ = temperature, max_tokens
        user_messages = [
            str(message.get("content") or "")
            for message in messages
            if str(message.get("role") or "").strip() == "user"
        ]
        prompt = user_messages[-1] if user_messages else ""
        return f"[echo:{model}] {prompt}".strip()

    def stream_generate(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int | None,
    ) -> Iterator[str]:
        text = self.generate(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if not text:
            return
        chunk_size = _env_int("MLX_SERVER_ECHO_STREAM_CHUNK_SIZE", 16)
        for idx in range(0, len(text), chunk_size):
            yield text[idx : idx + chunk_size]

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "backend": self.backend_name()}


class MlxLMBackend:
    """
    Minimal mlx-lm wrapper backend.

    This adapter is intentionally conservative. If runtime APIs differ across
    mlx-lm versions, it fails closed with actionable errors rather than
    silently generating wrong outputs.
    """

    def __init__(self) -> None:
        self._model_cache: dict[str, tuple[Any, Any]] = {}
        self._lock = threading.Lock()
        self._load_fn = None
        self._generate_fn = None
        self._stream_fn = None
        self._import_error: str | None = None
        self._import_runtime()

    def _import_runtime(self) -> None:
        try:
            from mlx_lm import generate as generate_fn  # type: ignore
            from mlx_lm import load as load_fn  # type: ignore
        except Exception as exc:  # pragma: no cover - depends on env
            self._import_error = str(exc)
            self._load_fn = None
            self._generate_fn = None
            self._stream_fn = None
            return

        stream_fn = None
        # stream_generate can live in different mlx-lm modules depending on version.
        for candidate in (
            "mlx_lm",
            "mlx_lm.utils",
        ):
            try:
                module = __import__(candidate, fromlist=["stream_generate"])
                maybe = getattr(module, "stream_generate", None)
                if callable(maybe):
                    stream_fn = maybe
                    break
            except Exception:
                continue

        self._load_fn = load_fn
        self._generate_fn = generate_fn
        self._stream_fn = stream_fn
        self._import_error = None

    def backend_name(self) -> str:
        return "mlx_lm"

    def _ensure_available(self) -> None:
        if self._load_fn is None or self._generate_fn is None:
            detail = self._import_error or "mlx_lm import failed"
            raise RuntimeError(f"MLX runtime unavailable: {detail}")

    def _ensure_model(self, model_id: str) -> tuple[Any, Any]:
        self._ensure_available()
        with self._lock:
            cached = self._model_cache.get(model_id)
            if cached is not None:
                return cached
            assert self._load_fn is not None
            model, tokenizer = self._load_fn(model_id)
            self._model_cache[model_id] = (model, tokenizer)
            return model, tokenizer

    def _to_prompt(self, tokenizer: Any, messages: list[dict[str, str]]) -> str:
        if hasattr(tokenizer, "apply_chat_template"):
            try:
                return str(
                    tokenizer.apply_chat_template(
                        messages,
                        tokenize=False,
                        add_generation_prompt=True,
                    )
                )
            except Exception:
                pass
        lines: list[str] = []
        for message in messages:
            role = str(message.get("role") or "user").strip() or "user"
            content = str(message.get("content") or "")
            lines.append(f"{role}: {content}")
        lines.append("assistant:")
        return "\n".join(lines)

    def _call_generate(
        self,
        model_obj: Any,
        tokenizer: Any,
        prompt: str,
        temperature: float,
        max_tokens: int | None,
    ) -> str:
        assert self._generate_fn is not None
        kwargs: dict[str, Any] = {}
        if max_tokens is not None:
            kwargs["max_tokens"] = int(max_tokens)

        signature = inspect.signature(self._generate_fn)
        if "temp" in signature.parameters:
            kwargs["temp"] = float(temperature)
        elif "temperature" in signature.parameters:
            kwargs["temperature"] = float(temperature)

        result = self._generate_fn(
            model_obj, tokenizer, prompt=prompt, **kwargs
        )
        if isinstance(result, str):
            return result
        if hasattr(result, "text"):
            return str(result.text)
        if isinstance(result, dict):
            for key in ("text", "output", "content"):
                if key in result:
                    return str(result[key])
        return str(result)

    def list_models(self) -> list[str]:
        declared = {
            _resolve_default_chat_model(),
            _resolve_default_coding_model(),
        }
        declared.update(_env_csv("MLX_SERVER_CHAT_MODELS"))
        declared.update(_env_csv("MLX_SERVER_CODING_MODELS"))
        with self._lock:
            declared.update(self._model_cache.keys())
        return sorted(model for model in declared if model)

    def generate(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int | None,
    ) -> str:
        model_obj, tokenizer = self._ensure_model(model)
        prompt = self._to_prompt(tokenizer, messages)
        return self._call_generate(
            model_obj=model_obj,
            tokenizer=tokenizer,
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def stream_generate(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int | None,
    ) -> Iterator[str]:
        model_obj, tokenizer = self._ensure_model(model)
        prompt = self._to_prompt(tokenizer, messages)
        if callable(self._stream_fn):
            kwargs: dict[str, Any] = {}
            if max_tokens is not None:
                kwargs["max_tokens"] = int(max_tokens)
            signature = inspect.signature(self._stream_fn)
            if "temp" in signature.parameters:
                kwargs["temp"] = float(temperature)
            elif "temperature" in signature.parameters:
                kwargs["temperature"] = float(temperature)

            iterator = self._stream_fn(
                model_obj,
                tokenizer,
                prompt=prompt,
                **kwargs,
            )
            for chunk in iterator:
                if isinstance(chunk, str):
                    if chunk:
                        yield chunk
                    continue
                if isinstance(chunk, dict):
                    token = str(
                        chunk.get("text")
                        or chunk.get("content")
                        or chunk.get("token")
                        or ""
                    )
                    if token:
                        yield token
                    continue
                text = str(chunk)
                if text:
                    yield text
            return

        # Fallback when streaming API is unavailable in current mlx-lm build.
        text = self._call_generate(
            model_obj=model_obj,
            tokenizer=tokenizer,
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if text:
            yield text

    def health(self) -> dict[str, Any]:
        if self._import_error:
            return {
                "status": "degraded",
                "backend": self.backend_name(),
                "detail": self._import_error,
            }
        return {
            "status": "ok",
            "backend": self.backend_name(),
            "loaded_models": self.list_models(),
        }


def _build_backend() -> TextBackend:
    backend_name = (
        str(os.getenv("MLX_SERVER_BACKEND", "mlx_lm")).strip().lower()
    )
    allow_echo_fallback = str(
        os.getenv("MLX_SERVER_ALLOW_ECHO_FALLBACK", "1")
    ).strip().lower() in {"1", "true", "yes", "on"}

    if backend_name == "echo":
        return EchoBackend()

    if backend_name == "mlx_lm":
        backend = MlxLMBackend()
        if backend.health().get("status") == "ok":
            return backend
        if allow_echo_fallback:
            logger.warning(
                "[mlx-server] mlx_lm backend unavailable; falling back to echo backend"
            )
            return EchoBackend()
        return backend

    logger.warning(
        "[mlx-server] unknown backend=%s, using echo fallback",
        backend_name,
    )
    return EchoBackend()


@dataclass(frozen=True)
class _ModeGate:
    mode: str
    semaphore: threading.BoundedSemaphore


_CHAT_GATE = _ModeGate(
    mode="chat",
    semaphore=threading.BoundedSemaphore(
        _env_int("MLX_SERVER_CHAT_MAX_INFLIGHT", 2)
    ),
)
_CODING_GATE = _ModeGate(
    mode="coding",
    semaphore=threading.BoundedSemaphore(
        _env_int("MLX_SERVER_CODING_MAX_INFLIGHT", 1)
    ),
)
_GATE_TIMEOUT_SECONDS = float(
    os.getenv("MLX_SERVER_GATE_ACQUIRE_TIMEOUT_SECONDS", "0.05")
)

_BACKEND: TextBackend = _build_backend()

app = FastAPI(title="Codexify MLX Server")


def _openai_completion_payload(
    *,
    completion_id: str,
    model: str,
    content: str,
) -> dict[str, Any]:
    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    }


def _stream_chunk(
    *,
    completion_id: str,
    model: str,
    token: str | None = None,
    finish_reason: str | None = None,
) -> str:
    payload = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {"content": token} if token else {},
                "finish_reason": finish_reason,
            }
        ],
    }
    return f"data: {json.dumps(payload, ensure_ascii=True)}\n\n"


def _acquire_gate(mode: str) -> _ModeGate:
    gate = _CODING_GATE if mode == "coding" else _CHAT_GATE
    acquired = gate.semaphore.acquire(timeout=_GATE_TIMEOUT_SECONDS)
    if not acquired:
        raise HTTPException(
            status_code=429,
            detail=f"{gate.mode}_capacity_reached",
        )
    return gate


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    health = _BACKEND.health()
    return {
        "status": health.get("status", "ok"),
        "backend": _BACKEND.backend_name(),
        "chat_max_inflight": _env_int("MLX_SERVER_CHAT_MAX_INFLIGHT", 2),
        "coding_max_inflight": _env_int("MLX_SERVER_CODING_MAX_INFLIGHT", 1),
        "detail": health.get("detail"),
    }


@app.get("/ping")
def ping() -> dict[str, str]:
    return {"ok": "true"}


@app.get("/v1/models")
def list_models() -> dict[str, Any]:
    data = [
        {
            "id": model_id,
            "object": "model",
            "owned_by": _BACKEND.backend_name(),
        }
        for model_id in _BACKEND.list_models()
    ]
    return {"object": "list", "data": data}


@app.get("/api/tags")
def list_tags() -> dict[str, Any]:
    # Compatibility endpoint used by warm-up probes.
    return {
        "models": [{"name": model_id} for model_id in _BACKEND.list_models()]
    }


@app.post("/v1/chat/completions", response_model=None)
def chat_completions(
    body: ChatCompletionRequest,
) -> JSONResponse | StreamingResponse:
    if not body.messages:
        raise HTTPException(status_code=400, detail="messages are required")

    explicit_mode = _normalize_mode(body.mode)
    if body.mode is not None and not explicit_mode:
        raise HTTPException(
            status_code=400, detail="invalid mode (expected 'chat' or 'coding')"
        )

    provisional_model = str(body.model or "").strip()
    mode = _infer_mode(provisional_model, explicit_mode)
    model = _resolve_model(body.model, mode)
    temperature = float(
        body.temperature if body.temperature is not None else 0.7
    )
    max_tokens = body.max_tokens
    messages = [
        {"role": message.role, "content": message.content}
        for message in body.messages
    ]
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"

    if body.stream:

        def _event_stream() -> Iterator[str]:
            gate = _acquire_gate(mode)
            try:
                for token in _BACKEND.stream_generate(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ):
                    if token:
                        yield _stream_chunk(
                            completion_id=completion_id,
                            model=model,
                            token=token,
                            finish_reason=None,
                        )
                yield _stream_chunk(
                    completion_id=completion_id,
                    model=model,
                    token=None,
                    finish_reason="stop",
                )
                yield "data: [DONE]\n\n"
            except HTTPException:
                raise
            except Exception as exc:
                logger.exception(
                    "[mlx-server] streaming generation failed: %s", exc
                )
                error_payload = {
                    "error": {"message": str(exc), "type": "server_error"}
                }
                yield f"data: {json.dumps(error_payload, ensure_ascii=True)}\n\n"
                yield "data: [DONE]\n\n"
            finally:
                gate.semaphore.release()

        return StreamingResponse(
            _event_stream(),
            media_type="text/event-stream",
        )

    gate = _acquire_gate(mode)
    try:
        content = _BACKEND.generate(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("[mlx-server] completion failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        gate.semaphore.release()

    return JSONResponse(
        _openai_completion_payload(
            completion_id=completion_id,
            model=model,
            content=str(content),
        )
    )
