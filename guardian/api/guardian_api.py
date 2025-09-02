"""
Minimal provider-agnostic FastAPI app exposing capabilities, chat (sync/stream), and embeddings.
"""
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
from typing import Iterator, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from guardian.providers.registry import ProviderRegistry


app = FastAPI(title="Guardian API", version="1.0")
providers = ProviderRegistry()


def require_api_key(x_api_key: Optional[str] = Query(None, alias="X-API-Key")):
    """Simple query-param API key guard (X-API-Key), per acceptance checks."""
    expected = os.getenv("GUARDIAN_API_KEY")
    if expected and x_api_key != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


@app.get("/capabilities", tags=["Diag"])
def capabilities(_: None = Depends(require_api_key)):
    return providers.capabilities()


class ChatBody(BaseModel):
    prompt: str
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None


@app.post("/chat", tags=["Chat"])
def chat(body: ChatBody, _: None = Depends(require_api_key)):
    chat = providers.get_chat(body.provider)
    try:
        extra = {k: v for k, v in {
            "temperature": body.temperature,
            "top_p": body.top_p,
            "max_tokens": body.max_tokens,
        }.items() if v is not None}
        text = chat.generate(body.prompt, model=body.model, **extra)
        return {"provider": chat.name, "model": body.model, "text": text}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Upstream error ({chat.name}): {e}")


@app.get("/chat/stream", tags=["Chat"])
def chat_stream(
    prompt: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    max_tokens: Optional[int] = None,
    _: None = Depends(require_api_key),
):
    chat = providers.get_chat(provider)
    extra = {k: v for k, v in {
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
    }.items() if v is not None}

    def gen() -> Iterator[bytes]:
        try:
            for token in chat.stream(prompt, model=model, **extra):
                yield f"data: {token}\n\n".encode("utf-8")
            yield b"data: [DONE]\n\n"
        except Exception as e:
            yield f"event: error\ndata: {chat.name} upstream error: {e}\n\n".encode("utf-8")

    return StreamingResponse(gen(), media_type="text/event-stream")


class EmbeddingsBody(BaseModel):
    texts: List[str]
    embedder: Optional[str] = None
    model: Optional[str] = None


@app.post("/embeddings", tags=["Embeddings"])
def embeddings(body: EmbeddingsBody, _: None = Depends(require_api_key)):
    emb = providers.get_embeddings(body.embedder)
    try:
        vecs = emb.embed(body.texts, model=body.model)
        return {"provider": emb.name, "model": body.model, "vectors": vecs}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Upstream error ({emb.name}): {e}")


@app.get("/healthz", tags=["Diag"])
def healthz():
    return {"ok": True}

