# Real Vault Obsidian Index Rollback

## Scope

This rollback clears premature local Codexify Obsidian index state created from a real-vault-derived markdown mirror.

It does not delete, modify, read, preview, index, summarize, or print host vault files. It does not change Codexify runtime behavior, frontend behavior, backend routes, database schema, migrations, protocol tokens, tests, or release posture.

## Operator Approval

The operator explicitly approved clearing the premature local indexed state in the rollback task on 2026-05-30.

No sensitive vault paths or note contents are included in this artifact.

## Repository Safety

- Working directory: `/Volumes/Dev_SSD/Codexify-main`
- Git root: `/Volumes/Dev_SSD/Codexify-main`
- Branch: `codex/fix-chat-slash-commands`
- Remote: `origin https://github.com/Resonant-Jones/Codexify.git`
- HEAD before rollback: `af6fa793b0fc9a2a4b0db1aa2e8991ca94b01b11`
- Dirty/untracked files before rollback: none
- Proof timestamp: `2026-05-30T17:04:44Z`

Repository safety commands:

```bash
pwd
git rev-parse --show-toplevel
git remote -v
git branch --show-current
git status --short
git show --name-only --stat f0b56e415380ce51fc7fce2dbc6cae253f1a27a0
git show --name-only --stat 15c088b05c8d166f3b1d99f9125610799820790d
git show --name-only --stat af6fa793b0fc9a2a4b0db1aa2e8991ca94b01b11
git ls-files | rg '(^|/)(codexify-obsidian-|vaultnode-real-vault|private/tmp|tmp/codexify-obsidian-|tmp/vaultnode-real-vault)'
```

Recent commit file-surface verification:

- `f0b56e415380ce51fc7fce2dbc6cae253f1a27a0` changed only `docs/audits/obsidian/2026-05-29-obsidian-synthetic-vault-proof.md`.
- `15c088b05c8d166f3b1d99f9125610799820790d` changed only `docs/audits/obsidian/2026-05-29-obsidian-workspace-context-closure.md`.
- `af6fa793b0fc9a2a4b0db1aa2e8991ca94b01b11` changed only `guardian/context/broker.py` and `tests/routes/test_chat_source_mode.py`.
- The tracked-file scan found no committed `/private/tmp/codexify-obsidian-*`, `/tmp/codexify-obsidian-*`, backend-container vault-mirror, or real vault files.

## Pre-Rollback State

Prior reported real-vault-derived indexing values:

- `scanned=578`
- `indexed=578`
- `failure_count=0`

Safe live count-only evidence before rollback:

```json
{
  "namespace": "obsidian:local",
  "obsidian_vector_count": 578,
  "vector_total_count": 581,
  "non_obsidian_vector_count": 3,
  "config_present": true,
  "vault_root_present": true,
  "allowed_paths_count": 0,
  "allowed_tags_count": 0,
  "last_indexed_count": 578,
  "last_indexed_at_present": true,
  "last_index_error_present": false
}
```

The current Obsidian connector config still pointed to a vault root before rollback. The path is intentionally redacted. No vault file content was read or printed.

Namespace/filter used for rollback: `obsidian:local`, matching `guardian.obsidian.indexer.OBSIDIAN_NAMESPACE`.

## Rollback Method

Implementation diagnosis:

- Obsidian index metadata is stored in Postgres table `connector_configs`, row name `obsidian_local`, inside the JSON config/settings payload.
- Obsidian embeddings are stored in the vector store collection using metadata field `namespace="obsidian:local"`.
- The existing helper `guardian.obsidian.indexer.clear_obsidian_namespace()` deletes vectors by selecting ids with `where={"namespace": OBSIDIAN_NAMESPACE}` and then deleting those ids.
- No existing HTTP clear/reset route is exposed, and no new route was added.
- Clearing also reset local index metadata by preserving the existing connector config while setting `last_indexed_at=null`, `last_indexed_count=0`, and `last_index_error=null`.
- The rollback used the existing vector-store helper plus the existing database connector-config update method. No raw SQL, schema edits, migrations, or runtime-code changes were used.

Commands run:

```bash
docker compose ps
```

Count-only preflight probe:

```bash
docker compose exec -T backend python -c '<count obsidian:local vector ids, total vector count, and redacted obsidian_local metadata>'
```

Rollback command:

```bash
docker compose exec -T backend python -c '<call clear_obsidian_namespace(VectorStore()) and reset obsidian_local last_indexed metadata>'
```

The rollback command did not call `/api/obsidian/preview`, did not call `/api/obsidian/index`, and did not read vault markdown files.

## Post-Rollback Verification

Safe post-rollback evidence:

```json
{
  "namespace": "obsidian:local",
  "before_obsidian_vector_count": 578,
  "before_vector_total_count": 581,
  "before_non_obsidian_vector_count": 3,
  "deleted_count": 578,
  "after_obsidian_vector_count": 0,
  "after_vector_total_count": 3,
  "after_non_obsidian_vector_count": 3,
  "config_present": true,
  "vault_root_present_after": true,
  "last_indexed_count_after": 0,
  "last_indexed_at_present_after": false,
  "last_index_error_present_after": false
}
```

Verification summary:

- The Obsidian vector namespace no longer contains the premature 578-note index.
- Non-Obsidian vector count remained `3`, matching the pre-rollback non-Obsidian count.
- The Obsidian connector config row still exists, but local index metadata was reset.
- A final count-only recheck after validation still reported `obsidian_vector_count=0`, `vector_total_count=3`, `last_indexed_count=0`, and no indexed timestamp.
- The vault root remains configured in local runtime state, with the path redacted here.
- No host vault files were deleted, modified, read, printed, or summarized.
- No repo vault files are staged or committed.
- Existing synthetic proof artifacts remain unchanged.

## What This Rollback Does Not Do

- Does not delete the host vault.
- Does not delete the installed Obsidian application.
- Does not prove real-vault ingestion.
- Does not run real-vault preview.
- Does not run real-vault indexing.
- Does not alter normal chat completion.
- Does not alter synthetic-vault proof results.
- Does not activate MCP, command bus, GitHub, or arbitrary tools.
- Does not widen release posture.

## Caveats

- The local Obsidian connector config still links to a vault root after rollback; the path is redacted and was left untouched.
- Metadata reset is exact for `last_indexed_at`, `last_indexed_count`, and `last_index_error`; it does not remove the connector config row.
- Vector-store deletion is namespace-level by vector id over Chroma metadata `namespace="obsidian:local"`.
- A backend-container markdown mirror from the premature proof may still exist from prior local setup; this rollback did not read, delete, or modify it because this task was scoped to Codexify index/vector state and forbade touching real vault note files.
- No content queries were used for verification. The proof relies on count and metadata evidence only.
- This rollback does not prove that no other non-Codexify local copy of vault content exists outside the index namespace.

## Validation

Validation commands for this rollback artifact:

```bash
./.venv/bin/pytest -v tests/routes/test_obsidian_routes.py
./.venv/bin/pytest -v tests/core/test_obsidian_only_retrieval.py
./.venv/bin/pytest -v tests/core/test_chat_completion_service_context_directives.py
./.venv/bin/pytest -v tests/routes/test_chat_context_directives.py
./.venv/bin/pytest -v tests/routes/test_chat_source_mode.py -k "slash or obsidian or context"
python3 scripts/validate_docs.py
git diff --check
```

Validation results:

- `./.venv/bin/pytest -v tests/routes/test_obsidian_routes.py` - 7 passed, 4 warnings.
- `./.venv/bin/pytest -v tests/core/test_obsidian_only_retrieval.py` - 2 passed.
- `./.venv/bin/pytest -v tests/core/test_chat_completion_service_context_directives.py` - 11 passed.
- `./.venv/bin/pytest -v tests/routes/test_chat_context_directives.py` - 11 passed, 4 warnings.
- `./.venv/bin/pytest -v tests/routes/test_chat_source_mode.py -k "slash or obsidian or context"` - 13 passed, 5 deselected, 4 warnings.
- `python3 scripts/validate_docs.py` - passed.
- `git diff --check` - passed.

## Final Result

`PASS`

The premature local Obsidian vector namespace was cleared, index metadata was reset, no real-vault preview or indexing was run, no vault files were committed, and release posture was unchanged.
