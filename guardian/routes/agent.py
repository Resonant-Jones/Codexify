from fastapi import APIRouter

router = APIRouter()

@router.get("/agent/ping")
async def ping_agent():
    return {"status": "Agent is active."}
