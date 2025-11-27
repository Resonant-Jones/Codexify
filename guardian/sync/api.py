import json
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from . import models
from .bus import bus

router = APIRouter()


@router.get("/health/sync")
def health_sync():
    return {"status": "ok"}


@router.post("/api/sync/event")
async def post_event(event: Dict[str, Any]):
    # Expected: {event_id, type, payload}
    event_id = str(event.get("event_id") or "").strip()
    ev_type = str(event.get("type") or "").strip()
    payload = event.get("payload") or {}
    if not event_id or not ev_type:
        raise HTTPException(
            status_code=400, detail="event_id and type are required"
        )

    is_new = models.record_event(event_id, ev_type, payload)

    # Apply idempotent upsert side-effects based on ev_type
    try:
        if ev_type in ("thread.update", "thread.state"):
            thread_id = str(
                payload.get("thread_id") or payload.get("id") or ""
            ).strip()
            if thread_id:
                models.upsert_thread_state(thread_id, payload)
        elif ev_type in ("persona.set", "persona.selection"):
            user_id = str(payload.get("user_id") or "default")
            persona = str(payload.get("persona") or "Default")
            models.upsert_persona(user_id, persona)
        elif ev_type in ("codex.result", "codex.upsert"):
            rid = (
                str(payload.get("result_id") or payload.get("id") or "").strip()
                or event_id
            )
            content = str(payload.get("content") or json.dumps(payload))
            meta = payload.get("meta") or {}
            models.upsert_codex_result(rid, content, meta)
    except Exception:
        # Side-effects must not break idempotent acknowledgement
        pass

    await bus.publish(
        {"event_id": event_id, "type": ev_type, "payload": payload}
    )
    return {"ok": True, "idempotent": not is_new}


@router.get("/api/sync/subscribe")
async def subscribe_events():
    async def event_stream():
        async for msg in bus.subscribe():
            yield f"data: {json.dumps(msg)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
