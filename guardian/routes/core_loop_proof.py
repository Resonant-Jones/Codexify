"""Experimental core-loop proof route.

The route is schema-hidden and flag-gated at runtime so the supported chat
surface stays untouched unless an operator explicitly opts in.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, PositiveInt, field_validator

from guardian.core import dependencies
from guardian.core.core_loop_proof import run_core_loop_proof
from guardian.core.dependencies import (
    RequestUserScope,
    get_request_user_scope,
    require_api_key,
)

router = APIRouter(
    prefix="/api/core-loop",
    tags=["Core Loop Proof"],
    dependencies=[Depends(require_api_key)],
)


class CoreLoopProofRetrievalRequest(BaseModel):
    enabled: bool = True
    query: str | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("query", mode="before")
    @classmethod
    def _normalize_query(cls, value: Any) -> Any:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class CoreLoopProofRequest(BaseModel):
    thread_id: PositiveInt | None = None
    message: str = Field(..., max_length=12_000)
    provider_hint: str | None = Field(default=None, max_length=128)
    retrieval: CoreLoopProofRetrievalRequest = Field(
        default_factory=CoreLoopProofRetrievalRequest
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("message", mode="before")
    @classmethod
    def _normalize_message(cls, value: Any) -> Any:
        text = str(value or "")
        if not text.strip():
            raise ValueError("message is required")
        return text

    @field_validator("provider_hint", mode="before")
    @classmethod
    def _normalize_provider_hint(cls, value: Any) -> Any:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


@router.post("/proof", include_in_schema=False)
async def core_loop_proof(
    body: CoreLoopProofRequest = Body(...),
    request: Request = None,
    request_id: str | None = Header(default=None, alias="X-Request-ID"),
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
) -> JSONResponse:
    if request is not None:
        request_id = request_id or getattr(request.state, "request_id", None)

    result = await run_core_loop_proof(
        chatlog_db=dependencies.chatlog_db,
        request_user_scope=request_user_scope,
        message=body.message,
        thread_id=body.thread_id,
        provider_hint=body.provider_hint,
        retrieval_enabled=bool(body.retrieval.enabled),
        retrieval_query=body.retrieval.query,
        request_id=request_id,
    )
    return JSONResponse(status_code=int(result.pop("http_status", 200)), content=result)


__all__ = ["router", "CoreLoopProofRequest", "CoreLoopProofRetrievalRequest"]
