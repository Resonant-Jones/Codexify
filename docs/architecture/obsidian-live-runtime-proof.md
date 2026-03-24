# Obsidian Live Runtime Proof

## Scope
This proof validates the live Obsidian CLI ingest path and MemoryOS retrieval path
against the real configured vector backend (Chroma) under the current Docker/dev
runtime. It does not expose connectors, enable sync semantics, or add UI.

## Runtime Environment
- Docker Compose `backend` service (runtime image)
- Env overrides:
  - `CODEXIFY_VECTOR_STORE=chroma`
  - `CODEXIFY_CHROMA_PATH=/tmp/codexify-obsidian-live-proof/.chroma`
  - `CODEXIFY_COLLECTION=obsidian_live_proof`
  - `CODEXIFY_EMBEDDINGS_BACKEND=mock`
- `CODEXIFY_RUNTIME_ENV_FILE=.env.example` (to satisfy compose env_file)
- Note: `mock` embeddings were used to keep the proof local and repeatable in this environment.

## Vault Sample
- Fixture vault: `tests/fixtures/obsidian_vault`
- Distinctive retrieval note: `Distinctive Retrieval.md`
- Distinctive phrase: `mariner-signal-lattice`

## Commands Run
Ingest via the existing CLI path:
```bash
CODEXIFY_RUNTIME_ENV_FILE=.env.example GUARDIAN_API_KEY=local \
  docker compose run --rm --no-deps \
  -v /tmp/codexify-obsidian-live-proof:/tmp/codexify-obsidian-live-proof \
  -e CODEXIFY_VECTOR_STORE=chroma \
  -e CODEXIFY_CHROMA_PATH=/tmp/codexify-obsidian-live-proof/.chroma \
  -e CODEXIFY_COLLECTION=obsidian_live_proof \
  -e CODEXIFY_EMBEDDINGS_BACKEND=mock \
  backend -m guardian.cli.ingest_cli ingest-obsidian /app/tests/fixtures/obsidian_vault
```

Retrieve through the real retriever/backend seam:
```bash
CODEXIFY_RUNTIME_ENV_FILE=.env.example GUARDIAN_API_KEY=local \
  docker compose run --rm --no-deps \
  -v /tmp/codexify-obsidian-live-proof:/tmp/codexify-obsidian-live-proof \
  -e CODEXIFY_VECTOR_STORE=chroma \
  -e CODEXIFY_CHROMA_PATH=/tmp/codexify-obsidian-live-proof/.chroma \
  -e CODEXIFY_COLLECTION=obsidian_live_proof \
  -e CODEXIFY_EMBEDDINGS_BACKEND=mock \
  backend - <<'PY'
import asyncio
import json
from pathlib import Path

from guardian.memoryos.retriever import MemoryOSRetriever
from guardian.vector.store import VectorStore

query = Path("/app/tests/fixtures/obsidian_vault/Distinctive Retrieval.md").read_text(
    encoding="utf-8"
)

async def main():
    retriever = MemoryOSRetriever(VectorStore())
    results = await retriever.retrieve(query, limit=3)
    hit = next((r for r in results if "mariner-signal-lattice" in r.get("text", "")), None)
    payload = {
        "query": "mariner-signal-lattice",
        "hit_path": hit["metadata"]["path"] if hit else None,
        "hit_text": (hit["text"] if hit else "")[:120],
        "result_count": len(results),
    }
    print(json.dumps(payload, ensure_ascii=False))

asyncio.run(main())
PY
```

## Retrieval Evidence
```
{"query": "mariner-signal-lattice", "hit_path": "/app/tests/fixtures/obsidian_vault/Distinctive Retrieval.md", "hit_text": "The mariner-signal-lattice calibrates under aurora pressure.\nThis distinctive phrase should be retrievable after ingest.", "result_count": 3}
```

## What Was Proven
- The live Obsidian CLI ingest path (`guardian.cli.ingest_cli ingest-obsidian`) can ingest a real local vault into Chroma.
- The configured vector backend (Chroma) persists the ingested notes and can be queried via `MemoryOSRetriever` + `VectorStore`.
- Retrieval returns the distinctive note content with the expected source path metadata.

## What Was Not Proven
- Real sentence-transformer embeddings (the proof used the mock backend for repeatability).
- API-level retrieval through HTTP routes.
- Connector exposure, sync tables, or any federation/replication path.
- Cross-process durability beyond the explicit Chroma path used for the proof.

## Hardening Changes
- `VectorStore` now respects `CODEXIFY_CHROMA_PATH` and `CODEXIFY_COLLECTION` to make backend selection/collection naming explicit.
- Chroma metadata coercion ensures list/dict metadata (e.g., Obsidian tags) serialize into Chroma-compatible scalar fields.

## Verdict
The current runtime can ingest a real local Obsidian vault into the configured
Chroma vector backend and retrieve it through the real retriever seam. The
proof is live and backend-backed, but still does not exercise full model-based
semantic retrieval, API surface, or sync semantics.
