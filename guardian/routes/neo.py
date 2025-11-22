"""
Neo4j Graph Logging Routes
~~~~~~~~~~~~~~~~~~~~~~~~~~

Provides a safe stub for message graph logging that always responds with 200.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from guardian.core.config import Settings, get_settings

router = APIRouter(prefix="/neo", tags=["neo"])


class GraphMessageRequest(BaseModel):
    thread_id: str | None = None
    message_id: str | None = None
    text: str | None = None
    metadata: dict | None = None


@router.post("/graph-message")
async def graph_message(
    payload: GraphMessageRequest | None = None,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    Safely handle a request to graph a user message.

    Current behaviour:
    - If graph logging is disabled, no-op and return status=disabled.
    - If enabled, acknowledge acceptance (future wiring to Neo4j).
    - Errors should not surface as 5xx; return 'unavailable' instead.
    """
    if not settings.GUARDIAN_ENABLE_GRAPH_LOGGING:
        return {"status": "disabled", "reason": "graph logging disabled in settings"}

    try:
        return {"status": "accepted", "mode": settings.GUARDIAN_GRAPH_LOGGING_MODE}
    except Exception as exc:  # pragma: no cover - defensive
        return {"status": "unavailable", "error": str(exc)}
