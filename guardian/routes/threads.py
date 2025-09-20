from fastapi import APIRouter

from guardian.threads_structure.threads import (  # import your logic function
    get_thread_summary,
)

router = APIRouter()


@router.get("/threads/{thread_id}/summary")
def thread_summary(thread_id: str):
    return get_thread_summary(thread_id)
