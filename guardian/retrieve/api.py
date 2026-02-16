from typing import Any, Dict

from fastapi import APIRouter

from guardian.vector.store import VectorStore

router = APIRouter()
_store = VectorStore()


@router.get("/health/vector")
def health_vector():
    return _store.health()


@router.post("/api/retrieve")
def retrieve(body: Dict[str, Any]):
    q = str(body.get("q") or "").strip()
    k = int(body.get("k") or 5)
    namespace = body.get("namespace")
    if q and namespace:
        matches = _store.search(q, k=k, namespace=str(namespace))
    else:
        matches = _store.search(q, k=k) if q else []
    return {"matches": matches}
