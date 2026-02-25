<<<<<<< HEAD
import logging
=======
>>>>>>> 17ac719d (fix(embed): gate LOCAL_EMBED_MODEL checks behind CODEXIFY_EMBEDDINGS_BACKEND=local)
import os

import chromadb
from chromadb.config import Settings
from chromadb.utils.embedding_functions.ollama_embedding_function import (
    OllamaEmbeddingFunction,
)

<<<<<<< HEAD
logger = logging.getLogger(__name__)


def _is_local_embeddings_backend() -> bool:
    backend = (os.getenv("CODEXIFY_EMBEDDINGS_BACKEND") or "").strip().lower()
    return backend == "local"


def _get_local_embed_model(*, strict: bool) -> str | None:
    model = (os.getenv("LOCAL_EMBED_MODEL") or "").strip()
    if strict and not model:
        raise ValueError("LOCAL_EMBED_MODEL is not set for Ollama embeddings.")
    return model or None
=======
from guardian.utils.embed_paths import get_local_embed_model
>>>>>>> 17ac719d (fix(embed): gate LOCAL_EMBED_MODEL checks behind CODEXIFY_EMBEDDINGS_BACKEND=local)


class VectorSearch:
    def __init__(
        self,
        model: str | None = None,
        name="new_collection",
        path: str = "./db",
    ):
<<<<<<< HEAD
        if model:
            logger.warning(
                "[rag] model override ignored; use LOCAL_EMBED_MODEL"
            )
        is_local = _is_local_embeddings_backend()
        model = _get_local_embed_model(strict=is_local)
        if not model:
            model = (os.getenv("OLLAMA_EMBED_MODEL") or "").strip()
        if not model:
            model = "nomic-embed-text"
        logger.info("[rag] local embedding model=%s", model)
=======
        backend = (
            (os.getenv("CODEXIFY_EMBEDDINGS_BACKEND") or "mock").strip().lower()
        )
        if backend != "local":
            _ = get_local_embed_model(strict=False)

>>>>>>> 17ac719d (fix(embed): gate LOCAL_EMBED_MODEL checks behind CODEXIFY_EMBEDDINGS_BACKEND=local)
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
        except:
            self.collection = self.client.get_collection(name=name)

    def add_document(self, documents: str, id: str, metadatas: None = None):
        if metadatas == None:
            self.collection.add(documents=documents, ids=id)
        else:
            self.collection.add(
                documents=documents, ids=id, metadatas=metadatas
            )

    def query(self, query: str, k: int):
        return self.collection.query(query_texts=query, n_results=k)

    def reset(self):
        self.client.reset()
