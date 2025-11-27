# guardian/api_exports.py
import logging
from typing import Any, Iterable

import orjson
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from guardian.core import db
from guardian.core.auth import AuthenticatedUser, require_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/exports",
    tags=["exports"],
)


def _serialize_chunk(row: Any) -> bytes:
    """
    Normalize the backend row into NDJSON bytes.
    """
    if isinstance(row, bytes):
        return row if row.endswith(b"\n") else row + b"\n"
    if isinstance(row, str):
        payload = row if row.endswith("\n") else row + "\n"
        return payload.encode("utf-8")
    # Fallback: assume a mapping/dict-like object.
    return orjson.dumps(row) + b"\n"


@router.get(
    "/threads.ndjson",
    summary="Download all of the current user's threads as newline‑delimited JSON",
)
def export_threads(user: AuthenticatedUser = Depends(require_user)):
    """Stream every thread the authenticated user can access in NDJSON format."""
    fetch_fn = getattr(db, "fetch_threads_for_user", None)
    if fetch_fn is None:
        logger.error(
            "Active DB backend %s lacks fetch_threads_for_user; cannot export threads",
            type(db),
        )
        raise HTTPException(
            status_code=500, detail="Thread export not available"
        )

    def generate() -> Iterable[bytes]:
        try:
            for row in fetch_fn(user.id):
                try:
                    yield _serialize_chunk(row)
                except Exception as encode_err:
                    logger.exception(
                        "Failed to encode thread row for user %s: %s",
                        user.id,
                        encode_err,
                    )
        except Exception as stream_err:
            logger.exception(
                "Thread export stream failed for user %s: %s",
                user.id,
                stream_err,
            )
            # Re-raise so the client receives a 500 instead of hanging.
            raise

    try:
        return StreamingResponse(
            generate(),
            media_type="application/x-ndjson",
            headers={
                "Content-Disposition": 'attachment; filename="threads.ndjson"'
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "Failed to start thread export for user %s: %s", user.id, exc
        )
        raise HTTPException(
            status_code=500, detail="Failed to start export"
        ) from exc
