import json
import os
from typing import Any, Dict, List, Optional

from backend.rag.embedder import Embedder

DEFAULT_NAMESPACE = "global"


def _normalize_namespace(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _metadata_namespace(meta: Dict[str, Any]) -> str:
    explicit = _normalize_namespace(meta.get("namespace"))
    if explicit:
        return explicit

    thread_id = _normalize_namespace(meta.get("thread_id"))
    if thread_id:
        return f"thread:{thread_id}"

    project_id = _normalize_namespace(meta.get("project_id"))
    if project_id:
        return f"project:{project_id}"

    return DEFAULT_NAMESPACE


def _coerce_chroma_metadata(meta: Dict[str, Any]) -> Dict[str, Any]:
    coerced: Dict[str, Any] = {}
    for key, value in meta.items():
        if value is None or isinstance(value, (str, int, float, bool)):
            coerced[key] = value
            continue
        if isinstance(value, (list, tuple, set)):
            normalized = [str(item) for item in value if item is not None]
            coerced[key] = json.dumps(normalized, ensure_ascii=False)
            continue
        if isinstance(value, dict):
            coerced[key] = json.dumps(value, ensure_ascii=False, default=str)
            continue
        coerced[key] = str(value)
    return coerced


class VectorStore:
    def __init__(self, index_dir: Optional[str] = None) -> None:
        # index_dir is kept for backward compatibility but not used for Chroma path (which comes from env)
        store = os.getenv("CODEXIFY_VECTOR_STORE", "faiss").strip().lower()
        if store not in ("faiss", "chroma"):
            store = "faiss"
        self.store = store
        chroma_path = (
            os.getenv("CODEXIFY_CHROMA_PATH", "./.chroma").strip()
            or "./.chroma"
        )
        collection = (
            os.getenv("CODEXIFY_COLLECTION", "codexify_vault").strip()
            or "codexify_vault"
        )
        self.embedder = Embedder(
            store=store,
            chroma_path=chroma_path,
            collection=collection,
        )

    def add_texts(self, items: List[Dict[str, Any]]) -> int:
        texts = [i.get("text", "") for i in items]
        metas: List[Dict[str, Any]] = []
        for item in items:
            raw_meta = item.get("meta", {})
            meta = dict(raw_meta) if isinstance(raw_meta, dict) else {}
            if "namespace" not in meta:
                top_level_namespace = _normalize_namespace(
                    item.get("namespace")
                )
                if top_level_namespace:
                    meta["namespace"] = top_level_namespace
            meta["namespace"] = _metadata_namespace(meta)
            if self.store == "chroma":
                meta = _coerce_chroma_metadata(meta)
            metas.append(meta)

        # Use embed_and_index which handles embedding and storage
        self.embedder.embed_and_index(texts, metadatas=metas)
        return len(items)

    def search(
        self,
        query: str,
        k: int = 5,
        *,
        namespace: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        normalized_namespace = _normalize_namespace(namespace)
        try:
            return self.embedder.search(
                query,
                k=k,
                namespace=normalized_namespace,
            )
        except TypeError:
            # Backward compatibility for alternate embedder implementations.
            return self.embedder.search(query, k=k)

    def health(self) -> Dict[str, Any]:
        try:
            # Simple health check by embedding a dummy string
            self.embedder.embed_texts(["health_check"])
            return {
                "status": "ok",
                "backend": getattr(self.embedder, "store", "unknown"),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
