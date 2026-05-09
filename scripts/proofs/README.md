# Proof Harness Suite

This directory contains operator-facing live-proof harnesses for the Codexify supported local Compose path.

## What These Harnesses Prove

Each harness exercises a specific runtime seam end-to-end on the live stack. The harnesses are **not** unit tests, integration tests, or generic smoke tests. They are **release-evidence tools**: they produce operator-readable verdicts that can be attached to evidence packs for release signoff.

## Current Harnesses

### `prove_workspace_obsidian_e2e.py`

**Seam:** `retrievalSource="workspace"` completion path with Obsidian-backed local notes.

**What it proves:**
1. Health surfaces (`/health`, `/health/chat`, `/api/health/llm`) are healthy.
2. Obsidian indexing can be triggered through the supported `/api/obsidian/index` route.
3. A chat thread and message can be created.
4. A completion request with `retrievalSource="workspace"` is accepted (task_id returned).
5. The task reaches terminal state (not just acceptance).
6. The assistant response contains content derived from the sentinel note.
7. The retrieval posture snapshot shows workspace-local participation.

**What it does NOT prove:**
- Sync automation between Obsidian and Codexify
- First-class connector UX
- Non-Compose install modes
- Any other retrieval source mode (thread, project, personal_knowledge, etc.)

**Required services:**
- Backend (`guardian_api`) running at `BASE` (default: `http://localhost:8888`)
- Redis (queue and task events)
- Postgres (chat messages, trace persistence)
- LLM provider (completion execution)

**Env requirements:**
| Variable | Required | Default |
|---|---|---|
| `BASE` | No | `http://localhost:8888` |
| `GUARDIAN_API_KEY` | Yes (or dev-key fallback) | Falls back to `scripts/dev/dev-key.sh` |

**Command:**
```bash
# With default BASE and dev-key fallback:
python scripts/proofs/prove_workspace_obsidian_e2e.py

# With explicit BASE and key:
BASE=http://localhost:8888 \
  GUARDIAN_API_KEY="$(cat ~/.codex_guardian_key)" \
  python scripts/proofs/prove_workspace_obsidian_e2e.py
```

**Success means:** The script exits 0 and prints a final verdict table with all proof conditions met.

**Failure classes:**

| Exit code | Category | Meaning |
|---|---|---|
| 2 | `HEALTH_CHECK_FAILED` | One or more health surfaces returned non-2xx |
| 3 | `INGESTION_FAILED` | Obsidian index trigger failed on `/api/obsidian/index` |
| 4 | `ACCEPTANCE_FAILED` | Completion request returned non-200 or no task_id |
| 5 | `COMPLETION_TIMEOUT` | Task did not reach terminal state within 120s |
| 6 | `RESPONSE_VERDICT_FAILED` | Assistant response missing sentinel-derived content |
| 7 | `RETRIEVAL_EVIDENCE_FAILED` | Retrieval posture missing workspace signal |
| 8 | `ABORT_MISSING_ENV` | `GUARDIAN_API_KEY` not set and dev-key fallback failed |

## Release-Evidence Workflow

1. Start from a clean `main` checkout.
2. Run `docker compose up --build` and confirm the stack is healthy.
3. Run the harness: `python scripts/proofs/prove_workspace_obsidian_e2e.py`.
4. Attach the full stdout/stderr output and the git commit hash to the evidence pack.
5. The harness output confirms all proof conditions explicitly — look for the final `VERDICT` table.

## Adding a New Harness

1. Create `scripts/proofs/prove_<seam_name>.py`.
2. Follow the pattern of `prove_workspace_obsidian_e2e.py`:
   - Check health surfaces first (fail fast).
   - Distinguish acceptance from completion (queue-backed semantics).
   - Wait for terminal task state before reading results.
   - Print an explicit verdict table.
   - Exit nonzero on any failed condition.
3. Add a narrow test in `tests/proofs/` to validate the harness contract (not the live stack).
4. Document in this README.

## Relationship to Test Suite

- `scripts/proofs/*.py` — live stack harnesses (require running backend)
- `tests/proofs/*.py` — harness contract tests (do NOT require live backend)
- `tests/golden/test_supported_beta_golden_tasks.py` — backend-seam golden tests
- `tests/obsidian/` — Obsidian ingest/retrieval unit tests

Each harness has a corresponding contract test that validates harness behavior without a live stack.
# Proof Harnesses

This directory contains release-evidence harnesses for the supported local Compose path.
They are intentionally narrower than general integration tests.

## `prove_workspace_obsidian_e2e.py`

Canonical live proof for the `retrievalSource="workspace"` seam.

What it proves:
- a local note can be indexed through the supported Obsidian control plane
- a real Guardian thread can be created with `retrievalSource="workspace"`
- the queue-backed completion path completes on the live stack
- the assistant answer reflects the sentinel note
- retrieval/trace evidence shows workspace-local participation on the supported local Compose path

What it does not prove:
- sync automation
- connector UX
- packaged desktop or webUI-only install modes
- any new retrieval subsystem or alternate storage model

### Required services

Use the supported local Compose posture with:
- `backend`
- `db`
- `redis`
- `worker-chat`
- `worker-document-embed`
- `migrator`

`worker-warmup` is helpful but not required for the proof.

### Environment

The harness reads:
- `BASE` with default `http://localhost:8888`
- `GUARDIAN_API_KEY` from the environment, or from `.env` as a fallback

The proof vault is staged under `tmp/` inside the repo so the backend container can see it on the supported Compose mount.

### Run it

```bash
BASE=http://localhost:8888 GUARDIAN_API_KEY="$(scripts/dev/dev-key.sh)" \
python scripts/proofs/prove_workspace_obsidian_e2e.py
```

### Success means

- health checks passed on `/health`, `/health/chat`, `/api/health/llm`, and `/api/health/retrieval`
- the scratch Obsidian vault indexed successfully
- a workspace-scoped completion was accepted and later completed
- the assistant response contained the sentinel token from the proof note
- retrieval evidence showed `workspace_local_success` and Obsidian participation
- the script printed `VERDICT: PASS`

### Failure classes

- health gate failure: the live stack is not healthy enough to run the proof
- Obsidian ingest failure: the scratch vault did not index through the supported control plane
- acceptance failure: the completion route did not accept the turn
- completion failure: the task never reached `task.completed`
- retrieval failure: workspace-local evidence was missing or collapsed to another source mode
- assistant mismatch: the final assistant message did not contain the sentinel token

This harness is a release-evidence harness, not a replacement for the full test suite.
