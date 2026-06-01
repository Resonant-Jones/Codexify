# Real Vault Scoped Obsidian Index Proof

## Scope

This proof intentionally indexed a scoped real-vault markdown subset for the
local `/obsidian` workspace-context path.

This proof did not index the full vault. It did not commit vault files, raw
note text, real vault paths, screenshots, secrets, or sensitive attachments. It
did not change runtime behavior, frontend behavior, backend routes, database
schema, protocol tokens, tests, or release posture.

The proof target was a filtered markdown mirror outside the repository. The
mirror contained only the operator-approved `Codexify HomeOS` scope.

## Operator Scope Approval

The operator approved the scope label `Codexify HomeOS` inside this Codex
session. The local vault scan matched that approval to a sanitized folder label
of `HomeOS`.

No approval was given for full-vault indexing, so the full vault was not
indexed. The proof used the scoped mirror only.

## Repository Safety

- Working directory: `/Volumes/Dev_SSD/Codexify-main`
- Git root: `/Volumes/Dev_SSD/Codexify-main`
- Branch: `codex/fix-chat-slash-commands`
- Remote: `origin https://github.com/Resonant-Jones/Codexify.git`
- HEAD before proof artifact: `a8bf3799ea76521c377d31d49cf67cc571d4ed08`
- Dirty/untracked files before proof: none reported by `git status --short`
- Recent rollback commit verified: `a8bf3799ea76521c377d31d49cf67cc571d4ed08`
- Rollback proof artifact verified present:
  `docs/audits/obsidian/2026-05-30-real-vault-index-rollback.md`
- Tracked temp-vault path check found no committed
  `/private/tmp/codexify-obsidian-*`, `/tmp/codexify-obsidian-*`,
  `/tmp/vaultnode-real-vault`, or real-vault files.

No vault files were staged or committed for this proof.

## Filter Policy

Allowed file type:

- `.md` only

Default excluded path categories:

- `journal`, `journals`, `daily`, `dailies`, `diary`
- `personal`, `private`, `therapy`, `health`, `medical`
- `finance`, `financial`, `tax`, `legal`
- `client`, `clients`, `customer`, `customers`
- `secrets`, `password`, `credentials`
- `.obsidian`
- `attachments`, `assets`, `images`, `screenshots`
- `archive`, `archived`, `trash`
- `inbox`, unless explicitly approved
- binary and non-markdown files

Discovery skipped 38 excluded directory entries before selecting the approved
scope. Within the approved scope, the filtered mirror copied 3 markdown files,
skipped 0 non-markdown files, and found no path-based exclusion hits.

Excluded contents were not read, printed, summarized, or copied into the
filtered mirror.

## Filtered Mirror

- Mirror location: `[redacted-host-scoped-mirror]`
- Backend-container mirror location: `[redacted-container-scoped-mirror]`
- Approved scope label: `Codexify HomeOS`
- Matched sanitized label: `HomeOS`
- Approved markdown count: 3
- Excluded markdown count inside approved scope: 0
- Non-markdown files skipped inside approved scope: 0
- Aggregate safe term coverage:
  - `architecture`: 3 approved markdown files
  - `codexify`: 3 approved markdown files
  - `homeos`: 1 approved markdown file

The mirror remained outside the repository. No personal note text or raw note
excerpts are included in this artifact.

## Namespace Reset Before Index

The Obsidian vector namespace is `obsidian:local`.

Before indexing, the namespace was verified clear:

- Pre-clear Obsidian vector count: 0
- Clear helper: `guardian.obsidian.indexer.clear_obsidian_namespace()`
- Clear result: `deleted_count=0`
- Metadata reset: true
- Post-clear Obsidian vector count: 0

This preserved non-Obsidian vector namespaces.

## Config, Preview, and Index

Runtime posture checks:

- `GET /health`: `200`, body status `ok`
- `GET /health/chat`: `200`, body status `healthy`
- `GET /openapi.json`: `200`
- OpenAPI exposed:
  - `/api/obsidian/config`
  - `/api/obsidian/preview`
  - `/api/obsidian/index`

Configuration used the supported local route:

- `PUT /api/obsidian/config`
- Payload shape: `{"vault_root": "[redacted-container-scoped-mirror]"}`
- Result: `200`
- Config present: true
- Vault root present: true
- Allowed path count: 0
- Allowed tag count: 0

Preview:

- `POST /api/obsidian/preview`
- Status: `200`
- Scanned: 3
- Note count: 3
- Failure count: 0
- Sample count: 3
- Raw note text printed: no

Index:

- `POST /api/obsidian/index`
- Status: `200`
- Scanned: 3
- Indexed: 3
- Deleted before rebuild: 0
- Failure count: 0
- `indexed_at` present: true

Post-index metadata:

- `last_indexed_count`: 3
- `last_indexed_at` present: true
- `last_index_error` present: false
- Obsidian vector count: 3
- Vector total count observed in local store: 6
- Non-Obsidian vector count preserved: 3
- Source root count for Obsidian metadata: 1

## Retrieval Proof

Retrieval was checked through the current supported retrieval health/search
surface without printing raw note text.

Safe query descriptions:

| Query label | Match count | Obsidian namespace matches | Excluded path segment hits | Status |
| --- | ---: | ---: | ---: | --- |
| `HomeOS` | 3 | 3 | 0 | ready |
| `Codexify HomeOS architecture` | 3 | 3 | 0 | ready |
| `Codexify architecture` | 3 | 3 | 0 | ready |

The scoped Obsidian evidence was returned from `obsidian:local`. No excluded
path segments appeared in the sanitized retrieval metadata.

## /obsidian Chat Proof

Proof thread: `5`

| Prompt label | Source message ID | Task ID | Terminal event | Assistant message ID | Grounding assessment | `/obsidian` rejected? |
| --- | ---: | --- | --- | ---: | --- | --- |
| Approved-scope HomeOS architecture question | 25 | `2047a5f0-34df-4df4-8429-09c3e89615cb` | `task.failed` | n/a | No assistant answer persisted; provider/runtime timed out after reaching `AWAITING_FIRST_TOKEN`. | no |
| Approved-scope Codexify/HomeOS relationship question | 26 | `a6b84bb5-20fd-4780-a5a9-09d512b0c49f` | `task.completed` | 27 | Grounded in scoped local evidence. Terminal payload reported 3 connector contexts and source mode `obsidian_only`. | no |

Completed `/obsidian` turn evidence:

- `connector_context_count`: 3
- `connector_context_injected`: true
- `obsidian_count`: 3
- `retrieval_injected`: true
- `source_mode`: `obsidian_only`
- Assistant message persisted: true
- Assistant answer referenced the approved HomeOS scope: true
- Raw assistant text recorded in this artifact: no

The failed `/obsidian` turn was a runtime timeout caveat, not an unknown-command
or route failure:

- State sequence: `QUEUED -> AWAITING_MODEL -> AWAITING_FIRST_TOKEN`
- Terminal event: `task.failed`
- Error type: `HTTPException`
- Runtime status: `timeout`
- Selection source: `LOCAL_CHAT_MODEL`
- Duration: approximately 61.5 seconds
- Raw note text printed: no

Guardian did not say `/obsidian` was unrecognized in either `/obsidian` turn.

## Negative Control

Negative-control thread: `6`

- Prompt type: normal non-`/obsidian` question using safe HomeOS wording
- Source message ID: 28
- Task ID: `b799f609-d8eb-4681-ac1a-b9d6acd49d22`
- Terminal event: `task.completed`
- Assistant message ID: 29
- `source_mode`: `project`
- `connector_context_count`: 0
- `obsidian_count`: 0
- `connector_context_injected`: false
- `retrieval_injected`: false

The answer mentioned HomeOS because the user prompt mentioned HomeOS, but the
terminal task payload reported no Obsidian context injection. Scoped vault
evidence was avoided in the negative control.

## What This Proof Does Not Prove

- It is not a full-vault proof.
- It is not proof that personal/private vault areas are safe to ingest.
- It is not proof that every vault shape or indexing mode works.
- It is not proof for attachments, images, screenshots, or binary files.
- It is not broad MCP/tool access.
- It is not command-bus activation.
- It is not GitHub context.
- It is not a dependency of normal chat completion on Obsidian.
- It does not widen release posture beyond the already documented
  workspace-local Obsidian path.

## Caveats

- Scope was limited to the approved `Codexify HomeOS` subset.
- The filtered mirror copied 3 markdown files; larger scoped subsets may expose
  indexing, retrieval ranking, or privacy-review issues not covered here.
- The Obsidian indexer performs a full namespace rebuild for the configured
  mirror.
- One `/obsidian` proof turn timed out at the provider/runtime layer after
  reaching `AWAITING_FIRST_TOKEN`; the following `/obsidian` turn completed with
  scoped Obsidian context injected.
- The current config now points at the filtered mirror path, redacted here. It
  does not point at the full host vault.
- Temporary proof mirror/state files remained under temp locations and were not
  committed.
- Retrieval proof uses safe query labels and aggregate counts, not raw note
  excerpts.

## Rollback Path

Rollback remains available through the existing Obsidian namespace helper:

```bash
docker compose exec -T backend python -c '<call guardian.obsidian.indexer.clear_obsidian_namespace() and reset obsidian_local metadata>'
```

The prior rollback proof is recorded in
`docs/audits/obsidian/2026-05-30-real-vault-index-rollback.md`.

The rollback target is the local `obsidian:local` namespace and associated
Obsidian index metadata only. It must not delete host vault files or normal
non-Obsidian vector namespaces.

## Validation

Validation commands for this docs/proof artifact:

```bash
./.venv/bin/pytest -v tests/routes/test_obsidian_routes.py
./.venv/bin/pytest -v tests/core/test_obsidian_only_retrieval.py
./.venv/bin/pytest -v tests/core/test_chat_completion_service_context_directives.py
./.venv/bin/pytest -v tests/routes/test_chat_context_directives.py
./.venv/bin/pytest -v tests/routes/test_chat_source_mode.py -k "slash or obsidian or context"
python3 scripts/validate_docs.py
git diff --check
```

Results:

- `tests/routes/test_obsidian_routes.py`: 7 passed
- `tests/core/test_obsidian_only_retrieval.py`: 2 passed
- `tests/core/test_chat_completion_service_context_directives.py`: 11 passed
- `tests/routes/test_chat_context_directives.py`: 11 passed
- `tests/routes/test_chat_source_mode.py -k "slash or obsidian or context"`:
  13 passed, 5 deselected
- `python3 scripts/validate_docs.py`: passed
- `git diff --check`: passed

## Final Result

PASS.

The approved scoped mirror was created outside the repository, only approved
markdown files were copied, the `obsidian:local` namespace was clear before
indexing, preview and indexing succeeded, one `/obsidian` chat answer used
scoped local evidence, no real vault files or raw note text were committed, and
release posture was not changed.
