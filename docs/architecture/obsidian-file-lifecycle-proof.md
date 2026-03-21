# Obsidian File Lifecycle Proof

## Scope
This proof validates rename, move, and deletion behavior for the derived Obsidian
index using the existing CLI ingest path plus an optional prune mode. It does
not introduce connector exposure or sync orchestration.

## Identity Model
- `source_id` is deterministic, derived from:
  - vault root path hash
  - vault-relative note path
- Rename/move changes the vault-relative path and therefore produces a new
  `source_id`.
- Without cleanup, the old `source_id` remains in the vector index.
- With `--prune`, stale `source_id` values under the same `source_root` are
  deleted after ingest.

## Rename Behavior
- Without `--prune`: rename creates a new `source_id` and leaves the old entry.
- With `--prune`: the old `source_id` is removed and count returns to steady state.

Evidence (no prune after rename):
```
{"count": 5, "old_id_present": true, "new_id_present": true}
```

Evidence (with prune after rename):
```
{"count": 4, "old_id_present": false, "new_id_present": true}
```

## Move Behavior
- Without `--prune`: move would create a new `source_id` and leave the old one.
- With `--prune`: the old `source_id` is removed and the new one remains.

Evidence (with prune after move):
```
{"count": 4, "old_id_present": false, "new_id_present": true}
```

## Deletion Behavior
- Without `--prune`: deleted files remain as stale entries.
- With `--prune`: deleted entries are removed and collection count decreases.

Evidence (with prune after delete):
```
{"count": 3, "deleted_id_present": false}
```

## Commands Run
Initial ingest:
```bash
CODEXIFY_RUNTIME_ENV_FILE=.env.example GUARDIAN_API_KEY=local \
  docker compose run --rm --no-deps \
  -v /tmp/codexify-obsidian-lifecycle-proof:/tmp/codexify-obsidian-lifecycle-proof \
  -e CODEXIFY_VECTOR_STORE=chroma \
  -e CODEXIFY_CHROMA_PATH=/tmp/codexify-obsidian-lifecycle-proof/.chroma \
  -e CODEXIFY_COLLECTION=obsidian_lifecycle \
  -e CODEXIFY_EMBEDDINGS_BACKEND=mock \
  backend -m guardian.cli.ingest_cli ingest-obsidian /tmp/codexify-obsidian-lifecycle-proof/vault
```

Rename + ingest without prune:
```bash
mv /tmp/codexify-obsidian-lifecycle-proof/vault/"Plain Note.md" \
  /tmp/codexify-obsidian-lifecycle-proof/vault/"Plain Note Renamed.md"

CODEXIFY_RUNTIME_ENV_FILE=.env.example GUARDIAN_API_KEY=local \
  docker compose run --rm --no-deps \
  -v /tmp/codexify-obsidian-lifecycle-proof:/tmp/codexify-obsidian-lifecycle-proof \
  -e CODEXIFY_VECTOR_STORE=chroma \
  -e CODEXIFY_CHROMA_PATH=/tmp/codexify-obsidian-lifecycle-proof/.chroma \
  -e CODEXIFY_COLLECTION=obsidian_lifecycle \
  -e CODEXIFY_EMBEDDINGS_BACKEND=mock \
  backend -m guardian.cli.ingest_cli ingest-obsidian /tmp/codexify-obsidian-lifecycle-proof/vault
```

Prune after rename:
```bash
CODEXIFY_RUNTIME_ENV_FILE=.env.example GUARDIAN_API_KEY=local \
  docker compose run --rm --no-deps \
  -v /tmp/codexify-obsidian-lifecycle-proof:/tmp/codexify-obsidian-lifecycle-proof \
  -e CODEXIFY_VECTOR_STORE=chroma \
  -e CODEXIFY_CHROMA_PATH=/tmp/codexify-obsidian-lifecycle-proof/.chroma \
  -e CODEXIFY_COLLECTION=obsidian_lifecycle \
  -e CODEXIFY_EMBEDDINGS_BACKEND=mock \
  backend -m guardian.cli.ingest_cli ingest-obsidian --prune /tmp/codexify-obsidian-lifecycle-proof/vault
```

Move + prune:
```bash
mkdir -p /tmp/codexify-obsidian-lifecycle-proof/vault/Moved \
  && mv /tmp/codexify-obsidian-lifecycle-proof/vault/"Tagged Metadata.md" \
  /tmp/codexify-obsidian-lifecycle-proof/vault/Moved/"Tagged Metadata.md"

CODEXIFY_RUNTIME_ENV_FILE=.env.example GUARDIAN_API_KEY=local \
  docker compose run --rm --no-deps \
  -v /tmp/codexify-obsidian-lifecycle-proof:/tmp/codexify-obsidian-lifecycle-proof \
  -e CODEXIFY_VECTOR_STORE=chroma \
  -e CODEXIFY_CHROMA_PATH=/tmp/codexify-obsidian-lifecycle-proof/.chroma \
  -e CODEXIFY_COLLECTION=obsidian_lifecycle \
  -e CODEXIFY_EMBEDDINGS_BACKEND=mock \
  backend -m guardian.cli.ingest_cli ingest-obsidian --prune /tmp/codexify-obsidian-lifecycle-proof/vault
```

Delete + prune:
```bash
rm /tmp/codexify-obsidian-lifecycle-proof/vault/"Frontmatter Note.md"

CODEXIFY_RUNTIME_ENV_FILE=.env.example GUARDIAN_API_KEY=local \
  docker compose run --rm --no-deps \
  -v /tmp/codexify-obsidian-lifecycle-proof:/tmp/codexify-obsidian-lifecycle-proof \
  -e CODEXIFY_VECTOR_STORE=chroma \
  -e CODEXIFY_CHROMA_PATH=/tmp/codexify-obsidian-lifecycle-proof/.chroma \
  -e CODEXIFY_COLLECTION=obsidian_lifecycle \
  -e CODEXIFY_EMBEDDINGS_BACKEND=mock \
  backend -m guardian.cli.ingest_cli ingest-obsidian --prune /tmp/codexify-obsidian-lifecycle-proof/vault
```

## Retrieval Evidence
```
{"query": "This note has YAML frontmatter and a title override.", "any_deleted_id": false, "result_paths": ["/tmp/codexify-obsidian-lifecycle-proof/vault/Plain Note Renamed.md", "/tmp/codexify-obsidian-lifecycle-proof/vault/Moved/Tagged Metadata.md", "/tmp/codexify-obsidian-lifecycle-proof/vault/Distinctive Retrieval.md"]}
```

## Hardening Changes
- Added `--prune` to Obsidian ingest to remove stale entries under the same
  `source_root`.
- Added Chroma id listing + deletion helpers to support pruning.

## What Was Proven
- Rename/move change `source_id` and create stale entries without pruning.
- `--prune` removes stale entries for renamed/moved/deleted notes.
- Retrieval after deletion does not return the deleted note’s `source_id`.

## What Was Not Proven
- Automatic pruning without the `--prune` flag.
- Multi-vault cleanup policy beyond per-vault `source_root`.
- Real sentence-transformer embeddings (mock backend used).

## Verdict
File lifecycle changes are now predictable when `--prune` is used. Without
pruning, rename/move/delete leave stale entries. With pruning, the derived
index stays aligned to the current vault contents.
