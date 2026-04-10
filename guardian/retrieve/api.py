from typing import Any, Dict

from fastapi import APIRouter

from guardian.core.dependencies import get_vector_store

router = APIRouter()


@router.get("/health/vector")
def health_vector():
    return get_vector_store().health()


@router.post("/api/retrieve")
def retrieve(body: Dict[str, Any]):
    q = str(body.get("q") or "").strip()
    k = int(body.get("k") or 5)
    namespace = body.get("namespace")
    store = get_vector_store()
    if q and namespace:
        matches = store.search(q, k=k, namespace=str(namespace))
    else:
        matches = store.search(q, k=k) if q else []
    return {"matches": matches}
