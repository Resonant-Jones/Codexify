"""
Tools Routes
~~~~~~~~~~~~

Minimal tools execution dispatcher and job status endpoints.
"""

import logging
from typing import Any, Dict
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# In-memory job registry (ok for dev; replace with persistent store for prod)
JOBS: Dict[str, Dict[str, Any]] = {}


class ToolRequest(BaseModel):
    name: str
    args: dict = Field(default_factory=dict)


class ToolResponse(BaseModel):
    job_id: str


class JobStatus(BaseModel):
    job_id: str
    status: str
    result: dict = Field(default_factory=dict)


# Import shared dependencies from core module (avoids circular imports)
try:
    from guardian.core.dependencies import require_api_key
except ImportError:
    # Fallback for standalone usage
    def require_api_key(api_key: str = None):
        return api_key


router = APIRouter(prefix="/tools", tags=["Tools"])


@router.post("/execute", response_model=ToolResponse)
def tools_execute(body: ToolRequest, api_key: str = Depends(require_api_key)):
    """
    Minimal tools dispatcher. For now, just echoes args and marks job done.
    Replace with real tool routing/execution as needed.

    Args:
        body: Tool execution request with name and arguments

    Returns:
        Job ID for tracking execution
    """
    jid = str(uuid4())
    # Example: no-op tool that returns provided args
    result = {"ok": True, "tool": body.name, "args": body.args}
    JOBS[jid] = {"status": "done", "result": result}
    logger.info("Tools.execute: %s job_id=%s", body.name, jid)
    return {"job_id": jid}
