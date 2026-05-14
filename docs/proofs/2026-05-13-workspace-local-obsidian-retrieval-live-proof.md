# Workspace-Local Obsidian Retrieval Live Proof

- Artifact date: 2026-05-13
- Evidence collected: 2026-05-14 19:07-19:10 America/New_York
- Branch: `main`
- HEAD: `4e379784d4349296401d626e8c9a71250644b71c`
- Proof window: current `main` tip on the supported local Compose path
- Result: `FAIL`

## Scope

This proof reran the supported local Docker Compose live path for `retrievalSource="workspace"` and checked whether an Obsidian-backed workspace note could be:

- discovered by workspace-local retrieval
- selected by the broker
- injected into the executed completion context
- reflected in assistant output
- preserved as worker-visible completion payload evidence

The proof also treated debug RAG trace as diagnostic only.

## Repo State

- The repository was on `main` at the HEAD above.
- The working tree was clean before the proof run.
- During the proof session, `scripts/proofs/prove_workspace_obsidian_e2e.py` needed a narrow harness correction so the newer vault-configuring harness could execute instead of the stale legacy entrypoint.

## Commands Run

Repository state:

```bash
git branch --show-current
git rev-parse HEAD
git status --short
git log --oneline -5
```

Supported stack bring-up:

```bash
docker compose up -d db redis neo4j
docker compose run --rm migrator
docker compose up -d backend frontend worker-chat worker-document-embed worker-chat-embed worker-warmup
docker compose ps
```

Supported-profile posture:

```bash
bash scripts/dev/dev-key.sh
curl -fsS -H "X-API-Key: <redacted>" http://localhost:8888/health
curl -fsS -H "X-API-Key: <redacted>" http://localhost:8888/health/chat
curl -fsS -H "X-API-Key: <redacted>" http://localhost:8888/api/health/llm
curl -fsS -H "X-API-Key: <redacted>" http://localhost:8888/api/llm/catalog
curl -fsS -H "X-API-Key: <redacted>" "http://localhost:8888/api/llm/catalog?include=all"
```

Live proof runs:

```bash
BASE=http://localhost:8888 GUARDIAN_API_KEY=<redacted> ./.venv/bin/python scripts/proofs/prove_workspace_obsidian_e2e.py
```

After correcting the proof-harness entrypoint, the proof was rerun with the same base/key against the same supported stack.

Evidence inspection:

```bash
curl -fsS -H "X-API-Key: <redacted>" http://localhost:8888/api/chat/43/messages
curl -fsS -H "X-API-Key: <redacted>" http://localhost:8888/api/chat/debug/retrieval-posture/43/latest
curl -fsS -H "X-API-Key: <redacted>" http://localhost:8888/api/chat/debug/rag-trace/43/latest
docker compose exec -T backend python -c "from guardian.queue import task_events; import json; task_id='7169c056-0b90-49df-9c00-9985db04262a'; payload = task_events.read_latest_completed_payload(task_id); print(json.dumps(payload, indent=2, sort_keys=True, default=str))"
docker compose exec -T backend python -c "from guardian.queue import task_events; import json; task_id='7169c056-0b90-49df-9c00-9985db04262a'; print(json.dumps(task_events.describe_terminal_state(task_id), indent=2, sort_keys=True))"
```

Validation:

```bash
./.venv/bin/python -m pytest tests/proofs/test_workspace_obsidian_e2e_contract.py
./.venv/bin/python scripts/validate_docs.py
./.venv/bin/python -m py_compile scripts/proofs/prove_workspace_obsidian_e2e.py
git diff --check
```

## Supported-Profile Health Evidence

Redacted summary of the runtime posture:

- `/health`: `status=ok`, `release_hold=false`
- `/health/chat`: `status=healthy`, `redis=ok`, `worker.status=fresh`, `queue.depth=0`
- `/api/health/llm`: `status=online`, local provider selected, `release_hold=false`
- `/api/llm/catalog`: local provider enabled and available; cloud providers were present in catalog output but remained unauthorized/unavailable because credentials were absent
- `/api/llm/catalog?include=all`: confirmed the same local-only supported posture with filtered cloud inventory still not part of the supported beta claim

Non-claims preserved:

- No cloud-provider beta support was claimed.
- No graph-write release claim was widened.

## Obsidian / Workspace Evidence Setup

The corrected proof harness created a scratch workspace vault under the repo-local `tmp/` tree, mirrored it into the Compose-visible container path, configured the Obsidian vault via `/api/obsidian/config`, and triggered indexing via `/api/obsidian/index`.

Sentinel note details:

- Note title: `Zephyr Candle Reef Sentinel 91f747ac`
- Sentinel token: `workspace-seal-zephyr-candle-reef-91f747ac`
- Question: ask for the exact workspace proof phrase and reply with only the phrase

Searchability result:

- The workspace note was searchable on the supported local Compose path.
- The harness recorded `SEARCHABILITY: searchable`.
- The retrieval search probe succeeded against `namespace=obsidian:local`.

## Completion Request Details

Fresh chat thread:

- `thread_id=43`
- user message id `65`
- completion task id `7169c056-0b90-49df-9c00-9985db04262a`

Completion request:

- `source_mode=workspace`
- `retrievalSource=workspace`
- `depth_mode=normal`

Acceptance:

- `accepted=true`

Terminal task:

- `task.completed`
- completion duration: `15137ms`

Assistant reflection:

- Assistant message text: `SUPPORTED_PROOF_SENTINEL_2026_05_08`
- This did not match the expected workspace sentinel token.

## Worker-Visible Completion Payload Evidence

The worker-visible payload preserved workspace posture but did not carry Obsidian-selected evidence:

- `source_mode=workspace`
- `retrieval_provenance.retrieval_status=workspace_local_success`
- `retrieval_injected=true`
- `semantic_count=1`
- `semantic_injected=true`
- `linked_document_count=2`
- `obsidian_count=0`
- `obsidian_injected=false`
- `obsidian_semantic=0`

Interpretation:

- The executed completion was influenced by workspace-local retrieval.
- The executed completion was not influenced by Obsidian-backed evidence.
- The proof requirement that Obsidian-backed evidence be selected and injected into executed completion context was not satisfied.

## Debug Trace Comparison

The debug trace was present and is useful for diagnosis, but it matched the same non-Obsidian outcome rather than rescuing proof:

- `trace_available=true`
- `retrieval_provenance.retrieval_status=workspace_local_success`
- `semantic_total=1`
- `obsidian_semantic=0`
- `semantic_count=1`
- `obsidian_count=0`
- `linked_document_count=2`

One retrieved document in the trace pointed at an older semantic retrieval artifact from a prior thread, which reinforces why trace-only evidence cannot be treated as proof of the current sentinel path.

## Non-Authority-Widening Evidence

During this proof run, the following were not invoked:

- Command Center dispatch
- coding worker dispatch
- lease allocation from UI
- terminal execution from UI
- plugin runtime activation
- merge automation

The proof stayed on supported backend, health, retrieval, and task-event surfaces only.

## Validation Results

- `./.venv/bin/python -m pytest tests/proofs/test_workspace_obsidian_e2e_contract.py` -> `11 passed`
- `./.venv/bin/python scripts/validate_docs.py` -> passed
- `./.venv/bin/python -m py_compile scripts/proofs/prove_workspace_obsidian_e2e.py` -> passed
- `git diff --check` -> passed

## Final Result

`FAIL`

### Explicit Non-Claims

- Workspace-local Obsidian retrieval is not release-evidenced on current `main`.
- Vector-store searchability alone is not enough.
- Debug trace alone is not enough.
- The worker-visible completion payload did not show Obsidian selection or injection.
- The assistant output did not reflect the expected workspace sentinel token.

### Follow-Up Recommendation

Investigate the workspace retrieval selection path so Obsidian-backed hits survive into the executed completion payload. The current evidence suggests the workspace posture is accepted and the note is searchable, but the broker did not select Obsidian evidence for injection.

## Post-Fix Note

On 2026-05-14, after repairing the workspace Obsidian retrieval path and restarting the supported Compose backend/workers against the current workspace code, the live proof was rerun and passed:

- `task_id=cc954ca5-ecc2-4048-98bd-418b9b927be5`
- `thread_id=45`
- `assistant_match=true`
- `retrieval_provenance.retrieval_status=workspace_local_success`
- `obsidian_semantic_hits=1`
- `obsidian_count=1`
- `obsidian_injected=True`
- `VERDICT: PASS`

This follow-up preserves the original failed proof record above while documenting that the repaired code path now selects and injects Obsidian-backed evidence into the executed completion payload on the supported local Compose runtime.
