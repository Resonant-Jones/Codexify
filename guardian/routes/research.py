from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from guardian.research import perform_research  # Ensure this function exists and works

router = APIRouter()

class ResearchRequest(BaseModel):
    query: str
    sources: list[str] = []

@router.post("/research")
async def research_handler(request: ResearchRequest):
    try:
        result = perform_research(request.query, request.sources)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
