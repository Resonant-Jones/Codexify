from __future__ import annotations

import asyncio
import gc
import json
import os
import shutil
import time
import uuid
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from mlx_vlm import apply_chat_template, generate, load
from mlx_vlm.models.base import load_chat_template
from mlx_vlm.tokenizer_utils import load_tokenizer
from mlx_vlm.utils import StoppingCriteria, load_config, load_model
from transformers import AutoTokenizer


APP_NAME = "Whoosh'd Gemma VLM Proxy"
DEFAULT_MODEL = (
    "/Users/resonant_jones/Keep/Resonant_Constructs/Whoosh'd/"
    "models/gemma-4-E2B-it-ultra-uncensored-heretic-MLX-3bit-mixed_3_6"
)


def _now() -> float:
    return time.time()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_int(value: Any, default: int) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _read_model_size(model_path: Path) -> int:
    weights = model_path / "model.safetensors"
    if weights.exists():
        return int(weights.stat().st_size)
    return 0


def _chunk_text(text: str, size: int = 1024) -> list[str]:
    if not text:
        return []
    return [text[i : i + size] for i in range(0, len(text), size)]


def _is_gemma4_bundle(model_path: Path) -> bool:
    processor_config = model_path / "processor_config.json"
    if not processor_config.exists():
        return False

    try:
        payload = json.loads(processor_config.read_text())
    except json.JSONDecodeError:
        return False

    return str(payload.get("processor_class", "")).strip() == "Gemma4Processor"


MODEL_OVERLAY_CACHE: dict[str, Path] = {}


def _prepare_model_bundle(model_path: Path) -> Path:
    if not _is_gemma4_bundle(model_path):
        return model_path

    cache_key = str(model_path)
    cached = MODEL_OVERLAY_CACHE.get(cache_key)
    if cached is not None and cached.exists():
        return cached

    overlay_root = Path(tempfile.mkdtemp(prefix="whooshd-gemma4-", dir="/private/tmp"))
    for entry in model_path.iterdir():
        target = overlay_root / entry.name
        if entry.name == "tokenizer_config.json":
            try:
                data = json.loads(entry.read_text())
            except json.JSONDecodeError:
                data = None
            if isinstance(data, dict) and isinstance(
                data.get("extra_special_tokens"), list
            ):
                data["extra_special_tokens"] = {}
            if isinstance(data, dict):
                target.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            else:
                shutil.copy2(entry, target)
            continue

        if entry.is_dir():
            target.symlink_to(entry, target_is_directory=True)
        else:
            target.symlink_to(entry)

    MODEL_OVERLAY_CACHE[cache_key] = overlay_root
    return overlay_root


def _load_gemma4_bundle(model_path: str) -> tuple[Any, Any, dict[str, Any]]:
    bundle_path = _prepare_model_bundle(Path(model_path))
    model = load_model(bundle_path, trust_remote_code=True)
    tokenizer = AutoTokenizer.from_pretrained(
        str(bundle_path),
        trust_remote_code=True,
        local_files_only=True,
    )
    load_chat_template(tokenizer, bundle_path)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.stopping_criteria = StoppingCriteria(
        getattr(tokenizer, "eos_token_ids", None),
        tokenizer,
    )
    detokenizer_class = load_tokenizer(bundle_path, return_tokenizer=False)

    class _TextOnlyProcessor:
        def __init__(self, tokenizer_obj: Any, detokenizer_cls: Any) -> None:
            self.tokenizer = tokenizer_obj
            self.detokenizer = detokenizer_cls(tokenizer_obj)
            self.image_processor = None
            self.feature_extractor = None

        def __call__(self, *args: Any, **kwargs: Any) -> Any:
            return self.tokenizer(*args, **kwargs)

        def __getattr__(self, attr: str) -> Any:
            return getattr(self.tokenizer, attr)

        def apply_chat_template(self, *args: Any, **kwargs: Any) -> Any:
            return self.tokenizer.apply_chat_template(*args, **kwargs)

        def batch_decode(self, *args: Any, **kwargs: Any) -> Any:
            return self.tokenizer.batch_decode(*args, **kwargs)

        def decode(self, *args: Any, **kwargs: Any) -> Any:
            return self.tokenizer.decode(*args, **kwargs)

    processor = _TextOnlyProcessor(tokenizer, detokenizer_class)
    config = load_config(bundle_path, trust_remote_code=True)
    return model, processor, config


@dataclass
class ProxyState:
    configured_model: str
    model: Any | None = None
    processor: Any | None = None
    config: dict[str, Any] | None = None
    lifecycle: str = "unloaded"
    last_error_message: str | None = None
    last_load_started_at: float | None = None
    last_load_completed_at: float | None = None
    last_unloaded_at: float | None = None

    @property
    def loaded(self) -> bool:
        return self.model is not None and self.processor is not None

    @property
    def loaded_model(self) -> str | None:
        return self.configured_model if self.loaded else None


MODEL_PATH = os.environ.get("WHOOSHD_MLX_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
STATE = ProxyState(configured_model=MODEL_PATH)
LOAD_LOCK = asyncio.Lock()

app = FastAPI(title=APP_NAME)


async def ensure_loaded() -> None:
    if STATE.loaded and STATE.lifecycle == "ready":
        return

    async with LOAD_LOCK:
        if STATE.loaded and STATE.lifecycle == "ready":
            return

        STATE.lifecycle = "warming"
        STATE.last_error_message = None
        STATE.last_load_started_at = _now()

        try:
            model_path = Path(STATE.configured_model)
            prepared_model_path = _prepare_model_bundle(model_path)
            if prepared_model_path != model_path:
                model, processor, config = await asyncio.to_thread(
                    _load_gemma4_bundle,
                    STATE.configured_model,
                )
            else:
                model, processor = await asyncio.to_thread(
                    load,
                    STATE.configured_model,
                    trust_remote_code=True,
                )
                config = await asyncio.to_thread(
                    load_config,
                    STATE.configured_model,
                    trust_remote_code=True,
                )
        except Exception as exc:  # pragma: no cover - surfaced via runtime verification
            STATE.model = None
            STATE.processor = None
            STATE.config = None
            STATE.lifecycle = "failed"
            STATE.last_error_message = str(exc)
            STATE.last_load_completed_at = _now()
            raise

        STATE.model = model
        STATE.processor = processor
        STATE.config = config
        STATE.lifecycle = "ready"
        STATE.last_load_completed_at = _now()


def unload_model() -> None:
    STATE.model = None
    STATE.processor = None
    STATE.config = None
    STATE.lifecycle = "unloaded"
    STATE.last_unloaded_at = _now()
    gc.collect()


def build_health_payload() -> dict[str, Any]:
    model_path = Path(STATE.configured_model)
    size_bytes = _read_model_size(model_path)
    model_lifecycle = STATE.lifecycle
    pressure = "normal"
    if model_lifecycle == "warming":
        pressure = "warming"
    elif model_lifecycle == "failed":
        pressure = "degraded"

    return {
        "ok": True,
        "runner": "whooshd",
        "version": "gemma-vlm-proxy",
        "status": model_lifecycle,
        "model_lifecycle": model_lifecycle,
        "active_model": STATE.loaded_model,
        "queue_depth": 0,
        "active_jobs": 0,
        "memory": {
            "pressure": pressure,
            "total_gb": 32.0,
            "used_gb": round(size_bytes / 1e9, 2),
            "available_gb": round(max(32.0 - (size_bytes / 1e9), 0.0), 2),
        },
    }


def build_model_entry() -> dict[str, Any]:
    return {
        "id": STATE.configured_model,
        "object": "model",
        "created": 1700000000,
        "owned_by": "whooshd",
    }


def build_tags_entry() -> dict[str, Any]:
    model_path = Path(STATE.configured_model)
    return {
        "name": STATE.configured_model,
        "modified_at": _utc_now(),
        "size": _read_model_size(model_path),
    }


def _build_prompt(messages: list[dict[str, Any]]) -> str:
    if STATE.processor is None or STATE.config is None:
        raise RuntimeError("model is not loaded")
    return apply_chat_template(
        STATE.processor,
        STATE.config,
        messages,
        add_generation_prompt=True,
        num_images=0,
        num_audios=0,
    )


def _generate_completion(payload: dict[str, Any]) -> dict[str, Any]:
    if STATE.model is None or STATE.processor is None:
        raise RuntimeError("model is not loaded")

    messages = payload.get("messages") or []
    prompt = _build_prompt(messages)
    max_tokens = _safe_int(payload.get("max_tokens"), 256)
    temperature = _safe_float(payload.get("temperature"), 0.7)
    top_p = _safe_float(payload.get("top_p"), 1.0)

    result = generate(
        STATE.model,
        STATE.processor,
        prompt,
        verbose=False,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
    )

    response_text = result.text or ""
    request_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    return {
        "id": request_id,
        "object": "chat.completion",
        "created": int(_now()),
        "model": STATE.configured_model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": response_text},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.generation_tokens,
            "total_tokens": result.total_tokens,
        },
    }


@app.get("/health")
async def health() -> dict[str, Any]:
    return build_health_payload()


@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    return build_health_payload()


@app.get("/ping")
async def ping() -> dict[str, Any]:
    return {"ok": True}


@app.get("/ready")
async def ready() -> JSONResponse:
    ready_state = STATE.lifecycle == "ready"
    body = {
        "ready": ready_state,
        "status": STATE.lifecycle,
        "model_lifecycle": STATE.lifecycle,
        "adapter": "mlx-vlm",
        "configured_model": STATE.configured_model,
        "loaded_model": STATE.loaded_model,
        "reason": None if ready_state else STATE.last_error_message or "model_not_ready",
    }
    return JSONResponse(content=body, status_code=200 if ready_state else 503)


@app.get("/runtime")
async def runtime() -> dict[str, Any]:
    return {
        "runner": "whooshd",
        "adapter": "mlx-vlm",
        "configured_model": STATE.configured_model,
        "loaded_model": STATE.loaded_model,
        "lifecycle_state": STATE.lifecycle,
        "loaded": STATE.loaded,
        "warming": STATE.lifecycle == "warming",
        "last_load_started_at": STATE.last_load_started_at,
        "last_load_completed_at": STATE.last_load_completed_at,
        "last_unloaded_at": STATE.last_unloaded_at,
        "last_error_message": STATE.last_error_message,
    }


@app.get("/runtime/model")
async def runtime_model() -> dict[str, Any]:
    return {
        "adapter": "mlx-vlm",
        "configured_model": STATE.configured_model,
        "loaded_model": STATE.loaded_model,
        "lifecycle_state": STATE.lifecycle,
        "loaded": STATE.loaded,
        "warming": STATE.lifecycle == "warming",
        "last_load_started_at": STATE.last_load_started_at,
        "last_load_completed_at": STATE.last_load_completed_at,
        "last_unloaded_at": STATE.last_unloaded_at,
        "last_error_code": None,
        "last_error_message": STATE.last_error_message,
    }


@app.post("/runtime/model/warmup")
async def runtime_model_warmup() -> dict[str, Any]:
    try:
        await ensure_loaded()
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"error": str(exc)})
    return {
        "ok": True,
        "model": STATE.configured_model,
        "lifecycle_state": STATE.lifecycle,
        "loaded": STATE.loaded,
    }


@app.post("/runtime/model/unload")
async def runtime_model_unload() -> dict[str, Any]:
    unload_model()
    return {"ok": True, "model": STATE.configured_model, "lifecycle_state": STATE.lifecycle}


@app.get("/models")
async def models() -> dict[str, Any]:
    return {"models": [build_model_entry()]}


@app.get("/v1/models")
async def v1_models() -> dict[str, Any]:
    return {"object": "list", "data": [build_model_entry()]}


@app.get("/api/tags")
async def api_tags() -> dict[str, Any]:
    return {"models": [build_tags_entry()]}


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    payload = await request.json()
    try:
        await ensure_loaded()
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"error": str(exc)})

    if payload.get("stream"):
        request_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"

        async def event_stream():
            response = await asyncio.to_thread(_generate_completion, payload)
            content = (
                response["choices"][0]["message"]["content"] or ""
            )
            created = response["created"]
            model = response["model"]
            yield (
                "data: "
                + json.dumps(
                    {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model,
                        "choices": [
                            {"index": 0, "delta": {"role": "assistant"}}
                        ],
                    }
                )
                + "\n\n"
            )
            for segment in _chunk_text(content, 1024):
                yield (
                    "data: "
                    + json.dumps(
                        {
                            "id": request_id,
                            "object": "chat.completion.chunk",
                            "created": created,
                            "model": model,
                            "choices": [
                                {"index": 0, "delta": {"content": segment}}
                            ],
                        }
                    )
                    + "\n\n"
                )
            yield (
                "data: "
                + json.dumps(
                    {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model,
                        "choices": [
                            {"index": 0, "delta": {}, "finish_reason": "stop"}
                        ],
                    }
                )
                + "\n\n"
            )
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    response = await asyncio.to_thread(_generate_completion, payload)
    return JSONResponse(content=response)


@app.get("/")
async def root() -> dict[str, Any]:
    return {"ok": True, "runner": "whooshd", "adapter": "mlx-vlm"}
