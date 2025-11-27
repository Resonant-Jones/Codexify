You are Codex. Apply the following patch set exactly.

GOAL

- Add a shared embedding runtime (OpenAI or local) with persistent Chroma (and optional FAISS).
- Expose two CLI commands:
  1) `embed` — embed and index docs
  2) `embed-diagnose` — quick index health check
- Ensure both show up in the guardian-diag TUI and can run with sensible defaults.

CHANGES

1) Create shared embedder module

File: guardian/runtime/embed/embedder.py
---

from __future__ import annotations
import os
from typing import List, Dict, Any, Iterable, Optional

# Optional deps; import lazily where possible

# OpenAI client (>=1.0)

try:
    from openai import OpenAI  # type: ignore
except Exception:
    OpenAI = None  # type: ignore

# Local embeddings

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
except Exception:
    SentenceTransformer = None  # type: ignore

# Vector stores

import numpy as np  # required by FAISS path
try:
    import faiss  # type: ignore
except Exception:
    faiss = None  # type: ignore

try:
    import chromadb  # type: ignore
except Exception:
    chromadb = None  # type: ignore

DEFAULT_LOCAL_MODEL = os.getenv("CODEXIFY_LOCAL_MODEL", "BAAI/bge-large-en-v1.5")
DEFAULT_OPENAI_MODEL = os.getenv("CODEXIFY_OPENAI_MODEL", "text-embedding-3-large")
DEFAULT_STORE = os.getenv("CODEXIFY_VECTOR_STORE", "chroma")  # 'chroma' | 'faiss'
CHROMA_PATH = os.getenv("CODEXIFY_CHROMA_PATH", "./.chroma")
COLLECTION = os.getenv("CODEXIFY_COLLECTION", "codexify_vault")

def _batched(seq: Iterable[str], batch_size: int = 64):
    buf: List[str] = []
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
        use_openai: bool = False,
        model: Optional[str] = None,
        store: str = DEFAULT_STORE,
        chroma_path: str = CHROMA_PATH,
        collection: str = COLLECTION,
    ):
        self.use_openai = use_openai
        self.model_name = model or (DEFAULT_OPENAI_MODEL if use_openai else DEFAULT_LOCAL_MODEL)
        self.store = store.lower()
        self.chroma_path = chroma_path
        self.collection = collection

        self._client = None
        self._local_model = None

        if self.use_openai:
            if OpenAI is None:
                raise RuntimeError("OpenAI client not installed. `pip install openai>=1.0`")
            self._client = OpenAI()
        else:
            if SentenceTransformer is None:
                raise RuntimeError("sentence-transformers not installed.")
            self._local_model = SentenceTransformer(self.model_name)

        if self.store not in ("chroma", "faiss"):
            raise ValueError("VECTOR_STORE must be 'chroma' or 'faiss'")

        if self.store == "chroma" and chromadb is None:
            raise RuntimeError("chromadb not installed.")
        if self.store == "faiss" and faiss is None:
            raise RuntimeError("faiss-cpu not installed.")

    # ---- Embeddings ----
    def _embed_batch_openai(self, texts: List[str]) -> List[List[float]]:
        resp = self._client.embeddings.create(model=self.model_name, input=texts)
        # preserve input order
        data_sorted = sorted(resp.data, key=lambda d: d.index)
        return [d.embedding for d in data_sorted]

    def _embed_batch_local(self, texts: List[str]) -> List[List[float]]:
        assert self._local_model is not None
        vecs = self._local_model.encode(texts, batch_size=64, convert_to_numpy=False, show_progress_bar=False)
        # vecs is a list/np array per text; normalize to list[list[float]]
        return [v.tolist() for v in vecs]

    def embed_texts(self, texts: List[str], batch_size: int = 64) -> List[List[float]]:
        embeddings: List[List[float]] = []
        for chunk in _batched(texts, batch_size):
            if self.use_openai:
                embeddings.extend(self._embed_batch_openai(chunk))
            else:
                embeddings.extend(self._embed_batch_local(chunk))
        return embeddings

    # ---- Stores ----
    def _store_chroma(
        self,
        docs: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids_prefix: str = "doc",
    ):
        client = chromadb.PersistentClient(path=self.chroma_path)
        coll = client.get_or_create_collection(name=self.collection)
        ids = [f"{ids_prefix}_{i}" for i in range(len(docs))]
        coll.add(documents=docs, embeddings=embeddings, metadatas=metadatas, ids=ids)

    def _store_faiss(
        self,
        docs: List[str],
        embeddings: List[List[float]],
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
        docs: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids_prefix: str = "doc",
    ):
        vecs = self.embed_texts(docs)
        if self.store == "chroma":
            self._store_chroma(docs, vecs, metadatas=metadatas, ids_prefix=ids_prefix)
            return {"store": "chroma", "path": self.chroma_path, "collection": self.collection, "count": len(docs)}
        else:
            self._store_faiss(docs, vecs)
            return {"store": "faiss", "index": "codexify_index.faiss", "count": len(docs)}

def embed_file(
    path: str = "chunked_docs.txt",
    use_openai: Optional[bool] = None,
    model: Optional[str] = None,
    store: str = DEFAULT_STORE,
    chroma_path: str = CHROMA_PATH,
    collection: str = COLLECTION,
):
    if not os.path.exists(path):
        raise FileNotFoundError(f"No such file: {path}")
    # split chunks by blank line; tweak if you use JSONL, etc.
    with open(path, "r", encoding="utf-8") as f:
        contents = f.read()
    docs = [d.strip() for d in contents.split("\n\n") if d.strip()]
    # default to env/const; allow flag to override
    use_openai = bool(int(os.getenv("CODEXIFY_USE_OPENAI", "1"))) if use_openai is None else use_openai
    emb = CodexifyEmbedder(
        use_openai=use_openai,
        model=model,
        store=store,
        chroma_path=chroma_path,
        collection=collection,
    )
    return emb.embed_and_index(docs, ids_prefix=os.path.basename(path).replace(".", "_"))
---

2) Add CLI command: embed

File: guardian/cli/memory/embed.py
---

import click
from guardian.runtime.embed.embedder import embed_file

@click.command(name="embed")
@click.option("--path", default="chunked_docs.txt", show_default=True, help="Input file (chunks separated by blank lines).")
@click.option("--use-openai/--use-local", default=True, show_default=True, help="Use OpenAI API or local model.")
@click.option("--model", default=None, help="Override embedding model name.")
@click.option("--store", type=click.Choice(["chroma", "faiss"]), default="chroma", show_default=True, help="Vector store backend.")
@click.option("--chroma-path", default="./.chroma", show_default=True, help="Chroma persistence path.")
@click.option("--collection", default="codexify_vault", show_default=True, help="Chroma collection name.")
def embed(path, use_openai, model, store, chroma_path, collection):
    \"\"\"Embed and index documents into the configured vector store.\"\"\"
    result = embed_file(
        path=path,
        use_openai=use_openai,
        model=model,
        store=store,
        chroma_path=chroma_path,
        collection=collection,
    )
    click.echo(f\"Embedded {result['count']} docs → store={result['store']}\")

---

3) Add CLI command: embed-diagnose

File: guardian/cli/memory/embed_diagnose.py
---

import os
import click

DEFAULT_PATH = os.getenv("CODEXIFY_CHROMA_PATH", "./.chroma")
DEFAULT_COLLECTION = os.getenv("CODEXIFY_COLLECTION", "codexify_vault")

@click.command(name="embed-diagnose")
@click.option("--path", default=DEFAULT_PATH, show_default=True, help="Chroma persistence path.")
@click.option("--collection", default=DEFAULT_COLLECTION, show_default=True, help="Chroma collection name.")
def embed_diagnose(path: str, collection: str):
    \"\"\"Quick health check for your embedding index (Chroma).\"\"\"
    try:
        import chromadb
    except ImportError:
        click.echo("chromadb not installed. `pip install chromadb`")
        raise SystemExit(1)

    client = chromadb.PersistentClient(path=path)
    coll = client.get_or_create_collection(name=collection)
    count = coll.count()
    click.echo(f\"Collection: {collection}\\nPath: {path}\\nDocs: {count}\")
---

4) Register new commands in the Click entrypoint

File: guardian/cli/__init__.py

- Import and add both commands to the root `cli` group.

PATCH (append near existing add_command lines)
---

from guardian.cli.memory.embed import embed
from guardian.cli.memory.embed_diagnose import embed_diagnose
cli.add_command(embed)
cli.add_command(embed_diagnose)
---

5) Ensure Typer → Click conversion is correct (if not already)

File: guardian/runtime/tools/registry.py

- Use: `from typer.main import get_command as typer_to_click`
- Convert Typer apps with: `gm_click = typer_to_click(guardian_main_app)` and `iz_click = typer_to_click(imprint_zero_app)`
- Walker should duck‑type groups: `hasattr(sub, "list_commands")` instead of `isinstance(sub, click.MultiCommand)`.

If this is already in place, do nothing.

6) Rebuild manifest and verify in TUI

After applying patches, run in the project shell:

python -m pip install -e “.[tui,rag]”
python -m guardian.runtime.tools.registry
guardian-diag

You should see `embed` and `embed-diagnose` in the left list. Press Enter on `embed` to run with defaults:

- Reads `chunked_docs.txt`
- Uses OpenAI by default (toggle in command: `--use-local` for your BGE model)
- Persists to `./.chroma` collection `codexify_vault`

Then run `embed-diagnose` to confirm the count.

ACCEPTANCE

- `guardian embed --use-local --model BAAI/bge-large-en-v1.5` embeds without error
- `guardian embed-diagnose` prints doc count
- Both appear and execute from `guardian-diag` TUI

Please apply these changes now.

⸻
