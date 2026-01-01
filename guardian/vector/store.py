import json
import os
from typing import Any, Dict, List, Optional

from backend.rag.embedder import Embedder


class VectorStore:
    def __init__(self, index_dir: Optional[str] = None) -> None:
        # index_dir is kept for backward compatibility but not used for Chroma path (which comes from env)
        store = os.getenv("CODEXIFY_VECTOR_STORE", "faiss").strip().lower()
        if store not in ("faiss", "chroma"):
            store = "faiss"
        self.embedder = Embedder(store=store)

    def add_texts(self, items: List[Dict[str, Any]]) -> int:
        texts = [i.get("text", "") for i in items]
        metas = [i.get("meta", {}) for i in items]

        # Use embed_and_index which handles embedding and storage
        self.embedder.embed_and_index(texts, metadatas=metas)
        return len(items)

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
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
