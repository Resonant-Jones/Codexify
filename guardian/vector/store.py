import json
from typing import Any, Dict, List, Optional

from backend.rag.embedder import Embedder
from guardian.core.config import resolve_vector_store_runtime

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


def _metadata_user_id(meta: Dict[str, Any]) -> Optional[str]:
    explicit = _normalize_namespace(meta.get("user_id"))
    if explicit:
        return explicit
    owner_user_id = _normalize_namespace(meta.get("owner_user_id"))
    if owner_user_id:
        return owner_user_id
    return _normalize_namespace(meta.get("actor_user_id"))


def _default_user_id() -> str:
    from guardian.core.dependencies import get_single_user_id

    return str(get_single_user_id())


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
        # index_dir is kept for backward compatibility while runtime resolution
        # is centralized through guardian.core.config.
        _ = index_dir
        runtime = resolve_vector_store_runtime()
        self.runtime = runtime
        self.store = runtime.backend
        self.chroma_path = runtime.chroma_path
        self.collection = runtime.collection

        shared_store = None
        try:  # pragma: no cover - import cycle guard
            from guardian.core import dependencies as core_dependencies

            shared_store = getattr(core_dependencies, "_vector_store", None)
        except Exception:
            shared_store = None

        if (
            shared_store is not None
            and shared_store is not self
            and getattr(shared_store, "runtime", None) is not None
            and getattr(shared_store.runtime, "as_dict", None) is not None
            and shared_store.runtime.as_dict() == self.runtime.as_dict()
            and getattr(shared_store, "_embedder_factory_token", None)
            == id(Embedder)
        ):
            self.embedder = shared_store.embedder
            self._embedder_factory_token = id(Embedder)
            return

        self.embedder = Embedder(
            store=self.store,
            chroma_path=self.chroma_path,
            collection=self.collection,
        )
        self._embedder_factory_token = id(Embedder)

    def describe_runtime(self) -> Dict[str, str]:
        return self.runtime.as_dict()

    def add_texts(self, items: List[Dict[str, Any]]) -> int:
        texts = [i.get("text", "") for i in items]
        metas: List[Dict[str, Any]] = []
        ids: List[str] = []
        include_ids = self.store == "chroma"
        for item in items:
            item_id = item.get("id")
            if include_ids:
                if item_id:
                    ids.append(str(item_id))
                else:
                    include_ids = False
            raw_meta = item.get("meta", {})
            meta = dict(raw_meta) if isinstance(raw_meta, dict) else {}
            if "namespace" not in meta:
                top_level_namespace = _normalize_namespace(
                    item.get("namespace")
                )
                if top_level_namespace:
                    meta["namespace"] = top_level_namespace
            meta["namespace"] = _metadata_namespace(meta)
            if "user_id" not in meta:
                normalized_user_id = _normalize_namespace(item.get("user_id"))
                if normalized_user_id:
                    meta["user_id"] = normalized_user_id
                else:
                    fallback_user_id = _metadata_user_id(meta)
                    if fallback_user_id:
                        meta["user_id"] = fallback_user_id
                    else:
                        meta["user_id"] = _normalize_namespace(
                            _default_user_id()
                        )
            if self.store == "chroma":
                meta = _coerce_chroma_metadata(meta)
            metas.append(meta)

        # Use embed_and_index which handles embedding and storage
        embed_kwargs = {"metadatas": metas}
        if include_ids and ids:
            embed_kwargs["ids"] = ids
        try:
            self.embedder.embed_and_index(texts, **embed_kwargs)
        except TypeError:
            # Backward compatibility for lighter-weight test doubles and
            # older embedder implementations that do not accept ids.
            self.embedder.embed_and_index(texts, metadatas=metas)
        return len(items)

    def search(
        self,
        query: str,
        k: int = 5,
        *,
        namespace: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        normalized_namespace = _normalize_namespace(namespace)
        normalized_user_id = _normalize_namespace(user_id)
        if not normalized_user_id:
            normalized_user_id = _normalize_namespace(_default_user_id())
        if not normalized_user_id:
            raise ValueError("VectorStore.search requires user_id")
        try:
            return self.embedder.search(
                query,
                k=k,
                namespace=normalized_namespace,
                user_id=normalized_user_id,
            )
        except TypeError:
            # Backward compatibility for alternate embedder implementations.
            try:
                results = self.embedder.search(
                    query,
                    k=k,
                    namespace=normalized_namespace,
                )
            except TypeError:
                results = self.embedder.search(query, k=k)
            if not isinstance(results, list):
                return []
            return [
                item
                for item in results
                if _normalize_namespace(
                    (item.get("metadata") or {}).get("user_id")
                    or (item.get("metadata") or {}).get("owner_user_id")
                    or item.get("user_id")
                    or item.get("owner_user_id")
                )
                == normalized_user_id
            ]

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

    def prune_source_root(self, source_root: str, keep_ids: set[str]) -> int:
        if self.store != "chroma":
            return 0
        root = (source_root or "").strip()
        if not root:
            return 0
        existing_ids = self.embedder.get_ids(where={"source_root": root})
        if not existing_ids:
            return 0
        keep = {str(value) for value in keep_ids if str(value).strip()}
        stale = [value for value in existing_ids if value not in keep]
        if not stale:
            return 0
        return self.embedder.delete_by_ids(stale)

    def delete_by_doc_id(self, doc_id: str) -> int:
        """Delete all chunks for a document by doc_id metadata.

        Args:
            doc_id: The document ID to delete chunks for.

        Returns:
            Number of chunks deleted.
        """
        if self.store != "chroma":
            return 0
        doc_id = (doc_id or "").strip()
        if not doc_id:
            return 0
        existing_ids = self.embedder.get_ids(where={"doc_id": doc_id})
        if not existing_ids:
            return 0
        return self.embedder.delete_by_ids(existing_ids)
