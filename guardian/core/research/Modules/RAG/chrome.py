import logging
import os

import chromadb
from chromadb.config import Settings
from chromadb.utils.embedding_functions.ollama_embedding_function import (
    OllamaEmbeddingFunction,
)

from guardian.utils.embed_paths import get_local_embed_model

logger = logging.getLogger(__name__)


class VectorSearch:
    def __init__(
        self,
        model: str | None = None,
        name: str = "new_collection",
        path: str = "./db",
    ):
        # Historical API accepted `model`, but this project now drives the embed model
        # from env so agents/ops can configure it without code changes.
        if model:
            logger.warning("[rag] model override ignored; configure via env")

        backend = (
            (os.getenv("CODEXIFY_EMBEDDINGS_BACKEND") or "mock").strip().lower()
        )
        strict = backend == "local"

        # Only require LOCAL_EMBED_MODEL when the local embeddings backend is selected.
        model = get_local_embed_model(strict=strict)

        # Back-compat / fallback: allow older env var, then default.
        if not model:
            model = (os.getenv("OLLAMA_EMBED_MODEL") or "").strip() or None
        if not model:
            model = "nomic-embed-text"

        logger.info(
            "[rag] embeddings_backend=%s embed_model=%s", backend, model
        )

        self.client = chromadb.PersistentClient(
            path=path, settings=Settings(allow_reset=True)
        )
        self.embedding = OllamaEmbeddingFunction(
            url="http://localhost:11434", model_name=model
        )
        try:
            self.collection = self.client.create_collection(
                name=name, embedding_function=self.embedding
            )
        except Exception:
            self.collection = self.client.get_collection(name=name)

    def add_document(self, documents: str, id: str, metadatas: None = None):
        if metadatas is None:
            self.collection.add(documents=documents, ids=id)
        else:
            self.collection.add(
                documents=documents, ids=id, metadatas=metadatas
            )

    def query(self, query: str, k: int):
        return self.collection.query(query_texts=query, n_results=k)

    def reset(self):
        self.client.reset()
