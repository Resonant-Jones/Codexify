from typing import Any, Dict

from fastapi import APIRouter

from guardian.core.dependencies import get_single_user_id, get_vector_store

router = APIRouter()


@router.get("/health/vector")
def health_vector():
    return get_vector_store().health()


@router.post("/api/retrieve")
def retrieve(body: Dict[str, Any]):
    q = str(body.get("q") or "").strip()
    k = int(body.get("k") or 5)
    namespace = body.get("namespace")
    user_id = str(body.get("user_id") or "").strip() or get_single_user_id()
    store = get_vector_store()
    if q and namespace:
        matches = store.search(
            q,
            k=k,
            namespace=str(namespace),
            user_id=user_id,
        )
    else:
        matches = store.search(q, k=k, user_id=user_id) if q else []
    return {"matches": matches}
