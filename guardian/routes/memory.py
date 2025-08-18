from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()

class MemoryInput(BaseModel):
    input: str
    thread_id: str | None = None
    mode: str | None = "default"

@router.post("/memory")
async def memory_handler(data: MemoryInput, request: Request):
    # Placeholder for now — you can wire this up to your actual logic later
    return {
        "message": "Memory endpoint received.",
        "input": data.input,
        "thread_id": data.thread_id,
        "mode": data.mode
    }
