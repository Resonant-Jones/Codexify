# Obsidian Ingest Idempotency Proof

## Scope
This proof validates repeatable local Obsidian ingest behavior and stable source
identity under the real Chroma backend. It does not expose connectors, activate
sync tables, or introduce UI changes.

## Vault Sample
- Fixture vault: `tests/fixtures/obsidian_vault`
- Runtime copy: `/tmp/codexify-obsidian-idempotency-proof/vault`
- Distinctive note: `Distinctive Retrieval.md`

## Identity Model
- Source identity is deterministic and derived from:
  - vault root path (hashed)
  - note relative path
- Stored fields:
  - `source_id` (deterministic id, used as Chroma document id)
  - `source_type=obsidian`
  - `source_root` (vault path)
  - `source_path` (absolute note path)
  - `source_relpath` (vault-relative path)
  - `source_content_hash` (sha256 of content)
- Repeat ingest of the same vault uses the same `source_id` and performs a
  Chroma upsert (no duplicate rows).

## Commands Run
Copy fixture vault to a runtime scratch directory:
```bash
rm -rf /tmp/codexify-obsidian-idempotency-proof \
  && mkdir -p /tmp/codexify-obsidian-idempotency-proof \
  && cp -R /Users/resonant_jones/.codex/worktrees/9657/Codexify/tests/fixtures/obsidian_vault \
    /tmp/codexify-obsidian-idempotency-proof/vault
```

First ingest:
```bash
CODEXIFY_RUNTIME_ENV_FILE=.env.example GUARDIAN_API_KEY=local \
  docker compose run --rm --no-deps \
  -v /tmp/codexify-obsidian-idempotency-proof:/tmp/codexify-obsidian-idempotency-proof \
  -e CODEXIFY_VECTOR_STORE=chroma \
  -e CODEXIFY_CHROMA_PATH=/tmp/codexify-obsidian-idempotency-proof/.chroma \
  -e CODEXIFY_COLLECTION=obsidian_idempotency \
  -e CODEXIFY_EMBEDDINGS_BACKEND=mock \
  backend -m guardian.cli.ingest_cli ingest-obsidian /tmp/codexify-obsidian-idempotency-proof/vault
```

Count + metadata snapshot:
```bash
CODEXIFY_RUNTIME_ENV_FILE=.env.example GUARDIAN_API_KEY=local \
  docker compose run --rm --no-deps \
  -v /tmp/codexify-obsidian-idempotency-proof:/tmp/codexify-obsidian-idempotency-proof \
  -e CODEXIFY_VECTOR_STORE=chroma \
  -e CODEXIFY_CHROMA_PATH=/tmp/codexify-obsidian-idempotency-proof/.chroma \
  -e CODEXIFY_COLLECTION=obsidian_idempotency \
  -e CODEXIFY_EMBEDDINGS_BACKEND=mock \
  backend - <<'PY'
import json
from pathlib import Path

import chromadb
from guardian.cli import ingest_cli

vault = Path("/tmp/codexify-obsidian-idempotency-proof/vault")
note = vault / "Distinctive Retrieval.md"
source_id = ingest_cli._obsidian_source_id(vault, note)
client = chromadb.PersistentClient(path="/tmp/codexify-obsidian-idempotency-proof/.chroma")
collection = client.get_or_create_collection(name="obsidian_idempotency")
record = collection.get(ids=[source_id])
meta = record["metadatas"][0]
payload = {
    "count": collection.count(),
    "source_id": source_id,
    "source_path": meta.get("source_path"),
    "source_content_hash": meta.get("source_content_hash"),
    "text_snippet": record["documents"][0][:120],
}
print(json.dumps(payload, ensure_ascii=False))
PY
```

Repeat ingest (unchanged vault):
```bash
CODEXIFY_RUNTIME_ENV_FILE=.env.example GUARDIAN_API_KEY=local \
  docker compose run --rm --no-deps \
  -v /tmp/codexify-obsidian-idempotency-proof:/tmp/codexify-obsidian-idempotency-proof \
  -e CODEXIFY_VECTOR_STORE=chroma \
  -e CODEXIFY_CHROMA_PATH=/tmp/codexify-obsidian-idempotency-proof/.chroma \
  -e CODEXIFY_COLLECTION=obsidian_idempotency \
  -e CODEXIFY_EMBEDDINGS_BACKEND=mock \
  backend -m guardian.cli.ingest_cli ingest-obsidian /tmp/codexify-obsidian-idempotency-proof/vault
```

Changed note update:
```bash
cat <<'EOF' > /tmp/codexify-obsidian-idempotency-proof/vault/Distinctive\ Retrieval.md
The mariner-signal-lattice recalibrates after midnight.
This update should replace the prior content.
EOF

CODEXIFY_RUNTIME_ENV_FILE=.env.example GUARDIAN_API_KEY=local \
  docker compose run --rm --no-deps \
  -v /tmp/codexify-obsidian-idempotency-proof:/tmp/codexify-obsidian-idempotency-proof \
  -e CODEXIFY_VECTOR_STORE=chroma \
  -e CODEXIFY_CHROMA_PATH=/tmp/codexify-obsidian-idempotency-proof/.chroma \
  -e CODEXIFY_COLLECTION=obsidian_idempotency \
  -e CODEXIFY_EMBEDDINGS_BACKEND=mock \
  backend -m guardian.cli.ingest_cli ingest-obsidian /tmp/codexify-obsidian-idempotency-proof/vault
```

Changed-note count + metadata snapshot:
```bash
CODEXIFY_RUNTIME_ENV_FILE=.env.example GUARDIAN_API_KEY=local \
  docker compose run --rm --no-deps \
  -v /tmp/codexify-obsidian-idempotency-proof:/tmp/codexify-obsidian-idempotency-proof \
  -e CODEXIFY_VECTOR_STORE=chroma \
  -e CODEXIFY_CHROMA_PATH=/tmp/codexify-obsidian-idempotency-proof/.chroma \
  -e CODEXIFY_COLLECTION=obsidian_idempotency \
  -e CODEXIFY_EMBEDDINGS_BACKEND=mock \
  backend - <<'PY'
import json
from pathlib import Path

import chromadb
from guardian.cli import ingest_cli

vault = Path("/tmp/codexify-obsidian-idempotency-proof/vault")
note = vault / "Distinctive Retrieval.md"
source_id = ingest_cli._obsidian_source_id(vault, note)
client = chromadb.PersistentClient(path="/tmp/codexify-obsidian-idempotency-proof/.chroma")
collection = client.get_or_create_collection(name="obsidian_idempotency")
record = collection.get(ids=[source_id])
meta = record["metadatas"][0]
payload = {
    "count": collection.count(),
    "source_id": source_id,
    "source_content_hash": meta.get("source_content_hash"),
    "text_snippet": record["documents"][0][:120],
}
print(json.dumps(payload, ensure_ascii=False))
PY
```

## First Ingest Result
```
{"count": 4, "source_id": "obsidian:5e66f4f42529a70258b5543d7ae3328c89e03c18e8b4b7786bd233dc00148382", "source_path": "/tmp/codexify-obsidian-idempotency-proof/vault/Distinctive Retrieval.md", "source_content_hash": "6caed7c0279fa2f255eba8f77e59d2747740847280c081a92c7b86e86d40a172", "text_snippet": "The mariner-signal-lattice calibrates under aurora pressure.\nThis distinctive phrase should be retrievable after ingest."}
```

## Repeat Ingest Result
```
{"count": 4, "source_id": "obsidian:5e66f4f42529a70258b5543d7ae3328c89e03c18e8b4b7786bd233dc00148382", "source_content_hash": "6caed7c0279fa2f255eba8f77e59d2747740847280c081a92c7b86e86d40a172"}
```

## Changed Note Result
```
{"count": 4, "source_id": "obsidian:5e66f4f42529a70258b5543d7ae3328c89e03c18e8b4b7786bd233dc00148382", "source_content_hash": "3cc6582ba381af55fd699a8544492715fe6bd48fdb86eaa0ddb5c07386577e5e", "text_snippet": "The mariner-signal-lattice recalibrates after midnight.\nThis update should replace the prior content.\n"}
```

## Retrieval Evidence
```
{"query": "recalibrates after midnight", "hit_source_id": "obsidian:5e66f4f42529a70258b5543d7ae3328c89e03c18e8b4b7786bd233dc00148382", "hit_source_path": "/tmp/codexify-obsidian-idempotency-proof/vault/Distinctive Retrieval.md", "hit_source_hash": "3cc6582ba381af55fd699a8544492715fe6bd48fdb86eaa0ddb5c07386577e5e", "hit_text": "The mariner-signal-lattice recalibrates after midnight.\nThis update should replace the prior content.\n"}
```

## Hardening Changes
- Deterministic Obsidian `source_id` + content hash metadata added at ingest.
- Chroma upsert used when deterministic ids are provided, preventing silent duplication.
- Source reporting fields (`source_type`, `source_root`, `source_path`, `source_relpath`) persisted in metadata.

## What Was Proven
- First ingest writes 4 notes into Chroma and records stable source identity.
- Repeat ingest of an unchanged vault does not increase collection count (idempotent).
- Changed-note ingest updates content and content hash for the same `source_id`.
- Retrieval returns source metadata sufficient to trace the originating note.

## What Was Not Proven
- Real sentence-transformer embeddings (mock embeddings used for repeatability).
- API-level retrieval routes or connector/sync workflows.
- Multi-vault collision behavior (single vault proof only).

## Verdict
Repeatable local Obsidian ingest now behaves predictably: re-ingest is idempotent
by deterministic source id, and changed notes replace content while preserving
source identity and metadata for reporting.
