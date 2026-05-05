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
