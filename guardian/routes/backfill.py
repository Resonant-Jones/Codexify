"""
Backfill status routes.

Expose lightweight status snapshots for embedding and graph backfills.
"""

import logging

from fastapi import APIRouter, Depends

from guardian.core.dependencies import require_api_key
from guardian.workers.backfill_status import get_backfill_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/backfill", tags=["Backfill"])


@router.get("/status")
async def backfill_status(api_key: str = Depends(require_api_key)):
    """Return the latest backfill status snapshot."""
    return get_backfill_status()
