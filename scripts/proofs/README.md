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

### `mutate_eight_gate_head_check.py`

**Seam:** the eight-gate self-check's migration-head comparison -- not the
runtime.

**What it proves:** that the self-check's assertion about the harness's
Alembic head can actually fail, and that it does not go stale. The
self-check used to expect a *pinned* revision literal, so it failed with
53/54 at every tip whose head had moved, while the harness under test was
reading the real head correctly. The expected head is now computed from the
migration source, independently of the harness, so it follows the source
and a harness that computes the wrong head still disagrees with it.

The harness proves four properties:

1. Mutating `eight_gate_evidence._read_checkout_head` to return a stale
   revision makes the self-check fail and exit non-zero.
2. A revision that supersedes the current head moves the expected head with
   it -- the property a pinned literal cannot have.
3. A source with two heads reports no head rather than picking one, so the
   check fails closed.
4. The independent source-level computation names the same head and the same
   revision count as Alembic's own revision map.

Each mutation starts from the pristine file, so one cannot mask or compose
with the next. Every file is restored byte-for-byte whether the mutation was
caught or not.

**Required services:** Python and Alembic only. The self-check needs no
running stack.

**Command:**
```bash
python scripts/proofs/mutate_eight_gate_head_check.py
```

**Success means:** the script exits 0 and prints a tally line.

**Failure classes:**

| Exit code | Category | Meaning |
|---|---|---|
| 1 | `MUTATION_NOT_CAUGHT` | A mutation was not caught, or a property did not hold |

### `prove_music_job_attribution.py`

**Seam:** the Music Producer's job attribution, end to end against a real
PostgreSQL and a real Agent-DAW service.

**What it proves:**
1. An async compose starts and returns a job handle.
2. The host records the job's project and thread in its own `music_jobs`
   row, written when the handle is minted.
3. The job is polled until it is terminal.
4. The host's own registration path runs.
5. The `media_assets` rows name the right project and thread.

**What it does NOT prove:**
- That the music surface is a supported path. It is behind a quarantining
  profile; `v1-music-producer` is not a qualified supported path.
- Anything about the live Private Preview database, which this harness
  does not advance.
- The engine's quality, its output, or the produced music itself.

**The pass condition is the invariant:** the files are attributed against
the right project and thread, *for every engine exercised*. Whether the
engine echoed the context back is reported as an observation, because that
is a property of the engine and not of the host. Running it against an
engine that discards the context is the point: before the host owned the
attribution, that engine produced files and registered none of them.

**Required services:**
- PostgreSQL, migrated to head, at `DATABASE_URL`
- One or more Agent-DAW services, reachable over HTTP

**Env requirements:**
| Variable | Required | Default |
|---|---|---|
| `DATABASE_URL` | Yes | -- |
| `MUSIC_ATTRIBUTION_ENGINES` | No | `AGENTDAW_SERVICE_URL`, default `http://127.0.0.1:8000` |
| `MUSIC_ATTRIBUTION_JOB_TIMEOUT` | No | `300` seconds |

**Command:**
```bash
DATABASE_URL=postgresql://... \
MUSIC_ATTRIBUTION_ENGINES='v0.1.6=http://127.0.0.1:8771,v0.1.2=http://127.0.0.1:8772' \
  python scripts/proofs/prove_music_job_attribution.py
```

**Success means:** the script exits 0 and prints a `VERDICT` table naming
each engine, its job status, and whether it echoed a context.

**Failure classes:**

| Exit code | Category | Meaning |
|---|---|---|
| 2 | `PRECONDITION_FAILED` | No database URL, or no engine was reachable |
| 3 | `ATTRIBUTION_FAILED` | An engine's files were produced but not attributed |

### `mutate_music_attribution_tests.py`

**Seam:** the attribution tests themselves -- not the runtime.

**What it proves:** that each of five mutations to the real source is
caught by the test that names it. A test that passes with and without the
fix proves nothing, so this harness applies each mutation in turn, runs
the one test, and asserts that it fails.

It restores every file it touches from a byte-verified backup whether the
mutation was caught or not, so the working tree is left as it was found.

**Required services:** PostgreSQL at `TEST_DATABASE_URL`, and pytest.

**Command:**
```bash
TEST_DATABASE_URL=postgresql://... \
  python scripts/proofs/mutate_music_attribution_tests.py
```

**Success means:** the script exits 0 and prints one line per mutation
naming the test that caught it.

**Failure classes:**

| Exit code | Category | Meaning |
|---|---|---|
| 2 | `PRECONDITION_FAILED` | No database URL |
| 3 | `MUTATION_NOT_CAUGHT` | A mutation was not caught, or could not be applied |

### `mutate_local_node_identity_tests.py`

**Seam:** the local-node identity tests themselves -- not the runtime.

**What it proves:** that each of four mutations to the real source is caught
by the test that names it. A test that passes with and without the fix
proves nothing, so this harness applies each mutation in turn, runs the one
test, and asserts that it fails.

Each mutation starts from the pristine file, so one mutation cannot mask or
compose with the next. It restores every file it touches from a
byte-verified backup whether the mutation was caught or not, so the working
tree is left as it was found.

**Required services:** pytest only. The tests build their own in-memory
SQLite engine.

**Command:**
```bash
python scripts/proofs/mutate_local_node_identity_tests.py
```

**Success means:** the script exits 0 and prints one line per mutation
naming the test that caught it.

**Failure classes:**

| Exit code | Category | Meaning |
|---|---|---|
| 1 | `MUTATION_NOT_CAUGHT` | A mutation was not caught, or could not be applied |

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
