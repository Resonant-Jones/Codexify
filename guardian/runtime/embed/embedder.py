from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List, Optional

# Optional deps; import lazily where possible
try:
    from openai import OpenAI  # type: ignore
except Exception:
    OpenAI = None  # type: ignore

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
except Exception:
    SentenceTransformer = None  # type: ignore

import numpy as np  # required by FAISS path

try:
    import faiss  # type: ignore
except Exception:
    faiss = None  # type: ignore

try:
    import chromadb  # type: ignore
except Exception:
    chromadb = None  # type: ignore

DEFAULT_LOCAL_MODEL = os.getenv(
    "CODEXIFY_LOCAL_MODEL", "BAAI/bge-large-en-v1.5"
)
DEFAULT_OPENAI_MODEL = os.getenv(
    "CODEXIFY_OPENAI_MODEL", "text-embedding-3-large"
)
DEFAULT_STORE = os.getenv(
    "CODEXIFY_VECTOR_STORE", "chroma"
)  # 'chroma' | 'faiss'
CHROMA_PATH = os.getenv("CODEXIFY_CHROMA_PATH", "./.chroma")
COLLECTION = os.getenv("CODEXIFY_COLLECTION", "codexify_vault")
MAX_EMBED_CHARS = int(os.getenv("CODEXIFY_MAX_EMBED_CHARS", "16000"))


def _batched(seq: Iterable[str], batch_size: int = 64):
    buf: list[str] = []
    for s in seq:
        buf.append(s)
        if len(buf) >= batch_size:
            yield buf
            buf = []
    if buf:
        yield buf


class CodexifyEmbedder:
    def __init__(
        self,
        use_openai: bool = True,
        model: str | None = None,
        store: str | None = None,
        chroma_path: str | None = None,
        collection: str | None = None,
    ):
        self.use_openai = use_openai
        self.model_name = model or (
            DEFAULT_OPENAI_MODEL if use_openai else DEFAULT_LOCAL_MODEL
        )
        # Resolve configuration from env if not provided
        self.store = (
            store or os.getenv("CODEXIFY_VECTOR_STORE", "chroma")
        ).lower()
        self.chroma_path = chroma_path or os.getenv(
            "CODEXIFY_CHROMA_PATH", "./.chroma"
        )
        self.collection = collection or os.getenv(
            "CODEXIFY_COLLECTION", "codexify_vault"
        )

        self._client = None
        self._local_model = None
        self._chroma_client = None
        self._chroma_collection = None

        if self.use_openai:
            if OpenAI is None:
                raise RuntimeError(
                    "OpenAI client not installed. `pip install openai>=1.0`"
                )
            self._client = OpenAI()
        else:
            if SentenceTransformer is None:
                raise RuntimeError("sentence-transformers not installed.")
            self._local_model = SentenceTransformer(self.model_name)

        if self.store not in ("chroma", "faiss"):
            raise ValueError("VECTOR_STORE must be 'chroma' or 'faiss'")

        if self.store == "chroma":
            if chromadb is None:
                raise RuntimeError("chromadb not installed.")
            # Initialize persistent client and collection
            self._chroma_client = chromadb.PersistentClient(
                path=self.chroma_path
            )
            self._chroma_collection = (
                self._chroma_client.get_or_create_collection(
                    name=self.collection
                )
            )
        if self.store == "faiss" and faiss is None:
            raise RuntimeError("faiss-cpu not installed.")

    # ---- Embeddings ----
    def _embed_batch_openai(self, texts: list[str]) -> list[list[float]]:
        # Ensure no text exceeds model context length (in tokens) by clamping by characters.
        # 16k chars is well under the 8k-token limit for typical English text.
        safe_texts = [
            t if len(t) <= MAX_EMBED_CHARS else t[:MAX_EMBED_CHARS]
            for t in texts
        ]
        resp = self._client.embeddings.create(
            model=self.model_name, input=safe_texts
        )
        data_sorted = sorted(resp.data, key=lambda d: d.index)
        return [d.embedding for d in data_sorted]

    def _embed_batch_local(self, texts: list[str]) -> list[list[float]]:
        assert self._local_model is not None
        vecs = self._local_model.encode(
            texts,
            batch_size=64,
            convert_to_numpy=False,
            show_progress_bar=False,
        )
        return [v.tolist() for v in vecs]

    def embed_texts(
        self, texts: list[str], batch_size: int = 64
    ) -> list[list[float]]:
        embeddings: list[list[float]] = []
        for chunk in _batched(texts, batch_size):
            if self.use_openai:
                embeddings.extend(self._embed_batch_openai(chunk))
            else:
                embeddings.extend(self._embed_batch_local(chunk))
        return embeddings

    # ---- Stores ----
    def _store_chroma(
        self,
        docs: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]] | None = None,
        ids_prefix: str = "doc",
    ):
        # Use the persistent collection initialized in __init__
        if self._chroma_collection is None:
            raise RuntimeError("Chroma collection not initialized")

        ids = [f"{ids_prefix}_{i}" for i in range(len(docs))]
        self._chroma_collection.add(
            documents=docs, embeddings=embeddings, metadatas=metadatas, ids=ids
        )

    def _store_faiss(
        self,
        docs: list[str],
        embeddings: list[list[float]],
        index_path: str = "codexify_index.faiss",
        docs_path: str = "faiss_docs.txt",
    ):
        arr = np.array(embeddings, dtype="float32")
        dim = arr.shape[1]
        index = faiss.IndexFlatL2(dim)
        index.add(arr)
        faiss.write_index(index, index_path)
        with open(docs_path, "w", encoding="utf-8") as f:
            for d in docs:
                f.write(d.replace("\n", "\\n") + "\n")

    # ---- Public ----
    def embed_and_index(
        self,
        docs: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        ids_prefix: str = "doc",
    ):
        vecs = self.embed_texts(docs)
        if self.store == "chroma":
            self._store_chroma(
                docs, vecs, metadatas=metadatas, ids_prefix=ids_prefix
            )
            return {
                "store": "chroma",
                "path": self.chroma_path,
                "collection": self.collection,
                "count": len(docs),
            }
        else:
            self._store_faiss(docs, vecs)
            return {
                "store": "faiss",
                "index": "codexify_index.faiss",
                "count": len(docs),
            }

    def search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Search the vector store for the query."""
        if self.store != "chroma":
            raise NotImplementedError(
                "Search only implemented for ChromaDB currently."
            )

        if self._chroma_collection is None:
            raise RuntimeError("Chroma collection not initialized")

        # Embed the query
        query_embeddings = self.embed_texts([query])

        # Query Chroma
        results = self._chroma_collection.query(
            query_embeddings=query_embeddings, n_results=k
        )

        # Format results to match the expected output structure
        # Chroma returns lists of lists (one per query), we only have one query
        formatted_results = []

        if results and results["documents"]:
            # Unpack the first (and only) query result
            docs = results["documents"][0]
            metas = (
                results["metadatas"][0]
                if results["metadatas"]
                else [{}] * len(docs)
            )
            distances = (
                results["distances"][0]
                if results["distances"]
                else [0.0] * len(docs)
            )

            for doc, meta, dist in zip(docs, metas, distances):
                formatted_results.append(
                    {
                        "text": doc,
                        "meta": meta,
                        "score": 1.0
                        - dist,  # Convert distance to similarity score roughly
                    }
                )

        return formatted_results


def embed_file(
    path: str = "chunked_docs.txt",
    use_openai: bool | None = None,
    model: str | None = None,
    store: str = DEFAULT_STORE,
    chroma_path: str = CHROMA_PATH,
    collection: str = COLLECTION,
):
    if not os.path.exists(path):
        raise FileNotFoundError(f"No such file: {path}")
    with open(path, encoding="utf-8") as f:
        contents = f.read()
    docs = [d.strip() for d in contents.split("\n\n") if d.strip()]
    use_openai = (
        bool(int(os.getenv("CODEXIFY_USE_OPENAI", "1")))
        if use_openai is None
        else use_openai
    )
    emb = CodexifyEmbedder(
        use_openai=use_openai,
        model=model,
        store=store,
        chroma_path=chroma_path,
        collection=collection,
    )
    return emb.embed_and_index(
        docs, ids_prefix=os.path.basename(path).replace(".", "_")
    )
